# Recovery retention policy

The recovery store intentionally has **no automatic deletion policy by default**.
This protects unsaved user work until the desktop product exposes a clear
retention setting and communicates the consequences.

The opt-in `emwat_linux.recovery_retention` module provides two explicit limits:

- `max_age_seconds`: remove validated snapshots older than the configured age.
- `max_snapshots`: retain the newest configured number of valid snapshots.

At least one limit is required; a count limit must be at least one. When both
limits are configured, age expiry is applied first, then the count limit is
applied to the remaining snapshots. Invalid or unverifiable entries are not
enumerated and are not deleted by this policy.

The caller must invoke `apply_recovery_retention(store, policy)` at a deliberate
lifecycle point. The module does not start a timer, delete files during import,
or choose a retention period on behalf of the user. This is policy execution,
not encryption: snapshot bytes remain unencrypted at rest. A production UI
must obtain informed user/admin configuration before enabling it.

## Optional encryption at rest

`RecoverySnapshotStore(root, encryption_key=key)` enables AES-256-GCM encryption for new snapshots. The key must be exactly 32 bytes and is injected by the trusted application; it is never written to the recovery directory or manifest. The on-disk document begins with a versioned envelope marker and contains a fresh 96-bit nonce plus authenticated ciphertext. Encrypted filenames use opaque random identifiers so they do not expose the plaintext SHA-256; the digest remains in the private manifest for post-decryption integrity checking. The manifest records the algorithm and nonce, while the plaintext SHA-256 remains an integrity/content identifier checked after authenticated decryption. Session ID, document name, plaintext size, and plaintext SHA-256 are bound as AES-GCM associated data. The nonce stored in the manifest is also checked against the nonce embedded in the encrypted envelope before decryption.

Key custody is deliberately outside this module. The optional `recovery_key_provider` helper now retrieves or creates a stable key through the freedesktop Secret Service backend and injects it into the store. It deliberately rejects other keyring backends, including plaintext fallback stores. KWallet integration and administrator-managed provider adapters remain future work. The application composition root exposes this as the explicit `encrypt_recovery=True` option on `create_libreoffice_bridge_server()`. It obtains the key through Secret Service and injects the resulting store into `LibreOfficeAdapter`. The default remains plaintext. If a caller supplies its own office adapter, the composition root rejects combining it with `encrypt_recovery=True` rather than assuming that custom adapter uses the encrypted store. Do not place the key beside the recovery directory, in the manifest, in logs, or in source control. If the key is lost, encrypted snapshots cannot be recovered. Key rotation and automatic migration are not implemented. Install the optional `recovery-keyring` extra and ensure a running desktop Secret Service is available before using the helper.

Compatibility is fail-closed:
- A store without a key cannot read encrypted schema-version 2 snapshots.
- A store configured with a key rejects legacy plaintext schema-version 1 snapshots rather than silently mixing encrypted and plaintext data.
- Existing plaintext snapshots are not automatically migrated or deleted. Back them up and perform an explicit, separately reviewed migration before switching a live profile to encryption.
- Encryption is opt-in at the storage API boundary; the current LibreOffice adapter still uses the default plaintext store unless the application injects an encrypted `RecoverySnapshotStore`.

AES-GCM protects snapshot contents at rest, not filenames, manifest metadata, timestamps, file sizes, or the user's unlocked session. Filesystem permissions remain enabled as an additional control. This feature must not be described as enabled by default.


## Snapshot size-bound validation

The recovery store constructor accepts `max_snapshot_bytes` only as a positive
built-in integer. Booleans, floating-point values (including integral-looking
floats), strings, zero, negative values, and `None` are rejected before any
filesystem access. This keeps the configured read/write bound unambiguous and
prevents Python's bool-is-int behavior from silently accepting invalid limits.
