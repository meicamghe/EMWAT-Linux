"""Evidence-bounded image and signer metadata mapping for EMWAT WordConfig.

The native protocol identifies image payloads and 20 signer metadata slots, but
it does not provide a verified field-id-to-Writer-anchor table. This module
decodes and classifies assets and applies images only through caller-supplied,
explicit target names. It never guesses signature image anchors or parses
signData.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from emwat_linux.emwat_field_catalog import parse_indexed_signer_field
from emwat_linux.word_config import WordDocumentConfig
from emwat_linux.word_fields import DecodedWordField, decode_word_fields


class WriterAssetMappingError(RuntimeError):
    """Raised when an explicit Writer image mapping cannot be applied safely."""


@dataclass(frozen=True)
class WordImageAsset:
    field_index: int
    field_id: str
    mimetype: str
    data: bytes
    external_parameter: str | None

    @property
    def is_empty(self) -> bool:
        return not self.data


@dataclass(frozen=True)
class ExternalImageParameterReference:
    field_index: int
    field_id: str
    parameter_id: str
    separator: str | None
    concater: str | None
    concator: str | None
    encryption: str | None
    mimetype: str | None


@dataclass(frozen=True)
class SignerMetadataSlot:
    index: int
    person: str = ""
    department: str = ""
    unit: str = ""
    index_unit: str = ""
    signature_number: str = ""
    behalf_name: str = ""
    signature_image_field_index: int | None = None
    present_families: tuple[str, ...] = ()
    missing_families: tuple[str, ...] = ()


@dataclass(frozen=True)
class WordAssetInventory:
    images: tuple[WordImageAsset, ...]
    signer_slots: tuple[SignerMetadataSlot, ...]
    signer_slot_count: int
    empty_image_field_indices: tuple[int, ...]
    unresolved_external_parameter_fields: tuple[tuple[int, str], ...]
    external_image_parameters: tuple[ExternalImageParameterReference, ...] = ()


@dataclass(frozen=True)
class WriterGraphicUpdate:
    field_index: int
    field_id: str
    target_name: str
    mimetype: str
    data: bytes


_IMAGE_EXTENSIONS = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/gif": ".gif",
    "image/tif": ".tif",
    "image/tiff": ".tif",
    "image/bmp": ".bmp",
}
_SIGNER_FAMILIES = (
    "department", "person", "unit", "index_unit",
    "signature_number", "behalf_name", "signature_image",
)
_MAX_SIGNER_SLOT = 19


def _text_value(field: DecodedWordField) -> str:
    if not isinstance(field.value, str):
        raise WriterAssetMappingError("signer_metadata_must_be_text")
    return field.value


def inspect_word_assets(
    config: WordDocumentConfig,
    *,
    max_image_bytes: int = 20 * 1024 * 1024,
    max_total_image_bytes: int = 64 * 1024 * 1024,
) -> WordAssetInventory:
    """Decode image fields and preserve all observed signer slots 0..19.

    Empty image fields are retained as empty indices; they are not interpreted
    as a request to delete a pre-existing Writer graphic. Image bytes remain
    in memory only and must not be written to logs or evidence reports.
    """
    if not isinstance(config, WordDocumentConfig):
        raise TypeError("invalid_word_document_config")
    if type(max_image_bytes) is not int or max_image_bytes <= 0:
        raise ValueError("max_image_bytes_must_be_positive")
    if type(max_total_image_bytes) is not int or max_total_image_bytes <= 0:
        raise ValueError("max_total_image_bytes_must_be_positive")

    decoded = decode_word_fields(config)
    images: list[WordImageAsset] = []
    empty_indices: list[int] = []
    unresolved_external: list[tuple[int, str]] = []
    external_references: list[ExternalImageParameterReference] = []
    total_bytes = 0
    slots: dict[int, dict[str, str]] = {}

    for index, field in enumerate(decoded):
        signer_field = parse_indexed_signer_field(field.field_id)
        if signer_field is not None and signer_field.index <= _MAX_SIGNER_SLOT:
            slot = slots.setdefault(signer_field.index, {})
            family = signer_field.family
            if family in slot:
                raise WriterAssetMappingError("duplicate_signer_metadata_field")
            if family == "signature_image":
                if not field.is_image:
                    raise WriterAssetMappingError("signer_signature_field_not_image")
                slot[family] = str(index)
            else:
                slot[family] = _text_value(field)

        if field.is_image:
            mimetype = (field.mimetype or "").casefold()
            if mimetype not in _IMAGE_EXTENSIONS:
                raise WriterAssetMappingError("unsupported_image_mimetype")
            # A native image field may carry no inline bytes and instead refer
            # to an outer EditWord parameter (for example signData). Keep that
            # binding unresolved; its concatenation/encoding contract is not
            # inferred here.
            if field.external_parameter and not field.value:
                data = b""
                unresolved_external.append((index, field.external_parameter))
                external_references.append(
                    ExternalImageParameterReference(
                        field_index=index,
                        field_id=field.field_id,
                        parameter_id=field.external_parameter,
                        separator=field.attributes.get("separator"),
                        # Keep both spellings: static analysis found the
                        # request capture spelling "concater", while the
                        # native setter reads "concator". Neither is aliased.
                        concater=field.attributes.get("concater"),
                        concator=field.attributes.get("concator"),
                        encryption=field.encoding,
                        mimetype=field.mimetype,
                    )
                )
            else:
                if (field.encoding or "").casefold() != "base64":
                    raise WriterAssetMappingError("image_field_requires_base64")
                if not isinstance(field.value, bytes):
                    raise WriterAssetMappingError("image_field_payload_not_binary")
                data = field.value
                if len(data) > max_image_bytes:
                    raise WriterAssetMappingError("image_field_size_exceeded")
                total_bytes += len(data)
                if total_bytes > max_total_image_bytes:
                    raise WriterAssetMappingError("total_image_payload_size_exceeded")
                if not data:
                    empty_indices.append(index)
            images.append(
                WordImageAsset(
                    field_index=index,
                    field_id=field.field_id,
                    mimetype=mimetype,
                    data=data,
                    external_parameter=field.external_parameter,
                )
            )

    signer_slots = tuple(
        SignerMetadataSlot(
            index=index,
            person=slots.get(index, {}).get("person", ""),
            department=slots.get(index, {}).get("department", ""),
            unit=slots.get(index, {}).get("unit", ""),
            index_unit=slots.get(index, {}).get("index_unit", ""),
            signature_number=slots.get(index, {}).get("signature_number", ""),
            behalf_name=slots.get(index, {}).get("behalf_name", ""),
            signature_image_field_index=(
                int(slots[index]["signature_image"])
                if "signature_image" in slots.get(index, {}) else None
            ),
            present_families=tuple(
                family for family in _SIGNER_FAMILIES
                if family in slots.get(index, {})
            ),
            missing_families=tuple(
                family for family in _SIGNER_FAMILIES
                if family not in slots.get(index, {})
            ),
        )
        for index in range(_MAX_SIGNER_SLOT + 1)
    )
    return WordAssetInventory(
        images=tuple(images),
        signer_slots=signer_slots,
        signer_slot_count=len(slots),
        empty_image_field_indices=tuple(empty_indices),
        unresolved_external_parameter_fields=tuple(unresolved_external),
        external_image_parameters=tuple(external_references),
    )


def build_writer_graphic_updates(
    inventory: WordAssetInventory,
    target_names_by_field_index: Mapping[int, str],
) -> tuple[WriterGraphicUpdate, ...]:
    """Bind image fields to existing Writer graphic names using explicit input.

    The field index is used because duplicate XML field IDs are observed and
    therefore cannot safely act as unique keys. Missing targets are not guessed.
    """
    if not isinstance(inventory, WordAssetInventory):
        raise TypeError("invalid_word_asset_inventory")
    if not isinstance(target_names_by_field_index, Mapping):
        raise TypeError("graphic_target_map_must_be_mapping")

    assets_by_index = {asset.field_index: asset for asset in inventory.images}
    if len(assets_by_index) != len(inventory.images):
        raise WriterAssetMappingError("duplicate_image_field_index")
    unknown_indices = tuple(
        index for index in target_names_by_field_index if index not in assets_by_index
    )
    if unknown_indices:
        raise WriterAssetMappingError("graphic_target_references_unknown_field")
    targets = tuple(target_names_by_field_index.values())
    if any(not isinstance(name, str) or not name for name in targets):
        raise ValueError("graphic_target_name_required")
    if len(set(targets)) != len(targets):
        raise WriterAssetMappingError("duplicate_writer_graphic_target")

    updates: list[WriterGraphicUpdate] = []
    for field_index, target_name in target_names_by_field_index.items():
        asset = assets_by_index[field_index]
        if asset.is_empty:
            if asset.external_parameter:
                raise WriterAssetMappingError("external_image_parameter_unresolved")
            raise WriterAssetMappingError("empty_image_field_not_applied")
        updates.append(
            WriterGraphicUpdate(
                field_index=field_index,
                field_id=asset.field_id,
                target_name=target_name,
                mimetype=asset.mimetype,
                data=asset.data,
            )
        )
    return tuple(updates)


def apply_writer_graphic_updates(
    document: object,
    updates: Sequence[WriterGraphicUpdate],
    asset_directory: Path,
) -> tuple[str, ...]:
    """Replace existing named Writer graphic objects without changing anchors.

    Image files are staged in a private session directory. Existing GraphicURL
    values are captured and restored in reverse order if any UNO setter fails.
    The caller owns the directory lifetime; the LibreOffice session workdir is
    an appropriate owner.
    """
    if not isinstance(updates, Sequence):
        raise TypeError("graphic_updates_must_be_sequence")
    if not updates:
        return ()
    if any(not isinstance(item, WriterGraphicUpdate) for item in updates):
        raise TypeError("invalid_writer_graphic_update")
    names = tuple(item.target_name for item in updates)
    if len(set(names)) != len(names):
        raise WriterAssetMappingError("duplicate_writer_graphic_target")

    try:
        container = document.getGraphicObjects()
        existing = set(str(name) for name in container.getElementNames())
        missing = tuple(name for name in names if name not in existing)
        if missing:
            raise KeyError("writer_graphic_object_not_found:" + ",".join(missing))
    except (KeyError, TypeError, ValueError):
        raise
    except Exception as exc:
        raise WriterAssetMappingError("writer_graphic_container_unavailable") from exc

    directory = Path(asset_directory)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    staged: list[tuple[object, str, str]] = []
    attempted: list[tuple[object, str]] = []
    try:
        for update in updates:
            extension = _IMAGE_EXTENSIONS.get(update.mimetype.casefold())
            if extension is None or not update.data:
                raise WriterAssetMappingError("invalid_writer_graphic_payload")
            path = directory / f"emwat-image-{update.field_index}{extension}"
            path.write_bytes(update.data)
            url = path.resolve().as_uri()
            graphic = container.getByName(update.target_name)
            previous_url = str(graphic.getPropertyValue("GraphicURL"))
            staged.append((graphic, previous_url, url))

        for graphic, previous_url, url in staged:
            attempted.append((graphic, previous_url))
            graphic.setPropertyValue("GraphicURL", url)
    except Exception as exc:
        rollback_failed = False
        for graphic, previous_url in reversed(attempted):
            try:
                graphic.setPropertyValue("GraphicURL", previous_url)
            except Exception:
                rollback_failed = True
        if rollback_failed:
            raise WriterAssetMappingError(
                "writer_graphic_update_failed_and_rollback_incomplete"
            ) from exc
        if isinstance(exc, (KeyError, TypeError, ValueError, WriterAssetMappingError)):
            raise
        raise WriterAssetMappingError("writer_graphic_update_failed") from exc

    return names


__all__ = [
    "ExternalImageParameterReference",
    "SignerMetadataSlot",
    "WordAssetInventory",
    "WordImageAsset",
    "WriterAssetMappingError",
    "WriterGraphicUpdate",
    "apply_writer_graphic_updates",
    "build_writer_graphic_updates",
    "inspect_word_assets",
]
