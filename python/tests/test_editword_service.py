import base64
import unittest

from emwat_linux.editword_service import EditWordDocumentService
from emwat_linux.office_adapter import CloseDisposition, OfficeCloseEvent
from emwat_linux.protocol import parse_method_call
from emwat_linux.sessions import DocumentState


def make_call():
    config = base64.b64encode(b"<word-document/>").decode("ascii")
    body = base64.b64encode(b"synthetic-input-doc").decode("ascii")
    xml = (
        '<emwat version="1.0"><method class="EditWordDocument">'
        f'<param name="wordConfig">{config}</param>'
        f'<param name="wordBody">{body}</param>'
        '<param name="signData"></param>'
        '</method></emwat>'
    )
    return parse_method_call(xml.encode("utf-8"))


class FakeOffice:
    def __init__(self, disposition=CloseDisposition.CLOSED):
        self.disposition = disposition
        self.opened_bytes = None
        self.export_count = 0

    def open_document(self, request):
        self.opened_bytes = request.document_bytes
        return object()

    def wait_for_close(self, handle):
        return OfficeCloseEvent(self.disposition)

    def export_final_document(self, handle):
        self.export_count += 1
        return b"synthetic-final-doc"


class EditWordDocumentServiceTests(unittest.TestCase):
    def test_processes_request_through_close_and_returns_final_bytes(self):
        office = FakeOffice()
        service = EditWordDocumentService(
            office, session_id_factory=lambda: "internal-session-id"
        )
        result = service.process(make_call())
        self.assertEqual(office.opened_bytes, b"synthetic-input-doc")
        self.assertEqual(result.session.session_id, "internal-session-id")
        self.assertEqual(result.session.state, DocumentState.RETURNED)
        self.assertEqual(result.payload, b"synthetic-final-doc")
        self.assertEqual(office.export_count, 1)

    def test_cancelled_session_has_no_success_payload(self):
        office = FakeOffice(CloseDisposition.CANCELLED)
        service = EditWordDocumentService(
            office, session_id_factory=lambda: "cancelled-session"
        )
        result = service.process(make_call())
        self.assertEqual(result.session.state, DocumentState.CANCELLED)
        self.assertIsNone(result.payload)
        self.assertEqual(office.export_count, 0)

    def test_invalid_method_is_rejected_before_opening_office(self):
        office = FakeOffice()
        service = EditWordDocumentService(office)
        call = parse_method_call(
            b'<emwat version="1.0"><method class="Other">'
            b'<param name="wordConfig">x</param>'
            b'<param name="wordBody">eA==</param>'
            b'</method></emwat>'
        )
        with self.assertRaises(ValueError):
            service.process(call)
        self.assertIsNone(office.opened_bytes)


if __name__ == "__main__":
    unittest.main()
