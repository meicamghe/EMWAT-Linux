# WordConfig to Writer application plan

Status: implementation boundary and acceptance contract; no guessed field mapping is enabled.

## Existing pipeline

- The EditWord request parser decodes the Base64 `wordConfig` XML and retains field metadata.
- `word_fields` decodes field values, identifies U+2020 (`†`) twin-property names, and preserves the observed native field-identifier rules.
- `word_writer_evidence` reports field identifiers, encodings, image/text classification, external parameter references, settings and Writer structural inventory without copying document values into the report.
- `field_mapping_audit` reports exact-name intersections and unambiguous case-only candidates. It deliberately does not treat enumeration-order similarity as semantic equivalence.
- `LibreOfficeAdapter.open_document()` currently opens the document payload but does not apply WordConfig to Writer. This is the remaining integration gap.

## Mapping policy

A mapping candidate is not a mapping decision. Production application must require all of the following:

1. A verified source Word fixture with its matching WordConfig and complete expected Windows result.
2. An explicit target rule identifying the Writer object/property or text range.
3. A verified value conversion rule, including URL decoding, Base64/image handling, empty-value semantics and non-ASCII behavior.
4. A collision policy for duplicate IDs, case-fold collisions and twin-field delimiters.
5. A roundtrip assertion proving the expected field appears in the returned Word payload at the correct semantic location.
6. A negative test proving unrelated fields, signatures and images are not overwritten.

Never use list position alone to map Word custom properties to Writer custom properties. Word COM and UNO enumeration order equivalence has not been established.

## Staged application design

### Stage A — read-only inventory

Generate a deterministic report from the incoming WordConfig and a Writer catalog. Keep document values, signatory data, image bytes and optional-attribute contents out of logs and reports. This stage is safe to run on arbitrary documents.

### Stage B — explicit mapping registry

Represent only evidence-backed mappings in a versioned registry. Each entry should identify:
- Word property name and/or WordConfig field ID;
- target Writer object kind and stable identifier;
- value type and conversion;
- whether the target is a single field or a twin pair;
- evidence fixture and test identifier;
- confidence/status (candidate, verified, unsupported).

Only entries marked verified may be applied. Unknown fields remain untouched and are reported as unsupported, not guessed.

### Stage C — controlled application

Apply verified mappings after Writer opens the document and before the user edits it. Record a per-field outcome without recording field values. If any required mapping is ambiguous or a required target is missing, fail the request safely rather than partially corrupting the document.

### Stage D — roundtrip verification

After Save, export the document and validate the resulting Word payload against expected field semantics. Do not assume that a successful UNO `storeToURL` means EMWAT-compatible serialization. Preserve the existing Save/Don't Save/Cancel lifecycle guarantees.

## Signatures and images

Signer fields must be treated as a family of indexed slots, not as a flat string substitution. Validate start/end pairs, signer ordering, empty slots and maximum slot count independently. Image fields and `signData` require byte-level evidence for anchor selection, image MIME type, encoding and response serialization. Do not replace or regenerate signature images from metadata alone.

## Required fixture set

Use synthetic content only:
- complete EditWord request envelope with matching WordConfig and document bytes;
- one plain text field, one URL-encoded non-ASCII field and one empty field;
- one twin field with U+2020 delimiter;
- duplicate and case-colliding field IDs;
- multiple signer slots, including unused slots;
- a signature image and its exact external parameter reference;
- expected Windows-saved response payload for each case.

A previously analyzed PCAP had missing TCP payload bytes and cannot serve as a byte-exact expected response fixture.

## Acceptance gates

- Parser/evidence tests pass without exposing values.
- Each verified registry entry has a focused unit test.
- Full synthetic Word -> Writer -> Word roundtrip passes.
- Save includes intended changes; Don't Save excludes unsaved changes; Cancel leaves the request pending and Writer open.
- Unknown/ambiguous fields remain unchanged.
- Live Almas browser integration is tested separately from local Writer roundtrip.

Until these gates pass, describe WordConfig support as parsed and audited, not applied or fully compatible.
