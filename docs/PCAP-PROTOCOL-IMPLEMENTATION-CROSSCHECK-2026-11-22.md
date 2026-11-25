# Windows capture ↔ Linux bridge implementation cross-check

Date: 2026-11-22  
Branch: `feature/recovery-retention-policy`  
Evidence: repository captures `http-requests.txt`, `tcp-conversations.txt`, and extracted Windows strings in `EMWAT-Analysis-Results.txt`. This is a metadata-only comparison; it does not reconstruct or publish document bodies.

## 1. Captured HTTP exchanges

The 2026-11-15 request index records these exchanges to `127.0.0.1:1984`:

| Frame | TCP stream | Request | Request frame payload | Response observation |
|---:|---:|---|---:|---|
| 240 / 244 | 2 | `GET /?heartbeat` | 231 bytes | HTTP 200; `text/html; charset=ISO-8859-1`; response payload 8 bytes |
| 339 / 343 | 3 | `GET /?heartbeat` | 231 bytes | HTTP 200; same content type; response payload 8 bytes |
| 868 / 874 | 4 | `GET /?init=40169_57326` | 515 bytes | HTTP 200; `text/html; charset=ISO-8859-1`; response payload 994 bytes |
| 917 / 929 | 5 | `POST /?invoke=26186` | 585 bytes | HTTP 200; `text/html; charset=ISO-8859-1`; response payload frame 78 bytes |
| 2076 / 2082 | 15 | `GET /?init=87432_1195` | 514 bytes | HTTP 200; same init response content type; response payload 994 bytes |
| 2244 / 2250 | 17 | `GET /?init=23273_1195` | 514 bytes | HTTP 200; same init response content type; response payload 994 bytes |
| 2344 / 2732 | 18 | `POST /?invoke=58351` | 31,420 bytes | HTTP 200; `text/html; charset=ISO-8859-1`; response payload frame 53,405 bytes |

The payload-byte values above are the values reported for the corresponding HTTP-bearing TCP frames, not asserted full HTTP entity lengths. In particular, the 53,405-byte response frame is not a claim that the complete response has that length. The TCP conversation summary for stream 18 reports a 54.6315-second duration and approximately 2.35 MB total traffic; do not infer the full HTTP body size from that aggregate.

## 2. Init-script behavior recovered from the Windows binary

The extracted service strings contain the init HTML/JavaScript. Its behavior is:

1. Listen for the browser `message` event (with an `attachEvent` fallback).
2. Read the message's `origin`, `source`, and `data`.
3. POST the data to `http://127.0.0.1:<port>?invoke=<random-number>`.
4. When the XHR reaches readyState 4, relay `responseText` to the original message source using the original origin.
5. Send the `<inited />` readiness message to the parent page.

The request index independently shows init GET responses of exactly 994 payload bytes. The Linux bridge's generated init script is also 994 bytes for the captured default-sized response. The generated script preserves the observed message/XHR/relay structure while substituting the configured loopback port and allowlisted parent origin.

## 3. Current Linux implementation mapping

| Captured behavior | Linux implementation | Cross-check |
|---|---|---|
| `GET /?heartbeat` | `bridge.py` `do_GET` | Returns HTTP 200, legacy ISO-8859-1 HTML content type, body `TickTack` (8 bytes) |
| `GET /?init=<digits>_<digits>` | `bridge.py` `do_GET` and `_build_init_response()` | Enforces the observed numeric pair shape; checks Referer against configured parent-origin allowlist; generates the 994-byte init script |
| `POST /?invoke=<nonce>` | `bridge.py` `do_POST` | Requires exactly one decimal ASCII invoke nonce, bounded Content-Length, configured Origin, and complete request body |
| UTF-8 XML method envelope | `protocol.py` `parse_method_call()` | Validates `emwat` root, version `1.0`, one `method`, class, and named `param` children |
| Explicit method dispatch | `dispatcher.py` `XMLMethodDispatcher` | Only registered classes execute; unknown classes return a non-success response |
| `EditWordDocument` request | `editword_request.py`, `editword_service.py` | Decodes the confirmed Base64 `wordConfig` and `wordBody`; preserves `signData` as opaque text |
| Successful Word response | `protocol.py` `serialize_word_document_response()` | Emits the captured `response-word` / `return-types` / Base64 `application/msword` structure |

The POST request media type in the capture is `text/plain;charset=UTF-8`. The transport currently records the supplied Content-Type and leaves XML interpretation to the protocol parser; it does not silently reinterpret the body based on that header.

## 4. Interpretation and limits

- Heartbeat and init behavior have direct capture evidence and matching Linux handlers.
- The init script's postMessage-to-XHR-to-postMessage relay is visible in the extracted Windows service string and represented in the Linux init response.
- The capture includes at least two invoke exchanges. The 585-byte request's method/body is not identified by the HTTP metadata export alone; do not label it as `EditWordDocument` without its reconstructed body.
- The 31,420-byte request and HTTP 200 response are a larger invoke exchange, but this CSV alone does not prove its complete body or method class. The separate earlier EditWordDocument round-trip report documents a fully identified request/response fixture.
- The 54.6-second stream-18 duration is consistent with a user-held document session, but this capture summary alone does not prove the precise Writer/Word close choice or the Almas response semantics for Save / Don't Save / Cancel.
- A separate DevTools screenshot pair (`when open.png`, `when close.png`) now shows the same `/?invoke=29501` request provisional while Word is open and completed as `POST 200` after Word closes. Its completed response declares `Content-Length: 1166820` and `text/html; charset=ISO-8859-1`. This supports a pending single-Invoke lifecycle, but the Headers views do not expose the body or prove its semantic type. See `docs/ALMAS-WRITER-LIFECYCLE-CONTRACT.md` for the detailed evidence and limits.
- No change is made to field mapping, signature handling, cancellation response, or Writer close disposition based on this metadata-only capture.

## 5. Verification

At the time of this cross-check, PR head `3e9f9d4988314aa45ae8c5505a48b1f6744311f7` has successful GitHub Actions runs for:
- Python bridge transport: run `44993581777`.
- LibreOffice UNO integration: run `44993581788`.
- Native image core build/test, DEB package lifecycle, and sanitizer jobs: run `44993581780`.

These are CI results for that exact head. They do not constitute a live Almas GUI acceptance test, a physical scanner test, or proof of complete Word/Writer field parity.

## 6. Sequence-aware PCAP reconstruction and frame-length reconciliation — 2026-11-25

The older HTTP packet index reports `tcp.len` for the individual frames in which Wireshark recognized the HTTP request/response:

- Request-bearing frame 2344: `tcp.len=31,420`.
- Response-bearing frame 2732: `tcp.len=53,405`.

These are **frame payload lengths**, not the complete HTTP entity sizes. The index has no `http.content_length` column, so those two values must not be described as the request and response body lengths.

The sequence-aware Scapy reconstruction preserved in `docs/PCAP-EDITWORD-DOCUMENT-ROUNDTRIP.md` establishes the actual HTTP headers for the same TCP tuple `127.0.0.1:61189 ↔ 127.0.0.1:1984`:

- Request: `POST /?invoke=58351`, `Content-Length: 1,177,821`.
- Response: `HTTP 200`, `Content-Length: 1,166,820`.
- Request body complete at 0.002154 s relative to capture start.
- First response payload at 54.560037 s; request-completion-to-response delay 54.557883 s.
- Response payload transmission then spans approximately 1.362 ms.

The TCP conversation summary's approximately 2.35 MB aggregate is therefore not evidence of an unexplained second application payload. It is the aggregate traffic for the bidirectional connection, while the HTTP packet index's 31,420 / 53,405 values describe only the HTTP-bearing frames. The aggregate is rounded and includes TCP-level accounting; do not use it as an exact HTTP body-length source.

### Cross-capture corroboration for the Word-close screenshot

The DevTools screenshot pair for the distinct nonce `29501` reports a completed response `Content-Length: 1,166,820`. That is an exact length match to the independently captured `invoke=58351` response whose sequence-aware reconstruction identifies a successful `response-word` envelope containing a Base64 `application/msword` document.

This exact size match materially strengthens the interpretation that the `29501` response is the same class of Word-document return, and is consistent with the same pending-Invoke-until-close lifecycle. It is **not body-level proof**: the screenshot does not expose the response body, and the two nonces belong to different captures. Keep the screenshot's payload classification marked as strongly corroborated, not directly observed.

### Static wait/release chain cross-check

The Windows BPL trace in `docs/WORD-RESPONSE-TIMER-CORRELATION-2026-11-16.md` maps the long wait:

1. `TWordViwer.LoadDocument` synchronously calls `OnTmrAutoSave`.
2. The wait loop performs `Sleep(5)` and `TApplication.ProcessMessages`, then polls viewer field `+0x58`.
3. The registered close/registration decision callback calls Word `Document.Close` and clears viewer field `+0x58`.
4. The wait returns; `LoadDocument` writes the successful `response-word` response.

This static chain is consistent with the 54.557883-second captured delay and the screenshot showing the same browser Invoke completing after Word closes. The formal COM event DISPID and the initial setter for viewer field `+0x58` remain unresolved; do not assign a more specific event identity.

### Capture availability boundary

The current repository tree contains the metadata exports, analysis scripts, and derived reports, but not the private `emwat.pcapng` or `tcp-payloads.txt` source exports. The sequence-aware measurements above are therefore cited from the preserved report and workflow artifact, not recomputed from a newly fetched raw capture in this turn. A fresh complete capture is still needed for any new body-level comparison or verification of nonce `29501`.
