# EMWAT imaging dependency map

Source: the PE import table extracted from `analysis-input/EmwatMethods.bpl1` (Run 57 onward). The import inventory is static evidence, not proof that every import runs in every workflow.

## Accusoft ImageGear — `GEAR32PD.DLL`

The BPL imports the following native image/scan functions:

| API | Evidence-backed role |
|---|---|
| `IG_load_file`, `IG_load_FD` | Load image from path / file descriptor |
| `IG_save_file`, `IG_save_FD` | Save image to path / file descriptor |
| `IG_page_count_get` | Query page count |
| `IG_image_is_valid` | Validate image handle |
| `IG_image_dimensions_get` | Query image dimensions |
| `IG_image_resolution_get`, `IG_image_resolution_set` | Read/write resolution |
| `IG_image_rect_set`, `IG_device_rect_set` | Set image/device rectangles |
| `IG_IP_crop` | Crop image; call target resolved at VA `0x004AFF38` |
| `IG_IP_rotate_multiple_90` | Rotate by multiples of 90 degrees |
| `IG_IP_flip` | Flip image |
| `IG_IP_color_promote` | Promote image color depth/format |
| `IG_save_JPEG_quality_set` | Set JPEG save quality |
| `IG_display_image` | Display/render image |
| `IG_scan_source_select`, `IG_scan_pages` | Select scanner source and acquire pages |
| `IG_error_get`, `IG_error_clear`, `IG_error_check` | ImageGear error-state handling |
| `IG_image_delete` | Release image handle |
| `IG_ext_load`, `IG_ext_unload` | Load/unload ImageGear extensions |

There are two import descriptors with casing variants `GEAR32PD.Dll` and `GEAR32PD.DLL`; preserve this observation in compatibility work, but Windows DLL lookup is case-insensitive. The exact deployed DLL version and matching headers are not yet present in the repository.

### Run 59: import thunk and call-site analysis

The revised raw-x86 scanner found **101 import thunks for 110 ImageGear/ImageEn import slots** across two executable sections. It searches canonical x86 forms (`FF 25` indirect jump thunks, `E8` relative calls, and `FF 15` direct IAT calls). The generated full table is `EmwatMethods-imaging-import-callers.md` in the CI artifact.

Selected ImageGear references:

| API | Thunk VA | Call-site VA(s) | Interpretation / validation |
|---|---:|---|---|
| `IG_IP_crop` | `0x004AFF38` | `0x004EEE44` | Validated in `TGearImgProc@$bdtr`; passes a local 16-byte `TRect`, then reloads page and reads resolution |
| `IG_IP_rotate_multiple_90` | `0x004AFEC8` | `0x004EF187`, `0x0061E5FC`, `0x0061E62C` | The first is inside `TGearImgProc.RotateLeft`; `RotateRight` dispatches to that method with direction value 3 |
| `IG_IP_flip` | `0x004AFED0` | `0x004F021F`, `0x0061E5CC`, `0x0061E65C` | First is inside `TGearImgProc.FlipHorizontal`; `FlipVertical` dispatches to it |
| `IG_load_file` | `0x004AFE88` | `0x004C43C7` | Static reference; containing method needs a focused disassembly pass |
| `IG_load_FD` | `0x004AFE98` | `0x004EF2D3`, `0x004EF2F9`, `0x004EF60B`, `0x0061D411`, `0x0061DD94` | File-descriptor load path; some references lie in the Gear image-processing region |
| `IG_save_FD` | `0x004AFEA0` | `0x004EF64E`, `0x0061DDE1`, `0x0061DDF8` | File-descriptor save path |
| `IG_save_file` | `0x004AFE90` | `0x004EEA8A`, `0x004EF7E6`, `0x004EF94F`, `0x0061D977`, `0x0061DA40`, `0x0061DA5C` | File save/load-related branches; inspect argument setup before implementing |
| `IG_scan_pages` | `0x004AFF30` | `0x004EFA96`, `0x0061E036`, `0x0061E059` | Scanner acquisition path |
| `IG_scan_source_select` | `0x004AFF28` | `0x004EFF83`, `0x0061E3DF` | Scanner source selection path |

Selected ImageEn references:

| Imported method | Thunk VA | Call-site VA(s) |
|---|---:|---|
| `TImageEnMIO.Acquire` | `0x004B012C` | `0x0050A364` |
| `TImageEnMIO.LoadFromFileAuto` | `0x004B014C` | `0x00508B88`, `0x0050A4D3` |
| `TImageEnMIO.SaveToFile` | `0x004B011C` | `0x0050AFC4` |
| `TImageEnMIO.SaveToFileTIFF` | `0x004B0114` | `0x0050B6A0` |
| `TImageEnProc.CropSel` | `0x004B0244` | `0x0050B770` |
| `TImageEnProc.RotateAndCrop` | `0x004B0264` | `0x0050ADAE` |
| `TImageEnProc.Rotate` | `0x004B024C` | `0x0050AB7D` |
| `TImageEnProc.Flip` | `0x004B023C` | `0x0050ACEE` |
| `TImageEnMView.AppendImage` | `0x004B01B4` | `0x0050A496` |
| `TImageEnView.SetZoom` | `0x004B0274` | `0x00509E11`, `0x00509E67`, `0x00509E8D` |

Important symbol-resolution caveat: some older TD32 helper-symbol labels disagree with the PE import-descriptor-to-IAT mapping for individual thunk addresses. For external DLL function identity, the import descriptor + IAT slot + decoded `FF 25` target is the stronger evidence. Do not infer an imported API name solely from a helper-symbol label when the two conflict.

The scanner is a byte-pattern discovery pass. Candidate call-site addresses can occur accidentally in data or misaligned bytes; validate the surrounding instruction stream before treating every row as a real call. The Crop, RotateLeft, FlipHorizontal, and selected Gear call sites above were checked against the emitted disassembly.

## ImageEn — `PKIECtrl23.bpl`

The BPL also imports a substantial ImageEn API surface. Notable methods include:

- I/O and acquisition: `TImageEnMIO.LoadFromFileAuto`, `SaveToFile`, `SaveToFileTIFF`, `Acquire`, `ExecuteOpenDialog`, `ExecuteSaveDialog`, `GetParams`.
- Image processing: `TImageEnProc.RotateAndCrop`, `Rotate`, `CropSel`, `Flip`, `SkewDetection`, `SetUndoLimit`.
- Viewer/coordinate support: `TImageEnView.Fit`, `FitToWidth`, `FitToHeight`, `XScr2Bmp`, `YScr2Bmp`, `SetZoom`.
- Multi-image/thumbnails: `TImageEnMView.AppendImage`, `InsertImage`, `SetImage`, `GetImageCount`, `GetImageOriginalWidth`, `GetImageOriginalHeight`, selection and move methods.
- Bitmap bridge: `TIEBitmap.CopyFromTBitmap`, `TIEBitmap.GetCanvas`, `TImageEnView.SetExternalBitmap`.

The presence of these imports means EMWAT's imaging functionality is not a single ImageGear-only pipeline. ImageGear is directly used by the traced `TGearImgProc` editor path, while ImageEn supplies additional acquisition, I/O, viewer, processing, and multi-image facilities. Do not assume that replacing `IG_IP_crop` alone replaces all image workflows.

## Scanner interfaces

The import table also contains ImageEn WIA/TWAIN units:

- `@Iewia@TIEWia@GetRoot`
- TWAIN unit initialization/finalization symbols
- `TImageEnMIO.Acquire`

ImageGear scanner calls (`IG_scan_source_select`, `IG_scan_pages`) are also present in the executable call-site map. The static references confirm integration points but do not identify the exact scanner transport implementation or platform-specific device enumeration behavior.

## Native Linux implementation strategy

1. Keep a backend-neutral image model: pixel buffer, dimensions, color format, DPI/resolution, page index, and error state.
2. Implement the confirmed Gear operations behind a small adapter first: load, save, crop, rotate, flip, dimensions/resolution, and page count.
3. Keep acquisition separate from file I/O. Linux scanner integration should use a native scanning interface; do not emulate Windows WIA/TWAIN DLLs.
4. Treat ImageEn viewer/UI operations as application-level behavior to reimplement, not as a requirement to reproduce VCL controls.
5. Trace and validate argument setup at call sites before implementing each imported API. Imports and raw byte-pattern hits alone do not prove runtime use.
6. Obtain the exact `GEAR32PD.DLL` and ImageEn package versions (or vendor headers) before locking down version-sensitive behavior and error codes.

## Current confidence

- High: imported API names and module association, from PE import descriptors.
- High: `IG_IP_crop` is called by the traced crop path, and the UI coordinates are converted using Delphi `System.Round`.
- High: the identified RotateLeft/FlipHorizontal API calls and the listed ImageEn call targets are supported by thunk resolution and static call references; runtime execution remains unverified.
- Medium: the remaining call-site candidates pending contextual disassembly.
- Unverified: deployed library versions, all argument types/calling conventions, exact pixel-format semantics, and scanner driver behavior.


### Run 60: TD32-bounded caller attribution

Run 60 replaced the broad raw-byte CALL scan with a second pass over bounded TD32 procedure ranges. It mapped **8,411 procedures** to executable code and decoded **46,620 CALL instructions**. The report `EmwatMethods-imaging-import-callers.md` now includes the Delphi caller symbol for each decoded call. This is materially stronger than Run 59's byte-pattern-only candidates, but remains static evidence: it does not prove a particular UI path was executed at runtime.

Selected caller relationships from Run 60:

| Imported API | Delphi caller | Call-site VA | Evidence / interpretation |
|---|---|---:|---|
| `IG_IP_crop` | `TGearImgProc@$bdtr` | `0x004EEE44` | Strong: bounded method disassembly shows a 16-byte local rectangle copied from the argument, then the image handle and rectangle are pushed to the ImageGear thunk |
| `IG_IP_rotate_multiple_90` | `TGearImgProc.RotateLeft` | `0x004EF187` | Strong: method checks image handle, passes direction argument, calls ImageGear, reloads page, refreshes resolution, marks image modified |
| `IG_IP_rotate_multiple_90` | `TGearImgProc.RotateRight` | `0x004EF1AC` | Strong: wrapper sets direction value 3 and dispatches to `RotateLeft` |
| `IG_IP_flip` | `TGearImgProc.FlipHorizontal` | `0x004F021F` | Strong: direct call from named processing method |
| `IG_save_file` | `TGearImgProc.SaveToFile` | `0x004EF7E6` | Strong: argument setup is visible in the bounded method; image handle, output path and format/compression-related values are prepared before call |
| `IG_save_file` | `TGearImgProc.ScanToFile` | `0x004EF94F` | Strong: separate scan-to-file save path |
| `IG_save_FD` | `TGearImgProc.SavePage` | `0x004EF64E` | Static caller attribution; inspect the full method and file-descriptor lifecycle before porting |
| `IG_load_FD` | `TGearImgProc.NotifyEditor` | `0x004EF2D3`, `0x004EF2F9` | Static caller attribution; likely editor notification/page handoff path, argument semantics still need tracing |
| `IG_load_FD` | `TGearImgProc.SavePage` | `0x004EF60B` | Static caller attribution; likely part of page/file-descriptor handling, not enough evidence to label the exact semantics |
| `IG_load_file` | `TWordViwer.EmbedTextToImage` | `0x004C43C7` | Strong caller name, but this is an embedded-text/image workflow, not evidence of the main document-open path |
| `IG_scan_pages` | `TGearImgProc.SelectScanner` | `0x004EFA96` | Static caller attribution; scanner workflow entry point candidate |
| `IG_scan_pages` | `TfrmGScanPreview.SelectScanner` | `0x0061E036`, `0x0061E059` | Static caller attribution; preview-form scanner path |
| `TImageEnMIO.Acquire` | `TfrmImageTools.InsertPicture` | `0x0050A364` | Strong symbol-level link to ImageTools picture insertion/acquisition |
| `TImageEnMIO.LoadFromFileAuto` | `TfrmImageTools.FreeRotate`, `TfrmImageTools.DeletePicture` | `0x00508B88`, `0x0050A4D3` | Static caller attribution; inspect method context before interpreting why the image is loaded |
| `TImageEnProc.CropSel` | `TfrmImageTools.iePageHolderImageChange` | `0x0050B770` | Static caller attribution; image-selection/change handler invokes selection crop |
| `TImageEnProc.RotateAndCrop` | `TfrmImageTools.ActiveMe` | `0x0050ADAE` | Static caller attribution; ImageTools active-image path |
| `TImageEnProc.Flip` | `TfrmImageTools.AutoOrient` | `0x0050ACEE` | Static caller attribution; automatic-orientation path |

Some Run 60 rows have caller names that look semantically surprising (for example, scanner or flip APIs attributed to unrelated-looking event names). Treat those as candidates until the complete containing method, call argument setup, and control-flow path have been inspected. The table above labels those rows as static attribution rather than confirmed user-visible behavior. The Crop, RotateLeft/Right, FlipHorizontal, SaveToFile, and ScanToFile relationships have direct supporting disassembly in the artifact.

### Updated implementation priority

1. **ImageGear core editor adapter:** handle ownership/lifetime, dimensions, resolution, crop, rotate, flip, load/save and error handling. Crop/rotate/flip/save now have named callers and useful argument setup evidence.
2. **Multi-page and file-descriptor semantics:** inspect `LoadPage`, `SavePage`, `NotifyEditor`, `ReloadPage`, and page-count call paths. Do not assume `IG_load_FD`/ `IG_save_FD` are interchangeable with pathname I/O.
3. **Scanner acquisition:** inspect both `TGearImgProc.SelectScanner` and `TfrmGScanPreview.SelectScanner`, then map the actual scanner API parameters. Linux should use a native SANE backend rather than reproducing WIA/TWAIN.
4. **ImageEn ImageTools:** port its separate insert-picture, auto-orient, crop-selection, zoom/viewer and multi-image workflows. This is a second imaging subsystem, not just a UI wrapper around the Gear adapter.
5. **Wordviewer embedded-image workflow:** trace `TWordViwer.EmbedTextToImage` independently; its `IG_load_file` call must not be mistaken for the main EMWAT document loader.

Run 60 is analysis-only. No native ImageGear/ImageEn replacement has been implemented yet, and no claim of feature parity is made.
