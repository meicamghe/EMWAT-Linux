"""Parser for the Base64-encoded wordConfig XML document.

The outer EMWAT method envelope and this inner configuration document are
separate protocol layers. Field values are preserved as opaque text; the
per-field encoding attributes are metadata, not an instruction to decode here.
"""
from __future__ import annotations

from dataclasses import dataclass
import base64
import binascii
from types import MappingProxyType
from typing import Mapping
import xml.etree.ElementTree as ET


class WordConfigError(ValueError):
    """Raised when an encoded wordConfig document is invalid."""


@dataclass(frozen=True)
class WordField:
    attributes: Mapping[str, str]
    text: str

    @property
    def field_id(self) -> str:
        return self.attributes.get("id", "")


@dataclass(frozen=True)
class WordSetting:
    name: str
    value: str


@dataclass(frozen=True)
class OptionalAttribute:
    attributes: Mapping[str, str]
    content_attributes: Mapping[str, str]
    content: str


@dataclass(frozen=True)
class WordDocumentConfig:
    root_attributes: Mapping[str, str]
    permissions: Mapping[str, str]
    settings: tuple[WordSetting, ...]
    fields: tuple[WordField, ...]
    optional_attributes: tuple[OptionalAttribute, ...]
    requested_types: tuple[Mapping[str, str], ...]


def _immutable(values: Mapping[str, str]) -> Mapping[str, str]:
    return MappingProxyType(dict(values))


def parse_word_config(
    encoded: str,
    *,
    max_encoded_chars: int = 24 * 1024 * 1024,
    max_decoded_bytes: int = 16 * 1024 * 1024,
) -> WordDocumentConfig:
    """Decode and parse one captured-style Base64 <word-document> document.

    XML whitespace in the Base64 text is accepted. XML field values are never
    URL-decoded or Base64-decoded by this parser.
    """
    if not isinstance(encoded, str):
        raise TypeError("encoded wordConfig must be text")
    limits = (max_encoded_chars, max_decoded_bytes)
    if any(type(limit) is not int or limit <= 0 for limit in limits):
        raise ValueError("size limits must be positive integers")
    if not encoded or len(encoded) > max_encoded_chars:
        raise WordConfigError("encoded_size_invalid")

    try:
        compact = "".join(encoded.split())
        raw = base64.b64decode(compact.encode("ascii"), validate=True)
    except (UnicodeEncodeError, binascii.Error, ValueError) as exc:
        raise WordConfigError("invalid_base64") from exc

    if not raw or len(raw) > max_decoded_bytes:
        raise WordConfigError("decoded_size_invalid")
    upper = raw.upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise WordConfigError("doctype_or_entity_forbidden")

    try:
        xml_text = raw.decode("utf-8", errors="strict")
        root = ET.fromstring(xml_text)
    except (UnicodeDecodeError, ET.ParseError) as exc:
        raise WordConfigError("malformed_xml") from exc

    if root.tag != "word-document":
        raise WordConfigError("unexpected_root")

    permissions: dict[str, str] = {}
    settings: list[WordSetting] = []
    fields: list[WordField] = []
    optional_attributes: list[OptionalAttribute] = []
    requested_types: list[Mapping[str, str]] = []

    for section in root:
        if section.tag == "permission":
            if permissions:
                raise WordConfigError("duplicate_permission_section")
            permissions = dict(section.attrib)
            if list(section):
                raise WordConfigError("unexpected_permission_children")
        elif section.tag == "settings":
            for setting in section:
                if setting.tag != "setting":
                    raise WordConfigError("unexpected_settings_child")
                name = setting.attrib.get("name", "")
                if not name:
                    raise WordConfigError("setting_name_missing")
                if list(setting):
                    raise WordConfigError("nested_setting_content")
                settings.append(WordSetting(name=name, value=setting.text or ""))
        elif section.tag == "fields":
            for field in section:
                if field.tag != "field":
                    raise WordConfigError("unexpected_fields_child")
                if not field.attrib.get("id"):
                    raise WordConfigError("field_id_missing")
                if list(field):
                    raise WordConfigError("nested_field_content")
                fields.append(
                    WordField(
                        attributes=_immutable(field.attrib),
                        text=field.text or "",
                    )
                )
        elif section.tag == "optional-attributes":
            for attribute in section:
                if attribute.tag != "attribute":
                    raise WordConfigError("unexpected_optional_attribute_child")
                content_nodes = list(attribute)
                if len(content_nodes) > 1 or any(node.tag != "content" for node in content_nodes):
                    raise WordConfigError("invalid_optional_attribute_content")
                content_node = content_nodes[0] if content_nodes else None
                optional_attributes.append(
                    OptionalAttribute(
                        attributes=_immutable(attribute.attrib),
                        content_attributes=_immutable(content_node.attrib if content_node is not None else {}),
                        content=(content_node.text or "") if content_node is not None else (attribute.text or ""),
                    )
                )
        elif section.tag == "requested-types":
            for requested_type in section:
                if requested_type.tag != "type":
                    raise WordConfigError("unexpected_requested_type_child")
                requested_types.append(_immutable(requested_type.attrib))
        # Unknown top-level sections are ignored for forward compatibility.

    return WordDocumentConfig(
        root_attributes=_immutable(root.attrib),
        permissions=_immutable(permissions),
        settings=tuple(settings),
        fields=tuple(fields),
        optional_attributes=tuple(optional_attributes),
        requested_types=tuple(requested_types),
    )
