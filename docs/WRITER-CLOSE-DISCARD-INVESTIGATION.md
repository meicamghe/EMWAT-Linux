# Writer close / discard investigation

Date: 2026-11-20
Branch: `feature/recovery-retention-policy`
Scope: LibreOffice Writer UNO close lifecycle

## Verified API facts

- LibreOffice's `XCloseListener.queryClosing` is invoked when a close is requested. It runs before `notifyClosing` and may veto the close by raising `CloseVetoException`.
- `XCloseListener.notifyClosing` is the notification that the object is really closing; at that point the listener cannot veto the close.
- The LibreOffice `SfxBaseModel::close` implementation calls registered `queryClosing` listeners, then `notifyClosing`, marks the model closed and disposes it. This API method itself does not show a Save / Don't Save / Cancel prompt.

References:
- https://api.libreoffice.org/docs/idl/ref/interfacecom_1_1sun_1_1star_1_1util_1_1XCloseListener.html
- https://github.com/LibreOffice/core/blob/master/sfx2/source/doc/sfxbasemodel.cxx

## What this does not establish

The API contract and the model close implementation do not, by themselves, establish where the interactive Writer Save / Don't Save / Cancel dialog is handled relative to UNO close-listener callbacks for a title-bar close. The current adapter avoids relying on that ordering: `queryClosing` records lifecycle evidence only, and the final payload comes from the last confirmed-saved Word-compatible copy.

The visible acceptance run in [`WRITER-CLOSE-ACCEPTANCE-TEST.md`](WRITER-CLOSE-ACCEPTANCE-TEST.md) verified Save, Don't Save, and Cancel-then-retry against the current adapter. Save returned the saved marker; Don't Save returned the prior confirmed-saved version; Cancel kept Writer open and the bridge wait pending. This establishes local Writer behavior only, not Windows/Almas wire compatibility.

## Visible acceptance test (completed)

Use a visible Writer instance and a disposable document fixture containing a known baseline marker:

1. Open the fixture through the actual adapter.
2. Add a unique unsaved marker in Writer.
3. Close the Writer window through the title-bar close control.
4. Choose **Don't Save** in the native prompt.
5. Confirm the document closes and the adapter returns the expected Word-compatible payload.
6. Decode the returned Word document and verify the unsaved marker is absent while the baseline marker remains.
7. Repeat with **Cancel** and verify Writer remains open, the bridge request remains pending, and no final response is emitted.
8. Repeat with **Save** and verify the saved marker is present in the returned document.

The marker-based visible run is recorded in [`WRITER-CLOSE-ACCEPTANCE-TEST.md`](WRITER-CLOSE-ACCEPTANCE-TEST.md). It exercises the local adapter only; it is not a live Almas roundtrip. Repeat it when changing close behavior or when adding a supported LibreOffice version.

## Implementation guardrail

Do not infer `DISCARDED` from `notifyClosing` or `disposing`; both describe closure/disposal, not the user's choice. Do not invent an Almas discard/cancel response or change the accepted local close semantics without a corresponding reference contract and visible-UI regression.

## Current branch implementation audit — 2026-11-23

The following describes the implementation at branch head `8daee0566de6b6c49d4ab3e14b8e7379a57067bd`:

- `LibreOfficeAdapter.open_document()` creates a private baseline Word-compatible `last-saved.doc` before editing and registers `_DocumentCloseListener`.
- `_DocumentCloseListener.queryClosing()` records a callback only; it does not export or snapshot the live document.
- `_DocumentEventListener` recognizes successful `OnSaveDone` and `OnSaveAsDone` events. Their callback stages an export, validates the legacy Word/CFB signature, then atomically replaces `last-saved.doc`.
- `wait_for_close()` waits for terminal document closure and returns `CloseDisposition.CLOSED` with the last confirmed-saved state available for export. This adapter does not emit `DISCARDED`.
- `DocumentCoordinator` has a `DISCARDED` branch, but the current LibreOffice adapter does not emit that disposition.

### Consequence

The current visible-UI probe has verified the local Save / Don't Save / Cancel-retry results using marker documents. It does not establish the exact Windows response for a discard, or whether Almas distinguishes that from a successful close. The user's reference behavior—closing Word returns control to Almas even when Save was not pressed beforehand—is consistent with choosing Save in the close prompt, but that interpretation is not assumed as the only Windows behavior.

### Remaining integration gate

Keep the last **confirmed saved** state separate from periodic recovery snapshots. Preserve the verified local behavior: Save returns the new confirmed state; Don't Save returns the previous confirmed state; Cancel leaves the document and bridge request pending. Any change to these semantics requires a new visible Writer acceptance run and a sanitized Windows/Almas reference fixture for the corresponding response behavior.

Do not implement a heuristic such as “no save event means discard” or “notifyClosed means save/discard”; neither has been proven. Do not alter the HTTP/XML cancellation response until its Almas contract is known.
