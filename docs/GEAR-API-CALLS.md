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


## Run 61 — scanner selection and page lifecycle (2026-11-11)

Run 61: workflow `43001855137`, commit `8597fc9`, artifact `13846033438`. The newly added TD32-bounded targets all mapped to executable code with high confidence.

### Scanner selection: important correction

The bounded body of `TfrmGScanPreview.SelectScanner` (VA `0x0061DEF4`) does **not** call `IG_scan_source_select`. It:
- resets the form's scanner-selection/result flag at `[self+0x456]`;
- checks a previously selected device/interface object at `[self+0x458]`;
- configures JPEG quality through `IG_save_JPEG_quality_set` (`0x004AFF20`);
- calls `IG_scan_pages` (`0x004AFF30`) in two branches with different literal mode arguments;
- reloads/validates the current image handle at `[self+0x428]`.

The two `IG_scan_source_select` caller attributions in the static import-caller report point to `TfrmGScanPreview.ShowCropRectangle` and `TGearImgProc.SetCurrentPage`, which are semantically suspicious. Treat those as unresolved attribution until their exact callsites and import thunk targets are revalidated. Do not use them to define the scanner-source-selection workflow.

`TGearImgProc.SelectScanner` (`0x004EF9CC`) is a separate, longer path. It interrogates an interface-like object at `[self+0x28]`, tests capability/status values, invokes callbacks through its VMT, stores a returned object at `[self+0x4C]`, and may call `IG_scan_pages` at `0x004EFA96`. It also checks device/status values through `LoadPage`. This is not interchangeable with the GScan Preview method.

### Page and handle lifecycle

- `TfrmGScanPreview.LoadImageToGearHandle` (`0x0061D36C`) checks the current handle `[self+0x428]` with `IG_image_is_valid`; if valid, it writes width/height/depth-like outputs to `[self+0x42C]`, `[self+0x430]`, `[self+0x434]` using `IG_image_dimensions_get`; otherwise it zeros those fields.
- `TGearImgProc.ReloadPage` (`0x004EF0E4`) validates `[self+0x10]` and updates its dimensions/resolution fields; invalid handles zero the cached dimensions.
- `TGearImgProc.SavePage` (`0x004EF510`) iterates page numbers from 1 through `[self+0x30]`. For the current page index `[self+0x34]`, it reuses `[self+0x10]`; for other pages it calls `IG_load_FD` (`0x004AFE98`) and releases temporary image handles with `IG_image_delete` (`0x004AFEB8`). It creates/opens an output stream/file handle, calls `IG_save_FD` (`0x004AFEA0`) for each page, and closes the stream. A failure flag is set when load/open/save fails.
- `TfrmGScanPreview.Scan` (`0x0061DC80`) follows a closely related per-page loop, using the page collection at `[self+0x3FC]`, current image handle `[self+0x428]`, output path `[self+0x458]`, and output-format flag `[self+0x434]`. It calls `IG_load_FD` for non-current pages and `IG_save_FD` for each output page; the save flags differ between the two output-format branches (`0x40028` vs `0x80028`). Temporary handles are deleted; the current handle is retained.
- These observations establish page iteration and ownership behavior, but the exact file-descriptor ABI, flags, and format enum meanings still require the matching GEAR32PD SDK/version or controlled runtime tests.

### Linux implementation consequence

Model scanner selection, acquisition, preview, and multi-page export as distinct operations. Use a native SANE device layer for acquisition, but keep the image/page model independent of SANE. Preserve the active-page handle separately from temporary page handles, and make export failures explicit per page. Do not emulate the undocumented GEAR file-descriptor ABI.


## Run 70/74 — scanner-source and file-descriptor corrections

The earlier Run 61 note that the IG_scan_source_select callsites were suspicious is superseded. Raw CALL instructions and thunk/IAT resolution confirm:

- TfrmGScanPreview.ShowCropRectangle at VA 0x0061E3C8 calls IG_scan_source_select at 0x0061E3DF after obtaining a native window handle through vcl230.bpl!TWinControl.GetHandle.
- TGearImgProc.SetCurrentPage at VA 0x004EFF6C calls IG_scan_source_select at 0x004EFF83 after obtaining the argument from TGearImgProc VMT slot +0x00 (HasError).
- Both calls use thunk 0x004AFF28 and IAT 0x00630CE8. The arguments are distinct and their semantic types beyond the observed HWND/result dataflow remain unverified.

### Confirmed FD import identities and argument order

The import table resolves 0x004AFE98 to IG_load_FD (IAT 0x00630D2C) and 0x004AFEA0 to IG_save_FD (IAT 0x00630D28). This corrects any older note that reverses these two thunks.

SavePage call 0x004EF60B matches IG_load_FD(fd, lOffset, nPage, nTile, lphIGear): descriptor, zero offset, loop page number, zero tile, pointer to temporary HIGEAR handle. SavePage call 0x004EF64E matches IG_save_FD(hIGear, fd, nPage, nReserved, lFormatType): temporary/current HIGEAR, descriptor, loop page, zero reserved, and [self+0x14] format code.

NotifyEditor calls IG_load_FD at 0x004EF2D3 and 0x004EF2F9, writing into [self+0x10]. It does not call IG_save_FD. The first call uses EDX as page number; the second uses page 1; both use offset 0 and tile 1.

The public prototypes corroborate the observed argument layouts:
- IG_load_FD: https://help.accusoft.com/ImageGear/v18.7/Linux/IGDLL-19-566.html
- IG_save_FD: https://help.accusoft.com/ImageGear/v21.0/Linux/IGDLL-19-684.html

These are reference signatures from other ImageGear releases, not proof of the exact GEAR32PD version bundled with EMWAT. The four format constants selected through 0x004EF048 are still unnamed pending the matching header/constants.


## Run 75 — scanner API callsite argument provenance

Workflow run 43008058751 confirms two distinct caller patterns for IG_scan_pages (thunk 0x004AFF30, IAT 0x00630CE4):

- TfrmGScanPreview.SelectScanner pushes a native HWND from TWinControl.GetHandle, a converted path/string from [self+0x458], scalar 0x28 or 2, and scalar 1.
- TGearImgProc.SelectScanner pushes the result of VMT slot +0 (HasError, dispatching through [self+0x24] slot +0x0C), a converted value obtained through [self+0x28] slot +0x0C, the mapper result from 0x004EF048, and the caller's byte argument.
- The Gear caller stores the IG_scan_pages return in [self+0x4C]. The preview caller does not consume the return in the immediately following path.

The TD32 decorated symbol is @Gear@IG_scan_pages$qqsp6HWND__pxcuio. This is insufficient to assign semantic names to all stack arguments. The first Gear-path value is not statically shown to come from TWinControl.GetHandle, unlike the preview path. Preserve this mismatch rather than forcing both paths into an assumed HWND contract.

IG_scan_source_select (thunk 0x004AFF28, IAT 0x00630CE8) also has two confirmed callers with different value provenance: ShowCropRectangle passes TWinControl.GetHandle; TGearImgProc.SetCurrentPage passes the result of VMT slot +0. Its decorated symbol @Gear@IG_scan_source_select$qqsp6HWND__ and the second caller's dataflow are not fully reconciled.

Public Accusoft references to IG_TWAIN_scan_pages describe a related TWAIN acquisition family, but do not establish ABI identity with IG_scan_pages in EMWAT's GEAR32PD.DLL. The extended parent-slot traces did not identify the class behind 0x004EDE18; no TImageProcessor attribution is made.


## Run 76 — IIPEditor pointer and HWND provenance correction

The interface stored at [TGearImgProc+0x24] is now identified as IIPEditor, superseding earlier notes that described it as an unidentified error/result interface:

- TScanCommand.$bdtr calls the setter-like routine at 0x004F0084 with EDX adjusted by +0x430.
- TfrmSimpleImageEditor implements IIPEditor at interface offset 0x430 (IID 7834c511-9078-411c-ab08-8b15ef1fd700; interface VTable 0x004F03D4).
- The same setter is called with nil at 0x004F1151, consistent with interface release/clear.
- TGearImgProc.HasError (0x004EF1C4) dispatches to IIPEditor slot +0x0C. The implementing method at 0x004F1158 calls TWinControl.GetHandle and returns its value.

Thus the Gear-path value previously described only as a HasError result is actually an HWND obtained through IIPEditor. Both confirmed IG_scan_source_select callsites pass an HWND-like value, and the first argument of TGearImgProc.SelectScanner's IG_scan_pages call is likewise an HWND. This resolves the Run 75 value-provenance discrepancy, but does not recover the complete GEAR32PD prototypes or the meanings of the remaining arguments/constants.

Do not treat the TD32 wrapper labels HasError, GetErrorCode, SaveAsType or SetForceSinglePage as semantic proof for the interface methods. The distinct object at [TGearImgProc+0x28] remains unresolved.


## Run 77 — IG_scan_pages call-site ABI evidence

The complete `TGearImgProc.SelectScanner` body at `0x004EF9CC` pushes four arguments before calling the imported `IG_scan_pages` thunk at `0x004EFA96`. The recovered order is:

1. HWND from the IIPEditor interface at `[TGearImgProc+0x24]` via virtual slot +0x0C.
2. Path-like value returned by virtual slot +0x0C on the separate object at `[TGearImgProc+0x28]`, passed through RTL helper `0x004012E0`.
3. Format code from the selector mapper at `0x004EF048`.
4. Zero-extended byte from `[EBP+8]`; probably a UI/control flag, but caller semantics remain unresolved.

The return value is stored at `[TGearImgProc+0x4C]` and then checked via VMT slot +0x04. This proves the call-site argument order and HWND provenance, not the exact exported C declaration or the path encoding. The selector mapper's numeric constants still lack verified format names. The attempted traces of six slots at the supposed parent VMT address did not produce valid code and are explicitly not used to identify the parent class.
