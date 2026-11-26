# ImageGear save pipeline — recovered static contract

Date: 2026-11-26 correction to the 2026-11-25 trace
Input: parallel TD32 trace artifacts `45560979156`, `45761480118`, and `45761544667`, exact EmwatMethods.bpl1 snapshot.
Scope: static control-flow, import-thunk identities, output-path constants, and corroborating public ImageGear API documentation. The exact shipped ImageGear version, output bytes, and live hardware behavior are not claimed.

## SaveToFile dispatch (`TGearImgProc.SaveToFile`, 0x004EF714)

1. It first requires processor dirty/state byte `+0x54` and checks the image handle at `+0x10` with imported `IG_image_is_valid` (`0x004AFEC0`).
2. It calls imported `IG_page_count_get` (`0x004AFEA8`) using the path/string at `+0x38`, storing the result at `+0x4c`.
3. If the image format field at `+0x14` equals `0x15` and the value at `+0x44` is below 8, it invokes `IG_IP_color_promote` (`0x004AFF18`) with value 2. The enum meaning of `0x15` and the precise meaning of `+0x44` remain unresolved.
4. It checks a virtual predicate at VMT slot `+0x04`.
5. If page count is at most one, it calls `IG_save_file` (`0x004AFE90`) with the image handle, path and format-like field. If the target path cannot be used, an error branch is raised.
6. If page count is greater than one, it delegates to `SavePage` (`0x004EF510`). It clears the dirty/state byte after the save path.

## SavePage (`0x004EF510`) — one page-indexed output container

- Iterates the page count stored at processor object `+0x30`, starting at page index 1.
- Opens the source path at `+0x38` through `_lopen` (`0x00402920`) and obtains the current source file handle.
- For the original/current page it reuses the existing image handle at `+0x10); for other page indices it calls `IG_load_FD` (`0x004AFE98`) with the source handle and page-index-related arguments.
- The destination path is derived from the source path and the string constant at `0x004EF708`, now decoded as `_New.tif`.
- It calls `CreateFileW` (`0x004026A4`) on that same destination path for each page. Reversing the seven pushed arguments according to the Win32 API signature gives `dwCreationDisposition=4` (`OPEN_ALWAYS`), not `1` (`CREATE_NEW`). The destination is created on the first iteration and reopened for later pages. The raw `hTemplateFile` argument is `0x40000000` and remains unexplained.
- It calls `IG_save_FD` (`0x004AFEA0`) with the loaded image handle, output handle, page index (1-based), reserved value 0, and format-like field. It then closes the output handle with `CloseHandle` (`0x00402684`).
- A newly loaded temporary image handle is deleted through `IG_image_delete` (`0x004AFEB8`). Error state is tracked and raised after iteration.

The public ImageGear API reference declares `IG_save_FD(hIGear, fd, nPage, nReserved, lFormatType)`; it documents one-based page numbering for multipage files and a reserved argument of zero. It also documents inserting a page into an existing multipage file and requires the file handle to point to the beginning of the existing image. The observed page-index loop, `OPEN_ALWAYS` reopen, and `_New.tif` destination are consistent with one multipage TIFF output container. This API documentation is corroboration, not proof that the target's older `GEAR32PD.DLL` has identical implementation details. <https://help.accusoft.com/ImageGear/v18.7/Linux/IGDLL-19-684.html> <https://help.accusoft.com/ImageGear/v18.7/Linux/IGDLL-06-010.html>

**Correction:** the prior report called this a set of one-file-per-page outputs and interpreted the pushed value `1` as `CREATE_NEW`. Both conclusions were wrong. The `1` is the `CreateFileW` share-mode argument; the fifth parameter, `dwCreationDisposition`, is the pushed value `4` (`OPEN_ALWAYS`). `IG_save_FD` receives the page index, so this is a single page-indexed output container, strongly consistent with multipage TIFF. The format-like values `0x40028`/ `0x80028` are still not mapped to a specific TIFF compression mode.

## SaveCPinMultiPageFile (`0x004EF40C`)

- Obtains an output stream-like object from the object at `+0x28` through helper calls and an interface method at slot `+0x14`.
- Iterates page indices 1..count (`+0x30`), sets the active page, marks the processor state, then invokes the stream object's interface slot `+0x20` with a page/result argument and an output parameter.
- Replaces the stored stream/object reference at `+0x28` after the loop and releases the previous reference via interface slot `+0x1c` and helper `0x4010E8`.
- This remains a distinct stream-oriented multipage path. The exact stream interface contract, output byte layout, and TIFF finalization remain unresolved.

## Native implementation implications

1. Keep the SavePage path as one page-indexed output container, not a page-file set.
2. Keep `ScanResult` capable of representing either a set of physical page files or one multipage file; do not assign the page-file-set variant to this SavePage path.
3. Do not infer multipage TIFF page count from `ScanResult::output_file_count()`; that method counts physical output files only.
4. Keep page-index iteration, temporary image-handle ownership, output-file creation, and stream/container finalization as separate adapters until the target ABI is proven.
5. Do not implement the `IG_load_FD`/`IG_save_FD` C++ signatures from call-site stack shape alone. Verify calling convention and handle ownership first.

## Evidence limits

- Imported thunk identities: `IG_image_is_valid`, `IG_page_count_get`, `IG_IP_color_promote`, `IG_save_file`, `IG_load_FD`, `IG_save_FD`, `IG_image_delete`, `CreateFileW`, `_lopen`, `_lclose`, `CloseHandle`.
- Exact ImageGear prototypes, TIFF compression/tags, file/stream ownership, and runtime parity are still open.
- No physical scanner or printer acceptance test was performed.
