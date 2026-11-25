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

The screenshots do not expose the POST Payload tab or Response tab. Consequently, they do not establish:

- the exact request body, XML envelope, encoding, or method class;
- whether the response contains raw HTML, XML, base64, an embedded document, or a multipart-like structure;
- how the browser consumes the 1,166,820-byte response;
- whether the request is initiated by a Word close callback, a parent-page message, or another close-time handler;
- whether the response is the final saved letter, a wrapper containing the letter, or another artifact.

Do not infer these details from the response headers alone.

## Next investigation

1. Obtain a sanitized HAR or screenshots of the selected request's **Payload** and **Response** tabs for this same close-time POST. Preserve raw bytes/charset information; redact letter content, names, identifiers, cookies, tokens, and private URLs before sharing.
2. Compare the request body with the statically confirmed method XML structure: method node with `class` attribute; parameter children with `name` attribute and text value. The exact parameter element tag and full envelope remain unknown.
3. Decode the response according to its actual bytes and charset. Determine whether the 1,166,820-byte body contains a document, HTML wrapper, XML envelope, or another format before implementing any response serializer.
4. Correlate the browser-side initiator stack / parent-page `postMessage` with Word close and the observed POST. Do not relabel the registered BeforeSave callback as BeforeClose.
5. Add a synthetic regression fixture only after the payload and response contract are understood. Keep the native Linux bridge loopback-only and do not copy the observed wildcard CORS policy into the hardened Linux service.

## Evidence classification

- **Runtime-confirmed from screenshots:** local POST URL, loopback port, HTTP 200, request content type and referer, response length and response content type/charset, connection-close header.
- **Previously statically confirmed:** bridge uses `postMessage` and local HTTP POST; `invoke` is a per-request nonce/cache-buster; the service has Word method/response structures; the registered Word callback at `0x004CD154` is BeforeSave.
- **Unknown:** body semantics, response semantics, exact close-time trigger, and end-to-end persistence mechanism.
