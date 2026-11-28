# EMWAT-Linux reverse-engineering status — 2026-11-28

The latest verified static-analysis run is Run 22 (`46112005385`), with all four jobs successful. The complete evidence and caveats are in `docs/REVERSE-ENGINEERING-PARALLEL-FOLLOWUP-2026-11-28-RUN22.md`.

- Scanner request/constraint path is better bounded: request parsing/finalization and per-page validation are separate; four image modes and resolution bounds are decoded. The +0x14 field maps to `TXMLConstraintsType.MaxFileSize` and is compared with stream size after scaling by 1024; exact external units/conversion remain open.
- ImageEn `Acquire` is an external import from `PKIECtrl23.bpl`; its internals are not present in the current analysis input.
- Word callback correction is maintained: `0x004CD154` is BeforeSave, not BeforeClose. Active BeforeClose registration and browser close bridge are still open.
- `SeparteImages` orchestrates printer checks, hidden worker invocation and per-image processing. Actual Winspool job submission, completion and GAM artifact hand-off remain unproven.
- SevenZip output callback storage/dispatch is now visible at +0x30/+0x34. Output `SetPassword` is a stub; encryption must not be assumed.
- A new four-lane workflow was added at `.github/workflows/emwat-parallel-contract-followup.yml` (commit `743b619af9a139c84fd2de3099ef4f09a3bc9ff4`) to investigate scanner XML, Word PrintOut ABI, Winspool import xrefs and SevenZip output callbacks. Verify that GitHub Actions actually started it before claiming results.

No production Linux code changed. No release build, merge or rebase was performed. Physical scanner, printer, Office and Almas end-to-end acceptance remain outstanding.
