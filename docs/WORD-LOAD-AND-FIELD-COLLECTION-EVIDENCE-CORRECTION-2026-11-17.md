# Word load callback and field-value collection — evidence correction (2026-11-17)

## Scope and evidence

This note adds a correction to the earlier AutoSave trace using the downloaded `emwat-word-lifecycle` artifact (`word-lifecycle-2026-11-17.zip`, artifact `14314903496`). It separates procedure names, observed code behavior, and actual persistence semantics. The artifact is a static PE/TD32 analysis; it does not prove live Word behavior.

## `OnTmrAutoSave` symbol versus observed body

TD32 labels address `0x004B8A84` as `TWordViwer.OnTmrAutoSave(TObject)`. The bounded body, however, has a different strongly evidenced role:

- It logs `wv.LoadDocument method called.` at `0x004B8AAD`.
- It reads Word application state and tests `view`, `readonly`, and `protected` options.
- It logs `connecting to Ole Word Engine.` and later `connected.`.
- It installs callback/owner pairs on the object held at viewer offset `+0x44`: BeforeSave (`0x004CD154`), NewDocument (`0x004CD54C`), WindowActivate (`0x004CD9C0`), and one conditional callback (`0x004D00AC` or `0x004CE030`).
- It calls `QuitWord` at `0x004CDB54`, tests the return value, and logs `Init word engine finished.` on the later path.

The only direct callsite found in the TD32-bounded scan is `TWordViwer.LoadDocument` at `0x004B7A58`. The exact raw 32-bit pointer scan for `0x004B8A84` returned no matches. These facts do **not** prove that the method can never be invoked by a timer/event framework (indirect event dispatch is outside the direct-call scan), but they do mean the method body must not be implemented as a simple periodic save operation. Its observed code is primarily Word-engine/load lifecycle setup and event registration.

The event callback pairs are assigned as runtime data during this routine; their existence does not mean the routine itself is the BeforeSave handler. Keep the actual event methods (`BeforeSave`, `BeforeClose`, `BeforePrint`, etc.) separate.

## `SilentSaveEmwatDoc` is a field-value collector path, not a proven file save

The procedure at `0x004D23D8` is TD32-labelled `TWordViwer.SilentSaveEmwatDoc`. Its only direct caller in the available scan is `TWordViwer.GetDocFieldName` at `0x004BBA86`, after a conditional check of the field/configuration state.

Within this method:

1. It checks four viewer-owned collections at offsets `+0x8C`, `+0x94`, `+0x98`, and `+0x9C`; an empty set takes the no-work path.
2. It constructs `TfrmWordPrintOption` and calls `SetLetterReceivers` at `0x004AEA78`.
3. It collects values from the four collections, including per-entry string values, and calls `FreePrinters` at `0x004AEBBC`.
4. It sets a helper flag at `+0x44C`, invokes virtual slot `+0x13C`, and calls `TWrapRecord.LineCount` at `0x004D2948`.
5. The `TWrapRecord.LineCount` body assembles lists from viewer collections and repeatedly calls `TWordViwer.StoreFieldValuesForPrint` at `0x004BFF1C`, passing the target field-list offsets `+0xB4`, `+0xC4`, `+0xD4`, and `+0xDC` along the observed branches.

The TD32 symbol for `0x004BFF1C` is:

```
TWordViwer.StoreFieldValuesForPrint(
  UnicodeString,
  TEmwatFieldType,
  UnicodeString,
  TStringList,
  ...
)
```

This is strong evidence that the path populates print/document field-value collections. It is **not** evidence of a Word COM `Document.Save`, a LibreOffice `XStorable.store`, an HTTP response, or durable file output. The misleading `SilentSave` method name must not be treated as a storage API until the collector and its callers are traced through a real persistence boundary.

## Updated implementation guidance

- Keep `OnTmrAutoSave` as a lifecycle/event-setup routine in the reverse-engineering model; do not wire it directly to a periodic Writer save.
- Keep BeforeSave/BeforeClose callbacks separate from the method that registers them.
- Model `SilentSaveEmwatDoc` initially as a field-value refresh/collection stage, not as document persistence.
- Map `StoreFieldValuesForPrint` and the four target collections before implementing the equivalent in the Linux bridge.
- Keep the registry `AutoSaveInterval` preference unresolved as to its consumer until the new pointer/reference scan and actual interval table are reviewed. Its existence in the settings form alone does not prove that it drives the observed Word lifecycle routine.

## Next static-analysis targets

- Decode `StoreFieldValuesForPrint` at `0x004BFF1C`, including its parameter use and all direct/indirect callers.
- Scan references to global pointer slot `0x0062A808` and string `AutoSaveInterval` to locate the runtime consumer of the configured duration.
- Inspect the `TWordViwer` resource/DFM for timer component and event-property wiring; static direct-call xrefs alone cannot settle this.
- Trace the final response/serialization path after the field-value lists are populated.
