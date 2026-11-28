import unittest
from types import SimpleNamespace
from unittest.mock import patch

from emwat_linux.bridge import BridgeRequest
from emwat_linux.deployment import (
    ALMAS_BRIDGE_HOST,
    ALMAS_BRIDGE_PORT,
    ALMAS_LOOPBACK_ORIGIN,
    ALMAS_MAX_REQUEST_BYTES,
    ALMAS_MAX_RESPONSE_BYTES,
    create_default_bridge_supervisor,
    explicit_discard_response,
)
from emwat_linux.sessions import DocumentState


class DeploymentCompositionTests(unittest.TestCase):
    def test_default_factory_uses_captured_loopback_and_explicit_limits(self):
        server = object()
        with patch("emwat_linux.deployment.create_libreoffice_bridge_server", return_value=server) as create:
            supervisor = create_default_bridge_supervisor()
            self.assertIs(supervisor._server_factory(), server)
        create.assert_called_once_with(
            host=ALMAS_BRIDGE_HOST,
            port=ALMAS_BRIDGE_PORT,
            allowed_origins=frozenset({ALMAS_LOOPBACK_ORIGIN}),
            allowed_parent_origins=frozenset({ALMAS_LOOPBACK_ORIGIN}),
            cancel_response_factory=explicit_discard_response,
            max_request_bytes=ALMAS_MAX_REQUEST_BYTES,
            max_response_bytes=ALMAS_MAX_RESPONSE_BYTES,
            socket_timeout_seconds=10.0,
        )
        self.assertEqual(ALMAS_BRIDGE_HOST, "127.0.0.1")
        self.assertEqual(ALMAS_BRIDGE_PORT, 1984)
        self.assertEqual(ALMAS_LOOPBACK_ORIGIN, "http://127.0.0.1:1984")

    def test_explicit_discard_is_fail_closed_and_not_success(self):
        result = SimpleNamespace(
            session=SimpleNamespace(state=DocumentState.DISCARDED),
            payload=None,
        )
        request = BridgeRequest("/", "invoke=123", "text/plain", ALMAS_LOOPBACK_ORIGIN, b"")
        response = explicit_discard_response(result, request)
        self.assertEqual(response.status, 409)
        self.assertEqual(response.content_type, "text/plain; charset=utf-8")
        self.assertEqual(response.body, b"operation_discarded")

    def test_non_discard_result_cannot_use_discard_response(self):
        result = SimpleNamespace(
            session=SimpleNamespace(state=DocumentState.RETURNED),
            payload=b"document",
        )
        request = BridgeRequest("/", "invoke=123", "text/plain", ALMAS_LOOPBACK_ORIGIN, b"")
        with self.assertRaisesRegex(ValueError, "explicit_discarded_session"):
            explicit_discard_response(result, request)


if __name__ == "__main__":
    unittest.main()
