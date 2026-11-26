# Deep parallel follow-up — scanner result ownership, ImageEn and native boundary

Date: 2026-11-26
Branch: feature/recovery-retention-policy
Workflow: https://github.com/meicamghe/EMWAT-Linux/actions/runs/45794156659
Analyzed input: analysis-input/EmwatMethods.bpl1

## Status at report creation

- imageen-acquisition: passed; artifact 15104267112.
- scanner-result-ownership: passed; artifact 15102809326.
- native-regression: passed (native build/CTest and Python bridge tests).
- word-printer-thread: still running when this report was started. No conclusion from that lane is included here.

These are static-analysis and CI results. They do not establish physical scanner, ADF/duplex, Windows printer-driver, or live Almas acceptance.

## 1. Result-image serial and ownership implementation

The TD32 symbol-derived trace identifies these procedures in IPResultImageUnit:

| Procedure | VA | Size |
|---|---:|---:|
| TResultImage.Create | 0x004EC8B4 | 420 |
| TResultImage.FileNameOf | 0x004ECB6C | 105 |
| TResultImage.GetFileNamePath | 0x004ECBD8 | 171 |
| TResultImage.GetFilesCount | 0x004ECC84 | 37 |
| TResultImage.GetResponseFileName | 0x004ECF38 | 23 |
| TResultImage.ShiftSerial | 0x004ECFC8 | 113 |
| TResultImage.GetScanFilePath | 0x004ED03C | 276 |
| TSetOfSinglePageImages.Create | 0x004ED168 | 304 |
| TSetOfMultiPageImages.Create | 0x004ED298 | 172 |
| TSetOfMultiPageImages.GetResponseFileName | 0x004ED438 | 134 |
| TSetOfMultiPageImages.GetScanFilePath | 0x004ED4C0 | 204 |
| TSetOfMultiPageImages.SetResponseFileName | 0x004ED58C | 141 |

### Confirmed base behavior

- The base object stores the response filename separately from the scan path: the response-name getter reads the field at +0x08; the scan-path implementation operates on the field at +0x10. The location getter reads the byte at +0x04.
- TResultImage.GetScanFilePath parses the trailing three-character serial from the stored scan-path string, applies the requested increment, bounds the resulting serial to 0..999, formats it as three digits, and rebuilds the candidate from the preserved prefix/suffix.
- TResultImage.ShiftSerial(1) calls the virtual scan-path getter, then checks whether the resulting candidate exists. Its Boolean result therefore represents a filesystem collision/availability test for the next candidate, not a page count.
- GetFileNamePath(index) returns the stored base path for a non-positive index; for a positive index it asks the scan-path virtual method for the preceding serial candidate. Keep this indexing behavior separate from external page numbering until runtime samples establish the connector convention.

### Multi-page specialization

- TSetOfMultiPageImages has its own constructor and overrides for scan path and response filename. It is not interchangeable with the base result object or the single-page collection.
- Its scan-path override checks the current candidate and, when occupied, constructs a new candidate using the class-specific path components. The recovered binary contains the _P marker and three-digit serial format, but the complete path concatenation still needs a controlled runtime sample.
- Its response-name override is a separate method that derives a response-facing name through FileNameOf and class-specific string handling. Do not collapse it into the physical scan path.
- The multi-page delete-file method (0x004ED344) removes the current file and then calls ShiftSerial; the multi-page constructor (0x004ED298) also initializes the collection/path state and performs serial availability handling.

### Limits

The static trace does not establish the external Almas page-numbering convention, the exact semantic mapping of the one-byte location field, the complete imageName to disk-path relationship, or the runtime cardinality of a multipage response. Preserve the current separate output/scan-path/response-name fields.

## 2. ImageEn image-tools path — acquisition and print UI are distinct

- TfrmImageTools.ScanPicture at 0x0050A298 is a one-byte procedure containing only ret; the direct-call scan found no callers. Do not treat this symbol as a working scanner implementation.
- TfrmImageTools.InsertPicture at 0x0050A29C is a real 376-byte procedure. It obtains the ImageEn MIO object from the image-view control, performs state/configuration checks, sets an object flag at +0x38, and calls the TImageEnMIO.Acquire thunk 0x004B012C at 0x0050A364. It then continues through image-tools update/selection handling.
- The direct-call scan lists itToolbarHint as a caller of InsertPicture; the symbol named ScanPicture itself has no direct callsite in this binary trace.
- TfrmImageTools.DoPrintingPanel at 0x0050A698 is a separate 1,120-byte path. Its body obtains image counts and iterates image entries, repeatedly dispatching an ImageEn helper at 0x004B0154 with page-index and print-layout arguments. The helper's exact imported API identity still needs explicit thunk resolution.
- DoPrinting (0x0050A534) is a separate short method; the current direct caller scan lists itToolbarHint at 0x00509FB8. DoPrintingPanel is directly called from iePageHolderDblClick at 0x0050B711.
- The binary imports ImageEn TWAIN/WIA units, TImageEnMIO.Acquire, TIFF/file save helpers and PrintImage. Import presence and UI calls do not prove that device transfer or a real printer spool job succeeds.

Keep the ImageEn image-tools acquisition/import and print-preview workflow separate from the main GEAR32PD TfrmGScanPreview scanner path.

## 3. Native scanner-to-result boundary audit

The current native code has two separate surfaces:

1. ScannerBackend::scan_pages / SaneScannerBackend::scan_pages return std::vector<ImagePage>.
2. ScanResult describes persisted file ownership (SinglePageFileSet or MultiPageFile), scan path, response filename and optional raw response metadata.

A branch-wide audit of all native C++ headers, sources, tests and CMake registration found that ScanResult is referenced only in native/include/emwat/scan_result.hpp and native/tests/test_scan_result.cpp. The scanner implementation and tests use std::vector<ImagePage>; no production composition currently persists a batch into ScanOutput, creates the response XML metadata from it, or bridges the two models.

This is an integration gap, not a failing test. The independent scan_result_contract test validates the value object only. Do not invent a conversion from page count to single/multipage file ownership: first implement a persistence/orchestration boundary with explicit output policy and test it against captured response fixtures.

## 4. Workflow implementation note

The scanner lane's state-table pointer step used scan_pe_pointer_refs.py without its output-path argument. The script therefore wrote its detailed report to its default bpl-analysis/PE-pointer-refs.md, outside the uploaded artifact directory; only the one-line summary was captured. The next workflow revision should pass an explicit artifact path. The scanner procedure/caller traces themselves were uploaded successfully.

## 5. Next steps

1. Resolve the exact VMT slots for the base and multi-page GetScanFilePath / GetResponseFileName overrides.
2. Decode the remaining format/path literals and verify complete serial-name composition with a controlled runtime sample.
3. Resolve ImageEn thunk 0x004B0154 and the print helper dispatch; trace the actual Word/GAM hidden thread separately.
4. Design a native scan orchestration API that owns page persistence, explicit single/multipage output policy and response metadata; do not conflate image pages, output files and response names.
5. Add captured response fixtures only after real connector samples establish field values and page sequencing.

## Artifacts

- emwat-deep-scanner-result-ownership — result-image procedures, callers and GetNextPage control-flow trace.
- emwat-deep-imageen-acquisition — ImageEn InsertPicture/ScanPicture/printing-panel procedures and callers.
- Word/Printer artifact will be appended after its lane completes.
