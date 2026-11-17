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
            allowed_parent_origins=frozenset({"https://office.example"}),
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
        with self.assertRaises(ValueError):
            BridgeHTTPServer(lambda _request: BridgeResponse(b""), host="::1")


    def test_init_endpoint_returns_captured_bridge_script(self):
        status, body, headers = self.request(
            "GET",
            "/?init=40169_57326",
            headers={"Referer": "https://office.example/"},
        )
        script = body.decode("iso-8859-1")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "text/html; charset=ISO-8859-1")
        self.assertEqual(headers["Access-Control-Allow-Origin"], "*")
        self.assertIn(f"http://127.0.0.1:{self.port}?invoke=", script)
        self.assertIn('"https://office.example/"', script)
        self.assertIn("addEventListener", script)
        self.assertIn("attachEvent", script)
        self.assertIn("responseText", script)
        self.assertTrue(script.endswith("</script>"))
        self.assertNotIn("</body></html>", script)

    def test_init_endpoint_rejects_ambiguous_duplicate_referer(self):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=2)
        conn.putrequest("GET", "/?init=123_456")
        conn.putheader("Referer", "https://office.example/")
        conn.putheader("Referer", "https://attacker.example/")
        conn.endheaders()
        response = conn.getresponse()
        self.assertEqual(response.status, 403)
        self.assertEqual(response.read(), b"init_referer_required")
        conn.close()

    def test_init_endpoint_requires_allowlisted_parent_referer(self):
        status, body, _ = self.request("GET", "/?init=123_456")
        self.assertEqual(status, 403)
        self.assertEqual(body, b"init_referer_required")

        status, body, _ = self.request(
            "GET",
            "/?init=123_456",
            headers={"Referer": "https://attacker.example/"},
        )
        self.assertEqual(status, 403)
        self.assertEqual(body, b"init_origin_not_allowed")

    def test_init_endpoint_rejects_unrecognized_query_shape(self):
        status, body, _ = self.request(
            "GET",
            "/?init=not-a-captured-token",
            headers={"Referer": "https://office.example/"},
        )
        self.assertEqual(status, 404)
        self.assertEqual(body, b"")

    def test_health_endpoint(self):
        status, body, headers = self.request("GET", "/healthz")
        self.assertEqual(status, 200)
        self.assertEqual(body, b'{"status":"ok"}')
        self.assertEqual(headers["Cache-Control"], "no-store")

    def test_legacy_agent_heartbeat_endpoint(self):
        status, body, headers = self.request("GET", "/?heartbeat")
        self.assertEqual(status, 200)
        self.assertEqual(body, b"TickTack")
        self.assertEqual(headers["Content-Length"], "8")
        self.assertEqual(headers["Content-Type"], "text/html; charset=ISO-8859-1")

    def test_post_preserves_opaque_body_and_query(self):
        payload = b'<emwat><method class="EditWordDocument"/></emwat>'
        status, body, headers = self.request(
            "POST", "/?invoke=12345", payload,
            {"Content-Type": "text/plain;charset=UTF-8", "Origin": "https://office.example"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(body, b"<reply/>")
        self.assertEqual(headers.get("Access-Control-Allow-Origin"), "https://office.example")
        self.assertEqual(headers.get("Access-Control-Allow-Headers"), "*")
        self.assertEqual(headers.get("Access-Control-Allow-Method"), "*")
        self.assertEqual(self.seen[0].body, payload)
        self.assertEqual(self.seen[0].query, "invoke=12345")
        self.assertEqual(self.seen[0].origin, "https://office.example")

    def test_document_post_waits_for_close_while_heartbeat_remains_responsive(self):
        entered = threading.Event()
        release = threading.Event()
        completed = threading.Event()
        outcome = {}

        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

        def close_driven_handler(_request):
            entered.set()
            if not release.wait(timeout=3):
                raise RuntimeError("test_close_event_timeout")
            return BridgeResponse(b"<final-document/>")

        self.server = BridgeHTTPServer(
            close_driven_handler,
            allowed_origins=frozenset({"https://office.example"}),
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.host, self.port = self.server.address

        def post_document():
            outcome["response"] = self.request(
                "POST",
                "/?invoke=54321",
                b'<emwat><method class="EditWordDocument"/></emwat>',
                {"Origin": "https://office.example"},
            )
            completed.set()

        request_thread = threading.Thread(target=post_document, daemon=True)
        request_thread.start()
        self.assertTrue(entered.wait(timeout=1))
        self.assertFalse(completed.wait(timeout=0.05))

        # A long-running document session must not block the independent
        # agent heartbeat route handled by the threaded bridge.
        heartbeat_status, heartbeat_body, _ = self.request("GET", "/?heartbeat")
        self.assertEqual((heartbeat_status, heartbeat_body), (200, b"TickTack"))
        self.assertFalse(completed.is_set())

        release.set()
        request_thread.join(timeout=2)
        self.assertTrue(completed.is_set())
        self.assertEqual(outcome["response"][0:2], (200, b"<final-document/>"))

    def test_host_header_must_match_loopback_listener(self):
        status, body, _ = self.request(
            "GET", "/healthz", headers={"Host": "attacker.example:1984"}
        )
        self.assertEqual(status, 400)
        self.assertEqual(body, b"invalid_host_header")

    def test_host_header_cannot_contain_a_path(self):
        status, body, _ = self.request(
            "GET", "/healthz", headers={"Host": f"{self.host}:{self.port}/evil"}
        )
        self.assertEqual(status, 400)
        self.assertEqual(body, b"invalid_host_header")

    def test_duplicate_content_length_is_rejected(self):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=2)
        conn.putrequest("POST", "/")
        conn.putheader("Content-Length", "1")
        conn.putheader("Content-Length", "1")
        conn.endheaders()
        response = conn.getresponse()
        self.assertEqual(response.status, 400)
        self.assertEqual(response.read(), b"invalid_content_length")
        conn.close()

    def test_non_decimal_content_length_is_rejected(self):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=2)
        conn.putrequest("POST", "/")
        conn.putheader("Content-Length", "+1")
        conn.endheaders()
        response = conn.getresponse()
        self.assertEqual(response.status, 400)
        self.assertEqual(response.read(), b"invalid_content_length")
        conn.close()

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

    def test_duplicate_origin_headers_are_rejected_before_dispatch(self):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=2)
        conn.putrequest("POST", "/")
        conn.putheader("Content-Length", "1")
        conn.putheader("Origin", "https://office.example")
        conn.putheader("Origin", "https://attacker.example")
        conn.endheaders(b"x")
        response = conn.getresponse()
        self.assertEqual(response.status, 400)
        self.assertEqual(response.read(), b"invalid_origin_header")
        conn.close()
        self.assertEqual(self.seen, [])

    def test_duplicate_content_type_headers_are_rejected(self):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=2)
        conn.putrequest("POST", "/")
        conn.putheader("Content-Length", "1")
        conn.putheader("Origin", "https://office.example")
        conn.putheader("Content-Type", "text/plain")
        conn.putheader("Content-Type", "application/xml")
        conn.endheaders(b"x")
        response = conn.getresponse()
        self.assertEqual(response.status, 400)
        self.assertEqual(response.read(), b"invalid_content_type")
        conn.close()
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
