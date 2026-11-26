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

These names are now confirmed symbol inventory only. The actual XML method names, dictionary keys, input validation, scan session state, response structure, error mapping, and page ownership are not yet established. The next workflow pass traces all eight procedures and their direct callers. Do not register Linux `ScanDocument` or `ImageEdition` handlers from names alone.

Evidence: run `45763574936`, artifact `15090488790`, files under `image-io/imageen/`.



## 12. Scanner connector and `TScanCommand` body traces (workflow run 45764043847)

The run-27 artifact now contains body-level traces for the two connector methods and the `TScanCommand` request lifecycle. The dictionary key strings have not yet been decoded, so no XML field names are assigned in this section.

### 12.1 `TScanDocument.PerformMethod` — `0x005EE82C`

- Receives a generic dictionary with `AnsiString` keys in `EDX` and a result dictionary in `ECX` (per Delphi register calling convention).
- Performs four key lookups through helper `0x0046DC8C`, using string constants at `0x005EE9F4`, `0x005EEA88`, `0x005EEAA0`, and `0x005EEABC`.
- Converts selected values through helper `0x004735D0`; one value is checked/normalized through helper `0x00401270`.
- Calls helper `0x004B7724` with the collected values and a local output pointer. It then inserts the returned value into the result dictionary through helper `0x004012F8`.
- Sets a byte flag at offset `+0x04` on the result object and notifies a global interface through vtable slot `+0x14` on both success and exception cleanup paths.

The method clearly performs dictionary-driven argument extraction and delegates to a scan/result operation. The key strings, dictionary value type, helper `0x004B7724` contract, result object schema, and relationship to the HTTP `Invoke` response remain unresolved.

### 12.2 `TImageEdition.PerformMethod` — `0x005EF24C`

- Performs one dictionary lookup through `0x0046DC8C` using string constant `0x005EF2F8`.
- Converts the selected value through `0x004735D0`, then calls helper `0x0050357C` with that value and the result dictionary.
- Uses a separate two-argument cleanup path and global interface notification.

This is a much smaller dictionary-driven operation than `TScanDocument.PerformMethod`. Its key, operation, result schema and image-editor object contract are still unknown.

### 12.3 `TScanCommand` request/page lifecycle

| Procedure | VA | Body-level observations |
|---|---:|---|
| `DoNewScan` | `0x004F22AC` | Clears/reinitializes object fields at `+0x24` and `+0x04`, masks an input flag with `0xFC`, and calls a state-reset helper; if the input flag is positive it calls an additional initialization helper. |
| `DoRequest` | `0x004F22E4` | Loads/parses request XML, checks the result image count, calls result/controller helpers, runs a constraint check, and updates status byte `+0x28` with several distinct values. One branch recurses after a result-object callback. |
| `GetNextPage` | `0x004F2558` | Calls `VerifyConstraints` and `LoadRequestXML`; uses a multi-file branch when flag `+0x29` is set; calls result-image helper `0x004EC8B4` with page/selection arguments (exact method identity unresolved) and stores the returned page/result object at `+0x20`; then calls `HasError`. |
| `HasError` | `0x004F2A94` | For the multi-file branch, constructs a path from field `+0x2C`, passes it to a result-object method, then calls result-object helper `0x004ECFC8` (exact method identity unresolved) and maps the result into status byte `+0x28`. |
| `LoadRequestXML` | `0x004F2B18` | Checks global service/controller state; obtains a string from an object at `+0x34`, combines it with global path/config state, and passes it to a global interface method at slot `+0x14`. Returns a Boolean-like result. |
| `VerifyConstraints` | `0x004F2C4C` | Reads multiple child/attribute values through XML-like interfaces (vtable slots `+0xAC`, `+0xB0`, `+0xB4`, `+0xB8`, `+0xBC`), compares them against static strings, and sets several validation/mode flags in the command object. |

The `TScanCommand` object stores distinct status/mode flags at offsets `+0x18), `+0x19), `+0x1A), `+0x1B), `+0x1C), `+0x1D), `+0x1E), `+0x28), and `+0x29), as well as result/path references at `+0x20), `+0x2C), `+0x30), and `+0x34`. These are object offsets only; names are deliberately not inferred from the values until XML strings and constructors are decoded.

### 12.4 Consequence for Linux handler design

- The procedure labelled `TScanDocument.PerformMethod` by TD32 at `0x005EE82C` is mapped by runtime VMT evidence to `TEditWordDocument.PerformMethod`; it is the Word handler, not a proven scanner endpoint.
- `TImageEdition.PerformMethod` is a separate dictionary-driven image-edition entry point.
- `TScanCommand` is a stateful internal request/result object with XML constraint validation and page/file iteration. Its relationship to a public connector method remains unproven; do not infer a `ScanDocument` endpoint from the TD32 class label.
- Result-image helper identities remain unresolved; preserve the generic `ScanResult` file-set/multipage model without mapping the unnamed helpers to specific methods.
- Do not register a Linux `ScanDocument` handler yet. Decode the `TImageEdition` key and `TScanCommand` XML constraint strings, trace helper `0x0050357C` and the result-image methods, and recover response serialization before implementing a wire-compatible scanner or image-edition method.

Evidence: run `45764043847`, artifact `15090469945`, `image-ui/procedure-005EE82C.md`, `procedure-005EF24C.md`, and `procedure-004F22AC.md` through `procedure-004F2C4C.md`.

