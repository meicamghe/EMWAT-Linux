"""Explicit allowlisted dispatcher for parsed EMWAT method envelopes."""
from __future__ import annotations

from typing import Callable

from emwat_linux.bridge import BridgeRequest, BridgeResponse
from emwat_linux.protocol import MethodCall, ProtocolError, parse_method_call


MethodHandler = Callable[[MethodCall, BridgeRequest], BridgeResponse]


class XMLMethodDispatcher:
    """Dispatch only methods explicitly registered by the application.

    The native Delphi service prefixes the XML class value with T before
    calling GetClass (for example, EditWordDocument becomes
    TEditWordDocument). Winux keeps the original XML value as its allowlisted
    registry key and never performs unrestricted runtime class resolution.
    No success-shaped XML response is fabricated.
    """

    def __init__(self, *, max_payload_bytes: int = 16 * 1024 * 1024) -> None:
        if type(max_payload_bytes) is not int or max_payload_bytes <= 0:
            raise ValueError("max_payload_bytes must be a positive integer")
        self._max_payload_bytes = max_payload_bytes
        self._handlers: dict[str, MethodHandler] = {}

    def register(self, class_name: str, handler: MethodHandler) -> None:
        if (
            not isinstance(class_name, str)
            or not class_name
            or class_name != class_name.strip()
        ):
            raise ValueError("invalid method class name")
        if not callable(handler):
            raise ValueError("method handler must be callable")
        if class_name in self._handlers:
            raise ValueError(f"handler already registered: {class_name}")
        self._handlers[class_name] = handler

    def __call__(self, request: BridgeRequest) -> BridgeResponse:
        if not isinstance(request, BridgeRequest) or not isinstance(request.body, bytes):
            return BridgeResponse(
                b"invalid_emwat_request",
                content_type="text/plain; charset=utf-8",
                status=400,
            )
        try:
            call = parse_method_call(request.body, max_bytes=self._max_payload_bytes)
        except ProtocolError:
            return BridgeResponse(
                b"invalid_emwat_request",
                content_type="text/plain; charset=utf-8",
                status=400,
            )

        handler = self._handlers.get(call.class_name)
        if handler is None:
            return BridgeResponse(
                b"method_not_implemented",
                content_type="text/plain; charset=utf-8",
                status=501,
            )
        try:
            response = handler(call, request)
        except Exception:
            return BridgeResponse(
                b"internal_method_error",
                content_type="text/plain; charset=utf-8",
                status=500,
            )
        if not isinstance(response, BridgeResponse):
            return BridgeResponse(
                b"invalid_method_response",
                content_type="text/plain; charset=utf-8",
                status=500,
            )
        return response
