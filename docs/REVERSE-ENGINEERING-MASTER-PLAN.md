## 2026-11-26 — scanner preview output and ImageGear acquisition APIs traced

- Run 32 Image/UI job (`45767912737`, artifact `15092827056`) completed successfully alongside Word/print and native regression.
- `TfrmGScanPreview.Scan` now has a traced page-indexed output contract: one `_New.tif` path, `CreateFileW(OPEN_ALWAYS)` per page, `IG_save_FD` with one-based page index, and `CloseHandle`; the selected format argument is `0x40028` or `0x80028`.
- Confirmed GEAR scanner import identities: `IG_scan_source_select`, `IG_scan_pages`, `IG_error_check`, `IG_error_clear`, `IG_error_get`. Argument and callback ABI remain open.
- This preview UI evidence is not transferred to the public `ScanDocument` connector's `TResultImage` ownership model without additional evidence.
- Detailed findings are in `docs/IMAGE-SCANNER-EDITOR-CALLGRAPH-INVENTORY.md` and `docs/NATIVE-IMAGE-PARITY-GAP-2026-11-25.md`.

## 2026-11-26 — GAM printer configuration contract recovered

- Run 32 Word/print job (`45767912737`, artifact `15092617354`) completed successfully; native regression passed. The image/UI job remained active while this update was written.
- Resolved the Windows registry, INI, special-folder, shell-launch, sleep and VCL printer API boundaries used by the GAM/Zan virtual printer.
- Confirmed registry lookup at `HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\zvprt50\\UninstallString`, fallback path handling, `configure.ini [policy] allusersfolder`, and concrete `save.ini`, `image.ini`, `general.ini` writes.
- Exact INI keys/values and Linux implementation guardrails are documented in `docs/GAM-PRINTER-CONFIGURATION-RECOVERY.md`. This does not prove Wine driver installation or actual TIFF output parity.
- Scanner result path literals are also partially decoded: base serial format `%.3d`, multipage marker `_P`, and related literal `_P000`; full path composition and output ownership remain unresolved.

## 2026-11-26 — runtime VMT map reconciles connector names

- The service-side `GetClass("T"+className)` / `VMT+0x10` mapping in `docs/EMWAT-SERVICE-EXECUTABLE-ANALYSIS.md` resolves the actual connector class names; TD32 `PerformMethod` labels are shifted for many methods.
- Runtime `TScanDocument` is confirmed at `0x005EEB48` (TD32 label `TFaxDocument.PerformMethod`). It reads `document`, logs `[Invoke ScanDocument]`, and calls `TScanCommand` target `0x004F2558` (TD32 label `GetNextPage`; RTTI published-method entry says `DoRequest`). A public scanner connector exists.
- Runtime `TEditWordDocument` remains `0x005EE82C` (TD32 label `TScanDocument.PerformMethod`).
- Runtime `TImageEdition` is `0x005EF300` (TD32 label `TEditExcelWorkBook.PerformMethod`), reads `data/config`, and logs `[Invoke EditImages]`.
- Runtime `TUpgradeEmwat` is `0x005EF24C` (TD32 label `TImageEdition.PerformMethod`), reads `PlugIn`, and calls `Applicationactivities.Finalization` (`0x0050357C`). Do not conflate it with ImageEdition.
- Updated `docs/CONNECTOR-HANDLER-ENTRYPOINT-INVENTORY.md`, `docs/IMAGE-SCANNER-EDITOR-CALLGRAPH-INVENTORY.md`, and `docs/SESSION-HANDOFF.md` to use runtime class/VMT names and retain TD32 labels only as aliases.

## 2026-11-26 — connector handler inventory update

- Runtime dispatch is now traced through `TEmwatMethod.Invoke` (`0x0046C82C`): it enumerates the incoming `TDictionary<AnsiString, T>`, invokes a handler through interface slot `+0x54`, and inserts the returned value into a result dictionary.
- The connector inventory now covers Word edit, Fax, Get/Set version, Upgrade, ImageEdition, EditExcelWorkBook, CompareWordDocument, ShowEmwatSetting, ShowLastEditedDocs, and ShowSendLog. Procedure addresses, body observations and unresolved schemas are tracked in `docs/CONNECTOR-HANDLER-ENTRYPOINT-INVENTORY.md`.
- The TD32 label `TScanDocument.PerformMethod` at `0x005EE82C` is runtime-mapped to `TEditWordDocument.PerformMethod` for `EditWordDocument`; it is not evidence of a public scanner endpoint.
- Linux currently implements/registers only the EditWordDocument method by default. Other discovered handlers remain reverse-engineering targets; do not add success stubs or inferred request keys.
- Run 31 is decoding remaining connector keys and tracing shared version/settings/compare/dispatch helpers.

# EMWAT-Linux — Master reverse-engineering coverage and work plan

Date: 2026-11-24  
Branch: feature/recovery-retention-policy  
Scope: Windows EMWAT evidence needed to complete the native Linux implementation. This is a coverage assessment, not a claim that every workflow has been runtime-validated.

## Executive result

The repository already contains substantial static analysis of the service/HTTP bridge, XML connector model, Word lifecycle, COM wrappers, archive recovery path, scanner/ImageGear calls, image forms and the GAM virtual-printer package. The next step is not to repeat broad string searches. It is to close the remaining behavioral contracts with targeted call-graph traces and sanitized synthetic runtime fixtures.

The highest-value gaps are:

1. **WordConfig and document round-trip fidelity:** semantic mapping of the full field catalog, signatures, image fields, recipient/CC configuration and response payload.
2. **Close/cancel/discard contract:** reconcile Word's registered BeforeSave callback, controller notification, content retrieval and the long-lived HTTP response for all three close choices.
3. **Agent/Service lifecycle and security:** heartbeat timing, process/session ownership, restart/termination, initialization, registry configuration and actual browser-host identity.
4. **Windows recovery archive (.easz):** writer, entry naming, encryption/password behavior and interoperability with a synthetic archive.
5. **Print subsystem:** EMWAT printer enumeration/selection/submission callsites, index semantics, GAM queue installation and the exact generated-file hand-off.
6. **Image and scan workflows:** ImageGear and ImageEn document/page lifecycle, format/metadata semantics, callbacks, multipage behavior and real-device parity.
7. **Secondary connectors and deployment:** Excel workflow, print option handlers, installer/updater behavior, COM activation identities and any data-store dependency that can be demonstrated.

## Coverage matrix

| Subsystem | Existing evidence | Remaining reverse engineering | Priority |
|---|---|---|---|
| HTTP bridge / XML parser | EmwatServiceCommandGet → TEmwatMethod.Invoke → TEditWordDocument.PerformMethod (TD32 label: TScanDocument.PerformMethod) → TWordViewer.LoadDocument is traced; LoadDocument calls OpenDoc then builds a TEmError status response and writes via Indy; heartbeat endpoint is present | Explain the 54.558-second duration inside OpenDoc/Word COM activation; decode TEmError wire schema; server-side Origin/token/session validation, endpoint coverage, error responses, method schemas and request bounds | P0 |
| Word document lifecycle | Custom Yes/No/Cancel prompt is decoded; ReadyToClose (+0x5E) is cleared during OnControlerNotify and restored at exit; BeforeSave cancels close while false; LoadDocument response is emitted after OpenDoc, not proven to wait for close | Map event-record DISPID; correlate each close choice with returned bytes/Almas result; preserve close and HTTP response as separate lifecycles | P0 |
| WordConfig / fields | GetXmlFieldInfo uses separate regular/twin dictionaries; SetFieldValue recognizes urlencoded/base64; TwinField carries Field1Name/Field2Name and caption typography/alignment; CustomDocumentProperties and image/text routes are statically mapped | Full semantic mapping of the approximately 180-field catalog; separator/concator/encryption semantics; twin ordering; signature signData; image sizing/caption layout; permission/settings/RequestedTypes; sanitized template parity | P0 |
| Agent ↔ Service | Exact mutex GUIDs and shutdown-message protocol confirmed; Service broadcasts TERMINATE_EM_SERVICE then self-terminates; Agent contains heartbeat URL http://127.0.0.1:1984/?heartbeat and registry strings LifeCheckInterval/MaxSequentialFailure/LogFilePath. Current hashes have no WTS/SCM imports. | Resolve heartbeat callsite/response, registry hive/defaults, peer launch/monitor/restart ownership, remaining messages/events and race/failure behavior; taskkill strings are not yet callsite-proven | P1 |
| Browser host / init | Embedded JavaScript postMessage bridge and init endpoint are recovered | Identify actual host control/process and CLSID/ProgID; prove how the Almas page loads the bridge; Origin/Referer validation and browser compatibility | P1 |
| AutoSave timer / .easz recovery | OnTmrAutoSave uses Dynamic Config AutoSaveInterval (seconds converted to ms, min 10,000 ms); callback invokes CostumizeRecAndCC, Get_Content(-1), builds .easd/.easz paths and calls euUnArchive. euResetMemory is now identified as a distinct output-archive helper with callers in Applicationactivities.Finalization and recovery Delete; the same fixed password candidate is passed in input and output paths | Resolve -1 semantics, archive entry/path mapping, output +0x44 slot identity and actual encryption; validate synthetic archives | P1 |
| Printer management / GAM | Explicit BGPrint path reaches Word COM Application.PrintOutOld; timer callback CostumizeRecAndCC calls Document.PrintOutOld slot +0x2BC once normally, with up to two exception-retry attempts; BeforePrint/print-handler classes and fBG_Printing/fDontAskSaveBeforePrint/fSaveBeforePrint flags are identified; run 32 recovers registry/INI/special-folder APIs and exact save/image/general INI settings for GAM; run 34 confirms EnumPrintersA Level-2 enumeration, 0x54-byte PRINTER_INFO_2A records and the `zvprt1` driver-name match | Correlate the normal PrintOutOld job with EnumJobsW document-name matching and the GAM artifact; identify +0x3F0 COM call and 15 Variant args; trace print-thread ownership, active/default queue and final output; validate a real GAM TIFF fixture | P1 |
| ImageGear GIF/LZW extension | Exact IGLZW32S.DLL identity/hash, 45-entry registration loop, four GIF extension handlers, GIF writer depth guard, encoder dictionary/bit-writer structure, TIFF LZW decode path, `GearExtInfoGet/Set` two-slot x86 ABI, and `TIF_Proc_LZW_Comp` 19-slot callee-cleanup boundary documented | Resolve nineteen TIF argument types and host callback prototypes from callers/controlled Wine 11 runtime; prove EOI/final-code ordering and trailer byte; validate width/reset boundaries with independent decoders; identify all registrations and thumbnail callback | P2 |
| ImageGear / scanner | GEAR API imports, many callsites, TScanCommand state transitions, IIPEditor and some page/handle semantics; Linux SANE backend exists; runtime ScanDocument connector confirmed; `TScanCommand` field table and `FResponseXML` handoff recovered; result path literals `%.3d`, `_P`, `_P000` partially decoded | Exact GEAR version/constants, remaining ABI arguments, frame/page lifecycle, cancellation/error mapping, metadata, save/load semantics, full result path composition/ownership and hardware comparison | P2 |
| ImageEn / image tools | DFM forms and ImageEn/WIA/TWAIN dependencies identified | Handler bodies, acquisition source selection, multipage document model, undo/redo, crop/rotate/flip semantics, insert/remove/reorder pages, TIFF/JPEG export and callback/result contract | P2 |
| Word print options | DFM plus print-handler callsites confirm Receivers, ReceiverDeps, ccReceivers, ccReceiverDeps and Persian CC-prefix paths for main/archive/selected documents | Exact list separators/order/deduplication, selected-field mapping, page-range parser, copy-count and saved-setting semantics, mapping to queue/output | P2 |
| Excel connector | Excel Automation wrappers and TEditExcelWorkBook class are identified | Method payload schema, workbook/sheet/range operations, formulas/styles, save/return behavior, error semantics and real fixture | P2 |
| Installer / updater / COM | PE imports/resources, some Registry keys and COM infrastructure are documented | Installer custom actions, service registration/config defaults, uninstall/upgrade rollback, actual Office CLSID/ProgID/version, 32-bit registry view, browser host registration | P2 |
| Database / external storage | No direct common SQL driver imports found in the inspected PE import report | Do not assume a database exists. Search configs, dynamically loaded modules, file formats and callsites only if a concrete storage read/write path appears | P3 |

## Ordered work packages

### P0-A — Separate Word close, periodic recovery, and HTTP response contracts

These are related workflows, but current evidence does **not** establish them as one callback chain:

1. **Word event sink:** trace callback registration and COM event interface/slot identity. The TD32 label `WordAppDocumentBeforeSave` conflicts with diagnostic text `Document.OnBeforeClose Called.` in the routine. `WordAppDocumentBeforeClose` is a separate procedure; its active registration is not yet proven. Do not assign a COM DISPID from the TD32 symbol alone.
2. **Close decision:** trace the registered callback's Yes/No/Cancel path, Word Close wrapper arguments and `Set_Saved` calls. Determine which bytes Word/EMWAT considers saved for each choice.
3. **Periodic recovery:** separately trace `OnControlerNotify` (timer callback, minimum 10 seconds), `ReadyToClose` gating, `CostumizeRecAndCC` (one normal Document.PrintOutOld call with up to two exception retries; `IsSavingNow` guard), `Get_Content(-1)`, `.easd`/`.easz` path construction, `euUnArchive` and the distinct output helper `euResetMemory`. The meaning of `-1` and the output +0x44 slot remain unknown. This path is not the final HTTP response writer.
4. **HTTP response:** the Service → BPL → Word → Indy write chain is now mapped through `EmwatServiceCommandGet`, `TEmwatMethod.Invoke`, `TEditWordDocument.PerformMethod` (TD32 label `TScanDocument.PerformMethod`), `TWordViewer.LoadDocument` and `TIdHTTPResponseInfo.WriteContent`. Trace the approximately 54.558-second duration inside OpenDoc/Word COM activation; do not assume the response waits for Word close.
5. Correlate the above with the captured successful `response-word` response and its approximately 54.558-second delay. The capture has TCP payload gaps, so do not treat the returned document bytes as a complete verified fixture.
6. Capture sanitized, synthetic Yes / No / Cancel cases and compare request completion, response XML, returned document bytes and Almas-side outcome.
7. Preserve the user's observed Windows behavior (closing Word returns control to EMWAT even without manually pressing Save) without assuming that it means the timer archive, Word Save event and HTTP return are the same operation.

**Exit criterion:** all three close choices have a documented state transition and response contract, or an explicit, bounded unknown with the missing fixture identified.

### P0-B — Complete WordConfig semantics

1. Preserve the confirmed text/plain vs image/* routing and the urlencoded/base64 image payload support.
2. Generate a metadata-only inventory of all field identifiers and declared encoding/type attributes.
3. Resolve twin-field pairing and ordering without assuming Writer enumeration order equals Word COM order.
4. Recover signData parsing, separator and concatenation semantics from code paths; do not log or publish signature values.
5. Compare a sanitized synthetic Windows request with Writer's field inventory and returned response.

**Exit criterion:** every field is classified as mapped, unsupported with a reason, or unknown; no arbitrary index-to-property mapping.

### P1-A — Agent and Service lifecycle

1. Trace Agent startup, service discovery, process creation/attachment, heartbeat timer, timeout and restart/termination.
2. Trace WTS session notifications and window-message/IPC receivers to their state transitions.
3. Identify registry/config keys actually read and written; distinguish static strings from callsite-confirmed use.
4. Test service unavailable, port occupied, stale process, user logoff/logon and multiple sessions in a controlled Windows VM.

**Exit criterion:** a state diagram and failure/recovery matrix with each transition tied to a callsite or runtime observation.

### P1-B — .easz archive interoperability

1. The timer-side read path is established: OnControlerNotify calls euUnArchive and the T7zInArchive entry enumeration/extraction methods.
2. Create a synthetic Windows archive containing a non-sensitive generated DOC/DOCX only.
3. Trace the actual writer call chain; do not treat the T7zOutArchive class presence as proof it creates .easz in this workflow.
4. Trace euResetMemory's output +0x44 method and prove its relationship to the T7zOutArchive callback/password setter; euGetAutoSavePass is not the fixed archive password source.
5. Verify Linux read/write interoperability independently; keep the existing Linux recovery manifest format separate.

**Exit criterion:** at least one known-good synthetic archive can be inspected and opened with a documented password/encryption contract, or support remains explicitly out of scope.

### P1-C — Printer pipeline and GAM package

1. EMWAT's print-options path reaches Word COM Application.PrintOutOld; the BeforePrint callback and print-handler/controller objects are identified.
2. Map the 15-Variant COM call at vtable +0x3F0 and the handler's stored method callback; determine active/default printer selection.
3. Keep queue enumeration/job-status calls separate from actual print submission.
4. Decode InstallShield tables/custom actions, driver/monitor registration, service setup and registry writes without executing the installer.
5. Trace zvprtsrv page completion, .zan lifecycle, final file path/extension and how EMWAT consumes the result. The config CLI proves fileformat 1 = TIFF and 2 = JPEG; it does not yet prove the EMWAT hand-off.
6. Resolve compression and save-collision enums with controlled output fixtures.

**Exit criterion:** Linux print adapter has a verified destination-selection and submission contract plus a known output format/return path.

### P2-A — ImageGear and ImageEn

1. Reconcile all scanner callsites against the exact GEAR DLL version and exported ABI.
2. Recover page/frame lifecycle, resolution/color metadata, error/cancel paths and output FD semantics.
3. Trace ImageEn event handlers and the three decoded DFM forms to actual BPL methods.
4. Test page order, rotate/crop/flip, undo/redo, TIFF/JPEG export and insert/remove/reorder operations on synthetic multipage images.
5. Compare SANE hardware behavior only after the Windows source/mode enums and page model are known.

**Exit criterion:** each visible image operation has a defined input/output contract and regression fixture; unimplemented device-specific behavior is explicit.

### P2-B — Excel, print options and deployment

1. Trace TEditExcelWorkBook.PerformMethod and its workbook/sheet/range operations.
2. Trace Word print option handlers, page syntax and saved-setting persistence.
3. Inspect installer/updater custom actions and registry writes, including 32-bit COM registration.
4. Identify Office activation CLSIDs/ProgIDs from type libraries, resources and registry fixtures; do not infer them from generic CoCreateInstance imports.

**Exit criterion:** each feature is either implemented against a known contract or deliberately deferred with evidence and impact recorded.

## Evidence discipline and safety

- Label every result user-observed, runtime-confirmed, statically confirmed, inferred, or unknown.
- A string, import, DFM control, class name or CI pass does not by itself prove a runtime workflow.
- Use synthetic documents, images, archive entries and print jobs. Never commit customer letters, signatures, tokens, cookies, credentials or unredacted HAR/PCAP data.
- Keep binary hashes and version metadata beside every address-level trace; do not combine offsets from different builds.
- Do not execute vendor installers or Windows driver packages as part of static analysis.
- Keep the Linux product native. Windows binaries are evidence inputs, not Linux runtime dependencies.
- Do not claim full Almas E2E, full field mapping, .easz compatibility, physical scanner parity or print parity until the corresponding acceptance fixtures pass.

## Existing evidence documents

- Project status (PROJECT-STATUS.md)
- Product workflow (PRODUCT-WORKFLOW-ANALYSIS.md)
- HTTP local API (HTTP-LOCAL-API-ANALYSIS.md)
- Word document protocol (WORD-DOCUMENT-PROTOCOL-ANALYSIS.md)
- Word recipient/CC print-handler analysis (WORD-RECIPIENT-CC-ANALYSIS.md)
- Service executable analysis (EMWAT-SERVICE-EXECUTABLE-ANALYSIS.md)
- Agent/Service IPC and lifecycle (AGENT-SERVICE-IPC-ANALYSIS.md)
- Office COM analysis (OFFICE-COM-ANALYSIS.md)
- Import table analysis (IMPORT-TABLE-ANALYSIS.md)
- Resource analysis (RESOURCE-ANALYSIS.md)
- Windows .easz archive (EASZ-ARCHIVE-FORMAT.md)
- SevenZip AutoSave archive/password analysis (SEVENZIP-ARCHIVE-ANALYSIS.md)
- Dynamic Config registry settings (DYNAMIC-CONFIG-REGISTRY-ANALYSIS.md)
- Scanner interface (SCANNER-INTERFACE-ANALYSIS.md)
- Image call graph (IMAGE-CALL-GRAPH.md)
- GEAR API calls (GEAR-API-CALLS.md)
- ImageGear GIF/LZW extension (IMAGEGEAR-LZW-GIF-REVERSE-ENGINEERING.md)
- Word print options (WORD-PRINT-OPTION-DFM.md)
- GAM virtual printer (GAM-VIRTUAL-PRINTER-REVERSE-ENGINEERING.md)
- Printer compatibility plan (PRINTER-COMPATIBILITY-PLAN.md)
- EMWAT Windows spooler selection/job matching (EMWAT-PRINTER-SPOOLER-ANALYSIS.md)
- Agent/Service IPC, heartbeat and watchdog (AGENT-SERVICE-IPC-ANALYSIS.md)
- Word XML image-field/caption and GEAR32PD resolution path (WORD-IMAGE-FIELD-PIPELINE-ANALYSIS.md)

## Immediate next execution order

1. Trace the 15 Word PrintOut arguments and print-thread handoff; EMWAT's driver-name queue discovery, paused-state check, and JOB_INFO_1 document-name matching are now mapped, but the matching job-to-GAM-artifact hand-off remains open.
2. In parallel, trace the 54.558-second duration inside OpenDoc/Word COM activation; the response is emitted after OpenDoc and is not proven to wait for Word close.
3. Trace the normal timer-driven CostumizeRecAndCC → Document.PrintOutOld → BeforePrint path and correlate its document label with the spooler job and GAM artifact; the two exception retries are fallback attempts, not three unconditional jobs.
4. Prove or exclude indirect calls into the `T7zOutArchive` wrapper stored at `T7zPlugin+0x44`; current direct-call scans show no application caller of `SaveToStream`/`SaveToFile`, and `SetPassword` is a no-op. Search other modules/processes for `.easz` writes and correlate a real file before implementing archive creation.
5. Complete WordConfig signature/twin/image field coverage.
6. Resolve the Agent config-record initializer and registered-message trailing-underscore mismatch. Also replace the Windows watchdog's process-wide `taskkill WINWORD.EXE` recovery side effect with document-session-scoped graceful recovery; then resolve the actual Word image caption save API/output format and `FillMSWFields` COM operations, followed by Excel and installer/updater details. The heartbeat contract is implemented in the native bridge and passed CI run `45352644056`, including a concurrency test that keeps heartbeat responsive during a blocked document POST. The original Service DFM also confirms loopback binding at `127.0.0.1:1984`, queue 100, and a 15-second server shutdown wait.


## 2026-11-28 — parallel analysis update

Run 22 added focused scanner request/constraint, ImageEn import, Word COM callback and printer/archive traces. See docs/REVERSE-ENGINEERING-PARALLEL-FOLLOWUP-2026-11-28.md for evidence and open questions.

Immediate execution order:
1. Review the pending Word/Printer artifact from run 22.
2. Map the 15-Variant Word PrintOut call to the actual printer job and GAM artifact.
3. Resolve the SevenZip output object +0x44 callback and prove or exclude encryption.
4. Continue scanner XML property names and the +0x14 image-derived threshold.
5. Obtain the exact PKIECtrl23.bpl from this EMWAT build before attempting to reverse the ImageEn Acquire implementation.


## 2026-11-28 evidence update and next gates

Newly recovered contracts are recorded in:
- `docs/SCANNER-XML-SERIALIZATION-CONTRACT-2026-11-28.md`
- `docs/PRINTER-QUEUE-AND-GAM-DRIVER-REVERSE-ENGINEERING-2026-11-28.md`
- `docs/WORD-PRINTOUT-18-VARIANT-ABI-RECHECK-2026-11-28.md`

Scanner XML root/key names are now known from UTF-16LE setter constants. Remaining scanner gates are root metadata/defaults, runtime request/response examples, and the `MaxFileSize` unit/conversion.

Printer analysis now establishes GAM-printer discovery by `PRINTER_INFO_2A.pDriverName`, paused-state inspection through `PRINTER_INFO_2A.Status`, and queue matching through `EnumJobsW` / `JOB_INFO_1W.pDocument`. The next gate is proving how `TrimLF` and indirect references invoke `ExtractFileNameEX`, and whether the match gates TIFF/archive completion. Decode the driver-name constant at `0x0047CC64` and map `InstallZanPrinter` / `CheckPrinterPaused`.

Word PrintOut remains blocked on a reproducible 18-Variant caller versus 17-Variant generated-wrapper mismatch. Resolve against the exact WordXP type-library metadata; do not drop an argument or infer parameter names.

ImageEn `TImageEnMIO.Acquire` remains an external `PKIECtrl23.bpl` dependency. SevenZip output encryption and `euResetMemory` VMT identities remain open. No implementation/release work until these contracts are closed and runtime acceptance is available.


## 2026-11-28 SevenZip output ownership gate

The latest SevenZip pass identifies the plugin-to-output-archive ownership path and the callback/context slots. See `docs/SEVENZIP-OUTPUT-ARCHIVE-OWNERSHIP-2026-11-28.md`. The remaining implementation gate is to identify the callback/context producer, SetCompleted/progress callback role, output entry naming, and whether encryption exists. Do not infer encryption from the method name `CryptoGetTextPassword2`; output `SetPassword` is a stub and the constructor-style initializer only stores an interface object.


## Scanner unit conversion gate updated

The MaxFileSize unit is now closed as KiB: `TResultImage.GetFileStream` returns the 64-bit stream byte size, and `TScanCommand.Finalization` compares it with `MaxFileSize << 10`. `TGearImgProc.GearType` contains explicit 39.37008 and 0.3937 conversion factors; the remaining gate is matching selector values to exact ImageGear enum labels and verifying rounding/edge behavior. Evidence: `docs/SCANNER-RESOLUTION-AND-FILESIZE-UNITS-2026-11-28.md`.


## TIFF output lifecycle gate

The current static call graph ties `TWordViewer.LoadDocument` to `TCreateTiff.SeparteImages`, then to printer checks, `THidePrintingThread.Execute`, and GDI+ page processing via `TGPImage`/`TGPEncoderParameters`. The remaining gate is to identify the exact GDI+ save API, output naming, compression parameters, and how the Word queue-disappearance condition/hidden worker result gates TIFF completion. Evidence: `docs/TIFF-OUTPUT-GDIPLUS-PIPELINE-2026-11-28.md`.


## GDI+ TIFF encoder parameters resolved

The two GUIDs passed by `SeparteImages` resolve to standard GDI+ `EncoderCompression` and `EncoderSaveFlag`. Their values are 2 (LZW compression) and 18 (MultiFrame), respectively. This establishes the intended multi-page TIFF encoding configuration. Remaining work: map the interface VMT slots to initial Save, SaveAdd, and final flush, then confirm page ordering and output filename.
