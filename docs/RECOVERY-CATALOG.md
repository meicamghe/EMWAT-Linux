# Recovery catalog contract

The Python recovery service exposes a metadata-only JSON catalog for a native
recovery picker. This contract is independent of the on-disk recovery-store
layout.

## Read catalog

Call `RecoverySnapshotService.catalog_json()`. The response is UTF-8 JSON:

```json
{
  "schema_version": 1,
  "snapshots": [
    {
      "session_id": "opaque-session-id",
      "document_name": "document-<sha256>-<unique-id>.doc",
      "size_bytes": 123456,
      "sha256": "<64 lowercase hexadecimal characters>",
      "updated_at": 1794931200.0
    }
  ]
}
```

- Entries are newest-first, and only snapshots that pass store validation are
  listed.
- `session_id` is an opaque identifier. Do not derive filesystem paths from it.
- `document_name` is display metadata, not a path.
- The catalog intentionally contains neither document bytes nor absolute
  recovery-store paths.
- Consumers should reject unsupported schema versions rather than guessing.

## Restore

A UI must ask the user to choose a destination using a trusted native save
dialog, then call `RecoverySnapshotService.restore(session_id, destination)`.
The store verifies the snapshot and publishes it atomically without replacing
an existing destination. A suffix mismatch or existing destination is an
explicit error; the UI must not silently choose another filename.

## Discard

Discard is destructive and must follow an explicit user action and
confirmation. Call `RecoverySnapshotService.discard(session_id)`; never
construct or delete store paths in UI code.

## Security and lifecycle notes

- Treat session IDs and all returned metadata as untrusted input when passed
  back from a UI. The recovery store performs identifier validation.
- Do not expose this service through an unauthenticated network endpoint.
  The current contract is an in-process application boundary, not an HTTP API.
- A successful final document export removes its recovery session. A failed
  export retains the snapshot for later recovery.
- This contract does not yet define a graphical picker, desktop notification,
  retention policy, or encryption-at-rest format.
