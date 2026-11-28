## 2026-11-28 — Run 34 print-worker caller gate

- The only direct caller of THidePrintingThread.Execute is TCreateTiff.SeparteImages at 0x004A02B8.
- The caller tests AL immediately; false branches to failure at 0x004A02C1, true continues at 0x004A02D7. Worker success is therefore a hard precondition for the GDI+ TIFF continuation.
- Combined acceptance has two distinct gates: spooler queue disappearance, then generated TIFF file existence accepted by THidePrintingThread. Queue disappearance alone is not proof of output completion.
- Report: docs/REVERSE-ENGINEERING-PARALLEL-FOLLOWUP-2026-11-28-RUN34.md; focused worker doc updated in commit e9b5252; report commit 782d6b9.
- No tests, CI, or package build were run.

## 2026-11-28 — local raw-PE extraction tool

- Added scripts/dump_pe_va_ranges.py and six synthetic PE tests in python/tests/test_pe_va_ranges.py. The tool maps PE32/PE32+ VAs to raw file offsets and prints DWORDs plus ANSI/UTF-16LE strings for the current GDI+, Worker, and XMLRTL target ranges.
- Tests are not executed yet. No CI workflow was started.
- To obtain the missing raw evidence from the tracked BPL: python3 scripts/dump_pe_va_ranges.py analysis-input/EmwatMethods.bpl1

## 2026-11-28 — Runs 32–33 XMLRTL and GDI+ crosswalk refinements

- XMLRTL helper map corrected from full generated-accessor call shapes: 0x0044B498 HasAttribute; 0x0044B488 AttributeNodes list getter; 0x0044B4C0 GetAttribute-style value getter (medium-high); 0x0044B4D8 ChildNodes list getter. The earlier Run 30 labels for 0x0044B488/0x0044B4C0 are superseded. 0x0044B508 remains open.
- GDI+ interface metadata now yields candidate table bases: TGPImage class slot 0x00484728+0x28 -> metadata 0x0047DD2C; RTTI block 0x0047DD84 +0x58 -> candidate VTable base 0x0062EEA0. TGPEncoderParameters class slot +0x28 -> 0x0062EE88. Candidate TGPImage slot addresses include 0x0062EEE8 (+0x48), 0x0062EEF8 (+0x58), 0x0062EEFC (+0x5C), 0x0062EF10 (+0x70), and 0x0062EF14 (+0x74). Actual pointer contents are not present in the artifacts.
- Reports: Run 32 XMLRTL helper correction; Run 33 GDI+ VTable candidates. XML contract commit 835a4d0, Run 32 report e21b8d5, GDI+ crosswalk update 9db37a1, Run 33 report d179b4e.
- No tests, CI, or packages were run. The raw PE range 0x0062EE88–0x0062EF18 and the helper body 0x0044B508 remain the exact next static-analysis targets.

## 2026-11-28 — Run 32 XMLRTL helper correction

- Rechecked all generated scanner accessor callsites against the XMLRTL interface contract. The previous Run 30 helper labels were too broad and are superseded.
- Corrected map: 0x0044B498 = HasAttribute; 0x0044B488 = AttributeNodes list getter; 0x0044B4C0 = GetAttribute-style value getter (medium-high); 0x0044B4D8 = ChildNodes list getter. AttributeNodes and ChildNodes are distinct IXMLNodeList properties.
- Setters traverse AttributeNodes.FindNode(property) and operate on the returned attribute node's value; do not describe 0x0044B4C0 as SetAttribute.
- 0x0044B508 remains unresolved; its zero argument does not prove the absent-attribute Boolean default.
- Run report: docs/REVERSE-ENGINEERING-PARALLEL-FOLLOWUP-2026-11-28-RUN32.md. XML contract update commit 835a4d0; Run 32 report commit e21b8d5.
- No tests, CI, or package build were run.

## 2026-11-28 — Run 31 reverse-engineering cross-correlation

- XMLRTL: the scanner Get_ColorDepth path now maps to IXMLNode.ChildNodes followed by IXMLNodeList.FindNode("constraints"). The ForceSinglePageFiles helper at 0x0044B508 remains unresolved; its zero-valued call argument does not prove the missing-attribute default.
- THidePrintingThread: 0x00404494 is resolved as shell32!ShellExecuteW (IAT 0x0062F9CC), not a printer-status helper. 0x00402818 is the GetVersionEx thunk. The caller initializes 0x114 (276) bytes, matching OSVERSIONINFOW rather than OSVERSIONINFOEXW (284 bytes), despite the TD32 decorated suffix. The worker branches on dwMajorVersion > 5 and performs staged ShellExecuteW calls; their return >32 gates later stages, but final worker success still depends on the final FileExists check.
- GDI+: functional Save/SaveAdd slot mapping remains high-confidence (+0x48 initial SaveImageToFile, +0x5C SaveAddImage, +0x58 final SaveAdd Flush=20). Raw Delphi interface VTable pointer bytes are not present in the current artifacts; the RTTI block must not be treated as a flat method pointer array.
- Run report: docs/REVERSE-ENGINEERING-PARALLEL-FOLLOWUP-2026-11-28-RUN31.md. Focused crosswalks updated. No tests or CI were run and no package was built.
- Remaining exact blockers: recover worker string literals and identify 0x004026B4; disassemble 0x0044B508; obtain raw GDI+ interface table bytes if direct slot-to-code mapping is required. A real TIFF fixture remains lower priority.

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

## Run 30: three proof tracks advanced

Run 30 resolves the core XMLRTL attribute helpers (`HasAttribute`, `GetAttribute`, `SetAttribute`), identifies the hidden print Worker's completion gate as a `FileExists(path, True)` poll after stale-file cleanup, and closes the functional GDI+ Save/SaveAdd sequence (`+0x48` initial SaveImageToFile, `+0x5C` SaveAddImage per later page, `+0x58` final SaveAdd with Flush=20). The raw TGPImage RTTI is still not a flat VMT; slot mapping is grounded in import targets, ABI and control-flow position. Exact Worker path strings/producer, XMLRTL `0x0044B508` semantics, and a runtime TIFF fixture remain open. See the Run-30 report and the three focused crosswalk documents.
