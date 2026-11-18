# Word ↔ Writer property alignment audit

`audit_writer_property_alignment()` compares Word CustomDocumentProperties
captured in native enumeration order with Writer's UNO custom-property
metadata. It reports exact, case-sensitive name intersections and unmatched
names, plus names observed on Writer `DocInfo.Custom` text fields.

This is an inventory aid, not an automatic mapping:
- exact-name intersection is a candidate, not proof of semantic equivalence;
- Word COM and UNO enumeration order are not assumed equivalent;
- no property values, letter text, or image data are read;
- no case folding, positional matching, or fuzzy matching is performed.

Validate candidates against anonymized real templates and field-result behavior
before enabling writes for any mapped EMWAT field.
