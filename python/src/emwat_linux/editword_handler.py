"""HTTP-dispatch adapter for the EditWordDocument domain service.

Non-success response semantics for explicit terminal discard/cancellation are
deliberately injected because the Windows envelopes have not been recovered.
The office UI's close-dialog Cancel is not a terminal cancellation: it keeps
the same invoke pending and does not reach this response factory.
"""
from __future__ import annotations

from collections.abc import Callable

from emwat_linux.bridge import BridgeRequest, BridgeResponse
from emwat_linux.document_coordinator import DocumentRunResult
from emwat_linux.editword_service import EditWordDocumentService
from emwat_linux.protocol import (
    WORD_RESPONSE_CONTENT_TYPE,
    MethodCall,
    serialize_word_document_response,
)


CancelResponseFactory = Callable[[DocumentRunResult, BridgeRequest], BridgeResponse]


def create_editword_handler(
    service: EditWordDocumentService,
    *,
    cancel_response_factory: CancelResponseFactory,
) -> Callable[[MethodCall, BridgeRequest], BridgeResponse]:
    """Create a handler with explicit terminal discard/cancel response policy.

    This factory handles terminal application outcomes only. A Cancel in the
    office close dialog leaves wait_for_close pending and produces no response
    until the user later chooses Save or Don't Save.
    """

    def handle(call: MethodCall, request: BridgeRequest) -> BridgeResponse:
        result = service.process(call)
        if result.payload is None:
            response = cancel_response_factory(result, request)
            if not isinstance(response, BridgeResponse):
                raise TypeError("cancel_response_factory_must_return_bridge_response")
            return response

        return BridgeResponse(
            body=serialize_word_document_response(result.payload),
            content_type=WORD_RESPONSE_CONTENT_TYPE,
            status=200,
        )

    return handle
