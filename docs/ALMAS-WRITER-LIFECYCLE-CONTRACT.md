# Almas ↔ EMWAT ↔ Writer lifecycle contract

Status: synthetic loopback HTTP → Writer → response path verified; interactive Writer close behavior manually accepted; live Almas wire behavior unresolved
Date: 2026-11-24
Scope: Linux implementation; LibreOffice Writer via UNO

This document separates behavior implemented and tested in Linux from behavior
that still requires a sanitized Windows/Almas capture. It is not evidence of a
live Almas acceptance test.

## 1. Request and successful response

The implemented synthetic path is:

1. The loopback HTTP bridge validates the request boundary and XML envelope.
2. The dispatcher resolves the explicitly registered method and invokes
   `EditWordDocument`.
3. The service decodes the document/configuration under bounded size limits.
4. The office adapter opens the source document in LibreOffice Writer.
5. The user edits the document in Writer.
6. A terminal close causes the adapter to return its last confirmed saved
   Word-compatible document.
7. The response serializer emits the observed `response-word` XML success
   envelope with Base64 document bytes.

The gated integration test POSTs a generated synthetic `EditWordDocument`
envelope through the actual loopback HTTP server. The server dispatches the
request to a real LibreOffice UNO process, exports a legacy Word/CFB result,
serializes `response-word`, and returns it over HTTP. The test validates the
status, content type, CORS origin, XML envelope, Base64 encoding, and CFB
signature. It automatically closes the synthetic Writer document for a
deterministic test; it does not simulate user interaction.

The full Python suite passed **326 tests with no skips** when run with
`EMWAT_RUN_LIBREOFFICE_INTEGRATION=1`. The fixture has an empty field list and
empty `signData`. This proves the Linux transport/service/UNO success path for
that synthetic request only; it does not validate Almas browser traffic,
WordConfig field mapping, signature/image handling, or production startup.

## 2. Save, Don't Save, and bridge return

The lifecycle keeps three events distinct:

- **Modified:** Writer reports a document change.
- **Engine save:** Writer reports a successful save; only then is the confirmed
  saved-state document updated.
- **Bridge return:** after terminal close, the adapter returns the last
  confirmed saved-state document and the bridge serializes it.

The adapter no longer snapshots the live, potentially dirty Writer document
from `queryClosing`. It creates a baseline Word-compatible file before
editing. Successful UNO `OnSaveDone` / `OnSaveAsDone` callbacks export a
candidate saved-state file, validate it, and atomically replace the previous
saved-state file. A failed export preserves the previous valid saved state.
Periodic recovery snapshots are separate and are never substituted for the
final bridge-return payload.

Manual visible-UI acceptance on Ubuntu/LibreOffice on 2026-11-23 established:

- **Save:** the returned Word file contained the newly saved marker
  `EMWAT_SAVE_FIXED_004`; the trace included
  `save_done -> saved_state_succeeded` before terminal close.
- **Don't Save:** the returned file retained the baseline marker
  `EMWAT_BASELINE_KEEP_20261123` and did not contain the newly added unsaved
  marker.
- **Cancel, then Don't Save:** after Cancel, Writer remained open and the
  terminal kept waiting. No terminal close result was produced until the
  operator made a later accepted close choice. The final Don't Save returned
  the last confirmed saved state without the new test information.

The detailed probe and operator observations are in
`docs/WRITER-CLOSE-ACCEPTANCE-TEST.md`.

These results validate the local Writer adapter's visible Save / Don't Save /
Cancel-retry behavior. They do not identify the Windows application's exact
wire response or prove the live Almas browser request lifecycle.

## 3. Close attempts and cancellation

A close attempt vetoed by the office engine is non-terminal. The adapter keeps
the document session alive and waits for a later accepted close. It signals
terminal closure only after the document actually closes. The close listener's
`queryClosing` callback records lifecycle evidence only; it does not export
or snapshot dirty document contents.

The observed Cancel case confirms that a cancelled close attempt leaves Writer
open and the adapter wait pending. A later accepted close completes the probe.
Do not infer a discard or the user's choice from `notifyClosed`, `disposing`,
or absence of a save callback alone. The returned bytes are selected through
the confirmed saved-state mechanism, not by interpreting the terminal-close
callback as a Save/Don't Save signal.

The Windows evidence recovered so far establishes a `BeforeSave` event sink.
It does not establish a distinct `BeforeClose` callback in that registration,
nor does it fully identify the user-visible choice-to-HTTP-response mapping.
In particular:

- the local Writer Save / Don't Save / Cancel-retry behavior is manually
  accepted as described above;
- the exact Almas response for a Windows-side discard remains unknown;
- a bridge-level cancellation must not be assigned a guessed HTTP/XML envelope;
- the handler therefore still requires an injected cancel-response factory
  whenever the service returns no payload.

## 4. Browser Invoke lifetime: Word open → Word close

A pair of DevTools screenshots committed in the repository as `when open.png`
and `when close.png` provides a direct observation of one browser-side
Invoke lifecycle. Both screenshots select the same request URL:

`http://127.0.0.1:1984/?invoke=29501`

Observed while the Word window is open:

- The selected request is shown with provisional request headers.
- The screenshot does not expose a completed request method or HTTP status.
- Its Referer is `http://127.0.0.1:1984/?init=84760_34426`.
- Its request Content-Type is `text/plain;charset=UTF-8`.

Observed after Word is closed:

- The selected request is still the same `invoke=29501` URL; no separate
  close-time Invoke is visible in this comparison.
- DevTools now reports `POST` and `200 OK`.
- The response is `text/html; charset=ISO-8859-1`, with
  `Content-Length: 1166820` (1,166,820 bytes).
- The Referer and request Content-Type shown remain the same as above.

This is consistent with one XHR remaining pending during the Word editing
session and completing after the editor closes. It is stronger evidence for a
held-open Invoke than for a second close notification. The first screenshot
does not show the request method/status, however, so the pair alone does not
prove that the browser changed an already-sent request's method; it shows the
same request URL in a provisional state and later as a completed POST.

The response body and request payload are not visible in these Headers
screenshots. Consequently, the 1,166,820-byte response cannot yet be
classified as a Word document, HTML wrapper, or another serialized envelope.
Do not hard-code this length or infer Save/Don't Save/Cancel semantics from it.

**Implementation consequence:** the production Invoke handler must support a
request whose dispatch remains pending while the office document is open, then
serialize exactly one terminal response when the document lifecycle completes.
It must not fabricate a second close-time Invoke. The Linux Writer adapter's
saved-state rules remain separate from the still-unidentified Windows/Almas
response body.

## 4. Required capture to close the Almas gap

Capture a sanitized test exchange from a controlled Almas account and the
Windows reference implementation, recording:

- complete request method, query, headers, and XML body (with secrets and
  document contents removed but structure and field names preserved);
- successful response status, headers, XML envelope, and content type;
- behavior and response for Save then close;
- behavior and response for close without Save / Don't Save;
- behavior and response for Cancel in the office close dialog;
- behavior for any separate application-level Cancel action;
- whether the browser request remains pending and how it terminates.

Do not commit cookies, authorization headers, real letter text, personal data,
or signature images. Keep each distinct user choice as a separate fixture.

## 5. Writer adapter and bridge acceptance

Before declaring the full workflow complete, tests must prove:

- Writer opens the request document and applies only verified configuration;
- custom properties and verified field mappings are applied before display
  refresh;
- successful Save events update confirmed saved state but do not complete the
  bridge request while Writer remains open;
- a vetoed/cancelled close attempt leaves the session open and a subsequent
  accepted close can succeed;
- the final returned file is the last confirmed saved state, not a dirty live
  snapshot or periodic recovery copy;
- the successful response branch matches a sanitized Almas fixture exactly;
- discard/cancel response branches match their own sanitized fixtures exactly.

Current evidence covers the synthetic successful response path, real Writer
roundtrip, and manual Writer Save / Don't Save / Cancel-retry acceptance. It
does not cover live Almas E2E, full WordConfig field mapping, or the Windows
discard/cancel response envelopes.


## 6. Application shutdown while Invoke is pending

The HTTP server uses non-daemon request workers so a Writer-backed Invoke is not silently abandoned when the listener stops. Python's `ThreadingMixIn.server_close()` joins those workers without a timeout; calling it directly while Writer is open can therefore block the caller indefinitely.

The bridge now counts active request workers and exposes a condition-based bounded drain. `BridgeRuntime.close()` stops accepting new requests, waits up to `request_drain_timeout_seconds` (default 5 seconds), and only calls `server_close()` after the active count reaches zero. A timeout raises `bridge_request_workers_did_not_drain_before_timeout`, leaves socket cleanup retryable, and does not fabricate a response or kill the active request.

The GTK main-window close path performs supervisor shutdown off the GTK main thread. If the drain times out, the window remains open and the user can close Writer and retry. This is a bounded, retryable lifecycle policy for normal window closure; forced process termination and live Almas acceptance remain outside this guarantee.

Regression tests were added for a real loopback HTTP handler held open across the first close attempt and for GTK window-close retry. They were not executed in the 2026-11-28 implementation session, and no CI run was started.
