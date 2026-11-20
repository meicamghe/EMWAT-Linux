"""Metadata-only evidence report for WordConfig and Writer structures.

This module deliberately does not infer field mappings or expose field values.
It summarizes the two sides of a sanitized fixture so an engineer can compare
identifiers and structural inventories without mutating a Writer document.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from emwat_linux.word_config import WordDocumentConfig
from emwat_linux.writer_inspector import WriterDocumentCatalog


@dataclass(frozen=True)
class WordConfigFieldEvidence:
    field_id: str
    mimetype: str | None
    encoding: str | None
    external_parameter: str | None
    is_image: bool
    is_plain_text: bool


@dataclass(frozen=True)
class WordWriterEvidenceReport:
    fields: tuple[WordConfigFieldEvidence, ...]
    duplicate_field_ids: tuple[str, ...]
    settings_names: tuple[str, ...]
    optional_attribute_ids: tuple[str, ...]
    requested_type_attributes: tuple[tuple[tuple[str, str], ...], ...]
    writer_bookmark_names: tuple[str, ...]
    writer_named_range_names: tuple[str, ...]
    writer_section_names: tuple[str, ...]
    writer_table_names: tuple[str, ...]
    writer_frame_names: tuple[str, ...]
    writer_graphic_object_names: tuple[str, ...]
    writer_custom_property_names: tuple[str, ...]
    writer_docinfo_custom_field_names: tuple[str, ...]


def build_word_writer_evidence_report(
    config: WordDocumentConfig,
    writer_catalog: WriterDocumentCatalog,
) -> WordWriterEvidenceReport:
    """Summarize identifiers and metadata only; never read values or mutate UNO."""
    evidence: list[WordConfigFieldEvidence] = []
    field_ids: list[str] = []
    for field in config.fields:
        field_id = field.field_id
        field_ids.append(field_id)
        mimetype = field.attributes.get("mimetype")
        evidence.append(
            WordConfigFieldEvidence(
                field_id=field_id,
                mimetype=mimetype,
                encoding=field.attributes.get("encryption"),
                external_parameter=field.attributes.get("paramId"),
                is_image=bool(mimetype and mimetype.casefold().startswith("image/")),
                is_plain_text=mimetype == "text/plain",
            )
        )

    duplicates = tuple(
        name for name, count in Counter(field_ids).items() if count > 1
    )
    return WordWriterEvidenceReport(
        fields=tuple(evidence),
        duplicate_field_ids=duplicates,
        settings_names=tuple(setting.name for setting in config.settings),
        optional_attribute_ids=tuple(
            attribute.attributes.get("id", "") for attribute in config.optional_attributes
        ),
        requested_type_attributes=tuple(
            tuple(sorted(attributes.items())) for attributes in config.requested_types
        ),
        writer_bookmark_names=writer_catalog.bookmarks,
        writer_named_range_names=writer_catalog.named_ranges,
        writer_section_names=writer_catalog.text_sections,
        writer_table_names=writer_catalog.text_tables,
        writer_frame_names=writer_catalog.text_frames,
        writer_graphic_object_names=writer_catalog.graphic_objects,
        writer_custom_property_names=writer_catalog.custom_document_properties_in_info_order,
        writer_docinfo_custom_field_names=tuple(
            field.custom_property_name
            for field in writer_catalog.text_fields
            if field.custom_property_name is not None
        ),
    )


__all__ = [
    "WordConfigFieldEvidence",
    "WordWriterEvidenceReport",
    "build_word_writer_evidence_report",
]
