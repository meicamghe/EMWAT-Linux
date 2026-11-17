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


__all__ = [
    "IndexedSignerField",
    "group_indexed_signer_fields",
    "parse_indexed_signer_field",
]
