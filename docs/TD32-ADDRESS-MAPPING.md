# TD32 address mapping — validated for EMWAT target methods

## Result

The previous analysis incorrectly treated a TD32 procedure Offset as either a PE RVA or a raw file offset. For the 24 image/scanning target procedures, the validated mapping is:

1. Read the procedure's TD32 Segment field.
2. Resolve that 1-based segment number to the corresponding PE section.
3. Interpret the procedure Offset as relative to that section.
4. Compute:
   - `RVA = section.VirtualAddress + procedure.Offset`
   - `raw = section.PointerToRawData + procedure.Offset`
5. Require the procedure range to fit both its TD32 module segment range and the PE section's raw data range.
6. Disassemble from the resulting VA and inspect the method entry.

This interpretation matches the TD32 definitions: `TSegmentInfo.Offset` is the offset in a segment where a module contributes code, and `TSymbolProcInfo.Offset` is the offset portion of a segmented procedure address. See the JCL TD32 structure definitions: https://github.com/project-jedi/jcl/blob/master/jcl/source/windows/JclTD32.pas

For the target methods in this BPL, TD32 segment 1 maps to PE section 1 (`.text`). This is an empirically validated mapping for the target procedures; do not assume every logical segment in every Delphi PE maps identically without checking its section and range.

## Validated examples

| Method | TD32 offset | Mapped RVA | Raw file offset |
|---|---:|---:|---:|
| `TGearImgProc.Rotate90` | `0xEE138` | `0xEF138` | `0xEE538` |
| `TGearImgProc.RotateLeft` | `0xEE178` | `0xEF178` | `0xEE578` |
| `TGearImgProc.RotateRight` | `0xEE1A4` | `0xEF1A4` | `0xEE5A4` |
| `TGearImgProc.FlipHorizontal` | `0xEF210` | `0xF0210` | `0xEF610` |
| `TGearImgProc.FlipVertical` | `0xEF23C` | `0xF023C` | `0xEF63C` |
| `TfrmSimpleImageEditor.CropImage` | `0xF01E8` | `0xF11E8` | `0xF05E8` |
| `TfrmGScanPreview.btnLRotateClick` | `0x21D5C0` | `0x21E5C0` | `0x21D9C0` |

## What the code reveals so far

- `Rotate90` begins with a normal Delphi x86 frame and checks an image-object field before calling a helper at `0x4AFEA8`.
- `RotateLeft` checks a field at `[ebx+0x10]`, calls the helper at `0x4AFEC8`, then invokes two internal image-state helpers.
- `RotateRight` is a small wrapper: it sets `EDX=3` and calls `RotateLeft`.
- `FlipHorizontal` calls the image operation helper with `EDX` preserved from the caller, then updates image state.
- `FlipVertical` sets `EDX=0` and calls `FlipHorizontal`.
- `TfrmGScanPreview.btnLRotateClick` passes `0` to helper `0x4AFED0`; `btnRRotateClick` passes `3` to `0x4AFEC8`; `btnVFlipClick` passes `1` to `0x4AFEC8`. These are strong clues for the operation enum, but helper semantics still need cross-reference validation.
- `TfrmSimpleImageEditor.CropImage` is an orchestration method that checks image/editor state, invokes component virtual methods, and calls `ShowCropRectangle`; it is not itself a low-level pixel crop routine.

## Tooling changes

- `tools/disassemble_emwat_targets.py`: now maps by TD32 segment index and section-relative procedure offset; scores the first 32 bytes to avoid rejecting valid Delphi methods because of later exception metadata or constants.
- `tools/diagnose_emwat_code_offsets.py`: now reports the same validated mapping and entry bytes.
- `tools/inspect_td32_module_map.py`: now validates target ranges against PE section bounds and reports section-index mapping.

## Validation

GitHub Actions run 42978328167 completed successfully. All 24 selected target procedures produced plausible code entries under the corrected mapping. This is a static-analysis result, not yet a complete semantic proof of every helper call.
