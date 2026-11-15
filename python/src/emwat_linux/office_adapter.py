"""Office-engine boundary for close-driven document sessions.

This module deliberately contains no LibreOffice UNO or Windows COM calls.
The adapter contract keeps engine lifecycle details out of the HTTP transport.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from emwat_linux.editword_request import EditWordDocumentRequest


class CloseDisposition(str, Enum):
    CLOSED = "closed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class OfficeCloseEvent:
    """Normalized close result emitted by an office-engine adapter."""

    disposition: CloseDisposition


class OfficeAdapter(Protocol):
    """Minimal synchronous contract for a user-edited office document.

    wait_for_close is intentionally unbounded by default: the captured Windows
    exchange keeps its HTTP request open while the document is being edited.
    The adapter reports modification and engine-save events separately.
    """

    def open_document(
        self,
        request: EditWordDocumentRequest,
        *,
        on_modified: Callable[[], int],
        on_saved: Callable[[], None],
    ) -> object:
        """Open the supplied document and apply supported config fields."""

    def wait_for_close(self, handle: object) -> OfficeCloseEvent:
        """Wait until the user closes or cancels the editing session."""

    def export_final_document(self, handle: object) -> bytes:
        """Return final document bytes after close, including unsaved edits."""
