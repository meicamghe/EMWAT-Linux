# Scanner interface and acquisition contract — Run 61

Date: 2026-11-11  
Evidence: `EmwatMethods-target-disassembly.md` from workflow run `43001855137` (artifact `13846033438`), TD32-bounded x86 disassembly.

## Scope and confidence

This document records what is directly visible in the bounded machine code. It deliberately does not assign semantic names to undocumented interface slots, scanner mode integers, or ImageGear prototypes. The exact deployed `GEAR32PD.DLL` build and its matching SDK/header set have not yet been identified.

## Two distinct scanner entry paths

### `TfrmGScanPreview.SelectScanner` — VA `0x0061DEF4`

Observed sequence:

1. Clears form flag `[self+0x456]`.
2. If the incoming Boolean argument is true, invokes an earlier helper and may take an early-exit branch.
3. Sets ImageGear JPEG quality with `IG_save_JPEG_quality_set` (thunk `0x004AFF20`, immediate value `0x41`).
4. Reads the configured output path from `[self+0x458]`, performs Delphi string/file handling, and checks a global status field.
5. Calls `IG_scan_pages` (thunk `0x004AFF30`) in two branches. The pushed scalar arguments differ: one branch pushes `1` and `0x28`; the other pushes `1` and `2`. The device/object argument is obtained through helper `0x004049CC`. The code then passes callback/context data to helper `0x0061D100`.
6. Checks the global status again, calls helper `0x0061D3BC`, validates the current image handle at `[self+0x428]` with `IG_image_is_valid`, and returns a Boolean-like result.

Important: the two integer argument sets are recorded as raw evidence only. Do not label them as duplex, color, feeder, page mode, or any other scanner option until the exact ImageGear version/prototype is known. This bounded method contains no direct call to `IG_scan_source_select`.

### `TGearImgProc.SelectScanner` — VA `0x004EF9CC`

This is a separate orchestration path and must not be merged with the preview form path.

Observed object layout and dispatch:

- `[self+0x28]` holds an interface-like object. The method checks it for null.
- It invokes the object's VTable entry at byte offset `+0x0C`, passing an output pointer, then checks the returned/output value.
- It invokes the same `+0x0C` entry again later to obtain another interface-related value.
- It calls local helper `0x004EF048`, then invokes a virtual method through the `TGearImgProc` instance VMT at offset `+0`, and passes the resulting value, another object, and a Boolean-like argument to `IG_scan_pages` at `0x004EFA96`.
- The returned value from `IG_scan_pages` is stored in `[self+0x4C]`.
- Subsequent branches query status/error values through helper `0x004EF1DC`, retrieve additional objects via interface VTable offset `+4`, and in two branches create a form/object and invoke its VTable entry at byte offset `+0x13C`. The return value is compared with `1`.
- Other branches dispatch through the TGearImgProc VMT at offsets `+8` or `+4`.
- The method returns a small status value (observed values include 0, 1, and 2) after exception-safe cleanup.

The interface method names and the meaning of the status values are unresolved. The class's VMT candidate is `0x004EE074`, instance size `0x60`; the interface-like object at `[self+0x28]` is not itself identified by the current interface-table scan. The VMT slot `+0x13C` belongs to a dynamically obtained form/object; it is not a GEAR import.

## What this establishes

- EMWAT has at least two distinct scan orchestration paths: preview-form acquisition and TGearImgProc-mediated scanner selection.
- The preview path sets JPEG quality, prepares an output path, calls `IG_scan_pages`, passes callback/context data into a helper, then validates the active image handle.
- The TGear path depends on an interface-like device/provider object and several virtual callbacks, not merely on a direct call to an ImageGear scanner function.
- The static caller attribution for `IG_scan_source_select` remains suspect. Neither of the two SelectScanner bodies above provides evidence for a direct call to that import. The previously reported callsites attributed to `ShowCropRectangle` and `SetCurrentPage` must be rechecked at raw callsite/thunk level before being used.

## Linux architecture consequence

Keep the Linux design split into independently testable services:

1. **Device discovery/selection:** SANE device enumeration and explicit selected-device identity.
2. **Acquisition session:** source capabilities, options, start/read/cancel, and device errors, mapped from SANE rather than guessed ImageGear integer modes.
3. **Scan result delivery:** a callback/event interface that reports page-start, page data, page-complete, cancellation, and failure. Do not reproduce Delphi VMT layout.
4. **Image/page store:** owns decoded pixel buffers and metadata independently of scanner lifetime.
5. **Preview/editor:** consumes page-store objects and never owns the scanner handle.
6. **Export:** separate per-page and multipage writers with explicit partial-failure reporting.

Suggested neutral acquisition contract (design proposal, not recovered ABI):

- `ScanRequest`: device ID, requested options, output policy, cancellation token.
- `ScanEvent`: session ID, event kind, page index, optional image/page payload, optional structured error.
- `ScanResult`: ordered page IDs, selected device ID, effective options, completion status, warnings/errors.

A native implementation should not expose ImageGear file-descriptor handles or Delphi object pointers in its public interfaces.

## Next reverse-engineering tasks

1. Resolve the runtime type and method names for the interface object at `[TGearImgProc+0x28]` using RTTI/interface tables, constructor writes, and callsites that populate the field.
2. Trace the confirmed callees `GetEditorModalResult` (`0x004EF048`), `LoadPage` (`0x004EF1DC`), `TWinControl.GetHandle` (`0x004049CC`, imported from VCL), and `GetImagePageNumber` (`0x0061D100`) in their actual call contexts. These are not four anonymous scanner helpers.
3. Revalidate every `IG_scan_source_select` callsite by decoding the actual instruction target and following the import thunk to its IAT slot.
4. Identify the exact shipped `GEAR32PD.DLL` version before interpreting scanner constants or ABI.
5. Only then finalize the SANE option mapping and implement a native acquisition prototype with fake-device tests plus hardware tests.

## Explicit non-claims

This analysis does not establish the exact scanner interface method names, ImageGear calling convention/prototypes, the meaning of numeric mode values, or successful runtime acquisition on Linux. No native scanner backend has been implemented yet.


## Run 62 — address identity correction

The four extra target traces from Run 62 resolve the target identities and correct the earlier generic helper interpretation:

| Address | Actual identity | Consequence |
|---|---|---|
| `0x004EF048` | `TGearImgProc.GetEditorModalResult` (TD32 symbol) | A form/editor result query; not a scanner-specific helper. |
| `0x004EF1DC` | `TGearImgProc.LoadPage` (TD32 symbol) | A page-loading/status path; its bounded body queries a value through helper `0x00403270`, then calls `0x00401398` with `[self+0x0C]` and checks the returned integer. |
| `0x004049CC` | VCL import thunk `vcl230.bpl!TWinControl.GetHandle` via IAT `0x0062FC48` | The call in `TfrmGScanPreview.SelectScanner` obtains a native window handle; it is not an interface/provider callback. |
| `0x0061D100` | `TfrmGScanPreview.GetImagePageNumber` (TD32 symbol) | It enumerates image/page-related entries and updates UI/control state; it is not a callback passed to the scanner. |

The `GetEditorModalResult` disassembly shows a byte-sized selector in `DL`, a switch-like branch, and a Boolean result. Its exact selector meanings still need callsite/context correlation. `GetImagePageNumber` uses `IG_error_check`, iterates a count, and calls `IG_page_count_get`/related imported routines while constructing page-related state; its exact UI semantics need the DFM and caller context. `LoadPage` checks an interface-like object at `[self+0x0C]` using helper `0x00401398`, returning a Boolean-like status. These facts narrow the work but do not identify the object type stored at `[TGearImgProc+0x28]`.

**Correction to previous next-step wording:** these four addresses are now symbol-resolved identities, not four anonymous helper routines. The open scanner question is the runtime type and construction/population path of the object at `[TGearImgProc+0x28]`, plus the semantics of the virtual methods at offsets `+0x0C`, `+4`, and the instance VMT's slot `+0`.
