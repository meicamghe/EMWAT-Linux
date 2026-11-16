import unittest

from emwat_linux.bridge import BridgeRequest, BridgeResponse
from emwat_linux.document_coordinator import DocumentRunResult
from emwat_linux.editword_handler import create_editword_handler
from emwat_linux.protocol import WORD_RESPONSE_CONTENT_TYPE, MethodCall, parse_method_call
from emwat_linux.sessions import DocumentSession, DocumentState


def request():
    return BridgeRequest(
        path="/",
        query="invoke=per-request-nonce",
        content_type="text/xml",
        origin="https://almas.example.test",
        body=b"<unused/>",
    )


def returned_result():
    session = DocumentSession("internal-session")
    session.begin_initialization()
    session.mark_opened()
    session.begin_finalize()
    session.complete_finalize(b"final-office-document")
    return DocumentRunResult(session=session, payload=b"final-office-document")


def cancelled_result():
    session = DocumentSession("internal-session-cancelled")
    session.begin_initialization()
    session.mark_opened()
    session.cancel()
    return DocumentRunResult(session=session, payload=None)


def discarded_result():
    session = DocumentSession("internal-session-discarded")
    session.begin_initialization()
    session.mark_opened()
    session.discard()
    return DocumentRunResult(session=session, payload=None)


class FakeService:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def process(self, call):
        self.calls.append(call)
        return self.result


class EditWordHandlerTests(unittest.TestCase):
    def test_success_uses_observed_response_word_serializer(self):
        service = FakeService(returned_result())
        handler = create_editword_handler(
            service,
            cancel_response_factory=lambda _result, _request: BridgeResponse(b"cancel"),
        )
        call = parse_method_call(
            b'<emwat version="1.0"><method class="EditWordDocument"/></emwat>'
        )
        response = handler(call, request())
        self.assertEqual(response.status, 200)
        self.assertEqual(response.content_type, WORD_RESPONSE_CONTENT_TYPE)
        self.assertIn(b"<response-word", response.body)
        self.assertIn(b"application/msword", response.body)
        self.assertEqual(len(service.calls), 1)

    def test_cancel_response_is_explicitly_injected(self):
        service = FakeService(cancelled_result())
        observed = []
        def cancel_factory(result, bridge_request):
            observed.append((result.session.state, bridge_request.query))
            return BridgeResponse(b"capture-specific-cancel", content_type="text/plain", status=409)

        handler = create_editword_handler(service, cancel_response_factory=cancel_factory)
        call = parse_method_call(
            b'<emwat version="1.0"><method class="EditWordDocument"/></emwat>'
        )
        response = handler(call, request())
        self.assertEqual(response.status, 409)
        self.assertEqual(response.body, b"capture-specific-cancel")
        self.assertEqual(observed, [(DocumentState.CANCELLED, "invoke=per-request-nonce")])

    def test_discard_uses_non_success_factory_without_becoming_cancelled(self):
        service = FakeService(discarded_result())
        observed = []

        def response_factory(result, bridge_request):
            observed.append((result.session.state, bridge_request.query))
            return BridgeResponse(b"capture-specific-non-success", status=409)

        handler = create_editword_handler(service, cancel_response_factory=response_factory)
        call = parse_method_call(
            b'<emwat version="1.0"><method class="EditWordDocument"/></emwat>'
        )
        response = handler(call, request())
        self.assertEqual(response.status, 409)
        self.assertEqual(response.body, b"capture-specific-non-success")
        self.assertEqual(observed, [(DocumentState.DISCARDED, "invoke=per-request-nonce")])

    def test_invalid_cancel_factory_response_is_rejected(self):
        service = FakeService(cancelled_result())
        handler = create_editword_handler(
            service,
            cancel_response_factory=lambda _result, _request: b"not-a-response",
        )
        call = parse_method_call(
            b'<emwat version="1.0"><method class="EditWordDocument"/></emwat>'
        )
        with self.assertRaises(TypeError):
            handler(call, request())


if __name__ == "__main__":
    unittest.main()
