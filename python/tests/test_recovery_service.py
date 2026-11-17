from pathlib import Path
import json
import tempfile
import unittest

from emwat_linux.recovery_service import RecoverySnapshotService
from emwat_linux.recovery_store import RecoverySnapshotStore, RecoveryStoreError


class RecoverySnapshotServiceTests(unittest.TestCase):
    def test_catalog_returns_safe_metadata_newest_first(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = RecoverySnapshotStore(Path(temporary) / "private" / "recovery")
            service = RecoverySnapshotService(store)
            older = store.create_session()
            newer = store.create_session()
            store.save_snapshot(
                older, bytes.fromhex("D0CF11E0A1B11AE1") + b"older"
            )
            store.save_snapshot(
                newer, bytes.fromhex("D0CF11E0A1B11AE1") + b"newer"
            )

            entries = service.list_snapshots()

            self.assertEqual({item.session_id for item in entries}, {older, newer})
            self.assertEqual(entries[0].session_id, newer)
            self.assertFalse(hasattr(entries[0], "document_path"))
            self.assertEqual(entries[0].size_bytes, len(
                bytes.fromhex("D0CF11E0A1B11AE1") + b"newer"
            ))

    def test_catalog_json_is_versioned_and_does_not_expose_store_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "private" / "recovery"
            store = RecoverySnapshotStore(root)
            service = RecoverySnapshotService(store)
            session_id = store.create_session()
            store.save_snapshot(
                session_id, bytes.fromhex("D0CF11E0A1B11AE1") + b"catalog"
            )

            payload = json.loads(service.catalog_json())

            self.assertEqual(payload["schema_version"], 1)
            self.assertEqual(len(payload["snapshots"]), 1)
            snapshot = payload["snapshots"][0]
            self.assertEqual(snapshot["session_id"], session_id)
            self.assertRegex(snapshot["document_name"], r"^document-[0-9a-f]{64}\\.doc$")
            self.assertNotIn("document_path", snapshot)
            self.assertNotIn(str(root), service.catalog_json())
            self.assertNotIn("content", snapshot)

    def test_restore_delegates_verified_no_overwrite_operation(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = RecoverySnapshotStore(Path(temporary) / "recovery")
            service = RecoverySnapshotService(store)
            session_id = store.create_session()
            payload = bytes.fromhex("D0CF11E0A1B11AE1") + b"recover"
            store.save_snapshot(session_id, payload)
            destination = Path(temporary) / "recovered.doc"

            self.assertEqual(service.restore(session_id, destination), destination)
            self.assertEqual(destination.read_bytes(), payload)
            with self.assertRaisesRegex(
                RecoveryStoreError, "recovery_restore_destination_exists"
            ):
                service.restore(session_id, destination)

    def test_discard_removes_selected_session_from_catalog(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = RecoverySnapshotStore(Path(temporary) / "recovery")
            service = RecoverySnapshotService(store)
            session_id = store.create_session()
            store.save_snapshot(
                session_id, bytes.fromhex("D0CF11E0A1B11AE1") + b"discard"
            )

            service.discard(session_id)

            self.assertEqual(service.list_snapshots(), ())


if __name__ == "__main__":
    unittest.main()
