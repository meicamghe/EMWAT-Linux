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

The body calls `IG_error_check`, uses its return value as the iteration bound, calls `IG_error_get` for each zero-based index with several output pointers, builds an aggregated string, and publishes a three-field Variant-like record through `0x00403368`. It then calls `IG_error_clear`. The exact meaning and types of the error fields, and the external serialization contract, remain to be recovered. Do not model this method as scanner page metadata.

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

Two independently named high-level methods call the `IG_scan_pages` thunk:

- `TfrmGScanPreview.SelectScanner` at `0x0061DEF4` calls `0x004AFF30` with the form window handle, path/configuration string, a mode-like value of `0x28` or `2`, and a final value of `1`.
- `TGearImgProc.SelectScanner` at `0x004EF9CC` also calls `0x004AFF30`, then stores the returned value in its result/state field at `+0x4C`.

This establishes the imported function identity and the observed callsite argument shapes. It does **not** establish the ImageGear prototype, calling convention, ownership rules, or the meaning of the `0x28` / `2` values. In particular, do not rename the imported API to scanner-source selection based on the Delphi wrapper name.

The import `IG_scan_source_select` (`0x004AFF28`) is present in the PE import table, but its callsites have not yet been established by the inspected artifact. Its relationship to the two `SelectScanner` methods remains open.

## 6. Implementation constraints and open work

- Model Word active-printer access as an automation adapter with separate get/set operations. Keep OS default-printer discovery as a separate capability.
- Recover `Zanprinter.GetPrinterName`, `SetPrinterForTiffout`, `CheckPrinterPaused`, install/configuration paths, and their callsites before implementing printer selection or TIFF routing.
- Keep the 18-Variant print callsite separate from the 17-argument wrapper until the true dispatch ABI is established.
- Keep scanner error aggregation, scanner page metadata, physical output-file count, and a multipage TIFF container's internal page count as distinct concepts.
- Recover the import callsites and ABI for `IG_scan_pages` and `IG_scan_source_select`; do not infer prototypes from the stack shape alone.
- Static disassembly does not validate actual Word, printer driver, scanner, ADF, duplex, or hardware behavior.

## 6. GAM printer selection and configuration string inventory

The expanded Word/printer artifact decodes the following static evidence:

- `Zanprinter.GetPrinterName` is `0x0047CAF0`. It calls helper `0x004044CC` with arguments shaped like a Winspool `EnumPrinters` level-2 query (flags value 8, level 2, initially null output buffer, and output pointers). It then walks returned records with a `0x54`-byte stride, compares the field at `+0x10` with the exact string `zvprt1`, and copies the field at `+0x04` into global string storage `0x0062B310`.
- The `0x54` stride and `+0x04`/`+0x10` fields match the layout positions of `pPrinterName` and `pDriverName` in Winspool `PRINTER_INFO_2`. This strongly suggests that EMWAT locates the installed printer by driver name `zvprt1` and returns its printer name. The helper thunk `0x004044CC` has not yet been resolved to `EnumPrintersA` versus `EnumPrintersW`; keep the ANSI/Unicode API variant unconfirmed.
- `Zanprinter.InstallZanPrinter` (`0x0047CC6C`) calls `GetPrinterName` and updates global printer-name state when it succeeds.
- The decoded string constants used by the printer configuration routines include `GAMPrinterSetup.exe`, `ZVPsrc\\save.ini`, `configure.ini`, `policy`, `allusersfolder`, and `zvprt50\\`.
- The `CheckPrinterPaused` path (`0x0047D448`) references `save.ini` keys/values including `folder`, `save`, `basefilename`, `No Dialogs`, `popupdialog`, `filexistact`; `image.ini` strings include `tiff`, `fileformat`, `image`, `256`, `imagecolor`, `lzw`, `compression`, `0`, `pagetype`, `Each page as a single strip`, and `rowsperstrip`; `general.ini` strings include `hidestsdialog`, `general`, `sentinel`, `JobFinishes.GAM`, and `sentinelfile`.

These are recovered literals and structure/call-shape evidence, not proof of every configuration value's active runtime effect. The `EnumPrinters` thunk, registry/path resolution, and the actual queue/driver installation state still require confirmation.

## Evidence

- Workflow runs: `https://github.com/meicamghe/EMWAT-Linux/actions/runs/45562585651`, `https://github.com/meicamghe/EMWAT-Linux/actions/runs/45563007730`
- Artifacts: `emwat-parallel-word-print`, `emwat-parallel-image-ui`
- Import inventory: `parallel-re/image-io/imports.md` from run `45563007730`
