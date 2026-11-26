# SANE scanner and ADF capability status

Date: 2026-11-26  
Branch: `feature/recovery-retention-policy`

## Current implementation (verified from source and regression tests)

The native SANE backend implements two intentionally different acquisition modes:

1. **Single-page / flatbed:** `scan_one()` starts one SANE image transfer, reads one page, then cancels/resets the SANE handle on both success and exception paths.
2. **Explicit simplex ADF batch:** `scan_pages()` enters repeated page acquisition only when the caller explicitly supplies a source label recognized as a simplex feeder. It does not repeatedly start a flatbed.

### Source-label safety rules

The helper `detail::is_adf_source()` accepts explicit feeder labels beginning with `ADF` or `Automatic Document Feeder`, and requires a positive simplex/front-side marker:

- `simplex`
- `front`
- `one-sided`
- `single-sided`

It rejects ambiguous feeder labels, duplex labels, and substring false positives. Regression cases cover `ADF Front`, `ADF (Simplex)`, `ADF-Simplex`, `ADF one-sided`, `Automatic Document Feeder - Simplex`, and negative cases including `ADF`, `ADF Duplex`, `ADF nonsimplex`, `ADF frontline`, `ADFree`, and `Automatic Document Feeder` without a simplex marker.

Duplex detection rejects labels containing `duplex`, `double-sided`, or `two-sided`. `scan_pages()` returns the explicit error `duplex_adf_batch_not_supported` before SANE initialization/device access for a duplex source. This is deliberate: it prevents reporting a one-sided capture as a successful duplex batch.

### Batch safety bounds

- Maximum ADF pages: 100.
- Maximum aggregate batch bytes: 4 GiB.
- Per-page read budget is reduced by bytes already consumed.
- A final feeder probe distinguishes exactly-at-limit completion from truncation.
- Feeder exhaustion (`SANE_STATUS_NO_DOCS` before a page) terminates the batch normally.
- An I/O error or `NO_DOCS` after partial frame bytes is not silently treated as normal feeder exhaustion.
- SANE cancellation/reset is guarded to run once on normal completion and error paths.

### Frame handling

The native page reader accepts 8-bit grayscale and interleaved RGB, and validates planar RGB as an ordered RED/GREEN/BLUE sequence. It checks width, height, stride, line count, frame flags, frame sequence consistency and byte budgets before returning a page. Unsupported depth or malformed/incomplete frame sequences fail explicitly.

## Relationship to the Windows EMWAT binary

The reverse-engineered Windows package has a GEAR32PD-facing scanner path (`IG_scan_source_select`, `IG_scan_pages`, `IG_load_FD`, `IG_save_FD`, `IG_save_file`) plus a distinct ImageEn `TImageEnMIO.Acquire` call in the image-tools UI. The current SANE backend is a Linux-native scanner backend; it is not an implementation of the GEAR32PD ABI and does not claim to reproduce the original driver's device dialogs or all its device-specific options.

The static Windows evidence currently does not establish whether the production workflow uses duplex in its real deployments, nor does it define how the external Almas connector requests simplex versus duplex.

## Remaining work

1. Add runtime scanner acceptance on at least one real simplex ADF device, including empty feeder, jam/error and maximum-page boundary behavior.
2. Capture the exact SANE source labels reported by supported hardware; ensure they map to the positive simplex markers without broadening the classifier unsafely.
3. Define duplex support only after the EMWAT/Almas contract and actual device capability are established. A duplex implementation must preserve front/back page association and ordering; simply repeating simplex starts is not duplex.
4. Connect `std::vector<ImagePage>` batch results to the output contract (`SinglePageFileSet` versus `MultiPageFile`) only after the external `ForceSinglePageFiles` and response naming semantics are proven.
5. Test multi-page TIFF persistence and page metadata end-to-end using actual SANE output.

## Evidence boundaries

- Source and unit tests confirm the current algorithm and its guardrails.
- CI can validate deterministic fake-SANE behavior.
- No physical scanner, ADF, duplex, or full Almas acceptance is claimed by this document.
