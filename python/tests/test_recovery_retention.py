import tempfile
import unittest
from pathlib import Path

from emwat_linux.recovery_retention import (
    RecoveryRetentionPolicy,
    apply_recovery_retention,
)
from emwat_linux.recovery_store import RecoverySnapshotStore


DOC = bytes.fromhex("D0CF11E0A1B11AE1") + b"retention-fixture"


class RecoveryRetentionTests(unittest.TestCase):
    def test_requires_an_explicit_non_empty_policy(self):
        with self.assertRaises(ValueError):
            RecoveryRetentionPolicy()
        with self.assertRaises(ValueError):
            RecoveryRetentionPolicy(max_snapshots=0)
        with self.assertRaises(ValueError):
            RecoveryRetentionPolicy(max_age_seconds=float("inf"))

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
            for index, info in enumerate(infos):
                manifest = info.document_path.parent / "manifest.json"
                import json
                data = json.loads(manifest.read_text())
                data["updated_at"] = float(index + 1)
                manifest.write_text(json.dumps(data))

            removed = apply_recovery_retention(
                store, RecoveryRetentionPolicy(max_snapshots=2), now=10
            )

            self.assertEqual(len(removed), 1)
            remaining = store.list_snapshots()
            self.assertEqual(len(remaining), 2)
            self.assertNotIn(removed[0], {item.session_id for item in remaining})

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
