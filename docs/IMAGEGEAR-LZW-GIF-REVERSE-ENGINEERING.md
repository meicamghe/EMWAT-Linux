# ImageGear LZW/GIF extension reverse engineering

Date: 2026-11-24  
Status: static reverse engineering; no runtime parity claim  
Binary: `IGLZW32S.DLL` (PE32/i386)  
SHA-256: `5cbb9352d71b74836c99429a1eaf39f77db753bfae6d5307199aaffbdeeee6cd`  
ImageGear host: `Gear32pd.dll` (AccuSoft ImageGear 7.0.15.15 version resource)

## Scope and evidence discipline

This note records the recovered GIF/LZW extension behavior from the disassembly supplied for the exact DLL above. Addresses are virtual addresses from the PE image as loaded at image base `0x10000000`. Findings are static unless explicitly stated otherwise. Export names, strings, and function names are not treated as proof of runtime use by themselves.

The extension is loaded by three `IG_ext_load` callsites in `EmwatMethods.bpl`; all three pass the same extension name, `igLzw32s.Dll`, alongside the same `Gam` and `HAMID` strings. This establishes repeated load requests for the same extension, not three different codecs.

## Binary identity

- PE32 Intel i386; six sections.
- Timestamp: 1997-11-10 17:54:57 (PE timestamp).
- Imports: `KERNEL32.dll`, `MSVCRT40.dll`.
- Internal DLL name: `iglzw32s.dll`.
- Export Address Table: 106 entries; Name Pointer Table: 10 named exports.
- Named exports:
  - `GIF_detect` RVA `0x2a60`
  - `GIF_header_read` RVA `0x29c0`
  - `GIF_page_count` RVA `0x2b30`
  - `GIF_read` RVA `0x2b80`
  - `GIF_thumbnail_read` RVA `0x2bc0`
  - `GIF_write` RVA `0x20a0`
  - `GearExtEntryProc` RVA `0x50c0`
  - `GearExtInfoGet` RVA `0x4bd0`
  - `GearExtInfoSet` RVA `0x4fc0`
  - `TIF_Proc_LZW_Comp` RVA `0x5650`

The binary contains source-path strings naming GIF read/write and TIFF LZW source files. Those strings are provenance clues, not a complete source tree.

## Extension registration

`GearExtEntryProc` at VA `0x100050c0` accepts action 1 (initialize) and action 2 (terminate). Initialization iterates a registration table of 45 entries (0xb4 bytes / 4-byte pointers) and invokes a registration helper for each. A failed registration returns 0; successful completion returns 1. This establishes a table-driven extension registration model. The exact meaning of all 45 registrations has not yet been decoded.

## GIF parser and extension blocks

The GIF parser dispatcher around `0x10001600–0x1000188a` dispatches four GIF extension block types:

| Handler VA | Signature bytes | Meaning |
|---|---|---|
| `0x10001d90` | `21 01 0C` | Plain Text Extension (label 0x01, fixed header length 12) |
| `0x10001cc0` | `21 F9 04` | Graphic Control Extension (label 0xF9, block length 4) |
| `0x10001f70` | `21 FE` | Comment Extension |
| `0x10001ff0` | `21 FF 0B` | Application Extension (11-byte application identifier/authentication header) |

The handlers use ImageGear callbacks at `0x100097e4`, `0x100097f0` (field read/validation), `0x100097d4` (block transfer), `0x10009848` (error reporting), and `0x1000984c` (cleanup/end callback).

The shared helper at `0x10001ed0` performs chunked transfer with length/bounds validation. Plain Text, Comment, and Application handlers use it. The Graphic Control handler validates its fixed fields separately. This proves parsing/validation paths for these four extension types; it does not yet prove how every metadata field is preserved when rewriting a GIF.

## GIF writer and LZW encoder

### Entry and image constraints

`GIF_write` begins at VA `0x100020a0`. It checks a metadata/depth argument at `[esp+0x1e]`; values greater than 8 enter an error path (line marker 0x26c). Valid input reaches helper `0x10001000` and the image encoder path. The supported GIF writer input depth is therefore bounded to at most 8 bits by this check. This does not establish support for every indexed pixel layout.

### Encoder setup: `0x10002230`

The setup routine:

- allocates an output buffer of `0x4000` bytes;
- computes row bytes as `ceil(width × bits_per_pixel / 8)`, then aligns the result to a 4-byte boundary;
- allocates a row/working buffer based on the aligned row size;
- allocates a dictionary workspace of `0x8008` bytes;
- initializes 64 blocks of 256 bytes in the first working area;
- initializes the LZW dictionary through `0x100021a0`.

The dictionary record size is 8 bytes. The count is stored at dictionary offset `+0x8004`, and the maximum count is `0x1000` (4096 entries).

The initial code-size parameter is normalized in setup: input 0x0c maps to 8; input 1 maps to 2; otherwise the input value is retained. This is a code-path observation; the caller-side semantic meaning of every input value remains to be verified.

### Dictionary initialization and insertion

- `0x100021a0` initializes base symbols and fills the remaining dictionary slots up to the 4096-entry capacity. It records the initial count as `(1 << code_size) + 2`, consistent with reserving Clear and End-of-Information codes.
- `0x10002160` inserts an entry and refuses insertion when count is already 4096.
- Each dictionary record is 8 bytes: symbol byte at offset 0, prefix code DWORD at offset 4, with padding/reserved bytes between.
- `0x10002770` searches for an existing (prefix, symbol) pair. It first writes the candidate prefix into the next free record's prefix field, then scans existing records beginning at index prefix+1. It compares the stored prefix DWORD and symbol byte. This is a linear search, not a hash table. The scan excludes the new free record because the prior count is its upper bound.

### Input symbol extraction

`0x10002670` extracts the next symbol from the source image:

- for an 8-bit path, it reads one byte;
- for a 12-bit path, it reads three source bytes and maps RGB values into a reduced palette representation. The non-grayscale path quantizes each channel and combines the quantized values as `R + 6×G + 36×B`;
- the grayscale special case uses a separate arithmetic expression and should not be simplified to the same 6×6×6 mapping without a dedicated algebra/test pass;
- other bit depths use bit extraction based on the configured sample width.

The 12-bit branch is evidence of a special RGB-to-index mapping path, not proof that arbitrary RGB GIF encoding is supported.

### Main LZW loop

The main loop is in approximately `0x10002496–0x10002595`:

1. Read the next input symbol using `0x10002670`.
2. Search the dictionary for the pair (current prefix, symbol) using `0x10002770`.
3. If found, replace prefix with the returned dictionary code.
4. If not found, emit the current prefix through `0x100027d0`, insert the new pair through `0x10002160`, then set prefix to the current symbol.
5. If the dictionary reaches 4096 entries, emit/reset behavior is entered using the 12-bit width and dictionary reinitialization.
6. Otherwise, code width is increased when the dictionary capacity threshold for the next width is crossed.

The exact threshold ordering at boundary values should be validated with synthetic streams before implementing a compatible encoder. The current static trace identifies the mechanism but does not yet prove every off-by-one convention against a reference GIF decoder.

### Bit writer and output buffering: `0x100027d0`

The bit writer has two paths:

- Normal code path: masks the requested code to the current bit width, packs bits into output bytes, and tracks the bit offset.
- Buffer-full path: when the 0x4000-byte staging block is filled, calls callback `0x100097d4` to transfer the block and checks that the returned byte count matches the expected size. A mismatch reports an error (line marker 0x325).

A special mode is selected when one argument is `0xffffffff`; it follows a row/segment transfer/finalization path rather than ordinary code packing. The exact meaning of this sentinel is not assumed to be EOI.

### End-of-stream sequence

At the end of `0x10002230`:

- a final normal bit-writer call occurs at `0x100025b8`;
- another normal bit-writer call occurs at `0x100025de`;
- a special `0xffffffff` bit-writer call occurs at `0x10002601`;
- the routine then calls the transfer callback `0x100097d4` with length 1 and data pointer `0x1000904c`;
- two cleanup callbacks at `0x10009840` release the dictionary and output/working allocation contexts.

This strongly indicates a final code emission, bitstream flush, and one-byte GIF sub-block terminator write. The byte at `0x1000904c` has not yet been dumped in the supplied evidence, so its value must not be asserted as 0x00. Likewise, the exact mapping of the two normal final writes to final-prefix and EOI is not yet confirmed. The next static check is to dump `0x10009040–0x10009060` and inspect argument provenance for the calls at `0x100025b8` and `0x100025de`.

## TIFF LZW routine

The export `TIF_Proc_LZW_Comp` begins at RVA `0x5650` (VA `0x10005650`). Its body allocates dictionary/working buffers including sizes `0x2001`, `0x8004`, and `0x100`. The inspected path reads data in chunks up to 0x100 bytes through a callback, processes 9-bit codes, recognizes Clear=0x100 and EOI=0x101, expands dictionary entries up to 0x2000, and grows code width to 12 bits.

This is strong evidence of a TIFF LZW decode/decompression path. The export suffix `Comp` alone does not establish whether it compresses or decompresses; do not infer encode direction from the name.

## Other export caveats

`GIF_thumbnail_read` at RVA `0x2bc0` is a short thunk through a callback pointer near `0x1000984c`; its full behavior has not been resolved. Do not label it a complete thumbnail decoder until the callback target and registration record are identified.

`Gear32pd.dll` contains evaluation/expiry strings, including “The ImageGear extension has expired.” Their presence does not prove that the shipped runtime blocks GIF operations. Runtime effect remains unknown.

## Linux implementation implications

1. Treat GIF read/write and TIFF LZW as separate codec capabilities behind a native imaging interface.
2. Prefer a maintained Linux codec implementation (e.g. system-supported GIF/TIFF libraries) rather than porting this 1997 binary or reproducing ImageGear internals.
3. Preserve indexed-color constraints, GIF extension metadata, multi-frame/page ordering, transparency/disposal semantics, and output termination through regression fixtures.
4. Test GIF inputs with Plain Text, Graphic Control, Comment, and Application extensions; include malformed/truncated sub-blocks and boundary-sized payloads.
5. Test encoder code-width boundaries, dictionary reset at 4096 entries, grayscale and RGB sample paths, and output block flush/terminator behavior.
6. Keep TIFF LZW interoperability tests separate from GIF LZW tests; shared algorithm family does not mean identical container semantics.
7. Never ship `IGLZW32S.DLL` as a Linux runtime dependency. It is a reverse-engineering reference only.

## Remaining work

- Dump the constant bytes around `0x1000904c` to identify the final one-byte trailer.
- Recover the exact values/arguments passed to the two normal final bit-writer calls and prove which one emits EOI.
- Validate code-width transition and dictionary-full reset boundaries against independent GIF decoders.
- Inspect the 45 extension registration entries and identify supported formats/features.
- Trace `GIF_read`, `GIF_header_read`, and `GIF_page_count` end-to-end, including interlace, transparency, animation frame control, and metadata preservation.
- Identify the callback target behind `GIF_thumbnail_read`.
- Determine whether ImageGear evaluation expiration affects any actual EMWAT imaging path through a controlled, non-customer runtime fixture.

## Confidence summary

| Finding | Confidence |
|---|---|
| DLL identity, imports, named exports, timestamp/hash | High |
| Four GIF extension handlers and signatures | High |
| GIF writer rejects depth values greater than 8 | High |
| Encoder dictionary layout/capacity and linear pair lookup | High |
| Main LZW prefix/symbol loop and bit writer buffering | High |
| TIFF routine is an LZW decompression path | High |
| Exact EOI/final-code ordering | Unresolved |
| Value at `0x1000904c` | Unresolved |
| Full semantics of all 45 registrations | Unresolved |
| Runtime effect of ImageGear evaluation strings | Unresolved |
