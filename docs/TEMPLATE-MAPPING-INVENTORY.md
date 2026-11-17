# Writer template mapping inventory

This module provides a conservative, read-only inventory aid for the next EMWAT field-mapping stage.

## API

`emwat_linux.template_mapping.inspect_template_mapping(config, catalog)` accepts:

- a parsed `WordDocumentConfig` from the incoming `wordConfig`;
- a `WriterDocumentCatalog` produced by `LibreOfficeAdapter.inspect_document(handle)`.

It returns a `TemplateMappingReport` with exact-name candidates and unmatched entries.

## Evidence constraints

1. Native analysis established that the application enumerates Word custom document properties and associates each property index with the XML field at the same index. The report uses this positional relationship only when the two sequences have exactly the same length.
2. A count mismatch produces an alignment error and **no positional candidates**.
3. Single identifiers and both members of a twin identifier are compared to Writer structure names using case-insensitive exact matching.
4. Bookmark, named-range, section, table, frame, graphic, document-index, and `DocInfo.Custom` field matches are kept as separate candidate kinds.
5. The report does not read letter text, field presentation values, or custom-property values. It does not modify the document.
6. An exact-name candidate is not proof that the original Word `Field.Result.Text` target is equivalent in Writer. It is an auditable lead for template validation, not a completed 180-field mapping.

## Example

```python
from emwat_linux.editword_request import parse_editword_request
from emwat_linux.template_mapping import inspect_template_mapping

edit_request = parse_editword_request(method_call)
catalog = office_adapter.inspect_document(handle)
report = inspect_template_mapping(edit_request.config, catalog)

if not report.index_alignment_valid:
    raise RuntimeError(report.alignment_error)

for candidate in report.candidates:
    print(
        candidate.config_index,
        candidate.xml_field_id,
        candidate.config_member,
        candidate.structure_kind,
        candidate.structure_name,
    )
```

Do not use these candidates to apply production values until they have been checked against an anonymized, representative Almas Gam template and the native Word behavior.


## Property-order caveat

The native Word trace confirms that Word's custom-property enumeration index is paired with the XML field at the same index. LibreOffice exposes a separate custom-property metadata sequence, and the inspector preserves that sequence rather than sorting it. **Equivalence between LibreOffice's property order and Word COM's enumeration order has not been proven.** Therefore equal counts only make a positional candidate report possible; they do not verify the order. The report sets `property_order_equivalence_verified=False` and must not be used to populate production letter fields until a representative sanitized template confirms the order.
