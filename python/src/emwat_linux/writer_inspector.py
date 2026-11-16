"""Metadata-only inventory of LibreOffice Writer document structures.

The inspector intentionally excludes document text, field values, images, and
custom-property values. It is designed to map EMWAT field IDs to Writer
bookmarks, named ranges, text fields, sections, tables, and graphic objects.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WriterTextFieldInfo:
    implementation_name: str
    presentation: str
    property_names: tuple[str, ...]


@dataclass(frozen=True)
class WriterDocumentCatalog:
    bookmarks: tuple[str, ...]
    named_ranges: tuple[str, ...]
    text_sections: tuple[str, ...]
    text_tables: tuple[str, ...]
    text_frames: tuple[str, ...]
    graphic_objects: tuple[str, ...]
    document_indexes: tuple[str, ...]
    text_fields: tuple[WriterTextFieldInfo, ...]


def _element_names(container: object) -> tuple[str, ...]:
    getter = getattr(container, "getElementNames", None)
    if not callable(getter):
        return ()
    try:
        return tuple(sorted(str(name) for name in getter()))
    except Exception:
        return ()


def _container_names(document: object, method_name: str) -> tuple[str, ...]:
    try:
        getter = getattr(document, method_name)
        return _element_names(getter())
    except Exception:
        return ()


def _text_fields(document: object) -> tuple[WriterTextFieldInfo, ...]:
    try:
        fields = document.getTextFields()
        enumeration = fields.createEnumeration()
    except Exception:
        return ()

    result: list[WriterTextFieldInfo] = []
    while True:
        try:
            if not enumeration.hasMoreElements():
                break
            field = enumeration.nextElement()
        except Exception:
            break

        try:
            implementation = str(field.getImplementationName())
        except Exception:
            implementation = type(field).__name__
        try:
            presentation = str(field.getPresentation(False))
        except Exception:
            presentation = ""
        try:
            properties = tuple(
                sorted(str(item.Name) for item in field.getPropertySetInfo().getProperties())
            )
        except Exception:
            properties = ()
        result.append(
            WriterTextFieldInfo(
                implementation_name=implementation,
                presentation=presentation,
                property_names=properties,
            )
        )
    return tuple(result)


def inspect_writer_document(document: object) -> WriterDocumentCatalog:
    """Return structural names and text-field metadata without document values."""
    return WriterDocumentCatalog(
        bookmarks=_container_names(document, "getBookmarks"),
        named_ranges=_container_names(document, "getNamedRanges"),
        text_sections=_container_names(document, "getTextSections"),
        text_tables=_container_names(document, "getTextTables"),
        text_frames=_container_names(document, "getTextFrames"),
        graphic_objects=_container_names(document, "getGraphicObjects"),
        document_indexes=_container_names(document, "getDocumentIndexes"),
        text_fields=_text_fields(document),
    )


__all__ = ["WriterDocumentCatalog", "WriterTextFieldInfo", "inspect_writer_document"]
