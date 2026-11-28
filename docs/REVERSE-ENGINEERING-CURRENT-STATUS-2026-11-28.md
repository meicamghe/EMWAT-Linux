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

- SevenZip output ownership is more bounded: T7zPlugin creates the T7zOutArchive initializer via constructor-style call to 0x004543C4, stores it at +0x44, and passes it through plugin slot +0x30. The object keeps an interface at +0x2C and callback/context at +0x30/+0x34. SetPassword remains a stub; encryption remains unproven. See `docs/SEVENZIP-OUTPUT-ARCHIVE-OWNERSHIP-2026-11-28.md`.

- Scanner unit closure: `TResultImage.GetFileStream` returns the 64-bit `TStream.Size` byte count, and `Finalization` compares it to `MaxFileSize * 1024`, proving the XML field is KiB. `TGearImgProc.GearType` uses 39.37008 and 0.3937 conversion constants; selectors 2/3/4 map to divide-by-39.37008 / unchanged / divide-by-0.3937. Exact ImageGear enum names and rounding are still open. See `docs/SCANNER-RESOLUTION-AND-FILESIZE-UNITS-2026-11-28.md`.

- TIFF path is now better bounded: LoadDocument calls SeparteImages; it performs printer checks and the hidden worker before GDI+ TGPImage/TGPEncoderParameters page processing. GDI+ Save/SaveAdd wrappers and GdipSaveImageToFile/Stream imports are confirmed; the specific SeparteImages overload, output filename, encoder parameters, and worker completion signal remain open. See `docs/TIFF-OUTPUT-GDIPLUS-PIPELINE-2026-11-28.md`.

- Queue-name handling: before the `EnumJobsW` comparison, Word passes the candidate through `FixDirectionInFarsiNumericMode`. The caller waits while a matching job remains; no explicit timeout was seen. Queue disappearance is a heuristic, not a success result.

- Delay-call cross-check: `0x004028D0` is `kernel32!Sleep` (IAT `0x0062F09C`), despite a misleading TD32 `SuspendThread` symbol. Word polls every 5 ms while the matching job remains. The following `0x00404F04` import is still unresolved.

- The Word queue loop is confirmed as `Sleep(5 ms)` followed by `TApplication.ProcessMessages` (thunk `0x00404F04`), then another `EnumJobsW` check. It keeps the UI responsive while waiting for the matching job to disappear; no timeout was observed.


## Latest run inventory

The following additional static-analysis runs passed: TIFF lifecycle `46118848571`; GearType constants `46118936944`; GearType consumer `46119039684`; GDI+ save API surface `46119009748`; Word spool loop `46119247319`; Sleep import verification `46119407268`; VCL ProcessMessages import resolution `46119495733`. GDI+ Save/SaveAdd method and encoder-parameter trace `46119662918` is still running. Artifacts and findings are indexed in the session handoff.

- GDI+ caveat: PE import names and TD32 thunk labels disagree on the Save/SaveAdd thunk addresses. The exact Save overload used by SeparteImages remains provisional until a second import parser and VMT-slot mapping agree.

- TIFF encoder settings resolved: the encoder receives `EncoderCompression=2` (LZW) and `EncoderSaveFlag=18` (MultiFrame) via the standard GDI+ GUIDs. This is strong evidence for multipage LZW TIFF; exact Save/SaveAdd/final-flush VMT mapping remains open.


GDI+ import identity is now independently confirmed: GNU `objdump -p` agrees with the PE import parser for GdipGetImageGraphicsContext, GdipSaveAddImage, GdipSaveAdd, GdipSaveImageToStream, and GdipSaveImageToFile. The TD32 labels on the corresponding thunk addresses are shifted/stale. Remaining work is the TGPImage interface VMT slot-to-call mapping.

- SevenZip output detail: SaveToFile is a stub; SaveToStream is the implemented path and calls SetCompleted. Progress callback +0x38 is separate from operation-result callback/context +0x30/+0x34. No output password path is proven.


GDI+ interface boundary: SeparteImages creates TGPEncoderParameters (VMT pointer 0x00483FA4 loaded from global slot 0x00483F4C) and obtains its interface at object +0x28, then calls interface slot +0x20 with the compression/save-flag GUIDs. TGPImage is created with VMT pointer 0x00484780 loaded from global slot 0x00484728; its interface is called through slots +0x48/+0x70/+0x74/+0x5C/+0x58. The interface metadata blocks are complex Delphi RTTI structures, not simple pointer arrays; exact Save/SaveAdd/final-flush identities remain open.


## Latest GDI+ / SevenZip run inventory

GDI+ Save/SaveAdd methods `46119662918`, VMT/encoder GUIDs `46120082255`, GNU objdump import cross-check `46120131505`, interface VMT dump `46120260548`, interface method detail `46120428310`, and SevenZip callback detail `46119766144` all completed successfully. The latest three-lane Word/TIFF/scanner workflow was added in commit `37dbd31b38a1a89dcbe88e8ad23f9f02f39a9d0f`; no run was visible at the time of this update.

- Word BeforeClose-named helper is now classified: GetFieldIndexInList → FillImgFldsForPrint → WordAppDocumentBeforeClose; the last routine returns a Boolean for print-field filtering and is not a close operation. The actual close-to-Almas bridge remains unresolved.


Corrected VMT pass: global slot 0x00483F4C contains 0x00483FA4 (not 0x00483FA0); TGPImage global slot 0x00484728 contains 0x00484780. The structures are Delphi class/interface metadata with interleaved records, not flat method arrays; interface dispatch semantics remain the reliable contract.

- Scanner XML strings now establish root `scan-document`, constraints object `constraints`, fields `colorDepth`, `minResolution`, `maxResolution`, `maxFileSize`, and error property `error`. Required/default semantics remain open.


TIFF load path resolved: `SeparteImages` pushes zero for both `TGPImage` constructor calls, obtains a UnicodeString path via object interface slot +0x0C, and selects the constructor branch that calls `GdipLoadImageFromFile`. Thus the observed page input is file-backed; the alternate stream branch is not used in this path.


Base64/GDI+ load closure (run 46121270958): Base64Decode is a shared AnsiString-to-AnsiString Base64 decoder used by SeparteImages, StoreFieldValuesForPrint, and FreeRotate; it is not filename-specific. GDI+ constructor load branches are both file APIs: zero flag → GdipLoadImageFromFile; nonzero flag → GdipLoadImageFromFileICM (GNU objdump confirms the imports). SeparteImages passes zero twice, so it uses non-ICM file loading.

- TIFF orchestration now ties the pipeline together: GAM printer setup → THidePrintingThread.Execute → page-file list from helper 0x004A0BA8 → TStringList → GDI+ file loads → multipage LZW TIFF. Output path starts from euGetASFileName(".tif"); exact directory/name policy and Save/SaveAdd dispatch remain open.

## Run 29 correction and next gates

Run 29 reconciles existing artifacts across Word, scanner XML, and TIFF output. The key correction is that `0x004CD154` is functionally the registered close/save-decision callback that releases the HTTP wait, but its COM event DISPID remains unknown; `0x004CCBBC` is the unrelated print-field helper. The hidden TIFF worker now has complete byte coverage (3,096 bytes, 28 skipdata bytes), not complete instruction decoding. Scanner string/boolean getter helper families are identified, but their XMLRTL default semantics and the `none/jpg/yes/no` property mapping remain unresolved. See `docs/REVERSE-ENGINEERING-PARALLEL-FOLLOWUP-2026-11-28-RUN29.md`.
