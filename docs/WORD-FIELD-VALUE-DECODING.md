# Word field value decoding analysis

Date: 2026-11-16

## Native encoding dispatch

The TD32 trace of `TWordViwer.SetFieldValue` at `0x004BFDB0` compares the field's encoding label against two fixed strings:

- `0x004BFEE8`: `urlencoded`
- `0x004BFF0C`: `base64`

Its three branches are:

1. `urlencoded`: invokes the URL-decoding helper at `0x00455314`, then assigns the decoded string.
2. `base64`: invokes the helper chain beginning at `0x00455108` and `0x004735D0`, then assigns the decoded result.
3. Any other label: copies the original string without decoding.

Direct callsites show that this method is shared by `GetDocFieldIndex`, `GetCaptionItemFont`, and `ShowRecAndCcOptionForm`; encoding conversion is therefore a shared field-value rule, not just a body-field operation.

## Linux implementation status

The Python `word_fields.py` decoder already applies the field's own `encryption` attribute independently:

- `urlencoded` → strict UTF-8 URL decode
- `base64` → strict Base64 decode to bytes
- absent encoding → preserve the original string
- unknown or malformed encoding → fail closed

The Linux implementation deliberately rejects malformed input instead of silently falling back to raw text. This is a safety improvement; exact malformed-input behavior of the original native helper remains under investigation.

## Remaining verification

Trace `0x00455314`, `0x00455108`, and `0x004735D0` to verify URL/Base64 edge cases and byte/string conversion details. The encoding labels and dispatch branches themselves are confirmed by the disassembly and decoded string constants.
