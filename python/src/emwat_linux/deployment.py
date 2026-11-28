"""Evidence-backed default deployment composition for the Almas loopback bridge."""
from __future__ import annotations

from emwat_linux.application import create_libreoffice_bridge_server
from emwat_linux.bridge import BridgeRequest, BridgeResponse
from emwat_linux.bridge_supervisor import BridgeSupervisor
from emwat_linux.document_coordinator import DocumentRunResult
from emwat_linux.sessions import DocumentState

ALMAS_BRIDGE_HOST = "127.0.0.1"
ALMAS_BRIDGE_PORT = 1984
ALMAS_LOOPBACK_ORIGIN = "http://127.0.0.1:1984"
ALMAS_MAX_REQUEST_BYTES = 128 * 1024 * 1024
ALMAS_MAX_RESPONSE_BYTES = 96 * 1024 * 1024


def explicit_discard_response(
    result: DocumentRunResult,
    _request: BridgeRequest,
) -> BridgeResponse:
    """Fail closed for explicit operation discard; this is not Windows parity."""
    if result.session.state is not DocumentState.DISCARDED or result.payload is not None:
        raise ValueError("discard_response_requires_explicit_discarded_session")
    return BridgeResponse(
        body=b"operation_discarded",
        content_type="text/plain; charset=utf-8",
        status=409,
    )


def create_default_bridge_supervisor() -> BridgeSupervisor:
    """Create a fresh, evidence-configured Almas bridge server for every start."""
    def server_factory():
        return create_libreoffice_bridge_server(
            host=ALMAS_BRIDGE_HOST,
            port=ALMAS_BRIDGE_PORT,
            allowed_origins=frozenset({ALMAS_LOOPBACK_ORIGIN}),
            allowed_parent_origins=frozenset({ALMAS_LOOPBACK_ORIGIN}),
            cancel_response_factory=explicit_discard_response,
            max_request_bytes=ALMAS_MAX_REQUEST_BYTES,
            max_response_bytes=ALMAS_MAX_RESPONSE_BYTES,
            socket_timeout_seconds=10.0,
        )

    return BridgeSupervisor(server_factory)


__all__ = [
    "ALMAS_BRIDGE_HOST",
    "ALMAS_BRIDGE_PORT",
    "ALMAS_LOOPBACK_ORIGIN",
    "ALMAS_MAX_REQUEST_BYTES",
    "ALMAS_MAX_RESPONSE_BYTES",
    "create_default_bridge_supervisor",
    "explicit_discard_response",
]
