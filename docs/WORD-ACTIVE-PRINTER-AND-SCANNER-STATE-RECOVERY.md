# Word printer automation and scanner preview state recovery

Evidence source: workflow run `45562585651`, artifact files generated from `analysis-input/EmwatMethods.bpl1`. This report records wrapper-level and state-management evidence only; it does not claim a completed end-to-end print or scanner hardware protocol.

## 1. Word ActivePrinter wrappers

TD32 resolves two exact wrappers:

- `0x0043FF40`: `TWordApplication.Get_ActivePrinter`
- `0x0043FFA0`: `TWordApplication.Set_ActivePrinter`

Both obtain the underlying automation interface through `0x0043E210`. The getter dispatches through vtable slot `+0x108`; the setter first converts the supplied `WideString` through Delphi's string helper and dispatches through slot `+0x10C`. This is strong evidence that EMWAT's Word automation layer can read and change Word's active printer through the Word application interface.

The wrappers do not identify the concrete printer string format, whether Word's selected printer is the Windows default queue, or which downstream EMWAT component changes the selection. Do not equate `ActivePrinter` with the OS default printer without runtime evidence.

## 2. Legacy Word PrintOut dispatch

`0x00441E44` is `TWordApplication.PrintOutOld`. It resolves the application automation interface through `0x0043E210` and dispatches through vtable slot `+0x1E4`. This is distinct from the ActivePrinter getter/setter slots and distinct from the 18-Variant callsite in `BGPrintWithGamPrintOptions` (`0x004C5FF8`). The previously documented 18-vs-17 argument discrepancy remains unresolved; this wrapper does not resolve it.

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

The constructor initializes several interface/object fields at offsets `+0xC8` through `+0xD8`, stores a controller-like reference at `+0x48), and retains another object at `+0x50`. `DoOnTerminate` releases the five fields at `+0xC8..+0xD8`, releases and clears `+0x48` and `+0x40`, and invokes a method through the interface stored at `+0x44`. This is lifecycle/ownership evidence, not enough to assign semantic names to each field.

The CC/receiver routines enumerate two interface-backed collections and merge values into string fields at `+0x60` and `+0x64`, with a delimiter/formatting helper. This supports that the handler prepares recipient/CC metadata for document processing. The exact collection types, field names, and business meaning are not yet proven.

## 4. Scanner preview page metadata

`0x0061D100` is `TfrmGScanPreview.GetImagePageNumber`. It obtains a count through ImageGear helper `0x004AFED8`, loops over page indices, and calls `0x004AFEE8` to retrieve per-page metadata into local output values. It assembles a three-field Variant-like record (each field tagged `0x11`) and calls `0x00403368` to serialize/format it into a shared state field. It also clears/updates shared status fields around the operation. This method is therefore a page-metadata aggregation/request helper, not merely a page-number getter.

`0x0061D250` is `GetImgSize`. It calls `IG_page_count_get` (thunk `0x004AFEA8`) on the preview path, reads a value through interface slot `+0x114`, and for multipage input iterates page indices to call interface slot `+0x3C` with each index. It then updates an interface property through slot `+0x10C` and toggles a control's visibility. This establishes a page-count-driven UI refresh path; it does not prove image resampling or scanner resolution behavior.

## 5. Scanner selection

`0x0061DEF4` is `TfrmGScanPreview.SelectScanner`. It resets a state byte at `this+0x456`, consults a helper at `0x0061E3C8`, and on the selection path uses the form's window handle and path/configuration field at `this+0x458) to call `0x004AFF30` with mode-like values `0x28` or `2`. It then refreshes UI/state through `0x0061D100`, invokes `0x0061D3BC`, and validates the ImageGear handle at `this+0x428` using `IG_image_is_valid` (`0x004AFEC0`). The call target `0x004AFF30` has not yet been semantically resolved; do not assume its mode values mean scanner selection modes until the next import/caller trace establishes that.

## 6. Implementation constraints and open work

- Model Word active-printer access as an automation adapter with separate get/set operations. Keep OS default-printer discovery as a separate capability.
- Recover `Zanprinter.GetPrinterName`, `SetPrinterForTiffout`, `CheckPrinterPaused`, install/configuration paths, and their callsites before implementing printer selection or TIFF routing.
- Keep the 18-Variant print callsite separate from the 17-argument wrapper until the true dispatch ABI is established.
- Keep scanner page metadata separate from physical output-file count and from a multipage TIFF container's page count.
- Resolve `0x004AFF30`, `0x004AFED8`, and `0x004AFEE8` against imports/callers before assigning external API names or C prototypes.
- Static disassembly does not validate actual Word, printer driver, scanner, ADF, duplex, or hardware behavior.

## Evidence

- Workflow: `https://github.com/meicamghe/EMWAT-Linux/actions/runs/45562585651`
- Word artifact: `emwat-parallel-word-print`
- Image artifact: `emwat-parallel-image-ui`
