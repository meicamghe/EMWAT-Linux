# Session handoff — 2026-11-28, after parallel runs 22–25

Current branch: `feature/recovery-retention-policy`

## Latest verified CI

- Run 22: `46112005385`; all four jobs passed: scanner-result-ownership, imageen-acquisition, word-printer-thread, native-regression.
- Contract closure: `46117085322`; all four jobs passed: scanner XML, Word PrintOut ABI, Winspool import xrefs, SevenZip output.
- Winspool thunk audit: `46117338896`; success. Artifact `15252371518`.
- Printer queue correlation: `46117480260`; success. Artifact `15252845315`.
- Print queue completion / driver follow-up: `46117826449`; success. Artifact `15252751125`.
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
- `MaxFileSize` is interpreted in KiB: `Finalization` multiplies the configured integer by 1024 (`shl 10`) before comparing it with the 64-bit image-size result from `0x004ECD60`. Confirm that helper's source length before implementing.
- Four color modes and resolution validation are recovered. Root metadata/defaults and runtime XML examples remain open.

## Confirmed printer / Word / queue contract

- `Zanprinter.GetPrinterName` enumerates `PRINTER_INFO_2A` and selects a printer by comparing `pDriverName` at +0x10 with a constant at `0x0047CC64`; it stores `pPrinterName` (+0x04) in global `0x0062B310`. Literal driver name still needs decoding.
- `Zanprinter.Finalization` opens that printer, gets `PRINTER_INFO_2A` level 2, closes it, and checks Status at +0x48 for value 1 (paused).
- `getPrinterNumJobs` actually calls `OpenPrinterW` and returns the handle; it does not count jobs itself.
- `ExtractFileNameEX` calls `EnumJobsW` twice (buffer sizing + data), iterates `JOB_INFO_1W` records at 0x40 stride, reads `pDocument` at +0x10, and compares the job document name with the supplied UnicodeString.
- Direct callers of `getPrinterNumJobs` include `TWordViewer.BGPrintWithGamPrintOptions` and `TrimLF` in module `frmWordPrintOptionUnit` (procedure start `0x004A609C`; not a `TCreateTiff` method). The direct link from `BGPrintWithGamPrintOptions` to `ExtractFileNameEX` is now proven: it waits while the matching `JOB_INFO_1W.pDocument` remains in the queue, retries after a short delay, and advances when the match disappears; it then closes the printer handle. The final TIFF/archive gate remains open.
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

1. Resolve the exact role of `frmWordPrintOptionUnit.TrimLF`; connect the queue-disappearance result to TIFF output/archive completion.
2. Trace `GetZanInstallDir`, helper `0x00401240`, and the full printer setup/installation branch; driver literal `zvprt1` is already decoded.
3. Trace `Zanprinter.CheckPrinterPaused` at `0x0047D448` and reconcile it with Finalization.
4. Resolve the 18-vs-17 Word PrintOut ABI against exact WordXP type-library metadata.
5. Map SevenZip output callback construction and `euResetMemory` VMT slots.
6. Confirm the exact byte source behind `0x004ECD60` and scanner root metadata/default behavior.
7. Keep ImageEn Acquire blocked at the missing matching `PKIECtrl23.bpl` boundary.

## Guardrails

Reverse engineering only. Do not start Windows or Linux release builds, do not implement inferred protocols, do not merge/rebase, and do not alter main. Static CI success is not physical-device or Almas acceptance.


## Confirmed Word-to-spool queue gate

A direct caller trace of `BGPrintWithGamPrintOptions` now proves the queue polling sequence: it obtains a printer handle with `getPrinterNumJobs`, prepares each document-name string, calls `ExtractFileNameEX` with the handle and name, waits/retries while the matching `JOB_INFO_1W.pDocument` remains in the queue, and advances when the match disappears. It then closes the handle with `ClosePrinter`. This is the program's queue-disappearance completion heuristic, not proof of successful printing or final TIFF/archive success. Full evidence: `docs/PRINTER-QUEUE-AND-GAM-DRIVER-REVERSE-ENGINEERING-2026-11-28.md`.


## SevenZip output ownership update

Run `46118303840` shows `T7zPlugin.Create` calls `T7zOutArchive.CryptoGetTextPassword2` at `0x004543C4` in Delphi constructor-style convention, stores the returned object at plugin offset +0x44, then passes it through plugin interface slot +0x30. The initializer stores a global interface from `0x0062FBB8` at object +0x2C and clears callback/context +0x30/+0x34. `SetPropertie` later installs callback/context; `SetOperationResult` invokes it. Output `SetPassword` remains a stub. `euResetMemory` is a distinct helper, with direct callers only from application finalization and autosave deletion. See `docs/SEVENZIP-OUTPUT-ARCHIVE-OWNERSHIP-2026-11-28.md`.


## Scanner units update

Run `46118668134` closes the size-unit question: `TResultImage.GetFileStream` returns 64-bit `TStream.Size` bytes; `Finalization` compares it against `MaxFileSize << 10`, so MaxFileSize is KiB. `TGearImgProc.GearType` uses constants 39.37008 and 0.3937; unit selectors 2/3/4 apply divide-by-39.37008 / no conversion / divide-by-0.3937. Exact ImageGear enum names and rounding remain to verify. See `docs/SCANNER-RESOLUTION-AND-FILESIZE-UNITS-2026-11-28.md`.


## TIFF/GDI+ pipeline update

Run `46118848571` shows `TWordViewer.LoadDocument` calls `TCreateTiff.SeparteImages` twice; that routine performs GAM-printer checks, invokes `THidePrintingThread.Execute`, then constructs GDI+ `TGPEncoderParameters` and `TGPImage` objects, initializes codecs, and iterates image pages through GDI+ VMT methods. Exact save API/output filename and worker completion contract remain open. See `docs/TIFF-OUTPUT-GDIPLUS-PIPELINE-2026-11-28.md`.


The queue polling loop also normalizes the candidate UnicodeString through `FixDirectionInFarsiNumericMode` before matching it against `JOB_INFO_1W.pDocument`. It waits while a match exists (one-argument delay call with value 5), and no explicit timeout was observed. Absence may mean completion, cancellation, no job submission, or a name mismatch; do not treat it as proof of successful print output.
