import tempfile
import unittest
from pathlib import Path

from emwat_linux.recovery_retention import (
    RecoveryRetentionPolicy,
    apply_recovery_retention,
)
from emwat_linux.recovery_store import RecoverySnapshotStore
from emwat_linux.recovery_service import RecoverySnapshotService


DOC = bytes.fromhex("D0CF11E0A1B11AE1") + b"retention-fixture"


class RecoveryRetentionTests(unittest.TestCase):
    def test_requires_an_explicit_non_empty_policy(self):
        with self.assertRaises(ValueError):
            RecoveryRetentionPolicy()
        with self.assertRaises(ValueError):
            RecoveryRetentionPolicy(max_snapshots=0)
        with self.assertRaises(ValueError):
            RecoveryRetentionPolicy(max_age_seconds=float("inf"))

    def test_rejects_boolean_age_limit_and_non_numeric_age_limit(self):
        for value in (True, "3600"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                RecoveryRetentionPolicy(max_age_seconds=value)

    def test_rejects_boolean_and_non_numeric_current_time(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = RecoverySnapshotStore(Path(temporary) / "recovery")
            policy = RecoveryRetentionPolicy(max_snapshots=1)
            for value in (True, "1000"):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    apply_recovery_retention(store, policy, now=value)

    def test_count_limit_keeps_newest_and_reports_removed_ids(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = RecoverySnapshotStore(Path(temporary) / "recovery")
            sessions = []
            for _ in range(3):
                session = store.create_session()
                store.save_snapshot(session, DOC)
                sessions.append(session)

            # Make ordering deterministic without sleeping.
            infos = store.list_snapshots()
            expected_removed = infos[0].session_id
            expected_kept = {item.session_id for item in infos[1:]}
            for index, info in enumerate(infos):
                manifest = info.document_path.parent / "manifest.json"
                import json
                data = json.loads(manifest.read_text())
                data["updated_at"] = float(index + 1)
                manifest.write_text(json.dumps(data))

            removed = apply_recovery_retention(
                store, RecoveryRetentionPolicy(max_snapshots=2), now=10
            )

            self.assertEqual(removed, (expected_removed,))
            remaining = store.list_snapshots()
            self.assertEqual({item.session_id for item in remaining}, expected_kept)

    def test_count_limit_uses_session_id_as_stable_timestamp_tie_breaker(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = RecoverySnapshotStore(Path(temporary) / "recovery")
            sessions = []
            for _ in range(3):
                session = store.create_session()
                store.save_snapshot(session, DOC)
                sessions.append(session)

            import json
            for session in sessions:
                manifest = store.root / session / "manifest.json"
                data = json.loads(manifest.read_text())
                data["updated_at"] = 500.0
                manifest.write_text(json.dumps(data))

            keep = set(sorted(sessions, reverse=True)[:2])
            expected_removed = (sorted(sessions)[0],)
            removed = apply_recovery_retention(
                store, RecoveryRetentionPolicy(max_snapshots=2), now=1000
            )

            self.assertEqual(removed, expected_removed)
            self.assertEqual(
                {item.session_id for item in store.list_snapshots()}, keep
            )

    def test_age_limit_removes_only_expired_valid_snapshots(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = RecoverySnapshotStore(Path(temporary) / "recovery")
            old = store.create_session()
            fresh = store.create_session()
            store.save_snapshot(old, DOC)
            store.save_snapshot(fresh, DOC)

            import json
            old_manifest = store.root / old / "manifest.json"
            old_data = json.loads(old_manifest.read_text())
            old_data["updated_at"] = 100.0
            old_manifest.write_text(json.dumps(old_data))
            fresh_manifest = store.root / fresh / "manifest.json"
            fresh_data = json.loads(fresh_manifest.read_text())
            fresh_data["updated_at"] = 950.0
            fresh_manifest.write_text(json.dumps(fresh_data))

            removed = apply_recovery_retention(
                store, RecoveryRetentionPolicy(max_age_seconds=100), now=1000
            )

            self.assertEqual(removed, (old,))
            self.assertEqual(tuple(item.session_id for item in store.list_snapshots()), (fresh,))

    def test_service_exposes_retention_only_when_explicitly_called(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = RecoverySnapshotStore(Path(temporary) / "recovery")
            service = RecoverySnapshotService(store)
            session = store.create_session()
            store.save_snapshot(session, DOC)

            removed = service.apply_retention(
                RecoveryRetentionPolicy(max_snapshots=1), now=10**12
            )

            self.assertEqual(removed, ())
            self.assertEqual(len(service.list_snapshots()), 1)

    def test_no_op_when_policy_does_not_exceed_limits(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = RecoverySnapshotStore(Path(temporary) / "recovery")
            session = store.create_session()
            store.save_snapshot(session, DOC)
            self.assertEqual(
                apply_recovery_retention(
                    store, RecoveryRetentionPolicy(max_snapshots=1), now=10**12
                ),
                (),
            )
            self.assertEqual(len(store.list_snapshots()), 1)


if __name__ == "__main__":
    unittest.main()
