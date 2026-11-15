"""Coordinate a close-driven document session with an injected office adapter."""
from __future__ import annotations

from dataclasses import dataclass

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
        try:
            session.begin_initialization()
            handle = self._office.open_document(
                request,
                on_modified=session.mark_dirty,
                on_saved=session.record_engine_save,
            )
            if handle is None:
                raise RuntimeError("office_adapter_returned_no_handle")
            session.mark_opened()

            close_event = self._office.wait_for_close(handle)
            if close_event.disposition is CloseDisposition.CANCELLED:
                session.cancel()
                return DocumentRunResult(session=session, payload=None)

            if close_event.disposition is not CloseDisposition.CLOSED:
                raise RuntimeError("office_adapter_returned_invalid_close_event")

            # A close-time return is independent of whether the user pressed Save.
            session.begin_finalize()
            payload = self._office.export_final_document(handle)
            session.complete_finalize(payload)
            return DocumentRunResult(session=session, payload=payload)
        except Exception as exc:
            if session.state not in (
                DocumentState.RETURNED,
                DocumentState.FAILED,
                DocumentState.CANCELLED,
            ):
                session.fail("office_adapter_failure")
            raise OfficeCoordinationError("office_session_failed") from exc
