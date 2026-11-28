# Session handoff — 2026-11-28, after parallel runs 22–25

Current branch: `feature/recovery-retention-policy`

## Latest verified CI

- Run 22: `46112005385`; all four jobs passed: scanner-result-ownership, imageen-acquisition, word-printer-thread, native-regression.
- Contract closure: `46117085322`; all four jobs passed: scanner XML, Word PrintOut ABI, Winspool import xrefs, SevenZip output.
- Winspool thunk audit: `46117338896`; success. Artifact `15252371518`.
- Printer queue correlation: `46117480260`; success. Artifact `15252845315`.
- Scanner XML string recovery: `46117637962`; success. Artifact `15252222334`.
- Primary evidence reports:
  - `docs/REVERSE-ENGINEERING-PARALLEL-FOLLOWUP-2026-11-28-RUN22.md`
  - `docs/WORD-PRINTOUT-18-VARIANT-ABI-RECHECK-2026-11-28.md`
  - `docs/PRINTER-QUEUE-AND-GAM-DRIVER-REVERSE-ENGINEERING-2026-11-28.md`
  - `docs/SCANNER-XML-SERIALIZATION-CONTRACT-2026-11-28.md`

## Confirmed scanner contract

- `TScanCommand.DoRequest` owns XML load + finalization; `GetNextPage` owns per-page constraint verification.
- Root XML name is UTF-16LE `scan-document`; output child `constraints`.
- Exact serialized keys recovered: `type`, `driverDialog`, `imageEditor`, `multiJpegSupport`, `previousImageName`, `forceSinglePageFiles`, `constraints`, `colorDepth`, `minResolution`, `maxResolution`, `maxFileSize`.
- `MaxFileSize` is compared to an image-derived stream size scaled by 1024; exact unit/conversion remains open.
- Four color modes and resolution validation are recovered. Root metadata/defaults and runtime XML examples remain open.

## Confirmed printer / Word / queue contract

- `Zanprinter.GetPrinterName` enumerates `PRINTER_INFO_2A` and selects a printer by comparing `pDriverName` at +0x10 with a constant at `0x0047CC64`; it stores `pPrinterName` (+0x04) in global `0x0062B310`. Literal driver name still needs decoding.
- `Zanprinter.Finalization` opens that printer, gets `PRINTER_INFO_2A` level 2, closes it, and checks Status at +0x48 for value 1 (paused).
- `getPrinterNumJobs` actually calls `OpenPrinterW` and returns the handle; it does not count jobs itself.
- `ExtractFileNameEX` calls `EnumJobsW` twice (buffer sizing + data), iterates `JOB_INFO_1W` records at 0x40 stride, reads `pDocument` at +0x10, and compares the job document name with the supplied UnicodeString.
- Direct callers of `getPrinterNumJobs` include `TWordViewer.BGPrintWithGamPrintOptions` and `TCreateTiff.TrimLF`. This establishes the queue-polling path's key components, but the exact call/indirect-reference link to `ExtractFileNameEX` and the final TIFF/archive gate still need proving.
- No direct EMWAT `StartDocPrinter`/`WritePrinter` calls were recovered. Word may own job submission through its print stack; do not mistake missing direct imports for missing spool jobs.

## Confirmed Word PrintOut discrepancy

- Four callsites through document slot +0x3F0: `0x004C70B6`, `0x004C78A4`, `0x004C7F50`, `0x004C87FA`.
- Each passes 18 local Variant-record pointers: 15 EmptyParam + 3 prepared records.
- TD32 wrapper inventory stops at 17 Variants. Exact COM ABI/type-library declaration is unresolved; do not drop an argument or infer semantic parameter names.

## Other boundaries

- ImageEn `TImageEnMIO.Acquire` remains an external `PKIECtrl23.bpl` boundary; the matching BPL is not in the analysis input.
- Word BeforeSave is `0x004CD154`; active BeforeClose registration/bridge remains open.
- SevenZip output callback/context is stored at +0x30/+0x34 and invoked by SetOperationResult; output SetPassword is a stub; encryption remains unproven.
- `THidePrintingThread.Execute` and TIFF processing remain partly opaque; physical printer/Word/Almas acceptance has not been run.

## Immediate parallel priorities

1. Trace `TCreateTiff.TrimLF` and pointer/VMT references to `ExtractFileNameEX`; connect queue match to TIFF output.
2. Decode `0x0047CC64`, trace `InstallZanPrinter`, and prove the exact GAM driver literal.
3. Trace `Zanprinter.CheckPrinterPaused` at `0x0047D448` and reconcile it with Finalization.
4. Resolve the 18-vs-17 Word PrintOut ABI against exact WordXP type-library metadata.
5. Map SevenZip output callback construction and `euResetMemory` VMT slots.
6. Confirm scanner MaxFileSize unit and root metadata/default behavior.
7. Keep ImageEn Acquire blocked at the missing matching `PKIECtrl23.bpl` boundary.

## Guardrails

Reverse engineering only. Do not start Windows or Linux release builds, do not implement inferred protocols, do not merge/rebase, and do not alter main. Static CI success is not physical-device or Almas acceptance.


## Confirmed Word-to-spool queue gate

A direct caller trace of `BGPrintWithGamPrintOptions` now proves the queue polling sequence: it obtains a printer handle with `getPrinterNumJobs`, prepares each document-name string, calls `ExtractFileNameEX` with the handle and name, retries after a short delay when no matching `JOB_INFO_1W.pDocument` is found, and closes the handle with `ClosePrinter`. This is job-appearance detection, not proof of completed printing or final TIFF/archive success. Full evidence: `docs/PRINTER-QUEUE-AND-GAM-DRIVER-REVERSE-ENGINEERING-2026-11-28.md`.
