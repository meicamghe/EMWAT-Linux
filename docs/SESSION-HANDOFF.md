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

1. **Finish the remaining XML method/serialization mapping.** The service parser's `TMethodInfo.Params` and BPL `TEmwatMethod.Invoke` use `TDictionary<AnsiString, AnsiString>`. Service slot `+0x0C` reaches shared wrapper `0x0046C9E0), which calls `TEmwatMethod.Invoke` (`0x0046C82C`) and then the subclass slot `+0x10`. Inside Invoke, local `[ebp-4]` is a `TXMLEmwatType` interface; its `+0xB0` thunk `0x0044B709` reaches `TXMLMethodType.AfterConstruction` at `0x0044C458), producing the interface in `[ebp-0x1C]`. That `TXMLMethodType` interface's `+0xCC` thunk `0x0044BA61` reaches `TXMLMethodType.Insert` at `0x0044C754), which appends a child and returns the interface in `[ebp-8]`. RTTI and VTable offsets strongly identify `[ebp-8]` as a `TXMLParamType` interface. Invoke then calls its `+0xB0` and `+0x68` slots with the first and second dictionary-pair strings. The TXMLParamType VTable thunks are `0x0044BDF5` and `0x0044BEB5`; they adjust Self by `-0x50` and resolve to `0x0044C8E4` and shared target `0x0044B568` respectively. The `+0x68` target `0x0044B568` is confirmed as `xmlrtl230.bpl!TXMLNode.SetText(UnicodeString)`, so the second pair string is the parameter node's text/value. The `+0xB0` target `0x0044C8E4` calls `xmlrtl230.bpl!TXMLNode.SetAttribute(UnicodeString, OleVariant)` with the literal attribute name `name` and the first pair string as its value. Thus each pair becomes an XML parameter node with `name` attribute and text content. Focused run 11 (`43571811038`, artifact `14105075475`) confirms both targets and the `name` literal. After the loop, TXMLEmwatType interface slot `+0x54` returns the serialized XML string into Invoke's output parameter; its VTable target still needs mapping. Next decode the TXMLMethodType +0xC8 attribute literal at `0x0044C6A4`: its implementation `0x0044C62C` (TD32 label `Get_Param`) passes the method-name string and this literal to `TXMLNode.SetAttribute`. The service parser expects `method@class`, so confirm whether the literal is `class`. The TXMLEmwatType serializer getter slot `+0x54` is at VTable address `0x0044B8CC`, pointing to thunk `0x0044B7A9`; map its implementation.

2. **Trace the concrete Word-edit method and its document helper.** Run 76 recovered `TEditWordDocument` VMT `0x005ED764`; slot `+0x10` points to executable target `0x005EE82C`, despite the missing TD32 procedure record. The target reads `wordConfig`, `wordBody`, `letterImages`, and `signData`, then calls `TWordViwer.LoadDocument` at `0x004B7724` with the `TEmwatInvokeParam*` and output-string reference. `LoadDocument` parses the `word-document` config, prepares the document/Wordviewer, and reaches `OnTmrAutoSave` at `0x004B8A84` to register Word callbacks. The registration maps `+0x80 → 0x004CD154` (`WordAppDocumentBeforeClose`), `+0x90 → 0x004CD54C` (`WordAppDocumentBeforeSave`), and `+0x98 → 0x004CD9C0` (export name `WordAppNewDocument`). The main close callback at `0x004CD154` prompts to save changes and calls the three-argument Word `Close` overload through slot `+0x29C`. It has no direct HTTP call; trace its viewer helpers and parent-page message. It reads the generated temp document, builds the response XML, and deletes the temp file. Keep the TD32 symbol-name mismatch caveat for other connector classes.
3. **Finish the service request-record and input-stream trace.** `TMainForm.IdHTTPServerCommandGet` (`0x0047BF30`) and the XML/class dispatcher at `0x00470D00` are mapped through BPL slot `+0x0C` (`0x0046C9E0`) → `TEmwatMethod.Invoke` (`0x0046C82C`) → subclass slot `+0x10`. The handler's `TEmwatInvokeParam` layout is known, and its `SessionId` is a separate server-generated six-digit string. The object at `[ARequestInfo+0xD4]` is now identified with high confidence as `TIdHTTPRequestInfo.PostStream`; identify the exact stream virtual method names/signatures behind its size/read operations, and trace how the internal `SessionId` is consumed. The embedded bridge generates the numeric `invoke` value solely as a per-request URL nonce/cache-buster; it is not a method ID or response-correlation token. The bridge forwards `event.data` unchanged and returns `responseText` to the original `event.source`/`event.origin`.
4. **Validate the concrete HTTP response and its schema.** The successful `LoadDocument` path writes its output XML to `AResponseInfo.ContentText`, calls `IdCustomHTTPServer.TIdHTTPResponseInfo.WriteContent` (`0x0040448C` / IAT `0x0062F9C0`), and sets `TEmwatInvokeParam.bResultSet=true`; the generic dispatcher fallback is skipped. It references `application/msword` and `success`, but the exact serialized element layout/encoding still needs comparison with the captured runtime response. Also trace `bUnloadPkg` cleanup after `TEditWordDocument` sets it true. Do not assume `requested-types=application/msword` proves the final file format is DOC.
5. **Trace the registered close callback to the parent-page message and final commit.** `TWordViwer.WordAppDocumentBeforeClose` at `0x004CD154` is registered at event-record `+0x80`. It first calls `RollBackOriginalOptions` (`0x004CB108`), checks `Document.Saved` via `_Document` slot `+0xD8` (typed wrapper `Get_Saved` at `0x0042BD94`), then prompts Yes/No/Cancel and invokes the three-argument `Close` overload through slot `+0x29C`. It does not issue HTTP directly. Identify which viewer helper/save path changes state and which parent-page `postMessage` causes the bridge's close-time XHR. Keep `0x004CCBBC` separate: it is the nested `Wordxp.Fields` helper reached from `BGPrintWithGamPrintOptions → GetFieldIndexInList → FillPrintDocFields`, not the registered close callback.
6. **Retain autosave/close candidates only in their proven scope.** The `uSendLog` callback at `0x005EC580` belongs to the autosave-files UI and calls `CloseWordApp`; its DFM resource does not visibly bind a Word close event. WordXP Close wrappers have no direct TD32 CALL xrefs. Neither is the proven main letter close path.
7. **Resume scanner/image subsystem analysis after the connector path is understood.** Keep image-only letters, TIFF, rotate/crop, multipage processing, ImageGear/ImageEn and GEAR/SANE scanning as first-class requirements. Do not reduce the Linux port to text-only document editing.
8. **Only then implement the native Linux bridge contract and integration tests.** Keep the local service loopback-only, validate origins/tokens/payload sizes/file paths/timeouts, and test synthetic letters and templates with LibreOffice Writer. Do not implement guessed endpoints or claim end-to-end parity before protocol/runtime validation.


## Runtime validation questions

- What exact request/response reaches the local service for a Word document?
- What exact TXMLMethodType method-name setter is reached through `TEmwatMethod.Invoke` slot `+0xC8`, and what target implements TXMLEmwatType serialization slot `+0x54`?
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
