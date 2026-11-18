import base64
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from emwat_linux.recovery_key_provider import (
    RecoveryKeyProviderError,
    create_secret_service_encrypted_store,
    get_or_create_secret_service_key,
)


class _SecretServiceBackend:
    __module__ = "keyring.backends.SecretService"


class _FakeKeyring:
    def __init__(self, backend=None):
        self.backend = backend if backend is not None else _SecretServiceBackend()
        self.values = {}

    def get_keyring(self):
        return self.backend

    def get_password(self, service, account):
        return self.values.get((service, account))

    def set_password(self, service, account, value):
        self.values[(service, account)] = value


class RecoveryKeyProviderTests(unittest.TestCase):
    def test_secret_service_key_is_created_once_and_reused(self):
        keyring = _FakeKeyring()
        first = get_or_create_secret_service_key(keyring_module=keyring)
        second = get_or_create_secret_service_key(keyring_module=keyring)
        self.assertEqual(len(first), 32)
        self.assertEqual(second, first)
        self.assertEqual(len(keyring.values), 1)

    def test_plaintext_or_other_keyring_backend_is_rejected(self):
        class PlaintextBackend:
            pass

        with self.assertRaisesRegex(
            RecoveryKeyProviderError, "secure_secret_service_backend_required"
        ):
            get_or_create_secret_service_key(
                keyring_module=_FakeKeyring(PlaintextBackend())
            )

    def test_malformed_existing_key_is_rejected_not_replaced(self):
        keyring = _FakeKeyring()
        keyring.values[("emwat-linux-recovery", "snapshot-aes-256-gcm")] = "not-base64!"
        with self.assertRaisesRegex(
            RecoveryKeyProviderError, "recovery_keyring_key_encoding_invalid"
        ):
            get_or_create_secret_service_key(keyring_module=keyring)

    def test_wrong_length_existing_key_is_rejected(self):
        keyring = _FakeKeyring()
        keyring.values[("emwat-linux-recovery", "snapshot-aes-256-gcm")] = base64.b64encode(
            b"short"
        ).decode("ascii")
        with self.assertRaisesRegex(
            RecoveryKeyProviderError, "recovery_keyring_key_length_invalid"
        ):
            get_or_create_secret_service_key(keyring_module=keyring)

    def test_factory_builds_encrypted_recovery_store(self):
        with tempfile.TemporaryDirectory() as temporary:
            keyring = _FakeKeyring()
            store = create_secret_service_encrypted_store(
                Path(temporary) / "recovery", keyring_module=keyring
            )
            session = store.create_session()
            payload = bytes.fromhex("D0CF11E0A1B11AE1") + b"secret-service"
            info = store.save_snapshot(session, payload)
            self.assertTrue(info.document_path.read_bytes().startswith(b"EMWATREC\\x01"))
            self.assertEqual(store.load_snapshot(session), payload)
            self.assertNotIn("key", [p.name for p in (Path(temporary) / "recovery").rglob("*")])


if __name__ == "__main__":
    unittest.main()
