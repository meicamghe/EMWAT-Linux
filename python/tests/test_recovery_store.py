import hashlib
import os
from pathlib import Path
import stat
import tempfile
import unittest

from emwat_linux.recovery_store import RecoverySnapshotStore, RecoveryStoreError


class RecoverySnapshotStoreTests(unittest.TestCase):
    def test_snapshot_is_atomic_private_and_verifiable(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "recovery"
            store = RecoverySnapshotStore(root)
            session_id = store.create_session()
            payload = bytes.fromhex("D0CF11E0A1B11AE1") + b"legacy-word-document"

            info = store.save_snapshot(session_id, payload)

            self.assertTrue(info.document_name.startswith("document-"))
            self.assertTrue(info.document_name.endswith(".doc"))
            self.assertEqual(info.size_bytes, len(payload))
            self.assertEqual(info.sha256, hashlib.sha256(payload).hexdigest())
            self.assertEqual(store.load_snapshot(session_id), payload)
            self.assertEqual(len(store.list_snapshots()), 1)
            self.assertEqual(stat.S_IMODE((root / session_id).stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(info.document_path.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE((root / session_id / "manifest.json").stat().st_mode), 0o600)

            store.remove_session(session_id)
            self.assertEqual(store.list_snapshots(), ())

    def test_docx_container_is_recognized(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = RecoverySnapshotStore(Path(temporary) / "recovery")
            session_id = store.create_session()
            payload = b"PK\x03\x04" + b"synthetic-docx"
            info = store.save_snapshot(session_id, payload)
            self.assertTrue(info.document_name.startswith("document-"))
            self.assertTrue(info.document_name.endswith(".docx"))
            self.assertEqual(store.load_snapshot(session_id), payload)

    def test_manifest_switch_keeps_previous_snapshot_if_update_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = RecoverySnapshotStore(Path(temporary) / "recovery")
            session_id = store.create_session()
            first = bytes.fromhex("D0CF11E0A1B11AE1") + b"first-document"
            second = bytes.fromhex("D0CF11E0A1B11AE1") + b"second-document"
            store.save_snapshot(session_id, first)

            atomic_write = store._atomic_write

            def fail_manifest(destination, payload):
                if destination.name == "manifest.json":
                    raise OSError("simulated_manifest_commit_failure")
                atomic_write(destination, payload)

            store._atomic_write = fail_manifest
            with self.assertRaisesRegex(OSError, "simulated_manifest_commit_failure"):
                store.save_snapshot(session_id, second)
            store._atomic_write = atomic_write

            self.assertEqual(store.load_snapshot(session_id), first)

            store.save_snapshot(session_id, second)
            document_files = tuple((Path(temporary) / "recovery" / session_id).glob("document-*"))
            self.assertEqual(len(document_files), 1)
            self.assertEqual(store.load_snapshot(session_id), second)

    def test_corrupted_snapshot_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = RecoverySnapshotStore(Path(temporary) / "recovery")
            session_id = store.create_session()
            info = store.save_snapshot(
                session_id,
                bytes.fromhex("D0CF11E0A1B11AE1") + b"document",
            )
            info.document_path.write_bytes(b"tampered")
            with self.assertRaisesRegex(RecoveryStoreError, "recovery_snapshot_size_mismatch"):
                store.load_snapshot(session_id)

    def test_invalid_session_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = RecoverySnapshotStore(Path(temporary) / "recovery")
            with self.assertRaisesRegex(RecoveryStoreError, "recovery_session_id_invalid"):
                store.load_snapshot("../outside")


if __name__ == "__main__":
    unittest.main()
