# Reverse-engineering parallel follow-up — 2026-11-28 Run 44

## TWordViwer.LoadDocument argument routing

The complete Run-50 skipdata trace `15253702066/procedure-004B7724.md` provides the following dataflow:

### wordBody

- Input arrives in EDX and is stored at `[EBP-0x1C]`.
- It passes through `0x00457050` and `0x00454B9C` at `0x004B7788–0x004B7796`.
- The resulting decoded string is stored at `[EBP-4]`.
- Its length is checked at `0x004B77AB–0x004B77B5`; empty output logs an error and raises.
- The decoded body is then used to construct the temporary source stream/file at `0x004B77F1–0x004B783A`.

This confirms that the Linux parser's non-empty decoded `wordBody` requirement is aligned with the native successful-load path. The handler-level TryGetValue may leave a missing key empty, but the loader rejects the empty result.

### letterImages

- Input arrives in ECX and is stored at `[EBP-0x20]`.
- It is passed as EDX to `TCreateTiff.SeparteImages` at `0x004B7A9C` (no wordBody branch) or `0x004B7ABD` (body-present branch).
- The currently proven consumer is the TIFF conversion/preview pipeline. Its exact payload format remains open.

This is a TIFF-side dependency and can remain deferred while the user has explicitly deprioritized multipage TIFF, subject to the live Almas workflow not requiring its preview result.

### signData

- It is passed as a stack argument to `TWordViwer.LoadDocument` and stored in local `[EBP-0x10]`.
- It is used in subsequent XML/interface operations around `0x004B7AEB–0x004B7B2F`, including child/node access and value assignment.
- The literal node/property names at `0x004B83C0` and `0x004B848C` have not yet been decoded, and the full data schema is unknown.

Therefore `signData` must remain preserved as opaque input; do not discard it or claim signature-field parity until its XML structure and target field mapping are proven.

## Priority refinement

For the requested initial Almas Word open/edit/save milestone:
1. Keep the non-empty Base64 `wordBody` path.
2. Preserve `wordConfig` and `signData`; recover signData semantics if the live workflow exercises signatures.
3. Defer `letterImages` format and TIFF preview processing while multipage TIFF remains out of scope.
4. Do not claim end-to-end Almas persistence until a real request/response capture verifies the returned Word body is accepted and stored by Almas.

No production code or workflow source was changed.
