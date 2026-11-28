# Parallel reverse-engineering follow-up — 2026-11-28

## Scope and evidence

This pass continues static analysis of the Windows EMWAT BPL, with concurrent CI jobs for scanner request/result ownership, ImageEn, Word COM events, printer-thread ownership and SevenZip archive callbacks.

- Analysis input: analysis-input/EmwatMethods.bpl1
- Current analysis commit: 9ac31f053c3fe8724f2d00819c7e49562f93a7d6
- Workflow run: 46112005385 (run 22)
- CI status at report time: scanner-result-ownership, imageen-acquisition and native-regression passed; word-printer-thread was still running.
- All findings below are static unless explicitly stated. CI success validates the analysis scripts and native regressions, not physical hardware or Almas end-to-end behavior.

## 1. Scanner request and constraint path

### Confirmed call relationships

- TFaxDocument.PerformMethod has a direct call to the TScanCommand lifecycle entry at 0x004F21DC.
- TScanCommand.DoRequest at 0x004F22E4 calls LoadRequestXML at 0x004F2B18, then Finalization at 0x004F32F4 on the validated branch, and uses HasError at 0x004F2A94 to set command state.
- TScanCommand.GetNextPage at 0x004F2558 calls VerifyConstraints at 0x004F2C4C and HasError at 0x004F2A94.
- The direct-caller scans show Finalization is called from DoRequest; VerifyConstraints is called from GetNextPage. These are separate request-time and page-advance checks.

### Constraint fields

The Finalization trace at 0x004F32F4 reads a byte at TScanCommand+0x08 and maps the values 1, 4, 8 and 24 to four localized mode labels:

- 1 — سیاه/سفید
- 4 — طیف سیاه و سفید
- 8 — طیف سیاه و سفید یا 256 رنگ
- 24 — رنگی 24 بیت

The pointer-reference scan found one code reference to each of the four global string slots, all inside the same Finalization branch. This supports a single selector-to-label mapping; the precise external XML field name is not yet proven.

The same routine compares the value returned by TGearImgProc.GearType at 0x004EEF30 against fields at +0x0C and +0x10. The associated messages identify these as minimum and maximum resolution checks. The +0x14 field is compared against an image-derived value from the result object at +0x20 after scaling by 1024; its exact unit and semantic name remain unknown.

The recovered Persian validation messages include:
- Image must be the requested mode.
- Image resolution must be at least the requested minimum.
- Image resolution must be between the requested minimum and maximum.
- Image resolution must not exceed the requested maximum.

The finalization path can report validation failure and expose Retry / Cancel choices. Do not replace this with silent coercion in a future adapter.

### Remaining scanner unknowns

- Exact XML property names and root/child node contract for NewScanDocument at 0x004E9D5C.
- Exact semantic name and unit for the +0x14 image-derived threshold.
- Exact units returned by GearType and the runtime behavior of the ImageGear resolution API.
- Whether the four mode labels represent strict required bit depth, maximum allowed bit depth, or a related scanner constraint; the selector values and message mapping are static facts, but the direction of the comparison needs a consumer/runtime cross-check.
- Physical scanner, ADF/duplex and live Almas acceptance remain untested.

## 2. ImageEn and ImageGear boundaries

The expanded ImageEn import analysis confirms:

- 0x004B012C is an import thunk to PKIECtrl23.bpl!TImageEnMIO.Acquire. TfrmImageTools.InsertPicture calls it at 0x0050A364.
- 0x004B0154 is an import thunk to PKIECtrl23.bpl!TImageEnMIO.PrintImage. TfrmImageTools.DoPrintingPanel calls it at 0x0050A7C3, 0x0050A8A6, 0x0050A999 and 0x0050AA85.
- 0x004B01A4 resolves to TImageEnMView.GetImageCount.
- 0x004B01F4 resolves to TImageEnMView.GetMultiSelectedImages.
- 0x004B01FC resolves to TImageEnMView.GetMultiSelectedImagesCount.
- 0x004B0204 resolves to TImageEnMView.MultiSelectSortList.
- TfrmImageTools.ScanPicture at 0x0050A298 is a one-byte RET stub in this build; it is not evidence of a functioning scan entry point.
- The symbol search did not recover a useful TWAIN/WIA acquisition implementation. Its sole iewia match is in the ExcelXP module and is not sufficient to assign a WIA scan role.

This reinforces the boundary already documented: ImageEn acquisition/import in the image-tools form is distinct from the GEAR32PD scanner preview and result path. The actual Acquire implementation is external to the current analysis input; PKIECtrl23.bpl is not present in the repository's analysis-input directory. Continue static work on the caller contract, but do not claim the external Acquire internals are reversed.

## 3. Word COM event cross-check

The current repository evidence already corrects the earlier callback confusion:

- OnTmrAutoSave at 0x004B8A84 stores 0x004CD154 as the BeforeSave callback in its event record.
- 0x004CCBBC is separately TD32-named WordAppDocumentBeforeClose. It has one direct bounded caller in FillImgFldsForPrint and no raw-pointer registration reference in the existing scans. Its active event role is unproven.
- Therefore 0x004CD154 must not be described as the registered BeforeClose callback.
- The exact parent-page message that triggers the close-time bridge POST/response path is still unresolved.

The run-22 callback crosswalk step completed successfully; its final artifact is pending the Word/Printer job upload. The existing evidence and caveats are maintained in docs/WORD-COM-INTERFACE-DISPATCH.md.

## 4. Printer and SevenZip archive

The Word/Printer lane is still running at report time. The existing evidence boundary remains:

- Printer queue discovery and paused-state checks are not proof of spool submission.
- THidePrintingThread.Execute remains only partially decoded; final spool submission/completion and the GAM artifact hand-off are not yet proven.
- euResetMemory is a distinct output-archive helper. Its output object receives a string through slot +0x44, opens a destination through +0x0C and receives a compression/property value through +0x3C.
- T7zOutArchive.SetPassword is a stub in the currently traced implementation. The output object's +0x44 slot identity and actual encryption behavior remain unproven.
- Do not infer archive encryption or hard-code the candidate password based on the input-side SetPassword path.

## 5. Verification and next work

Run 22 currently has successful scanner-result-ownership, imageen-acquisition and native-regression jobs. The Word/Printer job must finish before its artifacts can be reviewed and this report can be considered complete.

Next parallel tasks:
1. Review run-22 Word/Printer artifacts and resolve the print-worker / SevenZip output callback chain.
2. Map the 15-Variant Word PrintOut call and connect its document label to EnumJobsW/JOB_INFO_1W and the GAM output artifact.
3. Continue scanner XML node/property-name recovery and pin the +0x14 threshold to a named input field.
4. Obtain PKIECtrl23.bpl from the same EMWAT build if the ImageEn Acquire implementation itself must be reversed.
5. Trace the parent-page postMessage / close-time XHR and correlate it with the observed Word close acceptance behavior.

No production Linux code was changed in this pass. No merge or rebase was attempted. Keep the Linux product native; Windows binaries remain evidence inputs only.
