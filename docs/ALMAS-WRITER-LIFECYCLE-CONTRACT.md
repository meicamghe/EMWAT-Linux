# Almas ↔ EMWAT ↔ Writer lifecycle contract

Status: implementation contract with explicitly unresolved wire behavior  
Date: 2026-11-19  
Scope: Linux implementation; LibreOffice Writer via UNO

This document separates behavior implemented in the Linux bridge from behavior
that still requires a sanitized Windows/Almas capture. It is not evidence of a
live Almas acceptance test.

## 1. Request and successful response

The implemented synthetic path is:

1. The loopback HTTP bridge validates the request boundary and XML envelope.
2. The dispatcher resolves the registered method and invokes
   `EditWordDocument`.
3. The service decodes the document/configuration under bounded size limits.
4. The office adapter opens the source document in LibreOffice Writer.
5. The user edits the document in Writer.
6. A terminal close causes the adapter to export a Word-compatible document.
7. The response serializer emits the observed `response-word` XML success
   envelope with Base64 document bytes.

The application composition regression test decodes the response payload and
compares it byte-for-byte with the office adapter's final output. The current
test uses a synthetic office adapter; it does not prove live Almas compatibility.

## 2. Save is not return

The lifecycle keeps three events distinct:

- **Modified:** Writer reports a document change and the session revision advances.
- **Engine save:** Writer reports a save and the saved revision is recorded.
- **Bridge return:** the final document is exported after terminal close and
  serialized to Almas.

An explicit Save is not sufficient to complete the Almas request. The captured
workflow is close-driven, and the final close-time document is returned even
when no explicit Save event was observed. This avoids returning an intermediate
saved copy while the user still has the document open.

The reference workflow reported by the operator is that closing the Word
window without pressing Save returns control to Almas. This is recorded as a
close-driven handoff requirement. It does not, by itself, establish whether
Word displayed a Save / Don't Save / Cancel prompt or which choice was made.
A focused adapter regression now verifies that the final close snapshot and
terminal-close signal do not depend on an earlier SaveDone event.

## 3. Close attempts and cancellation

A close attempt vetoed by the office engine is non-terminal. The adapter must
keep the document session alive and wait for a later accepted close. The UNO
close listener resets its per-attempt snapshot result on every `queryClosing`,
so a failed snapshot from an earlier attempt does not poison a later successful
attempt. It signals terminal closure only from `notifyClosed`/`disposing`.
Regression tests now cover failed-first/successful-second close attempts and
verify that a save callback is emitted only for `OnSaveDone`/`OnSaveAsDone`.
A failure to create the final close-time snapshot is an error; it must not be
converted into a successful response.

The Windows evidence recovered so far establishes a `BeforeSave` event sink.
It does not establish a distinct `BeforeClose` callback in that registration,
nor does it fully identify the user-visible Save / Don't Save / Cancel decision
mapping. In particular:

- Canceling a close attempt must not be treated as a confirmed discard.
- A confirmed discard must not export or return document bytes.
- A bridge-level cancellation must not be assigned a guessed HTTP/XML envelope.
- The current LibreOffice adapter's successful close path returns
  `CloseDisposition.CLOSED`; a verified Writer discard/cancel adapter path is
  still outstanding.

The handler therefore requires an injected cancel-response factory whenever a
service returns no payload. This keeps the unknown Almas wire response explicit
instead of inventing a status code or XML body.

## 4. Required capture to close the gap

Capture a sanitized test exchange from a controlled Almas account and the
Windows reference implementation, recording:

- the complete request method, query, headers, and XML body (with secrets and
  document contents removed but structure and field names preserved);
- successful response status, headers, XML envelope, and content type;
- behavior for Save then close;
- behavior for close without Save / Don't Save;
- behavior for Cancel in the office close dialog;
- behavior for any separate application-level Cancel action;
- whether the browser request remains pending and how it terminates.

Do not commit cookies, authorization headers, real letter text, personal data,
or signature images. Keep each distinct user choice as a separate fixture.

## 5. Writer adapter acceptance

Before declaring the workflow complete, tests must prove:

- Writer open and edit use the same request document and configuration;
- custom properties and verified field mappings are applied before display
  refresh;
- Save events update saved revision but do not complete the bridge request;
- a vetoed/failed close attempt leaves the session open and a subsequent attempt can succeed;
- only confirmed save-complete document events update the saved revision;
- accepted close snapshots and exports the final Word-compatible bytes;
- confirmed discard never exports bytes;
- Cancel leaves the session open or follows the separately captured native
  behavior;
- all response branches match sanitized Almas fixtures exactly.

Until the required fixtures exist, only the successful synthetic response path
and the generic lifecycle contract are claimed.


## 6. Interactive Writer close evidence checkpoint (2026-11-20)

The adapter unit tests and the real UNO roundtrip workflow now pass on the latest tested head, including export of a Writer document as legacy Word and the synthetic EditWord response-handler path. This validates the ordinary close/export path exercised by CI.

It does **not** validate the interactive Save / Don't Save / Cancel prompt. The close listener currently captures a copy during `queryClosing`, while terminal closure is signaled later by `notifyClosed` or disposal. The UNO close-listener callbacks alone do not identify the user's choice in the Writer UI.

Until a visible-UI test or verified event contract exists:
- do not label a closed document as discarded;
- do not return a pre-prompt snapshot as though it represented the user's Don't Save choice;
- do not treat a close attempt as terminal until the document actually closes;
- keep the Almas Cancel/Discard response envelope unresolved.

Required acceptance tests and the callback-order evidence are specified in `docs/WRITER-CLOSE-DISCARD-INVESTIGATION.md`.
