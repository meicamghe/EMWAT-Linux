# EMWAT-Linux — Project Handoff

Last reviewed: 2026-11-14

This is the concise continuity entry point for future sessions. Detailed reverse-engineering evidence remains in the linked analysis documents.

## Product goal — fixed

Rebuild EMWAT as a **native Linux application** while preserving the real Windows product's workflows. Running the Windows EMWAT build under Wine is not the target product.

The confirmed real-world workflow is a local desktop bridge for the Almas Gam web-based office automation system: data and letter templates are prepared in the web system, EMWAT opens Word for editing, and the resulting document is returned to the same system. Some letters are image-only, so scanning and image-document workflows remain in scope.

## Confirmed user observations and constraints

- **User-observed product requirement:** the user tested that closing the document applies/registers changes whether or not Save was pressed. Reproduce this behavior in Linux. The exact internal event, file extraction method and transport remain to be identified.
- The user has supplied the original Windows installer/extracted files for analysis. The historical extraction location was `D:\EmwatInstaller`.
- The user stated that the extracted EMWAT files contain no customer information. Still inspect any future traces, sample letters, cookies, tokens, and logs before publishing them.
- The original Windows binaries examined are PE32/x86; this is a fact about the analyzed binaries, not a reason to make the Linux implementation 32-bit-only.
- Do not assume the database engine, browser engine, complete API, authentication mechanism, or wire format until evidence confirms them.

## Confirmed static-analysis findings

- `EmwatService.exe` hosts a local HTTP service based on Indy components.
- A default local port of `1984` appears in strings; the Agent has a heartbeat string to `http://127.0.0.1:1984/?heartbeat`.
- A JavaScript bridge uses `postMessage` and HTTP POST to a local `127.0.0.1:<port>?invoke=<random>` endpoint; response text is relayed to the parent window.
- Word/Excel automation through COM/OLE is supported by strong type-information and symbol evidence.
- Word connector/type structures include request and response XML models, fields, settings, styles, status and return-type metadata.
- Word lifecycle symbols include autosave, silent-save, before-close and before-save handlers. These support the existence of managed save/close behavior but do not alone establish exact wire timing.
- Image and scan UI structures have been decoded, including scan preview, image tools and simple image editor forms.
- ImageGear and ImageEn paths have been analyzed, including crop, rotate, flip, save, scan and multi-page handling. Do not infer enum meanings or scanner ABI from names alone.
- The exact database, full invoke API, complete payload contract, browser implementation and several runtime behaviors remain unresolved.

## Native Linux architecture principles

- Do not use Wine as a final runtime dependency.
- Keep the browser bridge, local service, document engine, and scan/image subsystem as separate components.
- Bind the local service to loopback only; validate origins/tokens, payload sizes, file paths, timeouts and lifecycle behavior.
- Do not invent an API that merely resembles EMWAT. Extract the original request/response contract first.
- LibreOffice Writer is the candidate document application/compatibility bridge, but real templates and field behavior must be tested.
- Preserve image-only letters, scanning, multipage documents, image edits and print-related workflows.
- Do not select a local database without evidence that one is needed and what data it must own.
- Never publish customer letters, credentials, cookies, private endpoints or unredacted runtime traces.

## Current evidence and technical documents

Start with these documents; do not repeat their completed work without new evidence:

- `docs/PROJECT-STATUS.md` — overall findings, confidence levels and next actions
- `docs/PRODUCT-WORKFLOW-ANALYSIS.md` — confirmed product workflow and revised priorities
- `docs/HTTP-LOCAL-API-ANALYSIS.md` — local HTTP service and JavaScript bridge
- `docs/WORD-DOCUMENT-PROTOCOL-ANALYSIS.md` — Word connector, XML structures and lifecycle
- `docs/OFFICE-COM-ANALYSIS.md` — Office Automation/COM
- `docs/IMPORT-TABLE-ANALYSIS.md` — PE imports and dependencies
- `docs/RESOURCE-ANALYSIS.md` — COM and PE resources
- `docs/SCAN-PREVIEW-DFM.md`, `docs/IMAGE-TOOLS-DFM.md`, `docs/SIMPLE-IMAGE-EDITOR-DFM.md` — decoded image/scan forms
- `docs/GEAR-API-CALLS.md`, `docs/IMAGE-CALL-GRAPH.md`, `docs/SCANNER-INTERFACE-ANALYSIS.md` — image/scanner call analysis

## Immediate next steps — in order (updated 2026-11-14)

1. **Finish the remaining XML method/serialization mapping.** The service parser's `TMethodInfo.Params` and BPL `TEmwatMethod.Invoke` use `TDictionary<AnsiString, AnsiString>`. Service slot `+0x0C` reaches shared wrapper `0x0046C9E0), which calls `TEmwatMethod.Invoke` (`0x0046C82C`) and then the subclass slot `+0x10`. Inside Invoke, local `[ebp-4]` is a `TXMLEmwatType` interface; its `+0xB0` thunk `0x0044B709` reaches `TXMLMethodType.AfterConstruction` at `0x0044C458), producing the interface in `[ebp-0x1C]`. That `TXMLMethodType` interface's `+0xCC` thunk `0x0044BA61` reaches `TXMLMethodType.Insert` at `0x0044C754), which appends a child and returns the interface in `[ebp-8]`. RTTI and VTable offsets strongly identify `[ebp-8]` as a `TXMLParamType` interface. Invoke then calls its `+0xB0` and `+0x68` slots with the first and second dictionary-pair strings. The TXMLParamType VTable thunks are `0x0044BDF5` and `0x0044BEB5`; they adjust Self by `-0x50` and resolve to `0x0044C8E4` and shared target `0x0044B568` respectively. The `+0x68` target `0x0044B568` is confirmed as `xmlrtl230.bpl!TXMLNode.SetText(UnicodeString)`, so the second pair string is the parameter node's text/value. The `+0xB0` target `0x0044C8E4` calls `xmlrtl230.bpl!TXMLNode.SetAttribute(UnicodeString, OleVariant)` with the literal attribute name `name` and the first pair string as its value. Thus each pair becomes an XML parameter node with `name` attribute and text content. Focused run 11 (`43571811038`, artifact `14105075475`) confirms both targets and the `name` literal. After the loop, TXMLEmwatType interface slot `+0x54` returns the serialized XML string into Invoke's output parameter; its VTable target still needs mapping. Next decode the TXMLMethodType +0xC8 attribute literal at `0x0044C6A4`: its implementation `0x0044C62C` (TD32 label `Get_Param`) passes the method-name string and this literal to `TXMLNode.SetAttribute`. The `class` attribute and `method` element literal are now confirmed. The TXMLEmwatType serializer getter slot `+0x54` resolves through thunk `0x0044B7A9` to `xmlrtl230.bpl!TXMLNode.GetXML` at `0x0044B590`. Remaining XML task: identify the constructor's second constant at `0x0044C4FC` passed to helper `0x00401430`, then validate the complete serialized XML against runtime captures.

2. **Trace the concrete Word-edit method and its document helper.** Run 76 recovered `TEditWordDocument` VMT `0x005ED764`; slot `+0x10` points to executable target `0x005EE82C`, despite the missing TD32 procedure record. The target reads `wordConfig`, `wordBody`, `letterImages`, and `signData`, then calls `TWordViwer.LoadDocument` at `0x004B7724` with the `TEmwatInvokeParam*` and output-string reference. `LoadDocument` parses the `word-document` config, prepares the document/Wordviewer, and reaches `OnTmrAutoSave` at `0x004B8A84` to register Word callbacks. The corrected registration maps `+0x80 → 0x004CD154` (TD32: `WordAppDocumentBeforeSave`), `+0x90 → 0x004CD54C`, and `+0x98 → 0x004CD9C0` (export name `WordAppNewDocument`). The registered BeforeSave callback at `0x004CD154` checks `Document.Saved`, prompts to save changes, and directly invokes interface slot `+0x29C` with three OleVariant arguments on Yes/No. It is not a registered BeforeClose callback. It has no direct HTTP call; trace its viewer helpers and parent-page message. It reads the generated temp document, builds the response XML, and deletes the temp file. Keep the TD32 symbol-name mismatch caveat for other connector classes.
3. **Finish the service request-record and input-stream trace.** `TMainForm.IdHTTPServerCommandGet` (`0x0047BF30`) and the XML/class dispatcher at `0x00470D00` are mapped through BPL slot `+0x0C` (`0x0046C9E0`) → `TEmwatMethod.Invoke` (`0x0046C82C`) → subclass slot `+0x10`. The handler's `TEmwatInvokeParam` layout is known, and its `SessionId` is a separate server-generated six-digit string. The object at `[ARequestInfo+0xD4]` is now identified with high confidence as `TIdHTTPRequestInfo.PostStream`; identify the exact stream virtual method names/signatures behind its size/read operations, and trace how the internal `SessionId` is consumed. The embedded bridge generates the numeric `invoke` value solely as a per-request URL nonce/cache-buster; it is not a method ID or response-correlation token. The bridge forwards `event.data` unchanged and returns `responseText` to the original `event.source`/`event.origin`.
4. **Validate the concrete HTTP response and its schema.** The successful `LoadDocument` path writes its output XML to `AResponseInfo.ContentText`, calls `IdCustomHTTPServer.TIdHTTPResponseInfo.WriteContent` (`0x0040448C` / IAT `0x0062F9C0`), and sets `TEmwatInvokeParam.bResultSet=true`; the generic dispatcher fallback is skipped. It references `application/msword` and `success`, but the exact serialized element layout/encoding still needs comparison with the captured runtime response. Also trace `bUnloadPkg` cleanup after `TEditWordDocument` sets it true. Do not assume `requested-types=application/msword` proves the final file format is DOC.
5. **Trace the registered BeforeSave callback to the parent-page message and final commit.** The callback at `0x004CD154` is `TWordViwer.WordAppDocumentBeforeSave`, registered at event-record `+0x80`; it is not `WordAppDocumentBeforeClose`. It calls `PreparePrintDocument` (`0x004CB108`), checks `Document.Saved` via `_Document` slot `+0xD8`, then prompts Yes/No/Cancel. Cancel sets the event Cancel word to `0xFFFF`; Yes/No directly invoke interface slot `+0x29C` with three OleVariant arguments (the same dispatch slot used by the three-argument wrapper at `0x0042FFF4`). It does not issue HTTP directly. The separately named `WordAppDocumentBeforeClose` at `0x004CCBBC` has only one direct bounded caller, `FillImgFldsForPrint` at `0x004CCF8F`, and no raw-pointer registration reference was found; its active event role is unproven. Continue by identifying which parent-page `postMessage` causes the bridge's close-time XHR and how its response applies the returned document.
6. **Retain autosave/close candidates only in their proven scope.** The `uSendLog` callback at `0x005EC580` belongs to the autosave-files UI and calls `CloseWordApp`; its DFM resource does not visibly bind a Word close event. WordXP Close wrappers have no direct TD32 CALL xrefs. Neither is the proven main letter close path.
7. **Resume scanner/image subsystem analysis after the connector path is understood.** Keep image-only letters, TIFF, rotate/crop, multipage processing, ImageGear/ImageEn and GEAR/SANE scanning as first-class requirements. Do not reduce the Linux port to text-only document editing.
8. **Only then implement the native Linux bridge contract and integration tests.** Keep the local service loopback-only, validate origins/tokens/payload sizes/file paths/timeouts, and test synthetic letters and templates with LibreOffice Writer. Do not implement guessed endpoints or claim end-to-end parity before protocol/runtime validation.


## Runtime validation questions

- What exact request/response reaches the local service for a Word document?
- What semantic role does the method-node constructor's second constant at `0x0044C4FC` play?
- How are template, fields, styles, body and attachments encoded?
- What is returned on close, including the user's observed close-triggered update?
- Can multiple documents be open at once?
- How are cancel, crash, autosave and recovery handled?
- How are image-only letters and scanned multipage documents transferred?

## Session start checklist

1. Read this handoff and `docs/PROJECT-STATUS.md`.
2. Read only the linked detailed documents relevant to the next checkpoint.
3. Inspect current GitHub Actions runs and the latest commits/artifacts before relying on a previous run.
4. Never repeat completed static-analysis tasks without new evidence.
5. Update `PROJECT-STATUS.md`, the affected analysis document, and this handoff when new evidence changes the next step.

## Evidence discipline

Every conclusion must be labeled as one of: user-observed, statically confirmed, runtime-confirmed, inferred, or unknown. A symbol, string, form caption, or API name alone does not prove runtime behavior. This file consolidates durable facts currently recovered; it is not a complete transcript archive.

## Latest XML protocol finding — 2026-11-14

Focused run 16 (`43573798242`, artifact `14105735885`) confirms the serialization getter: `TXMLEmwatType` interface slot `+0x54` thunk `0x0044B7A9` adjusts `Self` by `-0x50` and jumps to `0x0044B590`, an IAT thunk to `xmlrtl230.bpl!TXMLNode.GetXML`. The method node is set up using literal `method`; its `class` attribute is populated with the method name. Each parameter child stores dictionary key in `name` and dictionary value as node text. This proves the static method/parameter XML structure, but not the full document envelope or wire encoding. The constructor's additional constant at `0x0044C4FC` and helper `0x00401430` still need semantic identification.

## Constructor analysis checkpoint — run 17

Run 17 (`43574768657`, artifact `14106455607`) confirms `0x0044B4D8` is `xmlrtl230.bpl!TXMLNode.GetChildNodes`, used by `TXMLMethodType.AfterConstruction` before adding the `method` element. Constant `0x0044C4FC` is not a valid Delphi string. The subsequent call `0x00401430` jumps through IAT slot `0x0062EC40`; the imported symbol and meaning of its arguments remain unknown. Run 18 is resolving the import slot and dumping nearby bytes. Keep the XML envelope limited to proven `method`/`class` and parameter `name`/text until this is resolved.


## Constructor import lookup correction — run 19

Run 19 (`43575191082`, artifact `14106206890`) finds no import-descriptor entry for slot `0x0062EC40`, despite the slot residing in `.idata`; the on-disk DWORD is `0x00231274`. Treat the indirect jump as an unresolved external/relocated dispatch, not as a named imported routine. The constant at `0x0044C4FC` resembles the `TXMLMethodType` IID bytes but its use is not proven. Next, inspect `TXMLParamType.AfterConstruction` at `0x0044B4F8` (VMT `+0x0C`) to identify the parameter XML element tag. Preserve the existing confirmed mapping: method element + `class` attribute; parameter key in `name`, value in text; serializer getter calls `TXMLNode.GetXML`.
 

## Parameter element constructor probe — run 20

Run 20 (`43576636790`, artifact `14106479073`) corrected a bad VMT assumption: `0x0044B4F8` (`TXMLParamType` VMT `+0x0C`) is an import-style jump thunk via `0x006302B4` to the out-of-image address `0x0024060C`, not a TD32 procedure. Do not use it as `AfterConstruction` or infer the XML tag. The new `tools/find_td32_class_procedures.py` indexes TD32 decorated symbols by class name. Next: inspect its output for actual `TXMLParamType` procedures, trace the constructor candidate and its string references, then update the protocol docs only if the element tag is explicit.

## XML constructor comparison checkpoint — run 22

Run 22 (`43578292246`, artifact `14106852706`) completed successfully. It found a TD32 `TXMLParamType.AfterConstruction` procedure at `0x00614EC8` in the separate `WordRequestXML` module only. That constructor calls `0x0044B4D8` (`xmlrtl230.bpl!TXMLNode.GetChildNodes`) and then unresolved helper `0x00401430` with binary GUID-like constant `0x00614F2C`, not a text tag. The generic Invoke path's XmlResponse module has no own `TXMLParamType.AfterConstruction` symbol in the indexed procedures. The XmlResponse VMT parent pointers `0x00630314` and `0x0063030C` are outside the BPL image and have not been named.

Do not claim the parameter element tag is known. Do not copy the WordRequestXML constructor semantics into XmlResponse. The method/parameter field mapping and GetXML serializer remain statically confirmed; the complete envelope and wire bytes remain unknown.

**Resume here:** resolve the external parent VMT/class references or find the actual XmlResponse parameter initialization path; then prioritize tracing the parent-page message that triggers the close-time POST. Avoid repeating the already-completed TD32 symbol index. Keep image/scanner workflows in scope.

## Run 23 handoff — parameter insertion path

Run 23 (`43579138098`, artifact `14107224578`) succeeded. Important new detail: `XmlResponse.TXMLMethodType.Insert` (`0x0044C754`) calls child-node collection virtual slot `+0x20` with index `-1`, then interface-casts the result to `TXMLParamType`. No child tag string is supplied in that procedure. `TXMLParamType.Set_Name` follows the node's name/attribute interface path and does not reveal its element tag. The method constructor does pass literal `method` through child-node collection slot `+0x10`.

Do not guess the parameter element name. External parent VMTs (`0x0063030C`, `0x00630314`) and helper `0x00401430` remain unresolved. Resume by identifying the XML node-list virtual methods and external class metadata; then switch focus to the parent-page close-time POST/response behavior. Generic Invoke field mapping and GetXML serialization remain confirmed. Native Linux implementation is still not established by these analysis runs.

## Run 24 — XML node-list Add/Get_Param comparison

Run 24 (`43579618380`, artifact `14106929511`) completed successfully. The newly traced `XmlResponse.TXMLMethodType.Add` and the parallel `.EmwatMethods.TXMLMethodType.Add` bodies have the same dispatch pattern: obtain the wrapped node's child-node collection, then invoke its virtual slot `+0x10` with a string argument and an output interface. This is consistent with the method constructor's explicit `Add("method")` path. By contrast, `TXMLMethodType.Insert` invokes child-collection slot `+0x20` with index `-1`, without passing a tag string. This strengthens the conclusion that the parameter node tag is chosen inside the collection's Insert implementation or its underlying node-list class, not in `TXMLMethodType.Insert`.

The paired `XmlResponse` and `.EmwatMethods` `Get_Param` bodies are structurally identical: each calls `TXMLNode.SetAttribute` using the incoming string and a static attribute-name constant. The already decoded `XmlResponse` constant is `class`, consistent with the method-name attribute. The Add/Get_Param procedures have no direct immediate CALL xrefs in the TD32-bounded scan; their use is through interface/VMT dispatch.

**No new parameter element tag was identified.** Next, stop repeating the same class-level traces and resolve the child-node collection implementation / external parent VMT contract. In parallel, shift the main investigation toward the page-side `postMessage` sender and the close-time POST payload/response, because this is the remaining critical gap for the user's observed close-to-register workflow. Preserve the existing unknowns: exact parameter tag, complete XML envelope/wire bytes, and runtime close semantics.

## Next checkpoint — registered close callback trace (run 25 queued)

Historical note: the workflow extension after run 24 (commit b88451617f3500f8ec64e239902533b21ab82a4d) initially targeted 0x004CD154 as BeforeClose and 0x00430070 as a Close wrapper. Both labels were wrong. Run 25 corrected the symbol identity (0x004CD154 is BeforeSave; 0x00430070 is SaveAs2000), and run 26 traced the actual Close overloads and the separate TD32-named 0x004CCBBC helper. Do not reuse the original run-25 target labels.

Once this trace is read, continue toward the missing page-side sender/response contract. The parent web application's JavaScript is not currently included in the repository, so static BPL tracing can only narrow the Word/service side; runtime evidence from the user's HAR already proves that a POST occurs at close and returns an XML response, but the exact response payload semantics still need controlled comparison. Do not ask the user to repeat known close behavior.
 
## Correction — run 25 address/symbol verification (2026-11-14)

Run 25 (`43580008821`, artifact `14108665890`) exposed incorrect target labels in the preceding analysis step. The TD32 symbol at `0x004CD154` is `TWordViwer.WordAppDocumentBeforeSave`, not `WordAppDocumentBeforeClose`. The LoadDocument/OnTmrAutoSave registration code at `0x004B8C9C–0x004B8CCE` explicitly stores `0x004CD154` at callback field `+0x80`, `0x004CD54C` at `+0x90`, and `0x004CD9C0` at `+0x98`; the conditional callback at `+0x88` is `0x004D00AC` or `0x004CE030`. Thus `0x004CD154` is conclusively the registered BeforeSave callback. Do not call it a close callback.

The actual TD32 procedure named `TWordViwer.WordAppDocumentBeforeClose` begins at `0x004CCBBC`, but its only direct immediate caller found is `FillImgFldsForPrint` at `0x004CCF8F`; no registration reference was found in the scanned raw pointer data. Therefore its name alone does not prove that this procedure is the live Word application close-event handler.

A second address error: `0x00430070` is `TWordDocument.SaveAs2000`, not a Close wrapper. The actual `TWordDocument.Close` overload procedures are TD32-labeled at `0x0042FEB0`, `0x0042FF08`, `0x0042FF7C`, and `0x0042FFF4`; the latter is the three-argument overload. A three-argument Close invocation in the callback body dispatches through document interface VMT slot `+0x29C`, but the exact runtime target for that interface dispatch must be established by matching the interface VMT and wrapper semantics, not by assigning `0x00430070`.

Run 25 itself completed successfully, but its added trace commands targeted the wrong symbols for a close-event investigation. Treat its other outputs as useful only where the TD32 labels and address semantics are independently verified. Next analysis must trace the actual Close overload(s), find the genuine callback registration (if present), and distinguish the BeforeSave callback from document-close lifecycle. No claim about the page-side POST is changed by this correction.

## Run 26 — corrected Word Close overload trace queued

After correcting run 25's target-address mistake, the lifecycle workflow now explicitly classifies `0x004CD154` as the registered `WordAppDocumentBeforeSave` callback, identifies `0x004CB108` as `PreparePrintDocument`, and traces the actual `TWordDocument.Close` overloads at `0x0042FEB0`, `0x0042FF08`, `0x0042FF7C`, and `0x0042FFF4`. It also separately checks the TD32-named `WordAppDocumentBeforeClose` procedure at `0x004CCBBC` and its callsites. Workflow commit: `ed328c5c2876aad53ff6ee92054be87c7e6bedfe`.

The prior run's important correction is now recorded in the four protocol/lifecycle documents. Note that `0x004CCBBC` has only a direct call from `FillImgFldsForPrint` in the scanned TD32 callsite set, so the callback's symbolic name is not evidence that it is registered as a live Word event. The actual BeforeSave registration is explicit in `OnTmrAutoSave` at `0x004B8C9C–0x004B8CCE`. The next run must resolve the Close interface slot `+0x29C` and establish whether any separate close-event callback is registered elsewhere.


## Run 26 — corrected Word lifecycle findings (2026-11-14)

Run 26 (43584217243, artifact 14109926135) completed successfully; all 16 workflow steps passed. This section supersedes earlier callback-name interpretations in this handoff:

- 0x004CD154 is TD32-labeled TWordViwer.WordAppDocumentBeforeSave and is the callback registered at viewer field +0x80. It is not WordAppDocumentBeforeClose.
- The separate TD32-named TWordViwer.WordAppDocumentBeforeClose is 0x004CCBBC. Its only direct caller in the bounded scan is FillImgFldsForPrint at 0x004CCF8F; no raw-pointer registration reference was found. Its symbol name does not prove that it is the live Word close event.
- TWordDocument.Close overloads: no arguments at 0x0042FEB0 dispatches through interface slot +0x4D4; one OleVariant at 0x0042FF08, two at 0x0042FF7C, and three at 0x0042FFF4 dispatch through slot +0x29C.
- The registered BeforeSave callback at 0x004CD154 calls PreparePrintDocument (0x004CB108), checks _Document.Saved via slot +0xD8, and conditionally presents the changed-document prompt. Cancel sets the event Cancel word to 0xFFFF. Yes/No branches invoke the three-argument Close wrapper. This is BeforeSave handling, not proof of a separate BeforeClose event.
- 0x00430070 is TWordDocument.SaveAs2000, not Close.

The concrete runtime target behind slot +0x29C, any separate close-event registration, and browser-side close-time POST semantics remain unresolved. Do not overwrite the user's observed behavior that closing applies/registers changes regardless of Save; this static trace has not explained it. Next: resolve the COM interface behind +0x29C and trace the parent-page postMessage/localhost POST and response. Native Linux runtime implementation is not established by this analysis.


## Run 26 — Close overload and callback classification (2026-11-14)

Run 26 (`43584217243`, artifact `14109926135`) completed successfully; all 16 workflow steps passed. Confirmed findings:

- `TWordDocument.Close` no-argument overload at `0x0042FEB0` dispatches through the wrapped `_Document` interface slot `+0x4D4`.
- One-, two-, and three-argument overloads at `0x0042FF08`, `0x0042FF7C`, and `0x0042FFF4` dispatch through slot `+0x29C`.
- The three-argument wrapper loads its underlying interface via `0x0042ABA0`, then calls `[vtable+0x29C]`; this identifies the wrapper call slot, not the final implementation address.
- The registered callback at `0x004CD154` is `WordAppDocumentBeforeSave`; its body can invoke the three-argument Close overload after the Save-state prompt. Cancel writes `0xFFFF` to the event Cancel field.
- The separate TD32-named `WordAppDocumentBeforeClose` at `0x004CCBBC` has only the known direct caller in `FillImgFldsForPrint`; live event-registration status remains unproven.
- `0x00430070` remains correctly classified as `SaveAs2000`, not Close.

### Run 27 queued — controller close path and wrapper resolution

Workflow extension commit: `334b841dd279773345086e3e8903de068390c139`.

The next run adds a TD32 symbol inventory and traces the `CloseMyDoc` callsite at `0x005E9258`, its raw pointer references, `SilentSaveEmwatDoc` and callers, plus final cross-checks of the BeforeClose helper and BeforeSave callers. Do not treat the `CloseMyDoc` name or its `+0x2BC` dispatch as a proven document-close method until its receiver interface is typed. Do not equate `+0x29C` and `+0x4D4` without identifying the Word `_Document` typelib declarations.

The browser-side close POST remains the decisive missing contract. User runtime evidence shows a localhost POST when the document is closed and no equivalent request on Ctrl+S; static callback traces have not explained its trigger or response semantics. Native Linux runtime implementation is not established by these analysis runs.


## Run27 — close-path triage (2026-11-14)

- Run `43586456343` completed successfully; artifact `14110509457`.
- The newly traced `CloseMyDoc` at `0x005E9174` belongs to TD32 module `WordCompareCommandUnit`, not the main `TEditWordDocument` connector class. It invokes interface VMT slots `+0x13C` and `+0x2F0`, then slot `+0x2BC`; no direct raw pointer references to its callsite were found. Do not treat this method as the main letter close implementation without a caller/dispatch link.
- `SilentSaveEmwatDoc` at `0x004D23D8` is a substantial Wordviewer routine. It checks four controller-owned collections/objects at offsets `+0x8C/+0x94/+0x98/+0x9C`, allocates helper objects, invokes `0x004AEBBC`, sets a viewer flag at `+0x44C`, and calls helper `0x004D2948`. It is a stronger next analysis target than the unrelated `CloseMyDoc`, but its invocation timing and relation to HTTP response are not yet established.
- `uSendLog.TfrmShowAutoSaveFiles.WordAppDocumentBeforeClose` at `0x005EC580` belongs to the autosave-files UI and calls `CloseWordApp`; it is not evidence that the main editor registers this callback.
- Run27 did not establish the active Word close event or the close-time POST contract. User-observed close behavior remains the product requirement; static symbol names must not override it.
- Next focused trace: `0x004D2948` and callers/refs of `SilentSaveEmwatDoc`, plus `Emwat.Sys.CloseAllWords` only if its callers connect it to the main editor. Keep the main `TEditWordDocument → LoadDocument → HTTP response` path as the integration anchor.


## Run28 — reclassification of save/close candidates (2026-11-14)

- Run `43587704007` completed successfully; artifact `14110909233`.
- Critical correction: `0x004D2948` is TD32-labeled `TWrapRecord.LineCount` in module `ScanRequestXML`, procedure range `0x004D2948–0x004D2E77`. It is **not** a helper owned by `SilentSaveEmwatDoc`.
- `TWordViwer.SilentSaveEmwatDoc` at `0x004D23D8` has exact range `0x004D23D8–0x004D281B`. Its only direct bounded caller found is `TWordViwer.GetDocFieldName` at `0x004BBA86`. This places it on a field-name lookup/fallback path in the static call graph, not on a proven document-close callback. Its side effects and purpose remain to be determined.
- `Emwat.Sys.CloseAllWords` at `0x0044AD30` has one direct caller: `Emwat.Sys.DeleteTempRAW` at `0x0044B01C`. The routine builds four command strings and passes each to `0x0044B0F8`; current evidence associates it with temporary RAW cleanup, not the editor's user-close action.
- These three items are downgraded as candidates for the main letter-close path. Do not infer lifecycle from names alone.
- Main confirmed anchor remains `TEditWordDocument` slot `+0x10` → `0x005EE82C` → `TWordViwer.LoadDocument` `0x004B7724` → HTTP response writer. The user's observed close behavior remains a product requirement; the static path explaining it is unresolved.
- Next: trace the exact `GetDocFieldName → SilentSaveEmwatDoc` call context and the command targets under `DeleteTempRAW/CloseAllWords`; continue searching for the parent-page close POST and concrete response application path.


## Run 29 — field lookup and cleanup trace (2026-11-14)

Run 29 (`43589571290`, artifact `14111108881`) completed successfully. It adds the following corrections and scope limits:

- `TWordViwer.GetDocFieldName` (`0x004BB81C–0x004BC16F`) calls `SilentSaveEmwatDoc` (`0x004D23D8`) only on a conditional fallback branch: after obtaining a field-name value through interface slot `+0xAC`, it compares that value with a static string and calls SilentSave only when the comparison fails. This is a field-name resolution path, not evidence of a user-close callback.
- The helper addresses used by SilentSave were reclassified: `0x004AEA78` is `TfrmWordPrintOption.SetLetterReceivers`; `0x004AEBBC` is `TfrmWordPrintOption.FreePrinters`. They are print-options UI routines, not generic document-save helpers. The call context shows SilentSave interacts with print-option state; its wider side effects still need tracing.
- `Emwat.Sys.DeleteTempRAW` (`0x0044AE98–0x0044B053`) calls `Emwat.Sys.CloseAllWords` (`0x0044AD30`) at `0x0044B01C` only on a branch reached after its temporary-file/process checks.
- Although TD32 names the routine `CloseAllWords`, its four direct calls at `0x0044AD7E/0x0044ADA0/0x0044ADC2/0x0044ADF1` target `0x0044B0F8`, which TD32 identifies as `Emwat.Sys.GetFileVersion`. Thus the current static evidence does **not** establish that this routine closes Word processes; the symbol name must not be treated as behavioral proof. Its caller remains the RAW cleanup path, not the main editor connector.

**Run 29 conclusion:** no close-time POST trigger or final apply-on-close mechanism was identified. Preserve the user's close-applies-changes observation as a product requirement. The proven server-side `EditWordDocument → LoadDocument → HTTP WriteContent` path remains the anchor; the missing work is still the page-side message sender and the exact response/application lifecycle. Do not spend more runs on these unrelated print/cleanup symbols unless new caller evidence appears.


## User clarification — close is enough; underlying Word save is unresolved (2026-11-14)

The user repeated the real-world test and confirmed: they do not press Word's Save button, yet after closing Word the file is registered/visible in Almas Gam. Treat this as a firm end-to-end product requirement.

Do **not** infer that the document is never saved internally. A likely but unproven sequence is an automatic or EMWAT-triggered Word save during close, followed by EMWAT returning the final artifact/state in the HTTP response to the browser. Keep the following as separate investigation targets: (1) Word/COM save at close, (2) EMWAT artifact collection, (3) HTTP response delivery and Almas Gam persistence. User-facing/product wording: “closing Word is sufficient; the user need not press Save.”


## Next implementation milestone — Python loopback transport (2026-11-14)

A protocol-neutral transport implementation was added under `python/`:

- `src/emwat_linux/bridge.py`: loopback-only HTTP server, health endpoint, bounded opaque POST transport, exact configured Origin allowlist, no request-body logging, sanitized internal errors.
- `tests/test_bridge.py`: unit/integration tests using an ephemeral localhost port.
- `pyproject.toml`: minimal install metadata.
- `.github/workflows/python-bridge.yml`: independent CI workflow.

The `bridge.py` transport remains protocol-neutral and carries raw bytes to an injected handler. Protocol interpretation is now implemented separately in `protocol.py`, and `dispatcher.py` invokes only explicitly registered method handlers. The application factory in `application.py` wires these layers together.

**Immediate next actions:** use the latest Run #89 analysis artifact to refine the `wordBody` stream and temporary document path; recover the exact response/close lifecycle; then implement a real typed `EditWordDocument` handler. Do not register a placeholder as if it were production behavior, and do not claim end-to-end compatibility yet.


## Bridge transport milestone — CI green (2026-11-14)

- Workflow `Python bridge transport`, run `43592145701`, commit `c705ed34ad9a9e87b42d7e2d85d3aa60aea83815`: **success**.
- Seven tests cover loopback-only binding, health endpoint, opaque POST body/query preservation, exact Origin rejection and CORS echo, body-size rejection, unsupported route/method, and sanitized handler errors.
- CI uses `PYTHONPATH=src python -m unittest discover -s tests -v`; it intentionally does not require packaging/build dependencies for this stdlib-only transport.
- The earlier failing runs were corrected: missing setuptools in the runner was avoided, the test payload cap was aligned, and the module was placed under the actual `src/emwat_linux` package path.

Next: validate allowed Origin handling with a safe test page/origin, recover the exact XML parameter node and response envelope, then implement a typed dispatcher. Do not expose the listener to non-loopback interfaces or accept arbitrary origins.


## ادامه کار — parser پوسته XML

نمونه Response واقعی زمان بستن Word که قبلاً کاربر ثبت کرده بود، نام تگ پارامتر را مشخص می‌کند: `<emwat version="1.0"><method class="EditWordDocument"><param name="wordConfig">`. بنابراین برای همین مسیر، تگ `param` دیگر فرضیه نیست و شاهد runtime دارد.

فایل `python/src/emwat_linux/protocol.py` اضافه شد. parser فقط پوسته UTF-8 را می‌خواند، یک method و فرزندان `param` با نام یکتا را می‌پذیرد و متن مقدارها را بدون decode یا تغییر نگه می‌دارد. DTD/entity، XML خراب، نسخه نامعتبر، نام تکراری، markup تو در تو و payload بزرگ‌تر از سقف رد می‌شوند. تست‌ها در `python/tests/test_protocol.py` هستند.

در تحلیل ایستای سرویس، مسیرهای query با کلیدهای `invoke`، `init` و `heartbeat` نیز جداگانه دیده شده‌اند؛ اما پاسخ دقیق heartbeat و بایت‌های پاسخ init هنوز معلوم نیست و نباید پاسخ ساختگی تولید شود.

**وضعیت این گام تکمیل شده:** parser به dispatcher متصل شده و factory برنامه هر سه لایه را ترکیب می‌کند. گام بعدی، پیاده‌سازی handler واقعی `EditWordDocument` پس از روشن‌شدن payload نهایی و lifecycle بستن Word است؛ هنوز هیچ handler تولیدی برای این متد ثبت نشده است.


## Current implementation checkpoint — 2026-11-14 (CI run #20)

**Green:** Python bridge workflow run `43592721635` / commit `2fa217ae83f33b80a7799ede4c75f2cc58b40d76`; 24 tests passed.

Implementation now includes:
- `bridge.py`: IPv4 loopback-only HTTP server, Host-header validation, required exact Origin allowlist, CORS echo only for the exact allowed Origin, socket timeout, bounded request/response bodies, duplicate Content-Length rejection, no request-body logs and sanitized failures.
- `protocol.py`: UTF-8 parser for the runtime-confirmed `emwat → method → param` envelope; parameter values remain opaque.
- `dispatcher.py`: explicit method registry; no dynamic class imports; malformed input 400, unknown method 501, handler failures sanitized.
- Tests: `test_bridge.py`, `test_protocol.py`, `test_dispatcher.py`.

**Not implemented yet:** heartbeat/init response compatibility, a real `EditWordDocument` handler, Word/LibreOffice document editing, close-time response serialization and Almas Gam end-to-end persistence. The user's confirmed behavior—closing Word is enough for the document to appear in Almas Gam without manually pressing Save—remains the core acceptance criterion.

Next action: continue tracing the exact Word close-time response and the source of `wordBody`/final document payload; separately recover `?heartbeat` and `?init` contracts. Do not invent either response.


### Latest verified CI update (2026-11-14)

Python bridge workflow run #22, ID `43593083176`, commit `22a803912b0fa92c3bb5537fb1f0c7952fda7615`: **success**, 27 tests passed. New coverage and checks include Host header path/query/fragment rejection, duplicate Content-Length rejection, ASCII-decimal-only Content-Length parsing, and Transfer-Encoding rejection. No request body or response payload is logged.

A separate static-analysis workflow Run #89 is in progress, adding targeted traces for the Word body stream ingestion and temporary output handling path. Its conclusions are not yet available; do not treat that run as complete.


### Latest application integration checkpoint

`application.py` now exposes `create_bridge_server` to wire transport, parser and explicit dispatcher. Integration tests cover a full localhost POST through parser and a registered test handler, plus origin rejection. CI run #24 (`43593185429`) passed all 29 tests on commit `27986ee96b45009283cd96eecde95110e1b9e448`.

No real `EditWordDocument` handler is registered. The test handler is deliberately synthetic and proves only composition of the layers. The Word lifecycle analysis workflow Run #89 remains in progress; its new target traces include the `wordBody` stream ingestion and temporary output path.


### Latest verified implementation state — CI run #24

Python bridge transport workflow run #24 (`43593185429`), commit `27986ee96b45009283cd96eecde95110e1b9e448`, passed **29 tests**. The tested composition now includes `application.py` → `BridgeHTTPServer` → `XMLMethodDispatcher` → `parse_method_call` → an explicitly registered test handler → HTTP response. The test handler is synthetic; there is still no production `EditWordDocument` handler.

The separate Word lifecycle workflow Run #89 is still processing its deep trace steps. It now includes targeted analysis of `wordBody` stream ingestion, helper routines and temporary output handling. Do not report its findings until the artifact is available and inspected.


## Run 89 — LoadDocument input normalization (2026-11-14)

- Workflow run #89 (43592922191) completed successfully; artifact 14113237316 was inspected.
- Correction to the initial reading: 0x00457050 is TD32-labeled Emwatutils.Finalization in module EmailUtil, not a generic byte-stream helper. Its only direct caller in the scanned TD32 procedures is TWordViwer.LoadDocument at 0x004B778B; it compares the incoming UnicodeString against two global strings and can raise an exception. Exact semantic meaning of the two compared values remains pending string decoding.
- 0x00454B9C is TD32-labeled Emwatutils.euGetASFileName(UnicodeString, UnicodeString), also in EmailUtil. It is called by LoadDocument at 0x004B7796, but it is also used by TIFF/image routines (CreateTiff.SeparteImages, CreateImageFile, PrintWordDoc, and others). This strongly places it in filename/path normalization rather than a Word-only binary stream parser; exact output semantics remain to be verified.
- After those two calls, LoadDocument uses Delphi runtime/import thunks at 0x004012F8, 0x00401270, and 0x004012E0; these jump through the import table to external runtime addresses not mapped in the BPL. The code then constructs an object using global 0x0062F800 and constructor helper 0x004041BC, and calls its virtual slot +0x10 with the computed data pointer and length. The destination class and whether this represents a stream/file writer are not yet established.
- Do not describe wordBody as raw body bytes or a known file path yet. The parameter is handled as a Delphi UnicodeString, transformed by the filename helper, then a length/data pair is passed to an as-yet-unidentified object.
- Run #90 (43595049501) has been queued to decode LoadDocument string constants, inspect global 0x0062F800, trace constructor 0x004041BC, and expand the entry procedure.
