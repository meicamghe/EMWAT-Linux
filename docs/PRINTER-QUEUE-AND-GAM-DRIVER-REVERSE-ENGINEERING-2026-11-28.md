# Printer queue and GAM virtual-printer reverse engineering — 2026-11-28

## Run and source evidence

- Workflow: `EMWAT printer queue and output correlation`
- Run: `46117480260` (success)
- Artifact: `15252845315` (`emwat-printer-queue-ownership`)
- Analysis input: `analysis-input/EmwatMethods.bpl1`

## 1. GAM printer discovery

`Zanprinter.GetPrinterName` at `0x0047CAF0` calls `EnumPrintersA` through thunk `0x004044CC` twice:

- First pass uses flags `8`, level `2`, null buffer, and output-size/count pointers.
- Second pass allocates the required buffer and enumerates `PRINTER_INFO_2A` records.
- It walks records at stride `0x54` (84 bytes), compares the `pDriverName` field at offset `+0x10` with a constant at `0x0047CC64`, then copies `pPrinterName` at offset `+0x04` into global `0x0062B310`.
- This is a driver-name based selection of the target printer. The exact ANSI driver-name literal at `0x0047CC64` is `zvprt1`; this is the driver name, not necessarily the user-visible printer queue name.

Direct callers include `Zanprinter.InstallZanPrinter`, `Zanprinter.GetZanInstallDir`, `Zanprinter.CheckPrinterPaused`, `Zanprinter.Finalization`, and `TCreateTiff.SeparteImages`.

## 2. Printer paused-state check

`Zanprinter.Finalization` at `0x0047D8BC`:

1. Calls `GetPrinterName` to obtain global printer name `0x0062B310`.
2. Opens that printer with `OpenPrinterA` (`0x004044E4`).
3. Calls `GetPrinterA` (`0x004044D4`) twice at level 2, using a buffer-sizing pass and then a data pass.
4. Closes the handle with `ClosePrinter` (`0x004044B4`).
5. Reads `[PRINTER_INFO_2A + 0x48]` and returns true only when it equals `1`, consistent with `PRINTER_STATUS_PAUSED`.

`TCreateTiff.SeparteImages` calls this method and separately calls `Zanprinter.CheckPrinterPaused` at `0x0047D448`. The latter's exact relationship to the lower-level status check remains to be traced.

## 3. Queue handle and job-document matching

`Emwatutils.getPrinterNumJobs` at `0x00456258` calls `OpenPrinterW` through thunk `0x004044DC` and returns the resulting printer handle. Despite its name, this method does not itself call `EnumJobsW` or count jobs.

Its direct callers include:
- `TWordViewer.BGPrintWithGamPrintOptions` at `0x004C6099`
- `TrimLF` in module `frmWordPrintOptionUnit` at `0x004A6173` (procedure start `0x004A609C`). This routine only tests whether `OpenPrinterW` returned a nonzero handle, reports an error if it did not, and closes the handle later; it does not call `EnumJobsW` or use the handle for queue polling. It is not a `TCreateTiff.TrimLF` method.

`Emwatutils.ExtractFileNameEX` at `0x004562C4` calls `EnumJobsW` through thunk `0x004044BC` twice:

- First pass: `FirstJob=0`, `NoJobs=1000`, `Level=1`, null output buffer, and output pointers for required buffer size and returned count.
- Second pass: allocates the buffer and retrieves the `JOB_INFO_1W` array.
- It iterates records at stride `0x40` (64 bytes), reads the `pDocument` pointer at offset `+0x10`, and compares each document name with the supplied UnicodeString.
- It returns a Boolean indicating whether a matching print-job document name was found.

This is strong evidence that EMWAT correlates an Office/Word print operation with the Windows spool queue using the job's document name. It does not prove the final GAM TIFF output is complete or that the queue job has fully drained.


## 4A. Word queue polling is now directly connected

A second pass over `BGPrintWithGamPrintOptions` at `0x004C5FF8` confirms the direct queue-match call that was previously only inferred from the helper:

- At `0x004C6099`, the routine calls `getPrinterNumJobs` and stores the returned printer handle in local `[EBP-0xDC]`.
- For each document-name candidate, it calls `0x004563A8` (`FixDirectionInFarsiNumericMode`) to normalize the UnicodeString, places the normalized name in `EDX`, the printer handle in `EAX`, and calls `ExtractFileNameEX` at `0x004C8949`.
- If the helper returns true (matching job is still present), the caller waits via a one-argument delay call (`push 5`; target `0x004028D0`) and repeats the same queue check. A false result advances to the next document/page. The delay target is confirmed as `kernel32!Sleep` (IAT `0x0062F09C`) even though TD32 labels the thunk `SuspendThread`; the following thunk at `0x00404F04` is still being identified.
- The routine closes the printer handle through `ClosePrinter` at `0x004C8B72`.

This proves that the Word print path waits while the matching document job remains in the spool queue and advances when that job is no longer found. No explicit timeout was observed in this loop. The code treats queue disappearance as its completion condition, but absence can also result from cancellation, deletion, a job that was never submitted, or a document-name mismatch; it does not independently prove successful printing or final TIFF archive completion. The queue helper's direct caller is now established even though the separate TD32 direct-caller report missed this callsite.

## 4. Other printer enumeration path

`Emwatutils.euIsValidFileName` at `0x00456870` also calls `EnumPrintersW` (`0x004044C4`) twice at level 2 with flags value 6. It walks `PRINTER_INFO_2W`-shaped records (stride `0x54`) and compares printer-related fields through a helper object. Its exact semantic purpose is not yet settled despite the symbol name.

`Zanprinter.GetPrinterName` uses `EnumPrintersA` (not W) and has a distinct flags=8 discovery path.

## 5. End-to-end print model now supported

The current static evidence supports this sequence:

1. EMWAT discovers the GAM printer by enumerating local printer records and matching a driver-name constant.
2. It opens the selected printer and checks its paused state via `PRINTER_INFO_2A.Status`.
3. Word is invoked through the existing COM `PrintOut` path.
4. EMWAT opens/retains a printer handle and polls the queue with `EnumJobsW`, matching `JOB_INFO_1W.pDocument` against a supplied document name.
5. TIFF page processing and the hidden worker run in the `SeparteImages` orchestration path.

No direct EMWAT `StartDocPrinter`/`WritePrinter` call was recovered. This is compatible with Word owning actual job submission through its own print stack; do not treat the absence of those imports in EMWAT as evidence that no spool job is created.

## 6. Next parallel checks

1. Trace `TCreateTiff.TrimLF` and pointer/VMT references to `ExtractFileNameEX`; prove exactly where the document name is generated and how the match result gates TIFF output.
2. Decode `0x0047CC64` and confirm the printer driver literal. Trace `InstallZanPrinter` and the installer/setup branch.
3. Trace `Zanprinter.CheckPrinterPaused` at `0x0047D448` and reconcile it with `Finalization`'s PRINTER_INFO_2A.Status test.
4. Connect the queue-match result to `TCreateTiff.SeparteImages`, `THidePrintingThread.Execute`, and the final output archive object.
5. Confirm the exact Word PrintOut ABI independently; the four repeated callsites still pass 18 Variant-record pointers while the TD32 wrappers stop at 17.

## Guardrails

This is static binary analysis only. No physical printer, real Word, or Almas run was performed. The observed queue matching is not yet a complete print-success contract.

## 7. Driver installation / printer helper boundaries

- `InstallZanPrinter` at `0x0047CC6C` is a short helper that calls `GetPrinterName`; when a printer is found, it passes the selected queue name to helper `0x00401240`. The exact side effect of that helper is not yet named.
- `GetZanInstallDir` at `0x0047CC94` checks printer presence, performs path/registry/string work, and includes a bounded retry loop (up to 300 iterations with 100 ms delay) while waiting for the printer to appear. It also calls `0x0047D238` with the selected printer name.
- `CheckPrinterPaused` at `0x0047D448` independently calls `GetPrinterName` and `0x0047D238`; it is not yet proven to be the same status test as `Finalization`'s direct `PRINTER_INFO_2A.Status` check.


## 4B. Delay API symbol cross-check

The one-argument call target `0x004028D0` is confirmed by the PE import table as `kernel32.dll!Sleep` (IAT `0x0062F09C`). The TD32 symbol name `Winapi.Windows.SuspendThread` at the same thunk is therefore a stale/misleading debug symbol; trust the import table and call shape. The Word queue loop's `push 5; call 0x004028D0` is a 5 ms Sleep before the next queue check. The hidden worker uses the same Sleep thunk with other millisecond values. The following `0x00404F04` thunk is `Vcl.Forms.TApplication.ProcessMessages` (IAT `0x00630038`), keeping the UI responsive between queue checks.

