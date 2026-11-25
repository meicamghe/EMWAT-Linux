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

The helper traces refine the loop:
- `0x0046E324` is TD32-named `TDictionary<AnsiString,AnsiString>.TPairEnumerator.DoGetCurrent`; its body reads the current pair's two string fields from the dictionary's internal pair storage.
- `0x0046E3CC` is associated with the `TPairEnumerator.MoveNext` RTTI entry in the enumerator VMT. Its TD32 decorated symbol says `TList<TPair>.GetCapacity`, which conflicts with the RTTI/method-table evidence; use the RTTI association as the stronger label and retain the mismatch.
- `0x0046DE84` has a TD32 symbol label `TEnumerable<AnsiString>.ToArrayImpl` and calls helper `0x0046E384`; its precise role in this particular Invoke path still needs a class/constructor cross-check.
- `0x0046DC8C` is `TDictionary<AnsiString,AnsiString>.AddOrSetValue`, confirmed separately in the same BPL.

Thus the body definitely walks key/value pairs. It also makes virtual calls on XML-related objects, consistent with an XML parameter-building/serialization path; the exact output element and response role still require the enclosing caller chain.

A direct TD32 caller scan finds one direct call to `TEmwatMethod.Invoke`, from unit finalization at `0x0046CA67`; a separate raw-pointer scan finds no exact static pointer references to `0x0046C82C`. Therefore the runtime role of this method is still unresolved. Do not call it the request dispatcher merely because its name is `Invoke`; it may instead be a generic XML/dictionary conversion method used elsewhere.

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


## 2A. Concrete PerformMethod VMT evidence and symbol mismatch

The prior slot analysis gives a more direct link between the edit request parameters and the Word loader:

- `TEditWordDocument` VMT is `0x005ED764`; its `+0x10` entry contains `0x005EE82C`.
- The routine at `0x005EE82C` reads parameter keys `wordConfig`, `wordBody`, `letterImages`, and `signData`; it checks that `wordConfig` is present and then reaches `TWordViwer.LoadDocument` at `0x004B7724`.
- The same routine's TD32 decorated symbol is `TScanDocument.PerformMethod`, not `TEditWordDocument.PerformMethod`.
- `TScanDocument` VMT `0x005ED884` has `+0x10 = 0x005EEB48`; TD32 labels the routine at `0x005EEB48` as `TFaxDocument.PerformMethod`.

This is a real class/VMT/TD32-symbol discrepancy, not something to silently rename. The strongest grounded statement is: the `TEditWordDocument` VMT's `+0x10` method pointer targets the `0x005EE82C` routine, and that routine contains the edit-document parameter keys and calls the Word loader; TD32 labels it `TScanDocument.PerformMethod`. Resolve the class-registration table and neighboring VMTs before assigning a final source-level class name.

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


## Run 149 — corrected public Invoke wrapper and concrete VMT dispatch

The exact-address VMT artifact `14225224443` must be read together with the existing service dispatcher trace. It confirms the previously documented wrapper/helper distinction:

- `TEmwatMethod` VMT `0x0046ABFC` slot `+0x0C` points to `0x0046C9E0`. TD32 labels this routine `Emwatmethod.Finalization`, but the service dispatcher and VMT layout identify it as the shared public virtual `TEmwatMethod.Invoke` wrapper.
- `TEmwatMethod` VMT slot `+0x10` points to `0x00401068`, the abstract/error stub. This is **not** the concrete method dispatch slot.
- The wrapper at `0x0046C9E0` calls the inner dictionary/XML helper at `0x0046C82C` (callsite `0x0046CA67`), then calls the instance's subclass VMT slot `+0x10` (callsite `0x0046CA88`).
- `TEditWordDocument` VMT `0x005ED764` has parent pointer `0x0046ABA4`, which is the `TEmwatMethod` VMT header self-pointer. Its slot `+0x10` points to `0x005EE82C`.
- `TScanDocument` VMT `0x005ED884` has the same `TEmwatMethod` parent and slot `+0x10` points to `0x005EEB48`.

Thus the class inheritance and BPL virtual dispatch are confirmed. The TD32 procedure-name discrepancy remains: `0x005EE82C` is decorated as `TScanDocument.PerformMethod`, although it is the `TEditWordDocument` VMT target; `0x005EEB48` is decorated as `TFaxDocument.PerformMethod`, although it is the `TScanDocument` VMT target. Keep the VMT owner and TD32 symbol separate.

The service-side `GetClass("T"+className)` resolution and the VMT `+0x0C` call are documented in `docs/EMWAT-SERVICE-EXECUTABLE-ANALYSIS.md`. The remaining open work is not the existence of the dispatch chain; it is the complete `PerformMethod` behavior, the returned XML/HTTP response, and the connection between the periodic controller archive and the close-time commit.


## Run 150 — Word event wiring and save/close checkpoints

Source: Word lifecycle artifact `14226866454` (dispatch crosswalk run 6), superseded where noted by later runs 25–26, 95–99, and the event-sink artifact `14305641689`. The new field/dispatch expansion has been added to the current branch workflow and awaits its run artifact.

### Timer-side event registration

`TWordViwer.OnTmrAutoSave` at `0x004B8A84` (procedure range `0x004B8A84–0x004BB3AF`) writes callback/owner pointer pairs into event-related fields of the `TWordApplication` wrapper. In the decoded setup path it writes:
- event-record field `+0x80` → callback pointer `0x004CD154` (TD32 symbol `TWordViwer.WordAppDocumentBeforeSave`; formal COM event identity unresolved);
- slot `+0x90` → `WordAppNewDocument` at `0x004CD54C`;
- slot `+0x98` → `WordAppWindowActivate` at `0x004CD9C0`;
- slot `+0x88` → `WordAppDocumentBeforePrintBGPrint` at `0x004CE030` (or alternate handler `0x004D00AC`, based on a viewer flag).
The corresponding owner pointers are stored in adjacent event fields. This confirms the event wiring, not yet the full timer's repeated-save behavior; the first TD32 trace decoded only 1,159 of 10,540 procedure bytes.

### Callback body at `0x004CD154` (TD32 symbol: BeforeSave)

`WordAppDocumentBeforeSave` at `0x004CD154` checks that the event document matches the active document. If viewer flag `+0x5E` is clear, it sets the Word `Cancel` output to `-1` and exits. Otherwise it accesses the Word document through interface slot `+0xD8`. The wrapper crosswalk labels `+0xD8` as `Set_Saved` (while `Get_Saved` maps to `+0xD4`), but the callsite's argument/value flow is not fully resolved; do not describe it as reading `Document.Saved` or as a proven write of a particular value. For an unsaved document and viewer flag `+0x5F`, it presents a three-choice dialog; one choice explicitly sets `Cancel=-1`. On the continuing path it changes viewer flags, calls a Word document interface method at slot `+0x29C`, clears the stored document interface, and resets state.

The dialog's exact labels and the semantics of slot `+0x29C` are not yet decoded. The numeric COM DISPID remains unresolved. The wrapper RTTI now identifies the event property as `OnDocumentBeforeClose`; this does not by itself prove that the event is the final Almas commit.

### BeforeClose and silent-save candidates

- The TD32-named `WordAppDocumentBeforeClose` at `0x004CCBBC` has a known direct caller in `FillImgFldsForPrint`; its live event-registration role is unproven. `0x004BCA88` is identified elsewhere as a `GetXmlFieldInfo` overload, not a dedicated close/commit helper.
- `TWordViwer.SilentSaveEmwatDoc` at `0x004D23D8` creates two `TStringList` objects, fills them from viewer collections at `+0x90/+0x94/+0x98/+0x9C`, and passes them with the archive object to helper `0x004AEBBC`. Its exact archive/commit role is not yet established.
- `OnControlerNotify` at `0x004BB3B0` separately reads the Word document content and creates the passworded `.easz` archive described in Run 148/149.

Keep the timer callback wiring, the `0x004CD154` callback body, the TD32-named `0x004CCBBC` helper, and the controller-notify archive operation separate until their COM dispatch and data flow are linked. The new event-sink workflow expands field-offset and dispatch-helper tracing.


### LoadDocument → autosave path → archive source linkage

The existing full-range `TWordViwer.LoadDocument` trace (`0x004B7724`) shows it calls `TWordViwer.OnTmrAutoSave` at `0x004B8A84` with a document path string (`0x004B7A58`). The timer routine copies that string into `TWordViwer+0xA0` (`0x004B8AE8`). Later, `OnControlerNotify` reads `TWordViwer+0xA0` and passes it as the first/source path to the `T7zOutArchive.AddFiles` operation.

The same `LoadDocument` path creates a file stream from the document path through `0x004041BC` (`TFileStream.$bctr`) at `0x004B7C39`, then writes document data into it. This connects the Word document file created during `LoadDocument` to the file later packaged as the `.easd` archive entry and saved in the `.easz` archive.

The exact derivation of the sibling/base path stored at `TWordViwer+0x80` is still unresolved; that field is used to create the `.easd` and `.easz` names.


## Run 151 — EditWordDocument request parameters and local document creation

Source: BPL dispatch crosswalk artifact `14227558684`.

`TEditWordDocument.PerformMethod` at `0x005EE82C` reads four named values from the request dictionary:
- `wordConfig` (`0x005EE9F4`); missing value raises `Requset XML is not valid (wordConfig parameter is null)`;
- `wordBody` (`0x005EEA88`);
- `letterImages` (`0x005EEAA0`);
- `signData` (`0x005EEABC`).

It initializes COM on the calling thread (`CoInitialize`, logged as `CoInitializing thread`), calls `TWordViwer.LoadDocument` at `0x004B7724` with these values plus the `TEmwatInvokeParam` pointer and an output string, copies the returned string into the method result, sets `bUnloadPkg` at record offset `+0x04`, then calls `CoUninitialize` (logged as `CoUnInitializing thread. ok.`). The `bResultSet` flag is set inside the non-empty response branch of `LoadDocument`, after assigning `AResponseInfo.ContentText` and calling Indy `WriteContent`.

The `LoadDocument` trace resolves the initial file stage:
- It extracts a `DocFileName` from the `wordBody` payload; an empty name triggers `DocFileName can not be null.`
- It creates a `TFileStream` for that path with `fmCreate` (`0xFF00`) and writes the document data, then logs `Word document file created.`
- It parses `wordConfig` as XML, accesses the `word-document` node, reads Word Calling Mode/configuration, and logs `ConfigXML data loaded.`
- It calls `OnTmrAutoSave` with the document path; that routine stores the path in `TWordViwer+0xA0`, which `OnControlerNotify` later packages as the `.easd` archive entry.

This establishes that `wordBody` carries the local document-file payload/metadata, while `wordConfig` carries the XML configuration used to open and configure it in Word. `letterImages` and `signData` are forwarded into the viewer; their precise runtime types and all downstream uses remain to be traced. The successful non-empty `LoadDocument` response branch writes the generated XML through `AResponseInfo.ContentText` → `TIdHTTPResponseInfo.WriteContent` and sets `bResultSet`; the captured response envelope is documented in `docs/PCAP-EDITWORD-DOCUMENT-ROUNDTRIP.md`. The remaining critical gap is the wait/event that releases the long-lived invoke request and the exact relationship, if any, between local `.easz` recovery and final Almas registration.

## Run 152 — response writer and periodic timer correlation — 2026-11-16

Source: Word response/controller workflow run `43872534265`, artifact `14228851062`; controller ownership workflow run `43873363849`, artifact `14229520023`.

- The successful `LoadDocument` response branch at `0x004B7F9C` obtains `AResponseInfo` from `TEmwatInvokeParam+0x0C`, assigns the generated XML to `ContentText` (`+0xBC`), calls Indy `TIdHTTPResponseInfo.WriteContent` via `0x0040448C`, and sets `bResultSet` at record `+0x05`.
- The PCAP capture shows HTTP 200 with `response-word status="success"` and a Base64 `application/msword` payload. The response is a rewritten legacy OLE DOC; the capture has missing TCP payload bytes, so a full-file hash/equality comparison is not claimed.
- `OnTmrAutoSave` installs `OnControlerNotify` as the `TTimer.OnTimer` callback on the timer stored at viewer offset `+0x7C`; the timer interval at viewer offset `+0x88` is clamped to at least 10,000 ms and the timer is enabled.
- `OnControlerNotify` is therefore a periodic local content/archive callback, not the Word `BeforeClose` event. It reads Word Content through slot `+0xDC` and creates .easd/.easz local archive paths. It is not currently proven to submit the final Almas registration.
- `TEDPController.Notify` at `0x004D2EC8` is a separate print-handler controller callback; it invokes `TEmwatDocPrintHandler.GetDocFieldName` and must not be conflated with `TWordViwer.OnControlerNotify`.
- The response appears approximately 54.558 seconds after the request body completes. The static wait/release chain is now mapped: `LoadDocument` calls `OnTmrAutoSave` synchronously at `0x004B7A58`; `OnTmrAutoSave` repeats a `Sleep(5)` + `ProcessMessages` loop while viewer `+0x58` is nonzero; the callback at `0x004CD154` clears that field after Word `Document.Close` at `0x004CD31C`; then `LoadDocument` writes the HTTP response. The 200-iteration cycle is a repeating maintenance interval, not a one-second total timeout. The formal COM event DISPID and the initial nonzero setter for `+0x58` remain under investigation.

### Event identity caution — 2026-11-16

The callback pointer at event-record offset `+0x80` is `0x004CD154`. TD32 names the procedure `WordAppDocumentBeforeSave`, but its first log string is `Document.OnBeforeClose Called.` and its body prompts for change registration before calling the three-argument `Document.Close` wrapper. The formal COM event DISPID and event-source mapping are not yet established. Do not use the TD32 method name alone as proof of the COM event identity. The metadata block at `0x00627B74` has since been decoded as an error-message/resource map and auto-save interval labels, not an event DISPID table; it does not resolve the formal COM event identity.


## Run 153 — synchronous Word-close wait releases HTTP response — 2026-11-16

The request-lifecycle and wait-mechanism artifacts reveal the full static wait chain:

1. `TWordViwer.LoadDocument` calls `OnTmrAutoSave` synchronously at `0x004B7A58` and tests its return value before proceeding to the response branch.
2. `OnTmrAutoSave` waits at `0x004B9AE8`: `kernel32!Sleep(5)`, `TApplication.ProcessMessages`, then compare viewer field `+0x58` with zero.
3. If the field remains nonzero, it loops. Every 200 iterations it resets the counter and runs the maintenance/check block around `0x004B9B38` (calls `0x00445B10` and `0x00455108`), then repeats. Thus 200 × 5 ms is the maintenance cycle, not the total wait limit.
4. The callback body at `0x004CD154` calls the Word `Document.Close` wrapper at `0x004CD2FF`, then clears viewer field `+0x58` at `0x004CD31C`.
5. The wait loop sees zero, disables the 10-second timer, and returns from `OnTmrAutoSave`.
6. `LoadDocument` then takes its successful branch at `0x004B7F31`, writes the `response-word` XML via Indy `WriteContent`, and sets `bResultSet`.

This explains why the local HTTP request remains open during Word editing and returns the document after the close/registration path. The observed ~54.558-second delay is consistent with the user's Word session duration. The initial setter of viewer `+0x58` and the formal COM event identity of callback `0x004CD154` remain open.

Evidence: wait-mechanism run `43874638245`, artifact `14229716255`; request-lifecycle run `43873354906`, artifact `14229047092`; Word response run `43872534265`, artifact `14228851062`.


## 2026-11-25 — Linux close-decision contract and implementation boundary

The Linux implementation must distinguish the office engine's successful Save event from close-time finalization:

- Save returns the latest approved snapshot only after `OnSaveDone` or `OnSaveAsDone` has been observed and the corresponding DOC snapshot write succeeds.
- Don't Save closes normally but returns the previous approved snapshot; if no Save completed, that is the initial input baseline.
- Cancel is a cancelled close attempt, not a terminal session cancellation. No response is emitted and the same request/session remains pending until a later decision closes the document.
- Periodic recovery snapshots are separate and are never the final response.

The current reconciliation branch implements this boundary in `LibreOfficeAdapter` by keeping `approved.doc` separate from periodic recovery data and by removing live-buffer snapshotting from `queryClosing`. The Windows event callback's formal COM DISPID and the initial nonzero setter for viewer `+0x58` remain unresolved; the Linux contract is not evidence that those Windows internals have been fully identified.


## Run 154 — RTTI resolves the registered Word close event and wait-token writer (2026-11-25)

**New evidence: Word wrapper RTTI, event-record assignments, and full-class field scan.** Artifact: workflow run `45587968139`, artifact `15008774182`.

### Event identity crosswalk

The `TWordApplication` class type information at `0x00429128` explicitly names the event properties and their instance-field offsets:

| TWordApplication event property | Event field offset |
|---|---:|
| `OnDocumentBeforeClose` | `+0x80` |
| `OnDocumentBeforePrint` | `+0x88` |
| `OnDocumentBeforeSave` | `+0x90` |
| `OnNewDocument` | `+0x98` |
| `OnWindowActivate` | `+0xA0` |
| `OnWindowDeactivate` | `+0xA8` |

The `OnTmrAutoSave` registration instructions at `0x004B8C9C–0x004B8CCE` write callback `0x004CD154` to field `+0x80`. Combining the assignment with RTTI now resolves the event property as **Word.Application.OnDocumentBeforeClose**. The TD32 procedure label `WordAppDocumentBeforeSave` is misleading for this callback. This also agrees with its diagnostic string `Document.OnBeforeClose Called.` and its three-argument `Document.Close` path.

The other observed assignments crosswalk as follows:

- `+0x88` / `OnDocumentBeforePrint` → `0x004D00AC` or `0x004CE030` (conditional print handlers).
- `+0x90` / `OnDocumentBeforeSave` → `0x004CD54C` (TD32 label `WordAppNewDocument`).
- `+0x98` / `OnNewDocument` → `0x004CD9C0` (TD32 label `WordAppWindowActivate`).

This identifies the Delphi wrapper event property, not the numeric COM DISPID. The exact DISPID and event-interface IID remain open. Earlier run-25/26 claims that `0x004CD154` was a registered BeforeSave event are superseded.

### First nonzero write to viewer +0x58

The full `TWordViwer` field scan found one nonzero write besides the close-time clear:

1. `OnTmrAutoSave` calls `TWordViwer.PrintWithGamPrintOptions` at `0x004B937C`.
2. That method writes `Self+0x58 = EAX` at `0x004C5E44`; EAX is returned by helper `0x004565DC`.
3. The wait loop checks viewer `+0x58` for nonzero at `0x004B9AE8` / `0x004BB3F2`.
4. The now-identified `OnDocumentBeforeClose` callback at `0x004CD154` clears viewer `+0x58` at `0x004CD31C`.

This locates the first nonzero setter and ties it to the synchronous wait/release path. The exact object/token returned by `0x004565DC` is not yet identified; do not reduce the field to a Boolean until that helper is traced.

The current branch event-sink workflow has been extended to trace `PrintWithGamPrintOptions`, its callers, and helper `0x004565DC`; that follow-up artifact is still pending.
