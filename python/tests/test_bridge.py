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

    def test_origin_allowlists_must_be_sets_of_strings(self):
        handler = lambda _request: BridgeResponse(b"")
        for value in ("https://office.example", ["https://office.example"], {None}):
            with self.subTest(allowed_origins=value), self.assertRaisesRegex(
                ValueError, "allowed_origins must be a set of non-empty origin strings"
            ):
                BridgeHTTPServer(handler, allowed_origins=value)
        for value in ("https://office.example", ["https://office.example"], {None}):
            with self.subTest(allowed_parent_origins=value), self.assertRaisesRegex(
                ValueError, "allowed_parent_origins must be a set of non-empty origin strings"
            ):
                BridgeHTTPServer(handler, allowed_parent_origins=value)

    def test_allowed_origins_are_canonicalized_like_browser_origin_values(self):
        server = BridgeHTTPServer(
            lambda _request: BridgeResponse(b""),
            allowed_origins=frozenset({
                "HTTPS://Office.Example:443",
                "http://localhost:80",
            }),
        )
        try:
            self.assertEqual(
                server._allowed_origins,
                frozenset({"https://office.example", "http://localhost"}),
            )
        finally:
            server.server_close()

    def test_allowed_origins_reject_non_origin_urls_and_malformed_ports(self):
        invalid = (
            "ftp://office.example",
            "https://office.example/path",
            "https://user@office.example",
            "https://office.example?query=1",
            "https://office.example#fragment",
            "https://office.example:not-a-port",
            "https://",
        )
        for origin in invalid:
            with self.subTest(origin=origin):
                with self.assertRaises(ValueError) as raised:
                    BridgeHTTPServer(
                        lambda _request: BridgeResponse(b""),
                        allowed_origins=frozenset({origin}),
                    )
                self.assertEqual(
                    str(raised.exception),
                    "allowed_origins must contain bare HTTP(S) origins",
                )

    def test_only_loopback_bind_is_allowed(self):
        with self.assertRaises(ValueError):
            BridgeHTTPServer(lambda _request: BridgeResponse(b""), host="0.0.0.0")
        with self.assertRaises(ValueError):
            BridgeHTTPServer(lambda _request: BridgeResponse(b""), host="::1")

    def test_constructor_rejects_invalid_integer_bounds(self):
        factory = lambda **kwargs: BridgeHTTPServer(
            lambda _request: BridgeResponse(b""), **kwargs
        )
        for parameter in ("port", "max_body_bytes", "max_response_bytes"):
            for value in (True, False, 1.5, 16.0, "16", None):
                with self.subTest(parameter=parameter, value=value):
                    with self.assertRaises(ValueError):
                        factory(**{parameter: value})
        for parameter in ("max_body_bytes", "max_response_bytes"):
            for value in (0, -1):
                with self.subTest(parameter=parameter, value=value):
                    with self.assertRaises(ValueError):
                        factory(**{parameter: value})

    def test_constructor_rejects_non_finite_or_invalid_socket_timeouts(self):
        invalid = (True, False, float("nan"), float("inf"), float("-inf"), 0, -1, "1", 10 ** 1000)
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                BridgeHTTPServer(
                    lambda _request: BridgeResponse(b""),
                    socket_timeout_seconds=value,
                )

    def test_host_must_be_an_address_string(self):
        with self.assertRaises(ValueError):
            BridgeHTTPServer(lambda _request: BridgeResponse(b""), host=2130706433)


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

    def test_post_requires_one_nonempty_invoke_parameter(self):
        for path in ("/", "/?invoke=", "/?invoke=1&invoke=2", "/?other=1"):
            with self.subTest(path=path):
                status, body, _ = self.request(
                    "POST",
                    path,
                    b"<emwat/>",
                    {"Content-Type": "text/plain", "Origin": "https://office.example"},
                )
                self.assertEqual(status, 400)
                self.assertEqual(body, b"invalid_invoke_query")
        self.assertEqual(self.seen, [])

    def test_post_bounds_invoke_query_field_count(self):
        status, body, _ = self.request(
            "POST",
            "/?invoke=1&extra=2&another=3",
            b"<emwat/>",
            {"Content-Type": "text/plain", "Origin": "https://office.example"},
        )
        self.assertEqual(status, 400)
        self.assertEqual(body, b"invalid_invoke_query")
        self.assertEqual(self.seen, [])

    def test_post_rejects_malformed_invoke_query(self):
        status, body, _ = self.request(
            "POST",
            "/?invoke=1&",
            b"<emwat/>",
            {"Content-Type": "text/plain", "Origin": "https://office.example"},
        )
        self.assertEqual(status, 400)
        self.assertEqual(body, b"invalid_invoke_query")
        self.assertEqual(self.seen, [])

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
                b"<emwat><method class=\"EditWordDocument\"/></emwat>",
                {"Origin": "https://office.example"},
            )
            completed.set()

        request_thread = threading.Thread(target=post_document, daemon=True)
        request_thread.start()
        self.assertTrue(entered.wait(timeout=1))
        self.assertFalse(completed.wait(timeout=0.05))

        # The server is threaded: the long-running document session must not
        # block the independent agent heartbeat route.
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

    def test_invalid_handler_status_types_are_rejected(self):
        for status_value in (True, False, 200.5, "200", None, 199, 600):
            with self.subTest(status=status_value):
                self.server._handler = lambda _request, value=status_value: BridgeResponse(
                    b"invalid-status", status=value
                )
                status, body, _ = self.request(
                    "POST",
                    "/?invoke=invalid-status",
                    b"x",
                    {"Origin": "https://office.example"},
                )
                self.assertEqual(status, 500)
                self.assertEqual(body, b"internal_bridge_error")

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
            "POST", "/?invoke=test", b"x", {"Origin": "https://office.example"}
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
            "POST", "/?invoke=test", b"x", {"Origin": "https://office.example"}
        )
        self.assertEqual(status, 500)
        self.assertEqual(body, b"internal_bridge_error")


    def test_init_endpoint_rejects_duplicate_referer_headers(self):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=2)
        conn.putrequest("GET", "/?init=123_456")
        conn.putheader("Referer", "https://office.example/")
        conn.putheader("Referer", "https://attacker.example/")
        conn.endheaders()
        response = conn.getresponse()
        self.assertEqual(response.status, 403)
        self.assertEqual(response.read(), b"init_referer_required")
        conn.close()

    def test_post_rejects_duplicate_origin_headers(self):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=2)
        conn.putrequest("POST", "/?invoke=12345")
        conn.putheader("Content-Length", "1")
        conn.putheader("Origin", "https://office.example")
        conn.putheader("Origin", "https://attacker.example")
        conn.endheaders()
        conn.send(b"x")
        response = conn.getresponse()
        self.assertEqual(response.status, 400)
        self.assertEqual(response.read(), b"invalid_origin_header")
        conn.close()
        self.assertEqual(self.seen, [])

    def test_post_rejects_duplicate_content_type_headers(self):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=2)
        conn.putrequest("POST", "/?invoke=12345")
        conn.putheader("Content-Length", "1")
        conn.putheader("Origin", "https://office.example")
        conn.putheader("Content-Type", "text/plain")
        conn.putheader("Content-Type", "application/xml")
        conn.endheaders()
        conn.send(b"x")
        response = conn.getresponse()
        self.assertEqual(response.status, 400)
        self.assertEqual(response.read(), b"invalid_content_type")
        conn.close()
        self.assertEqual(self.seen, [])


    def test_duplicate_host_header_is_rejected(self):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=2)
        conn.putrequest("GET", "/healthz")
        conn.putheader("Host", f"{self.host}:{self.port}")
        conn.endheaders()
        response = conn.getresponse()
        self.assertEqual(response.status, 400)
        self.assertEqual(response.read(), b"invalid_host_header")
        conn.close()

    def test_transfer_encoding_is_rejected_even_with_content_length(self):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=2)
        conn.putrequest("POST", "/?invoke=12345")
        conn.putheader("Content-Length", "1")
        conn.putheader("Transfer-Encoding", "chunked")
        conn.putheader("Origin", "https://office.example")
        conn.endheaders()
        conn.send(b"x")
        response = conn.getresponse()
        self.assertEqual(response.status, 400)
        self.assertEqual(response.read(), b"transfer_encoding_not_supported")
        conn.close()
        self.assertEqual(self.seen, [])


    def test_constructor_rejects_non_callable_handler(self):
        for handler in (None, "handler", object()):
            with self.subTest(handler=handler), self.assertRaisesRegex(
                ValueError, "handler must be callable"
            ):
                BridgeHTTPServer(handler)

    def test_constructor_requires_boolean_origin_policy(self):
        for value in (None, 0, 1, "false", [], object()):
            with self.subTest(value=value), self.assertRaisesRegex(
                ValueError, "require_origin must be a boolean"
            ):
                BridgeHTTPServer(
                    lambda _request: BridgeResponse(b""),
                    require_origin=value,
                )
        # Both explicit boolean settings remain supported.
        for value in (True, False):
            server = BridgeHTTPServer(
                lambda _request: BridgeResponse(b""),
                require_origin=value,
            )
            server.server_close()

if __name__ == "__main__":
    unittest.main()
