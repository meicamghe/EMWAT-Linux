"""Resolve WordConfig external-parameter references without guessing wire encoding.

The native request proves that fields may point at outer method parameters
(such as signData). This module binds those references to their exact opaque
outer values, but deliberately does not split, decode, join, or apply them.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from emwat_linux.word_config import WordDocumentConfig
from emwat_linux.word_fields import decode_word_fields


class ExternalParameterResolutionError(ValueError):
    """Raised when external parameter references cannot be safely inventoried."""


@dataclass(frozen=True)
class ExternalParameterBinding:
    field_index: int
    field_id: str
    parameter_id: str
    present: bool
    raw_value: str = field(repr=False)
    mimetype: str | None = None
    encryption: str | None = None
    separator: str | None = None
    concater: str | None = None
    concator: str | None = None

    @property
    def value_length(self) -> int:
        return len(self.raw_value)


def resolve_external_parameter_bindings(
    config: WordDocumentConfig,
    parameters: Mapping[str, str],
    *,
    max_parameter_chars: int = 64 * 1024 * 1024,
    max_total_parameter_chars: int = 96 * 1024 * 1024,
) -> tuple[ExternalParameterBinding, ...]:
    """Bind every paramId field to the exact outer parameter value.

    Missing outer parameters are represented as present=False with an empty
    raw value, matching the native dictionary lookup's empty fallback. A
    present-but-empty parameter remains distinguishable. Repeated references
    produce repeated bindings in WordConfig order.

    The three delimiter attributes are preserved independently. In particular,
    concater is never aliased to concator. No Base64/URL decoding or
    concatenation is performed because the native signData composition path
    has not yet been proven.
    """
    if not isinstance(config, WordDocumentConfig):
        raise TypeError("invalid_word_document_config")
    if not isinstance(parameters, Mapping):
        raise TypeError("outer_parameters_must_be_mapping")
    if type(max_parameter_chars) is not int or max_parameter_chars <= 0:
        raise ValueError("max_parameter_chars_must_be_positive")
    if type(max_total_parameter_chars) is not int or max_total_parameter_chars <= 0:
        raise ValueError("max_total_parameter_chars_must_be_positive")
    if any(not isinstance(key, str) or not isinstance(value, str)
           for key, value in parameters.items()):
        raise ExternalParameterResolutionError("outer_parameters_must_be_text")

    decoded = decode_word_fields(config)
    bindings: list[ExternalParameterBinding] = []
    total_chars = 0
    for index, item in enumerate(decoded):
        parameter_id = item.external_parameter
        if not parameter_id:
            continue
        present = parameter_id in parameters
        raw_value = parameters[parameter_id] if present else ""
        if len(raw_value) > max_parameter_chars:
            raise ExternalParameterResolutionError("external_parameter_size_exceeded")
        total_chars += len(raw_value)
        if total_chars > max_total_parameter_chars:
            raise ExternalParameterResolutionError("total_external_parameter_size_exceeded")
        attrs = item.attributes
        bindings.append(ExternalParameterBinding(
            field_index=index,
            field_id=item.field_id,
            parameter_id=parameter_id,
            present=present,
            raw_value=raw_value,
            mimetype=item.mimetype,
            encryption=item.encoding,
            separator=attrs.get("separator"),
            concater=attrs.get("concater"),
            concator=attrs.get("concator"),
        ))
    return tuple(bindings)


__all__ = [
    "ExternalParameterBinding",
    "ExternalParameterResolutionError",
    "resolve_external_parameter_bindings",
]
