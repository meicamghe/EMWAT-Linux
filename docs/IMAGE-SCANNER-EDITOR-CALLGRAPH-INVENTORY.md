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
- Constructs `TScanCommand` at `0x004F21DC`, calls `GetNextPage` at `0x004F2558` with the opened stream, reads the result through interface slot `+0x54` from the command's result field at `+0x34`, and inserts the returned value into the output dictionary.
- The output dictionary key and final response serialization are not yet decoded.

This confirms that a public Windows `ScanDocument` connector exists. It is not the same code path as the `TfrmGScanPreview.Scan` UI method; it consumes a document/result request and delegates to the stateful `TScanCommand`/result-image layer. The `document` path value is untrusted and must be confined beneath an approved application data/output root in any Linux implementation.

### 12.3 Internal `TScanCommand` request/page lifecycle

| Procedure | VA | Body-level observations |
|---|---:|---|
| `DoNewScan` | `0x004F22AC` | Clears/reinitializes object fields at `+0x24` and `+0x04`, masks an input flag with `0xFC`, and calls a state-reset helper; positive input flags trigger additional initialization. |
| `DoRequest` | `0x004F22E4` | Loads/parses request XML, examines result-image state, calls result/controller helpers, validates constraints, and updates status byte `+0x28` with distinct values. One branch recurses after a result-object callback. |
| `GetNextPage` | `0x004F2558` | Calls `VerifyConstraints` and `LoadRequestXML`; uses a multi-file branch when flag `+0x29` is set; constructs a `TResultImage` via `0x004EC8B4` (`UnicodeString` path and `TImageFormat`), stores the returned object at `+0x20`, then calls `HasError`. |
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

### 12.5 Linux implementation boundary

- Runtime `TEditWordDocument` is implemented as the current Linux default handler.
- A public Windows `TScanDocument` connector is confirmed at `0x005EEB48`; Linux has not yet implemented its request/result/response contract.
- Runtime `TImageEdition` is confirmed at `0x005EF300`, with `data` and `config` inputs; its operation and response serialization remain open.
- `TFaxDocument`, version, upgrade, Excel, comparison, settings, last-edited-documents and send-log methods have runtime VMT targets, but require their complete request/response contracts.
- Do not add handler stubs or infer HTTP methods from TD32 labels. Use the service runtime class/VMT map, not stale procedure labels.
- Canonicalize every request-derived file path beneath an approved root.

Evidence: `docs/EMWAT-SERVICE-EXECUTABLE-ANALYSIS.md`; run `45764043847` (connector/ScanCommand body traces); run `45764787287` (string and result-image symbol inventory); run `45765541247` (result-image body traces); run `45766302144` (remaining connector/helper traces).
