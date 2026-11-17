"""Composition root for the EMWAT local bridge.

Production callers must explicitly allow the loopback Origin used by the browser XHR,
separately allow the Almas parent-page origins used by the init script, and supply
the method handlers supported by that installation. No legacy method is enabled
implicitly.
"""
from __future__ import annotations

from collections.abc import Mapping

from emwat_linux.bridge import BridgeHTTPServer
from emwat_linux.dispatcher import MethodHandler, XMLMethodDispatcher
from emwat_linux.bridge import BridgeRequest, BridgeResponse
from emwat_linux.document_coordinator import DocumentRunResult
from emwat_linux.office_adapter import OfficeAdapter
from typing import Callable


def create_bridge_server(
    *,
    allowed_origins: frozenset[str],
    handlers: Mapping[str, MethodHandler],
    allowed_parent_origins: frozenset[str] = frozenset(),
    host: str = "127.0.0.1",
    port: int = 1984,
    max_request_bytes: int = 16 * 1024 * 1024,
    max_response_bytes: int = 16 * 1024 * 1024,
    socket_timeout_seconds: float = 10.0,
) -> BridgeHTTPServer:
    """Build the loopback HTTP server with an explicit XML method registry."""
    dispatcher = XMLMethodDispatcher(max_payload_bytes=max_request_bytes)
    for class_name, handler in handlers.items():
        dispatcher.register(class_name, handler)
    return BridgeHTTPServer(
        dispatcher,
        host=host,
        port=port,
        max_body_bytes=max_request_bytes,
        max_response_bytes=max_response_bytes,
        socket_timeout_seconds=socket_timeout_seconds,
        allowed_origins=allowed_origins,
        allowed_parent_origins=allowed_parent_origins,
        require_origin=True,
    )


def create_libreoffice_bridge_server(
    *,
    allowed_origins: frozenset[str],
    cancel_response_factory: Callable[[DocumentRunResult, BridgeRequest], BridgeResponse],
    allowed_parent_origins: frozenset[str] = frozenset(),
    office_adapter: OfficeAdapter | None = None,
    additional_handlers: Mapping[str, MethodHandler] | None = None,
    host: str = "127.0.0.1",
    port: int = 1984,
    max_request_bytes: int = 128 * 1024 * 1024,
    max_response_bytes: int = 96 * 1024 * 1024,
    max_document_bytes: int = 64 * 1024 * 1024,
    socket_timeout_seconds: float = 10.0,
) -> BridgeHTTPServer:
    """Compose the captured EditWordDocument route with LibreOffice UNO.

    The cancellation response remains a required injection because its exact
    Windows wire envelope has not been captured. Additional method handlers
    may be supplied, but cannot replace EditWordDocument. The default 64 MiB
    document limit is paired with 128 MiB request and 96 MiB response bounds
    to account for Base64 expansion and the surrounding XML envelope.
    """
    from emwat_linux.editword_handler import create_editword_handler
    from emwat_linux.editword_service import EditWordDocumentService
    from emwat_linux.libreoffice_adapter import LibreOfficeAdapter

    office = office_adapter if office_adapter is not None else LibreOfficeAdapter()
    service = EditWordDocumentService(office, max_document_bytes=max_document_bytes)
    edit_word_handler = create_editword_handler(
        service,
        cancel_response_factory=cancel_response_factory,
        max_response_bytes=max_response_bytes,
    )
    registered_handlers = dict(additional_handlers or {})
    registered_handlers["EditWordDocument"] = edit_word_handler
    return create_bridge_server(
        allowed_origins=allowed_origins,
        allowed_parent_origins=allowed_parent_origins,
        handlers=registered_handlers,
        host=host,
        port=port,
        max_request_bytes=max_request_bytes,
        max_response_bytes=max_response_bytes,
        socket_timeout_seconds=socket_timeout_seconds,
    )
