"""Writer text-field operations used by the native document bridge."""
from __future__ import annotations


class WriterFieldRefreshError(RuntimeError):
    """Raised when LibreOffice cannot refresh Writer text fields."""


def refresh_writer_text_fields(document: object) -> None:
    """Refresh imported Word/Writer fields after document properties change.

    This updates displayed DOCPROPERTY results without reading their values.
    Call after a batch of custom-property updates rather than after each one.
    """
    try:
        document.getTextFields().refresh()
    except Exception as exc:
        raise WriterFieldRefreshError("writer_field_refresh_failed") from exc


__all__ = ["WriterFieldRefreshError", "refresh_writer_text_fields"]
