# EMWAT image/scanning call graph findings

## Analysis coverage

- The three image-related Binary DFM resources have been decoded and documented.
- Targeted TD32 disassembly resolves the main image-editor and scan-preview methods.
- Run 60 mapped 8,411 TD32 procedures to executable code and decoded 46,620 CALL instructions.
- Run 60 attributes imported ImageGear/ImageEn calls to bounded Delphi procedure symbols.
- Full caller table: `EmwatMethods-imaging-import-callers.md` in CI artifact for workflow run 42992351195.

## ImageGear import identity

Use the PE import descriptor, IAT slot, and actual thunk bytes as the source of truth. Older helper-symbol labels for these thunk addresses were wrong.

| Thunk VA | Imported API |
|---:|---|
| `0x004AFF38` | `IG_IP_crop` |
| `0x004AFEC8` | `IG_IP_rotate_multiple_90` |
| `0x004AFED0` | `IG_IP_flip` |
| `0x004AFED8` | `IG_error_check` |
| `0x004AFE88` | `IG_load_file` |
| `0x004AFE98` | `IG_load_FD` |
| `0x004AFE90` | `IG_save_file` |
| `0x004AFEA0` | `IG_save_FD` |

See [GEAR-API-CALLS.md](GEAR-API-CALLS.md) for the corrected API/caller table and per-method details.

## Confirmed Gear processing paths

- `TGearImgProc@$bdtr` calls `IG_IP_crop`, then `ReloadPage`, `GetImageResolution`, and marks the image modified.
- `TGearImgProc.RotateLeft` calls `IG_IP_rotate_multiple_90`, then reloads the page, refreshes resolution, and marks the image modified.
- `TGearImgProc.RotateRight` sets `EDX=3` and delegates to `RotateLeft`.
- `TGearImgProc.FlipHorizontal` calls `IG_IP_flip`, then reloads the page, refreshes resolution, and marks the image modified.
- `TGearImgProc.FlipVertical` sets `EDX=0` and delegates to `FlipHorizontal`.
- `TGearImgProc.SaveToFile` and `TGearImgProc.ScanToFile` both call `IG_save_file`.
- `TGearImgProc.SavePage` contains `IG_load_FD` and `IG_save_FD` calls; file-descriptor semantics and lifecycle still need tracing.
- `TWordViwer.EmbedTextToImage` calls `IG_load_file`; do not mislabel it as the application's main document-open path.

## GScan Preview handler calls

The bounded disassembly establishes these imported calls, which do not consistently match the Delphi handler names:

| Handler | API | EDX/direction value |
|---|---|---:|
| `btnLRotateClick` | `IG_IP_flip` | 0 |
| `btnRRotateClick` | `IG_IP_rotate_multiple_90` | 3 |
| `btnVFlipClick` | `IG_IP_rotate_multiple_90` | 1 |

After each imported call, the handlers invoke `LoadImageToGearHandle`, `cmbPagesChange`, and a virtual method at `[object VMT + 0xA8]`. Do not map the numeric direction values to visible actions until the exact ImageGear version and enum definitions are identified. The `btnHFlipClick` body changes a stored rectangle/flag and invalidates the view; it has no direct GEAR transform import in its bounded body.

## ImageEn call graph

Run 60 attributes these imported ImageEn methods to `TfrmImageTools` paths:

- `TImageEnMIO.Acquire` from `InsertPicture`.
- `TImageEnMIO.LoadFromFileAuto` from `FreeRotate` and `DeletePicture`.
- `TImageEnProc.CropSel` from `iePageHolderImageChange`.
- `TImageEnProc.RotateAndCrop` from `ActiveMe`.
- `TImageEnProc.Flip` from `AutoOrient`.
- `TImageEnView.SetZoom`, `XScr2Bmp`, and `YScr2Bmp` from viewer/toolbar/mouse handlers.
- `TImageEnMView.AppendImage` and related multi-image methods from image insertion and page-management handlers.

These are static caller attributions. Confirm argument setup and runtime paths before reproducing every behavior.

## Resolved inherited VCL virtual slots

The VMTs for `TfrmSimpleImageEditor`, `TfrmGScanPreview`, and `TfrmImageTools` share a parent VMT at `0x00630140`. The following inherited slots were resolved through the PE IAT:

| VMT byte offset | Imported VCL symbol | Interpretation |
|---:|---|---|
| `+0x64` | `vcl230.bpl!@Vcl@Forms@TCustomForm@GetClientRect$qqrv` | `TCustomForm.GetClientRect` |
| `+0x88` | `vcl230.bpl!@Vcl@Controls@TControl@SetEnabled$qqro` | `TControl.SetEnabled` |
| `+0xA8` | `vcl230.bpl!@Vcl@Controls@TWinControl@Invalidate$qqrv` | `TWinControl.Invalidate` |
| `+0x108` | `vcl230.bpl!@Vcl@Forms@TScrollingWinControl@AutoScrollEnabled$qqrv` | `TScrollingWinControl.AutoScrollEnabled` |

The virtual call at `[object+0xA8]` in the GScan handlers is therefore a redraw/invalidation request, not an image transformation.

## Important unresolved behavior

1. The exact ImageGear version shipped with EMWAT and its enum constants are unknown.
2. The GScan button names do not consistently match the imported API names and direction values. Do not infer the visible transformation from names.
3. File-descriptor load/save lifecycle and multi-page semantics need contextual tracing.
4. Scanner source-selection call references need validation against the complete method bodies.
5. ImageEn acquisition and viewer behavior need a native Linux design; WIA/TWAIN DLLs should not be emulated.

## Next reverse-engineering targets

1. Trace arguments and handle lifetime for `SavePage`, `NotifyEditor`, `ReloadPage`, and the ImageGear file-descriptor APIs.
2. Validate the scanner method call sites and inspect source selection/acquisition parameters.
3. Identify the exact ImageGear package/version and constants used by the shipped DLL.
4. Write the native image-backend specification (pixel buffer, color model, DPI, pages, errors, undo/dirty state) before coding the compatibility layer.
5. Implement and test the verified Gear image operations, then the separate ImageEn ImageTools workflow.


## Word XML image-field path — 2026-11-24

The Word field path is distinct from the standalone GScan/ImageTools UI:

- `TWordViwer.AddImagesToDoc` (`0x004C0410`) checks the XML field MIME type for `image/*` and routes image entries through `GetCaptionItemFont` (`0x004C19C0`).
- `GetCaptionItemFont` calls `GetImageResolution` (`0x004C2DE0`) and `EmbedTextToImage` (`0x004C436C`) before the later field/image insertion helpers.
- `GetCaptionItems` (`0x004C2B20`) parses caption style tokens including `Tahoma`, `bold`, `italic`, `underline`, and `strikeout`.
- The direction tokens `right`, `center`, `left`, `top`, `middle`, `bottom` map to numeric values 1–6 in the helper at `0x004C2DE0`. The symbol name says `GetImageResolution`, but these literals look like placement/alignment values; keep the semantic label provisional.
- The `EmbedTextToImage` bounded body calls GEAR32PD `IG_load_file`, `IG_image_resolution_get`, `IG_image_resolution_set`, and `IG_image_delete`. It proves image metadata normalization and handle cleanup, not text rasterization.

The separate [Word image-field pipeline analysis](WORD-IMAGE-FIELD-PIPELINE-ANALYSIS.md) records the exact boundaries and open questions.


### Caption composition vs. resolution metadata

The Word XML image path has two distinct helpers:
- `EmbedTextToImage` uses GEAR32PD to load the image and normalize its resolution metadata.
- `GetCaptionItemFont` calls helper `0x004C4DBC`, which iterates caption items, uses an image-view object and font/text metrics to calculate placement. If it returns false, the caller invokes `FillMSWFields` (`0x004C009C`) with a `Word.Fields` interface.

The caption helper is therefore separate from the GEAR resolution helper. Its final pixel-write/save operation and the exact Word COM calls in `FillMSWFields` remain open.


### Signature caption output confirmed

The helper `0x004C4DBC` logs `image saved to file. Params.Dpi: %d` and `Caption embeded to image.` after its caption-placement path. Its width-error branch calls `0x0044ABE4`, which is a custom modal dialog helper (VCL form setters/component enumeration), not the image save API. The `0x004C5AE8=4` value is the dialog control count. The actual image-save API remains unresolved.


The GEAR32PD helper's constants are now decoded: type 2 converts pixels/metre to DPI using 39.37 inches/metre; type 4 converts pixels/centimetre to DPI using 0.3937 inches/centimetre. The normalized values are written through `IG_image_resolution_set` mode 3.


The caption font parser at `0x004C2B20` selects direction-dependent font name/size/style slots from an eight-DWORD `TCaptionItem` record. It defaults empty font names to Tahoma, zero font size to 8, applies the caller's scale factor, and recognizes bold/italic/underline/strikeout tokens. Direction value 2 selects the second slot set; its exact RTL/LTR identity remains unconfirmed.
