"""Evidence-bounded matching between EMWAT config fields and Writer templates.

The native binary trace establishes index alignment between Word custom
properties and wordConfig.fields. This module reports only exact-name matches
against Writer structures; it never guesses positional, fuzzy, or semantic
mappings and never reads document text or property values.
"""
from __future__ import annotations

from dataclasses import dataclass

from emwat_linux.word_config import WordDocumentConfig
from emwat_linux.word_fields import (
    build_word_custom_property_field_maps,
    resolve_twin_field_partner,
)
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
    alignment_error: str | None
    candidates: tuple[TemplateFieldCandidate, ...]
    unmatched_config_fields: tuple[str, ...]
    unmatched_template_structures: tuple[str, ...]


def inspect_template_mapping(
    config: WordDocumentConfig,
    catalog: WriterDocumentCatalog,
) -> TemplateMappingReport:
    """Create an exact-name candidate report without mutating the Writer file.

    The recovered native AddCustomDocPropertiesToDic path uses each custom
    property's enumeration index to select the XML field at the same index.
    If those sequences differ in length, the association is ambiguous and no
    positional candidates are emitted.

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
            alignment_error="custom_property_and_config_field_counts_differ",
            candidates=(),
            unmatched_config_fields=tuple(field.field_id for field in config_fields),
            unmatched_template_structures=(),
        )

    # Reuse the native-shaped single/twin descriptor parser. It rejects
    # duplicate property keys rather than silently overwriting them.
    maps = build_word_custom_property_field_maps(
        property_names,
        xml_fields=config_fields,
    )

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

    for descriptor in (*maps.singles, *maps.twins):
        members = (
            (descriptor.property_name,)
            if not hasattr(descriptor, "first_field_name")
            else (descriptor.first_field_name, descriptor.second_field_name)
        )
        for member in members:
            for kind, actual_name in by_folded_name.get(member.casefold(), ()):
                candidates.append(
                    TemplateFieldCandidate(
                        config_index=descriptor.index,
                        xml_field_id=descriptor.xml_field.field_id,
                        custom_property_name=descriptor.property_name,
                        config_member=member,
                        structure_kind=kind,
                        structure_name=actual_name,
                    )
                )
                matched_structures.add((kind, actual_name))
                matched_config.add(descriptor.index)

    return TemplateMappingReport(
        property_count=len(property_names),
        config_field_count=len(config_fields),
        index_alignment_valid=True,
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
