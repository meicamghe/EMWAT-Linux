# Runtime capture — 2026-11-25

## Evidence source

Two screenshots committed to the repository on 2026-11-25 as `when open.png` and `when close.png`. They show Chrome DevTools Network for the Almas Gam letter page. This note records only what is legible in those screenshots; it does not claim access to the original HAR or request/response bodies.

## Runtime-confirmed observations

### Local bridge request

- Request URL shown: `http://127.0.0.1:1984/?invoke=29501`.
- The selected request is identified as a POST in the close-time screenshot.
- HTTP status: `200 OK`.
- Remote address: `127.0.0.1:1984`.
- Request `Content-Type`: `text/plain; charset=UTF-8`.
- Request `Referer`: `http://127.0.0.1:1984/?init=84760_34426`.
- The request uses the `invoke=29501` query value. Existing static analysis says this is a per-request nonce/cache-buster; the screenshot alone does not establish a method identifier or session correlation.

### Response

- `Content-Length`: `1166820` bytes.
- `Content-Type`: `text/html; charset=ISO-8859-1`.
- `Connection`: `close`.
- The visible response headers include wildcard `Access-Control-Allow-Headers`, `Access-Control-Allow-Method`, and `Access-Control-Allow-Origin` values.

The response is therefore a large payload (about 1.11 MiB), not a tiny status-only acknowledgement. The observed response media type is HTML with ISO-8859-1 charset, which is important new runtime evidence and should be compared against the statically observed `application/msword` strings. It does not by itself prove that the response body is an HTML document; the content may be an encoded or embedded document payload.

## What is not established

The screenshots do not expose the POST Payload tab or Response tab. The current PCAP report for the separate `invoke=58351` exchange records the same response Content-Length (1,166,820 bytes) and the same `text/html; charset=ISO-8859-1` HTTP Content-Type, while its captured body contains a `response-word` XML structure carrying Base64 `application/msword` data. This is a strong cross-capture correlation, but it is not direct evidence of the `invoke=29501` body because the two invoke values are different and the DevTools response body is unavailable.

Consequently, the screenshots alone do not establish:

- the exact request body, XML envelope, encoding, or method class;
- whether the `invoke=29501` response body has the same inner `response-word` structure as the PCAP `invoke=58351` response;
- how the browser consumes the 1,166,820-byte response;
- whether the request is initiated by a Word close callback, a parent-page message, or another close-time handler;
- whether the response is the final saved letter, a wrapper containing the letter, or another artifact.

Do not infer these details from the response headers alone.

## Next investigation

1. Obtain a sanitized HAR or screenshots of the selected request's **Payload** and **Response** tabs for this same close-time POST. Preserve raw bytes/charset information; redact letter content, names, identifiers, cookies, tokens, and private URLs before sharing.
2. Compare the request body with the statically confirmed method XML structure: method node with `class` attribute; parameter children with `name` attribute and text value. The exact parameter element tag and full envelope remain unknown.
3. Decode the response according to its actual bytes and charset. Determine whether the 1,166,820-byte body contains a document, HTML wrapper, XML envelope, or another format before implementing any response serializer.
4. Correlate the browser-side initiator stack / parent-page `postMessage` with Word close and the observed POST. Do not infer the event from the TD32 procedure name alone: the callback pointer `0x004CD154` is stored at `TWordApplication` field `+0x80`, which RTTI identifies as `OnDocumentBeforeClose`, despite the TD32 symbol `WordAppDocumentBeforeSave`.
5. Add a synthetic regression fixture only after the payload and response contract are understood. Keep the native Linux bridge loopback-only and do not copy the observed wildcard CORS policy into the hardened Linux service.

## Evidence classification

- **Runtime-confirmed from screenshots:** local POST URL, loopback port, HTTP 200, request content type and referer, response length and response content type/charset, connection-close header.
- **Cross-capture correlation only:** `invoke=29501` and `invoke=58351` have matching response length (1,166,820 bytes) and HTTP response content type/charset. The `29501` body is not directly available; identical inner payload structure is not proven.
- **Previously statically confirmed:** bridge uses `postMessage` and local HTTP POST; `invoke` is a per-request nonce/cache-buster; the service has Word method/response structures; the callback pointer at `0x004CD154` is stored in the RTTI-identified `OnDocumentBeforeClose` event property; its TD32 procedure symbol says `WordAppDocumentBeforeSave` and is misleading.
- **Unknown:** the actual `invoke=29501` body, exact close-time trigger, and end-to-end persistence mechanism. The `58351` PCAP body semantics are separately documented in `docs/PCAP-EDITWORD-DOCUMENT-ROUNDTRIP.md`.


## 2026-11-25 static event cross-check

The Word event-sink workflow's RTTI scan maps `TWordApplication` field `+0x80` to `OnDocumentBeforeClose`. `OnTmrAutoSave` stores callback pointer `0x004CD154` at that field. This is stronger event-property evidence than the TD32 procedure name; the numeric COM DISPID is still not decoded.

The same workflow's class-field scan found the first known nonzero writer for viewer `+0x58`: `OnTmrAutoSave` calls `PrintWithGamPrintOptions` (`0x004C5E04`), which stores the return from `0x004565DC` at `Self+0x58` (`0x004C5E44`). The callback clears the field at `0x004CD31C`. The helper's return type and token semantics remain to be identified.
