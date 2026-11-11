# EMWAT imaging dependency map

Source: the PE import table extracted from `analysis-input/EmwatMethods.bpl1` (Run 57 artifact, commit `1ee94d5`). This is a static import inventory, not proof that every import is called on every workflow.

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

The PE import inventory confirms integration points but does not identify the exact scanner transport implementation or platform-specific device enumeration behavior.

## Native Linux implementation strategy

1. Keep a backend-neutral image model: pixel buffer, dimensions, color format, DPI/resolution, page index, and error state.
2. Implement the confirmed Gear operations behind a small adapter first: load, save, crop, rotate, flip, dimensions/resolution, and page count.
3. Keep acquisition separate from file I/O. Linux scanner integration should use a native scanning interface; do not emulate Windows WIA/TWAIN DLLs.
4. Treat ImageEn viewer/UI operations as application-level behavior to reimplement, not as a requirement to reproduce VCL controls.
5. Prioritize tracing actual call sites before implementing each imported API. Imports can be linked but unused on a particular execution path.
6. Obtain the exact `GEAR32PD.DLL` and ImageEn package versions (or vendor headers) before locking down version-sensitive behavior and error codes.

## Current confidence

- High: imported API names and module association, from PE import descriptors.
- High: `IG_IP_crop` is called by the traced crop path, and the UI coordinates are converted using Delphi `System.Round`.
- Medium: functional role inferred from API names for imports without traced call sites.
- Unverified: deployed library versions, all argument types/calling conventions, exact pixel-format semantics, and scanner driver behavior.
