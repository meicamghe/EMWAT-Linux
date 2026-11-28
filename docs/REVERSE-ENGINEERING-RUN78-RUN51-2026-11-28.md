# Reverse-engineering artifact review — runs 78 and 51 (2026-11-28)

## Scope and provenance

This note records a manual review of the uploaded GitHub Actions artifacts from:

- Reverse-engineering run 78: `46146592017`
  - `emwat-parallel-image-ui`
  - `emwat-parallel-word-print`
- Deep-follow-up run 51: `46146595651`
  - `emwat-deep-word-printer-thread`
  - `emwat-deep-imageen-acquisition`
  - `emwat-deep-scanner-result-ownership`

The workflow jobs that produced these artifacts completed successfully. This validates that the analysis scripts ran and produced files; it does not by itself validate every interpretation below. All inputs are static analysis of `analysis-input/EmwatMethods.bpl1`. No Windows runtime, printer, scanner, or Almas session was executed.

## Findings safe to carry forward

### 1. Word event procedures are distinct entry points

The artifact provides complete procedure ranges for several Word event handlers:

- `0x004CD154–0x004CD54B`: TD32-labelled `TWordViwer.WordAppDocumentBeforeSave`.
- `0x004CE030–0x004CF157`: TD32-labelled `TWordViwer.WordAppDocumentBeforePrintBGPrint`.
- Additional event crosswalks were emitted for `0x004CCBBC`, `0x004CD54C`, `0x004CDC2C`, and `0x004D00AC`.

The `0x004CD154` procedure checks that the event's document interface matches the viewer's stored document interface before entering its body. This is consistent with an event sink guarded against unrelated Word documents. It is not sufficient, by itself, to claim that this callback is the close/quit callback. Preserve the distinct BeforeSave, BeforePrint, and close lifecycle hypotheses until the COM connection-point registration and event DISPID mapping are cross-checked.

Capstone skipdata output contains pseudo-instructions for embedded data. Control-flow targets crossing those ranges must be validated before using the trace to infer exact callback semantics.

### 2. TIFF split/save routine has a concrete procedure boundary

- `0x004A0148–0x004A0A67` is labelled `TCreateTiff.SeparteImages` in `EmwatDocPrintHandlerUnit`.
- The routine is 2,336 bytes; the generated artifact decoded 1,368 bytes as 442 instructions. The remaining bytes are not decoded by that report.
- The procedure includes branches around printer/status helpers and calls into helper procedures, including `0x0047CAF0`, `0x0047CC94`, `0x0047D8BC`, `0x0047D448`, `0x004A0E88`, and `0x004A0BA8`.

This gives a stable target for the next focused trace, but does not yet prove the complete TIFF encoder sequence, GDI+ Save/SaveAdd/Flush ordering, encoder parameter lifetime, or the exact output-file naming/creation contract. Do not implement a guessed GDI+ lifecycle from this partial disassembly.

### 3. Scanner colour options are now recovered as user-visible strings, not enum semantics

The scanner constraint globals point to these strings:

| Global slot | Target | Text |
| --- | --- | --- |
| `0x00628260` | `0x004F324C` | `سياه/سفيد` (black/white) |
| `0x00628264` | `0x004F326C` | `طيف سياه و سفيد` (grayscale) |
| `0x00628268` | `0x004F3298` | `طيف سياه و سفيد يا 256 رنگ` (grayscale or 256 colours) |
| `0x0062826C` | `0x004F32DC` | `رنگي 24 بيت` (24-bit colour) |

The artifact explicitly leaves enum meanings unassigned pending caller/consumer confirmation. These strings can guide UI vocabulary, but must not be turned into numeric protocol values until the consuming branch and serialization are resolved.

### 4. ImageEn acquisition helper region is predominantly import thunks

The `0x004B0100–0x004B0240` scan covers 80 decoded instructions, largely jump-through-IAT thunks. A nearby symbol candidate at `0x00624F4C` is labelled `iewia` and consists only of decrementing a global counter then returning. That tiny routine is not evidence of a complete WIA acquisition implementation. Keep ImageEn/TWAIN/WIA call graph work separate from actual device acquisition acceptance.

### 5. Scanner XML parsing remains partially unresolved

The deep scanner artifact emitted candidate string references and pointer chains, but several candidates decode as non-text or mixed encodings. The scanner option table at `0x0062A7FC` is not yet safely interpreted. Do not assign protocol field names from those candidate strings alone.

## Required next experiments

1. **Word event identity:** follow the COM connection-point registration and sink interface, recover the event IID/DISPID mapping, and match each callback to its actual Word event. In particular, prove which callback runs on document close and whether it is distinct from BeforeSave.
2. **TIFF/GDI+:** resolve all callees of `TCreateTiff.SeparteImages`, recover the full procedure including undecoded regions, identify imported GDI+ encoder calls and their argument structures, and trace file creation/rename/deletion through the print worker.
3. **Scanner colour serialization:** follow the four global string pointers into UI selection and `TScanCommand` serialization; record the exact numeric/string values and reject unknown values explicitly.
4. **ImageEn:** resolve the IAT targets and caller chain around `Acquire`, TWAIN, and WIA; identify which backend is selected on the target Windows deployment before choosing a Linux SANE mapping.
5. Re-run Python bridge tests on the current work branch and keep the live Almas Save/reopen test as a separate acceptance gate.

## Confidence and non-claims

- **Confirmed static boundaries:** the procedure addresses/ranges and global-to-string pointer targets listed above.
- **Strong but incomplete:** event handler identity as named by TD32; verify registration metadata before equating labels with runtime event semantics.
- **Unresolved:** exact close callback, TIFF encoder lifecycle, scanner numeric enum values, complete WIA/TWAIN behavior, printer job completion semantics.
- No new product runtime code was changed based on these artifacts.
- No claim is made for signData parity, TIFF parity, physical printer/scanner support, Duplex ADF, or live Almas persistence.
