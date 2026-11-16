# Word lifecycle and method dispatch — static trace checkpoint (2026-11-16)

## Source and evidence boundary

Source analyzed: `analysis-input/EmwatMethods.bpl1` (PE32 Delphi BPL).  
Trace source: GitHub Actions artifact `emwat-bpl-method-invoke-contract`, run `43832553168`, artifact `14208369288`.

This document reports static disassembly and TD32 symbol evidence only. It does not establish runtime timing, successful document persistence, or the exact contents of every HTTP response.

## 1. Method dispatch base

TD32 identifies:

- `TEmwatMethod.Invoke` at `0x0046C82C`, procedure size `0x1B1` (433 bytes).
- Its declared argument is `TDictionary<AnsiString,AnsiString>`.
- The routine calls helper `0x0046DE84`, then `0x0046E324` twice in the loop, and `0x0046E3CC` as the loop test.
- It performs indirect virtual calls through object VMT offsets `+0xB0`, `+0xC8`, `+0xCC`, `+0x68`, and `+0x54`.

The shape is consistent with iterating a dictionary-like parameter collection and forwarding key/value data through virtual/interface-backed objects. The exact helper names, XML node creation semantics, and final call target remain unresolved until the helper procedures and indirect dispatch are traced together.

A direct TD32 caller scan finds one direct call to `TEmwatMethod.Invoke`, from unit finalization at `0x0046CA67`. This is not evidence of the runtime request caller: the production call is likely indirect or outside the TD32-bounded code paths searched by the direct-CALL-only tool. Do not treat the caller scan as a complete call graph.

## 2. Concrete method classes

TD32 class procedure inventory confirms the following concrete methods derive from the shared method family:

- `TEditWordDocument`
- `TScanDocument`
- `TFaxDocument`
- `TGetEmwatVersion`
- `TSetEmwatVersion`
- `TUpgradeEmwat`
- `TImageEdition`
- `TEditExcelWorkBook`
- `TCompareWordDocument`

The class RTTI/VMT analysis independently identifies VMT candidates for `TEmwatMethod`, `TEditWordDocument`, and `TScanDocument`. Their interface tables are null in the examined output; that does not rule out virtual method dispatch through their VMTs.

## 3. Edit and scan entrypoints

TD32 confirms:

- `TScanDocument.PerformMethod` at `0x005EE82C` directly calls `TWordViwer.LoadDocument` at `0x004B7724` (call site `0x005EE961`).
- `TWordViwer.LoadDocument` is a 4,960-byte procedure (`0x1360`) in module `ScanRequestXML`.
- Within `LoadDocument`, the code calls the Word viewer constructor/destructor-related routines, accesses XML-backed configuration objects, and calls `TWordViwer.AddCustomDocPropertiesToDic` at `0x004D1454`. The complete semantic mapping of each helper is not yet established.

This proves a static link from the scan method implementation into the shared Word viewer loader. It does not by itself prove that the browser's `EditWordDocument` request uses the same exact path; that needs the runtime dispatch/handler chain.

## 4. Word lifecycle methods located in TD32

The class procedure inventory locates these methods and addresses:

| Method | VA | Size |
|---|---:|---:|
| `TWordViwer.LoadDocument` | `0x004B7724` | `0x1360` |
| `TWordViwer.OnTmrAutoSave` | `0x004B8A84` | `0x292C` |
| `TWordViwer.OnControlerNotify` | `0x004BB3B0` | `0x3C8` |
| `TWordViwer.WordAppDocumentBeforeClose` | `0x004CCBBC` | `0x20C` |
| `TWordViwer.WordAppDocumentBeforeSave` | `0x004CD154` | `0x3F8` |
| `TWordViwer.WordAppNewDocument` | `0x004CD54C` | `0x474` |
| `TWordViwer.WordAppWindowActivate` | `0x004CD9C0` | `0x16C` |
| `TWordViwer.QuitWord` | `0x004CDB54` | `0xD8` |
| `TWordViwer.WordAppDocumentBeforePrint` | `0x004CDC2C` | `0x404` |
| `TWordViwer.WordAppDocumentBeforePrintBGPrint` | `0x004CE030` | `0x1128` |
| `TWordViwer.SilentSaveEmwatDoc` | `0x004D23D8` | `0x444` |

Additional field/configuration methods located:

- `GetDocFieldName` — `0x004BB81C`
- `FillField` — `0x004BC2C4`
- `FillImageField` — `0x004BC30C`
- `GetXmlFieldInfo` — `0x004BCA88`
- `GetFieldValue` — `0x004BFD38`
- `SetFieldValue` — `0x004BFDB0`
- `FillMSWFields` — `0x004C009C`
- `AddImagesToDoc` — `0x004C0410`
- `FillPrintDocFields` — `0x004CB638`
- `AddXmlWordConfigFieldsToDic` — `0x004D1148`
- `AddCustomDocPropertiesToDic` — `0x004D1454`

These names and procedure boundaries are statically confirmed. Their execution order and trigger conditions must be derived from the expanded procedure traces and runtime captures; method names alone are not enough.

## 5. Controller interface evidence

The Delphi RTTI/interface scan identifies `TEDPController` VMT at `0x004B0DFC`, with one interface entry:

- IID: `34959712-4691-4b92-ae62-c740dc955895`
- Interface VTable: `0x004B0D68`
- Interface offset: `28`

The class procedure inventory and VMT candidate trace associate `TEDPController.Notify` with `0x004D2EC8`. The VMT-slot report labels the candidate unverified, so this association should be treated as a strong static lead, not a fully proven dispatch binding until the raw VMT layout is independently cross-checked.

## 6. Implications for the observed save behavior

The presence of separate `OnTmrAutoSave`, `WordAppDocumentBeforeSave`, `WordAppDocumentBeforeClose`, `OnControlerNotify`, and `SilentSaveEmwatDoc` paths is consistent with multiple distinct save/notification mechanisms.

It does **not** prove that pressing Ctrl+S sends a local HTTP request, nor that every close event performs a save. The user's runtime observation that the browser sends an HTTP POST on close while no new local HTTP request appeared on Ctrl+S remains a separate runtime fact. Static procedure traces are needed to identify which callback retrieves document content and when it notifies the controller.

## 7. Next trace batch

The expanded workflow now traces, in parallel:

1. Dispatch helpers `0x0046DE84`, `0x0046E324`, `0x0046E3CC` and method entrypoints.
2. AutoSave, controller notification, BeforeClose, BeforeSave, NewDocument, WindowActivate, QuitWord, BeforePrint, background print, and SilentSave procedures.
3. XML field extraction, dictionary conversion, field value get/set, Word field fill, and image insertion procedures.

The service executable is not currently present in `analysis-input/`. The service branch of the workflow now emits an explicit missing-input report rather than failing or fabricating a service trace. The HTTP service call chain therefore remains an open dependency until an authorized analysis copy is available.
