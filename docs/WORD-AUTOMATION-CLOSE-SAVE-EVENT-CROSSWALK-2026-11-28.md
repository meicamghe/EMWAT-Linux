# Word Automation close/save event crosswalk — 2026-11-28

## Evidence scope

- Binary: `analysis-input/EmwatMethods.bpl1`
- SHA-256: `6ff7d262f46ab009e3eecf20fca40cd41ec8ad937adf7bbfe2f6eddd56aaea2d`
- Size: 11,106,148 bytes
- Delphi metadata probe: workflow run `46151869334` / artifact `15266305067`; signature and lifecycle traces: run `46153034827` / artifact `15266446841`.
- Compiler identification: Delphi 10 Seattle, compiler version 30.0, Win32. Static analysis only; no live Word/Almas acceptance run is implied.

## Class metadata recovered by undelphi

### TWordApplication

Relevant instance fields:

| Offset | Field |
|---:|---|
| `+0x80` | `FOnDocumentBeforeClose` |
| `+0x88` | `FOnDocumentBeforePrint` |
| `+0x90` | `FOnDocumentBeforeSave` |
| `+0x98` | `FOnNewDocument` |
| `+0xA0` | `FOnWindowActivate` |
| `+0x118` | `FConnectionPoint` |
| `+0x124` | `FIntf` |

### TWordViwer

| Offset | Field | Observed role |
|---:|---|---|
| `+0x44` | `WordApp` | `TWordApplication` wrapper |
| `+0x48` | `EmwatDocument` | current Word `_Document` interface |
| `+0x58` | `DocWindow` | Word `_Window` interface |
| `+0x5C` | `IsSavingNow` | re-entrant save guard |
| `+0x5D` | `AnySaveRequested` | set by BeforeSave callback |
| `+0x5E` | `ReadyToClose` | busy/close gate |
| `+0x5F` | `OpenAsFree` | gates custom save/close prompts |
| `+0x79` | `IsSaveWithAutoSave` | autosave bypass flag |
| `+0xF4` | `SignData` | string consumed by caption-item path |

The constructor identified by undelphi is `TWordViwer.Create` at `0x004D0D24`; its destructor is at `0x004D1148`. TD32 labels around this region are stale/misaligned, so do not infer semantics from the decorated symbol alone.

## Event callback binding crosswalk

The code at `0x004B8C80` writes Delphi `TMethod` code/data pairs into the `TWordApplication` event fields. The data pointer is the `TWordViwer` instance.

| TWordApplication event field | Code pointer | Data pointer | Evidence |
|---|---:|---:|---|
| `FOnDocumentBeforeClose` (`+0x80`) | `0x004CD154` | `+0x84 = TWordViwer` | callback body checks `ReadyToClose` and writes the event Cancel argument |
| `FOnDocumentBeforePrint` (`+0x88`) | `0x004CE030` or `0x004D00AC` | `+0x8C = TWordViwer` | selected conditionally using `TWordViwer+0x3C` |
| `FOnDocumentBeforeSave` (`+0x90`) | `0x004CD54C` | `+0x94 = TWordViwer` | callback toggles save state, invokes Document.Save and cancels the original event |
| `FOnNewDocument` (`+0x98`) | `0x004CD9C0` | `+0x9C = TWordViwer` | field assignment; handler body still needs semantic cross-check |

This corrects several misleading TD32 names: `0x004CD154` is labelled `WordAppDocumentBeforeSave` but is assigned to the actual BeforeClose field; `0x004CD54C` is labelled `WordAppNewDocument` but is assigned to BeforeSave; `0x004CD9C0` is labelled `WordAppWindowActivate` but is assigned to NewDocument. Field layout, TMethod assignments, and callback behavior take precedence over those stale labels.

The `FOnDocumentBeforePrint` handler is selected based on `TWordViwer+0x3C` (`fBG_Printing`). The constructor reads these registry settings: `Background Priniting`, `Dont Ask Save On Print`, `Save Before Print`, and `AutoSaveInterval`. The `0x004D00AC` alternative is labelled `LoadOptions`; its exact semantic mapping is not closed.

## Confirmed BeforeClose behavior — 0x004CD154

1. The callback compares the incoming Word document interface with `TWordViwer.EmwatDocument` at `+0x48`; unrelated documents are ignored.
2. If `ReadyToClose` at `+0x5E` is zero, it writes `0xFFFF` to the event's Cancel word and exits. This is a hard busy/close gate.
3. When the gate is open, it pauses the autosave timer and queries the Word Document.Saved property through interface vtable slot `+0xD8`.
4. If the document is unsaved and `OpenAsFree` at `+0x5F` is nonzero, it displays this custom prompt:
   - Title: `ام وات`
   - Message: `محتويات اين سند تغيير كرده است. آيا مايل به ثبت تغييرات مي‌باشيد؟`
   - Yes: `موافقم`
   - No: `خیر`
   - Cancel: `انصراف`
5. The modal-result branches are explicit: result 2 (Cancel) sets the event Cancel word and aborts the close path; result 6 (Yes) prepares the SaveChanges variant with integer `-1`; the No branch prepares it with `0`.
6. The handler then sets `ReadyToClose=1` and calls the Word `_Document.Close` interface slot `+0x29C` with three Variant arguments, before releasing `EmwatDocument` and clearing `DocWindow`.
7. If the user cancels, the autosave timer is restored when it had previously been active.

The custom prompt is only entered when both conditions hold: the document is not saved and `OpenAsFree` is true. The source of `OpenAsFree` is unresolved: the all-procedure displacement scan found reads in ProtectDocument/BeforeClose/BeforeSave but no direct writes to `TWordViwer+0x5F` in this BPL. It may be initialized or set by the host/another module or through an indirect copy path; do not assume its runtime value.

## Confirmed BeforeSave behavior — 0x004CD54C

- If `IsSaveWithAutoSave` at `+0x79` is set, the custom branch is bypassed.
- Otherwise it sets `AnySaveRequested=1`, checks `IsSavingNow` and document identity, and uses `OpenAsFree` to choose the path.
- In the custom path it sets `ReadyToClose=0` and `IsSavingNow=1`, calls the Word Document.Save interface slot `+0x2BC`, and may call `TWordViwer.PrintWithGamPrintOptions` at `0x004C5E04` when the document-window condition matches `GamElectronic EMWAT`.
- It marks the Word document Saved through the paired interface slot `+0xDC`, resets the busy flags, and sets the original BeforeSave event Cancel word to `0xFFFF`. This suppresses Word's default save event after the custom handling.
- If `OpenAsFree` is false, it cancels the default save path; the code includes a permission message: `.شما دسترسي %s سند را نداريد` with title `ام وات - Gam Document` and confirmation button `تایید`.
- `TWordViwer.CostumizeRecAndCC` at `0x004D281C` is a separate save helper: it toggles `IsSavingNow`, calls Document.Save at `+0x2BC`, and restores the flag.
- `OnControlerNotify` at `0x004BB3B0` sets `IsSaveWithAutoSave=1`, sets `ReadyToClose=0`, calls `CostumizeRecAndCC`, marks the Word document Saved through slot `+0xDC`, then restores the flags. This is the controller/autosave route.

The `+0xD8` getter and `+0xDC` setter are consistent with the Word `Document.Saved` property pair. The exact external COM type behind the shared type reference `0x0062EEB4` on Close/Quit parameters remains unresolved.

## State-field cross-reference

| Field | Confirmed accesses |
|---|---|
| `IsSavingNow +0x5C` | BeforeSave `0x004CD6B5/0x004CD704`; CostumizeRecAndCC `0x004D2829/0x004D28ED` |
| `AnySaveRequested +0x5D` | BeforeSave sets at `0x004CD583`; constructor clears at `0x004D0E9B`; no internal read found in the current TWordViwer scan |
| `ReadyToClose +0x5E` | OnControlerNotify, GetDocFieldName, GetFieldIndexInList, BeforeClose and BeforeSave; it is toggled around work, so interpret as a busy gate rather than a simple user preference |
| `OpenAsFree +0x5F` | read by ProtectDocument, BeforeClose and BeforeSave; no direct write found in this BPL scan |
| `IsSaveWithAutoSave +0x79` | set/reset by OnControlerNotify at `0x004BB4EA/0x004BB538`; read by BeforeSave at `0x004CD579` |
| `SignData +0xF4` | read by GetCaptionItemFont at `0x004C1A18/0x004C1B0B`; loaded from the request in LoadDocument |

## SignData consumption point

- The native string key at `0x004C2718` decodes to ASCII `signData`.
- `TWordViwer.GetCaptionItemFont` at `0x004C1A18` compares a caption item's key with `signData`; on that branch it copies `TWordViwer.SignData` from `+0xF4` into a local string for caption-item processing.
- This proves a native consumption path for the external `signData` value. It does **not** decode the payload or establish the final rendered object; trace the caption-item consumer and its call sites next.
- The field's RTTI type reference is `0x0062EEBC`; the type name was not resolved. The copy helper pattern is consistent with a Delphi string assignment.

## COM wrapper signatures and remaining boundaries

- `TWordDocument.Close` overloads were recovered at `0x0042FF08` (no arguments), `0x0042FF7C` (SaveChanges), `0x0042FFF4` (SaveChanges + OriginalFormat), and `0x00430070` (SaveChanges + OriginalFormat + RouteDocument).
- The three optional parameters share unresolved type reference `0x0062EEB4`; the BeforeClose handler calls the underlying `_Document.Close` slot `+0x29C` with three Variant arguments.
- `TWordDocument.FOnClose` exists at `+0x70`, but its callback registration/use is not yet mapped.
- `TWordApplication.ConnectTo` at `0x0043E0FC` stores the default `_Application` interface and calls helper `0x00404FAC`; the actual connection-point IID/Advise path is not yet proven.
- No live Word/Almas round-trip has been run. Save/Discard/Cancel acceptance still needs the original Windows/Almas environment or a faithful runtime harness.


## Print integration and worker handoff — 2026-11-28

### BeforePrint selection and save-before-print policy

- `TWordViwer.Create` at `0x004D0D24` initializes and reads registry settings for `Background Priniting`, `Dont Ask Save On Print`, `Save Before Print`, and `AutoSaveInterval`. Defaults visible in the constructor are `fBG_Printing=1`, `fDontAskSaveBeforePrint=1`, and `fSaveBeforePrint=0`, then registry values can override them.
- The event-binding block at `0x004B8C80` chooses `FOnDocumentBeforePrint` based on `fBG_Printing` at `TWordViwer+0x3C`: nonzero selects `0x004D00AC` (`LoadOptions`); zero selects `0x004CE030` (`WordAppDocumentBeforePrintBGPrint`).
- `LoadOptions` calls `ProtectDocument` at `0x004C9EA8`. That method returns early when `OpenAsFree` is false. When true, `fDontAskSaveBeforePrint` and `fSaveBeforePrint` control behavior:
  - both true: save automatically through `CostumizeRecAndCC` at `0x004D281C`;
  - `fDontAskSaveBeforePrint` false and the document is unsaved: show the Yes/No prompt `آيا مايل به ذخيره تغييرات قبل از چاپ هستيد؟`; Yes invokes `CostumizeRecAndCC`;
  - if the document is already saved, no prompt/save is needed.
- The constructor's default `fDontAskSaveBeforePrint=1` and `fSaveBeforePrint=0` therefore do not imply an automatic save; registry overrides matter.

### Save-to-print connection

- The BeforeSave callback `0x004CD54C` invokes `PrintWithGamPrintOptions` at `0x004C5E04` only when its document-window condition matches `GamElectronic EMWAT`.
- `PrintWithGamPrintOptions` constructs/uses `TPrintOptions` and calls a Word document interface slot at `+0x6C`. The exact COM method name at that slot is not yet independently mapped, so do not label it `PrintOut` as a proven fact.
- This statically links a qualifying Save event to the GAM print-options path, but it does not yet prove the final printer queue/TIFF output timing.

### Worker and print-handler anchors

- `THidePrintingThread`: VMT header `0x004A0090`; Execute virtual slot target `0x004A1AA0`.
- `TEmwatDocPrintHandler`: VMT header `0x004A2298`; Execute virtual slot target `0x004A609C`; instance fields include `fWordApp +0x48`, `fWordDoc +0x4C`, `fJob +0x50`, `fDocFileName +0x68`, and `fPrintingOption +0x6C`.
- These are the next exact targets for resolving the print-worker wait condition and page-file handoff. No worker completion condition is claimed yet.
