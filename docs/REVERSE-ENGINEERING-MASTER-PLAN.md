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
| HTTP bridge / XML parser | Indy server, loopback port 1984, init/heartbeat/invoke captures, XML names (emwat/version/method/class/param/name), bridge message forwarding and wildcard CORS-related header strings have static/runtime evidence | Server-side Origin/token/session validation, endpoint coverage, error responses, all method schemas, request bounds/version behavior and exact response behavior for non-Word methods | P0 |
| Word document lifecycle | Custom Persian Yes/No/Cancel prompt is decoded; Yes calls Document.Close(SaveChanges=True), No calls Document.Close(SaveChanges=False), Cancel sets COM Cancel; LoadDocument writes through TIdHTTPResponseInfo.ContentText/WriteContent | Resolve the long-lived invoke release condition and exact close-to-response correlation; map event-record DISPID; correlate each close choice with returned bytes/Almas result. No direct WaitForSingleObject/Sleep callsite was found in the inspected BPL | P0 |
| WordConfig / fields | GetXmlFieldInfo uses separate regular/twin dictionaries; SetFieldValue recognizes urlencoded/base64; TwinField carries Field1Name/Field2Name and caption typography/alignment; CustomDocumentProperties and image/text routes are statically mapped | Full semantic mapping of the approximately 180-field catalog; separator/concator/encryption semantics; twin ordering; signature signData; image sizing/caption layout; permission/settings/RequestedTypes; sanitized template parity | P0 |
| Agent ↔ Service | Exact Agent/Service mutex GUIDs and single-instance checks confirmed; Agent registers TERMINATE_EM_AGENT and TERMINATE_EM_SERVICE, Service registers/broadcasts TERMINATE_EM_SERVICE; Service handles WM_QUERYENDSESSION/WM_ENDSESSION and self-terminates after broadcast. Current hashes have no WTS/SCM imports. | Resolve remaining Agent messages/events, FindWindow target identity, peer launch/monitor/restart ownership, heartbeat and race/failure behavior | P1 |
| Browser host / init | Embedded JavaScript postMessage bridge and init endpoint are recovered | Identify actual host control/process and CLSID/ProgID; prove how the Almas page loads the bridge; Origin/Referer validation and browser compatibility | P1 |
| AutoSave timer / .easz recovery | OnTmrAutoSave assigns OnControlerNotify to a TTimer; HKCU\\Software\\Emwat\\Dynamic Config exposes AutoSaveInterval (seconds converted to ms, min 10,000 ms); callback invokes CostumizeRecAndCC, Get_Content(-1), builds .easd/.easz paths and calls euUnArchive/T7zInArchive extraction. A hardcoded 15-character input-archive password argument is present at VA 0x456EE0 (literal redacted) | Resolve -1 semantics and exact archive entry/path mapping; locate the actual .easz writer and output encryption contract; validate a synthetic archive | P1 |
| Printer management / GAM | Explicit BGPrint path reaches Word COM Application.PrintOutOld; timer callback CostumizeRecAndCC also calls Document.PrintOutOld slot +0x2BC three times; BeforePrint and print-handler/controller classes are identified; spooler calls enumerate queues/jobs; GAM OEM stack mapped | Determine whether timer calls produce separate jobs; identify +0x3F0 COM call and 15 Variant args; trace print-thread ownership, active/default queue and GAM hand-off; resolve .zan/final output and installer actions | P1 |
| ImageGear / scanner | GEAR API imports, many callsites, TScanCommand state transitions, IIPEditor and some page/handle semantics; Linux SANE backend exists | Exact GEAR version/constants, remaining ABI arguments, frame/page lifecycle, cancellation/error mapping, metadata, save/load semantics and hardware comparison | P2 |
| ImageEn / image tools | DFM forms and ImageEn/WIA/TWAIN dependencies identified | Handler bodies, acquisition source selection, multipage document model, undo/redo, crop/rotate/flip semantics, insert/remove/reorder pages, TIFF/JPEG export and callback/result contract | P2 |
| Word print options | DFM reveals recipients/CC, page-range and copy-count controls | Event-handler logic, page-range parser, saved settings storage, recipient/CC copy rules, mapping to printer queue and actual output | P2 |
| Excel connector | Excel Automation wrappers and TEditExcelWorkBook class are identified | Method payload schema, workbook/sheet/range operations, formulas/styles, save/return behavior, error semantics and real fixture | P2 |
| Installer / updater / COM | PE imports/resources, some Registry keys and COM infrastructure are documented | Installer custom actions, service registration/config defaults, uninstall/upgrade rollback, actual Office CLSID/ProgID/version, 32-bit registry view, browser host registration | P2 |
| Database / external storage | No direct common SQL driver imports found in the inspected PE import report | Do not assume a database exists. Search configs, dynamically loaded modules, file formats and callsites only if a concrete storage read/write path appears | P3 |

## Ordered work packages

### P0-A — Separate Word close, periodic recovery, and HTTP response contracts

These are related workflows, but current evidence does **not** establish them as one callback chain:

1. **Word event sink:** trace callback registration and COM event interface/slot identity. The TD32 label `WordAppDocumentBeforeSave` conflicts with diagnostic text `Document.OnBeforeClose Called.` in the routine. `WordAppDocumentBeforeClose` is a separate procedure; its active registration is not yet proven. Do not assign a COM DISPID from the TD32 symbol alone.
2. **Close decision:** trace the registered callback's Yes/No/Cancel path, Word Close wrapper arguments and `Set_Saved` calls. Determine which bytes Word/EMWAT considers saved for each choice.
3. **Periodic recovery:** separately trace `OnControlerNotify` (timer callback, minimum 10 seconds), `CostumizeRecAndCC`, `Get_Content(-1)`, `.easd`/`.easz` path construction and the 7-Zip writer. The meaning of `-1` remains unknown. This path is not the final HTTP response writer.
4. **HTTP response:** separately trace the long-lived invoke wait/release condition into the already mapped `LoadDocument` response branch, which assigns `AResponseInfo.ContentText` and calls `TIdHTTPResponseInfo.WriteContent`.
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
4. Resolve password/encryption flags from the writer and a controlled fixture; euGetAutoSavePass is not a proven archive password source.
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
- Word print options (WORD-PRINT-OPTION-DFM.md)
- GAM virtual printer (GAM-VIRTUAL-PRINTER-REVERSE-ENGINEERING.md)
- Printer compatibility plan (PRINTER-COMPATIBILITY-PLAN.md)

## Immediate next execution order

1. Trace the 15 Word PrintOut arguments, print-thread handoff, and GAM output file/consumer contract.
2. In parallel, resolve the pending HTTP invoke release condition and close-to-response correlation.
3. Trace the timer-driven CostumizeRecAndCC → Document.PrintOutOld → BeforePrint path and determine whether it generates GAM jobs.
4. Trace the actual .easz writer; current evidence proves extraction and a hardcoded input-password argument, but not archive creation or output encryption.
5. Complete WordConfig signature/twin/image field coverage.
6. Continue Agent lifecycle, then ImageEn handlers, Excel and installer/updater details.
