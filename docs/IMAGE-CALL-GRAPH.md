# EMWAT image/scanning call graph findings

## Analysis coverage

- 24 target procedures were disassembled using the corrected TD32 segment-relative mapping.
- 73 unique direct-call addresses were collected.
- Direct calls were resolved against 8,411 TD32 procedure records.
- Indirect calls (VCL/Delphi virtual dispatch) remain unresolved until the relevant object/vtable is identified.
- CI artifact: `EmwatMethods-helper-symbols.md` from workflow run 42978953736.

## GEAR API calls confirmed

| API | Observed use |
|---|---|
| `IG_display_image` | Called from `TGearImgProc.Rotate90` and `SaveToFile` |
| `IG_IP_rotate_multiple_90` | Called from `SaveToFile` and `ScanToFile` |
| `IG_IP_flip` | Called from `TGearImgProc.RotateLeft`; `RotateRight` delegates to it with EDX=3; also called by `btnRRotateClick` with EDX=3 and `btnVFlipClick` with EDX=1 |
| `IG_error_check` | Called from `TGearImgProc.FlipHorizontal` and `btnLRotateClick` |
| `IG_load_FD` | Used in save/scan file handling |
| `IG_save_JPEG_quality_set` | Used in save/scan paths |

The ImageGear API documentation describes `IG_IP_flip` as horizontal/vertical flipping and `IG_IP_rotate_multiple_90` as 90/180/270-degree rotation. The exact enum constants for the deployed GEAR version remain to be verified:
- https://help.accusoft.com/ImageGear/v15/Unix/Core/IG_Unix.pdf
- https://help.accusoft.com/ImageGear/v21.0/Linux/IGDLL-19-529.html

## Internal calls confirmed

- `TGearImgProc.RotateLeft` calls `ReloadPage` and `GetImageResolution`.
- `TGearImgProc.RotateRight` delegates to `RotateLeft` after setting EDX=3.
- `TGearImgProc.FlipVertical` delegates to `FlipHorizontal`.
- `TGearImgProc.SaveToFile` calls `SavePage` on one path.
- `TfrmSimpleImageEditor.CropImage` calls `GetImageBPP` and then `btnRegisterClick`; two virtual calls at vtable offset `0x88` remain to be resolved.
- GScan preview button handlers call `LoadImageToGearHandle` and `cmbPagesChange` after their GEAR API call.
- GScan preview button handlers also make a virtual call at vtable offset `0xA8`; this may be part of the visible update/operation path.

## Important unresolved behavior

The GScan preview button names and direct calls do not yet line up cleanly:
- `btnLRotateClick` calls `IG_error_check` with EDX=0.
- `btnRRotateClick` calls `IG_IP_flip` with EDX=3.
- `btnVFlipClick` calls `IG_IP_flip` with EDX=1.

Do not translate these values into Linux operations based on names alone. The exact GEAR version, enum definitions, and virtual method at `[object vtable + 0xA8]` must be identified first.

## Next reverse-engineering targets

1. Resolve vtable offsets `0x88` and `0xA8` to their object types and method names.
2. Identify the exact GEAR32PD version and its `IG_FLIP_*` / `IG_ROTATE_*` constants.
3. Trace `TGearImgProc.Rotate90`'s virtual call through the object at `[self+0x28]`.
4. Implement the verified transformation sequence in the native Linux image layer and test it against the Windows app's output.
