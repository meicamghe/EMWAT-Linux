## 2026-11-26 — Run 49 green; ScanCommand paging trace and connector contract extended

Current branch: `feature/recovery-retention-policy`  
Run 49: [45788814934](https://github.com/meicamghe/EMWAT-Linux/actions/runs/45788814934)  
Detailed report: [REVERSE-ENGINEERING-RUN49.md](REVERSE-ENGINEERING-RUN49.md)

- All three Run 49 jobs passed: native regression, Word/Printer/COM, and Image/UI/VMT. Both analysis artifacts were downloaded and reviewed.
- The deep skipdata trace for `TScanCommand.GetNextPage` now covers all 1,340 bytes (16 `.byte` pseudo-instructions). This is full byte coverage, not full instruction decoding; embedded data and branch targets still need validation.
- Confirmed paging path: `VerifyConstraints` then `LoadRequestXML`; branch on `FIsNextPageRequest +0x29`; next-page path checks `FPreviousReturnedFileName +0x2C` against `_P`, updates state bytes `+0x1D/+0x1E`, and updates `ResultImage +0x20`. Four-entry state table at `0x0062A7F0` remains unresolved.
- Confirmed response XML names: root `response-scan`, child `scaned-image`, fields `status`, `errorCode`, `imageName`, `encoding`. Binary constants `success` and `base64` are present in the response path; runtime protocol semantics still need capture.
- `TScanDocument.PerformMethod` dictionary lookup keys now include `wordConfig`, `wordBody`, `letterImages`, and `signData`. Do not infer value types/optionality from key strings alone.
- ImageGear exports/callsites now resolve `IG_IP_flip` and `IG_IP_rotate_multiple_90`; ImageEn import inventory identifies `Acquire`, `LoadFromFileAuto`, `SaveToFileTIFF`, and `PrintImage`.
- Preserved Delphi resources inventory identifies scanner preview and image tools controls (crop, flips, rotations, TIFF/JPEG, multi-image view, add/scan/print). Resource presence is not runtime validation.
- Word/Printer artifact reconfirms `EnumPrintersA` driver match `zvprt1` and actual pause check through `GetPrinterA` status offset `+0x48`; real spool submission remains unproven.
- No code behavior was changed by this analysis. No merge or rebase was performed.

Next:
1. Validate all control-flow destinations in the skipdata trace and recover the four-state table.
2. Trace request/response XML end-to-end, including caller-side interpretation and response collection cardinality.
3. Recover `.tmp` helper output and `document` Variant semantics.
4. Trace ImageEn Acquire through TWAIN/WIA device setup, transfer and TIFF persistence.
5. Resolve Word/GAM actual spool submission and completion.
6. Keep physical scanner/ADF/Duplex and real printer acceptance explicitly open.

## 2026-11-26 — Run 40 complete; SANE variable-height support committed

Current branch: `feature/recovery-retention-policy`  
Current head: `f956e40b1ad3d7dfd4959a7d3df1ce77f0a9dba1`

- Commit `f956e40` supports SANE `lines == -1` for interleaved Gray/RGB and planar RGB frames, deriving height at EOF and rejecting incomplete rows or over-budget frames. Padded row stride remains preserved.
- Run 40 (`45779391301`) is complete and successful on this exact SHA: Native CTest 5/5; Python 317 passed, 9 skipped, 339 subtests passed; Word and Image reverse-engineering jobs both succeeded.
- Artifacts: Run 39 Word `15096235579`, Image `15095104593`; Run 40 Word `15097418557`, Image `15098092258`. Run 39/40 artifacts were downloaded and inspected.
- Run 39/40 scanner evidence: response root `response-scan`, child `scaned-image`, fields `status`, `errorCode`, `imageName`, `encoding`; request properties and `TScanCommand` field offsets are documented in `IMAGE-SCANNER-EDITOR-CALLGRAPH-INVENTORY.md`.
- Run 39/40 printer evidence: `GetPrinterName` enumerates local Level-2 printers, matches driver `zvprt1`, and selects the first matching queue in enumeration order. The configuration/INI path remains in `GAM-PRINTER-CONFIGURATION-RECOVERY.md`.
- `0x00401428` still resolves only to an external RTL target `0x002312F2`; 395 callers are mostly Word property accessors. It is not proven to be a print-worker callback.
- PR #2 remains Draft/open/unmerged; compare is 994 ahead / 9 behind and GitHub says not mergeable. Do not merge/rebase without an explicit decision.

Next parallel targets:
1. Trace `TCreateTiff.SeparteImages` and direct/indirect VCL `TPrinter.BeginDoc/GetCanvas/NewPage/EndDoc` callers.
2. Trace Winspool `OpenPrinter`, `GetPrinter`, and `EnumJobsW` callsites; determine whether the apparent paused/status path is separate from the INI writer.
3. Resolve `TScanCommand` response-list cardinality, `imageName` meaning, and the outer result dictionary key.
4. Keep CUPS backend work behind the confirmed TIFF/job-output contract; do not port the Windows driver installer as if it were a Linux CUPS driver.
5. Obtain physical simplex ADF and Duplex acceptance evidence; current SANE tests use the fake backend.

## 2026-11-26 — run 39 XML tag strings and Word Variant helper targets

- Run 38 (`45773058079`) completed successfully across all three jobs. Its Image artifact (`15094674346`) traced all available TD32 getters/setters for `TXMLResponseScanType`, `TXMLScanedImageType`, `TXMLConfigType`, and `TXMLOutputType`; details and exact procedure VAs are in `docs/IMAGE-SCANNER-EDITOR-CALLGRAPH-INVENTORY.md`.
- `TXMLResponseScanType` exposes `Status`, `ErrorCode`, and `Scanedimage`; each image entry exposes `ImageName` and `Encoding`. Request-side `TXMLConfigType` exposes `Type`, `DriverDialog`, `ImageEditor`, `MultiJpegSupport`, `PreviousImageName`; `TXMLOutputType` exposes `ForceSinglePageFiles` and `Constraints`. The XML property model is now known, but serialized tag strings and `TXMLConstraintsType` details are not yet recovered.
- Reclassified `0x0042ABA0`: its 451 callers are Word document property getters; it lazily obtains an interface via object field `+0x78`/VMT slot `+0x50`, then calls `0x00401428` to assign the interface reference. This is not a print worker callback. The 18-vs-17 `PrintOut` discrepancy remains open.
- Run 39 (`45774122169`, workflow commit `7305d59`) completed successfully. Word artifact `15096235579` and Image artifact `15095104593` were downloaded and reviewed. Run 40 (`45779391301`) then completed successfully on `f956e40`; Word artifact `15097418557` and Image artifact `15098092258` add the ScanCommand constructor/VMT/response path and the external RTL helper trace.

## 2026-11-26 — run 38 XML getter/setter methods and Word helper trace completed

- Run 38 (`45773058079`) completed successfully in all three jobs: Native, Word/print and Image/UI. Native regression passed.
- The image artifact (`15094674346`) now provides symbol-driven body traces for the scanner XML classes. Exact getter/setter procedures are recorded in `docs/IMAGE-SCANNER-EDITOR-CALLGRAPH-INVENTORY.md`:
  - `TXMLResponseScanType`: `Status` getter/setter (`0x004EB8BC`/`0x004EB908`), `ErrorCode` getter/setter (`0x004EB9C0`/`0x004EBA48`), and `Scanedimage` getter (`0x004EBB04`).
  - `TXMLScanedImageType`: `ImageName` getter/setter (`0x004EBB90`/`0x004EBC50`), `Encoding` getter/setter (`0x004EBD0C`/`0x004EBD98`).
  - `TXMLConfigType`: getters/setters for `Type`, `DriverDialog`, `ImageEditor`, `MultiJpegSupport`, and `PreviousImageName`.
  - `TXMLOutputType`: `ForceSinglePageFiles` getter/setter and `Constraints` getter.
- This recovers the Delphi XML object model, but not XML element/tag spelling, list ownership/cardinality, actual values, or the outer result dictionary key. The generic VMT candidates remain unverified; symbol-driven method traces are the trusted evidence.
- The Word artifact (`15095336625`) found 451 callers of `0x0042ABA0`; its body is a shared interface-property getter used by `TWordDocument.Get_*` methods, not a print worker callback. It calls helper `0x00401428`; this does not resolve the 18-vs-17 Variant PrintOut discrepancy. Added this correction to `docs/WORD-PRINT-DISPATCH-AND-WORKER-ANALYSIS.md`.
- Next pass: decode the embedded XML property/tag strings from the traced getter/setter addresses; trace `TXMLConstraintsType` and helper `0x00401428`; keep the `Scanedimage` list/response serialization open until the class/collection contract is established.

## 2026-11-26 — Word PrintOut helper 0x0042ABA0 reclassified

- Run 38 Word artifact `15095336625` traces `0x0042ABA0` and 451 direct callers. Its TD32 label claims `TWordDocument.$bctr`, but the body is a shared interface-property getter used by `TWordDocument.Get_*` accessors: it checks object field `+0x78`, calls VMT slot `+0x50` if null, then passes the interface reference to `0x00401428` for output assignment.
- This is not a print worker callback or constructor path. Updated `docs/WORD-PRINT-DISPATCH-AND-WORKER-ANALYSIS.md`; the 18-Variant caller versus 17-Variant wrapper discrepancy remains unresolved.
- Next Word trace target is helper `0x00401428`, followed by a focused re-audit of interface construction and argument transfer at `0x004C70B6`.

## 2026-11-26 — GAM configuration document argument-order correction

- Cross-checked `docs/GAM-PRINTER-CONFIGURATION-RECOVERY.md` against the actual `SetPrinterForTiffout` and `CheckPrinterPaused` stack argument order.
- Corrected `configure.ini` to section `[allusersfolder]`, key `policy`, default `1` (the previous GAM-specific page had section/key reversed).
- Corrected `save.ini` to section `[save]`, key `popupdialog`, value `No Dialogs` (the previous table had section/key/value transposed).
- The other `save.ini`, `image.ini`, and `general.ini` key/value mappings remain as decoded. This is documentation-only; no Linux printer behavior was implemented.

## 2026-11-26 — run 37 VMT scan inconclusive; run 38 symbol-driven XML tracing

- Run 37 (`45771016476`) completed successfully across Native, Word and Image jobs. The VMT extension found class-name-associated candidates for `TXMLResponseScanType`, `TXMLScanedImageType`, `TXMLConfigType`, and `TXMLOutputType`, but all were explicitly marked **unverified**. Parsed slots `+0x54`/`+0xB8` were unmapped/implausible and the parent metadata pointed outside the BPL to XMLRTL; do not use these candidates to infer the response interface.
- Updated `docs/IMAGE-SCANNER-EDITOR-CALLGRAPH-INVENTORY.md` to distinguish recovered XML property setter names from unresolved VMT/interface-slot identity.
- Extended `resolve_delphi_vmt_slots.py` search targets to include the four scanner XML classes. The VMT scan alone did not resolve their virtual interface methods, so run 38 adds a symbol-driven trace of every TD32 procedure and direct caller belonging to those classes. This should recover method bodies/slot calls without trusting the candidate VMT layout.
- Run 38 (`45773058079`, workflow commit `f844417`) is in progress: image/VMT lane is tracing XML-class procedures; Word print trace and Native regression are also running. Do not claim results until all three jobs finish.
- This is an analysis/tooling-only change; no Linux scanner handler or guessed XML schema was added.

## 2026-11-26 — run 37 scanner XML VMT expansion

- Workflow commit `3f53f522208c45f94261bf6f5321808dcc4a7496` queued run 37 (`45771016531`).
- Extended `resolve_delphi_vmt_slots.py` to include `TXMLResponseScanType`, `TXMLScanedImageType`, `TXMLConfigType`, and `TXMLOutputType`. The goal is to identify the response object's concrete VMT and map interface slots `+0x54` and `+0xB8` without guessing.
- Run 37 completed successfully; its VMT candidates were unverified and did not resolve interface slots `+0x54`/`+0xB8`. See the newer run-37 audit entry at the top of this handoff.

## 2026-11-26 — run 36 ScanResponseXML object and scanner property names recovered

- Run 36 (`45769890366`) completed successfully across Native, Word/print and Image/UI jobs.
- `TScanCommand.FResponseXML` is created through `0x004EB7F4`, whose TD32 identity is `Scanresponsexml.TXMLResponseScanType.AfterConstruction`. The constructor then stores it at field `+0x34) and calls its interface slot `+0xB8) with callback address `0x004F22A4`; that address lies inside the `TScanCommand` constructor body, so callback semantics remain unresolved.
- Property setter inventory from direct callers of external thunk `0x004012F8`:
  - `TXMLResponseScanType`: `Status` (`0x004EB964`), `ErrorCode` (`0x004EBAA4`).
  - `TXMLScanedImageType`: `ImageName` (`0x004EBCAC`), `Encoding` (`0x004EBDF4`).
  - `TXMLConfigType`: `Type`, `DriverDialog`, `ImageEditor`, `MultiJpegSupport`, `PreviousImageName`.
  - `TXMLOutputType`: `ForceSinglePageFiles`.
- These are Delphi property names and setter callsites, not a complete XML schema. Root/tag hierarchy, required values, image list ownership, outer result key and serialization remain open. `0x004012F8` is an external/relocated thunk whose target is outside the BPL; do not name it as a dictionary API.
- ImageEn wrapper/caller traces remain a distinct `TfrmImageTools` path; no shared handoff to `TScanDocument` or the ImageGear preview path has been demonstrated.
- Updated `docs/IMAGE-SCANNER-EDITOR-CALLGRAPH-INVENTORY.md` and `docs/CONNECTOR-HANDLER-ENTRYPOINT-INVENTORY.md` with the response/request property inventory and method-name caveat.

## 2026-11-26 — run 36 supersedes cancelled run 35

- Run 35 (`45769864678`) was cancelled by the newer workflow commit `713cb7a1878a90aadf8c2137433b606d23575cb5`, which queued run 36 (`45769890366`). This is a superseded run, not a test failure.
- Run 36 completed successfully and produced the `FResponseXML` factory/callback and ImageEn wrapper artifacts described below.

## 2026-11-26 — run 35 superseded by run 36 response XML and ImageEn tracing

- Run 35 (`45769864678`, workflow commit `a1f0c7ae5853f5bf004dbb9e697e8f08b5e180a3`) was cancelled when the next workflow commit queued run 36 (`45769890366`). This is a superseded CI run, not a test failure.
- Run 36 (`713cb7a1878a90aadf8c2137433b606d23575cb5`) traces the `FResponseXML` factory/helper `0x004EB7F4`, constructor callback `0x004F22A4`, and ImageEn wrapper/call targets used by `TfrmImageTools` (`Acquire`, `SaveToFileTIFF`, `PrintImage`, `SaveToFile`, `ExecuteSaveDialog`, `GetParams`, and supporting MView calls).
- Goal: identify the concrete response XML object behind `TScanCommand.FResponseXML`, its interface slots `+0xB8` and `+0x54`, and the handoff that populates the scanner result dictionary. Separately clarify whether ImageEn Acquire is a scanner/device source or another image insertion path. Do not merge it with ImageGear/ScanDocument without a shared handoff.
- Run 36 completed successfully in all three jobs. Native regression passed; the Image and Word artifacts are available for follow-up.

## 2026-11-26 — run 34 completed: ScanCommand and ImageEn caller contracts expanded

- Run 34 (`45768861461`) completed successfully in all three lanes: Native regression, Word/print analysis, and Image/UI analysis. Artifacts: Word `15093730448`, Image `15092409839`. Native C++ and Python bridge tests passed.
- `TScanCommand` constructor `0x004F21DC` is directly called by runtime `TScanDocument.PerformMethod`. Class-name/field-table metadata identifies `TScanCommand` with instance size `0x40`; field offsets include `ResultImage +0x20`, `FEditorForm +0x24`, `FCommandState +0x28`, `FIsNextPageRequest +0x29`, `FPreviousReturnedFileName +0x2C`, `FRequsetXML +0x30`, and `FResponseXML +0x34`. Parent VMT pointer `0x0062EEA4` is outside the BPL image, so its virtual layout remains unverified.
- After `GetNextPage`, the public scanner handler reads field `FResponseXML` at `+0x34` through interface slot `+0x54`, then calls unresolved helper `0x004012F8`. Its IAT target is outside the image; the output dictionary key/XML root/tag/serialization remain unknown. No response schema was guessed.
- Method-name conflict: RTTI published-method table bytes list `DoRequest` at `0x004F2558`, while TD32 labels that VA `GetNextPage`; a separate `DoRequest(UnicodeString)` exists at `0x004F22E4`. Keep the call addresses distinct until the RTTI method-table encoding is reconciled.
- ImageEn caller procedures are now mapped: `Acquire` from `TfrmImageTools.InsertPicture`; `LoadFromFileAuto` from `FreeRotate` and `DeletePicture`; `SaveToFileTIFF` from `btnPrinterSetupClick`; `SaveToFile` from `CreateParams`; `PrintImage` from `DoPrintingPanel`. Keep ImageEn acquisition/edit/print separate from ImageGear preview and public `ScanDocument` until a shared file/session handoff is proven.
- GAM printer analysis now confirms `EnumPrintersA` Level-2 enumeration, stride `0x54`, and driver-name match `zvprt1`; the matching `pPrinterName` is copied to active-printer storage. Full INI/registry contract is in `docs/GAM-PRINTER-CONFIGURATION-RECOVERY.md`.
- Updated `docs/IMAGE-SCANNER-EDITOR-CALLGRAPH-INVENTORY.md`, `docs/CONNECTOR-HANDLER-ENTRYPOINT-INVENTORY.md`, and GAM printer docs. No production Linux scanner or printer handler was added.

## 2026-11-26 — run 34 supersedes the cancelled run 33

- Run 33 (`45768755921`) was cancelled when the expanded workflow commit `34a2900e9c53ca5262c227f9ab977322bb01fc74` queued run 34 (`45768861461`). This is a superseded CI run, not a test failure.
- Run 34 includes the `TScanCommand` constructor/VMT inspection and ImageEn caller-procedure traces, plus expanded scanner result-ownership/GAM analysis. Native regression (C++ and Python bridge) and the Word/print lane have completed successfully; the Image/UI lane is still running. Word artifact `15093730448` confirms `EnumPrintersA` Level-2 enumeration and the `zvprt1` driver-name match; details are in `docs/GAM-PRINTER-CONFIGURATION-RECOVERY.md`.

## 2026-11-26 — preview scanner UI output and ImageGear API boundaries traced

- Run 32 Image/UI job (`45767912737`, artifact `15092827056`) completed successfully; the parallel Word/print job and native regression also passed.
- `TfrmGScanPreview.Scan` (`0x0061DC80`) builds a path ending in `_New.tif`, iterates one-based page indices, reuses the current page handle or loads another with `IG_load_FD`, opens the same output path with `CreateFileW(OPEN_ALWAYS)` per page, calls `IG_save_FD` with the page index, and closes each handle. Format argument is `0x40028` or `0x80028` depending on form field `+0x434`.
- This is strong evidence for a single page-indexed multipage `_New.tif` container in the preview UI path only. Do not assume the public `ScanDocument` connector's `TSetOfMultiPageImages` uses the same ownership semantics.
- Resolved GEAR imports: `IG_scan_source_select`, `IG_scan_pages`, `IG_error_check`, `IG_error_clear`, and `IG_error_get`. Argument/callback/error contracts remain open.
- Added details to `docs/IMAGE-SCANNER-EDITOR-CALLGRAPH-INVENTORY.md` and `docs/NATIVE-IMAGE-PARITY-GAP-2026-11-25.md`. No native scanner code was changed.

## 2026-11-26 — run 33 scanner/result and ImageEn caller tracing

- Workflow commit `543ebb072b34c24b149df09a45b684a9ab8dd11d` starts run 33.
- New parallel Image tasks: inspect the `TScanCommand` class/VMT candidate (`0x004F1F94`) and class pointer (`0x004F1F3C`); trace constructor `0x004F21DC` and callers; trace dictionary insertion helper `0x004012F8); and resolve enclosing procedures for ImageEn `Acquire`, `SaveToFileTIFF`, `SaveToFile`, `LoadFromFileAuto`, `GetParams`, print and dialog callsites.
- Also tracing path/stream helpers `0x00454B9C`, `0x00403268`, `0x00403378`, `0x00401348`, and `0x00401370` used by runtime `TImageEdition`/file paths.
- Keep ImageEn and ImageGear paths separate until caller procedures prove their relationship. No production connector code is being guessed or added.

## 2026-11-26 — run 32 completed; next scanner/result trace targets

- Run 32 (`45767912737`) completed successfully across all three jobs; native regression, Word connector traces, and Image/VMT traces passed.
- The runtime `TShowSendLog` target `0x005EFF4C` and base wrapper `0x0046C9E0` are now traced. The wrapper invokes the XML-building `TEmwatMethod.Invoke` then the concrete VMT `+0x10` method. `TShowSendLog` calls global service object `0x0062B4F0`, service slot `+0x13C`, and result getter slot `+0x54`.
- The Image artifact includes a `TScanCommand` class RTTI/VMT candidate at `0x004F1F94` (unverified by the generic VMT scanner; instance size `0x40`) and a type/class pointer used at `0x004F1F3C` by runtime `TScanDocument`. The constructor target is `0x004F21DC`; it has not yet been body-traced. The result object at `TScanCommand+0x34` exposes interface slots `+0x14` (request XML path) and `+0x54` (result value); exact interface class/slot names remain open.
- Run 32 also found a separate ImageEn I/O family: `TImageEnMIO.Acquire` caller `0x0050A364`, `SaveToFileTIFF` `0x0050B6A0`, `SaveToFile` `0x0050AFC4`, `LoadFromFileAuto` `0x00508B88`/`0x0050A4D3`, and several `GetParams`/print/dialog callers. These are distinct from the ImageGear `IG_save_FD` scanner preview path; their enclosing procedures must be traced before assigning semantics.
- Next parallel pass: trace `TScanCommand.Create` (`0x004F21DC`) and VMT/class pointer `0x004F1F3C`/`0x004F1F94`; resolve the `+0x14`/`+0x54` result interface; trace ImageEn caller procedures `0x0050A364`, `0x0050B6A0`, `0x0050AFC4`, `0x00508B88`, `0x0050A4D3`, `0x0050B648`, and related callers. Keep ImageEn and ImageGear paths separate until correlated.

## 2026-11-26 — GAM printer configuration APIs and INI contract recovered

- Run 32 Word/print job (`45767912737`, artifact `15092617354`) completed successfully; native regression also passed. The parallel image job was still running at handoff.
- Resolved the Windows API boundary used by the GAM/Zan printer path: `RegOpenKeyExW`, `RegQueryValueExW`, `RegCloseKey`, `GetPrivateProfileIntW`, `GetPrivateProfileStringW`, `WritePrivateProfileStringW`, `SHGetFolderPathW`, `ShellExecuteW`, `GetVersionExW`, `Sleep`, VCL `Printer/Refresh`, and Delphi `FileExists/DirectoryExists/ExtractFileName/StrComp`.
- `GetZanConfigurationDir` reads `HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\zvprt50\\UninstallString`; fallback uses CSIDL `0x26` (Program Files) plus `zvprt50`.
- `SetPrinterForTiffout` reads `configure.ini` / `[policy]` / `allusersfolder`, selects a Windows special-folder path based on the policy and OS version, and falls back to user AppData if needed.
- `CheckPrinterPaused` writes exact settings to `save.ini`, `image.ini`, and `general.ini`: `save.folder`, `save.basefilename`, `save.filexistact=1`, `popupdialog.No Dialogs=1`, TIFF, 256 image color, LZW compression, page type 0, one strip per page, hidden status dialog, and the `JobFinishes.GAM` sentinel. Exact section/key/value mappings are in `docs/GAM-PRINTER-CONFIGURATION-RECOVERY.md`.
- The printer setup path references `GAMPrinterSetup.exe`, `zvprt1`, `ZVPsrc\\save.ini`, and `zvprt50\\`; launching the installer and observing a printer appear are separate from proving the driver can emit a correct TIFF.
- No Linux printer implementation was added. Keep the Windows CSIDL/registry path logic separate from the Linux application-owned output directory.

## 2026-11-26 — connector base wrapper and SendLog target traced

- Run 32 (`45767912737`) native regression and Word connector lane passed. The Word artifact confirms the base wrapper `TEmwatMethod.Finalization` at `0x0046C9E0`: it calls `TEmwatMethod.Invoke` (`0x0046C82C`) to serialize dictionary pairs into XML parameter nodes, then calls the concrete handler via VMT slot `+0x10`. The `+0x54` interface call inside `Invoke` is the XML getter, not the handler dispatch.
- Runtime `TShowSendLog` target `0x005EFF4C` is now body-traced: it obtains global service object `0x0062B4F0` through `0x00404D5C`, calls service vtable slot `+0x13C`, gets the result through interface slot `+0x54`, and inserts it into the result dictionary. Its output key/value serialization remains unresolved.
- Run 32 completed successfully in all three jobs, including the Image/VMT lane and native CMake/CTest/Python regression.

## 2026-11-26 — runtime connector mappings and request keys reconciled

- The service-side VMT map in `docs/EMWAT-SERVICE-EXECUTABLE-ANALYSIS.md` is authoritative for runtime class names. TD32 `PerformMethod` labels are shifted for multiple methods; the connector inventory now separates runtime class, `VMT+0x10` target, and TD32 label.
- Confirmed request keys and embedded log/error literals:
  - Runtime `TScanDocument` (`0x005EEB48`, TD32 label `TFaxDocument`): key `document`; opens it as a stream via `0x004041BC`, creates `TScanCommand` (`0x004F21DC`), calls `GetNextPage` (`0x004F2558`), extracts the result through interface slot `+0x54`, and inserts it into the result dictionary. The output key/serializer remains unknown.
  - Runtime `TFaxDocument` (`0x005EEDFC`, TD32 label `TGetEmwatVersion`): key `fax`.
  - Runtime `TImageEdition` (`0x005EF300`, TD32 label `TEditExcelWorkBook`): keys `data` and `config`, log `[Invoke EditImages]`, null-input errors.
  - Runtime `TUpgradeEmwat` (`0x005EF24C`, TD32 label `TImageEdition`): key `PlugIn`; finalization helper logs `UpgradeEmwat method called`, references `EmwatMethods.bpl`, `.zip`, and `EmwatUpdate.exe`.
  - Runtime `TEditExcelWorkBook` (`0x005EF8AC`, TD32 label `TCompareWordDocument`): keys `ExcelConfig` and `ExcelWorkBookContent`, log `[Invoke EditExcelWorkBook]`.
  - Runtime `TCompareWordDocument` (`0x005EFC54`, TD32 label `TShowEmwatSetting`): key `documentsData`; calls `TCompareCommand.DoRequest` and its finalization.
- Version targets: runtime `TGetEmwatVersion` at `0x005EF110` calls helper `UpgradeEmwatPlugin` (`0x00502F70`, mode 0) and `SetEmwatVersion` (`0x0050291C`); runtime `TSetEmwatVersion` at `0x005EF218` calls `UpgradeEmwatPlugin` with mode 1. Do not infer the business meaning from helper names alone.
- Result-path literals decoded: `%.3d` at `0x004ED144`, `_P` at `0x004ED290)/`0x004ED584`, and `_P000` at `0x004ED338`. This proves page/serial suffix formatting but not the exact one-to-one mapping of `TSetOfMultiPageImages` to a single physical file. Updated the imaging/native parity docs to keep that mapping open.
- Run 32 workflow update adds explicit traces for the shared wrapper `0x0046C9E0` and runtime `TShowSendLog` target `0x005EFF4C`; workflow commit `99896e936724750335348787075194c7b95a49dc`.

## 2026-11-26 — full connector handler inventory completed

- Run 30 (`45765541247`) completed successfully across all three jobs. The Word artifact `15092201094` dynamically traced 12 symbols: central `TEmwatMethod.Invoke` (`0x0046C82C`), `TWordViwer.LoadDocument`, and 10 concrete connector `PerformMethod` procedures. The image artifact `15091712828` includes the corrected `TResultImage`/single-page/multipage result methods. Native regression passed.
- The service calls the base wrapper at `0x0046C9E0` (VMT slot `+0x0C`); it invokes `TEmwatMethod.Invoke` at `0x0046C82C` to serialize dictionary pairs into XML parameter nodes, then calls the concrete handler through VMT slot `+0x10`. Interface slot `+0x54` inside the inner helper is the `TXMLEmwatType.GetXML` serializer getter, not the handler dispatch.
- Discovered connector handler inventory:
  - Word edit (runtime `TEditWordDocument`, TD32 label `TScanDocument`, VA `0x005EE82C`) — four known keys; calls `TWordViwer.LoadDocument`.
  - Scanner (runtime `TScanDocument`, TD32 label `TFaxDocument`, VA `0x005EEB48`) — `document` key; calls `TScanCommand.GetNextPage`.
  - Fax — reads one value, opens a file stream, uses `TScanCommand.GetNextPage`.
  - Get/Set version and Upgrade — separate version/service helper paths.
  - ImageEdition — key `PlugIn`, calls `Applicationactivities.Finalization`.
  - EditExcelWorkBook — two dictionary values and file-stream processing.
  - CompareWordDocument — two dictionary values and helper `0x005E72B8`.
  - ShowEmwatSetting — one dictionary key and settings helpers.
  - ShowLastEditedDocs and ShowSendLog — service-object calls through vtable slot `+0x13C`, then response getters.
- Created `docs/CONNECTOR-HANDLER-ENTRYPOINT-INVENTORY.md` with procedure addresses, body observations, confidence boundaries, and implementation status. These are discovered Windows entry points; Linux currently registers only EditWordDocument by default. No handler stubs or guessed request keys were added.
- Run 31 (`45766298102`) is running with remaining handler-key/response-string decoding, ImageEdition/result-path string decoding, and shared version/settings/compare/dispatch helper traces.

## 2026-11-26 — run 29 scanner constraints and result-image details

- Run 29 (`45764787287`) passed all three jobs, including native regression.
- The embedded `TScanCommand.VerifyConstraints` constants map to command flags by traversal position: first value `none/jpg` → `+0x1B/+0x1D`; second `none/yes` → `+0x1C/+0x1E`; third nonempty value → `+0x29`; fourth `yes` → `+0x18`; fifth and sixth values not equal to `no` → `+0x19/+0x1A`. Exact XML tag names are still not visible at this callsite. A Persian retry prompt is shown when image constraints are not satisfied; it is UI text, not an HTTP response.
- Corrected result-image method identities: `TResultImage.Create` `0x004EC8B4`; `ShiftSerial` `0x004ECFC8`; `GetScanFilePath` `0x004ED03C`; `NextFile` `0x004ECF50`; `TSetOfSinglePageImages.Create` `0x004ED168`; `TSetOfMultiPageImages.Create` `0x004ED298`. `ShiftSerial` checks whether the resolved scan path exists. Native `ScanOutput` has the same top-level two-variant distinction; actual filename/serial policy remains unimplemented pending further traces.
- `TImageEdition.PerformMethod` key `PlugIn` is confirmed, but helper `0x0050357C` and the operation/response contract are still being traced.
- Run 30 (`45765541247`) is running with corrected result-image method addresses and a dynamic connector-symbol pass for all connector `PerformMethod` entries, the service dispatcher, `TEmwatMethod.Invoke`, and `TWordViwer.LoadDocument`.

## 2026-11-26 — scanner result-image hierarchy confirmed; connector trace expansion running

- Run 29 (`45764787287`) completed successfully in all three jobs; native regression passed. Its Image artifact `15091627434` and Word artifact `15090789687` were inspected.
- Embedded strings independently confirm the Word handler keys `wordConfig`, `wordBody`, `letterImages`, `signData`; the `TImageEdition.PerformMethod` key is `PlugIn`. Scanner literals include `none`, `jpg`, `yes`, `no`, log strings `SCAN: NewDocument.` / `SCAN: NextPage Requested.`, and error prefix `<ScanDoc HasError>. ErrorXML: `. The Farsi retry prompt is embedded as well; exact XML field mapping remains open.
- Result-image symbol resolution corrected two earlier helper assumptions:
  - `0x004EC8B4` is `TResultImage.Create(UnicodeString, TImageFormat)`, called by `TScanCommand.GetNextPage`.
  - `0x004ECFC8` is `TResultImage.ShiftSerial`, called by `TScanCommand.HasError`; it uses `GetScanFilePath` (`0x004ED03C`) and checks file existence. It is not a `HasError` method.
  - `TResultImage.NextFile` is `0x004ECF50`; `TSetOfSinglePageImages` and `TSetOfMultiPageImages` constructors are `0x004ED168` and `0x004ED298`. This confirms the native `ScanOutput` single-page-set/multipage distinction at the model level. See `docs/NATIVE-IMAGE-PARITY-GAP-2026-11-25.md`.
- Runtime VMT reconciliation: `0x005EE82C` is `TEditWordDocument.PerformMethod` (TD32 label `TScanDocument.PerformMethod`); it extracts the four Word keys and calls `TWordViwer.LoadDocument`. Separately, runtime `TScanDocument` is at `0x005EEB48` (TD32 label `TFaxDocument.PerformMethod`); its `document` key, `[Invoke ScanDocument]` log prefix, and `TScanCommand.GetNextPage` call confirm the public scanner connector. The stale TD32 label at `0x005EE82C` must not be mistaken for the scanner endpoint. Updated the connector and imaging inventories.
- Updated the Image trace target list to use the exact current TD32 addresses for all `TResultImage`, `TSetOfSinglePageImages`, and `TSetOfMultiPageImages` methods. Added a dynamic Word-lane pass that indexes and traces all concrete connector `PerformMethod` procedures plus `TEmwatMethod.Invoke`, `EmwatServiceCommandGet`, and `TWordViwer.LoadDocument`. Workflow commit `ac88ea14d0bfcaeabef736fde7f087065338159f`; run 30 (`45765541247`) is in progress.
- The branch-scoped concurrency group is active; stale runs 21 and 22 are now both cancelled. Do not count them as regression passes.

## 2026-11-26 — connector key decoding and stale-run control queued

- Run 29 (`45764787287`, workflow commit `fed7d6e`) is running with the next scanner connector pass: decode dictionary/XML string constants, trace dictionary conversion helpers, and include `TResultImage` / `TSetOfMultiPageImages` procedures and callers.
- Added a branch-scoped workflow concurrency group with `cancel-in-progress: true`. Future pushes to the same branch will replace older parallel-analysis runs rather than leave overlapping runs consuming Actions minutes. This does not retroactively add concurrency metadata to older runs; run 21 and run 22 are now both cancelled (run 22 cancellation recorded at 05:56:29Z).
- The new connector analysis step does not add Linux handlers. Its purpose is to recover exact dictionary keys, XML constraints, result-file methods and response schema before implementation.

## 2026-11-26 — ScanDocument body trace and GAM installer/profile APIs resolved

- Run 27 (`45764043847`) completed successfully across Word, Image and Native jobs. Artifacts: `15090968111` (Word) and `15090469945` (Image). Run 28 (`45764222813`) also completed successfully across all three jobs; artifacts: `15091790290` (Word) and `15091725676` (Image). Native regression passed in both.
- Run-28 helper identities:
  - `0x0040275C` = `kernel32!GetPrivateProfileStringW`.
  - `0x00404494` = `shell32!ShellExecuteW`.
- `GetZanInstallDir` now has an exact installer call contract: relative `GAMPrinterSetup.exe`, checked with `FileExists`; `ShellExecuteW(hwnd=0, lpOperation=Open|RunAs, lpFile=GAMPrinterSetup.exe, lpParameters=NULL, lpDirectory=NULL, nShowCmd=0)`. `GetVersionExW` selects `Open` on Windows major <=5 and `RunAs` on major >5.
- After the GAM queue appears, the same routine reads `[save]/basefilename` from both relative `ZVPsrc\\save.ini` and the resolved configuration-directory `save.ini` using `GetPrivateProfileStringW` (default NULL, 0x104-character buffers), comparing them in a 100 ms retry loop until they match. This is a config synchronization handshake, separate from the 300-iteration printer queue discovery loop.
- Run-27 Image artifact confirms body traces for `TScanDocument.PerformMethod`, `TImageEdition.PerformMethod`, and `TScanCommand` methods. Both connector methods receive generic dictionaries with `AnsiString` keys. `TScanDocument` looks up four keys and delegates through `0x004B7724`; `TImageEdition` looks up one key and delegates through `0x0050357C`. The exact key names are not decoded yet.
- `TScanCommand.DoRequest` parses request XML, examines result-image state, validates constraints, and updates state flags; runtime `TScanDocument` reaches `GetNextPage`, which constructs `TResultImage` at `0x004EC8B4`; `HasError` calls `TResultImage.ShiftSerial` at `0x004ECFC8`. Public scanner connector mapping is now confirmed by the service VMT map. The exact procedure observations are in `docs/IMAGE-SCANNER-EDITOR-CALLGRAPH-INVENTORY.md`.
- Corrected the report to leave `0x004EC8B4` and `0x004ECFC8` unnamed pending symbol resolution; do not assume they are `TResultImage.NextFile/HasError`.
- The next high-value pass is decoding dictionary/XML constants at `0x005EE9F4`, `0x005EEA88`, `0x005EEAA0`, `0x005EEABC`, `0x005EEAD4`, `0x005EF2F8`, and `0x004F31F8`/nearby addresses; trace helpers `0x0046DC8C`, `0x004735D0`, `0x004B7724`, `0x0050357C`, and map `TResultImage` methods.
- Runs 21 and 22 remain stale/in-progress from the broken nonce fixtures. Runs 23–28 are completed successfully on corrected code. Add workflow concurrency cancellation after the current analysis batch so future pushes do not leave old runs consuming Actions minutes.

## 2026-11-26 — ImageEn path and protocol connector entry points found

- Run 26 (`45763574936`) completed successfully across Word, Image and native regression jobs. Its Image artifact `15090488790` was inspected.
- The ImageEn import scan proves a second image I/O stack, separate from the ImageGear scanner-preview API:
  - `TImageEnMIO.Acquire` thunk `0x004B012C`, callsite `0x0050A364` in `TfrmImageTools.InsertPicture`.
  - `TImageEnMIO.PrintImage` thunk `0x004B0154`, four callsites in `TfrmImageTools.DoPrintingPanel`.
  - `LoadFromFileAuto`, `GetParams`, `ExecuteSaveDialog`, `ExecuteOpenDialog`, `SaveToFile`, and `SaveToFileTIFF` are also identified with exact IAT thunks/callsites. Documented in `docs/IMAGE-SCANNER-EDITOR-CALLGRAPH-INVENTORY.md`.
- The symbol index reveals TD32 procedure labels `TScanDocument.PerformMethod` (`0x005EE82C`) and `TImageEdition.PerformMethod` (`0x005EF24C`), but the runtime VMT map resolves these addresses to `TEditWordDocument` and `TUpgradeEmwat`, respectively. Runtime `TScanDocument` is `0x005EEB48`; runtime `TImageEdition` is `0x005EF300`. `TScanCommand` lifecycle methods are separately traced.
- Added all eight procedures to the parallel image trace target list. Workflow commit `7d31f79aecb7c31699cd51d85abfb28397825d0d`; next run should produce the bodies and direct caller traces. These are connector symbols only until the request dictionaries/XML fields and response contract are decoded.
- No `ScanDocument` or `ImageEdition` Linux handler was added; exact method names, parameter keys, page state, errors and output serialization remain unknown.

## 2026-11-26 — ImageGear transform and dimensions callsites recovered

- Run 25 (`45763380148`) image job completed successfully; artifact `15090612978` was inspected. The run's Word helper pass was still active at last poll; native regression passed.
- Exact imports:
  - `0x004AFEC8` → `IG_IP_rotate_multiple_90`
  - `0x004AFED0` → `IG_IP_flip`
  - `0x004AFF00` → `IG_image_dimensions_get`
  - `0x004AFEF0` → `IG_device_rect_set`
- Direct caller inventory:
  - `IG_IP_rotate_multiple_90`: `TGearImgProc.RotateLeft` (`0x004EF187`), preview handlers `0x0061E5FC` and `0x0061E62C).
  - `IG_IP_flip`: `TGearImgProc.FlipHorizontal` (`0x004F021F)), preview methods `0x0061E5CC` and `0x0061E65C).
  - `IG_image_dimensions_get`: `TGearImgProc.ReloadPage` (`0x004EF107`), `TfrmGScanPreview.GearErrorHandling` (`0x0061D09C)), and `LoadImageToGearHandle` (`0x0061D39B`).
  - `IG_device_rect_set`: direct calls at `0x004EEF0F` and `0x0061D853`.
- The names are misleading relative to the imported operations: `btnLRotateClick` calls `IG_IP_flip`; `btnVFlipClick` calls `IG_IP_rotate_multiple_90`. Do not infer user-visible behavior from event-handler names. `LoadImageToGearHandle` passes image handle `this+0x428` and output addresses `+0x42C/+0x430/+0x434` to `IG_image_dimensions_get`; individual output meanings/units remain unknown.
- Updated `docs/IMAGE-SCANNER-EDITOR-CALLGRAPH-INVENTORY.md` and `docs/NATIVE-IMAGE-PARITY-GAP-2026-11-25.md`. Native transform code was not changed; current quarter-turn and flip algorithms exist, but exact vendor argument semantics and metadata parity remain open.
- Run 26 (`45763574936`) adds ImageEn acquisition/TIFF callsite inventory and is still in progress; its results are not yet inspected.

## 2026-11-26 — GAM printer Win32/INI helper APIs resolved

- Run 24 (`45763269503`, workflow commit `07fa8be`) completed successfully in all three jobs. Its Word artifact `15091306103` was downloaded and inspected; image artifact `15091500582` is available. Native regression also passed in this run.
- Helper thunks now resolve exactly:
  - `0x00402674` = `RegOpenKeyExW`; `0x0040267C` = `RegQueryValueExW`; `0x0040266C` = `RegCloseKey`.
  - `0x00402754` = `GetPrivateProfileIntW`; `0x00402910` = `WritePrivateProfileStringW`.
  - `0x004044AC` = `SHGetFolderPathW`; `0x00402818` = `GetVersionExW`.
  - `0x004032C0` = Delphi `FileExists`; `0x004032C8` = `DirectoryExists`; `0x00403320` = `ExtractFileName`; `0x00403350` = `StrComp`.
  - `0x00404F4C` = VCL `Printer()`; `0x00404F54` = VCL `TPrinter.Refresh`; `0x00403438` = `Sleep`.
- Corrected the INI argument mapping using the actual Win32 function prototypes and push order:
  - `configure.ini`: `GetPrivateProfileIntW(section="allusersfolder", key="policy", default=1)`. The earlier report reversed section and key; that is withdrawn.
  - `CheckPrinterPaused` uses `WritePrivateProfileStringW`, so it writes, rather than merely reads, the observed values:
    - `save.ini`, section `save`: `folder` (runtime path), `basefilename` (runtime base name), `popupdialog=No Dialogs`, `filexistact=1`.
    - `image.ini`, section `image`: `fileformat=tiff`, `imagecolor=256`, `compression=lzw`, `pagetype=0`, `rowsperstrip=Each page as a single strip`.
    - `general.ini`, section `general`: `hidestsdialog=1`, `sentinel=1`, `sentinelfile=JobFinishes.GAM`.
- `SetPrinterForTiffout` uses `GetVersionExW`, `GetPrivateProfileIntW`, and `SHGetFolderPathW`; the selected CSIDL is raw `0x23` or `0x2e`, depending on the policy and OS major version. The final runtime path under each Windows/account policy remains unverified.
- Updated `docs/WORD-ACTIVE-PRINTER-AND-SCANNER-STATE-RECOVERY.md` with exact API identities, INI sections/keys/values, and the corrected config.ini mapping. No Linux defaults were hardcoded.
- Runs 25 and 26 are active with additional ImageGear rotate/flip and ImageEn acquisition/TIFF callsite scans. Do not report their findings until the corresponding artifacts are inspected.

## 2026-11-26 — bridge fixture repair CI verification

- Run 23 (`45763089199`, commit `9cf55fbcc2b3befc899ae8d46505ca13e8586173`) completed successfully across all three parallel jobs.
- Native regression: CTest 5/5 passed.
- Python bridge regression: 317 passed, 9 skipped, 339 subtests passed in 10.78 seconds.
- Word print and Image UI/VMT static-analysis jobs both passed. Artifacts: `15090746518` (Word), `15090318746` (Image).
- This confirms that the nonce fixture correction removed the pytest process hang; it is a test-data repair only, with no production bridge change.
- Runs 21 and 22 still show stale in-progress status from the broken test fixtures and are not evidence of passing. Run 24 includes the new printer helper trace; run 25 adds ImageGear rotate/flip traces; run 26 adds ImageEn acquisition/TIFF callsite inventory. Those are separate runs and still require inspection.

## 2026-11-26 — Winspool ANSI API confirmed; bridge regression hang root cause fixed

- Downloaded and inspected run-22 Word artifact `15090546185`. The `0x004044CC` thunk is exactly `winspool.drv!EnumPrintersA` through IAT `0x0062F9F0`; it is not `EnumPrintersW`. `GetPrinterName` calls it twice with Flags=8, Name=NULL, Level=2: first a null-buffer size query, then a second call with allocated buffer. It iterates `0x54)-byte `PRINTER_INFO_2A` records, compares `pDriverName` at +0x10 with `zvprt1`, and copies `pPrinterName` at +0x04 to global `0x0062B310`. Driver matching and queue-name extraction are now confirmed at the static callsite/API level.
- `GetZanConfigurationDir` (`0x0047D054`) opens `HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\zvprt50` using root `HKEY_LOCAL_MACHINE` and access mask `0x20019`, then queries `UninstallString`; it has a fallback that appends `zvprt50\\`. `GetZanInstallDir` (`0x0047CC94`) polls printer discovery up to 300 times at 100 ms intervals, and its installer branch uses `GAMPrinterSetup.exe` plus decoded `Open`/`RunAs` literals. The exact ShellExecute/registry/INI helper APIs and normalization behavior remain under trace.
- `SetPrinterForTiffout` (`0x0047D238`) reads `configure.ini` / `policy` / `allusersfolder` and references `save.ini` / `basefilename` / `save`. `CheckPrinterPaused` reads the previously inventoried `save.ini`, `image.ini`, and `general.ini` keys. Updated `docs/WORD-ACTIVE-PRINTER-AND-SCANNER-STATE-RECOVERY.md` with the confirmed ANSI API, x86 record layout, registry path, and exact limitations.
- Added a new parallel workflow pass for helpers called by the printer registry/INI routines (`0x00402674`, `0x0040267C`, `0x0040266C`, `0x00402754`, `0x004044AC`, `0x004032C0`, `0x004032C8`, `0x00402818`, `0x00403438`, `0x00404F4C`, `0x00404F54`, `0x00402910`, `0x00403320`, `0x00403350`, `0x00401368`, `0x00401370`, `0x00401378`). Workflow commit: `07fa8beec752cb941563cc573ffc3b3c6e73bfce`.
- Re-audited the bridge test fixtures after runs 21/22 appeared stuck. The request used by `test_server_close_waits_for_active_document_request` had `invoke=active`, so the server correctly rejected it before calling the blocking handler; the test then failed before shutting down its non-daemon serving thread, keeping pytest alive. Separately, the negative nonce list still used valid numeric `54320`, which contradicted the decimal-only rule. Corrected the active request to decimal `54320` and the negative case to nonnumeric `active`; production code was not changed. Commit: `9cf55fbcc2b3befc899ae8d46505ca13e8586173`.
- Run 23 (`45763089199`, commit `9cf55fb`) completed successfully in all three jobs after the fixture correction: native CTest 5/5 passed; Python bridge suite 317 passed, 9 skipped, 339 subtests passed in 10.78 s; Word and Image static-analysis jobs passed. Its artifact IDs are `15090746518` (Word) and `15090318746` (Image). This verifies the corrected test fixture and removes the apparent pytest hang for the new run. Runs 21/22 were launched with the broken fixtures and remain marked in progress; they are stale and must not be counted as passing.
- This batch is remote-only. No local checkout, Wine prefix, physical printer, scanner, or EMWAT installation was touched.

## 2026-11-26 — scanner API caller map completed

- The run-20 image artifact `15088974707` now supplies exact direct callsites for the scanner-related imports. `IG_scan_pages` (`0x004AFF30`) has three calls: `TGearImgProc.SelectScanner` at `0x004EFA96`, and `TfrmGScanPreview.SelectScanner` at `0x0061E036` and `0x0061E059`. `IG_scan_source_select` (`0x004AFF28`) has two calls: `TGearImgProc.SetCurrentPage` at `0x004EFF83` and `TfrmGScanPreview.ShowCropRectangle` at `0x0061E3DF`. The latter two uses are semantically surprising; do not assume the API name alone explains them.
- The same scan shows `IG_error_check/get/clear` used not only by `TfrmGScanPreview.GetImagePageNumber`, but also by `TGearImgProc.CheckOutputParameter`; `TGearImgProc.GetForceSinglePage` also calls `IG_error_get`. The active-printer/scanner report now records these direct callsites and leaves the vendor API prototypes open.
- Updated `docs/WORD-ACTIVE-PRINTER-AND-SCANNER-STATE-RECOVERY.md` accordingly. This is static callsite evidence; it does not prove scanner-source selection or crop semantics.
- Corrected run `45761732772`: the Word and image jobs have passed; its native job passed CMake/CTest and is currently running the Python bridge suite after the test-fixture fixes. Run `45762129809` is running with the new Winspool `0x004044CC` trace and expanded string decode; inspect its artifact before identifying the ANSI/Unicode `EnumPrinters` variant.
- Latest docs-only commit at this checkpoint: `7002216cc63477bee5d709fb2febb41bebdca654`. No local repository was changed.

## 2026-11-26 — scanner output model correction, GAM printer evidence, and CI fixture repair

- A deeper argument-order audit corrected a material scanner finding. In both `TfrmGScanPreview.Scan` (`0x0061DC80`) and `TGearImgProc.SavePage` (`0x004EF510`), the seven arguments pushed before `CreateFileW` map in reverse order to the Win32 signature. The fifth parameter is the pushed value `4` (`OPEN_ALWAYS`), not the pushed value `1`; the latter is the share-mode argument. The previous `CREATE_NEW` / one-physical-file-per-page interpretation is withdrawn.
- The exact output suffix is now decoded at `0x0061DEE8` and `0x004EF708`: `_New.tif`. Each loop reopens that same path with `OPEN_ALWAYS` and calls `IG_save_FD` with page indices 1..N and reserved argument 0. The public ImageGear 18.7 API reference documents the five-argument `IG_save_FD` signature, one-based page numbers, and page insertion into multipage files. Combined with the observed call shape, this strongly supports one page-indexed `_New.tif` container, not a set of per-page files. The exact target format IDs `0x40028`/`0x80028`, the unusual raw `hTemplateFile=0x40000000`, and actual output bytes remain unresolved.
- Corrected `docs/SCANNER-PREVIEW-OUTPUT-RECOVERY.md` and `docs/IMAGEGEAR-SAVE-PIPELINE-RECOVERY.md` to withdraw the old output model and record the new call-argument mapping. The native `ScanResult` model remains generic and can represent either physical page files or a multipage file; no code adapter was added.
- The same run-20 word artifact decoded printer strings: exact driver-name literal `zvprt1`; `GAMPrinterSetup.exe`; `ZVPsrc\\save.ini`; `configure.ini`; `policy`; `allusersfolder`; `zvprt50\\`; and multiple `save.ini`, `image.ini`, and `general.ini` keys/values. `GetPrinterName` (`0x0047CAF0`) walks records of stride `0x54`, compares field `+0x10) with `zvprt1`, and copies field `+0x04). The layout matches `PRINTER_INFO_2` field offsets; the `0x004044CC` helper's exact mapping to `EnumPrintersA/W` is still pending. Added these bounded findings to `docs/WORD-ACTIVE-PRINTER-AND-SCANNER-STATE-RECOVERY.md` and added a dedicated Winspool helper/IAT trace step to the parallel workflow.
- CI run `45761544667` (run 20): `image-ui-and-vmt` and `word-print-com` passed; `native-regression` failed only in Python bridge fixtures. The CMake/CTest step passed. Failure root cause was stale test data: `9f44941` had made `54320` a valid decimal nonce in positive fixtures but also left it in the invalid-path list; `test_application.py` still used nonnumeric `local-nonce`; and raw fullwidth digits could not be sent by Python's HTTP client. Fixed tests only (no production behavior change): invalid nonce is `active`, fullwidth digits are percent-encoded, and application integration uses a decimal nonce.
- Added `python/**` to the parallel workflow's push paths so Python changes actually rerun the Python regression suite. Corrected test run `45761732772` is running; new workflow run `45762129809` is queued with the printer API trace step. Do not report the corrected Python suite as green until its job finishes.
- Relevant commits: `719e66af2a13522f6f9139df57113d70b27d1b76` (scanner preview output correction), `1ee1b56e1a1b4976bb4755b7b756979a1e318b80` (ImageGear SavePage correction), `54b988918f59bd4f7df5a00344cc793ec935ce7e` (GAM printer strings), `9d9d15a54bae7f4259dde757d4d4ccd03f4d55da` and `070730ac93672d4d9504f616098eab84199944c6` (nonce test fixtures), `398c5a8dae265bee23f85d7e1a382ef96f4649ab` (Python CI trigger), `04cc18163c3c92951304932c1c143390cd08a31d` (Winspool trace).
- No local repository, Wine prefix, physical printer, or scanner was touched. All changes are on `feature/recovery-retention-policy`.

## 2026-11-26 — bridge nonce fixture drift found and corrected

- Parallel workflow run `45761480118` (run 19) exposed a Python regression-suite failure: native CMake/CTest passed; Python reported `315 passed, 9 skipped` with four failures/subfailures in two tests.
- Root cause is stale test data, not a transport implementation regression: commit `9dee565` intentionally changed POST routing validation to require ASCII decimal digits, while commit `9f44941` accidentally changed the invalid test case from nonnumeric `active` to numeric `54320`. The same valid decimal nonce was already used by positive fixtures. `test_application.py` also still sent `local-nonce`, which contradicts the now-required decimal contract. The fullwidth-digit test placed raw Unicode in an HTTP request target, so Python's HTTP client failed before the server could validate it.
- Corrected tests only: restored `/?invoke=active` as the nonnumeric negative case; percent-encoded fullwidth digits so the server receives a valid ASCII URI and decodes the Unicode query value; changed the application integration fixture to a decimal nonce. No production bridge behavior was changed.
- Commits: `9d9d15a54bae7f4259dde757d4d4ccd03f4d55da` and `070730ac93672d4d9504f616098eab84199944c6`.
- The corrected tests are awaiting a fresh CI run; do not mark Python regression green until that run completes. The earlier run 19 failure must remain in history as a test-fixture failure and not be rewritten as a pass.

## 2026-11-26 — ImageGear scanner import identity correction and next trace lane

- Inspected the complete artifacts from parallel workflow run `45563007730`; all three jobs passed (`image-ui-and-vmt`, `word-print-com`, `native-regression`). The image artifact's import table resolves `0x004AFF30` to `IG_scan_pages`, `0x004AFF28` to `IG_scan_source_select`, `0x004AFED8` to `IG_error_check`, `0x004AFEE8` to `IG_error_get`, and `0x004AFEE0` to `IG_error_clear`.
- Corrected a material documentation error: `TfrmGScanPreview.GetImagePageNumber` at `0x0061D100` is a misleading TD32 symbol name; its body aggregates ImageGear errors using `IG_error_check/get/clear` and publishes a Variant-like status record. It is not the page-metadata enumerator. The actual page-count UI path is `GetImgSize` at `0x0061D250`, which calls `IG_page_count_get` at `0x004AFEA8`.
- Both `TfrmGScanPreview.SelectScanner` (`0x0061DEF4`) and `TGearImgProc.SelectScanner` (`0x004EF9CC`) call the `IG_scan_pages` thunk. The observed argument values and wrapper names do not establish the vendor API prototype or mode semantics. `IG_scan_source_select` is imported, but its callers remain unverified.
- Updated `docs/WORD-ACTIVE-PRINTER-AND-SCANNER-STATE-RECOVERY.md` with these exact import identities and the corrected error-aggregation interpretation. Extended `.github/workflows/emwat-parallel-reverse-engineering.yml` to scan IAT callsites and trace scanner import wrappers in a dedicated artifact directory.
- The new workflow-triggering commit must be checked for all three job results and the scanner API callsite artifact before accepting any further ABI conclusions. No scanner handler or ImageGear prototype has been implemented; those remain blocked on the recovered contract. No physical scanner, printer, Wine prefix, or user system was touched.

## 2026-11-25 — crop coordinate conversion helper resolved

- The image lane in run `45561529517` completed successfully, as did its Word and native-regression jobs. Its artifact was inspected.
- `0x00401058` resolves to `rtl230.bpl!@System@@ROUND` (Delphi `System.Round`), so crop preview-to-source coordinates are independently scaled on X and Y and rounded by the target RTL before being passed into the `TGearImgProc` constructor. It is not a truncating cast. Also identified `IntToStr` helper thunks, `TControl.SetVisible`, and `TWinControl.GetHandle` used by the editor path. See the updated crop-coordinate report.
- Word print Variant helper recovery remains as recorded in section 9 of the Word dispatch report. New follow-up traces now include the property/automation helper addresses `0x004ADA4C`, `0x0043EC28`, `0x0043EAB8`, `0x0043F308`, `0x00440B2C`, and `0x00403488`, plus a broader `TWordViwer` symbol index. The next run is `45561859598`.
## 2026-11-25 — scan-result rename and Debian package verification

- Native-core run `45561332281` completed successfully on commit `8cb43e5c276c84362a043f4bac376f8b491c6bdf`: `build-test`, `sanitizer-test`, and `deb-package-lifecycle` all passed. The package job now checks that `scan_result.hpp` is present after install and upgrade and absent after package removal.
- The scan-result API now uses `output_file_count()` rather than `page_file_count()`, explicitly counting physical output files only. This avoids claiming that one multipage container contains one image page.
## 2026-11-25 — Word Print Variant helper ABI recovered

- The Word lane in run `45561529517` completed successfully and produced an inspected artifact. `0x00403550` is not a generic Variant initializer: it resolves to `rtl230.bpl!@System@Variants@EmptyParam`. Fifteen of the eighteen pushed records are therefore explicit missing optional parameters.
- The remaining records are now typed at the helper level: `-0x58` is populated via `OleVarFromInt` from a document/application property at `+0x408`; `-0x78` is `OleVarFromInt` with 0 or 4; `-0x88` starts as `EmptyParam` and may be replaced with an `OleVarFromUStr` value depending on branches. `VarClr`, `VarToUStr`, and `CheckAutoResult` thunk identities were also resolved. Full semantic parameter mapping and the 18-vs-17 interface ABI discrepancy remain open. See section 9 of `docs/WORD-PRINT-DISPATCH-AND-WORKER-ANALYSIS.md`.
- The native-regression job in run `45561529517` passed. The image/scanner lane in that run was still running at this checkpoint; its artifact must be inspected before accepting new conclusions.
- The native-core run `45561490818` has passed build-test and ASan/UBSan; Debian package lifecycle was still running at this checkpoint. The earlier run on intermediate commit `c5e434c` failed because the header rename landed before the test rename in separate commits; the next commit `8cb43e5` passed the complete native-core workflow. Treat this as a transient intermediate-commit failure, not a final branch failure.
## 2026-11-25 — ImageGear save path and editor constructor correction

- Parallel run `45560979156` completed successfully across all three jobs (`word-print-com`, `image-ui-and-vmt`, `native-regression`). The new image artifact was inspected, not just generated.
- Correction to crop analysis: `0x004EEE24` is the `TGearImgProc` constructor, called by `pbImgViewerMouseDown` with the scaled four-coordinate record. It is not the crop/apply routine. The crop/apply-side path is `TfrmSimpleImageEditor.CropImage` at `0x004F11E8`, which dispatches through image interface slot `+0x88`. The editor's `btnRegisterClick` at `0x004F17B4` dispatches raw mode values 0, 1 and 4; value 1 calls `ToggleCropMode`, value 4 calls CropImage/Rotate90/ShowCropRectangle, and CropImage calls back with mode 0. Do not assign user-facing labels to those raw values without resource/runtime proof. See `docs/IMAGE-EDITOR-CROP-COORDINATE-RECOVERY.md`.
- Added `docs/IMAGEGEAR-SAVE-PIPELINE-RECOVERY.md`: `SaveToFile` checks image validity/page count, uses `IG_save_file` for one-page output, and delegates to `SavePage` for multi-page source handling. `SavePage` iterates page indices, loads non-current pages through `IG_load_FD`, creates per-page outputs through `CreateFileW`, writes through `IG_save_FD`, closes handles, and deletes temporary ImageGear handles. `SaveCPinMultiPageFile` is a distinct stream-oriented path. Exact ABI, output naming, and TIFF finalization remain unresolved.
- Improved `ScanResult`: renamed `page_file_count()` to `output_file_count()` because a multipage container is one physical output file but may contain many image pages. Added explicit API documentation; tests assert physical output file count only. Debian package lifecycle now checks installation/removal of `scan_result.hpp`.
- Added a new workflow pass to disassemble Delphi RTL helper bodies not covered by TD32 procedure ranges: Word Variant helpers (`0x00403550`, `0x004034E8`, `0x00403520`, etc.) and crop coordinate conversion helpers (`0x00401058`, `0x00403270`, etc.). Await and inspect its artifacts before assigning Variant types or exact rounding semantics.
## 2026-11-25 — parallel lane verification and new reverse-engineering corrections

- Parallel workflow run `45560465682` completed successfully: `word-print-com`, `image-ui-and-vmt`, and `native-regression` all passed. The image artifact includes the expanded scanner/editor traces and result-container symbol index.
- Native-core run `45560461337` completed successfully: all three jobs passed (`build-test`, ASan/UBSan `sanitizer-test`, and `deb-package-lifecycle`). The build ran 5/5 CTest tests, including `scan_result_contract`, and verified staged installation of `scan_result.hpp`.
- New static recovery: the Simple Image Editor crop path uses independent source/viewer X and Y scale ratios. MouseDown scales both X bounds and both Y bounds into source pixels before calling helper `0x004EEE24`; mouse move/up implement edge/interior selection and drag updates. See `docs/IMAGE-EDITOR-CROP-COORDINATE-RECOVERY.md`. Exact rounding helper, preview offset/letterboxing and editor transaction semantics remain open.
- Important correction: the 17-Variant `TWordDocument.PrintOut` wrapper at `0x004361B0` is independently confirmed, but the `BGPrintWithGamPrintOptions` callsite appears to prepare/push **18** Variant-record addresses before its `+0x3F0` dispatch. The prior claim that the caller matched the 17-argument wrapper is withdrawn. See section 8 of `docs/WORD-PRINT-DISPATCH-AND-WORKER-ANALYSIS.md`.
- A new parallel workflow run `45560979156` is executing the next targeted pass for Variant helper ABI and the crop helper/state-transition procedures. Do not record conclusions from those traces until the artifact is inspected.
## 2026-11-25 — native scan-result CI verification

- Native-core workflow run `45560461337` completed successfully on commit `fa64dc9491fa5cdde3fabf32bc7d7ee5980fe994`: `build-test`, `sanitizer-test` (ASan/UBSan), and `deb-package-lifecycle` all passed.
- The build job ran **5/5 CTest tests**, including the new `scan_result_contract` test, and verified installation of `scan_result.hpp`. The sanitizer job also passed its test step; the package lifecycle job completed install/upgrade/removal.
- This verifies the new output model's compilation, structural contract tests, sanitizer run, and packaging inclusion. It does not yet integrate `ScanResult` into a live scanner workflow or establish exact Windows response-path semantics.
## 2026-11-25 — native scan-result boundary

- Added `native/include/emwat/scan_result.hpp`: a typed `ScanResult` that explicitly distinguishes a collection of single-page files from one multipage file, while retaining optional scan-path and response-filename metadata. It validates structural invariants without probing the filesystem or inventing the Windows naming contract.
- Added native contract tests for both result variants, page-file counts, empty collections/paths, and empty metadata; registered them with CTest. The pixel/page model (`ImageDocument`) and scanner backend/session remain separate.
- Enabled the native-core CI workflow on the working feature branch and made the parallel workflow respond to native changes, so this implementation is checked by normal build, sanitizer, package lifecycle, and parallel regression jobs.
## 2026-11-25 — expanded parallel reverse-engineering coverage

- Expanded the image/scanner lane to trace the preview Register/Cancel handlers, crop mouse-coordinate lifecycle, page selector, form close checks, free rotation, auto-orient, rotate/flip, and print-preview operations alongside the existing scanner and multipage-save paths. Added a separate symbol index for TResultImage, TSetOfSinglePageImages, and TSetOfMultiPageImages plus scan-path/response-filename accessors.
- This is a static-analysis coverage expansion only. It does not claim recovered crop coordinate math, editor commit/cancel semantics, arbitrary-angle behavior, or TIFF finalization. The new workflow run triggered by this commit is the verification gate; record its run ID and job results after completion.
- Next independent lanes remain: recover the 17 TWordDocument.PrintOut Variant values from the caller's local records; correlate printer selection/queue job names with GAM output publication; and complete ImageGear LZW callback ABI from a hash-matched local DLL (the proprietary DLL is intentionally not checked into the repository).
## 2026 11 18 — scanner input validation test

- Added hardware-independent regression checks that `SaneScannerBackend.get_capabilities("")` and `scan_one("")` reject an empty device identifier before entering SANE.
- Native image core workflow `44244437647` completed successfully on `ed811a14f9d151a8a386c67b80b26b3d155f5c24`: build-test and ASan/UBSan sanitizer-test both passed, including their test steps.
- Included in draft PR #2; this does not claim validation against a physical scanner, ADF, or duplex device.

## 2026-11-18 — opt-in recovery retention implementation (PR #2)

- Added `recovery_retention.py` with explicit age and/or snapshot-count limits. It keeps the newest valid snapshots, removes expired/excess sessions only when explicitly invoked, and returns removed session IDs.
- Exposed the policy through `RecoverySnapshotService.apply_retention()`; there is no default policy, background timer, or implicit deletion. At least one positive limit is required and count limits cannot be zero.
- Added unit tests for policy validation, age pruning, newest-N retention, service integration, and no-op behavior. Invalid/unverifiable entries are not enumerated by the store and are not deleted by this policy.
- Python bridge CI passed on the final PR head `f1a8260589d6f5fbd8fda0a2e45bd29c7741ff4e`: runs `44244362768` and `44244353561` both completed successfully.
- Draft PR: https://github.com/meicamghe/EMWAT-Linux/pull/2. This is not merged to main. Retention is not encryption; encryption-at-rest, user-facing policy controls, and a real Recovery UI remain open.

## 2026-11-18 — CI verification and recovery trigger coverage

- Native image core run `44240525477` completed successfully on `ecf4fa8a8784b2403272ecd79186fd073e1a8e1b`: both `build-test` and `sanitizer-test` passed, including the ASan/UBSan test step.
- Updated `.github/workflows/libreoffice-integration.yml` so changes to `recovery_store.py` and `writer_inspector.py` trigger the real LibreOffice UNO integration job on both push and pull request. This closes a CI coverage gap for recovery-store changes.
- The UNO run for this workflow update, `44240952654`, completed successfully: LibreOffice Writer/Python UNO installation, runtime verification, and adapter unit plus real UNO roundtrip test step all passed.

## 2026-11-18 — additional parallel work

- Native scanner scope documented against actual SANE implementation: one 8-bit Gray/RGB frame, optional mode/source/DPI, bounded 1 GiB frame size, and explicit unverified gaps (ADF/duplex/multi-frame, interactive cancellation, physical scanner matrix).
- Removed duplicate `libsane-dev` entry from `.github/workflows/native-core.yml`; existing native build and ASan/UBSan jobs will validate the workflow change.
- Python bridge CI for the latest property-order assertion passed: run `44237865553`, 147 tests, 145 passed, 2 optional UNO skips.
- Recovery UI, at-rest encryption, executable retention, semantic field mapping, Cancel/Discard wire contract and Almas E2E remain open.

## 2026-11-18 — parallel implementation checkpoint

- Added toolkit-neutral `RecoveryPickerController`; it exposes safe metadata, delegates restore to the hardened store using a UI-selected destination, and requires explicit confirmation before destructive discard. It is not a graphical widget or HTTP endpoint.
- Added `audit_writer_property_alignment()` to report exact case-sensitive Word custom-property ↔ Writer custom-property name intersections and unmatched names, plus Writer DocInfo.Custom field references. It preserves Word property index order and makes no COM/UNO order-equivalence claim.
- Python bridge CI run `44237776415` passed on `448090b0c7625bac5cfb086fcdf10b0ef1f17a19`: 147 tests, 145 passed, 2 optional LibreOffice tests skipped.
- Still open: actual GTK/Qt picker, verified semantic/template mapping, Cancel/Discard wire response evidence, encrypted recovery/retention, native scanner hardware validation, and Almas end-to-end.

# EMWAT-Linux — Project Handoff

## Current continuation checkpoint — 2026-11-25

- Reference installation: `/home/m/.wine-emwat`, confirmed `wine-11.0`; the installed `IGLZW32S.DLL` SHA-256 is `5cbb9352d71b74836c99429a1eaf39f77db753bfae6d5307199aaffbdeeee6cd`. This pass used static disassembly only and did not launch EMWAT or modify the prefix.
- Read-only SSH inventory confirmed `EmwatAgent.exe`, `EmwatService.exe`, `EmwatMethods.bpl`, and `GAMPrinterSetup.exe` are installed under `/home/m/.wine-emwat/drive_c/ProgramData/Gamelectronics/Emwat Service/`; no Wine/EMWAT process was running during the check. A prefix search found no `WINWORD.EXE`, so do not assume the full Word automation workflow can currently run in this Wine prefix. Existing printer captures and support files are present in `/home/m/gam-printer-analysis`, `/home/m/emwat-printer-capture`, and `/home/m/emwat-dlls`. No binaries were copied into the repository.
- At the start of this continuation, `feature/recovery-retention-policy` was at `f55410b7abc8b02bd27b8ed9750defedfafdf34c`; the evidence and probe harness updates below are being committed on that branch. The full local Python suite with real LibreOffice integration enabled passed **326/326 tests**; the focused `word_fields` suite passed **17/17**. GitHub Actions had no run for the preceding head; no remote CI pass is claimed.
- Wine 11 runtime probe of the hash-matched `EmwatMethods.bpl` confirmed direct Base64 decoder results for valid groups, invalid alphabet/length, and permissive `QQ=A` padding. The probe used `DONT_RESOLVE_DLL_REFERENCES` and a disposable prefix, which was removed; hashes for the original `.wine-emwat` binaries were unchanged. The probe did not exercise wrapper `0x004738CC`, pre-conversion `0x00455108`, Word or Almas. See `docs/WORD-FIELD-VALUE-DECODING.md` and `tools/reverse_engineering/probe_emwat_base64_decoder.c`.
- Follow-up disassembly confirms `0x00455108` converts a NUL-terminated WideString to AnsiString using caller code page 0 (ACP in the Base64 path), flags `0x270`, a queried size `N`, then output capacity `N-1`; it ignores the second `WideCharToMultiByte` return. A separate disposable Wine 11 WinAPI probe confirmed that this short capacity returns 0 / error 122 while still writing the first converted byte for tested ASCII, ACP-representable, and unrepresentable characters. This does not dynamically invoke the BPL helper. The temporary prefix and harness were removed; the original installed BPL hash still matches the analysis snapshot. See `docs/WORD-FIELD-VALUE-DECODING.md`.
- Static and runtime traces confirm URL `+` maps to a space, and the inner Base64 decoder requires a multiple-of-four length and uses a 256-byte translation table. The full Base64 wrapper behavior under Wine, malformed percent escapes, exact Unicode/whitespace handling through the complete helper chain, and semantic Writer field mapping remain unresolved.
- Read-only SSH through `linux-ubuntu` confirmed Wine `11.0`; installed `EmwatMethods.bpl` SHA-256 `6ff7d262f46ab009e3eecf20fca40cd41ec8ad937adf7bbfe2f6eddd56aaea2d` matches the checked-in snapshot, and installed `IGLZW32S.DLL` matches its documented hash. The original prefix was not modified.
- New static ABI facts and evidence are in `docs/IMAGEGEAR-LZW-GIF-REVERSE-ENGINEERING.md`: `GearExtInfoGet/Set` each clean two x86 stack slots; `GearExtInfoGet` selector 14 returns `TIF_Proc_LZW_Comp` when mode state is 1; the TIFF routine cleans `0x4c` bytes (19 x86 stack slots) and uses host allocation/free/error/finalization callbacks.
- **Next priority:** continue the product-critical P0-A/P0-B work in `REVERSE-ENGINEERING-MASTER-PLAN.md`: obtain a sanitized matching Almas/Word fixture so semantic mapping and close-response behavior can be verified, then exercise the full Base64 helper path with harmless controlled inputs. The GitHub text reports and installer archive are not that fixture. Preserve the existing loopback → real UNO integration regression while doing so.
- ImageGear TIFF/GIF ABI completion remains useful independent work, but it is lower priority than the Almas/Writer letter path. Do not invoke unverified DLL entry points; runtime probes must use a disposable isolated Wine prefix (or a protected copy of the valuable prefix) and harmless synthetic fixtures. Wine 9 must not be introduced.
- For printing, trace GAM's TIFF artifact path and queue/job correlation before adding a CUPS/IPP backend. Keep the Windows spooler and GAM virtual printer as separate analysis components.
- Keep these boundaries explicit: no typed TIF wrapper, ImageGear runtime parity, full scanner/ADF/duplex, CUPS printing, or verified end-to-end GAM workflow is claimed. Wine 9 must not be introduced.
- Printer checkpoint: SSH inspection confirms host CUPS is active but has no configured destinations/default queue. The existing Wine trace records `libcups.so.2` loading, zero enumerated printers, and `OpenPrinter2W(L"GAMPrinter", ...)` failing with error 1801. A separate x64 installer trace reports missing Wine x64 spool-driver support files; this does not establish x86 setup behavior. No printer configuration was changed, and the complete findings are in [GAM-VIRTUAL-PRINTER-REVERSE-ENGINEERING.md](GAM-VIRTUAL-PRINTER-REVERSE-ENGINEERING.md).

## Latest main-branch implementation — 2026-11-17

- POST bridge requests now require exactly one non-empty `invoke` query parameter before the request body is read or a method is dispatched. Duplicate/missing/invalid query shapes return HTTP 400.
- The hardened `RecoverySnapshotStore` has been ported to main. It validates manifest metadata, SHA-256, DOC/CFB vs DOCX container extension, symlink boundaries and the 128 MiB default limit. Restore uses a private temporary file, fsync and no-overwrite atomic publication.
- `LibreOfficeAdapter` starts a per-document periodic recovery worker (default 10 seconds), serializes snapshotting with document operations, retries transient failures, stops the worker on confirmed close, and removes the recovery session only after successful final export. A failed session preserves its last valid snapshot.
- Python bridge CI on commit `a92822d1aa83edba4e811ebebe1edd111e7dfab2` passed **131 tests, 2 skipped** (run `44081916126`). The corresponding LibreOffice UNO workflow also passed **13 tests** (run `44081916143`).
- Recovery UI/picker and retention policy are not yet implemented. The local store is not encrypted and is not compatible with the Windows password-protected `.easz` archive. Do not claim Almas end-to-end or full 180-field mapping.


Last reviewed: 2026-11-16

This is the concise continuity entry point for future sessions. Detailed reverse-engineering evidence remains in the linked analysis documents.

## Latest verified implementation progress — 2026-11-16

- **Saved-slot correction:** generated Word wrappers map Get_Saved to _Document +0xD4 and Set_Saved to +0xD8. WordAppDocumentBeforeSave uses +0xD8, so do not describe that instruction as reading Saved; its assigned OleVariant value and prompt condition remain unresolved. OnControlerNotify uses +0xDC, mapped to TWordDocument.Get_Content (0x0042BDF8); the supplied -1 argument remains unexplained. The same handler logs AutoSave execution, builds .easd/.easz paths and calls euUnArchive, confirming a local archive/recovery path distinct from Almas registration.

- Real LibreOffice UNO adapter added: per-document process/profile/socket isolation; DOC/CFB and DOCX input detection; document modification/save/close listeners; close-time Word 97 snapshot.
- writer_properties.py adds a strict custom-property update operation: it requires an exact existing property name, does not create unknown properties, and never reads the current value. The real UNO fixture now imports an actual Word DOCPROPERTY field and matching custom property, updates the property, refreshes Writer fields, verifies the displayed document text changes, and then closes/exports.
- Real UNO integration workflow run 43810592239 passed 8/8 tests, including a generated DOCX opened and closed through LibreOffice, a bookmark inspected through UNO, and export as a legacy Word CFB file.
- Latest Python bridge run 43815578467 passed 98 tests with one optional UNO skip (99 total); LibreOffice UNO runs 43815561042 and 43815592590 both passed 8/8, including adapter-level custom-property batch update, DOCPROPERTY refresh, and DOC/CFB export. The separate LibreOffice UNO run 43813378877 passed 8/8 tests, including the existing-property update path and DOCX → Writer → DOC/CFB close/export.
- application.py now has create_libreoffice_bridge_server to compose EditWordDocument → service → office adapter. Cancellation response remains an injected policy because the Windows cancellation envelope is not yet known.
- word_fields.py decodes each field according to its own encryption attribute, exposes parsed single/twin identifiers, and includes extract_docproperty_identifier() matching native DOCPROPERTY token parsing (case-sensitive, first double-space, 255-character bound). The observed dagger delimiter is U+2020; this is identifier parsing only, not a template-field mapping. writer_inspector.py and LibreOfficeAdapter.inspect_document inventory Writer bookmarks, named ranges, sections, tables, frames, graphic objects, indexes, and text-field metadata without reading letter content. URL-encoded text and Base64 image values are decoded independently; plain text remains unchanged. External signData bindings remain opaque until separator/concater semantics are confirmed.
- The latest custom-property pipeline (run 43813303321, artifact 14201306994) confirms dictionary helper use in the FillImageField/FillPrintDocFields paths; ShowRecAndCcOptionForm is called from GetDocFieldName, and FindWindowExtd is reached from FillImageField. Its next revision is queued with additional traces for shared field lookup and XML-config population. Their full business semantics and the 180-field mapping remain unresolved.
- Not yet complete: mapping the 180 EMWAT fields into the real Writer template; signer/image insertion; applying permissions/settings; close-cancel behavior; and end-to-end registration with Almas Gam.
- Native SetFieldValue constants are confirmed: urlencoded and base64. FindFieldInActivefields recognizes DOCPROPERTY field codes; Hidden_Customizable conditionally enters SilentSaveEmwatDoc during GetDocFieldName. AddCustomDocPropertiesToDic enumerates Word CustomDocumentProperties and parses twin names. Native URL-decoder behavior is now matched: + becomes space and %2B becomes literal +. Next: trace the Base64 byte-to-Unicode helper at 0x004738CC, resolve the indirect/VMT call into AddXmlWordConfigFieldsToDic, and continue correlating DOCPROPERTY fields with Writer DocInfo.Custom fields. In parallel, continue the close/response chain and validate mappings against an anonymized real DOC/CFB fixture. Do not claim template compatibility until this passes.

## Product goal — fixed

Rebuild EMWAT as a **native Linux application** while preserving the real Windows product's workflows. Running the Windows EMWAT build under Wine is not the target product.

The confirmed real-world workflow is a local desktop bridge for the Almas Gam web-based office automation system: data and letter templates are prepared in the web system, EMWAT opens Word for editing, and the resulting document is returned to the same system. Some letters are image-only, so scanning and image-document workflows remain in scope.

## Confirmed user observations and constraints

- **User-observed product requirement:** the user tested that closing the document applies/registers changes whether or not Save was pressed. Reproduce this behavior in Linux. The exact internal event, file extraction method and transport remain to be identified.
- The user has supplied the original Windows installer/extracted files for analysis. The historical extraction location was `D:\EmwatInstaller`.
- The user stated that the extracted EMWAT files contain no customer information. Still inspect any future traces, sample letters, cookies, tokens, and logs before publishing them.
- The original Windows binaries examined are PE32/x86; this is a fact about the analyzed binaries, not a reason to make the Linux implementation 32-bit-only.
- Do not assume the database engine, browser engine, complete API, authentication mechanism, or wire format until evidence confirms them.

## Confirmed static-analysis findings

- `EmwatService.exe` hosts a local HTTP service based on Indy components.
- A default local port of `1984` appears in strings; the Agent has a heartbeat string to `http://127.0.0.1:1984/?heartbeat`.
- A JavaScript bridge uses `postMessage` and HTTP POST to a local `127.0.0.1:<port>?invoke=<random>` endpoint; response text is relayed to the parent window.
- Word/Excel automation through COM/OLE is supported by strong type-information and symbol evidence.
- Word connector/type structures include request and response XML models, fields, settings, styles, status and return-type metadata.
- Word lifecycle symbols include autosave, silent-save, before-close and before-save handlers. These support the existence of managed save/close behavior but do not alone establish exact wire timing.
- Image and scan UI structures have been decoded, including scan preview, image tools and simple image editor forms.
- ImageGear and ImageEn paths have been analyzed, including crop, rotate, flip, save, scan and multi-page handling. Do not infer enum meanings or scanner ABI from names alone.
- The exact database, full invoke API, complete payload contract, browser implementation and several runtime behaviors remain unresolved.

## Native Linux architecture principles

- Do not use Wine as a final runtime dependency.
- Keep the browser bridge, local service, document engine, and scan/image subsystem as separate components.
- Bind the local service to loopback only; validate origins/tokens, payload sizes, file paths, timeouts and lifecycle behavior.
- Do not invent an API that merely resembles EMWAT. Extract the original request/response contract first.
- LibreOffice Writer is the candidate document application/compatibility bridge, but real templates and field behavior must be tested.
- Preserve image-only letters, scanning, multipage documents, image edits and print-related workflows.
- Do not select a local database without evidence that one is needed and what data it must own.
- Never publish customer letters, credentials, cookies, private endpoints or unredacted runtime traces.

## Current evidence and technical documents

Start with these documents; do not repeat their completed work without new evidence:

- `docs/PROJECT-STATUS.md` — overall findings, confidence levels and next actions
- `docs/PRODUCT-WORKFLOW-ANALYSIS.md` — confirmed product workflow and revised priorities
- `docs/HTTP-LOCAL-API-ANALYSIS.md` — local HTTP service and JavaScript bridge
- `docs/WORD-DOCUMENT-PROTOCOL-ANALYSIS.md` — Word connector, XML structures and lifecycle
- `docs/OFFICE-COM-ANALYSIS.md` — Office Automation/COM
- `docs/IMPORT-TABLE-ANALYSIS.md` — PE imports and dependencies
- `docs/RESOURCE-ANALYSIS.md` — COM and PE resources
- `docs/SCAN-PREVIEW-DFM.md`, `docs/IMAGE-TOOLS-DFM.md`, `docs/SIMPLE-IMAGE-EDITOR-DFM.md` — decoded image/scan forms
- `docs/GEAR-API-CALLS.md`, `docs/IMAGE-CALL-GRAPH.md`, `docs/SCANNER-INTERFACE-ANALYSIS.md` — image/scanner call analysis

## Immediate next steps — in order (updated 2026-11-14)

1. **Finish the remaining XML method/serialization mapping.** The service parser's `TMethodInfo.Params` and BPL `TEmwatMethod.Invoke` use `TDictionary<AnsiString, AnsiString>`. Service slot `+0x0C` reaches shared wrapper `0x0046C9E0), which calls `TEmwatMethod.Invoke` (`0x0046C82C`) and then the subclass slot `+0x10`. Inside Invoke, local `[ebp-4]` is a `TXMLEmwatType` interface; its `+0xB0` thunk `0x0044B709` reaches `TXMLMethodType.AfterConstruction` at `0x0044C458), producing the interface in `[ebp-0x1C]`. That `TXMLMethodType` interface's `+0xCC` thunk `0x0044BA61` reaches `TXMLMethodType.Insert` at `0x0044C754), which appends a child and returns the interface in `[ebp-8]`. RTTI and VTable offsets strongly identify `[ebp-8]` as a `TXMLParamType` interface. Invoke then calls its `+0xB0` and `+0x68` slots with the first and second dictionary-pair strings. The TXMLParamType VTable thunks are `0x0044BDF5` and `0x0044BEB5`; they adjust Self by `-0x50` and resolve to `0x0044C8E4` and shared target `0x0044B568` respectively. The `+0x68` target `0x0044B568` is confirmed as `xmlrtl230.bpl!TXMLNode.SetText(UnicodeString)`, so the second pair string is the parameter node's text/value. The `+0xB0` target `0x0044C8E4` calls `xmlrtl230.bpl!TXMLNode.SetAttribute(UnicodeString, OleVariant)` with the literal attribute name `name` and the first pair string as its value. Thus each pair becomes an XML parameter node with `name` attribute and text content. Focused run 11 (`43571811038`, artifact `14105075475`) confirms both targets and the `name` literal. After the loop, TXMLEmwatType interface slot `+0x54` returns the serialized XML string into Invoke's output parameter; its VTable target still needs mapping. Next decode the TXMLMethodType +0xC8 attribute literal at `0x0044C6A4`: its implementation `0x0044C62C` (TD32 label `Get_Param`) passes the method-name string and this literal to `TXMLNode.SetAttribute`. The `class` attribute and `method` element literal are now confirmed. The TXMLEmwatType serializer getter slot `+0x54` resolves through thunk `0x0044B7A9` to `xmlrtl230.bpl!TXMLNode.GetXML` at `0x0044B590`. Remaining XML task: identify the constructor's second constant at `0x0044C4FC` passed to helper `0x00401430`, then validate the complete serialized XML against runtime captures.

2. **Trace the concrete Word-edit method and its document helper.** Run 76 recovered `TEditWordDocument` VMT `0x005ED764`; slot `+0x10` points to executable target `0x005EE82C`, despite the missing TD32 procedure record. The target reads `wordConfig`, `wordBody`, `letterImages`, and `signData`, then calls `TWordViwer.LoadDocument` at `0x004B7724` with the `TEmwatInvokeParam*` and output-string reference. `LoadDocument` parses the `word-document` config, prepares the document/Wordviewer, and reaches `OnTmrAutoSave` at `0x004B8A84` to register Word callbacks. The corrected registration maps `+0x80 → 0x004CD154` (TD32: `WordAppDocumentBeforeSave`), `+0x90 → 0x004CD54C`, and `+0x98 → 0x004CD9C0` (export name `WordAppNewDocument`). The registered BeforeSave callback at `0x004CD154` checks `Document.Saved`, prompts to save changes, and directly invokes interface slot `+0x29C` with three OleVariant arguments on Yes/No. It is not a registered BeforeClose callback. It has no direct HTTP call; trace its viewer helpers and parent-page message. It reads the generated temp document, builds the response XML, and deletes the temp file. Keep the TD32 symbol-name mismatch caveat for other connector classes.
3. **Finish the service request-record and input-stream trace.** `TMainForm.IdHTTPServerCommandGet` (`0x0047BF30`) and the XML/class dispatcher at `0x00470D00` are mapped through BPL slot `+0x0C` (`0x0046C9E0`) → `TEmwatMethod.Invoke` (`0x0046C82C`) → subclass slot `+0x10`. The handler's `TEmwatInvokeParam` layout is known, and its `SessionId` is a separate server-generated six-digit string. The object at `[ARequestInfo+0xD4]` is now identified with high confidence as `TIdHTTPRequestInfo.PostStream`; identify the exact stream virtual method names/signatures behind its size/read operations, and trace how the internal `SessionId` is consumed. The embedded bridge generates the numeric `invoke` value solely as a per-request URL nonce/cache-buster; it is not a method ID or response-correlation token. The bridge forwards `event.data` unchanged and returns `responseText` to the original `event.source`/`event.origin`.
4. **Validate the concrete HTTP response and its schema.** The successful `LoadDocument` path writes its output XML to `AResponseInfo.ContentText`, calls `IdCustomHTTPServer.TIdHTTPResponseInfo.WriteContent` (`0x0040448C` / IAT `0x0062F9C0`), and sets `TEmwatInvokeParam.bResultSet=true`; the generic dispatcher fallback is skipped. It references `application/msword` and `success`, but the exact serialized element layout/encoding still needs comparison with the captured runtime response. Also trace `bUnloadPkg` cleanup after `TEditWordDocument` sets it true. Do not assume `requested-types=application/msword` proves the final file format is DOC.
5. **Trace the registered BeforeSave callback to the parent-page message and final commit.** The callback at `0x004CD154` is `TWordViwer.WordAppDocumentBeforeSave`, registered at event-record `+0x80`; it is not `WordAppDocumentBeforeClose`. It calls `PreparePrintDocument` (`0x004CB108`), checks `Document.Saved` via `_Document` slot `+0xD8`, then prompts Yes/No/Cancel. Cancel sets the event Cancel word to `0xFFFF`; Yes/No directly invoke interface slot `+0x29C` with three OleVariant arguments (the same dispatch slot used by the three-argument wrapper at `0x0042FFF4`). It does not issue HTTP directly. The separately named `WordAppDocumentBeforeClose` at `0x004CCBBC` has only one direct bounded caller, `FillImgFldsForPrint` at `0x004CCF8F`, and no raw-pointer registration reference was found; its active event role is unproven. Continue by identifying which parent-page `postMessage` causes the bridge's close-time XHR and how its response applies the returned document.
6. **Retain autosave/close candidates only in their proven scope.** The `uSendLog` callback at `0x005EC580` belongs to the autosave-files UI and calls `CloseWordApp`; its DFM resource does not visibly bind a Word close event. WordXP Close wrappers have no direct TD32 CALL xrefs. Neither is the proven main letter close path.
7. **Resume scanner/image subsystem analysis after the connector path is understood.** Keep image-only letters, TIFF, rotate/crop, multipage processing, ImageGear/ImageEn and GEAR/SANE scanning as first-class requirements. Do not reduce the Linux port to text-only document editing.
8. **Only then implement the native Linux bridge contract and integration tests.** Keep the local service loopback-only, validate origins/tokens/payload sizes/file paths/timeouts, and test synthetic letters and templates with LibreOffice Writer. Do not implement guessed endpoints or claim end-to-end parity before protocol/runtime validation.


## Runtime validation questions

- What exact request/response reaches the local service for a Word document?
- What semantic role does the method-node constructor's second constant at `0x0044C4FC` play?
- How are template, fields, styles, body and attachments encoded?
- What is returned on close, including the user's observed close-triggered update?
- Can multiple documents be open at once?
- How are cancel, crash, autosave and recovery handled?
- How are image-only letters and scanned multipage documents transferred?

## Session start checklist

1. Read this handoff and `docs/PROJECT-STATUS.md`.
2. Read only the linked detailed documents relevant to the next checkpoint.
3. Inspect current GitHub Actions runs and the latest commits/artifacts before relying on a previous run.
4. Never repeat completed static-analysis tasks without new evidence.
5. Update `PROJECT-STATUS.md`, the affected analysis document, and this handoff when new evidence changes the next step.

## Evidence discipline

Every conclusion must be labeled as one of: user-observed, statically confirmed, runtime-confirmed, inferred, or unknown. A symbol, string, form caption, or API name alone does not prove runtime behavior. This file consolidates durable facts currently recovered; it is not a complete transcript archive.

## Latest XML protocol finding — 2026-11-14

Focused run 16 (`43573798242`, artifact `14105735885`) confirms the serialization getter: `TXMLEmwatType` interface slot `+0x54` thunk `0x0044B7A9` adjusts `Self` by `-0x50` and jumps to `0x0044B590`, an IAT thunk to `xmlrtl230.bpl!TXMLNode.GetXML`. The method node is set up using literal `method`; its `class` attribute is populated with the method name. Each parameter child stores dictionary key in `name` and dictionary value as node text. This proves the static method/parameter XML structure, but not the full document envelope or wire encoding. The constructor's additional constant at `0x0044C4FC` and helper `0x00401430` still need semantic identification.

## Constructor analysis checkpoint — run 17

Run 17 (`43574768657`, artifact `14106455607`) confirms `0x0044B4D8` is `xmlrtl230.bpl!TXMLNode.GetChildNodes`, used by `TXMLMethodType.AfterConstruction` before adding the `method` element. Constant `0x0044C4FC` is not a valid Delphi string. The subsequent call `0x00401430` jumps through IAT slot `0x0062EC40`; the imported symbol and meaning of its arguments remain unknown. Run 18 is resolving the import slot and dumping nearby bytes. Keep the XML envelope limited to proven `method`/`class` and parameter `name`/text until this is resolved.


## Constructor import lookup correction — run 19

Run 19 (`43575191082`, artifact `14106206890`) finds no import-descriptor entry for slot `0x0062EC40`, despite the slot residing in `.idata`; the on-disk DWORD is `0x00231274`. Treat the indirect jump as an unresolved external/relocated dispatch, not as a named imported routine. The constant at `0x0044C4FC` resembles the `TXMLMethodType` IID bytes but its use is not proven. Next, inspect `TXMLParamType.AfterConstruction` at `0x0044B4F8` (VMT `+0x0C`) to identify the parameter XML element tag. Preserve the existing confirmed mapping: method element + `class` attribute; parameter key in `name`, value in text; serializer getter calls `TXMLNode.GetXML`.
 

## Parameter element constructor probe — run 20

Run 20 (`43576636790`, artifact `14106479073`) corrected a bad VMT assumption: `0x0044B4F8` (`TXMLParamType` VMT `+0x0C`) is an import-style jump thunk via `0x006302B4` to the out-of-image address `0x0024060C`, not a TD32 procedure. Do not use it as `AfterConstruction` or infer the XML tag. The new `tools/find_td32_class_procedures.py` indexes TD32 decorated symbols by class name. Next: inspect its output for actual `TXMLParamType` procedures, trace the constructor candidate and its string references, then update the protocol docs only if the element tag is explicit.

## XML constructor comparison checkpoint — run 22

Run 22 (`43578292246`, artifact `14106852706`) completed successfully. It found a TD32 `TXMLParamType.AfterConstruction` procedure at `0x00614EC8` in the separate `WordRequestXML` module only. That constructor calls `0x0044B4D8` (`xmlrtl230.bpl!TXMLNode.GetChildNodes`) and then unresolved helper `0x00401430` with binary GUID-like constant `0x00614F2C`, not a text tag. The generic Invoke path's XmlResponse module has no own `TXMLParamType.AfterConstruction` symbol in the indexed procedures. The XmlResponse VMT parent pointers `0x00630314` and `0x0063030C` are outside the BPL image and have not been named.

Do not claim the parameter element tag is known. Do not copy the WordRequestXML constructor semantics into XmlResponse. The method/parameter field mapping and GetXML serializer remain statically confirmed; the complete envelope and wire bytes remain unknown.

**Resume here:** resolve the external parent VMT/class references or find the actual XmlResponse parameter initialization path; then prioritize tracing the parent-page message that triggers the close-time POST. Avoid repeating the already-completed TD32 symbol index. Keep image/scanner workflows in scope.

## Run 23 handoff — parameter insertion path

Run 23 (`43579138098`, artifact `14107224578`) succeeded. Important new detail: `XmlResponse.TXMLMethodType.Insert` (`0x0044C754`) calls child-node collection virtual slot `+0x20` with index `-1`, then interface-casts the result to `TXMLParamType`. No child tag string is supplied in that procedure. `TXMLParamType.Set_Name` follows the node's name/attribute interface path and does not reveal its element tag. The method constructor does pass literal `method` through child-node collection slot `+0x10`.

Do not guess the parameter element name. External parent VMTs (`0x0063030C`, `0x00630314`) and helper `0x00401430` remain unresolved. Resume by identifying the XML node-list virtual methods and external class metadata; then switch focus to the parent-page close-time POST/response behavior. Generic Invoke field mapping and GetXML serialization remain confirmed. Native Linux implementation is still not established by these analysis runs.

## Run 24 — XML node-list Add/Get_Param comparison

Run 24 (`43579618380`, artifact `14106929511`) completed successfully. The newly traced `XmlResponse.TXMLMethodType.Add` and the parallel `.EmwatMethods.TXMLMethodType.Add` bodies have the same dispatch pattern: obtain the wrapped node's child-node collection, then invoke its virtual slot `+0x10` with a string argument and an output interface. This is consistent with the method constructor's explicit `Add("method")` path. By contrast, `TXMLMethodType.Insert` invokes child-collection slot `+0x20` with index `-1`, without passing a tag string. This strengthens the conclusion that the parameter node tag is chosen inside the collection's Insert implementation or its underlying node-list class, not in `TXMLMethodType.Insert`.

The paired `XmlResponse` and `.EmwatMethods` `Get_Param` bodies are structurally identical: each calls `TXMLNode.SetAttribute` using the incoming string and a static attribute-name constant. The already decoded `XmlResponse` constant is `class`, consistent with the method-name attribute. The Add/Get_Param procedures have no direct immediate CALL xrefs in the TD32-bounded scan; their use is through interface/VMT dispatch.

**No new parameter element tag was identified.** Next, stop repeating the same class-level traces and resolve the child-node collection implementation / external parent VMT contract. In parallel, shift the main investigation toward the page-side `postMessage` sender and the close-time POST payload/response, because this is the remaining critical gap for the user's observed close-to-register workflow. Preserve the existing unknowns: exact parameter tag, complete XML envelope/wire bytes, and runtime close semantics.

## Next checkpoint — registered close callback trace (run 25 queued)

Historical note: the workflow extension after run 24 (commit b88451617f3500f8ec64e239902533b21ab82a4d) initially targeted 0x004CD154 as BeforeClose and 0x00430070 as a Close wrapper. Both labels were wrong. Run 25 corrected the symbol identity (0x004CD154 is BeforeSave; 0x00430070 is SaveAs2000), and run 26 traced the actual Close overloads and the separate TD32-named 0x004CCBBC helper. Do not reuse the original run-25 target labels.

Once this trace is read, continue toward the missing page-side sender/response contract. The parent web application's JavaScript is not currently included in the repository, so static BPL tracing can only narrow the Word/service side; runtime evidence from the user's HAR already proves that a POST occurs at close and returns an XML response, but the exact response payload semantics still need controlled comparison. Do not ask the user to repeat known close behavior.
 
## Correction — run 25 address/symbol verification (2026-11-14)

Run 25 (`43580008821`, artifact `14108665890`) exposed incorrect target labels in the preceding analysis step. The TD32 symbol at `0x004CD154` is `TWordViwer.WordAppDocumentBeforeSave`, not `WordAppDocumentBeforeClose`. The LoadDocument/OnTmrAutoSave registration code at `0x004B8C9C–0x004B8CCE` explicitly stores `0x004CD154` at callback field `+0x80`, `0x004CD54C` at `+0x90`, and `0x004CD9C0` at `+0x98`; the conditional callback at `+0x88` is `0x004D00AC` or `0x004CE030`. Thus `0x004CD154` is conclusively the registered BeforeSave callback. Do not call it a close callback.

The actual TD32 procedure named `TWordViwer.WordAppDocumentBeforeClose` begins at `0x004CCBBC`, but its only direct immediate caller found is `FillImgFldsForPrint` at `0x004CCF8F`; no registration reference was found in the scanned raw pointer data. Therefore its name alone does not prove that this procedure is the live Word application close-event handler.

A second address error: `0x00430070` is `TWordDocument.SaveAs2000`, not a Close wrapper. The actual `TWordDocument.Close` overload procedures are TD32-labeled at `0x0042FEB0`, `0x0042FF08`, `0x0042FF7C`, and `0x0042FFF4`; the latter is the three-argument overload. A three-argument Close invocation in the callback body dispatches through document interface VMT slot `+0x29C`, but the exact runtime target for that interface dispatch must be established by matching the interface VMT and wrapper semantics, not by assigning `0x00430070`.

Run 25 itself completed successfully, but its added trace commands targeted the wrong symbols for a close-event investigation. Treat its other outputs as useful only where the TD32 labels and address semantics are independently verified. Next analysis must trace the actual Close overload(s), find the genuine callback registration (if present), and distinguish the BeforeSave callback from document-close lifecycle. No claim about the page-side POST is changed by this correction.

## Run 26 — corrected Word Close overload trace queued

After correcting run 25's target-address mistake, the lifecycle workflow now explicitly classifies `0x004CD154` as the registered `WordAppDocumentBeforeSave` callback, identifies `0x004CB108` as `PreparePrintDocument`, and traces the actual `TWordDocument.Close` overloads at `0x0042FEB0`, `0x0042FF08`, `0x0042FF7C`, and `0x0042FFF4`. It also separately checks the TD32-named `WordAppDocumentBeforeClose` procedure at `0x004CCBBC` and its callsites. Workflow commit: `ed328c5c2876aad53ff6ee92054be87c7e6bedfe`.

The prior run's important correction is now recorded in the four protocol/lifecycle documents. Note that `0x004CCBBC` has only a direct call from `FillImgFldsForPrint` in the scanned TD32 callsite set, so the callback's symbolic name is not evidence that it is registered as a live Word event. The actual BeforeSave registration is explicit in `OnTmrAutoSave` at `0x004B8C9C–0x004B8CCE`. The next run must resolve the Close interface slot `+0x29C` and establish whether any separate close-event callback is registered elsewhere.


## Run 26 — corrected Word lifecycle findings (2026-11-14)

Run 26 (43584217243, artifact 14109926135) completed successfully; all 16 workflow steps passed. This section supersedes earlier callback-name interpretations in this handoff:

- 0x004CD154 is TD32-labeled TWordViwer.WordAppDocumentBeforeSave and is the callback registered at viewer field +0x80. It is not WordAppDocumentBeforeClose.
- The separate TD32-named TWordViwer.WordAppDocumentBeforeClose is 0x004CCBBC. Its only direct caller in the bounded scan is FillImgFldsForPrint at 0x004CCF8F; no raw-pointer registration reference was found. Its symbol name does not prove that it is the live Word close event.
- TWordDocument.Close overloads: no arguments at 0x0042FEB0 dispatches through interface slot +0x4D4; one OleVariant at 0x0042FF08, two at 0x0042FF7C, and three at 0x0042FFF4 dispatch through slot +0x29C.
- The registered BeforeSave callback at 0x004CD154 calls PreparePrintDocument (0x004CB108), checks _Document.Saved via slot +0xD8, and conditionally presents the changed-document prompt. Cancel sets the event Cancel word to 0xFFFF. Yes/No branches invoke the three-argument Close wrapper. This is BeforeSave handling, not proof of a separate BeforeClose event.
- 0x00430070 is TWordDocument.SaveAs2000, not Close.

The concrete runtime target behind slot +0x29C, any separate close-event registration, and browser-side close-time POST semantics remain unresolved. Do not overwrite the user's observed behavior that closing applies/registers changes regardless of Save; this static trace has not explained it. Next: resolve the COM interface behind +0x29C and trace the parent-page postMessage/localhost POST and response. Native Linux runtime implementation is not established by this analysis.


## Run 26 — Close overload and callback classification (2026-11-14)

Run 26 (`43584217243`, artifact `14109926135`) completed successfully; all 16 workflow steps passed. Confirmed findings:

- `TWordDocument.Close` no-argument overload at `0x0042FEB0` dispatches through the wrapped `_Document` interface slot `+0x4D4`.
- One-, two-, and three-argument overloads at `0x0042FF08`, `0x0042FF7C`, and `0x0042FFF4` dispatch through slot `+0x29C`.
- The three-argument wrapper loads its underlying interface via `0x0042ABA0`, then calls `[vtable+0x29C]`; this identifies the wrapper call slot, not the final implementation address.
- The registered callback at `0x004CD154` is `WordAppDocumentBeforeSave`; its body can invoke the three-argument Close overload after the Save-state prompt. Cancel writes `0xFFFF` to the event Cancel field.
- The separate TD32-named `WordAppDocumentBeforeClose` at `0x004CCBBC` has only the known direct caller in `FillImgFldsForPrint`; live event-registration status remains unproven.
- `0x00430070` remains correctly classified as `SaveAs2000`, not Close.

### Run 27 queued — controller close path and wrapper resolution

Workflow extension commit: `334b841dd279773345086e3e8903de068390c139`.

The next run adds a TD32 symbol inventory and traces the `CloseMyDoc` callsite at `0x005E9258`, its raw pointer references, `SilentSaveEmwatDoc` and callers, plus final cross-checks of the BeforeClose helper and BeforeSave callers. Do not treat the `CloseMyDoc` name or its `+0x2BC` dispatch as a proven document-close method until its receiver interface is typed. Do not equate `+0x29C` and `+0x4D4` without identifying the Word `_Document` typelib declarations.

The browser-side close POST remains the decisive missing contract. User runtime evidence shows a localhost POST when the document is closed and no equivalent request on Ctrl+S; static callback traces have not explained its trigger or response semantics. Native Linux runtime implementation is not established by these analysis runs.


## Run27 — close-path triage (2026-11-14)

- Run `43586456343` completed successfully; artifact `14110509457`.
- The newly traced `CloseMyDoc` at `0x005E9174` belongs to TD32 module `WordCompareCommandUnit`, not the main `TEditWordDocument` connector class. It invokes interface VMT slots `+0x13C` and `+0x2F0`, then slot `+0x2BC`; no direct raw pointer references to its callsite were found. Do not treat this method as the main letter close implementation without a caller/dispatch link.
- `SilentSaveEmwatDoc` at `0x004D23D8` is a substantial Wordviewer routine. It checks four controller-owned collections/objects at offsets `+0x8C/+0x94/+0x98/+0x9C`, allocates helper objects, invokes `0x004AEBBC`, sets a viewer flag at `+0x44C`, and calls helper `0x004D2948`. It is a stronger next analysis target than the unrelated `CloseMyDoc`, but its invocation timing and relation to HTTP response are not yet established.
- `uSendLog.TfrmShowAutoSaveFiles.WordAppDocumentBeforeClose` at `0x005EC580` belongs to the autosave-files UI and calls `CloseWordApp`; it is not evidence that the main editor registers this callback.
- Run27 did not establish the active Word close event or the close-time POST contract. User-observed close behavior remains the product requirement; static symbol names must not override it.
- Next focused trace: `0x004D2948` and callers/refs of `SilentSaveEmwatDoc`, plus `Emwat.Sys.CloseAllWords` only if its callers connect it to the main editor. Keep the main `TEditWordDocument → LoadDocument → HTTP response` path as the integration anchor.


## Run28 — reclassification of save/close candidates (2026-11-14)

- Run `43587704007` completed successfully; artifact `14110909233`.
- Critical correction: `0x004D2948` is TD32-labeled `TWrapRecord.LineCount` in module `ScanRequestXML`, procedure range `0x004D2948–0x004D2E77`. It is **not** a helper owned by `SilentSaveEmwatDoc`.
- `TWordViwer.SilentSaveEmwatDoc` at `0x004D23D8` has exact range `0x004D23D8–0x004D281B`. Its only direct bounded caller found is `TWordViwer.GetDocFieldName` at `0x004BBA86`. This places it on a field-name lookup/fallback path in the static call graph, not on a proven document-close callback. Its side effects and purpose remain to be determined.
- `Emwat.Sys.CloseAllWords` at `0x0044AD30` has one direct caller: `Emwat.Sys.DeleteTempRAW` at `0x0044B01C`. The routine builds four command strings and passes each to `0x0044B0F8`; current evidence associates it with temporary RAW cleanup, not the editor's user-close action.
- These three items are downgraded as candidates for the main letter-close path. Do not infer lifecycle from names alone.
- Main confirmed anchor remains `TEditWordDocument` slot `+0x10` → `0x005EE82C` → `TWordViwer.LoadDocument` `0x004B7724` → HTTP response writer. The user's observed close behavior remains a product requirement; the static path explaining it is unresolved.
- Next: trace the exact `GetDocFieldName → SilentSaveEmwatDoc` call context and the command targets under `DeleteTempRAW/CloseAllWords`; continue searching for the parent-page close POST and concrete response application path.


## Run 29 — field lookup and cleanup trace (2026-11-14)

Run 29 (`43589571290`, artifact `14111108881`) completed successfully. It adds the following corrections and scope limits:

- `TWordViwer.GetDocFieldName` (`0x004BB81C–0x004BC16F`) calls `SilentSaveEmwatDoc` (`0x004D23D8`) only on a conditional fallback branch: after obtaining a field-name value through interface slot `+0xAC`, it compares that value with a static string and calls SilentSave only when the comparison fails. This is a field-name resolution path, not evidence of a user-close callback.
- The helper addresses used by SilentSave were reclassified: `0x004AEA78` is `TfrmWordPrintOption.SetLetterReceivers`; `0x004AEBBC` is `TfrmWordPrintOption.FreePrinters`. They are print-options UI routines, not generic document-save helpers. The call context shows SilentSave interacts with print-option state; its wider side effects still need tracing.
- `Emwat.Sys.DeleteTempRAW` (`0x0044AE98–0x0044B053`) calls `Emwat.Sys.CloseAllWords` (`0x0044AD30`) at `0x0044B01C` only on a branch reached after its temporary-file/process checks.
- Although TD32 names the routine `CloseAllWords`, its four direct calls at `0x0044AD7E/0x0044ADA0/0x0044ADC2/0x0044ADF1` target `0x0044B0F8`, which TD32 identifies as `Emwat.Sys.GetFileVersion`. Thus the current static evidence does **not** establish that this routine closes Word processes; the symbol name must not be treated as behavioral proof. Its caller remains the RAW cleanup path, not the main editor connector.

**Run 29 conclusion:** no close-time POST trigger or final apply-on-close mechanism was identified. Preserve the user's close-applies-changes observation as a product requirement. The proven server-side `EditWordDocument → LoadDocument → HTTP WriteContent` path remains the anchor; the missing work is still the page-side message sender and the exact response/application lifecycle. Do not spend more runs on these unrelated print/cleanup symbols unless new caller evidence appears.


## User clarification — close is enough; underlying Word save is unresolved (2026-11-14)

The user repeated the real-world test and confirmed: they do not press Word's Save button, yet after closing Word the file is registered/visible in Almas Gam. Treat this as a firm end-to-end product requirement.

Do **not** infer that the document is never saved internally. A likely but unproven sequence is an automatic or EMWAT-triggered Word save during close, followed by EMWAT returning the final artifact/state in the HTTP response to the browser. Keep the following as separate investigation targets: (1) Word/COM save at close, (2) EMWAT artifact collection, (3) HTTP response delivery and Almas Gam persistence. User-facing/product wording: “closing Word is sufficient; the user need not press Save.”


## Next implementation milestone — Python loopback transport (2026-11-14)

A protocol-neutral transport implementation was added under `python/`:

- `src/emwat_linux/bridge.py`: loopback-only HTTP server, health endpoint, bounded opaque POST transport, exact configured Origin allowlist, no request-body logging, sanitized internal errors.
- `tests/test_bridge.py`: unit/integration tests using an ephemeral localhost port.
- `pyproject.toml`: minimal install metadata.
- `.github/workflows/python-bridge.yml`: independent CI workflow.

The `bridge.py` transport remains protocol-neutral and carries raw bytes to an injected handler. Protocol interpretation is now implemented separately in `protocol.py`, and `dispatcher.py` invokes only explicitly registered method handlers. The application factory in `application.py` wires these layers together.

**Immediate next actions:** use the latest Run #89 analysis artifact to refine the `wordBody` stream and temporary document path; recover the exact response/close lifecycle; then implement a real typed `EditWordDocument` handler. Do not register a placeholder as if it were production behavior, and do not claim end-to-end compatibility yet.


## Bridge transport milestone — CI green (2026-11-14)

- Workflow `Python bridge transport`, run `43592145701`, commit `c705ed34ad9a9e87b42d7e2d85d3aa60aea83815`: **success**.
- Seven tests cover loopback-only binding, health endpoint, opaque POST body/query preservation, exact Origin rejection and CORS echo, body-size rejection, unsupported route/method, and sanitized handler errors.
- CI uses `PYTHONPATH=src python -m unittest discover -s tests -v`; it intentionally does not require packaging/build dependencies for this stdlib-only transport.
- The earlier failing runs were corrected: missing setuptools in the runner was avoided, the test payload cap was aligned, and the module was placed under the actual `src/emwat_linux` package path.

Next: validate allowed Origin handling with a safe test page/origin, recover the exact XML parameter node and response envelope, then implement a typed dispatcher. Do not expose the listener to non-loopback interfaces or accept arbitrary origins.


## ادامه کار — parser پوسته XML

نمونه Response واقعی زمان بستن Word که قبلاً کاربر ثبت کرده بود، نام تگ پارامتر را مشخص می‌کند: `<emwat version="1.0"><method class="EditWordDocument"><param name="wordConfig">`. بنابراین برای همین مسیر، تگ `param` دیگر فرضیه نیست و شاهد runtime دارد.

فایل `python/src/emwat_linux/protocol.py` اضافه شد. parser فقط پوسته UTF-8 را می‌خواند، یک method و فرزندان `param` با نام یکتا را می‌پذیرد و متن مقدارها را بدون decode یا تغییر نگه می‌دارد. DTD/entity، XML خراب، نسخه نامعتبر، نام تکراری، markup تو در تو و payload بزرگ‌تر از سقف رد می‌شوند. تست‌ها در `python/tests/test_protocol.py` هستند.

در تحلیل ایستای سرویس، مسیرهای query با کلیدهای `invoke`، `init` و `heartbeat` نیز جداگانه دیده شده‌اند؛ اما پاسخ دقیق heartbeat و بایت‌های پاسخ init هنوز معلوم نیست و نباید پاسخ ساختگی تولید شود.

**وضعیت این گام تکمیل شده:** parser به dispatcher متصل شده و factory برنامه هر سه لایه را ترکیب می‌کند. گام بعدی، پیاده‌سازی handler واقعی `EditWordDocument` پس از روشن‌شدن payload نهایی و lifecycle بستن Word است؛ هنوز هیچ handler تولیدی برای این متد ثبت نشده است.


## Current implementation checkpoint — 2026-11-14 (CI run #20)

**Green:** Python bridge workflow run `43592721635` / commit `2fa217ae83f33b80a7799ede4c75f2cc58b40d76`; 24 tests passed.

Implementation now includes:
- `bridge.py`: IPv4 loopback-only HTTP server, Host-header validation, required exact Origin allowlist, CORS echo only for the exact allowed Origin, socket timeout, bounded request/response bodies, duplicate Content-Length rejection, no request-body logs and sanitized failures.
- `protocol.py`: UTF-8 parser for the runtime-confirmed `emwat → method → param` envelope; parameter values remain opaque.
- `dispatcher.py`: explicit method registry; no dynamic class imports; malformed input 400, unknown method 501, handler failures sanitized.
- Tests: `test_bridge.py`, `test_protocol.py`, `test_dispatcher.py`.

**Not implemented yet:** heartbeat/init response compatibility, a real `EditWordDocument` handler, Word/LibreOffice document editing, close-time response serialization and Almas Gam end-to-end persistence. The user's confirmed behavior—closing Word is enough for the document to appear in Almas Gam without manually pressing Save—remains the core acceptance criterion.

Next action: continue tracing the exact Word close-time response and the source of `wordBody`/final document payload; separately recover `?heartbeat` and `?init` contracts. Do not invent either response.


### Latest verified CI update (2026-11-14)

Python bridge workflow run #22, ID `43593083176`, commit `22a803912b0fa92c3bb5537fb1f0c7952fda7615`: **success**, 27 tests passed. New coverage and checks include Host header path/query/fragment rejection, duplicate Content-Length rejection, ASCII-decimal-only Content-Length parsing, and Transfer-Encoding rejection. No request body or response payload is logged.

A separate static-analysis workflow Run #89 is in progress, adding targeted traces for the Word body stream ingestion and temporary output handling path. Its conclusions are not yet available; do not treat that run as complete.


### Latest application integration checkpoint

`application.py` now exposes `create_bridge_server` to wire transport, parser and explicit dispatcher. Integration tests cover a full localhost POST through parser and a registered test handler, plus origin rejection. CI run #24 (`43593185429`) passed all 29 tests on commit `27986ee96b45009283cd96eecde95110e1b9e448`.

No real `EditWordDocument` handler is registered. The test handler is deliberately synthetic and proves only composition of the layers. The Word lifecycle analysis workflow Run #89 remains in progress; its new target traces include the `wordBody` stream ingestion and temporary output path.


### Latest verified implementation state — CI run #24

Python bridge transport workflow run #24 (`43593185429`), commit `27986ee96b45009283cd96eecde95110e1b9e448`, passed **29 tests**. The tested composition now includes `application.py` → `BridgeHTTPServer` → `XMLMethodDispatcher` → `parse_method_call` → an explicitly registered test handler → HTTP response. The test handler is synthetic; there is still no production `EditWordDocument` handler.

The separate Word lifecycle workflow Run #89 is still processing its deep trace steps. It now includes targeted analysis of `wordBody` stream ingestion, helper routines and temporary output handling. Do not report its findings until the artifact is available and inspected.


## Run 89 — LoadDocument input normalization (2026-11-14)

- Workflow run #89 (43592922191) completed successfully; artifact 14113237316 was inspected.
- Correction to the initial reading: 0x00457050 is TD32-labeled Emwatutils.Finalization in module EmailUtil, not a generic byte-stream helper. Its only direct caller in the scanned TD32 procedures is TWordViwer.LoadDocument at 0x004B778B; it compares the incoming UnicodeString against two global strings and can raise an exception. Exact semantic meaning of the two compared values remains pending string decoding.
- 0x00454B9C is TD32-labeled Emwatutils.euGetASFileName(UnicodeString, UnicodeString), also in EmailUtil. It is called by LoadDocument at 0x004B7796, but it is also used by TIFF/image routines (CreateTiff.SeparteImages, CreateImageFile, PrintWordDoc, and others). This strongly places it in filename/path normalization rather than a Word-only binary stream parser; exact output semantics remain to be verified.
- After those two calls, LoadDocument uses Delphi runtime/import thunks at 0x004012F8, 0x00401270, and 0x004012E0; these jump through the import table to external runtime addresses not mapped in the BPL. The code then constructs an object using global 0x0062F800 and constructor helper 0x004041BC, and calls its virtual slot +0x10 with the computed data pointer and length. The destination class and whether this represents a stream/file writer are not yet established.
- Do not describe wordBody as raw body bytes or a known file path yet. The parameter is handled as a Delphi UnicodeString, transformed by the filename helper, then a length/data pair is passed to an as-yet-unidentified object.
- Run #90 is complete; its verified results and the Run #91 follow-up are recorded below.


## Run 89 supplement — DocFileName evidence

- The LoadDocument string constants include the exact error text `DocFileName can not be null.` at 0x004B8238. In the LoadDocument control flow, the transformed local string is checked for zero length immediately before this error path. This is strong evidence that the LoadDocument argument is being treated as a document filename, not simply as arbitrary document-body bytes.
- The same routine contains the strings `word-document`, `ConfigXML data loaded.`, and `Word Calling Mode: `, indicating logging/configuration activity around document loading. The strings `.doc` and `.docx` are present in the filename validation/normalization helper path. Their exact branch semantics are not yet established.
- Update the working interpretation: outer connector key `wordBody` is passed into LoadDocument, but inside LoadDocument it is validated/processed as a DocFileName-like UnicodeString. Do not assume the key name accurately describes its runtime value type.


## Run 90 — LoadDocument file-stream identification

- Run #90 (`43595049501`) completed successfully; artifact `14113854620`.
- The constructor helper at `0x004041BC` is definitively an IAT thunk to `rtl230.bpl!TFileStream.Create(UnicodeString, Word)`. Therefore the object created at `0x004B780B` is a file stream, not an unidentified memory stream.
- `LoadDocument` passes a filename-like string into that constructor, then invokes the stream object's virtual slot `+0x10` with a data pointer and a length obtained from the original `wordBody` argument. This is strong evidence that `wordBody` is used as file content/data at this point, while a separately derived local string supplies the destination filename. Do not yet claim whether the data is UTF-8, UTF-16, Base64-decoded, or another encoding; the exact length semantics and destination path are still open.
- The constructor mode argument is pushed as `0xFF00`; do not translate this to a named Delphi file mode until the calling convention and constant are checked against the exact RTL version.
- Run #90 decoded additional strings: `Word document file created.`, `word-document`, `ConfigXML data loaded.`, `Word Calling Mode: `, `image/tif`, `base64`, `Result word file content read successfully. try (%d)`, and error `DocFileName can not be null.`. These support a staged file-creation/configuration workflow, but do not independently establish the temporary folder or response schema.
- `0x00457050` is TD32-labeled `Emwatutils.Finalization` in module `EmailUtil`, and `0x00454B9C` is `Emwatutils.euGetASFileName`; treat these as string cleanup/name transformation helpers, not body parsers.
- The response write path remains the known `AResponseInfo.ContentText` → `TIdHTTPResponseInfo.WriteContent` path. Run #90 did not reveal the final close-time POST/apply contract.
- Immediate next work: trace the destination filename construction (`0x00401348`, `0x004012F8`, `0x00401270`, `0x004012E0`), inspect the second file-stream creation in `LoadDocument` around `0x004B7C39`, and correlate the file path/data with the final response XML.

- Additional Run #90 detail: a second object is constructed through the same `TFileStream` VMT/constructor path at `0x004B7C3E`, using the same derived filename and constructor mode argument `0`. Its code obtains stream size and calls virtual slot `+0x0C` with a buffer/count pair, consistent with reopening and reading the file. Treat the exact operation name as provisional until the RTL VMT slot is resolved.


## Run 91 — تأیید عملیات نوشتن/خواندن فایل در TFileStream

- Run #91 (43595953793) با موفقیت تمام شد؛ artifact 14114711446.
- import/VMT slot در 0x0062F800 به نماد کلاس rtl230.bpl!@System@Classes@TFileStream@ resolve شد و constructor در 0x004041BC به TFileStream.Create(UnicodeString, Word) تعلق دارد.
- در مسیر اول LoadDocument، مقدار mode برابر 0xFF00 است که در قرارداد TFileStream.Create معادل fmCreate است؛ سپس virtual slot +0x10 با pointer و count داده فراخوانی می‌شود. در layout استاندارد TStream این slot متد Write است. بنابراین فایل مقصد ایجاد و داده ورودی در آن نوشته می‌شود.
- در مسیر دوم، همان VMT/constructor با mode برابر صفر (fmOpenRead) استفاده می‌شود؛ سپس اندازه stream گرفته شده و virtual slot +0x0C با buffer و count فراخوانی می‌شود که در layout استاندارد TStream متد Read است. این تأیید می‌کند فایل تولیدشده دوباره باز و خوانده می‌شود.
- این دو مسیر شواهد مستقیم یک چرخه create/write سپس open-read/read را فراهم می‌کنند. مسیر واقعی فایل و مقصد نهایی داده خوانده‌شده هنوز مشخص نیست؛ بنابراین فعلاً نام آن را «فایل میانی» می‌گذاریم، نه الزاماً temp directory خاص.
- helperهای 0x00401270، 0x004012E0، 0x00401348 به slotهای .idata می‌پرند که در import descriptorهای قابل‌تحلیل پیدا نشدند؛ نام‌گذاری این helperها یا نسبت‌دادن قطعی آن‌ها به تبدیل encoding مجاز نیست.
- Run #91 هیچ قرارداد close-time POST یا response payload تازه‌ای پیدا نکرد. مرحله بعد: تحلیل ادامه LoadDocument پس از خواندن فایل، مشخص‌کردن مسیر فایل و اینکه بایت‌های خوانده‌شده چگونه به Word/فرمت TIFF و پاسخ HTTP منتقل می‌شوند.


## آخرین وضعیت مهندسی معکوس — Run 92

- GitHub Actions workflow run #92 با شناسه 43597403349 موفق شد؛ artifact دقیق 14114738491 بررسی شد.
- در `LoadDocument`، بعد از بازکردن مجدد فایل واسط و خواندن آن، تابع TD32 با نام `TWordViwer.OnTmrAutoSave` در آدرس 0x004B8A84 فراخوانی می‌شود (callsite: 0x004B7A58). این تابع نقطه شروع مهمی برای trace چرخه پس از بارگذاری Word است، اما هنوز نباید آن را callback بستن سند یا ارسال پاسخ HTTP فرض کرد.
- تابع `TWordViwer.AddCustomDocPropertiesToDic` در 0x004D1454 نیز در LoadDocument فراخوانی مستقیم دارد و به نظر می‌رسد properties سفارشی سند را به dictionary منتقل می‌کند.
- مسیر تصاویر: `CreateImageFile` در `EmwatDocPrintHandlerUnit` مجموعه ورودی‌ها را پردازش می‌کند و `PrintWordDoc` با `TFileStream(fmCreate)` داده را در فایل می‌نویسد. `CreateTIFF.SeparteImages` نیز در همان ماژول وجود دارد؛ caller مستقیم در اسکن فعلی پیدا نشد. این مسیرها هنوز به bridge اصلی یا HTTP response متصل نشده‌اند.
- هیچ close-time POST یا payload نهایی در Run 92 کشف نشد.
- گام بعدی بدون سؤال از کاربر: trace کامل `OnTmrAutoSave` و helperها/callerها، سپس event registration و مسیرهای Word COM Save/Close؛ هم‌زمان شناسایی dispatch غیرمستقیم برای TIFF/Print. پس از هر run، یافته‌ها و محدودیت استنتاج در همین handoff و اسناد پروتکل ثبت شوند.


## اجرای بعدی — Run 94 در حال اجرا

- Workflow توسعه‌یافته برای trace عمیق‌تر `OnTmrAutoSave` با commit نهایی `ea721080388e7d1903a6fb67af08abcf300c8f7c` ثبت شد.
- Run #93 به‌دلیل push اصلاحیه workflow لغو شد؛ Run #94 با شناسه 43598550321 روی نسخه اصلاح‌شده در حال اجراست.
- این run بدنه و ارجاعات `OnTmrAutoSave`، helperهای 0x004CDB54، 0x004C5D68، 0x004D68D4 و 0x004D531C، constructor مربوط به WordViewer و ارجاعات pointer مسیر TIFF/Image را جمع‌آوری می‌کند.
- پس از پایان Run #94، artifact را با شناسه واقعی از GitHub دریافت و بررسی کن؛ تا آن زمان هیچ نتیجه‌ای درباره Save/Close یا اتصال TIFF به bridge اعلام نشود.


## Run 94 — یافته‌های جدید و اصلاح برداشت از OnTmrAutoSave

- Run #94 با شناسه 43598550321 و artifact 14115756587 موفق بود.
- تابع `TWordViwer.OnTmrAutoSave` در 0x004B8A84 فقط یک نام نماد است؛ caller مستقیم مشاهده‌شده در TD32، `LoadDocument` در 0x004B7A58 است. بدنه در زمان LoadDocument اتصال OLE Word را برقرار می‌کند، حالت‌های view/readonly/protected را می‌خواند، چند callback را ثبت می‌کند و پیام `Init word engine finished.` را ثبت می‌کند. نباید آن را صرفاً عملیات ذخیره خودکار یا close handler دانست.
- callbackهای ثبت‌شده: 0x004CD154، 0x004CD54C، 0x004CD9C0 و بر اساس flag یکی از 0x004D00AC/0x004CE030. Run #95 برای trace بدنه و callerهای این handlerها ساخته شد.
- 0x004CDB54 = `TWordViwer.QuitWord`; 0x004C5D68 = `TWordViwer.SetDocCaption`. دو تابع 0x004D68D4 و 0x004D531C متدهای Remove دو Dictionary برای Custom Document Properties هستند و ارتباطی با AutoSave ندارند.
- Run #95: workflow run id 43599550286؛ commit fc4702dbd4c80ed73ac6bc5edac2b2f8d3a98654؛ وضعیت اولیه queued. پس از پایان، artifact را دریافت و handlerهای ثبت‌شده را بررسی کن.
- پرسش فنی اصلی همچنان: کدام event واقعی Word باعث ذخیره/جمع‌آوری سند و کدام مسیر داده را به HTTP response می‌سپارد؟ تا زمانی که handlerها و callerهایشان بررسی نشده‌اند، ادعای close-time POST نکن.


## Handoff — Run 95 completed (2026-11-14)

Run `43599550286` succeeded; artifact `14115498934` was downloaded and inspected.

### New evidence
- `0x004CD154` = `TWordViwer.WordAppDocumentBeforeSave` (not BeforeClose).
- `0x004CD54C` = `TWordViwer.WordAppNewDocument`.
- `0x004CD9C0` = `TWordViwer.WordAppWindowActivate`.
- `0x004CE030` = `TWordViwer.WordAppDocumentBeforePrintBGPrint`.
- `0x004D00AC` = `LoadOptions`.
- `OnTmrAutoSave` writes `0x004CD154` and `0x004CD54C` into callback-like object fields during LoadDocument. Treat this as evidence consistent with callback registration, not a complete proof of the COM event contract.
- Direct-call scans have zero direct CALL xrefs for these handlers; indirect COM/callback dispatch is not covered by those scans.
- The distinct `WordAppDocumentBeforeClose` procedure at `0x004CCBBC` has only one direct caller found, `FillImgFldsForPrint`; do not treat it as the main editor's active close handler.
- No close-time HTTP POST or final result payload was identified.

### Continue next
1. Trace the callback table/object construction and the indirect event dispatch that reaches `0x004CD154` / `0x004CD54C`.
2. Resolve interface VMT slot `+0x29C` used by `WordAppWindowActivate` and the document interface calls used by `WordAppNewDocument`.
3. Separate print/export/image handling from editor close/return behavior.
4. Keep the XML handler schema and close-result payload opaque until directly proven. Do not implement speculative production handlers.
5. Continue updating all three analysis documents after each meaningful run.


## Run 96 handoff — callback slots (2026-11-14)

Run `43600693760` succeeded; artifact `14116641628` inspected.

Callback/context pairs assigned in `TWordViwer.OnTmrAutoSave` to the Word object at `viewer + 0x44`:
- `+0x80/+0x84`: `0x004CD154` = `WordAppDocumentBeforeSave`
- `+0x90/+0x94`: `0x004CD54C` = `WordAppNewDocument`
- `+0x98/+0x9C`: `0x004CD9C0` = `WordAppWindowActivate`
- `+0x88/+0x8C`: conditional `0x004D00AC` (LoadOptions) or `0x004CE030` (BeforePrintBGPrint), based on `[viewer+0x3C]`; later assignment sites exist too.

Next: inspect the full tail of `OnTmrAutoSave`, determine the callback-record consumer/indirect dispatch ABI, and identify whether the close event is hooked through another Word event object. Do not implement a guessed close-time POST.

## آخرین پیشرفت مهندسی معکوس — 2026-11-14، Run 97

- GitHub Actions Run 97 موفق شد؛ artifact 14117102104 بررسی شد.
- 0x00404FBC برابر thunk به TOleServer.SetConnectKind در vcl230.bpl است؛ در راه‌اندازی OLE با آرگومان 1 استفاده می‌شود.
- 0x004013F8 = DynArrayClear، 0x00401398 = System.Pos، 0x00401368 = UStrCat. این‌ها helperهای RTL هستند و نباید به‌عنوان callback dispatcher تفسیر شوند.
- 0x004C5D68 دو property ناشناخته از OLE می‌خواند و در viewer+0x4C/+0x4D ذخیره می‌کند.
- 0x004CDB54 بررسی substring انجام می‌دهد؛ مقدار مورد جست‌وجو هنوز از نظر معنایی شناسایی نشده است.
- teardown مسیر OnTmrAutoSave در بعضی شاخه‌ها TWordApplication.Quit و چند فراخوانی VMT/interface دارد. معنای دقیق slotها هنوز باز است.
- WordAppDocumentBeforeClose در 0x004CCBBC هنوز فقط یک direct caller قطعی دارد: FillImgFldsForPrint. آن را handler قطعی close editor فرض نکن.
- هیچ close-time HTTP payload یا XML response در این run کشف نشد.
- Run 98 برای trace کردن 0x004BCA88 و slotهای teardown به workflow افزوده شد.

## اصلاح برداشت از Run 98 — 2026-11-14

- `0x004CDB54` نام TD32 آن `TWordViwer.QuitWord` است. propertyای از OLE را به رشته تبدیل می‌کند و literal ناشناختهٔ `0x004CDC14` را در آن جست‌وجو می‌کند. وجود literal نتیجه False و نبود آن True می‌دهد؛ caller در حالت True به شاخه‌ای با `TWordApplication.Quit` و interface calls می‌رود. متن literal هنوز decode نشده است.
- `0x004C5D68` نام نمادین `TWordViwer.SetDocCaption` دارد. بدنه دو property از OLE می‌خواند و در `viewer+0x4C/+0x4D` ذخیره می‌کند؛ نام و رفتار دقیق propertyها باز است.
- `0x004BCA88` در واقع `TWordViwer.GetXmlFieldInfo` است (procedure بزرگ 12,688 بایتی)، نه helper اختصاصی close. در `GetCaptionItemFont` و `WordAppDocumentBeforeClose` فراخوانی می‌شود.
- `WordAppDocumentBeforeClose` مقادیر field را از مجموعه‌های `+0xE8/+0xEC` پردازش می‌کند و سپس `GetXmlFieldInfo` را فراخوانی می‌کند؛ اما ثبت آن به‌عنوان رویداد عادی بستن سند هنوز اثبات نشده است.
- Run 99 برای decode literal شرط و بررسی interface tableها اضافه شده است.


## Run 101 — تفکیک شرط فعال‌سازی Office از چرخه بستن سند (2026-11-15)

- GitHub Actions workflow run #101 با شناسه `43680106253` روی commit `cdf542e4bd486a63d92a1b26c41a05f30028ae70` با موفقیت پایان یافت؛ artifact `14148322936` دریافت و بررسی شد.
- خطای Run 100 صرفاً از فراخوانی scanner بدون آرگومان selector لازم بود؛ workflow با selector صریح `*` اصلاح شد و Run 101 کامل شد.
- literal در `0x004CDC14` اکنون decode شده است: `Activation` (UTF-16LE). تابع `TWordViwer.QuitWord` در `0x004CDB54` این substring را در رشته‌ای که از property شیء OLE در `viewer+0x44` می‌خواند جست‌وجو می‌کند.
- اگر `Activation` پیدا شود، `QuitWord` مقدار False می‌دهد؛ اگر پیدا نشود، True می‌دهد. در caller یعنی `OnTmrAutoSave`، نتیجه True شاخه‌ای را فعال می‌کند که پیام `<Office LISENCE>: Word is not activated. Close Method.` را ثبت/نمایش می‌دهد و سپس `TWordApplication.Quit` را فراخوانی می‌کند. بنابراین این شاخه کنترل فعال‌سازی Office و خروج از Word است؛ مدرکی برای ذخیره سند یا ارسال آن به Almas Gam نیست.
- در resourceهای BPL، فرم `TEmSettingForm` شامل کنترل‌های `rbAutoSave`، `rbDontSave`، `chkDntAskForSave` و `cbbAutoSaveInterval` است. این‌ها وجود تنظیمات ذخیره خودکار/عدم ذخیره و فاصله زمانی را ثابت می‌کنند، اما به‌تنهایی نشان نمی‌دهند که کدام گزینه در نصب کاربر فعال بوده یا مسیر ثبت نهایی نامه چگونه عمل می‌کند.
- یک مسیر جدا در ماژول `uSendLog` شناسایی شد: `TfrmShowAutoSaveFiles.WordAppDocumentBeforeClose` در `0x005EC580`، تابع `CloseWordApp` در `0x005EBDA8` را فراخوانی می‌کند؛ caller دیگر `btnShowFileClick` است. نام کلاس، فرم `TfrmShowAutoSaveFiles` و callerهای مستقیم نشان می‌دهند این handler متعلق به پنجره نمایش فایل‌های AutoSave است، نه اینکه لزوماً handler اصلی ویرایش نامه باشد. بدنه CloseWordApp روی مجموعه‌ای از اشیای Word/Document loop می‌زند و متدهای interface را صدا می‌زند؛ معنای دقیق هر slot هنوز resolve نشده است.
- این مسیر جدا را نباید با `TWordViwer.WordAppDocumentBeforeClose` در `0x004CCBBC` یکی دانست. دومی همچنان فقط caller مستقیم شناخته‌شده `FillImgFldsForPrint` دارد.
- نتیجه منفی پابرجاست: Run 101 هیچ close-time POST تازه، payload نهایی، یا اتصال اثبات‌شده‌ای از `CloseWordApp` به پاسخ HTTP ارائه نکرد.
- گام بعد: trace بدنه `TEmSettingForm` و ذخیره/خواندن گزینه‌های AutoSave، resolve کردن interface slotهای `CloseWordApp`، و بررسی اینکه callbackهای ثبت‌شده در WordViewer چگونه به مسیر پاسخ نهایی `EditWordDocument` می‌رسند. تا آن زمان production handler یا close protocol حدس زده نشود.


## Run 102 — AutoSave settings and separate AutoSave viewer lifecycle

- GitHub Actions run #102 (43681595513, commit 168793fd5e2dfaeff6036894409e7a5385944d31) completed successfully; artifact 14148712060 was inspected.
- TEmSettingForm.chkDntAskForSaveClick at 0x005EAA20 opens the current-user registry hive (0x80000001, HKCU) and performs multiple registry value writes. The values include settings associated with controls at instance offsets +0x3E0, +0x3D8, +0x3C4, +0x3C8, +0x3CC, and the AutoSave interval control at +0x3F4. For interval values 1–5 it multiplies a lookup-table value by 1000; otherwise it writes 0x2710 (10000 ms). Registry value names and complete semantic mapping still require resolving the referenced string constants and registry helper APIs.
- The settings resource confirms controls rbAutoSave, rbDontSave, chkDntAskForSave, chkSaveIOxmls, and cbbAutoSaveInterval. This proves the UI exposes AutoSave-related options; it does not prove which options were selected in the user's session or how the main editor's final registration works.
- TEmSettingForm.FormCreate at 0x005EAD94 delegates to inherited form creation, then invokes helper 0x00402A50 and 0x0040496C; those helper semantics and the exact read-side settings mapping remain unresolved.
- The small btnOkClick handler at 0x005EAA14 calls TCustomForm.Close via thunk 0x00404E84; it does not itself show persistence logic. The checkbox click handler is the one containing registry operations.
- The separate TfrmShowAutoSaveFiles.FormClose at 0x005EBF20 is called from its own Delete/FormCreate/finalization paths. Its WordAppDocumentBeforeClose callback at 0x005EC580 calls CloseWordApp only when a document interface's first word equals 0x2E; this is tied to the AutoSave-files viewer, not proven to be the main Word editor's close event.
- CloseWordApp at 0x005EBDA8 iterates a Word Documents collection, conditionally inspects/updates document items, and invokes interface slot +0x29C; exact COM method semantics remain unresolved. It does not establish an HTTP POST or final registration payload.
- No evidence in Run 102 links these registry settings or the AutoSave viewer teardown to the main editor's final Almas Gam registration request. Keep that protocol unknown until a concrete caller/payload/response chain is found.
- Next target: resolve registry helper APIs and string constants to map each setting key/value; separately resolve the +0x29C Word interface slot and identify actual event registration/dispatch for the main viewer's BeforeClose callback. Continue tracing the main editor's save/close-to-HTTP response path without conflating it with the AutoSave viewer.


## Run 103 — registry settings and Word lifecycle follow-up (2026-11-15)

- GitHub Actions run #103 (run ID `43682606812`, commit `b0f92c0f3298b1d92b41906691e84960f75f6ee7`) completed successfully: 36/36 steps; artifact `14149148019` (`emwat-word-lifecycle-analysis`).
- The settings handler `TEmSettingForm.chkDntAskForSaveClick` at `0x005EAA20` confirms a current-user registry flow: it creates/uses a registry object, selects root `HKEY_CURRENT_USER` (`0x80000001`), opens `Software\\Emwat\\Dynamic Config`, writes integer and Boolean values, then releases the registry object. The IAT/thunk map identifies `0x00404414` as `TRegistry.WriteInteger(UnicodeString, Integer)` and `0x00404424` as `TRegistry.WriteBool(UnicodeString, Boolean)`.
- Confirmed value names extracted from the Delphi UTF-16 string headers: `Logging Level`, `Save I/O Trace Files`, `Background Priniting` (original spelling), `Dont Ask Save On Print`, `Save Before Print`, and `AutoSaveInterval`.
- Handler mapping from the observed writes: component/object offsets `+0x3E0` → integer `Logging Level`; `+0x3D8` → Boolean `Save I/O Trace Files`; `+0x3C4` → Boolean `Background Priniting`; `+0x3C8` → Boolean `Dont Ask Save On Print`; `+0x3CC` → Boolean `Save Before Print`; `+0x3F4` → integer `AutoSaveInterval`. For interval selection values 1–5, the selected lookup-table value is multiplied by 1000 before writing; other values write 10000 ms. This is the save-side mapping; don't assume startup reads use the same helper path until found.
- Corrected a prior lead: `TEmSettingForm.FormCreate` at `0x005EAD94` calls `0x00402A50` (`user32!GetDesktopWindow`) and `0x0040496C` (`TWinControl.SetParentWindow`), not registry-read routines. Its short body does not load the persisted settings. The exact settings-load path remains unresolved.
- The `BeforeSave` callback body still performs a prompt and may dispatch the 3-argument Word `Close` overload through interface slot `+0x29C`; direct CALL xref scans do not resolve its callback wiring because the stored function pointer is assigned as data in `OnTmrAutoSave`. This is evidence of callback pointer storage, not yet proof of the COM event-sink ABI or final server registration.
- All four `TWordDocument.Close` overload wrappers were traced. The no-argument overload dispatches slot `+0x4D4`; overloads with one, two, or three optional arguments dispatch slot `+0x29C`. TD32 direct-call scans show no direct CALL xrefs for these wrappers; raw pointer matches occur in debug metadata, so do not infer which overload is used by the main editor solely from those scans.
- No verified close-time HTTP POST, response payload, or final Almas Gam registration operation was found. The user's observed behavior (closing Word without manually pressing Save still registers the document) remains an important runtime fact to reconcile, not a protocol proven by this static trace.
- Next targets: locate the *read-side* registry operations for `Dynamic Config` and the actual settings form initialization; trace callback record consumption / COM connection-point wiring around `OnTmrAutoSave`; identify real main-editor close and final local HTTP request/response chain. Keep the AutoSave files viewer's separate close handler isolated from the main editor.


## Handoff — after Run 104 (2026-11-15)

Run #104 (`43683614577`) completed successfully (37/37); artifact `14150300042`.

Important new validation notes:
- Registry-related imports exist (Win32 `RegOpenKeyExW`/`RegQueryValueExW` and Delphi `TRegistry` read/write APIs), but the first scanner only searched direct calls to executable thunks and found zero sites. This does not prove absence of registry reads.
- The first post-read code range `0x004B7CFA–0x004B809D` decoded zero instructions because it starts in non-code data. The observed valid continuation is `0x004B7DE1`.
- Commits `743e6378` and `a4027a70` add IAT-indirect CALL/JMP and pointer-reference scanning and correct the post-read range. Check the latest workflow run/artifact before drawing conclusions.

Do not claim the registry startup read path, main-editor close event sink, close-time HTTP request, or final Almas Gam registration payload has been resolved. Continue with the latest workflow output.

## Winux/Wine live validation checkpoint — 2026-11-15

The detailed evidence is recorded in [WINUX-RUNTIME-VALIDATION.md](WINUX-RUNTIME-VALIDATION.md). This checkpoint separates observed behavior from assumptions:

- **User-observed / runtime-confirmed:** the Windows installer was run through Winux Engine in the managed `emwat` prefix; Winux recorded installer status `SUCCESS` (verification remained `PENDING`). This is installation success, not proof of full application compatibility.
- **Runtime-confirmed:** `EmwatService.exe` and `EmwatAgent.exe` were present as running Wine processes under the normal desktop user, not root. Their logs report Service startup/listening on port 1984 and Agent startup. Winux's own process/service listings did not track these processes.
- **Runtime-confirmed:** `127.0.0.1:1984` was listening. A plain GET to `http://127.0.0.1:1984/` returned `HTTP/1.1 200 OK`, `Content-Length: 0`, and an `IDHTTPSESSIONID` cookie header. The socket was attributed by `ss` to `wineserver`, not directly to either Windows executable.
- **Strict interpretation:** this GET proves only that the loopback HTTP listener answered at that time. It does not validate `?heartbeat`, `?init`, POST dispatch, browser messaging, XML method handling, Word document round-trip, or Almas Gam registration.
- **Runtime-confirmed:** host CUPS scheduler was running but `lpstat -t` reported no destinations/queues. GAM-related files `winzvprt5.sys`, `zvprt5.ini`, and `spool/drivers/x64/zvprt1.gpd` were present in the Wine prefix. This proves file presence only—not Windows spooler registration, printer enumeration, or successful printing.
- **Unknown:** whether the GAM virtual printer can function under Wine, whether it can be replaced by a Linux/CUPS implementation, and what exact print data/protocol it consumes. Do not infer failure solely from the absent CUPS queue or infer success from the installed driver files.
- **Next runtime probe:** inspect the results of GET/HEAD/OPTIONS/POST against the root endpoint and the service/agent binaries/configuration for endpoint clues. Do not send fabricated XML to production method handlers. Continue with a harmless test letter and sanitized browser Network metadata before attempting the real Almas Gam workflow.

This Wine runtime experiment is a reverse-engineering aid only. The product target remains a native Linux implementation; do not make Wine or Windows kernel printer drivers dependencies of the final architecture.

## Winux HTTP method and binary-string checkpoint — 2026-11-15

New runtime evidence and executable-string findings are recorded in:
- [WINUX-RUNTIME-VALIDATION.md](WINUX-RUNTIME-VALIDATION.md)
- [HTTP-LOCAL-API-ANALYSIS.md](HTTP-LOCAL-API-ANALYSIS.md)

Key facts:
- GET, HEAD, OPTIONS and POST to only `http://127.0.0.1:1984/` each returned `200 OK` with an empty body. GET/HEAD/POST showed an `IDHTTPSESSIONID` cookie header; OPTIONS did not in the captured output.
- These root-path probes used no valid EMWAT application request. They do **not** establish CORS support, XML parsing, POST dispatch, heartbeat/init behavior, or document workflow success.
- `EmwatService.exe` contains Indy HTTP server/session symbols, `IDHTTPSESSIONID`, HTTP method-override strings, a port-1984 bind-failure message, and a service termination marker `{2EC42BF4-EA08-4476-AB86-466763F80E9A}_TERMINATE_EM_SERVICE_`.
- `EmwatAgent.exe` contains localhost/127.0.0.1 strings, Word connection/open-document/sign-insertion error messages, and `TLoginCredentialService` RTTI/symbol strings. These are static string/RTTI observations, not proof those code paths executed in the current session.
- No matching Emwat-named config files with the searched extensions were found in the searched ProgramData/AppData locations; this is not proof that no configuration exists elsewhere.

**Resume:** inspect `?heartbeat` and `?init` safely; identify root handler/session creation; trace Agent heartbeat and Word automation failure/success paths; then capture sanitized metadata for a real browser-originated request. Do not send fabricated payloads to real application methods. Do not treat generic empty 200 responses as API compatibility.


## Cross-project Winux update — 2026-11-15

Reviewed the latest Winux Engine development context and recorded the transferable findings in [WINUX-RUNTIME-VALIDATION.md](WINUX-RUNTIME-VALIDATION.md). Reusable patterns include the ServiceBackend contract and injected systemd-user backend, separation of ServiceManager from ProcessManager, read-only diagnostics, symlink-safe prefix/path handling, and explicit x86/x64 WoW64 detection. The latest Winux working-tree context reports 216 passing tests, but the public Winux GitHub docs may lag those local changes.

Use these capabilities only as optional Wine-test infrastructure and as design patterns. Do not make Winux or Wine a dependency of EMWAT-Linux's native product architecture. In particular, do not equate a Winux-managed Linux user service with Windows Service Control Manager support, and do not assume the already-observed EMWAT Wine processes are tracked by Winux until verified.


## Run 113 — startup registry read located (2026-11-15)

Workflow #113 succeeded (run ID `43688755518`, artifact `14151906706`). The earlier “startup settings-read path unresolved” note is superseded: the main `TWordViwer` constructor at `0x004D0D24–0x004D0FE6` opens `HKCU\\Software\\Emwat\\Dynamic Config` and reads four values:
- `Background Priniting` → Boolean field `+0x3C`, default true.
- `Dont Ask Save On Print` → Boolean field `+0x3D`, default true.
- `Save Before Print` → Boolean field `+0x3E`, default false.
- `AutoSaveInterval` → integer field `+0x88`, default 0 and minimum 10000 ms.

Reads are guarded by `ValueExists`; values are loaded with `ReadBool` / `ReadInteger`. `Logging Level` and `Save I/O Trace Files` are not handled in this constructor. Do not infer timer/save semantics solely from the interval field.

**Still unresolved:** main-editor close callback semantics, close-time HTTP request/response, and final Almas Gam registration payload. Preserve the user's observed fact that closing Word without pressing Save registers the document; static analysis has not yet explained the mechanism.


## Registry follow-up — Runs 116–117 (2026-11-15)

Runs #116 (`43699248792`) and #117 (`43703253785`) succeeded (37/37 and 38/38 steps). The new artifact identifies `TETracer.GetUniquePostfix` as a registry **write** path: create `TRegistry` (`0x00467C99`), set root to HKCU (`0x00467CB7`), call `WriteBool` (`0x00467D63`) and `WriteInteger` (`0x00467D75`). The value-name strings at `0x00467F2C` and `0x00467F64` are not yet decoded. The `0x00466D16` hit is only a raw pointer reference; its surrounding bounded trace is incomplete. Do not claim that either path reads `Logging Level` or `Save I/O Trace Files`.

**Resume target:** extract complete procedure boundaries/disassembly for `TETracer.GetUniquePostfix` and decode the two string arguments, then locate actual `ReadBool` / `ReadInteger` consumers for the remaining settings. Do not disturb the established Run 113 read-side mapping. The main Word close-to-Almas registration chain remains unproven.


## Handoff — parallel reverse-engineering checkpoint (2026-11-15)

Continue autonomously; no user input is required for the current static-analysis work.

### Latest workflow results

- Word lifecycle #121: run 43707049641, successful; artifact 14158949168.
- Word request lifecycle #3: run 43709706063, successful 13/13; artifact 14159833681.
- Registry settings #4: run 43709607471, successful; artifact 14159692702.
- Filename/temp cleanup #7: run 43709510495, successful; artifact 14160380463.
- Python bridge #42: run 43709846976, successful; 45 tests.

### Critical findings to preserve

- Main Word callback record installs 0x004CD154 at +0x80. Its TD32 symbol is WordAppDocumentBeforeSave, but its log strings say OnBeforeClose. It displays the custom Persian register-changes prompt and calls Document.Close through interface slot +0x29C on non-cancel paths. The exact COM event-slot name remains unproven.
- The separate routine 0x004CCBBC (symbolized WordAppDocumentBeforeClose) is not the pointer installed in the main event record.
- Dynamic Config reads are now mapped: Background Priniting, Dont Ask Save On Print, Save Before Print, AutoSaveInterval, Logging Level, Save I/O Trace Files. TETracer's Created IO Trace Count is a 15-count trace quota.
- Image/print settings use HKCU\SOFTWARE\Emwat\PrintParams with mLeft/mTop/mRight/mBottom, Posotion, Size, PrintRange.
- Exported CloseAllWords (0x0044AE98) enumerates Word windows and may execute taskkill.exe /f /im WINWORD.EXE; it then calls exported RemoveTempFiles (0x0044AD30), which uses DeleteTempRAW (0x0044B0F8) to remove temp-file masks. Exported GetFileVersion is at 0x0044B2DC. The external service caller is unknown; do not equate this cleanup API with the user's main-editor close action.
- Packet-level timing confirms one long-lived EditWordDocument request: body complete at 0.002154 s, first response byte at 54.560037 s, gap 54.557883 s; the response transfers in about 1.362 ms. The returned DOC is rewritten: input 872,960 bytes; estimated complete response 875,008 bytes (+2,048); OLE first-directory-sector pointer 1698 → 1702 at offset 48. The exact Word/COM release event is still unresolved.
- LoadDocument writes wordBody bytes directly to a temporary stream. Base64Decode at 0x004B7E44 uses [ebp-8], not the wordBody argument. Do not claim this call decodes wordBody.
- The successful LoadDocument path writes AResponseInfo.ContentText and calls WriteContent. Exact timing relative to Word close remains unresolved.

### Python bridge

- Heartbeat returns captured TickTack.
- Init route returns the 994-byte capture-matched script with dynamic local port and allowlisted parent origin.
- response-word success serializer is implemented.
- allowed_origins is for the local XHR Origin; allowed_parent_origins is for the Almas page Referer.
- Python CI is green with 45 tests. There is still no production EditWordDocument handler or LibreOffice integration.

### Next autonomous work

1. Continue the request-lifecycle workflow around LoadDocument helper calls and event-sink slot mapping.
2. Resolve the DeleteTempRAW caller through unit initialization/finalization tables or indirect references.
3. Finish image/print registry value mapping and temp cleanup helper semantics.
4. Keep all conclusions evidence-tagged: the long-lived XHR is confirmed, but the exact Word close callback that releases it and the parent page's final Almas POST still need proof.
5. Translate only confirmed contracts into the native Linux bridge and LibreOffice integration.


### Request/response DOC evidence

Pcap workflow #4 (run 43710628491, artifact 14159604189) confirms the returned application/msword document differs from wordBody. Input size is 872,960 bytes; the response capture decodes to 874,957 bytes with 68 Base64 characters missing (51 decoded bytes), giving an estimated complete size of 875,008 bytes (+2,048). The OLE header's first-directory-sector pointer changes from 1698 to 1702 at offset 48. Full-file equality is not authoritative because the response capture is incomplete.


### Dispatch address clarification — 2026-11-15

Use this exact naming in future traces: public/exported TEmwatMethod.Invoke = 0x0046C9E0 (VMT slot +0x0C); inner dictionary/XML helper = 0x0046C82C (433 bytes; TD32 symbol says Invoke). The wrapper calls the helper at 0x0046CA67, then the subclass PerformMethod at VMT slot +0x10 / callsite 0x0046CA88. Do not describe 0x0046C82C as the public service dispatch entry.


## Latest verified continuation — 2026-11-15

- The captured `EditWordDocument` exchange now has a dedicated gap-aware report at `docs/PCAP-EDITWORD-DOCUMENT-ROUNDTRIP.md`. The response is a successful `response-word` envelope containing Base64 `application/msword` data. It differs from the submitted DOC in the intact prefix, but 17 TCP sequence gaps (68 bytes) prevent a full-file comparison.
- The native protocol module includes a bounded `serialize_word_document_response` helper and synthetic tests. This is not yet wired to a production `EditWordDocument` handler or LibreOffice.
- Latest verified CI snapshots: Python bridge run #42, 45 tests passed; native core run #104, normal tests 4/4 and sanitizer tests 4/4.
- A separate `.github/workflows/analyze-recovery-store.yml` workflow is being executed to trace every `TfrmShowAutoSaveFiles` / `TfrmSendLog` procedure, callers, callback references, resources, and recovery-related embedded strings. Treat results as pending until run #2 artifact is checked.
- Existing analysis branches remain independent: request parameters, PCAP timing, registry settings, Word event sink, wait/COM, filename normalization, Word lifecycle, native core, and Python bridge.


## Recovery branch update — 2026-11-15

- Recovery form workflow run #2 (`43715017039`) completed successfully; artifact `14162835454`.
- The form is `TfrmShowAutoSaveFiles` in module `uSendLog`; its separate Word Automation lifecycle is not the main editor's `TWordViwer` lifecycle.
- Recovered literals: `*.easz` at `0x005EC49C` is passed from `lslFilesDblClick` to helper `0x004043BC`; `.easd` at `0x005EBD3C` is used in string construction inside `Delete`. Their exact roles remain under analysis.
- Autosave helpers identified: `euGetAutoSavePass` (`0x00456B78`), `DoClearOldAutoSaveFiles` (`0x00456C0C`), `euClearOldAutoSaveFiles` (`0x00456C98`), and path/temp helpers under `Emwat.Sys`. The path/helper workflow run #2 (`43715620696`) is in progress; do not treat its results as final yet.
- See `docs/RECOVERY-STORE-ANALYSIS.md` for confirmed evidence and unresolved items.


## Recovery path workflow run #2 — verified

- `analyze-recovery-paths.yml` run #2 (`43715620696`) succeeded; artifact `14162601983`.
- `0x004043BC` is `TDirectory.GetFiles`; the UI and old-AutoSave cleanup both enumerate `*.easz`.
- `0x004026B4` is `DeleteFileW`; the cleanup loop passes aged matching file paths to this API.
- Local AppData helper uses `SHGetSpecialFolderLocation(CSIDL 0x1C)` and `SHGetPathFromIDListW`. Exact `.easz` root still unknown.
- `euClearOldAutoSaveFiles` compares an age result with `0x18`; do not call it 24 days until the age helper confirms Delphi `TDateTime` units.
- Run #3 (`43715933101`) extends traces for the age, password-read, path-construction, and process-cleanup helpers.


## New confirmed recovery and request-schema findings — 2026-11-15

- Recovery path workflow run #4 (`43716283296`) confirms `euGetWinTempPath` calls `kernel32!GetTempPathW` (`0x004027F8`); `euGetTempFileName` appends `temp-emwatASwf\\`. The AutoSave store is `%TEMP%\\temp-emwatASwf\\*.easz`.
- Recovery password helper `euGetAutoSavePass` calls `GetUserNameW`; it returns the Windows account name, with fallback `@25*gamsign*25@` if the API fails.
- Cleanup age is explicitly measured with `HoursBetween(Now, FileDateToDateTime(FileAge(path)))`; threshold is 24 hours, then `DeleteFileW`.
- Recovery `Delete` handler passes selected item path and temp root to `euResetMemory`, then constructs an additional path with `.easd`; exact file transformation is pending. Run #5 (`43716527945`) traces `euResetMemory` internals and object pointers.
- Added `docs/EDITWORD-REQUEST-SCHEMA.md`: one captured request has a Base64 XML `wordConfig` with 180 fields (including 20 repeated signer slots across seven field families) and a Base64 legacy DOC/OLE `wordBody`. Sensitive field values were not copied.
- Word event-sink workflow run #8 (`43716384031`) fixes an event-callback extraction regex that previously failed to match the actual table pointer format; callback target tracing is now running.


## Native protocol implementation update — 2026-11-15

- Added `python/src/emwat_linux/word_config.py` to parse the inner Base64-encoded `word-document` XML separately from the outer EMWAT method envelope.
- Parser preserves field order, duplicate IDs, per-field attributes, opaque field text, settings, permission strings, optional-attribute content, and requested MIME types. It rejects invalid Base64, non-UTF-8, DTD/entities, oversized input, and malformed field structures.
- New tests cover the captured shape without including customer letter values.
- Python bridge CI run #44 (`43716641854`) passed **53 tests**. The preceding intermediate commit run #43 also passed 45 tests.
- This parser is not yet connected to a production EditWordDocument handler or LibreOffice adapter.


## Event table interpretation correction — 2026-11-15

The 20 addresses extracted from `0x00627B74` are not Word event callback pointers. Run #9 (`43716905570`, artifact `14162568118`) decoded them as server error strings (`Err_20000`, `Request XML is invalid.`, `Can not open document.`, `Temp path not Found.`, etc.). The earlier callback-table interpretation is retracted. Workflow run #10 now extracts this as an error map. The main viewer's `BeforeSave` registration at `0x004CD154` remains confirmed independently from `OnTmrAutoSave`.


## Recovery archive password correction — 2026-11-15

Do not treat the Windows username or `@25*gamsign*25@` as the confirmed `.easz` archive password. `euGetAutoSavePass` returns the account name (or fallback) and `DoClearOldAutoSaveFiles` concatenates it with `@25*gamsign*25@`, but the exact archive consumer is unresolved. The recovery `Delete` path constructs a `Sevenzip.T7zInArchive` object; `euResetMemory` passes `[redacted candidate string]` to virtual slot `+0x44` when its optional password string is null. The exact slot/property mapping and archive open/extract sequence remain pending. See `docs/RECOVERY-STORE-ANALYSIS.md`.

## EditWordDocument request adapter — 2026-11-15

- Added `python/src/emwat_linux/editword_request.py` with `parse_editword_request(MethodCall)`: validates the method name and required parameters, parses Base64 `wordConfig`, decodes Base64 `wordBody` to opaque document bytes, preserves `signData` text and extra parameters, and enforces size limits.
- It deliberately does not assume `signData` is one Base64 blob; the inner config declares concatenation and per-field encoding.
- Python bridge CI run #46 (`43717259882`) passed **58 tests**. This adapter is not yet wired into a production method handler or office engine.

## Word error map — 2026-11-15

- Event/error workflow run #11 (`43717625474`), artifact `14162998865`, decoded the full pointer list in the server metadata block. It contains `Err_20001` XML-invalid, `Err_20002` empty document, `Err_20003` Word connection, `Err_20004` document open, `Err_20005` signature insertion, `Err_20006` missing twin field, `Err_20007` temp path, `Err_20008` scan failure, `Err_Ignore` user cancellation, `Err_20010` image load, `Err_20016` Excel connection, `Err_20017` workbook open, and `Err_20018` missing user-local folder.
- The same block includes log-level labels and Persian AutoSave interval labels. See `docs/WORD-ERROR-MAP.md`.
- Important: this is a string/error map, not a Word COM callback table. The live BeforeSave registration remains separately confirmed at `0x004CD154`.

## Recovery / AutoSave findings — 2026-11-15

The recovery subsystem now has a dedicated analysis report: `docs/RECOVERY-STORE-ANALYSIS.md`. Two additional recovery-path runs (#9 and #10; artifacts `14163436366` and `14163367757`) traced the SevenZip reader class. `euResetMemory` (`0x00456F00`) calls a helper named `CreateOutArchive` and passes the fallback password `[redacted candidate string]` through virtual/interface slot `+0x44`. The call sequence strongly aligns with `T7zInArchive.SetPassword` → `OpenFile` → `ExtractTo`, but the slot-to-method mapping remains unproven. `T7zInArchive.SetPassword` (`0x00453860`) stores the string at `+0x58` and invokes an extraction-style interface call with a callback-like helper. The username / `@25*gamsign*25@` value returned by `euGetAutoSavePass` belongs to a separate cleanup/logging path and is not established as the recovery archive password.

The reader exposes archive open, item-query and extraction methods. Do not yet name the `euResetMemory` path arguments as a proven OpenFile/ExtractTo pair: VMT slots `+0x0C` and `+0x3C` still need exact mapping. The `.easd` file's content and lifecycle, the SevenZip archive variant, and the writer-side `.easz` creation settings remain unresolved. Continue from `docs/RECOVERY-STORE-ANALYSIS.md`; do not repeat the completed class-method trace.


## Latest continuity checkpoint — 2026-11-15

### Verified since the previous handoff

- Python bridge CI run `43721449170` succeeded with **69 tests**. The close-driven coordinator and EditWordDocument domain-service tests cover close without explicit Save, separate modification/save callbacks, cancellation, sanitized adapter failures, and rejection of non-byte output.
- New engine-neutral files: `office_adapter.py`, `document_coordinator.py`, and `editword_service.py`. They model request normalization → open → track modifications and engine saves independently → wait for user close → export final bytes. They are not a LibreOffice implementation. `editword_handler.py` now adapts the service to the XML dispatcher and uses the observed success serializer, but the factory is not yet registered in the application.
- `EditWordDocument` request normalization exists, including Base64 document decoding and conservative preservation of signData as opaque text.
- Heartbeat response and init-script generation are implemented against the captured exchange; production allowlists must still be configured.
- Recovery analysis identifies `T7zInArchive` as the reader wrapper relevant to recovery. Its SetPassword implementation at `0x00453860` stores the supplied Unicode password at instance offset `+0x58` and invokes an extraction-style interface call with a callback-like helper. `euResetMemory` supplies `[redacted candidate string]` to virtual/interface slot `+0x44` when its optional password is absent and the flag selects the fallback. The likely SetPassword → OpenFile → ExtractTo mapping remains unproven. Do not substitute the Windows username or `@25*gamsign*25@`, which belong to a separate cleanup/logging path.
- The reader exposes archive open, item metadata and extraction methods. Exact standard archive format, euResetMemory path-slot VMT mapping, .easd contents, and writer password callback remain unresolved. `T7zOutArchive.SetPassword` is a no-op stub; writer callback tracing is a separate task.
- Word error strings were decoded and documented separately from the unresolved COM event dispatch map. Do not interpret the error string table as event callback metadata.

### Active parallel jobs at handoff

- Recovery SevenZip plugin-focused workflow: run `43719323732`, completed successfully, artifact `14164146310` inspected.
- Recovery path/helper workflow: run `43719180035`, still in progress at the SevenZip reader/writer trace step.

Inspect their status and artifacts before starting duplicate work. If a job is still active, continue the independent native implementation track rather than waiting idle.

### Immediate next actions

1. Inspect the two active recovery artifacts; focus on T7zPlugin construction, VMT dispatch mapping, archive writer password callback, and the euResetMemory call chain.
2. Keep the native OfficeAdapter/DocumentCoordinator separate from HTTP. Next implement a concrete LibreOffice UNO adapter behind the protocol only after the lifecycle event contract is clear enough to test.
3. Connect the production EditWordDocument handler to request parsing, session coordination, and the observed response-word serializer only when a real office adapter exists; do not return the input bytes as a fake successful document.
4. Continue tracing Word BeforeClose/BeforeSave → worker completion → response WriteContent and correlate with the approximately 54.56-second capture delay. Do not claim the close-time callback is proven.
5. Keep docs/PROJECT-STATUS.md, docs/LINUX-NATIVE-IMPLEMENTATION-PLAN.md, docs/RECOVERY-STORE-ANALYSIS.md, and this handoff synchronized as evidence changes.



### Follow-up: request-to-session service verified

- `EditWordDocumentService.process(MethodCall)` now normalizes the request and invokes the coordinator. It generates a local random session ID and never reads the HTTP `invoke` nonce.
- Office adapters must report document modifications and engine-save events separately. A save records a revision but does not release the waiting request; close triggers export.
- Latest verified CI: run `43719841339`, success, 66 tests.


### SevenZip plugin analysis result

Run `43719323732` completed successfully (artifact `14164146310`). New facts:

- `T7zPlugin` has constructor, destructor, and a shared `CreateObject` method. Both `T7zInArchive.GetInArchive` and `T7zOutArchive.GetOutArchive` call that shared factory.
- `euUnArchive` directly constructs the plugin wrapper using global `0x0062A824`; `euResetMemory` instead calls `CreateOutArchive` (`0x00452BBC`) with a 16-byte global-derived value and the literal module name `7z.dll`.
- `CryptoGetTextPassword2` calls helper `0x00404734`, resolved as the RTL TObjectList constructor; its class pointer comes from global `0x0062FBB8`, and the list is stored at object offset `+0x2C`. This does not identify the writer password value/provider.
- `T7zOutArchive.SetPassword` is a no-op stub. `T7zInArchive.SetPassword` stores its string at `+0x58` and invokes an extraction-style interface call with a callback-like helper, but no raw static pointer to this method was found. Therefore, the mapping from `euResetMemory` slot `+0x44` to that setter remains a strong candidate, not a proven binding.
- Detailed update is in `docs/RECOVERY-STORE-ANALYSIS.md`, section 16.


### Latest coordinator verification

- Python bridge run `43720329600` passed **66 tests** after adding an initialization-event guard. Writer/config initialization events do not mark the document dirty or record a user save; only callbacks after OPENED affect the session state.
- Recovery path workflow `43719180035` completed successfully; artifact `14164088249` was inspected. Plugin follow-up run `43720247793` completed successfully; artifact `14164382428` was inspected for the `euUnArchive` caller path.


### Recovery path workflow #10 result

Run `43719180035` succeeded; artifact `14164088249` was inspected. Additional evidence:

- `T7zInArchive.SetPassword` stores the password at `Self+0x58` and invokes an extraction-style interface call with a callback-like helper; it does not simply forward the string as a COM setter.
- `PrepareOperation` reads `Self+0x58` and handles callback/context fields at `+0x50/+0x54`. The explicit `CryptoGetTextPassword` and `SetPasswordCallback` methods are stubs.
- The three euResetMemory dispatches (+0x44 password, +0x0C path, +0x3C path) align by signature and behavior with SetPassword → OpenFile → ExtractTo. Treat this as the leading hypothesis, not a proven VMT mapping.
- Cleanup imports are now resolved: `TDirectory.GetFiles` enumerates `*.easz`; FileAge/FileDateToDateTime/Now/HoursBetween implement the 24-hour threshold; DeleteFileW deletes older files.
- Detailed update is in `docs/RECOVERY-STORE-ANALYSIS.md`, section 17.


### Separate euUnArchive path result

- Plugin workflow run `43720247793` succeeded; artifact `14164382428` inspected.
- `euUnArchive` (`0x00456DFC–0x00456EFF`) is the only direct bounded caller of the `T7zPlugin` constructor in this scan. It uses global `0x0062A824`, then calls object/interface slots `+0x28`, `+0x10`, and `+0x18` while iterating paired collection-like inputs.
- This is separate from `euResetMemory` → `CreateOutArchive` and its `+0x44/+0x0C/+0x3C` sequence. The `euUnArchive` slot meanings and archive direction remain unresolved; do not use this path to infer the .easz recovery contract.
- Full trace: `docs/RECOVERY-STORE-ANALYSIS.md`, section 18.


### Dispatcher adapter result

- Added `python/src/emwat_linux/editword_handler.py`. It adapts the domain service to the XML dispatcher and serializes successful final bytes using the observed `response-word` envelope.
- A cancellation response factory is mandatory and injected; cancellation HTTP semantics are not guessed.
- The factory is not registered in the running application yet. Registration waits for a real LibreOffice OfficeAdapter and captured cancellation behavior.
- Latest Python CI: run `43721322012`, success, 69 tests.


- Concrete OfficeAdapter implementations must isolate handles/callbacks per document and support concurrent sessions because the loopback bridge serves requests concurrently. The protocol contract now states this explicitly; CI run `43721449170` passed 69 tests.


### Active base-class VMT analysis

- New optimized workflow run `43721583502` is indexing `T7zArchive` separately from `T7zPlugin`/`T7zInArchive`/`T7zOutArchive`, to avoid tracing every inherited method as a duplicate. It also traces target `0x00453950` and VMT/typeinfo references.
- Earlier broad run `43721251511` has now completed successfully; artifact `14164434028` was inspected. It indexes `T7zArchive` base-class procedures including constructor `0x0045392C`, `GetClassId` `0x00453950`, and handler/library-property helpers. The optimized run `43721583502` remains active at its class-index step.


### Base-class index result — 2026-11-15

- Broad plugin workflow run #3 (`43721251511`) completed successfully; artifact `14164434028` was inspected.
- The base class `T7zArchive` is now indexed separately. Constructor `0x0045392C` writes its UnicodeString argument to `Self+0x44` and sets a Boolean at `Self+0x40` according to whether the string is nonempty.
- `GetHandlerProperty` (`0x00453A54`) copies the 16-byte handler-property record at `Self+0x18`. `GetClassId` (`0x00453950`) initializes the base object, resolves a handler using the stored name, and copies a 16-byte property record from global `0x0062A820` into `Self+0x18`.
- These are object-field offsets, not proof of the virtual dispatch slot numbers used by `euResetMemory`. Keep the +0x44 dispatch mapping as the leading hypothesis until the interface/VMT layout is recovered.
- Optimized workflow run #4 (`43721583502`) is still in progress, indexing the class family and related interface/type metadata.


### Close-callback race hardening — 2026-11-15

- `DocumentCoordinator` now guards modification/save callbacks with an `RLock` and disables them immediately after `wait_for_close` returns, before final export. This prevents delayed office-engine events from mutating a finalizing/returned session.
- New regression coverage invokes both callbacks during export and again after return; the revision and saved revision remain unchanged. Python CI run `43722184809` passed **70 tests**.

### SevenZip interface/VMT resolution branch — 2026-11-15

- The completed optimized class-index workflow run `43721583502` succeeded; artifact `14165155588` was inspected.
- The next workflow run `43722345225` now invokes both `resolve_delphi_vmt_slots.py` and `trace_delphi_interfaces.py` for the SevenZip class family. The resolver target list and interface scanner were extended to include `T7zArchive`, `T7zPlugin`, `T7zInArchive`, `T7zOutArchive`, and SevenZip archive/stream interface RTTI names.
- This is specifically intended to resolve whether `euResetMemory`'s interface slots `+0x44/+0x0C/+0x3C` map to the reader wrapper's password/open/extract methods. Do not treat the mapping as proven until the generated interface table is inspected.


### Cancellation callback edge case — 2026-11-15

- Review found that callback detachment originally occurred only on the normal-close branch. The coordinator now disables callbacks immediately after `wait_for_close` returns, before handling either `CLOSED` or `CANCELLED`.
- Added a regression test proving delayed modify/save notifications after cancellation are ignored. Python CI run `43722805637` passed **71 tests** (4.49 seconds).


### `euResetMemory` custom interface identity — 2026-11-15

- SevenZip plugin run `43722345225` succeeded; artifact `14165136040` was inspected.
- `CreateOutArchive` constructs `T7zInArchive` (VMT `0x004525B0`) and returns `Self+0x70`. The class interface table has seven entries; entry 6 has `IOffset=0x70`, IID `022cf785-3ece-46ef-9755-291fa84cc6c9`, and VTable `0x00452420`.
- This proves that `euResetMemory` dispatches `+0x44`, `+0x0C`, and `+0x3C` on this custom interface. The proposed mapping to `SetPassword`, `OpenFile`, and `ExtractTo` is still a hypothesis pending direct vtable slot decoding.
- The next run expands interface vtable output to 20 entries (through `+0x4C`) to expose those targets.


### Word COM metadata and close callback cross-check — 2026-11-15

- Methods BPL run `43722341778` (artifact `14165431103`) shows `WordAppDocumentBeforeClose` (`0x004CCBBC`) calls `0x004BCA88`; the same helper is used by `GetCaptionItemFont`. Direct caller of `0x004CCBBC` remains `FillImgFldsForPrint` (`0x004CCF8F`). No close-time HTTP/response path was found in this body.
- Word event-sink run `43722990625` (artifact `14165586257`) confirms server-data records begin with Word's `ApplicationClass` CLSID (`000209FF`) and `DocumentClass` CLSID (`00020906`) and include known ApplicationEvents/ApplicationEvents2 IIDs. These are generated OLE metadata, not a callback address map.
- Active follow-ups: SevenZip interface vtable through slot `+0x4C` (`43722990639`), RTL helper disassembly for Word server data (`43723423283`), autosave Delete caller (`43723328264`), Word lifecycle (`43722990611`), and broad Methods BPL trace (`43722990637`).


### SevenZip `OpenStream` slot mapped — 2026-11-15

- From artifact `14165136040`, custom interface slot `+0x0C` points through thunk `0x004522E9` to `T7zInArchive.OpenStream` (`0x00452FDC`). `IInStream` is the method's return type; the method accepts an archive-path UnicodeString and creates the stream.


### All three `euResetMemory` SevenZip slots mapped — 2026-11-15

- Plugin run `43722990639` succeeded; artifact `14165676602` includes 20 interface vtable slots.
- On custom interface vtable `0x00452420`: `+0x0C` forwards to `OpenStream(UnicodeString) -> IInStream` (`0x00452FDC`); `+0x3C` forwards to `SetPassword(UnicodeString)` (`0x00453860`); `+0x44` forwards to virtual constructor `T7zArchive.$bctr` (`0x0045392C`).
- `SetPassword` stores its string at `Self+0x58`, creates an extraction callback interface from `Self+8`, and invokes `IInArchive.Extract` (`+0x1C`) with `indices=NULL`, `numItems=-1`, `testMode=0`. This is an all-items archive operation; callback output semantics are not yet proven.
- The autosave Delete trace shows `euResetMemory` takes the selected `.easz` path as its first UnicodeString, a second string from helper `0x0044A998` as the `SetPassword` argument, and a null optional third string. Two true Boolean flags select the constructor fallback `[redacted candidate string]`. The meaning of the second string and callback output path remain open. `ExtractTo` is a separate wrapper, not one of the three direct slots.


### SevenZip extraction callback comparison — 2026-11-15

- `T7zInArchive.SetPassword` uses callback type-info reference `0x0045391C`, creates the callback from `Self+8`, and invokes the underlying archive-interface slot `+0x1C` with `indices=NULL`, `numItems=-1`, `testMode=0`.
- Separate `T7zInArchive.ExtractTo` uses type-info reference `0x00453850`, stores callback/context at `Self+0x50/+0x54`, and invokes the same underlying slot with `testMode` selected by its Boolean parameter.
- Both are all-items operations, but they use different callback types. The latest plugin run `43723896564` is tracing those type-info blocks and pointer references; output destination remains unproven.


- The internal archive-interface slot `+0x1C` is identified as `IInArchive.Extract`: the wrapper methods `ExtractItem` and `ExtractTo` also call this slot with their item/test-mode arguments. Thus `SetPassword` in the recovery path issues an all-items Extract request through its own callback. The callback's output destination remains unresolved.


### Autosave Delete caller argument types — 2026-11-15

- Run `43723328264` / artifact `14165058222` traces `TfrmShowAutoSaveFiles.Delete` (`0x005EB828`). The selected archive path is copied from the selected item record's `+0x20` field into `[ebp-4]` via `UStrLAsg`; this is the first `euResetMemory` argument.
- `[ebp-8]`, the second argument, is produced by helper `0x0044A998` and passed to `SetPassword`. Its source semantics remain unknown.
- The call passes `ECX=0` and two stack Boolean flags set to 1, selecting the `[redacted candidate string]` constructor fallback.
- After `euResetMemory`, the caller invokes `0x004563A8` with the same two strings, then `0x004565DC` and `0x004555D8`. These helpers are the next targets for identifying the `.easd` output path and cleanup.


### Latest verified work — 2026-11-15

- Recovery/SevenZip artifact 14166161804 (run 43723896564) shows T7zInArchive.SetPassword initiates IInArchive.Extract for all items through a callback; it is not merely a password-field assignment. PrepareOperation has distinct callback/context and stored-string paths. Output stream destination remains unresolved.
- ExtractTo uses callback type-info 0x00453850; SetPassword uses 0x0045391C.
- Word lifecycle run 43722990611 completed successfully; artifact 14165369436 resolved registry thunks: 0x404414 WriteInteger, 0x404424 WriteBool, 0x40441C ReadInteger, 0x40442C ReadBool, and 0x404454 ValueExists.
- Detailed findings were appended to docs/RECOVERY-STORE-ANALYSIS.md sections 21–22 in commit d17a801d0d02f12e4a6b286af7aa1e21a9e691ac.
- Recovery-path run 43724386278 was still in progress at the last check. Keep the .easd destination, archive password semantics, and Almas close-time registration protocol unresolved until direct evidence is available.


### Current recovery reverse-engineering state — 2026-11-15

- Run 13 (`43724386278`, artifact `14165938809`) completed. `0x0044A998` is `Emwat.Sys.MyMessageDialog`, called by the recovery Delete handler to produce the string passed as `euResetMemory`'s second argument; it then reaches `T7zInArchive.SetPassword` through interface slot `+0x3C`. Exact dialog semantics and the returned string's relation to the archive password are not proven.
- Do not confuse that helper with `euGetAutoSavePass` (`0x00456B78`), a separate `GetUserNameW` helper used in cleanup/logging.
- Recovery Delete applies `FixDirectionInFarsiNumericMode` (`0x004563A8`) to a path-like value before constructing a `.easd` path; extraction destination/content remains unresolved.
- Callback-contract analysis is now a separate workflow. It traces callback RTTI, `+0x44` dispatch target, and the archive extraction callbacks. See `docs/RECOVERY-STORE-ANALYSIS.md` section 23 and commit `b753390bd421047e22d072b1012d9be3d829015a`.


- Follow-up correction commit `6ed0f8f490515f548065a39afe546c9a6838c660` fixes the recovery Delete call-site description: `0x004563A8` receives only the selected `.easz` path (with Boolean flags false) and produces the normalized path-like string used to construct the `.easd` path. It is not passed the password string.


### Latest callback-contract findings — 2026-11-15

- Callback-contract run 2 (`43725294172`, artifact `14165994624`) confirms `T7zArchive.$bctr` at `0x0045392C` stores its string at `Self+0x44` and sets `Self+0x40` according to whether it is nonempty. The recovery fallback `[redacted candidate string]` is passed to this constructor, not to `SetPassword`.
- The `MyMessageDialog` result is a separate string passed to `T7zInArchive.SetPassword` via slot `+0x3C`.
- Callback references `0x00453850` and `0x0045391C` contain the same `IArchiveExtractCallback` IID. Their construction contexts differ, but they implement the same COM callback interface.
- `PrepareOperation` has distinct branches using `Self+0x3C`, `Self+0x50/+0x54`, and `Self+0x58`; exact property mapping and final output destination remain open. See `docs/RECOVERY-STORE-ANALYSIS.md` sections 24–25.
- Follow-up workflow run 3 is queued to resolve the remaining non-TD32 slot targets and dialog strings.


## 2026-11-16 — ادامه موازی: Twin Field، Custom Properties و مقصدهای مقداردهی Word

### شواهد تأییدشده جدید

- اجرای `43811074616` موفق شد؛ artifact شامل 41 فایل procedure/callers/pointer refs/strings بود.
- اجرای helper pipeline `43812127854` موفق شد و delimiter ثابت `0x004D1768` را به `†` (U+2020) decode کرد.
- `AddCustomDocPropertiesToDic` نام propertyهای سفارشی سند را با اولین dagger بررسی می‌کند. دو بخش غیرخالی، رکورد `TXmlWordConfigTwinField` می‌سازند؛ حالت بدون delimiter یا یک سمت خالی، به `TXmlWordConfigField` تکی برمی‌گردد.
- dictionaryهای viewer در offsetهای `+0x68` و `+0x6C` به‌ترتیب با `TXmlWordConfigField` و `TXmlWordConfigTwinField` مرتبط‌اند. متدهای `0x004D531C` و `0x004D68D4` generic Remove هستند، نه setter.
- `FillImageField` در `0x004BC30C` فقط image insertion نیست: logهای داخلی دو مقصد مقداردهی را تأیید می‌کنند: `CustomDocumentProperties[index]` و `Field.Result.Text`. مسیر دوم وضعیت lock فیلد را بررسی می‌کند.
- نام‌های ویژه `LetterRegistrationDate`، `LetterRegistrationNo` و `ProduceDate` در شاخه‌ای وابسته به flag داخلی `viewer+0xF0` پردازش می‌شوند.
- Writer catalog اکنون نام Custom Document Properties را بدون خواندن مقدارشان گزارش می‌کند.
- `parse_word_field_identifier` در Python اولین dagger را جدا می‌کند و ورودی ناقص را single نگه می‌دارد.

### CI تأییدشده

- Python bridge run `43812324657`: 87 تست پاس، یک تست UNO اختیاری skip.
- LibreOffice UNO run `43811929904`: 8/8 تست پاس؛ fixture یک UserDefinedProperty ساختگی اضافه می‌کند و فقط نام آن را از catalog می‌گیرد.
- Word custom-property helper analysis run `43812127854`: success.
- Word field pipeline run `43811074616`: success.

### کارهای موازی بعدی

1. بررسی دقیق قرارداد رکورد `TDocumentCProperty` و رابطه indexهای آن با collection واقعی Word CustomDocumentProperties؛ helperهای `ContainsValue` و `SetItem` اکنون شناسایی شده‌اند.
2. اعتبارسنجی رفتار معکوس‌سازی componentهای `FindWindowExtd` با مقدار واقعی مجاز/ناشناس‌سازی‌شده؛ الگوریتم slash/hyphen و reverse order اکنون از disassembly استخراج شده، اما نمونه واقعی برای تعیین قاعده locale لازم است.
3. تکمیل معنای `FillPrintOptionForm` در `0x004D1B30` و نگاشت collectionهای `Receivers`/`ReceiverDeps`/`ccReceivers`/`ccReceiverDeps` به recipient/CC نهایی.
4. پس از تکمیل این helperها، مدل Writer را به سه مقصد مستقل گسترش بده: custom properties، text-field result، و image anchors؛ mapping واقعی 180 شناسه را بدون template واقعی حدس نزن.
5. مسیر close/XHR و پاسخ cancel هنوز end-to-end با Almas تأیید نشده است؛ از پاسخ ساختگی یا اعلام ثبت قطعی خودداری شود.


### تکمیل مقصد Custom Document Property در Writer

- ماژول `python/src/emwat_linux/writer_properties.py` اضافه شد.
- `set_custom_document_property(document, property_name, value)` فقط property موجود را با نام دقیق به‌روزرسانی می‌کند؛ اگر نام وجود نداشته باشد `KeyError` می‌دهد و property جدید ایجاد نمی‌کند.
- تابع مقدار قبلی property را نمی‌خواند؛ catalog همچنان فقط نام‌ها را inventory می‌کند.
- تست UNO واقعی روی property ساختگی نشان داد Writer property را به‌روزرسانی می‌کند.
- CI پس از این تغییر: Python run `43813400123` = 91 تست سبز (یک skip اختیاری)، UNO run `43813378877` = 8/8 سبز.
- یک workflow برای index کردن تمام TD32 symbolهای `TDocumentCProperty` و `TXmlWordConfigField/TwinField` اضافه شده است. نسخه نخست script خطای آرگومان TD32 داشت؛ اصلاح شد و اجرای جدید در حال بررسی است. خطاهای قدیمی `43813052058` و `43813063493` مربوط به نسخه‌های پیش از اصلاح هستند و نباید به‌عنوان وضعیت نهایی تلقی شوند.


### TD32 symbol inventory

- Run `43813303321` completed successfully; artifact `14201306994` indexes 611 procedures whose symbols mention `TDocumentCProperty`, `TXmlWordConfigField`, or `TXmlWordConfigTwinField`.
- New utility `tools/list_td32_symbols.py` produces the index with VA, size, module, and symbol name.
- High-value next procedures now identified:
  - `0x004BFDB0` — `TWordViwer.SetFieldValue`
  - `0x004BFC18` — `TWordViwer.GetXmlFieldInfo`
  - `0x004D3B38` — `TDictionary<UnicodeString,TDocumentCProperty>.Add`
  - `0x004D3D2C` / `0x004D3D3C` — `TryGetValue` / `AddOrSetValue` for document custom properties
  - `0x004D52DC` / `0x004D54E0` — single-field dictionary `Add` / `AddOrSetValue`
  - `0x004D6894` / `0x004D6A98` — twin-field dictionary `Add` / `AddOrSetValue`
- Focused helper workflow now traces these addresses in parallel; run IDs `43813533418` and `43813557802` were created while expanding the target set. Verify the newest run before reporting its outcome.


### قرارداد دقیق GetXmlFieldInfo

- `0x004BFC18` ابتدا dictionary single در viewer `+0x68` را lookup می‌کند؛ در صورت نبود، dictionary twin در `+0x6C` را lookup می‌کند.
- Single record: index در `+4` و field ID در `+8`.
- Twin record: index در `+4`، شناسه اول در `+8` و شناسه دوم در `+0xC`. تابع counterpart طرف مقابل را برمی‌گرداند.
- در صورت عدم تطبیق، index برابر `-1` و flag موفقیت false می‌ماند.
- هدف بعدی trace کردن `SetFieldValue` در `0x004BFDB0` و callsiteهای dictionary Add/AddOrSetValue است تا قرارداد value/index نهایی روشن شود.


### Controller Notify و مسیر finalize سند

- Run `43813684507` موفق شد؛ artifact `14200889822`.
- `TWordViwer.OnControlerNotify` در `0x004BB3B0` پس از اعتبارسنجی state/message، `CostumizeRecAndCC` را اجرا می‌کند، سپس `-1` را همراه document interface به COM slot `+0xDC` می‌دهد و flagها را reset می‌کند.
- بعد از آن دو مقدار از مسیر `FixDirectionInFarsiNumericMode` و `0x00456DFC` عبور می‌کنند.
- `0x005EE82C` در TD32 با نام `TScanDocument.PerformMethod` آمده و `LoadDocument` در `0x004B7724` را فراخوانی می‌کند؛ نام procedure را به‌جای برچسب قبلی TEditWordDocument در مستندات استفاده کن.
- COM slot `+0xDC` هنوز با wrapperهای `TWordDocument.Close` و `Save` تطبیق داده نشده. دو workflow جدید برای مقایسه slotها و decode رشته‌های controller/PerformMethod در حال اجرا هستند: `43814055308` و `43814083027`.
- ثبت نهایی Almas و payload شبکه هنوز اثبات نشده؛ صرفاً این controller-notify sequence با finalize/close-side سازگار است.


### آخرین وضعیت موازی — 2026-11-16

- Python bridge run `43816293635`: **99 تست run، 98 پاس، 1 skip اختیاری**. URL decoder مطابق native رفتار می‌کند: `+` به فاصله و `%2B` به plus تبدیل می‌شود.
- Word custom-property helper run `43816241948`, artifact `14201844295`: `0x004D1B30` تابع `FillPrintOptionForm` است؛ `tokenizedReceivers` و delimiter U+2020 (`†`) تأیید شدند. چهار config key شامل `Receivers`, `ReceiverDeps`, `ccReceivers`, `ccReceiverDeps` هستند.
- LibreOffice integration run `43815592590`: **8/8 سبز**. `LibreOfficeAdapter.apply_custom_property_updates` propertyهای موجود را batch-update می‌کند و text fields را یک بار refresh می‌کند؛ complex DOCX DOCPROPERTY field نتیجهٔ جدید را نشان می‌دهد و خروجی DOC/CFB تولید می‌شود.
- VMT/interface artifact `14201779902` از close-response run `43815900214`، آدرس VMTهای `TEditWordDocument=0x005ED764` و `TScanDocument=0x005ED884` را گزارش می‌کند؛ هر دو parent برابر `0x0046ABA4` هستند. با این حال resolver نتوانست slotهای method را از RTTI تأیید کند.
- VMT candidate مربوط به `TWordDocument` در `0x00412174` نیز unverified است. wrapperهای typed نشان می‌دهند `Get_Saved → interface slot +0xD4`، `Set_Saved → +0xD8`، `Get_Content → +0xDC` و `Save → +0x2B8`. چون callsite در `OnControlerNotify` برای `+0xDC` آرگومان `-1` می‌فرستد، receiver/signature دقیق هنوز حل نشده؛ آن را Save/Close فرض نکن.
- `0x005EE82C` در TD32 با نام `TScanDocument.PerformMethod` دیده می‌شود و pointer reference آن در محدودهٔ VMTهای connector نیز نیازمند تطبیق دقیق است؛ نام کلاس را قطعی به TEditWordDocument نسبت نده.
- مسیرهای باز: قرارداد و callsiteهای `TDocumentCProperty.Add/AddOrSetValue`، معنای دقیق collectionهای Rec/CC، direct `Field.Result.Text`، image anchors، template واقعی Almas و close/XHR ثبت نهایی.



## Autonomous parallel checkpoint — 2026-11-16 09:50 local

### Verified since previous handoff

- Native Base64 field decoder path is resolved: `SetFieldValue(encryption=base64)` → `WideCharToMultiByte` → wrapper `0x004735D0` → orchestrator `0x004738CC` → decoded-length helper `0x00473608` + quartet decoder `0x00473700` (lookup table `0x00627F98`). The Linux field decoder no longer strips whitespace; standard complete quartets and one-/two-character padding are tested.
- Python bridge workflow `43818155017`: 99 tests passed, 1 skipped.
- `TXMLFieldType` metadata is mapped: VMT `0x004751E4`, interface offset `0x50`; typed getters/setters exist for Id, Mimetype, Encryption, Separator, Concater, ParamId, IsNew.
- Viewer-side VMTs: `TDocumentCProperty` `0x004B05A8` / size `0x1C`; `TXmlWordConfigField` `0x004B068C` / size `0x10`; `TXmlWordConfigTwinField` `0x004B0774` / size `0x18`.
- COM wrapper dispatch: `Get_Saved +0xD4`, `Set_Saved +0xD8`, `Get_Content +0xDC`, `Save +0x2B8`. `OnControlerNotify` uses `+0xDC`, not Save/Close.
- Event record callbacks are BeforeSave (`0x004CD154`), conditional BeforePrint/LoadOptions (`0x004D00AC`), NewDocument (`0x004CD54C`), WindowActivate (`0x004CD9C0`). Main-editor BeforeClose registration is still unproven.
- Controller-notify has a second paired-stream branch that prepares `.easd` and `.easz` paths and calls `euUnArchive` through the SevenZip plugin. Its relationship to recovery Delete and final Almas registration is not yet established.

### Current parallel workflow snapshot

- `43817445960` — Word lifecycle analysis; in progress, 18/37 top-level steps completed at snapshot.
- `43818082486` — XML twin-field metadata/property trace; in progress, first parallel trace step running.
- `43818434937` — controller notification dispatch trace; queued at snapshot.

### Remaining critical blockers

1. Resolve `TXmlWordConfigTwinField` and `TXMLFieldType` property consumption to prove `separator`/`concater` semantics.
2. Trace `TEDPController.Notify` (`0x004D2EC8`) into `TWordViwer.OnControlerNotify` and identify the exact notification message activating paired streams.
3. Resolve the exact main-editor close/registration request and response envelope.
4. Obtain an anonymized representative Almas Word template; current installer archive contains no Word-family templates, so visual fidelity and field-to-bookmark mapping remain unverified.

Do not implement guessed `signData` joining or claim end-to-end Almas registration until these traces/template are available.


## Confirmed Word close lifecycle — 2026-11-16

- Main editor close path is the registered `WordAppDocumentBeforeSave` callback at `0x004CD154`, not `WordAppDocumentBeforeClose` at `0x004CCBBC`.
- Callback sets Word `Saved=False` via COM slot `+0xD8`, asks whether to register changes, then invokes the three-argument `_Document.Close` through slot `+0x29C`.
- Dialog mapping: Yes → SaveChanges `-1`; No → SaveChanges `0`; Cancel → event Cancel `0xFFFF` and no close.
- One-/two-/three-argument Close wrappers at `0x0042FF08`, `0x0042FF7C`, `0x0042FFF4` all dispatch to the same COM Close slot `+0x29C`.
- This explains close-triggered registration without a manual Save click. Exact HTTP return envelope and the notification that transfers final bytes to Almas remain unresolved.
- Evidence: lifecycle run `43817445960`, artifact `14203757393`; details in `docs/WORD-COM-INTERFACE-DISPATCH.md` Run 134.


## XML attribute spelling caution

- Native parser-side `TXMLFieldType.Set_Concator` reads the key `concator`; existing request-schema transcription currently says `concater`.
- These are not treated as aliases. Runtime preserves raw attributes; do not normalize or implement concatenation until the raw request is rechecked.
- `Set_Separator` reads `separator`; `Set_ParamId` reads `paramId`.


## Autonomous continuation checkpoint — 2026-11-16 12:xx

### Repository and current scope
- Continue only EMWAT reverse engineering in `meicamghe/EMWAT-Linux`.
- Do not switch to or mix in the separate Winux workstream.
- Current latest analysis note: `docs/WORD-LIFECYCLE-STATIC-TRACE.md`; project status has the latest summary.

### Newly checked artifacts
- Re-opened artifact `14208369288` from successful run `43832553168` (BPL Invoke/VMT analysis).
- Re-opened artifact `14203757393` (large Word lifecycle, class-method, VMT, controller, and AutoSave trace collection).
- Re-opened artifact `14205656649` (service HTTP response and Indy VMT trace collection).
- Re-opened artifact `14206405476` (Word COM event-sink and close decision evidence).

### Important findings and corrections
1. `TEmwatMethod.Invoke` (`0x0046C82C`) walks dictionary key/value pairs. `0x0046E324` is `TPairEnumerator.DoGetCurrent`; `0x0046E3CC` maps to `TPairEnumerator.MoveNext` in VMT RTTI despite a conflicting TD32 decorated label. Raw pointer search found no static reference to `0x0046C82C`; its runtime role is still unresolved. Do not assume it is the request dispatcher.
2. `TEditWordDocument` VMT `0x005ED764` slot `+0x10` points to `0x005EE82C`. This routine reads `wordConfig`, `wordBody`, `letterImages`, `signData`, validates `wordConfig`, and calls `TWordViwer.LoadDocument` at `0x004B7724`. TD32 decorates the target as `TScanDocument.PerformMethod`. `TScanDocument` VMT slot `+0x10` points to `0x005EEB48`, which TD32 decorates as `TFaxDocument.PerformMethod`. Preserve this VMT/symbol mismatch; resolve class registration before renaming.
3. The main editor close behavior is already resolved in earlier artifacts: registered callback is `WordAppDocumentBeforeSave` at `0x004CD154`, with Yes → Close(SaveChanges=True), No → Close(SaveChanges=False), Cancel → event Cancel and leave the document open. `WordAppDocumentBeforeClose` at `0x004CCBBC` is not the main editor close callback.
4. The periodic `OnTmrAutoSave` path sets `OnControlerNotify` as a timer callback and enforces a minimum interval of 10 seconds. Keep this separate from the close-time registration prompt.
5. Service HTTP handler/Indy response writer work is already substantially mapped in existing artifacts. The current public `analysis-input/` directory does not contain `EmwatService.exe`, so a fresh service PE trace cannot run from this checkout unless an authorized analysis copy is added.

### New work committed
- Added `.github/workflows/analyze-emwat-dispatch-crosswalk.yml` with parallel service/BPL/Word jobs; service job now reports missing input cleanly.
- Expanded target lists to cover dispatch helpers, Word lifecycle callbacks, field mapping, and SilentSave.
- Added `docs/WORD-LIFECYCLE-STATIC-TRACE.md` and linked it from README.
- Updated `docs/PROJECT-STATUS.md`.
- Latest known commits at checkpoint: `bfc6654ca90e3ddf4edda9e0dc0edb07635f4bd5` (status update; latest of the above batch).

### Do not claim
- Do not claim the newly expanded workflow has passed; its run/artifacts have not yet been verified.
- Do not claim the full service-parser → concrete class → PerformMethod → HTTP response chain is closed.
- Do not infer the exact meaning of the final invoke response or Almas persistence from HTTP 200 alone.

### Next work, in order
1. Resolve XML `class="EditWordDocument"` to the concrete Delphi class/VMT and the `+0x10` method slot; inspect class registration tables, class-name lookup, and RTTI invocation in the BPL and service traces.
2. Trace the request-side method factory/dispatch helper into the VMT call. Keep `TEmwatMethod.Invoke` separate until its runtime caller and role are proven.
3. Connect `TWordViwer.OnControlerNotify` → `Get_Content` → helper `0x00456DFC` to the long-lived HTTP invoke response writer, without assuming that every timer tick is a final registration response.
4. Compare the close-time response payload with the request `wordConfig` and the opaque document bytes, using only synthetic or anonymized data.
5. Update the docs and Python bridge only when the dispatch and response contract is evidenced.


## Latest verified continuation — 2026-11-16

### Successful runs and artifacts
- Run `43867641761`: all 3 dispatch-crosswalk jobs succeeded. BPL artifact `14225499151`, Word artifact `14226866454`; service artifact `14226172178` is an explicit missing-input note only.
- Run `43868190188`: all 3 expanded VMT/Word/service jobs succeeded. BPL artifact `14225224443`.
- Run `43868321797`: controller content unpack job succeeded. Artifact `14226342809`.
- The new service-artifact workflow run `43868531786` and expanded controller archive run `43868705082` were queued at the last check; inspect them before claiming success.

### Important corrections
1. `0x004563A8` is `FixDirectionInFarsiNumericMode`, not a list constructor. The two objects in `OnControlerNotify` are created by helper `0x0040414C` using global/class reference `0x0062F810`.
2. Strings `0x004BB754` and `0x004BB76C` decode to `.easd` and `.easz`. The path at `TWordViwer+0x80` is direction-normalized and these suffixes are appended.
3. SUPERSEDED: the earlier interpretation of output interface slot `+0x28` as assigning `FPassword` was based on an incorrect field/method attribution. Current VMT evidence maps `+0x28` to the progress-callback method; it is not a confirmed password setter.
4. The exact VMT inspection proves `TEmwatMethod` slot `+0x0C` is the shared public Invoke wrapper `0x0046C9E0` (TD32 label `Finalization`); slot `+0x10` is the abstract/error stub `0x00401068`. The wrapper calls the inner dictionary/XML helper `0x0046C82C`, then dispatches the concrete subclass through VMT slot `+0x10`.
5. `TEditWordDocument` inherits `TEmwatMethod`; its VMT slot `+0x10` points to `0x005EE82C`, TD32-decorated as `TScanDocument.PerformMethod`. `TScanDocument` VMT slot `+0x10` points to `0x005EEB48`, TD32-decorated as `TFaxDocument.PerformMethod`. Class resolution and the wrapper-to-subclass VMT dispatch are confirmed; preserve the pointer/name discrepancies.

### New workflows
- `.github/workflows/analyze-emwat-controller-unarchive.yml` expanded to inspect helpers `0x0040414C`, `0x004543C4`, SevenZip class procedures, VMTs, and interface tables.
- `.github/workflows/analyze-emwat-service-dispatch.yml` downloads the preserved artifact `emwat-mainform-invoke-handler` from run `43831365563`, so the service EXE can be analyzed without adding it to the public repo.
- The dispatch crosswalk workflow's YAML path-filter newline bug was corrected; run `43868190188` passed all jobs.

### Next tasks
1. Inspect the latest archive-method workflow artifact for the exact stream class behind global `0x0062F800` and the remaining password callback path.
2. Trace the concrete `TEditWordDocument.PerformMethod` body at `0x005EE82C` through `TWordViwer.LoadDocument`, field updates, and the archive source file.
3. Connect the `.easz` archive output from `OnControlerNotify` to the service invoke response and determine whether it is the close-time commit payload.
4. Trace the final HTTP response serialization/ContentText assignment; do not treat init/heartbeat WriteContent calls as proof of the invoke response.
5. Keep timer-driven `OnControlerNotify`, Word BeforeSave, and the Almas apply-on-close action as separate events until their data flow is linked.


### Service artifact analysis correction
- The preserved artifact `emwat-mainform-invoke-handler` downloaded successfully from prior run `43831365563`; it contains `EmwatService.exe`.
- The first deep service workflow `43868531786` failed because this EXE has no TD32 debug signature. It is not a missing file and not a bad download.
- Service workflow was corrected to use PE disassembly, raw pointer-reference scans, VA context inspection, and string decoding only. It no longer invokes TD32-dependent scripts for the service EXE.
- Corrected run `43868823284` was queued at this checkpoint; inspect its job and artifact before reporting success.
- Keep the EXE out of the public repository; use the preserved workflow artifact as the CI input.


### SevenZip interface correction
- Exact VMT inspection shows `T7zPlugin.$bctr` obtains an interface pointer at `T7zOutArchive` object offset `+0x44`, IID `baa9d5dc-9ff4-4382-9bfd-ec9065bd0125`.
- Through this interface: `+0x10 → AddFiles (0x453F34)`, `+0x18 → SaveToStream (0x454668)`, `+0x28 → SetProgressCallback (0x4547E8)`.
- Therefore do not call `[redacted candidate string]` a confirmed password; it is passed to SetProgressCallback through the observed interface. `SetPassword` exists separately at `0x4547DC`, but is not the mapped target.
- `euUnArchive` passes two TStringList values to AddFiles and a `.easz` UnicodeString to SaveToStream; these do not obviously match the TD32 signatures. The archive direction and exact argument types remain unresolved. Next inspect target method bodies and the wrapper/factory.
- Expanded archive workflow run `43869599848` was queued for those method-body traces at the last check.


### Invoke bridge and XML version contract
- Service artifact `14226099734` confirms the embedded init script POSTs `message.data` to `http://127.0.0.1:$V{myport}?invoke=<random nonce>` and relays `responseText` to the parent frame.
- Service strings and parser traces confirm root `emwat`, attribute `version`, exact numeric version `1`, child `method`, attribute `class`, child `param`, and attribute `name`.
- `0x0047E0EC` is BPL package load; `0x0047E2D4` is package unload. They bracket `ParseMethod`; neither is the concrete method dispatcher.
- The exact request schema is updated in `docs/EDITWORD-REQUEST-SCHEMA.md`; HTTP bridge details are in `docs/HTTP-LOCAL-API-ANALYSIS.md`.


- Artifact `14226742624` confirms `0x0040414C` is the `rtl230.bpl!TStringList.$bctr` import thunk. Both objects passed into `euUnArchive` are TStringList instances. First list receives `TWordViwer+0xA0`; second receives the direction-normalized `TWordViwer+0x80` path with `.easd` appended. The pairwise list loop passes entries to the `T7zOutArchive` interface, then sends the `.easz` path through slot `+0x18`.


### Archive path resolved (Run 148)
- Artifact `14227611377` establishes the output writer path and SevenZip wrapper, but does not prove that the resulting archive is encrypted.
- Interface `+0x10` → `T7zOutArchive.AddFiles` (`0x453F34`): first TStringList value is the source file path (`TWordViwer+0xA0`); second is the archive entry name (base path + `.easd`).
- Interface `+0x18` → `T7zOutArchive.SaveToStream` (`0x454668`): saves to base path + `.easz`.
- Interface `+0x28` → `0x4547E8`: mapped as the progress-callback method. The earlier inference that its input was definitively the writer password is withdrawn. `T7zOutArchive.SetPassword` at `0x4547DC` is a no-op stub. No confirmed writer password value/provider is established.
- Remaining: resolve the output stream and callback semantics, determine actual runtime encryption flags/password source, and capture a synthetic runtime archive if possible. Do not claim encryption or interoperability is validated.


### Confirmed service-to-BPL dispatch correction
- The prior caution that the `TEmwatMethod.Invoke` helper was not the runtime dispatcher is superseded by the public wrapper distinction.
- Service parser extracts `method@class` and `param@name`, resolves `GetClass("T"+className)`, constructs the class, and calls VMT slot `+0x0C`.
- `TEmwatMethod` VMT slot `+0x0C` → `0x0046C9E0` shared wrapper; wrapper calls inner XML/dictionary helper `0x0046C82C` then subclass `PerformMethod` at VMT slot `+0x10`.
- The service-side class lookup and dispatch chain is fully documented in `docs/EMWAT-SERVICE-EXECUTABLE-ANALYSIS.md`; the remaining response serialization and close-time commit link are still open.


- Run 5 artifact `14227002967` confirms `0x004041BC` is the `rtl230.bpl!TFileStream.$bctr(UnicodeString, Word)` thunk. `SaveToStream` constructs the file stream from `.easz` using `0xFF00` (`fmCreate`) and passes it to `SetCompleted` (`0x004546C4`). Thus `.easz` is a real file output, created/truncated by the archive path.


### Word event lifecycle targets
- `OnTmrAutoSave` (`0x004B8A84`) registers WordApp callbacks: BeforeSave `0x004CD154`, NewDocument `0x004CD54C`, WindowActivate `0x004CD9C0`, BeforePrintBGPrint `0x004CE030`/`0x004D00AC`.
- `WordAppDocumentBeforeSave` can set Cancel=-1 when viewer state is not ready and can show a three-choice dialog for an unsaved document. One choice cancels. Do not assume this is the Almas commit event.
- `WordAppDocumentBeforeClose` (`0x004CCBBC`) calls `0x004BCA88`; `SilentSaveEmwatDoc` (`0x004D23D8`) builds two TStringLists and calls `0x004AEBBC`. These are key next targets.
- A complete-range rerun is in progress to trace OnTmrAutoSave, OnControlerNotify, BeforeClose, BeforeSave, SilentSaveEmwatDoc, and the two helpers. See `docs/WORD-LIFECYCLE-STATIC-TRACE.md` Run 150.


- `LoadDocument` calls `OnTmrAutoSave` with the document path at `0x004B7A58`; `OnTmrAutoSave` stores it at `TWordViwer+0xA0` (`0x004B8AE8`). `OnControlerNotify` later reads that field as the source path passed to `T7zOutArchive.AddFiles`. `LoadDocument` creates a `TFileStream` for the same path and writes document data. This links the file generated during Word document setup to the `.easd` archive entry inside `.easz`. Viewer field `+0x80` (base path) still needs mapping.


### EditWordDocument request/response path
- Concrete method `TEditWordDocument.PerformMethod` reads `wordConfig` (required), `wordBody`, `letterImages`, `signData`; missing `wordConfig` throws the explicit XML-invalid error.
- It wraps `TWordViwer.LoadDocument` in `CoInitialize`/`CoUninitialize`, passes the `TEmwatInvokeParam` pointer and output string, stores the returned method result, and sets `bResultSet=1`.
- `LoadDocument` extracts `DocFileName` from `wordBody`, writes document data to a local `TFileStream(fmCreate)`, parses `wordConfig` XML, then calls `OnTmrAutoSave` with that file path. The path is stored in viewer `+0xA0` and later packaged as `.easd` inside `.easz`.
- Next priority: determine how the returned string and `bResultSet` become the actual HTTP response body, and trace the full `wordConfig`/`letterImages`/`signData` handling.


## Accepted product decisions — 2026-11-18 (do not reopen implicitly)

- Linux only. Do not develop a new Windows app, UI, or installer; Windows is an analysis/compatibility reference only.
- GTK 4 + Python/PyGObject is selected for a small, free/open-source Linux control UI. Do not use Qt/PySide unless the owner explicitly changes the decision.
- LibreOffice Writer via UNO is the document editor. GTK is only for EMWAT status, settings, recovery, scanner entry points, and diagnostics.
- Main product workflow: Almas request/document → local EMWAT protocol bridge → LibreOffice Writer editing → final document returned to Almas in the verified response format.
- Keep bridge, document coordinator, UNO adapter, recovery, and scanner core independent from GTK; core and tests must run headlessly.
- No paid toolkit, subscription, or mandatory cloud service. Check license obligations for all distributed dependencies.
- Source of truth: `docs/LINUX-PRODUCT-DECISIONS.md`; also reflected in README, PROJECT-STATUS, Ubuntu installation guide, and recovery picker UX.
- Next implementation priority remains real Almas/browser wire-contract evidence and full Writer document roundtrip, not GTK screen proliferation.


## EMWAT Linux — Writer close evidence and CI handoff (2026-11-20)

- Latest branch checkpoint: `79c017e757485dbd5fb19b7a7e1fd13beb05353c`; PR #2 remains open/Draft/unmerged.
- Added `docs/WRITER-CLOSE-DISCARD-INVESTIGATION.md`: UNO `queryClosing`/terminal-close semantics are documented, but interactive Writer Save / Don't Save / Cancel ordering remains unverified. Do not infer discard from `notifyClosed` or `disposing`.
- Python CI run `44784556864`: success.
- LibreOffice UNO CI run `44784556817`: success; 17 tests passed, including real UNO open/close/export and EditWord response-handler integration.
- Native CI run `44784556764`: package lifecycle and normal build/CTest/staged install passed; ASan/UBSan was still running at the checkpoint.
- Next: poll Native sanitizer job, then record final combined CI status. Continue the Writer visible-UI Save / Don't Save / Cancel test design. Do not ship a daemon/desktop entrypoint or claim production readiness until Origin allowlists, verified close response policy, lifecycle supervision, secure recovery key custody and Almas wire fixtures are resolved.


## 2026-11-20 — parallel Word/Writer evidence and close acceptance work

- Added `python/src/emwat_linux/word_writer_evidence.py`: metadata-only summary of WordConfig field IDs, declared MIME/encoding, external parameter IDs, duplicates, settings, optional attributes and requested types, alongside Writer structural and custom-property names. It excludes field values, body text, image bytes and property values.
- Exposed `LibreOfficeAdapter.audit_word_writer_evidence(handle, config)` under the document snapshot lock. It is read-only; no inferred mapping is applied.
- Added tests for the report and adapter entry point. Initial report-only Python CI run `44796731919` passed 219 tests (217 passed, 2 optional skips). Newer adapter integration/test commit `4c571a74` has fresh CI runs queued.
- Added `docs/WORD-WRITER-EVIDENCE-REPORT.md` and `docs/WRITER-VISIBLE-CLOSE-ACCEPTANCE.md`. The latter defines visible Writer Save, Don't Save, Cancel and retry acceptance, including output-marker checks and non-sensitive callback diagnostics.
- Keep automatic WordConfig mapping disabled until a sanitized matching Word + wordConfig fixture and expected output are supplied and independently verified. Do not infer signData separators or property ordering.
- Next: poll CI runs for commit `4c571a74be9c75ad6fa0b7b823bcd6a3e8d88f28` (Python `44796996459`, Native `44796996414`, UNO `44796996426`); then poll docs-triggered UNO run `44797006712`. PR #2 stays open, Draft and unmerged.

## 2026-11-20 — corrected adapter evidence audit verification

- Added a lock-protected, read-only `LibreOfficeAdapter.audit_word_writer_evidence()` entry point for the metadata-only report.
- Corrected the test module imports after the first intermediate push; that intermediate CI attempt failed and is superseded by the corrected code/test head.
- Corrected head `4c571a74be9c75ad6fa0b7b823bcd6a3e8d88f28`: Python run `44796996459` passed 220 tests (218 passed, 2 optional skips); UNO run `44796996426` passed 18 tests including the new audit regression and real Writer roundtrip.
- Docs-triggered UNO run `44797006712` also passed. Native build/CTest/staged install passed; package lifecycle and ASan/UBSan were still running at last poll.
- Continue polling Native run `44796996414`; keep PR #2 open, Draft and unmerged.


## 2026-11-20 — complete CI checkpoint

- Verified code/test head: `4c571a74be9c75ad6fa0b7b823bcd6a3e8d88f28`.
- Python run `44796996459`: 220 tests, 218 passed, 2 optional skips.
- UNO run `44796996426`: 18 tests passed, including the new read-only adapter evidence audit and real Writer roundtrip.
- Native run `44796996414`: build/CTest, staged install, Debian package install/upgrade/removal lifecycle, and ASan/UBSan passed. Both normal and sanitizer CTest report 4/4 passed.
- Docs-only UNO run `44797006712` passed. Later commits through `bb1d920` only update status/handoff documentation after the verified code/test head.
- PR #2 remains open, Draft and unmerged. Do not claim live Almas E2E, automatic WordConfig field mapping, visible Save/Don't Save/Cancel parity, complete desktop installer, or physical scanner/ADF/duplex validation.


## 2026-11-20 — expanded evidence report and close retry tests

- Evidence report now includes field indices, twin delimiter members, duplicate/case-fold collision groups, root/permission attribute names, optional attribute type/encoding and content-element presence, plus Writer property collision metadata. No values or document text are exposed.
- `OptionalAttribute.has_content_element` preserves the distinction between no `<content>` node and an explicitly empty node.
- Added tests for missing optional IDs, empty content nodes, twin identifiers, collision handling, and redaction.
- Added a close listener regression proving that a successful snapshot from a cancelled attempt is replaced on the next attempt and that terminal close notification is required.
- Python run `44798087534` on `491ca49a`: 224 tests, 222 passed, 2 optional skips. Native run `44798087414`: build/CTest 4/4, sanitizer CTest 4/4, package lifecycle success.
- UNO run `44797952771` on `226e0205`: 19 tests passed. New adapter integration coverage for twin metadata and empty optional content is in commit `41e15bbe`; poll its Python/UNO/Native workflows `44798367250`, `44798367221`, and `44798367187`.
- An intermediate evidence-report test run failed because one assertion still referenced a removed report attribute; corrected immediately and verified by the subsequent 224-test green run.
- Keep all automatic field writes disabled until the real sanitized Almas fixture and expected output are available. PR #2 stays open, Draft, unmerged.


## 2026-11-20 — privacy-safe close trace

- Added `CloseLifecycleTrace` and wired it into Writer close and save listeners. It stores fixed callback names, attempt ordinal, sequence, and monotonic timestamp only; it never stores document or field data and does not infer user choice.
- Exposed read-only in-memory trace retrieval via `LibreOfficeAdapter.inspect_close_lifecycle_trace(handle)`.
- Added tests for callback order, retry attempt numbering, allowlisted event names, and absence of payload/path data.
- Python run `44798818684` on `2feff5bf`: 227 tests, 225 passed, 2 optional skips. UNO `44798818677` and Native `44798818848` still running at last poll.
- The trace supports the visible Save / Don't Save / Cancel acceptance matrix; it does not itself prove the selected outcome.


## Latest close-trace CI state

- Python `44798818684`: 227 tests, 225 passed, 2 optional skips.
- Native `44798818848`: normal build/CTest, ASan/UBSan and DEB package lifecycle all passed.
- UNO `44798818677`: LibreOffice installation and runtime verification passed; the test step remains in progress. Poll it before claiming close-trace integration is UNO-verified.
- PR #2 remains open, Draft, unmerged.

## EMWAT Linux — corrected parallel-work checkpoint (2026-11-23)

### CI at commit 8a29d56bdf366039882555cee92853b180eb5a04

- Python Bridge run 45172202794: success.
- LibreOffice UNO run 45172202821: success.
- GTK desktop smoke test run 45172202655: success.
- Native Image Core run 45172202648: build/CTest and staged install passed; Debian package install/upgrade/removal lifecycle passed; ASan/UBSan job also completed successfully.
- These workflows validate the CI jobs at this exact branch head. They do not validate a physical scanner, live Almas browser integration, or Windows archive interoperability.

### Archive evidence correction — supersedes older handoff wording

- The .easz output-file path and .easd entry-name construction are supported by static call traces.
- Do not describe the writer password or encryption state as confirmed. The writer CryptoGetTextPassword2 trace initializes an internal object list; it does not reveal a password value/provider. The mapped SetPassword implementation is a no-op, and interface slot +0x28 maps to the progress-callback method, not to a proven password setter.
- Older notes in this handoff that label a fallback/configuration string as the archive password are superseded. Do not reuse any such string as an archive password.
- The actual runtime encryption flags, password source, archive header profile and interoperability remain unverified. The current evidence boundary is documented in docs/EASZ-ARCHIVE-FORMAT.md.

### Scanner implementation boundary

- ImageDocument stores multiple pages. ScannerBackend exposes scan_one() and a source-compatible scan_pages() fallback; SaneScannerBackend overrides scan_pages() for explicitly selected simplex ADF sources. Duplex-labelled source values are deliberately excluded from batch mode.
- SANE ADF batches keep one device/session open, use NO_DOCS at page boundaries (from start or before read bytes) as normal completion, cap batches at 100 pages / 4 GiB with the remaining byte budget enforced before allocation, and reject a 101st page rather than silently truncate. Flatbed and unspecified sources remain single-page only. The bounded collection state machine has deterministic fake tests for page order, exact-limit completion, empty feeder, read/start failure, over-limit failure, byte limits and cleanup.
- Each page accepts one terminal 8-bit Gray/interleaved RGB frame or a validated planar RED → GREEN → BLUE sequence, interleaved into one RGB page. The production page reader now uses an injectable SANE function table, with fake-device tests for interleaved RGB, planar RGB, multi-page ADF, feeder-empty read status, partial-page rejection and invalid channel order. Duplex front/back semantics and physical scanner hardware acceptance remain open. See docs/SCANNER-MULTIFRAME-IMPLEMENTATION.md.

### WordConfig / Writer boundary

- The adapter opens the incoming document and exposes a read-only WordConfig-to-Writer evidence audit. It does not automatically apply WordConfig fields.
- Exact-name intersections and case-only matches remain candidates, not verified semantic mappings. No positional mapping, signature-image substitution or unverified twin-field writes are permitted.
- See docs/WORDCONFIG-WRITER-APPLICATION-PLAN.md.


## 2026-11-23 — automatic Writer inventory and partial-inspection diagnostics

- `LibreOfficeAdapter.open_document()` now captures a metadata-only WordConfig/Writer inventory automatically after opening the document and recording its baseline. The report is retained in-memory on the office handle as `word_writer_evidence`; no field values or body text are written and no mappings are applied.
- Overall inventory failure does not block document open; only the stable status `writer_inventory_unavailable` is retained.
- Writer catalog inspection now records stable, value-free `inspection_warnings` for individual UNO structures that cannot be enumerated. The evidence report exposes these as `writer_inventory_warnings`, preventing an unavailable container from being silently mistaken for a genuinely empty one.
- Custom document-property metadata is now read once per inventory pass, preserving its UNO-reported order and producing the sorted view from the same snapshot.
- Added unit coverage for unavailable containers and propagation of warning codes into the evidence report.
- Latest verified CI at commit `7f92fdd0b1e293a34b73105e48a0f8b896ca0726`: LibreOffice UNO run `45177847225` passed 24 tests. Python, GTK and Native workflows for this exact head were still running/queued at the time of this handoff update; do not reuse earlier-head counts as proof for this commit.
- Python run `45177757461` on prior code head `2f8ce039d0395c2870cdd743600e91bdf18e0b21` passed 277 tests; UNO run `45177756605` on that prior head passed 24 tests. These are not a substitute for final-head CI.
- The SANE `scan_one()` terminal-frame guard and archive evidence correction are also present on the branch. No ADF/duplex or `.easz` interoperability claim is made.
- PR #2 remains open, Draft and unmerged.


## 2026-11-23 — automatic evidence-bounded template inventory

- Added `emwat_linux.template_mapping.inspect_template_mapping(config, catalog)` and unit tests.
- The inventory compares custom-property names with Writer bookmarks, named ranges, sections, tables, frames, graphic objects, document indexes and `DocInfo.Custom` text fields using case-insensitive exact matches only.
- Critical safety correction: the report does **not** attach a Writer property index to a WordConfig XML field index. Equal counts are only a count observation; Word COM and LibreOffice property enumeration order equivalence remains unproven. All XML field IDs remain explicitly unassociated.
- The inventory is captured automatically alongside the existing metadata-only Word/Writer evidence from a single UNO catalog snapshot. It neither reads property values nor modifies the document.
- Added unit coverage and a live UNO integration assertion that the report preserves the unassociated-field boundary.
- CI for the current branch head is triggered by the latest commits; do not claim it passed until all four workflows complete on the same head.


## 2026-11-25 — Word print dispatch and worker ownership follow-up

- Inspected the successful printer-pipeline artifact `45345628400` and print-handler/controller artifact `45347505938` from the existing branch; no local Wine prefix or printer configuration was touched.
- Added `docs/WORD-PRINT-DISPATCH-AND-WORKER-ANALYSIS.md`. It separates the explicit `BGPrintWithGamPrintOptions` sequence (document vtable `+0x3F0`, then application `PrintOutOld` at `+0x1E4`) from the timer-driven document `PrintOutOld` path (`+0x2BC`). It also records the `TEmwatDocPrintHandler.Execute` callback field and cleanup lifecycle, while keeping unresolved method ownership explicit.
- Commit: `e0d3795cd8a1cbbd1b6d498fee3e70d3471b8804`.
- Next: resolve the document `+0x3F0` member and fifteen OleVariant arguments from exact wrapper/type-library metadata; trace helper `0x004677B8` and indirect controller callers; then correlate `ExtractFileNameEX` with the GAM TIFF artifact. No end-to-end print claim is made.


## 2026-11-25 — parallel reverse-engineering and regression lanes

- Added `.github/workflows/emwat-parallel-reverse-engineering.yml` with three independent jobs: (1) Word print COM/callback procedure, caller and pointer-reference traces; (2) Delphi VMT/symbol analysis plus read-only inventory of preserved scanner/image DFM resources; (3) native image-core build/tests and Python bridge regression tests.
- The workflow is triggered by changes to its own file and relevant preserved analysis inputs. It runs on GitHub Actions; it does not require Codex or local Ubuntu access from ChatGPT.
- Corrected the Python test install command to install the project from `./python` and `pytest` explicitly; the project does not declare a `test` extra.
- Commits: `bc25c106ec835d61df23a084cb03ccaaa2c0512c` (workflow), `b49f0b3eabbc3650afe4e717a59f203ef7747bbb` (dependency correction).
- Workflow execution and test outcomes are pending/unverified at this checkpoint. Do not report success until the run and all three jobs are inspected.


## 2026-11-25 — parallel RE lanes: first verified batch

- Added `.github/workflows/emwat-parallel-reverse-engineering.yml` with three independent jobs: Word print COM/callback traces; scanner/image VMT, symbol and procedure traces; native C++ and Python regression suites.
- Successful workflow run `45558987223` on commit `b49f0b3eabbc3650afe4e717a59f203ef7747bbb`: all 3 jobs passed. Native image core: 4/4 CTest tests passed. Python bridge: 317 passed, 9 skipped, 336 subtests passed.
- The first workflow attempt `45558964591` failed only because the Python package has no `test` extra and pytest was not installed. Corrected to `pip install -e ./python pytest`; the corrected run passed. Do not count the failed first attempt as a product regression.
- Expanded image procedure/caller tracing in the workflow. Run `45559122428` completed successfully with all 3 jobs passed, including the additional scanner, TIFF, crop, rotate, page and ImageEn traces.
- Added `docs/IMAGE-SCANNER-EDITOR-CALLGRAPH-INVENTORY.md` with class/method inventory, multipage page iteration, SavePage/SaveToFile/ScanToFile path observations, image-editor operations, and the explicit unverified VMT boundary.
- Corrected `docs/WORD-PRINT-DISPATCH-AND-WORKER-ANALYSIS.md`: `0x004677B8` is `TETracer.LogException`, and `0x00467788` is `TETracer.LogDebugF`. They are not a worker callback dispatcher. The controller/thread ownership relation remains open.
- Latest recorded commits for this batch: `c3f0ffdb491c5904ac4c8cc4b804aacc35316a4e` (print-analysis correction), `035855358083ed31b248c834b60198cd62742444` (image call-graph inventory), `5614bb08a57d8fa9be6254215a0e617f26b4c1d8` (expanded body-level image traces).
- No physical scanner, TIFF hardware capture, Wine prefix, or physical printer was exercised. No VMT candidate is treated as proven. The exact Word COM `+0x3F0` member and its fifteen Variant arguments remain unresolved.

- Compared recovered scanner/editor operations against current native source and added `docs/NATIVE-IMAGE-PARITY-GAP-2026-11-25.md`. Current native `ImageDocument` already supports ordered multipage pixels, DPI metadata, quarter-turn/flip/crop, and atomic all-page save; remaining parity gaps include single-file-set vs multipage result ownership, preview-coordinate crop, free rotate, auto-orient, insert/delete/reorder and explicit accept/cancel transactions. This is a source-level comparison, not a new code change.
- Added further helper-boundary and Word `TWordDocument.PrintOut` overload traces to the parallel workflow. Their newest runs are pending at this handoff update; inspect artifacts before making claims about helper API identities or the exact `+0x3F0` COM member.

- Resolved the formerly unknown Word document vtable call: TD32 wrapper `0x00436030` is `TWordDocument.PrintOut` with 15 `OleVariant` arguments, and its body dispatches through vtable `+0x3F0`. `BGPrintWithGamPrintOptions` prepares the same 15 Variant records and calls that exact slot at `0x004C70B6`; the wrapper's `ret 0x34` is consistent with 13 stack args plus two register args. The following `TWordApplication.PrintOutOld` call is separate. Detailed evidence and standard 15-parameter order are in `docs/WORD-PRINT-DISPATCH-AND-WORKER-ANALYSIS.md`; caller-side concrete values/types remain to be mapped.
- The latest Word wrapper workflow run `45559474102` passed all three jobs; it included the `0x00436030/0x004360F0/0x004361B0` overload comparison. The earlier image helper run `45559407814` passed all three jobs, but its image artifact omitted the separate `parallel-re/image-io` directory; the artifact path has been corrected and a fresh run is required to capture those helper traces.

- **Correction to the previous PrintOut note:** the actual `BGPrintWithGamPrintOptions` call setup contains 17 Variant arguments (plus the separately pushed document interface pointer), not 15. The exact matching wrapper is `TWordDocument.PrintOut` at `0x004361B0`, the 17-Variant overload; adjacent wrappers `0x00436030` and `0x004360F0` are the 15- and 16-Variant overloads. All dispatch through slot `+0x3F0`. The earlier proposed 15-name generic Word parameter list is withdrawn; semantic names/values/types for this 17-argument overload remain unresolved. See corrected section 6 in `docs/WORD-PRINT-DISPATCH-AND-WORKER-ANALYSIS.md`.

- The artifact-path correction is verified in run `45559625754`: image artifacts now include the separate `image-io/` outputs. Helper import analysis resolved `0x004AFE78`=`IG_ext_load`, `0x004AFE90`=`IG_save_file`, `0x004AFE98`=`IG_load_FD`, `0x004AFEA0`=`IG_save_FD`, `0x004AFEA8`=`IG_page_count_get`, `0x004AFEB8`=`IG_image_delete`, `0x004AFEC0`=`IG_image_is_valid`, `0x004AFF18`=`IG_IP_color_promote`, plus `CreateFileW`, `CloseHandle`, `_lopen`, `_lclose`. Added these to `docs/IMAGE-SCANNER-EDITOR-CALLGRAPH-INVENTORY.md`. These are exact import-thunk identities; the full ImageGear argument ABI/ownership is still open.
- Workflow run `45559625754` passed `word-print-com` and `native-regression` (the image job completed successfully as well); inspect the final run summary before quoting overall conclusion.

## 2026-11-25 — scanner page-output path recovered; parallel run inspected

- Parallel workflow run `45561859598` completed successfully: `native-regression`, `word-print-com`, and `image-ui-and-vmt` all passed. The native job completed both the native regression suite and Python bridge regression suite. Both Word and image artifacts were downloaded and inspected.
- New report: `docs/SCANNER-PREVIEW-OUTPUT-RECOVERY.md`. `TfrmGScanPreview.Scan` (`0x0061DC80`) iterates the source image's page count and writes each page to a separate physical output file: it reuses the current ImageGear page handle or loads other pages through `IG_load_FD`, creates each output with `CreateFileW(CREATE_NEW)`, writes it through `IG_save_FD`, closes the output handle, and deletes temporary ImageGear handles. The format/flag is selected by object field `+0x434` (values `0x40028` or `0x80028`); meanings remain unresolved.
- Important distinction: `Save_Tiff_MultyPages` (`0x0061D888`) is a separate operation using `IG_save_file` and format value `0x15` in one branch. Do not collapse this multipage save operation into the per-page `Scan` output contract. Filename constant at `0x0061DEE8`, naming/collision policy beyond `CREATE_NEW`, ImageGear ABI, and live response publication remain open.
- `cmbPagesChange` (`0x0061E680`) is preview geometry only: it computes a uniform fit scale, rounds fitted dimensions with the already-resolved Delphi `System.Round` helper, and centers the preview. It does not establish scanner DPI or resampling semantics.
- The new Word traces confirm additional `TWordApplication` getters and dispatch slots: `Get_Windows` (`0x0043EAB8`, slot `+0x2C`), `Get_WordBasic` (`0x0043EC28`, slot `+0x3C`), `Get_Version` (`0x0043F308`, slot `+0x88`), and `Get_CustomDictionaries` (`0x00440B2C`, slot `+0x188`). `PrintOutOld` (`0x00441E44`) dispatches through slot `+0x1E4`. This confirms wrapper targets, not the semantic mapping or ABI of the 18-record `BGPrintWithGamPrintOptions` callsite; the 18-vs-17 discrepancy remains open.
- Branch head before this handoff update: `5969ca3f007aa15589cc10797a2811e27e55a126`; the scanner report was committed as `781624eb79a9d8dcb48ea73b849b0f40c1ccbbe9`.

## 2026-11-25 — next parallel pass launched

- Expanded `.github/workflows/emwat-parallel-reverse-engineering.yml` and committed as `934793b0889cd3c90bfe33c34269f666ce56446a`. The next run is `45562585651` (https://github.com/meicamghe/EMWAT-Linux/actions/runs/45562585651).
- New Word targets cover `TWordApplication.Get_ActivePrinter` / `Set_ActivePrinter`, print-handler preparation/field methods, and controller notification. The symbol index now searches `Zanprinter`, `GetPrinterName`, and printer interfaces so the next artifact can connect Word's selected printer to EMWAT's printer layer.
- New scanner targets cover preview form destruction, page-number/image-size helpers, image-handle loading, and scanner selection in addition to the already recovered per-page output path.
- At handoff update time, all three jobs had started: `native-regression` was installing native dependencies; `word-print-com` was tracing the expanded target set; `image-ui-and-vmt` was resolving scanner/image VMTs. No artifacts or final conclusions from run `45562585651` are available yet.
- Current branch head before this handoff update: `934793b0889cd3c90bfe33c34269f666ce56446a`.

## 2026-11-25 — ActivePrinter wrappers and scanner page-state path recovered

- Run `45562585651` completed successfully in all three jobs; `native-regression` passed both native and Python bridge suites. Word and image artifacts were downloaded and inspected.
- New report: `docs/WORD-ACTIVE-PRINTER-AND-SCANNER-STATE-RECOVERY.md`.
- Word: `TWordApplication.Get_ActivePrinter` (`0x0043FF40`) dispatches via interface slot `+0x108`; `Set_ActivePrinter` (`0x0043FFA0`) dispatches via `+0x10C`. Both acquire the automation interface via `0x0043E210`. `PrintOutOld` (`0x00441E44`) is a separate dispatch via slot `+0x1E4`. This proves Word application ActivePrinter get/set wrappers, not OS default printer semantics or the end-to-end EMWAT queue-selection chain.
- `TEmwatDocPrintHandler` constructor initializes interface/object fields `+0xC8..+0xD8), controller-like reference `+0x48), and another retained object `+0x50). `DoOnTerminate` releases those references and clears `+0x48)/`+0x40`. `SetCCValueForMain`, `SetCCValueForArchive`, and `SetReceiversValueForSelected` enumerate interface-backed collections and merge values into string fields `+0x60)/`+0x64`; semantic names of the collections/fields remain unproven.
- Scanner: `GetImagePageNumber` (`0x0061D100`) uses ImageGear page-count and per-page metadata helpers, aggregates records into shared state; it is not a simple page-number getter. `GetImgSize` (`0x0061D250`) refreshes multipage UI through interface slots `+0x114`, `+0x3C`, and `+0x10C). `SelectScanner` (`0x0061DEF4`) uses `0x004AFF30` with values `0x28`/ `2`, refreshes state and validates the image handle; `0x004AFF30` semantics remain unresolved.
- Expanded next-pass workflow targets with `Zanprinter.GetPrinterName` (`0x0047CAF0`), install/configuration routines (`0x0047CC6C`, `0x0047CC94`, `0x0047D054`), `SetPrinterForTiffout` (`0x0047D238`), `CheckPrinterPaused` (`0x0047D448`), plus scanner error/load/destroy/crop helpers. Commit: `0c9b8152c6054cf81a9524d0d2a1f7f14a55ad12`.
- The new run `45563007730` on that commit is active. At last poll, all three jobs had started; native was installing dependencies, Word was tracing the expanded targets, and image was installing Python analysis dependencies. No final result/artifacts were available at that poll.
- The report commit is `edffc1d2c815e1c8f58ea47923042994d5f4af48`; current branch head may advance as further documentation is committed.

- Follow-up notation cleanup in `docs/WORD-ACTIVE-PRINTER-AND-SCANNER-STATE-RECOVERY.md` committed as `d7f7226f01f9b3945f041733aca37d307c238a97`.
- Latest run `45563007730`: native regression is complete/success. Word and image jobs are still running their expanded trace batches; their trace steps have not yet completed, so no artifacts or claims from the new Zanprinter targets are accepted yet.

---

## 2026-11-25 follow-up — Invoke response evidence reconciliation

### New repository-state discovery

The `main` branch was inspected separately from `feature/recovery-retention-policy`. Its 2026-11-25 upload adds a 13,722,034-byte `emwat_strings.txt` plus extracted analysis assets and reports. This supersedes the earlier observation that `emwat_strings.txt` was empty on the older branch/ref. Do not treat that earlier empty-file result as the current `main` state.

The recursive `main` tree was checked: it contains `http-requests.txt`, `tcp-conversations.txt`, the PCAP analysis scripts, and derived reports, but does not contain the private `emwat.pcapng` or `tcp-payloads.txt` source exports. The existing sequence-aware report and workflow artifact remain the evidence source for the 2026-11-15 raw capture.

### Correct interpretation of stream 18 sizes

The packet index's `tcp.len=31,420` (request-bearing frame 2344) and `tcp.len=53,405` (response-bearing frame 2732) are individual TCP frame payload lengths, not full HTTP body lengths. The sequence-aware PCAP report establishes:
- request `Content-Length: 1,177,821`;
- response `Content-Length: 1,166,820`;
- request body complete at 0.002154 s;
- first response payload at 54.560037 s;
- 54.557883 s from final request-body byte to first response byte;
- response payload sent over approximately 1.362 ms.

The approximately 2.35 MB TCP conversation aggregate is bidirectional connection traffic and must not be interpreted as a second application payload or as the exact size of either HTTP entity. The old frame-length/body-length ambiguity is reconciled; exact packet-byte accounting still requires the private raw PCAP.

### Cross-capture inference for nonce 29501

The DevTools screenshot pair for `invoke=29501` reports a completed response Content-Length of exactly 1,166,820 bytes. This exactly matches the independently captured `invoke=58351` response, whose body was reconstructed as a successful `response-word` envelope carrying Base64 `application/msword` content.

This is strong cross-capture corroboration that nonce 29501 returned the same class of Word-document response, but not direct body-level proof: the screenshot exposes headers only and the nonces are from distinct captures. Keep the classification as strongly corroborated, not confirmed from the screenshot itself.

### Static close-release chain

The preserved BPL trace maps `LoadDocument → OnTmrAutoSave`, a `Sleep(5) + ProcessMessages` polling loop on viewer field `+0x58`, the registered close/registration callback calling Word `Document.Close` and clearing `+0x58`, followed by `LoadDocument` writing the successful `response-word` response. This is consistent with the captured ~54.56-second wait and the browser screenshot's same-Invoke completion after Word closes. The formal COM event DISPID and initial setter for `+0x58` remain unresolved.

### Repository change

Detailed evidence and limitations were added to:
- `docs/PCAP-PROTOCOL-IMPLEMENTATION-CROSSCHECK-2026-11-22.md`, section 6.

Commit on `feature/recovery-retention-policy`:
- `849a2ef3532509ca775231e0cefeca2198aa2583` — `docs: reconcile invoke frame lengths with PCAP reconstruction`.

The documentation file was fetched again after the write and its new blob SHA verified. No CI status was reported for this docs-only commit. No live Almas E2E, complete raw-capture reanalysis, or nonce-29501 body inspection was performed.

## 2026-11-25 follow-up — Office close contract wording audit

A focused source review compared the captured close lifecycle with the current bridge/service/adapter contract. It found a stale interface docstring that contradicted the accepted Writer behavior: `OfficeAdapter.export_final_document` said it returned “including unsaved edits”, while the actual LibreOffice adapter reads the last confirmed saved-state file. The manual acceptance evidence establishes that Don't Save returns the previous confirmed baseline, not the dirty live document.

Corrected and committed:
- `python/src/emwat_linux/office_adapter.py`: documented that `CLOSED` includes Save and Don't Save; both return the latest confirmed saved state. `DISCARDED` is reserved for explicit operation-level discard with no document payload.
- `python/src/emwat_linux/document_coordinator.py`: clarified that finalization must never substitute a dirty live snapshot.
- `python/src/emwat_linux/editword_handler.py`: corrected the factory contract; the coordinator currently emits a `DISCARDED` result, not a terminal `CANCELLED` result. A vetoed close remains non-terminal and the adapter keeps waiting.

Commits:
- `a686b156336fcf4057d1c67ca1343bf477ac13b7`
- `6a452ebef9381c23ed0501981212891ceadccf03`
- `b0304651b49af1fd89d2eb115624bb619c3a75bb`

This is a contract/documentation correction, not a behavior change. Existing coordinator and LibreOffice tests were inspected; no test execution is claimed for these commits. The bridge's synchronous handler waits inside its request worker while the threaded server can continue serving heartbeat requests, as covered by the existing `test_document_post_waits_for_close_while_heartbeat_remains_responsive`. The captured ~54.56-second wait is compatible with this design; the socket timeout applies to socket I/O, not to elapsed time spent waiting in the office adapter.


---

## 2026-11-26 — Run 42 verified; parser fix and scanner ownership clarified

- Workflow run `45782764971` completed successfully on commit `295fc6e513664abe211d2ebeeda1964f1fcd584f`. All three jobs passed: `word-print-com`, `image-ui-and-vmt`, and `native-regression`.
- The fixed Word/Printer TIFF trace parser completed and produced Word artifact `15098978072`; the expanded Image/Scanner trace produced artifact `15099188562`.
- Word/Printer: `TCreateTiff.SeparteImages` (`0x004A0148`) has direct callers in `TWordViwer.LoadDocument` at `0x004B7A9C` and `0x004B7ABD`. It checks `GetPrinterName`, conditionally calls `InstallZanPrinter`, enters the GAM configuration path, and iterates the image collection. VCL `TPrinter` imports are present, but the complete caller-to-canvas/print-job chain remains unresolved.
- Clarification: `Zanprinter.CheckPrinterPaused` (`0x0047D448`) writes the recovered `save.ini`, `image.ini`, and `general.ini` configuration defaults; the actual queue status check is in the separately traced `Zanprinter.Finalization` (`0x0047D8BC`). Avoid using the method name as evidence of pause detection.
- Scanner: direct calls to `TScanCommand.Create` (`0x004F21DC`) and `GetNextPage` (`0x004F2558`) were found in `TFaxDocument.PerformMethod` at `0x005EECA1` and `0x005EECBD`. The public `TScanDocument.PerformMethod` at `0x005EE82C` is a separate path reading `wordConfig`, `wordBody`, `letterImages`, and `signData`. Do not conflate these paths without further evidence.
- The `TScanCommand` field-reference pass confirmed its field offsets and observed state values 1–4; state meanings remain unresolved. The attempted parent-VMT parse was invalid and is explicitly rejected.
- New workflow expansion committed after Run 42 as `e372fc188936ffcbeb54986630fe4981483a9577` (`ci: trace fax scanner command integration`). A fresh workflow run is expected from that commit; inspect it before accepting the next FaxDocument trace. No merge/rebase was performed; PR #2 remains Draft and unmerged.

## 2026-11-26 — Run 43 printer trace review and scanner lane continuation

- Run 43 (`45783897821`) Word/Printer and Native jobs completed successfully. Word artifact `15099392610` was downloaded and reviewed; the Image/UI job is still running, currently tracing result-image path and response-name ownership callers.
- The Run 43 printer trace now separates four concerns: `GetPrinterName` discovers the first local queue whose driver is `zvprt1`; `SetPrinterForTiffout` resolves the GAM output directory and folder policy; `CheckPrinterPaused` writes GAM INI settings despite its misleading symbol name; `Finalization` performs the actual Winspool paused-state query through `OpenPrinterA` and `GetPrinterA`. `getPrinterNumJobs` is another distinct helper and its full result path remains unresolved.
- Updated `docs/GAM-PRINTER-CONFIGURATION-RECOVERY.md` in commit `e85c5051a9de80a7f6542082a3428515f4e9e2db`; this is documentation-only. No merge/rebase was performed.
- `TCreateTiff.SeparteImages` iterates image collections through virtual count/index calls and enters per-image processing. Exact VCL canvas/spool submission semantics remain open; no CUPS backend or runtime printer parity is claimed.
- Next: finish Run 43 Image artifact review; recover the exact result-image base path versus XML response-name ownership, scan output cardinality, and `TFaxDocument` paging/handler relationship. Then update scanner contract docs and run fresh CI on the resulting combined head.


## 2026-11-26 — Run 43 scanner trace completed

- Run `45783897821` completed with all three jobs successful: `word-print-com`, `image-ui-and-vmt`, and `native-regression`. The Image/Scanner artifact `15099174916` was downloaded and reviewed.
- `TFaxDocument.PerformMethod` (`0x005EEB48`) directly constructs `TScanCommand` (`0x004F21DC`), calls `GetNextPage` (`0x004F2558`), and retrieves the `Scanedimage` property from its `ResponseXML` object. The earlier note treating `.tmp` and `document` as two dictionary keys is corrected: `.tmp` is a literal passed through helper `0x00454B9C` to form the local string sent to `GetNextPage`; `document` is passed to generic `TDictionary<String, Variant>.SetItem` (`0x0046D2E4`), i.e. it is written/updated, not retrieved. The Variant value's purpose is not yet known.
- The separate `TScanDocument.PerformMethod` (`0x005EE82C`) reads `wordConfig`, `wordBody`, `letterImages`, and `signData`, then calls `0x004B7724`. Do not merge these handlers or assume an indirect relationship without further evidence.
- Response XML is structurally split into `Status`, `ErrorCode`, and `Scanedimage`; the nested image has `ImageName` and `Encoding`. The `TScanCommand` path is stateful: it uses `FIsNextPageRequest` and `FPreviousReturnedFileName` while resolving the next image result.
- Updated scanner call-graph inventory with the new evidence and explicit unknowns. The native regression job passed, but that does not validate a physical scanner, ADF/duplex, or Almas wire compatibility.
- Next: compare this recovered handler contract against the native scan-result/connector boundary; implement only the parts whose semantics are now grounded. Capture real single-page and multipage outputs before finalizing response-name and file-cardinality rules. PR #2 remains Draft and unmerged; do not merge or rebase.

- Cross-lane follow-up (corrected): `.tmp` is a literal used by helper `0x00454B9C` and the resulting local string is passed to `GetNextPage`; `document` is the key of a `SetItem` write/update, not a dictionary read. The Variant value type and intent remain unknown.


## 2026-11-26 — Native scanner response metadata model

- Added an optional raw response-metadata structure to `ScanResult`, reflecting the recovered XML split: `Status`, `ErrorCode`, nested `Scanedimage.ImageName`, and `Scanedimage.Encoding`.
- Kept `scan_path`, outer `response_filename`, physical `ScanOutput`, and response metadata as separate values. No enum meanings, encoding-to-extension conversion, or path inference are assumed.
- Added focused regression coverage proving these fields remain independent. Commits: header `faba1970efe44a36cd1a398711ac0f9eee6f2d9f`; test `6f75b41edb0643029479cbc2f1cf1f644d69ac6e`.
- The first CI attempt exposed a missing-field-initializer warning under `-Werror`; fixed by adding the explicit `{}` default member initializer to `response_metadata`. Follow-up commit `35ffc42ef1717aecfdd065378c9cd249c3ff0ce8` passed Native regression run `45786665652` (C++ build, CTest, Python bridge) and Native image core run `45786665929` (build/test, sanitizer, Debian package lifecycle). This is native software verification only; it does not prove physical scanner or Almas protocol acceptance.


## 2026-11-26 — Corrected TFaxDocument dictionary analysis

The first interpretation of `.tmp` and `document` as two input keys was disproved by the call targets. `.tmp` is passed as a literal to helper `0x00454B9C`; the resulting string is forwarded to `GetNextPage`. `document` is the key passed to `TDictionary<String, Variant>.SetItem` at `0x0046D2E4`, so this is a write/update. The Variant payload and semantic intent remain unknown. Added a skipdata-aware trace script and extended the reverse-engineering workflow to inspect the complete paging routine and relevant helper internals. Workflow will validate these tools on push.


## 2026-11-26 — Native scanner metadata CI recovery

- Initial run `45786489435` correctly caught missing-field-initializer warnings after adding `response_metadata` under `-Werror`. Fixed with `std::optional<ScanResponseMetadata> response_metadata{};`, retaining compatibility with existing three-field aggregate initializers.
- Follow-up commit `35ffc42ef1717aecfdd065378c9cd249c3ff0ce8`: reverse-engineering run `45786665652` Native regression passed (C++ build, CTest, Python bridge tests); Native image core run `45786665929` passed build/test, sanitizer and Debian package lifecycle.
- Image/Scanner and Word/Printer analysis jobs in run `45786665652` are still running at handoff time. Do not report those lanes complete until artifacts are uploaded and inspected.

## 2026-11-26 — Run 48 complete; GetNextPage skipdata trace recovered

- Run 48 ([45786665652](https://github.com/meicamghe/EMWAT-Linux/actions/runs/45786665652)) completed successfully in all three lanes: Native regression, Image/UI/VMT, and Word/COM/Printer. Native C++/CTest and Python bridge tests passed. Image artifact `15102155195` and Word/Printer artifact `15101725038` were downloaded and inspected.
- The skipdata-aware trace covers all 1,340 bytes of `TScanCommand.GetNextPage` at `0x004F2558`; 16 bytes remain explicitly marked as undecoded data. New evidence confirms the `FIsNextPageRequest` branch, four-entry lookup against `FPreviousReturnedFileName`, the `_P` marker test, `ResultImage` construction, and response-XML virtual update/finalization path. Exact enum values, response property slots, output filename semantics and collection cardinality remain open.
- `0x00454B9C` receives the `.tmp` literal in `TFaxDocument.PerformMethod` and produces a derived local string through Delphi string/list operations. Do not call it a full path or a confirmed temporary filename yet.
- `document` remains a dictionary write via `TDictionary<String, Variant>.SetItem` at `0x0046D2E4`; `0x0046D210` and `0x0046D2C0` are generic dictionary lookup/hash helpers, not semantic decoders for the Variant.
- Full findings and next probes: `docs/REVERSE-ENGINEERING-RUN48.md`; scanner callgraph inventory also updated.
- Run 48 is a successful static-analysis/CI result, not physical scanner, printer, Wine, or live Almas acceptance. No production scanner implementation changed.
- PR #2 remains Draft/open/unmerged. No merge or rebase was attempted.

Next probes: recover the four filename-table strings and state-byte meanings; resolve response XML virtual targets and the `Scanedimage` update; trace `TResultImage` ownership/finalization; clarify the `.tmp` helper contract.
