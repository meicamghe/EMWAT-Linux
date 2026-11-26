# Reverse-engineering report — Run 49

Date: 2026-11-26  
Repository: `meicamghe/EMWAT-Linux`  
Branch: `feature/recovery-retention-policy`  
Analyzed input: `analysis-input/EmwatMethods.bpl1`  
Workflow run: [Run 49](https://github.com/meicamghe/EMWAT-Linux/actions/runs/45788814934)

## CI result

All three Run 49 jobs completed successfully:

- `native-regression`: native build/regression and Python bridge regression passed.
- `word-print-com`: printer/Word/COM reverse-engineering trace completed and artifact uploaded.
- `image-ui-and-vmt`: scanner paging, connector helpers, XML classes, ImageGear callsites and preserved image form resource inventory completed and artifact uploaded.

This is CI and static-analysis evidence. It does not establish physical scanner/ADF/duplex operation, real printer queue operation, or end-to-end Almas compatibility.

## 1. ScanCommand paging trace — newly extended

The deep trace for `TScanCommand.GetNextPage` at `0x004F2558` now covers the full TD32 procedure range:

- Procedure range: `0x004F2558–0x004F2A93`
- Size: `0x53C` (1,340 bytes)
- Skipdata trace coverage: `1340/1340`
- Capstone `.byte` pseudo-instructions: 16

Important interpretation warning: full byte coverage is not equivalent to full instruction decoding. The `.byte` entries are explicitly undecoded data; some regions in the procedure also contain data that Capstone may render as plausible but meaningless instructions. Control-flow targets and branch reachability must be checked before interpreting those regions as executable code.

### Confirmed control-flow observations

- The method first invokes `VerifyConstraints` (`0x004F2C4C`) and `LoadRequestXML` (`0x004F2B18`).
- The branch discriminator is `FIsNextPageRequest` at instance offset `+0x29`.
- In the next-page branch it logs `SCAN: NextPage Requested.`, examines `FPreviousReturnedFileName` at `+0x2C`, compares against the literal `_P`, updates state bytes at `+0x1D` and `+0x1E`, constructs/updates `ResultImage` at `+0x20), and calls `HasError`.
- In the new-document branch it logs `SCAN: NewDocument.`, creates or selects a result image according to the state bytes, then continues through the response/result handling path.
- The response path writes the literal status `success` and encoding `base64` into response XML objects, and associates the selected result image's filename with the response image node.
- Error handling includes the literal `error` and the message prefix `<ScanDoc HasError>. ErrorXML: `.

The meaning of the four-entry table walked from global address `0x0062A7F0`, the exact state enum values, and the full external connector paging protocol remain unresolved. Do not treat `_P` as a complete page-number protocol based on this comparison alone.

## 2. Scan response XML contract — stronger field evidence

The response XML class metadata and property accessors expose these names:

- Root response properties: `status`, `errorCode`, and `scaned-image` (the source spelling is retained exactly).
- Nested image properties: `imageName` and `encoding`.
- The response XML object is constructed in `TScanCommand` construction at `0x004F21DC–0x004F2294`; the response object is stored at instance offset `+0x34`.
- The XML accessors are represented by TD32 symbols in `IPResultImageUnit`, including getters/setters for status, error code, image name and encoding.

These are source-level field names and class/accessor evidence. Actual values and error-code semantics still require runtime protocol captures. The strings `success` and `base64` are observed constants in this binary, not synthetic test fixtures; their use in a real response still needs an end-to-end capture.

## 3. Connector dictionary keys

The `TScanDocument.PerformMethod` trace at `0x005EE82C` contains dictionary lookups for these exact keys:

- `wordConfig`
- `wordBody`
- `letterImages`
- `signData`

This establishes that the connector handler checks these keys in its input dictionary. It does not yet establish the full data type, optionality, or downstream semantics of each value.

In `TFaxDocument.PerformMethod` (`0x005EEB48–0x005EEDFB`), the `.tmp` literal is passed through helper `0x00454B9C`; its helper-produced string is then passed to `GetNextPage`. Separately, `document` at `0x005EED6C` is passed to `TDictionary<String, Variant>.SetItem` at `0x0046D2E4`. This is a dictionary write/update, not evidence of a dictionary read. The exact value semantics remain open.

## 4. Image editing and acquisition APIs

The IAT/callsite trace resolves these ImageGear exports from `GEAR32PD.DLL`:

- `IG_IP_flip` — thunk `0x004AFED0`; direct callers include `0x004F021F`, `0x0061E5CC`, `0x0061E65C`.
- `IG_IP_rotate_multiple_90` — thunk `0x004AFEC8`; direct callers include `0x004EF187`, `0x0061E5FC`, `0x0061E62C`.
- `IG_page_count_get`, `IG_load_FD`, `IG_save_FD`, `IG_load_file`, `IG_save_file`, image validation/deletion and error APIs are also present in the import/callsite inventory.

ImageEn IAT evidence identifies:

- `TImageEnMIO.Acquire` — IAT `0x00630D84`; direct caller `0x0050A364`.
- `TImageEnMIO.LoadFromFileAuto` — IAT `0x00630D74`; direct callers include `0x00508B88` and `0x0050A4D3`.
- `TImageEnMIO.SaveToFile` — IAT `0x00630D8C`.
- `TImageEnMIO.SaveToFileTIFF` — IAT `0x00630D90`; direct caller `0x0050B6A0`.
- `TImageEnMIO.PrintImage` — IAT `0x00630D70`; direct caller set is recorded in the artifact.

Imports and callsites prove that the binary references these APIs; they do not by themselves prove that the complete acquisition or printing workflows succeed on Linux/Wine.

## 5. Preserved UI resources

The artifact inventories the original Delphi form resources without modifying them. Relevant observations:

- `TfrmGScanPreview`: scan preview surface, cancel/register controls, rotate left/right, crop, horizontal/vertical flip, original-image control, and TIFF/JPEG selection.
- `TfrmImageTools`: `TImageEnMView` image collection, add-image, scan and print toolbar controls, thumbnail selection and drag/drop event bindings.
- `TfrmSimpleImageEditor`: paint-box based image editor with pointer interaction and paint handlers.

This is resource inventory evidence only. It does not imply that each event handler or image operation has been fully traced or implemented in the Linux replacement.

## 6. Word / printer artifact reconfirmation

Run 49's Word/Printer/COM artifact reconfirms the previously documented static call path:

- Printer selection enumerates local printers and matches the `zvprt1` driver name.
- The actual pause-status check is in `Zanprinter.Finalization` (`0x0047D8BC`), which opens the selected printer and checks the status field at `PRINTER_INFO_2A + 0x48` against `PRINTER_STATUS_PAUSED`.
- `TCreateTiff.SeparteImages` at `0x004A0148` is called from the WordViewer load path.
- ImageEn/VCL printer APIs are present, but a complete real spool submission chain and successful queue operation have not been demonstrated.

## 7. Next investigations

1. Resolve `GetNextPage` control-flow targets around embedded data and validate the four-entry state table at `0x0062A7F0`.
2. Trace the complete XML request and response lifecycle, including the external caller's interpretation of `status`, `errorCode`, `scaned-image`, `imageName` and `encoding`.
3. Recover the precise meaning of the helper-produced `.tmp` string and the `document` Variant value.
4. Trace the ImageEn acquisition callsite through TWAIN/WIA selection, device configuration, page transfer and TIFF save.
5. Continue the Word-to-GAM print path until the actual spool submission and completion signals are identified.
6. Convert confirmed behavior into protocol fixtures and regression tests only after runtime evidence exists.

## Evidence artifacts

- `emwat-parallel-image-ui` — scanner, XML, ImageGear/ImageEn, VMT and form-resource analysis.
- `emwat-parallel-word-print` — Word, GAM printer, Winspool and COM analysis.

## 8. Request constraints and next-page detection — follow-up trace

A second pass over `TScanCommand.VerifyConstraints` (`0x004F2C4C–0x004F323F`) and `HasError` (`0x004F2A94–0x004F2B17`) narrows several previously open questions:

- The request parser constructs/stores the request XML object in `FRequestXML +0x30`.
- `TXMLConfigType` properties are read, including `Type`, `DriverDialog`, `ImageEditor`, `MultiJpegSupport`, and `PreviousImageName`.
- `PreviousImageName` is copied into `FPreviousReturnedFileName +0x2C`. Its string length is checked; a non-empty value sets `FIsNextPageRequest +0x29` to true. Thus the next-page branch is driven by the presence of the previous image name, not by an independently proven Boolean request flag.
- The four `TXMLConstraintsType` numeric properties are `ColorDepth`, `MinResolution`, `MaxResolution`, and `MaxFileSize`. Their parsed values are stored in the constraint area beginning at `TScanCommand +0x08` (four numeric slots at `+0x08/+0x0C/+0x10/+0x14`).
- `FHasConstraints +0x38` is set according to whether the sum of those four stored values is greater than zero. A zero-valued constraint set is therefore treated as no active constraints by this code path.
- The request parser also reads literal values `none`, `jpg`, `yes`, and `no` while setting format/option flags. Their precise XML element-to-field mapping should be retained from the individual getter traces rather than inferred solely from string order.
- In `HasError`, when `FIsNextPageRequest` is true, the code passes `FPreviousReturnedFileName` into `TResultImage.ShiftSerial` (`0x004ECFC8`). A successful shift sets command state `+0x28` to 2; failure sets it to 4.

These findings substantially clarify how the current request is classified and how numeric scan constraints are represented. They do not yet identify the external connector's page-sequence numbering convention, nor the exact meaning of the four-entry table at `0x0062A7F0`.

## 9. Public TScanDocument dictionary-to-WordViewer handoff

The complete `TScanDocument.PerformMethod` body (`0x005EE82C–0x005EEB47`) shows more than the dictionary key inventory:

- It looks up `wordConfig` first. If the key is absent, it raises the explicit error text `Requset XML is not valid (wordConfig parameter is null)` (source spelling retained).
- It then looks up `wordBody`, `letterImages`, and `signData`.
- The handler forwards the four retrieved values into `TWordViewer.LoadDocument` at `0x004B7724`. Register/stack setup at the callsite passes the values as separate inputs; the helper then performs the actual Word document loading and related image processing.
- The handler sets a state byte on its receiver after the LoadDocument call and logs its thread uninitialization path.

This narrows the connector contract: `wordConfig` is explicitly required by this entrypoint; the other three keys are consumed and forwarded, but their optionality and exact serialized types are not yet proven. Do not treat the names as a complete schema or assume that each value is a plain string without inspecting the downstream stream/Variant handling.
