# EMWAT Windows spooler selection and job matching

Date: 2026-11-24  
Input: static TD32/disassembly traces of `EmwatMethods.bpl1`.  
Scope: EMWAT's own queue-discovery and job-correlation helpers, distinct from the GAM virtual printer's OEM driver and local port monitor.

## 1. Queue discovery — `Zanprinter.GetPrinterName`

Procedure: `0x0047CAF0` (`GdiPlus` module).

- Calls `EnumPrintersA` twice at level 2: first with a zero-size buffer to obtain the required size, then with an allocated buffer.
- Iterates the returned `PRINTER_INFO_2A` records using a `0x54`-byte stride.
- Reads `pDriverName` at record offset `+0x10` and compares it with the embedded string at `0x0047CC64`.
- When a match is found, reads `pPrinterName` at offset `+0x04` and stores it in global `0x0062B310`.

**Interpretation:** the queue is selected by matching its installed driver name, then retaining the corresponding queue name. The literal at `0x0047CC64` has not yet been independently decoded. Do not infer that it is exactly `Zan Image Printer` or `GAM Virtual Printer` solely from adjacent branding strings.

Direct callers identified:
- `Zanprinter.InstallZanPrinter`
- `Zanprinter.GetZanInstallDir`
- `Zanprinter.CheckPrinterPaused`
- `Zanprinter.Finalization`
- `Createtiff.SeparteImages`

## 2. Queue paused-state check — `Zanprinter.Finalization`

Procedure: `0x0047D8BC`.

- Calls `GetPrinterName`; if no matching queue is found, follows an error/exception branch.
- Opens the discovered queue with `OpenPrinterA`.
- Calls `GetPrinterA` at level 2, using the standard size-probe then data-fetch pattern.
- Closes the handle with `ClosePrinter`.
- Checks the DWORD at `PRINTER_INFO_2A+0x48` against `1`. This offset is the `Status` member of `PRINTER_INFO_2`; value 1 is `PRINTER_STATUS_PAUSED`.

**Interpretation:** EMWAT explicitly distinguishes a paused queue from a ready queue. This should be represented as a printer-state check, not as a generic "printer exists" result.

## 3. Match a queued job by document name — `Emwatutils.ExtractFileNameEX`

Procedure: `0x004562C4`.

- Receives an existing printer handle and a target document-name string.
- Calls `EnumJobsW` at level 1, requesting up to 1000 jobs.
- Uses the two-call buffer-size pattern: query required bytes, allocate, then retrieve the `JOB_INFO_1W` records.
- Iterates the returned records with a `0x40`-byte stride.
- Reads `pDocument` at offset `+0x10` and compares it with the supplied document-name string.
- Returns a Boolean indicating whether a matching document-name job was found.

This is stronger than a simple queue count: it provides a document-label-to-spool-job matching primitive. The direct-call scan did not find a direct caller in the bounded TD32 procedures, so the higher-level invocation path remains open.

## 4. Printer-job count helper

`Emwatutils.getPrinterNumJobs` at `0x00456258` is called from `TWordViewer.BGPrintWithGamPrintOptions` at `0x004C6099`. It opens a printer using `OpenPrinterW`. The exact helper/API dispatch that supplies the returned count has not yet been resolved; the method name alone is not sufficient evidence for the implementation.

## 5. Static spooler callsite inventory

| API | Observed caller | Current role |
|---|---|---|
| `EnumPrintersA` | `Zanprinter.GetPrinterName` | Discover queue by driver metadata |
| `OpenPrinterA` | `Zanprinter.Finalization` | Open discovered queue |
| `GetPrinterA` | `Zanprinter.Finalization` | Read `PRINTER_INFO_2` status |
| `ClosePrinter` | `Zanprinter.Finalization` | Release queue handle |
| `OpenPrinterW` | `Emwatutils.getPrinterNumJobs` | Open queue before print path |
| `EnumJobsW` | `Emwatutils.ExtractFileNameEX` | Find a job by document name |
| `EnumPrintersW` | `Emwatutils.euIsValidFileName` | Separate utility path; exact relation to print submission not established |

These are static callsites. They do not prove that every helper runs for every print request.

## 6. Linux implementation requirements

- Represent queue discovery, queue identity, queue state and job identity as separate data.
- Support paused-state reporting and avoid treating a paused queue as ready.
- Implement job matching using the document label as a correlation key, but do not assume document labels are globally unique.
- Keep spool-job IDs and the final GAM artifact path separate until a controlled Windows trace establishes their relationship.
- Use CUPS/IPP for native Linux queue/job operations; do not port Windows spooler DLLs or ANSI API assumptions.

## 7. Open questions

1. Decode the exact driver-name literal at `0x0047CC64`.
2. Resolve the full `getPrinterNumJobs` helper/API path and whether it is a count, availability check, or both.
3. Find the higher-level caller of `ExtractFileNameEX` (including VMT/indirect callsites).
4. Correlate the matching `JOB_INFO_1W` document name and job ID with the GAM port monitor/server output file.
5. Determine whether the three timer-triggered `Document.PrintOutOld` calls create separate queue jobs or are coordinated by the BeforePrint handler.
