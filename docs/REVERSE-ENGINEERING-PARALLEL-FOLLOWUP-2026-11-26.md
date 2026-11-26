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
