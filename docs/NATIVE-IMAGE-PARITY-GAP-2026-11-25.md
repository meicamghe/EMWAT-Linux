# Native image model — parity gap against recovered EMWAT workflows

Date: 2026-11-25  
Inputs: current native image source/tests on `feature/recovery-retention-policy` plus static TD32 evidence in `docs/IMAGE-SCANNER-EDITOR-CALLGRAPH-INVENTORY.md`.

## Existing native foundation (confirmed from source)

- `ImageDocument` stores an ordered vector of pages, an active-page index, dirty state and generation counter.
- Each `ImagePage` carries a `PixelBuffer` and optional X/Y DPI metadata.
- Pixel operations currently include crop, horizontal/vertical flip and 90/180/270-degree rotations.
- Document operations include append page, select page and transform the active page.
- `load_into_document` decodes all pages before replacing the current document; failed decoding therefore does not partially replace the current document.
- `save_document` snapshots all pages, writes through a temporary file in the destination directory, atomically renames on success, then marks the document clean.
- Existing native tests exercise pixel transforms, padded-row crop, invalid geometry/metadata, multipage append/select and DPI swapping on quarter-turn rotation.

## Recovered EMWAT behaviors that need explicit parity work

| Recovered surface | Current native support | Gap / next implementation boundary |
|---|---|---|
| Single-page and multipage image result containers | Ordered multipage `ImageDocument` exists | Preserve the distinction between a set of single-page files and one multipage output, plus response filename and scan-path semantics |
| Scanner preview page selection | Active-page selection exists | Add a scanner-session/result adapter that retains original page index and result ownership |
| TIFF multipage save | Generic all-page codec save exists | Verify append/finalize/metadata behavior against the recovered `Save_Tiff_MultyPages` and `SaveCPinMultiPageFile` paths |
| Crop rectangle interaction | Pixel-space crop exists | Add preview-to-source coordinate mapping and UI selection state; don't mix display coordinates with source pixels |
| Rotate 90 / left / right and flips | Quarter turns and horizontal/vertical flips exist | Confirm sign/direction and orientation metadata parity from handler bodies |
| Free rotate | Not present in `PixelBuffer` API | Add arbitrary-angle rotation only after tracing angle units, interpolation, background fill, bounds and DPI behavior |
| Auto orientation | Not present in `PixelBuffer` API | Determine whether source uses EXIF orientation or scanner metadata, then implement explicit metadata normalization |
| Force single page | Not represented as a document-level save policy | Add an output policy that does not silently discard pages; preserve original multipage data |
| Insert/delete image in ImageEn multi-view | No explicit editor collection operations in `ImageDocument` | Model insert/delete/reorder as document edits with stable page identity and undoable transactions |
| Save/accept/cancel editor result | Dirty/generation exists, no recovered UI commit contract | Trace Register/Cancel handlers and implement explicit transaction/rollback semantics |

## Recommended implementation order

1. Keep `ImageDocument` as the pixel/page model; do not conflate it with scanner hardware session or external result-file ownership.
2. Add a separate `ScanResult`/output representation that can express either a page-file set or one multipage file and carries response path/name metadata.
3. Implement and test preview-coordinate-to-source-coordinate crop mapping.
4. Recover and test exact free-rotate and auto-orient contracts before adding pixel algorithms.
5. Add insert/delete/reorder and explicit accept/cancel transaction semantics after tracing the corresponding editor handlers.
6. Validate TIFF multipage roundtrips with generated fixtures and independent decoders, then compare a controlled Windows capture when available.

## Guardrails

- Do not assume that a TIFF extension proves a TIFF-only internal representation; the same controller supports multiple format values.
- Do not treat `TfrmGScanPreview`'s `Save_Tiff_MultyPages` method name as proof of exact TIFF tags, compression, page order or finalization behavior.
- Do not infer a valid Delphi VMT layout from heuristic candidates.
- No physical scanner or Windows hardware capture was part of this comparison.


## 2026-11-26 update — ImageGear transform imports are now identified

The expanded run-25 image artifact (`45763380148`, artifact `15090612978`) resolves:

- `0x004AFEC8` → `IG_IP_rotate_multiple_90`
- `0x004AFED0` → `IG_IP_flip`
- `0x004AFF00` → `IG_image_dimensions_get`
- `0x004AFEF0` → `IG_device_rect_set`

Direct callers include `TGearImgProc.RotateLeft`, `TGearImgProc.FlipHorizontal`, `TfrmGScanPreview.btnRRotateClick`, `btnLRotateClick`, `btnVFlipClick`, and `CalculateBestFitSize`. The names are not a reliable transform contract: for example, the handler named `btnLRotateClick` calls `IG_IP_flip`, while `btnVFlipClick` calls `IG_IP_rotate_multiple_90`. Preserve this mismatch as an open finding; do not assign UI semantics or axis/direction from Delphi method names alone.

`LoadImageToGearHandle` passes the handle at `this+0x428` and output pointers for fields `+0x42C`, `+0x430`, and `+0x434` to `IG_image_dimensions_get`. Their grouping is confirmed, but individual field meanings/units are not. `IG_device_rect_set` has direct callsites at `0x004EEF0F` and `0x0061D853`; its relation to preview geometry/crop still needs body-level tracing.

The current native quarter-turn and horizontal/vertical pixel transforms provide the required algorithmic building blocks, but exact parity still depends on recovering ImageGear argument semantics, transform direction, metadata updates, and device-rectangle behavior. No native transform code was changed in this update.


## 2026-11-26 update — Windows result-image class hierarchy confirms native output variants

Run 29 (`45764787287`, artifact `15091627434`) resolved the Windows result-image symbol hierarchy:

- `TResultImage.Create` at `0x004EC8B4` accepts a `UnicodeString` path and `TImageFormat`.
- Concrete collection classes exist: `TSetOfSinglePageImages` constructor at `0x004ED168` and `TSetOfMultiPageImages` constructor at `0x004ED298`.
- `TResultImage.NextFile` is `0x004ECF50`; `GetFilesCount` is `0x004ECC84`; `GetFileNamePath` is `0x004ECBD8`; `GetScanFilePath` is `0x004ED03C`; `GetResponseFileName` is `0x004ECF38`; `SetResponseFileName` is `0x004ED150`.
- `TResultImage.ShiftSerial` is `0x004ECFC8`, not a `HasError` method. Its body obtains a scan path through `GetScanFilePath` and checks file existence. `TScanCommand.HasError` calls this helper and maps the result to its own status flag.

This confirms two distinct Windows result-collection classes for single-page and multi-page image modes, but does not yet prove that `TSetOfMultiPageImages` maps one-to-one to a single `MultiPageFile`; both classes expose indexed file-path/count operations. The native `ScanOutput` variants are consistent with the recovered distinction, but the exact mapping remains open. Separately, the preview UI `Scan` routine's `_New.tif`/`IG_save_FD` path supports a single page-indexed multipage container. Exact file naming, serial increment rules, page-to-file ownership, and response serialization remain open; no native adapter or output policy was changed.
