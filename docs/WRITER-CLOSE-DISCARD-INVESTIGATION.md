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

The API contract and the model close implementation do not, by themselves, establish where the interactive Writer Save / Don't Save / Cancel dialog is handled relative to the UNO close-listener callbacks for a title-bar close. Therefore they do not prove whether the current `queryClosing` snapshot is captured before or after the user chooses Don't Save.

The current adapter calls `storeToURL` from `queryClosing`, and later treats the file as the final output after terminal close. A unit test with a fake document proves that a snapshot can be produced without an earlier `OnSaveDone` event; it does not prove correct discard behavior in the real Writer UI.

## Required acceptance test

Use a visible Writer instance and a disposable document fixture containing a known baseline marker:

1. Open the fixture through the actual adapter.
2. Add a unique unsaved marker in Writer.
3. Close the Writer window through the title-bar close control.
4. Choose **Don't Save** in the native prompt.
5. Confirm the document closes and the bridge returns to Almas.
6. Decode the returned Word document and verify the unsaved marker is absent while the baseline marker remains.
7. Repeat with **Cancel** and verify Writer remains open, the bridge request remains pending, and no final response is emitted.
8. Repeat with **Save** and verify the saved marker is present in the returned document.

Record callback order and the final bytes for each case. Run this against the supported Ubuntu/LibreOffice versions, not only a headless API close.

## Implementation guardrail

Do not infer `DISCARDED` from `notifyClosing` or `disposing`; both describe closure/disposal, not the user's choice. Do not change the current snapshot timing or map a close to a discard response until the visible-UI acceptance test or an equivalent verified interaction contract establishes the behavior.

## Current branch implementation audit — 2026-11-23

Inspected on branch `feature/recovery-retention-policy` at head `944ec9f3f34c355a7d20e49e7fd734e56e955ee1`:

- `LibreOfficeAdapter.open_document()` creates `final.doc` as a separate output path and registers `_DocumentCloseListener`.
- `_DocumentCloseListener.queryClosing()` calls `document.storeToURL(final.doc, ...)` immediately when a close attempt is queried. This is before the implementation has established which button the visible Writer prompt will resolve to.
- `_DocumentEventListener` recognizes `OnSaveDone` and `OnSaveAsDone`, but its callback only calls the coordinator's `session.record_engine_save()`. It does not refresh or replace `final.doc`.
- `wait_for_close()` waits for the closed event, then accepts the queryClosing snapshot as the final document. It always returns `CloseDisposition.CLOSED`; it does not produce `DISCARDED`.
- `DocumentCoordinator` has a `DISCARDED` branch, but the current LibreOffice adapter does not emit that disposition.

### Consequence

The current visible-UI result is not proven correct for **Don't Save**. If `queryClosing` runs before the user chooses Don't Save, the file already written to `final.doc` can contain edits the user explicitly discarded. The existing fake-document tests only prove that `storeToURL` is called and that listener callbacks are traced; they do not prove the native Writer prompt ordering or final bytes.

The Save event callback is currently observational only; it does not fix this gap. Therefore this branch must not claim Save/Don't Save parity or release readiness.

### Safe implementation direction (not yet implemented)

Before changing the adapter, establish the actual visible Writer event order and file behavior on the supported LibreOffice version. The candidate design must preserve the last **confirmed saved** state separately from recovery snapshots, and must only return that saved state after an accepted close when the user chose Don't Save. Save must return the newly confirmed saved state. Cancel must leave the document and bridge request pending. A save event alone is not sufficient unless its ordering and the bytes it confirms are validated in the visible acceptance test.

Do not implement a heuristic such as “no save event means discard” or “notifyClosed means save/discard”; neither has been proven. Do not alter the HTTP/XML cancellation response until its Almas contract is known.
