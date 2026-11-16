# EMWAT-Linux — Project Handoff

Last reviewed: 2026-11-16

This is the concise continuity entry point for future sessions. Detailed reverse-engineering evidence remains in the linked analysis documents.

## Latest verified implementation progress — 2026-11-16

- **Saved-slot correction:** generated Word wrappers map Get_Saved to _Document +0xD4 and Set_Saved to +0xD8. WordAppDocumentBeforeSave uses +0xD8, so do not describe that instruction as reading Saved; its assigned OleVariant value and prompt condition remain unresolved. OnControlerNotify uses +0xDC, mapped to TWordDocument.Get_Content (0x0042BDF8); the supplied -1 argument remains unexplained. The same handler logs AutoSave execution, builds .easd/.easz paths and calls euUnArchive, confirming a local archive/recovery path distinct from Almas registration.

- Real LibreOffice UNO adapter added: per-document process/profile/socket isolation; DOC/CFB and DOCX input detection; document modification/save/close listeners; close-time Word 97 snapshot.
- writer_properties.py adds a strict custom-property update operation: it requires an exact existing property name, does not create unknown properties, and never reads the current value. The real UNO fixture now imports an actual Word DOCPROPERTY field and matching custom property, updates the property, refreshes Writer fields, verifies the displayed document text changes, and then closes/exports.
- Real UNO integration workflow run 43810592239 passed 8/8 tests, including a generated DOCX opened and closed through LibreOffice, a bookmark inspected through UNO, and export as a legacy Word CFB file.
- Latest Python bridge run 43815578467 passed 98 tests with one optional UNO skip (99 total); LibreOffice UNO runs 43815561042 and 43815592590 both passed 8/8, including adapter-level custom-property batch update, DOCPROPERTY refresh, and DOC/CFB export. The separate LibreOffice UNO run 43813378877 passed 8/8 tests, including the existing-property update path and DOCX → Writer → DOC/CFB close/export.
- application.py now has create_libreoffice_bridge_server to compose EditWordDocument → service → office adapter. Cancellation response remains an injected policy because the Windows cancellation envelope is not yet known.
- word_fields.py decodes each field according to its own encryption attribute, exposes parsed single/twin identifiers, and includes extract_docproperty_identifier() matching native DOCPROPERTY token parsing (case-sensitive, first double-space, 255-character bound). The observed dagger delimiter is U+2020; this is identifier parsing only, not a template-field mapping. writer_inspector.py and LibreOfficeAdapter.inspect_document inventory Writer bookmarks, named ranges, sections, tables, frames, graphic objects, indexes, and text-field metadata without reading letter content. URL-encoded text and Base64 image values are decoded independently; plain text remains unchanged. External signData bindings remain opaque until separator/concater semantics are confirmed.
- The latest custom-property pipeline (run 43813303321, artifact 14201306994) confirms dictionary helper use in the FillImageField/FillPrintDocFields paths; ShowRecAndCcOptionForm is called from GetDocFieldName, and FindWindowExtd is reached from FillImageField. Its next revision is queued with additional traces for shared field lookup and XML-config population. Their full business semantics and the 180-field mapping remain unresolved.
- Not yet complete: mapping the 180 EMWAT fields into the real Writer template; signer/image insertion; applying permissions/settings; close-cancel behavior; and end-to-end registration with Almas Gam.
- Native SetFieldValue constants are confirmed: urlencoded and base64. FindFieldInActivefields recognizes DOCPROPERTY field codes; Hidden_Customizable conditionally enters SilentSaveEmwatDoc during GetDocFieldName. AddCustomDocPropertiesToDic enumerates Word CustomDocumentProperties and parses twin names. Native URL-decoder behavior is now matched: + becomes space and %2B becomes literal +. Next: trace the Base64 byte-to-Unicode helper at 0x004738CC, resolve the indirect/VMT call into AddXmlWordConfigFieldsToDic, and continue correlating DOCPROPERTY fields with Writer DocInfo.Custom fields. In parallel, continue the close/response chain and validate mappings against an anonymized real DOC/CFB fixture. Do not claim template compatibility until this passes.

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
- Run #90 is complete; its verified results and the Run #91 follow-up are recorded below.


## Run 89 supplement — DocFileName evidence

- The LoadDocument string constants include the exact error text `DocFileName can not be null.` at 0x004B8238. In the LoadDocument control flow, the transformed local string is checked for zero length immediately before this error path. This is strong evidence that the LoadDocument argument is being treated as a document filename, not simply as arbitrary document-body bytes.
- The same routine contains the strings `word-document`, `ConfigXML data loaded.`, and `Word Calling Mode: `, indicating logging/configuration activity around document loading. The strings `.doc` and `.docx` are present in the filename validation/normalization helper path. Their exact branch semantics are not yet established.
- Update the working interpretation: outer connector key `wordBody` is passed into LoadDocument, but inside LoadDocument it is validated/processed as a DocFileName-like UnicodeString. Do not assume the key name accurately describes its runtime value type.


## Run 90 — LoadDocument file-stream identification

- Run #90 (`43595049501`) completed successfully; artifact `14113854620`.
- The constructor helper at `0x004041BC` is definitively an IAT thunk to `rtl230.bpl!TFileStream.Create(UnicodeString, Word)`. Therefore the object created at `0x004B780B` is a file stream, not an unidentified memory stream.
- `LoadDocument` passes a filename-like string into that constructor, then invokes the stream object's virtual slot `+0x10` with a data pointer and a length obtained from the original `wordBody` argument. This is strong evidence that `wordBody` is used as file content/data at this point, while a separately derived local string supplies the destination filename. Do not yet claim whether the data is UTF-8, UTF-16, Base64-decoded, or another encoding; the exact length semantics and destination path are still open.
- The constructor mode argument is pushed as `0xFF00`; do not translate this to a named Delphi file mode until the calling convention and constant are checked against the exact RTL version.
- Run #90 decoded additional strings: `Word document file created.`, `word-document`, `ConfigXML data loaded.`, `Word Calling Mode: `, `image/tif`, `base64`, `Result word file content read successfully. try (%d)`, and error `DocFileName can not be null.`. These support a staged file-creation/configuration workflow, but do not independently establish the temporary folder or response schema.
- `0x00457050` is TD32-labeled `Emwatutils.Finalization` in module `EmailUtil`, and `0x00454B9C` is `Emwatutils.euGetASFileName`; treat these as string cleanup/name transformation helpers, not body parsers.
- The response write path remains the known `AResponseInfo.ContentText` → `TIdHTTPResponseInfo.WriteContent` path. Run #90 did not reveal the final close-time POST/apply contract.
- Immediate next work: trace the destination filename construction (`0x00401348`, `0x004012F8`, `0x00401270`, `0x004012E0`), inspect the second file-stream creation in `LoadDocument` around `0x004B7C39`, and correlate the file path/data with the final response XML.

- Additional Run #90 detail: a second object is constructed through the same `TFileStream` VMT/constructor path at `0x004B7C3E`, using the same derived filename and constructor mode argument `0`. Its code obtains stream size and calls virtual slot `+0x0C` with a buffer/count pair, consistent with reopening and reading the file. Treat the exact operation name as provisional until the RTL VMT slot is resolved.


## Run 91 — تأیید عملیات نوشتن/خواندن فایل در TFileStream

- Run #91 (43595953793) با موفقیت تمام شد؛ artifact 14114711446.
- import/VMT slot در 0x0062F800 به نماد کلاس rtl230.bpl!@System@Classes@TFileStream@ resolve شد و constructor در 0x004041BC به TFileStream.Create(UnicodeString, Word) تعلق دارد.
- در مسیر اول LoadDocument، مقدار mode برابر 0xFF00 است که در قرارداد TFileStream.Create معادل fmCreate است؛ سپس virtual slot +0x10 با pointer و count داده فراخوانی می‌شود. در layout استاندارد TStream این slot متد Write است. بنابراین فایل مقصد ایجاد و داده ورودی در آن نوشته می‌شود.
- در مسیر دوم، همان VMT/constructor با mode برابر صفر (fmOpenRead) استفاده می‌شود؛ سپس اندازه stream گرفته شده و virtual slot +0x0C با buffer و count فراخوانی می‌شود که در layout استاندارد TStream متد Read است. این تأیید می‌کند فایل تولیدشده دوباره باز و خوانده می‌شود.
- این دو مسیر شواهد مستقیم یک چرخه create/write سپس open-read/read را فراهم می‌کنند. مسیر واقعی فایل و مقصد نهایی داده خوانده‌شده هنوز مشخص نیست؛ بنابراین فعلاً نام آن را «فایل میانی» می‌گذاریم، نه الزاماً temp directory خاص.
- helperهای 0x00401270، 0x004012E0، 0x00401348 به slotهای .idata می‌پرند که در import descriptorهای قابل‌تحلیل پیدا نشدند؛ نام‌گذاری این helperها یا نسبت‌دادن قطعی آن‌ها به تبدیل encoding مجاز نیست.
- Run #91 هیچ قرارداد close-time POST یا response payload تازه‌ای پیدا نکرد. مرحله بعد: تحلیل ادامه LoadDocument پس از خواندن فایل، مشخص‌کردن مسیر فایل و اینکه بایت‌های خوانده‌شده چگونه به Word/فرمت TIFF و پاسخ HTTP منتقل می‌شوند.


## آخرین وضعیت مهندسی معکوس — Run 92

- GitHub Actions workflow run #92 با شناسه 43597403349 موفق شد؛ artifact دقیق 14114738491 بررسی شد.
- در `LoadDocument`، بعد از بازکردن مجدد فایل واسط و خواندن آن، تابع TD32 با نام `TWordViwer.OnTmrAutoSave` در آدرس 0x004B8A84 فراخوانی می‌شود (callsite: 0x004B7A58). این تابع نقطه شروع مهمی برای trace چرخه پس از بارگذاری Word است، اما هنوز نباید آن را callback بستن سند یا ارسال پاسخ HTTP فرض کرد.
- تابع `TWordViwer.AddCustomDocPropertiesToDic` در 0x004D1454 نیز در LoadDocument فراخوانی مستقیم دارد و به نظر می‌رسد properties سفارشی سند را به dictionary منتقل می‌کند.
- مسیر تصاویر: `CreateImageFile` در `EmwatDocPrintHandlerUnit` مجموعه ورودی‌ها را پردازش می‌کند و `PrintWordDoc` با `TFileStream(fmCreate)` داده را در فایل می‌نویسد. `CreateTIFF.SeparteImages` نیز در همان ماژول وجود دارد؛ caller مستقیم در اسکن فعلی پیدا نشد. این مسیرها هنوز به bridge اصلی یا HTTP response متصل نشده‌اند.
- هیچ close-time POST یا payload نهایی در Run 92 کشف نشد.
- گام بعدی بدون سؤال از کاربر: trace کامل `OnTmrAutoSave` و helperها/callerها، سپس event registration و مسیرهای Word COM Save/Close؛ هم‌زمان شناسایی dispatch غیرمستقیم برای TIFF/Print. پس از هر run، یافته‌ها و محدودیت استنتاج در همین handoff و اسناد پروتکل ثبت شوند.


## اجرای بعدی — Run 94 در حال اجرا

- Workflow توسعه‌یافته برای trace عمیق‌تر `OnTmrAutoSave` با commit نهایی `ea721080388e7d1903a6fb67af08abcf300c8f7c` ثبت شد.
- Run #93 به‌دلیل push اصلاحیه workflow لغو شد؛ Run #94 با شناسه 43598550321 روی نسخه اصلاح‌شده در حال اجراست.
- این run بدنه و ارجاعات `OnTmrAutoSave`، helperهای 0x004CDB54، 0x004C5D68، 0x004D68D4 و 0x004D531C، constructor مربوط به WordViewer و ارجاعات pointer مسیر TIFF/Image را جمع‌آوری می‌کند.
- پس از پایان Run #94، artifact را با شناسه واقعی از GitHub دریافت و بررسی کن؛ تا آن زمان هیچ نتیجه‌ای درباره Save/Close یا اتصال TIFF به bridge اعلام نشود.


## Run 94 — یافته‌های جدید و اصلاح برداشت از OnTmrAutoSave

- Run #94 با شناسه 43598550321 و artifact 14115756587 موفق بود.
- تابع `TWordViwer.OnTmrAutoSave` در 0x004B8A84 فقط یک نام نماد است؛ caller مستقیم مشاهده‌شده در TD32، `LoadDocument` در 0x004B7A58 است. بدنه در زمان LoadDocument اتصال OLE Word را برقرار می‌کند، حالت‌های view/readonly/protected را می‌خواند، چند callback را ثبت می‌کند و پیام `Init word engine finished.` را ثبت می‌کند. نباید آن را صرفاً عملیات ذخیره خودکار یا close handler دانست.
- callbackهای ثبت‌شده: 0x004CD154، 0x004CD54C، 0x004CD9C0 و بر اساس flag یکی از 0x004D00AC/0x004CE030. Run #95 برای trace بدنه و callerهای این handlerها ساخته شد.
- 0x004CDB54 = `TWordViwer.QuitWord`; 0x004C5D68 = `TWordViwer.SetDocCaption`. دو تابع 0x004D68D4 و 0x004D531C متدهای Remove دو Dictionary برای Custom Document Properties هستند و ارتباطی با AutoSave ندارند.
- Run #95: workflow run id 43599550286؛ commit fc4702dbd4c80ed73ac6bc5edac2b2f8d3a98654؛ وضعیت اولیه queued. پس از پایان، artifact را دریافت و handlerهای ثبت‌شده را بررسی کن.
- پرسش فنی اصلی همچنان: کدام event واقعی Word باعث ذخیره/جمع‌آوری سند و کدام مسیر داده را به HTTP response می‌سپارد؟ تا زمانی که handlerها و callerهایشان بررسی نشده‌اند، ادعای close-time POST نکن.


## Handoff — Run 95 completed (2026-11-14)

Run `43599550286` succeeded; artifact `14115498934` was downloaded and inspected.

### New evidence
- `0x004CD154` = `TWordViwer.WordAppDocumentBeforeSave` (not BeforeClose).
- `0x004CD54C` = `TWordViwer.WordAppNewDocument`.
- `0x004CD9C0` = `TWordViwer.WordAppWindowActivate`.
- `0x004CE030` = `TWordViwer.WordAppDocumentBeforePrintBGPrint`.
- `0x004D00AC` = `LoadOptions`.
- `OnTmrAutoSave` writes `0x004CD154` and `0x004CD54C` into callback-like object fields during LoadDocument. Treat this as evidence consistent with callback registration, not a complete proof of the COM event contract.
- Direct-call scans have zero direct CALL xrefs for these handlers; indirect COM/callback dispatch is not covered by those scans.
- The distinct `WordAppDocumentBeforeClose` procedure at `0x004CCBBC` has only one direct caller found, `FillImgFldsForPrint`; do not treat it as the main editor's active close handler.
- No close-time HTTP POST or final result payload was identified.

### Continue next
1. Trace the callback table/object construction and the indirect event dispatch that reaches `0x004CD154` / `0x004CD54C`.
2. Resolve interface VMT slot `+0x29C` used by `WordAppWindowActivate` and the document interface calls used by `WordAppNewDocument`.
3. Separate print/export/image handling from editor close/return behavior.
4. Keep the XML handler schema and close-result payload opaque until directly proven. Do not implement speculative production handlers.
5. Continue updating all three analysis documents after each meaningful run.


## Run 96 handoff — callback slots (2026-11-14)

Run `43600693760` succeeded; artifact `14116641628` inspected.

Callback/context pairs assigned in `TWordViwer.OnTmrAutoSave` to the Word object at `viewer + 0x44`:
- `+0x80/+0x84`: `0x004CD154` = `WordAppDocumentBeforeSave`
- `+0x90/+0x94`: `0x004CD54C` = `WordAppNewDocument`
- `+0x98/+0x9C`: `0x004CD9C0` = `WordAppWindowActivate`
- `+0x88/+0x8C`: conditional `0x004D00AC` (LoadOptions) or `0x004CE030` (BeforePrintBGPrint), based on `[viewer+0x3C]`; later assignment sites exist too.

Next: inspect the full tail of `OnTmrAutoSave`, determine the callback-record consumer/indirect dispatch ABI, and identify whether the close event is hooked through another Word event object. Do not implement a guessed close-time POST.

## آخرین پیشرفت مهندسی معکوس — 2026-11-14، Run 97

- GitHub Actions Run 97 موفق شد؛ artifact 14117102104 بررسی شد.
- 0x00404FBC برابر thunk به TOleServer.SetConnectKind در vcl230.bpl است؛ در راه‌اندازی OLE با آرگومان 1 استفاده می‌شود.
- 0x004013F8 = DynArrayClear، 0x00401398 = System.Pos، 0x00401368 = UStrCat. این‌ها helperهای RTL هستند و نباید به‌عنوان callback dispatcher تفسیر شوند.
- 0x004C5D68 دو property ناشناخته از OLE می‌خواند و در viewer+0x4C/+0x4D ذخیره می‌کند.
- 0x004CDB54 بررسی substring انجام می‌دهد؛ مقدار مورد جست‌وجو هنوز از نظر معنایی شناسایی نشده است.
- teardown مسیر OnTmrAutoSave در بعضی شاخه‌ها TWordApplication.Quit و چند فراخوانی VMT/interface دارد. معنای دقیق slotها هنوز باز است.
- WordAppDocumentBeforeClose در 0x004CCBBC هنوز فقط یک direct caller قطعی دارد: FillImgFldsForPrint. آن را handler قطعی close editor فرض نکن.
- هیچ close-time HTTP payload یا XML response در این run کشف نشد.
- Run 98 برای trace کردن 0x004BCA88 و slotهای teardown به workflow افزوده شد.

## اصلاح برداشت از Run 98 — 2026-11-14

- `0x004CDB54` نام TD32 آن `TWordViwer.QuitWord` است. propertyای از OLE را به رشته تبدیل می‌کند و literal ناشناختهٔ `0x004CDC14` را در آن جست‌وجو می‌کند. وجود literal نتیجه False و نبود آن True می‌دهد؛ caller در حالت True به شاخه‌ای با `TWordApplication.Quit` و interface calls می‌رود. متن literal هنوز decode نشده است.
- `0x004C5D68` نام نمادین `TWordViwer.SetDocCaption` دارد. بدنه دو property از OLE می‌خواند و در `viewer+0x4C/+0x4D` ذخیره می‌کند؛ نام و رفتار دقیق propertyها باز است.
- `0x004BCA88` در واقع `TWordViwer.GetXmlFieldInfo` است (procedure بزرگ 12,688 بایتی)، نه helper اختصاصی close. در `GetCaptionItemFont` و `WordAppDocumentBeforeClose` فراخوانی می‌شود.
- `WordAppDocumentBeforeClose` مقادیر field را از مجموعه‌های `+0xE8/+0xEC` پردازش می‌کند و سپس `GetXmlFieldInfo` را فراخوانی می‌کند؛ اما ثبت آن به‌عنوان رویداد عادی بستن سند هنوز اثبات نشده است.
- Run 99 برای decode literal شرط و بررسی interface tableها اضافه شده است.


## Run 101 — تفکیک شرط فعال‌سازی Office از چرخه بستن سند (2026-11-15)

- GitHub Actions workflow run #101 با شناسه `43680106253` روی commit `cdf542e4bd486a63d92a1b26c41a05f30028ae70` با موفقیت پایان یافت؛ artifact `14148322936` دریافت و بررسی شد.
- خطای Run 100 صرفاً از فراخوانی scanner بدون آرگومان selector لازم بود؛ workflow با selector صریح `*` اصلاح شد و Run 101 کامل شد.
- literal در `0x004CDC14` اکنون decode شده است: `Activation` (UTF-16LE). تابع `TWordViwer.QuitWord` در `0x004CDB54` این substring را در رشته‌ای که از property شیء OLE در `viewer+0x44` می‌خواند جست‌وجو می‌کند.
- اگر `Activation` پیدا شود، `QuitWord` مقدار False می‌دهد؛ اگر پیدا نشود، True می‌دهد. در caller یعنی `OnTmrAutoSave`، نتیجه True شاخه‌ای را فعال می‌کند که پیام `<Office LISENCE>: Word is not activated. Close Method.` را ثبت/نمایش می‌دهد و سپس `TWordApplication.Quit` را فراخوانی می‌کند. بنابراین این شاخه کنترل فعال‌سازی Office و خروج از Word است؛ مدرکی برای ذخیره سند یا ارسال آن به Almas Gam نیست.
- در resourceهای BPL، فرم `TEmSettingForm` شامل کنترل‌های `rbAutoSave`، `rbDontSave`، `chkDntAskForSave` و `cbbAutoSaveInterval` است. این‌ها وجود تنظیمات ذخیره خودکار/عدم ذخیره و فاصله زمانی را ثابت می‌کنند، اما به‌تنهایی نشان نمی‌دهند که کدام گزینه در نصب کاربر فعال بوده یا مسیر ثبت نهایی نامه چگونه عمل می‌کند.
- یک مسیر جدا در ماژول `uSendLog` شناسایی شد: `TfrmShowAutoSaveFiles.WordAppDocumentBeforeClose` در `0x005EC580`، تابع `CloseWordApp` در `0x005EBDA8` را فراخوانی می‌کند؛ caller دیگر `btnShowFileClick` است. نام کلاس، فرم `TfrmShowAutoSaveFiles` و callerهای مستقیم نشان می‌دهند این handler متعلق به پنجره نمایش فایل‌های AutoSave است، نه اینکه لزوماً handler اصلی ویرایش نامه باشد. بدنه CloseWordApp روی مجموعه‌ای از اشیای Word/Document loop می‌زند و متدهای interface را صدا می‌زند؛ معنای دقیق هر slot هنوز resolve نشده است.
- این مسیر جدا را نباید با `TWordViwer.WordAppDocumentBeforeClose` در `0x004CCBBC` یکی دانست. دومی همچنان فقط caller مستقیم شناخته‌شده `FillImgFldsForPrint` دارد.
- نتیجه منفی پابرجاست: Run 101 هیچ close-time POST تازه، payload نهایی، یا اتصال اثبات‌شده‌ای از `CloseWordApp` به پاسخ HTTP ارائه نکرد.
- گام بعد: trace بدنه `TEmSettingForm` و ذخیره/خواندن گزینه‌های AutoSave، resolve کردن interface slotهای `CloseWordApp`، و بررسی اینکه callbackهای ثبت‌شده در WordViewer چگونه به مسیر پاسخ نهایی `EditWordDocument` می‌رسند. تا آن زمان production handler یا close protocol حدس زده نشود.


## Run 102 — AutoSave settings and separate AutoSave viewer lifecycle

- GitHub Actions run #102 (43681595513, commit 168793fd5e2dfaeff6036894409e7a5385944d31) completed successfully; artifact 14148712060 was inspected.
- TEmSettingForm.chkDntAskForSaveClick at 0x005EAA20 opens the current-user registry hive (0x80000001, HKCU) and performs multiple registry value writes. The values include settings associated with controls at instance offsets +0x3E0, +0x3D8, +0x3C4, +0x3C8, +0x3CC, and the AutoSave interval control at +0x3F4. For interval values 1–5 it multiplies a lookup-table value by 1000; otherwise it writes 0x2710 (10000 ms). Registry value names and complete semantic mapping still require resolving the referenced string constants and registry helper APIs.
- The settings resource confirms controls rbAutoSave, rbDontSave, chkDntAskForSave, chkSaveIOxmls, and cbbAutoSaveInterval. This proves the UI exposes AutoSave-related options; it does not prove which options were selected in the user's session or how the main editor's final registration works.
- TEmSettingForm.FormCreate at 0x005EAD94 delegates to inherited form creation, then invokes helper 0x00402A50 and 0x0040496C; those helper semantics and the exact read-side settings mapping remain unresolved.
- The small btnOkClick handler at 0x005EAA14 calls TCustomForm.Close via thunk 0x00404E84; it does not itself show persistence logic. The checkbox click handler is the one containing registry operations.
- The separate TfrmShowAutoSaveFiles.FormClose at 0x005EBF20 is called from its own Delete/FormCreate/finalization paths. Its WordAppDocumentBeforeClose callback at 0x005EC580 calls CloseWordApp only when a document interface's first word equals 0x2E; this is tied to the AutoSave-files viewer, not proven to be the main Word editor's close event.
- CloseWordApp at 0x005EBDA8 iterates a Word Documents collection, conditionally inspects/updates document items, and invokes interface slot +0x29C; exact COM method semantics remain unresolved. It does not establish an HTTP POST or final registration payload.
- No evidence in Run 102 links these registry settings or the AutoSave viewer teardown to the main editor's final Almas Gam registration request. Keep that protocol unknown until a concrete caller/payload/response chain is found.
- Next target: resolve registry helper APIs and string constants to map each setting key/value; separately resolve the +0x29C Word interface slot and identify actual event registration/dispatch for the main viewer's BeforeClose callback. Continue tracing the main editor's save/close-to-HTTP response path without conflating it with the AutoSave viewer.


## Run 103 — registry settings and Word lifecycle follow-up (2026-11-15)

- GitHub Actions run #103 (run ID `43682606812`, commit `b0f92c0f3298b1d92b41906691e84960f75f6ee7`) completed successfully: 36/36 steps; artifact `14149148019` (`emwat-word-lifecycle-analysis`).
- The settings handler `TEmSettingForm.chkDntAskForSaveClick` at `0x005EAA20` confirms a current-user registry flow: it creates/uses a registry object, selects root `HKEY_CURRENT_USER` (`0x80000001`), opens `Software\\Emwat\\Dynamic Config`, writes integer and Boolean values, then releases the registry object. The IAT/thunk map identifies `0x00404414` as `TRegistry.WriteInteger(UnicodeString, Integer)` and `0x00404424` as `TRegistry.WriteBool(UnicodeString, Boolean)`.
- Confirmed value names extracted from the Delphi UTF-16 string headers: `Logging Level`, `Save I/O Trace Files`, `Background Priniting` (original spelling), `Dont Ask Save On Print`, `Save Before Print`, and `AutoSaveInterval`.
- Handler mapping from the observed writes: component/object offsets `+0x3E0` → integer `Logging Level`; `+0x3D8` → Boolean `Save I/O Trace Files`; `+0x3C4` → Boolean `Background Priniting`; `+0x3C8` → Boolean `Dont Ask Save On Print`; `+0x3CC` → Boolean `Save Before Print`; `+0x3F4` → integer `AutoSaveInterval`. For interval selection values 1–5, the selected lookup-table value is multiplied by 1000 before writing; other values write 10000 ms. This is the save-side mapping; don't assume startup reads use the same helper path until found.
- Corrected a prior lead: `TEmSettingForm.FormCreate` at `0x005EAD94` calls `0x00402A50` (`user32!GetDesktopWindow`) and `0x0040496C` (`TWinControl.SetParentWindow`), not registry-read routines. Its short body does not load the persisted settings. The exact settings-load path remains unresolved.
- The `BeforeSave` callback body still performs a prompt and may dispatch the 3-argument Word `Close` overload through interface slot `+0x29C`; direct CALL xref scans do not resolve its callback wiring because the stored function pointer is assigned as data in `OnTmrAutoSave`. This is evidence of callback pointer storage, not yet proof of the COM event-sink ABI or final server registration.
- All four `TWordDocument.Close` overload wrappers were traced. The no-argument overload dispatches slot `+0x4D4`; overloads with one, two, or three optional arguments dispatch slot `+0x29C`. TD32 direct-call scans show no direct CALL xrefs for these wrappers; raw pointer matches occur in debug metadata, so do not infer which overload is used by the main editor solely from those scans.
- No verified close-time HTTP POST, response payload, or final Almas Gam registration operation was found. The user's observed behavior (closing Word without manually pressing Save still registers the document) remains an important runtime fact to reconcile, not a protocol proven by this static trace.
- Next targets: locate the *read-side* registry operations for `Dynamic Config` and the actual settings form initialization; trace callback record consumption / COM connection-point wiring around `OnTmrAutoSave`; identify real main-editor close and final local HTTP request/response chain. Keep the AutoSave files viewer's separate close handler isolated from the main editor.


## Handoff — after Run 104 (2026-11-15)

Run #104 (`43683614577`) completed successfully (37/37); artifact `14150300042`.

Important new validation notes:
- Registry-related imports exist (Win32 `RegOpenKeyExW`/`RegQueryValueExW` and Delphi `TRegistry` read/write APIs), but the first scanner only searched direct calls to executable thunks and found zero sites. This does not prove absence of registry reads.
- The first post-read code range `0x004B7CFA–0x004B809D` decoded zero instructions because it starts in non-code data. The observed valid continuation is `0x004B7DE1`.
- Commits `743e6378` and `a4027a70` add IAT-indirect CALL/JMP and pointer-reference scanning and correct the post-read range. Check the latest workflow run/artifact before drawing conclusions.

Do not claim the registry startup read path, main-editor close event sink, close-time HTTP request, or final Almas Gam registration payload has been resolved. Continue with the latest workflow output.

## Winux/Wine live validation checkpoint — 2026-11-15

The detailed evidence is recorded in [WINUX-RUNTIME-VALIDATION.md](WINUX-RUNTIME-VALIDATION.md). This checkpoint separates observed behavior from assumptions:

- **User-observed / runtime-confirmed:** the Windows installer was run through Winux Engine in the managed `emwat` prefix; Winux recorded installer status `SUCCESS` (verification remained `PENDING`). This is installation success, not proof of full application compatibility.
- **Runtime-confirmed:** `EmwatService.exe` and `EmwatAgent.exe` were present as running Wine processes under the normal desktop user, not root. Their logs report Service startup/listening on port 1984 and Agent startup. Winux's own process/service listings did not track these processes.
- **Runtime-confirmed:** `127.0.0.1:1984` was listening. A plain GET to `http://127.0.0.1:1984/` returned `HTTP/1.1 200 OK`, `Content-Length: 0`, and an `IDHTTPSESSIONID` cookie header. The socket was attributed by `ss` to `wineserver`, not directly to either Windows executable.
- **Strict interpretation:** this GET proves only that the loopback HTTP listener answered at that time. It does not validate `?heartbeat`, `?init`, POST dispatch, browser messaging, XML method handling, Word document round-trip, or Almas Gam registration.
- **Runtime-confirmed:** host CUPS scheduler was running but `lpstat -t` reported no destinations/queues. GAM-related files `winzvprt5.sys`, `zvprt5.ini`, and `spool/drivers/x64/zvprt1.gpd` were present in the Wine prefix. This proves file presence only—not Windows spooler registration, printer enumeration, or successful printing.
- **Unknown:** whether the GAM virtual printer can function under Wine, whether it can be replaced by a Linux/CUPS implementation, and what exact print data/protocol it consumes. Do not infer failure solely from the absent CUPS queue or infer success from the installed driver files.
- **Next runtime probe:** inspect the results of GET/HEAD/OPTIONS/POST against the root endpoint and the service/agent binaries/configuration for endpoint clues. Do not send fabricated XML to production method handlers. Continue with a harmless test letter and sanitized browser Network metadata before attempting the real Almas Gam workflow.

This Wine runtime experiment is a reverse-engineering aid only. The product target remains a native Linux implementation; do not make Wine or Windows kernel printer drivers dependencies of the final architecture.

## Winux HTTP method and binary-string checkpoint — 2026-11-15

New runtime evidence and executable-string findings are recorded in:
- [WINUX-RUNTIME-VALIDATION.md](WINUX-RUNTIME-VALIDATION.md)
- [HTTP-LOCAL-API-ANALYSIS.md](HTTP-LOCAL-API-ANALYSIS.md)

Key facts:
- GET, HEAD, OPTIONS and POST to only `http://127.0.0.1:1984/` each returned `200 OK` with an empty body. GET/HEAD/POST showed an `IDHTTPSESSIONID` cookie header; OPTIONS did not in the captured output.
- These root-path probes used no valid EMWAT application request. They do **not** establish CORS support, XML parsing, POST dispatch, heartbeat/init behavior, or document workflow success.
- `EmwatService.exe` contains Indy HTTP server/session symbols, `IDHTTPSESSIONID`, HTTP method-override strings, a port-1984 bind-failure message, and a service termination marker `{2EC42BF4-EA08-4476-AB86-466763F80E9A}_TERMINATE_EM_SERVICE_`.
- `EmwatAgent.exe` contains localhost/127.0.0.1 strings, Word connection/open-document/sign-insertion error messages, and `TLoginCredentialService` RTTI/symbol strings. These are static string/RTTI observations, not proof those code paths executed in the current session.
- No matching Emwat-named config files with the searched extensions were found in the searched ProgramData/AppData locations; this is not proof that no configuration exists elsewhere.

**Resume:** inspect `?heartbeat` and `?init` safely; identify root handler/session creation; trace Agent heartbeat and Word automation failure/success paths; then capture sanitized metadata for a real browser-originated request. Do not send fabricated payloads to real application methods. Do not treat generic empty 200 responses as API compatibility.


## Cross-project Winux update — 2026-11-15

Reviewed the latest Winux Engine development context and recorded the transferable findings in [WINUX-RUNTIME-VALIDATION.md](WINUX-RUNTIME-VALIDATION.md). Reusable patterns include the ServiceBackend contract and injected systemd-user backend, separation of ServiceManager from ProcessManager, read-only diagnostics, symlink-safe prefix/path handling, and explicit x86/x64 WoW64 detection. The latest Winux working-tree context reports 216 passing tests, but the public Winux GitHub docs may lag those local changes.

Use these capabilities only as optional Wine-test infrastructure and as design patterns. Do not make Winux or Wine a dependency of EMWAT-Linux's native product architecture. In particular, do not equate a Winux-managed Linux user service with Windows Service Control Manager support, and do not assume the already-observed EMWAT Wine processes are tracked by Winux until verified.


## Run 113 — startup registry read located (2026-11-15)

Workflow #113 succeeded (run ID `43688755518`, artifact `14151906706`). The earlier “startup settings-read path unresolved” note is superseded: the main `TWordViwer` constructor at `0x004D0D24–0x004D0FE6` opens `HKCU\\Software\\Emwat\\Dynamic Config` and reads four values:
- `Background Priniting` → Boolean field `+0x3C`, default true.
- `Dont Ask Save On Print` → Boolean field `+0x3D`, default true.
- `Save Before Print` → Boolean field `+0x3E`, default false.
- `AutoSaveInterval` → integer field `+0x88`, default 0 and minimum 10000 ms.

Reads are guarded by `ValueExists`; values are loaded with `ReadBool` / `ReadInteger`. `Logging Level` and `Save I/O Trace Files` are not handled in this constructor. Do not infer timer/save semantics solely from the interval field.

**Still unresolved:** main-editor close callback semantics, close-time HTTP request/response, and final Almas Gam registration payload. Preserve the user's observed fact that closing Word without pressing Save registers the document; static analysis has not yet explained the mechanism.


## Registry follow-up — Runs 116–117 (2026-11-15)

Runs #116 (`43699248792`) and #117 (`43703253785`) succeeded (37/37 and 38/38 steps). The new artifact identifies `TETracer.GetUniquePostfix` as a registry **write** path: create `TRegistry` (`0x00467C99`), set root to HKCU (`0x00467CB7`), call `WriteBool` (`0x00467D63`) and `WriteInteger` (`0x00467D75`). The value-name strings at `0x00467F2C` and `0x00467F64` are not yet decoded. The `0x00466D16` hit is only a raw pointer reference; its surrounding bounded trace is incomplete. Do not claim that either path reads `Logging Level` or `Save I/O Trace Files`.

**Resume target:** extract complete procedure boundaries/disassembly for `TETracer.GetUniquePostfix` and decode the two string arguments, then locate actual `ReadBool` / `ReadInteger` consumers for the remaining settings. Do not disturb the established Run 113 read-side mapping. The main Word close-to-Almas registration chain remains unproven.


## Handoff — parallel reverse-engineering checkpoint (2026-11-15)

Continue autonomously; no user input is required for the current static-analysis work.

### Latest workflow results

- Word lifecycle #121: run 43707049641, successful; artifact 14158949168.
- Word request lifecycle #3: run 43709706063, successful 13/13; artifact 14159833681.
- Registry settings #4: run 43709607471, successful; artifact 14159692702.
- Filename/temp cleanup #7: run 43709510495, successful; artifact 14160380463.
- Python bridge #42: run 43709846976, successful; 45 tests.

### Critical findings to preserve

- Main Word callback record installs 0x004CD154 at +0x80. Its TD32 symbol is WordAppDocumentBeforeSave, but its log strings say OnBeforeClose. It displays the custom Persian register-changes prompt and calls Document.Close through interface slot +0x29C on non-cancel paths. The exact COM event-slot name remains unproven.
- The separate routine 0x004CCBBC (symbolized WordAppDocumentBeforeClose) is not the pointer installed in the main event record.
- Dynamic Config reads are now mapped: Background Priniting, Dont Ask Save On Print, Save Before Print, AutoSaveInterval, Logging Level, Save I/O Trace Files. TETracer's Created IO Trace Count is a 15-count trace quota.
- Image/print settings use HKCU\SOFTWARE\Emwat\PrintParams with mLeft/mTop/mRight/mBottom, Posotion, Size, PrintRange.
- Exported CloseAllWords (0x0044AE98) enumerates Word windows and may execute taskkill.exe /f /im WINWORD.EXE; it then calls exported RemoveTempFiles (0x0044AD30), which uses DeleteTempRAW (0x0044B0F8) to remove temp-file masks. Exported GetFileVersion is at 0x0044B2DC. The external service caller is unknown; do not equate this cleanup API with the user's main-editor close action.
- Packet-level timing confirms one long-lived EditWordDocument request: body complete at 0.002154 s, first response byte at 54.560037 s, gap 54.557883 s; the response transfers in about 1.362 ms. The returned DOC is rewritten: input 872,960 bytes; estimated complete response 875,008 bytes (+2,048); OLE first-directory-sector pointer 1698 → 1702 at offset 48. The exact Word/COM release event is still unresolved.
- LoadDocument writes wordBody bytes directly to a temporary stream. Base64Decode at 0x004B7E44 uses [ebp-8], not the wordBody argument. Do not claim this call decodes wordBody.
- The successful LoadDocument path writes AResponseInfo.ContentText and calls WriteContent. Exact timing relative to Word close remains unresolved.

### Python bridge

- Heartbeat returns captured TickTack.
- Init route returns the 994-byte capture-matched script with dynamic local port and allowlisted parent origin.
- response-word success serializer is implemented.
- allowed_origins is for the local XHR Origin; allowed_parent_origins is for the Almas page Referer.
- Python CI is green with 45 tests. There is still no production EditWordDocument handler or LibreOffice integration.

### Next autonomous work

1. Continue the request-lifecycle workflow around LoadDocument helper calls and event-sink slot mapping.
2. Resolve the DeleteTempRAW caller through unit initialization/finalization tables or indirect references.
3. Finish image/print registry value mapping and temp cleanup helper semantics.
4. Keep all conclusions evidence-tagged: the long-lived XHR is confirmed, but the exact Word close callback that releases it and the parent page's final Almas POST still need proof.
5. Translate only confirmed contracts into the native Linux bridge and LibreOffice integration.


### Request/response DOC evidence

Pcap workflow #4 (run 43710628491, artifact 14159604189) confirms the returned application/msword document differs from wordBody. Input size is 872,960 bytes; the response capture decodes to 874,957 bytes with 68 Base64 characters missing (51 decoded bytes), giving an estimated complete size of 875,008 bytes (+2,048). The OLE header's first-directory-sector pointer changes from 1698 to 1702 at offset 48. Full-file equality is not authoritative because the response capture is incomplete.


### Dispatch address clarification — 2026-11-15

Use this exact naming in future traces: public/exported TEmwatMethod.Invoke = 0x0046C9E0 (VMT slot +0x0C); inner dictionary/XML helper = 0x0046C82C (433 bytes; TD32 symbol says Invoke). The wrapper calls the helper at 0x0046CA67, then the subclass PerformMethod at VMT slot +0x10 / callsite 0x0046CA88. Do not describe 0x0046C82C as the public service dispatch entry.


## Latest verified continuation — 2026-11-15

- The captured `EditWordDocument` exchange now has a dedicated gap-aware report at `docs/PCAP-EDITWORD-DOCUMENT-ROUNDTRIP.md`. The response is a successful `response-word` envelope containing Base64 `application/msword` data. It differs from the submitted DOC in the intact prefix, but 17 TCP sequence gaps (68 bytes) prevent a full-file comparison.
- The native protocol module includes a bounded `serialize_word_document_response` helper and synthetic tests. This is not yet wired to a production `EditWordDocument` handler or LibreOffice.
- Latest verified CI snapshots: Python bridge run #42, 45 tests passed; native core run #104, normal tests 4/4 and sanitizer tests 4/4.
- A separate `.github/workflows/analyze-recovery-store.yml` workflow is being executed to trace every `TfrmShowAutoSaveFiles` / `TfrmSendLog` procedure, callers, callback references, resources, and recovery-related embedded strings. Treat results as pending until run #2 artifact is checked.
- Existing analysis branches remain independent: request parameters, PCAP timing, registry settings, Word event sink, wait/COM, filename normalization, Word lifecycle, native core, and Python bridge.


## Recovery branch update — 2026-11-15

- Recovery form workflow run #2 (`43715017039`) completed successfully; artifact `14162835454`.
- The form is `TfrmShowAutoSaveFiles` in module `uSendLog`; its separate Word Automation lifecycle is not the main editor's `TWordViwer` lifecycle.
- Recovered literals: `*.easz` at `0x005EC49C` is passed from `lslFilesDblClick` to helper `0x004043BC`; `.easd` at `0x005EBD3C` is used in string construction inside `Delete`. Their exact roles remain under analysis.
- Autosave helpers identified: `euGetAutoSavePass` (`0x00456B78`), `DoClearOldAutoSaveFiles` (`0x00456C0C`), `euClearOldAutoSaveFiles` (`0x00456C98`), and path/temp helpers under `Emwat.Sys`. The path/helper workflow run #2 (`43715620696`) is in progress; do not treat its results as final yet.
- See `docs/RECOVERY-STORE-ANALYSIS.md` for confirmed evidence and unresolved items.


## Recovery path workflow run #2 — verified

- `analyze-recovery-paths.yml` run #2 (`43715620696`) succeeded; artifact `14162601983`.
- `0x004043BC` is `TDirectory.GetFiles`; the UI and old-AutoSave cleanup both enumerate `*.easz`.
- `0x004026B4` is `DeleteFileW`; the cleanup loop passes aged matching file paths to this API.
- Local AppData helper uses `SHGetSpecialFolderLocation(CSIDL 0x1C)` and `SHGetPathFromIDListW`. Exact `.easz` root still unknown.
- `euClearOldAutoSaveFiles` compares an age result with `0x18`; do not call it 24 days until the age helper confirms Delphi `TDateTime` units.
- Run #3 (`43715933101`) extends traces for the age, password-read, path-construction, and process-cleanup helpers.


## New confirmed recovery and request-schema findings — 2026-11-15

- Recovery path workflow run #4 (`43716283296`) confirms `euGetWinTempPath` calls `kernel32!GetTempPathW` (`0x004027F8`); `euGetTempFileName` appends `temp-emwatASwf\\`. The AutoSave store is `%TEMP%\\temp-emwatASwf\\*.easz`.
- Recovery password helper `euGetAutoSavePass` calls `GetUserNameW`; it returns the Windows account name, with fallback `@25*gamsign*25@` if the API fails.
- Cleanup age is explicitly measured with `HoursBetween(Now, FileDateToDateTime(FileAge(path)))`; threshold is 24 hours, then `DeleteFileW`.
- Recovery `Delete` handler passes selected item path and temp root to `euResetMemory`, then constructs an additional path with `.easd`; exact file transformation is pending. Run #5 (`43716527945`) traces `euResetMemory` internals and object pointers.
- Added `docs/EDITWORD-REQUEST-SCHEMA.md`: one captured request has a Base64 XML `wordConfig` with 180 fields (including 20 repeated signer slots across seven field families) and a Base64 legacy DOC/OLE `wordBody`. Sensitive field values were not copied.
- Word event-sink workflow run #8 (`43716384031`) fixes an event-callback extraction regex that previously failed to match the actual table pointer format; callback target tracing is now running.


## Native protocol implementation update — 2026-11-15

- Added `python/src/emwat_linux/word_config.py` to parse the inner Base64-encoded `word-document` XML separately from the outer EMWAT method envelope.
- Parser preserves field order, duplicate IDs, per-field attributes, opaque field text, settings, permission strings, optional-attribute content, and requested MIME types. It rejects invalid Base64, non-UTF-8, DTD/entities, oversized input, and malformed field structures.
- New tests cover the captured shape without including customer letter values.
- Python bridge CI run #44 (`43716641854`) passed **53 tests**. The preceding intermediate commit run #43 also passed 45 tests.
- This parser is not yet connected to a production EditWordDocument handler or LibreOffice adapter.


## Event table interpretation correction — 2026-11-15

The 20 addresses extracted from `0x00627B74` are not Word event callback pointers. Run #9 (`43716905570`, artifact `14162568118`) decoded them as server error strings (`Err_20000`, `Request XML is invalid.`, `Can not open document.`, `Temp path not Found.`, etc.). The earlier callback-table interpretation is retracted. Workflow run #10 now extracts this as an error map. The main viewer's `BeforeSave` registration at `0x004CD154` remains confirmed independently from `OnTmrAutoSave`.


## Recovery archive password correction — 2026-11-15

Do not treat the Windows username or `@25*gamsign*25@` as the confirmed `.easz` archive password. `euGetAutoSavePass` returns the account name (or fallback) and `DoClearOldAutoSaveFiles` concatenates it with `@25*gamsign*25@`, but the exact archive consumer is unresolved. The recovery `Delete` path constructs a `Sevenzip.T7zInArchive` object; `euResetMemory` passes `mW@Tlogs43end_+` to virtual slot `+0x44` when its optional password string is null. The exact slot/property mapping and archive open/extract sequence remain pending. See `docs/RECOVERY-STORE-ANALYSIS.md`.

## EditWordDocument request adapter — 2026-11-15

- Added `python/src/emwat_linux/editword_request.py` with `parse_editword_request(MethodCall)`: validates the method name and required parameters, parses Base64 `wordConfig`, decodes Base64 `wordBody` to opaque document bytes, preserves `signData` text and extra parameters, and enforces size limits.
- It deliberately does not assume `signData` is one Base64 blob; the inner config declares concatenation and per-field encoding.
- Python bridge CI run #46 (`43717259882`) passed **58 tests**. This adapter is not yet wired into a production method handler or office engine.

## Word error map — 2026-11-15

- Event/error workflow run #11 (`43717625474`), artifact `14162998865`, decoded the full pointer list in the server metadata block. It contains `Err_20001` XML-invalid, `Err_20002` empty document, `Err_20003` Word connection, `Err_20004` document open, `Err_20005` signature insertion, `Err_20006` missing twin field, `Err_20007` temp path, `Err_20008` scan failure, `Err_Ignore` user cancellation, `Err_20010` image load, `Err_20016` Excel connection, `Err_20017` workbook open, and `Err_20018` missing user-local folder.
- The same block includes log-level labels and Persian AutoSave interval labels. See `docs/WORD-ERROR-MAP.md`.
- Important: this is a string/error map, not a Word COM callback table. The live BeforeSave registration remains separately confirmed at `0x004CD154`.

## Recovery / AutoSave findings — 2026-11-15

The recovery subsystem now has a dedicated analysis report: `docs/RECOVERY-STORE-ANALYSIS.md`. Two additional recovery-path runs (#9 and #10; artifacts `14163436366` and `14163367757`) traced the SevenZip reader class. `euResetMemory` (`0x00456F00`) calls a helper named `CreateOutArchive` and passes the fallback password `mW@Tlogs43end_+` through virtual/interface slot `+0x44`. The call sequence strongly aligns with `T7zInArchive.SetPassword` → `OpenFile` → `ExtractTo`, but the slot-to-method mapping remains unproven. `T7zInArchive.SetPassword` (`0x00453860`) stores the string at `+0x58` and invokes an extraction-style interface call with a callback-like helper. The username / `@25*gamsign*25@` value returned by `euGetAutoSavePass` belongs to a separate cleanup/logging path and is not established as the recovery archive password.

The reader exposes archive open, item-query and extraction methods. Do not yet name the `euResetMemory` path arguments as a proven OpenFile/ExtractTo pair: VMT slots `+0x0C` and `+0x3C` still need exact mapping. The `.easd` file's content and lifecycle, the SevenZip archive variant, and the writer-side `.easz` creation settings remain unresolved. Continue from `docs/RECOVERY-STORE-ANALYSIS.md`; do not repeat the completed class-method trace.


## Latest continuity checkpoint — 2026-11-15

### Verified since the previous handoff

- Python bridge CI run `43721449170` succeeded with **69 tests**. The close-driven coordinator and EditWordDocument domain-service tests cover close without explicit Save, separate modification/save callbacks, cancellation, sanitized adapter failures, and rejection of non-byte output.
- New engine-neutral files: `office_adapter.py`, `document_coordinator.py`, and `editword_service.py`. They model request normalization → open → track modifications and engine saves independently → wait for user close → export final bytes. They are not a LibreOffice implementation. `editword_handler.py` now adapts the service to the XML dispatcher and uses the observed success serializer, but the factory is not yet registered in the application.
- `EditWordDocument` request normalization exists, including Base64 document decoding and conservative preservation of signData as opaque text.
- Heartbeat response and init-script generation are implemented against the captured exchange; production allowlists must still be configured.
- Recovery analysis identifies `T7zInArchive` as the reader wrapper relevant to recovery. Its SetPassword implementation at `0x00453860` stores the supplied Unicode password at instance offset `+0x58` and invokes an extraction-style interface call with a callback-like helper. `euResetMemory` supplies `mW@Tlogs43end_+` to virtual/interface slot `+0x44` when its optional password is absent and the flag selects the fallback. The likely SetPassword → OpenFile → ExtractTo mapping remains unproven. Do not substitute the Windows username or `@25*gamsign*25@`, which belong to a separate cleanup/logging path.
- The reader exposes archive open, item metadata and extraction methods. Exact standard archive format, euResetMemory path-slot VMT mapping, .easd contents, and writer password callback remain unresolved. `T7zOutArchive.SetPassword` is a no-op stub; writer callback tracing is a separate task.
- Word error strings were decoded and documented separately from the unresolved COM event dispatch map. Do not interpret the error string table as event callback metadata.

### Active parallel jobs at handoff

- Recovery SevenZip plugin-focused workflow: run `43719323732`, completed successfully, artifact `14164146310` inspected.
- Recovery path/helper workflow: run `43719180035`, still in progress at the SevenZip reader/writer trace step.

Inspect their status and artifacts before starting duplicate work. If a job is still active, continue the independent native implementation track rather than waiting idle.

### Immediate next actions

1. Inspect the two active recovery artifacts; focus on T7zPlugin construction, VMT dispatch mapping, archive writer password callback, and the euResetMemory call chain.
2. Keep the native OfficeAdapter/DocumentCoordinator separate from HTTP. Next implement a concrete LibreOffice UNO adapter behind the protocol only after the lifecycle event contract is clear enough to test.
3. Connect the production EditWordDocument handler to request parsing, session coordination, and the observed response-word serializer only when a real office adapter exists; do not return the input bytes as a fake successful document.
4. Continue tracing Word BeforeClose/BeforeSave → worker completion → response WriteContent and correlate with the approximately 54.56-second capture delay. Do not claim the close-time callback is proven.
5. Keep docs/PROJECT-STATUS.md, docs/LINUX-NATIVE-IMPLEMENTATION-PLAN.md, docs/RECOVERY-STORE-ANALYSIS.md, and this handoff synchronized as evidence changes.



### Follow-up: request-to-session service verified

- `EditWordDocumentService.process(MethodCall)` now normalizes the request and invokes the coordinator. It generates a local random session ID and never reads the HTTP `invoke` nonce.
- Office adapters must report document modifications and engine-save events separately. A save records a revision but does not release the waiting request; close triggers export.
- Latest verified CI: run `43719841339`, success, 66 tests.


### SevenZip plugin analysis result

Run `43719323732` completed successfully (artifact `14164146310`). New facts:

- `T7zPlugin` has constructor, destructor, and a shared `CreateObject` method. Both `T7zInArchive.GetInArchive` and `T7zOutArchive.GetOutArchive` call that shared factory.
- `euUnArchive` directly constructs the plugin wrapper using global `0x0062A824`; `euResetMemory` instead calls `CreateOutArchive` (`0x00452BBC`) with a 16-byte global-derived value and the literal module name `7z.dll`.
- `CryptoGetTextPassword2` calls helper `0x00404734`, resolved as the RTL TObjectList constructor; its class pointer comes from global `0x0062FBB8`, and the list is stored at object offset `+0x2C`. This does not identify the writer password value/provider.
- `T7zOutArchive.SetPassword` is a no-op stub. `T7zInArchive.SetPassword` stores its string at `+0x58` and invokes an extraction-style interface call with a callback-like helper, but no raw static pointer to this method was found. Therefore, the mapping from `euResetMemory` slot `+0x44` to that setter remains a strong candidate, not a proven binding.
- Detailed update is in `docs/RECOVERY-STORE-ANALYSIS.md`, section 16.


### Latest coordinator verification

- Python bridge run `43720329600` passed **66 tests** after adding an initialization-event guard. Writer/config initialization events do not mark the document dirty or record a user save; only callbacks after OPENED affect the session state.
- Recovery path workflow `43719180035` completed successfully; artifact `14164088249` was inspected. Plugin follow-up run `43720247793` completed successfully; artifact `14164382428` was inspected for the `euUnArchive` caller path.


### Recovery path workflow #10 result

Run `43719180035` succeeded; artifact `14164088249` was inspected. Additional evidence:

- `T7zInArchive.SetPassword` stores the password at `Self+0x58` and invokes an extraction-style interface call with a callback-like helper; it does not simply forward the string as a COM setter.
- `PrepareOperation` reads `Self+0x58` and handles callback/context fields at `+0x50/+0x54`. The explicit `CryptoGetTextPassword` and `SetPasswordCallback` methods are stubs.
- The three euResetMemory dispatches (+0x44 password, +0x0C path, +0x3C path) align by signature and behavior with SetPassword → OpenFile → ExtractTo. Treat this as the leading hypothesis, not a proven VMT mapping.
- Cleanup imports are now resolved: `TDirectory.GetFiles` enumerates `*.easz`; FileAge/FileDateToDateTime/Now/HoursBetween implement the 24-hour threshold; DeleteFileW deletes older files.
- Detailed update is in `docs/RECOVERY-STORE-ANALYSIS.md`, section 17.


### Separate euUnArchive path result

- Plugin workflow run `43720247793` succeeded; artifact `14164382428` inspected.
- `euUnArchive` (`0x00456DFC–0x00456EFF`) is the only direct bounded caller of the `T7zPlugin` constructor in this scan. It uses global `0x0062A824`, then calls object/interface slots `+0x28`, `+0x10`, and `+0x18` while iterating paired collection-like inputs.
- This is separate from `euResetMemory` → `CreateOutArchive` and its `+0x44/+0x0C/+0x3C` sequence. The `euUnArchive` slot meanings and archive direction remain unresolved; do not use this path to infer the .easz recovery contract.
- Full trace: `docs/RECOVERY-STORE-ANALYSIS.md`, section 18.


### Dispatcher adapter result

- Added `python/src/emwat_linux/editword_handler.py`. It adapts the domain service to the XML dispatcher and serializes successful final bytes using the observed `response-word` envelope.
- A cancellation response factory is mandatory and injected; cancellation HTTP semantics are not guessed.
- The factory is not registered in the running application yet. Registration waits for a real LibreOffice OfficeAdapter and captured cancellation behavior.
- Latest Python CI: run `43721322012`, success, 69 tests.


- Concrete OfficeAdapter implementations must isolate handles/callbacks per document and support concurrent sessions because the loopback bridge serves requests concurrently. The protocol contract now states this explicitly; CI run `43721449170` passed 69 tests.


### Active base-class VMT analysis

- New optimized workflow run `43721583502` is indexing `T7zArchive` separately from `T7zPlugin`/`T7zInArchive`/`T7zOutArchive`, to avoid tracing every inherited method as a duplicate. It also traces target `0x00453950` and VMT/typeinfo references.
- Earlier broad run `43721251511` has now completed successfully; artifact `14164434028` was inspected. It indexes `T7zArchive` base-class procedures including constructor `0x0045392C`, `GetClassId` `0x00453950`, and handler/library-property helpers. The optimized run `43721583502` remains active at its class-index step.


### Base-class index result — 2026-11-15

- Broad plugin workflow run #3 (`43721251511`) completed successfully; artifact `14164434028` was inspected.
- The base class `T7zArchive` is now indexed separately. Constructor `0x0045392C` writes its UnicodeString argument to `Self+0x44` and sets a Boolean at `Self+0x40` according to whether the string is nonempty.
- `GetHandlerProperty` (`0x00453A54`) copies the 16-byte handler-property record at `Self+0x18`. `GetClassId` (`0x00453950`) initializes the base object, resolves a handler using the stored name, and copies a 16-byte property record from global `0x0062A820` into `Self+0x18`.
- These are object-field offsets, not proof of the virtual dispatch slot numbers used by `euResetMemory`. Keep the +0x44 dispatch mapping as the leading hypothesis until the interface/VMT layout is recovered.
- Optimized workflow run #4 (`43721583502`) is still in progress, indexing the class family and related interface/type metadata.


### Close-callback race hardening — 2026-11-15

- `DocumentCoordinator` now guards modification/save callbacks with an `RLock` and disables them immediately after `wait_for_close` returns, before final export. This prevents delayed office-engine events from mutating a finalizing/returned session.
- New regression coverage invokes both callbacks during export and again after return; the revision and saved revision remain unchanged. Python CI run `43722184809` passed **70 tests**.

### SevenZip interface/VMT resolution branch — 2026-11-15

- The completed optimized class-index workflow run `43721583502` succeeded; artifact `14165155588` was inspected.
- The next workflow run `43722345225` now invokes both `resolve_delphi_vmt_slots.py` and `trace_delphi_interfaces.py` for the SevenZip class family. The resolver target list and interface scanner were extended to include `T7zArchive`, `T7zPlugin`, `T7zInArchive`, `T7zOutArchive`, and SevenZip archive/stream interface RTTI names.
- This is specifically intended to resolve whether `euResetMemory`'s interface slots `+0x44/+0x0C/+0x3C` map to the reader wrapper's password/open/extract methods. Do not treat the mapping as proven until the generated interface table is inspected.


### Cancellation callback edge case — 2026-11-15

- Review found that callback detachment originally occurred only on the normal-close branch. The coordinator now disables callbacks immediately after `wait_for_close` returns, before handling either `CLOSED` or `CANCELLED`.
- Added a regression test proving delayed modify/save notifications after cancellation are ignored. Python CI run `43722805637` passed **71 tests** (4.49 seconds).


### `euResetMemory` custom interface identity — 2026-11-15

- SevenZip plugin run `43722345225` succeeded; artifact `14165136040` was inspected.
- `CreateOutArchive` constructs `T7zInArchive` (VMT `0x004525B0`) and returns `Self+0x70`. The class interface table has seven entries; entry 6 has `IOffset=0x70`, IID `022cf785-3ece-46ef-9755-291fa84cc6c9`, and VTable `0x00452420`.
- This proves that `euResetMemory` dispatches `+0x44`, `+0x0C`, and `+0x3C` on this custom interface. The proposed mapping to `SetPassword`, `OpenFile`, and `ExtractTo` is still a hypothesis pending direct vtable slot decoding.
- The next run expands interface vtable output to 20 entries (through `+0x4C`) to expose those targets.


### Word COM metadata and close callback cross-check — 2026-11-15

- Methods BPL run `43722341778` (artifact `14165431103`) shows `WordAppDocumentBeforeClose` (`0x004CCBBC`) calls `0x004BCA88`; the same helper is used by `GetCaptionItemFont`. Direct caller of `0x004CCBBC` remains `FillImgFldsForPrint` (`0x004CCF8F`). No close-time HTTP/response path was found in this body.
- Word event-sink run `43722990625` (artifact `14165586257`) confirms server-data records begin with Word's `ApplicationClass` CLSID (`000209FF`) and `DocumentClass` CLSID (`00020906`) and include known ApplicationEvents/ApplicationEvents2 IIDs. These are generated OLE metadata, not a callback address map.
- Active follow-ups: SevenZip interface vtable through slot `+0x4C` (`43722990639`), RTL helper disassembly for Word server data (`43723423283`), autosave Delete caller (`43723328264`), Word lifecycle (`43722990611`), and broad Methods BPL trace (`43722990637`).


### SevenZip `OpenStream` slot mapped — 2026-11-15

- From artifact `14165136040`, custom interface slot `+0x0C` points through thunk `0x004522E9` to `T7zInArchive.OpenStream` (`0x00452FDC`). `IInStream` is the method's return type; the method accepts an archive-path UnicodeString and creates the stream.


### All three `euResetMemory` SevenZip slots mapped — 2026-11-15

- Plugin run `43722990639` succeeded; artifact `14165676602` includes 20 interface vtable slots.
- On custom interface vtable `0x00452420`: `+0x0C` forwards to `OpenStream(UnicodeString) -> IInStream` (`0x00452FDC`); `+0x3C` forwards to `SetPassword(UnicodeString)` (`0x00453860`); `+0x44` forwards to virtual constructor `T7zArchive.$bctr` (`0x0045392C`).
- `SetPassword` stores its string at `Self+0x58`, creates an extraction callback interface from `Self+8`, and invokes `IInArchive.Extract` (`+0x1C`) with `indices=NULL`, `numItems=-1`, `testMode=0`. This is an all-items archive operation; callback output semantics are not yet proven.
- The autosave Delete trace shows `euResetMemory` takes the selected `.easz` path as its first UnicodeString, a second string from helper `0x0044A998` as the `SetPassword` argument, and a null optional third string. Two true Boolean flags select the constructor fallback `mW@Tlogs43end_+`. The meaning of the second string and callback output path remain open. `ExtractTo` is a separate wrapper, not one of the three direct slots.


### SevenZip extraction callback comparison — 2026-11-15

- `T7zInArchive.SetPassword` uses callback type-info reference `0x0045391C`, creates the callback from `Self+8`, and invokes the underlying archive-interface slot `+0x1C` with `indices=NULL`, `numItems=-1`, `testMode=0`.
- Separate `T7zInArchive.ExtractTo` uses type-info reference `0x00453850`, stores callback/context at `Self+0x50/+0x54`, and invokes the same underlying slot with `testMode` selected by its Boolean parameter.
- Both are all-items operations, but they use different callback types. The latest plugin run `43723896564` is tracing those type-info blocks and pointer references; output destination remains unproven.


- The internal archive-interface slot `+0x1C` is identified as `IInArchive.Extract`: the wrapper methods `ExtractItem` and `ExtractTo` also call this slot with their item/test-mode arguments. Thus `SetPassword` in the recovery path issues an all-items Extract request through its own callback. The callback's output destination remains unresolved.


### Autosave Delete caller argument types — 2026-11-15

- Run `43723328264` / artifact `14165058222` traces `TfrmShowAutoSaveFiles.Delete` (`0x005EB828`). The selected archive path is copied from the selected item record's `+0x20` field into `[ebp-4]` via `UStrLAsg`; this is the first `euResetMemory` argument.
- `[ebp-8]`, the second argument, is produced by helper `0x0044A998` and passed to `SetPassword`. Its source semantics remain unknown.
- The call passes `ECX=0` and two stack Boolean flags set to 1, selecting the `mW@Tlogs43end_+` constructor fallback.
- After `euResetMemory`, the caller invokes `0x004563A8` with the same two strings, then `0x004565DC` and `0x004555D8`. These helpers are the next targets for identifying the `.easd` output path and cleanup.


### Latest verified work — 2026-11-15

- Recovery/SevenZip artifact 14166161804 (run 43723896564) shows T7zInArchive.SetPassword initiates IInArchive.Extract for all items through a callback; it is not merely a password-field assignment. PrepareOperation has distinct callback/context and stored-string paths. Output stream destination remains unresolved.
- ExtractTo uses callback type-info 0x00453850; SetPassword uses 0x0045391C.
- Word lifecycle run 43722990611 completed successfully; artifact 14165369436 resolved registry thunks: 0x404414 WriteInteger, 0x404424 WriteBool, 0x40441C ReadInteger, 0x40442C ReadBool, and 0x404454 ValueExists.
- Detailed findings were appended to docs/RECOVERY-STORE-ANALYSIS.md sections 21–22 in commit d17a801d0d02f12e4a6b286af7aa1e21a9e691ac.
- Recovery-path run 43724386278 was still in progress at the last check. Keep the .easd destination, archive password semantics, and Almas close-time registration protocol unresolved until direct evidence is available.


### Current recovery reverse-engineering state — 2026-11-15

- Run 13 (`43724386278`, artifact `14165938809`) completed. `0x0044A998` is `Emwat.Sys.MyMessageDialog`, called by the recovery Delete handler to produce the string passed as `euResetMemory`'s second argument; it then reaches `T7zInArchive.SetPassword` through interface slot `+0x3C`. Exact dialog semantics and the returned string's relation to the archive password are not proven.
- Do not confuse that helper with `euGetAutoSavePass` (`0x00456B78`), a separate `GetUserNameW` helper used in cleanup/logging.
- Recovery Delete applies `FixDirectionInFarsiNumericMode` (`0x004563A8`) to a path-like value before constructing a `.easd` path; extraction destination/content remains unresolved.
- Callback-contract analysis is now a separate workflow. It traces callback RTTI, `+0x44` dispatch target, and the archive extraction callbacks. See `docs/RECOVERY-STORE-ANALYSIS.md` section 23 and commit `b753390bd421047e22d072b1012d9be3d829015a`.


- Follow-up correction commit `6ed0f8f490515f548065a39afe546c9a6838c660` fixes the recovery Delete call-site description: `0x004563A8` receives only the selected `.easz` path (with Boolean flags false) and produces the normalized path-like string used to construct the `.easd` path. It is not passed the password string.


### Latest callback-contract findings — 2026-11-15

- Callback-contract run 2 (`43725294172`, artifact `14165994624`) confirms `T7zArchive.$bctr` at `0x0045392C` stores its string at `Self+0x44` and sets `Self+0x40` according to whether it is nonempty. The recovery fallback `mW@Tlogs43end_+` is passed to this constructor, not to `SetPassword`.
- The `MyMessageDialog` result is a separate string passed to `T7zInArchive.SetPassword` via slot `+0x3C`.
- Callback references `0x00453850` and `0x0045391C` contain the same `IArchiveExtractCallback` IID. Their construction contexts differ, but they implement the same COM callback interface.
- `PrepareOperation` has distinct branches using `Self+0x3C`, `Self+0x50/+0x54`, and `Self+0x58`; exact property mapping and final output destination remain open. See `docs/RECOVERY-STORE-ANALYSIS.md` sections 24–25.
- Follow-up workflow run 3 is queued to resolve the remaining non-TD32 slot targets and dialog strings.


## 2026-11-16 — ادامه موازی: Twin Field، Custom Properties و مقصدهای مقداردهی Word

### شواهد تأییدشده جدید

- اجرای `43811074616` موفق شد؛ artifact شامل 41 فایل procedure/callers/pointer refs/strings بود.
- اجرای helper pipeline `43812127854` موفق شد و delimiter ثابت `0x004D1768` را به `†` (U+2020) decode کرد.
- `AddCustomDocPropertiesToDic` نام propertyهای سفارشی سند را با اولین dagger بررسی می‌کند. دو بخش غیرخالی، رکورد `TXmlWordConfigTwinField` می‌سازند؛ حالت بدون delimiter یا یک سمت خالی، به `TXmlWordConfigField` تکی برمی‌گردد.
- dictionaryهای viewer در offsetهای `+0x68` و `+0x6C` به‌ترتیب با `TXmlWordConfigField` و `TXmlWordConfigTwinField` مرتبط‌اند. متدهای `0x004D531C` و `0x004D68D4` generic Remove هستند، نه setter.
- `FillImageField` در `0x004BC30C` فقط image insertion نیست: logهای داخلی دو مقصد مقداردهی را تأیید می‌کنند: `CustomDocumentProperties[index]` و `Field.Result.Text`. مسیر دوم وضعیت lock فیلد را بررسی می‌کند.
- نام‌های ویژه `LetterRegistrationDate`، `LetterRegistrationNo` و `ProduceDate` در شاخه‌ای وابسته به flag داخلی `viewer+0xF0` پردازش می‌شوند.
- Writer catalog اکنون نام Custom Document Properties را بدون خواندن مقدارشان گزارش می‌کند.
- `parse_word_field_identifier` در Python اولین dagger را جدا می‌کند و ورودی ناقص را single نگه می‌دارد.

### CI تأییدشده

- Python bridge run `43812324657`: 87 تست پاس، یک تست UNO اختیاری skip.
- LibreOffice UNO run `43811929904`: 8/8 تست پاس؛ fixture یک UserDefinedProperty ساختگی اضافه می‌کند و فقط نام آن را از catalog می‌گیرد.
- Word custom-property helper analysis run `43812127854`: success.
- Word field pipeline run `43811074616`: success.

### کارهای موازی بعدی

1. بررسی دقیق قرارداد رکورد `TDocumentCProperty` و رابطه indexهای آن با collection واقعی Word CustomDocumentProperties؛ helperهای `ContainsValue` و `SetItem` اکنون شناسایی شده‌اند.
2. اعتبارسنجی رفتار معکوس‌سازی componentهای `FindWindowExtd` با مقدار واقعی مجاز/ناشناس‌سازی‌شده؛ الگوریتم slash/hyphen و reverse order اکنون از disassembly استخراج شده، اما نمونه واقعی برای تعیین قاعده locale لازم است.
3. تکمیل معنای `FillPrintOptionForm` در `0x004D1B30` و نگاشت collectionهای `Receivers`/`ReceiverDeps`/`ccReceivers`/`ccReceiverDeps` به recipient/CC نهایی.
4. پس از تکمیل این helperها، مدل Writer را به سه مقصد مستقل گسترش بده: custom properties، text-field result، و image anchors؛ mapping واقعی 180 شناسه را بدون template واقعی حدس نزن.
5. مسیر close/XHR و پاسخ cancel هنوز end-to-end با Almas تأیید نشده است؛ از پاسخ ساختگی یا اعلام ثبت قطعی خودداری شود.


### تکمیل مقصد Custom Document Property در Writer

- ماژول `python/src/emwat_linux/writer_properties.py` اضافه شد.
- `set_custom_document_property(document, property_name, value)` فقط property موجود را با نام دقیق به‌روزرسانی می‌کند؛ اگر نام وجود نداشته باشد `KeyError` می‌دهد و property جدید ایجاد نمی‌کند.
- تابع مقدار قبلی property را نمی‌خواند؛ catalog همچنان فقط نام‌ها را inventory می‌کند.
- تست UNO واقعی روی property ساختگی نشان داد Writer property را به‌روزرسانی می‌کند.
- CI پس از این تغییر: Python run `43813400123` = 91 تست سبز (یک skip اختیاری)، UNO run `43813378877` = 8/8 سبز.
- یک workflow برای index کردن تمام TD32 symbolهای `TDocumentCProperty` و `TXmlWordConfigField/TwinField` اضافه شده است. نسخه نخست script خطای آرگومان TD32 داشت؛ اصلاح شد و اجرای جدید در حال بررسی است. خطاهای قدیمی `43813052058` و `43813063493` مربوط به نسخه‌های پیش از اصلاح هستند و نباید به‌عنوان وضعیت نهایی تلقی شوند.


### TD32 symbol inventory

- Run `43813303321` completed successfully; artifact `14201306994` indexes 611 procedures whose symbols mention `TDocumentCProperty`, `TXmlWordConfigField`, or `TXmlWordConfigTwinField`.
- New utility `tools/list_td32_symbols.py` produces the index with VA, size, module, and symbol name.
- High-value next procedures now identified:
  - `0x004BFDB0` — `TWordViwer.SetFieldValue`
  - `0x004BFC18` — `TWordViwer.GetXmlFieldInfo`
  - `0x004D3B38` — `TDictionary<UnicodeString,TDocumentCProperty>.Add`
  - `0x004D3D2C` / `0x004D3D3C` — `TryGetValue` / `AddOrSetValue` for document custom properties
  - `0x004D52DC` / `0x004D54E0` — single-field dictionary `Add` / `AddOrSetValue`
  - `0x004D6894` / `0x004D6A98` — twin-field dictionary `Add` / `AddOrSetValue`
- Focused helper workflow now traces these addresses in parallel; run IDs `43813533418` and `43813557802` were created while expanding the target set. Verify the newest run before reporting its outcome.


### قرارداد دقیق GetXmlFieldInfo

- `0x004BFC18` ابتدا dictionary single در viewer `+0x68` را lookup می‌کند؛ در صورت نبود، dictionary twin در `+0x6C` را lookup می‌کند.
- Single record: index در `+4` و field ID در `+8`.
- Twin record: index در `+4`، شناسه اول در `+8` و شناسه دوم در `+0xC`. تابع counterpart طرف مقابل را برمی‌گرداند.
- در صورت عدم تطبیق، index برابر `-1` و flag موفقیت false می‌ماند.
- هدف بعدی trace کردن `SetFieldValue` در `0x004BFDB0` و callsiteهای dictionary Add/AddOrSetValue است تا قرارداد value/index نهایی روشن شود.


### Controller Notify و مسیر finalize سند

- Run `43813684507` موفق شد؛ artifact `14200889822`.
- `TWordViwer.OnControlerNotify` در `0x004BB3B0` پس از اعتبارسنجی state/message، `CostumizeRecAndCC` را اجرا می‌کند، سپس `-1` را همراه document interface به COM slot `+0xDC` می‌دهد و flagها را reset می‌کند.
- بعد از آن دو مقدار از مسیر `FixDirectionInFarsiNumericMode` و `0x00456DFC` عبور می‌کنند.
- `0x005EE82C` در TD32 با نام `TScanDocument.PerformMethod` آمده و `LoadDocument` در `0x004B7724` را فراخوانی می‌کند؛ نام procedure را به‌جای برچسب قبلی TEditWordDocument در مستندات استفاده کن.
- COM slot `+0xDC` هنوز با wrapperهای `TWordDocument.Close` و `Save` تطبیق داده نشده. دو workflow جدید برای مقایسه slotها و decode رشته‌های controller/PerformMethod در حال اجرا هستند: `43814055308` و `43814083027`.
- ثبت نهایی Almas و payload شبکه هنوز اثبات نشده؛ صرفاً این controller-notify sequence با finalize/close-side سازگار است.


### آخرین وضعیت موازی — 2026-11-16

- Python bridge run `43816293635`: **99 تست run، 98 پاس، 1 skip اختیاری**. URL decoder مطابق native رفتار می‌کند: `+` به فاصله و `%2B` به plus تبدیل می‌شود.
- Word custom-property helper run `43816241948`, artifact `14201844295`: `0x004D1B30` تابع `FillPrintOptionForm` است؛ `tokenizedReceivers` و delimiter U+2020 (`†`) تأیید شدند. چهار config key شامل `Receivers`, `ReceiverDeps`, `ccReceivers`, `ccReceiverDeps` هستند.
- LibreOffice integration run `43815592590`: **8/8 سبز**. `LibreOfficeAdapter.apply_custom_property_updates` propertyهای موجود را batch-update می‌کند و text fields را یک بار refresh می‌کند؛ complex DOCX DOCPROPERTY field نتیجهٔ جدید را نشان می‌دهد و خروجی DOC/CFB تولید می‌شود.
- VMT/interface artifact `14201779902` از close-response run `43815900214`، آدرس VMTهای `TEditWordDocument=0x005ED764` و `TScanDocument=0x005ED884` را گزارش می‌کند؛ هر دو parent برابر `0x0046ABA4` هستند. با این حال resolver نتوانست slotهای method را از RTTI تأیید کند.
- VMT candidate مربوط به `TWordDocument` در `0x00412174` نیز unverified است. wrapperهای typed نشان می‌دهند `Get_Saved → interface slot +0xD4`، `Set_Saved → +0xD8`، `Get_Content → +0xDC` و `Save → +0x2B8`. چون callsite در `OnControlerNotify` برای `+0xDC` آرگومان `-1` می‌فرستد، receiver/signature دقیق هنوز حل نشده؛ آن را Save/Close فرض نکن.
- `0x005EE82C` در TD32 با نام `TScanDocument.PerformMethod` دیده می‌شود و pointer reference آن در محدودهٔ VMTهای connector نیز نیازمند تطبیق دقیق است؛ نام کلاس را قطعی به TEditWordDocument نسبت نده.
- مسیرهای باز: قرارداد و callsiteهای `TDocumentCProperty.Add/AddOrSetValue`، معنای دقیق collectionهای Rec/CC، direct `Field.Result.Text`، image anchors، template واقعی Almas و close/XHR ثبت نهایی.



## Autonomous parallel checkpoint — 2026-11-16 09:50 local

### Verified since previous handoff

- Native Base64 field decoder path is resolved: `SetFieldValue(encryption=base64)` → `WideCharToMultiByte` → wrapper `0x004735D0` → orchestrator `0x004738CC` → decoded-length helper `0x00473608` + quartet decoder `0x00473700` (lookup table `0x00627F98`). The Linux field decoder no longer strips whitespace; standard complete quartets and one-/two-character padding are tested.
- Python bridge workflow `43818155017`: 99 tests passed, 1 skipped.
- `TXMLFieldType` metadata is mapped: VMT `0x004751E4`, interface offset `0x50`; typed getters/setters exist for Id, Mimetype, Encryption, Separator, Concater, ParamId, IsNew.
- Viewer-side VMTs: `TDocumentCProperty` `0x004B05A8` / size `0x1C`; `TXmlWordConfigField` `0x004B068C` / size `0x10`; `TXmlWordConfigTwinField` `0x004B0774` / size `0x18`.
- COM wrapper dispatch: `Get_Saved +0xD4`, `Set_Saved +0xD8`, `Get_Content +0xDC`, `Save +0x2B8`. `OnControlerNotify` uses `+0xDC`, not Save/Close.
- Event record callbacks are BeforeSave (`0x004CD154`), conditional BeforePrint/LoadOptions (`0x004D00AC`), NewDocument (`0x004CD54C`), WindowActivate (`0x004CD9C0`). Main-editor BeforeClose registration is still unproven.
- Controller-notify has a second paired-stream branch that prepares `.easd` and `.easz` paths and calls `euUnArchive` through the SevenZip plugin. Its relationship to recovery Delete and final Almas registration is not yet established.

### Current parallel workflow snapshot

- `43817445960` — Word lifecycle analysis; in progress, 18/37 top-level steps completed at snapshot.
- `43818082486` — XML twin-field metadata/property trace; in progress, first parallel trace step running.
- `43818434937` — controller notification dispatch trace; queued at snapshot.

### Remaining critical blockers

1. Resolve `TXmlWordConfigTwinField` and `TXMLFieldType` property consumption to prove `separator`/`concater` semantics.
2. Trace `TEDPController.Notify` (`0x004D2EC8`) into `TWordViwer.OnControlerNotify` and identify the exact notification message activating paired streams.
3. Resolve the exact main-editor close/registration request and response envelope.
4. Obtain an anonymized representative Almas Word template; current installer archive contains no Word-family templates, so visual fidelity and field-to-bookmark mapping remain unverified.

Do not implement guessed `signData` joining or claim end-to-end Almas registration until these traces/template are available.


## Confirmed Word close lifecycle — 2026-11-16

- Main editor close path is the registered `WordAppDocumentBeforeSave` callback at `0x004CD154`, not `WordAppDocumentBeforeClose` at `0x004CCBBC`.
- Callback sets Word `Saved=False` via COM slot `+0xD8`, asks whether to register changes, then invokes the three-argument `_Document.Close` through slot `+0x29C`.
- Dialog mapping: Yes → SaveChanges `-1`; No → SaveChanges `0`; Cancel → event Cancel `0xFFFF` and no close.
- One-/two-/three-argument Close wrappers at `0x0042FF08`, `0x0042FF7C`, `0x0042FFF4` all dispatch to the same COM Close slot `+0x29C`.
- This explains close-triggered registration without a manual Save click. Exact HTTP return envelope and the notification that transfers final bytes to Almas remain unresolved.
- Evidence: lifecycle run `43817445960`, artifact `14203757393`; details in `docs/WORD-COM-INTERFACE-DISPATCH.md` Run 134.


## XML attribute spelling caution

- Native parser-side `TXMLFieldType.Set_Concator` reads the key `concator`; existing request-schema transcription currently says `concater`.
- These are not treated as aliases. Runtime preserves raw attributes; do not normalize or implement concatenation until the raw request is rechecked.
- `Set_Separator` reads `separator`; `Set_ParamId` reads `paramId`.


## Autonomous continuation checkpoint — 2026-11-16 12:xx

### Repository and current scope
- Continue only EMWAT reverse engineering in `meicamghe/EMWAT-Linux`.
- Do not switch to or mix in the separate Winux workstream.
- Current latest analysis note: `docs/WORD-LIFECYCLE-STATIC-TRACE.md`; project status has the latest summary.

### Newly checked artifacts
- Re-opened artifact `14208369288` from successful run `43832553168` (BPL Invoke/VMT analysis).
- Re-opened artifact `14203757393` (large Word lifecycle, class-method, VMT, controller, and AutoSave trace collection).
- Re-opened artifact `14205656649` (service HTTP response and Indy VMT trace collection).
- Re-opened artifact `14206405476` (Word COM event-sink and close decision evidence).

### Important findings and corrections
1. `TEmwatMethod.Invoke` (`0x0046C82C`) walks dictionary key/value pairs. `0x0046E324` is `TPairEnumerator.DoGetCurrent`; `0x0046E3CC` maps to `TPairEnumerator.MoveNext` in VMT RTTI despite a conflicting TD32 decorated label. Raw pointer search found no static reference to `0x0046C82C`; its runtime role is still unresolved. Do not assume it is the request dispatcher.
2. `TEditWordDocument` VMT `0x005ED764` slot `+0x10` points to `0x005EE82C`. This routine reads `wordConfig`, `wordBody`, `letterImages`, `signData`, validates `wordConfig`, and calls `TWordViwer.LoadDocument` at `0x004B7724`. TD32 decorates the target as `TScanDocument.PerformMethod`. `TScanDocument` VMT slot `+0x10` points to `0x005EEB48`, which TD32 decorates as `TFaxDocument.PerformMethod`. Preserve this VMT/symbol mismatch; resolve class registration before renaming.
3. The main editor close behavior is already resolved in earlier artifacts: registered callback is `WordAppDocumentBeforeSave` at `0x004CD154`, with Yes → Close(SaveChanges=True), No → Close(SaveChanges=False), Cancel → event Cancel and leave the document open. `WordAppDocumentBeforeClose` at `0x004CCBBC` is not the main editor close callback.
4. The periodic `OnTmrAutoSave` path sets `OnControlerNotify` as a timer callback and enforces a minimum interval of 10 seconds. Keep this separate from the close-time registration prompt.
5. Service HTTP handler/Indy response writer work is already substantially mapped in existing artifacts. The current public `analysis-input/` directory does not contain `EmwatService.exe`, so a fresh service PE trace cannot run from this checkout unless an authorized analysis copy is added.

### New work committed
- Added `.github/workflows/analyze-emwat-dispatch-crosswalk.yml` with parallel service/BPL/Word jobs; service job now reports missing input cleanly.
- Expanded target lists to cover dispatch helpers, Word lifecycle callbacks, field mapping, and SilentSave.
- Added `docs/WORD-LIFECYCLE-STATIC-TRACE.md` and linked it from README.
- Updated `docs/PROJECT-STATUS.md`.
- Latest known commits at checkpoint: `bfc6654ca90e3ddf4edda9e0dc0edb07635f4bd5` (status update; latest of the above batch).

### Do not claim
- Do not claim the newly expanded workflow has passed; its run/artifacts have not yet been verified.
- Do not claim the full service-parser → concrete class → PerformMethod → HTTP response chain is closed.
- Do not infer the exact meaning of the final invoke response or Almas persistence from HTTP 200 alone.

### Next work, in order
1. Resolve XML `class="EditWordDocument"` to the concrete Delphi class/VMT and the `+0x10` method slot; inspect class registration tables, class-name lookup, and RTTI invocation in the BPL and service traces.
2. Trace the request-side method factory/dispatch helper into the VMT call. Keep `TEmwatMethod.Invoke` separate until its runtime caller and role are proven.
3. Connect `TWordViwer.OnControlerNotify` → `Get_Content` → helper `0x00456DFC` to the long-lived HTTP invoke response writer, without assuming that every timer tick is a final registration response.
4. Compare the close-time response payload with the request `wordConfig` and the opaque document bytes, using only synthetic or anonymized data.
5. Update the docs and Python bridge only when the dispatch and response contract is evidenced.


## Latest verified continuation — 2026-11-16

### Successful runs and artifacts
- Run `43867641761`: all 3 dispatch-crosswalk jobs succeeded. BPL artifact `14225499151`, Word artifact `14226866454`; service artifact `14226172178` is an explicit missing-input note only.
- Run `43868190188`: all 3 expanded VMT/Word/service jobs succeeded. BPL artifact `14225224443`.
- Run `43868321797`: controller content unpack job succeeded. Artifact `14226342809`.
- The new service-artifact workflow run `43868531786` and expanded controller archive run `43868705082` were queued at the last check; inspect them before claiming success.

### Important corrections
1. `0x004563A8` is `FixDirectionInFarsiNumericMode`, not a list constructor. The two objects in `OnControlerNotify` are created by helper `0x0040414C` using global/class reference `0x0062F810`.
2. Strings `0x004BB754` and `0x004BB76C` decode to `.easd` and `.easz`. The path at `TWordViwer+0x80` is direction-normalized and these suffixes are appended.
3. `0x00452C10` constructs the `T7zOutArchive` interface returned by `T7zPlugin`; `0x00456DFC` is `Emwatutils.euUnArchive`. Its two inputs are `TStringList` instances. Interface slot `+0x10` reaches `AddFiles` (`0x453F34`), slot `+0x18` reaches `SaveToStream` (`0x454668`), and slot `+0x28` reaches `0x4547E8`, which stores the input string in field `+0x38` = `FPassword`. Thus `mW@Tlogs43end_+` is the archive password. The path `.easd` is the archive entry name and `.easz` is the output archive path.
4. The exact VMT inspection proves `TEmwatMethod` slot `+0x0C` is the shared public Invoke wrapper `0x0046C9E0` (TD32 label `Finalization`); slot `+0x10` is the abstract/error stub `0x00401068`. The wrapper calls the inner dictionary/XML helper `0x0046C82C`, then dispatches the concrete subclass through VMT slot `+0x10`.
5. `TEditWordDocument` inherits `TEmwatMethod`; its VMT slot `+0x10` points to `0x005EE82C`, TD32-decorated as `TScanDocument.PerformMethod`. `TScanDocument` VMT slot `+0x10` points to `0x005EEB48`, TD32-decorated as `TFaxDocument.PerformMethod`. Class resolution and the wrapper-to-subclass VMT dispatch are confirmed; preserve the pointer/name discrepancies.

### New workflows
- `.github/workflows/analyze-emwat-controller-unarchive.yml` expanded to inspect helpers `0x0040414C`, `0x004543C4`, SevenZip class procedures, VMTs, and interface tables.
- `.github/workflows/analyze-emwat-service-dispatch.yml` downloads the preserved artifact `emwat-mainform-invoke-handler` from run `43831365563`, so the service EXE can be analyzed without adding it to the public repo.
- The dispatch crosswalk workflow's YAML path-filter newline bug was corrected; run `43868190188` passed all jobs.

### Next tasks
1. Inspect the latest archive-method workflow artifact for the exact stream class behind global `0x0062F800` and the remaining password callback path.
2. Trace the concrete `TEditWordDocument.PerformMethod` body at `0x005EE82C` through `TWordViwer.LoadDocument`, field updates, and the archive source file.
3. Connect the `.easz` archive output from `OnControlerNotify` to the service invoke response and determine whether it is the close-time commit payload.
4. Trace the final HTTP response serialization/ContentText assignment; do not treat init/heartbeat WriteContent calls as proof of the invoke response.
5. Keep timer-driven `OnControlerNotify`, Word BeforeSave, and the Almas apply-on-close action as separate events until their data flow is linked.


### Service artifact analysis correction
- The preserved artifact `emwat-mainform-invoke-handler` downloaded successfully from prior run `43831365563`; it contains `EmwatService.exe`.
- The first deep service workflow `43868531786` failed because this EXE has no TD32 debug signature. It is not a missing file and not a bad download.
- Service workflow was corrected to use PE disassembly, raw pointer-reference scans, VA context inspection, and string decoding only. It no longer invokes TD32-dependent scripts for the service EXE.
- Corrected run `43868823284` was queued at this checkpoint; inspect its job and artifact before reporting success.
- Keep the EXE out of the public repository; use the preserved workflow artifact as the CI input.


### SevenZip interface correction
- Exact VMT inspection shows `T7zPlugin.$bctr` obtains an interface pointer at `T7zOutArchive` object offset `+0x44`, IID `baa9d5dc-9ff4-4382-9bfd-ec9065bd0125`.
- Through this interface: `+0x10 → AddFiles (0x453F34)`, `+0x18 → SaveToStream (0x454668)`, `+0x28 → SetProgressCallback (0x4547E8)`.
- Therefore do not call `mW@Tlogs43end_+` a confirmed password; it is passed to SetProgressCallback through the observed interface. `SetPassword` exists separately at `0x4547DC`, but is not the mapped target.
- `euUnArchive` passes two TStringList values to AddFiles and a `.easz` UnicodeString to SaveToStream; these do not obviously match the TD32 signatures. The archive direction and exact argument types remain unresolved. Next inspect target method bodies and the wrapper/factory.
- Expanded archive workflow run `43869599848` was queued for those method-body traces at the last check.


### Invoke bridge and XML version contract
- Service artifact `14226099734` confirms the embedded init script POSTs `message.data` to `http://127.0.0.1:$V{myport}?invoke=<random nonce>` and relays `responseText` to the parent frame.
- Service strings and parser traces confirm root `emwat`, attribute `version`, exact numeric version `1`, child `method`, attribute `class`, child `param`, and attribute `name`.
- `0x0047E0EC` is BPL package load; `0x0047E2D4` is package unload. They bracket `ParseMethod`; neither is the concrete method dispatcher.
- The exact request schema is updated in `docs/EDITWORD-REQUEST-SCHEMA.md`; HTTP bridge details are in `docs/HTTP-LOCAL-API-ANALYSIS.md`.


- Artifact `14226742624` confirms `0x0040414C` is the `rtl230.bpl!TStringList.$bctr` import thunk. Both objects passed into `euUnArchive` are TStringList instances. First list receives `TWordViwer+0xA0`; second receives the direction-normalized `TWordViwer+0x80` path with `.easd` appended. The pairwise list loop passes entries to the `T7zOutArchive` interface, then sends the `.easz` path through slot `+0x18`.


### Archive path resolved (Run 148)
- Artifact `14227611377` proves the `euUnArchive` path is building a password-protected 7z output archive, despite its helper name.
- Interface `+0x10` → `T7zOutArchive.AddFiles` (`0x453F34`): first TStringList value is the source file path (`TWordViwer+0xA0`); second is the archive entry name (base path + `.easd`).
- Interface `+0x18` → `T7zOutArchive.SaveToStream` (`0x454668`): saves to base path + `.easz`.
- Interface `+0x28` → `0x4547E8`: despite TD32 label `SetProgressCallback`, body stores the input string in field `+0x38`, identified by the T7zOutArchive field table as `FPassword`. Therefore `mW@Tlogs43end_+` is the archive password assigned in this path. The separate `SetPassword` at `0x4547DC` is a no-op.
- Remaining: resolve global `0x62F800` to exact stream class; trace the callback that consumes FPassword; then capture a synthetic runtime archive if possible. Do not claim the archive has been validated at runtime.


### Confirmed service-to-BPL dispatch correction
- The prior caution that the `TEmwatMethod.Invoke` helper was not the runtime dispatcher is superseded by the public wrapper distinction.
- Service parser extracts `method@class` and `param@name`, resolves `GetClass("T"+className)`, constructs the class, and calls VMT slot `+0x0C`.
- `TEmwatMethod` VMT slot `+0x0C` → `0x0046C9E0` shared wrapper; wrapper calls inner XML/dictionary helper `0x0046C82C` then subclass `PerformMethod` at VMT slot `+0x10`.
- The service-side class lookup and dispatch chain is fully documented in `docs/EMWAT-SERVICE-EXECUTABLE-ANALYSIS.md`; the remaining response serialization and close-time commit link are still open.
