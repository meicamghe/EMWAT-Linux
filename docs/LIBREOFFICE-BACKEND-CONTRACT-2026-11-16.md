# EMWAT LibreOffice backend — implementation contract and test plan

Date: 2026-11-16  
Scope: Linux replacement backend for the Word-facing part of EMWAT. This is an engineering contract derived from the current static evidence; it is not a claim that a working replacement already exists.

## 1. Objective

Replace the Microsoft Word automation dependency while preserving the observable EMWAT contract used by the Almas Gam web application. The Linux implementation should retain the local service boundary and route document operations to LibreOffice through UNO (or a separately testable office adapter).

The first milestone is protocol compatibility and a deterministic document lifecycle. Pixel-perfect Word layout and every legacy print option are later compatibility milestones.

## 2. Evidence-backed boundaries

| Boundary | Current evidence | Status |
|---|---|---|
| Local service | Local observation: TCP port 1984 returned HTTP 200 | Runtime-observed; exact route/verb still unknown |
| Request envelope | XML root `emwat`, `version`, child `method`, `class`, and `param name` | Static-confirmed parser structure |
| Parameter collection | Parser helper appends a three-value record | Static-confirmed operation; record semantics unknown |
| Method dispatch | `TEmwatMethod.Invoke` accepts `TDictionary<AnsiString,AnsiString>`; concrete request-time dispatch unresolved | Static-confirmed signature; dispatch unresolved |
| Word dependency | TD32 signatures reference `Wordxp._Document`, `Wordxp.Fields`, `Wordxp.Field`, and Word event callbacks | Static-confirmed |
| Request lifetime | Word viewer waits in a message-pumping loop until a state field is cleared by the close/save path; response writer is reached afterwards | Static-confirmed from previously inspected artifacts |
| Response payload | Document metadata/content are collected into dictionaries; exact key names and wire serialization not yet established | Partially known; schema unresolved |

Do not treat the local HTTP observation as a complete endpoint specification. Do not invent the meanings of parser tuple members or response keys.

## 3. Proposed component architecture

### A. Compatibility service

Responsibilities:
- Bind only to the intended loopback interface.
- Reproduce the discovered HTTP behavior after route, method, headers, status codes, and response serialization are captured.
- Parse XML into a typed request object without discarding parameter order or duplicate names until their semantics are known.
- Keep a request alive while the document-editing session is active.
- Return the response only at the same lifecycle point as the original client expects.

Implementation rule: transport and XML parsing must be independent from LibreOffice so protocol tests can run without an office process.

### B. Method registry and dispatcher

Responsibilities:
- Map the XML `class` identifier to a handler.
- Preserve the string key/value parameter contract where evidence confirms it.
- Reject unknown methods with a captured-compatible error once the original error contract is known.
- Keep a trace ID and structured, redacted logs for each request.

Do not hard-code guessed class names or assume every BPL class uses the same response format. The inherited method list is evidence for candidate handlers, not proof of the complete dispatch table.

### C. Office adapter

Define a small backend-neutral interface:

- `open_or_create(request, template)`
- `read_field(anchor)`
- `write_text(anchor, value)`
- `write_image(anchor, image)`
- `read_custom_properties()`
- `write_custom_properties(properties)`
- `save()`
- `prepare_print(options)`
- `print(options)`
- `close()`

The LibreOffice implementation should use UNO. Keep all UNO-specific types behind this adapter so a fake backend can drive protocol and lifecycle tests.

### D. Document mapping layer

The original code has separate routines for XML field metadata, field-name resolution, text/value mutation, image fields, and custom document properties. The replacement therefore needs a mapping layer rather than blind text replacement.

Candidate LibreOffice primitives to evaluate:
- bookmarks and named ranges for stable text anchors;
- Writer fields and user-defined fields for dynamic values;
- document custom properties for metadata;
- embedded graphics or image anchors for image fields.

These are candidate implementation mechanisms only. The original mapping rules and exact Word field types have not yet been recovered. The mapping layer must be driven by captured EMWAT templates and sanitized request fixtures.

### E. Lifecycle coordinator

Model the editing session explicitly:

`RECEIVED → PARSED → DISPATCHED → DOCUMENT_OPEN → EDITING → SAVING → CLOSED → RESPONSE_READY`

The state machine must support:
- normal save and close;
- close without an explicit save;
- user cancellation / close veto if the original protocol requires it;
- timeout/disconnect cleanup;
- office process crash and stale-session recovery;
- duplicate close/save notifications without duplicate responses.

The original implementation's periodic timer/message-pump loop is not a one-second timeout. It repeats until the viewer state is cleared. The Linux implementation should use an event-driven wait, not reproduce a busy polling loop.

## 4. Compatibility matrix

| Original behavior | Linux implementation target | Required evidence before claiming parity |
|---|---|---|
| Open Word document/template | UNO Writer load/create | Sanitized template + equivalent visible document |
| Resolve EMWAT XML fields | Mapping layer over bookmarks/fields | Field-name and XML-to-anchor examples |
| Fill text fields | UNO text/field update | Before/after document comparison |
| Fill image fields | UNO graphic insertion/replacement | Sanitized image-field fixture |
| Read field values back | UNO extraction | Exact response key/value capture |
| Read custom properties | UNO document properties | Original property names and value types |
| Auto-save / periodic sync | Lifecycle coordinator + timer/event | Captured timing and state transitions |
| BeforeSave / BeforeClose | UNO document event listeners | Original cancel/save semantics and callback order |
| Delayed HTTP response | Pending request completed after close/registration | Captured request/response pair |
| Print preparation | Dedicated print transformation | Original print field substitutions/options |
| Background print | Print job abstraction | Original behavior and completion semantics |
| Protect/restore document options | Scoped document-state snapshot | Original option list and restoration rules |

## 5. Test strategy

### Layer 1 — parser tests (no office dependency)
- valid minimal XML envelope;
- missing root/version/method/class;
- zero, one, and multiple parameters;
- empty values, Unicode Persian text, XML special characters;
- duplicate parameter names (preserve until original behavior is known);
- malformed XML and oversized payloads.

Expected results must be filled from captured Windows behavior. Until then, tests should assert parser structure only, not guessed HTTP status codes or error text.

### Layer 2 — dispatcher tests (fake office adapter)
- known and unknown method identifiers;
- missing required parameter;
- parameter round-trip without Unicode corruption;
- handler exception and cleanup;
- idempotent close and one-response-only guarantee.

### Layer 3 — document adapter tests (LibreOffice)
- open DOCX template;
- find and update a named anchor;
- update text and image fields;
- read back values;
- preserve custom properties;
- save, close, and reopen;
- compare extracted text, field values, and metadata.

### Layer 4 — lifecycle/integration tests
- request remains pending while user edits;
- save without closing;
- close after save;
- close without explicit save;
- cancel close if supported by the original contract;
- office crash while request is pending;
- client disconnect and cleanup;
- ensure exactly one HTTP response is emitted.

### Layer 5 — end-to-end parity
Run the same sanitized request/template through Windows EMWAT+Word and Linux EMWAT+LibreOffice. Compare:
1. HTTP status/headers/body;
2. extracted document text and field values;
3. custom properties;
4. document lifecycle events;
5. print output and page count.

Use semantic comparisons first; binary DOCX equality is not a valid parity criterion because office applications may rewrite package metadata and XML ordering.

## 6. Immediate blockers and evidence requests

The next high-value inputs are:
1. the exact `EmwatMethods.bpl1` used for the current TD32 traces;
2. sanitized request XML captured from the browser-to-local-service exchange;
3. the matching HTTP response after document close;
4. a blank/sanitized DOCX template containing representative EMWAT fields;
5. a screen recording or event log for save, close, cancel, and print behavior.

Do not commit customer letters, signatures, authentication tokens, cookies, or unredacted packet captures to the public repository. Keep private fixtures outside Git and publish only synthetic/redacted test cases.

## 7. Exit criteria for the first usable Linux prototype

The first prototype is ready for controlled testing only when:
- it accepts a captured request envelope;
- it opens a sanitized template in LibreOffice;
- it fills at least one text field and one image field using verified mappings;
- it keeps the originating request pending while the document is edited;
- it returns a captured-compatible response after the expected close/save event;
- it can reopen the saved document and verify the filled content;
- parser, dispatcher, and lifecycle tests pass without a live Word installation.

Until those conditions are met, describe the project as a reverse-engineering and compatibility implementation in progress, not as a working EMWAT replacement.
