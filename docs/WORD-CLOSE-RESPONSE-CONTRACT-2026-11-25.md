# Word close/response contract reconciliation — 2026-11-25

## Authority and scope

This note reconciles the current `main` tree and the 2026-11-25 runtime evidence. It supersedes older implementation assumptions where they conflict with the close-decision contract below. Historical reverse-engineering notes remain useful as evidence, but must not override this current contract.

Reviewed base: `main` at `0f95be8577718e16b6c59afb1f43fe561dabe517`.

## Current evidence inventory

- `emwat_strings.txt` exists on this `main` commit and is 13,722,034 bytes (Git blob metadata). Any earlier conclusion based on an empty file refers to an older tree and is invalid for this revision.
- PCAP exchange `invoke=58351`: the request body completes, then the first response payload arrives about 54.557883 seconds later. The response has HTTP 200, Content-Length 1,166,820 and Content-Type `text/html; charset=ISO-8859-1`. The captured response body contains a `response-word status="success"` structure with `return-types/type`, `mimetype="application/msword"`, `encryption="base64"`, and a Base64 legacy OLE/CFB Word document. The response TCP stream has sequence gaps, so the returned file is incomplete and its full hash is not verified.
- DevTools close-time exchange `invoke=29501`: the screenshot shows HTTP 200 and Content-Length 1,166,820, with the same `text/html; charset=ISO-8859-1` response Content-Type. Its Response/Body tab is not present in the evidence set.
- The exact length match across the two different invoke values is strong cross-capture correlation, not proof that the response bodies or payload types are identical. The `invoke` query value remains a per-request nonce/cache-buster, not a method ID or durable session ID.
- The service's long-lived Word request is held in the Word load/wait path while the document remains open. The HTTP response is emitted after the close/registration state is released. Heartbeat service must remain responsive concurrently; do not serialize heartbeat behind the long-lived document request.

## Word decision contract for the Linux implementation

The response must be selected from the last approved/saved document snapshot, never from an arbitrary unsaved live buffer captured merely because a close callback fired.

| User decision | Snapshot returned | Session behavior |
|---|---|---|
| Save | The latest snapshot whose office-engine save completed successfully | Close and return that saved snapshot |
| Don't Save | The previously approved snapshot (the last successful save, or the original input document if no save completed) | Close and return that approved snapshot; discard later unsaved edits |
| Cancel | No snapshot is returned and no response is finalized | Keep the same document session open and continue waiting for another decision |

Important distinctions:

- An office Save event and the final bridge/HTTP return are separate operations.
- The initial input document is the baseline approved snapshot until a successful Save replaces it.
- Periodic recovery snapshots are crash-recovery material only. They are not approved snapshots and must never be returned as the final document.
- A close attempt that is cancelled is not a terminal session state. The request worker remains waiting; a later Save or Don't Save decision can complete the same request.
- Do not create or overwrite the approved snapshot in a generic `queryClosing` callback. That callback does not, by itself, distinguish Save, Don't Save, and Cancel.
- A Save-complete event may advance the approved snapshot only after its snapshot write succeeds. A failed snapshot must fail closed rather than returning newer unsaved bytes.

## Implementation reconciliation

The reviewed `main` implementation had three mismatches with this contract:

1. `_DocumentCloseListener.queryClosing` wrote the live Writer document to `final.doc` for every close attempt. That could capture unsaved edits and did not distinguish Save from Don't Save.
2. `DocumentCoordinator` returned the close-time file regardless of whether the office engine had emitted a Save-complete event.
3. `DocumentSession.cancel()` was terminal and was being conflated with the office close-dialog Cancel. The reconciliation adds `cancel_close_attempt()` for the retryable UI decision while retaining `cancel()` for explicit terminal application cancellation.

The Linux adapter is therefore being reconciled to maintain a separate approved DOC snapshot: initialize it from the opened input, replace it only after a successful Save-complete event, and export only that snapshot after actual close. A cancelled close attempt does not signal `notifyClosed`, so the waiting request remains pending. The separate periodic recovery store remains unchanged.

## Reverse-engineering questions that remain open

1. Event identity is cross-identified: `TWordApplication.OnDocumentBeforeClose`, event-source IID `00020A00-0000-0000-C000-000000000046` (`ApplicationEvents3`), Word interop DISPID `0x00000006`. The TD32 procedure label `WordAppDocumentBeforeSave` is misleading. Direct decoding of the BPL's embedded typelib member record remains optional confirmation.
2. Find the first instruction that sets viewer field `+0x58` to a nonzero value and identify its exact state/pointer meaning. The clear at `0x004CD31C` and the `Sleep(5) + ProcessMessages` wait loop are known; the initial setter is not.
3. Obtain the actual response body for `invoke=29501` (sanitized HAR or Response-tab export) to establish whether its inner structure matches the PCAP `invoke=58351` response. Matching size and headers alone are insufficient.
4. Obtain a complete, gap-free PCAP response for definitive document bytes/hash comparison.
5. Trace Save, Don't Save, and Cancel through the actual Word callback and compare the emitted response bytes for each branch. The Linux contract above is the required target behavior; exact Windows event-to-wire mapping remains evidence-driven.

## Safety and evidence rules

- Never publish document text, Base64 payloads, customer identifiers, cookies, tokens, or private URLs.
- Preserve the distinction between direct capture evidence, static binary evidence, user-observed behavior, and implementation policy.
- Do not promote the likely `invoke=29501` / `invoke=58351` payload equivalence to a verified fact until the first body is available.


## CI verification

The code/test implementation at commit `886aee77fcc498e0ff17979d0f218b04e20a7856` passed:

- Python Bridge workflow run `45585674994`: 148 tests, 2 optional skips.
- LibreOffice UNO workflow run `45585674974`: 13 tests passed, including real Writer roundtrip and the Save-complete snapshot path.

Later commits on the reconciliation branch update documentation only. These CI runs validate the tested Linux implementation path; they do not establish the unresolved Windows COM DISPID, the `invoke=29501` response body, or live Almas end-to-end compatibility.


## 2026-11-25 UNO close-listener conformance correction

The previous adapter implementation waited for a non-interface `notifyClosed` callback. LibreOffice's `com.sun.star.util.XCloseListener` exposes `queryClosing`, `notifyClosing`, and inherited `disposing`; there is no `notifyClosed` method. The official IDL specifies that `notifyClosing` is called when the close is actually accepted, after `queryClosing`; a listener can veto a close by throwing `CloseVetoException`.

The adapter now marks the document closed from `notifyClosing`, and also accepts `disposing` as a terminal fallback when the broadcaster is externally disposed. `queryClosing` remains non-vetoing: a user's Cancel in the office save prompt is represented by the absence of a successful `notifyClosing`/disposal event, so the pending bridge request continues waiting. The listener no longer advertises or depends on the nonexistent `notifyClosed` method.

References:
- LibreOffice SDK `XCloseListener`: https://api.libreoffice.org/docs/idl/ref/interfacecom_1_1sun_1_1star_1_1util_1_1XCloseListener.html
- LibreOffice SDK `XCloseable`: https://api.libreoffice.org/docs/idl/ref/interfacecom_1_1sun_1_1star_1_1util_1_1XCloseable.html

The Save snapshot listener remains based on `OnSaveDone` and `OnSaveAsDone`. The approved-copy export uses `XStorable.storeToURL`, which is an export operation and emits `OnSaveToDone`, not the Save/Save-As completion event. This prevents the internal approved-copy export from being mistaken for a user Save.
