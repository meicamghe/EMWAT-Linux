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
