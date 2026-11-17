"""Per-field decoding for the captured wordConfig XML schema.

Decoding is driven by each field's own encryption attribute. Unknown encodings
are rejected instead of being silently interpreted as plain text.
"""
from __future__ import annotations

import base64
import binascii
import re
from dataclasses import dataclass
from typing import Mapping, Sequence
from urllib.parse import unquote_plus

from emwat_linux.word_config import WordDocumentConfig, WordField


class WordFieldDecodeError(ValueError):
    """Raised when a field's declared encoding cannot be decoded safely."""


@dataclass(frozen=True)
class WordFieldIdentifier:
    """A Word field key, optionally represented as an EMWAT twin-field pair."""

    first: str
    second: str | None = None

    @property
    def is_twin(self) -> bool:
        return self.second is not None


def parse_word_field_identifier(field_id: str) -> WordFieldIdentifier:
    """Split the observed U+2020 twin-field delimiter once.

    The native AddCustomDocPropertiesToDic routine uses the first dagger
    separator to choose a TXmlWordConfigTwinField versus TXmlWordConfigField.
    Empty sides fall back to a single descriptor, matching its observed branch.
    """
    first, separator, remainder = field_id.partition("†")
    if separator and first and remainder:
        return WordFieldIdentifier(first=first, second=remainder)
    return WordFieldIdentifier(first=field_id)


@dataclass(frozen=True)
class SingleWordFieldDescriptor:
    """Native TXmlWordConfigField entry for one custom-property identifier."""

    index: int
    property_name: str
    xml_field: WordField | None


@dataclass(frozen=True)
class TwinWordFieldDescriptor:
    """Native TXmlWordConfigTwinField entry for a dagger-separated pair."""

    index: int
    property_name: str
    first_field_name: str
    second_field_name: str
    xml_field: WordField | None = None


def resolve_twin_field_partner(
    descriptor: TwinWordFieldDescriptor,
    requested_field_name: str,
) -> str | None:
    """Return the opposite member using EMWAT's case-insensitive CompareText.

    GetXmlFieldInfo compares the requested field name with both descriptor
    members using System.SysUtils.CompareText. A match on the first member
    returns the second, and vice versa; a non-match returns None.
    """
    requested = requested_field_name.casefold()
    if requested == descriptor.first_field_name.casefold():
        return descriptor.second_field_name
    if requested == descriptor.second_field_name.casefold():
        return descriptor.first_field_name
    return None


@dataclass(frozen=True)
class WordCustomPropertyFieldMaps:
    """Single/twin descriptor entries populated from ordered custom properties."""

    singles: tuple[SingleWordFieldDescriptor, ...]
    twins: tuple[TwinWordFieldDescriptor, ...]

    @property
    def single_by_property_name(self) -> Mapping[str, SingleWordFieldDescriptor]:
        return {item.property_name: item for item in self.singles}

    @property
    def twin_by_property_name(self) -> Mapping[str, TwinWordFieldDescriptor]:
        return {item.property_name: item for item in self.twins}


def build_word_custom_property_field_maps(
    property_names: Sequence[str],
    *,
    xml_fields: Sequence[WordField] | None = None,
) -> WordCustomPropertyFieldMaps:
    """Build native-shaped descriptors in custom-property enumeration order.

    The native AddCustomDocPropertiesToDic routine assigns a zero-based index
    to each Word CustomDocumentProperties item, retrieves the corresponding
    IXMLFieldType object from wordConfig.fields at the same index, and inserts
    a descriptor under the original (unsplit) property name. The first dagger
    separates twin members; empty sides follow the native single-field branch.

    Pass xml_fields in the exact corresponding wordConfig field order. The
    descriptor retains the full WordField node (attributes and text), matching
    the native interface reference stored in TXmlWordConfigField/TwinField.
    If omitted, the reference remains None. When supplied, the two sequences
    must have equal lengths so index alignment cannot silently drift.
    """
    if xml_fields is not None and len(xml_fields) != len(property_names):
        raise ValueError("xml_fields_must_match_property_names_length")

    singles: list[SingleWordFieldDescriptor] = []
    twins: list[TwinWordFieldDescriptor] = []
    seen_single_names: set[str] = set()
    seen_twin_names: set[str] = set()
    for index, property_name in enumerate(property_names):
        xml_field = xml_fields[index] if xml_fields is not None else None
        identifier = parse_word_field_identifier(property_name)
        if identifier.is_twin:
            if property_name in seen_twin_names:
                raise ValueError(f"duplicate_twin_custom_property_name:{property_name}")
            seen_twin_names.add(property_name)
            twins.append(
                TwinWordFieldDescriptor(
                    index=index,
                    property_name=property_name,
                    first_field_name=identifier.first,
                    second_field_name=identifier.second or "",
                    xml_field=xml_field,
                )
            )
        else:
            if property_name in seen_single_names:
                raise ValueError(f"duplicate_single_custom_property_name:{property_name}")
            seen_single_names.add(property_name)
            singles.append(
                SingleWordFieldDescriptor(
                    index=index,
                    property_name=property_name,
                    xml_field=xml_field,
                )
            )
    return WordCustomPropertyFieldMaps(
        singles=tuple(singles),
        twins=tuple(twins),
    )


_NATIVE_BUSINESS_SIGNATURE_END = re.compile(r"^sign.*end[0-2]?[0-9]?$")


def is_native_business_signature_end(field_name: str) -> bool:
    """Match the exact signature-end exclusion used by GetDocFieldIndex.

    Native code calls System.RegularExpressions.TRegEx.IsMatch with the
    case-sensitive pattern ^sign.*end[0-2]?[0-9]?$. Matching active-field
    names are logged as skipped by business logic. Pass the resolved active
    field name; do not assume every XML field ID is identical.
    """
    return _NATIVE_BUSINESS_SIGNATURE_END.fullmatch(field_name) is not None


def extract_docproperty_identifier(field_code: str) -> str:
    """Mirror EMWAT's DOCPROPERTY field-code extraction.

    The native helper searches case-sensitively for DOCPROPERTY. If absent,
    it preserves the input. Otherwise it copies up to 255 characters starting
    two characters after the first double-space position (or from character 2
    when that delimiter is absent), then truncates at the first single space
    if present. If no single space exists, it returns the copied segment.
    This intentionally preserves the native parser's odd edge cases.
    """
    if "DOCPROPERTY" not in field_code:
        return field_code
    separator = field_code.find("  ")
    # Delphi Pos returns 0 when absent; Copy(..., Pos + 2, ...) is 1-based.
    start = separator + 2
    segment = field_code[start : start + 255]
    next_space = segment.find(" ")
    if next_space < 0:
        return segment
    return segment[:next_space]


def find_native_twin_field_index(
    field_codes: Sequence[str],
    target_identifier: str,
    *,
    start_index: int = 1,
) -> int:
    """Find a twin-field partner using the native one-based Word Fields scan.

    FillTwinFields starts at start_index, extracts each Word Field.Code through
    FindFieldInActivefields, compares names with RTL CompareText (case-insensitive),
    and returns the first matching one-based index. Native code returns zero
    when no matching partner is found. Python casefold matches the observed
    ASCII field identifiers; locale-specific Unicode collation is unverified.
    """
    if start_index < 1:
        raise ValueError("start_index must be one-based and positive")
    for index in range(start_index, len(field_codes) + 1):
        if extract_docproperty_identifier(field_codes[index - 1]).casefold() == target_identifier.casefold():
            return index
    return 0


@dataclass(frozen=True)
class DecodedWordField:
    field_id: str
    identifier: WordFieldIdentifier
    value: str | bytes
    mimetype: str | None
    encoding: str | None
    external_parameter: str | None
    attributes: Mapping[str, str]

    @property
    def uses_native_text_field_path(self) -> bool:
        """Whether FillTextField takes its ordinary text/plain branch."""
        return self.mimetype == "text/plain"

    @property
    def is_image(self) -> bool:
        """Whether the native field metadata declares an image MIME type."""
        return bool(self.mimetype and self.mimetype.casefold().startswith("image/"))


@dataclass(frozen=True)
class DecodedOptionalAttribute:
    attribute_id: str
    value: str
    value_type: str | None
    encoding: str | None
    attributes: Mapping[str, str]


def _decode_value(text: str, encoding: str | None, *, field_id: str) -> str | bytes:
    normalized = (encoding or "").strip().lower()
    if not normalized:
        return text
    if normalized == "urlencoded":
        if re.search(r"%(?![0-9A-Fa-f]{2})", text):
            raise WordFieldDecodeError(f"field_url_decode_failed:{field_id}")
        try:
            return unquote_plus(text, encoding="utf-8", errors="strict")
        except (UnicodeDecodeError, ValueError) as exc:
            raise WordFieldDecodeError(f"field_url_decode_failed:{field_id}") from exc
    if normalized == "base64":
        try:
            # The native 7-Zip/Base64 decoder consumes fixed four-byte groups
            # through a strict lookup table; whitespace is not normalized.
            return base64.b64decode(text.encode("ascii"), validate=True)
        except (UnicodeEncodeError, binascii.Error, ValueError) as exc:
            raise WordFieldDecodeError(f"field_base64_decode_failed:{field_id}") from exc
    raise WordFieldDecodeError(f"unsupported_field_encoding:{field_id}:{normalized}")


def decode_word_fields(config: WordDocumentConfig) -> tuple[DecodedWordField, ...]:
    """Decode text/image fields independently while preserving their order."""
    decoded: list[DecodedWordField] = []
    for field in config.fields:
        attrs = field.attributes
        encoding = attrs.get("encryption")
        value = _decode_value(field.text, encoding, field_id=field.field_id)
        decoded.append(
            DecodedWordField(
                field_id=field.field_id,
                identifier=parse_word_field_identifier(field.field_id),
                value=value,
                mimetype=attrs.get("mimetype"),
                encoding=encoding,
                external_parameter=attrs.get("paramId"),
                attributes=attrs,
            )
        )
    return tuple(decoded)


def decode_optional_attributes(
    config: WordDocumentConfig,
) -> tuple[DecodedOptionalAttribute, ...]:
    """Decode optional-attribute content using its nested content metadata."""
    decoded: list[DecodedOptionalAttribute] = []
    for index, attribute in enumerate(config.optional_attributes):
        encoding = attribute.content_attributes.get("encryption")
        attribute_id = attribute.attributes.get("id", f"optional-{index}")
        value = _decode_value(attribute.content, encoding, field_id=attribute_id)
        if not isinstance(value, str):
            raise WordFieldDecodeError(
                f"optional_attribute_must_be_text:{attribute_id}"
            )
        decoded.append(
            DecodedOptionalAttribute(
                attribute_id=attribute_id,
                value=value,
                value_type=attribute.attributes.get("type"),
                encoding=encoding,
                attributes=attribute.attributes,
            )
        )
    return tuple(decoded)


def external_parameter_bindings(
    fields: tuple[DecodedWordField, ...],
) -> tuple[DecodedWordField, ...]:
    """Return fields whose values are supplied by a separate method parameter.

    The caller must resolve these against the original method parameter map.
    This function deliberately does not split or concatenate signData because
    the exact separator/concater semantics have not been fully validated.
    """
    return tuple(field for field in fields if field.external_parameter)
