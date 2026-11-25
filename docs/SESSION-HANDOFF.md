Warning: truncated output (original token count: 41582)
Total output lines: 1308

## 2026 11 18 — scanner input validation test

- Added hardware-independent regression checks that `SaneScannerBackend.get_capabilities("")` and `scan_one("")` reject an empty device identifier before entering SANE.
- Native image core workflow `44244437647` completed successfully on `ed811a14f9d151a8a386c67b80b26b3d155f5c24`: build-test and ASan/UBSan sanitizer-test both passed, including their test steps.
- Included in draft PR #2; this does not claim validation against a physical scanner, ADF, or duplex device.

## 2026-11-18 — opt-in recovery retention implementation (PR #2)

- Added `recovery_retention.py` with explicit age and/or snapshot-count limits. It keeps the newest valid snapshots, removes expired/excess sessions only when explicitly invoked, and returns removed session IDs.
- Exposed the policy through `RecoverySnapshotService.apply_retention()`; there is no default policy, background timer, or implicit deletion. At least one positive limit is required and count limits cannot be zero.
- Added unit tests for policy validation, age pruning, newest-N retention, service integration, and no-op behavior. Invalid/unverifiable entries are not enumerated by the store and are not deleted by this policy.
- Python bridge CI passed on the final PR head `f1a8260589d6f5fbd8fda0a2e45bd29c7741ff4e`: runs `44244362768` and `44244353561` both completed successfully.
- Draft PR: https://github.com/meicamghe/EMWAT-Linux/pull/2. This is not merged to main. Retention is not encryption; encryption-at-rest, user-facing policy controls, and a real Recovery UI remain open.

## 2026-11-18 — CI verification and recovery trigger coverage

- Native image core run `44240525477` completed successfully on `ecf4fa8a8784b2403272ecd79186fd073e1a8e1b`: both `build-test` and `sanitizer-test` passed, including the ASan/UBSan test step.
- Updated `.github/workflows/libreoffice-integration.yml` so changes to `recovery_store.py` and `writer_inspector.py` trigger the real LibreOffice UNO integration job on both push and pull request. This closes a CI coverage gap for recovery-store changes.
- The UNO run for this workflow update, `44240952654`, completed successfully: LibreOffice Writer/Python UNO installation, runtime verification, and adapter unit plus real UNO roundtrip test step all passed.

## 2026-11-18 — additional parallel work

- Native scanner scope documented against actual SANE implementation: one 8-bit Gray/RGB frame, optional mode/source/DPI, bounded 1 GiB frame size, and explicit unverified gaps (ADF/duplex/multi-frame, interactive cancellation, physical scanner matrix).
- Removed duplicate `libsane-dev` entry from `.github/workflows/native-core.yml`; existing native build and ASan/UBSan jobs will validate the workflow change.
- Python bridge CI for the latest property-order assertion passed: run `44237865553`, 147 tests, 145 passed, 2 optional UNO skips.
- Recovery UI, at-rest encryption, executable retention, semantic field mapping, Cancel/Discard wire contract and Almas E2E remain open.

## 2026-11-18 — parallel implementation checkpoint

- Added toolkit-neutral `RecoveryPickerController`; it exposes safe metadata, delegates restore to the hardened store using a UI-selected destination, and requires explicit confirmation before destructive discard. It is not a graphical widget or HTTP endpoint.
- Added `audit_writer_property_alignment()` to report exact case-sensitive Word custom-property ↔ Writer custom-property name intersections and unmatched names, plus Writer DocInfo.Custom field references. It preserves Word property index order and makes no COM/UNO order-equivalence claim.
- Python bridge CI run `44237776415` passed on `448090b0c7625bac5cfb086fcdf10b0ef1f17a19`: 147 tests, 145 passed, 2 optional LibreOffice tests skipped.
- Still open: actual GTK/Qt picker, verified semantic/template mapping, Cancel/Discard wire response evidence, encrypted recovery/retention, native scanner hardware validation, and Almas end-to-end.

# EMWAT-Linux — Project Handoff

## Current continuation checkpoint — 2026-11-25

- Reference installation: `/home/m/.wine-emwat`, confirmed `wine-11.0`; the installed `IGLZW32S.DLL` SHA-256 is `5cbb9352d71b74836c99429a1eaf39f77db753bfae6d5307199aaffbdeeee6cd`. This pass used static disassembly only and did not launch EMWAT or modify the prefix.
- Read-only SSH inventory confirmed `EmwatAgent.exe`, `EmwatService.exe`, `EmwatMethods.bpl`, and `GAMPrinterSetup.exe` are installed under `/home/m/.wine-emwat/drive_c/ProgramData/Gamelectronics/Emwat Service/`; no Wine/EMWAT process was running during the check. A prefix search found no `WINWORD.EXE`, so do not assume the full Word automation workflow can currently run in this Wine prefix. Existing printer captures and support files are present in `/home/m/gam-printer-analysis`, `/home/m/emwat-printer-capture`, and `/home/m/emwat-dlls`. No binaries were copied into the repository.
- At the start of this continuation, `feature/recovery-retention-policy` was at `f55410b7abc8b02bd27b8ed9750defedfafdf34c`; the evidence and probe harness updates below are being committed on that branch. The full local Python suite with real LibreOffice integration enabled passed **326/326 tests**; the focused `word_fields` suite passed **17/17**. GitHub Actions had no run for the preceding head; no remote CI pass is claimed.
- Wine 11 runtime probe of the hash-matched `EmwatMethods.bpl` confirmed direct Base64 decoder results for valid groups, invalid alphabet/length, and permissive `QQ=A` padding. The probe used `DONT_RESOLVE_DLL_REFERENCES` and a disposable prefix, which was removed; hashes for the original `.wine-emwat` binaries were unchanged. The probe did not exercise wrapper `0x004738CC`, pre-conversion `0x00455108`, Word or Almas. See `docs/WORD-FIELD-VALUE-DECODING.md` and `tools/reverse_engineering/probe_emwat_base64_decoder.c`.
- Follow-up disassembly confirms `0x00455108` converts a NUL-terminated WideString to AnsiString using caller code page 0 (ACP in the Base64 path), flags `0x270`, a queried size `N`, then output capacity `N-1`; it ignores the second `WideCharToMultiByte` return. A separate disposable Wine 11 WinAPI probe confirmed that this short capacity returns 0 / error 122 while still writing the first converted byte for tested ASCII, ACP-representable, and unrepresentable characters. This does not dynamically invoke the BPL helper. The temporary prefix and harness were removed; the original installed BPL hash still matches the analysis snapshot. See `docs/WORD-FIELD-VALUE-DECODING.md`.
- Static and runtime traces confirm URL `+` maps to a space, and the inner Base64 decoder requires a multiple-of-four length and uses a 256-byte translation table. The full Base64 wrapper behavior under Wine, malformed percent escapes, exact Unicode/whitespace handling through the complete helper chain, and semantic Writer field mapping remain unresolved.
- Read-only SSH through `linux-ubuntu` confirmed Wine `11.0`; installed `EmwatMethods.bpl` SHA-256 `6ff7d262f46ab009e3eecf20fca40cd41ec8ad937adf7bbfe2f6eddd56aaea2d` matches the checked-in snapshot, and installed `IGLZW32S.DLL` matches its documented hash. The original prefix was not modified.
- New static ABI facts and evidence are in `docs/IMAGEGEAR-LZW-GIF-REVERSE-ENGINEERING.md`: `GearExtInfoGet/Set` each clean two x86 stack slots; `GearExtInfoGet` selector 14 returns `TIF_Proc_LZW_Comp` when mode state is 1; the TIFF routine cleans `0x4c` bytes (19 x86 stack slots) and uses host allocation/free/error/finalization callbacks.
- **Next priority:** continue the product-critical P0-A/P0-B work in `REVERSE-ENGINEERING-MASTER-PLAN.md`: obtain a sanitized matching Almas/Word fixture so semantic mapping and close-response behavior can be verified, then exercise the full Base64 helper path with harmless controlled inputs. The GitHub text reports and installer archive are not that fixture. Preserve the existing loopback → real UNO integration regression while doing so.
- ImageGear TIFF/GIF ABI completion remains useful independent work, but it is lower priority than the Almas/Writer letter path. Do not invoke unverified DLL entry points; runtime probes must use a disposable isolated Wine prefix (or a protected copy of the valuable prefix) and harmless synthetic fixtures. Wine 9 must not be introduced.
- For printing, trace GAM's TIFF artifact path and queue/job correlation before adding a CUPS/IPP backend. Keep the Windows spooler and GAM virtual printer as separate analysis components.
- Keep these boundaries explicit: no typed TIF wrapper, ImageGear runtime parity, full scanner/ADF/duplex, CUPS printing, or verified end-to-end GAM workflow is claimed. Wine 9 must not be introduced.
- Printer checkpoint: SSH inspection confirms host CUPS is active but has no configured destinations/default queue. The existing Wine trace records `libcups.so.2` loading, zero enumerated printers, and `OpenPrinter2W(L"GAMPrinter", ...)` failing with error 1801. A separate x64 installer trace reports missing Wine x64 spool-driver support files; this does not establish x86 setup behavior. No printer configuration was changed, and the complete findings are in [GAM-VIRTUAL-PRINTER-REVERSE-ENGINEERING.md](GAM-VIRTUAL-PRINTER-REVERSE-ENGINEERING.md).

## Latest main-branch implementation — 2026-11-17

- POST bridge requests now require exactly one non-empty `invoke` query parameter before the request body is read or a method is dispatched. Duplicate/missing/invalid query shapes return HTTP 400.
- The hardened `RecoverySnapshotStore` has been ported to main. It validates manifest metadata, SHA-256, DOC/CFB vs DOCX container extension, symlink boundaries and the 128 MiB default limit. Restore uses a private temporary file, fsync and no-overwrite atomic publication.
- `LibreOfficeAdapter` starts a per-document periodic recovery worker (default 10 seconds), serializes snapshotting with document operations, retries transient failures, stops the worker on confirmed close, and removes the recovery session only after successful final export. A failed session preserves its last valid snapshot.
- Python bridge CI on commit `a92822d1aa83edba4e811ebebe1edd111e7dfab2` passed **131 tests, 2 skipped** (run `44081916126`). The corresponding LibreOffice UNO workflow also passed **13 tests** (run `44081916143`).
- Recovery UI/picker and retention policy are not yet implemented. The local store is not encrypted and is not compatible with the Windows password-protected `.easz` archive. Do not claim Almas end-to-end or full 180-field mapping.


Last reviewed: 2026-11-16

This is the concise continuity entry point for future sessions. Detailed reverse-engineering evidence remains in the linked analysis documents.

## Latest verified implementation progress — 2026-11-16

- **Saved-slot correction:** generated Word wrappers map Get_Saved to _Document +0xD4 and Set_Saved to +0xD8. WordAppDocumentBeforeSave uses +0xD8, so do not describe that instruction as reading Saved; its assigned OleVariant value and prompt condition remain unresolved. OnControlerNotify uses +0xDC, mapped to TWordDocument.Get_Content (0x0042BDF8); the supplied -1 argument remains unexplained. The same handler logs AutoSave execution, builds .easd/.easz paths and calls euUnArchive, confirming a local archive/recovery path distinct from Almas registration.

- Real LibreOffice UNO adapter added: per-document process/profile/socket isolation; DOC/CFB and DOCX input detection; document modification/save/close listeners; close-time Word 97 snapshot.
- writer_properties.py adds a strict custom-property update operation: it requires an exact existing property name, does not create unknown properties, and never reads the current value. The real UNO fixture now imports an actual Word DOCPROPERTY field and matching custom property, updates the property, refreshes Writer fields, verifies the displayed document text changes, and then closes/exports.
- Real UNO integration workflow run 43810592239 passed 8/8 tests, including a generated DOCX opened and closed through LibreOffice, a bookmark inspected through UNO, and export as a legacy Word CFB file.
- Latest Python bridge run 43815578467 passed 98 tests with one optional UNO skip (99 total); LibreOffice UNO runs 43815561042 and 43815592590 both passed 8/8, including adapter-level custom-property batch update, DOCPROPERTY refresh, and DOC/CFB export. The separate LibreOffice UNO run 43813378877 passed 8/8 tests, including the existing-property update path and DOCX → Writer → DOC/CFB close/export.
- application.py now has create_libreoffice_bridge_server to compose EditWordDocument → service → office adapter. Cancellation response remains an injected policy because the Windows cancellation envelope is not yet known.
- word_fields.py decodes each field according to its own encryption attribute, exposes parsed single/twin identifiers, and includes extract_docproperty_identifier() matching native DOCPROPERTY token parsing (case-sensitive, first double-space, 255-character bound). The observed dagger delimiter is U+2020; this is identifier parsing only, not a template-field mapping. writer_inspector.py and LibreOfficeAdapter.inspect_document inventory Writer bookmarks, named ranges, sections, tables, frames, graphic objects, indexes, and text-field metadata without reading letter content. URL-encoded text and Base64 image values are decoded independently; plain text remains unchanged. External signData bindings remain opaque until separator/concater semantics are confirmed.
- The latest custom-property pipeline (run 43813303321, artifact 14201306994) confirms dictionary helper use in the FillImageField/FillPrintDocFields paths; ShowRecAndCcOptionForm is called from GetDocFieldName, and FindWindowExtd is reached from FillImageField. Its next revision is queued with additional traces for shared field lookup and XML-config population. Their full business semantics and the 180-field mapping remain unresolved.
- Not yet complete: mapping the 180 EMWAT fields into the real Writer template; signer/image insertion; applying permissions/settings; close-cancel behavior; and end-to-end registration with Almas Gam.
- Native SetFieldValue constants are confirmed: urlencoded and base64. FindFieldInActivefields recognizes DOCPROPERTY field codes; Hidden_Customizable conditionally enters SilentSaveEmwatDoc during GetDocFieldName. AddCustomDocPropertiesToDic enumerates Word CustomDocumentProperties and parses twin names. Native URL-decoder behavior is now matched: + becomes space and %2B becomes literal +. Next: trace the Base64 byte-to-Unicode helper at 0x004738CC, resolve the indirect/VMT call into AddXmlWordConfigFieldsToDic, and continue correlating DOCPROPERTY fields with Writer DocInfo.Custom fields. In parallel, continue the close/response chain and validate mappings against an anonymized real DOC/CFB fixture. Do not claim template compatibility until this passes.

## Product goal — fixed

Rebuild EMWAT as a **native Linux application** while preserving the real Windows product's workflows. Running the Windows EMWAT build under Wine is not the target product.

The confirmed real-world workflow is a local desktop bridge for the Almas Gam web-based office automation system: data and letter templates are prepared in the web system, EMWAT opens Word for editing, and the resulting document is returned to the same system. Some letters are image-only, so scanning and image-document workflows remain in scope.

## Confirmed user observations and constraints

- **User-observed product requirement:** the user tested that closing the document applies/registers changes whether or not Save was pressed. Reproduce this behavior in Linux. The exact internal event, file extraction method and transport remain to be identified.
- The user has supplied the original Windows installer/extracted files for analysis. The historical extraction location was `D:\EmwatInstaller`.
- The user stated that the extracted EMWAT files contain no customer information. Still inspect any future traces, sample letters, cookies, tokens, and logs before publishing them.
- The original Windows binaries examined are PE32/x86; this is a fact about the analyzed binaries, not a reason to make the Linux implementation 32-bit-only.
- Do not assume the database engine, browser engine, complete API, authentication mechanism, or wire format until evidence confirms them.

## Confirmed static-analysis findings

- `EmwatService.exe` hosts a local HTTP service based on Indy components.
- A default local port of `1984` appears in strings; the Agent has a heartbeat string to `http://127.0.0.1:1984/?heartbeat`.
- A JavaScript bridge uses `postMessage` and HTTP POST to a local `127.0.0.1:<port>?invoke=<random>` endpoint; response text is relayed to the parent window.
- Word/Excel automation through COM/OLE is supported by strong type-information and symbol evidence.
- Word connector/type structures include request and response XML models, fields, settings, styles, status and return-type metadata.
- Word lifecycle symbols include autosave, silent-save, before-close and before-save handlers. These support the existence of managed save/close behavior but do not alone establish exact wire timing.
- Image and scan UI structures have been decoded, including scan preview, image tools and simple image editor forms.
- ImageGear and ImageEn paths have been analyzed, including crop, rotate, flip, save, scan and multi-page handling. Do not infer enum meanings or scanner ABI from names alone.
- The exact database, full invoke API, complete payload contract, browser implementation and several runtime behaviors remain unresolved.

## Native Linux architecture principles

- Do not use Wine as a final runtime dependency.
- Keep the browser bridge, local service, document engine, and scan/image subsystem as separate components.
- Bind the local service to loopback only; validate origins/tokens, payload sizes, file paths, timeouts and lifecycle behavior.
- Do not invent an API that merely resembles EMWAT. Extract the original request/response contract first.
- LibreOffice Writer is the candidate document application/compatibility bridge, but real templates and field behavior must be tested.
- Preserve image-only letters, scanning, multipage documents, image edits and print-related workflows.
- Do not select a local database without evidence that one is needed and what data it must own.
- Never publish customer letters, credentials, cookies, private endpoints or unredacted runtime traces.

## Current evidence and technical documents

Start with these documents; do not repeat their completed work without new evidence:

- `docs/PROJECT-STATUS.md` — overall findings, confidence levels and next actions
- `docs/PRODUCT-WORKFLOW-ANALYSIS.md` — confirmed product workflow and revised priorities
- `docs/HTTP-LOCAL-API-ANALYSIS.md` — local HTTP service and JavaScript bridge
- `docs/WORD-DOCUMENT-PROTOCOL-ANALYSIS.md` — Word connector, XML structures and lifecycle
- `docs/OFFICE-COM-ANALYSIS.md` — Office Automation/COM
- `docs/IMPORT-TABLE-ANALYSIS.md` — PE imports and dependencies
- `docs/RESOURCE-ANALYSIS.md` — COM and PE resources
- `docs/SCAN-PREVIEW-DFM.md`, `docs/IMAGE-TOOLS-DFM.md`, `docs/SIMPLE-IMAGE-EDITOR-DFM.md` — decoded image/scan forms
- `docs/GEAR-API-CALLS.md`, `docs/IMAGE-CALL-GRAPH.md`, `docs/SCANNER-INTERFACE-ANALYSIS.md` — image/scanner call analysis

## Immediate next steps — in order (updated 2026-11-14)

1. **Finish the remaining XML method/serialization mapping.** The service parser's `TMethodInfo.Params` and BPL `TEmwatMethod.Invoke` use `TDictionary<AnsiString, AnsiString>`. Service slot `+0x0C` reaches shared wrapper `0x0046C9E0), which calls `TEmwatMethod.Invoke` (`0x0046C82C`) and then the subclass slot `+0x10`. Inside Invoke, local `[ebp-4]` is a `TXMLEmwatType` interface; its `+0xB0` thunk `0x0044B70…31582 tokens truncated…t obviously match the TD32 signatures. The archive direction and exact argument types remain unresolved. Next inspect target method bodies and the wrapper/factory.
- Expanded archive workflow run `43869599848` was queued for those method-body traces at the last check.


### Invoke bridge and XML version contract
- Service artifact `14226099734` confirms the embedded init script POSTs `message.data` to `http://127.0.0.1:$V{myport}?invoke=<random nonce>` and relays `responseText` to the parent frame.
- Service strings and parser traces confirm root `emwat`, attribute `version`, exact numeric version `1`, child `method`, attribute `class`, child `param`, and attribute `name`.
- `0x0047E0EC` is BPL package load; `0x0047E2D4` is package unload. They bracket `ParseMethod`; neither is the concrete method dispatcher.
- The exact request schema is updated in `docs/EDITWORD-REQUEST-SCHEMA.md`; HTTP bridge details are in `docs/HTTP-LOCAL-API-ANALYSIS.md`.


- Artifact `14226742624` confirms `0x0040414C` is the `rtl230.bpl!TStringList.$bctr` import thunk. Both objects passed into `euUnArchive` are TStringList instances. First list receives `TWordViwer+0xA0`; second receives the direction-normalized `TWordViwer+0x80` path with `.easd` appended. The pairwise list loop passes entries to the `T7zOutArchive` interface, then sends the `.easz` path through slot `+0x18`.


### Archive path resolved (Run 148)
- Artifact `14227611377` establishes the output writer path and SevenZip wrapper, but does not prove that the resulting archive is encrypted.
- Interface `+0x10` → `T7zOutArchive.AddFiles` (`0x453F34`): first TStringList value is the source file path (`TWordViwer+0xA0`); second is the archive entry name (base path + `.easd`).
- Interface `+0x18` → `T7zOutArchive.SaveToStream` (`0x454668`): saves to base path + `.easz`.
- Interface `+0x28` → `0x4547E8`: mapped as the progress-callback method. The earlier inference that its input was definitively the writer password is withdrawn. `T7zOutArchive.SetPassword` at `0x4547DC` is a no-op stub. No confirmed writer password value/provider is established.
- Remaining: resolve the output stream and callback semantics, determine actual runtime encryption flags/password source, and capture a synthetic runtime archive if possible. Do not claim encryption or interoperability is validated.


### Confirmed service-to-BPL dispatch correction
- The prior caution that the `TEmwatMethod.Invoke` helper was not the runtime dispatcher is superseded by the public wrapper distinction.
- Service parser extracts `method@class` and `param@name`, resolves `GetClass("T"+className)`, constructs the class, and calls VMT slot `+0x0C`.
- `TEmwatMethod` VMT slot `+0x0C` → `0x0046C9E0` shared wrapper; wrapper calls inner XML/dictionary helper `0x0046C82C` then subclass `PerformMethod` at VMT slot `+0x10`.
- The service-side class lookup and dispatch chain is fully documented in `docs/EMWAT-SERVICE-EXECUTABLE-ANALYSIS.md`; the remaining response serialization and close-time commit link are still open.


- Run 5 artifact `14227002967` confirms `0x004041BC` is the `rtl230.bpl!TFileStream.$bctr(UnicodeString, Word)` thunk. `SaveToStream` constructs the file stream from `.easz` using `0xFF00` (`fmCreate`) and passes it to `SetCompleted` (`0x004546C4`). Thus `.easz` is a real file output, created/truncated by the archive path.


### Word event lifecycle targets
- `OnTmrAutoSave` (`0x004B8A84`) registers WordApp callbacks: BeforeSave `0x004CD154`, NewDocument `0x004CD54C`, WindowActivate `0x004CD9C0`, BeforePrintBGPrint `0x004CE030`/`0x004D00AC`.
- `WordAppDocumentBeforeSave` can set Cancel=-1 when viewer state is not ready and can show a three-choice dialog for an unsaved document. One choice cancels. Do not assume this is the Almas commit event.
- `WordAppDocumentBeforeClose` (`0x004CCBBC`) calls `0x004BCA88`; `SilentSaveEmwatDoc` (`0x004D23D8`) builds two TStringLists and calls `0x004AEBBC`. These are key next targets.
- A complete-range rerun is in progress to trace OnTmrAutoSave, OnControlerNotify, BeforeClose, BeforeSave, SilentSaveEmwatDoc, and the two helpers. See `docs/WORD-LIFECYCLE-STATIC-TRACE.md` Run 150.


- `LoadDocument` calls `OnTmrAutoSave` with the document path at `0x004B7A58`; `OnTmrAutoSave` stores it at `TWordViwer+0xA0` (`0x004B8AE8`). `OnControlerNotify` later reads that field as the source path passed to `T7zOutArchive.AddFiles`. `LoadDocument` creates a `TFileStream` for the same path and writes document data. This links the file generated during Word document setup to the `.easd` archive entry inside `.easz`. Viewer field `+0x80` (base path) still needs mapping.


### EditWordDocument request/response path
- Concrete method `TEditWordDocument.PerformMethod` reads `wordConfig` (required), `wordBody`, `letterImages`, `signData`; missing `wordConfig` throws the explicit XML-invalid error.
- It wraps `TWordViwer.LoadDocument` in `CoInitialize`/`CoUninitialize`, passes the `TEmwatInvokeParam` pointer and output string, stores the returned method result, and sets `bResultSet=1`.
- `LoadDocument` extracts `DocFileName` from `wordBody`, writes document data to a local `TFileStream(fmCreate)`, parses `wordConfig` XML, then calls `OnTmrAutoSave` with that file path. The path is stored in viewer `+0xA0` and later packaged as `.easd` inside `.easz`.
- Next priority: determine how the returned string and `bResultSet` become the actual HTTP response body, and trace the full `wordConfig`/`letterImages`/`signData` handling.


## Accepted product decisions — 2026-11-18 (do not reopen implicitly)

- Linux only. Do not develop a new Windows app, UI, or installer; Windows is an analysis/compatibility reference only.
- GTK 4 + Python/PyGObject is selected for a small, free/open-source Linux control UI. Do not use Qt/PySide unless the owner explicitly changes the decision.
- LibreOffice Writer via UNO is the document editor. GTK is only for EMWAT status, settings, recovery, scanner entry points, and diagnostics.
- Main product workflow: Almas request/document → local EMWAT protocol bridge → LibreOffice Writer editing → final document returned to Almas in the verified response format.
- Keep bridge, document coordinator, UNO adapter, recovery, and scanner core independent from GTK; core and tests must run headlessly.
- No paid toolkit, subscription, or mandatory cloud service. Check license obligations for all distributed dependencies.
- Source of truth: `docs/LINUX-PRODUCT-DECISIONS.md`; also reflected in README, PROJECT-STATUS, Ubuntu installation guide, and recovery picker UX.
- Next implementation priority remains real Almas/browser wire-contract evidence and full Writer document roundtrip, not GTK screen proliferation.


## EMWAT Linux — Writer close evidence and CI handoff (2026-11-20)

- Latest branch checkpoint: `79c017e757485dbd5fb19b7a7e1fd13beb05353c`; PR #2 remains open/Draft/unmerged.
- Added `docs/WRITER-CLOSE-DISCARD-INVESTIGATION.md`: UNO `queryClosing`/terminal-close semantics are documented, but interactive Writer Save / Don't Save / Cancel ordering remains unverified. Do not infer discard from `notifyClosed` or `disposing`.
- Python CI run `44784556864`: success.
- LibreOffice UNO CI run `44784556817`: success; 17 tests passed, including real UNO open/close/export and EditWord response-handler integration.
- Native CI run `44784556764`: package lifecycle and normal build/CTest/staged install passed; ASan/UBSan was still running at the checkpoint.
- Next: poll Native sanitizer job, then record final combined CI status. Continue the Writer visible-UI Save / Don't Save / Cancel test design. Do not ship a daemon/desktop entrypoint or claim production readiness until Origin allowlists, verified close response policy, lifecycle supervision, secure recovery key custody and Almas wire fixtures are resolved.


## 2026-11-20 — parallel Word/Writer evidence and close acceptance work

- Added `python/src/emwat_linux/word_writer_evidence.py`: metadata-only summary of WordConfig field IDs, declared MIME/encoding, external parameter IDs, duplicates, settings, optional attributes and requested types, alongside Writer structural and custom-property names. It excludes field values, body text, image bytes and property values.
- Exposed `LibreOfficeAdapter.audit_word_writer_evidence(handle, config)` under the document snapshot lock. It is read-only; no inferred mapping is applied.
- Added tests for the report and adapter entry point. Initial report-only Python CI run `44796731919` passed 219 tests (217 passed, 2 optional skips). Newer adapter integration/test commit `4c571a74` has fresh CI runs queued.
- Added `docs/WORD-WRITER-EVIDENCE-REPORT.md` and `docs/WRITER-VISIBLE-CLOSE-ACCEPTANCE.md`. The latter defines visible Writer Save, Don't Save, Cancel and retry acceptance, including output-marker checks and non-sensitive callback diagnostics.
- Keep automatic WordConfig mapping disabled until a sanitized matching Word + wordConfig fixture and expected output are supplied and independently verified. Do not infer signData separators or property ordering.
- Next: poll CI runs for commit `4c571a74be9c75ad6fa0b7b823bcd6a3e8d88f28` (Python `44796996459`, Native `44796996414`, UNO `44796996426`); then poll docs-triggered UNO run `44797006712`. PR #2 stays open, Draft and unmerged.

## 2026-11-20 — corrected adapter evidence audit verification

- Added a lock-protected, read-only `LibreOfficeAdapter.audit_word_writer_evidence()` entry point for the metadata-only report.
- Corrected the test module imports after the first intermediate push; that intermediate CI attempt failed and is superseded by the corrected code/test head.
- Corrected head `4c571a74be9c75ad6fa0b7b823bcd6a3e8d88f28`: Python run `44796996459` passed 220 tests (218 passed, 2 optional skips); UNO run `44796996426` passed 18 tests including the new audit regression and real Writer roundtrip.
- Docs-triggered UNO run `44797006712` also passed. Native build/CTest/staged install passed; package lifecycle and ASan/UBSan were still running at last poll.
- Continue polling Native run `44796996414`; keep PR #2 open, Draft and unmerged.


## 2026-11-20 — complete CI checkpoint

- Verified code/test head: `4c571a74be9c75ad6fa0b7b823bcd6a3e8d88f28`.
- Python run `44796996459`: 220 tests, 218 passed, 2 optional skips.
- UNO run `44796996426`: 18 tests passed, including the new read-only adapter evidence audit and real Writer roundtrip.
- Native run `44796996414`: build/CTest, staged install, Debian package install/upgrade/removal lifecycle, and ASan/UBSan passed. Both normal and sanitizer CTest report 4/4 passed.
- Docs-only UNO run `44797006712` passed. Later commits through `bb1d920` only update status/handoff documentation after the verified code/test head.
- PR #2 remains open, Draft and unmerged. Do not claim live Almas E2E, automatic WordConfig field mapping, visible Save/Don't Save/Cancel parity, complete desktop installer, or physical scanner/ADF/duplex validation.


## 2026-11-20 — expanded evidence report and close retry tests

- Evidence report now includes field indices, twin delimiter members, duplicate/case-fold collision groups, root/permission attribute names, optional attribute type/encoding and content-element presence, plus Writer property collision metadata. No values or document text are exposed.
- `OptionalAttribute.has_content_element` preserves the distinction between no `<content>` node and an explicitly empty node.
- Added tests for missing optional IDs, empty content nodes, twin identifiers, collision handling, and redaction.
- Added a close listener regression proving that a successful snapshot from a cancelled attempt is replaced on the next attempt and that terminal close notification is required.
- Python run `44798087534` on `491ca49a`: 224 tests, 222 passed, 2 optional skips. Native run `44798087414`: build/CTest 4/4, sanitizer CTest 4/4, package lifecycle success.
- UNO run `44797952771` on `226e0205`: 19 tests passed. New adapter integration coverage for twin metadata and empty optional content is in commit `41e15bbe`; poll its Python/UNO/Native workflows `44798367250`, `44798367221`, and `44798367187`.
- An intermediate evidence-report test run failed because one assertion still referenced a removed report attribute; corrected immediately and verified by the subsequent 224-test green run.
- Keep all automatic field writes disabled until the real sanitized Almas fixture and expected output are available. PR #2 stays open, Draft, unmerged.


## 2026-11-20 — privacy-safe close trace

- Added `CloseLifecycleTrace` and wired it into Writer close and save listeners. It stores fixed callback names, attempt ordinal, sequence, and monotonic timestamp only; it never stores document or field data and does not infer user choice.
- Exposed read-only in-memory trace retrieval via `LibreOfficeAdapter.inspect_close_lifecycle_trace(handle)`.
- Added tests for callback order, retry attempt numbering, allowlisted event names, and absence of payload/path data.
- Python run `44798818684` on `2feff5bf`: 227 tests, 225 passed, 2 optional skips. UNO `44798818677` and Native `44798818848` still running at last poll.
- The trace supports the visible Save / Don't Save / Cancel acceptance matrix; it does not itself prove the selected outcome.


## Latest close-trace CI state

- Python `44798818684`: 227 tests, 225 passed, 2 optional skips.
- Native `44798818848`: normal build/CTest, ASan/UBSan and DEB package lifecycle all passed.
- UNO `44798818677`: LibreOffice installation and runtime verification passed; the test step remains in progress. Poll it before claiming close-trace integration is UNO-verified.
- PR #2 remains open, Draft, unmerged.

## EMWAT Linux — corrected parallel-work checkpoint (2026-11-23)

### CI at commit 8a29d56bdf366039882555cee92853b180eb5a04

- Python Bridge run 45172202794: success.
- LibreOffice UNO run 45172202821: success.
- GTK desktop smoke test run 45172202655: success.
- Native Image Core run 45172202648: build/CTest and staged install passed; Debian package install/upgrade/removal lifecycle passed; ASan/UBSan job also completed successfully.
- These workflows validate the CI jobs at this exact branch head. They do not validate a physical scanner, live Almas browser integration, or Windows archive interoperability.

### Archive evidence correction — supersedes older handoff wording

- The .easz output-file path and .easd entry-name construction are supported by static call traces.
- Do not describe the writer password or encryption state as confirmed. The writer CryptoGetTextPassword2 trace initializes an internal object list; it does not reveal a password value/provider. The mapped SetPassword implementation is a no-op, and interface slot +0x28 maps to the progress-callback method, not to a proven password setter.
- Older notes in this handoff that label a fallback/configuration string as the archive password are superseded. Do not reuse any such string as an archive password.
- The actual runtime encryption flags, password source, archive header profile and interoperability remain unverified. The current evidence boundary is documented in docs/EASZ-ARCHIVE-FORMAT.md.

### Scanner implementation boundary

- ImageDocument stores multiple pages. ScannerBackend exposes scan_one() and a source-compatible scan_pages() fallback; SaneScannerBackend overrides scan_pages() for explicitly selected simplex ADF sources. Duplex-labelled source values are deliberately excluded from batch mode.
- SANE ADF batches keep one device/session open, use NO_DOCS at page boundaries (from start or before read bytes) as normal completion, cap batches at 100 pages / 4 GiB with the remaining byte budget enforced before allocation, and reject a 101st page rather than silently truncate. Flatbed and unspecified sources remain single-page only. The bounded collection state machine has deterministic fake tests for page order, exact-limit completion, empty feeder, read/start failure, over-limit failure, byte limits and cleanup.
- Each page accepts one terminal 8-bit Gray/interleaved RGB frame or a validated planar RED → GREEN → BLUE sequence, interleaved into one RGB page. The production page reader now uses an injectable SANE function table, with fake-device tests for interleaved RGB, planar RGB, multi-page ADF, feeder-empty read status, partial-page rejection and invalid channel order. Duplex front/back semantics and physical scanner hardware acceptance remain open. See docs/SCANNER-MULTIFRAME-IMPLEMENTATION.md.

### WordConfig / Writer boundary

- The adapter opens the incoming document and exposes a read-only WordConfig-to-Writer evidence audit. It does not automatically apply WordConfig fields.
- Exact-name intersections and case-only matches remain candidates, not verified semantic mappings. No positional mapping, signature-image substitution or unverified twin-field writes are permitted.
- See docs/WORDCONFIG-WRITER-APPLICATION-PLAN.md.


## 2026-11-23 — automatic Writer inventory and partial-inspection diagnostics

- `LibreOfficeAdapter.open_document()` now captures a metadata-only WordConfig/Writer inventory automatically after opening the document and recording its baseline. The report is retained in-memory on the office handle as `word_writer_evidence`; no field values or body text are written and no mappings are applied.
- Overall inventory failure does not block document open; only the stable status `writer_inventory_unavailable` is retained.
- Writer catalog inspection now records stable, value-free `inspection_warnings` for individual UNO structures that cannot be enumerated. The evidence report exposes these as `writer_inventory_warnings`, preventing an unavailable container from being silently mistaken for a genuinely empty one.
- Custom document-property metadata is now read once per inventory pass, preserving its UNO-reported order and producing the sorted view from the same snapshot.
- Added unit coverage for unavailable containers and propagation of warning codes into the evidence report.
- Latest verified CI at commit `7f92fdd0b1e293a34b73105e48a0f8b896ca0726`: LibreOffice UNO run `45177847225` passed 24 tests. Python, GTK and Native workflows for this exact head were still running/queued at the time of this handoff update; do not reuse earlier-head counts as proof for this commit.
- Python run `45177757461` on prior code head `2f8ce039d0395c2870cdd743600e91bdf18e0b21` passed 277 tests; UNO run `45177756605` on that prior head passed 24 tests. These are not a substitute for final-head CI.
- The SANE `scan_one()` terminal-frame guard and archive evidence correction are also present on the branch. No ADF/duplex or `.easz` interoperability claim is made.
- PR #2 remains open, Draft and unmerged.


## 2026-11-23 — automatic evidence-bounded template inventory

- Added `emwat_linux.template_mapping.inspect_template_mapping(config, catalog)` and unit tests.
- The inventory compares custom-property names with Writer bookmarks, named ranges, sections, tables, frames, graphic objects, document indexes and `DocInfo.Custom` text fields using case-insensitive exact matches only.
- Critical safety correction: the report does **not** attach a Writer property index to a WordConfig XML field index. Equal counts are only a count observation; Word COM and LibreOffice property enumeration order equivalence remains unproven. All XML field IDs remain explicitly unassociated.
- The inventory is captured automatically alongside the existing metadata-only Word/Writer evidence from a single UNO catalog snapshot. It neither reads property values nor modifies the document.
- Added unit coverage and a live UNO integration assertion that the report preserves the unassociated-field boundary.
- CI for the current branch head is triggered by the latest commits; do not claim it passed until all four workflows complete on the same head.
