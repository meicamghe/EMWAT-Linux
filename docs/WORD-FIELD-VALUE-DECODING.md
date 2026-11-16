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


## Word field-code name extraction

The native `FindFieldInActivefields` routine at `0x004BC170` uses these constants:

- `0x004BC23C`: `DOCPROPERTY`
- `0x004BC260`: two-space delimiter
- `0x004BC274`: one-space delimiter

When the case-sensitive `DOCPROPERTY` keyword is present, the routine extracts the token after the first two-space delimiter, scanning a maximum 255-character window and stopping at the next space. If the expected structure is absent, it preserves the original input.

Python implements this as `extract_docproperty_identifier`, including the observed Delphi one-based Copy offset and fallback behavior. Python CI run `43814423443` passed **94 tests** (one optional UNO-only test skipped).

The helper implementations at `0x00455314`, `0x00455108`, and `0x004735D0` are still being traced. In particular, the exact treatment of `+` in URL-encoded values remains unverified.
