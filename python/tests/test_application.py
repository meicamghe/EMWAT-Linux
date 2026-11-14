import http.client
import threading
import unittest

from emwat_linux.application import create_bridge_server
from emwat_linux.bridge import BridgeResponse


class ApplicationCompositionTests(unittest.TestCase):
    def test_factory_connects_transport_parser_and_explicit_handler(self):
        seen = []

        def edit_word(call, request):
            seen.append((call.class_name, dict(call.params), request.query))
            return BridgeResponse(
                b"<reply>accepted</reply>",
                content_type="application/xml; charset=utf-8",
            )

        server = create_bridge_server(
            allowed_origins=frozenset({"https://office.example"}),
            handlers={"EditWordDocument": edit_word},
            port=0,
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            host, port = server.address
            conn = http.client.HTTPConnection(host, port, timeout=2)
            body = (
                b'<emwat version="1.0"><method class="EditWordDocument">'
                b'<param name="wordConfig">opaque-config</param>'
                b'</method></emwat>'
            )
            conn.request(
                "POST",
                "/?invoke=123",
                body=body,
                headers={
                    "Content-Type": "text/plain;charset=UTF-8",
                    "Origin": "https://office.example",
                },
            )
            response = conn.getresponse()
            payload = response.read()
            self.assertEqual(response.status, 200)
            self.assertEqual(payload, b"<reply>accepted</reply>")
            self.assertEqual(
                response.getheader("Access-Control-Allow-Origin"),
                "https://office.example",
            )
            self.assertEqual(
                seen,
                [("EditWordDocument", {"wordConfig": "opaque-config"}, "invoke=123")],
            )
            conn.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_factory_does_not_allow_missing_or_unlisted_origin(self):
        server = create_bridge_server(
            allowed_origins=frozenset({"https://office.example"}),
            handlers={},
            port=0,
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            host, port = server.address
            for headers, expected in [
                ({"Content-Type": "text/plain"}, 403),
                ({"Content-Type": "text/plain", "Origin": "https://evil.example"}, 403),
            ]:
                conn = http.client.HTTPConnection(host, port, timeout=2)
                conn.request("POST", "/", b"x", headers)
                response = conn.getresponse()
                self.assertEqual(response.status, expected)
                response.read()
                conn.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
