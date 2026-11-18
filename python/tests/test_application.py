import base64
import http.client
import socket
import threading
import unittest
from unittest.mock import patch

from emwat_linux.application import create_bridge_server, create_libreoffice_bridge_server
from emwat_linux.bridge import BridgeResponse
from emwat_linux.office_adapter import CloseDisposition, OfficeCloseEvent


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


    def test_libreoffice_factory_can_explicitly_enable_secret_service_recovery(self):
        recovery_store = object()
        port = self.free_port()
        with (
            patch(
                "emwat_linux.recovery_key_provider.create_secret_service_encrypted_store",
                return_value=recovery_store,
            ),
            patch("emwat_linux.libreoffice_adapter.LibreOfficeAdapter") as adapter_type,
        ):
            server = create_libreoffice_bridge_server(
                allowed_origins=frozenset({"http://127.0.0.1"}),
                cancel_response_factory=lambda _result, _request: BridgeResponse(b"cancelled"),
                encrypt_recovery=True,
                recovery_root="/tmp/emwat-test-recovery",
                port=port,
            )
            try:
                adapter_type.assert_called_once_with(recovery_store=recovery_store)
            finally:
                server.server_close()

    def test_encrypted_recovery_rejects_caller_supplied_unverified_adapter(self):
        with self.assertRaisesRegex(ValueError, "caller-supplied office_adapter"):
            create_libreoffice_bridge_server(
                allowed_origins=frozenset({"http://127.0.0.1"}),
                office_adapter=object(),
                cancel_response_factory=lambda _result, _request: BridgeResponse(b"cancelled"),
                encrypt_recovery=True,
                port=self.free_port(),
            )

    def test_libreoffice_factory_connects_editword_handler_and_fake_office(self):
        class FakeOffice:
            def __init__(self):
                self.request = None

            def open_document(self, request, *, on_modified, on_saved):
                self.request = request
                return object()

            def wait_for_close(self, handle):
                return OfficeCloseEvent(CloseDisposition.CLOSED)

            def export_final_document(self, handle):
                return bytes.fromhex("d0cf11e0a1b11ae1") + b"final-word-doc"

        office = FakeOffice()
        port = self.free_port()
        local_origin = f"http://127.0.0.1:{port}"
        server = create_libreoffice_bridge_server(
            allowed_origins=frozenset({local_origin}),
            allowed_parent_origins=frozenset({"https://office.example"}),
            office_adapter=office,
            cancel_response_factory=lambda _result, _request: BridgeResponse(
                b"cancelled", content_type="text/plain", status=409
            ),
            port=port,
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            config = base64.b64encode(b"<word-document/>").decode("ascii")
            document = base64.b64encode(
                bytes.fromhex("d0cf11e0a1b11ae1") + b"input-word-doc"
            ).decode("ascii")
            body = (
                '<emwat version="1.0"><method class="EditWordDocument">'
                f'<param name="wordConfig">{config}</param>'
                f'<param name="wordBody">{document}</param>'
                '<param name="signData"></param>'
                '</method></emwat>'
            ).encode("utf-8")
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
            conn.request(
                "POST",
                "/?invoke=local-nonce",
                body=body,
                headers={
                    "Content-Type": "text/plain;charset=UTF-8",
                    "Origin": local_origin,
                },
            )
            response = conn.getresponse()
            payload = response.read()
            self.assertEqual(response.status, 200)
            self.assertIn(b'<response-word status="success">', payload)
            self.assertIn(b"application/msword", payload)
            self.assertEqual(office.request.document_bytes[:8], bytes.fromhex("d0cf11e0a1b11ae1"))
            conn.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
