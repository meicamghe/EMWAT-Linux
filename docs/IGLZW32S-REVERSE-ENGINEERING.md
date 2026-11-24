# IGLZW32S.DLL — static reverse-engineering notes

Date: 2026-11-24  
Target: `IGLZW32S.DLL` from the user's Wine EMWAT installation  
Observed path (local reference only): `~/.wine-emwat/drive_c/ProgramData/Gamelectronics/Emwat Service/IGLZW32S.DLL`  
Architecture: PE32 / i386  
Tooling evidence: GNU `objdump` disassembly and section dump supplied by the user.

> This document records static findings only. No runtime trace, native implementation, or byte-for-byte compatibility test has been completed. Do not commit the proprietary DLL or extracted customer/application binaries.

## 1. Identity and metadata

The `.rdata` section contains:

- `AccuSoft Corporation`
- `GIF|`
- `Nov 10 1997`

The code also contains source-path strings referring to Accusoft ImageGear LZW extension sources such as `Gifwrite.c`, `Gifread.c`, and `TifLzw.c`. These strings strongly identify this module as an old Accusoft ImageGear LZW extension. The embedded date is a string, not independently verified build metadata.

## 2. Export surface

Previously extracted PE exports:

| Export | VA | Current interpretation |
|---|---:|---|
| `GIF_detect` | `0x10002B30` | GIF detection callback |
| `GIF_header_read` | `0x100029C0` | GIF header reader |
| `GIF_page_count` | `0x10002B80` | GIF page count |
| `GIF_read` | `0x10002A60` | GIF image reader |
| `GIF_thumbnail_read` | `0x10002BC0` | GIF thumbnail reader |
| `GIF_write` | `0x100020A0` | GIF writer |
| `GearExtEntryProc` | `0x100050C0` | ImageGear extension entry point |
| `GearExtInfoGet` | `0x10004BD0` | Extension capability/function query |
| `GearExtInfoSet` | `0x10004FC0` | Extension information setter |
| `TIF_Proc_LZW_Comp` | `0x10005650` | TIFF LZW processing export |

Addresses are VAs from the preferred image base `0x10000000`; they are not stable runtime addresses under relocation/ASLR.

## 3. ImageGear extension registration

### 3.1 Entry point

`GearExtEntryProc` at `0x100050C0` reads its action from `[esp+8]`:

- Action 1 performs initialization through `0x10004B00`.
- The resulting state is stored at `0x100097C4`.
- It iterates offsets `0,4,...,0xB0` (45 DWORD slots), reads candidate callback addresses from `0x10008030 + offset`, resolves them through `0x10004B70`, and stores the returned values at `0x100097D0 + offset`.
- A zero resolution aborts initialization; all 45 successful resolutions produce return value 1.
- Action 2 calls `0x10004B90` with the stored state and configuration pointer, then returns 1.
- Other actions return 1 without this initialization path.

The 45 entries are host callback/function slots. Do not describe them as 45 independently identified public APIs until each slot's contract is mapped.

### 3.2 Registration table

The data at `0x10008030..0x100080E0` is a sequence of 45 little-endian 32-bit VAs, descending from `0x10009768` to `0x100093EC`. These are pointers into the module's own code/data address range used as inputs to the resolver; they are not the resolved host callback addresses themselves.

The adjacent strings include vendor, format and date metadata. `GearExtInfoGet` uses query IDs and dispatch/mapping tables to return extension metadata, capability constants, strings and function addresses. The extracted query mapping includes GIF entry points and `TIF_Proc_LZW_Comp`. This is a registration/metadata interface, not a direct image-processing routine.

## 4. TIFF LZW decoder core

### 4.1 Main processing routine

The disassembly around `0x10005150` through `0x1000564F` shows a TIFF LZW decode pipeline:

1. Reads compressed input through a resolved host callback at `0x100097D0`.
2. Requests input in chunks capped at `0x100` (256) bytes.
3. Builds a compressed input buffer and initializes a dictionary/work table.
4. Handles both MSB-first and LSB-first code extraction branches.
5. Starts with 9-bit codes and grows the code width up to 12 bits.
6. Uses Clear Code `0x100` and End-of-Information Code `0x101`.
7. Reinitializes dictionary state when Clear Code is encountered.
8. Expands dictionary strings into the output buffer, including the special `code == next_code` case.
9. Uses a helper at `0x10005620` to follow dictionary links / resolve a code's root symbol.
10. Pads output to a multiple of the calculated row stride and reports the resulting row count through an output pointer.

The routine's return convention and all argument meanings should be confirmed from its caller and ImageGear headers before implementing an ABI-compatible replacement.

### 4.2 Dictionary details

Observed constants and operations:

- Initial code width: 9 bits.
- Maximum code width: 12 bits.
- Clear code: `0x100`.
- EOI code: `0x101`.
- First dictionary code after control codes: `0x102`.
- Initial width-growth threshold: `0x200`; subsequent thresholds double.
- Width growth stops at 12 bits.
- Dictionary/work entries are initialized with sentinel `0x2001`.
- The working table is initialized over `0x2000` DWORD entries.
- Dictionary-chain traversal is bounded around code `0x2000`.

The 0x2000-sized work table should not be confused with the standard 4096-code limit of classic 12-bit GIF/TIFF LZW. The code's actual bounds and sentinel behavior must be preserved and tested rather than normalized based on the standard alone.

### 4.3 Bit order

Two separate extraction branches are visible:

- One branch shifts bytes into an accumulator from the high side and extracts the next code from the high-order bits (MSB-first).
- The other places each incoming byte at the current low-bit offset and extracts with a low-bit mask (LSB-first).

The branch selector is an input parameter/flag. Its exact mapping to TIFF FillOrder or host configuration remains to be verified from the caller and format metadata.

### 4.4 Output layout

The routine calculates a row stride from image width and a bit-depth/packing parameter, or uses a supplied stride-like value in an alternate branch. It decodes into a temporary/output buffer, then appends zero bytes until the final output length is divisible by that stride. It writes the resulting row count through an output pointer.

Do not assume the output is always a byte-per-pixel raster: the stride calculation includes packed-bit handling.

## 5. GIF implementation findings already established

- GIF parser recognizes marker bytes: Extension `0x21`, Image Descriptor `0x2C`, Trailer `0x3B`.
- Extension labels observed include Plain Text `0x01`, Graphic Control `0xF9`, Comment `0xFE`, and Application `0xFF`.
- Graphic Control writer at `0x10001CC0` emits `21 F9`.
- Plain Text writer at `0x10001D90` emits `21 01 0C`.
- Comment writer at `0x10001F70` emits `21 FE`.
- Application writer at `0x10001FF0` emits `21 FF 0B`, followed by the 8-byte application identifier and 3-byte authentication code.
- Shared sub-block helper at `0x10001ED0` handles data sub-blocks up to 255 bytes, writes each length byte and payload, then writes a zero terminator. It uses host callbacks and checks transferred byte counts.
- GIF writer rejects depths above 8 bits.
- LZW table helpers initialize the first entries from `1 << code_size`, reserve control codes, and cap the GIF dictionary at 4096 entries.

## 6. Host callback and error boundaries

The module uses function pointers populated during extension initialization; addresses such as `0x100097D0`, `0x100097E4`, `0x100097F0`, and `0x100097D4` are global callback slots, not Windows API exports. Other globals include an error/reporting callback at `0x10009848` and a cleanup/state callback at `0x1000984C` (the latter interpretation is provisional).

For a native Linux port, isolate these behind an ImageGear-host compatibility adapter. Keep codec logic separate from allocation, stream I/O, error reporting and host lifecycle.

## 7. Native implementation guidance

Recommended decomposition:

- `LzwBitReader`: bounded MSB/LSB code extraction, widths 9–12, truncated-stream handling.
- `LzwDictionary`: clear/reset, prefix/suffix expansion, special next-code case, strict bounds.
- `TiffLzwDecoder`: TIFF-specific code-order/FillOrder handling and row-stride/output contract.
- `GifLzwEncoder/Decoder`: separate GIF framing and GIF-specific dictionary semantics; do not assume TIFF and GIF wrappers are interchangeable.
- `ImageGearExtensionAdapter`: explicit registration, stream callbacks, allocator and error mapping.

Add golden tests for both bit orders, clear/reset, EOI, width transitions 9→10→11→12, dictionary saturation, the KwKwK/special-next-code case, malformed chains, truncated input, row padding and output row count. Use legally obtained or project-owned fixtures; do not commit proprietary customer documents.

## 8. Open questions / next reverse-engineering tasks

1. Disassemble and trace the full exported wrapper `TIF_Proc_LZW_Comp` at `0x10005650` and identify its callers, argument layout, direction/mode flags and exact host data structures.
2. Resolve the input flag selecting MSB-first versus LSB-first and correlate it with TIFF FillOrder and compression tags.
3. Identify allocation/free callback contracts and all error codes passed through `0x10009848`.
4. Inspect `GearExtInfoSet` and complete the query-ID contract, including returned strings and constants.
5. Map the 45 registration slots to their expected host services using resolver code and caller behavior.
6. Complete the GIF core analysis at `0x10001000` and `0x10001720`, and verify GIF read/write behavior with fixtures.
7. Build an independent, tested native LZW implementation before connecting it to EMWAT's image adapter.

## 9. Evidence confidence

- High: PE32 architecture, export names/addresses, embedded strings, 45-slot initialization loop, control-code constants, code-width transitions, dual bit-reader branches, sub-block framing.
- Medium: overall TIFF LZW decoder interpretation and output-row contract, pending full wrapper/caller analysis.
- Unverified: exact export ABI, argument semantics, TIFF tag mapping, callback ownership/lifetime, runtime behavior under EMWAT, and native compatibility.
