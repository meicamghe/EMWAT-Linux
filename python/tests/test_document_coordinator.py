import unittest

from emwat_linux.document_coordinator import (
    DocumentCoordinator,
    OfficeCoordinationError,
)
from emwat_linux.editword_request import EditWordDocumentRequest
from emwat_linux.office_adapter import CloseDisposition, OfficeCloseEvent
from emwat_linux.sessions import DocumentState
from emwat_linux.word_config import WordDocumentConfig


def sample_request():
    return EditWordDocumentRequest(
        config=WordDocumentConfig(
            root_attributes={},
            permissions={},
            settings=(),
            fields=(),
            optional_attributes=(),
            requested_types=(),
        ),
        document_bytes=b"input-document",
        sign_data_text="",
        extra_parameters={},
    )


class FakeOffice:
    def __init__(self, *, close=CloseDisposition.CLOSED, output=b"final-document", save=False):
        self.close = close
        self.output = output
        self.save = save
        self.calls = []
        self.on_modified = None
        self.on_saved = None

    def open_document(self, request, *, on_modified, on_saved):
        self.calls.append(("open", request.document_bytes))
        self.on_modified = on_modified
        self.on_saved = on_saved
        # Simulate configuration/field initialization before the session opens.
        on_modified()
        on_saved()
        return object()

    def wait_for_close(self, handle):
        self.calls.append(("wait_for_close", handle))
        self.on_modified()
        if self.save:
            self.on_saved()
        return OfficeCloseEvent(self.close)

    def export_final_document(self, handle):
        self.calls.append(("export_final_document", handle))
        return self.output


class DocumentCoordinatorTests(unittest.TestCase):
    def test_close_returns_final_bytes_without_explicit_save(self):
        office = FakeOffice()
        result = DocumentCoordinator(office).run(
            session_id="local-session-1", request=sample_request()
        )
        self.assertTrue(result.returned)
        self.assertEqual(result.payload, b"final-document")
        self.assertEqual(result.session.state, DocumentState.RETURNED)
        self.assertEqual(result.session.revision, 1)
        self.assertIsNone(result.session.saved_revision)
        self.assertEqual(
            [call[0] for call in office.calls],
            ["open", "wait_for_close", "export_final_document"],
        )

    def test_engine_save_is_recorded_but_does_not_trigger_return(self):
        office = FakeOffice(save=True)
        result = DocumentCoordinator(office).run(
            session_id="local-session-save", request=sample_request()
        )
        self.assertEqual(result.session.saved_revision, 1)
        self.assertEqual(result.session.state, DocumentState.RETURNED)
        self.assertEqual(
            [call[0] for call in office.calls],
            ["open", "wait_for_close", "export_final_document"],
        )

    def test_cancel_does_not_export_document(self):
        office = FakeOffice(close=CloseDisposition.CANCELLED)
        result = DocumentCoordinator(office).run(
            session_id="local-session-2", request=sample_request()
        )
        self.assertFalse(result.returned)
        self.assertIsNone(result.payload)
        self.assertEqual(result.session.state, DocumentState.CANCELLED)
        self.assertEqual([call[0] for call in office.calls], ["open", "wait_for_close"])

    def test_adapter_failure_is_sanitized(self):
        class BrokenOffice(FakeOffice):
            def wait_for_close(self, handle):
                raise RuntimeError("sensitive engine detail")

        with self.assertRaises(OfficeCoordinationError) as caught:
            DocumentCoordinator(BrokenOffice()).run(
                session_id="local-session-3", request=sample_request()
            )
        self.assertEqual(str(caught.exception), "office_session_failed")
        self.assertIsInstance(caught.exception.__cause__, RuntimeError)

    def test_invalid_output_bytes_fail_closed(self):
        office = FakeOffice(output="not-bytes")
        with self.assertRaises(OfficeCoordinationError):
            DocumentCoordinator(office).run(
                session_id="local-session-4", request=sample_request()
            )


if __name__ == "__main__":
    unittest.main()
