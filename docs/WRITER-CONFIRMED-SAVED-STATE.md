# Confirmed-saved Writer state and close handoff

Date: 2026-11-23
Branch: `feature/recovery-retention-policy`

## Implementation rule

The visible Writer acceptance run showed a save-complete event before `queryClosing` for Save, while Don't Save produced `queryClosing` without a save-complete event. The adapter now uses that observed ordering as its save-state boundary:

- At open, export a baseline Word 97 document to a private `last-saved.doc` before the user can edit.
- On `OnSaveDone` or `OnSaveAsDone`, export the confirmed Writer state to a temporary file, validate its CFB/Word signature, and atomically replace `last-saved.doc`.
- If the export fails, retain the previous saved copy, record the error, and fail the close handoff rather than returning ambiguous bytes.
- `queryClosing` no longer exports the live document. Edits discarded by Don't Save therefore cannot overwrite the last-saved copy.
- Periodic recovery snapshots remain separate and are never used as the Almas final response.
- Cancel remains a non-terminal close attempt: Writer stays open and the bridge waiter continues waiting. No unknown HTTP/XML cancellation response is invented.

## Tests

- Close queries and retries have no document-export side effect.
- Confirmed-save export atomically replaces the baseline.
- Failed confirmed-save export preserves the prior baseline and is not acknowledged to the coordinator.
- Existing UNO integration continues to exercise Word 97 export and response serialization.

## Acceptance boundary

Rerun the visible Writer matrix against the updated branch:

1. Save: returned file contains the new marker.
2. Don't Save: returned file retains baseline but excludes the unsaved marker.
3. Cancel: Writer remains open and the request remains pending; after a subsequent Save or Don't Save, the request completes using that choice.

This change is based on the user's visible Writer callback trace on Ubuntu/LibreOffice on 2026-11-23. It is not a release-readiness or live Almas compatibility claim.
