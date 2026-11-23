"""Privacy-preserving in-memory trace of Writer close/save callbacks.

Only fixed event names, attempt numbers, sequence numbers, and monotonic
timestamps are retained. No document content, field values, file paths, or
exception messages are recorded. The trace is diagnostic and never infers
Save/Don't Save/Cancel from callback order.
"""
from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
import time


@dataclass(frozen=True)
class CloseLifecycleEvent:
    sequence: int
    name: str
    attempt: int
    monotonic_ns: int


class CloseLifecycleTrace:
    _EVENTS = frozenset(
        {
            "query_closing",
            "snapshot_succeeded",
            "snapshot_failed",
            "notify_closing",
            "notify_closed",
            "disposing",
            "save_done",
            "save_as_done",
            "saved_state_succeeded",
            "saved_state_failed",
        }
    )

    def __init__(self) -> None:
        self._lock = Lock()
        self._attempt = 0
        self._events: list[CloseLifecycleEvent] = []

    def record(self, name: str) -> CloseLifecycleEvent:
        if name not in self._EVENTS:
            raise ValueError("unsupported_close_trace_event")
        with self._lock:
            if name == "query_closing":
                self._attempt += 1
            event = CloseLifecycleEvent(
                sequence=len(self._events) + 1,
                name=name,
                attempt=self._attempt,
                monotonic_ns=time.monotonic_ns(),
            )
            self._events.append(event)
            return event

    def snapshot(self) -> tuple[CloseLifecycleEvent, ...]:
        with self._lock:
            return tuple(self._events)

    @property
    def attempt_count(self) -> int:
        with self._lock:
            return self._attempt


__all__ = ["CloseLifecycleEvent", "CloseLifecycleTrace"]
