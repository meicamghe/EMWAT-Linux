# Parallel reverse-engineering follow-up — 2026-11-28 (Run 27)

## Scope

Run 27 re-opened the underlying scanner, Word, SevenZip and GDI+ procedure artifacts rather than relying only on the Run-26 prose summary, then cross-checked the relevant COM/Delphi/7-Zip contracts against public technical documentation. It also identified a verifiable Zan Image Printer 5.0.19 package record as a family-level comparison target.

This was static artifact re-analysis plus public documentation research. It was **not** a new GitHub Actions run. No production source code, build, release, merge or rebase was performed.

## 1. GAM/Zan printer — family-level package capability now corroborated; sentinel consumer still open

### Verifiable public package record

Download3K's record identifies:
- Product: Zan Image Printer 5.0.19, developed by `zan1011.com`.
- Installer: `zvprt5.exe`, 6.53 MB.
- MD5: `958e08527bc89a56e4d436ffc920e805`.
- SHA-1: `e671cfa915332ef99e1de0478441c2bdc04a7ad2`.
- Updated/tested: 2016-06-05.
- The publisher page describes appending multiple files into one PDF or TIFF, batch/silent output, command-line integration and a detailed text debug log. It lists PNG, GIF, JPG, TIFF, BMP and PDF output.

The Download3K antivirus report for this exact 5.0.19 record reports clean results from Avast, AVG, Avira, Kaspersky and NOD32. This is third-party distribution/test evidence, not a vendor-signed hash or proof that EMWAT ships this exact build.

### Relationship to EMWAT's GAM package

The EMWAT BPL's `zvprt1` driver-name match, queue selection and INI profile writes remain directly recovered from the BPL. A separate Zan 5.x installer log previously identified `zvprtmon5.dll`, `zvprtmonui5.dll`, `zvprtsrv.exe`, `zvprtcfg.exe`, `zvprt1.gpd`, `zvprt5.ini`, `configure.ini` and `sentineltemplate.txt`, with an `AddZvprtMonitor` step. The 5.0.19 record and that older installer log are separate public evidence items; do not combine their manifests as if they were one exact build.

A separate Hybrid Analysis sample named `zvprt5.exe` has SHA-256 `b81622b81bc19fe46d32f5832825726a41ff2ba6634cfa2f51c8ab5edc0587ed` and a high threat score. It is a different hash from the Download3K 5.0.19 package. It was not downloaded or executed, and its detection score must not be attributed to the 5.0.19 package.

### What this proves / does not prove

- The Zan printer family supports multi-file append into TIFF/PDF; this makes the driver-side multipage path a real capability, not merely an inferred setting.
- It strengthens the reason to inspect `zvprtsrv.exe` and monitor DLLs as part of TIFF production and completion.
- It does **not** prove that EMWAT's GAMPrinterSetup.exe is version 5.0.19, that the same implementation is bundled, or that the sentinel file is created by the server or monitor.
- The `JobFinishes.GAM` producer/consumer, file contents/format, atomicity and relationship to queue completion remain unresolved.

Sources:
- Download3K product record and hashes: https://www.download3k.com/Install-Zan-Image-Printer.html
- Download3K antivirus report: https://www.download3k.com/Antivirus-Report-Zan-Image-Printer.html
- Zan installer payload/monitor registration log: https://learn.microsoft.com/en-us/answers/questions/2472284/printer-port-installs-but-driver-install-will-not
- Separate suspicious sample record: https://hybrid-analysis.com/sample/b81622b81bc19fe46d32f5832825726a41ff2ba6634cfa2f51c8ab5edc0587ed/5eec166726e0bd5df311992d

## 2. Word close callback — event identity strongly resolved to Application.DocumentBeforeClose

Re-opened `procedure-004CD154.md`, `pointers-004CD154.md` and the callback body from Word artifact `15255360751` (run `46124030841`).

The callback's effective parameter/behavior shape matches Microsoft Word's `Application.DocumentBeforeClose(Doc As Document, Cancel As Boolean)` event:
- It validates the callback's Document against the active viewer Document pointer.
- It reads `Document.Saved`.
- For an unsaved document, it presents the three-way prompt when the viewer flag permits.
- Cancel sets the event's Cancel Boolean to true.
- Save selects `SaveChanges = true`; Discard selects `SaveChanges = false`.
- It then calls the document `Close` method and clears the viewer's stored document pointer.
- Run-153's separate wait-loop trace links that clear to the timer exiting and the local HTTP response being written.

The TD32 symbol label `WordAppDocumentBeforeSave` is therefore a stale/misleading name for this callback body. The unrelated `WordAppDocumentBeforeClose` symbol at `0x004CCBBC` remains the print-field/XML metadata helper and must not be confused with the real close callback.

**Revised confidence:** event identity is strongly resolved to Word `Application.DocumentBeforeClose` by the event signature and semantics. The numeric COM DISPID/type-library binding and browser/Almas parent-page response handling remain open. Do not label the event as formally DISPID-confirmed until type-library or runtime event metadata is available.

Official reference:
https://learn.microsoft.com/en-us/office/vba/api/word.application.documentbeforeclose

## 3. SevenZip output — actual sequential write call mapped; password callback label corrected

Re-opened artifacts `15252965648` and `15253196955` (existing runs `46118303840` and `46119766144`).

### File creation and write

- `T7zOutArchive.SaveToStream` at `0x00454668` creates a `TFileStream` for the requested path with mode `fmCreate` (`0xFF00`).
- It passes the stream through `SetCompleted` at `0x004546C4`.
- `SetCompleted` obtains the stream interface and invokes vtable slot `+0x0C`.
- In the 7-Zip SDK, `ISequentialOutStream` inherits `IUnknown` and its first method at vtable offset `+0x0C` is `Write(data, size, processedSize)`. The recovered call setup supplies the write buffer/size/output-size arguments before dispatch.

This closes the earlier uncertainty about whether `SaveToStream` only creates a placeholder: the wrapper follows the 7-Zip sequential-output-stream write interface to send data to the created file. `SaveToFile` at `0x00454644` remains an out-parameter/metadata callback, not the byte-writing path.

### Password/encryption

- The procedure at `0x004543C4`, despite its TD32 symbol label `CryptoGetTextPassword2`, is invoked from `T7zPlugin.Create` in constructor calling shape and initializes object/interface state. It is not evidence that a password is returned to 7-Zip.
- `T7zOutArchive.SetPassword` at `0x004547DC` is a stub returning zero.
- No functional output `ICryptoGetTextPassword2` password-return body has been proven in the inspected wrapper.
- Standard 7-Zip SDK implementations use `ICryptoGetTextPassword2` as an additional callback interface for encrypted update operations. Its absence from the recovered functional path means output encryption remains **unproven**, not proven enabled or disabled.
- Input `T7zInArchive.SetPassword` remains a separate, functional candidate path. Do not project input-password behavior onto output archives.

References:
- 7-Zip stream interface: https://github.com/m2team/nanazip/blob/93e5e4f76e988210f763e1b84cb0f6bb910741b5/NanaZip.Core/SevenZip/CPP/7zip/IStream.h
- 7-Zip update callback/password interfaces: https://github.com/m2team/nanazip/blob/93e5e4f76e988210f763e1b84cb0f6bb910741b5/NanaZip.Core/SevenZip/CPP/7zip/UI/Common/UpdateCallback.h

## 4. Scanner XML — numeric absent-field default is now confirmed; empty/malformed is not zero

Re-opened scanner artifact `15253432241` (run `46120998177`), including the individual accessors at:
- `0x004EAA08` — TD32-named `Set_ColorDepth`
- `0x004EAB58` — `Set_MinResolution`
- `0x004EACB0` — `Set_MaxResolution`
- `0x004EAE08` — `Set_MaxFileSize`

Each integer-returning accessor:
1. Initializes its result register to zero.
2. Calls the XML node `HasAttribute` helper with the exact case-sensitive property key.
3. If the attribute is absent, skips `GetAttribute` and returns the zero result.
4. If present, calls `GetAttribute`, invokes the Variant-to-integer conversion method, and returns the converted integer.

This is stronger than the Run-26 observation of zero-initialized local storage: the absent-attribute branch is explicit. For these four numeric constraint attributes, **absent means 0**. If all four are absent/zero, the existing `FHasConstraints` aggregate test remains false.

For a present empty or non-numeric string, the code takes the conversion path rather than the absent branch. Embarcadero's Delphi Variant conversion documentation states that string-to-integer conversion raises when the string is not numeric. Thus empty/malformed values must not be silently normalized to zero in a Linux parser unless a runtime trace demonstrates a catch/default at a higher layer.

The apparent `Null Variant` concern is also resolved: Embarcadero documents that `IXMLNode.GetAttribute` returns Null when an attribute is missing, but these four accessors call `HasAttribute` first and do not call `GetAttribute` on the absent path. The separate `Get_*` accessor routines and external XMLRTL behavior still need method-level mapping before their output semantics are used.

**Still open:** required/optional status of the string fields (`type`, `driverDialog`, `imageEditor`, `multiJpegSupport`, `previousImageName`), empty-string semantics for those fields, serialization order, and complete request/response samples.

References:
- IXMLNode.GetAttribute (missing returns Null Variant): https://docwiki.embarcadero.com/Libraries/Sydney/en/Xml.XMLIntf.IXMLNode.GetAttribute
- TXMLNode.HasAttribute: https://docwiki.embarcadero.com/Libraries/Athens/en/Xml.XMLDoc.TXMLNode.HasAttribute
- Delphi Variant conversion rules: https://docwiki.embarcadero.com/RADStudio/Sydney/en/Variant_Types_(Delphi)

## 5. GDI+ multipage TIFF — loop rechecked, no regression to Run-26 conclusion

Re-opened `procedure-004A0148.md` from artifact `15254911990` (run `46124227390`).

- The first-page flag is set before the outer page-file loop.
- The initial TIFF Save writes the first page/frame.
- In the frame loop, the first iteration clears that flag and jumps past SelectActiveFrame/SaveAddImage. This deliberately avoids appending the frame already written by the initial Save.
- Subsequent frames in the first input and all frames in subsequent inputs use SelectActiveFrame then SaveAddImage.
- The final EncoderSaveFlag is 20 (Flush), followed by the final SaveAdd call and a 50 ms wait before the stream wrapper path.

This confirms the static first-frame non-duplication and list-order lifecycle from Run 26. Runtime TIFF byte/order validation and Almas acceptance remain open; no original-runtime fixture was available in this pass.

## 6. Updated proof gates

| Workstream | Current result | Remaining proof |
|---|---|---|
| GAM/Zan | Public 5.0.19 package supports multi-file TIFF/PDF append; monitor/server manifest leads corroborated | Exact EMWAT GAM payload, JobFinishes.GAM writer/reader and completion correlation |
| Word | Callback strongly maps to Application.DocumentBeforeClose; Save/Discard/Cancel and HTTP response release recovered | Numeric DISPID/type-library confirmation and Almas parent-side response handling |
| SevenZip | SaveToStream creates file and writes through ISequentialOutStream.Write | Callback installer/owner, exact .easz format/options, output encryption policy and archive consumer |
| Scanner XML | Four numeric missing attributes default to 0; empty/non-numeric values take Variant conversion path | String-field required/optional/default behavior and runtime XML fixtures |
| GDI+ TIFF | First frame is not duplicated; Save/SaveAddImage/Flush sequence rechecked | Runtime TIFF bytes, list ordering and downstream Almas acceptance |

No Linux implementation change is justified by this static-analysis pass alone. Preserve the current guardrail: keep each printer/TIFF/archive/Word signal separate until a real hand-off trace links them.
