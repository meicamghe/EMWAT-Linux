# EMWAT image/scanning call graph findings

## Analysis coverage

- 24 target procedures were disassembled using the corrected TD32 segment-relative mapping.
- 73 unique direct-call addresses were collected.
- Direct calls were resolved against 8,411 TD32 procedure records.
- Four shared inherited VMT slots used by the three form classes were resolved through the PE import address table (IAT) to VCL 23.0 package symbols.
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
- `TfrmSimpleImageEditor.CropImage` calls `GetImageBPP` and then `btnRegisterClick`; its virtual call at vtable offset `0x88` resolves to inherited `TControl.SetEnabled` from `vcl230.bpl`.
- GScan preview button handlers call `LoadImageToGearHandle` and `cmbPagesChange` after their GEAR API call.
- Their virtual call at vtable offset `0xA8` resolves to inherited `TWinControl.Invalidate` from `vcl230.bpl`, i.e. a UI invalidation/redraw request rather than an image transform.

## Resolved inherited VCL virtual slots

The VMTs for `TfrmSimpleImageEditor`, `TfrmGScanPreview`, and `TfrmImageTools` all point to the same parent VMT at `0x00630140`. Their shared inherited slots resolve as follows:

| VMT byte offset | Imported VCL symbol | Interpretation |
|---:|---|---|
| `+0x64` | `vcl230.bpl!@Vcl@Forms@TCustomForm@GetClientRect$qqrv` | `TCustomForm.GetClientRect` |
| `+0x88` | `vcl230.bpl!@Vcl@Controls@TControl@SetEnabled$qqro` | `TControl.SetEnabled` |
| `+0xA8` | `vcl230.bpl!@Vcl@Controls@TWinControl@Invalidate$qqrv` | `TWinControl.Invalidate` |
| `+0x108` | `vcl230.bpl!@Vcl@Forms@TScrollingWinControl@AutoScrollEnabled$qqrv` | `TScrollingWinControl.AutoScrollEnabled` |

This resolves the previously ambiguous virtual calls at `[object+0x88]` and `[object+0xA8]`: they are inherited VCL UI-state/redraw operations, not custom image-processing methods. The imported symbol names are taken directly from the PE IAT; the parent RTTI byte sequence itself is not yet cleanly decoded.

## Important unresolved behavior

The GScan preview button names and direct calls do not yet line up cleanly:
- `btnLRotateClick` calls `IG_error_check` with EDX=0.
- `btnRRotateClick` calls `IG_IP_flip` with EDX=3.
- `btnVFlipClick` calls `IG_IP_flip` with EDX=1.

Do not translate these values into Linux operations based on names alone. The exact GEAR version, enum definitions, and virtual method at `[object vtable + 0xA8]` must be identified first.

## Next reverse-engineering targets

1. Identify the exact GEAR32PD version and its `IG_FLIP_*` / `IG_ROTATE_*` constants.
2. Trace `TGearImgProc.Rotate90`'s virtual call through the object at `[self+0x28]`.
3. Resolve the remaining virtual dispatches in the image editor by tracing the actual object VMTs at each call site (rather than assuming the form VMT).
4. Implement the verified transformation sequence in the native Linux image layer and test it against the Windows app's output.

## TGearImgProc.Rotate90 dispatch trace (run 38)

The call at `0x004EF165` is **not** one of the form VMT slots listed above. The method does this:

1. Checks the object pointer stored at `[TGearImgProc+0x28]`.
2. Calls `IG_display_image` with the image handle at `[self+0x38]` and a local output value.
3. Stores the returned value at `[self+0x4C]`.
4. Loads the object pointer from `[self+0x28]`, reads its VMT pointer from `[object]`, then invokes the **first VMT entry** via `call dword ptr [vmt]`. Two stack arguments are prepared immediately before this dispatch (the output value and zero).
5. Treats the virtual method's EAX result as a signed 64-bit value (via `cdq`) and passes that pair to internal routine `0x004035D8`; stores that routine's EAX result at `[self+0x30]`.

The virtual target belongs to the object held in the field at offset `+0x28`, not to `TGearImgProc` itself and not to the three form classes. Its class/VMT and the semantics of `0x004035D8` are still unresolved. Do not substitute `TWinControl.Invalidate` or another inherited form slot here.

### Revised next steps

1. Resolve the runtime/static type and VMT of the object held at `[TGearImgProc+0x28]`; trace its constructor/assignment sites and first VMT entry.
2. Disassemble and identify internal routine `0x004035D8`, including its callers and return-value contract.
3. Only then decide whether `Rotate90`'s virtual call is display/rendering, geometry, or another operation.
4. Obtain the exact deployed `GEAR32PD.DLL` before implementing enum/ABI-dependent operations.
