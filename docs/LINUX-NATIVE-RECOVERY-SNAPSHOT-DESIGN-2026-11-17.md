# Linux-native periodic recovery snapshots — 2026-11-17

## Purpose and Windows evidence

The Windows trace establishes a periodic local recovery path: `TWordViwer.OnTmrAutoSave` installs `OnControlerNotify` on a VCL timer with a minimum interval of 10 seconds. The callback reads Word document content and writes the local `.easd/.easz` recovery/archive pair. That local archive is separate from the final `response-word` HTTP response returned after the close-wait state clears.

The Linux implementation now provides a separate, versioned recovery store. It does **not** claim compatibility with the Windows 7z/`.easz` archive, and it does not guess the Windows archive password.

## Runtime behavior

- `LibreOfficeAdapter` starts a recovery worker for each opened document.
- The default interval is 10 seconds; tests can inject a shorter interval.
- The worker calls UNO `XStorable.storeToURL` with the `MS Word 97` filter to export a copy without changing the active document URL/internal state.
- The snapshot is written into a per-user recovery session. The worker is serialized with close-time final export, property updates and document inspection through a per-document lock.
- Transient snapshot failures are retained on the internal office handle and do not terminate the user's live editing session. The previous verified snapshot remains available.
- On a successful final DOC export, the recovery session is removed. If the office process/session fails before successful finalization, the last verified recovery snapshot is preserved.

## Storage contract

Default root:

- `$XDG_STATE_HOME/emwat-linux/recovery`, when `XDG_STATE_HOME` is set; otherwise
- `~/.local/state/emwat-linux/recovery`.

Each session uses a random 32-hex identifier. Directory permissions are owner-only (`0700`); snapshot and manifest files are owner-only (`0600`). The snapshot format is the actual Word container emitted by the configured filter (currently legacy DOC/CFB for the active adapter).

The manifest records schema version, session ID, document filename, size, SHA-256 and update time. Snapshot filenames include the full SHA-256 digest. Update order is crash-conscious:

1. Write/fsync a new immutable snapshot file.
2. Atomically replace/fsync `manifest.json` to point to the new snapshot.
3. Remove the previous snapshot only after the manifest switch.

If a process crashes between steps 1 and 2, the previous manifest still points to the previous intact file. A later cleanup can remove the orphan file.

`RecoverySnapshotStore.list_snapshots()` inventories recoverable sessions; `load_snapshot(session_id)` verifies size and SHA-256 before returning document bytes. `remove_session(session_id)` removes a session after successful completion or explicit cleanup.

## Security and limitations

- The store is **not encrypted**. It relies on owner-only directory/file permissions and the user's local account security. Do not treat it as a replacement for the Windows password-protected `.easz` archive.
- A recovery catalog/restore UI and retention policy are not implemented yet. The storage API is present so those can be added without coupling recovery to HTTP response serialization.
- Recovery snapshots are not Almas registration payloads. The final response remains the close-time DOC/CFB export serialized as Base64 in the observed `response-word` envelope.
- No physical-office crash/restart recovery test or end-to-end Almas test is claimed.

## Tests added

- `python/tests/test_recovery_store.py`: CFB/DOCX recognition, owner-only permissions, integrity validation, invalid session rejection, and manifest-switch crash safety.
- `python/tests/test_libreoffice_integration.py`: live UNO session waits for a periodic recovery snapshot, verifies the stored DOC/CFB signature and that `storeToURL` did not change the Writer modified flag, then verifies successful close/export removes the recovery session.

These tests are committed but have not yet been confirmed by a fresh CI run in this session.
