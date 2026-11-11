# GEAR API call resolution

## Authoritative PE import-thunk mapping (Run 60)

The earlier helper-symbol labels for several GEAR thunk addresses were incorrect. For imported function identity, use the PE import descriptor + IAT slot + actual indirect-jump thunk, not a TD32 helper label.

| Thunk VA | IAT slot | Imported API |
|---:|---:|---|
| `0x004AFF38` | `0x00630CE0` | `GEAR32PD.DLL!IG_IP_crop` |
| `0x004AFEC8` | `0x00630D14` | `GEAR32PD.DLL!IG_IP_rotate_multiple_90` |
| `0x004AFED0` | `0x00630D10` | `GEAR32PD.DLL!IG_IP_flip` |
| `0x004AFEE8` | `0x00630D04` | `GEAR32PD.DLL!IG_error_get` |
| `0x004AFED8` | `0x00630D0C` | `GEAR32PD.DLL!IG_error_check` |
| `0x004AFF00` | `0x00630CF8` | `GEAR32PD.DLL!IG_image_dimensions_get` |
| `0x004AFF08` | `0x00630CF4` | `GEAR32PD.DLL!IG_image_resolution_get` |
| `0x004AFE88` | `0x00630D34` | `GEAR32PD.DLL!IG_load_file` |
| `0x004AFE98` | `0x00630D2C` | `GEAR32PD.DLL!IG_load_FD` |
| `0x004AFE90` | `0x00630D30` | `GEAR32PD.DLL!IG_save_file` |
| `0x004AFEA0` | `0x00630D28` | `GEAR32PD.DLL!IG_save_FD` |

## Confirmed processing methods

### Crop

`TGearImgProc@$bdtr` at `0x004EEE24` copies the incoming 16-byte `TRect` to a local stack buffer, loads the image handle from `[self+0x10]`, pushes rectangle pointer and image handle, then calls `IG_IP_crop` through `0x004AFF38`. It subsequently calls `ReloadPage` and `GetImageResolution`, then sets the modified flag `[self+0x54] = 1`.

The UI coordinate conversion is separately documented in [IIPEditor-ABI.md](IIPEditor-ABI.md): image/viewer scale factors are applied and each edge is rounded using Delphi `System.Round`.

### Rotate

- `TGearImgProc.RotateLeft` at `0x004EF178` loads the image handle from `[self+0x10]`, pushes the incoming direction argument and handle, then calls `IG_IP_rotate_multiple_90` at `0x004AFEC8`. It then reloads the page, reads resolution, and sets the modified flag.
- `TGearImgProc.RotateRight` at `0x004EF1A4` sets `EDX = 3` and delegates to `RotateLeft`.
- This reverses the earlier helper-symbol interpretation: `RotateLeft` calls `IG_IP_rotate_multiple_90`, not `IG_IP_flip`.

### Flip

- `TGearImgProc.FlipHorizontal` at `0x004F0210` pushes the incoming direction and image handle, calls `IG_IP_flip` at `0x004AFED0`, reloads the page, reads resolution, and sets the modified flag.
- `TGearImgProc.FlipVertical` at `0x004F023C` sets `EDX = 0` and delegates to `FlipHorizontal`.

## GScan Preview button handlers

The TD32-bounded disassembly shows the following exact imported calls:

| Handler | Imported API | Direction value | Follow-up calls |
|---|---|---:|---|
| `TfrmGScanPreview.btnLRotateClick` | `IG_IP_flip` | 0 | `LoadImageToGearHandle`, `cmbPagesChange`, VCL virtual call at `+0xA8` |
| `TfrmGScanPreview.btnRRotateClick` | `IG_IP_rotate_multiple_90` | 3 | `LoadImageToGearHandle`, `cmbPagesChange`, VCL virtual call at `+0xA8` |
| `TfrmGScanPreview.btnVFlipClick` | `IG_IP_rotate_multiple_90` | 1 | `LoadImageToGearHandle`, `cmbPagesChange`, VCL virtual call at `+0xA8` |

Do not infer the visible action from handler names or direction integers alone. The observed imported API/direction pairs are authoritative static evidence; exact enum meanings for the deployed ImageGear version remain unverified. The handler `btnHFlipClick` changes the stored rectangle/flag and invalidates the view; no direct GEAR pixel-transform import appears in its bounded body.

## Other GEAR call paths

- `TGearImgProc.SaveToFile` calls `IG_save_file` at `0x004EF7E6`.
- `TGearImgProc.ScanToFile` calls `IG_save_file` at `0x004EF94F`.
- `TGearImgProc.SavePage` calls `IG_save_FD` at `0x004EF64E`; the same method also contains an `IG_load_FD` call at `0x004EF60B`. Inspect full handle and descriptor lifecycle before implementing this path.
- `TGearImgProc.NotifyEditor` contains `IG_load_FD` calls at `0x004EF2D3` and `0x004EF2F9`.
- `TWordViwer.EmbedTextToImage` calls `IG_load_file` at `0x004C43C7`; this is not evidence of the main document-open path.
- `TGearImgProc.SelectScanner` and `TfrmGScanPreview.SelectScanner` are attributed to `IG_scan_pages` in the Run 60 caller report. Scanner source-selection call attribution still needs contextual validation.

## Confidence and open questions

- High: imported function identity from PE import descriptors, IAT slots, and thunk bytes.
- High: Crop, RotateLeft/Right, FlipHorizontal/Vertical and the listed GScan button instruction sequences from bounded TD32 procedure disassembly.
- Medium: other file-descriptor and scanner call ownership; inspect full methods and control flow.
- Unverified: deployed ImageGear DLL version, exact enum constants, full API prototypes/calling convention, pixel-format behavior, and scanner transport details.

The exact GEAR32PD version shipped with EMWAT is not yet available. Do not hard-code enum values or ABI details based only on newer SDK documentation.
