"""Evidence-bounded matching between EMWAT config fields and Writer templates.

The native binary trace establishes index alignment between Word custom
properties and wordConfig.fields. This module reports only exact-name matches
against Writer structures; it never guesses positional, fuzzy, or semantic
mappings and never reads document text or property values.
"""
from __future__ import annotations

from dataclasses import dataclass

from emwat_linux.word_config import WordDocumentConfig
from emwat_linux.word_fields import parse_word_field_identifier
from emwat_linux.writer_inspector import WriterDocumentCatalog


@dataclass(frozen=True)
class TemplateFieldCandidate:
    config_index: int
    xml_field_id: str
    custom_property_name: str
    config_member: str
    structure_kind: str
    structure_name: str


@dataclass(frozen=True)
class TemplateMappingReport:
    property_count: int
    config_field_count: int
    index_alignment_valid: bool
    property_order_equivalence_verified: bool
    alignment_error: str | None
    candidates: tuple[TemplateFieldCandidate, ...]
    unmatched_config_fields: tuple[str, ...]
    unmatched_template_structures: tuple[str, ...]


def inspect_template_mapping(
    config: WordDocumentConfig,
    catalog: WriterDocumentCatalog,
) -> TemplateMappingReport:
    """Create exact-name candidates without mutating the Writer file.

    The native Word path associates each custom-property enumeration index
    with the XML field at the same index. LibreOffice exposes its own property
    metadata order; equivalence between that order and Word COM enumeration is
    not yet proven. Equal counts are therefore necessary for candidates, but
    do not prove positional equivalence. The report exposes that distinction.

    For aligned entries, single-field names and both sides of a twin identifier
    are compared case-insensitively with Writer structure names. Custom
    DocInfo.Custom text-field names are also reported as a distinct structure
    kind. These are candidates, not proof that a given structure is the active
    Word Field.Result.Text target.
    """
    property_names = catalog.custom_document_properties_in_info_order
    config_fields = config.fields
    if len(property_names) != len(config_fields):
        return TemplateMappingReport(
            property_count=len(property_names),
            config_field_count=len(config_fields),
            index_alignment_valid=False,
            property_order_equivalence_verified=False,
            alignment_error="custom_property_and_config_field_counts_differ",
            candidates=(),
            unmatched_config_fields=tuple(field.field_id for field in config_fields),
            unmatched_template_structures=(),
        )

    # The recovered native path enumerates custom document properties and
    # splits a property name at the first U+2020 dagger into twin members.
    # Each enumerated property remains aligned with the XML field at the same
    # index; this association is used only after the count check above.
    folded_members: set[str] = set()
    descriptors: list[tuple[int, str, str, tuple[str, ...]]] = []
    for index, (property_name, xml_field) in enumerate(zip(property_names, config_fields)):
        if not property_name:
            raise ValueError("custom_property_name_missing")
        identifier = parse_word_field_identifier(property_name)
        members = tuple(
            member for member in (identifier.first, identifier.second) if member
        )
        for member in members:
            folded = member.casefold()
            if folded in folded_members:
                raise ValueError("duplicate_custom_property_field_name")
            folded_members.add(folded)
        descriptors.append((index, property_name, xml_field.field_id, members))

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
        ("custom_property_text_field", item.custom_property_name)
        for item in catalog.text_fields
        if item.custom_property_name
    )

    by_folded_name: dict[str, list[tuple[str, str]]] = {}
    for kind, name in structures:
        by_folded_name.setdefault(name.casefold(), []).append((kind, name))

    candidates: list[TemplateFieldCandidate] = []
    matched_structures: set[tuple[str, str]] = set()
    matched_config: set[int] = set()

    for config_index, property_name, xml_field_id, members in descriptors:
        for member in members:
            for kind, actual_name in by_folded_name.get(member.casefold(), ()):
                candidates.append(
                    TemplateFieldCandidate(
                        config_index=config_index,
                        xml_field_id=xml_field_id,
                        custom_property_name=property_name,
                        config_member=member,
                        structure_kind=kind,
                        structure_name=actual_name,
                    )
                )
                matched_structures.add((kind, actual_name))
                matched_config.add(config_index)

    return TemplateMappingReport(
        property_count=len(property_names),
        config_field_count=len(config_fields),
        index_alignment_valid=True,
        property_order_equivalence_verified=False,
        alignment_error=None,
        candidates=tuple(candidates),
        unmatched_config_fields=tuple(
            field.field_id
            for index, field in enumerate(config_fields)
            if index not in matched_config
        ),
        unmatched_template_structures=tuple(
            f"{kind}:{name}"
            for kind, name in structures
            if (kind, name) not in matched_structures
        ),
    )


__all__ = [
    "TemplateFieldCandidate",
    "TemplateMappingReport",
    "inspect_template_mapping",
]
