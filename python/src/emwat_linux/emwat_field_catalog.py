"""Structural catalog helpers for the captured EMWAT Word field schema.

The catalog recognizes only the seven indexed signer-field families observed
in the 180-field request capture. It does not infer Writer property mappings.
"""
from __future__ import annotations

from dataclasses import dataclass
import re


_SIGNER_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("department", re.compile(r"^LetterSignerDep(?P<index>\d+)$")),
    ("person", re.compile(r"^LetterSignerPer(?P<index>\d+)$")),
    ("unit", re.compile(r"^LetterSignerUnit(?P<index>\d+)$")),
    ("index_unit", re.compile(r"^LetterSignerIndexUnit(?P<index>\d+)$")),
    ("signature_number", re.compile(r"^SignNumberOfSigner(?P<index>\d+)$")),
    ("behalf_name", re.compile(r"^BehalfNameOfSigner(?P<index>\d+)$")),
    (
        "signature_image",
        re.compile(
            r"^SignOfSignerStart(?P<index>\d+)†SignOfSignerEnd(?P=index)$"
        ),
    ),
)


@dataclass(frozen=True)
class IndexedSignerField:
    """One field in an observed repeated signer slot."""

    family: str
    index: int
    field_id: str


@dataclass(frozen=True)
class IndexedSignerSlot:
    """Fields observed for one signer index, without inferred property mapping."""

    index: int
    fields: tuple[IndexedSignerField, ...]
    missing_families: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return not self.missing_families


def parse_indexed_signer_field(field_id: str) -> IndexedSignerField | None:
    """Classify a known indexed signer field without rewriting its raw ID.

    Returns None for non-signer fields and malformed/non-matching twin IDs.
    The captured schema uses zero-based signer indices 0 through 19; parsing
    accepts any non-negative index so future captures are not silently clipped.
    """
    if not isinstance(field_id, str):
        raise TypeError("field_id_must_be_text")
    for family, pattern in _SIGNER_PATTERNS:
        match = pattern.fullmatch(field_id)
        if match is not None:
            return IndexedSignerField(
                family=family,
                index=int(match.group("index")),
                field_id=field_id,
            )
    return None


def group_indexed_signer_fields(
    field_ids: tuple[str, ...] | list[str],
) -> dict[str, tuple[IndexedSignerField, ...]]:
    """Group recognized signer fields by family, preserving input order."""
    grouped: dict[str, list[IndexedSignerField]] = {
        family: [] for family, _pattern in _SIGNER_PATTERNS
    }
    for field_id in field_ids:
        parsed = parse_indexed_signer_field(field_id)
        if parsed is not None:
            grouped[parsed.family].append(parsed)
    return {family: tuple(items) for family, items in grouped.items()}


def build_indexed_signer_slots(
    field_ids: tuple[str, ...] | list[str],
) -> tuple[IndexedSignerSlot, ...]:
    """Align recognized fields by numeric signer index for schema auditing.

    Slots are ordered by numeric index. Fields inside each slot retain their
    original capture order. Missing families are reported, never synthesized.
    """
    grouped = group_indexed_signer_fields(field_ids)
    by_index: dict[int, list[IndexedSignerField]] = {}
    for fields in grouped.values():
        for field in fields:
            by_index.setdefault(field.index, []).append(field)
    expected_families = tuple(family for family, _pattern in _SIGNER_PATTERNS)
    slots = []
    for index in sorted(by_index):
        fields = tuple(sorted(by_index[index], key=lambda item: field_ids.index(item.field_id)))
        present = {field.family for field in fields}
        slots.append(IndexedSignerSlot(
            index=index,
            fields=fields,
            missing_families=tuple(family for family in expected_families if family not in present),
        ))
    return tuple(slots)


__all__ = [
    "IndexedSignerField",
    "IndexedSignerSlot",
    "build_indexed_signer_slots",
    "group_indexed_signer_fields",
    "parse_indexed_signer_field",
]
