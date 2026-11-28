# Reverse-engineering parallel follow-up — 2026-11-28 Run 46

## 1. Resolve the EditWordDocument class/handler chain using authoritative VMT evidence

The newer Run-67 generic VMT resolver returned no candidate for TEditWordDocument. Cross-checking the established direct VMT/interface analysis in docs/WORD-LIFECYCLE-STATIC-TRACE.md and docs/WORD-DOCUMENT-PROTOCOL-ANALYSIS.md shows this is a heuristic false negative:

| Structure | Address / relation |
|---|---|
| TEmwatMethod VMT | 0x0046ABFC |
| TEmwatMethod Invoke slot | +0x0C -> 0x0046C9E0 |
| Shared dictionary/XML helper | 0x0046C82C |
| Concrete subclass dispatch | VMT slot +0x10, callsite 0x0046CA88 |
| TEditWordDocument VMT | 0x005ED764 |
| TEditWordDocument parent | 0x0046ABA4 (TEmwatMethod VMT header) |
| TEditWordDocument.PerformMethod | VMT +0x10 -> 0x005EE82C |
| TScanDocument VMT | 0x005ED884 |
| TScanDocument.PerformMethod | VMT +0x10 -> 0x005EEB48 |

The TD32 labels are stale/mismatched: 0x005EE82C is decorated as TScanDocument.PerformMethod, and 0x005EEB48 as TFaxDocument.PerformMethod. The VMT owner and method body are authoritative. The service constructs TEditWordDocument from XML class EditWordDocument via GetClass("T"+className), calls the common Invoke wrapper at +0x0C, and the wrapper dispatches to 0x005EE82C at subclass slot +0x10.

This closes the actual handler identity; it is no longer an open question. The generic resolver gap is only a tooling false negative.

## 2. Wire response contract is established

The existing Run-6 PCAP report docs/PCAP-EDITWORD-DOCUMENT-ROUNDTRIP.md gives the successful exchange:

- Request: POST /?invoke=58351, text/plain;charset=UTF-8, 1,177,821 bytes, Origin http://127.0.0.1:1984.
- Response: HTTP 200, text/html; charset=ISO-8859-1, 1,166,820 bytes.
- XML response: response-word status="success" / return-types / type mimetype="application/msword" encryption="base64".
- Decoded payload is an OLE Compound File legacy DOC. The response capture has 17 TCP gaps / 68 missing bytes; the request has no detected gaps.

The native BPL response branch sets AResponseInfo.ContentText, calls Indy TIdHTTPResponseInfo.WriteContent, then sets bResultSet. This confirms that the successful handler response is a Base64 Word document payload, not merely an acknowledgement.

The XHR Origin and browser Referer evidence are loopback-local:
- Origin: http://127.0.0.1:1984.
- Referer: http://127.0.0.1:1984/?init=...

Therefore the captured deployment's explicit Origin allowlist can use http://127.0.0.1:1984. The bridge should remain bound to 127.0.0.1. The external Almas page domain is not the Origin of this loopback XHR and need not be guessed for the HTTP bridge.

## 3. Remaining engineering work

The static class dispatch and successful response contract are now closed. The remaining release-critical gap is live runtime acceptance:

1. Start the configured bridge from the normal GTK application entry point using the evidence-backed loopback bind and Origin allowlist.
2. Launch the actual Almas page and open a document through the local service.
3. Keep the HTTP Invoke pending while LibreOffice Writer remains open.
4. Save in Writer, close Writer, receive the response-word payload in Almas, and verify Almas persists it.
5. Reopen the document in Almas and verify the saved marker.
6. Run the bridge worker-start race, bounded drain, pending POST/heartbeat, and GTK close-retry tests locally.
7. Obtain a gap-free response capture if exact full-response byte parity is required.
8. Complete only those WordConfig/signData mappings exercised by the live fixture; keep TIFF-only letterImages deferred.

No production code was changed in Run 46. No new workflow was dispatched.
