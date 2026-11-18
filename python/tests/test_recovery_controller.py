from pathlib import Path
import tempfile
import unittest

from emwat_linux.recovery_controller import RecoveryPickerController
from emwat_linux.recovery_service import RecoverySnapshotService
from emwat_linux.recovery_store import RecoverySnapshotStore


_CFB = bytes.fromhex("D0CF11E0A1B11AE1")


class RecoveryPickerControllerTests(unittest.TestCase):
    def test_entries_expose_only_service_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = RecoverySnapshotStore(Path(temporary) / "private")
            session = store.create_session()
            store.save_snapshot(session, _CFB + b"document")
            controller = RecoveryPickerController(RecoverySnapshotService(store))

            entries = controller.entries()

            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].session_id, session)
            self.assertFalse(hasattr(entries[0], "document_path"))

    def test_restore_uses_selected_destination_without_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = RecoverySnapshotStore(Path(temporary) / "private")
            session = store.create_session()
            payload = _CFB + b"document"
            store.save_snapshot(session, payload)
            destination = Path(temporary) / "restored.doc"
            controller = RecoveryPickerController(RecoverySnapshotService(store))

            self.assertEqual(controller.restore(session, destination), destination)
            self.assertEqual(destination.read_bytes(), payload)

    def test_discard_requires_explicit_confirmation(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = RecoverySnapshotStore(Path(temporary) / "private")
            session = store.create_session()
            store.save_snapshot(session, _CFB + b"document")
            controller = RecoveryPickerController(RecoverySnapshotService(store))

            for invalid_confirmation in (False, None, 1, "yes"):
                with self.subTest(confirmed=invalid_confirmation):
                    with self.assertRaisesRegex(
                        PermissionError, "recovery_discard_confirmation_required"
                    ):
                        controller.discard(
                            session, confirmed=invalid_confirmation
                        )
            self.assertEqual(len(controller.entries()), 1)

            controller.discard(session, confirmed=True)
            self.assertEqual(controller.entries(), ())


if __name__ == "__main__":
    unittest.main()
