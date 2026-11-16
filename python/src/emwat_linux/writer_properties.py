"""Strict Writer custom-document-property updates for mapped EMWAT fields.

The caller must supply a verified property name. This module never creates
properties implicitly and never reads their current values.
"""
from __future__ import annotations


class WriterPropertyUpdateError(RuntimeError):
    """Raised when a mapped Writer custom property cannot be updated."""


def set_custom_document_property(
    document: object,
    property_name: str,
    value: object,
) -> None:
    """Set an existing user-defined document property by its exact name."""
    if not isinstance(property_name, str) or not property_name:
        raise ValueError("custom_property_name_required")
    try:
        properties = document.getDocumentProperties().getUserDefinedProperties()
        info = properties.getPropertySetInfo()
        if not info.hasPropertyByName(property_name):
            raise KeyError(f"custom_property_not_found:{property_name}")
        properties.setPropertyValue(property_name, value)
    except KeyError:
        raise
    except Exception as exc:
        raise WriterPropertyUpdateError(
            f"custom_property_update_failed:{property_name}"
        ) from exc


__all__ = ["WriterPropertyUpdateError", "set_custom_document_property"]
