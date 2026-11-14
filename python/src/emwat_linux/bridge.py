"""Loopback HTTP transport for the native EMWAT bridge.

This module deliberately treats request and response bodies as opaque bytes.
The legacy XML envelope and close-time response schema are not fully recovered;
protocol parsing belongs in a separately tested handler once that contract is known.
"""
from __future__ import annotations

from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from ipaddress import ip_address
from typing import Callable
from urllib.parse import urlsplit


@dataclass(frozen=True)
class BridgeRequest:
    path: str
    query: str
    content_type: str
    origin: str | None
    body: bytes


@dataclass(frozen=True)
class BridgeResponse:
    body: bytes
    content_type: str = "application/xml; charset=utf-8"
    status: int = 200


RequestHandler = Callable[[BridgeRequest], BridgeResponse]


class BridgeHTTPServer:
    """Small, bounded HTTP server that can only listen on IPv4 loopback."""

    def __init__(
        self,
        handler: RequestHandler,
        *,
        host: str = "127.0.0.1",
        port: int = 0,
        max_body_bytes: int = 16 * 1024 * 1024,
        allowed_origins: frozenset[str] = frozenset(),
        max_response_bytes: int = 16 * 1024 * 1024,
        socket_timeout_seconds: float = 10.0,
    ) -> None:
        if not ip_address(host).is_loopback:
            raise ValueError("EMWAT bridge must bind to a loopback address")
        if not 0 <= port <= 65535:
            raise ValueError("invalid TCP port")
        if max_body_bytes <= 0:
            raise ValueError("max_body_bytes must be positive")
        if max_response_bytes <= 0:
            raise ValueError("max_response_bytes must be positive")
        if socket_timeout_seconds <= 0:
            raise ValueError("socket_timeout_seconds must be positive")

        self._handler = handler
        self._max_body_bytes = max_body_bytes
        self._max_response_bytes = max_response_bytes
        self._socket_timeout_seconds = socket_timeout_seconds
        self._allowed_origins = allowed_origins
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"
            server_version = "EMWAT-Bridge"
            sys_version = ""

            def setup(self) -> None:
                super().setup()
                self.connection.settimeout(owner._socket_timeout_seconds)

            def log_message(self, _format: str, *_args: object) -> None:
                # Never log request bodies, query values, or Origin by default.
                return

            def _send(self, status: int, body: bytes, content_type: str) -> None:
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                response_origin = getattr(self, "_allowed_response_origin", None)
                if response_origin is not None:
                    self.send_header("Access-Control-Allow-Origin", response_origin)
                    self.send_header("Vary", "Origin")
                self.send_header("Connection", "close")
                self.end_headers()
                if body:
                    self.wfile.write(body)
                self.close_connection = True

            def _valid_host_header(self) -> bool:
                values = self.headers.get_all("Host", [])
                if len(values) != 1:
                    return False
                try:
                    parsed_host = urlsplit("//" + values[0])
                    expected_host, expected_port = owner._server.server_address[:2]
                    return (parsed_host.hostname == str(expected_host).lower()
                            and parsed_host.port == int(expected_port)
                            and parsed_host.username is None and parsed_host.password is None)
                except ValueError:
                    return False

            def do_GET(self) -> None:
                if not self._valid_host_header():
                    self._send(400, b"invalid_host_header", "text/plain; charset=utf-8")
                    return
                parsed = urlsplit(self.path)
                if parsed.path == "/healthz":
                    self._send(200, b'{"status":"ok"}', "application/json; charset=utf-8")
                else:
                    self._send(404, b"", "text/plain; charset=utf-8")

            def do_POST(self) -> None:
                parsed = urlsplit(self.path)
                if not self._valid_host_header():
                    self._send(400, b"invalid_host_header", "text/plain; charset=utf-8")
                    return
                if parsed.path != "/":
                    self._send(404, b"", "text/plain; charset=utf-8")
                    return
                content_lengths = self.headers.get_all("Content-Length", [])
                if not content_lengths:
                    self._send(411, b"content_length_required", "text/plain; charset=utf-8")
                    return
                if len(content_lengths) != 1:
                    self._send(400, b"invalid_content_length", "text/plain; charset=utf-8")
                    return
                if self.headers.get("Transfer-Encoding"):
                    self._send(400, b"transfer_encoding_not_supported", "text/plain; charset=utf-8")
                    return
                raw_length = self.headers.get("Content-Length")
                if raw_length is None:
                    self._send(411, b"content_length_required", "text/plain; charset=utf-8")
                    return
                try:
                    length = int(raw_length, 10)
                except ValueError:
                    self._send(400, b"invalid_content_length", "text/plain; charset=utf-8")
                    return
                if length < 0:
                    self._send(400, b"invalid_content_length", "text/plain; charset=utf-8")
                    return
                if length > owner._max_body_bytes:
                    self._send(413, b"request_too_large", "text/plain; charset=utf-8")
                    return

                origin = self.headers.get("Origin")
                if origin is not None and origin not in owner._allowed_origins:
                    self._send(403, b"origin_not_allowed", "text/plain; charset=utf-8")
                    return
                if origin is not None:
                    self._allowed_response_origin = origin

                body = self.rfile.read(length)
                if len(body) != length:
                    self._send(400, b"incomplete_request_body", "text/plain; charset=utf-8")
                    return

                request = BridgeRequest(
                    path=parsed.path,
                    query=parsed.query,
                    content_type=self.headers.get("Content-Type", ""),
                    origin=origin,
                    body=body,
                )
                try:
                    response = owner._handler(request)
                    if not isinstance(response, BridgeResponse):
                        raise TypeError("bridge handler must return BridgeResponse")
                    if not 200 <= response.status <= 599:
                        raise ValueError("invalid HTTP response status")
                    if not isinstance(response.body, bytes) or len(response.body) > owner._max_response_bytes:
                        raise ValueError("invalid or oversized response body")
                    if not isinstance(response.content_type, str) or "\r" in response.content_type or "\n" in response.content_type:
                        raise ValueError("invalid response content type")
                    self._send(response.status, response.body, response.content_type)
                except Exception:
                    # Do not expose internal exception details to the browser.
                    self._send(500, b"internal_bridge_error", "text/plain; charset=utf-8")

            def do_OPTIONS(self) -> None:
                self._send(405, b"method_not_allowed", "text/plain; charset=utf-8")

            def _unsupported(self) -> None:
                self._send(405, b"method_not_allowed", "text/plain; charset=utf-8")

            do_PUT = _unsupported
            do_PATCH = _unsupported
            do_DELETE = _unsupported
            do_HEAD = _unsupported

        self._server = ThreadingHTTPServer((host, port), Handler)
        self._server.daemon_threads = True
        self._server.request_queue_size = 32

    @property
    def address(self) -> tuple[str, int]:
        host, port = self._server.server_address[:2]
        return str(host), int(port)

    def serve_forever(self) -> None:
        self._server.serve_forever(poll_interval=0.2)

    def shutdown(self) -> None:
        self._server.shutdown()

    def server_close(self) -> None:
        self._server.server_close()
