"""Strict Writer custom-document-property updates for mapped EMWAT fields.

The caller must supply verified property names. This module never creates
properties implicitly and captures old values to compensate partial updates.
"""
from __future__ import annotations

from collections.abc import Mapping


class WriterPropertyUpdateError(RuntimeError):
    """Raised when a mapped Writer custom property cannot be updated."""


def set_custom_document_properties(
    document: object,
    updates: Mapping[str, str],
) -> None:
    """Update a batch of existing string properties after validating all names.

    Every property name is checked before the first mutation, so an unknown
    mapping cannot leave an otherwise valid prefix of the batch applied.
    """
    if not isinstance(updates, Mapping):
        raise TypeError("custom_property_updates_must_be_mapping")
    items = tuple(updates.items())
    if not items:
        return

    for property_name, value in items:
        if not isinstance(property_name, str) or not property_name:
            raise ValueError("custom_property_name_required")
        if not isinstance(value, str):
            raise TypeError("custom_property_value_must_be_text")

    try:
        properties = document.getDocumentProperties().getUserDefinedProperties()
        info = properties.getPropertySetInfo()
        missing = tuple(
            name for name, _value in items if not info.hasPropertyByName(name)
        )
        if missing:
            raise KeyError("custom_property_not_found:" + ",".join(missing))

        # Capture previous values before the first mutation. UNO has no
        # transaction primitive for user-defined properties, so roll back
        # already-applied entries if a later setter fails.
        previous = tuple(
            (name, properties.getPropertyValue(name)) for name, _value in items
        )
        attempted: list[str] = []
        for property_name, value in items:
            # Include the currently failing setter in compensation: an UNO
            # implementation may mutate before surfacing an exception.
            attempted.append(property_name)
            try:
                properties.setPropertyValue(property_name, value)
            except Exception as exc:
                rollback_failed = False
                previous_by_name = dict(previous)
                for attempted_name in reversed(attempted):
                    try:
                        properties.setPropertyValue(
                            attempted_name, previous_by_name[attempted_name]
                        )
                    except Exception:
                        rollback_failed = True
                if rollback_failed:
                    raise WriterPropertyUpdateError(
                        "custom_property_update_failed_and_rollback_incomplete"
                    ) from exc
                raise WriterPropertyUpdateError(
                    f"custom_property_update_failed:{property_name}"
                ) from exc
    except (KeyError, TypeError, ValueError, WriterPropertyUpdateError):
        raise
    except Exception as exc:
        raise WriterPropertyUpdateError("custom_property_batch_update_failed") from exc


def set_custom_document_property(
    document: object,
    property_name: str,
    value: object,
) -> None:
    """Set one existing user-defined document property by its exact name."""
    if not isinstance(value, str):
        raise TypeError("custom_property_value_must_be_text")
    set_custom_document_properties(document, {property_name: value})


__all__ = [
    "WriterPropertyUpdateError",
    "set_custom_document_properties",
    "set_custom_document_property",
]
