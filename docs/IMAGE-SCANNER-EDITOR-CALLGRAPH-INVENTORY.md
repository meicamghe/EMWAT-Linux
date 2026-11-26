## Run 49 follow-up — request constraints and next-page detection

A follow-up pass over `VerifyConstraints` and `HasError` resolves:

- `PreviousImageName` is copied to `FPreviousReturnedFileName +0x2C`; if non-empty, `FIsNextPageRequest +0x29` becomes true.
- `TXMLConstraintsType` numeric properties: `ColorDepth`, `MinResolution`, `MaxResolution`, `MaxFileSize`. Their values occupy four slots beginning at `TScanCommand +0x08`; `FHasConstraints +0x38` is set when their sum is nonzero.
- `HasError` calls `TResultImage.ShiftSerial` with the previous filename; success sets command state `+0x28=2`, failure sets it to `+0x28=4`.
- External page numbering and exact XML option/value semantics remain open. Full details are in `docs/REVERSE-ENGINEERING-RUN49.md`.

---

## Run 49 — scanner paging, XML contract, ImageGear/ImageEn and preserved UI resources

Run 49's complete artifact review adds the following evidence (full details in `docs/REVERSE-ENGINEERING-RUN49.md`):

### ScanCommand paging

- Deep trace for `TScanCommand.GetNextPage` at `0x004F2558` spans `0x004F2558–0x004F2A93`, 1,340 bytes. Skipdata coverage is 1,340/1,340 with 16 `.byte` pseudo-instructions.
- Coverage means all bytes were traversed, not that every byte is executable code. Embedded data and branch destinations need validation.
- The method calls `VerifyConstraints` and `LoadRequestXML`, then branches on `FIsNextPageRequest +0x29`. The next-page path examines `FPreviousReturnedFileName +0x2C`, compares `_P`, updates bytes `+0x1D/+0x1E`, and writes `ResultImage +0x20`.
- The four-entry table referenced through `0x0062A7F0` and exact enum/protocol semantics remain unresolved.

### Connector and response XML

- `TScanDocument.PerformMethod` looks up `wordConfig`, `wordBody`, `letterImages`, and `signData` in its dictionary. This does not establish each value's type or optionality.
- `TScanCommand` response class evidence confirms `response-scan` / `scaned-image`, with `status`, `errorCode`, `imageName`, and `encoding`.
- `success` and `base64` occur as constants in the response path; external runtime semantics still require a real connector capture.
- In `TFaxDocument.PerformMethod`, `.tmp` is passed through helper `0x00454B9C` and the helper-produced string reaches `GetNextPage`. `document` is passed to `TDictionary<String, Variant>.SetItem`, i.e. a write/update rather than a read.

### Image operations and resources

- ImageGear callsites resolve `IG_IP_flip` and `IG_IP_rotate_multiple_90`; ImageEn IAT inventory identifies `Acquire`, `LoadFromFileAuto`, `SaveToFileTIFF`, and `PrintImage`.
- Preserved `TfrmGScanPreview` resource includes scan preview, cancel/register, rotate, crop, H/V flip, original-image, TIFF/JPEG controls.
- Preserved `TfrmImageTools` resource includes ImageEn multi-view and add-image/scan/print toolbar controls.
- These are static resource/API observations, not proof of runtime behavior or hardware support.

### CI

Run 49 completed successfully in all three lanes. The separate artifact report is authoritative for the exact callsites and caveats. Physical scanner, ADF/Duplex and real printer acceptance remain open.

---

# Image, scanner and editor call-graph inventory

Date: 2026-11-25  
Input: successful `emwat-parallel-image-ui` artifact from workflow run `45558987223`, generated from `analysis-input/EmwatMethods.bpl1` and preserved DFM resources.  
Method: TD32 procedure-symbol indexing plus heuristic Delphi VMT candidate inspection. This is static evidence only.

## 1. Scanner preview form — `TfrmGScanPreview`

The symbol index identifies the following procedures in module `XmlRequest`:

| Procedure | VA | Size |
|---|---:|---:|
| `Scan` | `0x0061DC80` | 628 |
| `SelectScanner` | `0x0061DEF4` | 1236 |
| `Save_Tiff_MultyPages` | `0x0061D888` | 1016 |
| `GetImagePageNumber` | `0x0061D100` | 336 |
| `GetImgSize` | `0x0061D250` | 284 |
| `LoadImageToGearHandle` | `0x0061D36C` | 80 |
| `btnCropClick` | `0x0061E50C` | 60 |
| `btnHFlipClick` | `0x0061E548` | 119 |
| `btnLRotateClick` | `0x0061E5C0` | 47 |
| `btnRRotateClick` | `0x0061E5F0` | 47 |
| `btnVFlipClick` | `0x0061E620` | 47 |
| `cmbPagesChange` | `0x0061E680` | 768 |
| `uibtnRegisterClick` | `0x0061E470` | 60 |
| `uibtnCancelClick` | `0x0061E3F0` | 125 |

The names establish that scanner selection, acquisition, page counting/loading, multipage TIFF saving, page navigation, crop, flips and rotations are separate handlers. The handler names do not alone establish exact pixel transforms, error semantics, or the commit/cancel behavior.

## 2. Shared image-processing controller — `TGearImgProc`

The TD32 index in module `Vcl.XPMan` exposes a cohesive controller surface:

| Operation | VA |
|---|---:|
| `SelectScanner` | `0x004EF9CC` |
| `ScanToFile` | `0x004EF8C0` |
| `SaveToFile` | `0x004EF714` |
| `SavePage` | `0x004EF510` |
| `SaveCPinMultiPageFile` | `0x004EF40C` |
| `Crop` | `0x004EEDB4` |
| `Rotate90` | `0x004EF138` |
| `RotateLeft` / `RotateRight` | `0x004EF178` / `0x004EF1A4` |
| `Flip` / `FlipHorizontal` / `FlipVertical` | `0x004F01F0` / `0x004F0210` / `0x004F023C` |
| `LoadPage` / `ReloadPage` | `0x004EF1DC` / `0x004EF0E4` |
| `SetCurrentPage` / `ReNewPageCount` | `0x004EFF6C` / `0x004EF124` |
| `NotifyEditor` / `ShowEditor` | `0x004EF240` / `0x004F0174` |
| `SetResultImage` | `0x004F0160` |
| `GetForceSinglePage` / `SetForceSinglePage` | `0x004EF088` / `0x004F0084` |
| `GetImageResolution` / `GetImageBPP` | `0x004EEEC4` / `0x004EF0C4` |
| `GetFormatIndex` / `SetFormatIndex` | `0x004EF0B4` / `0x004F00FC` |
| `SetJpgQuality` | `0x004F012C` |

This is strong evidence that the original product centralizes scanner, page, transform, format and editor notification operations behind a controller-like object. The exact method bodies and argument contracts still require the expanded procedure traces.

## 3. Simple image editor — `TfrmSimpleImageEditor`

The symbol index identifies:

- `Initial` `0x004F116C`
- `CropImage` `0x004F11E8`
- `pbImgViewerMouseDown/Move/Up` `0x004F1274/0x004F1308/0x004F1404`
- `ShowCropRectangle` `0x004F1660`
- `ToggleCropMode` `0x004F1890`
- `CalculateBestFitSize` `0x004F1988`
- `chkForceSinglePageClick` `0x004F1A04`
- `cmbPagesChange` `0x004F1CE0`
- `doCommand` `0x004F1D04`
- `FormClose` / `FormCloseQuery` `0x004F1064` / `0x004F109C`

This supports a real crop-selection interaction (mouse down/move/up plus crop rectangle) and an explicit force-single-page option. Exact coordinate conversion, crop bounds, cancel/accept semantics and page behavior remain to be traced.

## 4. Image tools — `TfrmImageTools`

The symbol index identifies an ImageEn multi-view workflow:

- Multi-image operations: `InsertPicture` `0x0050A29C`, `DeletePicture` `0x0050A414`, `ScanPicture` `0x0050A298`, `itNavigatePages` `0x0050A1D4`.
- Transforms: `FreeRotate` `0x00508A90`, `RotateImage` `0x0050AB2C`, `FlipImage` `0x0050ABA4`, `AutoOrient` `0x0050ACDC`.
- Editing and commands: `doProc` `0x0050BBB8`, `itRunCommand` `0x0050A218`.
- Printing: `DoPrinting` `0x0050A534`, `DoPrintingPanel` `0x0050A698`, `ShowPrintPanel` `0x005098B0`, `UpdatePrintPreview` `0x0050BB90`.
- ImageEn interaction: `iePageHolderImageChange` `0x0050B718`, image select/deselect and mouse handlers around `0x0050B254–0x0050B94C`.

This confirms that image tools are not a single-image viewer: the form exposes insertion/deletion, navigation, transformations, scanning and print-preview paths.

## 5. Image result and multipage containers

The symbol index identifies `TResultImage` operations for file enumeration, per-index file naming, file stream, image type, file size, scan path and response filename. It also identifies distinct `TSetOfSinglePageImages` and `TSetOfMultiPageImages` constructors; the latter has its own delete, scan-path and response-filename methods.

This is an important modeling boundary for Linux: a scan result is not necessarily a single path. The native model must preserve single-page collections and multipage-file collections as distinct representations, with explicit response naming and page indexing.

## 6. VMT candidate caveat

The VMT script found self-pointer and instance-size-consistent candidates for `TfrmSimpleImageEditor`, `TfrmGScanPreview`, `TfrmImageTools`, `TGearImgProc` and `TScanCommand`. It explicitly labels them **unverified candidates**. Several candidates point into executable sections containing Delphi package thunks; a valid-looking candidate and method table profile do not prove the VMT boundary or inherited slot layout. Do not use these candidates to assign interface slots until corroborated by RTTI, constructor references, or runtime inspection.

No candidate was found for several data-model classes (`TResultImage`, `TSetOfSinglePageImages`, `TSetOfMultiPageImages`), despite their TD32 procedure symbols. This is not evidence that they lack classes or methods; their RTTI representation may differ.

## 7. Linux implementation implications and next probes

1. Keep `ScanSession`, `ImageDocument`, `Page`, and `ScanResult` separate. Support both a set of single-page files and a single multipage TIFF result.
2. Preserve page navigation and explicit force-single-page behavior.
3. Model crop selection as coordinates in the displayed preview, then map to source-image coordinates with a tested scale/offset transform.
4. Keep transformations (rotate/flip/free-rotate/auto-orient) explicit operations with metadata/orientation tests.
5. Trace the listed procedures and their callers to recover exact state mutations, output naming, TIFF append/finalize behavior, and cancel/register semantics.
6. Compare these contracts against existing `native/include/emwat/image_document.hpp`, `native/src/image_document.cpp`, and scanner backend tests before changing the native API.

## Evidence limits

- Artifact workflow run `45558987223` completed the image VMT/symbol/resource inventory job successfully.
- The initial artifact contains symbol indexes and heuristic VMT output. The expanded procedure/caller trace job was added afterward and has its own pending workflow run.
- No physical scanner, real TIFF device capture, Wine prefix, or printer was exercised by this artifact.


## 8. Expanded procedure traces (workflow run 45559122428)

The follow-up run traced 23 procedures and direct callers in parallel. The following body-level observations are supported by those traces:

- `TGearImgProc.SaveCPinMultiPageFile` (`0x004EF40C`) reads the page count from its image-set object, iterates pages starting at index 1, sets the current page through `SetCurrentPage`, sets an internal active flag, invokes a page-stream/interface method at slot `+0x20`, stores the returned page value, and runs `CheckErrors`. After the loop it closes/releases the previous stream/interface and restores the new one. This is a per-page append/serialization path; the exact stream ABI and output byte layout remain unresolved.
- `TGearImgProc.SavePage` (`0x004EF510`) iterates a page count stored at object offset `+0x30`, chooses a source handle/path per page, opens/creates an output handle through helper calls, writes each page, closes the temporary handle, and performs a finalization step when no page error was recorded. The exact Win32 API wrappers and file naming contract still need mapping.
- `TGearImgProc.SaveToFile` (`0x004EF714`) checks internal state and output path, selects a save route based on the image format/state fields, and falls back to `SavePage` for one branch. It calls the shared output/format helper chain; the numeric format value `0x15` is not labeled here because its enum mapping has not yet been independently proven.
- `TGearImgProc.ScanToFile` (`0x004EF8C0`) normalizes/updates its target format, queries the selected scanner/result object, derives a format index and output destination, invokes the scanner/output helper chain, and updates the controller's result field. Its caller-facing Boolean/error semantics require further trace.
- `TfrmGScanPreview.Save_Tiff_MultyPages` (`0x0061D888`) contains separate output branches based on form state and format fields; it uses the page-count helper and calls file/handle helpers, with distinct flags for output mode. It also delegates to the scan path for one branch. The procedure name and calls support a multipage TIFF save path, but exact flags, TIFF finalization and path ownership are still open.
- `TGearImgProc.Rotate90` (`0x004EF138`) returns early when the backing image-set field is null; otherwise it obtains a result handle and dispatches a rotation operation through an object method, then updates a stored result value. Rotation direction/angle semantics still require mapping of the callee.
- `TGearImgProc.Crop` (`0x004EEDB4`) is a short wrapper that initializes a GEAR image-processing object using embedded constants and stores the resulting object reference; it is not itself the full crop implementation. The actual crop operation is called through another interface path.
- `TfrmSimpleImageEditor.CropImage` (`0x004F11E8`) reads state from the editor/controller objects, dispatches through an interface slot at `+0x88`, updates related flags based on image bit-depth/state, and then invokes the register/accept handler. This is consistent with a staged edit/accept flow; it does not by itself prove the UI Cancel semantics.
- `TfrmImageTools.InsertPicture` and `DeletePicture` (`0x0050A29C`, `0x0050A414`) operate on an ImageEn multi-view object and its selected/current image/page. The delete path has a distinct branch when the form's mode field equals 3 and uses separate remove/replace helper calls; the exact mode enum and selected-image ownership remain unresolved.
- `TfrmImageTools.doProc` (`0x0050BBB8`) derives a three-way operation selector from an ImageEn object method result, then computes floating-point parameters from several stored controls/objects and calls the free-rotate path. This confirms that free rotation is a parameterized operation, not just a 90-degree transform.

The expanded trace does not change the VMT caveat: candidate VMTs remain heuristic/unverified until corroborated independently.


## 9. ImageGear and file-I/O helper identities (workflow run 45559625754)

The previously opaque helper addresses are now resolved against the PE import table. These are not all ordinary file-system helpers; most are ImageGear API thunks:

| Helper VA | Resolved target | Evidence role |
|---|---|---|
| `0x004AFE78` | `GEAR32PD.DLL!IG_ext_load` | Load ImageGear extension |
| `0x004AFE90` | `GEAR32PD.DLL!IG_save_file` | Save image file through ImageGear |
| `0x004AFE98` | `GEAR32PD.DLL!IG_load_FD` | Load image through an FD/stream path |
| `0x004AFEA0` | `GEAR32PD.DLL!IG_save_FD` | Save image through an FD/stream path |
| `0x004AFEA8` | `GEAR32PD.DLL!IG_page_count_get` | Read page count |
| `0x004AFEB8` | `GEAR32PD.DLL!IG_image_delete` | Delete/release an ImageGear image object |
| `0x004AFEC0` | `GEAR32PD.DLL!IG_image_is_valid` | Validate an ImageGear image object |
| `0x004AFF18` | `GEAR32PD.DLL!IG_IP_color_promote` | Promote image color representation |
| `0x00402684` | `kernel32.dll!CloseHandle` | Close a Win32 handle |
| `0x004026A4` | `kernel32.dll!CreateFileW` | Open/create a Win32 file handle |
| `0x00402918` | `kernel32.dll!_lclose` | Close a legacy CRT file handle |
| `0x00402920` | `kernel32.dll!_lopen` | Open a legacy CRT file handle |

The thunk identities are exact import-table matches. The wrapper names establish which ImageGear operations the native implementation must replace, but they do not reveal the complete argument ABI or ownership rules. In particular, do not assume that `IG_load_FD` and `IG_save_FD` take ordinary POSIX file descriptors without recovering their argument contract.

### Linux parity consequence

The native backend should replace these calls at the semantic boundary:

- image decode/encode and format dispatch (`IG_load_FD`, `IG_save_FD`, `IG_save_file`);
- multipage count and page iteration (`IG_page_count_get`);
- image-object validity and lifecycle (`IG_image_is_valid`, `IG_image_delete`);
- color-depth promotion (`IG_IP_color_promote`);
- file-handle creation/closure using safe POSIX file descriptors.

This confirms why a thin CUPS or Wine compatibility shim is insufficient: the original scanner/image pipeline is coupled to ImageGear image objects, page streams and format operations. Native libtiff/libjpeg/libpng plus a well-defined Linux image-document/result model is the appropriate replacement boundary, after exact output semantics are verified.



## 10. ImageGear operation imports and editor callsites (workflow run 45763380148)

The expanded IAT scan and thunk traces identify additional image-operation APIs and their exact direct callsites:

| Import thunk | Resolved ImageGear API | Direct callsites / TD32 method names |
|---|---|---|
| `0x004AFED0` | `IG_IP_flip` | `TGearImgProc.FlipHorizontal` at `0x004F021F`; preview methods at `0x0061E5CC` and `0x0061E65C` |
| `0x004AFEC8` | `IG_IP_rotate_multiple_90` | `TGearImgProc.RotateLeft` at `0x004EF187`; preview methods at `0x0061E5FC` and `0x0061E62C` |
| `0x004AFF00` | `IG_image_dimensions_get` | `TGearImgProc.ReloadPage` at `0x004EF107`; `TfrmGScanPreview.GearErrorHandling` at `0x0061D09C`; `TfrmGScanPreview.LoadImageToGearHandle` at `0x0061D39B` |
| `0x004AFEF0` | `IG_device_rect_set` | Direct calls at `0x004EEF0F` and `0x0061D853`; containing method semantics are not yet identified |

The exact IAT identities are:

- `0x00630D10` → `IG_IP_flip`
- `0x00630D14` → `IG_IP_rotate_multiple_90`
- `0x00630CF8` → `IG_image_dimensions_get`
- `0x00630D00` → `IG_device_rect_set`

### Important name/operation mismatch

The Delphi method names do not consistently match the imported operation at the callsite:

- The preview method named `btnLRotateClick` calls `IG_IP_flip` with argument 0.
- The method named `btnRRotateClick` calls `IG_IP_rotate_multiple_90` with argument 3.
- The method named `btnVFlipClick` calls `IG_IP_rotate_multiple_90` with argument 1.
- `TGearImgProc.RotateLeft` calls `IG_IP_rotate_multiple_90`; `TGearImgProc.FlipHorizontal` calls `IG_IP_flip`.

This is direct evidence that the imported API, not the Delphi event-handler name, must govern the Linux operation mapping. It is **not** enough to conclude that the UI labels are wrong: the arguments, coordinate/orientation state and surrounding refresh handlers may encode a different transform convention. Do not assign final user-visible semantics until the relevant ImageGear prototypes and state updates are recovered.

### Image dimension outputs

`TfrmGScanPreview.LoadImageToGearHandle` passes the image handle at `this+0x428` to `IG_image_dimensions_get` and passes addresses of fields `this+0x42C`, `this+0x430`, and `this+0x434` as output pointers. The same thunk is used by `TGearImgProc.ReloadPage` and `TfrmGScanPreview.GearErrorHandling`. The three output fields are confirmed as a grouped dimensions/result tuple, but their individual meanings and units are not yet proven. Do not label them width/height/DPI or copy them into Linux metadata without the vendor API contract.

The `IG_device_rect_set` calls establish that the scanner/image path also updates a device rectangle through ImageGear; the exact rectangle source and relation to crop/preview coordinates remain open.

Evidence: run `45763380148`, artifact `15090612978`, `image-io/image-operations/`.



## 11. Separate ImageEn I/O path and connector handler entry points (workflow run 45763574936)

The run-26 symbol and IAT inventory confirms that EMWAT contains a second imaging path based on ImageEn, distinct from the ImageGear `IG_*` scanner-preview path.

### 11.1 ImageEn `TImageEnMIO` API callsites

| IAT thunk | Resolved ImageEn method | Direct callsites |
|---|---|---|
| `0x004B0154` | `TImageEnMIO.PrintImage` | `0x0050A7C3`, `0x0050A8A6`, `0x0050A999`, `0x0050AA85` |
| `0x004B014C` | `TImageEnMIO.LoadFromFileAuto` | `0x00508B88`, `0x0050A4D3` |
| `0x004B0144` | `TImageEnMIO.GetParams` | `0x00508CD1`, `0x00508CE6`, `0x0050B648`, `0x0050B659`, `0x0050B676` |
| `0x004B013C` | `TImageEnMIO.ExecuteSaveDialog` | `0x0050AFAE` |
| `0x004B0134` | `TImageEnMIO.ExecuteOpenDialog` | `0x0050A48C`, `0x0050A4BF` |
| `0x004B012C` | `TImageEnMIO.Acquire` | `0x0050A364` |
| `0x004B011C` | `TImageEnMIO.SaveToFile` | `0x0050AFC4` |
| `0x004B0114` | `TImageEnMIO.SaveToFileTIFF` | `0x0050B6A0` |

The `Acquire` call is inside `TfrmImageTools.InsertPicture`; the `PrintImage` calls belong to `TfrmImageTools.DoPrintingPanel`. The save/load/dialog calls are distributed across image-tools handlers. This confirms a separate ImageEn capture, file-open/save and print-preview workflow. It must not be conflated with `TfrmGScanPreview.Scan` / ImageGear's `IG_scan_pages` and `IG_save_FD` path.

### 11.2 Protocol connector methods

The symbol index labels two procedures in module `Winapi.MMSystem`:

- TD32 label `TScanDocument.PerformMethod` at `0x005EE82C` (796 bytes)
- `TImageEdition.PerformMethod` at `0x005EF24C` (180 bytes)

**Important reconciliation:** the runtime class/VMT analysis in `docs/WORD-DOCUMENT-PROTOCOL-ANALYSIS.md` maps `0x005EE82C` to the concrete `TEditWordDocument.PerformMethod` target for the `EditWordDocument` request. That method reads `wordConfig`, `wordBody`, `letterImages`, and `signData`, then calls `TWordViwer.LoadDocument` at `0x004B7724`. The TD32 `TScanDocument` name is therefore a stale/misleading symbol label for this runtime Word handler; do not treat `0x005EE82C` as proof of a public `ScanDocument` endpoint.

Both procedures expose a parameter typed as a Delphi generic `TDictionary` with `System.AnsiString` keys; the dictionary value type and exact key/value schema are not encoded in the symbol name. The `TImageEdition.PerformMethod` entry remains a separate image-edition connector target, but its key and operation are still unknown.

The same index identifies the `TScanCommand` lifecycle/request methods:

- `DoNewScan` `0x004F22AC`
- `DoRequest` `0x004F22E4`
- `GetNextPage` `0x004F2558`
- `HasError` `0x004F2A94`
- `LoadRequestXML` `0x004F2B18`
- `VerifyConstraints` `0x004F2C4C`

These names are now confirmed symbol inventory only. The actual XML method names, `TImageEdition` key, input validation, scan session state, response structure, error mapping, and page ownership are not yet established. The run-27 workflow traced the `TScanCommand` methods; the next pass decodes their constants and maps the result-image helpers. Do not register Linux `ScanDocument` or `ImageEdition` handlers from names alone.

Evidence: run `45763574936`, artifact `15090488790`, files under `image-io/imageen/`.



## 12. Runtime scanner/image connector and result-image contracts

The service-side class-resolution/VMT map in `docs/EMWAT-SERVICE-EXECUTABLE-ANALYSIS.md` resolves the actual runtime class for each concrete `VMT+0x10` target. Several TD32 procedure labels are stale or shifted; runtime class names below use the service/VMT mapping, with TD32 labels shown separately.

### 12.1 Word handler — runtime `TEditWordDocument`, `0x005EE82C`

- TD32 label: `TScanDocument.PerformMethod`.
- Runtime VMT evidence maps this VA to `TEditWordDocument.PerformMethod` for XML class `EditWordDocument`.
- Reads `wordConfig`, `wordBody`, `letterImages`, and `signData`; delegates to `TWordViwer.LoadDocument` at `0x004B7724`.
- The four embedded keys are confirmed by the run-29 string decode.

This is the Word handler, not the scanner endpoint.

### 12.2 Public scanner connector — runtime `TScanDocument`, `0x005EEB48`

- TD32 label: `TFaxDocument.PerformMethod`.
- The service VMT map resolves runtime class `TScanDocument` to this `VMT+0x10` target.
- Reads dictionary key `document` and emits the embedded log prefix `[Invoke ScanDocument]`.
- Converts the `document` value to a path and opens it as a file stream through `0x004041BC` (access flags `0xFF00`), then logs `[Invoke ScanDocument]`.
- Constructs `TScanCommand` at `0x004F21DC`, calls `GetNextPage` at `0x004F2558` with the opened stream, reads the value through interface slot `+0x54` from command field `+0x34` (RTTI field name `FResponseXML`), and passes it to an unresolved external insertion helper at `0x004012F8`. The output dictionary key and value encoding are still unknown.
- The output dictionary key and final response serialization are not yet decoded.

This confirms that a public Windows `ScanDocument` connector exists. It is not the same code path as the `TfrmGScanPreview.Scan` UI method; it consumes a document/result request and delegates to the stateful `TScanCommand`/result-image layer. The `document` path value is untrusted and must be confined beneath an approved application data/output root in any Linux implementation.

### 12.3 Internal `TScanCommand` request/page lifecycle

| Procedure | VA | Body-level observations |
|---|---:|---|
| `DoNewScan` | `0x004F22AC` | Clears/reinitializes object fields at `+0x24` and `+0x04`, masks an input flag with `0xFC`, and calls a state-reset helper; positive input flags trigger additional initialization. |
| `DoRequest` | `0x004F22E4` | Loads/parses request XML, examines result-image state, calls result/controller helpers, validates constraints, and updates status byte `+0x28` with distinct values. One branch recurses after a result-object callback. |
| method at `0x004F2558` (TD32 label `GetNextPage`; RTTI published-method table `DoRequest`) | `0x004F2558` | Calls `VerifyConstraints` and `LoadRequestXML`; uses a multi-file branch when flag `+0x29` is set; constructs a `TResultImage` via `0x004EC8B4` (`UnicodeString` path and `TImageFormat`), stores the returned object at `+0x20`, then calls `HasError`. |
| `HasError` | `0x004F2A94` | For the multi-file branch, constructs a path from field `+0x2C`, passes it to a result-object method, then calls `TResultImage.ShiftSerial` (`0x004ECFC8`) and maps its Boolean result into status byte `+0x28`. `ShiftSerial` calls `GetScanFilePath` (`0x004ED03C`) and checks whether the resulting file exists. |
| `LoadRequestXML` | `0x004F2B18` | Checks global service/controller state; obtains a string from an object at `+0x34`, combines it with global path/config state, and passes it to a global interface method at slot `+0x14`. Returns a Boolean-like result. |
| `VerifyConstraints` | `0x004F2C4C` | Reads multiple child/attribute values through XML-like interfaces (vtable slots `+0xAC`, `+0xB0`, `+0xB4`, `+0xB8`, `+0xBC`), compares them against static strings, and sets validation/mode flags. |

The command object stores state flags at offsets `+0x18` through `+0x1E`, plus `+0x28` and `+0x29`; result/path references are observed at `+0x20`, `+0x2C`, `+0x30`, and `+0x34`. These are object offsets only; do not assign semantic field names until XML tags and constructors are fully decoded.

#### 12.3.1 Constraint values and state flags

The decoded constants used by `VerifyConstraints` are `none`, `jpg`, `yes`, and `no`. Their exact XML tag names are not present at this callsite, but the value-to-state mapping is visible:

| XML value read in traversal order | Resulting command state |
|---|---|
| First value equals `none` | `+0x1D=1`, `+0x1B=1` |
| First value is not `none`, equals `jpg` | `+0x1D=2`, `+0x1B=0` |
| First value is neither `none` nor `jpg` | `+0x1D=1`, `+0x1B=0` |
| Second value equals `none` | `+0x1E=1`, `+0x1C=1` |
| Second value is not `none`, equals `yes` | `+0x1E=2`, `+0x1C=0` |
| Second value is neither `none` nor `yes` | `+0x1E=1`, `+0x1C=0` |
| Third value is nonempty | `+0x29=1`; empty gives `+0x29=0` |
| Fourth value equals `yes` | `+0x18=1`; otherwise `+0x18=0` |
| Fifth value is not `no` | `+0x19=1`; equals `no` gives `+0x19=0` |
| Sixth value is not `no` | `+0x1A=1`; equals `no` gives `+0x1A=0` |

The embedded UI warning asks in Persian whether the operation should be repeated when image constraints are not satisfied. It is UI text, not an HTTP response.

#### 12.3.2 Result-image hierarchy and file ownership

Run 29/30 symbol and body traces resolve the Windows result-image hierarchy:

- `TResultImage.Create`: `0x004EC8B4`, accepts a `UnicodeString` path and `TImageFormat`.
- `TResultImage.Create` is a factory-style dispatcher: its format/mode switch selects VMT/class references `0x004EC558`, `0x004EC628`, or `0x004EC788`, then calls constructors/helpers at `0x004ECA58`, `0x004ED344`, or `0x004ED298`. The `0x004ED344` TD32 label is `TSetOfMultiPageImages.DeleteImageFile` despite its use in a constructor branch; do not infer the concrete result class from that symbol label. `TSetOfSinglePageImages.Create` at `0x004ED168` is a separate constructor called from `Finalization` at `0x004ED634`. The three VMT identities and exact format/mode mapping remain to be resolved.
- `TResultImage.ShiftSerial`: `0x004ECFC8`; resolves `GetScanFilePath` (`0x004ED03C`) and checks file existence.
- `TResultImage.NextFile`: `0x004ECF50`.
- `TResultImage.GetFilesCount`: `0x004ECC84`; count comes from the internal collection at `+0x08`.
- `TResultImage.GetFileNamePath`: `0x004ECBD8); for a positive one-based index it calls `GetScanFilePath(index-1)`.
- `TResultImage.FileNameOf`: `0x004ECB6C); returns a filename only when the resolved file exists.
- `TResultImage.GetFileStream`: `0x004ECD60); opens the resolved file through helper `0x004041BC`.
- `TResultImage.GetFileSize`: `0x004ECCAC); repeatedly calls `ShiftSerial` while serial/path values exist.
- `TSetOfSinglePageImages.Create`: `0x004ED168`.
- `TSetOfMultiPageImages.Create`: `0x004ED298); stores one base path at `+0x10` and calls `ShiftSerial` to choose a non-colliding serial.
- `TSetOfMultiPageImages.GetScanFilePath`: `0x004ED4C0`; its format string at `0x004ED584` is `_P`.
- Base `TResultImage.GetScanFilePath` (`0x004ED03C`) uses `%.3d` at `0x004ED144`.
- A related literal `_P000` is present at `0x004ED338`; its exact callsite/format role must be kept distinct from the `_P` format string until the full argument flow is reconciled.

This confirms two distinct Windows result-collection classes (`TSetOfSinglePageImages` and `TSetOfMultiPageImages`) and partially decodes their naming machinery: base result paths use a three-digit (`%.3d`) serial format; the multipage subclass uses `_P` in its path format; `_P000` is another decoded literal whose precise role remains under callsite review. This is not enough to determine the complete filename concatenation order, whether the serial identifies a scan session or collision retry, or the exact one-to-one mapping to native `SinglePageFileSet` versus `MultiPageFile`: both classes expose indexed `GetScanFilePath`/file-count operations. Separately, the preview UI's `TfrmGScanPreview.Scan` path is strong evidence for one page-indexed `_New.tif` multipage container via `IG_save_FD`. Keep connector result ownership open until path callsites and actual output bytes are traced.

### 12.3.3 `TScanCommand` class metadata and response handoff

Run 34 traced the constructor and inspected the class metadata around `0x004F1F94`:

- Runtime `TScanDocument.PerformMethod` creates the command using class pointer `0x004F1F3C` and constructor `0x004F21DC`; this is a direct constructor callsite from the public scanner connector.
- The class-name metadata at `0x004F20D7` decodes to `TScanCommand`; the field table gives instance size `0x40` and these exact names/offsets:

| Field name in RTTI | Offset | Evidence/use |
|---|---:|---|
| `ImgProc` | `+0x04` | Initialized by constructor |
| `Options` | `+0x08` | Field-table entry; detailed use pending |
| `ResultImage` | `+0x20` | Assigned by `GetNextPage` after constructing `TResultImage` |
| `FEditorForm` | `+0x24` | Initialized by constructor; reset by `DoNewScan` |
| `FCommandState` | `+0x28` | Updated by `DoRequest`/error paths |
| `FIsNextPageRequest` | `+0x29` | Branches the next-page path in `GetNextPage` |
| `FPreviousReturnedFileName` | `+0x2C` | Used for previous-output comparison/path selection |
| `FRequsetXML` | `+0x30` | Exact RTTI spelling; request XML state |
| `FResponseXML` | `+0x34` | Read by `TScanDocument.PerformMethod` after `GetNextPage` |
| `FHasConstratints` | `+0x38` | Exact RTTI spelling; constraint state |

The class metadata is strongly corroborated by the constructor symbol, class-name string, field table and direct connector constructor call. However, the candidate parent VMT pointer is `0x0062EEA4`, outside the BPL image; do not treat the generic VMT scanner's virtual-slot layout as fully verified until that parent metadata is resolved.

**Method-name conflict to preserve:** the RTTI published-method table bytes at `0x004F20B9` contain a `DoRequest` entry pointing to `0x004F2558`, while the TD32 symbol index labels `0x004F2558` as `TScanCommand.GetNextPage`. A separate TD32 `TScanCommand.DoRequest(UnicodeString)` symbol exists at `0x004F22E4`. The public `TScanDocument` handler calls `0x004F2558`. Keep the address-level call graph, but do not collapse the two methods or choose one name until the RTTI method-table encoding and call signatures are reconciled.

The constructor body at `0x004F21DC` shows the ownership setup: it creates `ImgProc` from class reference `0x004EE01C` via `0x004EEDB4` and stores it at `+0x04`; obtains the editor/service object from class reference `0x004F0414` via `0x00404D5C` and stores it at `+0x24`; initializes the image processor through `0x004F0084`; creates `FResponseXML` via helper `0x004EB7F4` and stores it at `+0x34`; then calls `FResponseXML` interface slot `+0xB8` with callback address `0x004F22A4`. The callback's meaning and the XML response object's concrete class are not yet identified.

The connector then calls method address `0x004F2558`, reads `FResponseXML` through interface slot `+0x54`, and calls helper `0x004012F8`. That helper is an unresolved external/relocated thunk (IAT slot `0x0062ECDC` resolves outside the image); its generic callers include XML property setters and string-assignment paths, so it does not prove a specific output key. Preserve the output dictionary key, XML root/tag and response schema as unknown.

### 12.3.4 Scan request/response XML property inventory

The run-36 cross-reference of the external dictionary-assignment thunk `0x004012F8` identifies XML property setters used by the scanner request/response types:

| XML type | Property setter | Setter callsite |
|---|---|---:|
| `TXMLConfigType` | `Type` | `0x004EA10C` |
| `TXMLConfigType` | `DriverDialog` | `0x004EA244` |
| `TXMLConfigType` | `ImageEditor` | `0x004EA39C` |
| `TXMLConfigType` | `MultiJpegSupport` | `0x004EA4EC` |
| `TXMLConfigType` | `PreviousImageName` | `0x004EA654` |
| `TXMLOutputType` | `ForceSinglePageFiles` | `0x004EA820` |
| `TXMLResponseScanType` | `Status` | `0x004EB964` |
| `TXMLResponseScanType` | `ErrorCode` | `0x004EBAA4` |
| `TXMLScanedImageType` | `ImageName` | `0x004EBCAC` |
| `TXMLScanedImageType` | `Encoding` | `0x004EBDF4` |

- The run-37 VMT scan found class-name-associated candidate records for `TXMLResponseScanType` (`0x004EB2B0`), `TXMLScanedImageType` (`0x004EB614`), `TXMLConfigType` (`0x004E958C`), and `TXMLOutputType` (`0x004E98A4`). However, the scanner labels all four **unverified VMT candidates**; the parsed slots `+0x54`/`+0xB8` are unmapped/implausible values and the candidate parent metadata points to an external XMLRTL VMT. Therefore this run does not resolve the concrete class VMT or either interface slot. Do not treat these candidate addresses as confirmed VMTs. A new symbol-driven pass now traces every TD32 method and direct caller for these four XML classes, which is more reliable than assigning semantics from the candidate table.

The `TScanCommand` fields `FRequestXML` (`+0x30`) and `FResponseXML` (`+0x34`) are therefore XML request/response objects, not raw image buffers.
- `FResponseXML` is initialized through `TXMLResponseScanType.AfterConstruction` at `0x004EB7F4`. The `TScanCommand` constructor then calls its interface slot `+0xB8` with callback address `0x004F22A4`; the callback/event semantics remain unresolved.
- The public `TScanDocument` handler obtains the response object through interface slot `+0x54` and inserts that value into the outer result dictionary. The output key and final XML serialization are still unknown.
- These are recovered Delphi property names and setter callsites, not yet a complete XML schema. The XML hierarchy, element/tag spelling, required/optional status, values and relationship to `VerifyConstraints` must be verified from the XML resources and setter callers before implementing a parser/serializer.
- The same external thunk `0x004012F8` is used by many unrelated generated XML setters (Word, Excel, scanner and global response types); its target is outside this BPL image, so do not assign it a dictionary-specific semantic name.

Run 38's symbol-driven TD32 pass now recovers the actual getter/setter procedures even though the generic VMT scan remains unverified:

| XML class | Property | Getter VA | Setter VA | Setter's external XML assignment callsite |
|---|---|---:|---:|---:|
| `TXMLConfigType` (`Scanrequestxml`) | `Type` | `0x004E9FFC` | `0x004EA0B0` | `0x004EA047` |
| `TXMLConfigType` | `DriverDialog` | `0x004EA164` | `0x004EA1E8` | `0x004EA1AC` |
| `TXMLConfigType` | `ImageEditor` | `0x004EA2AC` | `0x004EA340` | `0x004EA3A9` |
| `TXMLConfigType` | `MultiJpegSupport` | `0x004EA400` | `0x004EA490` | `0x004EA4F9` |
| `TXMLConfigType` | `PreviousImageName` | `0x004EA55C` | `0x004EA5F8` | `0x004EA661` |
| `TXMLOutputType` (`Scanrequestxml`) | `ForceSinglePageFiles` | `0x004EA760` | `0x004EA7A8` | `0x004EA820` |
| `TXMLOutputType` | `Constraints` | `0x004EA8A8` | not present in this symbol pass | — |
| `TXMLResponseScanType` (`Scanresponsexml`) | `Status` | `0x004EB8BC` | `0x004EB908` | `0x004EB964` |
| `TXMLResponseScanType` | `ErrorCode` | `0x004EB9C0` | `0x004EBA48` | `0x004EBAA4` |
| `TXMLResponseScanType` | `Scanedimage` | `0x004EBB04` | not present in this symbol pass | — |
| `TXMLScanedImageType` (`Scanresponsexml`) | `ImageName` | `0x004EBB90` | `0x004EBC50` | `0x004EBCAC` |
| `TXMLScanedImageType` | `Encoding` | `0x004EBD0C` | `0x004EBD98` | `0x004EBDF4` |

The response object therefore exposes a scan-image collection property named `Scanedimage` (spelling as compiled), whose element type has `ImageName` and `Encoding`. This establishes the property-level object model but not the serialized XML element names, list cardinality/ownership, or the final outer result dictionary key. The property getters/setters route through XMLRTL interface helpers; the external `0x004012F8` call is an assignment helper, not a direct dictionary insertion.


### 12.4 ImageEdition and Upgrade are separate runtime methods

**Runtime `TImageEdition` — `0x005EF300` (TD32 label `TEditExcelWorkBook.PerformMethod`)**

- Embedded log prefix: `[Invoke EditImages]`.
- Reads dictionary keys `data` and `config`.
- Validates null/missing input and opens file streams through `0x004041BC`.
- The complete image-edit operation, plugin payload, output ownership and response schema remain unresolved.
- File/path values must be confined beneath an approved application data root.

**Runtime `TUpgradeEmwat` — `0x005EF24C` (TD32 label `TImageEdition.PerformMethod`)**

- Reads dictionary key `PlugIn`.
- Delegates to `@Applicationactivities.Finalization` at `0x0050357C` in module `imageEditionResposeXML`.
- The finalization routine distinguishes null input (status byte `2`) from missing file (status byte `1`), builds a path from the selected value and a static suffix, checks it with `FileExists`, and on the existing-file path opens a stream through `0x004041BC`.
- The routine also embeds an `[Invoke EditWordDocument]` log literal, but the runtime VMT target and the `UpgradeEmwat method called`/updater-file strings identify this as an old copied log message, not a Word handler.
- The path/payload format is still unknown. Treat `PlugIn` as untrusted and constrain it to an approved plugin/data root; reject absolute-path and traversal escapes.

Do not conflate the `PlugIn`/Finalization upgrade method with the runtime ImageEdition `data/config` method.

### 12.4.1 Preview UI output: page-indexed `_New.tif`

Run 32 traced `TfrmGScanPreview.Scan` (`0x0061DC80`) through its full page loop and resolved the relevant Win32/GEAR call boundary:

- It derives a base output path from the form's path field at `+0x458`, appends the exact suffix `_New.tif` (`0x0061DEE8`), and uses that same output path for the page loop.
- It obtains the selected source page count from the image-set interface and iterates page numbers from 1 through that count. The currently loaded page handle is reused for the matching current page; other pages are loaded with `IG_load_FD`.
- For each page it calls `CreateFileW` (`0x004026A4`) with creation disposition `OPEN_ALWAYS` (`4`), then calls `IG_save_FD` with the one-based page index and reserved argument `0`. The format argument is `0x40028` when form field `+0x434 == 1`, otherwise `0x80028`.
- Each created handle is closed with `CloseHandle` (`0x00402684`). The failure path marks the operation unsuccessful; after the loop the routine removes a partial output and restores the original path/state rather than reporting the failed output as complete.
- The observed call shape and same-path reopen with `OPEN_ALWAYS` strongly support one page-indexed multipage `_New.tif` output container for this preview UI routine. This does **not** prove that the connector's `TSetOfMultiPageImages` uses the same output ownership model.

Keep the two paths separate: the UI routine's `_New.tif` is grounded by direct file/create/save calls, while the public `ScanDocument` connector returns a `TResultImage`-derived object whose exact response key and path ownership remain open.

### 12.4.2 ImageGear scanner API boundaries

The same run resolved the following imported GEAR entry points:

- `0x004AFF28` → `IG_scan_source_select`
- `0x004AFF30` → `IG_scan_pages`
- `0x004AFED8` → `IG_error_check`
- `0x004AFEE0` → `IG_error_clear`
- `0x004AFEE8` → `IG_error_get`

These identities establish API boundaries only. Device/source selection arguments, callback ABI, cancellation semantics and exact error ownership still need caller-level validation; do not bind them directly to SANE options by name.

### 12.5 Linux implementation boundary

- Runtime `TEditWordDocument` is implemented as the current Linux default handler.
- A public Windows `TScanDocument` connector is confirmed at `0x005EEB48`; Linux has not yet implemented its request/result/response contract.
- Runtime `TImageEdition` is confirmed at `0x005EF300`, with `data` and `config` inputs; its operation and response serialization remain open.
- `TFaxDocument`, version, upgrade, Excel, comparison, settings, last-edited-documents and send-log methods have runtime VMT targets, but require their complete request/response contracts.
- Do not add handler stubs or infer HTTP methods from TD32 labels. Use the service runtime class/VMT map, not stale procedure labels.
- Canonicalize every request-derived file path beneath an approved root.

Evidence: `docs/EMWAT-SERVICE-EXECUTABLE-ANALYSIS.md`; run `45764043847` (connector/ScanCommand body traces); run `45764787287` (string and result-image symbol inventory); run `45765541247` (result-image body traces); run `45766302144` (remaining connector/helper traces).


### 12.6 Separate ImageEn I/O callsite family (run 32)

The same BPL also imports ImageEn `TImageEnMIO` methods. The run-32 IAT scan found these direct callsites:

| Imported method | IAT | Direct caller VAs |
|---|---:|---|
| `TImageEnMIO.Acquire` | `0x00630D84` | `0x0050A364` |
| `TImageEnMIO.SaveToFileTIFF` | `0x00630D90` | `0x0050B6A0` |
| `TImageEnMIO.SaveToFile` | `0x00630D8C` | `0x0050AFC4` |
| `TImageEnMIO.LoadFromFileAuto` | `0x00630D74` | `0x00508B88`, `0x0050A4D3` |
| `TImageEnMIO.GetParams` | `0x00630D78` | `0x00508CD1`, `0x00508CE6`, `0x0050B648`, `0x0050B659`, `0x0050B676` |
| `TImageEnMIO.PrintImage` | `0x00630D70` | `0x0050A7C3`, `0x0050A8A6`, `0x0050A999`, `0x0050AA85` |
| `TImageEnMIO.ExecuteOpenDialog` | `0x00630D80` | `0x0050A48C`, `0x0050A4BF` |
| `TImageEnMIO.ExecuteSaveDialog` | `0x00630D7C` | `0x0050AFAE` |

Run 36 thunk resolution confirms the wrappers are imported package methods from `PKIECtrl23.bpl`, not local BPL implementations: `@Iemio@TImageEnMIO@Acquire`, `SaveToFileTIFF`, `SaveToFile`, `LoadFromFileAuto`, `GetParams`, `PrintImage`, `ExecuteOpenDialog`, and `ExecuteSaveDialog`. For example, wrapper `0x004B012C` jumps through IAT `0x00630D84` to `PKIECtrl23.bpl!TImageEnMIO.Acquire`; `0x004B0114` jumps through IAT `0x00630D90` to `SaveToFileTIFF`. This confirms the external package boundary, not scanner-source semantics.

These are ImageEn imports/callsites, separate from the ImageGear `IG_save_FD` / `IG_save_file` path recovered in `TfrmGScanPreview.Scan` and `Save_Tiff_MultyPages`. Run 34 resolved the enclosing procedures: `Acquire` is called by `TfrmImageTools.InsertPicture` (`0x0050A29C`); `LoadFromFileAuto` is called by `FreeRotate` (`0x00508A90`) and `DeletePicture` (`0x0050A414`); `SaveToFileTIFF` is called by `btnPrinterSetupClick` (`0x0050B61C`); `SaveToFile` is called by `CreateParams` (`0x0050AF74`); `PrintImage` belongs to `DoPrintingPanel`; and the open/save dialog methods are used by image-tools handlers. This proves ImageEn is used by the image-tools acquisition/edit/save/print surface, but does not establish that its acquisition is the same scanner session as the ImageGear preview or the public `TScanDocument` connector. Keep the three paths separate until a shared file/session/result handoff is demonstrated.



## 12. Run 39/40 — scanner XML contract, ScanCommand state, and result ownership (2026-11-26)

### Response XML strings

The string inventory and response factory trace confirm:

- Root element: `response-scan` (version `1.0`).
- Child element: `scaned-image` (the single-`n` spelling is present in the original binary).
- Response properties/serialized keys: `status`, `errorCode`, `imageName`, and `encoding`.
- The Delphi property name is `Scanedimage`; the image entry exposes `ImageName` and `Encoding`.

### Request property surface

The recovered request-side object model exposes:

- `TXMLConfigType`: `type`, `driverDialog`, `imageEditor`, `multiJpegSupport`, `previousImageName`.
- `TXMLOutputType`: `forceSinglePageFiles`, `constraints`.
- `TXMLConstraintsType` property methods: `ColorDepth`, `MinResolution`, `MaxResolution`, `MaxFileSize`.

The first two groups have corresponding string keys in the binary inventory. The constraint names above are recovered Delphi property identities; do not assume their serialized casing/spelling until the XMLRTL serializer mapping is proven. The request root element and outer result-dictionary key are still open.

### TScanCommand object and request flow

Run 40 recovers `TScanCommand` at VMT `0x004F1F94`, instance size `0x40`, constructor `0x004F21DC`, and `DoRequest` `0x004F22E4`. Relevant fields:

| Offset | Field |
|---:|---|
| `+0x04` | `ImgProc` |
| `+0x08` | `Options` |
| `+0x20` | `ResultImage` |
| `+0x24` | `FEditorForm` |
| `+0x28` | `FCommandState` |
| `+0x29` | `FIsNextPageRequest` |
| `+0x2c` | `FPreviousReturnedFileName` |
| `+0x30` | `FRequestXML` |
| `+0x34` | `FResponseXML` |
| `+0x38` | `FHasConstraints` |

The constructor creates `TXMLResponseScanType` through `0x004EB7F4` and stores it at `+0x34`. `DoRequest` checks command/next-page state, uses `ResultImage`, and invokes constraint verification at `0x004F32F4`. The constraint-failure path contains a Persian retry prompt. Exact meanings of the numeric command-state values and the full response serialization/list cardinality are not yet established. RTTI contains spelling irregularities such as `FRequsetXML` and `FHasConstratints`; these are binary metadata typos, not recommended Linux API names.

### Result-file ownership

`TResultImage` keeps distinct values for the response filename and scan-file path: `GetResponseFileName` reads the response-name field at `+0x08`, while `GetScanFilePath` uses the scan path field at `+0x10` and serial/page helpers. Separate result classes exist for `TSetOfSinglePageImages` and `TSetOfMultiPageImages`. Binary strings include `%.3d`, `_P`, `_P000`, `_New.tif`, `.tif`, and `.jpg`.

Do not collapse response filename and physical output path into one property. The exact relationship between `imageName`, the response filename, the actual TIFF/JPEG file, and multi-page collection cardinality still requires the outer connector caller trace and a controlled runtime capture.

Evidence: Run 39 artifacts `15095104593`/`15096235579`; Run 40 Image artifact `15098092258`.


## 12.7 Run 42 — ScanCommand ownership and connector separation (2026-11-26)

Run `45782764971` completed successfully on commit `295fc6e513664abe211d2ebeeda1964f1fcd584f`; the Image/Scanner artifact is `15099188562`.

The new direct-constructor caller scan found:

- `TScanCommand.Create` (`0x004F21DC`) is directly called from `TFaxDocument.PerformMethod` at `0x005EECA1`.
- `TScanCommand.GetNextPage` (`0x004F2558`) is called from the same `TFaxDocument.PerformMethod` at `0x005EECBD`.
- The separately named `TScanDocument.PerformMethod` begins at `0x005EE82C`. Its recovered body reads the outer dictionary keys `wordConfig`, `wordBody`, `letterImages`, and `signData`, then calls helper `0x004B7724`. The direct callsite scan did not identify this method as the direct constructor caller of `TScanCommand`.

Therefore, do not collapse the `TFaxDocument`/scanner-command path into the public `TScanDocument` connector path based on names alone. The Run 43 trace now resolves the `TFaxDocument` route described in section 12.9. It still does not establish an indirect dispatch relationship between these methods or the live Almas invocation order.

The field-reference pass found 59 references across seven `TScanCommand` methods. It corroborates the instance field table already recorded in section 12.5:

- `ImgProc` at `+0x04`, `Options` at `+0x08`, `ResultImage` at `+0x20`, `FEditorForm` at `+0x24`.
- `FCommandState` at `+0x28`, `FIsNextPageRequest` at `+0x29`, `FPreviousReturnedFileName` at `+0x2C`, request/response XML objects at `+0x30`/`+0x34`, and `FHasConstratints` at `+0x38`.
- The code assigns numeric values 1, 2, 3 and 4 to `FCommandState` on different paths. Their public semantic meanings and their mapping to serialized `status`/ `errorCode` remain unresolved.
- Offset `+0x18` is read by `DoRequest` as an option passed to the image processor, but it is not named in the recovered published field table. Keep it unnamed.
- `VerifyConstraints` sets `FIsNextPageRequest` based on the request/previous-returned-filename path. This confirms a stateful next-page branch, not a stateless one-shot scan API.

The attempt to inspect parent VMT `0x0062EEA4` returned clearly invalid metadata (including an implausible instance size); reject that parser output and do not use it to infer inheritance. The response-helper IAT probe at `0x0062ECDC` also found no absolute import thunk; it did not resolve a serializer/helper identity.

Evidence:
- Run 42 Image artifact `15099188562`.
- Run 42 Word artifact `15098978072`.
- Run 42 workflow `45782764971`: all three jobs passed.
- All findings are static binary analysis; no physical scanner, ADF or duplex behavior is claimed.


## 12.8 Run 42 — response-name versus numbered scan-file paths

The expanded result-container traces in Image artifact `15099188562` make the filename ownership split more concrete:

- `TResultImage.GetResponseFileName` (`0x004ECF38`) returns the string stored at object offset `+0x08`.
- `TResultImage.GetScanFilePath` (`0x004ED03C`) operates on the separate path string at offset `+0x10`.
- `TResultImage.GetFileNamePath` (`0x004ECBD8`) starts from the `+0x10` path and delegates indexed resolution through `GetScanFilePath`; it is not simply an alias for the response filename.
- The single-page path routine parses the trailing three-character numeric suffix, adds the requested page/index offset, rejects values outside the 000–999 range, formats the replacement with `%.3d`, and replaces that trailing suffix. This is a bounded serial filename scheme.
- The multipage collection has a separate `GetScanFilePath` implementation (`0x004ED4C0`). It uses the stored page collection and the literal `_P` when constructing a page-specific path. The binary also contains `_P000`; do not assume that this exact literal is emitted in every branch without a runtime output fixture.
- The binary contains both `.tif` and `.jpg` image extensions, plus `_New.tif`; these strings alone do not establish which extension is used for every scan mode or whether the response name includes the extension.

This strengthens the Linux ownership model: keep at least three concepts separate—response-visible image name, collection/base output path, and resolved per-page physical file path. Apply bounded serial generation and collision handling explicitly; never derive a physical path by trusting an unconfined response filename.

The Run 43 `TFaxDocument.PerformMethod` trace is now available (section 12.9). The exact interaction between `forceSinglePageFiles`, the two collection constructors, response XML cardinality, and final extension still needs a controlled output capture.

Evidence:
- Run 42 Image artifact `15099188562`, especially `image-ui/result-path-callers/procedure-004ED03C.md`, `procedure-004ED4C0.md`, and the `TResultImage`/collection constructor traces.
- Run 42 workflow `45782764971` passed all three jobs.


## 12.9 Run 43 — ScanCommand response and FaxDocument paging trace (2026-11-26)

Workflow run `45783897821` completed successfully on analysis commit `e372fc188936ffcbeb54986630fe4981483a9577`. All three jobs passed: Word/Printer, Image/Scanner, and Native regression. The Image/Scanner artifact is `15099174916`.

### Connector boundary: two different handlers

The expanded trace confirms two distinct connector methods:

- `TScanDocument.PerformMethod` at `0x005EE82C` reads the outer dictionary keys `wordConfig`, `wordBody`, `letterImages`, and `signData`, then calls helper `0x004B7724`. The helper's complete semantic contract remains unresolved.
- `TFaxDocument.PerformMethod` at `0x005EEB48` directly constructs `TScanCommand` at `0x004F21DC`, calls `GetNextPage` at `0x004F2558`, then reads the command's `ResponseXML` object at `+0x34` and invokes its `Scanedimage` property accessor (VMT slot `+0x54`, corroborated by `TXMLResponseScanType.Get_Scanedimage` at `0x004EBB04`). The returned value is inserted into the handler's output dictionary. This is the concrete FaxDocument-to-ScanCommand path; it is not evidence that the public TScanDocument handler delegates to the same command.

The previous interpretation of both strings as input dictionary keys was incorrect. `0x005EED54` is the literal `.tmp`, passed to helper `0x00454B9C` to construct a local string/path value which is later passed to `GetNextPage`; it is not looked up in the input dictionary. `0x005EED6C` is the `document` key. At `0x005EEBAE`, `TFaxDocument.PerformMethod` calls the generic `TDictionary<String, Variant>.SetItem` implementation (`0x0046D2E4`) with that key and a local value slot. This is a dictionary write/update, not a read. The precise value type and intended semantics of the `document` entry remain unresolved; do not claim it is fetched as an input document payload.

### ScanCommand request and state

- `TScanCommand` instance size is `0x40`. The field table identifies `ImgProc` `+0x04`, `Options` `+0x08`, `ResultImage` `+0x20`, `FEditorForm` `+0x24`, `FCommandState` `+0x28`, `FIsNextPageRequest` `+0x29`, `FPreviousReturnedFileName` `+0x2C`, `FRequsetXML` `+0x30`, `FResponseXML` `+0x34`, and `FHasConstratints` `+0x38`.
- The constructor creates the image-processing object and options object, associates the editor form, and creates a `TXMLResponseScanType` response object through `0x004EB7F4`.
- `GetNextPage` calls `VerifyConstraints` and `LoadRequestXML`, branches on `FIsNextPageRequest`, consults `FPreviousReturnedFileName`, recognizes the literal `_P` in the prior name path, and updates `ResultImage`. This confirms a stateful continuation contract rather than a stateless one-shot call. The exact meaning of all internal state values and the full response cardinality remain unresolved.
- `DoRequest` distinguishes multiple command outcomes and writes observed `FCommandState` values 1, 2, and 3; `HasError` can additionally write 2 or 4. These numeric values must not be exposed as public status enums until their complete transitions and serialization are decoded.
- `VerifyConstraints` reads request XML fields including output/type, driver-dialog, image-editor, multi-JPEG support, previous-image name and constraints. The constraint model includes color depth, min/max resolution and max file size. Keep validation distinct from scanner acquisition and response serialization.

### Response XML model

The response object has separate `Status`, `ErrorCode`, and `Scanedimage` properties. The nested `TXMLScanedImageType` has separate `ImageName` and `Encoding` properties. Preserve these as distinct fields; do not infer that a response filename is the physical output path, that encoding is an extension, or that status can be inferred from file existence.

### ImageEn boundary and remaining gaps

Run 43 also expanded ImageEn wrapper and caller traces, including `TImageEnMIO.PrintImage`, `LoadFromFileAuto`, `GetParams`, and `PreviewPrintImage` callsites. These establish a separate ImageEn path alongside the ImageGear scanner path, but do not yet recover all method ABIs, object ownership, or the complete output-file/response cardinality.

The Run 43 evidence narrows the Linux contract but does not authorize a guessed protocol implementation. Next implementation work should preserve the separate handler contracts, response metadata, previous-page continuation state, and file-collection ownership. Before claiming Almas compatibility, obtain a controlled request/response capture and actual generated files for single-page and multipage cases. No physical scanner, ADF/duplex, or live Almas run was part of this workflow.


### Run 43 key cross-reference correction

The `.tmp` and `document` strings were decoded in the Run 43 Word/Printer artifact's `connector-handlers/handler-string-constants.md`, not in the Image/Scanner artifact. Cross-lane use-site inspection corrects the initial interpretation: `.tmp` is a literal passed to a helper to construct a temporary string/path; `document` is passed to generic `TDictionary<String, Variant>.SetItem`, so it is written/updated rather than read. The variant value's semantic type remains open.


### Native response-metadata model follow-up

The native `ScanResult` now has an optional `ScanResponseMetadata` member with separate raw `status`, `error_code`, and nested `scanned_image.image_name` / `encoding` fields. These are intentionally strings/optionals: no public status enum, encoding-to-extension mapping, or path inference is introduced. `scan_path`, `response_filename`, and the physical `ScanOutput` remain separate. A focused `test_scan_result` case verifies all four response fields remain independent from the physical output path and outer response filename. Code commit `faba1970efe44a36cd1a398711ac0f9eee6f2d9f`; test commit `6f75b41edb0643029479cbc2f1cf1f644d69ac6e`. Native verification subsequently passed on commit `35ffc42ef1717aecfdd065378c9cd249c3ff0ce8`: reverse-engineering workflow run `45786665652` completed its Native regression job successfully (C++ build, CTest, and Python bridge tests); the separate Native image core workflow run `45786665929` also passed its build, sanitizer, and Debian package lifecycle jobs. The initial missing-field-initializer warning was fixed by default-initializing `response_metadata`.


### Run 43 correction — dictionary direction and `.tmp` role

The initial cross-lane interpretation in this section and the first Run 43 notes was wrong and is superseded here. Disassembly at `0x005EEB89` loads the `.tmp` literal into `0x00454B9C`; no dictionary lookup occurs at that site. The resulting local string is passed as the `edx` argument to `TScanCommand.GetNextPage` at `0x005EECBD`. Separately, `0x005EEBAE` calls `0x0046D2E4`, whose TD32 symbol is `TDictionary<String, Variant>.SetItem`; its key is `document`. Thus the handler mutates/writes that dictionary entry, not reads it. The actual Variant value and purpose still need further tracing. The next workflow adds a skipdata-aware GetNextPage disassembly plus helper traces for `.tmp` construction and dictionary internals.


### Native metadata model CI result — 2026-11-26

The first CI attempt on the metadata test commit exposed `-Werror=missing-field-initializers` for the newly added optional member. `response_metadata` now has an explicit `{}` default member initializer. On follow-up commit `35ffc42ef1717aecfdd065378c9cd249c3ff0ce8`, reverse-engineering run `45786665652` passed the Native regression job, including C++ build, CTest, and Python bridge tests; Native image core run `45786665929` passed all three jobs (build/test, sanitizer, and Debian package lifecycle). This validates the native model/test change, not scanner hardware or Almas end-to-end behavior.

## 11. Run 48 — full GetNextPage trace and connector helper follow-up (2026-11-26)

Workflow run `45786665652` completed successfully in all three lanes (Native regression, Image/UI/VMT, Word/COM/Printer). The Image artifact `15102155195` and Word/Printer artifact `15101725038` were downloaded and inspected. Native C++/CTest and Python bridge regression passed.

The skipdata-aware trace covers all 1,340 bytes of `TScanCommand.GetNextPage` (`0x004F2558–0x004F2A93`); it marks 16 bytes as undecoded `.byte` data. Do not interpret those pseudo-instructions as code. The trace establishes:

- `VerifyConstraints` and `LoadRequestXML` are called before request handling; XML-load failure exits through the error path.
- The `FIsNextPageRequest` field at `TScanCommand+0x29` selects the paging branch.
- The paging branch compares `FPreviousReturnedFileName` (`+0x2C`) against a four-entry global string table, writes the matched index to byte field `+0x1D`, and checks for the `_P` marker. A positive marker check sets byte field `+0x1E` to 2.
- Both paging and new-document paths construct a `TResultImage` at `+0x20` through constructor `0x004EC8B4`. Constructor arguments include the selected string and format byte; the exact enum-to-format mapping is not yet established.
- The routine then uses virtual calls on `FResponseXML` (`+0x34`) and `ResultImage` to update response state and finalize the result. The virtual slot offsets alone do not prove XML property names or lifecycle semantics.

Helper follow-up:

- `0x00454B9C` receives the `.tmp` literal in `TFaxDocument.PerformMethod` and produces a derived local string through Delphi string/list operations. Exact caller-specific filename/path semantics remain unresolved.
- The `document` argument remains a dictionary write via `0x0046D2E4` (`TDictionary<String, Variant>.SetItem`), not a read.
- `0x0046D210` and `0x0046D2C0` are generic dictionary lookup/hash helpers; their callers include `AddOrSetValue`, `ContainsKey`, and `ContainsValue`. They do not decode the semantic meaning of the `document` Variant.
- `0x004738CC` is a string/Base64-related conversion wrapper; the current trace does not tie it to the `.tmp` value.

Open probes: recover the four global filename strings and meanings of state bytes `+0x1D/+0x1E`; resolve response XML virtual targets and exact `Scanedimage` updates; trace `TResultImage` ownership/finalization; clarify `0x00454B9C` without assuming the `.tmp` literal is a complete path.

Detailed artifact findings: `docs/REVERSE-ENGINEERING-RUN48.md`. No production native scanner behavior was changed, and this static analysis does not constitute physical scanner/printer or Wine runtime acceptance.
