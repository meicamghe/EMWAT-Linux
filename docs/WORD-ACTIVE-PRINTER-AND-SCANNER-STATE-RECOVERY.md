# Word printer automation and scanner preview state recovery

Evidence source: workflow runs `45562585651` and `45563007730`, with the latter's `emwat-parallel-image-ui` artifact generated from `analysis-input/EmwatMethods.bpl1`. This report records wrapper, import-table, and static control-flow evidence only; it does not claim a completed end-to-end print or scanner hardware protocol.

## 1. Word ActivePrinter wrappers

TD32 resolves two exact wrappers:

- `0x0043FF40`: `TWordApplication.Get_ActivePrinter`
- `0x0043FFA0`: `TWordApplication.Set_ActivePrinter`

Both obtain the underlying automation interface through `0x0043E210`. The getter dispatches through vtable slot `+0x108`; the setter first converts the supplied `WideString` through Delphi's string helper and dispatches through slot `+0x10C`. This is strong evidence that EMWAT's Word automation layer can read and change Word's active printer through the Word application interface.

The wrappers do not identify the concrete printer string format, whether Word's selected printer is the Windows default queue, or which downstream EMWAT component changes the selection. Do not equate `ActivePrinter` with the OS default printer without runtime evidence.

## 2. Legacy Word PrintOut dispatch

`0x00441E44` is `TWordApplication.PrintOutOld`. It resolves the application automation interface through `0x0043E210` and dispatches through vtable slot `+0x1E4`. This is distinct from the ActivePrinter getter/setter slots and distinct from the 18-Variant callsite in `BGPrintWithGamPrintOptions` (`0x004C5FF8`). The 18-vs-17 argument discrepancy remains unresolved; this wrapper does not resolve it.

## 3. TEmwatDocPrintHandler lifecycle

TD32 identifies the following methods in `frmWordPrintOptionUnit`:

- `0x004A5C10`: constructor
- `0x004A5D78`: `DoOnTerminate`
- `0x004A8E58`: `ForgotMe`
- `0x004A8F78`: `GetDocFieldName`
- `0x004A8FCC`: `PrepareDoc`
- `0x004A90D4`: `SetCCValueForMain`
- `0x004A9464`: `SetCCValueForArchive`
- `0x004A9884`: `SetReceiversValue`
- `0x004A9A08`: `SetReceiversValueForSelected`

The constructor initializes several interface/object fields at offsets `+0xC8` through `+0xD8`, stores a controller-like reference at `+0x48`, and retains another object at `+0x50`. `DoOnTerminate` releases the five fields at `+0xC8..+0xD8`, releases and clears `+0x48` and `+0x40`, and invokes a method through the interface stored at `+0x44`. This is lifecycle/ownership evidence, not enough to assign semantic names to each field.

The CC/receiver routines enumerate two interface-backed collections and merge values into string fields at `+0x60` and `+0x64`, with a delimiter/formatting helper. This supports that the handler prepares recipient/CC metadata for document processing. The exact collection types, field names, and business meaning are not yet proven.

## 4. Scanner preview error aggregation (symbol name is misleading)

`0x0061D100` is named `TfrmGScanPreview.GetImagePageNumber` in TD32, but the expanded import-table and body trace shows that it is not a page-number getter:

- `0x004AFED8` is an import thunk to `IG_error_check` (IAT `0x00630D0C`).
- `0x004AFEE8` is an import thunk to `IG_error_get` (IAT `0x00630D04`).
- `0x004AFEE0` is an import thunk to `IG_error_clear` (IAT `0x00630D08`).

The body calls `IG_error_check`, uses its return value as the iteration bound, calls `IG_error_get` for each zero-based index with several output pointers, builds an aggregated string, and publishes a three-field Variant-like record through `0x00403368`. It then calls `IG_error_clear`. The direct callsite inventory also shows these error APIs used by `TGearImgProc.CheckOutputParameter` (`IG_error_check` at `0x004EEB81`, `IG_error_get` at `0x004EEBBA`, `IG_error_clear` at `0x004EEC09`) and `TGearImgProc.GetForceSinglePage` (`IG_error_get` at `0x004EF0A7`). The exact meaning and types of the error fields, and the external serialization contract, remain to be recovered. Do not model `GetImagePageNumber` as scanner page metadata.

The actual page-count path is separate: `0x0061D250` (`GetImgSize`) calls `IG_page_count_get` through thunk `0x004AFEA8`, then iterates page indices and updates the preview/page interface. This is page-count-driven UI behavior, not evidence of source-image resampling or scanner resolution changes.

## 5. Scanner API import identities and callsites

The PE import inventory resolves the relevant ImageGear thunks exactly:

| Thunk VA | IAT VA | Imported API |
|---|---:|---|
| `0x004AFF30` | `0x00630CE4` | `IG_scan_pages` |
| `0x004AFF28` | `0x00630CE8` | `IG_scan_source_select` |
| `0x004AFED8` | `0x00630D0C` | `IG_error_check` |
| `0x004AFEE8` | `0x00630D04` | `IG_error_get` |
| `0x004AFEE0` | `0x00630D08` | `IG_error_clear` |

Direct IAT/thunk scanning found three callsites to `IG_scan_pages`:

- `TGearImgProc.SelectScanner` at `0x004EFA96`; it stores the return value in object field `+0x4C`.
- `TfrmGScanPreview.SelectScanner` at `0x0061E036` and `0x0061E059`; these are two separate calls in the same method, with the second call followed by error aggregation through `0x0061D100`.

The import `IG_scan_source_select` (`0x004AFF28`) has two direct callsites:

- `TGearImgProc.SetCurrentPage` at `0x004EFF83`, after an interface/vtable call whose return value is passed as the sole stack argument.
- `TfrmGScanPreview.ShowCropRectangle` at `0x0061E3DF`, after helper `0x004049CC` produces the argument.

This establishes the imported function identities and direct callsite shapes, but the usage of `IG_scan_source_select` in `SetCurrentPage` and `ShowCropRectangle` is not self-explanatory. It does **not** establish either API's full prototype, calling convention, ownership rules, or the meaning of the `0x28` / `2` values. Do not infer semantic equivalence from the Delphi wrapper names.

## 6. Implementation constraints and open work

- Model Word active-printer access as an automation adapter with separate get/set operations. Keep OS default-printer discovery as a separate capability.
- Recover `Zanprinter.GetPrinterName`, `SetPrinterForTiffout`, `CheckPrinterPaused`, install/configuration paths, and their callsites before implementing printer selection or TIFF routing.
- Keep the 18-Variant print callsite separate from the 17-argument wrapper until the true dispatch ABI is established.
- Keep scanner error aggregation, scanner page metadata, physical output-file count, and a multipage TIFF container's internal page count as distinct concepts.
- Recover the import callsites and ABI for `IG_scan_pages` and `IG_scan_source_select`; do not infer prototypes from the stack shape alone.
- Static disassembly does not validate actual Word, printer driver, scanner, ADF, duplex, or hardware behavior.

## 6. GAM printer selection and configuration string inventory

### 6.1 Exact Winspool API and driver matching

The run-22 artifact resolves helper thunk `0x004044CC` exactly to `winspool.drv!EnumPrintersA` through IAT `0x0062F9F0`; this is ANSI, not Unicode. `Zanprinter.GetPrinterName` (`0x0047CAF0`) calls it twice using the same raw parameters:

- `Flags=8`
- `Name=NULL`
- `Level=2`
- First call: `pPrinterEnum=NULL`, `cbBuf=0`, with `pcbNeeded` and `pcReturned` output pointers
- Second call: allocated output buffer and required byte count from the first call

The routine walks the returned records using a `0x54`-byte stride, compares the field at offset `+0x10` with the exact driver-name string `zvprt1`, and copies the field at offset `+0x04` into global Unicode string storage `0x0062B310`. On 32-bit Windows, these offsets and stride match `PRINTER_INFO_2A` (`pPrinterName` at +0x04, `pDriverName` at +0x10, structure size 0x54). The matching queue is therefore selected by **driver name** `zvprt1`, and the returned value is its **printer/queue name**. This is now directly grounded in the resolved `EnumPrintersA` thunk and callsite; it is no longer merely an ANSI/Unicode guess.

Direct callers of `EnumPrintersA` are the two calls inside `GetPrinterName` at `0x0047CB37` and `0x0047CB7D`. Other nearby Winspool imports have separate IAT thunks/callsites and must not be conflated with this enumeration path.

### 6.2 Driver install and configuration-directory discovery

- `Zanprinter.InstallZanPrinter` (`0x0047CC6C`) calls `GetPrinterName`; when a matching queue is found it copies global `0x0062B310` into its output string and returns success.
- `Zanprinter.GetZanInstallDir` (`0x0047CC94`) polls `GetPrinterName` up to 300 times, sleeping `0x64` ms between attempts. This is a bounded ~30-second wait for the driver queue to appear, not proof that the installer completed successfully.
- Its missing-printer branch constructs a path containing `GAMPrinterSetup.exe` and passes the decoded verb strings `Open` / `RunAs` through helper `0x00404494`. The exact helper/API contract and which branch selects each verb remain pending.
- `Zanprinter.GetZanConfigurationDir` (`0x0047D054`) opens the exact registry subkey `HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\zvprt50` (root handle `0x80000002`, access mask `0x20019`) and queries value `UninstallString`. If the registry path/value cannot be used, it falls back to appending `zvprt50\\` to the supplied path. The precise normalization of the returned uninstall string is still being traced.
- `Zanprinter.SetPrinterForTiffout` (`0x0047D238`) calls `GetZanConfigurationDir`, reads `configure.ini` / section `policy` / key `allusersfolder`, and constructs paths involving `zvprt50\\` and `save.ini`. The same routine references `save.ini` keys `basefilename` and `save`. The meaning of the numeric return/branch values and exact helper API semantics are not yet mapped.

### 6.3 INI keys consumed by the pause/configuration check

`Zanprinter.CheckPrinterPaused` (`0x0047D448`) references these decoded literals:

- `save.ini`: `folder`, `save`, `basefilename`, `No Dialogs`, `popupdialog`, `filexistact` (with literal default/value strings including `1`)
- `image.ini`: `fileformat=tiff`, `image=256`, `imagecolor=lzw`, `compression=0`, `pagetype=Each page as a single strip`, `rowsperstrip`
- `general.ini`: `hidestsdialog`, `sentinel`, `sentinelfile=JobFinishes.GAM`

These are static key/value strings and the observed sequence of helper calls, not proof of every effective value under every installed-driver version. Do not hardcode these as Linux defaults until their read/write helper contracts, path resolution and actual generated INI files are verified.


## Evidence

- Workflow runs: `https://github.com/meicamghe/EMWAT-Linux/actions/runs/45562585651`, `https://github.com/meicamghe/EMWAT-Linux/actions/runs/45563007730`
- Artifacts: `emwat-parallel-word-print`, `emwat-parallel-image-ui`
- Import inventory: `parallel-re/image-io/imports.md` from run `45563007730`
