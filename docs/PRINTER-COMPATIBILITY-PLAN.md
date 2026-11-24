# EMWAT printer compatibility — evidence and implementation plan

Date: 2026-11-24
Branch at analysis: `feature/recovery-retention-policy`

## Evidence currently available

The following observations were supplied by the project owner and are treated as high-value reverse-engineering leads, not as independently revalidated binary conclusions in this commit:

1. `EmwatMethods.bpl` contains printer-management methods named `GetPrinterIndex` and `SetPrinterIndex`.
2. `EmwatAgent.exe` calls Windows Spooler APIs including `OpenPrinterW`, `EnumPrintersW`, and `GetPrinterW`.
3. `GAMPrinterSetup.exe` is an InstallShield installer package.

The repository currently contains `analysis-input/EmwatMethods.bpl1` and generated string inventories for `EmwatMethods.bpl1` and `EmwatAgent.exe`. The relationship between the owner's `.bpl` filename and the repository's `.bpl1` artifact (same binary, renamed copy, or different build) must be verified by file hash and PE metadata before address-level traces are combined. String inventories alone do not establish callsites or runtime semantics.

## Newly recovered GAM Virtual Printer package evidence (2026-11-24)

Detailed payload, INI, rendering, and uncertainty inventory: [GAM Virtual Printer reverse-engineering evidence](GAM-VIRTUAL-PRINTER-REVERSE-ENGINEERING.md). The extracted package confirms a GAMPrinter queue configured over a Zan Image Printer-derived OEM graphics-driver/port-monitor stack. It also exposes color/BW/Fax profiles, filename templating and optional FTP/email/event features. Numeric format/compression/collision enums and the exact EMWAT output hand-off remain unresolved; do not select a Linux output format from the current enum values.

## Additional output-format evidence (2026-11-24)

The `zvprtcfg_x86.exe` usage examples now explicitly decode `image.fileformat=1` as TIFF and `image.fileformat=2` as JPEG. Compression and save-collision enums remain unresolved; see [the detailed reverse-engineering evidence](GAM-VIRTUAL-PRINTER-REVERSE-ENGINEERING.md).

## What the Windows API evidence means

- `EnumPrintersW` is a discovery/enumeration boundary. Its flags, name/server filters, returned level, and buffer handling determine which printers are visible to EMWAT.
- `OpenPrinterW` opens a handle for a printer or print server. It is not itself a print-job submission operation.
- `GetPrinterW` reads printer metadata through an opened handle. The requested information level (for example, `PRINTER_INFO_2`) and the exact fields consumed by the caller must be recovered before defining the compatibility DTO.
- The existence of these imports does not prove that EMWAT submits jobs through this same code path. Actual submission APIs and their callers must be traced separately.
- `GetPrinterIndex` / `SetPrinterIndex` names suggest index-based selection, but do not prove whether the index is zero- or one-based, whether it indexes a filtered list, which list flags/order are used, or whether the selected index is persisted.

## Linux design boundary

Implement the printer subsystem as four independent operations:

1. **Discovery:** enumerate CUPS/IPP-visible destinations and expose stable destination identifiers, display names, descriptions, and availability where supported.
2. **Metadata:** retrieve destination attributes separately from enumeration. Missing CUPS/IPP attributes must remain explicitly unknown rather than being fabricated from a display name.
3. **Selection:** persist a stable destination identity, not a numeric list index. Provide a compatibility adapter that resolves a legacy index only against the exact ordered snapshot supplied by the corresponding request; reject stale/out-of-range indices.
4. **Submission:** submit a print job through the selected destination only after the original EMWAT print path, document format, options, and response semantics have been identified. Discovery and selection must not implicitly print.

A future backend contract should expose typed operations such as `list_destinations()`, `get_destination(destination_id)`, `get_default_destination()`, `set_default_destination(destination_id)`, and `submit_job(destination_id, document, options)`. The API names are a Linux-side design proposal, not recovered Windows ABI.

### Index compatibility rules

- Never store a numeric index as the durable selected-printer setting.
- Capture one ordered enumeration snapshot per legacy request and bind its generation/token to any index-based follow-up.
- Translate the legacy index to a stable destination ID only within that snapshot.
- Reject an index when the snapshot is absent, stale, ambiguous, or out of range; do not silently fall back to the system default.
- Keep the EMWAT-selected destination distinct from the operating-system default printer until traces prove they are the same setting.

## InstallShield investigation

Treat `GAMPrinterSetup.exe` as a separate installation/reconfiguration workflow. Before implementing an equivalent, extract and inspect its InstallShield metadata and payload inventory, identify custom actions/scripts, driver package names and architectures, registry writes, service dependencies, and whether it installs a vendor driver or merely configures a queue. Do not execute the installer as part of static analysis and do not copy Windows driver binaries into the Linux package. Linux support should use an appropriate CUPS/IPP driverless path or a separately licensed/redistributable vendor Linux driver when evidence supports it.

## Required reverse-engineering work

1. Verify SHA-256, PE timestamp, image size, architecture, and version/resource metadata for the exact `EmwatMethods.bpl`, `EmwatAgent.exe`, and `GAMPrinterSetup.exe` builds. Compare the BPL against the repository's `EmwatMethods.bpl1` artifact.
2. Resolve the BPL methods through TD32/RTTI and trace every caller/callee of `GetPrinterIndex` and `SetPrinterIndex`; recover argument/return types, index base, enumeration source, ordering, persistence location, and error behavior.
3. Inspect the Agent import table and callsites for `EnumPrintersW`, `OpenPrinterW`, and `GetPrinterW`; record enumeration flags, information levels, fields read, handle lifetime, and all relevant error codes.
4. Trace actual print submission separately (for example, spooler job/document APIs or a vendor-specific transport); do not infer it from metadata calls.
5. Inspect InstallShield tables/scripts and custom actions for queue creation, driver installation, port configuration, registry changes, and service dependencies.
6. Build sanitized fixtures with at least: no printers, one printer, multiple printers, reordered enumeration, removed destination, offline destination, access denied, and invalid/stale legacy index.

## Acceptance tests for the Linux implementation

- Discovery returns stable unique IDs and tolerates an empty CUPS destination list.
- A changed enumeration order does not change the persisted selected destination.
- Legacy index translation is deterministic within one snapshot and rejects stale/out-of-range references.
- An unavailable selected destination is reported explicitly; it does not silently switch to another printer.
- Metadata failures do not invalidate unrelated destinations or leak native handles.
- Print submission is not triggered by discovery, metadata lookup, or selection changes.
- Submission preserves document bytes and supported options, reports the CUPS/IPP job identifier, and surfaces failure/cancellation distinctly.
- Unit tests use a fake backend; integration tests use a controlled CUPS test destination. Physical printer acceptance remains a separate gate.

## Current implementation status

No Linux printer backend, legacy index adapter, persistent printer selection, or print-job submission path is present in the inspected Python/native source tree at this analysis point. The existing SANE scanner subsystem is unrelated and must not be reused as a printer abstraction. No claim of printer compatibility or installer equivalence is made.


## 2026-11-24 — EMWAT spooler calls and Word COM print path

Source: workflow run 45345628400, expanded printer-pipeline artifact.

### Windows spooler callsites in EmwatMethods

The import-callsite map found 11 static callsites across the inspected spooler functions:

| EMWAT method | API | Observed role |
|---|---|---|
| `Zanprinter.GetPrinterName` | `EnumPrintersA` | Enumerate printer names |
| `Zanprinter.Finalization` | `OpenPrinterA`, `GetPrinterA`, `ClosePrinter` | Printer handle/info lifecycle |
| `Emwatutils.getPrinterNumJobs` | `OpenPrinterW` | Open queue for job-count query |
| `Emwatutils.ExtractFileNameEX` | `EnumJobsW` | Enumerate jobs |
| `Emwatutils.euIsValidFileName` | `EnumPrintersW` | Printer enumeration in this helper; exact semantic reason still needs callsite context |

No direct `WritePrinter`, `StartDocW`, `StartPage`, `EndPage` or `EndDoc` import/callsite was found in the inspected BPL. This does not mean the product does not print; it means the BPL delegates the actual print operation through a higher-level API.

### Word COM print operation

- `TWordViewer.BGPrintWithGamPrintOptions` at `0x004C5FF8` contains a 15-Variant COM vtable call at slot `+0x3F0` (the exact interface method identity remains unresolved), followed by a direct call to `TWordApplication.PrintOutOld` at `0x004C70CA`.
- The `TWordApplication.PrintOutOld` wrapper at `0x00441E44` invokes COM interface slot `+0x1E4`. Its direct callers include `BGPrintWithGamPrintOptions` and `LoadOptions`.
- `WordAppDocumentBeforePrintBGPrint` at `0x004CE030` is the Word print-event callback. It verifies the active document, checks print configuration and builds recipient/CC-related lists before the print path proceeds.
- `TEmwatDocPrintHandler.Execute` at `0x004A5EA8` dispatches a stored method callback through helper `0x004677B8`; `TEDPController.SetPrintThread` stores handler/method pointers in controller fields. The complete callback-to-thread method ownership still needs one more callsite trace.
- The similarly named `PrintWordDoc` routines in the `Createtiff` unit are not the main GAM print path in this evidence set: their direct callers are `CreateImageFile` and `GetCaptionItemFont`.

### Remaining print questions

1. Identify the COM method at vtable slot `+0x3F0` and map the 15 Variant arguments.
2. Trace the selected/default printer queue and any `ActivePrinter`/registry state.
3. Connect Word's print job to the GAM queue and the GAM server's final file path/extension.
4. Resolve the relationship between print completion and EMWAT's document/response lifecycle.


## Parallel BPL callsite trace — printer discovery and print boundary (2026-11-24)

A TD32 callsite scan of the exact repository BPL (`analysis-input/EmwatMethods.bpl1`) found 11 statically attributed Windows spooler API callsites. Important results:

- `Zanprinter.GetPrinterName` (`0x0047CAF0`) calls `EnumPrintersA` with flags `0x8` and information level `2`, then iterates `PRINTER_INFO_2`-sized entries and compares the printer-name field against the configured global name. This is a local-printer enumeration path, not proof of remote/shared-printer discovery.
- `Zanprinter.Finalization` (`0x0047D8BC`) opens the configured queue with `OpenPrinterA`, calls `GetPrinterA` at level `2`, reads the `PRINTER_INFO_2` field at offset `+0x48` (Status), compares it to `1`, and closes the handle. The comparison is consistent with checking the paused status bit; the precise user-visible policy still needs runtime confirmation.
- `Emwatutils.getPrinterNumJobs` (`0x00456258`) actually calls `OpenPrinterW` and returns the resulting printer handle (or zero). Its symbol name is misleading: the traced body does not call `EnumJobs` or calculate a job count.
- `BGPrintWithGamPrintOptions` (`0x004C5FF8`) calls that helper early, so opening/validating the selected printer handle is part of the background-print path.
- The same BPL contains Word `TWordDocument.PrintOut` / `TWordApplication.PrintOut` Automation wrappers and a large `BGPrintWithGamPrintOptions` routine. No direct `WritePrinter` callsite was identified in this import/callsite scan. This does not rule out indirect calls or submission performed by Word/another module.

**Updated conclusion:** printer discovery/selection is demonstrably part of the BPL; actual job submission still appears to cross the Word Automation PrintOut boundary rather than a proven direct WritePrinter call. Trace the PrintOut VMT slot and a controlled job before defining the Linux submission contract.


## 2026-11-24 — timer-driven print path and configuration

Additional source: workflow runs 45345628398 (OnControlerNotify) and 45347505938 (print-handler/controller).

- `OnControlerNotify` invokes `CostumizeRecAndCC` before `Get_Content(-1)`. The full `CostumizeRecAndCC` procedure calls Word Document vtable slot `+0x2BC` once on the normal path, with up to two additional attempts only when a prior call raises an exception. This is the same slot used by the `TWordDocument.PrintOutOld` Automation wrapper. The method sets `IsSavingNow` (+0x5C) while active and clears it on exit.
- This ties the timer-driven AutoSave/archive callback to Word print operations at the callsite level. The normal PrintOutOld call's relationship to the registered BeforePrint handler and the resulting spool job is still unknown; the exception retries should not be modelled as three unconditional jobs.
- The Word BeforePrint callback `WordAppDocumentBeforePrintBGPrint` checks the active document and print configuration and builds recipient/CC lists. `TEmwatDocPrintHandler.Execute` dispatches a stored method callback via helper `0x004677B8`; `TEDPController.SetPrintThread` stores a handler and method pointer. Direct static callsites do not yet establish the exact callback-to-thread ownership.
- Dynamic settings are stored under `HKCU\Software\Emwat\Dynamic Config`. The setting form exposes `Background Priniting`, `Dont Ask Save On Print`, `Save Before Print` and `AutoSaveInterval`; the interval is converted from seconds to milliseconds and clamped to a minimum of 10 seconds.

**Next print trace:** determine whether the three Document.PrintOutOld calls in CostumizeRecAndCC each reach the Word BeforePrint callback, map the 15-Variant COM call at `+0x3F0`, identify the active/default printer selection and correlate each resulting job with the GAM output file.


### Word COM submission callsite details

The expanded `BGPrintWithGamPrintOptions` trace resolves a two-stage Word Automation sequence:

- At `0x004C70B6`, the routine invokes vtable slot `+0x3F0` after preparing 15 Variant arguments. This slot matches the generated `TWordDocument.PrintOut` wrapper's COM dispatch.
- Immediately afterward, at `0x004C70CA`, it calls the generated `TWordApplication.PrintOutOld` wrapper at `0x00441E44` (the wrapper dispatches through the application's `+0x1E4` slot).

This is stronger evidence than the mere presence of Word PrintOut wrappers: the GAM background-print routine itself reaches the Word COM print boundary. The exact semantics of all 15 optional arguments and the reason for the subsequent PrintOutOld call still require argument-by-argument tracing and a controlled print job.

The separate `TEmwatDocPrintHandlerUnit.SeparteImages` caller at `0x004A02FB` invokes `CreateImageFile` (`0x004A0BA8`), which in turn calls `CreateTiff.PrintWordDoc` (`0x004A0A68`) for generated items. This is a second image-file preparation path; its extension, bytes and relationship to the final GAM spool output are not established by these names alone.


## 2026-11-24 — timer-driven print / ReadyToClose coordination

The `TWordViewer` VMT identifies `fBG_Printing` (+0x3C), `fDontAskSaveBeforePrint` (+0x3D), `fSaveBeforePrint` (+0x3E) and `ReadyToClose` (+0x5E). These are separate flags and must not be collapsed into a single print preference.

`OnControlerNotify` clears `ReadyToClose` during the timer callback, calls `CostumizeRecAndCC`, retrieves `Get_Content(-1)`, runs the local archive extraction path, then restores `ReadyToClose`. `WordAppDocumentBeforeSave` cancels the close if `ReadyToClose` is false.

`CostumizeRecAndCC` contains three calls through Word Document vtable slot `+0x2BC`, matching the `TWordDocument.PrintOutOld` wrapper. This ties the periodic recovery callback to Word print operations, but it remains unknown whether the three calls become separate spool jobs or are intercepted/coalesced by the registered BeforePrint handler.

The explicit BeforePrint path `BGPrintWithGamPrintOptions` reaches `TWordApplication.PrintOutOld` and also issues a 15-Variant COM call at slot `+0x3F0`; the slot identity and argument mapping remain open.


## 2026-11-24 — EMWAT's own Windows spooler selection and job matching

The expanded BPL callsite map provides a separate view of EMWAT's **own** spooler logic, upstream of the GAM virtual-printer driver/monitor.

### Queue discovery

`Zanprinter.GetPrinterName` at `0x0047CAF0` calls `EnumPrintersA` twice (size probe, then data retrieval) at level 2. It iterates `PRINTER_INFO_2A` records using the 0x54-byte record stride, compares the `pDriverName` field at offset `+0x10` against an embedded string at `0x0047CC64`, and on a match stores the corresponding `pPrinterName` field at offset `+0x04` in global `0x0062B310`.

This means the printer queue is discovered by a **driver-name match**, not by assuming that the installed queue is always named `GAMPrinter`. The literal at `0x0047CC64` still needs an independent string decode; do not hardcode its value from the nearby Zan/GAM branding alone.

### Paused-state check

`Zanprinter.Finalization` at `0x0047D8BC` uses the discovered name to call `OpenPrinterA`, then `GetPrinterA(level=2)`, and closes the handle. It checks the DWORD at `PRINTER_INFO_2A+0x48` against `1`, which corresponds to `PRINTER_STATUS_PAUSED`. The helper therefore includes an explicit paused-queue test. If the printer cannot be opened, the alternate branch raises an error rather than silently treating it as ready.

### Job/document matching

`Emwatutils.ExtractFileNameEX` at `0x004562C4` calls `EnumJobsW(level=1)` with a maximum request of 1000 jobs, first querying the required buffer size and then retrieving the `JOB_INFO_1W` array. It walks records at a 0x40-byte stride, reads `pDocument` at offset `+0x10`, and compares it with the supplied document-name string. It returns a Boolean indicating whether a matching document-name job is present.

This is a concrete queue-correlation primitive: EMWAT can search the Windows spool queue for a job whose document label matches a requested name. The exact higher-level caller and the point where that job is correlated with a GAM-generated file remain unresolved.

### Other spooler callsites

The expanded static import map also confirms:
- `Emwatutils.getPrinterNumJobs` is called from `BGPrintWithGamPrintOptions` before the explicit Word print path and opens a printer through `OpenPrinterW`; the exact count/query implementation behind its helper call still needs resolving.
- `EnumJobsW` is used by `ExtractFileNameEX`, not by the queue-discovery routine.
- `EnumPrintersA`/ `OpenPrinterA`/ `GetPrinterA` are used by the Zanprinter helper path, while other EMWAT utilities use wide-character spooler APIs.

### Linux compatibility consequences

1. Discover candidate queues by driver metadata where a migration/import mode needs to reproduce Windows matching; do not assume a queue-name-only lookup.
2. Model queue state explicitly, including paused vs ready.
3. Support document-name/job correlation independently of queue enumeration.
4. Keep the Windows spooler job identity and the GAM-produced output artifact as separate objects until the final hand-off is proven.

The evidence and limits above are also tracked in [the dedicated spooler analysis](EMWAT-PRINTER-SPOOLER-ANALYSIS.md).


## 2026-11-24 — confirmed GAM output format values

The `zvprtcfg` examples establish:
- `image.fileformat=1` → TIFF (Example 5).
- `image.fileformat=2` → JPEG (Example 6).

The extracted color, BW and Fax INIs all use `fileformat=1`; therefore their base output format is TIFF. The Fax profile additionally enables TIFF-FAX-specific fields such as page number, width/height adjustment and T4 options. Do not infer the numeric compression enum meanings from these settings alone.


## Output-format priority update

Because the shipped GAM queue profiles all set `image.fileformat=1`, and the `zvprtcfg` usage examples explicitly define value 1 as TIFF, **TIFF is now the first compatibility-test output target** for the Linux virtual printer. The color, BW and Fax profiles all select TIFF; their compression/profile differences must be preserved.

PDF may still be useful as an internal CUPS interchange format or an alternate output, but it must not be treated as the original GAM output contract. The exact EMWAT consumer hand-off (file path, stream, extension and whether it reads the TIFF directly) remains unresolved. Do not freeze the native architecture around PDF until that path is traced.
