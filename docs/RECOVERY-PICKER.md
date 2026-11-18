# Recovery picker controller

The in-process `RecoveryPickerController` is a toolkit-neutral boundary for
native desktop UI integration. It exposes validated metadata, delegates restore
to the recovery service using the destination selected by the user, and refuses
discard unless the caller passes an explicit confirmation flag.

The controller is not a graphical UI and is not exposed over HTTP. A future
GTK/Qt/other native view should:
- render only `entries()` metadata;
- use a trusted native save dialog and call `restore(session_id, destination)`;
- show a destructive confirmation before `discard(session_id, confirmed=True)`.

The store remains responsible for identifier validation, integrity checks,
symlink boundaries, and no-overwrite atomic restore.
