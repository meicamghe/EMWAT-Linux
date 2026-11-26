# Parallel reverse-engineering follow-up — 2026-11-26

Repository: `meicamghe/EMWAT-Linux`  
Branch: `feature/recovery-retention-policy`  
Source binary: `analysis-input/EmwatMethods.bpl1`  
Evidence source: Run 49 Image/UI/VMT and Word/Printer/COM artifacts.

This report records three independent analysis tracks. All observations are static binary/TD32 evidence; none proves operation against physical scanner or printer hardware.

## Track A — GEAR32PD scanner and image-file lifecycle

### Separate scan-driver calls

The PE import table resolves these GEAR32PD exports:

| Export | IAT | thunk |
|---|---:|---:|
| `IG_scan_pages` | `0x00630CE4` | `0x004AFF30` |
| `IG_scan_source_select` | `0x00630CE8` | `0x004AFF28` |
| `IG_image_is_valid` | `0x00630D18` | `0x004AFEC0` |
| `IG_page_count_get` | `0x00630D24` | `0x004AFEA8` |
| `IG_load_FD` | `0x00630D2C` | `0x004AFE98` |
| `IG_save_FD` | `0x00630D28` | `0x004AFEA0` |
| `IG_save_file` | `0x00630D30` | `0x004AFE90` |
| `IG_image_delete` | `0x00630D1C` | `0x004AFEB8` |

Direct callsites include `IG_scan_pages` at `0x004EFA96`, `0x0061E036`, and `0x0061E059`; `IG_scan_source_select` at `0x004EFF83` and `0x0061E3DF`. The latter is inside the TD32-named `TfrmGScanPreview.ShowCropRectangle` procedure and is reached from the preview form's `SelectScanner` flow. The name/callsite mismatch is retained as an open semantic question rather than silently re-labelled.

### Preview scan method and intermediate files

`TfrmGScanPreview.Scan` at `0x0061DC80–0x0061DEF3` (628 bytes) contains a file-oriented page loop:

- It derives a filename from the configured working path and the literal `_New.tif`.
- It enumerates a page collection and loops through the discovered entries.
- It calls `IG_load_FD` for page input and `IG_save_FD` for writing/transforming the loaded image data.
- The save flags differ by the format selector at instance offset `+0x434`: the trace passes `0x40028` for one branch and `0x80028` for the other.
- It calls `IG_image_delete` for temporary image handles that are not the retained base handle.
- The method carries an explicit error flag through the loop and updates the working path after the loop.

The trace supports a temporary-file / image-handle conversion pipeline, but it does not yet prove the upstream device driver's exact output-directory naming or the full lifecycle of every temporary file.

### ScanToFile is validation plus persistence, not acquisition

`TGearImgProc.ScanToFile` at `0x004EF8C0–0x004EF9CB`:

1. compares/updates the configured output filename at object offset `+0x38`;
2. calls `IG_image_is_valid` on the image handle at `+0x10`;
3. resolves the output format through `GetFormatIndex`;
4. calls `IG_save_file` with the image handle and target path;
5. stores the returned result at object offset `+0x4C` and runs the controller's error check.

Therefore this method is a post-acquisition save path; do not treat it as the device-acquisition implementation.

### Multipage TIFF save path

`TfrmGScanPreview.Save_Tiff_MultyPages` at `0x0061D888–0x0061DC7F` (1,016 bytes) uses the page-count API and file-save path, and contains the strings:

- `_New.tif`
- `.jpg`
- `.tif`
- `SaveEditedImages1`
- `SaveEditedImages2`
- `SaveEditedImages3(ImgBpp = `
- `Can not save page: `
- `Can not save page: File is in use.`

The method branches on the form/controller format state and uses an indirect collection-count query before invoking save operations. It logs which save branch is used and includes a specific file-in-use failure message. The current trace does not justify identifying that virtual call as the GEAR32PD `IG_page_count_get` export. The complete filename assembly, exact meaning of every mode constant, and whether the final output is always a single multipage TIFF still need runtime confirmation.

## Track B — ImageEn acquisition and image-tools are a distinct path

The ImageEn import table identifies `TImageEnMIO.Acquire` at IAT `0x00630D84`, thunk `0x004B012C`.

- Its only direct TD32 callsite in the current artifact is `TfrmImageTools.InsertPicture` at `0x0050A364`.
- The caller obtains the ImageEn MIO object from the image-view control, calls `Acquire`, then continues through insertion/update handling.
- The same image-tools module imports ImageEn operations including `LoadFromFileAuto`, `SaveToFile`, `SaveToFileTIFF`, and `PrintImage`, plus multi-image-view methods such as `AppendImage`, `InsertImage`, `DeleteSelectedImages`, `GetImageCount`, and selected-image operations.
- The import set also includes the ImageEn TWAIN and WIA units (`Ietwain`, `Iewia`) and `TIEWia.GetRoot`.

This proves a second image acquisition/import capability in the image-tools UI. It does not prove that the main `TfrmGScanPreview` scanner path uses ImageEn.Acquire; its observed driver-facing calls are through GEAR32PD. Linux architecture should model the two workflows separately until runtime captures show an actual shared device backend.

## Track C — Word/GAM printing pipeline

### Printer gate and per-page preparation

`TCreateTiff.SeparteImages` at `0x004A0148–0x004A0A67` (2,336 bytes):

- initializes its print handler state and prepares the Word-document/page collection;
- calls `Zanprinter.GetPrinterName` (`0x0047CAF0`);
- consults the printer configuration/policy path through `SetPrinterForTiffout` (`0x0047D238`);
- checks queue pause state through `Zanprinter.Finalization` (`0x0047D8BC`);
- invokes the thread execution path `TCreateTiff.THidePrintingThread.Execute` (`0x004A0E88`);
- walks the document page collection and processes each page through indexed interface calls.

The method includes explicit error branches for unavailable printer, paused queue, and failures in the subsequent page/print path. The pause check itself opens the selected printer and reads the status field at `PRINTER_INFO_2A + 0x48`, comparing it with `PRINTER_STATUS_PAUSED`.

### What remains unproven

The artifacts do not yet establish a complete successful chain from the page collection through the final Windows spool submission and job completion. VCL/Winspool imports and a thread entrypoint are not enough to claim that the Linux replacement can print correctly. The next trace must resolve the body of `THidePrintingThread.Execute`, its indirect Word/Printer interface calls, and the final job-completion signal.

## Architecture consequences

1. Keep the GEAR32PD scan-source/page-acquisition flow separate from ImageEn's `Acquire` action used by `TfrmImageTools.InsertPicture`.
2. Keep `ScanToFile` as a validation/persistence responsibility, not the scanner-device adapter.
3. Preserve intermediate scan-file handling, image handles, single-page/multipage ownership, and final response filename as distinct concepts.
4. Keep the Word/GAM printer adapter behind a separate backend boundary; queue discovery, pause-state checks, per-page preparation, submission, and completion are different stages.
5. Do not add guessed enum values, filename rules, or native output mapping until the remaining branch/table and runtime behavior are confirmed.

## Next parallel tasks

- Scanner: resolve the exact `IG_scan_source_select` caller semantics, `IG_scan_pages` parameter setup, and intermediate directory/file naming.
- Image tools: trace ImageEn `Acquire` through the TWAIN/WIA objects, and trace TIFF save options from the image-tools UI.
- Word/Printer: decode `THidePrintingThread.Execute` and the indirect interface dispatches to the actual print submission and completion stages.
- Native model: compare confirmed single/multipage ownership and response-file fields against the current C++ types; change code only where a binary contract is fully supported.


## Track D — Native scanner page vector versus filesystem result contract

A focused source audit confirms that the native model already contains both sides of the ownership distinction, but does not yet establish their integration:

- `ScannerBackend::scan_one` returns one decoded `ImagePage`; `scan_pages` returns `std::vector<ImagePage>`. The SANE override performs bounded simplex ADF collection and returns the decoded page vector.
- `ImageDocument` owns decoded in-memory pages and provides append/select/edit operations. It is not a filesystem output manifest.
- `ScanResult` separately models physical output as `SinglePageFileSet` or `MultiPageFile`, plus independent optional `scan_path`, `response_filename`, and response XML metadata.
- `tests/test_scanner.cpp` exercises the scanner contract and SANE frame decoding; `tests/test_scan_result.cpp` independently exercises output ownership and response-field separation. CMake registers these as distinct test targets (`scanner_backend_contract` and `scan_result_contract`).

This confirms that the two contracts are not accidentally conflated in their public types. It does **not** prove a production adapter that turns captured `ImagePage` values into saved page files and then constructs the correct `ScanResult`. The inspected public scanner API and CMake test graph do not demonstrate that handoff. Do not add an implicit mapping based only on page count: the Windows binary has separate single-page/multipage result classes and distinct path/response-name fields, while final file naming and connector cardinality remain unresolved.

Next implementation gate: recover the Windows output naming/cardinality semantics and identify the service-layer owner for persistence; then add an explicit orchestration adapter with tests for one-page file set, multi-page TIFF, response filename independence, partial-save failure cleanup, and no false success before durable output exists. Keep scanner acquisition, image-document editing, and persisted-result ownership as three separate responsibilities.

## Track E — Corrected preview Scan output cardinality (cross-check against scanner output report)

A cross-document audit found that the preview output report contains stronger evidence than the earlier Run 49 paragraph about `TfrmGScanPreview.Scan`. Use the following as the current interpretation and treat any older wording that leaves its output cardinality open as superseded:

- `Scan` derives one destination ending in `_New.tif` from the preview path field at `this+0x458`.
- It queries the source page count through an interface at `this+0x3FC+0x2CC`, slot `+0x14`, then iterates page indices from 1.
- It opens the source with `_lopen`; for non-current pages it loads the indexed page with `IG_load_FD`.
- The destination is opened on each iteration with `CreateFileW` and `dwCreationDisposition=OPEN_ALWAYS`, not `CREATE_NEW`. It then calls `IG_save_FD` with the current 1-based page index, enabling successive page insertion into the same destination.
- The output handle is closed per iteration and temporary ImageGear handles are deleted. The original current-page handle is retained.
- Vendor ImageGear API documentation corroborates the `IG_save_FD(hIGear, fd, nPage, nReserved, lFormatType)` multipage-page-index semantics. This is API-version corroboration, not proof of the exact bundled version or runtime success.

Current conclusion: this particular `Scan` path is strongly consistent with one page-indexed multipage TIFF container, not a page-file set. `Save_Tiff_MultyPages` is a separate operation with its own branches and must not be merged into this interpretation. Keep `ScanResult` capable of both output variants because other result classes exist, but do not infer that this particular method creates `SinglePageFileSet`.

The exact format constants, unusual CreateFile template argument, final byte-level TIFF structure, and response publication remain unverified. This does not establish physical scanner/ADF/duplex operation or end-to-end Almas compatibility.

Source report: `docs/SCANNER-PREVIEW-OUTPUT-RECOVERY.md` (procedures `0x0061DC80`, `0x0061D888`).


## Track F — Keep preview TIFF generation separate from connector result paging

The combined scanner audit now has three distinct, evidenced layers:

1. **Preview/editor file generation:** `TfrmGScanPreview.Scan` (`0x0061DC80`) opens one `_New.tif` destination with `OPEN_ALWAYS` and writes successive one-based pages with `IG_save_FD`. This is strongly consistent with one multipage TIFF.
2. **Connector request paging:** `TScanCommand.VerifyConstraints` derives `FIsNextPageRequest` from whether `PreviousImageName` is non-empty. `GetNextPage` then uses the previous returned name and `HasError`/serial availability to choose a command state. This is a connector-level continuation protocol, not the preview form's local TIFF page loop.
3. **Connector result ownership:** `TResultImage` has distinct single-page and multipage subclasses, separate scan-path and response-filename fields, and class-specific naming. The base serial collision check and multipage `_P` handling are not enough to derive a complete external page sequence without a real request/response pair.

These layers must not be collapsed. In particular, a local multipage TIFF generated by the preview form does not prove that the Almas connector expects one multipage file; nor does a non-empty `PreviousImageName` prove that each connector continuation maps to a new physical file. The production adapter should wait for a captured scan request/response sequence that links `PreviousImageName`, `imageName`, response filename, physical scan path and file contents.

The next deep-follow-up workflow is now wired to trigger when either the workflow definition or the skipdata tracer changes. This closes a trigger gap: previously, editing only the workflow YAML was outside its own push path filter. The new push-filter commit is expected to start the workflow; its run and artifacts must be checked before claiming success.


## Track G — Expand helper-level tracing across the three independent lanes

The deep-follow-up workflow has been extended with bounded, reproducible helper traces:

- **Scanner/Fax connector:** helper `0x00454B9C`, which receives the literal `.tmp` path construction input before its result is passed to `GetNextPage`, now gets ordinary procedure disassembly, skipdata disassembly, direct callers and PE pointer-reference reports. This is intended to resolve the transformed path and whether any callers share the helper; it does not pre-assign a file extension or output policy.
- **ImageEn:** helper `0x004B0154` now gets procedure, skipdata, caller and pointer-reference reports alongside the already separate `TImageEnMIO.Acquire` caller path. Its identity remains unresolved until the generated reports are inspected.
- **Word close/recovery:** helper candidates `0x004BCA88`, `0x004AEBBC` and callback `0x004CD154` now get procedure, skipdata and direct-caller reports in the Word/GAM lane. These targets are kept separate from the GAM print-thread execution path; the callback's formal COM event identity must still be proven from its registration metadata.

The workflow file itself is included in the push path filter, so this workflow-only change is eligible to trigger a push run. The current GitHub connector's commit-run lookup is PR-trigger-only and therefore cannot establish whether a push-triggered run started. Do not interpret an empty result from that lookup as evidence that no push run exists; verify the Actions run list/artifacts when available.

No runtime behavior, native production code, or Windows protocol mapping was changed in this instrumentation-only pass.


## Track H — Run 51 helper identity corrections and next-page table follow-up

Run 51 (45796645461) completed successfully on workflow commit 4a729f6d1daf736fb57bc8ffc26a2c1ea8c25425. All four jobs passed: scanner/result ownership, ImageEn acquisition, Word/printer thread, and native regression (native CTest plus Python bridge suite). Artifacts were downloaded and inspected:
- scanner/result ownership: 15106015637
- ImageEn acquisition: 15105256757
- Word/printer thread: 15105750858

### Scanner filename helper correction

The target 0x00454B9C is now symbol-resolved as Emwatutils.euGetASFileName (236 bytes; 236/236 byte coverage, with two skipdata pseudo-instructions). It is a shared filename utility, not a fax-only or scanner-specific helper. Direct callers include:
- TCreateTiff.SeparteImages at 0x004A01EB and 0x004A0201
- CreateImageFile at 0x004A0C8B
- TWordViwer.LoadDocument at 0x004B7796
- TCreateTiff.PrintWordDoc at 0x004C1809
- TWordViwer.BGPrintWithGamPrintOptions at 0x004C6B50
- TWordViwer.ProtectDocument at 0x004CA00B
- TFaxDocument.SendFax at 0x00500E12
- TFaxDocument.PerformMethod at 0x005EEB91
- additional Excel, connector-finalization and version-handler callsites.

The body builds candidate names and loops through a file-existence check while changing a candidate component. The exact suffix formatting, helper-call semantics and per-caller output contract are not yet fully resolved. The direct-call inventory does not show a call from TScanCommand.GetNextPage; therefore the earlier Track G association of this helper with a scanner-specific .tmp path passed to GetNextPage is withdrawn. Do not infer a filename extension or connector output rule from this utility name alone.

### ImageEn helper remains a print-path helper candidate

0x004B0154 has no TD32 procedure range. Its four direct callsites are all inside TfrmImageTools.DoPrintingPanel (0x0050A7C3, 0x0050A8A6, 0x0050A999, 0x0050AA85), arranged in two page-iteration loops. This is distinct from the TImageEnMIO.Acquire import thunk 0x004B012C called by InsertPicture. The helper identity and its precise arguments/results remain unresolved; do not label it as Acquire or as the main GEAR32PD scanner path.

### Word close/archive candidate corrections

- 0x004BCA88 resolves to TWordViwer.GetXmlFieldInfo (0x004BCA88–0x004BFC17, 12,688 bytes). Its direct callers include two GetCaptionItemFont sites and TWordViwer.WordAppDocumentBeforeClose at 0x004CCCC9. It is an XML field-information lookup, not a generic close/archive helper. The callback's use of this helper is now explicit, but the helper's full field-selection semantics still need targeted analysis.
- 0x004AEBBC resolves to TfrmWordPrintOption.FreePrinters (0x004AEBBC–0x004AED10, 341 bytes). Its direct callers are WordAppDocumentBeforePrintBGPrint, GetOptionsFromReg, and SilentSaveEmwatDoc; this is a printer-options/UI lifecycle helper, not a close/archive helper.
- 0x004CD154 resolves to the TD32-labelled TWordViwer.WordAppDocumentBeforeSave callback (0x004CD154–0x004CD54B, 1,016 bytes; 536 bytes decoded in the ordinary trace). It has no direct CALL xrefs, consistent with its event-registration path. Existing RTTI/event-source evidence maps the registered event slot to OnDocumentBeforeClose; retain that stronger registration evidence over the misleading TD32 label. The callback calls GetXmlFieldInfo and manipulates close-state fields; its complete undecoded tail and exact UI/wire behavior remain open.

### Four-entry next-page state table

The pointer-reference artifact finds one raw reference to global 0x0062A7F0, at 0x004F25C6 inside TScanCommand.GetNextPage. The trace loads the table pointer from that global, iterates four pointer slots, compares the previous returned filename against each entry, and writes the selected index into command field +0x1D; a separate comparison can set field +0x1E. This confirms the table's use and four-entry cardinality, but not its actual string contents or semantic labels.

A new static inspector tools/dump_pe_delphi_pointer_table.py and a workflow step now attempt to decode the global pointer and its four Delphi UnicodeString candidates from raw PE data. The workflow push filter includes both the new tool and workflow definition. The inspector explicitly reports unavailable/runtime-initialized pointers instead of fabricating table contents. Results are pending the newly triggered workflow run.

No production Linux scanner, ImageEn, Word or printer behavior changed in this track.


## Track I — Run 5 ImageEn loop context and result-image ownership methods

Run 5 (45797672865) has completed the ImageEn and Word/printer jobs successfully; the scanner/result-ownership job was still running at the time of this inspection. Native regression passed, including the Python bridge suite. Run 5 Word artifact: 15106390855; ImageEn artifact: 15104489976.

### ImageEn helper 0x004B0154 — caller context narrowed, identity still open

The Run 5 artifact confirms no TD32 procedure range and no raw pointer references for 0x004B0154. All four direct calls are in TfrmImageTools.DoPrintingPanel. The full caller trace shows two separate page-iteration loops:
- First branch: 0x0050A7C3 is called after preparing an ImageEn/page-related object via 0x00404F3C; 0x004B01A4 immediately follows and its return value controls a count loop. The per-page loop passes a one-based counter from local [ebp-8] to 0x004B0154.
- Second branch: 0x0050A999 is called after 0x004B01F4 and a VMT call at slot +0x158; 0x004B01FC immediately follows and its return value controls another one-based page loop. The per-page loop again calls 0x004B0154.
- The same routine also uses 0x004B0204 in a third branch. The four calls to 0x004B0154 are therefore part of ImageEn printing/page iteration, not proof of device acquisition. They remain separate from TImageEnMIO.Acquire at thunk 0x004B012C and from the GEAR32PD scan preview path.

The workflow now traces 0x004B01A4, 0x004B01F4, 0x004B01FC, 0x004B0204 and 0x00404F3C with skipdata and caller scans to resolve the count/dispatch helpers. Those results are pending. Do not name 0x004B0154 until its target and call convention are identified.

### TResultImage result ownership methods — stronger field-level evidence

Run 50 artifact 15102809326 exposes additional methods in Ipresultimageunit:
- TResultImage.GetLocation (0x004ECF30) returns the byte at object offset +0x04.
- TResultImage.GetResponseFileName (0x004ECF38) reads the string field at +0x08.
- TResultImage.SetResponseFileName (0x004ED150) writes through the string-property setter at +0x08.
- TResultImage.GetScanFilePath (0x004ED03C) reads the string field at +0x10, validates/extracts a suffix-like component and composes a derived string. Its exact path naming rule is not established here.
- TResultImage.NextFile (0x004ECF50) checks the object at +0x04 and either clears the output string or delegates to a string-conversion helper. This is not evidence of a physical file write by itself.
- TResultImage.ShiftSerial (0x004ECFC8) checks whether the string at +0x10 is non-empty and calls GetScanFilePath; the boolean result depends on a file/path predicate.
- TResultImage.GetFileStream (0x004ECD60) returns a zero stream-size pair when the path at +0x10 is empty; otherwise it constructs a stream from that path and reads its size. This is stronger evidence that the object can open its scan-path file, but it does not prove when/how that file was produced.

The type hierarchy remains explicit: TSetOfSinglePageImages and TSetOfMultiPageImages have separate constructors and path/response filename overrides. The multipage class has its own response filename and scan path methods; do not collapse these into the base class or infer that every connector response uses one multipage file. The connector adapter gap remains: these Delphi ownership methods do not prove a Linux production adapter currently persists native ImagePage vectors or emits the corresponding XML response.

### Word callback helper review

Run 5 confirms 0x004BCA88 has exactly three direct callers: two GetCaptionItemFont callsites and WordAppDocumentBeforeClose at 0x004CCCC9. The helper is the large GetXmlFieldInfo routine, not a close/archive routine. 0x004CD154 remains a TD32-labelled BeforeSave method but has no direct CALL xrefs; the callback registration/RTTI mapping to OnDocumentBeforeClose remains the stronger event identity evidence. Its visible path queries Word document state, uses the close-cancel result word, manipulates internal flags at +0x5E/+0x5F/+0x58 and may call an application-level event hook. Full semantics and undecoded tail remain open.

No production Linux scanner, ImageEn, Word or printer behavior changed in this track.


## Track J — Scanner table probe failure analysis and workflow repair

Run 5 (45797672865) completed with overall failure because the scanner/result-ownership job failed in the 'Inspect global scan-state table and paging references' step. The preceding symbol extraction succeeded, and its artifact confirms exactly one raw reference to global 0x0062A7F0 at code address 0x004F25C8 (the immediate operand of the load at 0x004F25C6). The table-inspector output was absent, so no string values were recovered in that run. The independent ImageEn and Word/printer jobs succeeded, as did native regression.

Inspection of the committed workflow identified a shell line-continuation defect: the table-inspector invocation contained a doubled trailing backslash, causing the output-path continuation to be parsed incorrectly. Commit 1a6729a2 fixes the continuation and captures stdout, stderr and exit status as artifacts; a probe failure is now recorded without skipping the remaining scanner helper traces. This is a diagnostic/CI-only correction, not a change to the parser's semantic assumptions.

Run 7 (45798441917), on commit 1a6729a2, is the validation run for this repair. Its completion and the scanner table artifact must be checked before treating the static table inspection as successful. Run 6 (45798176238) was cancelled by the newer push while its independent lanes had completed; do not count it as a completed green run.

### Confirmed GetNextPage selection mechanics from the Run 50 trace

The full skipdata-enabled procedure trace for TScanCommand.GetNextPage (0x004F2558–0x004F2A93) shows it loads the global at 0x0062A7F0, then compares the PreviousImageName-derived string against four successive pointer entries, advancing the table pointer by four bytes and stopping on a match or after four entries. It stores the matched zero-based index in command byte +0x1D. A separate comparison against a constant string at 0x004F29E0 can set command byte +0x1E to 2. The method then constructs a TResultImage object using these state bytes and writes the result object pointer to command field +0x20. The table's string labels remain unknown until the static/runtime data is recovered; do not infer semantic names from the indices.


## Track K — ImageEn helper cross-caller context (Run 7 artifact)

Run 7 ImageEn artifact 15106012257 completed successfully and adds cross-caller evidence for the nearby helper targets:
- 0x004B01A4 has nine direct callsites across InsertPicture, DeletePicture, DoPrinting, DoPrintingPanel, mouse interaction and printer setup. In DoPrintingPanel its return value is decremented and used as a loop bound; in InsertPicture and DeletePicture it is used in image-index/count checks. This strongly suggests a collection/count-related ImageEn view helper, but no TD32 symbol range or definitive method identity was recovered. Do not promote the likely role to a named API without VMT/import evidence.
- 0x004B01FC has three direct callsites: DoPrinting compares its return value with 0x004B01A4's result, DoPrintingPanel uses it as a loop bound, and a drag/drop handler tests it for zero. This is consistent with a current/selected-image state query but is not conclusive.
- 0x004B01F4 appears only twice in DoPrintingPanel and receives the loop index plus floating-point print parameters before a VMT dispatch at slot +0x158. Its exact role remains unknown.
- 0x004B0204 is called from DoPrintingPanel and a drag-over handler; it appears to participate in print/drag state gating, not image acquisition.
- 0x00404F3C appears only in the four DoPrintingPanel calls immediately before 0x004B0154. Its target also has no TD32 procedure range in this artifact.

The helper procedures themselves all lack TD32 procedure ranges. The caller inventory narrows their roles but cannot resolve VMT method names, return types or full argument semantics. The 0x004B0154 conclusion remains unchanged: a page-loop helper in the ImageEn printing panel, not established as scanner acquisition. This track is based on Run 7 artifact output; overall Run 7 completion still needs checking.


## Track L — Four-entry GetNextPage table contents recovered (Run 7)

Run 7 (45798441917) completed successfully on commit 1a6729a2ab71d2616ddfd5d06b3e232934d7667c. All four jobs passed: scanner/result ownership, ImageEn acquisition, Word/printer thread and native regression. Scanner artifact: 15106421845.

The corrected static Delphi pointer-table inspector completed with exit_status=0 and decoded the global at 0x0062A7F0:
- Global raw offset: 0x002285F0
- Stored table pointer: 0x00628250
- Entry 0: null pointer (empty/uninitialized string slot)
- Entry 1: 0x004EC0BC -> `.tif`
- Entry 2: 0x004EC0D4 -> `.jpg`
- Entry 3: 0x004EC0EC -> `.bmp`

The GetNextPage trace loads this four-entry pointer table and compares a string derived from command field +0x2C against the entries. The static contents are therefore one empty slot followed by three image-extension strings. This does not yet prove the complete connector protocol meaning of each entry, nor whether the compared string is always a basename suffix in every runtime path. Preserve the exact observation and obtain a runtime request/response capture before encoding an external file-naming rule.

Run 7 also confirms the shell-continuation repair: the table output, stdout, stderr and status artifacts are present, with no stderr and exit_status=0. All four workflow lanes are green.
