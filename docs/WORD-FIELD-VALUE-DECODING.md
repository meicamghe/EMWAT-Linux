# Word field value decoding analysis

Date: 2026-11-25

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

The `+` behavior is confirmed by the `0x00455314` disassembly: the ordinary-character branch compares the current byte with `0x2B` and, on a match, appends the one-byte string at `0x00455454`; that byte is `0x20` (space). The percent branch reads the following two bytes and routes them through the hexadecimal conversion helper at `0x004551FC` before appending the result. Thus `A+B%20C` → `A B C` is supported by both the binary trace and the Python regression test.

### Base64 path — static helper findings

The `base64` branch in `SetFieldValue` (`0x004BFDB0`) calls `0x00455108`, then `0x004735D0`, before assigning the result. `0x004735D0` delegates to `0x004738CC`, which calculates the decoded byte count and calls the decoder at `0x00473700`.

The decoder rejects input lengths not divisible by four, maps each input byte through a 256-byte character-translation table at `0x00627F98`, rejects a table value of `0xFF`, and assembles three output bytes per four input characters. The final group handles one or two `=` padding characters and emits one or two bytes. On decode failure, the `0x004738CC` wrapper clears the output value. These are static findings from the checked-in `EmwatMethods.bpl1`; they do not establish how the preceding `0x00455108` transformation affects whitespace or Unicode input before lookup.

The Linux decoder currently rejects malformed Base64 instead of silently treating it as an empty value. This is deliberately fail-closed and is not claimed as exact native error parity. Controlled Wine 11 fixtures are still needed for malformed/truncated `%` sequences and for Base64 whitespace, non-ASCII input, padding edge cases, and the complete `0x00455108` byte/string conversion.


## Word field-code name extraction

The native `FindFieldInActivefields` routine at `0x004BC170` uses these constants:

- `0x004BC23C`: `DOCPROPERTY`
- `0x004BC260`: two-space delimiter
- `0x004BC274`: one-space delimiter

When the case-sensitive `DOCPROPERTY` keyword is present, the routine extracts the token after the first two-space delimiter, scanning a maximum 255-character window and stopping at the next space. If the expected structure is absent, it preserves the original input.

Python implements this as `extract_docproperty_identifier`, including the observed Delphi one-based Copy offset and fallback behavior. Python CI run `43814423443` passed **94 tests** (one optional UNO-only test skipped).

The helper implementations at `0x00455314`, `0x00455108`, and `0x004735D0` are still being traced. In particular, the exact treatment of `+` in URL-encoded values remains unverified.
