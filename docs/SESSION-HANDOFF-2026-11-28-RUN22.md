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


The 5 ms wait call is now verified as `kernel32!Sleep` at thunk `0x004028D0` / IAT `0x0062F09C`. TD32 labels the same thunk `SuspendThread`, which is a stale/misleading symbol; trust the PE import. The next thunk `0x00404F04` is still being identified.


The second call in the retry loop is now identified as `Vcl.Forms.TApplication.ProcessMessages` at thunk `0x00404F04` / IAT `0x00630038`. Thus the loop is explicitly `Sleep(5 ms)` + VCL message pumping + queue recheck; no timeout was observed.


## Additional parallel lanes (after Run 22)

- TIFF output lifecycle: run `46118848571`, success, artifact `15252563510`.
- GearType resolution constants: run `46118936944`, success, artifact `15253185071`.
- GearType resolution consumer: run `46119039684`, success, artifact `15252484299`.
- GDI+ TIFF save API surface: run `46119009748`, success, artifact `15252962538`.
- Word spool loop/document-name helper: run `46119247319`, success, artifact `15253240740`.
- Wait API verification: run `46119407268`, success, artifact `15252639245`.
- VCL companion import resolution: run `46119495733`, success, artifact `15252544710`.
- GDI+ Save/SaveAdd method and encoder-parameter trace: run `46119662918`, in progress at handoff time.

The 5 ms queue loop is confirmed as `kernel32!Sleep(5)` followed by `Vcl.Forms.TApplication.ProcessMessages`, then a fresh `EnumJobsW` lookup. It waits while the matching job exists and advances when absent; no timeout was observed. The candidate name is normalized by `FixDirectionInFarsiNumericMode` before comparison.


GDI+ caveat: the PE import table and TD32 thunk labels disagree for the save APIs. Treat PE import names as primary but cross-check with a second parser and TGPImage VMT slots before mapping a specific Save overload; TD32 also mislabeled the verified Sleep thunk.


GDI+ encoder parameters are now decoded: `0x0062A84C` points to the standard `EncoderCompression` GUID and is passed value 2 (LZW); `0x0062A804` points to the standard `EncoderSaveFlag` GUID and is passed value 18 (MultiFrame). This is strong evidence for multipage TIFF with LZW compression. Interface VMT mapping for initial Save / SaveAdd / final flush remains open.


GDI+ import identity is now independently confirmed: GNU `objdump -p` agrees with the PE import parser for GdipGetImageGraphicsContext, GdipSaveAddImage, GdipSaveAdd, GdipSaveImageToStream, and GdipSaveImageToFile. The TD32 labels on the corresponding thunk addresses are shifted/stale. Remaining work is the TGPImage interface VMT slot-to-call mapping.


SevenZip callback-detail run `46119766144` further shows `SaveToFile` is a stub (fixed out values, returns zero), while `SaveToStream` creates a stream wrapper and calls `SetCompleted`. Progress callback is stored separately at +0x38; operation-result callback/context are +0x30/+0x34. See `docs/SEVENZIP-OUTPUT-ARCHIVE-OWNERSHIP-2026-11-28.md`.


GDI+ interface boundary: SeparteImages creates TGPEncoderParameters (VMT pointer 0x00483FA4 loaded from global slot 0x00483F4C) and obtains its interface at object +0x28, then calls interface slot +0x20 with the compression/save-flag GUIDs. TGPImage is created with VMT pointer 0x00484780 loaded from global slot 0x00484728; its interface is called through slots +0x48/+0x70/+0x74/+0x5C/+0x58. The interface metadata blocks are complex Delphi RTTI structures, not simple pointer arrays; exact Save/SaveAdd/final-flush identities remain open.


## GDI+ and SevenZip closure run updates

- GDI+ Save/SaveAdd methods and encoder constants: run `46119662918`, success, artifact `15252784605`.
- GDI+ VMT/encoder GUID pointer analysis: run `46120082255`, success, artifact `15253750667`.
- GDI+ PE import cross-check with GNU objdump: run `46120131505`, success, artifact `15253595662`.
- GDI+ interface VMT candidate dump: run `46120260548`, success, artifact `15253721199`.
- GDI+ interface method detail: run `46120428310`, success, artifact `15253761384`.
- SevenZip output callback detail: run `46119766144`, success, artifact `15253196955`.

Latest branch head at this handoff: `37dbd31b38a1a89dcbe88e8ad23f9f02f39a9d0f`. New three-lane Word/TIFF/scanner closure workflow was added at this commit; no run ID was visible yet.


Word close-handler correction: the TD32-named `WordAppDocumentBeforeClose` is now identified as a Boolean print-field helper. Call chain: `GetFieldIndexInList` → `FillImgFldsForPrint` → `WordAppDocumentBeforeClose`; it inspects field arrays and document metadata. It is not an active COM close callback in the observed wiring. See `docs/WORD-BEFORECLOSE-NAMED-HELPER-AND-PRINT-FIELD-CHAIN-2026-11-28.md`.


Corrected VMT pass: global slot 0x00483F4C contains 0x00483FA4 (not 0x00483FA0); TGPImage global slot 0x00484728 contains 0x00484780. The structures are Delphi class/interface metadata with interleaved records, not flat method arrays; interface dispatch semantics remain the reliable contract.


## New contract closure lanes

- Parallel Word/TIFF/scanner trace: run `46120657637`, success; artifacts `15253243404` (Word), `15253702066` (TIFF), `15252979938` (scanner).
- Corrected GDI+ class-pointer pass: run `46120792038`, success; artifact `15253014782`. It corrected the TGPEncoderParameters class pointer to `0x00483FA4` and TGPImage pointer to `0x00484780`; raw structures are Delphi metadata/interleaved records, not flat vtables.
- Scanner XML root/property-string closure: run `46120998177`, in progress.
- Base64/TIFF payload trace: run `46121009769`, in progress.

New Word finding: `WordAppDocumentBeforeClose` is a Boolean print-field helper called only from `FillImgFldsForPrint`, itself called by `GetFieldIndexInList`; it is not a COM close event handler in this call graph. New TIFF constants: `.tif` extension and paused-printer/error messages; Base64Decode is shared by print fields and image rotation, so its TIFF call does not prove filename decoding.


Scanner XML root/property names are now recovered: `scan-document` root; `constraints` child; `colorDepth`, `minResolution`, `maxResolution`, `maxFileSize` fields; `error` property and its XML error prefix. See `docs/SCANNER-XML-ROOT-AND-PROPERTY-NAMES-2026-11-28.md`. Required/optional/default semantics remain open.


TIFF load path resolved: `SeparteImages` pushes zero for both `TGPImage` constructor calls, obtains a UnicodeString path via object interface slot +0x0C, and selects the constructor branch that calls `GdipLoadImageFromFile`. Thus the observed page input is file-backed; the alternate stream branch is not used in this path.


Base64/GDI+ load closure (run 46121270958): Base64Decode is a shared AnsiString-to-AnsiString Base64 decoder used by SeparteImages, StoreFieldValuesForPrint, and FreeRotate; it is not filename-specific. GDI+ constructor load branches are both file APIs: zero flag → GdipLoadImageFromFile; nonzero flag → GdipLoadImageFromFileICM (GNU objdump confirms the imports). SeparteImages passes zero twice, so it uses non-ICM file loading.
