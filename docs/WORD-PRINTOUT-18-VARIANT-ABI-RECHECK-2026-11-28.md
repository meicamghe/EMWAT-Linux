# Word PrintOut ABI re-check — 2026-11-28

## Run and evidence

- Workflow run: `46117085322` (contract-closure workflow).
- Word artifact: `15252266519`.
- Relevant procedure: `BGPrintWithGamPrintOptions` at `0x004C5FF8`.
- Wrapper traces: `TWordDocument.PrintOut` at `0x00436030`, `0x004360F0`, and `0x004361B0`.

## Confirmed wrapper arities

TD32 symbols and procedure bodies identify the generated document `PrintOut` overloads for 15, 16 and 17 OleVariant arguments:

- `0x00436030`: 15-Variant wrapper; `ret 0x34`.
- `0x004360F0`: 16-Variant wrapper; `ret 0x38`.
- `0x004361B0`: 17-Variant wrapper; `ret 0x3C`.

The 17-Variant wrapper transfers fifteen stack arguments plus two register arguments to the document interface slot `+0x3F0`. The symbol index contains no 18-Variant `TWordDocument.PrintOut` wrapper.

## Repeated caller evidence

The `BGPrintWithGamPrintOptions` procedure contains four separate calls through document interface slot `+0x3F0`:

- `0x004C70B6`
- `0x004C78A4`
- `0x004C7F50`
- `0x004C87FA`

For each callsite, the preceding argument setup contains exactly eighteen distinct local Variant-record addresses. Each group has fifteen records initialized by `rtl230.bpl!@System@Variants@EmptyParam` plus three records prepared earlier in the procedure. Across the four callsites, the local frame offsets differ, but the 18-record structure repeats.

The three non-empty/maybe-empty records are prepared by the already identified helpers:
- `0x004034E8`: OleVariant-from-integer; two records carry integer-like values.
- `0x00403520`: OleVariant-from-UnicodeString; one record may remain EmptyParam or hold a string.
- `0x00403550`: EmptyParam; fifteen missing/optional arguments per call.

## Conclusion and boundary

The 18-versus-17 mismatch is not an artifact of one callsite: all four branches reproduce the same 18-record call setup. The exact COM ABI still is not proven. The wrapper table offers a 17-Variant maximum, while this caller pushes eighteen Variant pointers before the interface dispatch. Do not discard one Variant, assign semantic Word parameter names, or substitute a generic Word PrintOut signature without establishing the hidden/interface argument convention and the exact type-library metadata.

The following remain separate:
- the document-interface call through slot `+0x3F0`;
- the subsequent application-level `TWordApplication.PrintOutOld` call at `0x004C70CA` (and analogous calls in other branches);
- the timer-driven document `PrintOutOld` path through slot `+0x2BC`.

## Next targeted check

Inspect the exact WordXP type-library/COM interface metadata corresponding to slot `+0x3F0`, then reconcile its declared parameter count and VARTYPEs with the four repeated 18-record caller blocks. Keep the caller's register state at each of the four indirect calls in scope.
