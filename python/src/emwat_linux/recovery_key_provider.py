"""Strict Secret Service key custody for encrypted recovery snapshots.

The provider deliberately refuses keyring fallback backends: a plaintext file
backend would defeat the at-rest encryption this key protects.
"""
from __future__ import annotations

import base64
import binascii
import secrets
from pathlib import Path
from types import ModuleType

from emwat_linux.recovery_store import RecoverySnapshotStore


_DEFAULT_SERVICE = "emwat-linux-recovery"
_DEFAULT_ACCOUNT = "snapshot-aes-256-gcm"


class RecoveryKeyProviderError(RuntimeError):
    """Raised when a secure desktop keyring cannot safely provide the key."""


def get_or_create_secret_service_key(
    *,
    service: str = _DEFAULT_SERVICE,
    account: str = _DEFAULT_ACCOUNT,
    keyring_module: object | None = None,
) -> bytes:
    """Get a stable 32-byte key from freedesktop Secret Service.

    No insecure keyring backend is accepted. The secret is stored as Base64
    inside the desktop Secret Service and never written to the recovery folder.
    """
    if not service or not account:
        raise ValueError("service and account must be non-empty")
    if keyring_module is None:
        try:
            import keyring as keyring_module  # type: ignore[no-redef]
        except ImportError as exc:
            raise RecoveryKeyProviderError("recovery_keyring_dependency_missing") from exc

    try:
        backend = keyring_module.get_keyring()
        backend_module = type(backend).__module__
        if backend_module != "keyring.backends.SecretService":
            raise RecoveryKeyProviderError("secure_secret_service_backend_required")

        encoded = keyring_module.get_password(service, account)
        if encoded is None:
            key = secrets.token_bytes(32)
            encoded = base64.b64encode(key).decode("ascii")
            keyring_module.set_password(service, account, encoded)
            # Read back to detect a failed/non-persistent secret write.
            if keyring_module.get_password(service, account) != encoded:
                raise RecoveryKeyProviderError("recovery_keyring_persistence_failed")
            return key

        try:
            key = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError, TypeError) as exc:
            raise RecoveryKeyProviderError("recovery_keyring_key_encoding_invalid") from exc
        if len(key) != 32:
            raise RecoveryKeyProviderError("recovery_keyring_key_length_invalid")
        return key
    except RecoveryKeyProviderError:
        raise
    except Exception as exc:
        raise RecoveryKeyProviderError("recovery_keyring_unavailable") from exc


def create_secret_service_encrypted_store(
    root: str | Path | None = None,
    *,
    max_snapshot_bytes: int = 128 * 1024 * 1024,
    keyring_module: ModuleType | object | None = None,
) -> RecoverySnapshotStore:
    """Construct an encrypted store using a stable Secret Service key.

    This helper is explicit; the default adapter configuration remains
    unchanged and plaintext until the desktop composition opts into this call.
    """
    key = get_or_create_secret_service_key(keyring_module=keyring_module)
    return RecoverySnapshotStore(
        root,
        max_snapshot_bytes=max_snapshot_bytes,
        encryption_key=key,
    )


__all__ = [
    "RecoveryKeyProviderError",
    "create_secret_service_encrypted_store",
    "get_or_create_secret_service_key",
]
