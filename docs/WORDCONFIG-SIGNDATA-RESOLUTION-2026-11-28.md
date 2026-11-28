# WordConfig and signData external-parameter closure — 2026-11-28

## Confirmed native contract

- EditWordDocument requires wordConfig and forwards wordConfig, wordBody, letterImages, and signData to TWordViwer.LoadDocument.
- wordBody is Base64 legacy Word data and must decode to a non-empty document on the successful load path.
- wordConfig is a Base64 XML document. The captured example has 180 fields: 40 base identifiers plus seven signer-field families across slots 0–19.
- The external image field is SignsStart†SignsEnd with paramId="signData". It is distinct from the indexed inline image fields SignOfSignerStartN†SignOfSignerEndN.
- The captured XML contains separator="&" and concater="\\n". A separate static trace found the native setter reads the spelling concator. Neither spelling is aliased in the Linux model.
- The native handler's dictionary helper normalizes absent letterImages and signData to empty strings. The captured PCAP's signData happens to be empty; that does not establish non-empty payload semantics.
- TWordViwer.LoadDocument passes signData into XML/interface operations around 0x004B7AEB–0x004B7B2F. The exact serializer, delimiter loop, decoder, image binding, and output relationship have not yet been proven.

## Implemented in this branch

- EditWordDocumentRequest keeps signData and other auxiliary parameters opaque, bounds their sizes, and excludes document bytes, the full WordConfig (including field values), signData, and auxiliary payloads from repr().
- resolve_external_parameter_bindings() associates every WordConfig paramId with the exact outer request parameter, preserving field order, repeated references, missing-versus-present-empty state, MIME type, encoding label, and raw separator / concater / concator attributes.
- The resolver reads the WordConfig structure without decoding unrelated field values. Size accounting counts each distinct outer parameter once, even when multiple fields reference it.
- Raw parameter values are never copied into diagnostics or dataclass representations.
- The resolver intentionally performs no Base64/URL decoding, splitting, joining, or Writer mutation. This is a safe binding layer, not a claim that signData processing is complete.

## Remaining evidence required for full signData parity

1. A non-empty sanitized Windows signData request paired with its matching wordConfig and letterImages value.
2. A trace of the complete native code from 0x004B7AEB through the XML/interface calls, including string lengths, allocation/copy operations, and any Base64/URL decoder entry points.
3. The exact concater versus concator resolution and whether separator divides records, parameters, or image payload segments.
4. A byte-level mapping from each decoded segment to SignsStart†SignsEnd and any signer image target.
5. A Windows-saved response document and a round-trip comparison against LibreOffice output.

Until these are available, the correct status is: WordConfig is parsed, catalogued and externally bound; inline images and signer slots are inventoried; external signData is resolved to its request parameter but remains opaque and unapplied. Do not advertise full signature parity.


## Native SignData storage and consumption — 2026-11-28

- The actual `TWordViwer` class has a private field `SignData` at instance offset `+0xF4`. The LoadDocument path stores the external request value in this field.
- Native string key `0x004C2718` decodes to ASCII `signData`.
- `TWordViwer.GetCaptionItemFont` at `0x004C1A18` compares a caption item's key against `signData`; on the matching branch it copies the `SignData` field into a local string for caption-item processing.
- This proves that the request's `signData` value is consumed by the native caption-item path. It does not reveal the payload's encoding or fully reconstruct the final rendered object; keep the resolver's payload opaque and bounded until a non-empty Windows fixture and output comparison are available.
- The field RTTI type reference is `0x0062EEBC` and remains unresolved. The native copy pattern is consistent with Delphi string assignment.
- No use of `SignData` was found in the current BeforeClose/BeforeSave callback traces.


## Native caption-image consumption — 2026-11-28

- `signData` is stored in `TWordViwer+0xF4`; the native string key `signData` is compared in `GetCaptionItemFont` (`0x004C19C0`).
- When a caption item has that key, the routine copies the external SignData value into the caption value and later calls `EmbedTextToImage` (`0x004C436C`) with a UnicodeString and a dynamic array of `TCaptionItem`.
- `GetCaptionItems` (`0x004C2B20`) parses the caption-item structure and maps multiple attributes into XML.
- This establishes a caption/image-rendering consumer for SignData. It does not establish how the base64 value is decoded or how the PNG/TIFF bytes are produced; do not decode/split the external payload by assumption.
- The WordConfig fixture's `mimetype=image/png` and `encryption=base64` remain the authoritative metadata for the external binding; the native caption path explains where it is consumed, not the exact byte-level transformation.
