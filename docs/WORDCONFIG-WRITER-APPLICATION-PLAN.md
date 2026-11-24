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

The LibreOffice adapter now attempts this inventory automatically after opening the document and capturing its baseline. The report is retained on the in-memory office handle as `word_writer_evidence`; if the overall catalog inspection raises, opening continues and only the value-free status `writer_inventory_unavailable` is retained. Individual UNO containers can also fail independently: the catalog and report now preserve stable, value-free `writer_inventory_warnings` codes instead of silently representing an unavailable container as an empty one. This is diagnostic inventory only: it does not mutate Writer content, apply field mappings, or guarantee that the report is externally surfaced. In the same catalog pass, `template_mapping_inventory` reports case-insensitive exact-name candidates between custom-property identifiers and Writer bookmarks/ranges/sections/tables/frames/graphics/indexes/`DocInfo.Custom` fields. It deliberately does **not** associate a Writer property index with a WordConfig XML field index: `property_order_equivalence_verified` is false, and all XML field IDs remain in `unassociated_config_field_ids` until Word COM and UNO ordering are validated against the same fixture. This report is also value-free and read-only.

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

## Controlled Writer property updates

The low-level custom-property setter accepts only an explicit caller-supplied mapping and updates existing exact-name properties; it does not create missing properties or infer mappings from WordConfig. Before mutation it validates every target and captures the previous values. If a later UNO setter fails, it attempts reverse-order rollback of earlier updates and reports separately when rollback is incomplete. This is best-effort compensation, not a true UNO transaction; callers must treat an incomplete rollback as a failed document operation and avoid returning the document as a successful EMWAT roundtrip.


## Stage A2 — image and signer metadata inventory / controlled Writer image updates

The Linux bridge now decodes the observed `image/*` + `encryption="base64"` WordConfig fields into a bounded, in-memory image inventory. It preserves source field indices (not IDs) because duplicate XML field IDs have been observed, retains `paramId` references as metadata, and recognizes the 20 signer metadata slots `LetterSignerPer0..19`, `LetterSignerDep0..19`, and `LetterSignerUnit0..19`. Missing signer values remain empty slots; duplicate members in one slot are rejected. Empty image fields are recorded but are never treated as delete instructions.

An explicit Writer image update API is now available. It requires a caller-supplied mapping from WordConfig field index to an existing Writer graphic-object name, validates every target before mutation, stages image bytes in the private per-session directory, updates only `GraphicURL` (preserving the existing anchor/frame geometry), and compensates prior updates if a later UNO setter fails. It never creates or guesses graphic anchors. The adapter captures only a fixed error code if inventory fails; image bytes and signer values are not written to logs or evidence reports.

This closes the **asset decoding, signer-slot normalization, and controlled image replacement mechanism**. It does not establish the production field-index-to-Writer-anchor table: the sample WordConfig names the image families but the matching Almas Writer/Word template is absent. `signData` is still preserved as opaque request text because the native concatenation/serialization contract has not been resolved; no splitting, decoding, or association with a particular signature image is assumed. The full 180-field mapping remains gated on a matching sanitized document/template fixture and byte-exact expected Windows result.
