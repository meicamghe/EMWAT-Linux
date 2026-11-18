"""Structured request adapter for the captured EditWordDocument method."""
from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from emwat_linux.protocol import MethodCall
from emwat_linux.word_config import WordDocumentConfig, WordConfigError, parse_word_config


class EditWordDocumentRequestError(ValueError):
    """Raised when an EditWordDocument request cannot be normalized safely."""


@dataclass(frozen=True)
class EditWordDocumentRequest:
    config: WordDocumentConfig
    document_bytes: bytes
    sign_data_text: str
    extra_parameters: Mapping[str, str]


def parse_editword_request(
    call: MethodCall,
    *,
    max_document_bytes: int = 64 * 1024 * 1024,
    max_encoded_document_chars: int = 90 * 1024 * 1024,
    max_config_bytes: int = 16 * 1024 * 1024,
) -> EditWordDocumentRequest:
    """Decode the two confirmed Base64 parameters and retain signData opaque.

    The captured request confirms Base64 wordConfig and wordBody. signData is
    deliberately retained as text because the inner config describes its
    concatenation and per-field encoding; it is not necessarily one Base64 blob.
    """
    if call.class_name != "EditWordDocument":
        raise EditWordDocumentRequestError("unexpected_method_class")
    limits = (max_document_bytes, max_encoded_document_chars, max_config_bytes)
    if any(type(limit) is not int or limit <= 0 for limit in limits):
        raise ValueError("size limits must be positive integers")

    encoded_config = call.params.get("wordConfig")
    encoded_document = call.params.get("wordBody")
    if encoded_config is None or encoded_document is None:
        raise EditWordDocumentRequestError("required_parameter_missing")
    if not encoded_document or len(encoded_document) > max_encoded_document_chars:
        raise EditWordDocumentRequestError("document_encoded_size_invalid")

    try:
        config = parse_word_config(
            encoded_config,
            max_decoded_bytes=max_config_bytes,
        )
    except WordConfigError as exc:
        raise EditWordDocumentRequestError("word_config_invalid") from exc

    try:
        compact_document = "".join(encoded_document.split())
        document_bytes = base64.b64decode(compact_document.encode("ascii"), validate=True)
    except (UnicodeEncodeError, binascii.Error, ValueError) as exc:
        raise EditWordDocumentRequestError("word_body_invalid_base64") from exc

    if not document_bytes or len(document_bytes) > max_document_bytes:
        raise EditWordDocumentRequestError("document_decoded_size_invalid")

    sign_data = call.params.get("signData", "")
    extras = {
        key: value
        for key, value in call.params.items()
        if key not in {"wordConfig", "wordBody", "signData"}
    }
    return EditWordDocumentRequest(
        config=config,
        document_bytes=document_bytes,
        sign_data_text=sign_data,
        extra_parameters=MappingProxyType(extras),
    )
