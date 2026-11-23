"""Supervised, one-shot lifecycle for the local EMWAT bridge server.

This module deliberately does not choose Almas origins, Cancel/Discard wire
responses, or process policy. Callers must compose a fully configured server
before handing it to the runtime.
"""
from __future__ import annotations

from enum import Enum
import threading
from typing import Protocol


class _Server(Protocol):
    def serve_forever(self) -> None: ...
    def wait_until_serving(self) -> None: ...
    def shutdown(self) -> None: ...
    def server_close(self) -> None: ...


class BridgeRuntimeState(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


class BridgeRuntime:
    """Run one configured bridge server in a supervised, non-daemon thread.

    The runtime is intentionally one-shot: a closed HTTPServer cannot safely
    be restarted. close() waits for active request workers because the
    underlying BridgeHTTPServer uses non-daemon request threads.
    """

    def __init__(self, server: _Server, *, thread_name: str = "emwat-bridge") -> None:
        if not all(callable(getattr(server, name, None)) for name in (
            "serve_forever", "wait_until_serving", "shutdown", "server_close"
        )):
            raise TypeError("server must provide serve_forever, wait_until_serving, shutdown and server_close")
        if not isinstance(thread_name, str) or not thread_name.strip():
            raise ValueError("thread_name must be a non-empty string")
        self._server = server
        self._thread_name = thread_name
        self._lock = threading.RLock()
        self._close_lock = threading.Lock()
        self._state = BridgeRuntimeState.CREATED
        self._thread: threading.Thread | None = None
        self._failure: BaseException | None = None
        self._closed_socket = False

    @property
    def state(self) -> BridgeRuntimeState:
        with self._lock:
            return self._state

    @property
    def failure(self) -> BaseException | None:
        with self._lock:
            return self._failure

    def start(self) -> None:
        with self._lock:
            if self._state is not BridgeRuntimeState.CREATED:
                raise RuntimeError(f"bridge_runtime_cannot_start_from_{self._state.value}")
            thread = threading.Thread(
                target=self._serve,
                name=self._thread_name,
                daemon=False,
            )
            self._thread = thread
            self._state = BridgeRuntimeState.RUNNING
            try:
                thread.start()
                # Do not allow close() to call BaseServer.shutdown() before
                # serve_forever has entered its loop: that ordering can block
                # forever because BaseServer starts with its shutdown Event unset.
                self._server.wait_until_serving()
            except BaseException as exc:
                self._failure = exc
                self._state = BridgeRuntimeState.FAILED
                raise

    def _serve(self) -> None:
        try:
            self._server.serve_forever()
        except BaseException as exc:
            with self._lock:
                self._failure = exc
                self._state = BridgeRuntimeState.FAILED
            # Keep the exception available through failure without emitting an
            # unhandled-thread traceback into the desktop application's stderr.

    def close(self) -> None:
        # Serialize concurrent callers so every close() return guarantees that
        # socket closure and worker-thread joining have both completed.
        with self._close_lock:
            self._close_once()

    def _close_once(self) -> None:
        with self._lock:
            state = self._state
            thread = self._thread
            if state is BridgeRuntimeState.CREATED:
                self._state = BridgeRuntimeState.STOPPED
                self._closed_socket = True
                close_socket = True
                shutdown_server = False
            elif state is BridgeRuntimeState.RUNNING:
                self._state = BridgeRuntimeState.STOPPING
                close_socket = True
                shutdown_server = True
            elif state is BridgeRuntimeState.STOPPING:
                close_socket = False
                shutdown_server = False
            elif state is BridgeRuntimeState.FAILED:
                close_socket = not self._closed_socket
                self._closed_socket = True
                shutdown_server = False
            else:
                return

        if shutdown_server:
            self._server.shutdown()
        if close_socket:
            self._server.server_close()
            with self._lock:
                self._closed_socket = True
        if thread is not None:
            thread.join()
        with self._lock:
            if self._state is BridgeRuntimeState.STOPPING:
                self._state = BridgeRuntimeState.STOPPED

    def __enter__(self) -> "BridgeRuntime":
        self.start()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()
