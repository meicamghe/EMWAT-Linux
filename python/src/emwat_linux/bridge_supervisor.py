"""Restartable supervisor for explicitly configured EMWAT bridge servers.

The supervisor owns lifecycle only. A deployment must provide a server factory
that supplies evidence-backed Almas origins, handlers, and response contracts.
No network policy or protocol response is inferred here.
"""
from __future__ import annotations

from collections.abc import Callable
from enum import Enum
import threading
from typing import Protocol

from emwat_linux.application_runtime import BridgeRuntime, BridgeRuntimeState


class _Server(Protocol):
    def serve_forever(self) -> None: ...
    def wait_until_serving(self) -> None: ...
    def shutdown(self) -> None: ...
    def server_close(self) -> None: ...


class BridgeSupervisorState(str, Enum):
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


class BridgeSupervisor:
    """Own successive one-shot BridgeRuntime instances from a server factory.

    BridgeRuntime instances cannot be restarted after close. This supervisor
    therefore asks the injected factory for a fresh, fully configured server
    on each start after a successful stop. It never silently retries a failed
    start/stop because doing so could hide a leaked serving thread or socket.
    Call stop() to retry cleanup of a failed runtime before starting again.
    """

    def __init__(
        self,
        server_factory: Callable[[], _Server],
        *,
        runtime_factory: Callable[[_Server], BridgeRuntime] = BridgeRuntime,
    ) -> None:
        if not callable(server_factory):
            raise TypeError("server_factory must be callable")
        if not callable(runtime_factory):
            raise TypeError("runtime_factory must be callable")
        self._server_factory = server_factory
        self._runtime_factory = runtime_factory
        self._lock = threading.RLock()
        self._state = BridgeSupervisorState.IDLE
        self._runtime: BridgeRuntime | None = None
        self._failure: BaseException | None = None

    @property
    def state(self) -> BridgeSupervisorState:
        with self._lock:
            return self._state

    @property
    def runtime(self) -> BridgeRuntime | None:
        with self._lock:
            return self._runtime

    @property
    def failure(self) -> BaseException | None:
        with self._lock:
            return self._failure

    def start(self) -> BridgeRuntime:
        """Start a fresh configured server, or return the active runtime."""
        with self._lock:
            if self._state is BridgeSupervisorState.RUNNING:
                assert self._runtime is not None
                return self._runtime
            if self._state in (
                BridgeSupervisorState.STARTING,
                BridgeSupervisorState.STOPPING,
            ):
                raise RuntimeError(
                    f"bridge_supervisor_busy_{self._state.value}"
                )
            if self._state is BridgeSupervisorState.FAILED:
                raise RuntimeError(
                    "bridge_supervisor_requires_successful_cleanup_before_restart"
                ) from self._failure

            self._state = BridgeSupervisorState.STARTING
            self._failure = None

        runtime: BridgeRuntime | None = None
        try:
            server = self._server_factory()
            runtime = self._runtime_factory(server)
            with self._lock:
                self._runtime = runtime
            runtime.start()
        except BaseException as exc:
            cleanup_error: BaseException | None = None
            if runtime is not None:
                try:
                    runtime.close()
                except BaseException as close_exc:
                    cleanup_error = close_exc
            with self._lock:
                self._runtime = runtime
                self._failure = cleanup_error or exc
                self._state = BridgeSupervisorState.FAILED
            raise

        with self._lock:
            self._runtime = runtime
            if runtime.state is BridgeRuntimeState.RUNNING:
                self._state = BridgeSupervisorState.RUNNING
            else:
                failure = runtime.failure or RuntimeError(
                    "bridge_runtime_did_not_enter_running_state"
                )
                self._failure = failure
                self._state = BridgeSupervisorState.FAILED
                raise RuntimeError(
                    "bridge_supervisor_start_did_not_reach_running_state"
                ) from failure
        return runtime

    def stop(self) -> None:
        """Stop the current runtime; a failed cleanup can be retried."""
        with self._lock:
            if self._state in (
                BridgeSupervisorState.IDLE,
                BridgeSupervisorState.STOPPED,
            ):
                self._state = BridgeSupervisorState.STOPPED
                return
            if self._state in (
                BridgeSupervisorState.STARTING,
                BridgeSupervisorState.STOPPING,
            ):
                raise RuntimeError(
                    f"bridge_supervisor_busy_{self._state.value}"
                )
            runtime = self._runtime
            if runtime is None:
                self._state = BridgeSupervisorState.FAILED
                self._failure = RuntimeError(
                    "bridge_supervisor_missing_runtime_during_cleanup"
                )
                raise self._failure
            self._state = BridgeSupervisorState.STOPPING

        try:
            runtime.close()
        except BaseException as exc:
            with self._lock:
                self._failure = exc
                self._state = BridgeSupervisorState.FAILED
            raise

        with self._lock:
            self._failure = None
            self._state = BridgeSupervisorState.STOPPED
