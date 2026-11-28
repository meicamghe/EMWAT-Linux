# Parallel reverse-engineering follow-up — 2026-11-28 (Run 25 artifact re-analysis)

## Scope and evidence

This is a fresh, parallel re-analysis of the completed Run-24 artifacts; it is not a new GitHub Actions run. The artifacts were downloaded and their procedure traces, callsites, import maps and string tables were inspected directly.

- Word: workflow run 46124030841, artifact 15255360751.
- GAM printer: workflow run 46124104850, artifact 15254533525.
- GDI+ callsites/imports: workflow run 46124227390, artifact 15254911990.
- GDI+ class/interface metadata: artifact 15255092521.
- Scanner constants: artifact 15253544912.
- Scanner procedure/interface traces: artifact 15254995277.
- SevenZip output archive: workflow run 46118303840, artifact 15252965648.

No production source code, release build, merge, rebase or new CI run was performed.

## 1. GDI+ multipage TIFF save sequence — substantially closed

### Output and input objects

- TWordViewer.LoadDocument reaches TCreateTiff.SeparteImages at 0x004A0148.
- SeparteImages obtains the TIFF destination name through euGetASFileName with the .tif suffix. The resulting path is retained and passed into the initial GDI+ save operation.
- The page-file list is copied into a local string list. Each source path is loaded through the TGPImage constructor with flag zero, which selects GdipLoadImageFromFile rather than the ICM or stream branch.
- The first-iteration branch constructs both the anchor TGPImage and the working TGPImage using the same list index. This is an observed detail; do not silently deduplicate or assume page ordering until a runtime TIFF sample confirms the result.

### Encoder settings

The encoder-parameter interface is configured with:

- EncoderCompression GUID {e09d739d-ccd4-44ee-8eba-3fbf8be4fc58}, value 2 = LZW.
- EncoderSaveFlag GUID {292266fc-ac40-47bf-8cfc-a85b89a655de}, value 18 = MultiFrame.

The later per-frame phase changes EncoderSaveFlag to 23 (FrameDimensionPage). The finalization phase changes it to 20 (Flush).

### Recovered call sequence

The SeparteImages interface calls can now be assigned by argument shape and control-flow role:

1. TGPImage interface slot +0x48 is the initial file save. It receives the destination .tif path, codec information and encoder parameters. Its role matches GdipSaveImageToFile.
2. Slot +0x70 is called on the working image with the Page frame-dimension GUID at 0x0062A810; its return value is used as the frame-loop bound. This matches GetFrameCount.
3. Slot +0x74 receives the same Page GUID and the current frame index. This matches SelectActiveFrame.
4. Slot +0x5C is called on the anchor image with the selected working image and encoder parameters. This matches SaveAddImage, appending the selected frame to the multipage output.
5. After the page/frame loops, EncoderSaveFlag is set to 20 (Flush) and slot +0x58 is called on the anchor image with the encoder parameters. This matches SaveAdd final flush.

The PE import map independently confirms the underlying APIs; do not use the shifted TD32 thunk labels as API identities:

| Code thunk | Actual PE import |
|---|---|
| 0x00481C64 | GdipSaveImageToFile |
| 0x00481C6C | GdipSaveImageToStream |
| 0x00481C74 | GdipSaveAdd |
| 0x00481C7C | GdipSaveAddImage |

The wrapper-level direct-call inventory corroborates the four distinct API paths. The interface structures are Delphi metadata, not flat method-pointer arrays, so the slot assignments above are based on the call arguments and surrounding sequence rather than a naïve raw VMT pointer scan.

### Result

The static lifecycle is now established: create LZW/MultiFrame encoder parameters → save the first image to the destination TIFF → enumerate/select page frames → append frames with SaveAddImage → set Flush and call SaveAdd. SeparteImages then waits 50 ms and enters a stream-wrapper path using the same output filename.

Remaining validation is about output ordering and runtime byte-level fidelity, especially the first-iteration dual-image construction. Static analysis does not prove that the resulting TIFF is accepted by Almas or by every downstream reader.

## 2. GAM printer INI contract and JobFinishes.GAM — producer side clarified

### Two different printer routines

- Zanprinter.Finalization at 0x0047D8BC is the actual paused-state query. It opens the selected queue, calls GetPrinterA at level 2, reads PRINTER_INFO_2A.Status at +0x48, and returns true when the value is 1 (PRINTER_STATUS_PAUSED).
- Zanprinter.CheckPrinterPaused at 0x0047D448 is misleadingly named. It calls GetPrinterName, derives the printer configuration paths, and writes the GAM profile files. It does not perform the GetPrinterA status query. Its nonzero return is used by SeparteImages as an error condition for setting GAM printer parameters.

### Confirmed profile writes

CheckPrinterPaused uses WritePrivateProfileStringW through thunk 0x00402910. The observed profile contract is:

| File | Section | Key | Value |
|---|---|---|---|
| save.ini | save | folder | path derived from the selected printer/output configuration |
| save.ini | save | basefilename | derived base filename |
| save.ini | save | popupdialog | No Dialogs |
| save.ini | save | filexistact | 1 |
| image.ini | image | fileformat | tiff |
| image.ini | image | imagecolor | 256 |
| image.ini | image | compression | lzw |
| image.ini | image | pagetype | Each page as a single strip |
| image.ini | image | rowsperstrip | 0 |
| general.ini | general | hidestsdialog | 1 |
| general.ini | general | sentinel | 1 |
| general.ini | general | sentinelfile | JobFinishes.GAM |

The separate helper at 0x0047D238 also handles the configure.ini path and references the policy/allusersfolder keys and the zvprt50\\ path component. The meaning of every policy branch is not yet fully recovered.

### Sentinel conclusion

The EMWAT module is proven to configure JobFinishes.GAM as the sentinel filename in general.ini. The reviewed EmwatMethods.bpl1 call graph does not prove that EMWAT itself creates, consumes or checks this file. The likely consumer is outside this module, in the GAM printer/port-monitor side, but that is not yet a proven fact.

Therefore, keep these events separate:
- queue job disappearance in EnumJobsW;
- GAM driver's sentinel-file behavior;
- GDI+ TIFF flush/finalization;
- final archive/Almas hand-off.

No one of these alone proves the others completed.

## 3. Word close-to-Almas bridge — negative boundary confirmed

- OnTmrAutoSave registers BeforeSave, NewDocument and WindowActivate handlers, plus the conditional LoadOptions/BeforePrintBGPrint callback. The Run-24 follow-up also identifies WindowDeactivate and WordIsActivated as a paired activation-state callback set.
- WordIsActivated sets the active flag and calls SaveOriginalOptions. WindowDeactivate clears the active flag for the matching Word window.
- The TD32-named WordAppDocumentBeforeClose at 0x004CCBBC is not the close callback in the observed call graph. Its direct caller is FillImgFldsForPrint, reached from GetFieldIndexInList; it is a Boolean print-field/XML metadata helper.
- QuitWord at 0x004CDB54 is called from the timer path, obtains the Word Application Caption and compares it with the literal Activation. Its body does not call Document.Close or Application.Quit and does not establish a close notification to Almas.
- The embedded EmwatService browser bridge is a generic postMessage → loopback HTTP POST → response postMessage forwarder. No close-specific message is present in that embedded bridge.

### Result

The actual Word close → Save/Discard/Cancel → return-to-Almas bridge is not established in the inspected EmwatMethods.bpl1 event registration or the embedded generic service bridge. The remaining owner is outside the recovered event path: likely parent-page/host code or another component, but the exact source must be captured rather than guessed.

The prior LibreOffice Save/Discard/Cancel acceptance test remains valid for the Linux Writer close listener; it is not evidence of Windows Word parity.

## 4. SevenZip output archive — ownership and encryption boundary

- T7zPlugin.Create at 0x00452C10 constructs a T7zOutArchive object through the constructor-style call to 0x004543C4, stores it at plugin offset +0x44, and passes it through the plugin interface slot +0x30.
- The output archive initializer obtains an interface object and stores it at +0x2C; callback/context fields +0x30 and +0x34 are cleared.
- SetPropertie stores an operation-result callback at +0x30 and its context at +0x34. SetOperationResult invokes that callback with the context and the leading result fields.
- SetProgressCallback uses a separate callback at +0x38. It must not be conflated with the operation-result callback.
- SaveToFile at 0x00454644 is a stub and contains no file-writing path. SaveToStream at 0x00454668 is the implemented output entry point in this wrapper and calls SetCompleted.
- SetPassword at 0x004547DC is a stub returning zero. The initializer's TD32 name CryptoGetTextPassword2 is not proof that a password is supplied at construction time.
- euResetMemory at 0x00456F00 is a separate autosave/finalization helper, not the T7zOutArchive callback object.

### Result

The output object and callback slots are identified, but the code that installs the callback/context and the semantic owner of the callback remain unresolved because no direct callsites were found in the bounded TD32 scan. Encryption is neither proven nor excluded: the SetPassword stub alone is insufficient to establish archive encryption policy. Do not connect this SevenZip path to the GAM TIFF path without a direct stream/file hand-off.

## 5. Scanner XML contract — names and numeric behavior tightened

### XML structure and error handling

- NewScanDocument at 0x004E9D5C passes the UTF-16LE root name scan-document to an XML interface call at slot +0x8C.
- The constraints child is constraints.
- The exact case-sensitive property keys already recovered are type, driverDialog, imageEditor, multiJpegSupport, previousImageName, forceSinglePageFiles, colorDepth, minResolution, maxResolution and maxFileSize.
- LoadRequestXML at 0x004F2B18 reads the error property through XML interface slot +0xB8 and uses the diagnostic prefix <ScanDoc HasError>. ErrorXML: . It returns false when both of its tested global XML references are null.
- The pointer at 0x004E9E00 is not a valid recovered UTF-16 property string; do not publish it as an XML key.

### Values and constraints

- VerifyConstraints compares the string literals none, jpg, yes and no in its option-validation path. These are values, not XML property names. The current XMLRTL interface-slot evidence does not safely assign each literal to one specific config property, so no mapping is invented.
- ColorDepth values accepted by the command path are 1, 4, 8 and 24. The labels are black/white, grayscale, grayscale-or-256-color, and 24-bit color respectively.
- MinResolution, MaxResolution and MaxFileSize are numeric constraint fields. FHasConstraints is set when the sum of the four numeric values (ColorDepth, MinResolution, MaxResolution, MaxFileSize) is nonzero; all-zero numeric constraints do not activate the constraint group.
- MaxFileSize is KiB: the command shifts the configured integer left by 10 and compares it against the 64-bit TStream.Size result in bytes.
- PreviousImageName, when non-empty, marks a next-page request. ForceSinglePageFiles is a separate output property, not one of the four numeric constraints.

### Remaining scanner boundary

The external XMLRTL interface implementations and their defaults are not in the analyzed module. Required/optional/default behavior for absent properties, empty strings, zero values and serialization order therefore remains open until a matching XMLRTL implementation or sanitized Almas request/response capture is available. Do not invent defaults from nearby constants.

## 6. Consolidated outcome and next gates

| Workstream | Outcome of this pass | Remaining proof |
|---|---|---|
| GDI+ TIFF | Save → frame selection → SaveAddImage → Flush sequence recovered statically | Runtime output ordering/byte-level acceptance |
| GAM printer | Exact INI/sentinel producer side recovered | External driver/port-monitor consumer and sentinel lifecycle |
| Word close | Misleading helper and timer-caption path excluded as close bridge | Parent-page/host close notification and Windows Save/Discard/Cancel capture |
| SevenZip | Output object and callback fields mapped | Callback installer/owner, archive consumer and encryption policy |
| Scanner XML | Root, keys, numeric selectors and error property recovered | XMLRTL defaults, required/optional rules and real request/response capture |

Implementation remains gated. No guessed XML defaults, SevenZip encryption policy, printer completion signal or Word close event should be added to the Linux implementation. The next useful evidence for the remaining gaps is the GAM printer/port-monitor binary, the Almas parent-page script or a sanitized close-time HTTP capture, the callback-installing SevenZip interface implementation, and the matching XMLRTL runtime/schema.
