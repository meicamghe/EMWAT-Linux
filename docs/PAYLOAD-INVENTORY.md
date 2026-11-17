# EMWAT payload inventory

`emwat_linux.payload_inventory.inspect_request_payloads(request)` provides a privacy-preserving inventory before image import and signData decoding are implemented.

## Image fields

- Uses the existing per-field decoder and declared `mimetype` / `encryption`.
- For decoded image fields, reports only field ID, MIME type, byte count, and SHA-256.
- Never returns or logs image bytes.
- Rejects an image declared as binary when its decoder yields text.

## External references and signData

- Reports each exact `paramId` as an unresolved reference.
- Reports whether signData is present, its character count, and a SHA-256 fingerprint.
- Does not split, Base64-decode, concatenate, or otherwise interpret signData.
- Does not assume `paramId` is an offset, separator, or parameter name.

## Why this boundary exists

The field metadata exposes image MIME/encoding declarations and external parameter IDs, but the native signData framing and association rules have not yet been verified. This inventory makes captures comparable and helps isolate fields without inventing a production mapping. It performs no Writer mutation.


## Optional attributes

The inventory also decodes `optional-attributes/attribute/content` using that content node's own declared encoding. It records only the attribute ID, declared value type, decoded character count, and SHA-256. Text values are never included in the report. Values that decode to binary are rejected by the text-only optional-attribute decoder rather than silently coerced.
