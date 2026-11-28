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

- EditWordDocumentRequest keeps signData and other auxiliary parameters opaque, bounds their sizes, and excludes document/signature payloads from repr() to reduce accidental log exposure.
- resolve_external_parameter_bindings() associates every WordConfig paramId with the exact outer request parameter, preserving field order, repeated references, missing-versus-present-empty state, MIME type, encoding label, and raw separator / concater / concator attributes.
- Raw parameter values are never copied into diagnostics or dataclass representations.
- The resolver intentionally performs no Base64/URL decoding, splitting, joining, or Writer mutation. This is a safe binding layer, not a claim that signData processing is complete.

## Remaining evidence required for full signData parity

1. A non-empty sanitized Windows signData request paired with its matching wordConfig and letterImages value.
2. A trace of the complete native code from 0x004B7AEB through the XML/interface calls, including string lengths, allocation/copy operations, and any Base64/URL decoder entry points.
3. The exact concater versus concator resolution and whether separator divides records, parameters, or image payload segments.
4. A byte-level mapping from each decoded segment to SignsStart†SignsEnd and any signer image target.
5. A Windows-saved response document and a round-trip comparison against LibreOffice output.

Until these are available, the correct status is: WordConfig is parsed, catalogued and externally bound; inline images and signer slots are inventoried; external signData is resolved to its request parameter but remains opaque and unapplied. Do not advertise full signature parity.
