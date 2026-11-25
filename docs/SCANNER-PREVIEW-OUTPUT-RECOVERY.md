# Scanner preview output and page-navigation recovery

Static evidence recovered from the `emwat-parallel-image-ui` artifact of workflow run `45561859598` (source image: `analysis-input/EmwatMethods.bpl1`). This report separates the scanner's per-page output path from the separately named multipage-TIFF save path.

## 1. `TfrmGScanPreview.Scan` — per-page physical output path

TD32 identifies `0x0061DC80` as `TfrmGScanPreview.Scan` (628 bytes).

Observed control/data flow:

1. The routine derives a destination path from the preview object's path field at `this+0x458`, using Delphi string helpers and a constant at `0x0061DEE8`. The literal constant and exact naming policy have not yet been independently decoded.
2. It obtains a page count through an interface at `this+0x3FC+0x2CC`, vtable slot `+0x14`.
3. It opens the source path with `_lopen` (thunk `0x00402920`, mode 0).
4. For each page, starting at page index 1, it obtains the currently loaded page index through an interface call at `this+0x3FC`, slot `+0x108`. If the requested page is already the current page, it reuses the image handle at `this+0x428`; otherwise it loads that page through `IG_load_FD` (thunk `0x004AFE98`) using the open source handle and the page index.
5. It creates each destination with `CreateFileW` (thunk `0x004026A4`). The arguments include `dwCreationDisposition=1` (`CREATE_NEW`), so this path does not silently overwrite an existing destination.
6. It writes the page with `IG_save_FD` (thunk `0x004AFEA0`). The format/flag argument is selected as `0x40028` when the object field at `this+0x434` equals 1, otherwise `0x80028`.
7. It closes each output handle with `CloseHandle` and deletes temporary ImageGear image handles with `IG_image_delete`. The original current-page handle is not deleted by this loop.
8. A failed source open or destination creation sets a local failure flag; the routine follows a distinct cleanup/return path.

**Safe conclusion:** this method materializes one physical output file per page. It is not the one-file multipage-container implementation. The exact output suffix, filename collision handling beyond `CREATE_NEW`, format enum meanings, ImageGear argument ABI, and failure reporting contract remain unresolved.

## 2. `Save_Tiff_MultyPages` is a separate save operation

TD32 identifies `0x0061D888` as `TfrmGScanPreview.Save_Tiff_MultyPages` (1016 bytes). This routine:

- reads the preview object's source/path field at `this+0x458`;
- calls `IG_save_file` (thunk `0x004AFE90`) with image handle `this+0x428`, a path assembled from Delphi strings, and format value `0x15` in its first save branch;
- contains a separate branch that also calls `IG_save_file`, selecting `0x40028` or `0x80028` based on `this+0x434`;
- routes progress/error handling through `0x0061D100` (`GetImagePageNumber`) and `0x00404E84` in the observed branches.

The routine name and ImageGear page-count context are consistent with a multipage TIFF save action, but the numeric format value `0x15` and all finalization/stream semantics are not yet independently proven. Do not substitute this method for the per-page `Scan` path when implementing scanner result publication.

## 3. Page selector geometry

TD32 identifies `0x0061E680` as `TfrmGScanPreview.cmbPagesChange` (768 bytes). It reads image/client rectangle coordinates through interface slot `+0x64`, compares image dimensions against the available preview area, calculates a uniform fit scale, rounds computed dimensions through `0x00401058` (`rtl230.bpl!@System@@ROUND`), and centers the fitted image by deriving horizontal/vertical offsets. It then writes the resulting bounds through helper calls `0x00404844`, `0x00404854`, `0x0040484C`, and `0x0040485C`.

This is preview layout behavior; it is not evidence of scanner DPI, source-image resampling, or crop pixel-coordinate conversion.

## 4. Implementation constraints

- Keep `ScanResult`'s distinction between a list of single-page output files and one multipage output file.
- Model this `Scan` path as a per-page output collection only after the filename/response contract is recovered; do not infer names from the constant address.
- Do not invent ImageGear C prototypes or assume its FD parameters are POSIX descriptors.
- Preserve `CREATE_NEW` collision behavior in any compatible adapter; report collisions rather than silently overwriting.
- The current evidence is static disassembly. It does not validate a physical scanner, ADF, duplex path, or a live EMWAT response exchange.

## Evidence locations

- Workflow: `https://github.com/meicamghe/EMWAT-Linux/actions/runs/45561859598`
- Artifact: `emwat-parallel-image-ui`
- Procedures: `0x0061D888`, `0x0061DC80`, `0x0061E680`
- Relevant helper traces: `0x00402684`, `0x004026A4`, `0x00402918`, `0x00402920`, `0x004AFE90`, `0x004AFE98`, `0x004AFEA0`, `0x004AFEB8`
