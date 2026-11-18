# EditWord input size-limit validation

Date: 2026-11-18

## Contract

Every caller-supplied size bound in the EditWord request path must be a
positive built-in Python integer. The implementation deliberately uses
`type(value) is int`, rather than `isinstance(value, int)`, so booleans are
not accepted as integer limits. Floats, numeric strings, `None`, zero and
negative values are rejected before decoding or office-engine work begins.

The rule is applied consistently to:

- `parse_editword_request`: decoded document bytes, encoded document
  characters and decoded wordConfig bytes;
- `EditWordDocumentService`: the service-level document byte limit;
- `parse_method_call`: the outer XML request byte limit;
- `serialize_word_document_response`: the serialized response byte limit;
- `parse_word_config`: encoded Base64 character and decoded XML byte limits;\n- `LibreOfficeAdapter`: connection, polling, optional close and recovery intervals must be finite positive numbers (booleans, NaN, infinities, strings and non-positive values are rejected).

Invalid configuration raises `ValueError` with a stable, layer-specific
message. Invalid request contents continue to use the existing protocol or
request error types.

## Regression coverage

Synthetic unit tests reject `True`, `False`, floating-point values,
numeric strings, zero, negative values and `None` for each public size-limit
argument. Existing positive integer limits and ordinary request/response
roundtrips remain covered by the existing tests.

## Scope

This change validates configuration types; it does not change the observed
EMWAT wire format, document payload decoding, response envelope, or office
lifecycle. No Windows runtime capture or Almas end-to-end test is implied.


## Bridge transport and response bounds

The loopback HTTP server now validates constructor configuration before binding:
the TCP port must be a built-in integer in range, request/response byte limits
must be positive built-in integers, and the socket timeout must be a finite
positive number. Boolean values, floats/strings for integer limits, NaN,
infinities, non-positive values and oversized integers that cannot be safely
converted to a finite timeout are rejected. The bind host must be supplied as
an IPv4 loopback address string.

The EditWord success serializer receives the same configured
`max_response_bytes` as the HTTP server. This removes the former hidden
16 MiB serializer ceiling when an application explicitly configures a larger
bounded response allowance. Both layers still enforce the bound independently.
