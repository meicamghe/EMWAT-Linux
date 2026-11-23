"""Read-only exact-name inventory across WordConfig, custom properties and Writer.

This module deliberately does NOT join a custom-property enumeration index to a
WordConfig field index: LibreOffice's property order has not been proven equal
to Word COM's order. It reports property-to-Writer structural candidates only.
No values are read and no document is modified.
"""
from __future__ import annotations

from dataclasses import dataclass

from emwat_linux.word_config import WordDocumentConfig
from emwat_linux.word_fields import parse_word_field_identifier
from emwat_linux.writer_inspector import WriterDocumentCatalog


@dataclass(frozen=True)
class TemplateStructureCandidate:
    property_index: int
    custom_property_name: str
    property_member: str
    structure_kind: str
    structure_name: str


@dataclass(frozen=True)
class TemplateMappingInventory:
    config_field_count: int
    custom_property_count: int
    property_config_counts_match: bool
    property_order_equivalence_verified: bool
    candidates: tuple[TemplateStructureCandidate, ...]
    duplicate_property_names: tuple[str, ...]
    duplicate_property_members: tuple[str, ...]
    unmatched_custom_properties: tuple[str, ...]
    unmatched_writer_structures: tuple[str, ...]
    unassociated_config_field_ids: tuple[str, ...]
    inspection_warnings: tuple[str, ...]


def _duplicates(values: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for value in values:
        folded = value.casefold()
        if folded in seen and value not in duplicates:
            duplicates.append(value)
        seen.add(folded)
    return tuple(duplicates)


def inspect_template_mapping(
    config: WordDocumentConfig,
    catalog: WriterDocumentCatalog,
) -> TemplateMappingInventory:
    """Report exact-name property/Writer candidates without config-field pairing."""
    if not isinstance(config, WordDocumentConfig):
        raise TypeError("invalid_word_document_config")
    if not isinstance(catalog, WriterDocumentCatalog):
        raise TypeError("invalid_writer_document_catalog")

    property_names = catalog.custom_document_properties_in_info_order
    structures: list[tuple[str, str]] = []
    for kind, names in (
        ("bookmark", catalog.bookmarks),
        ("named_range", catalog.named_ranges),
        ("text_section", catalog.text_sections),
        ("text_table", catalog.text_tables),
        ("text_frame", catalog.text_frames),
        ("graphic_object", catalog.graphic_objects),
        ("document_index", catalog.document_indexes),
    ):
        structures.extend((kind, name) for name in names)
    structures.extend(
        ("custom_property_text_field", field.custom_property_name)
        for field in catalog.text_fields
        if field.custom_property_name
    )

    by_folded_name: dict[str, list[tuple[str, str]]] = {}
    for kind, name in structures:
        by_folded_name.setdefault(name.casefold(), []).append((kind, name))

    candidates: list[TemplateStructureCandidate] = []
    matched_properties: set[int] = set()
    matched_structures: set[tuple[str, str]] = set()
    seen_members: set[str] = set()
    duplicate_members: list[str] = []

    for property_index, property_name in enumerate(property_names):
        identifier = parse_word_field_identifier(property_name)
        members = tuple(
            member for member in (identifier.first, identifier.second) if member
        )
        for member in members:
            folded = member.casefold()
            if folded in seen_members and member not in duplicate_members:
                duplicate_members.append(member)
            seen_members.add(folded)
            for kind, actual_name in by_folded_name.get(folded, ()):
                candidates.append(
                    TemplateStructureCandidate(
                        property_index=property_index,
                        custom_property_name=property_name,
                        property_member=member,
                        structure_kind=kind,
                        structure_name=actual_name,
                    )
                )
                matched_properties.add(property_index)
                matched_structures.add((kind, actual_name))

    return TemplateMappingInventory(
        config_field_count=len(config.fields),
        custom_property_count=len(property_names),
        property_config_counts_match=len(config.fields) == len(property_names),
        property_order_equivalence_verified=False,
        candidates=tuple(candidates),
        duplicate_property_names=_duplicates(property_names),
        duplicate_property_members=tuple(duplicate_members),
        unmatched_custom_properties=tuple(
            name for index, name in enumerate(property_names)
            if index not in matched_properties
        ),
        unmatched_writer_structures=tuple(
            f"{kind}:{name}" for kind, name in structures
            if (kind, name) not in matched_structures
        ),
        # Until Word COM and LibreOffice enumeration order are proven equivalent,
        # no XML field can safely be attached to a property index.
        unassociated_config_field_ids=tuple(field.field_id for field in config.fields),
        inspection_warnings=catalog.inspection_warnings,
    )


__all__ = [
    "TemplateMappingInventory",
    "TemplateStructureCandidate",
    "inspect_template_mapping",
]
