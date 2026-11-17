"""Private, crash-survivable recovery snapshots for active EMWAT documents.

This is a Linux-native recovery format. It deliberately does not claim
compatibility with the Windows password-protected .easz archive.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import time
import uuid


_SESSION_ID = re.compile(r"^[0-9a-f]{32}$")
_CFB_SIGNATURE = bytes.fromhex("D0CF11E0A1B11AE1")
_ZIP_SIGNATURES = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")


class RecoveryStoreError(RuntimeError):
    """Raised when a recovery snapshot cannot be safely stored or verified."""


@dataclass(frozen=True)
class RecoverySnapshotInfo:
    session_id: str
    document_name: str
    size_bytes: int
    sha256: str
    updated_at: float
    document_path: Path


class RecoverySnapshotStore:
    """Owner-only atomic snapshots under XDG_STATE_HOME or ~/.local/state."""

    def __init__(
        self,
        root: str | Path | None = None,
        *,
        max_snapshot_bytes: int = 128 * 1024 * 1024,
    ) -> None:
        if max_snapshot_bytes <= 0:
            raise ValueError("max_snapshot_bytes must be positive")
        self.max_snapshot_bytes = max_snapshot_bytes
        if root is None:
            state_home = os.environ.get("XDG_STATE_HOME")
            base = Path(state_home).expanduser() if state_home else Path.home() / ".local" / "state"
            root = base / "emwat-linux" / "recovery"
        self.root = Path(root).expanduser()

    def create_session(self) -> str:
        self._ensure_root()
        session_id = uuid.uuid4().hex
        folder = self._session_dir(session_id)
        folder.mkdir(mode=0o700)
        folder.chmod(0o700)
        self._fsync_directory(self.root)
        return session_id

    def save_snapshot(self, session_id: str, payload: bytes) -> RecoverySnapshotInfo:
        if not isinstance(payload, bytes) or not payload:
            raise RecoveryStoreError("recovery_snapshot_empty_or_invalid")
        if len(payload) > self.max_snapshot_bytes:
            raise RecoveryStoreError("recovery_snapshot_too_large")
        folder = self._session_dir(session_id)
        if folder.is_symlink() or not folder.is_dir():
            raise RecoveryStoreError("recovery_session_missing")
        folder.chmod(0o700)

        if payload.startswith(_CFB_SIGNATURE):
            document_name = "document.doc"
        elif payload.startswith(_ZIP_SIGNATURES):
            document_name = "document.docx"
        else:
            raise RecoveryStoreError("recovery_document_format_unsupported")

        digest = hashlib.sha256(payload).hexdigest()
        updated_at = time.time()
        suffix = ".doc" if document_name == "document.doc" else ".docx"
        document_name = f"document-{digest}{suffix}"
        document_path = folder / document_name
        manifest_path = folder / "manifest.json"

        # Write a new immutable snapshot first, then atomically switch the manifest.
        # A crash between these steps leaves the previous manifest/document usable.
        self._atomic_write(document_path, payload)
        manifest = {
            "schema_version": 1,
            "session_id": session_id,
            "document_name": document_name,
            "size_bytes": len(payload),
            "sha256": digest,
            "updated_at": updated_at,
        }
        self._atomic_write(
            manifest_path,
            (json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"),
        )
        for candidate in folder.iterdir():
            if (
                candidate.is_file()
                and candidate.name != document_name
                and re.fullmatch(r"document-[0-9a-f]{64}\.(?:doc|docx)", candidate.name)
            ):
                try:
                    candidate.unlink()
                except FileNotFoundError:
                    pass
        self._fsync_directory(folder)
        return RecoverySnapshotInfo(
            session_id=session_id,
            document_name=document_name,
            size_bytes=len(payload),
            sha256=digest,
            updated_at=updated_at,
            document_path=document_path,
        )

    def load_snapshot(self, session_id: str) -> bytes:
        folder = self._session_dir(session_id)
        try:
            if folder.is_symlink() or not folder.is_dir():
                raise RecoveryStoreError("recovery_session_missing")
            manifest_path = folder / "manifest.json"
            if manifest_path.is_symlink() or not manifest_path.is_file():
                raise RecoveryStoreError("recovery_snapshot_unavailable")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("schema_version") != 1 or manifest.get("session_id") != session_id:
                raise RecoveryStoreError("recovery_manifest_identity_invalid")
            document_name = manifest["document_name"]
            if not re.fullmatch(r"document-[0-9a-f]{64}\.(?:doc|docx)", document_name):
                raise RecoveryStoreError("recovery_manifest_document_name_invalid")
            document_path = folder / document_name
            if document_path.is_symlink() or not document_path.is_file():
                raise RecoveryStoreError("recovery_snapshot_unavailable")
            if document_path.stat().st_size > self.max_snapshot_bytes:
                raise RecoveryStoreError("recovery_snapshot_too_large")
            payload = document_path.read_bytes()
            if type(manifest["size_bytes"]) is not int or len(payload) != manifest["size_bytes"]:
                raise RecoveryStoreError("recovery_snapshot_size_mismatch")
            if not isinstance(manifest["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", manifest["sha256"]):
                raise RecoveryStoreError("recovery_manifest_hash_invalid")
            if hashlib.sha256(payload).hexdigest() != manifest["sha256"]:
                raise RecoveryStoreError("recovery_snapshot_hash_mismatch")
            if payload.startswith(_CFB_SIGNATURE) and not document_name.endswith(".doc"):
                raise RecoveryStoreError("recovery_snapshot_format_mismatch")
            if payload.startswith(_ZIP_SIGNATURES) and not document_name.endswith(".docx"):
                raise RecoveryStoreError("recovery_snapshot_format_mismatch")
            return payload
        except RecoveryStoreError:
            raise
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise RecoveryStoreError("recovery_snapshot_unavailable") from exc

    def list_snapshots(self) -> tuple[RecoverySnapshotInfo, ...]:
        # Never follow a replaced/symlinked state directory while enumerating
        # snapshots. A symlink here could otherwise expose another directory.
        if self.root.is_symlink() or not self.root.is_dir():
            return ()
        snapshots = []
        for folder in self.root.iterdir():
            if folder.is_symlink() or not folder.is_dir() or not _SESSION_ID.fullmatch(folder.name):
                continue
            try:
                manifest_path = folder / "manifest.json"
                if manifest_path.is_symlink() or not manifest_path.is_file():
                    continue
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                if manifest.get("schema_version") != 1 or manifest.get("session_id") != folder.name:
                    continue
                name = manifest["document_name"]
                if not isinstance(name, str) or not re.fullmatch(r"document-[0-9a-f]{64}\.(?:doc|docx)", name):
                    continue
                path = folder / name
                if path.is_symlink() or not path.is_file():
                    continue
                payload = self.load_snapshot(folder.name)
                snapshots.append(
                    RecoverySnapshotInfo(
                        session_id=folder.name,
                        document_name=name,
                        size_bytes=len(payload),
                        sha256=hashlib.sha256(payload).hexdigest(),
                        updated_at=float(manifest["updated_at"]),
                        document_path=path,
                    )
                )
            except (OSError, ValueError, KeyError, TypeError, RecoveryStoreError):
                continue
        return tuple(sorted(snapshots, key=lambda item: item.updated_at, reverse=True))

    def has_snapshot(self, session_id: str) -> bool:
        try:
            self.load_snapshot(session_id)
            return True
        except RecoveryStoreError:
            return False

    def restore_snapshot(self, session_id: str, destination: str | Path) -> Path:
        """Atomically restore a verified snapshot without overwriting an existing file."""
        payload = self.load_snapshot(session_id)
        destination_path = Path(destination).expanduser()
        expected_suffix = ".doc" if payload.startswith(_CFB_SIGNATURE) else ".docx"
        if destination_path.suffix.lower() != expected_suffix:
            raise RecoveryStoreError("recovery_restore_extension_mismatch")
        parent = destination_path.parent
        if not parent.is_dir():
            raise RecoveryStoreError("recovery_restore_directory_missing")
        descriptor, temporary_name = tempfile.mkstemp(prefix=".emwat-restore-", dir=parent)
        temporary = Path(temporary_name)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            # A hard link publishes the complete file and fails rather than
            # replacing an existing destination or following a destination symlink.
            os.link(temporary, destination_path)
            self._fsync_directory(parent)
            return destination_path
        except FileExistsError as exc:
            raise RecoveryStoreError("recovery_restore_destination_exists") from exc
        except OSError as exc:
            raise RecoveryStoreError("recovery_restore_failed") from exc
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass

    def remove_session(self, session_id: str) -> None:
        folder = self._session_dir(session_id)
        if folder.is_symlink():
            raise RecoveryStoreError("recovery_session_symlink_rejected")
        if folder.exists():
            if not folder.is_dir():
                raise RecoveryStoreError("recovery_session_not_directory")
            shutil.rmtree(folder)
            if self.root.exists():
                self._fsync_directory(self.root)

    def _ensure_root(self) -> None:
        # XDG state is private application data. Refuse a symlink or a
        # non-directory at the trust boundary instead of chmod/mkdir-following it.
        if self.root.is_symlink():
            raise RecoveryStoreError("recovery_root_symlink_rejected")
        if self.root.exists() and not self.root.is_dir():
            raise RecoveryStoreError("recovery_root_not_directory")
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.root.is_symlink():
            raise RecoveryStoreError("recovery_root_symlink_rejected")
        self.root.chmod(0o700)

    def _session_dir(self, session_id: str) -> Path:
        if not isinstance(session_id, str) or not _SESSION_ID.fullmatch(session_id):
            raise RecoveryStoreError("recovery_session_id_invalid")
        if self.root.is_symlink():
            raise RecoveryStoreError("recovery_root_symlink_rejected")
        return self.root / session_id

    @staticmethod
    def _atomic_write(destination: Path, payload: bytes) -> None:
        fd, temporary_name = tempfile.mkstemp(prefix=".emwat-recovery-", dir=destination.parent)
        temporary = Path(temporary_name)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, destination)
            RecoverySnapshotStore._fsync_directory(destination.parent)
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass

    @staticmethod
    def _fsync_directory(directory: Path) -> None:
        flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        descriptor = os.open(directory, flags)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


__all__ = ["RecoverySnapshotInfo", "RecoverySnapshotStore", "RecoveryStoreError"]
