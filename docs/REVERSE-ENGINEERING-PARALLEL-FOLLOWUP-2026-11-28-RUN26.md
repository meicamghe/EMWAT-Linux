# Parallel reverse-engineering follow-up — 2026-11-28 (Run 26 cross-artifact reconciliation)

## Scope and evidence

This pass re-opened and reconciled existing static-analysis artifacts across the five active workstreams. It is **not** a new GitHub Actions run and does not claim runtime acceptance.

Artifacts re-reviewed:
- Word event/close path: run 46124030841, artifact 15255360751.
- GAM queue ownership: run 46117480260, artifact 15252845315; printer INI producer: run 46124104850, artifact 15254533525.
- GDI+ page-save path: run 46124227390, artifact 15254911990; interface metadata artifact 15255092521; interface-method follow-up run 46120428310, artifact 15253761384.
- SevenZip output callback: run 46119766144, artifact 15253196955; archive/plugin ownership: run 46118303840, artifact 15252965648.
- Scanner XML: run 46120998177, artifact 15253432241; numeric-unit helper run 46118668134, artifact 15252787473; scanner procedure/caller traces artifact 15254995277.

No production source code, release build, merge, rebase or new CI run was performed.

## 1. GDI+ multipage TIFF — first-page duplication question resolved statically

The prior Run-25 report correctly recovered the API sequence but left the first-iteration dual-image construction as an unresolved duplication risk. The full loop resolves that risk:

1. The page-file list is iterated in its stored order.
2. On the first page only, the same source file is loaded twice: one TGPImage becomes the anchor image and the other becomes the working image.
3. The anchor image is saved first through TGPImage slot +0x48 with LZW compression and EncoderSaveFlag=18 (MultiFrame).
4. The working image's page-frame count is read through slot +0x70.
5. During the first page's frame loop, the first-frame flag is cleared and frame index 0 deliberately skips both SelectActiveFrame and SaveAddImage. That frame is already present from the initial Save; it is not appended twice.
6. Remaining frames of the first source file are selected through slot +0x74 and appended through anchor slot +0x5C.
7. For every subsequent source file, the first-frame skip flag is no longer set, so all frames of each later file are selected and appended in order.
8. Finalization sets EncoderSaveFlag=20 (Flush) and calls anchor slot +0x58 (SaveAdd).

The PE import map independently identifies the underlying GDI+ imports: 0x00481C64=GdipSaveImageToFile, 0x00481C74=GdipSaveAdd, and 0x00481C7C=GdipSaveAddImage. The shifted TD32 thunk labels remain unsuitable as API identities.

**Conclusion:** the static control flow does not duplicate the first frame. The intended order is first file/frame 0 via initial Save, remaining frames of that file via SaveAddImage, then every frame from later files in list order, followed by Flush. What remains is runtime verification of the actual file-list ordering, TIFF bytes, and acceptance by Almas/downstream readers.

## 2. GAM printer and JobFinishes.GAM — queue identity improved; external consumer still absent

### Queue selection

The printer queue artifact adds a precise identity rule:
- GetPrinterName enumerates PRINTER_INFO_2A entries through EnumPrintersA.
- It compares the entry's pDriverName field (structure offset +0x10) against the literal driver name `zvprt1`.
- On a match it copies pPrinterName (offset +0x04) into the selected-queue global. The queue name is therefore discovered from the installed printer using its driver name; it is not hard-coded as the queue display name.

### Paused-state check

Zanprinter.Finalization at 0x0047D8BC opens the discovered queue through OpenPrinterA, calls GetPrinterA at level 2, reads PRINTER_INFO_2A.Status at +0x48 and returns true only when Status equals 1 (PRINTER_STATUS_PAUSED). This is a paused-state query, not a completed-job query.

The separate Zanprinter.CheckPrinterPaused at 0x0047D448 writes save.ini, image.ini and general.ini. The latter contains sentinel=1 and sentinelfile=JobFinishes.GAM. The names are misleading: the routine is the INI producer, while Finalization is the paused-state query.

### Completion boundary

The EMWAT BPL configures the sentinel filename but the inspected module still does not show the external producer/consumer that creates or observes JobFinishes.GAM. It also does not establish that queue disappearance, TIFF Flush, sentinel creation, and final Almas hand-off are the same event. The GAM printer/port-monitor/server binary or a controlled Windows file/queue trace is still required.

The existing print call graph supports Word PrintOutOld submission to the Windows queue, but the exact driver-side TIFF publication and the final file-to-Almas hand-off remain unproven. Do not implement a Linux completion signal from the sentinel setting alone.

## 3. Word close-to-Almas — close decision and local response release recovered

This pass narrows the Run-25 conclusion. The procedure named `WordAppDocumentBeforeClose` at 0x004CCBBC is indeed a print-field/XML metadata helper reached through FillImgFldsForPrint; it is not the active close handler. However, the separate callback at 0x004CD154 is installed by OnTmrAutoSave into the Word event record at offset +0x80 (with its owner pointer at +0x84), and its body contains the close/registration decision path.

Observed behavior in 0x004CD154:
- It verifies that the event document matches the viewer's active document pointer at +0x48.
- If viewer flag +0x5E is clear, it sets the Word event Cancel output to -1 and exits.
- It reads the document's Saved property through interface slot +0xD8.
- If the document is unsaved and viewer flag +0x5F is set, it displays a three-choice modal dialog.
- Modal result 2 (Delphi mrCancel) sets the Word Cancel output to -1 and exits without closing.
- Modal result 6 (Delphi mrYes) sets the SaveChanges argument to -1 (true).
- Other non-cancel results set SaveChanges to 0 (false), which is the discard path.
- The handler then invokes the Word document interface at slot +0x29C with the three Close arguments, releases the stored document interface, and clears viewer field +0x58.

The separate Run-153 trace establishes the release chain: OnTmrAutoSave waits while viewer +0x58 is nonzero; the callback clears it after the Document.Close call; the wait exits, the timer is disabled, and LoadDocument writes the response-word XML through Indy WriteContent. This is the local long-lived HTTP request/response bridge that returns the edited document after the Word close path.

**Correction to Run 25:** the close decision and the local HTTP response-release path are statically recovered; they should no longer be described as wholly unresolved. The formal COM event DISPID remains unresolved because the TD32 symbol labels the installed callback BeforeSave while the handler's behavior and historical log evidence are close-oriented. The exact UI button captions, the initial setter of viewer +0x58, and the browser/Almas parent-side handling of the returned response are also not fully proven. Do not confuse this handler with the unrelated 0x004CCBBC print-field helper or the periodic OnControlerNotify archive callback.

This is static evidence only. It does not replace the existing LibreOffice Writer Save/Discard/Cancel acceptance tests or establish Windows runtime parity.

## 4. SevenZip output — file creation and callback dispatch boundary sharpened

- T7zPlugin.Create constructs and stores the T7zOutArchive object at plugin offset +0x44, then exposes it through the plugin interface.
- T7zOutArchive.SaveToFile at 0x00454644 is a short metadata/out-parameter callback: it writes fixed output values and returns zero. It is not the file-writing implementation.
- T7zOutArchive.SaveToStream at 0x00454668 creates a TFileStream for the supplied path with fmCreate (0xFF00), then passes that stream into SetCompleted. This is direct evidence that the stream route creates the destination file.
- SetCompleted obtains the archive/stream interfaces and dispatches through an interface method at slot +0x0C. The exact external interface method identity and the complete 7-Zip SDK call contract are not established by this wrapper trace.
- SetPropertie stores the operation-result callback at object +0x30 and context at +0x34; SetOperationResult invokes that pair. SetProgressCallback uses a separate callback field at +0x38.
- The output SetPassword method at 0x004547DC is a stub. The +0x44 dispatch used by euResetMemory has not been conclusively mapped to that named method, so the fixed string passed there is not proof of output encryption.
- Input T7zInArchive.SetPassword at 0x00453860 is implemented and forwards its value to the input archive interface. That supports a passworded-input candidate, but the exact fixed-literal dispatch and actual .easz encryption flags still require a controlled archive fixture.

**Conclusion:** output-file creation through SaveToStream is proven, and callback fields are mapped. The callback installer/semantic owner, output encryption policy, and the relationship between this output path and the GAM TIFF path remain open. Do not merge .easz recovery archive semantics with the GAM TIFF/sentinel pipeline without a direct hand-off trace.

## 5. Scanner XML — numeric fallback narrowed, schema defaults remain provisional

The root and property-name evidence remains unchanged:
- Root: `scan-document`; child: `constraints`.
- Case-sensitive keys include `type`, `driverDialog`, `imageEditor`, `multiJpegSupport`, `previousImageName`, `forceSinglePageFiles`, `colorDepth`, `minResolution`, `maxResolution`, `maxFileSize`.
- LoadRequestXML reads `error` through XML interface slot +0xB8 and uses the diagnostic prefix `<ScanDoc HasError>. ErrorXML: `.
- ColorDepth accepts 1, 4, 8 and 24; MaxFileSize is KiB and is shifted left by 10 before comparison with a 64-bit byte count.
- PreviousImageName non-empty selects the next-page request path; ForceSinglePageFiles is a separate output property.

The getter traces for the numeric constraint fields initialize local numeric/variant fallback storage to zero before calling the XML attribute helpers. This is evidence for a zero fallback when the helper returns no value, but the XMLRTL helper's absent, empty-string and malformed-value behavior is not present in the inspected module. Record zero as a **probable numeric fallback**, not yet as a fully verified external schema default. The required/optional status of the string fields and their serialization order also remain unresolved.

No default should be added to the Linux protocol implementation solely from nearby constants or generated-property names. A matching XMLRTL implementation or sanitized request/response samples are still needed.

## 6. Consolidated status and remaining proof gates

| Workstream | Static result after this pass | Remaining proof |
|---|---|---|
| GDI+ TIFF | First-frame duplication ruled out; ordered Save/SaveAddImage/Flush lifecycle recovered | Runtime TIFF bytes, source-list order and Almas acceptance |
| GAM printer | Driver identity `zvprt1`, queue discovery and paused-state check recovered; sentinel configuration known | External JobFinishes.GAM producer/consumer and final TIFF delivery |
| Word close | Three-way decision, Document.Close call and HTTP response-release chain recovered | Formal COM DISPID, exact UI labels and Almas parent-page response handling |
| SevenZip | SaveToStream file creation and callback fields recovered | Callback installer/owner, output encryption and archive consumer |
| Scanner XML | Root, keys, numeric rules and probable zero fallback recovered | XMLRTL missing/empty semantics, required/optional rules and runtime samples |

### Evidence still required before Linux behavior is changed

1. GAM printer/port-monitor/server files or a sanitized Windows trace that correlates queue job, TIFF file, JobFinishes.GAM and Almas hand-off.
2. Word type-library/event metadata plus a sanitized close-time request/response trace to confirm the formal event identity and browser-side response consumer.
3. The SevenZip callback-installing interface implementation and a synthetic .easz fixture with 7-Zip header/encryption inspection.
4. Matching XMLRTL runtime/schema or sanitized scanner request/response samples covering omitted, empty, zero and malformed fields.
5. A generated multipage TIFF fixture from the original runtime for byte-level and downstream-reader acceptance.

No Linux implementation changes are justified by the remaining unresolved boundaries. No production code, builds/releases, merge/rebase or new Actions run were performed in this pass.


## 7. External package-family evidence — GAM printer target set identified

A public Microsoft Q&A installer log for the 32-bit Zan Image Printer 5.0.14.18 package (2011-08-11) records the same driver identity `zvprt1` and install root `C:\\Program Files\\zvprt50\\`. The log identifies the following installed payloads:

- `zvprtsrv.exe` and `zvprtcfg.exe` / `zvprtcfg_win32.exe` under `zvprt50`;
- `zvprtmon5.dll` and `zvprtmonui5.dll` under Windows system32, with an explicit `AddZvprtMonitor` installation step;
- `zvprtui5.dll`, `zvprtuni5.dll`, `zvprt5.ini`, `zvprt1.gpd`, `configure.ini`, and `zvprthlp.chm`;
- the printer profile list includes `save.ini`, `image_bw.ini`, `general.ini`, other output profiles, and `sentineltemplate.txt`.

The same log identifies the installed printer as `Zan Image Printer (BW)`, driver `zvprt1`, and GPD `zvprt1.gpd`. This independently corroborates the BPL's `zvprt1` driver-name match. It also identifies the most useful external binaries to inspect next: the port-monitor DLL (`zvprtmon5.dll`), monitor UI DLL, server process (`zvprtsrv.exe`), configuration tools, GPD and sentinel template. The monitor DLL and server process are **candidate** locations for sentinel handling, not yet proven consumers.

A separate third-party inventory of Emwat Service lists `GAMPrinterSetup.exe` as the self-extracting GAM Virtual Printer package and lists `Gear32pd.dll` plus `IGLZW32S.DLL` as AccuSoft ImageGear and its LZW extension. This is useful package-inventory corroboration only; it does not prove that the inspected BPL calls those libraries. Keep the ImageGear path separate from the statically recovered GDI+ TIFF path until imports/calls or runtime traces connect them.

Sources:
- [Microsoft Q&A — Zan Image Printer installation log](https://learn.microsoft.com/en-us/answers/questions/2472284/printer-port-installs-but-driver-install-will-not), especially the installer payload and `AddZvprtMonitor` sections.
- [Should I Remove It? — Emwat Service installed-file inventory](https://www.shouldiremoveit.com/Emwat-Service-37480-program.aspx), which lists GAMPrinterSetup.exe, Gear32pd.dll and IGLZW32S.DLL.

**Revised next step for the printer lane:** inspect `zvprtmon5.dll`, `zvprtmonui5.dll`, `zvprtsrv.exe`, `zvprtcfg.exe`, `zvprt1.gpd`, `zvprt5.ini`, `sentineltemplate.txt`, and the active `general.ini`/save/image profiles from the exact GAMPrinterSetup.exe version shipped with EMWAT. The 2011 Zan package is a family-level lead, not a substitute for the exact EMWAT payload.
