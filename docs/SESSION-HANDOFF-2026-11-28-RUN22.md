# Session handoff — 2026-11-28, after Run 22

Current branch: `feature/recovery-retention-policy`

## Latest verified state

- Run 22: `46112005385`; all four jobs passed: scanner-result-ownership, imageen-acquisition, word-printer-thread, native-regression.
- Workflow commit: `9ac31f053c3fe8724f2d00819c7e49562f93a7d6`.
- Results report: `docs/REVERSE-ENGINEERING-PARALLEL-FOLLOWUP-2026-11-28-RUN22.md`.
- Run-22 Word/Printer artifact: `15250471963`; scanner artifact: `15250485683`; ImageEn artifact: `15250475053`.
- Follow-up workflow file added: `.github/workflows/emwat-parallel-contract-followup.yml`, commit `743b619af9a139c84fd2de3099ef4f09a3bc9ff4`. It defines four independent lanes: scanner XML contract, Word PrintOut ABI, Winspool/GDI import xrefs, and SevenZip output contract. No workflow run was visible yet when this handoff was written; verify dispatch/run status before relying on artifacts.

## Confirmed new evidence

- Scanner: `DoRequest` owns XML load + finalization; `GetNextPage` owns per-page constraint verification. Selector values map to B/W, grayscale, grayscale-or-256-color, and 24-bit color. Resolution bounds are +0x0C/+0x10; +0x14 is the file-size limit compared to stream size scaled by 1024, consistent with MaxFileSize but exact units still require caller/runtime validation.
- ImageEn: `TImageEnMIO.Acquire` is an external `PKIECtrl23.bpl` import from `TfrmImageTools.InsertPicture`; actual internals are unavailable in the current input. `ScanPicture` is a RET stub in this build.
- Word events: `0x004CD154` is BeforeSave; `0x004CCBBC` is a separate BeforeClose-named helper whose active COM registration remains unproven.
- Print preparation: `SeparteImages` runs printer preflight, calls `THidePrintingThread.Execute`, and iterates image collection items. The worker trace has full byte coverage via skipdata but contains 28 undecoded data pseudo-instructions; no actual spool submission/completion is proven.
- SevenZip: output `SetPropertie` stores callback/context at +0x30/+0x34 and `SetOperationResult` invokes that callback. Output `SetPassword` is a stub; `CryptoGetTextPassword2` alone does not prove encryption. `euResetMemory` uses a different object and virtual slots +0x44/+0x0C/+0x3C.

## Immediate parallel priorities

1. Resolve the 18 local Variant pointers at `BGPrintWithGamPrintOptions` against the 17-Variant `TWordDocument.PrintOut` wrapper; do not assume the arity discrepancy is solved.
2. Correlate Winspool imports, queue job document names, and GAM TIFF output.
3. Identify SevenZip output callback construction, password callback consumers, and `euResetMemory` VMT slots.
4. Resolve scanner `TXMLConstraintsType` property serialization and MaxFileSize units.
5. Keep ImageEn internals blocked at the missing matching `PKIECtrl23.bpl` boundary.

## Guardrails

Reverse engineering only. Do not start Windows or Linux release builds, do not implement inferred protocols, do not merge/rebase, and do not alter main. Static CI success is not physical-device or Almas acceptance.
