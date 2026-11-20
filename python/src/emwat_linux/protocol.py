"""Conservative parser for the recovered EMWAT XML method envelope.

Only the outer envelope is interpreted here. Parameter values remain opaque
Unicode text; document-specific XML/Base64 decoding belongs to later adapters.
"""
from __future__ import annotations

from dataclasses import dataclass
import base64
from types import MappingProxyType
from typing import Mapping
import xml.etree.ElementTree as ET


@dataclass(frozen=True)
class MethodCall:
    class_name: str
    params: Mapping[str, str]
    version: str


class ProtocolError(ValueError):
    """Raised when an incoming EMWAT method envelope is invalid."""


def parse_method_call(payload: bytes, *, max_bytes: int = 16 * 1024 * 1024) -> MethodCall:
    """Parse one UTF-8 <emwat><method class=...><param name=...> envelope.

    Runtime traces confirm the outer element names and attributes. This parser
    deliberately does not interpret invoke query values or parameter contents.
    """
    if not isinstance(payload, bytes):
        raise TypeError("payload must be bytes")
    if type(max_bytes) is not int or max_bytes <= 0:
        raise ValueError("max_bytes must be a positive integer")
    if not payload or len(payload) > max_bytes:
        raise ProtocolError("payload_size_invalid")

    # Reject DTD/entity declarations before handing input to the XML parser.
    upper_payload = payload.upper()
    if b"<!DOCTYPE" in upper_payload or b"<!ENTITY" in upper_payload:
        raise ProtocolError("doctype_or_entity_forbidden")

    try:
        text = payload.decode("utf-8", errors="strict")
        root = ET.fromstring(text)
    except (UnicodeDecodeError, ET.ParseError) as exc:
        raise ProtocolError("malformed_xml") from exc

    if root.tag != "emwat":
        raise ProtocolError("unexpected_root")
    version = root.attrib.get("version", "")
    if version != "1.0":
        raise ProtocolError("unsupported_version")

    methods = list(root)
    if len(methods) != 1 or methods[0].tag != "method":
        raise ProtocolError("expected_single_method")
    method = methods[0]
    class_name = method.attrib.get("class", "")
    if not class_name or class_name != class_name.strip():
        raise ProtocolError("invalid_method_class")

    params: dict[str, str] = {}
    for child in method:
        if child.tag != "param":
            raise ProtocolError("unexpected_method_child")
        name = child.attrib.get("name", "")
        if not name or name != name.strip():
            raise ProtocolError("invalid_parameter_name")
        if name in params:
            raise ProtocolError("duplicate_parameter")
        if len(child):
            raise ProtocolError("nested_parameter_content")
        params[name] = child.text or ""

    return MethodCall(
        class_name=class_name,
        params=MappingProxyType(params),
        version=version,
    )


# Observed in the 2026-11-15 TCP capture for EditWordDocument responses.
WORD_RESPONSE_CONTENT_TYPE = "text/html; charset=ISO-8859-1"


def serialize_word_document_response(
    document: bytes,
    *,
    max_response_bytes: int = 16 * 1024 * 1024,
) -> bytes:
    """Serialize the observed successful response-word envelope.

    The returned document is opaque binary data encoded as Base64. This helper
    does not inspect, convert, or modify the Word document.
    """
    if not isinstance(document, bytes):
        raise TypeError("document must be bytes")
    if not document:
        raise ProtocolError("empty_document")
    if type(max_response_bytes) is not int or max_response_bytes <= 0:
        raise ValueError("max_response_bytes must be a positive integer")

    root = ET.Element("response-word", {"status": "success"})
    return_types = ET.SubElement(root, "return-types")
    node = ET.SubElement(
        return_types,
        "type",
        {"mimetype": "application/msword", "encryption": "base64"},
    )

    # Base64 output is ASCII and needs no XML escaping. Compute its exact
    # envelope size before allocating the expanded encoded document.
    empty_envelope = ET.tostring(root, encoding="utf-8")
    encoded_size = 4 * ((len(document) + 2) // 3)
    expected_response_size = len(empty_envelope) + encoded_size + 5
    if expected_response_size > max_response_bytes:
        raise ProtocolError("response_size_invalid")

    node.text = base64.b64encode(document).decode("ascii")
    response = ET.tostring(root, encoding="utf-8")
    if len(response) != expected_response_size:
        raise ProtocolError("response_size_calculation_mismatch")
    return response
