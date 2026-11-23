# Almas ↔ EMWAT ↔ Writer lifecycle contract

Status: synthetic bridge path implemented; interactive Writer close behavior manually accepted; Almas wire behavior unresolved  
Date: 2026-11-23  
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

The application-composition regression test decodes the response payload and
compares it byte-for-byte with the office adapter's output. This test uses a
synthetic office adapter; it does not prove live Almas compatibility.

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
