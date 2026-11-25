"""Document lifecycle state machine independent of the office-suite adapter.

A user pressing Save, the office engine persisting bytes, and EMWAT returning
the document on close are deliberately represented as separate operations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from threading import RLock


class DocumentState(str, Enum):
    CREATED = "created"
    INITIALIZING = "initializing"
    OPENED = "opened"
    DIRTY = "dirty"
    FINALIZING = "finalizing"
    RETURNED = "returned"
    DISCARDED = "discarded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class InvalidTransition(RuntimeError):
    """Raised when a document session receives an invalid lifecycle event."""


@dataclass
class DocumentSession:
    session_id: str
    state: DocumentState = DocumentState.CREATED
    revision: int = 0
    saved_revision: int | None = None
    returned_payload: bytes | None = None
    failure_reason: str | None = None
    _lock: RLock = field(default_factory=RLock, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.session_id or self.session_id != self.session_id.strip():
            raise ValueError("session_id must be a non-empty trimmed string")

    def begin_initialization(self) -> None:
        with self._lock:
            self._require(DocumentState.CREATED)
            self.state = DocumentState.INITIALIZING

    def mark_opened(self) -> None:
        with self._lock:
            self._require(DocumentState.INITIALIZING)
            self.state = DocumentState.OPENED

    def mark_dirty(self) -> int:
        with self._lock:
            if self.state not in (DocumentState.OPENED, DocumentState.DIRTY):
                raise InvalidTransition(f"cannot edit a session in state {self.state.value}")
            self.revision += 1
            self.state = DocumentState.DIRTY
            return self.revision

    def record_engine_save(self) -> None:
        """Record an office-engine save without implying a bridge return/upload."""
        with self._lock:
            if self.state not in (DocumentState.OPENED, DocumentState.DIRTY):
                raise InvalidTransition(f"cannot save a session in state {self.state.value}")
            self.saved_revision = self.revision

    def begin_finalize(self) -> bool:
        """Enter close-time finalization once; return False for duplicate calls."""
        with self._lock:
            if self.state in (DocumentState.FINALIZING, DocumentState.RETURNED):
                return False
            if self.state not in (DocumentState.OPENED, DocumentState.DIRTY):
                raise InvalidTransition(f"cannot finalize a session in state {self.state.value}")
            self.state = DocumentState.FINALIZING
            return True

    def complete_finalize(self, payload: bytes) -> bool:
        """Commit the exact returned document bytes; identical retries are safe."""
        if not isinstance(payload, bytes):
            raise TypeError("payload must be bytes")
        with self._lock:
            if self.state == DocumentState.RETURNED:
                if self.returned_payload != payload:
                    raise InvalidTransition("session was already returned with different bytes")
                return False
            self._require(DocumentState.FINALIZING)
            self.returned_payload = payload
            self.state = DocumentState.RETURNED
            return True

    def fail(self, reason: str) -> None:
        with self._lock:
            if self.state in (DocumentState.RETURNED, DocumentState.DISCARDED, DocumentState.FAILED, DocumentState.CANCELLED):
                raise InvalidTransition(f"cannot fail a terminal session in state {self.state.value}")
            self.failure_reason = reason.strip() or "unspecified_failure"
            self.state = DocumentState.FAILED

    def discard(self) -> None:
        """Terminate without a response after an explicit application-level abort.

        This is not the office UI's "Don't Save" choice: that closes normally
        and returns the previous approved snapshot.

        Do not infer discard merely from a BeforeSave cancellation: the recovered
        native event sink proves a BeforeSave callback, not a separate
        DocumentBeforeClose callback or a complete close/discard decision map.
        """
        with self._lock:
            if self.state not in (DocumentState.OPENED, DocumentState.DIRTY):
                raise InvalidTransition(f"cannot discard a session in state {self.state.value}")
            self.state = DocumentState.DISCARDED

    def cancel_close_attempt(self) -> None:
        """Cancel one close attempt without terminating the document session."""
        with self._lock:
            if self.state not in (DocumentState.OPENED, DocumentState.DIRTY):
                raise InvalidTransition(
                    f"cannot cancel a close attempt in state {self.state.value}"
                )
            # Intentionally preserve OPENED/DIRTY and all revision metadata.

    def cancel(self) -> None:
        """Terminate a session explicitly, distinct from the office UI's Cancel."""
        with self._lock:
            if self.state in (
                DocumentState.FINALIZING, DocumentState.RETURNED,
                DocumentState.DISCARDED, DocumentState.FAILED, DocumentState.CANCELLED,
            ):
                raise InvalidTransition(f"cannot cancel a session in state {self.state.value}")
            self.state = DocumentState.CANCELLED

    def _require(self, expected: DocumentState) -> None:
        if self.state != expected:
            raise InvalidTransition(
                f"expected state {expected.value}, got {self.state.value}"
            )
