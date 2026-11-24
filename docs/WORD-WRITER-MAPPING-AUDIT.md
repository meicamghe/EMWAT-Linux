# Word ↔ Writer property alignment audit

`audit_writer_property_alignment()` compares Word CustomDocumentProperties
captured in native enumeration order with Writer's UNO custom-property
metadata. It reports exact, case-sensitive name intersections and unmatched
names, plus names observed on Writer `DocInfo.Custom` text fields.

This is an inventory aid, not an automatic mapping:
- exact-name intersection is a candidate, not proof of semantic equivalence;
- Word COM and UNO enumeration order are not assumed equivalent;
- no property values, letter text, or image data are read;
- case-only candidates are reported only when the case-folded name is unique on both sides; they remain review hints, never automatic mappings;
- ambiguous case-fold collisions are omitted rather than guessed;
- no positional matching or fuzzy matching is performed.

Validate candidates against anonymized real templates and field-result behavior
before enabling writes for any mapped EMWAT field.


## Runtime wiring boundary — 2026-11-20

The current request path parses `wordConfig` and retains its field nodes, but it does **not** yet apply those fields to Writer:

1. `parse_editword_request()` decodes and parses `wordConfig`, while preserving `signData` as opaque text.
2. `EditWordDocumentService.process()` passes the resulting request to `DocumentCoordinator`.
3. `LibreOfficeAdapter.open_document()` opens the input document and explicitly documents that request config is not applied.
4. `decode_word_fields()`, `build_word_custom_property_field_maps()`, `inspect_writer_document()`, and `apply_custom_property_updates()` are available as separate analysis/adapter operations, but the current service does not compose them into an automatic mapping-and-write step.

Therefore the green UNO roundtrip proves document open/close/export and the synthetic response path; it does not prove that an incoming Almas `wordConfig` populates all corresponding Writer fields. Do not describe the current integration as a complete EMWAT document-editing workflow.

### Safe next integration gate

Before enabling automatic field writes, obtain a sanitized real Word fixture plus its matching `wordConfig` and expected output. Establish, for that fixture:

- the actual Word custom-property enumeration order used by the native implementation;
- the corresponding Writer custom-property names and order after import;
- exact field-to-property associations, including twin identifiers and empty values;
- URL-encoded text, Base64 image bytes, MIME types, and external `signData` bindings;
- visible field refresh behavior after updates;
- output roundtrip equivalence for text, images, bookmarks, and signatures.

Until this fixture exists, keep property updates explicit and exact-name-only. Do not auto-create properties, infer positional alignment from Writer metadata order, or guess `signData` concatenation.


## Indexed signer catalog ordering hardening — 2026-11-23

The indexed signer-slot audit now records each recognized field's actual input
position in a single pass. This preserves repeated occurrences of an identical
field ID in their original order and avoids the previous repeated
`field_ids.index()` scan (quadratic behavior on large catalogs). This is still
structural evidence only: duplicate IDs remain visible for investigation, no
missing field is synthesized, and no Word-to-Writer mapping is inferred.
A regression test covers an interleaved duplicate signer field.
