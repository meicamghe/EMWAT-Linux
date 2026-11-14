"""Composition root for the EMWAT local bridge.

Production callers must supply the real Almas Gam Origin allowlist and the
method handlers supported by that installation. No legacy method is enabled
implicitly.
"""
from __future__ import annotations

from collections.abc import Mapping

from emwat_linux.bridge import BridgeHTTPServer
from emwat_linux.dispatcher import MethodHandler, XMLMethodDispatcher


def create_bridge_server(
    *,
    allowed_origins: frozenset[str],
    handlers: Mapping[str, MethodHandler],
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
        require_origin=True,
    )
