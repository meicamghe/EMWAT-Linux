"""Application-facing recovery catalog and restore operations.

This module is the UI boundary for the native recovery store. It exposes
metadata only (never document bytes or absolute private-store paths) and
requires an explicit destination for restore.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

from emwat_linux.recovery_store import RecoverySnapshotStore


@dataclass(frozen=True)
class RecoverySnapshot:
    """Safe metadata suitable for a recovery picker or JSON response."""

    session_id: str
    document_name: str
    size_bytes: int
    sha256: str
    updated_at: float


class RecoverySnapshotService:
    """List, restore, and discard validated recovery snapshots."""

    def __init__(self, store: RecoverySnapshotStore) -> None:
        self._store = store

    def list_snapshots(self) -> tuple[RecoverySnapshot, ...]:
        """Return newest-first valid snapshots without leaking private paths."""
        return tuple(
            RecoverySnapshot(
                session_id=item.session_id,
                document_name=item.document_name,
                size_bytes=item.size_bytes,
                sha256=item.sha256,
                updated_at=item.updated_at,
            )
            for item in self._store.list_snapshots()
        )

    def catalog_json(self) -> str:
        """Serialize a versioned, metadata-only catalog for native UI clients.

        The schema is deliberately independent of the private store layout. No
        absolute paths, document contents, or mutable store objects are exposed.
        """
        payload = {
            "schema_version": 1,
            "snapshots": [asdict(item) for item in self.list_snapshots()],
        }
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    def restore(self, session_id: str, destination: str | Path) -> Path:
        """Restore one verified snapshot without overwriting an existing file."""
        return self._store.restore_snapshot(session_id, destination)

    def discard(self, session_id: str) -> None:
        """Discard one recovery session after explicit UI/user selection."""
        self._store.remove_session(session_id)


__all__ = ["RecoverySnapshot", "RecoverySnapshotService"]
