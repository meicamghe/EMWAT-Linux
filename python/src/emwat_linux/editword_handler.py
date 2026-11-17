"""HTTP-dispatch adapter for the EditWordDocument domain service.

Non-success response semantics are deliberately injected because the
captured successful response is known but the Windows discard/cancel envelopes
have not yet been recovered.
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
    max_response_bytes: int = 96 * 1024 * 1024,
) -> Callable[[MethodCall, BridgeRequest], BridgeResponse]:
    """Create a dispatcher handler with explicit discard/cancel response policy.

    The injected factory is called for both DISCARDED and CANCELLED sessions;
    their distinct DocumentState values let the caller choose a verified wire
    response without conflating "No" with "Cancel".
    """

    def handle(call: MethodCall, request: BridgeRequest) -> BridgeResponse:
        result = service.process(call)
        if result.payload is None:
            response = cancel_response_factory(result, request)
            if not isinstance(response, BridgeResponse):
                raise TypeError("cancel_response_factory_must_return_bridge_response")
            return response

        return BridgeResponse(
            body=serialize_word_document_response(
                result.payload, max_response_bytes=max_response_bytes
            ),
            content_type=WORD_RESPONSE_CONTENT_TYPE,
            status=200,
        )

    return handle
