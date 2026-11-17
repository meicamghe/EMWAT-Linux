# AutoSave settings and registry contract — 2026-11-17

## Evidence

Static analysis artifact: `emwat-word-lifecycle-analysis`, run `44053390645`, commit `9060bb725a69f0a457934a65c1923084ae998d2b`. The Word lifecycle job completed successfully and uploaded 452 analysis files.

## Registry location and named values

The settings handler at `0x005EAA20` constructs a Delphi `TRegistry`, selects root `0x80000001` (HKEY_CURRENT_USER), opens the key `Software\\Emwat\\Dynamic Config`, and reads/writes named values.

The decoded value names used by this handler are:

| Registry value | Meaning supported by code/UI naming |
|---|---|
| `Logging Level` | Logging level |
| `Save I/O Trace Files` | Whether I/O trace files are saved |
| `Background Priniting` | Background printing option (native spelling retained) |
| `Dont Ask Save On Print` | Suppress the save prompt during print |
| `Save Before Print` | Save before printing |
| `AutoSaveInterval` | Auto-save interval setting |

Preserve the exact registry key and value spellings, including the original typo `Priniting`. Compatibility code should not silently normalize persisted key names.

## AutoSaveInterval conversion

The settings handler reads the interval control value. If it is between 1 and 5 inclusive, the code indexes a global lookup table and multiplies the selected value by `1000` before writing `AutoSaveInterval`. Values outside that range take a default branch that writes `10000`.

This supports a millisecond conversion at the registry-write boundary and a 10,000-unit fallback. The actual table entries were not decoded in this pass, so do not assume the exact five selectable intervals beyond the observed range and multiplication. The setting's UI label/resource should be cross-checked before naming the unit in user-facing settings.

## Additional settings-form behavior

- `TEmSettingForm.chkDntAskForSaveClick` is the handler that reads/writes the registry values above.
- `TEmSettingForm.chkThrdPrntClick` is a separate setting handler; its full UI-to-registry mapping remains a follow-up.
- `TEmSettingForm.FormCreate` initializes the form and a default form parameter; it does not by itself prove the persisted values are loaded into every control.
- The settings resource and method table identify the form class as `TEmSettingForm`; the auto-save file viewer is a separate `TfrmShowAutoSaveFiles` class.

## Auto-save timer and callback wiring

The Word viewer's `OnTmrAutoSave` setup creates/initializes its event-sink object and writes explicit callback/owner pairs for:
- `WordAppDocumentBeforeSave` at `0x004CD154`;
- `WordAppNewDocument` at `0x004CD54C`;
- `WordAppWindowActivate` at `0x004CD9C0`;
- a conditional callback at `0x004D00AC`, installed when the controller flag at offset `+0x3C` is nonzero.

This confirms that AutoSave configuration and Word event callback registration are related in the same timer/setup path, but it does not establish that the timer itself saves a document on every tick. The separate `OnTmrAutoSave` trace must be followed through its state checks and worker/callback handoff before implementing an interval scheduler.

## Auto-save file viewer and close behavior

The `TfrmShowAutoSaveFiles` viewer has separate handlers for showing a selected file, deleting entries, closing Word, and closing the form. Its `CloseWordApp` routine iterates a list of Word document objects, checks an item-state value, and invokes a document virtual method at slot `+0x104`; it then releases/clears its tracked Word application object. The exact COM method represented by slot `+0x104` is not identified in this pass.

The viewer's `WordAppDocumentBeforeClose` callback checks an event argument value and calls `CloseWordApp` only for the matching close-event case. The full callback/teardown contract remains distinct from the primary `TWordViwer.WordAppDocumentBeforeClose` path.

## Linux implementation implications

1. Persist compatible settings in a documented Linux configuration namespace while preserving the original key/value mapping in the compatibility layer.
2. Keep the five AutoSave interval choices as an unresolved lookup table; do not invent exact UI labels or durations.
3. Keep `Background Priniting`, `Dont Ask Save On Print`, and `Save Before Print` as separate flags. Their effects are not interchangeable.
4. The UNO listener layer must be registered and released with document lifecycle ownership; the Windows event sink explicitly stores both callback addresses and owner pointers.
5. Implement the AutoSave scheduler only after the remaining `OnTmrAutoSave` state checks, interval source, and close/wait path have been reconciled. Do not equate the registry interval with a proven save frequency yet.

## Open questions

- Exact five values in the `AutoSaveInterval` lookup table and their UI labels.
- Exact meaning of `chkThrdPrntClick` and whether it persists additional registry values.
- Full `OnTmrAutoSave` tick-to-save decision and whether it saves, snapshots, or only coordinates a pending operation.
- Exact document virtual method at slot `+0x104` in `TfrmShowAutoSaveFiles.CloseWordApp`.
- Exact relation between the AutoSave file viewer and the main Word viewer's close event.
