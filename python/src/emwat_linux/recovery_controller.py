"""In-process controller boundary for a future native recovery picker.

This module deliberately contains no toolkit-specific widgets and no HTTP
routes. A desktop UI can bind its list/restore/discard actions to this
controller while keeping filesystem access inside RecoverySnapshotService.
"""
from __future__ import annotations

from pathlib import Path

from emwat_linux.recovery_service import RecoverySnapshot, RecoverySnapshotService


class RecoveryPickerController:
    """Expose safe picker actions and require explicit discard confirmation."""

    def __init__(self, service: RecoverySnapshotService) -> None:
        self._service = service

    def entries(self) -> tuple[RecoverySnapshot, ...]:
        """Return validated, newest-first metadata for display."""
        return self._service.list_snapshots()

    def restore(self, session_id: str, destination: str | Path) -> Path:
        """Restore the selected entry to a user-selected, non-existing path."""
        return self._service.restore(session_id, destination)

    def discard(self, session_id: str, *, confirmed: bool = False) -> None:
        """Delete only after the UI has obtained an explicit confirmation."""
        if confirmed is not True:
            raise PermissionError("recovery_discard_confirmation_required")
        self._service.discard(session_id)


__all__ = ["RecoveryPickerController"]
