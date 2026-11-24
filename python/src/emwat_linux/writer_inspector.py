"""Metadata-only inventory of LibreOffice Writer document structures.

The inspector intentionally excludes document text, field values, images, and
custom-property values. It is designed to map EMWAT field IDs to Writer
bookmarks, named ranges, text fields, custom-property names, sections, tables, and graphic objects.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WriterTextFieldInfo:
    implementation_name: str
    property_names: tuple[str, ...]
    supported_services: tuple[str, ...] = ()
    custom_property_name: str | None = None


@dataclass(frozen=True)
class WriterGraphicObjectInfo:
    name: str
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
    custom_document_properties: tuple[str, ...]
    custom_document_properties_in_info_order: tuple[str, ...]
    inspection_warnings: tuple[str, ...] = ()
    graphic_object_details: tuple[WriterGraphicObjectInfo, ...] = ()


def _element_names(container: object, warning_code: str, warnings: list[str]) -> tuple[str, ...]:
    getter = getattr(container, "getElementNames", None)
    if not callable(getter):
        warnings.append(warning_code)
        return ()
    try:
        return tuple(sorted(str(name) for name in getter()))
    except Exception:
        warnings.append(warning_code)
        return ()


def _container_names(document: object, method_name: str, warnings: list[str]) -> tuple[str, ...]:
    try:
        getter = getattr(document, method_name)
        return _element_names(getter(), f"{method_name}_unavailable", warnings)
    except Exception:
        warnings.append(f"{method_name}_unavailable")
        return ()


def _text_fields(document: object, warnings: list[str]) -> tuple[WriterTextFieldInfo, ...]:
    try:
        fields = document.getTextFields()
        enumeration = fields.createEnumeration()
    except Exception:
        warnings.append("text_fields_unavailable")
        return ()

    result: list[WriterTextFieldInfo] = []
    while True:
        try:
            if not enumeration.hasMoreElements():
                break
            field = enumeration.nextElement()
        except Exception:
            warnings.append("text_field_enumeration_incomplete")
            break

        try:
            implementation = str(field.getImplementationName())
        except Exception:
            implementation = type(field).__name__
            warnings.append("text_field_implementation_name_unavailable")
        try:
            properties = tuple(
                sorted(str(item.Name) for item in field.getPropertySetInfo().getProperties())
            )
        except Exception:
            properties = ()
            warnings.append("text_field_properties_unavailable")
        try:
            services = tuple(sorted(str(item) for item in field.getSupportedServiceNames()))
        except Exception:
            services = ()
            warnings.append("text_field_services_unavailable")
        custom_property_name = None
        if "com.sun.star.text.TextField.DocInfo.Custom" in services:
            try:
                custom_property_name = str(field.getPropertyValue("Name"))
            except Exception:
                custom_property_name = None
                warnings.append("custom_text_field_name_unavailable")
        result.append(
            WriterTextFieldInfo(
                implementation_name=implementation,
                property_names=properties,
                supported_services=services,
                custom_property_name=custom_property_name,
            )
        )
    return tuple(result)


def _graphic_object_details(
    document: object, warnings: list[str]
) -> tuple[WriterGraphicObjectInfo, ...]:
    """Inventory graphic property names only; never read GraphicURL or bytes."""
    try:
        container = document.getGraphicObjects()
        names = tuple(sorted(str(name) for name in container.getElementNames()))
    except Exception:
        warnings.append("graphic_object_details_unavailable")
        return ()

    details: list[WriterGraphicObjectInfo] = []
    for name in names:
        try:
            graphic = container.getByName(name)
            properties = tuple(sorted(
                str(item.Name)
                for item in graphic.getPropertySetInfo().getProperties()
            ))
            details.append(WriterGraphicObjectInfo(name, properties))
        except Exception:
            warnings.append("graphic_object_properties_unavailable")
    return tuple(details)


def _custom_document_property_names_in_info_order(document: object, warnings: list[str]) -> tuple[str, ...]:
    """Return custom-property names in UNO PropertySetInfo order, without sorting."""
    try:
        properties = document.getDocumentProperties().getUserDefinedProperties()
        info = properties.getPropertySetInfo()
        return tuple(str(item.Name) for item in info.getProperties())
    except Exception:
        warnings.append("custom_document_properties_unavailable")
        return ()


def inspect_writer_document(document: object) -> WriterDocumentCatalog:
    """Return structural names and text-field metadata without document values."""
    warnings: list[str] = []
    custom_names_in_info_order = _custom_document_property_names_in_info_order(
        document, warnings
    )
    graphic_details = _graphic_object_details(document, warnings)
    return WriterDocumentCatalog(
        bookmarks=_container_names(document, "getBookmarks", warnings),
        named_ranges=_container_names(document, "getNamedRanges", warnings),
        text_sections=_container_names(document, "getTextSections", warnings),
        text_tables=_container_names(document, "getTextTables", warnings),
        text_frames=_container_names(document, "getTextFrames", warnings),
        graphic_objects=_container_names(document, "getGraphicObjects", warnings),
        document_indexes=_container_names(document, "getDocumentIndexes", warnings),
        text_fields=_text_fields(document, warnings),
        custom_document_properties=tuple(sorted(custom_names_in_info_order)),
        custom_document_properties_in_info_order=custom_names_in_info_order,
        inspection_warnings=tuple(dict.fromkeys(warnings)),
        graphic_object_details=graphic_details,
    )


__all__ = [
    "WriterDocumentCatalog",
    "WriterGraphicObjectInfo",
    "WriterTextFieldInfo",
    "inspect_writer_document",
]
