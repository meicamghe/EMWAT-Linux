# SANE multi-frame and ADF implementation contract

Status: bounded ADF page batching and ordered 8-bit planar RGB assembly are implemented. Duplex semantics and physical hardware acceptance remain open.

## Current implementation

- `ScannerBackend::scan_pages()` is a non-pure virtual compatibility API. Its default implementation wraps `scan_one()` into a one-page vector.
- `SaneScannerBackend::scan_one()` captures one complete page: 8-bit grayscale, interleaved RGB, or a validated RED → GREEN → BLUE planar RGB sequence. It requires a terminal frame and resets the SANE operation with `sane_cancel()`.
- `SaneScannerBackend::scan_pages()` overrides the fallback. When the caller explicitly selects an advertised source whose name identifies an ADF, it keeps one SANE session/device handle open and starts subsequent page cycles after each terminal frame. `SANE_STATUS_NO_DOCS` at a page boundary—whether returned by `sane_start()` or by `sane_read()` before any bytes of the next page—ends the batch normally.
- If no ADF source is explicitly selected, `scan_pages()` performs one scan only. It never repeatedly starts a flatbed.
- Batch safety limits are currently fixed at 100 pages and 4 GiB total image data; each page also retains the existing 1 GiB limit. A 101st page is probed and rejected rather than silently truncated.
- Planar RGB is assembled only for the exact RED → GREEN → BLUE sequence with matching dimensions/depth and expected `last_frame` transitions. Each channel is interleaved into one RGB page; channel planes are never exposed as separate pages. Unknown, reordered or inconsistent sequences are rejected.
- Duplex front/back semantics are not implemented or hardware-verified.

## SANE acquisition state machine

1. Validate the device identifier and scan options before initializing SANE.
2. Acquire the process-wide SANE mutex, initialize SANE, open the selected device, and apply supported options once before the first page.
3. Read device-selected DPI after options are applied.
4. For each page, call `sane_start()`, then `sane_get_parameters()`, validate frame format/depth/dimensions/stride and bounded byte arithmetic, and read until `SANE_STATUS_EOF`.
5. The current backend accepts only 8-bit `SANE_FRAME_GRAY` and interleaved `SANE_FRAME_RGB` with `last_frame=true`. Other frame formats and non-terminal frames are rejected and cancelled.
6. For ADF batches only, after a complete page call `sane_start()` again on the same handle. `SANE_STATUS_NO_DOCS` is normal completion; other statuses fail the batch.
7. On normal batch completion or any failure, call `sane_cancel()` before closing the handle and exiting SANE.
8. Preserve acquisition order. Do not infer front/back labels from page parity.

## Resource and failure policy

- Per-page image allocation is capped at 1 GiB.
- ADF batches are capped at 100 pages and 4 GiB of accumulated image bytes. The remaining batch budget is passed into the page reader, so the next page is rejected before its pixel buffer is reserved if it cannot fit; the batch does not intentionally allocate a full extra page beyond the total budget.
- Read lengths, zero-progress reads, excess bytes, incomplete payloads and stride arithmetic are validated.
- If a later page fails, the API throws rather than presenting a partial batch as a complete successful scan.
- Feeder-empty is recognized only as `SANE_STATUS_NO_DOCS` from the next `sane_start()` boundary. Paper jam, cover open, I/O errors and cancellation remain explicit failures.
- The ADF classifier is intentionally conservative: only an explicitly supplied source string containing `ADF` or `Automatic Document Feeder` activates batch mode. The normal SANE option setter still verifies that the device actually exposes a compatible `source` option.

## Remaining implementation work

- Add a narrow injectable SANE function table/frame-reader seam so the real acquisition loop can be exercised with deterministic fake frames.
- Add an injectable SANE function-table/frame-reader seam so the actual multi-frame sequence can be tested without physical hardware. The pure planar channel interleaver and padded-stride handling now have deterministic unit tests.
- Add a configurable page/byte limit with API-level validation if product requirements call for it.
- Expose feeder/duplex capabilities only when the SANE device descriptors or backend metadata support them.
- Verify exact feeder-empty and error behavior against physical ADF devices and record scanner model, backend/version, source option, frame sequence and resulting page count.

## Required automated tests

- ADF source classifier: explicit ADF values accepted; flatbed and generic document-table values rejected.
- Single-page fallback when no ADF source is selected.
- Fake SANE function-table tests for one-page success, multiple ADF pages, feeder-empty completion, start/read failure, cancellation, 100-page cap, 4 GiB cap and short/oversized/no-progress reads.
- Full SANE planar RGB sequence success and invalid/missing/reordered channel failures through the future fake SANE function table.
- Native build, CTest and ASan/UBSan.

CI tests do not replace physical scanner acceptance. No physical scanner has been validated by this change.
