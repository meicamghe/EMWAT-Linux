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


_BASE_FIELD_CATEGORIES: dict[str, str] = {
    "RelatedLetters": "letter_relationships",
    "LetterDescription": "letter_content",
    "LetterSubject": "letter_content",
    "Appendix": "letter_content",
    "HasAppendix": "letter_content",
    "Version": "document_metadata",
    "letterId": "document_metadata",
    "LetterProducerName": "producer_metadata",
    "LetterProducerDep": "producer_metadata",
    "LetterProducerDepPhoneNumber": "producer_contact",
    "LetterProducerPhoneNumber": "producer_contact",
    "LetterProducerUnit": "producer_metadata",
    "LetterProducerUnitCode": "producer_metadata",
    "LetterSenderName": "sender_metadata",
    "LetterSenderDep": "sender_metadata",
    "LetterSenderAddress": "sender_contact",
    "LetterSenderUnit": "sender_metadata",
    "LetterSenderUnitCode": "sender_metadata",
    "LetterSenderIndexUnit": "sender_metadata",
    "ProduceDate": "registration_metadata",
    "LetterRegistrationNo": "registration_metadata",
    "LetterRegistrationDate": "registration_metadata",
    "LetterRegistrationTime": "registration_metadata",
    "Classification": "classification_metadata",
    "TransferType": "classification_metadata",
    "DocType": "classification_metadata",
    "Priority": "classification_metadata",
    "Receivers": "recipient_metadata",
    "ReceiverDeps": "recipient_metadata",
    "ReceiverCeremonialUnits": "recipient_metadata",
    "ccReceivers": "cc_metadata",
    "ccReceiverDeps": "cc_metadata",
    "ccReceiverCeremonialUnits": "cc_metadata",
    "SenderSignerBehalfName": "sender_signature_metadata",
    "SignNumberOfSender": "sender_signature_metadata",
    "SignOfSenderStart†SignOfSenderEnd": "sender_signature_image",
    "ShamsQRcodeStart†ShamsQRcodeEnd": "qr_code_image",
    "shamsBarcode": "barcode_image",
    "Slogan": "slogan_asset_unclassified",
    "SignsStart†SignsEnd": "external_signature_parameter",
}


@dataclass(frozen=True)
class BaseWordField:
    """One of the 40 non-indexed identifiers in the captured WordConfig."""

    position: int
    field_id: str
    category: str


@dataclass(frozen=True)
class WordConfigFieldCatalog:
    """Ordered classification of the captured 40 base + indexed signer fields."""

    base_fields: tuple[BaseWordField, ...]
    indexed_signer_fields: tuple[tuple[int, IndexedSignerField], ...]
    unknown_fields: tuple[tuple[int, str], ...]
    duplicate_field_ids: tuple[str, ...]


def classify_base_word_field(field_id: str) -> str | None:
    """Return a category only for an exact field ID from the captured schema."""
    if not isinstance(field_id, str):
        raise TypeError("field_id_must_be_text")
    return _BASE_FIELD_CATEGORIES.get(field_id)


def build_word_config_field_catalog(
    field_ids: tuple[str, ...] | list[str],
) -> WordConfigFieldCatalog:
    """Classify known base and signer IDs, preserving every original position."""
    seen: set[str] = set()
    duplicates: list[str] = []
    base: list[BaseWordField] = []
    signer: list[tuple[int, IndexedSignerField]] = []
    unknown: list[tuple[int, str]] = []
    for position, field_id in enumerate(field_ids):
        if not isinstance(field_id, str):
            raise TypeError("field_id_must_be_text")
        if field_id in seen and field_id not in duplicates:
            duplicates.append(field_id)
        seen.add(field_id)
        category = classify_base_word_field(field_id)
        if category is not None:
            base.append(BaseWordField(position, field_id, category))
            continue
        indexed = parse_indexed_signer_field(field_id)
        if indexed is not None:
            signer.append((position, indexed))
            continue
        unknown.append((position, field_id))
    return WordConfigFieldCatalog(
        base_fields=tuple(base),
        indexed_signer_fields=tuple(signer),
        unknown_fields=tuple(unknown),
        duplicate_field_ids=tuple(duplicates),
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
    # Record each occurrence's actual position in one pass. Using
    # field_ids.index(field_id) loses the position of repeated identifiers
    # (it always returns the first occurrence) and makes this audit O(n²).
    by_index: dict[int, list[tuple[int, IndexedSignerField]]] = {}
    for position, field_id in enumerate(field_ids):
        parsed = parse_indexed_signer_field(field_id)
        if parsed is not None:
            by_index.setdefault(parsed.index, []).append((position, parsed))
    expected_families = tuple(family for family, _pattern in _SIGNER_PATTERNS)
    slots = []
    for index in sorted(by_index):
        fields = tuple(field for _position, field in sorted(by_index[index], key=lambda item: item[0]))
        present = {field.family for field in fields}
        slots.append(IndexedSignerSlot(
            index=index,
            fields=fields,
            missing_families=tuple(family for family in expected_families if family not in present),
        ))
    return tuple(slots)


__all__ = [
    "BaseWordField",
    "IndexedSignerField",
    "WordConfigFieldCatalog",
    "build_word_config_field_catalog",
    "classify_base_word_field",
    "IndexedSignerSlot",
    "build_indexed_signer_slots",
    "group_indexed_signer_fields",
    "parse_indexed_signer_field",
]
