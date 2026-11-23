# SANE multi-frame and ADF implementation contract

Status: design contract for the next scanner implementation; no claim of ADF or duplex support.

## Current implementation boundary

`SaneScannerBackend::scan_one()` performs one `sane_start()`, reads one frame until `SANE_STATUS_EOF`, and returns one `ImagePage`. It accepts only 8-bit Gray and RGB frames. `ImageDocument` stores multiple pages. The public `ScannerBackend` now also exposes `scan_pages()` as a non-pure virtual compatibility method; its default implementation wraps `scan_one()` in a one-element vector. This establishes a source-compatible batch API, but the current SANE backend does not yet override it, so actual ADF/multi-page acquisition is still unavailable.

## API evolution

The first API-evolution step is now implemented as a non-pure virtual method on `ScannerBackend`:

- `scan_pages(device_id, options)` returns an ordered `std::vector<ImagePage>`.
- Implemented compatibility default calls `scan_one()` and returns a one-element vector; the fake-backend test covers this fallback. Existing test doubles and downstream backends remain source-compatible.
- **Not yet implemented:** `SaneScannerBackend` must override it and perform the SANE multi-frame/feeder protocol.
- Keep `scan_one()` as the existing single-page contract. It must not silently discard later pages; if the selected source produces more than one frame, fail with a stable `ScannerError` code/message and require callers to use `scan_pages()`.

The desktop/controller layer should append returned pages to `ImageDocument` in acquisition order. The scanner backend must not depend on GTK, Writer, or Almas request state.

## SANE acquisition state machine

1. Validate device identifier and options before initializing SANE.
2. Acquire the process-wide SANE mutex, initialize SANE, open the selected device, and apply supported options once before the first frame.
3. Treat one `sane_start()` through its terminal frame (`last_frame=true`) as one page-acquisition cycle. Call `sane_get_parameters()` for every frame in that cycle.
4. Validate frame format, depth, dimensions, stride, byte-count arithmetic and configured resource limits before allocating memory.
5. Read each frame until `SANE_STATUS_EOF`; reject negative/oversized read lengths, excess bytes, zero-progress reads and incomplete frames.
6. If `last_frame` is false, call `sane_start()` again on the same open handle to obtain the next frame of the *same page*. If it is true, finish assembling that page.
7. Do not equate SANE frames with pages. Planar RGB backends may emit RED/GREEN/BLUE frames for one page; combine only a verified, correctly ordered channel set into one RGB page. Preserve Gray/RGB interleaved frames as one page. Reject unknown or inconsistent frame sequences rather than returning color planes as separate pages.
8. Only after a page's final frame, and only when an explicitly selected source is positively identified as a feeder, start the next page cycle. Treat `SANE_STATUS_NO_DOCS` at that boundary as normal feeder completion; propagate other statuses. A flatbed source must not be repeatedly started.
9. On any failure, call `sane_cancel()` for the active frame before closing the handle and exiting SANE.
10. Preserve page order and within-page frame order exactly as reported by the backend. Do not infer front/back labels from frame parity unless the device's duplex contract is independently established.



### Important frame/page distinction

SANE's `last_frame` marks the end of a frame sequence, not necessarily the end of a feeder batch. A multi-frame sequence can encode one image (for example, planar RGB); it must be assembled into one `ImagePage`. ADF batch acquisition is a separate outer loop that starts another scan cycle after the previous page is complete, and is safe only for an explicitly selected, positively identified feeder source. The public `scan_pages()` API returns pages, never raw SANE frames.

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
