# GEAR API call resolution

## Confirmed helper thunks

TD32 procedure symbols resolve the direct-call targets in `EmwatMethods.bpl1` to these imported GEAR functions:

| VA | TD32 symbol | Evidence |
|---:|---|---|
| `0x004AFEA8` | `IG_display_image` | 6-byte import thunk |
| `0x004AFEC0` | `IG_IP_rotate_multiple_90` | 6-byte import thunk |
| `0x004AFEC8` | `IG_IP_flip` | 6-byte import thunk |
| `0x004AFED0` | `IG_error_check` | 6-byte import thunk |

The helper-symbol report also resolves internal calls:

| VA | TD32 procedure |
|---:|---|
| `0x004EF0E4` | `TGearImgProc.ReloadPage` |
| `0x004EEEC4` | `TGearImgProc.GetImageResolution` |
| `0x0061D36C` | `TfrmGScanPreview.LoadImageToGearHandle` |
| `0x0061E680` | `TfrmGScanPreview.cmbPagesChange` |

## Relevant ImageGear API semantics

Accusoft's ImageGear documentation describes `IG_IP_flip(HIGEAR, nDirection)` as a horizontal or vertical flip. It describes `IG_IP_rotate_multiple_90(HIGEAR, nMult_90_Mode)` as a 90/180/270-degree rotation. The exact enum values must be verified against the ImageGear version shipped with EMWAT, rather than copied from a newer SDK.

References:
- https://help.accusoft.com/ImageGear/v21.0/Linux/IGDLL-19-529.html
- https://help.accusoft.com/ImageGear/v21.0/Linux/IGDLL-06-025.html

## Observed call paths

- `TGearImgProc.RotateLeft` calls `IG_IP_flip` with the incoming EDX value, then `ReloadPage` and `GetImageResolution`.
- `TGearImgProc.RotateRight` sets EDX to `3` and delegates to `RotateLeft`.
- `TGearImgProc.Rotate90` calls `IG_display_image`, then invokes a virtual method on the object stored at `[self+0x28]`, and updates a field at `[self+0x30]`. It does not directly call `IG_IP_rotate_multiple_90` in its own body.
- `TGearImgProc.SaveToFile` calls `IG_IP_rotate_multiple_90` before proceeding with its save path.
- `TfrmGScanPreview.btnRRotateClick` calls `IG_IP_flip` with EDX=`3`, then reloads the image handle and changes the page.
- `TfrmGScanPreview.btnVFlipClick` calls `IG_IP_flip` with EDX=`1`, then reloads the image handle and changes the page.
- `TfrmGScanPreview.btnLRotateClick` calls `IG_error_check` with EDX=`0`, then reloads the image handle and changes the page.

## Open question — do not hard-code rotation semantics yet

The names of the GEAR APIs and their documented semantics do not fully explain the observed call paths: notably the value `3` passed to `IG_IP_flip`, and the left-rotate handler's call to `IG_error_check`. The UI handlers also make a virtual call at vtable offset `0xA8`, which may be part of the operation path.

Before implementing these operations in the Linux port, resolve:
1. The exact ImageGear enum values used by the shipped `GEAR32PD.DLL`.
2. The object type and virtual method at vtable offset `0xA8`.
3. The state transition performed by `TGearImgProc.Rotate90` through its virtual call at `[self+0x28]`.

The current disassembly proves the call targets and argument values; it does not yet prove the full user-visible rotation semantics.
