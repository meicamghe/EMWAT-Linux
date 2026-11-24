"""Build explicit, type-safe Writer custom-property updates from WordConfig.

This module decodes source values but never chooses target property names.
Callers must supply a fixture-backed field-index-to-property-name mapping.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping as TypingMapping

from emwat_linux.word_config import WordDocumentConfig
from emwat_linux.word_fields import decode_word_fields


class WordConfigTextUpdateError(ValueError):
    """Raised when an explicit text-field mapping cannot be built safely."""


@dataclass(frozen=True)
class WordConfigTextUpdate:
    field_index: int
    field_id: str
    target_property_name: str
    value: str = field(repr=False)


def build_word_config_text_updates(
    config: WordDocumentConfig,
    target_names_by_field_index: Mapping[int, str],
) -> tuple[WordConfigTextUpdate, ...]:
    """Decode only text fields using explicit source-index to target-name rules.

    No matching or target inference occurs here. Image fields, external
    parameters, and non-text MIME types are rejected so binary payloads cannot
    be written into string properties by mistake.
    """
    if not isinstance(config, WordDocumentConfig):
        raise TypeError("invalid_word_document_config")
    if not isinstance(target_names_by_field_index, Mapping):
        raise TypeError("field_target_map_must_be_mapping")

    decoded = decode_word_fields(config)
    seen_targets: set[str] = set()
    updates: list[WordConfigTextUpdate] = []
    for field_index, target_name in target_names_by_field_index.items():
        if type(field_index) is not int or not 0 <= field_index < len(decoded):
            raise WordConfigTextUpdateError("source_field_index_invalid")
        if not isinstance(target_name, str) or not target_name or target_name.strip() != target_name:
            raise WordConfigTextUpdateError("target_property_name_invalid")
        folded_target = target_name.casefold()
        if folded_target in seen_targets:
            raise WordConfigTextUpdateError("duplicate_target_property_name")
        seen_targets.add(folded_target)

        source = decoded[field_index]
        if source.external_parameter:
            raise WordConfigTextUpdateError("external_parameter_not_text_property")
        if source.is_image:
            raise WordConfigTextUpdateError("image_field_not_text_property")
        if source.mimetype and source.mimetype.casefold() != "text/plain":
            raise WordConfigTextUpdateError("unsupported_text_field_mimetype")
        if not isinstance(source.value, str):
            raise WordConfigTextUpdateError("text_field_value_not_text")
        updates.append(WordConfigTextUpdate(
            field_index=field_index,
            field_id=source.field_id,
            target_property_name=target_name,
            value=source.value,
        ))
    return tuple(updates)


def as_custom_property_update_mapping(
    updates: tuple[WordConfigTextUpdate, ...],
) -> TypingMapping[str, str]:
    """Return an immutable target/value mapping for the strict Writer setter."""
    if not isinstance(updates, tuple) or any(
        not isinstance(item, WordConfigTextUpdate) for item in updates
    ):
        raise TypeError("invalid_word_config_text_updates")
    return MappingProxyType({
        item.target_property_name: item.value for item in updates
    })


__all__ = [
    "WordConfigTextUpdate",
    "WordConfigTextUpdateError",
    "as_custom_property_update_mapping",
    "build_word_config_text_updates",
]
