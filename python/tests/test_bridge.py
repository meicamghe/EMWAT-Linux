import http.client
import threading
import unittest

from emwat_linux.bridge import BridgeHTTPServer, BridgeRequest, BridgeResponse


class BridgeHTTPServerTests(unittest.TestCase):
    def setUp(self):
        self.seen = []

        def handler(request: BridgeRequest) -> BridgeResponse:
            self.seen.append(request)
            return BridgeResponse(b"<reply/>")

        self.server = BridgeHTTPServer(
            handler,
            max_body_bytes=128,
            allowed_origins=frozenset({"https://office.example"}),
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.host, self.port = self.server.address

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=2)
        conn.request(method, path, body=body, headers=headers or {})
        response = conn.getresponse()
        result = response.status, response.read(), dict(response.getheaders())
        conn.close()
        return result

    def test_only_loopback_bind_is_allowed(self):
        with self.assertRaises(ValueError):
            BridgeHTTPServer(lambda _request: BridgeResponse(b""), host="0.0.0.0")

    def test_health_endpoint(self):
        status, body, headers = self.request("GET", "/healthz")
        self.assertEqual(status, 200)
        self.assertEqual(body, b'{"status":"ok"}')
        self.assertEqual(headers["Cache-Control"], "no-store")

    def test_post_preserves_opaque_body_and_query(self):
        payload = b'<emwat><method class="EditWordDocument"/></emwat>'
        status, body, headers = self.request(
            "POST", "/?invoke=12345", payload,
            {"Content-Type": "text/plain;charset=UTF-8", "Origin": "https://office.example"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(body, b"<reply/>")
        self.assertEqual(headers.get("Access-Control-Allow-Origin"), "https://office.example")
        self.assertEqual(self.seen[0].body, payload)
        self.assertEqual(self.seen[0].query, "invoke=12345")
        self.assertEqual(self.seen[0].origin, "https://office.example")

    def test_host_header_must_match_loopback_listener(self):
        status, body, _ = self.request(
            "GET", "/healthz", headers={"Host": "attacker.example:1984"}
        )
        self.assertEqual(status, 400)
        self.assertEqual(body, b"invalid_host_header")

    def test_missing_content_length_is_rejected(self):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=2)
        conn.putrequest("POST", "/")
        conn.endheaders()
        response = conn.getresponse()
        self.assertEqual(response.status, 411)
        self.assertEqual(response.read(), b"content_length_required")
        conn.close()

    def test_oversized_handler_response_is_not_sent(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.server = BridgeHTTPServer(
            lambda _request: BridgeResponse(b"x" * 9),
            max_response_bytes=8,
            allowed_origins=frozenset({"https://office.example"}),
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.host, self.port = self.server.address
        status, body, _ = self.request(
            "POST", "/", b"x", {"Origin": "https://office.example"}
        )
        self.assertEqual(status, 500)
        self.assertEqual(body, b"internal_bridge_error")

    def test_missing_origin_is_rejected_by_default(self):
        status, body, _ = self.request("POST", "/", b"x")
        self.assertEqual(status, 403)
        self.assertEqual(body, b"origin_required")
        self.assertEqual(self.seen, [])

    def test_unlisted_origin_is_rejected(self):
        status, body, _ = self.request(
            "POST", "/", b"x", {"Origin": "https://attacker.example"}
        )
        self.assertEqual(status, 403)
        self.assertEqual(body, b"origin_not_allowed")
        self.assertEqual(self.seen, [])

    def test_oversized_body_is_rejected_before_read(self):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=2)
        conn.putrequest("POST", "/")
        conn.putheader("Content-Length", "129")
        conn.endheaders()
        response = conn.getresponse()
        self.assertEqual(response.status, 413)
        self.assertEqual(response.read(), b"request_too_large")
        conn.close()
        self.assertEqual(self.seen, [])

    def test_unknown_route_and_method_are_rejected(self):
        self.assertEqual(self.request("POST", "/other", b"x")[0], 404)
        self.assertEqual(self.request("PUT", "/", b"x")[0], 405)

    def test_handler_failure_is_sanitized(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

        def fail(_request):
            raise RuntimeError("private diagnostic")

        self.server = BridgeHTTPServer(
            fail, allowed_origins=frozenset({"https://office.example"})
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.host, self.port = self.server.address
        status, body, _ = self.request(
            "POST", "/", b"x", {"Origin": "https://office.example"}
        )
        self.assertEqual(status, 500)
        self.assertEqual(body, b"internal_bridge_error")


if __name__ == "__main__":
    unittest.main()
