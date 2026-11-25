# ImageGear save pipeline — recovered static contract

Date: 2026-11-25
Input: parallel TD32 trace artifact `45560979156`, exact EmwatMethods.bpl1 snapshot.
Scope: static control-flow and imported-thunk identification. ImageGear argument prototypes, ownership rules and output byte-level format are not claimed.

## SaveToFile dispatch (`TGearImgProc.SaveToFile`, 0x004EF714)

1. It first requires processor dirty/state byte `+0x54` and checks the image handle at `+0x10` with imported `IG_image_is_valid` (`0x004AFEC0`).
2. It calls imported `IG_page_count_get` (`0x004AFEA8`) using the path/string at `+0x38`, storing the result at `+0x4c`.
3. If the image format field at `+0x14` equals `0x15` and the value at `+0x44` is below 8, it invokes `IG_IP_color_promote` (`0x004AFF18`) with value 2. The enum meaning of `0x15` and the precise meaning of `+0x44` remain unresolved.
4. It checks a virtual predicate at VMT slot `+0x04`.
5. If page count is at most one, it calls `IG_save_file` (`0x004AFE90`) with the image handle, path and format-like field. If the target path already exists or cannot be used, an error branch is raised.
6. If page count is greater than one, it delegates to `SavePage` (`0x004EF510`). It clears the dirty/state byte after the save path.

## SavePage (`0x004EF510`)

- Iterates the page count stored at processor object `+0x30`, starting at page index 1.
- Opens the source path at `+0x38` through `_lopen` (`0x00402920`) and obtains the current source file handle.
- For the original/current page it reuses the existing image handle at `+0x10`; for other page indices it calls `IG_load_FD` (`0x004AFE98`) with a source handle and page-index-related arguments.
- Creates an output file using `CreateFileW` (`0x004026A4`) with a creation-disposition value of 1 (`CREATE_NEW`) and write access. It then calls `IG_save_FD` (`0x004AFEA0`) with the loaded image handle, output handle, page index and format-like field, and closes the output handle with `CloseHandle` (`0x00402684`).
- A newly loaded temporary image handle is deleted through `IG_image_delete` (`0x004AFEB8`). Error state is tracked and raised after iteration.
- The per-page target path is derived through Delphi string/path helpers from the source path. The exact naming template and collision policy are not yet fully decoded.

## SaveCPinMultiPageFile (`0x004EF40C`)

- Obtains an output stream-like object from the object at `+0x28` through helper calls and an interface method at slot `+0x14`.
- Iterates page indices 1..count (`+0x30`), sets the active page, marks the processor state, then invokes the stream object's interface slot `+0x20` with a page/result argument and an output parameter.
- Replaces the stored stream/object reference at `+0x28` after the loop and releases the previous reference via interface slot `+0x1c` and helper `0x4010E8`.
- This is a separate stream-oriented multipage path from `SavePage`'s per-page file path. It is consistent with distinct single-page-file and multipage-container output modes, but the exact stream interface contract and TIFF finalization remain unresolved.

## Native implementation implications

1. Preserve two distinct output modes: multiple physical files vs one container file.
2. Do not infer multipage TIFF page count from `ScanResult::output_file_count()`; that method counts physical files only.
3. Keep page-index iteration, temporary image-handle ownership, output-file creation and stream/container finalization as separate adapters until the ImageGear ABI is proven.
4. Do not implement the `IG_load_FD`/`IG_save_FD` C++ signatures from call-site stack shape alone. Verify calling convention and handle ownership first.

## Evidence limits

- Imported thunk identities: `IG_image_is_valid`, `IG_page_count_get`, `IG_IP_color_promote`, `IG_save_file`, `IG_load_FD`, `IG_save_FD`, `IG_image_delete`, `CreateFileW`, `_lopen`, `_lclose`, `CloseHandle`.
- Exact ImageGear prototypes, TIFF compression/tags, output filename template, file/stream ownership, and runtime parity are still open.
- No physical scanner or printer acceptance test was performed.
