# Word / Writer evidence report

Date: 2026-11-20

## Purpose

`LibreOfficeAdapter.audit_word_writer_evidence(handle, config)` uses `build_word_writer_evidence_report()` to create a metadata-only summary of one parsed `wordConfig` and one Writer structural catalog. It is intended for sanitized fixture analysis before implementing any automatic field mapping.

## What it reports

- WordConfig field IDs, MIME types, declared encoding names, and external parameter IDs.
- Whether a field declares `text/plain` or an `image/*` MIME type.
- Root/permission attribute names; WordConfig field positions and IDs; duplicate and case-fold-collision groups; setting and optional-attribute duplicate names; optional-attribute type/encoding/content-presence metadata; requested-type attributes.
- Writer bookmark, named-range, section, table, frame, graphic-object, and custom-property names.
- Writer DocInfo.Custom field property names.

## Safety and evidence boundary

- Field text, decoded values, setting values, optional-attribute content, document body text, image bytes, and custom-property values are never included.
- The report does not pair WordConfig field IDs with Writer anchors.
- It does not infer property enumeration equivalence, twin-field semantics, image placement, or `signData` separators.
- It does not mutate a Writer document and must not be used as an automatic mapping plan.

A report is evidence for human comparison only. Automatic updates remain disabled until a sanitized Word document, its matching `wordConfig`, and independently verified expected output are available.