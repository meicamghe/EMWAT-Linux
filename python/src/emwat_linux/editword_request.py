"""Structured request adapter for the captured EditWordDocument method."""
from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from emwat_linux.protocol import MethodCall
from emwat_linux.word_config import WordDocumentConfig, WordConfigError, parse_word_config


class EditWordDocumentRequestError(ValueError):
    """Raised when an EditWordDocument request cannot be normalized safely."""


@dataclass(frozen=True)
class EditWordDocumentRequest:
    config: WordDocumentConfig = field(repr=False)
    document_bytes: bytes = field(repr=False)
    sign_data_text: str = field(repr=False)
    extra_parameters: Mapping[str, str] = field(repr=False)


def parse_editword_request(
    call: MethodCall,
    *,
    max_document_bytes: int = 64 * 1024 * 1024,
    max_encoded_document_chars: int = 90 * 1024 * 1024,
    max_config_bytes: int = 16 * 1024 * 1024,
    max_encoded_config_chars: int = 24 * 1024 * 1024,
    max_auxiliary_parameter_chars: int = 64 * 1024 * 1024,
) -> EditWordDocumentRequest:
    """Decode confirmed Base64 parameters and retain auxiliary values opaquely.

    The captured request confirms Base64 wordConfig and wordBody. signData and
    letterImages/other auxiliary parameters remain opaque text because the
    native external-parameter concatenation and per-field encoding contract is
    not fully resolved. Their lengths are bounded and all document/config/
    auxiliary payloads are excluded from repr to prevent accidental log leaks.
    """
    if not isinstance(call, MethodCall):
        raise EditWordDocumentRequestError("method_call_invalid")
    if call.class_name != "EditWordDocument":
        raise EditWordDocumentRequestError("unexpected_method_class")
    if not isinstance(call.params, Mapping):
        raise EditWordDocumentRequestError("method_parameters_invalid")

    limits = (
        max_document_bytes,
        max_encoded_document_chars,
        max_config_bytes,
        max_encoded_config_chars,
        max_auxiliary_parameter_chars,
    )
    if any(type(limit) is not int or limit <= 0 for limit in limits):
        raise ValueError("size limits must be positive integers")

    encoded_config = call.params.get("wordConfig")
    encoded_document = call.params.get("wordBody")
    if encoded_config is None or encoded_document is None:
        raise EditWordDocumentRequestError("required_parameter_missing")
    if not isinstance(encoded_config, str):
        raise EditWordDocumentRequestError("word_config_invalid_type")
    if not isinstance(encoded_document, str):
        raise EditWordDocumentRequestError("word_body_invalid_type")
    if not encoded_document or len(encoded_document) > max_encoded_document_chars:
        raise EditWordDocumentRequestError("document_encoded_size_invalid")

    try:
        config = parse_word_config(
            encoded_config,
            max_encoded_chars=max_encoded_config_chars,
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
    if not isinstance(sign_data, str):
        raise EditWordDocumentRequestError("sign_data_invalid_type")
    if len(sign_data) > max_auxiliary_parameter_chars:
        raise EditWordDocumentRequestError("sign_data_size_exceeded")

    extras = {
        key: value
        for key, value in call.params.items()
        if key not in {"wordConfig", "wordBody", "signData"}
    }
    if any(not isinstance(key, str) or not isinstance(value, str) for key, value in extras.items()):
        raise EditWordDocumentRequestError("extra_parameter_invalid_type")
    if any(len(value) > max_auxiliary_parameter_chars for value in extras.values()):
        raise EditWordDocumentRequestError("extra_parameter_size_exceeded")

    return EditWordDocumentRequest(
        config=config,
        document_bytes=document_bytes,
        sign_data_text=sign_data,
        extra_parameters=MappingProxyType(extras),
    )
