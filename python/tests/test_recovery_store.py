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

    def test_snapshot_size_limit_is_enforced(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = RecoverySnapshotStore(Path(temporary) / "recovery", max_snapshot_bytes=16)
            session_id = store.create_session()
            payload = bytes.fromhex("D0CF11E0A1B11AE1") + b"oversized"
            with self.assertRaisesRegex(RecoveryStoreError, "recovery_snapshot_too_large"):
                store.save_snapshot(session_id, payload)
            self.assertFalse(store.has_snapshot(session_id))

    def test_non_object_manifests_fail_closed_without_crashing_catalog(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = RecoverySnapshotStore(Path(temporary) / "recovery")
            for malformed in ("[]", "null", '"not-a-manifest"'):
                session_id = store.create_session()
                info = store.save_snapshot(
                    session_id,
                    bytes.fromhex("D0CF11E0A1B11AE1") + b"manifest-shape",
                )
                (info.document_path.parent / "manifest.json").write_text(
                    malformed, encoding="utf-8"
                )
                with self.subTest(manifest=malformed):
                    with self.assertRaisesRegex(
                        RecoveryStoreError, "recovery_manifest_invalid"
                    ):
                        store.load_snapshot(session_id)
                    self.assertNotIn(
                        session_id, {item.session_id for item in store.list_snapshots()}
                    )

    def test_corrupt_snapshot_is_not_listed_or_reported_as_available(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = RecoverySnapshotStore(Path(temporary) / "recovery")
            session_id = store.create_session()
            info = store.save_snapshot(
                session_id,
                bytes.fromhex("D0CF11E0A1B11AE1") + b"document",
            )
            info.document_path.write_bytes(b"tampered")
            self.assertFalse(store.has_snapshot(session_id))
            self.assertEqual(store.list_snapshots(), ())

    def test_snapshot_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "recovery"
            store = RecoverySnapshotStore(root)
            session_id = store.create_session()
            outside = Path(temporary) / "outside.doc"
            outside.write_bytes(bytes.fromhex("D0CF11E0A1B11AE1") + b"outside")
            info = store.save_snapshot(session_id, outside.read_bytes())
            info.document_path.unlink()
            info.document_path.symlink_to(outside)
            with self.assertRaisesRegex(RecoveryStoreError, "recovery_snapshot_unavailable"):
                store.load_snapshot(session_id)

    def test_restore_writes_verified_snapshot_atomically_without_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "recovery"
            store = RecoverySnapshotStore(root)
            session_id = store.create_session()
            payload = bytes.fromhex("D0CF11E0A1B11AE1") + b"recover-me"
            store.save_snapshot(session_id, payload)
            destination = Path(temporary) / "restored.doc"

            restored = store.restore_snapshot(session_id, destination)

            self.assertEqual(restored, destination)
            self.assertEqual(destination.read_bytes(), payload)
            self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o600)
            with self.assertRaisesRegex(RecoveryStoreError, "recovery_restore_destination_exists"):
                store.restore_snapshot(session_id, destination)
            self.assertEqual(destination.read_bytes(), payload)

    def test_restore_rejects_wrong_extension(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = RecoverySnapshotStore(Path(temporary) / "recovery")
            session_id = store.create_session()
            store.save_snapshot(session_id, bytes.fromhex("D0CF11E0A1B11AE1") + b"doc")
            with self.assertRaisesRegex(RecoveryStoreError, "recovery_restore_extension_mismatch"):
                store.restore_snapshot(session_id, Path(temporary) / "restored.docx")

    def test_symlinked_recovery_root_is_rejected_and_not_enumerated(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            outside = base / "outside"
            outside.mkdir()
            store = RecoverySnapshotStore(outside)
            session_id = store.create_session()
            store.save_snapshot(
                session_id,
                bytes.fromhex("D0CF11E0A1B11AE1") + b"outside-document",
            )

            link = base / "recovery-link"
            link.symlink_to(outside, target_is_directory=True)
            linked_store = RecoverySnapshotStore(link)

            self.assertEqual(linked_store.list_snapshots(), ())
            with self.assertRaisesRegex(
                RecoveryStoreError, "recovery_root_symlink_rejected"
            ):
                linked_store.create_session()
            with self.assertRaisesRegex(
                RecoveryStoreError, "recovery_root_symlink_rejected"
            ):
                linked_store.load_snapshot(session_id)

    def test_remove_session_rejects_symlink_without_touching_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "recovery"
            store = RecoverySnapshotStore(root)
            session_id = store.create_session()
            outside = base / "outside"
            outside.mkdir()
            (outside / "keep.txt").write_text("keep", encoding="utf-8")
            (root / session_id).rmdir()
            (root / session_id).symlink_to(outside, target_is_directory=True)

            with self.assertRaisesRegex(
                RecoveryStoreError, "recovery_session_symlink_rejected"
            ):
                store.remove_session(session_id)

            self.assertEqual((outside / "keep.txt").read_text(encoding="utf-8"), "keep")

    def test_invalid_session_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = RecoverySnapshotStore(Path(temporary) / "recovery")
            with self.assertRaisesRegex(RecoveryStoreError, "recovery_session_id_invalid"):
                store.load_snapshot("../outside")

    def test_manifest_rejects_non_finite_or_non_numeric_timestamp(self):
        import json
        with tempfile.TemporaryDirectory() as temporary:
            store = RecoverySnapshotStore(Path(temporary) / "recovery")
            session_id = store.create_session()
            info = store.save_snapshot(
                session_id, bytes.fromhex("D0CF11E0A1B11AE1") + b"timestamp"
            )
            manifest = info.document_path.parent / "manifest.json"
            data = json.loads(manifest.read_text(encoding="utf-8"))
            data["updated_at"] = "nan"
            manifest.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(
                RecoveryStoreError, "recovery_manifest_timestamp_invalid"
            ):
                store.load_snapshot(session_id)
            self.assertEqual(store.list_snapshots(), ())

    def test_manifest_rejects_document_name_not_bound_to_content_hash(self):
        import json
        import shutil
        with tempfile.TemporaryDirectory() as temporary:
            store = RecoverySnapshotStore(Path(temporary) / "recovery")
            session_id = store.create_session()
            info = store.save_snapshot(
                session_id, bytes.fromhex("D0CF11E0A1B11AE1") + b"hash-bound"
            )
            manifest = info.document_path.parent / "manifest.json"
            data = json.loads(manifest.read_text(encoding="utf-8"))
            substituted_name = "document-" + ("0" * 64) + ".doc"
            shutil.copyfile(info.document_path, info.document_path.parent / substituted_name)
            data["document_name"] = substituted_name
            manifest.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(
                RecoveryStoreError, "recovery_snapshot_name_hash_mismatch"
            ):
                store.load_snapshot(session_id)
            self.assertEqual(store.list_snapshots(), ())


    def test_aes_gcm_encryption_hides_plaintext_and_roundtrips(self):
        key = b"K" * 32
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "recovery"
            store = RecoverySnapshotStore(root, encryption_key=key)
            session_id = store.create_session()
            payload = bytes.fromhex("D0CF11E0A1B11AE1") + b"secret-document-content"
            info = store.save_snapshot(session_id, payload)
            stored = info.document_path.read_bytes()
            self.assertTrue(stored.startswith(b"EMWATREC\x01"))
            self.assertNotIn(hashlib.sha256(payload).hexdigest(), info.document_name)
            self.assertNotIn(b"secret-document-content", stored)
            self.assertEqual(store.load_snapshot(session_id), payload)
            self.assertEqual(store.list_snapshots()[0].sha256, hashlib.sha256(payload).hexdigest())

    def test_encrypted_snapshot_requires_correct_key_and_authenticates(self):
        key = b"A" * 32
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "recovery"
            store = RecoverySnapshotStore(root, encryption_key=key)
            session_id = store.create_session()
            payload = bytes.fromhex("D0CF11E0A1B11AE1") + b"authenticated"
            info = store.save_snapshot(session_id, payload)
            without_key = RecoverySnapshotStore(root)
            with self.assertRaisesRegex(RecoveryStoreError, "recovery_encryption_key_required"):
                without_key.load_snapshot(session_id)
            wrong_key = RecoverySnapshotStore(root, encryption_key=b"B" * 32)
            with self.assertRaisesRegex(RecoveryStoreError, "recovery_snapshot_authentication_failed"):
                wrong_key.load_snapshot(session_id)
            damaged = bytearray(info.document_path.read_bytes())
            damaged[-1] ^= 1
            info.document_path.write_bytes(damaged)
            with self.assertRaisesRegex(RecoveryStoreError, "recovery_snapshot_authentication_failed"):
                store.load_snapshot(session_id)

    def test_encrypted_envelope_nonce_must_match_manifest_nonce(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = RecoverySnapshotStore(
                Path(temporary) / "recovery", encryption_key=b"N" * 32
            )
            session_id = store.create_session()
            info = store.save_snapshot(
                session_id, bytes.fromhex("D0CF11E0A1B11AE1") + b"nonce-binding"
            )
            envelope = bytearray(info.document_path.read_bytes())
            nonce_offset = len(b"EMWATREC\\x01")
            envelope[nonce_offset] ^= 0x01
            info.document_path.write_bytes(envelope)
            with self.assertRaisesRegex(
                RecoveryStoreError, "recovery_snapshot_authentication_failed"
            ):
                store.load_snapshot(session_id)

    def test_encrypted_store_rejects_legacy_plaintext_snapshot(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "recovery"
            plain_store = RecoverySnapshotStore(root)
            session_id = plain_store.create_session()
            plain_store.save_snapshot(
                session_id, bytes.fromhex("D0CF11E0A1B11AE1") + b"legacy-plaintext"
            )
            encrypted_store = RecoverySnapshotStore(root, encryption_key=b"C" * 32)
            with self.assertRaisesRegex(RecoveryStoreError, "recovery_plaintext_snapshot_rejected"):
                encrypted_store.load_snapshot(session_id)

    def test_encryption_key_must_be_256_bits(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "exactly 32 bytes"):
                RecoverySnapshotStore(Path(temporary) / "recovery", encryption_key=b"short")


    def test_encrypted_rewrite_keeps_previous_snapshot_if_manifest_commit_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = RecoverySnapshotStore(
                Path(temporary) / "recovery", encryption_key=b"R" * 32
            )
            session_id = store.create_session()
            payload = bytes.fromhex("D0CF11E0A1B11AE1") + b"same-plaintext"
            first = store.save_snapshot(session_id, payload)
            atomic_write = store._atomic_write

            def fail_manifest(destination, data):
                if destination.name == "manifest.json":
                    raise OSError("simulated_encrypted_manifest_failure")
                atomic_write(destination, data)

            store._atomic_write = fail_manifest
            with self.assertRaisesRegex(OSError, "simulated_encrypted_manifest_failure"):
                store.save_snapshot(session_id, payload)
            store._atomic_write = atomic_write

            self.assertEqual(store.load_snapshot(session_id), payload)
            self.assertTrue(first.document_path.exists())
            second = store.save_snapshot(session_id, payload)
            self.assertEqual(store.load_snapshot(session_id), payload)
            self.assertNotEqual(first.document_path, second.document_path)
            self.assertEqual(len(tuple(first.document_path.parent.glob("document-*"))), 1)
            self.assertEqual(len(store.list_snapshots()), 1)


    def test_manifest_rejects_boolean_schema_version(self):
        import json
        with tempfile.TemporaryDirectory() as temporary:
            store = RecoverySnapshotStore(Path(temporary) / "recovery")
            session_id = store.create_session()
            info = store.save_snapshot(
                session_id, bytes.fromhex("D0CF11E0A1B11AE1") + b"schema"
            )
            manifest = info.document_path.parent / "manifest.json"
            data = json.loads(manifest.read_text(encoding="utf-8"))
            data["schema_version"] = True
            manifest.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(
                RecoveryStoreError, "recovery_manifest_identity_invalid"
            ):
                store.load_snapshot(session_id)


    def test_snapshot_size_limit_must_be_a_positive_integer(self):
        with tempfile.TemporaryDirectory() as temporary:
            for invalid_limit in (True, False, 1.5, 16.0, "16", 0, -1, None):
                with self.subTest(max_snapshot_bytes=invalid_limit):
                    with self.assertRaisesRegex(
                        ValueError, "max_snapshot_bytes must be a positive integer"
                    ):
                        RecoverySnapshotStore(
                            Path(temporary) / "recovery",
                            max_snapshot_bytes=invalid_limit,
                        )


    def test_oversized_manifest_is_rejected_with_a_bounded_read(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = RecoverySnapshotStore(Path(temporary) / "recovery")
            session_id = store.create_session()
            info = store.save_snapshot(
                session_id,
                bytes.fromhex("D0CF11E0A1B11AE1") + b"bounded-manifest",
            )
            manifest = info.document_path.parent / "manifest.json"
            manifest.write_bytes(b" " * (64 * 1024 + 1))

            with self.assertRaisesRegex(
                RecoveryStoreError, "recovery_manifest_too_large"
            ):
                store.load_snapshot(session_id)
            self.assertEqual(store.list_snapshots(), ())

    def test_symlinked_manifest_is_not_followed(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            store = RecoverySnapshotStore(base / "recovery")
            session_id = store.create_session()
            info = store.save_snapshot(
                session_id,
                bytes.fromhex("D0CF11E0A1B11AE1") + b"manifest-symlink",
            )
            manifest = info.document_path.parent / "manifest.json"
            outside = base / "outside-manifest.json"
            outside.write_text(manifest.read_text(encoding="utf-8"), encoding="utf-8")
            manifest.unlink()
            manifest.symlink_to(outside)

            with self.assertRaisesRegex(
                RecoveryStoreError, "recovery_snapshot_unavailable"
            ):
                store.load_snapshot(session_id)
            self.assertEqual(store.list_snapshots(), ())



    def test_deeply_nested_manifest_json_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = RecoverySnapshotStore(Path(temporary) / "recovery")
            session_id = store.create_session()
            info = store.save_snapshot(
                session_id,
                bytes.fromhex("D0CF11E0A1B11AE1") + b"nested-manifest",
            )
            manifest = info.document_path.parent / "manifest.json"
            manifest.write_bytes(b"[" * 2000 + b"]" * 2000)

            with self.assertRaisesRegex(
                RecoveryStoreError, "recovery_manifest_invalid"
            ):
                store.load_snapshot(session_id)
            self.assertEqual(store.list_snapshots(), ())


    def test_snapshot_read_is_bounded_even_if_file_grows_after_metadata_check(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = RecoverySnapshotStore(
                Path(temporary) / "recovery", max_snapshot_bytes=128
            )
            session_id = store.create_session()
            info = store.save_snapshot(
                session_id, bytes.fromhex("D0CF11E0A1B11AE1") + b"bounded"
            )
            info.document_path.write_bytes(b"X" * 256)
            with self.assertRaisesRegex(
                RecoveryStoreError, "recovery_snapshot_too_large"
            ):
                store.load_snapshot(session_id)
            self.assertEqual(store.list_snapshots(), ())

    def test_snapshot_open_rejects_symlink_even_if_path_precheck_is_raced(self):
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            store = RecoverySnapshotStore(base / "recovery")
            session_id = store.create_session()
            info = store.save_snapshot(
                session_id, bytes.fromhex("D0CF11E0A1B11AE1") + b"no-follow"
            )
            outside = base / "outside.doc"
            outside.write_bytes(info.document_path.read_bytes())
            info.document_path.unlink()
            info.document_path.symlink_to(outside)

            # Simulate the path-based symlink check losing a replacement race.
            with patch.object(Path, "is_symlink", return_value=False):
                with self.assertRaisesRegex(
                    RecoveryStoreError, "recovery_snapshot_unavailable"
                ):
                    store.load_snapshot(session_id)


if __name__ == "__main__":
    unittest.main()
