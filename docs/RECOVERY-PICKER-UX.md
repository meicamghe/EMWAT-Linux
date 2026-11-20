# Recovery picker UX and toolkit-neutral interaction contract

Status: design contract accepted; GTK 4 + PyGObject selected.
Date: 2026-11-18

## Product boundary

The Recovery picker is a local, in-process view over
`RecoveryPickerController` and `RecoverySnapshotService`. It must not access
the recovery directory directly and must not expose a network endpoint.

The view receives immutable `RecoveryPickerState` values. It sends user
intent (selected session ID, restore destination, explicit discard
confirmation) back to the controller. The store remains the authority for
snapshot validation, atomic restore, and deletion.

## Main view

The primary window/pane contains:

- A newest-first list of validated snapshots.
- Display name, last-updated time, and human-readable size for each row.
- A details area for the selected row (name, exact size, update time, and
  optionally a short SHA-256 fingerprint for diagnostics).
- Refresh, Restore, and Discard actions.
- A persistent explanation that recovery copies are local working snapshots,
  not the final registered document.

Do not display absolute store paths, manifest paths, encryption keys, or
document bytes. The SHA-256 value is metadata only; it is not a substitute for
the store's validation.

## View states

| State | Presentation | Allowed actions |
|---|---|---|
| Loading | Progress indicator; list actions disabled | Cancel view navigation only; no destructive action |
| Empty | Explain that no valid recovery snapshots were found | Refresh, close |
| Populated / no selection | List visible; details placeholder | Select row, refresh |
| Selected | Details visible for exactly the selected session | Restore, Discard, refresh |
| Restore destination | Native Save dialog, suggested filename from safe display metadata | Confirm destination or cancel |
| Discard confirmation | Destructive confirmation names the selected document and warns it cannot be undone | Confirm discard or cancel |
| Action error | Safe error summary; retain selection and list | Retry or close |
| Refresh error | Keep last successfully rendered state and show a non-sensitive warning | Retry refresh |

A stale selection must be cleared on refresh; the UI must never silently
substitute a different document. When a selected session still exists, keep
that selection. On first open with no prior selection, default to the newest
valid entry. These rules are implemented by
`RecoveryPickerController.state(selected_session_id)`.

## Restore flow

1. User selects a snapshot.
2. Restore opens the toolkit's native Save dialog.
3. Suggest the snapshot's display filename; do not construct a path from
   `session_id` or expose the private recovery root.
4. User explicitly chooses a destination.
5. Call `controller.restore(session_id, destination)`.
6. The store validates the snapshot and atomically publishes it without
   replacing an existing file.
7. If the destination already exists or the suffix is incompatible, show the
   error and let the user choose another destination. Never auto-rename or
   overwrite.

Canceling the Save dialog has no side effects.

## Discard flow

1. User selects a snapshot and chooses Discard.
2. Show a modal confirmation identifying the selected document by display
   name and timestamp; state clearly that deletion is irreversible.
3. Cancel is the default focused action.
4. Only after affirmative confirmation call
   `controller.discard(session_id, confirmed=True)`.
5. Refresh the catalog and select the newest remaining snapshot only if no
   previous selection remains valid.

Never invoke discard from row selection, window close, timeout, or retention
policy side effects. The controller rejects any confirmation value other than
literal boolean `True`.

## Keyboard and accessibility

- Full list navigation and selection must work without a pointer.
- Restore and Discard actions must have accessible names and visible focus.
- Destructive confirmation must be keyboard accessible, with Cancel as the
  default.
- Announce empty, loading, success, and error states to assistive technology.
- Do not communicate errors by color alone.

## Encryption and retention

- Encryption remains opt-in and key custody remains outside the UI.
- If the Secret Service key is unavailable or locked, explain that encrypted
  recovery cannot be opened; never offer plaintext fallback.
- Retention remains an explicit user-configured policy. The picker must not
  silently enable retention, start a timer, or delete old entries on open.
- A retention preview should be a separate explicit workflow, not a side
  effect of list refresh.

## Toolkit binding map

The contract is to be implemented in GTK 4 + PyGObject:

| Contract element | GTK 4 binding |
|---|---|
| Snapshot list | Gtk.ListView or Gtk.ColumnView |
| Selection | Gtk.SingleSelection |
| Restore destination | Gtk.FileChooserNative / Save dialog |
| Discard confirmation | Gtk.AlertDialog (or supported GTK 4 dialog API for the target minimum version) |
| Loading / errors | Gtk.Spinner + accessible status label |

Keep this view thin: all catalog, restore, discard, and validation behavior stays in the existing controller/service layer. GTK must not be imported by the headless protocol or document core. Do not add Qt/PySide.

## Acceptance tests before release

- Empty catalog renders without a fake row.
- First open selects newest valid snapshot.
- Refresh preserves a valid selection and clears a stale one.
- Restore cancellation changes nothing.
- Restore never overwrites an existing destination.
- Discard cannot execute without affirmative confirmation.
- A failed restore/discard preserves enough state for a retry.
- UI never receives or displays the recovery root, manifest path, key, or
  document bytes.
- Keyboard-only and screen-reader flows cover selection, restore, and discard.


## Accepted project decision

The project owner selected GTK 4 + Python/PyGObject for the Linux-only control UI and LibreOffice Writer via UNO for document editing. This picker is a GTK view, not an editor. The authoritative scope and cost/licensing requirements are in [LINUX-PRODUCT-DECISIONS.md](LINUX-PRODUCT-DECISIONS.md).
