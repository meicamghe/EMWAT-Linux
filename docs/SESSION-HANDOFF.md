# EMWAT-Linux — Project Handoff

Last reviewed: 2026-11-13

This is the concise continuity entry point for future sessions. Detailed reverse-engineering evidence remains in the linked analysis documents.

## Product goal — fixed

Rebuild EMWAT as a **native Linux application** while preserving the real Windows product's workflows. Running the Windows EMWAT build under Wine is not the target product.

The confirmed real-world workflow is a local desktop bridge for the Almas Gam web-based office automation system: data and letter templates are prepared in the web system, EMWAT opens Word for editing, and the resulting document is returned to the same system. Some letters are image-only, so scanning and image-document workflows remain in scope.

## Confirmed user observations and constraints

- The user tested the Windows application's close/save behavior and reported that changes are applied when the document is closed, regardless of whether the user explicitly presses Save. Treat this as an observed behavior to reproduce and verify, not as proof of the exact internal event or transport mechanism.
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

## Immediate next steps — in order

1. Continue from the latest `PROJECT-STATUS.md` checkpoint. Do not redo completed Import Table analysis, Office/COM confirmation, or the three DFM decodes.
2. Validate the questionable `IG_scan_source_select` thunk/callsite at raw PE/IAT level; keep earlier uncertain caller attributions untrusted until proven.
3. Continue extracting scanner interface/VMT callback contracts and identify the exact GEAR32PD version/prototypes before assigning meaning to ABI arguments or flags.
4. Trace `doCommand` and the relevant image-editor tags/handlers in `EmwatMethods.bpl1`; connect UI events to actual image operations.
5. In parallel, prioritize the browser bridge invoke dispatch: map methods to connector classes, payload fields, response envelope and file transfer.
6. Obtain a safe runtime trace using synthetic letter data in the real Almas Gam workflow. Redact names, letter numbers, text, tokens, cookies and private URLs.
7. Build a mock end-to-end text-letter flow with a controlled document, LibreOffice Writer and a simulated response. Only connect to the live system after the contract is understood.
8. Write a testable specification before implementing native Linux scan/image parity.

## Runtime validation questions

- What exact request/response reaches the local service for a Word document?
- Which invoke method dispatches to which connector?
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
