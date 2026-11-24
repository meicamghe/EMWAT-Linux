"""Domain service joining EditWordDocument parsing to office lifecycle control.

HTTP response policy is intentionally left to the bridge/application layer:
the captured success response is known, but cancellation/error response
semantics are not yet fully recovered.
"""
from __future__ import annotations

import secrets
from collections.abc import Callable

from emwat_linux.document_coordinator import DocumentCoordinator, DocumentRunResult
from emwat_linux.editword_request import parse_editword_request
from emwat_linux.office_adapter import OfficeAdapter
from emwat_linux.protocol import MethodCall


class EditWordDocumentService:
    """Normalize a captured method call and run one close-driven office session."""

    def __init__(
        self,
        office: OfficeAdapter,
        *,
        session_id_factory: Callable[[], str] | None = None,
        max_document_bytes: int = 64 * 1024 * 1024,
        max_encoded_document_chars: int = 90 * 1024 * 1024,
        max_config_bytes: int = 16 * 1024 * 1024,
        max_encoded_config_chars: int = 24 * 1024 * 1024,
    ) -> None:
        limits = {
            "max_document_bytes": max_document_bytes,
            "max_encoded_document_chars": max_encoded_document_chars,
            "max_config_bytes": max_config_bytes,
            "max_encoded_config_chars": max_encoded_config_chars,
        }
        for name, value in limits.items():
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        self._coordinator = DocumentCoordinator(office)
        self._session_id_factory = session_id_factory or (lambda: secrets.token_urlsafe(24))
        self._request_limits = limits

    def process(self, call: MethodCall) -> DocumentRunResult:
        """Process one EditWordDocument call; never reuse its HTTP invoke nonce."""
        request = parse_editword_request(call, **self._request_limits)
        session_id = self._session_id_factory()
        return self._coordinator.run(session_id=session_id, request=request)
