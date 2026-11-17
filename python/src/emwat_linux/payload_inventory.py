"""Privacy-preserving inventory of EMWAT image and external field payloads.

This module deliberately stops before inserting data into Writer. Image payload
bytes can be fingerprinted and sized; signData remains opaque until its native
framing and field association are recovered from a representative capture.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib

from emwat_linux.editword_request import EditWordDocumentRequest
from emwat_linux.word_fields import (
    DecodedWordField,
    WordFieldDecodeError,
    decode_optional_attributes,
    decode_word_fields,
)


@dataclass(frozen=True)
class ImagePayloadInfo:
    field_id: str
    mimetype: str
    byte_count: int
    sha256: str


@dataclass(frozen=True)
class ExternalFieldReference:
    field_id: str
    parameter_id: str
    declared_mimetype: str | None
    declared_encoding: str | None


@dataclass(frozen=True)
class OptionalPayloadInfo:
    attribute_id: str
    value_type: str | None
    character_count: int
    sha256: str


@dataclass(frozen=True)
class PayloadInventory:
    decoded_field_count: int
    image_payloads: tuple[ImagePayloadInfo, ...]
    external_references: tuple[ExternalFieldReference, ...]
    optional_attributes: tuple[OptionalPayloadInfo, ...]
    unresolved_external_references: tuple[str, ...]
    sign_data_present: bool
    sign_data_character_count: int
    sign_data_sha256: str | None


def _image_info(field: DecodedWordField) -> ImagePayloadInfo:
    if not field.is_image:
        raise ValueError("field_is_not_declared_image")
    if not isinstance(field.value, bytes):
        raise WordFieldDecodeError(f"image_payload_not_binary:{field.field_id}")
    return ImagePayloadInfo(
        field_id=field.field_id,
        mimetype=field.mimetype or "application/octet-stream",
        byte_count=len(field.value),
        sha256=hashlib.sha256(field.value).hexdigest(),
    )


def inspect_request_payloads(
    request: EditWordDocumentRequest,
) -> PayloadInventory:
    """Summarize image bytes and opaque signData references without mutation.

    A paramId is recorded as an unresolved reference, not interpreted as an
    offset, delimiter, parameter name, or Base64 token. The signData digest
    allows two captures to be compared without exposing their contents.
    """
    fields = decode_word_fields(request.config)
    images = tuple(_image_info(field) for field in fields if field.is_image)
    external = tuple(
        ExternalFieldReference(
            field_id=field.field_id,
            parameter_id=field.external_parameter or "",
            declared_mimetype=field.mimetype,
            declared_encoding=field.encoding,
        )
        for field in fields
        if field.external_parameter
    )
    optional_attributes = tuple(
        OptionalPayloadInfo(
            attribute_id=item.attribute_id,
            value_type=item.value_type,
            character_count=len(item.value),
            sha256=hashlib.sha256(item.value.encode("utf-8")).hexdigest(),
        )
        for item in decode_optional_attributes(request.config)
    )
    sign_data = request.sign_data_text
    return PayloadInventory(
        decoded_field_count=len(fields),
        image_payloads=images,
        external_references=external,
        optional_attributes=optional_attributes,
        unresolved_external_references=tuple(
            item.parameter_id for item in external
        ),
        sign_data_present=bool(sign_data),
        sign_data_character_count=len(sign_data),
        sign_data_sha256=(
            hashlib.sha256(sign_data.encode("utf-8")).hexdigest()
            if sign_data
            else None
        ),
    )


__all__ = [
    "ExternalFieldReference",
    "ImagePayloadInfo",
    "OptionalPayloadInfo",
    "PayloadInventory",
    "inspect_request_payloads",
]
