"""Loopback HTTP transport for the native EMWAT bridge.

The captured heartbeat and init-script routes are implemented here. Request
bodies remain opaque at the transport layer; XML method parsing and the full
close-time registration contract remain separate, explicitly tested concerns.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
from ipaddress import ip_address
from typing import Callable
from urllib.parse import parse_qsl, urlsplit


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


class _ServingThreadingHTTPServer(ThreadingHTTPServer):
    """ThreadingHTTPServer with a reliable serve-loop readiness handshake."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        self._serving_event = threading.Event()
        super().__init__(*args, **kwargs)

    def service_actions(self) -> None:
        # BaseServer calls this only after serve_forever has entered its loop.
        self._serving_event.set()
        super().service_actions()

    def serve_forever(self, poll_interval: float = 0.5) -> None:
        try:
            super().serve_forever(poll_interval=poll_interval)
        finally:
            # Also release waiters if startup fails before the first loop tick.
            self._serving_event.set()

    def wait_until_serving(self) -> None:
        self._serving_event.wait()


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
        allowed_parent_origins: frozenset[str] = frozenset(),
        max_response_bytes: int = 16 * 1024 * 1024,
        socket_timeout_seconds: float = 10.0,
        require_origin: bool = True,
    ) -> None:
        if not callable(handler):
            raise ValueError("handler must be callable")
        if type(require_origin) is not bool:
            raise ValueError("require_origin must be a boolean")
        if not isinstance(host, str):
            raise ValueError("host must be an IPv4 loopback address string")
        address = ip_address(host)
        if address.version != 4 or not address.is_loopback:
            raise ValueError("EMWAT bridge must bind to an IPv4 loopback address")
        if type(port) is not int or not 0 <= port <= 65535:
            raise ValueError("port must be an integer in the TCP port range")
        if type(max_body_bytes) is not int or max_body_bytes <= 0:
            raise ValueError("max_body_bytes must be a positive integer")
        if type(max_response_bytes) is not int or max_response_bytes <= 0:
            raise ValueError("max_response_bytes must be a positive integer")
        if (
            isinstance(socket_timeout_seconds, bool)
            or not isinstance(socket_timeout_seconds, (int, float))
        ):
            raise ValueError("socket_timeout_seconds must be a finite positive number")
        try:
            timeout_is_finite = math.isfinite(float(socket_timeout_seconds))
        except (OverflowError, ValueError):
            timeout_is_finite = False
        if not timeout_is_finite or socket_timeout_seconds <= 0:
            raise ValueError("socket_timeout_seconds must be a finite positive number")

        if not isinstance(allowed_origins, (set, frozenset)) or any(
            not isinstance(origin, str) or not origin for origin in allowed_origins
        ):
            raise ValueError("allowed_origins must be a set of non-empty origin strings")
        if not isinstance(allowed_parent_origins, (set, frozenset)) or any(
            not isinstance(origin, str) or not origin for origin in allowed_parent_origins
        ):
            raise ValueError("allowed_parent_origins must be a set of non-empty origin strings")

        self._handler = handler
        self._max_body_bytes = max_body_bytes
        self._max_response_bytes = max_response_bytes
        self._socket_timeout_seconds = socket_timeout_seconds
        self._allowed_origins = self._normalize_origins(allowed_origins)
        self._allowed_parent_origins = self._normalize_parent_origins(allowed_parent_origins)
        self._require_origin = require_origin
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

            def _send(self, status: int, body: bytes, content_type: str, extra_headers: dict[str, str] | None = None) -> None:
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                response_origin = getattr(self, "_allowed_response_origin", None)
                if response_origin is not None:
                    self.send_header("Access-Control-Allow-Origin", response_origin)
                    self.send_header("Vary", "Origin")
                for name, value in (extra_headers or {}).items():
                    if any(ch in name or ch in value for ch in "\r\n"):
                        raise ValueError("invalid response header")
                    self.send_header(name, value)
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
                            and parsed_host.username is None and parsed_host.password is None
                            and not parsed_host.path and not parsed_host.query
                            and not parsed_host.fragment)
                except ValueError:
                    return False

            def do_GET(self) -> None:
                if not self._valid_host_header():
                    self._send(400, b"invalid_host_header", "text/plain; charset=utf-8")
                    return
                parsed = urlsplit(self.path)
                if parsed.path == "/" and parsed.query == "heartbeat":
                    # Captured Windows Agent exchange: HTTP 200, body "TickTack".
                    self._send(200, b"TickTack", "text/html; charset=ISO-8859-1")
                elif parsed.path == "/" and parsed.query.startswith("init="):
                    if not re.fullmatch(r"init=\d+_\d+", parsed.query):
                        self._send(404, b"", "text/plain; charset=utf-8")
                        return
                    referers = self.headers.get_all("Referer", [])
                    if len(referers) != 1:
                        self._send(403, b"init_referer_required", "text/plain; charset=utf-8")
                        return
                    parent_origin = owner._referer_origin(referers[0])
                    if parent_origin is None:
                        self._send(403, b"init_referer_required", "text/plain; charset=utf-8")
                        return
                    if parent_origin not in owner._allowed_parent_origins:
                        self._send(403, b"init_origin_not_allowed", "text/plain; charset=utf-8")
                        return
                    body = owner._build_init_response(parent_origin)
                    self._send(
                        200,
                        body,
                        "text/html; charset=ISO-8859-1",
                        {
                            "Access-Control-Allow-Origin": "*",
                            "Access-Control-Allow-Headers": "*",
                            "Access-Control-Allow-Method": "*",
                        },
                    )
                elif parsed.path == "/healthz":
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
                if self.headers.get("Transfer-Encoding"):
                    self._send(400, b"transfer_encoding_not_supported", "text/plain; charset=utf-8")
                    return
                content_lengths = self.headers.get_all("Content-Length", [])
                if not content_lengths:
                    self._send(411, b"content_length_required", "text/plain; charset=utf-8")
                    return
                if len(content_lengths) != 1:
                    self._send(400, b"invalid_content_length", "text/plain; charset=utf-8")
                    return
                raw_length = self.headers.get("Content-Length")
                if raw_length is None:
                    self._send(411, b"content_length_required", "text/plain; charset=utf-8")
                    return
                if not raw_length.isascii() or not raw_length.isdigit():
                    self._send(400, b"invalid_content_length", "text/plain; charset=utf-8")
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

                origins = self.headers.get_all("Origin", [])
                if len(origins) > 1:
                    self._send(400, b"invalid_origin_header", "text/plain; charset=utf-8")
                    return
                origin = origins[0] if origins else None
                if origin is None and owner._require_origin:
                    self._send(403, b"origin_required", "text/plain; charset=utf-8")
                    return
                if origin is not None and origin not in owner._allowed_origins:
                    self._send(403, b"origin_not_allowed", "text/plain; charset=utf-8")
                    return
                if origin is not None:
                    self._allowed_response_origin = origin

                # The captured browser bridge sends exactly one invoke nonce
                # per POST. Reject ambiguous/missing routing before reading the
                # body or dispatching a method.
                try:
                    invoke_parameters = parse_qsl(
                        parsed.query,
                        keep_blank_values=True,
                        strict_parsing=True,
                        max_num_fields=1,
                    )
                except ValueError:
                    self._send(400, b"invalid_invoke_query", "text/plain; charset=utf-8")
                    return
                if (
                    len(invoke_parameters) != 1
                    or invoke_parameters[0][0] != "invoke"
                    or not invoke_parameters[0][1]
                ):
                    self._send(400, b"invalid_invoke_query", "text/plain; charset=utf-8")
                    return

                body = self.rfile.read(length)
                if len(body) != length:
                    self._send(400, b"incomplete_request_body", "text/plain; charset=utf-8")
                    return

                content_types = self.headers.get_all("Content-Type", [])
                if len(content_types) > 1:
                    self._send(400, b"invalid_content_type", "text/plain; charset=utf-8")
                    return
                request = BridgeRequest(
                    path=parsed.path,
                    query=parsed.query,
                    content_type=content_types[0] if content_types else "",
                    origin=origin,
                    body=body,
                )
                try:
                    response = owner._handler(request)
                    if not isinstance(response, BridgeResponse):
                        raise TypeError("bridge handler must return BridgeResponse")
                    if type(response.status) is not int or not 200 <= response.status <= 599:
                        raise ValueError("invalid HTTP response status")
                    if not isinstance(response.body, bytes) or len(response.body) > owner._max_response_bytes:
                        raise ValueError("invalid or oversized response body")
                    if not isinstance(response.content_type, str) or "\r" in response.content_type or "\n" in response.content_type:
                        raise ValueError("invalid response content type")
                    self._send(
                        response.status,
                        response.body,
                        response.content_type,
                        {
                            # Preserve the exact legacy header spelling recovered from
                            # EmwatService.exe. Origin remains allowlisted above.
                            "Access-Control-Allow-Headers": "*",
                            "Access-Control-Allow-Method": "*",
                        },
                    )
                except Exception:
                    # Do not expose internal exception details to the browser.
                    self._send(
                        500,
                        b"internal_bridge_error",
                        "text/plain; charset=utf-8",
                        {
                            "Access-Control-Allow-Headers": "*",
                            "Access-Control-Allow-Method": "*",
                        },
                    )

            def do_OPTIONS(self) -> None:
                self._send(405, b"method_not_allowed", "text/plain; charset=utf-8")

            def _unsupported(self) -> None:
                self._send(405, b"method_not_allowed", "text/plain; charset=utf-8")

            do_PUT = _unsupported
            do_PATCH = _unsupported
            do_DELETE = _unsupported
            do_HEAD = _unsupported

        self._server = _ServingThreadingHTTPServer((host, port), Handler)
        # Do not abandon active document requests during shutdown. The caller
        # must call shutdown() and then server_close(); ThreadingMixIn will join
        # request workers before server_close() returns.
        self._server.daemon_threads = False
        self._server.request_queue_size = 32

    @staticmethod
    def _normalize_origins(origins: frozenset[str]) -> frozenset[str]:
        """Validate and canonicalize configured browser XHR origins.

        Browser Origin values contain only scheme, host and an optional
        non-default port. Normalize scheme/host case and elide default ports
        so equivalent configuration spellings match the browser header.
        Paths, credentials, query strings and fragments are never origins.
        """
        normalized: set[str] = set()
        for value in origins:
            try:
                parsed = urlsplit(value)
                port = parsed.port
            except ValueError as exc:
                raise ValueError(
                    "allowed_origins must contain bare HTTP(S) origins"
                ) from exc
            if (
                parsed.scheme.lower() not in {"http", "https"}
                or not parsed.netloc
                or parsed.hostname is None
                # An explicit empty port (for example, https://host:) is not
                # equivalent to omitting the port, even though urlsplit.port
                # returns None for both forms.
                or parsed.netloc.endswith(":")
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path
                or parsed.query
                or parsed.fragment
                or any(character.isspace() for character in parsed.hostname)
            ):
                raise ValueError("allowed_origins must contain bare HTTP(S) origins")
            scheme = parsed.scheme.lower()
            hostname = parsed.hostname.lower()
            if ":" in hostname:
                hostname = f"[{hostname}]"
            default_port = 80 if scheme == "http" else 443
            authority = hostname if port in (None, default_port) else f"{hostname}:{port}"
            normalized.add(f"{scheme}://{authority}")
        return frozenset(normalized)

    @staticmethod
    def _normalize_parent_origins(origins: frozenset[str]) -> frozenset[str]:
        """Canonicalize the Almas parent-page origins used by the init route."""
        normalized: set[str] = set()
        for value in origins:
            try:
                parsed = urlsplit(value)
                port = parsed.port
            except ValueError as exc:
                raise ValueError(
                    "allowed parent origins must be bare HTTP(S) origins"
                ) from exc
            if (
                parsed.scheme.lower() not in {"http", "https"}
                or not parsed.netloc
                or parsed.hostname is None
                or parsed.netloc.endswith(":")
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path
                or parsed.query
                or parsed.fragment
                or any(character.isspace() for character in parsed.hostname)
            ):
                raise ValueError("allowed parent origins must be bare HTTP(S) origins")
            scheme = parsed.scheme.lower()
            hostname = parsed.hostname.lower()
            if ":" in hostname:
                hostname = f"[{hostname}]"
            default_port = 80 if scheme == "http" else 443
            authority = hostname if port in (None, default_port) else f"{hostname}:{port}"
            normalized.add(f"{scheme}://{authority}")
        return frozenset(normalized)

    @staticmethod
    def _referer_origin(referer: str | None) -> str | None:
        if not referer:
            return None
        try:
            parsed = urlsplit(referer)
            if (
                parsed.scheme.lower() not in {"http", "https"}
                or not parsed.netloc
                or parsed.username is not None
                or parsed.password is not None
                or parsed.hostname is None
            ):
                return None
            # Reuse the same canonicalization as the configured allowlist so
            # host case and explicit default ports cannot cause false rejects.
            candidate = f"{parsed.scheme}://{parsed.netloc}"
            return next(iter(BridgeHTTPServer._normalize_parent_origins(frozenset({candidate}))))
        except (StopIteration, ValueError):
            return None

    def _build_init_response(self, parent_origin: str) -> bytes:
        port = self._server.server_address[1]
        template = r'''<html><body><script type="text/javascript">var _0x7079=["origin","source","random","floor","POST","http://127.0.0.1:1984?invoke=","open","onreadystatechange","readyState","responseText","postMessage","data","send","message","addEventListener","onmessage","attachEvent","\x3Cinited /\x3E","https://automation.bsi.ir/"];var _origin=null;var _source=null;function invoke(_0xe2ffx4){_origin=_0xe2ffx4[_0x7079[0]];_source=_0xe2ffx4[_0x7079[1]];var _0xe2ffx5= new XMLHttpRequest();var _0xe2ffx6=Math[_0x7079[3]](Math[_0x7079[2]]()*99999);_0xe2ffx5[_0x7079[6]](_0x7079[4],_0x7079[5]+_0xe2ffx6);_0xe2ffx5[_0x7079[7]]=function (){if(_0xe2ffx5[_0x7079[8]]==4){_source[_0x7079[10]](_0xe2ffx5[_0x7079[9]],_origin);} ;} ;_0xe2ffx5[_0x7079[12]](_0xe2ffx4[_0x7079[11]]);} ;try{window[_0x7079[14]](_0x7079[13],function (_0xe2ffx4){invoke(_0xe2ffx4);} ,false);} catch(err){window[_0x7079[16]](_0x7079[15],function (_0xe2ffx4){invoke(_0xe2ffx4);} ,false);} ;parent[_0x7079[10]](_0x7079[17],_0x7079[18]);</script>'''
        script = template.replace(
            "http://127.0.0.1:1984?invoke=",
            f"http://127.0.0.1:{port}?invoke=",
        ).replace(
            '"https://automation.bsi.ir/"',
            json.dumps(parent_origin + "/"),
        )
        return script.encode("iso-8859-1")

    @property
    def address(self) -> tuple[str, int]:
        host, port = self._server.server_address[:2]
        return str(host), int(port)

    def serve_forever(self) -> None:
        self._server.serve_forever(poll_interval=0.2)

    def wait_until_serving(self) -> None:
        """Block until the HTTP serve loop has entered or exited during startup."""
        self._server.wait_until_serving()

    def shutdown(self) -> None:
        self._server.shutdown()

    def server_close(self) -> None:
        self._server.server_close()
