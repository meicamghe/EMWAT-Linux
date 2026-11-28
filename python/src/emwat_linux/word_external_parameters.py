"""Resolve WordConfig external-parameter references without guessing wire encoding.

This module binds paramId metadata to exact outer request values. It deliberately
does not split, decode, join, or apply opaque payloads such as signData.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from emwat_linux.word_config import WordDocumentConfig


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
    """Bind every paramId field to its exact outer parameter value.

    Missing values are represented as present=False and empty raw text; a
    present-but-empty parameter remains distinguishable. Repeated references
    are preserved in WordConfig order, while size accounting counts each
    distinct outer parameter only once.

    Fields are read structurally without decoding unrelated field payloads.
    The separator, concater, and concator attributes remain independent. No
    Base64/URL decoding or concatenation is performed because native signData
    composition has not yet been proven.
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

    bindings: list[ExternalParameterBinding] = []
    accounted_parameters: set[str] = set()
    total_chars = 0
    for index, field_node in enumerate(config.fields):
        attrs = field_node.attributes
        parameter_id = attrs.get("paramId")
        if not parameter_id:
            continue
        present = parameter_id in parameters
        raw_value = parameters[parameter_id] if present else ""
        if len(raw_value) > max_parameter_chars:
            raise ExternalParameterResolutionError("external_parameter_size_exceeded")
        if present and parameter_id not in accounted_parameters:
            total_chars += len(raw_value)
            accounted_parameters.add(parameter_id)
            if total_chars > max_total_parameter_chars:
                raise ExternalParameterResolutionError("total_external_parameter_size_exceeded")
        bindings.append(ExternalParameterBinding(
            field_index=index,
            field_id=field_node.field_id,
            parameter_id=parameter_id,
            present=present,
            raw_value=raw_value,
            mimetype=attrs.get("mimetype"),
            encryption=attrs.get("encryption"),
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
