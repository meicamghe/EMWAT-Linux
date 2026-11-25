# Image, scanner and editor call-graph inventory

Date: 2026-11-25  
Input: successful `emwat-parallel-image-ui` artifact from workflow run `45558987223`, generated from `analysis-input/EmwatMethods.bpl1` and preserved DFM resources.  
Method: TD32 procedure-symbol indexing plus heuristic Delphi VMT candidate inspection. This is static evidence only.

## 1. Scanner preview form — `TfrmGScanPreview`

The symbol index identifies the following procedures in module `XmlRequest`:

| Procedure | VA | Size |
|---|---:|---:|
| `Scan` | `0x0061DC80` | 628 |
| `SelectScanner` | `0x0061DEF4` | 1236 |
| `Save_Tiff_MultyPages` | `0x0061D888` | 1016 |
| `GetImagePageNumber` | `0x0061D100` | 336 |
| `GetImgSize` | `0x0061D250` | 284 |
| `LoadImageToGearHandle` | `0x0061D36C` | 80 |
| `btnCropClick` | `0x0061E50C` | 60 |
| `btnHFlipClick` | `0x0061E548` | 119 |
| `btnLRotateClick` | `0x0061E5C0` | 47 |
| `btnRRotateClick` | `0x0061E5F0` | 47 |
| `btnVFlipClick` | `0x0061E620` | 47 |
| `cmbPagesChange` | `0x0061E680` | 768 |
| `uibtnRegisterClick` | `0x0061E470` | 60 |
| `uibtnCancelClick` | `0x0061E3F0` | 125 |

The names establish that scanner selection, acquisition, page counting/loading, multipage TIFF saving, page navigation, crop, flips and rotations are separate handlers. The handler names do not alone establish exact pixel transforms, error semantics, or the commit/cancel behavior.

## 2. Shared image-processing controller — `TGearImgProc`

The TD32 index in module `Vcl.XPMan` exposes a cohesive controller surface:

| Operation | VA |
|---|---:|
| `SelectScanner` | `0x004EF9CC` |
| `ScanToFile` | `0x004EF8C0` |
| `SaveToFile` | `0x004EF714` |
| `SavePage` | `0x004EF510` |
| `SaveCPinMultiPageFile` | `0x004EF40C` |
| `Crop` | `0x004EEDB4` |
| `Rotate90` | `0x004EF138` |
| `RotateLeft` / `RotateRight` | `0x004EF178` / `0x004EF1A4` |
| `Flip` / `FlipHorizontal` / `FlipVertical` | `0x004F01F0` / `0x004F0210` / `0x004F023C` |
| `LoadPage` / `ReloadPage` | `0x004EF1DC` / `0x004EF0E4` |
| `SetCurrentPage` / `ReNewPageCount` | `0x004EFF6C` / `0x004EF124` |
| `NotifyEditor` / `ShowEditor` | `0x004EF240` / `0x004F0174` |
| `SetResultImage` | `0x004F0160` |
| `GetForceSinglePage` / `SetForceSinglePage` | `0x004EF088` / `0x004F0084` |
| `GetImageResolution` / `GetImageBPP` | `0x004EEEC4` / `0x004EF0C4` |
| `GetFormatIndex` / `SetFormatIndex` | `0x004EF0B4` / `0x004F00FC` |
| `SetJpgQuality` | `0x004F012C` |

This is strong evidence that the original product centralizes scanner, page, transform, format and editor notification operations behind a controller-like object. The exact method bodies and argument contracts still require the expanded procedure traces.

## 3. Simple image editor — `TfrmSimpleImageEditor`

The symbol index identifies:

- `Initial` `0x004F116C`
- `CropImage` `0x004F11E8`
- `pbImgViewerMouseDown/Move/Up` `0x004F1274/0x004F1308/0x004F1404`
- `ShowCropRectangle` `0x004F1660`
- `ToggleCropMode` `0x004F1890`
- `CalculateBestFitSize` `0x004F1988`
- `chkForceSinglePageClick` `0x004F1A04`
- `cmbPagesChange` `0x004F1CE0`
- `doCommand` `0x004F1D04`
- `FormClose` / `FormCloseQuery` `0x004F1064` / `0x004F109C`

This supports a real crop-selection interaction (mouse down/move/up plus crop rectangle) and an explicit force-single-page option. Exact coordinate conversion, crop bounds, cancel/accept semantics and page behavior remain to be traced.

## 4. Image tools — `TfrmImageTools`

The symbol index identifies an ImageEn multi-view workflow:

- Multi-image operations: `InsertPicture` `0x0050A29C`, `DeletePicture` `0x0050A414`, `ScanPicture` `0x0050A298`, `itNavigatePages` `0x0050A1D4`.
- Transforms: `FreeRotate` `0x00508A90`, `RotateImage` `0x0050AB2C`, `FlipImage` `0x0050ABA4`, `AutoOrient` `0x0050ACDC`.
- Editing and commands: `doProc` `0x0050BBB8`, `itRunCommand` `0x0050A218`.
- Printing: `DoPrinting` `0x0050A534`, `DoPrintingPanel` `0x0050A698`, `ShowPrintPanel` `0x005098B0`, `UpdatePrintPreview` `0x0050BB90`.
- ImageEn interaction: `iePageHolderImageChange` `0x0050B718`, image select/deselect and mouse handlers around `0x0050B254–0x0050B94C`.

This confirms that image tools are not a single-image viewer: the form exposes insertion/deletion, navigation, transformations, scanning and print-preview paths.

## 5. Image result and multipage containers

The symbol index identifies `TResultImage` operations for file enumeration, per-index file naming, file stream, image type, file size, scan path and response filename. It also identifies distinct `TSetOfSinglePageImages` and `TSetOfMultiPageImages` constructors; the latter has its own delete, scan-path and response-filename methods.

This is an important modeling boundary for Linux: a scan result is not necessarily a single path. The native model must preserve single-page collections and multipage-file collections as distinct representations, with explicit response naming and page indexing.

## 6. VMT candidate caveat

The VMT script found self-pointer and instance-size-consistent candidates for `TfrmSimpleImageEditor`, `TfrmGScanPreview`, `TfrmImageTools`, `TGearImgProc` and `TScanCommand`. It explicitly labels them **unverified candidates**. Several candidates point into executable sections containing Delphi package thunks; a valid-looking candidate and method table profile do not prove the VMT boundary or inherited slot layout. Do not use these candidates to assign interface slots until corroborated by RTTI, constructor references, or runtime inspection.

No candidate was found for several data-model classes (`TResultImage`, `TSetOfSinglePageImages`, `TSetOfMultiPageImages`), despite their TD32 procedure symbols. This is not evidence that they lack classes or methods; their RTTI representation may differ.

## 7. Linux implementation implications and next probes

1. Keep `ScanSession`, `ImageDocument`, `Page`, and `ScanResult` separate. Support both a set of single-page files and a single multipage TIFF result.
2. Preserve page navigation and explicit force-single-page behavior.
3. Model crop selection as coordinates in the displayed preview, then map to source-image coordinates with a tested scale/offset transform.
4. Keep transformations (rotate/flip/free-rotate/auto-orient) explicit operations with metadata/orientation tests.
5. Trace the listed procedures and their callers to recover exact state mutations, output naming, TIFF append/finalize behavior, and cancel/register semantics.
6. Compare these contracts against existing `native/include/emwat/image_document.hpp`, `native/src/image_document.cpp`, and scanner backend tests before changing the native API.

## Evidence limits

- Artifact workflow run `45558987223` completed the image VMT/symbol/resource inventory job successfully.
- The initial artifact contains symbol indexes and heuristic VMT output. The expanded procedure/caller trace job was added afterward and has its own pending workflow run.
- No physical scanner, real TIFF device capture, Wine prefix, or printer was exercised by this artifact.
