"""Coordinate a close-driven document session with an injected office adapter."""
from __future__ import annotations

from dataclasses import dataclass
from threading import RLock

from emwat_linux.editword_request import EditWordDocumentRequest
from emwat_linux.office_adapter import CloseDisposition, OfficeAdapter
from emwat_linux.sessions import DocumentSession, DocumentState


class OfficeCoordinationError(RuntimeError):
    """Raised when the office adapter cannot complete a document session."""


@dataclass(frozen=True)
class DocumentRunResult:
    session: DocumentSession
    payload: bytes | None

    @property
    def returned(self) -> bool:
        return self.session.state is DocumentState.RETURNED


class DocumentCoordinator:
    """Keep open/edit/close/export orchestration independent of HTTP and UNO.

    The coordinator does not infer a session ID from the invoke query value:
    that value is a per-request nonce in the observed bridge. Callers must
    supply an independently generated local session identifier.
    """

    def __init__(self, office: OfficeAdapter) -> None:
        self._office = office

    def run(
        self,
        *,
        session_id: str,
        request: EditWordDocumentRequest,
    ) -> DocumentRunResult:
        session = DocumentSession(session_id)
        callbacks_lock = RLock()
        callbacks_active = False

        def on_modified() -> int:
            # Serialize callbacks with close/finalize so late engine events are ignored.
            with callbacks_lock:
                if not callbacks_active:
                    return session.revision
                return session.mark_dirty()

        def on_saved() -> None:
            # Ignore initialization and post-close engine saves.
            with callbacks_lock:
                if callbacks_active:
                    session.record_engine_save()

        try:
            session.begin_initialization()
            handle = self._office.open_document(
                request,
                on_modified=on_modified,
                on_saved=on_saved,
            )
            if handle is None:
                raise RuntimeError("office_adapter_returned_no_handle")
            session.mark_opened()
            with callbacks_lock:
                callbacks_active = True

            close_event = self._office.wait_for_close(handle)
            # Wait for any callback already in progress, then detach both callbacks
            # before interpreting the close result or exporting. Engines may emit
            # delayed events on close, including when the user cancels the session.
            with callbacks_lock:
                callbacks_active = False

            if close_event.disposition is CloseDisposition.DISCARDED:
                session.discard()
                return DocumentRunResult(session=session, payload=None)

            if close_event.disposition is not CloseDisposition.CLOSED:
                raise RuntimeError("office_adapter_returned_invalid_close_event")

            # The adapter exports its last approved snapshot: a successful Save
            # advances it; Don't Save leaves the prior approved snapshot intact.
            # A cancelled close never reaches this point because wait_for_close
            # continues waiting until the document actually closes.
            session.begin_finalize()
            payload = self._office.export_final_document(handle)
            session.complete_finalize(payload)
            return DocumentRunResult(session=session, payload=payload)
        except Exception as exc:
            with callbacks_lock:
                callbacks_active = False
            if session.state not in (
                DocumentState.RETURNED,
                DocumentState.DISCARDED,
                DocumentState.FAILED,
            ):
                session.fail("office_adapter_failure")
            raise OfficeCoordinationError("office_session_failed") from exc
