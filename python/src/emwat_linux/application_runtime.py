"""Supervised, one-shot lifecycle for the local EMWAT bridge server.

This module deliberately does not choose Almas origins, Cancel/Discard wire
responses, or process policy. Callers must compose a fully configured server
before handing it to the runtime.
"""
from __future__ import annotations

from enum import Enum
import math
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
    be restarted. A successful close joins the serving thread. If shutdown
    fails, the join is bounded and the caller receives a failure instead of
    waiting forever; a later close may retry shutdown. The underlying server's
    server_close() can still wait for active non-daemon request workers.
    """

    def __init__(
        self,
        server: _Server,
        *,
        thread_name: str = "emwat-bridge",
        join_timeout_seconds: float = 5.0,
    ) -> None:
        if not all(callable(getattr(server, name, None)) for name in (
            "serve_forever", "wait_until_serving", "shutdown", "server_close"
        )):
            raise TypeError("server must provide serve_forever, wait_until_serving, shutdown and server_close")
        if not isinstance(thread_name, str) or not thread_name.strip():
            raise ValueError("thread_name must be a non-empty string")
        if isinstance(join_timeout_seconds, bool) or not isinstance(
            join_timeout_seconds, (int, float)
        ):
            raise ValueError("join_timeout_seconds must be a finite non-negative number")
        try:
            timeout_value = float(join_timeout_seconds)
        except OverflowError as exc:
            raise ValueError(
                "join_timeout_seconds must be a finite non-negative number"
            ) from exc
        if not math.isfinite(timeout_value) or timeout_value < 0:
            raise ValueError("join_timeout_seconds must be a finite non-negative number")
        self._server = server
        self._thread_name = thread_name
        self._join_timeout_seconds = timeout_value
        self._lock = threading.RLock()
        self._close_lock = threading.Lock()
        self._state = BridgeRuntimeState.CREATED
        self._thread: threading.Thread | None = None
        self._failure: BaseException | None = None
        self._closed_socket = False
        self._shutdown_complete = False
        self._serve_failed = False

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
                self._serve_failed = True
                self._state = BridgeRuntimeState.FAILED
            # Keep the exception available through failure without emitting an
            # unhandled-thread traceback into the desktop application's stderr.

    def close(self) -> None:
        # Serialize concurrent callers. A successful return guarantees socket
        # closure and serving-thread join; failed attempts raise after a bounded
        # join and leave FAILED state for the supervisor to surface or retry.
        with self._close_lock:
            self._close_once()

    def _close_once(self) -> None:
        with self._lock:
            state = self._state
            thread = self._thread
            if state is BridgeRuntimeState.CREATED:
                self._state = BridgeRuntimeState.STOPPING
            elif state is BridgeRuntimeState.RUNNING:
                self._state = BridgeRuntimeState.STOPPING
            elif state not in (BridgeRuntimeState.STOPPING, BridgeRuntimeState.FAILED):
                return

            close_socket = not self._closed_socket
            shutdown_server = (
                thread is not None
                and thread.is_alive()
                and not self._shutdown_complete
            )

        close_error: BaseException | None = None
        if shutdown_server:
            try:
                self._server.shutdown()
            except BaseException as exc:
                close_error = exc
            else:
                with self._lock:
                    self._shutdown_complete = True

        if close_socket:
            try:
                self._server.server_close()
            except BaseException as exc:
                if close_error is None:
                    close_error = exc
            else:
                with self._lock:
                    self._closed_socket = True

        if thread is not None:
            thread.join(timeout=self._join_timeout_seconds)
            if thread.is_alive() and close_error is None:
                close_error = TimeoutError(
                    "bridge_server_thread_did_not_stop_before_join_timeout"
                )

        with self._lock:
            if close_error is not None:
                if self._failure is None:
                    self._failure = close_error
                self._state = BridgeRuntimeState.FAILED
            elif self._closed_socket and (thread is None or not thread.is_alive()):
                if self._serve_failed:
                    self._state = BridgeRuntimeState.FAILED
                else:
                    self._failure = None
                    self._state = BridgeRuntimeState.STOPPED

        if close_error is not None:
            raise close_error

    def __enter__(self) -> "BridgeRuntime":
        self.start()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()
