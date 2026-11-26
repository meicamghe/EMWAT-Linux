## 2026-11-26 — Word/GAM print-thread handoff

Run 49's Word/Printer/COM artifact confirms that `TCreateTiff.SeparteImages` (`0x004A0148–0x004A0A67`) performs document/page preparation, calls printer discovery/configuration and pause-state checks, then enters `TCreateTiff.THidePrintingThread.Execute` (`0x004A0E88`). The pause-state check remains the `GetPrinterA` status-field check at `PRINTER_INFO_2A + 0x48` against `PRINTER_STATUS_PAUSED`.

The next unresolved stage is the hidden thread's indirect Word/Printer interface dispatch and its final spool-submission/completion signal. Presence of Winspool/VCL imports and this thread entrypoint is not proof of a successful real print job. See `docs/REVERSE-ENGINEERING-PARALLEL-FOLLOWUP-2026-11-26.md`.

# GAM / Zan printer configuration recovery

Date: 2026-11-26  
Evidence: parallel reverse-engineering runs 22, 24, 27, 28, 32 and 34; Word/print artifacts and TD32 procedure traces plus PE IAT thunk resolution for `EmwatMethods.bpl1`.

This document records static evidence for the EMWAT GAM/Zan virtual-printer setup/configuration path. It does not claim that the driver installs or prints successfully under Wine or Linux.

## 1. Recovered Windows API boundaries

| VA | Resolved target | Use evidenced by callers |
|---|---|---|
| `0x004044CC` | `winspool.drv!EnumPrintersA` | Enumerate Level-2 printer records to locate the GAM driver instance |
| `0x00402674` | `advapi32!RegOpenKeyExW` | Open the GAM printer uninstall registry key |
| `0x0040267C` | `advapi32!RegQueryValueExW` | Read its `UninstallString` value |
| `0x0040266C` | `advapi32!RegCloseKey` | Close the opened registry key |
| `0x00402754` | `kernel32!GetPrivateProfileIntW` | Read integer policy from `configure.ini` |
| `0x0040275C` | `kernel32!GetPrivateProfileStringW` | Read `basefilename` from `save.ini` |
| `0x00402910` | `kernel32!WritePrivateProfileStringW` | Write the recovered save/image/general INI settings |
| `0x004044AC` | `shell32!SHGetFolderPathW` | Resolve Windows special-folder paths |
| `0x00404494` | `shell32!ShellExecuteW` | Launch `GAMPrinterSetup.exe` using `Open` or `RunAs` verb |
| `0x00402818` | `kernel32!GetVersionExW` | Read OS version for folder/elevation policy |
| `0x00403438` | `kernel32!Sleep` | Wait between printer installation/discovery attempts |
| `0x00404F4C` | VCL `Printers.Printer` | Obtain the global VCL printer object |
| `0x00404F54` | VCL `TPrinter.Refresh` | Refresh installed printer enumeration |
| `0x004032C0` | Delphi `FileExists` | Test file/path existence |
| `0x004032C8` | Delphi `DirectoryExists` | Test directory existence |
| `0x00403320` | Delphi `ExtractFileName` | Extract the executable/file name from a path |
| `0x00403350` | Delphi `StrComp` | Compare printer/configuration strings |
| `0x00401368` | RTL `UStrCat` | Concatenate two Unicode strings |
| `0x00401370` | RTL `UStrCat3` | Concatenate three Unicode strings |

### 1.1 Exact printer-instance match

`Zanprinter.GetPrinterName` (`0x0047CAF0`) calls `EnumPrintersA` (`0x004044CC`) twice: first to obtain the required buffer size, then to retrieve Level-2 printer records. The call uses enumeration flags `8` and information level `2`.

The returned records are traversed with stride `0x54`, consistent with the x86 `PRINTER_INFO_2A` record layout. The routine compares the record's driver-name pointer at offset `+0x10` against the exact literal `zvprt1`; on a match it copies the printer-name pointer at offset `+0x04` into global active-printer-name storage (`0x0062B310`). This is stronger than matching a friendly printer display name: the driver identity is the filter.

`Zanprinter.InstallZanPrinter` (`0x0047CC6C`) calls this lookup and returns a status based on whether the matching driver instance is found. Keep this discovery check separate from the later installer launch and TIFF configuration routines.

## 2. Installer discovery and launch

- The driver name literal is `zvprt1`; `GetPrinterName` enumerates `PRINTER_INFO_2A` records and selects the record whose driver-name field equals that literal. The setup executable literal is `GAMPrinterSetup.exe`.
- `Zanprinter.GetZanInstallDir` (`0x0047CC94`) calls the printer-install check (`0x0047CAF0`). When installation is needed, it constructs a path to `GAMPrinterSetup.exe` and calls `ShellExecuteW`; the verb literals are `Open` and `RunAs`.
- The routine calls `GetVersionExW` and chooses the launch verb through an OS-version branch. It then waits in a loop of at most 300 iterations, with `Sleep(100)` and VCL printer refresh calls, before continuing. The loop is bounded at roughly 30 seconds of requested sleep time, excluding call overhead.
- The helper inspects the installed-printer state; its exact return/result contract is not a Linux API and should not be emulated as a successful install merely because the process launched.

## 3. Registry-based configuration directory

`Zanprinter.GetZanConfigurationDir` (`0x0047D054`) uses:

- Registry root: `HKEY_LOCAL_MACHINE` (`0x80000002`).
- Subkey: `Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\zvprt50`.
- Value: `UninstallString`.
- APIs: `RegOpenKeyExW`, `RegQueryValueExW`, and `RegCloseKey`.

If the registry lookup does not provide a usable directory, the procedure falls back through `SHGetFolderPathW` with CSIDL `0x26` (Program Files) and appends the `zvprt50` directory. Keep the registry path and fallback as distinct branches; do not hardcode a single Windows path for Linux.

## 4. TIFF output directory policy

`Zanprinter.SetPrinterForTiffout` (`0x0047D238`) first reads OS version and calls `GetZanConfigurationDir`. It reads:

- File: `configure.ini`
- Section: `allusersfolder`
- Key: `policy`
- Default: `1`
- API: `GetPrivateProfileIntW`

The `GetPrivateProfileIntW` call is `GetPrivateProfileIntW(L"allusersfolder", L"policy", 1, configure_ini_path)`. The resulting policy and OS major-version branch select Windows CSIDL `0x23` or `0x2e`. The routine then constructs a `zvprt50\\` path and checks it with `DirectoryExists`; if unavailable, it falls back through CSIDL `0x1a` (user AppData). This is a Windows folder policy; Linux must use an application-owned writable data/output directory rather than reproducing CSIDL values.

## 5. INI values written by printer configuration

`Zanprinter.CheckPrinterPaused` (`0x0047D448`) writes the following settings using `WritePrivateProfileStringW`. These are exact decoded section/key/value literals and callsite groupings:

| INI file | Section | Key | Value |
|---|---|---|---|
| `save.ini` | `save` | `folder` | dynamically assembled output directory |
| `save.ini` | `save` | `basefilename` | value read/assembled from the printer configuration path |
| `save.ini` | `save` | `popupdialog` | `No Dialogs` |
| `save.ini` | `save` | `filexistact` | `1` |
| `image.ini` | `image` | `fileformat` | `tiff` |
| `image.ini` | `image` | `imagecolor` | `256` |
| `image.ini` | `image` | `compression` | `lzw` |
| `image.ini` | `image` | `pagetype` | `0` |
| `image.ini` | `image` | `rowsperstrip` | `Each page as a single strip` |
| `general.ini` | `general` | `hidestsdialog` | `1` |
| `general.ini` | `general` | `sentinel` | `1` |
| `general.ini` | `general` | `sentinelfile` | `JobFinishes.GAM` |

The method also reads `save.ini` section `save`, key `basefilename`, through `GetPrivateProfileStringW`. The decoded literal `ZVPsrc\\save.ini` is used in the installation/configuration path logic. The exact final absolute paths depend on the registry and special-folder branches above.

## 6. Linux implementation implications

- This is now a concrete configuration contract for the legacy GAM printer, not proof of a usable Linux printer backend.
- Preserve the recovered output settings as compatibility metadata if the Linux implementation later writes TIFFs; do not assume that setting `fileformat=tiff` alone proves the full TIFF byte/layout contract.
- Do not write into arbitrary Windows-style shared directories. Resolve all Linux output paths under an explicit application-owned directory with normal path confinement and permissions.
- Do not launch the Windows setup executable as a Linux installation strategy. The installer is only one branch in the Windows recovery flow; driver installation, port/monitor registration and actual print output remain separate unresolved compatibility tasks.
- The printer discovery check and its pause/status return semantics still require a complete trace and a controlled runtime fixture.

## 7. Remaining questions

1. Decode the full return contract of `GetZanInstallDir` and `CheckPrinterPaused`, including all branches beyond the TD32 bounded output.
2. Trace how `InstallZanPrinter`/`GetPrinterName` handles multiple matching `zvprt1` instances, queue state and default-printer selection.
3. Establish how `ZVPsrc\\save.ini` and the selected `zvprt50` folder are related on clean installs versus upgrades.
4. Compare the configured TIFF output with a real file emitted by GAM Printer, including compression, strip organization, multipage handling and sentinel lifecycle.
5. Keep Wine/Windows driver installation experiments separate from native Linux printing implementation; do not claim parity until a real output fixture is compared.


## 9. Run 39/40 confirmation — queue identity and print-layer boundary (2026-11-26)

The successful Word artifacts from runs `45774122169` and `45779391301` independently confirm the printer-selection routine at `0x0047CAF0`:

- It calls `EnumPrintersA` with `PRINTER_ENUM_LOCAL` (`flags=8`), information level 2, and the standard size-query/fill-buffer sequence.
- It walks `PRINTER_INFO_2A` records using the observed `0x54`-byte stride.
- It compares `pDriverName` at record offset `+0x10` to the literal `zvprt1`; on the first match it copies `pPrinterName` at offset `+0x04` to global active-printer storage `0x0062B310`, then exits the loop.
- It does not select by queue name, default-printer status, or a status field in this routine. If multiple local queues use the same driver, the first enumeration match wins; no explicit disambiguation is visible here.

The `TCreateTiff.SeparteImages` caller checks `GetPrinterName` and calls `InstallZanPrinter` if no match is found. The same caller later enters the routine named `CheckPrinterPaused`, which invokes the recovered configuration writer path. The exact queue-status decision is still not fully mapped.

The VCL import inventory includes `TPrinter.Refresh`, `GetPrinterIndex`, `GetCanvas`, `NewPage`, `EndDoc`, and `BeginDoc`. The inspected Winspool import inventory does not show `StartDocPrinter`/`WritePrinter`; this is **not** proof that no spooler operation occurs elsewhere. It means the Linux design must not assume the Windows code submits a raw spooler buffer: the VCL printer/canvas path still needs a caller trace.

Next: trace `TCreateTiff.SeparteImages`, VCL `TPrinter` callsites, and the imported `OpenPrinter`/`GetPrinter`/`EnumJobsW` routines before finalizing queue-state or job-correlation behavior.

Evidence:
- Run 39 Word artifact `15096235579`, Image artifact `15095104593`.
- Run 40 Word artifact `15097418557`, Image artifact `15098092258`.
- Static binary evidence only; no Windows runtime print or Wine hardware acceptance is claimed.


## 10. Run 42 — TIFF producer and printer configuration chain (2026-11-26)

Workflow run `45782764971` completed successfully on commit `295fc6e513664abe211d2ebeeda1964f1fcd584f`. The Word/Printer and Image/Scanner jobs both uploaded artifacts; Native regression also passed. The Word artifact is `15098978072`.

The expanded `TCreateTiff.SeparteImages` trace (`0x004A0148`) establishes the following caller and setup chain:

- Direct callers are `TWordViwer.LoadDocument` at `0x004B7A9C` and `0x004B7ABD`.
- It calls `Zanprinter.GetPrinterName` (`0x0047CAF0`). If no matching local queue is found, it calls `InstallZanPrinter` (`0x0047CC94`); a failed install follows an error/abort branch.
- It then enters the printer configuration/finalization path and iterates the image collection through count/index virtual calls. The complete mapping from those virtual slots to the final printer canvas call remains open.
- `Zanprinter.CheckPrinterPaused` (`0x0047D448`) is a misleading method name: the recovered body reads/writes the GAM INI configuration defaults listed in section 5. The separately traced `Zanprinter.Finalization` routine (`0x0047D8BC`) is the queue-handle/status path documented in `EMWAT-PRINTER-SPOOLER-ANALYSIS.md`. Do not describe `CheckPrinterPaused` itself as the spooler pause-state check.

The same artifact confirms the imported VCL printer surface: `TPrinter.Refresh`, `Printer`, `GetPrinterIndex`, `GetCanvas`, `NewPage`, `EndDoc`, `BeginDoc`, and the ImageEn `TImageEnIO.PreviewPrintImage` import. Their presence is not yet a complete caller-level proof that all of them participate in `SeparteImages`; the VCL canvas/print submission chain remains a target for the next pass.

The workflow parser fix is now verified: the TIFF trace step completed and the Word/Printer artifact was uploaded. This is static reverse-engineering evidence only; it does not establish that GAM printing works under Wine or on a physical printer.

Evidence:
- Run 42 Word artifact `15098978072`.
- Run 42 Image artifact `15099188562`.
- Run 42 workflow `45782764971`: all three jobs passed.

## 11. Run 43 — configuration preparation versus spooler state (2026-11-26)

Workflow run `45783897821` completed its Word/Printer job successfully on workflow commit `e372fc188936ffcbeb54986630fe4981483a9577`. The Word artifact is `15099392610`.

The expanded traces refine the printer boundary:

- `Zanprinter.GetPrinterName` (`0x0047CAF0`) enumerates local Level-2 printer records and matches `PRINTER_INFO_2A.pDriverName` to `zvprt1`; it stores the first matching `pPrinterName` in global active-printer storage. This routine is discovery, not queue-state validation.
- `Zanprinter.SetPrinterForTiffout` (`0x0047D238`) resolves the GAM configuration directory, reads the `allusersfolder/policy` value from `configure.ini`, selects a Windows special-folder branch, constructs the output directory and checks directory availability. It is output-path/configuration preparation, not a spooler status query.
- `Zanprinter.CheckPrinterPaused` (`0x0047D448`) calls the two routines above and writes the recovered `save.ini`, `image.ini`, and `general.ini` settings through `WritePrivateProfileStringW`. Despite its symbol name, this body is the GAM INI configuration writer; do not interpret its Boolean return as a direct Winspool paused-state result.
- The separate `Zanprinter.Finalization` procedure (`0x0047D8BC`) is the actual queue-handle/status path: it discovers the queue, opens it with `OpenPrinterA`, obtains `PRINTER_INFO_2` using `GetPrinterA`, checks the status field at offset `+0x48` for `PRINTER_STATUS_PAUSED`, and closes the handle. See `docs/EMWAT-PRINTER-SPOOLER-ANALYSIS.md`.
- `Emwatutils.getPrinterNumJobs` (`0x00456258`) is a separate helper called from `TWordViewer.BGPrintWithGamPrintOptions`; the helper opens a queue through `OpenPrinterW`. Its name and caller establish a job-count role, but the complete API/result path is not yet decoded.
- `TCreateTiff.SeparteImages` (`0x004A0148`) calls printer discovery/configuration, checks a separate readiness helper, then iterates the image collection using virtual count/index operations. It subsequently enters a per-image processing loop. The precise VCL canvas and spool submission mapping remains unresolved.

### Linux design consequence

Keep four interfaces distinct: (1) queue discovery/selection, (2) GAM-compatible TIFF output-directory and INI policy, (3) queue paused-state inspection, and (4) queued-job counting/correlation. A CUPS implementation should map these to separate IPP/CUPS operations and must not treat successful configuration as proof that a queue is ready. Preserve the TIFF options as metadata until a real GAM-produced TIFF fixture establishes byte-level and multipage equivalence.

Evidence: Run 43 Word artifact `15099392610`, including `procedure-0047CAF0.md`, `procedure-0047D238.md`, `procedure-0047D448.md`, `printer-api/status-callers/open-printer-jobs-procedure.md`, and `printer-api/print-pipeline/procedure-004A0148.md`. Static analysis only; no Wine/Linux printer runtime success is claimed.


## 2026-11-26 — Run 50 hidden print-thread trace

Run 50 (45794156659) completed successfully; Word/Printer artifact 15104841284 is reviewed in docs/REVERSE-ENGINEERING-DEEP-FOLLOWUP-2026-11-26.md.

- TWordViewer.LoadDocument calls TCreateTiff.SeparteImages at 0x004B7A9C and 0x004B7ABD.
- SeparteImages resolves the configured printer through Zanprinter.GetPrinterName, calls SetPrinterForTiffout and the pause-state check, then calls THidePrintingThread.Execute at 0x004A0E88. The caller checks the returned Boolean and has an error path.
- GetPrinterName uses EnumPrintersA level 2 and walks PRINTER_INFO_2A records at 0x54-byte intervals. It matches the configured driver-name field at +0x10 and returns the printer-name field at +0x04.
- The pause-state gate checks PRINTER_INFO_2A +0x48 against PRINTER_STATUS_PAUSED (1).
- THidePrintingThread.Execute is 3,096 bytes, but only 1,885 bytes were decoded by the current trace; the remaining 1,211 bytes are unresolved. The decoded section contains indirect interface dispatches, page-index loops, file-stream operations and repeated file-existence polling with sleeps/retries.
- The TWordApplication ActivePrinter getter/setter wrappers have no direct TD32 CALL xrefs in this artifact. Do not claim the code explicitly sets ActivePrinter.
- Actual Winspool job submission/completion and final output delivery remain unproven. No physical printer or Wine printer acceptance was performed.
