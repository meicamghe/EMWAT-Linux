from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from emwat_linux.recovery_controller import RecoveryPickerController
from emwat_linux.recovery_service import RecoverySnapshot, RecoverySnapshotService
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

    def test_state_defaults_to_newest_entry_and_exposes_selected_metadata(self):
        newest = RecoverySnapshot("newest", "new.doc", 10, "a" * 64, 20.0)
        older = RecoverySnapshot("older", "old.doc", 8, "b" * 64, 10.0)
        service = Mock()
        service.list_snapshots.return_value = (newest, older)

        state = RecoveryPickerController(service).state()

        self.assertEqual(state.entries, (newest, older))
        self.assertEqual(state.selected_session_id, "newest")
        self.assertEqual(state.selected_entry, newest)
        self.assertFalse(state.is_empty)

    def test_state_preserves_valid_selection_and_clears_stale_selection(self):
        entry = RecoverySnapshot("session", "doc.doc", 10, "a" * 64, 20.0)
        service = Mock()
        service.list_snapshots.return_value = (entry,)
        controller = RecoveryPickerController(service)

        self.assertEqual(controller.state("session").selected_entry, entry)
        stale = controller.state("no-longer-present")
        self.assertIsNone(stale.selected_session_id)
        self.assertIsNone(stale.selected_entry)

    def test_state_represents_empty_catalog_without_selection(self):
        service = Mock()
        service.list_snapshots.return_value = ()

        state = RecoveryPickerController(service).state()

        self.assertTrue(state.is_empty)
        self.assertEqual(state.entries, ())
        self.assertIsNone(state.selected_session_id)
        self.assertIsNone(state.selected_entry)

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
