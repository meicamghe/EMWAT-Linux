# Parallel reverse-engineering workstreams — run 117

Source: existing GitHub Actions artifact `emwat-word-lifecycle-run117` and its TD32 disassembly/metadata files. This document records independent findings that can be pursued in parallel; it does not claim the complete EMWAT protocol is decoded.

## Workstream A — request/command dispatch and TEmwatMethod.Invoke

- The public/exported TEmwatMethod.Invoke entry is 0x0046C9E0. Every TEmwatMethod descendant uses this address in VMT slot +0x0C.
- The shared wrapper at 0x0046C9E0 calls the inner dictionary/XML helper at 0x0046C82C (433 bytes) at callsite 0x0046CA67, then invokes the concrete subclass's VMT slot +0x10 at callsite 0x0046CA88.
- The inner helper at 0x0046C82C builds the XML method/parameter structure from TDictionary<AnsiString,AnsiString> and calls TXMLEmwatType interface slot +0x54 at 0x0046C937 to serialize it.
- TD32 labels are misleading at this boundary: 0x0046C82C is symbolized as TEmwatMethod.Invoke, while 0x0046C9E0 is symbolized as Emwatmethod.Finalization. The export name, shared VMT slot +0x0C, and call graph establish 0x0046C9E0 as the public virtual Invoke wrapper and 0x0046C82C as its inner helper.
- There are two distinct +0x68 indirect dispatches: one in the inner helper at 0x0046C921 and another in the wrapper at 0x0046CBB7. Their receiver types must not be conflated.
- The concrete EditWordDocument VMT slot +0x10 target is 0x005EE82C. Its body retrieves wordConfig, wordBody, letterImages, and signData, then calls TWordViwer.LoadDocument at 0x004B7724.
- The BPL export table confirms the service-facing PerformMethod names and targets. TD32 procedure labels for several neighboring connector methods are shifted by one class name; use export names together with method-body semantics when mapping the public method identifiers.
- The helper's XML serializer getter target is TXMLEmwatType interface slot +0x54, resolved through thunk 0x0044B7A9 to xmlrtl230.bpl!TXMLNode.GetXML at 0x0044B590.


## Workstream B — Word document lifecycle

### Confirmed observations
- The event callback `TWordViwer.WordAppDocumentBeforeClose` occupies `0x004CCBBC–0x004CCD59`.
- It derives indexes and values from viewer-owned structures at offsets `+0xE8` and `+0xEC`, obtains an XML field interface, and calls `TWordViwer.GetXmlFieldInfo` at `0x004BCA88`.
- The return value from `GetXmlFieldInfo` is retained in a local boolean-like register/value and the callback performs a subsequent global reporting/logging call with selector `6`.
- `GetXmlFieldInfo` is a large XML/Word field-processing routine (12,688 bytes), with an `IXMLFieldType` parameter in its TD32 signature.

### Implication
The BeforeClose callback is not merely a call to Word's Close method. It performs EMWAT-side field/XML processing during the close event. The exact business meaning of the field and whether the returned flag cancels or changes close behavior must be established from the event interface signature and caller contract.

### Next targets
1. Decode the string constants and XML field names used by `GetXmlFieldInfo`.
2. Trace the event's COM argument and the returned boolean to determine whether it is a Cancel flag or a status result.
3. Compare this callback with `BeforeSave` and `BeforePrint` to identify common field serialization logic.

## Workstream C — print and letter preparation

### Confirmed observations
- `BGPrintWithGamPrintOptions` is a large routine (`0x004C5FF8–0x004C9EA7`) and creates the shared Word Automation wrapper.
- It reads the global print-option state at `0x0062A828`, performs validation, and proceeds through a substantial print preparation path.
- `WordAppDocumentBeforePrintBGPrint` separately gates the Word BeforePrint event and prepares the same global print-option object.
- `PreparePrintDocument` is called from the BeforeSave path.

### Next targets
1. Recover all option names and values consumed by the print routine.
2. Identify the Word document properties and fields changed before print.
3. Map the printer-related state to a Linux CUPS/IPP workflow without attempting to load the Windows kernel printer driver.

## Workstream D — AutoSave/recovery

### Confirmed observations
- The recovery form's Delete path creates the same Word Automation wrapper class used by LoadDocument and BGPrint.
- FormClose iterates Word-side collection items and issues late-bound Automation dispatch calls; the dispatch slot alone does not reveal the method name.
- The artifact does not yet establish the recovery directory, filename extension, list-population function, or exact deletion operation.

### Next targets
1. Resolve the selected-item arguments passed into the Automation wrapper.
2. Trace the wrapper's event callback at `0x005EC594`.
3. Search other modules/resources for list population and recovery path construction.

## Workstream E — Native Linux implementation contracts

Keep implementation separate from reverse engineering, but only encode behavior supported by evidence:
- local loopback HTTP service with route/command registry;
- per-user configuration replacing HKCU registry values;
- document lifecycle event adapter;
- print preparation/validation service;
- recovery provider interface with pluggable discovery backend;
- structured trace/logging around each operation.

Do not implement guessed Word field names, recovery paths, or opaque invoke serialization as if they were known.

## Parallel execution order

The five workstreams can proceed independently against the same immutable artifact. Merge only at explicit interfaces:
1. command dispatcher ↔ XML/request model;
2. document lifecycle ↔ field serializer;
3. field serializer ↔ print preparation;
4. recovery provider ↔ Word Automation adapter;
5. all subsystems ↔ local HTTP API and per-user configuration.

## Confidence summary
- **Confirmed:** dictionary enumeration and update behavior in `TEmwatMethod.Invoke`; direct caller currently points to Finalization, not a proven HTTP handler.
- **Confirmed:** BeforeClose invokes the large `GetXmlFieldInfo` XML/field-processing routine.
- **Confirmed:** print routine and BeforePrint callback share the global print-option state and Word Automation wrapper.
- **Unresolved:** actual HTTP command dispatch mapping, XML field schema, close cancellation semantics, recovery file paths, and full print side effects.


## Parallel execution update — 2026-11-15

The analysis is now split across independent GitHub Actions workflows rather than one serial queue. The shared TD32 procedure tracer also records PE section, raw file offset, and decoded-byte coverage so incomplete instruction decoding is visible in each artifact.

### Completed parallel branches

**A. Invoke/XML serializer — workflow #25, run 43707049586, success (23/23), artifact 14159051458**

- TEmwatMethod.Invoke calls interface slot +0x54 at 0x0046C937 after building the XML method/parameter nodes.
- The corresponding TXMLEmwatType interface thunk at 0x0044B7A9 adjusts the interface pointer by -0x50 and jumps to 0x0044B590.
- 0x0044B590 is the imported xmlrtl230.bpl!TXMLNode.GetXML thunk. Therefore the final serializer call in Invoke is now mapped: the constructed XML envelope is serialized through GetXML.
- The method element name method, method attribute class, and parameter attribute name are backed by decoded string constants. Parameter text is assigned through xmlrtl230.bpl!TXMLNode.SetText (0x0044B568).
- This closes the previously unresolved serializer slot in the Invoke helper. It does not yet identify every method handler or decode opaque document-specific parameter values.

**B. Filename/format classification — workflow #3, run 43707049640, success, artifact 14158921386**

- TWordViwer.LoadDocument passes its second argument (the wordBody parameter) into EmailUtil.Finalization at 0x004B778B.
- Finalization at 0x00457050 defaults the output extension to .doc; it compares the leading bytes against two ZIP local-file signatures and selects .docx when either signature matches.
- The two signature constants begin PK 03 04 14 06 and PK 03 04 14 08. The exact semantics of the ZIP flag variants are not needed for the extension-selection result.
- LoadDocument then passes the selected extension into euGetASFileName at 0x00454B9C. That helper is shared by Word loading and several image/print/fax paths.
- In the captured HTTP envelope, wordBody is Base64 text; decoding its prefix yields the Compound File Binary signature D0 CF 11 E0 A1 B1 1A E1. Neither the transport text prefix nor the decoded CFB prefix matches the two PK signatures, so this sample follows the .doc branch.
- The exact stage at which the Service decodes wordBody relative to the BPL Finalization call remains unresolved. The classifier's .doc result for this sample is supported; do not infer that every Base64-wrapped DOCX would be classified correctly until the service-side decode path is traced.
- The helper does not establish the full temporary path, cleanup policy, or persistence destination. Do not infer those from the extension selection alone.

**C. Network/API capture — workflow #2, run 43707410915, success, artifact 14159156356**

- The metadata-only analyzer found 15 TCP streams involving port 1984: ten heartbeat exchanges, three init requests, one GetEmwatVersion, and one EditWordDocument.
- The captured EditWordDocument request contains wordConfig, wordBody, and empty signData; the decoded config contains 180 field elements. Decoding the Base64 wordBody and returned-document values yields the Compound File Binary signature.
- The response is response-word status=success, with a return type marked application/msword and encryption=base64.
- Init requests carry the external Almas page as Referer; the subsequent XHR POST to the local service has loopback Origin/Referer. The bridge boundary is now confirmed by runtime headers.
- Heartbeat replies are 200 OK with body TickTack.
- The analyzer deliberately emits metadata only. Its frame-order reconstruction is not a substitute for TCP-sequence-aware reassembly.

**D. Native and Python verification**

- Native image-core workflow #104 (run 43707221674) passed both build/test and sanitizer jobs after adding page-selection lifecycle assertions.
- Python bridge workflow #25 (run 43707211730) passed after adding a synthetic capture-sized (>1 MB) opaque Base64 parameter preservation test. No customer document bytes were added to tests.

### Still running at the time of this update

- Word lifecycle workflow #121 (run 43707049641) is continuing through the full 37-step analysis. Its latest observed state had no failed steps; do not treat the artifact as complete until the workflow reports success and its outputs are inspected.

### Updated next actions

1. Reconcile the mapped GetXML serializer with the captured runtime request/response, then add a regression fixture containing only synthetic metadata and opaque payloads.
2. Trace the actual euGetASFileName output path and temporary-file cleanup without assuming that the selected extension determines storage location.
3. Continue main-editor close callback → parent-page postMessage → local POST correlation. The capture proves an EditWordDocument round-trip, but not that this particular request is triggered by closing Word.
4. Finish Word lifecycle run #121, inspect its artifact, and then update the main protocol/status handoff documents.
5. Keep native Writer document lifecycle work independent of Wine/Winux runtime supervision.


### Additional implementation follow-up — Python bridge workflow #33

- The heartbeat handler now matches the captured Agent response: HTTP 200, body TickTack, Content-Type text/html; charset=ISO-8859-1.
- protocol.py now exposes a bounded serializer for the observed successful response-word envelope. It Base64-encodes opaque document bytes under return-types/type with application/msword and encryption=base64; it does not transform the document.
- Python bridge workflow #33 (run 43707888187) passed all 42 tests, including heartbeat contract checks, a synthetic >1 MB request payload, response-envelope round-trip, input validation, and response-size enforcement.
- The response serializer is a building block only. No production EditWordDocument handler, init endpoint, LibreOffice integration, or close-time Almas registration flow is claimed complete.


### Additional implementation follow-up — init script workflow #36

- Stream 4's complete init response confirms the bridge script listens for parent-window message events, POSTs event.data to the local /?invoke endpoint, returns responseText to event.source via postMessage, and sends the <inited /> marker to the parent.
- The script generates invoke values with Math.floor(Math.random() * 99999); this is a per-request random value, not a method identifier.
- Python BridgeHTTPServer now implements GET /?init=<digits>_<digits>. Its 994-byte template is byte-for-byte identical to capture stream 4 when port and parent origin match; runtime substitutions are limited to the bound loopback port and an explicitly allowlisted parent origin derived from Referer.
- Parent-origin allowlisting is separate from POST Origin allowlisting because the capture shows the Almas page as the init Referer while the subsequent POST Origin is the local loopback service.
- Python bridge workflow #40 (run 43708542723) passed all 45 tests, including init script generation, dynamic port, allowlisted and rejected parent origins, and malformed init query rejection. A direct comparison confirmed byte-for-byte parity with the captured init response.
- This is a capture-matched endpoint implementation, not yet an end-to-end test against the actual Almas page/browser.


## Long-lived EditWordDocument request confirmed; close trigger pending — 2026-11-15

Packet-level analysis of stream 18 has now resolved the timing question:

### Direct packet timing

- TCP tuple: 127.0.0.1:61189 → 127.0.0.1:1984.
- The complete HTTP request body (Content-Length 1,177,821) is present by relative time 0.002154 s.
- The first server response payload arrives at relative time 54.560037 s.
- Gap from complete request body to first response byte: 54.557883 s.
- The 1,166,820-byte response is transmitted between 54.560037 s and 54.561399 s (about 1.362 ms).
- Two Agent heartbeat streams begin during the wait, at 126.2416352 s and 146.4003695 s in capture-relative time.
- The request is POST /?invoke=58351; its Origin is http://127.0.0.1:1984. The response is HTTP/1.1 200 with Content-Length 1,166,820.

This proves the local service receives the full EditWordDocument body promptly, keeps the HTTP request open for about 54.56 seconds, and only then begins sending the response. The delay is not the time required to transfer the response document.

### What this means

The single long-lived XHR is now confirmed at the transport level. It is strongly consistent with the Word editing session remaining active during the wait and the response being released when that operation finishes. The user's observation and the custom register-changes prompt make Word close/save the leading explanation for the release event.

However, the exact causal edge from the Word close callback to the HTTP response is still not directly mapped. The LoadDocument code reaches WriteContent after a series of COM/helper calls, but no obvious explicit WaitFor/ProcessMessages loop has yet been identified in the decoded ranges. The wait may be inside a COM call, nested modal/message processing, or another helper.


### What is still unproven

- Which COM call, modal UI loop, worker synchronization, or helper keeps LoadDocument active for the 54.56-second interval.
- Whether the captured response is produced before the user finishes editing or after the close/register prompt.
- The exact Save / No / Cancel COM variant types and how the returned file is consumed by the Almas page.
- The service-side Base64 decode stage for wordBody and the Almas parent page's final registration handler.
- Whether a separate close request exists in other workflows/capture sessions.


### Next focused trace

A separate request-lifecycle analysis should trace the COM/helper calls between LoadDocument entry and WriteContent, identify the wait/release mechanism, and correlate it with the registered Word close/register callback, and decode the BeforeSave prompt strings around 0x004CD3C0–0x004CD50C.


## Temporary Word-process cleanup discovery — corrected by export-table evidence (2026-11-15)

Filename workflow #9 (run 43710547860, artifact 14160317510) and the complete export table establish the public BPL API names. TD32 procedure labels at these addresses are shifted/mismatched:

- Exported RemoveTempFiles is at VA 0x0044AD30. It obtains the Windows temp path and invokes DeleteTempRAW on masks including %TEMP%\efg*.*, %TEMP%\~$g*.*, and %TEMP%\temp-emwatwf\*.* (the last mask is retried after ensuring the directory exists).
- Exported CloseAllWords is at VA 0x0044AE98. It enumerates top-level windows with FindWindowW/GetWindow/GetWindowTextW and checks title markers including "GamElectronic EMWAT" and ".doc". On a match it runs taskkill.exe /f /im WINWORD.EXE, sleeps 100 ms, and repeats; it then calls RemoveTempFiles (0x0044AD30).
- Exported DeleteTempRAW is at VA 0x0044B0F8. Although TD32 labels this address GetFileVersion, its body enumerates matching files with FindFirst/FindNext, normalizes attributes with FileSetAttr, and deletes matches with DeleteFile.
- Exported GetFileVersion is at VA 0x0044B2DC. Although TD32 labels this address Finalization, its body parses version-resource data. Its direct callers include Applicationactivities.SetEmwatVersion and UpgradeEmwatPlugin.
- The full export list also exposes TEmwatMethod.Invoke (0x0046C9E0) and the PerformMethod entrypoints for EditWordDocument, CompareWordDocument, ScanDocument, ImageEdition, and related operations. These exports form the likely service-to-BPL dispatch surface.
- No internal direct caller of exported CloseAllWords was found. Because it is exported, EmwatService.exe may invoke it externally by package export; the service binary is not present in this analysis set, so the external call site is unknown.

This is a global Word-process/temp-file cleanup API, not evidence of the main editor's user-driven close callback. Do not connect it to the observed user close behavior until the external invocation point is identified.


## Registry read-side closure — 2026-11-15

Registry workflow #2 (run 43709159573, artifact 14159334586) resolved the two settings that were previously marked as lacking a startup read path:

- TETracer constructor at 0x00466CA0 opens HKCU\\Software\\Emwat\\Dynamic Config.
- It checks ValueExists, then reads integer key Logging Level into object offset +0x10.
- It checks ValueExists, then reads Boolean key Save I/O Trace Files into object offset +0x11.
- TWordViwer constructor separately reads Background Priniting, Dont Ask Save On Print, Save Before Print, and AutoSaveInterval.
- The settings-unit Finalization routine opens the same HKCU\\Software\\Emwat\\Dynamic Config subkey and reads the same six persisted settings into associated controls. Its exact lifecycle trigger (unit finalization versus a mislabeled form lifecycle method) remains to be mapped.

The TETracer.GetUniquePostfix procedure at 0x00467C18 uses the exact registry names Save I/O Trace Files and Created IO Trace Count. It checks whether I/O tracing is enabled, reads the count, decrements it, and writes it back. When the count becomes non-positive, it disables Save I/O Trace Files and resets Created IO Trace Count to 15. The routine then creates and writes a trace file. This is a bounded trace-file quota/countdown, not evidence of the main letter's save-registration path.

The same caller scan resolved a separate image/print settings branch: TfrmImageTools.SetOldParamRecord reads from HKCU\\SOFTWARE\\Emwat\\PrintParams, and TfrmImageTools.ShowPrintPanel writes the same subkey. Four floating-point values are mLeft, mTop, mRight, and mBottom; integer values are Posotion (exact misspelling), Size, and PrintRange. These belong to image/print tools, not the main Word registration flow.

This closes the earlier uncertainty about Logging Level and Save I/O Trace Files startup reads. Do not conflate these diagnostic/image settings with the Word close/registration workflow.


## Word close prompt confirmed — request-lifecycle workflow #1

The focused trace decoded the exact BeforeSave prompt and its control flow:

- The callback's log strings are "Document.OnBeforeClose Called." and "Document.OnBeforeClose succeed."
- The Persian prompt is: "محتويات اين سند تغيير كرده است. آيا مايل به ثبت تغييرات مي‌باشيد؟" (the document contents changed; would you like to register the changes?).
- The three buttons are "موافقم", "خیر", and "انصراف".
- Dialog result 2 writes Cancel = -1 and exits without invoking the final Document.Close call.
- Dialog result 6 enters the affirmative branch and passes -1 through the SaveChanges variant setup.
- Other non-cancel results enter the negative branch and pass 0 through the SaveChanges variant setup.
- On the non-cancel path, the handler calls the Word Document.Close interface slot +0x29C, releases the current document interface, clears the viewer's active-document state, and logs "Document.OnBeforeClose succeed."

This is direct evidence that the main editor's registered 0x004CD154 handler implements the custom close/register prompt and closes the document after the user's choice. Its TD32 symbol says BeforeSave, while its own log strings say OnBeforeClose; until the event-sink slot is mapped, retain both observations rather than assuming the COM event name. It explains why pressing Word's Save toolbar button is not the only route into the registration prompt: this handler participates in the close/save lifecycle. The exact COM variant type/argument interpretation and response timing still need the focused LoadDocument control-flow trace.


### LoadDocument Base64 boundary clarification — request-lifecycle workflow #3

- LoadDocument's wordBody argument is held in [ebp-0x1C] and its bytes are written directly to the temporary TFileStream at 0x004B7821–0x004B783A.
- The Base64Decode call at 0x004B7E44 is invoked with [ebp-8], not [ebp-0x1C]. The surrounding code walks a separate indexed data collection, so this decode must not be attributed to wordBody; it is likely image/auxiliary data, but that identity is not yet proven.
- The capture's XML wordBody value is Base64 text. Since LoadDocument writes its argument directly, the decode may happen in EmwatService's XML/parameter layer before the BPL call. That service-side boundary is not present in the current BPL input, so this remains unresolved.


### Request/response DOC comparison — pcap workflow #4

The second pcap workflow compared the decoded request wordBody with the response-word payload:

- Request DOC: 872,960 bytes; OLE Compound File signature.
- Response DOC: 874,957 bytes available from the capture; the response contains 17 sequence gaps totaling 68 missing Base64 characters, all inside the document value.
- Those 68 missing Base64 characters represent 51 decoded bytes. The estimated complete response size is therefore 875,008 bytes, exactly 2,048 bytes (four 512-byte sectors) larger than the request and sector-aligned.
- Both OLE headers report 14 FAT sectors. The first directory sector pointer at header offset 48 changes from 1698 (request) to 1702 (response).
- The first differing decoded byte is offset 48, before the first capture gap; the first approximately 49,041 decoded bytes are available for comparison and are not equal.

This proves the response is not a byte-for-byte echo of wordBody. The response is a rewritten/restructured legacy DOC container; the directory-sector pointer moves by four sectors and the complete file is estimated to grow by 2 KiB. The pcap's 68 missing Base64 characters prevent a full-file hash/equality comparison, so do not claim exact content edits beyond the intact prefix and OLE header evidence.

Combined with the 54.557883-second wait after the request body completes, this strongly supports the model that EMWAT holds the original request during the Word editing operation and returns the processed document when the operation ends. The custom register-changes prompt is the leading candidate for the release point; the exact callback-to-response call chain and the parent page's final Almas POST still need proof.


## Parallel execution update — verified runs on 2026-11-15

The repository already contains separate GitHub Actions workflows for the independent branches. The latest checked runs below all completed successfully; this is a status snapshot, not a claim that every workstream is finished.

| Branch | Workflow run | Result | Artifact |
|---|---:|---|---|
| HTTP capture timing + document comparison | #6 / `43711788034` | success | `14160597175` |
| EditWordDocument request parameter structure | #3 / `43711758572` | success | `14161075867` |
| Word wait/COM call chain | #7 / `43711714558` | success | `14161275669` |
| Word event sink | #7 / `43711661477` | success | `14160309683` |

### New result: captured response contains the returned DOC

The PCAP comparison branch establishes that the selected `POST /?invoke=58351` receives HTTP 200 with a `response-word status="success"` XML envelope and a `return-types/type` payload marked `mimetype="application/msword"` and `encryption="base64"`. The decoded payload begins with the OLE Compound File signature.

The returned document differs from the submitted `wordBody` in the intact capture prefix, including the CFB first-directory-sector pointer (1698 → 1702). The response capture has 17 four-byte TCP sequence gaps, so its full size and hash cannot be verified. The estimated size delta is 2,048 bytes, but remains an estimate. See `docs/PCAP-EDITWORD-DOCUMENT-ROUNDTRIP.md`.

### New request structure observations

The latest request-parameter artifact confirms that the captured `wordBody` is Base64 text decoding to 872,960 bytes of OLE Compound File / legacy DOC data. The request includes a `requested-types/type` entry for `application/msword`. It also contains a `tokenizedReceivers` optional attribute whose nested content is marked `urlencoded`; this is a structural observation only, and its content is intentionally not copied into documentation.

### Parallel execution rules going forward

1. Keep the existing independent workflows separate; do not duplicate their jobs inside the monolithic Word lifecycle workflow.
2. Treat each artifact as a branch output and merge only evidence summaries into shared docs.
3. Preserve capture gaps and partial disassembly coverage explicitly; never silently fill missing bytes or treat missing procedures as proof of absence.
4. Continue the next analysis in parallel: (a) resolve the Word event sink's actual dispatch/argument mapping, (b) improve recovery form list-population and storage-path tracing, (c) analyze the TCP payload export alongside the PCAP with sequence-aware validation, and (d) maintain the Python bridge/session tests.
5. The highest-value external evidence is a second, gap-free capture of the same close-without-Save workflow, ideally with a known harmless edit, so request and returned document can be compared completely.


## Recovery workstream split — verified 2026-11-15

Recovery analysis is now split into two independent workflows:
- `analyze-recovery-store.yml`: form procedures, Word Automation lifecycle, resource and embedded-string triage. Run #2 (`43715017039`) succeeded; artifact `14162835454`.
- `analyze-recovery-paths.yml`: autosave helper implementations, direct callers, path constants, and filesystem APIs. Run #2 (`43715620696`) succeeded; artifact `14162601983`. Run #3 (`43715933101`) adds age/password/process helper traces and is queued/running.

Confirmed recovery evidence now includes the `*.easz` file mask in both the recovery UI and old-AutoSave cleanup, `TDirectory.GetFiles` as the enumeration API, `DeleteFileW` as the conditional cleanup API, and Local AppData resolution through CSIDL `0x1C`. The actual AutoSave directory and exact retention interval are still unresolved. Details: `docs/RECOVERY-STORE-ANALYSIS.md`.

The next independent tasks are to resolve the `euGetAutoSavePass` read path, determine the units behind the `0x18` age threshold, and identify the root/prefix returned by `euGetTempFileName`. Do not infer a final directory or retention policy from the current evidence.


## Additional parallel outputs — 2026-11-15

- Recovery path run #5 (`43716527945`, artifact `14162334126`) confirmed that `euResetMemory` constructs an object from class metadata at `0x00452558`, calls virtual slot `+0x4C`, and passes source/destination paths to virtual slots `+0x0C` and `+0x3C`. It copies a 16-byte block from one of two global data areas based on a Boolean flag. Exact class and transform semantics are pending.
- Recovery path run #6 (`43716808189`, artifact `14162727483`) succeeded and supplied the VMT/global reference dumps. Run #7 (`43717048702`) is tracing the class typeinfo and its VMT method implementations.
- Word event sink run #8 (`43716384031`, artifact `14162362638`) extracted 20 pointers from `0x00627B74`, but run #9 (`43716905570`, artifact `14162568118`) proved these point to Delphi error strings (`Err_20000`, `Request XML is invalid.`, `Can not open document.`, etc.), not callback functions. The workflow has been corrected to classify this as a server error map. Actual event callback/DISPID mapping remains unresolved.
- The inner `wordConfig` parser (`python/src/emwat_linux/word_config.py`) is implemented and covered by CI. Python bridge run #44 (`43716641854`) passed 53 tests. It preserves opaque field contents and per-field encoding metadata; no production document handler is wired yet.


### Correction to event-sink branch interpretation

The pointer list at `0x00627BB0` is an error-message string table. The previous callback-table interpretation was incorrect and is explicitly superseded in `docs/WORD-COM-INTERFACE-DISPATCH.md`. Workflow run #10 changes the extraction to decode these strings rather than tracing them as procedures. Main-viewer BeforeSave registration at `0x004CD154` remains independently confirmed.


## Recovery archive reader identification — 2026-11-15

- Run #7 (`43717048702`, artifact `14163205743`) identifies `Sevenzip.T7zInArchive` in the `euResetMemory` object construction path; `0x00452ED8` is TD32-labeled `T7zInArchive.GetInArchive`. The type metadata exposes archive properties including `Password`, `Stream`, `PasswordIsDefined`, `SubArchiveMode`, and extraction callbacks.
- Password interpretation was corrected in `docs/RECOVERY-STORE-ANALYSIS.md`: `euGetAutoSavePass` plus `@25*gamsign*25@` is a distinct AutoSave-related value, not yet proven to be the `.easz` password. The recovery open path passes `mW@Tlogs43end_+` to object slot `+0x44` when no optional password is supplied. The property/slot mapping is pending.
- Recovery workflow run #9 (`43717439805`) adds the SevenZip class method indexes. Run #10 (`43717465958`) traces those methods and the relevant VMT metadata.


## Current CI snapshot — 2026-11-15

- Python bridge run #46 (`43717259882`) passed 58 tests after adding the inner `wordConfig` parser and `EditWordDocument` request normalizer.
- Network metadata run #2 (`43707410915`, artifact `14159156356`) identifies 15 streams touching port 1984 and independently confirms stream 18's `EditWordDocument` request/response metadata; detailed cross-check is in `docs/PCAP-EDITWORD-DOCUMENT-ROUNDTRIP.md`.
- Word error-map run #11 (`43717625474`, artifact `14162998865`) succeeded; full normalized strings are in `docs/WORD-ERROR-MAP.md`.
- Recovery SevenZip class method runs #9 and #10 (`43717439805`, `43717465958`) were still executing at this status snapshot. Do not mark the archive password or `.easd` transformation as resolved until their artifacts are inspected.


## Parallel update — SevenZip plugin and native close orchestration (2026-11-15)

### Recovery/plugin branch

- Workflow `Analyze EMWAT recovery SevenZip plugin`, run `43719323732`, completed successfully; artifact `14164146310`.
- TD32 indexes `T7zPlugin`, `T7zInArchive`, and `T7zOutArchive`. The shared `T7zPlugin.CreateObject` method is directly called by both `T7zInArchive.GetInArchive` and `T7zOutArchive.GetOutArchive`.
- The plugin constructor at `0x00452C10` calls `T7zOutArchive.CryptoGetTextPassword2` at `0x004543C4`; that method calls helper `0x00404734`, resolved as the RTL TObjectList constructor, using the class pointer at global `0x0062FBB8` and storing the list at object offset `+0x2C`. This does not identify the writer password value/provider.
- `euUnArchive` is a direct caller of the plugin constructor and uses global `0x0062A824`. `euResetMemory` instead calls the separate `CreateOutArchive` helper at `0x00452BBC), which uses the literal `7z.dll` and a 16-byte global-derived value before a virtual dispatch.
- The wrapper `T7zOutArchive.SetPassword` is a no-op stub. `T7zInArchive.SetPassword` stores the Unicode password at instance offset `+0x58` and invokes an extraction-style interface slot with a callback-like helper; no raw static pointer to this method was found. The exact mapping of `euResetMemory` slot `+0x44` remains unresolved.
- Full caveats and method traces are in `docs/RECOVERY-STORE-ANALYSIS.md`, sections 14–16.

### Native document orchestration branch

- Added `office_adapter.py`, `document_coordinator.py), and `editword_service.py` under `python/src/emwat_linux/`.
- The adapter contract separates modification callbacks, engine-save callbacks, close notification, and final export. Save records a revision but does not return the document; close triggers final export.
- The service normalizes an EditWordDocument MethodCall and assigns a fresh local session ID; it does not reuse the `invoke` query nonce.
- Python bridge CI run `43719841339` passed **66 tests**. These tests use a fake office adapter; no LibreOffice UNO implementation or production HTTP handler is claimed complete.


### Recovery path workflow #10 — reader/extract and cleanup targets

- Workflow run `43719180035` completed successfully; artifact `14164088249` inspected.
- `T7zInArchive.SetPassword` stores the Unicode password at `Self+0x58` and invokes the archive interface's extraction-style slot with a callback-like helper. `PrepareOperation` reads the stored password field and handles callback/context fields `+0x50/+0x54`. `CryptoGetTextPassword` and `SetPasswordCallback` are stubs.
- The `euResetMemory` dispatch sequence (+0x44 password, +0x0C path, +0x3C path) strongly aligns with `SetPassword` → `OpenFile` → `ExtractTo`, but the VMT/interface slot table remains unproven. Keep this as the leading hypothesis.
- Cleanup APIs resolve exactly: `TDirectory.GetFiles` for `*.easz`, `FileAge`, `FileDateToDateTime`, `Now`, `HoursBetween`, and `DeleteFileW`; threshold is 24 hours.
- The `CryptoGetTextPassword2` helper was corrected: it initializes a `TObjectList` via RTL constructor `0x00404734`; it does not identify the writer password provider.
- See `docs/RECOVERY-STORE-ANALYSIS.md`, sections 16–17.


### Plugin follow-up #2 — euUnArchive is a separate path

- Run `43720247793` completed successfully; artifact `14164382428` inspected.
- `euUnArchive` (`0x00456DFC–0x00456EFF`) is the only direct bounded caller of `T7zPlugin` constructor in this scan. It uses global `0x0062A824`, then calls object/interface slots `+0x28`, `+0x10`, and `+0x18` while iterating paired collection-like inputs.
- This multi-item helper is separate from `euResetMemory` → `CreateOutArchive` and the latter's `+0x44/+0x0C/+0x3C` dispatch sequence. Slot meanings and archive direction remain unresolved; do not use euUnArchive to infer the .easz recovery protocol.
- Detailed trace: `docs/RECOVERY-STORE-ANALYSIS.md`, section 18.


### Python bridge dispatcher adapter — 2026-11-15

- Added `editword_handler.py`, a factory that adapts `EditWordDocumentService` to the XML dispatcher contract.
- Successful final bytes are serialized with the observed `response-word` envelope and Word MIME type.
- Cancellation response mapping is a mandatory injected factory; original cancellation semantics remain unknown and are not guessed.
- The factory is not yet registered in the application; a real LibreOffice adapter is still required.
- CI run `43721449170` passed **69 tests**.


### Close-driven coordinator concurrency hardening — 2026-11-15

- `DocumentCoordinator` now serializes office callbacks with close/finalize transitions using an `RLock`; callbacks are disabled after close and before final export.
- Regression test covers delayed modification/save events during export and after response return. Python CI run `43722184809` passed **70 tests**.

### SevenZip class-interface mapping branch — 2026-11-15

- The base-class workflow run `43721583502` completed successfully (artifact `14165155588`). It indexed `T7zArchive` base methods, but did not resolve the returned COM-style interface's virtual slots.
- Extended `resolve_delphi_vmt_slots.py` and `trace_delphi_interfaces.py` to include the SevenZip classes and `IInArchive`/`IOutArchive`/stream interface RTTI. Updated `.github/workflows/analyze-recovery-plugin.yml` to emit `SevenZip-VMT-slots.md` and `SevenZip-interface-tables.md`.
- New analysis run `43722345225` is in progress. Its purpose is to prove or reject the leading `SetPassword → OpenFile → ExtractTo` mapping for `euResetMemory`, not to assume it.


### SevenZip custom interface identity resolved — 2026-11-15

- Plugin workflow run `43722345225` completed successfully; artifact `14165136040` was inspected.
- `CreateOutArchive` constructs `T7zInArchive` at VMT `0x004525B0` and returns the interface at `Self+0x70`. Its interface table entry 6 has `IOffset=0x70`, IID `022cf785-3ece-46ef-9755-291fa84cc6c9`, and VTable `0x00452420`.
- Thus `euResetMemory` slots `+0x44/+0x0C/+0x3C` are confirmed to be calls on this custom interface. Method names remain unproven; vtable tracing was extended to 20 entries to expose the actual targets.


### Word event source and autosave recovery follow-ups — 2026-11-15

- `WordAppDocumentBeforeClose` (`0x004CCBBC`) calls shared helper `0x004BCA88`, which is also used by `GetCaptionItemFont`; it is not evidence of a close-time registration/POST routine. Its direct caller remains `FillImgFldsForPrint` (`0x004CCF8F`).
- Generated Word server metadata contains CLSID `000209FF` (ApplicationClass), CLSID `00020906` (DocumentClass), and known ApplicationEvents/ApplicationEvents2 interface GUIDs. This identifies OLE metadata but not the live event sink subscription.
- Parallel work continues in the SevenZip vtable mapping, Word server-data RTL helpers, autosave Delete caller, Word lifecycle callbacks, and BPL method-index branches. Keep event registration and close-time Almas commit as unresolved until the relevant traces prove them.


- Confirmed one `euResetMemory` interface slot: custom vtable `0x00452420 +0x0C` forwards through thunk `0x004522E9` to `T7zInArchive.OpenStream` (`0x00452FDC`), accepting `IInStream`. This corrects the earlier `OpenFile` candidate. The first `euResetMemory` argument is an input stream interface; the form Delete trace is checking its construction. `+0x3C` and `+0x44` remain unresolved.


### `euResetMemory` interface slot mapping resolved — 2026-11-15

- The 20-slot interface table from run `43722990639` / artifact `14165676602` resolves the custom `T7zInArchive` interface calls:
  - `+0x0C` → `OpenStream(IInStream)` at `0x00452FDC`.
  - `+0x3C` → `SetPassword(UnicodeString)` at `0x00453860`.
  - `+0x44` → virtual `T7zArchive` constructor at `0x0045392C`.
- `SetPassword` stores its string at `Self+0x58`, creates an extraction callback from `Self+8`, and invokes the internal archive interface slot `+0x1C` for all items (`indices=NULL`, `numItems=-1`, `testMode=0`). This suggests the recovery routine triggers an all-items archive operation through this callback; do not yet claim the exact output path.
- Remaining recovery work: inspect the autosave Delete caller to type the input stream and second string, and trace the callback object at typeinfo references `0x0045391C` and `0x00453850` to identify the output destination and lifecycle.


- Compare `SetPassword` callback typeinfo `0x0045391C` with `ExtractTo` callback typeinfo `0x00453850`. Both invoke internal archive slot `+0x1C` for all items, but `SetPassword` uses `testMode=0` and a callback from `Self+8`; `ExtractTo` stores context at `Self+0x50/+0x54` and uses its Boolean argument as `testMode`. Latest plugin run `43723896564` traces both typeinfo regions and references to resolve output semantics.
