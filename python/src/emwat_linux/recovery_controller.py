"""In-process controller boundary for a future native recovery picker.

This module deliberately contains no toolkit-specific widgets and no HTTP
routes. A desktop UI can bind its list/restore/discard actions to this
controller while keeping filesystem access inside RecoverySnapshotService.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from emwat_linux.recovery_service import RecoverySnapshot, RecoverySnapshotService


@dataclass(frozen=True)
class RecoveryPickerState:
    """Immutable, toolkit-neutral projection for a recovery picker view."""

    entries: tuple[RecoverySnapshot, ...]
    selected_session_id: str | None

    @property
    def selected_entry(self) -> RecoverySnapshot | None:
        """Return the selected metadata row, if the selection is still valid."""
        return next(
            (
                entry
                for entry in self.entries
                if entry.session_id == self.selected_session_id
            ),
            None,
        )

    @property
    def is_empty(self) -> bool:
        """Whether the picker should show its empty-recovery state."""
        return not self.entries


class RecoveryPickerController:
    """Expose safe picker actions and require explicit discard confirmation."""

    def __init__(self, service: RecoverySnapshotService) -> None:
        self._service = service

    def entries(self) -> tuple[RecoverySnapshot, ...]:
        """Return validated, newest-first metadata for display."""
        return self._service.list_snapshots()

    def state(
        self, selected_session_id: str | None = None
    ) -> RecoveryPickerState:
        """Build a stable view projection without exposing store paths.

        With no requested selection, the newest entry is selected. A stale or
        unknown selection is cleared instead of silently selecting another
        document. An empty catalog produces a state suitable for an empty view.
        """
        entries = self.entries()
        if selected_session_id is None:
            selected = entries[0].session_id if entries else None
        else:
            selected = next(
                (
                    entry.session_id
                    for entry in entries
                    if entry.session_id == selected_session_id
                ),
                None,
            )
        return RecoveryPickerState(entries, selected)

    def restore(self, session_id: str, destination: str | Path) -> Path:
        """Restore the selected entry to a user-selected, non-existing path."""
        return self._service.restore(session_id, destination)

    def discard(self, session_id: str, *, confirmed: bool = False) -> None:
        """Delete only after the UI has obtained an explicit confirmation."""
        if confirmed is not True:
            raise PermissionError("recovery_discard_confirmation_required")
        self._service.discard(session_id)


__all__ = ["RecoveryPickerController", "RecoveryPickerState"]
