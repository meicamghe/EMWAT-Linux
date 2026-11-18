"""Evidence-bounded comparison of Word custom properties and Writer metadata.

Exact-name intersections are reported as candidates only. This module never
assumes Word COM and UNO enumeration orders are equivalent and never reads
document property values or letter content.
"""
from __future__ import annotations

from dataclasses import dataclass

from emwat_linux.word_fields import WordCustomPropertyFieldMaps
from emwat_linux.writer_inspector import WriterDocumentCatalog


@dataclass(frozen=True)
class WriterPropertyAlignmentAudit:
    word_property_names: tuple[str, ...]
    writer_property_names: tuple[str, ...]
    exact_name_matches: tuple[str, ...]
    word_only_names: tuple[str, ...]
    writer_only_names: tuple[str, ...]
    writer_docinfo_custom_field_names: tuple[str, ...]


def audit_writer_property_alignment(
    word_maps: WordCustomPropertyFieldMaps,
    writer_catalog: WriterDocumentCatalog,
) -> WriterPropertyAlignmentAudit:
    """Compare exact identifiers without inferring order or semantic equivalence."""
    word_names = tuple(
        item.property_name for item in (*word_maps.singles, *word_maps.twins)
    )
    writer_names = writer_catalog.custom_document_properties_in_info_order
    word_set = set(word_names)
    writer_set = set(writer_names)
    return WriterPropertyAlignmentAudit(
        word_property_names=word_names,
        writer_property_names=writer_names,
        exact_name_matches=tuple(name for name in word_names if name in writer_set),
        word_only_names=tuple(name for name in word_names if name not in writer_set),
        writer_only_names=tuple(name for name in writer_names if name not in word_set),
        writer_docinfo_custom_field_names=tuple(
            field.custom_property_name
            for field in writer_catalog.text_fields
            if field.custom_property_name is not None
        ),
    )


__all__ = ["WriterPropertyAlignmentAudit", "audit_writer_property_alignment"]
