# SANE multi-frame and ADF implementation contract

Status: design contract for the next scanner implementation; no claim of ADF or duplex support.

## Current implementation boundary

`SaneScannerBackend::scan_one()` performs one `sane_start()`, reads one frame until `SANE_STATUS_EOF`, and returns one `ImagePage`. It accepts only 8-bit Gray and RGB frames. `ImageDocument` already stores multiple pages, but the scanner API currently exposes only one page per call. Therefore the document model is multi-page while the hardware acquisition path is not.

## API evolution

Add a non-pure virtual method to `ScannerBackend`:

- `scan_pages(device_id, options)` returns an ordered `std::vector<ImagePage>`.
- Its compatibility default calls `scan_one()` and returns a one-element vector, so existing test doubles and downstream backends remain source-compatible.
- `SaneScannerBackend` overrides it and performs the SANE multi-frame protocol.
- Keep `scan_one()` as the existing single-page contract. It must not silently discard later pages; if the selected source produces more than one frame, fail with a stable `ScannerError` code/message and require callers to use `scan_pages()`.

The desktop/controller layer should append returned pages to `ImageDocument` in acquisition order. The scanner backend must not depend on GTK, Writer, or Almas request state.

## SANE acquisition state machine

1. Validate device identifier and options before initializing SANE.
2. Acquire the process-wide SANE mutex, initialize SANE, open the selected device, and apply supported options once before the first frame.
3. For each frame, call `sane_start()`, then `sane_get_parameters()`.
4. Validate frame format, depth, dimensions, stride, byte-count arithmetic and configured resource limits before allocating memory.
5. Read until `SANE_STATUS_EOF`; reject negative/oversized read lengths, excess bytes, zero-progress reads and incomplete frames.
6. If `SANE_Parameters.last_frame` is true, finish the document. Otherwise start the next frame using the same open device handle.
7. On any failure, call `sane_cancel()` for the active frame before closing the handle and exiting SANE.
8. Preserve frame order exactly as reported by the backend. Do not infer front/back labels from frame parity unless the device's duplex contract is independently established.

## Resource and failure policy

- Set a conservative configurable maximum page count (initial default: 100 pages).
- Keep the existing per-frame 1 GiB ceiling, but add a total-document byte ceiling so a multi-page scan cannot multiply the memory budget without bound.
- Check multiplication/addition overflow before reserve/append.
- Treat unsupported bit depth or frame formats as explicit errors; do not silently reinterpret lineart, 16-bit gray, or planar data.
- Distinguish feeder-empty, paper-jam, cover-open, I/O failure and user cancellation only where SANE status/backend evidence supports the distinction. Preserve the raw SANE status in diagnostics without leaking sensitive device data.
- If a later page fails, return an error and do not present a partial document as a complete successful scan. A future UI may offer explicit recovery of already acquired pages.

## ADF and duplex semantics

- ADF support is selected through the device's advertised `source` option; never hardcode vendor-specific option names beyond the existing SANE standard option lookup.
- Duplex must be represented as a capability only when the device exposes a documented duplex source/option or the backend provides reliable metadata.
- Multi-frame does not automatically mean duplex: a device can emit multiple frames for color channels or other reasons. Frame format and `last_frame` must be interpreted per SANE, not assumed to mean one sheet per frame.
- Front/back ordering must be tested against a real duplex device before exposing a user-facing “duplex” guarantee.

## Required automated tests

Use an injectable SANE function table or a narrow frame-reader abstraction to test without physical hardware:

- one-frame success and compatibility behavior of `scan_one()`;
- two and three frame success with stable order and independent DPI metadata;
- `last_frame` true/false transitions;
- second-frame start failure and second-frame read failure;
- EOF with short/incomplete payload, no-progress read, negative length and excess bytes;
- frame count and total byte budget enforcement;
- cancellation on every active-frame error path;
- unsupported format/depth on a later frame;
- feeder-empty/jam/cancel status propagation without falsely reporting successful completion.

## Hardware acceptance

Before declaring ADF/duplex supported, record model, SANE backend name/version, source option values, frame count, `last_frame` sequence, page order and resulting page count for at least one physical ADF device. Duplex requires a physical duplex device. CI fake tests are not hardware acceptance.

## Implementation sequencing

1. Introduce the backward-compatible vector API and frame-reader seam.
2. Refactor one-frame acquisition through the shared frame validation/reader path.
3. Add multi-frame loop and aggregate limits.
4. Add deterministic fake-frame tests and run native + sanitizer workflows.
5. Add ADF/duplex UI options only after capabilities and hardware evidence are available.
