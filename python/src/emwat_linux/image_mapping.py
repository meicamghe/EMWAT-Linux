"""Read-only candidate matching for WordConfig image fields to Writer graphics.

Candidates are exact or unique case-folded name intersections only. They are
never applied automatically; duplicate IDs and multi-target matches stay
ambiguous until a fixture-backed registry resolves them.
"""
from __future__ import annotations

from dataclasses import dataclass

from emwat_linux.word_config import WordDocumentConfig
from emwat_linux.word_fields import parse_word_field_identifier
from emwat_linux.writer_inspector import WriterDocumentCatalog


@dataclass(frozen=True)
class ImageStructureCandidate:
    field_index: int
    field_id: str
    matched_member: str
    writer_graphic_name: str
    match_kind: str


@dataclass(frozen=True)
class ImageMappingInventory:
    image_field_count: int
    candidates: tuple[ImageStructureCandidate, ...]
    unmatched_image_field_indices: tuple[int, ...]
    ambiguous_image_field_indices: tuple[int, ...]


def inspect_word_image_mapping(
    config: WordDocumentConfig,
    catalog: WriterDocumentCatalog,
) -> ImageMappingInventory:
    """Find conservative name candidates without reading or mutating image data."""
    if not isinstance(config, WordDocumentConfig):
        raise TypeError("invalid_word_document_config")
    if not isinstance(catalog, WriterDocumentCatalog):
        raise TypeError("invalid_writer_document_catalog")

    graphic_names = catalog.graphic_objects
    by_folded: dict[str, list[str]] = {}
    for name in graphic_names:
        by_folded.setdefault(name.casefold(), []).append(name)

    candidates: list[ImageStructureCandidate] = []
    unmatched: list[int] = []
    ambiguous: list[int] = []
    image_count = 0
    for field_index, field in enumerate(config.fields):
        if not field.attributes.get("mimetype", "").casefold().startswith("image/"):
            continue
        image_count += 1
        identifier = parse_word_field_identifier(field.field_id)
        members = tuple(dict.fromkeys(
            member for member in (identifier.first, identifier.second) if member
        ))
        matches: list[ImageStructureCandidate] = []
        for member in members:
            exact = tuple(name for name in graphic_names if name == member)
            if len(exact) == 1:
                matches.append(ImageStructureCandidate(
                    field_index, field.field_id, member, exact[0], "exact"
                ))
            elif not exact:
                folded = by_folded.get(member.casefold(), ())
                if len(folded) == 1:
                    matches.append(ImageStructureCandidate(
                        field_index, field.field_id, member, folded[0], "casefold"
                    ))
                elif len(folded) > 1:
                    field_ambiguous = True
        if field_ambiguous or len(matches) > 1:
            ambiguous.append(field_index)
        elif len(matches) == 1:
            candidates.append(matches[0])
        else:
            unmatched.append(field_index)

    target_owners: dict[str, list[int]] = {}
    for candidate in candidates:
        target_owners.setdefault(candidate.writer_graphic_name, []).append(
            candidate.field_index
        )
    collisions = {
        index
        for owners in target_owners.values()
        if len(owners) > 1
        for index in owners
    }
    if collisions:
        ambiguous.extend(sorted(collisions))
        candidates = [
            candidate for candidate in candidates
            if candidate.field_index not in collisions
        ]
    ambiguous_tuple = tuple(sorted(set(ambiguous)))
    return ImageMappingInventory(
        image_field_count=image_count,
        candidates=tuple(candidates),
        unmatched_image_field_indices=tuple(unmatched),
        ambiguous_image_field_indices=ambiguous_tuple,
    )


__all__ = [
    "ImageMappingInventory",
    "ImageStructureCandidate",
    "inspect_word_image_mapping",
]
