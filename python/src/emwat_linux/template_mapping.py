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
class ConfigFieldStructureCandidate:
    field_index: int
    field_id: str
    field_member: str
    structure_kind: str
    structure_name: str
    match_kind: str


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
    config_field_candidates: tuple[ConfigFieldStructureCandidate, ...] = ()
    unmatched_config_field_indices: tuple[int, ...] = ()
    partial_config_field_indices: tuple[int, ...] = ()
    ambiguous_config_field_indices: tuple[int, ...] = ()


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

    # Independently compare each WordConfig identifier (including twin
    # members) to Writer structures by name. This avoids using property
    # enumeration position as a surrogate for semantic identity.
    config_structures = list(structures)
    config_structures.extend(
        ("custom_document_property", name)
        for name in catalog.custom_document_properties_in_info_order
    )
    config_by_folded_name: dict[str, list[tuple[str, str]]] = {}
    exact_structures: dict[str, list[tuple[str, str]]] = {}
    for kind, name in config_structures:
        exact_structures.setdefault(name, []).append((kind, name))
        config_by_folded_name.setdefault(name.casefold(), []).append((kind, name))
    config_candidates: list[ConfigFieldStructureCandidate] = []
    unmatched_config: list[int] = []
    partial_config: list[int] = []
    ambiguous_config: list[int] = []
    field_candidate_owners: dict[tuple[str, str], list[int]] = {}
    for field_index, field in enumerate(config.fields):
        identifier = parse_word_field_identifier(field.field_id)
        members = tuple(dict.fromkeys(
            member for member in (identifier.first, identifier.second) if member
        ))
        matched_members = 0
        field_ambiguous = False
        for member in members:
            exact = exact_structures.get(member, ())
            if len(exact) == 1:
                kind, name = exact[0]
                match_kind = "exact"
            elif len(exact) > 1:
                field_ambiguous = True
                continue
            else:
                folded = config_by_folded_name.get(member.casefold(), ())
                if len(folded) == 1:
                    kind, name = folded[0]
                    match_kind = "casefold"
                elif len(folded) > 1:
                    field_ambiguous = True
                    continue
                else:
                    continue
            matched_members += 1
            config_candidates.append(
                ConfigFieldStructureCandidate(
                    field_index, field.field_id, member, kind, name, match_kind
                )
            )
            field_candidate_owners.setdefault((kind, name), []).append(field_index)
        if field_ambiguous:
            ambiguous_config.append(field_index)
        elif matched_members == 0:
            unmatched_config.append(field_index)
        elif matched_members < len(members):
            partial_config.append(field_index)

    reused_targets = {
        index
        for owners in field_candidate_owners.values()
        if len(set(owners)) > 1
        for index in owners
    }
    if reused_targets:
        ambiguous_config.extend(sorted(reused_targets))
        config_candidates = [
            candidate for candidate in config_candidates
            if candidate.field_index not in reused_targets
        ]
    ambiguous_config_tuple = tuple(sorted(set(ambiguous_config)))
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
        config_field_candidates=tuple(config_candidates),
        unmatched_config_field_indices=tuple(unmatched_config),
        partial_config_field_indices=tuple(partial_config),
        ambiguous_config_field_indices=ambiguous_config_tuple,
    )


__all__ = [
    "ConfigFieldStructureCandidate",
    "TemplateMappingInventory",
    "TemplateStructureCandidate",
    "inspect_template_mapping",
]
