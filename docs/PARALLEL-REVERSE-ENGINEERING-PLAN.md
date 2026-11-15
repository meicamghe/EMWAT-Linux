# Parallel reverse-engineering workstreams — run 117

Source: existing GitHub Actions artifact `emwat-word-lifecycle-run117` and its TD32 disassembly/metadata files. This document records independent findings that can be pursued in parallel; it does not claim the complete EMWAT protocol is decoded.

## Workstream A — request/command dispatch and TEmwatMethod.Invoke

### Confirmed observations
- `TEmwatMethod.Invoke` is a 433-byte procedure at `0x0046C82C–0x0046C9DC`.
- Its Delphi signature contains a `TDictionary<AnsiString, ...>`.
- It constructs/initializes a `TXMLEmwatType` object through `0x0044C238`.
- It enumerates dictionary pairs using `TEnumerable.ToArrayImpl` (`0x0046DE84`) and `TPairEnumerator.DoGetCurrent` (`0x0046E324`).
- It uses `TDictionary.AddOrSetValue` (`0x0046DC8C`) to insert/update values in a dictionary during this traversal.
- The only direct TD32-bounded caller currently identified is `TEmwatMethod.Finalization` at `0x0046CA67`. This is important: the current evidence does **not** establish that this method is the HTTP `invoke` route handler.

### Implication
Treat this as a dictionary-to-XML/type-object transformation/finalization helper until the caller chain and request dispatcher are resolved. Do not equate its name with the HTTP query parameter `?invoke=`.

### Next targets
1. Trace `TEmwatMethod.Finalization` around `0x0046CA67` and identify the dictionary's producer and consumer.
2. Resolve the class/VMT method that dispatches the HTTP `invoke` parameter.
3. Correlate command metadata with the observed `POST /?invoke=58351` payload only after the request parser is identified.

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


## High-confidence request/Word lifecycle model — 2026-11-15

The latest static traces and TCP capture now fit a single long-lived request model better than a separate close-time POST.

### Directly observed evidence

- The browser bridge sends one POST for EditWordDocument and receives one response-word success document in the same TCP stream.
- TCP stream 18 starts at relative time 106.8698387 s and lasts 54.6315 s (to approximately 161.5013 s). The request carries 1,177,821 bytes and the response carries 1,166,820 bytes.
- Two independent Agent heartbeat streams begin during that same interval, at 126.2416352 s and 146.4003695 s (approximately +19.37 s and +39.53 s after the EditWordDocument stream begins). This is consistent with the service keeping the document session active while the Agent remains alive.
- TEditWordDocument.PerformMethod calls TWordViwer.LoadDocument synchronously before it sets the method result flags.
- On the successful LoadDocument path, the BPL writes the returned document into AResponseInfo.ContentText and calls TIdHTTPResponseInfo.WriteContent.
- The init JavaScript sends the original message body through one XHR and relays that XHR's responseText to the parent page with postMessage. It contains no separate close-time POST implementation.
- The main editor event record installs routine 0x004CD154 (TD32 symbol: WordAppDocumentBeforeSave), NewDocument (0x004CD54C), WindowActivate (0x004CD9C0), and a settings-dependent print/options callback. The separate routine symbolized WordAppDocumentBeforeClose (0x004CCBBC) is not the pointer installed in this record. The precise COM event-slot name corresponding to record offset +0x80 remains to be proven.
- WordAppDocumentBeforeSave can display the custom save/register prompt and then calls the Word Document.Close interface slot (+0x29C). The separate BeforeClose routine is not evidence of the main editor's close hook.

### Current best-fit model — not yet a fully proven causal chain

1. Almas sends one EditWordDocument message to the local bridge.
2. The service dispatches the method and enters LoadDocument; the Word session remains active while the user edits.
3. Word's BeforeSave callback handles the save/register prompt and document-close path.
4. LoadDocument completes its successful response path and returns response-word with the resulting Word document.
5. The original XHR completes; the bridge JavaScript posts responseText back to the Almas parent page, which can then process/register the returned document.

This model explains the user's confirmed observation that closing Word is followed by registration even without pressing Word's Save button, and it explains why the capture contains only one EditWordDocument POST rather than a second close-time POST.

### What is still unproven

- The capture provides conversation start/duration, not per-packet timestamps, so the exact instant at which response bytes begin is not yet established.
- The exact control-flow edge that makes LoadDocument wait for the Word session to close still needs a focused trace through the remainder of OnTmrAutoSave and its event/message loop.
- The exact Save / No / Cancel dialog mapping and whether each branch returns a document or cancels the XHR need string/branch confirmation.
- The service-side Base64 decode stage for wordBody and the Almas parent page's final registration handler are outside the currently analyzed BPL.
- Do not claim a close-time POST. Current evidence instead favors completion of the original EditWordDocument request.

### Next focused trace

A separate request-lifecycle analysis should decode the remainder of OnTmrAutoSave (0x004BA058–0x004BB3AF), identify message-loop/wait operations, trace LoadDocument callers and response dispatch, and decode the BeforeSave prompt strings around 0x004CD3C0–0x004CD50C.


## Temporary Word-process cleanup discovery — 2026-11-15

Filename workflow #5 (run 43708844302, artifact 14158984794) clarified that the routine named DeleteTempRAW is not a simple file-deletion loop:

- DeleteTempRAW (0x0044AE98) calls FindWindowW with null class/title filters, then iterates windows using GetWindow and reads each title with GetWindowTextW.
- It compares window-title text against embedded strings including "GamElectronic EMWAT", ".doc", and other markers.
- On a matching window it calls ShellExecuteW with taskkill.exe and arguments "/f /im WINWORD.EXE", then sleeps 100 ms and repeats the window scan.
- Once the scan ends it calls CloseAllWords (0x0044AD30).
- No direct DeleteFile call appears in the decoded DeleteTempRAW procedure. The subsequent CloseAllWords routine constructs temp-path patterns and calls a helper named GetFileVersion; its exact file handling remains unresolved.

This is potentially a global Word cleanup/termination path, not evidence of the main editor's user-driven close callback. Its actual caller and whether it runs at startup, service shutdown, or another lifecycle point are still unknown. Do not connect it to the observed user close behavior until callers are traced.


## Registry read-side closure — 2026-11-15

Registry workflow #2 (run 43709159573, artifact 14159334586) resolved the two settings that were previously marked as lacking a startup read path:

- TETracer constructor at 0x00466CA0 opens HKCU\\Software\\Emwat\\Dynamic Config.
- It checks ValueExists, then reads integer key Logging Level into object offset +0x10.
- It checks ValueExists, then reads Boolean key Save I/O Trace Files into object offset +0x11.
- TWordViwer constructor separately reads Background Priniting, Dont Ask Save On Print, Save Before Print, and AutoSaveInterval.
- The settings-unit Finalization routine also reads the same six persisted settings and assigns values to the associated controls. Its exact lifecycle trigger (unit finalization versus a mislabeled form lifecycle method) remains to be mapped.

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
