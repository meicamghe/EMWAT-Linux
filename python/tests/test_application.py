import http.client
import socket
import threading
import unittest

from emwat_linux.application import create_bridge_server
from emwat_linux.bridge import BridgeResponse


class ApplicationCompositionTests(unittest.TestCase):
    @staticmethod
    def free_port():
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            return sock.getsockname()[1]

    def test_factory_connects_transport_parser_and_explicit_handler(self):
        seen = []

        def edit_word(call, request):
            seen.append((call.class_name, dict(call.params), request.query))
            return BridgeResponse(
                b"<reply>accepted</reply>",
                content_type="application/xml; charset=utf-8",
            )

        port = self.free_port()
        local_origin = f"http://127.0.0.1:{port}"
        server = create_bridge_server(
            allowed_origins=frozenset({local_origin}),
            allowed_parent_origins=frozenset({"https://office.example"}),
            handlers={"EditWordDocument": edit_word},
            port=port,
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
                    "Origin": local_origin,
                },
            )
            response = conn.getresponse()
            payload = response.read()
            self.assertEqual(response.status, 200)
            self.assertEqual(payload, b"<reply>accepted</reply>")
            self.assertEqual(
                response.getheader("Access-Control-Allow-Origin"),
                local_origin,
            )
            self.assertEqual(
                seen,
                [("EditWordDocument", {"wordConfig": "opaque-config"}, "invoke=123")],
            )
            conn.close()
            init_conn = http.client.HTTPConnection(host, port, timeout=2)
            init_conn.request(
                "GET",
                "/?init=123_456",
                headers={"Referer": "https://office.example/"},
            )
            init_response = init_conn.getresponse()
            init_script = init_response.read().decode("iso-8859-1")
            self.assertEqual(init_response.status, 200)
            self.assertIn(f"{local_origin}?invoke=", init_script)
            self.assertIn('"https://office.example/"', init_script)
            init_conn.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_factory_does_not_allow_missing_or_unlisted_origin(self):
        port = self.free_port()
        local_origin = f"http://127.0.0.1:{port}"
        server = create_bridge_server(
            allowed_origins=frozenset({local_origin}),
            handlers={},
            port=port,
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
