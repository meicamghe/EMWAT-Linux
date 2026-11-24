# Writer template mapping inventory

`emwat_linux.template_mapping.inspect_template_mapping(config, catalog)` creates a read-only inventory of exact-name candidates between Writer custom document-property names and Writer structural objects.

## Safety boundary

- The report compares custom-property names against Writer bookmarks, named ranges, sections, tables, frames, graphic objects, indexes, and `DocInfo.Custom` text fields.
- Matching is case-insensitive but otherwise exact. There is no fuzzy, positional, or semantic guessing.
- The report never reads document text, field presentation values, or custom-property values and never modifies the document.
- The native Word path associates Word COM custom-property enumeration indices with `wordConfig.fields`. LibreOffice exposes a separate metadata order. Equivalence between these orders has **not** been proven.
- Therefore `property_config_counts_match` is only a count check. It is not an alignment proof. `property_order_equivalence_verified` remains false and every XML field ID is listed in `unassociated_config_field_ids`.
- Candidate records identify a custom-property index/name and a Writer structure only. They intentionally contain no XML field index or XML field ID.

## Use

Treat candidates as leads for validating an anonymized representative template. Do not use them to populate production fields until Word COM and LibreOffice property ordering, actual Word field targets, and save/round-trip behavior have been verified against the same fixture.
