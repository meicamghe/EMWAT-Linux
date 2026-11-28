# EMWAT-Linux reverse-engineering status — 2026-11-28

Parallel static-analysis runs 22–25 have produced several new contracts. The evidence is recorded in:

- `docs/REVERSE-ENGINEERING-PARALLEL-FOLLOWUP-2026-11-28-RUN22.md`
- `docs/SCANNER-XML-SERIALIZATION-CONTRACT-2026-11-28.md`
- `docs/WORD-PRINTOUT-18-VARIANT-ABI-RECHECK-2026-11-28.md`
- `docs/PRINTER-QUEUE-AND-GAM-DRIVER-REVERSE-ENGINEERING-2026-11-28.md`

## Proven from static analysis

- Scanner root/key contract: root `scan-document`; nested output node `constraints`; exact UTF-16LE keys `type`, `driverDialog`, `imageEditor`, `multiJpegSupport`, `previousImageName`, `forceSinglePageFiles`, `colorDepth`, `minResolution`, `maxResolution`, `maxFileSize`.
- Scanner request/constraint ownership: DoRequest loads/finalizes; GetNextPage validates each page. Color-depth values and resolution bounds are recovered. MaxFileSize is interpreted in KiB: Finalization multiplies the configured integer by 1024 before comparing against a 64-bit image-size result.
- GAM printer discovery: `Zanprinter.GetPrinterName` enumerates PRINTER_INFO_2A, matches a driver-name constant at `0x0047CC64`, and stores the selected printer name in global `0x0062B310`. Exact literal is pending.
- Printer paused-state: `Zanprinter.Finalization` obtains PRINTER_INFO_2A level 2 and checks Status at +0x48 for value 1.
- Queue correlation: `getPrinterNumJobs` opens a printer handle; `ExtractFileNameEX` calls EnumJobsW twice, iterates JOB_INFO_1W (64-byte records), reads pDocument at +0x10 and compares document names. This is evidence for EMWAT monitoring the Word spool queue by document name.
- Word PrintOut: four callsites through +0x3F0 each pass 18 Variant pointers (15 EmptyParam + 3 prepared). TD32 wrappers stop at 17; exact COM ABI remains unresolved.
- SevenZip output callback plumbing is visible; output SetPassword remains a stub and encryption is unproven.

## Still not proven

- Exact GAM printer driver string, install branch and printer pause helper crosswalk.
- `TrimLF` is a `frmWordPrintOptionUnit` printer-open preflight (not a `TCreateTiff` method); queue-disappearance-to-TIFF/archive gating remains open.
- Actual spool submission/completion is likely delegated to Word's print stack; no direct EMWAT StartDocPrinter/WritePrinter call was recovered.
- WordXP type-library declaration for the 18-Variant caller.
- SevenZip output encryption and euResetMemory VMT slot identities.
- ImageEn Acquire internals (external `PKIECtrl23.bpl` not present).
- Scanner MaxFileSize unit and root metadata/defaults.
- Physical scanner/printer, Office and Almas end-to-end acceptance.

No production Linux code changed. No Windows/Linux release build, merge or rebase was performed. Reverse engineering remains the only active project phase.

- Word-to-spool queue gate is now direct: `BGPrintWithGamPrintOptions` opens a printer handle, checks each generated document name with `ExtractFileNameEX` / `EnumJobsW`, waits/retries while the matching queue entry exists, and advances when it disappears. This is the program's queue-disappearance condition, not an independent proof of successful printing or final TIFF success.
