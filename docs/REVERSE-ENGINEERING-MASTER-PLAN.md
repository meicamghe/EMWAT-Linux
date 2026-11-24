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
| HTTP bridge / XML parser | Indy server, loopback port 1984, init/heartbeat/invoke captures, parser envelope and service-to-BPL dispatch have substantial static/runtime evidence | Complete error responses, all method classes and parameter schemas, request bounds/version behavior, Origin/token/session checks, additional endpoints, exact response behavior for non-Word methods | P0 |
| Word document lifecycle | LoadDocument, close-driven wait, registered BeforeSave callback, controller notification and Get_Content wrapper have been traced | Reconcile all branches and event ordering; resolve -1 argument/buffer semantics; exact Yes/No/Cancel outcomes; connect content serialization to HTTP response and observed Almas registration | P0 |
| WordConfig / fields | XML field model, URL-encoded/Base64 decoding, DOCPROPERTY token parsing, several field/image/recipient paths and Writer inventory exist | Full semantic mapping of the approximately 180-field catalog; single/twin fields; signature signData separators/concatenation; image storage/layout; permission/settings/RequestedTypes; real sanitized template parity | P0 |
| Agent ↔ Service | Imports, HTTP heartbeat, WTS notifications, service UI messaging and parts of the Service handler are known | Agent state machine, heartbeat interval/timeouts, launch/restart/stop policy, session-change behavior, process ownership, IPC/window-message contract, failure recovery | P1 |
| Browser host / init | Embedded JavaScript postMessage bridge and init endpoint are recovered | Identify actual host control/process and CLSID/ProgID; prove how the Almas page loads the bridge; Origin/Referer validation and browser compatibility | P1 |
| .easz recovery archive | SevenZip interfaces and writer path, .easd entry naming and file creation have static evidence | Synthetic archive fixture; password source/derivation/encoding; actual encryption flags/header; entry metadata and extraction error behavior; cross-tool interoperability | P1 |
| Printer management / GAM | Windows spooler imports and GetPrinterIndex/SetPrinterIndex names; GAM OEM driver/monitor/server stack, queue defaults and CLI examples | Exact callers, API levels/flags, stable ordering/index base/persistence; actual job submission; InstallShield custom actions/registry/service setup; .zan and output hand-off; collision/compression enums | P1 |
| ImageGear / scanner | GEAR API imports, many callsites, TScanCommand state transitions, IIPEditor and some page/handle semantics; Linux SANE backend exists | Exact GEAR version/constants, remaining ABI arguments, frame/page lifecycle, cancellation/error mapping, metadata, save/load semantics and hardware comparison | P2 |
| ImageEn / image tools | DFM forms and ImageEn/WIA/TWAIN dependencies identified | Handler bodies, acquisition source selection, multipage document model, undo/redo, crop/rotate/flip semantics, insert/remove/reorder pages, TIFF/JPEG export and callback/result contract | P2 |
| Word print options | DFM reveals recipients/CC, page-range and copy-count controls | Event-handler logic, page-range parser, saved settings storage, recipient/CC copy rules, mapping to printer queue and actual output | P2 |
| Excel connector | Excel Automation wrappers and TEditExcelWorkBook class are identified | Method payload schema, workbook/sheet/range operations, formulas/styles, save/return behavior, error semantics and real fixture | P2 |
| Installer / updater / COM | PE imports/resources, some Registry keys and COM infrastructure are documented | Installer custom actions, service registration/config defaults, uninstall/upgrade rollback, actual Office CLSID/ProgID/version, 32-bit registry view, browser host registration | P2 |
| Database / external storage | No direct common SQL driver imports found in the inspected PE import report | Do not assume a database exists. Search configs, dynamically loaded modules, file formats and callsites only if a concrete storage read/write path appears | P3 |

## Ordered work packages

### P0-A — Close the Word response contract

1. Build a single cross-reference from the registered BeforeSave callback, OnControlerNotify, TWordDocument.Get_Content, the HTTP response writer and the browser postMessage response.
2. Resolve the Get_Content(-1) argument and output buffer using the exact interface signature and callers.
3. Capture sanitized, synthetic Yes / No / Cancel cases and compare request completion, response XML, returned document bytes and Almas-side outcome.
4. Keep the product's observed behavior (closing the editor registers/applies the document even when Save was not manually pressed) separate from assumptions about whether Word silently saved first.
5. Add tests only for behaviors established by binary evidence or a controlled fixture. Keep unknown Cancel/Discard envelopes injected rather than guessed.

**Exit criterion:** all three close choices have a documented state transition and response contract, or an explicit, bounded unknown with the missing fixture identified.

### P0-B — Complete WordConfig semantics

1. Generate a metadata-only inventory of all field identifiers and their declared encoding/type attributes.
2. Trace native field lookup/population for text, image, signature, recipient, CC, QR/barcode and option fields.
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

1. Create a synthetic Windows recovery archive containing a non-sensitive generated DOC/DOCX only.
2. Record archive signature, entries, compression/encryption flags, sizes, password prompts and failure behavior.
3. Trace the password callback to its actual source and encoding; the existence of CryptoGetTextPassword2 alone does not prove encryption is enabled.
4. Verify Linux read/write interoperability independently; keep the existing Linux recovery manifest format separate.

**Exit criterion:** at least one known-good synthetic archive can be inspected and opened with a documented password/encryption contract, or support remains explicitly out of scope.

### P1-C — Printer pipeline and GAM package

1. Hash and compare the exact EmwatMethods.bpl against repository analysis-input/EmwatMethods.bpl1; record PE version, architecture and timestamp before merging address-level traces.
2. Trace every GetPrinterIndex / SetPrinterIndex caller and the underlying EnumPrinters / GetPrinter levels, flags, fields and ordering.
3. Find actual job-submission callsites separately from printer enumeration/configuration.
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
- Office COM analysis (OFFICE-COM-ANALYSIS.md)
- Import table analysis (IMPORT-TABLE-ANALYSIS.md)
- Resource analysis (RESOURCE-ANALYSIS.md)
- Windows .easz archive (EASZ-ARCHIVE-FORMAT.md)
- Scanner interface (SCANNER-INTERFACE-ANALYSIS.md)
- Image call graph (IMAGE-CALL-GRAPH.md)
- GEAR API calls (GEAR-API-CALLS.md)
- Word print options (WORD-PRINT-OPTION-DFM.md)
- GAM virtual printer (GAM-VIRTUAL-PRINTER-REVERSE-ENGINEERING.md)
- Printer compatibility plan (PRINTER-COMPATIBILITY-PLAN.md)

## Immediate next execution order

1. Finish the printer callsite and output hand-off trace already in progress.
2. In parallel, resolve Get_Content(-1) and the HTTP close-response serialization path.
3. Build the sanitized WordConfig field coverage report, focusing on signatures and image fields.
4. Start Agent lifecycle and .easz fixture investigations as independent tracks.
5. Only then expand into ImageEn handlers, Excel, and installer/updater details.
