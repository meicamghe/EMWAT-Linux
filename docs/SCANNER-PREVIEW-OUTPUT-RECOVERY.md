# Scanner preview output and page-navigation recovery

Static evidence from the `emwat-parallel-image-ui` artifacts of workflow runs `45561859598` and `45761544667` (source image: `analysis-input/EmwatMethods.bpl1`). This report distinguishes the preview form's page-indexed `IG_save_FD` output path from the separately named `Save_Tiff_MultyPages` operation. A previous interpretation of `Scan` as one physical file per page is withdrawn.

## 1. `TfrmGScanPreview.Scan` — one page-indexed output container

TD32 identifies `0x0061DC80` as `TfrmGScanPreview.Scan` (628 bytes).

Observed control/data flow:

1. The routine derives one destination path from the preview object's path field at `this+0x458`. The string constant at `0x0061DEE8` is confirmed as `_New.tif`; the path is formed by the Delphi string/path helpers before the page loop.
2. It obtains the source page count through an interface at `this+0x3FC+0x2CC`, vtable slot `+0x14`.
3. It opens the source path with `_lopen` (thunk `0x00402920`, mode 0).
4. It iterates page indices starting at 1. If the requested page is already the current page, it reuses the image handle at `this+0x428`; otherwise it loads that page through `IG_load_FD` (thunk `0x004AFE98`) using the open source handle and page index.
5. It opens the same destination path with `CreateFileW` (thunk `0x004026A4`) on each iteration. Reversing the seven pushed arguments according to the Win32 `CreateFileW` signature gives `dwCreationDisposition=4` (`OPEN_ALWAYS`), **not** `1` (`CREATE_NEW`). The path is therefore created on the first pass and reopened on later passes; the prior collision/one-file-per-page conclusion was incorrect. The raw `hTemplateFile` argument is `0x40000000` and remains unexplained.
6. It calls `IG_save_FD` (thunk `0x004AFEA0`) with the current image handle, output handle, current page index, reserved value 0, and format-like value. The format-like value is `0x40028` when `this+0x434 == 1`, otherwise `0x80028`.
7. It closes the output handle with `CloseHandle` and deletes temporary ImageGear image handles with `IG_image_delete`. The original current-page handle is not deleted by this loop.
8. A failed source open or destination open sets a local failure flag; the routine follows a distinct cleanup/return path.

The public ImageGear API reference declares `IG_save_FD(hIGear, fd, nPage, nReserved, lFormatType)`; it documents `nPage` as a one-based page number for multipage files, with `nReserved=0`, and supports inserting a page into an existing multipage file. This matches the five pushed arguments and page-index loop observed above. The same reference explains that the file handle must point to the beginning of the existing image; reopening the `OPEN_ALWAYS` destination for each pass is consistent with that requirement. This is API-reference corroboration, not proof of the exact ImageGear version shipped with EMWAT. <https://help.accusoft.com/ImageGear/v18.7/Linux/IGDLL-19-684.html> <https://help.accusoft.com/ImageGear/v18.7/Linux/IGDLL-06-010.html>

**Updated conclusion:** `Scan` writes successive page indices into one `_New.tif` destination using `IG_save_FD`. The intended output is strongly consistent with a single multipage TIFF container, not a collection of one-file-per-page outputs. The exact meanings of format values `0x40028`/`0x80028`, the unusual `hTemplateFile` value, final TIFF byte structure, and live response publication remain unverified.

## 2. `Save_Tiff_MultyPages` is a separate save operation

TD32 identifies `0x0061D888` as `TfrmGScanPreview.Save_Tiff_MultyPages` (1016 bytes). This routine:

- reads the preview object's source/path field at `this+0x458`;
- calls `IG_save_file` (thunk `0x004AFE90`) with image handle `this+0x428`, a path assembled from Delphi strings, and format value `0x15` in its first save branch;
- contains a separate branch that also calls `IG_save_file`, selecting `0x40028` or `0x80028` based on `this+0x434`;
- routes progress/error reporting through `0x0061D100` (TD32 symbol `GetImagePageNumber`, whose body actually aggregates ImageGear errors) and `0x00404E84` in the observed branches.

This is a separate save operation from `Scan`; do not assume its path, format selection, or response publication is identical. The numeric format values and finalization/stream semantics remain unresolved.

## 3. Page selector geometry

TD32 identifies `0x0061E680` as `TfrmGScanPreview.cmbPagesChange` (768 bytes). It reads image/client rectangle coordinates through interface slot `+0x64`, compares image dimensions against the available preview area, calculates a uniform fit scale, rounds computed dimensions through `0x00401058` (`rtl230.bpl!@System@@ROUND`), and centers the fitted image by deriving horizontal/vertical offsets. It then writes the resulting bounds through helper calls `0x00404844`, `0x00404854`, `0x0040484C`, and `0x0040485C`.

This is preview layout behavior; it is not evidence of scanner DPI, source-image resampling, or crop pixel-coordinate conversion.

## 4. Implementation constraints

- Model the recovered `Scan` path as one page-indexed output container; do not implement a page-file set based on the earlier withdrawn `CREATE_NEW` interpretation.
- Keep `ScanResult` capable of representing both a page-file set and one multipage file, but do not claim that this particular `Scan` method produces the former.
- Do not invent ImageGear C prototypes or assume its FD parameters are POSIX descriptors. The vendor API describes a Windows file handle cast to the ImageGear integer FD parameter.
- Preserve the observed `OPEN_ALWAYS` behavior and 1-based page index; do not replace it with exclusive-create semantics.
- Keep the two preview save methods distinct until their format/response contracts are reconciled.
- The evidence is static disassembly plus API-reference corroboration. It does not validate a physical scanner, ADF, duplex path, or a live EMWAT response exchange.

## Evidence locations

- Workflows: `https://github.com/meicamghe/EMWAT-Linux/actions/runs/45561859598`, `https://github.com/meicamghe/EMWAT-Linux/actions/runs/45761544667`
- Artifact: `emwat-parallel-image-ui`
- Procedures: `0x0061D888`, `0x0061DC80`, `0x0061E680`
- Relevant helper traces: `0x00402684`, `0x004026A4`, `0x00402918`, `0x00402920`, `0x004AFE90`, `0x004AFE98`, `0x004AFEA0`, `0x004AFEB8`
- ImageGear API reference: `IG_save_FD` declaration and multipage page-index semantics, ImageGear 18.7 documentation.
