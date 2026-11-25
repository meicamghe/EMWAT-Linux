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

The decoder rejects input lengths not divisible by four, maps each input byte through a 256-byte character-translation table at `0x00627F98`, rejects a table value of `0xFF`, and assembles three output bytes per four input characters. The final group handles `=` padding and emits one or two bytes. On decode failure, the `0x004738CC` wrapper clears the output value. These findings were statically traced in the checked-in `EmwatMethods.bpl1` and runtime-probed against the byte-identical Wine 11 installation.

#### Pre-decoder conversion at `0x00455108`

Static disassembly establishes that this helper converts the input Delphi `WideString` to an `AnsiString` using the caller-supplied code page (the `SetFieldValue` Base64 path supplies `0`, Windows ACP), flags `0x270`, and a NUL-terminated source (`cchWideChar=-1`). It first queries the required byte count `N`, sets the destination string length to `N-1`, then calls `WideCharToMultiByte` with destination capacity `N-1`. The API return value is ignored. This helper therefore does not itself normalize whitespace; it performs ACP conversion before the Base64 table lookup.

A disposable Wine 11 WinAPI probe (Wine reports `11.0`) confirmed that the query for the test strings returns 2 bytes including the terminator. Passing capacity 1 to the second call returns 0 with `ERROR_INSUFFICIENT_BUFFER` (122), while the first converted byte has already been written. For `A`, `é`, and an unrepresentable CJK character, the written ACP bytes were respectively `41`, `e9`, and `3f` in this Wine prefix. The `0x270` flags call succeeded through the query and reached the same short-buffer behavior. The probe did not call the BPL helper, so it confirms Wine's WinAPI behavior, not full `SetFieldValue` output. Prefix `/home/m/.wine-wchar-probe-20261125` and its temporary harness were removed; the installed BPL hash was rechecked and still matches the repository snapshot.

#### Wine 11 direct decoder probe

The installed `EmwatMethods.bpl` hash is `6ff7d262f46ab009e3eecf20fca40cd41ec8ad937adf7bbfe2f6eddd56aaea2d`, matching the repository analysis snapshot. A 32-bit harness at `tools/reverse_engineering/probe_emwat_base64_decoder.c` loaded the installed BPL with `LoadLibraryEx(..., DONT_RESOLVE_DLL_REFERENCES)` and called decoder RVA `0x73700`; package initialization and imports were not resolved. It ran under Wine `11.0` in a disposable prefix, which was removed afterward. The original `/home/m/.wine-emwat` prefix was not launched or modified; its EMWAT binary hashes were rechecked after the probe.

| Input | Decoder result | Output | Observation |
|---|---:|---|---|
| `TWFu` | success | `4d 61 6e` (`Man`) | Three-byte group |
| `QQ==` | success | `41` (`A`) | Two `=` padding characters |
| `QUI=` | success | `41 42` (`AB`) | One `=` padding character |
| `QQ?=` | failure | partial byte `41` remains in the caller buffer | Invalid alphabet is reported after earlier output was written |
| `TWE` | failure | output buffer untouched | Length not divisible by four |
| `QQ=A` | success | `41` (`A`) | Direct decoder accepts noncanonical padding and ignores the fourth character after `=` |

The wrapper at `0x004738CC` clears its output after a failed decode, based on static control-flow analysis; the decoder harness tested only the lower-level routine and did not call that wrapper. Likewise, the surprising `QQ=A` acceptance is a property of the direct routine and is not yet proven to be reachable unchanged through the conversion helper and full `SetFieldValue` path.

The Linux decoder rejects malformed Base64 instead of silently treating it as an empty value. It also rejects the direct decoder's noncanonical `QQ=A` case. This is deliberately fail-closed and is not claimed as exact native error parity. Controlled Wine 11 fixtures are still needed for malformed/truncated `%` sequences, Base64 whitespace and non-ASCII input, and the behavior of padding through the complete method path. The conversion helper's ACP/code-page and short-buffer mechanics are statically established, but its exact BPL runtime result remains untested.


## Word field-code name extraction

The native `FindFieldInActivefields` routine at `0x004BC170` uses these constants:

- `0x004BC23C`: `DOCPROPERTY`
- `0x004BC260`: two-space delimiter
- `0x004BC274`: one-space delimiter

When the case-sensitive `DOCPROPERTY` keyword is present, the routine extracts the token after the first two-space delimiter, scanning a maximum 255-character window and stopping at the next space. If the expected structure is absent, it preserves the original input.

Python implements this as `extract_docproperty_identifier`, including the observed Delphi one-based Copy offset and fallback behavior. Python CI run `43814423443` passed **94 tests** (one optional UNO-only test skipped).

The URL helper at `0x00455314` is statically traced for ordinary characters, `+`, and `%HH`; `+` maps to a space. Malformed/truncated percent escapes still require a controlled Wine fixture. For Base64, the inner decoder and conversion helper at `0x00455108` are statically traced, and a Wine 11 WinAPI probe confirms the short-buffer behavior described above. The wrapper/full method path and whitespace/Unicode behavior end to end remain unresolved.
