"""Metadata-only evidence report for WordConfig and Writer structures.

The report intentionally excludes document values and never proposes or applies
field mappings. It is a safe inventory for comparing sanitized fixtures.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from emwat_linux.word_config import WordDocumentConfig
from emwat_linux.writer_inspector import WriterDocumentCatalog


@dataclass(frozen=True)
class WordConfigFieldEvidence:
    index: int
    field_id: str
    mimetype: str | None
    encoding: str | None
    external_parameter: str | None
    is_image: bool
    is_plain_text: bool


@dataclass(frozen=True)
class OptionalAttributeEvidence:
    attribute_id: str
    value_type: str | None
    content_encoding: str | None
    has_content: bool


@dataclass(frozen=True)
class WordWriterEvidenceReport:
    root_attribute_names: tuple[str, ...]
    permission_attribute_names: tuple[str, ...]
    fields: tuple[WordConfigFieldEvidence, ...]
    duplicate_field_ids: tuple[str, ...]
    casefold_field_id_collisions: tuple[tuple[str, ...], ...]
    settings_names: tuple[str, ...]
    duplicate_setting_names: tuple[str, ...]
    optional_attributes: tuple[OptionalAttributeEvidence, ...]
    duplicate_optional_attribute_ids: tuple[str, ...]
    requested_type_attributes: tuple[tuple[tuple[str, str], ...], ...]
    writer_bookmark_names: tuple[str, ...]
    writer_named_range_names: tuple[str, ...]
    writer_section_names: tuple[str, ...]
    writer_table_names: tuple[str, ...]
    writer_frame_names: tuple[str, ...]
    writer_graphic_object_names: tuple[str, ...]
    writer_custom_property_names: tuple[str, ...]
    writer_custom_property_casefold_collisions: tuple[tuple[str, ...], ...]
    writer_docinfo_custom_field_names: tuple[str, ...]


def _duplicates(values: tuple[str, ...]) -> tuple[str, ...]:
    counts = Counter(values)
    return tuple(value for value in dict.fromkeys(values) if counts[value] > 1)


def _casefold_collisions(values: tuple[str, ...]) -> tuple[tuple[str, ...], ...]:
    groups: dict[str, list[str]] = {}
    for value in values:
        groups.setdefault(value.casefold(), []).append(value)
    return tuple(
        tuple(group)
        for group in groups.values()
        if len(group) > 1 and len(set(group)) > 1
    )


def build_word_writer_evidence_report(
    config: WordDocumentConfig,
    writer_catalog: WriterDocumentCatalog,
) -> WordWriterEvidenceReport:
    """Summarize identifiers and structural metadata only; never read values."""
    if not isinstance(config, WordDocumentConfig):
        raise TypeError("invalid_word_document_config")
    if not isinstance(writer_catalog, WriterDocumentCatalog):
        raise TypeError("invalid_writer_document_catalog")

    evidence: list[WordConfigFieldEvidence] = []
    field_ids: list[str] = []
    for index, field in enumerate(config.fields):
        field_id = field.field_id
        field_ids.append(field_id)
        mimetype = field.attributes.get("mimetype")
        evidence.append(
            WordConfigFieldEvidence(
                index=index,
                field_id=field_id,
                mimetype=mimetype,
                encoding=field.attributes.get("encryption"),
                external_parameter=field.attributes.get("paramId"),
                is_image=bool(mimetype and mimetype.casefold().startswith("image/")),
                is_plain_text=bool(mimetype and mimetype.casefold() == "text/plain"),
            )
        )

    field_id_tuple = tuple(field_ids)
    setting_names = tuple(setting.name for setting in config.settings)
    optional_ids = tuple(
        attribute.attributes.get("id", "") for attribute in config.optional_attributes
    )
    custom_names = writer_catalog.custom_document_properties_in_info_order
    return WordWriterEvidenceReport(
        root_attribute_names=tuple(sorted(config.root_attributes)),
        permission_attribute_names=tuple(sorted(config.permissions)),
        fields=tuple(evidence),
        duplicate_field_ids=_duplicates(field_id_tuple),
        casefold_field_id_collisions=_casefold_collisions(field_id_tuple),
        settings_names=setting_names,
        duplicate_setting_names=_duplicates(setting_names),
        optional_attributes=tuple(
            OptionalAttributeEvidence(
                attribute_id=attribute.attributes.get("id", ""),
                value_type=attribute.attributes.get("type"),
                content_encoding=attribute.content_attributes.get("encryption"),
                has_content=bool(attribute.content),
            )
            for attribute in config.optional_attributes
        ),
        duplicate_optional_attribute_ids=_duplicates(optional_ids),
        requested_type_attributes=tuple(
            tuple(sorted(attributes.items())) for attributes in config.requested_types
        ),
        writer_bookmark_names=writer_catalog.bookmarks,
        writer_named_range_names=writer_catalog.named_ranges,
        writer_section_names=writer_catalog.text_sections,
        writer_table_names=writer_catalog.text_tables,
        writer_frame_names=writer_catalog.text_frames,
        writer_graphic_object_names=writer_catalog.graphic_objects,
        writer_custom_property_names=custom_names,
        writer_custom_property_casefold_collisions=_casefold_collisions(custom_names),
        writer_docinfo_custom_field_names=tuple(
            field.custom_property_name
            for field in writer_catalog.text_fields
            if field.custom_property_name is not None
        ),
    )


__all__ = [
    "OptionalAttributeEvidence",
    "WordConfigFieldEvidence",
    "WordWriterEvidenceReport",
    "build_word_writer_evidence_report",
]
