# GDI+ live Save/SaveAdd slot crosswalk — 2026-11-28

## Result

The functional multipage TIFF sequence in `TCreateTiff.SeparteImages` can now be mapped to the real GDI+ APIs with high confidence by combining the PE import table, direct wrapper callsites, call arguments, and the post-loop control flow. This closes the functional Save/SaveAdd cycle; the raw Delphi RTTI/interface metadata is still not a flat VMT pointer array.

## Confirmed import thunks

| Thunk VA | PE import target |
|---|---|
| `0x00481C64` | `GdipSaveImageToFile` |
| `0x00481C6C` | `GdipSaveImageToStream` |
| `0x00481C74` | `GdipSaveAdd` |
| `0x00481C7C` | `GdipSaveAddImage` |

The PE import parser and GNU `objdump -p` agree on these IAT targets. TD32 procedure labels on the wrappers are stale/shifted in multiple places and must not override the import target or actual argument shape.

Direct wrapper callsites in artifact `15254911990`:
- `0x00490923` and `0x00490A57` call `GdipSaveImageToFile`.
- `0x0049098A` and `0x004909EE` call `GdipSaveImageToStream`.
- `0x00490ABF` calls `GdipSaveAddImage` with base image, next image, and encoder parameters.
- `0x00490AFE` calls `GdipSaveAdd` with the base image and encoder parameters.

## Live `SeparteImages` interface dispatch

At `0x004A0148`, `SeparteImages` dispatches through the `TGPImage` interface:

| Interface slot | Call-site shape | Resolved operation |
|---|---|---|
| `+0x48` at `0x004A0470` | Base image + output filename/codec configuration + encoder parameters | Initial `GdipSaveImageToFile` save; creates the multipage TIFF and writes the first frame |
| `+0x5C` at `0x004A0507` | Base image + next page image + encoder parameters, inside the page loop | `GdipSaveAddImage`; appends each subsequent frame |
| `+0x58` at `0x004A0568` | Base image + encoder parameters only, after the page loop | `GdipSaveAdd`; final `EncoderValueFlush` operation |

The argument count and register/stack shape distinguish the two SaveAdd forms. The `+0x5C` call is inside the per-page loop and passes the current page image. The `+0x58` call is after the loop, passes no new image, and follows the encoder-parameter update with value `20` (`EncoderValueFlush`).

The encoder configuration remains `EncoderCompression=2` (LZW) and `EncoderSaveFlag=18` (MultiFrame). The first frame is included by the initial Save; the first loop iteration is deliberately skipped for SaveAddImage, then subsequent pages are appended. The final SaveAdd(Flush) is issued after the loop.

## VMT/RTTI correction

`0x00484728` is the class-reference/global slot used by the constructor path; it contains the class metadata pointer `0x00484780`. The `TGPImage` interface metadata begins at `0x0047DD2C`, with related interface RTTI around `0x0047DD84`. These are Delphi class/interface metadata records, not a directly usable flat table of method implementation pointers. The functional interface slots above are resolved from their call-site ABI and control-flow role; do not claim that the raw dword dump alone is the live VMT.

## Acceptance boundary

No runtime multipage TIFF was generated in this run. A real output fixture is still required to validate frame count/order, LZW encoding, final stream/file close, and Almas acceptance before changing Linux output code.

## Run 31 — raw RTTI boundary and functional dispatch status

The class metadata dump confirms that the pointer stored in the `TGPImage` class slot leads into Delphi interface/type metadata. The bounded range at `0x0047DD84` contains interface RTTI fields and names such as `NativeHandle` / `TGdiPlusBase`; it is not a flat array of implementation pointers. The functional `SeparteImages` interface slots therefore remain mapped from call-site ABI, the matching wrapper bodies, the independently verified PE import targets, and their loop/finalization positions—not from treating raw metadata DWORDs as code pointers.

The operation-level mapping is complete enough to describe the Save/SaveAdd lifecycle, but the raw interface VTable pointer table itself is **not** fully reconstructed from the available artifacts. The pointer to the interface metadata (`0x0047DD2C`) and the RTTI candidate range (`0x0047DD84`) are known; the raw method table contents needed to map every interface slot directly to a code VA are not present in the downloaded artifact. No Linux TIFF behavior should be changed on the basis of a guessed raw table.


## Run 33 — interface VTable base candidates

The class/interface metadata provides a narrower raw-table dump target:

- TGPImage class slot: 0x00484728 + 0x28 -> interface-table metadata at 0x0047DD2C.
- The associated interface RTTI candidate begins at 0x0047DD84. Its +0x58 DWORD is 0x0062EEA0, a candidate base pointer for the TGPImage interface method table.
- TGPEncoderParameters class slot: 0x00483F4C + 0x28 -> 0x0062EE88, a separate interface-table candidate. The two candidate bases differ by 0x18 bytes; this is consistent with nearby interface tables but is not proof of their exact extent or layout.

If 0x0062EEA0 is the TGPImage interface VTable base, the observed call slots address these DWORD locations:

| Interface slot | Candidate table address |
|---:|---:|
| +0x48 | 0x0062EEE8 |
| +0x58 | 0x0062EEF8 |
| +0x5C | 0x0062EEFC |
| +0x70 | 0x0062EF10 |
| +0x74 | 0x0062EF14 |

These are calculated addresses only; the pointer values stored there were not included in the artifact and must not be guessed. A raw dump of 0x0062EE88–0x0062EF18 from the original PE would confirm or reject the candidate and expose the actual method pointers. The operation-level Save/SaveAdd mapping remains valid independently of this raw-table gap.


## Raw table extraction command

A standard-library-only dumper is available at scripts/dump_pe_va_ranges.py. It maps VAs through PE section headers and prints raw DWORDs plus nearby ANSI/UTF-16LE strings. To inspect the candidate interface tables and the worker/XML helper addresses in one pass:

    python3 scripts/dump_pe_va_ranges.py analysis-input/EmwatMethods.bpl1

Synthetic PE tests were added but have not yet been run. The raw TGPImage pointer values remain unverified until this command is executed against the original BPL.
