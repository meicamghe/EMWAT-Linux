# Almas Live End-to-End Acceptance Gate

## Purpose

This document defines the evidence required before calling the Linux implementation
compatible with the real Almas application or producing a release package. The
critical workflow is:

1. Almas invokes `EditWordDocument` through its local EMWAT bridge.
2. LibreOffice Writer opens the document supplied by Almas.
3. The user edits and chooses a close/save action.
4. The bridge returns the correct document response to the same Almas request.
5. Almas accepts and persists the returned document.

A standalone Writer open/save test is not an Almas end-to-end acceptance test.

## Implemented locally (not yet live-Almas verified)

- The HTTP bridge binds only to IPv4 loopback and validates Host, Origin,
  request size, and the numeric `invoke` query parameter.
- The captured heartbeat route returns `TickTack`; the init route validates
  the parent-page Referer against an explicit allowlist.
- The XML method parser recognizes the recovered `emwat/method/param`
  envelope and rejects duplicate or malformed parameters.
- `EditWordDocument` parsing decodes the captured Base64 `wordConfig` and
  `wordBody` values and preserves `signData` as opaque text.
- The LibreOffice adapter opens the legacy OLE/CFB `.doc` input, tracks
  confirmed saves, waits for an accepted close, and exports the final CFB
  document.
- The successful response serializer emits the implemented
  `response-word status="success"` envelope with
  `application/msword` / Base64 content.
- Local tests cover the HTTP bridge, method dispatch, response serialization,
  synthetic LibreOffice round-trip, and close lifecycle.
- Save/Discard/Cancel behavior was exercised locally with Writer. Those tests
  do not establish that Almas accepts or persists the returned bytes.

## Close semantics that must remain distinct

| Writer / operation outcome | Required local behavior | Almas response status |
| --- | --- | --- |
| Save, then close | Return the latest confirmed saved document | Successful response envelope is implemented; live acceptance pending |
| Don't Save, then close | Return the last confirmed saved state (the original input if no save occurred) | Same successful response path; live acceptance pending |
| Cancel the close prompt | Keep Writer open and keep the original HTTP request pending | No response until a later terminal close |
| Explicit operation-level discard | Do not export a document | Exact Windows response envelope is not yet recovered |

A close-prompt Cancel is a vetoed close attempt, not a terminal Cancel result.
The implementation must not return an unsaved live snapshot after a veto or
after a Don't Save choice.

## Release blockers

1. **Deployment origin verification:** the captured Windows exchange establishes
   XHR Origin and init Referer origin as `http://127.0.0.1:1984`. Configure
   both separate allowlists with this exact loopback origin for the captured
   deployment. Confirm only if the target Almas deployment behaves differently;
   do not guess an external hostname.
2. **Complete response bytes:** the PCAP establishes the successful request
   and response metadata, XML envelope, MIME type, and legacy DOC/CFB payload.
   The response capture has 17 TCP gaps / 68 missing payload bytes, so a
   gap-free full response or a live successful round-trip is still needed for
   byte-for-byte validation.
3. **Non-success response policy:** the application composition root requires
   an injected response factory for an explicit operation-level discard.
   Writer's Don't Save and close-prompt Cancel are separate, already modeled
   outcomes. The exact Windows wire response for explicit operation-level
   discard is not established; use a fail-closed local policy and do not claim
   Windows parity for it.
4. **Desktop bootstrap:** the work branch now implements the normal GTK
   entry-point composition in `python/src/emwat_linux/deployment.py` and
   `gtk_desktop.py`, including the captured loopback-only bind and Origin /
   Referer allowlists. This is implementation evidence, not live deployment
   acceptance; verify dependency failure, port conflict, start/stop, and the
   real Almas browser workflow before release.
5. **Almas persistence:** no test has yet shown that the real Almas application
   receives, accepts, and persists the returned edited document from Linux.
6. **In-flight shutdown acceptance and test result:** the bridge now tracks
   accepted workers and performs bounded drain before closing the socket.
   The worker-count registration race was corrected. Run 67's Python step was
   cancelled; a new PR CI cycle is in progress on the isolated work branch.
   A GTK smoke run exposed a failure-message ordering bug in the close retry
   path; the fix is committed and the GTK workflow is being rerun. Live Almas
   shutdown behavior and forced process termination remain unverified.
7. **WordConfig/signature parity:** controlled Writer text/image update APIs
   and inline Base64 image inventory exist, but no automatic field map is
   enabled. The outer `letterImages` payload is TIFF/preview-side; `signData`
   remains opaque and its field schema is unresolved. Complete only mappings
   exercised by the live acceptance fixture.

## Required live acceptance procedure

Use a non-production/test Almas account and a disposable document. Record
timestamps and HTTP metadata, but redact credentials, cookies, personal data,
and document contents before sharing artifacts.

1. Use the existing sanitized PCAP fixture as the baseline: POST path/query,
   numeric invoke nonce, loopback Origin/Referer, Content-Type, parameter
   names, and successful response-word envelope are documented. Confirm the
   target Almas deployment uses the same loopback behavior.
2. If byte-for-byte parity is required, obtain a gap-free Windows response
   capture; otherwise validate the complete Linux response through a live
   Almas round-trip and preserve only sanitized metadata.
3. Configure the two explicit loopback allowlists separately and start the
   Linux bridge on 127.0.0.1 only.
4. Open the same document from Almas. Confirm Writer opens the expected
   document and that the Almas request remains pending while Writer is open.
5. Add a unique harmless marker, save, close Writer, and verify Almas completes
   the operation. Reopen the document in Almas and verify the marker persisted.
6. Repeat with a second marker and choose Don't Save. Verify the unsaved marker
   is absent from the document returned/persisted by Almas.
7. Repeat and choose Cancel at the Writer close prompt. Verify Writer remains
   open and Almas does not prematurely complete the request. Then make a
   terminal close choice and verify the request completes exactly once.
8. Capture the explicit operation-level discard path only if the real Almas
   workflow exposes it; compare its Windows response before enabling it on
   Linux.
9. Repeat the accepted workflow after restarting the desktop application and
   after rebooting the test machine.
10. While a real EditWordDocument request is pending, attempt to quit the
    EMWAT desktop application. Verify the chosen drain/cancel behavior, that
    Almas receives no false success, and that no Writer/soffice process or
    temporary session is orphaned.

## Release decision

The Linux release gate passes only when steps 1–8 applicable to the real Almas
workflow pass against the Linux implementation, the exact origins and response
contract are recorded, and the normal desktop entry point starts/stops the
configured bridge reliably. Until then, the project remains an integration
candidate, not a verified Almas-compatible release.


## Run 67 static-analysis boundary — Word viewer is not the Almas edit handler

The Run-67 `word-print-com` artifact shows `TWordViwer.LoadDocument` calls `TCreateTiff.SeparteImages` at `0x004B7A9C` and `0x004B7ABD`. Run 46 cross-checked this with the earlier direct VMT/interface map and **confirmed** that the handler at `0x005EE82C` is the concrete `TEditWordDocument.PerformMethod`, despite its stale TD32 label `TScanDocument.PerformMethod`. This handler invokes the WordViewer loader. The static EditWordDocument dispatch identity is therefore closed; the remaining live gate is Almas persistence through LibreOffice.


## Run 67 VMT scan — handler class names exist but standard VMT resolution fails

The Run-67 generic `resolve_delphi_vmt_slots.py` artifact reported no standard-layout candidate for these classes and one unverified `TWordViwer` candidate. This was a **false negative of that generic heuristic**, not absence of a VMT. Run 46 supersedes this observation with the direct VMT/interface crosswalk: `TEditWordDocument` VMT `0x005ED764`, parent `TEmwatMethod`, concrete slot `+0x10 -> 0x005EE82C`. Do not use the generic resolver's no-candidate result to override the direct VMT evidence.


## Run 67/46 — confirmed EditWordDocument handler data flow

Run 46's direct VMT map confirms that procedure `0x005EE82C`, decorated by stale TD32 as `TScanDocument.PerformMethod`, is the concrete `TEditWordDocument.PerformMethod`. Its actual dictionary data flow is:

- `wordConfig` (`0x005EE9F4`) is required; if absent, it raises the message `Requset XML is not valid (wordConfig parameter is null)` (`0x005EEA0C`).
- `wordBody` (`0x005EEA88`) is looked up and an empty value is initialized when absent/empty.
- `letterImages` (`0x005EEAA0`) and `signData` (`0x005EEABC`) are also looked up; the shared lookup helper zero-initializes its output, so missing values default to empty strings.
- The method calls `TWordViwer.LoadDocument` at `0x004B7724` (`0x005EE961` callsite), then adds its returned string to the output collection.

This is the best-supported static data-flow candidate for the EditWordDocument route, because it consumes the Word-specific request keys and enters the WordViewer loader. Its TD32 class name `TScanDocument` is not accepted as the actual external method name without registration evidence. The separate `TFaxDocument`-labelled procedure at `0x005EEB48` consumes `document` and calls the scanner command's `GetNextPage`, which is consistent with an actual ScanDocument path and demonstrates the label mismatch.

**Linux implementation gap:** `editword_request.py` decodes `wordConfig`/`wordBody`, preserves `signData` as text, and retains `letterImages` in `extra_parameters`. Stage-A inventory already decodes inline Base64 `image/*` WordConfig fields, identifies signer slots and external `paramId` references, and exposes controlled Writer image/text update APIs. Those update APIs require explicit evidence-backed target maps and are not automatically invoked during open. The outer `letterImages` parameter is not yet resolved against `paramId`/separator/`concater` metadata, and `signData` remains opaque and unapplied. `TWordViwer.AddImagesToDoc` at `0x004C0410` confirms the native Word field path routes `image/*` fields, but the exact external-parameter binding and call relation still need proof. Thus the basic open/edit/save lifecycle exists, and controlled inline-image machinery exists, but full Almas parity for external images, signatures, and field substitutions is not established.


## Run 67 — required/optional request-key correction

The full `0x005EE82C` procedure proves the outer request-key requirements more precisely:

- `wordConfig` is the only key explicitly checked as required; absence raises the WordConfig-null error.
- `wordBody` is looked up conditionally. If absent, its initialized empty string is retained and passed to `TWordViwer.LoadDocument`; it is not rejected by this handler.
- `letterImages` and `signData` are looked up into initialized strings, and the TryGetValue Boolean is ignored, so absent keys remain empty.
- The loader call at `0x005EE961` receives `wordConfig`, `wordBody`, `letterImages`, and `signData` (plus the handler's output/owner arguments).

**Success-path requirement:** although the connector handler's dictionary lookup does not explicitly reject a missing `wordBody`, the full `TWordViwer.LoadDocument` trace decodes it and checks the decoded length at `0x004B77AB–0x004B77B5`; an empty result enters an error path. Therefore the Linux parser's non-empty Base64 body requirement matches the native successful-load path. The remaining mismatch is error timing/response semantics for missing or empty bodies, not support for successful body-less document creation. Do not add blank-document creation without evidence of a successful native empty-body branch. The current Writer adapter cannot safely open an empty payload as a document.


## Run 44 — request argument routing inside TWordViwer.LoadDocument

The complete Run-50 skipdata trace narrows the three non-config inputs:

- `wordBody` is passed through helper `0x00457050` and `0x00454B9C`, stored as a decoded string, checked for non-zero length, and used to construct the temporary source stream/file before WordViewer proceeds. This supports the Linux parser's non-empty decoded-body requirement for successful opens.
- `letterImages` is passed as EDX to `TCreateTiff.SeparteImages` at `0x004B7A9C` / `0x004B7ABD`. Its currently proven consumer is therefore the print-to-TIFF/preview side, not the basic Word body open/save path. This can remain deferred while TIFF is out of scope.
- `signData` is passed as an additional argument and is subsequently used in XML-node/interface operations around `0x004B7AEB–0x004B7B2F`. It is not safe to discard, but its exact schema and effect on Writer fields are still unresolved.

This refines the parity priorities: preserve `signData` and recover its mapping before claiming signature parity; do not block the basic Word edit/save milestone solely on `letterImages`/TIFF generation, provided the real Almas acceptance fixture does not require those preview artifacts.


## Run 45 — WordViewer call ABI and result hand-off

The caller at `0x005EE961` and full loader prologue/epilogue establish the call ABI despite the stale TD32 signature:

- EAX = `wordConfig`
- EDX = `wordBody`
- ECX = `letterImages`
- stack arg 1 = output-string pointer (callee `[EBP+8]`)
- stack arg 2 = handler field `[self+4]`
- stack arg 3 = `signData` (callee `[EBP+0x10]`)

The loader returns with `ret 0xC`, confirming three stack arguments. It writes/obtains a UnicodeString result through the out pointer at `[EBP+8]`; the handler then forwards that string to its output collection at `0x005EE970` and sets a completion byte at `0x005EE988`. The exact semantic of the returned string (updated document body versus another serialized result) and the output collection key are not proven without the response XML/wire fixture.


## Run 46 — authoritative EditWordDocument dispatch/VMT correction

The Run-67 generic VMT resolver's failure to find a standard-layout candidate for TEditWordDocument is a false negative for this class and is superseded by the earlier direct VMT/interface crosswalk in docs/WORD-DOCUMENT-PROTOCOL-ANALYSIS.md and docs/WORD-LIFECYCLE-STATIC-TRACE.md:

- TEmwatMethod VMT: 0x0046ABFC; slot +0x0C points to the public Invoke wrapper at 0x0046C9E0.
- The wrapper calls the shared dictionary/XML helper at 0x0046C82C, then dispatches the concrete method through VMT slot +0x10 at 0x0046CA88.
- TEditWordDocument VMT: 0x005ED764; parent pointer 0x0046ABA4 resolves to the TEmwatMethod VMT header; slot +0x10 points to 0x005EE82C.
- The routine at 0x005EE82C is therefore definitively the concrete TEditWordDocument.PerformMethod, despite TD32 decorating it as TScanDocument.PerformMethod.
- TScanDocument VMT 0x005ED884 slot +0x10 points to 0x005EEB48, despite TD32 decorating that routine as TFaxDocument.PerformMethod.

The end-to-end static dispatch chain is now closed: service XML class EditWordDocument -> constructs TEditWordDocument via GetClass("T"+className) -> VMT +0x0C Invoke -> shared dictionary/XML helper -> concrete VMT +0x10 at 0x005EE82C -> WordViewer loader.

## Run 46 — response and loopback origin evidence

The existing PCAP round-trip is the wire source of truth for the successful path:

- Request: POST /?invoke=58351, Content-Type text/plain;charset=UTF-8, Content-Length 1,177,821, Origin http://127.0.0.1:1984.
- Response: HTTP 200, Content-Type text/html; charset=ISO-8859-1, Content-Length 1,166,820.
- XML: response-word status="success" / return-types / type mimetype="application/msword" encryption="base64".
- Decoded response begins with the OLE Compound File signature; it is a returned Word document, not a status-only acknowledgement.
- The BPL assigns generated XML to AResponseInfo.ContentText, calls Indy WriteContent, and sets bResultSet on the successful branch.

The PCAP response has 17 TCP sequence gaps totaling 68 missing payload bytes, so the exact full response bytes/hash remain unverified. The request body itself has no detected sequence gaps.

The browser screenshot pair records Referer http://127.0.0.1:1984/?init=...; the XHR Origin in the PCAP is also http://127.0.0.1:1984. This is evidence for an allowlist entry of exactly http://127.0.0.1:1984 for the captured deployment. It is not necessary to guess the external Almas page's domain for the local XHR Origin. Keep the listener loopback-only and make the allowlist explicit/configurable.

## Remaining release gates after static protocol closure

1. Run the real Almas browser workflow against the GTK application with the captured loopback Origin/Referer behavior and LibreOffice Writer.
2. Verify the same Invoke remains pending while Writer is open; Save then close; ensure Almas receives and persists the returned DOC; reopen it and verify the saved marker.
3. Capture a gap-free response or otherwise validate the complete serialized response body against the native implementation.
4. Complete the current PR CI cycle for Python bridge, GTK smoke, and Debian package lifecycle. The previous GTK run failed on shutdown-error label ordering; the fix is committed on the isolated work branch. Run-67's Python step was cancelled, so it is not a pass/fail result.
5. Resolve WordConfig field mapping and signData only to the extent required by the live acceptance fixture. letterImages is currently tied to the TIFF/preview path and remains deferred while TIFF is out of scope.
6. Run the configured GTK bridge against a real Almas page using the exact loopback origins; verify Almas accepts and persists the returned DOC. Do not enable wildcard origins or an unverified host.

The earlier Run-40 statement that TEditWordDocument had no VMT is superseded: it describes only a false negative in the newer generic resolver, not the overall evidence. The direct VMT mapping above is authoritative.


## Run 47 — GTK deployment wiring values are now evidence-backed

The bridge already supports separate XHR Origin and parent-page Referer allowlists. The PCAP/screenshot establishes both origins as http://127.0.0.1:1984, with the bridge bound to 127.0.0.1:1984. The external Almas web page hostname is not the Origin of the captured loopback XHR and should not be guessed or required for this listener. A precise startup composition and explicit-discard fallback policy are documented in docs/ALMAS-GTK-STARTUP-WIRING-PLAN.md.

This Run-47 implementation-gap statement is superseded by the isolated
work-branch implementation recorded in the implementation-status section of
`docs/ALMAS-GTK-STARTUP-WIRING-PLAN.md` and by PR #6. The remaining gate is
runtime acceptance against real Almas, not the existence of the GTK composition.
The CancelResponseFactory remains a fail-closed local 409 only for explicit
operation-level DISCARDED; Writer's Save/Don't Save/Cancel lifecycle is separate.


## Run 50 — preserve the native pending-request duration

The approximately 54.56-second PCAP gap from the final request-body byte to the first response byte is explained by the separate `TWordViwer.OnTmrAutoSave` close loop documented in `docs/WORD-RESPONSE-TIMER-CORRELATION-2026-11-16.md`: it pumps messages, sleeps 5 ms, and waits until viewer field `+0x58` is cleared by the Word close/registration callback at `0x004CD154/0x004CD31C`. This is the main user-open duration, distinct from the short EFOpenError class poll at `0x004B7D57`.

The Linux `LibreOfficeAdapter` has `close_timeout_seconds=None` by default, so its `wait_for_close` remains pending until the Writer close listener fires. Keep that default for parity; do not add a 30/60-second lifecycle timeout. The bridge's 10-second socket timeout governs socket I/O, not the synchronous office-session wait after the request body has been read. The browser-side XHR must likewise remain pending for the user's editing session.
