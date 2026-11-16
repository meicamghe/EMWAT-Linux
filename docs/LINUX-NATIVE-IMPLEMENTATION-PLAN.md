# Native Linux implementation plan — parallel workstreams

Status date: 2026-11-15

This plan turns confirmed Windows behavior into independent Linux implementation tracks. It separates verified compatibility requirements from unknown protocol details. It is an implementation plan, not a claim that the native service is already complete.

## Product invariants supported by current evidence

1. EMWAT is a local bridge between the Almas Gam web application and desktop document workflows.
2. The Windows service listens on loopback, with port 1984 as the observed/default port.
3. The browser-side bridge sends message payloads with HTTP POST to /?invoke=<value>; the Agent uses /?heartbeat.
4. Runtime observations include UTF-8 text/plain request bodies and XML responses for at least one close-time invoke. The complete request/response contract is not yet known.
5. Closing Word is sufficient for the letter to be registered/returned to Almas Gam even when the user does not press Save. This is a product requirement; it does not prove that the underlying Word document was never saved.
6. A native Linux implementation is required. Wine is a reverse-engineering/compatibility aid, not the product runtime.
7. LibreOffice Writer is the primary candidate document engine, but each Word behavior needs an adapter and regression test.
8. Printing and scanning are distinct subsystems. Windows printer kernel drivers cannot be reused as Linux drivers; native CUPS/IPP and SANE-facing paths must be evaluated separately.

## Parallel workstreams

### A. Local bridge and protocol compatibility

Deliverables:
- Loopback-only HTTP service.
- Compatibility endpoints for heartbeat, initialization, and invoke.
- Request-size limits, timeouts, structured logs, and correlation IDs.
- XML envelope parsing/serialization with UTF-8 handling.
- Origin/Host validation and a local anti-CSRF strategy suitable for browser-to-loopback communication.

Rules:
- Preserve observed paths and methods where supported by evidence.
- Do not hard-code observed invoke values such as 5208 or 58351 as method IDs.
- Do not invent missing XML elements or decode opaque payloads by guesswork.
- Keep protocol parsing separate from document-engine logic.

Acceptance tests:
- Heartbeat returns a deterministic liveness response.
- Initialization and invoke can be exercised from saved, anonymized fixtures.
- Malformed XML, oversized bodies, unsupported methods, and port conflicts fail predictably.
- A close-time response can be correlated to the correct open document session.

### B. Document lifecycle and LibreOffice adapter

Deliverables:
- A document-session state machine.
- A LibreOffice UNO adapter behind a stable internal interface.
- Field mapping for subject, letter number, signatories, recipients, layout, and editable body fields as protocol evidence permits.
- Explicit close/finalize behavior that returns the final document even if the user did not click Save.

Initial state model:
created → initializing → opened → dirty → finalizing → returned
with failure/cancel branches from each operation where appropriate.

Important distinction:
- User Save, engine save, EMWAT silent-save, and close-time return are separate events.
- A Ctrl+S operation did not produce a new invoke in one captured runtime trace; closing did. Therefore, do not implement “Save button = upload” as an assumption.
- The finalization contract must be idempotent so duplicate close notifications cannot upload inconsistent versions.

Acceptance tests:
- Open, edit, explicit save, close without explicit save, cancel, and application crash/recovery scenarios.
- Verify the exact bytes returned after each supported close path.
- Preserve the source document and avoid lossy conversion unless the negotiated output format requires it.

### C. Recovery and Word Automation compatibility

Deliverables:
- A recovery-session abstraction independent of Windows COM.
- An adapter for enumerating, selecting, restoring, and removing recovery entries once their actual storage contract is identified.
- A typed mapping for Word Automation operations, including generic dispatch calls whose DISPID/arguments remain unresolved.

Current evidence boundary:
- The Windows recovery form uses a shared interface helper and COM/Automation dispatch.
- The helper at 0x0043EAB8 appears across recovery, background printing, and unprotect workflows.
- The recovery list's exact persistence format, directory, and extensions remain unknown. Do not assume .asd or .wbk.

Acceptance tests:
- Recovery metadata can be listed without launching the office suite.
- Restoring an entry does not delete it until the restore is confirmed.
- Deletion and cleanup are transactional and recoverable after interruption.

### D. Printing and scanning adapters

Printing:
- Native CUPS/IPP printer discovery and selection.
- A print-options model for recipients, copies, page range, and background/GAM print behavior.
- Keep the original Windows printer-driver integration out of the Linux process.

Scanning and images:
- Separate scanner discovery/capture from image editing and document insertion.
- SANE is the native scanner integration candidate.
- Preserve confirmed image operations (crop, rotate, flip, page handling, and output encoding) through a backend-neutral interface.

Acceptance tests:
- Print to a virtual CUPS queue and verify page range/copy settings.
- Scan to a test backend and verify page ordering, rotation, and encoded output.
- Test multi-page image workflows independently of Word/Writer.

## Shared internal interfaces

The first implementation should expose these boundaries before Windows-specific protocol details are filled in:

- BridgeTransport: HTTP lifecycle, request parsing, response writing.
- ProtocolCodec: XML/text envelope parsing and serialization.
- DocumentSessionManager: session identity, state transitions, close/finalize.
- OfficeAdapter: open, inspect fields, save, export, close.
- RecoveryStore: list, restore, remove, and retain recovery entries.
- PrintBackend: discover printers and submit configured jobs.
- ScanBackend: discover devices and capture pages.
- AuditLog: structured events with secrets and letter content redacted.

No module should depend directly on LibreOffice UNO from the HTTP layer.

## Integration order

1. Build protocol fixtures and a loopback service skeleton.
2. Build the document-session state machine and fake OfficeAdapter tests in parallel.
3. Implement the LibreOffice adapter against the stable OfficeAdapter interface.
4. Add recovery and print/scan backends as separate modules.
5. Connect the actual protocol only as each field and transition becomes evidenced.
6. Run end-to-end tests against anonymized request/response fixtures before attempting Almas Gam integration.

## Evidence and uncertainty policy

Every behavior must be labeled as Confirmed, Strongly inferred, or Unknown. Unknown protocol values must remain configurable or isolated behind adapters. Guesses must not silently become compatibility requirements.


## Implementation progress (2026-11-15)

The first two workstreams now have concrete code in the repository:

- **Bridge transport:** GET /?heartbeat returns HTTP 200 with body `TickTack`, matching the captured Agent exchange. GET /?init=<digits>_<digits> returns the capture-matched initialization script after validating the parent-page Referer against a separate allowlist. `/healthz` remains a separate development health check.
- **Document lifecycle:** python/src/emwat_linux/sessions.py introduces an office-engine-independent state machine with explicit initialization, opened/dirty, engine-save, finalizing, returned, failed, and cancelled states.
- **Close semantics:** the state machine deliberately permits finalization and return without an explicit engine-save event, reflecting the confirmed user-visible close-without-Save requirement.
- **Idempotency:** duplicate finalization requests are ignored while finalizing/returned; an identical returned payload is accepted as a no-op, while a conflicting second payload is rejected.
- **Tests added:** python/tests/test_sessions.py and an additional heartbeat test in python/tests/test_bridge.py. These commits have been written to the repository; a fresh CI result for these newest commits has not yet been verified.

Still not implemented: application registration of the EditWordDocument handler, a real LibreOffice UNO adapter, recovery store, and CUPS/SANE backends. The dispatcher handler factory now exists, but requires an explicit cancellation response policy and a real OfficeAdapter before production registration. The production deployment must supply the actual Almas parent-page and loopback Origin allowlists.


## Close-driven office adapter boundary — 2026-11-15

A new, engine-independent orchestration layer has been added in parallel with the SevenZip recovery analysis:

- `python/src/emwat_linux/office_adapter.py` defines the OfficeAdapter protocol and normalized close outcomes (`CLOSED` / `CANCELLED`). It contains no UNO or COM implementation.
- `python/src/emwat_linux/document_coordinator.py` sequences open → wait for close → export final bytes, using the existing DocumentSession state machine.
- The coordinator deliberately waits for the close event rather than treating Save as the return trigger. This matches the observed product requirement and the captured long-lived HTTP exchange, without claiming the exact Windows callback has been mapped.
- The local session identifier is supplied independently; the `invoke` query value is not reused because it is a per-request nonce.
- Fake-adapter tests cover close without explicit Save, cancellation without export, adapter failure sanitization, and invalid output bytes.

Python bridge workflow run `43720329600` completed successfully with 66 tests. The coordinator and service tests are CI-verified. No production HTTP handler or LibreOffice implementation is connected yet.


### Request-to-session domain service — 2026-11-15

- `python/src/emwat_linux/editword_service.py` now joins the existing outer method parser, EditWordDocument request normalizer, and DocumentCoordinator.
- It generates an independent local session ID with a cryptographically random token by default. It deliberately does not reuse the `invoke` query nonce.
- The OfficeAdapter contract now receives separate `on_modified` and `on_saved` callbacks. A modification marks the session dirty; an engine save only records the saved revision. Neither callback completes the bridge response: only the close event advances to final export.
- The coordinator exports the final bytes after a normal close, including when no engine-save callback occurred. A cancelled close returns a domain-level cancelled result without exporting bytes.
- The latest Python CI run `43719841339` passed **66 tests** (4.44 seconds). This verifies the parser-to-domain-service-to-fake-office path only; cancellation/error HTTP response semantics remain intentionally unimplemented until captured.


- The coordinator now ignores office modification/save notifications fired during document initialization; only events after the session is marked OPENED can change revision/save state. This avoids treating config/field population as user edits. Run `43720329600` passed all 66 tests after this guard was added.


### Dispatcher handler adapter — 2026-11-15

- Added `python/src/emwat_linux/editword_handler.py` to connect `EditWordDocumentService` to the XML dispatcher contract.
- Successful close responses use the observed `response-word` Base64 serializer and the captured Word MIME envelope.
- Cancellation response generation is injected and mandatory; no HTTP status/body is invented because the original cancellation envelope has not been captured.
- The factory is not yet registered in the application and must not be treated as production-ready until a real LibreOffice adapter and explicit cancellation policy are provided.
- Python bridge CI run `43721449170` passed **69 tests**.


- OfficeAdapter protocol documentation now explicitly requires per-document handle isolation and concurrent-session safety, matching the threaded bridge. CI run `43721449170` passed 69 tests.


### Close callback race hardening — 2026-11-15

- `DocumentCoordinator` now protects office callbacks with an `RLock`. After `wait_for_close` returns, it waits for any in-flight callback and disables modification/save notifications before final export.
- Delayed callbacks during export or after a returned/cancelled session are ignored, rather than attempting an invalid state transition. Adapter failure also disables callbacks before propagating a sanitized coordination error.
- Regression coverage invokes late callbacks during export and after return. Python bridge CI run `43722184809` passed **70 tests**. This validates the orchestration against fake adapters; no live LibreOffice UNO integration is claimed.

### SevenZip interface mapping in parallel

- The recovery plugin analysis now resolves Delphi VMT slots and interface tables for `T7zArchive`, `T7zPlugin`, `T7zInArchive`, and `T7zOutArchive`, including SevenZip archive/stream interface RTTI.
- The purpose is to map the interface returned by `CreateOutArchive` to the `euResetMemory` dispatches. The mapping is still open until artifact `SevenZip-interface-tables.md` is inspected; do not promote the current `SetPassword → OpenFile → ExtractTo` sequence beyond a strong hypothesis.


- Follow-up review fixed the cancellation branch too: office callbacks are now detached immediately after `wait_for_close`, before checking whether the result is `CLOSED` or `CANCELLED`. Late callbacks after cancellation are covered by a regression test. CI run `43722805637` passed **71 tests**.


### LibreOffice UNO adapter — 2026-11-16

A first concrete UNO-backed office adapter is now present at `python/src/emwat_linux/libreoffice_adapter.py`:

- Launches a separate LibreOffice process and private user profile per document session, with a dedicated loopback UNO socket.
- Recognizes the observed OLE Compound File Word payload as legacy `.doc`, and also recognizes ZIP-based `.docx` input.
- Opens the document visibly for normal use; a headless mode exists only for automated integration testing.
- Registers document modification, save-completion, and close listeners.
- On the UNO close callback, writes a separate `MS Word 97` snapshot without changing the source document URL; after the close notification, the coordinator can return those bytes through the already-tested response serializer.
- Keeps the original request's field configuration and signData opaque. No EMWAT field-to-Writer mapping is claimed yet.

A dedicated `.github/workflows/libreoffice-integration.yml` installs LibreOffice Writer and distro `python3-uno`, then runs a real generated-DOCX → UNO open → close → legacy-DOC export roundtrip. **Verified:** integration run `43810188525` passed all 8 adapter tests, including the real LibreOffice roundtrip. The Python bridge workflow also passed on the same implementation commit `63ae7210110720535f8b02ca27d91542a9efc972`.

Known limitations:
- This verifies the LibreOffice document-engine boundary, not Almas Gam end-to-end registration.
- The Windows-specific EMWAT field mapping, sign insertion, image layout, and exact cancellation response remain unresolved.
- Close-listener snapshot behavior passed the current live UNO integration fixture. It still needs validation against an actual captured EMWAT `.doc` payload and interactive desktop close/save/cancel flows.
- The adapter currently expects the system Python interpreter to have the distro `python3-uno` module available.


### Live UNO verification checkpoint — 2026-11-16

- LibreOffice integration run: `43810188525` — **success**, 8 tests passed.
- The test installed LibreOffice Writer + `python3-uno`, launched an isolated headless Writer process over a private loopback UNO socket, opened a generated DOCX fixture, closed it through UNO, and verified the close listener produced a legacy Word CFB `.doc` snapshot.
- Python bridge run: `43810188517` — **success**.
- This is a real engine roundtrip, not a fake adapter test. It does not yet prove fidelity for the captured EMWAT template, Persian fields, embedded images, signData, or Almas registration.


### Field decoding and Writer structure inventory — 2026-11-16

- `python/src/emwat_linux/word_fields.py` now decodes each field using its own declared `encryption`: URL-encoded values become UTF-8 text, Base64 values become bytes, and fields without an encoding remain unchanged.
- Optional-attribute content is decoded using its nested content metadata. Unknown encodings fail closed.
- Fields declaring `paramId` (including the observed external `signData` binding) are identified separately. The code deliberately does not split/concatenate signData until the `separator` / `concater` semantics are validated.
- `python/src/emwat_linux/writer_inspector.py` inventories Writer bookmarks, named ranges, sections, tables, frames, graphic objects, document indexes, and text-field implementation/property metadata. It does not read or log letter text or field values.
- The adapter exposes this inventory through `LibreOfficeAdapter.inspect_document(handle)`. The live UNO test now checks a bookmark imported from a DOCX fixture.
- The inventory is groundwork for mapping the 180 known EMWAT field IDs to actual template structures. No field-to-bookmark mapping is hard-coded yet; the original template's structure still needs to be inspected.


### Packaged installer asset check — 2026-11-16

The metadata-only inventory workflow `43810767154` inspected the tracked `EMWAT_Extracted.zip` and found no Word-family files (`.doc`, `.docx`, `.dot`, `.dotx`, `.dotm`, or `.rtf`). Consequently, the original EMWAT Word template is not available in the current extracted installer archive.

The Windows binary analysis indicates that the original application actively enumerates the Word `Fields` collection, resolves XML field metadata, and has separate text/image field paths. The Linux mapping therefore must inspect more than bookmarks: Writer text fields, named ranges, bookmarks, content controls imported from OOXML, frames, and graphics all remain candidates. The current Writer inspector inventories these structures, but a representative anonymized Almas letter/template is still required to establish the actual mapping and visual fidelity.


## Implementation status correction — 2026-11-16

The earlier roadmap sections above are historical snapshots. The following components have since been implemented and CI-verified:

- A concrete LibreOffice UNO adapter exists in `python/src/emwat_linux/libreoffice_adapter.py`, including isolated process/profile setup, DOC/DOCX container recognition, modification/save/close listeners, legacy DOC export, process reaping, metadata-only Writer inventory, custom-property batch updates, and one-time Writer text-field refresh.
- The `EditWordDocument` request parser, close-driven coordinator, response handler, and composition function `create_libreoffice_bridge_server` are present. The cancellation response factory remains explicitly injected because the exact native cancel envelope is unknown.
- Python bridge CI reached **101 tests run, 100 passed, 1 optional UNO test skipped** (run `43820250444`). The UNO integration workflow reached **10 passing tests**, including a live DOCX → Writer → legacy DOC roundtrip and child-process cleanup (run `43818676967`).
- Word field decoding, twin identifier parsing, DOCPROPERTY field-code extraction, custom-property inventory/update, and structural Writer inspection are implemented. They intentionally do not invent the mapping of the 180 request IDs to actual Almas template structures.

### Remaining implementation blockers

1. **Close-choice parity:** Native Word BeforeSave prompts Yes/No/Cancel. The current UNO close listener snapshots on close but does not yet reproduce this three-way decision. The No and Cancel HTTP outcomes are not fully captured; do not return changed content on an unverified branch.
2. **Field/template mapping:** the installer archive contains no Word-family template. A representative anonymized Almas DOC/DOCX template is required before mapping the 180 field IDs, twin fields, image anchors, and visual formatting.
3. **signData:** its raw XML attributes and external parameter binding are preserved, but separator/concator behavior and the canonical attribute spelling in a live request must be verified before joining or inserting signatures.
4. **Controller/HTTP handoff:** controller notification and paired `.easd/.easz` archive paths are being traced independently. Neither should be labeled the final Almas registration response until the payload and response chain are proven.
5. **Deployment wiring:** the composition root is available, but production Origin allowlists, explicit cancellation response policy, and a real user-facing close-decision policy still need to be configured and tested.

A new parallel workflow, `.github/workflows/analyze-word-controller-callback-ownership.yml`, is now tracing the viewer constructor/destructor, timer callbacks, controller dispatch, and print-handler ownership (run `43821043328` was in progress at the last check).
