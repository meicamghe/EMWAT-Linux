"""Per-field decoding for the captured wordConfig XML schema.

Decoding is driven by each field's own encryption attribute. Unknown encodings
are rejected instead of being silently interpreted as plain text.
"""
from __future__ import annotations

import base64
import binascii
import re
from dataclasses import dataclass
from typing import Mapping
from urllib.parse import unquote

from emwat_linux.word_config import WordDocumentConfig


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
    separator to distinguish TXmlWordConfigTwinField from TXmlWordConfigField.
    Empty sides fall back to a single identifier, matching its observed branch.
    """
    first, separator, remainder = field_id.partition("†")
    if separator and first and remainder:
        return WordFieldIdentifier(first=first, second=remainder)
    return WordFieldIdentifier(first=field_id)


def extract_docproperty_identifier(field_code: str) -> str:
    """Mirror EMWAT's DOCPROPERTY field-code extraction.

    The native helper first searches case-sensitively for DOCPROPERTY.
    It then copies up to 255 characters after the first double-space token
    and, when that copied segment contains a further space, returns the first
    token. If either search branch does not match, it preserves the input.
    This intentionally mirrors the observed legacy parser rather than
    normalizing arbitrary Word field-code syntax.
    """
    if "DOCPROPERTY" not in field_code:
        return field_code
    separator = field_code.find("  ")
    # Delphi Pos returns 0 when absent; Copy(..., Pos + 2, ...) is 1-based.
    start = separator + 1 if separator >= 0 else 1
    segment = field_code[start : start + 255]
    next_space = segment.find(" ")
    if next_space < 0:
        return field_code
    return segment[:next_space]


@dataclass(frozen=True)
class DecodedWordField:
    field_id: str
    identifier: WordFieldIdentifier
    value: str | bytes
    mimetype: str | None
    encoding: str | None
    external_parameter: str | None
    attributes: Mapping[str, str]


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
            return unquote(text, encoding="utf-8", errors="strict")
        except (UnicodeDecodeError, ValueError) as exc:
            raise WordFieldDecodeError(f"field_url_decode_failed:{field_id}") from exc
    if normalized == "base64":
        try:
            compact = "".join(text.split())
            return base64.b64decode(compact.encode("ascii"), validate=True)
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
