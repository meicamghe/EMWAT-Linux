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

1. **Continue the connector dispatch trace.** The service parser's `TMethodInfo.Params` is `TDictionary<AnsiString, AnsiString>`, and the BPL `TEmwatMethod.Invoke` and concrete `PerformMethod` signatures use the same string-to-string dictionary. `TEmwatMethod` VMT slot `+0x0C` is the shared wrapper at `0x0046C9E0`; it calls `TEmwatMethod.Invoke` (`0x0046C82C`) and then the subclass virtual slot `+0x10`. `Invoke` also has a separate unresolved indirect slot `+0x68` at `0x0046C921`; identify that receiver and method without conflating it with the class's `PerformMethod` slot `+0x10`.
2. **Trace the concrete Word-edit method body.** Run 76 recovered `TEditWordDocument` VMT `0x005ED764`; its slot `+0x10` points to executable target `0x005EE82C`, despite the missing TD32 procedure record. The common VMT slot `+0x0C` (`0x0046C9E0`) calls `TEmwatMethod.Invoke` and then dispatches to the subclass's `+0x10` method. The target `0x005EE82C` reads the `document` parameter and calls helper `0x004B7724`; trace this helper and the complete bounded code range. Keep the TD32 symbol-name mismatch caveat for other connector classes.
3. **Finish the service request-record and input-stream trace.** `TMainForm.IdHTTPServerCommandGet` (`0x0047BF30`) and the XML/class dispatcher at `0x00470D00` are mapped through BPL slot `+0x0C` (`0x0046C9E0`) → `TEmwatMethod.Invoke` (`0x0046C82C`) → subclass slot `+0x10`. The handler's `TEmwatInvokeParam` layout is known, and its `SessionId` is a separate server-generated six-digit string. The object at `[ARequestInfo+0xD4]` is now identified with high confidence as `TIdHTTPRequestInfo.PostStream`; identify the exact stream virtual method names/signatures behind its size/read operations, and trace how the internal `SessionId` is consumed. The numeric browser `invoke` query value is not copied into `SessionId`; only its route-selection role is currently established.
4. **Trace response construction and transport separately.** Connect the method implementation to `EditWordDocument`, `wordConfig`, XML serialization and the local POST response. Do not use the abstract `ParamsToXML` thunk as proof of a concrete serializer, and do not assume `requested-types=application/msword` proves the final file format is DOC.
5. **Keep the Word field/print graph separate from close-time update.** Runs 27–33 resolved `0x004CCBBC` as a nested helper on `Wordxp.Fields`, reached from `BGPrintWithGamPrintOptions → GetFieldIndexInList → FillPrintDocFields`. Its `+0x28)/`+0x38` calls are in the Word Fields collection/field path (high-confidence `Count`/`Item(index)` inferences), not a proven main-document close callback. Run 44 found no exact raw pointer registration for `0x004CCBBC`; the actual close-time update path remains elsewhere.
6. **Retain autosave/close candidates only in their proven scope.** The `uSendLog` callback at `0x005EC580` belongs to the autosave-files UI and calls `CloseWordApp`; its DFM resource does not visibly bind a Word close event. WordXP Close wrappers have no direct TD32 CALL xrefs. Neither is the proven main letter close path.
7. **Resume scanner/image subsystem analysis after the connector path is understood.** Keep image-only letters, TIFF, rotate/crop, multipage processing, ImageGear/ImageEn and GEAR/SANE scanning as first-class requirements. Do not reduce the Linux port to text-only document editing.
8. **Only then implement the native Linux bridge contract and integration tests.** Keep the local service loopback-only, validate origins/tokens/payload sizes/file paths/timeouts, and test synthetic letters and templates with LibreOffice Writer. Do not implement guessed endpoints or claim end-to-end parity before protocol/runtime validation.


## Runtime validation questions

- What exact request/response reaches the local service for a Word document?
- How does service-side virtual slot `+0x0C` reach the BPL connector dispatch, and is the numeric `invoke` query value used beyond route selection?
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
