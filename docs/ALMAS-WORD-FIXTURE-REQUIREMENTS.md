# Sanitized Almas / Word fixture required for semantic mapping

## Purpose

The Linux adapter must reproduce the field behavior of the existing Almas-to-Word
workflow in LibreOffice Writer. Static metadata inventories and synthetic UNO
roundtrips are not sufficient to infer this mapping safely.

## Existing repository evidence reviewed (2026-11-24)

The GitHub text reports contain extracted strings, static-analysis results, or packet metadata; they do not contain the matching editable Word fixture. `http-requests.txt` records request metadata and TCP payload lengths, not the HTTP request body. `EMWAT_Extracted.zip` contains installer/service binaries and GAM printer support files, but no `.doc`, `.docx`, HAR, PCAP, or matching `wordConfig` fixture. These files are useful reverse-engineering references, but cannot establish semantic field-to-Writer mappings or expected output.

## Minimum fixture set

Provide one small, disposable, sanitized transaction containing:

1. The original Word document received by the Windows EMWAT path (`.doc` or
   `.docx`), before editing.
2. The exact matching `wordConfig` payload/XML captured for that document.
3. The expected final Word document produced by the known-good Windows flow
   after representative edits.
4. If available, the corresponding `signData` value and the exact request /
   response envelope with credentials, personal data, and host identifiers
   removed.
5. A short field map written by the fixture owner identifying which visible
   test markers should appear in which document locations.

Do not submit production correspondence or real personal/sensitive content.
Replace all names, addresses, identifiers, and letter text with synthetic
markers while preserving the document structure and field identifiers.

## Required representative cases

The fixture should include, where supported by the source format:

- one ordinary text field;
- one empty field and one missing/optional field;
- one twin field with both declared members;
- one URL-encoded non-ASCII text value;
- one image field with Base64 bytes and MIME type;
- one Writer/Word custom property;
- one signature-related field and its associated `signData` contract, if used.

If the production template does not contain one of these cases, mark it
"not used" rather than inventing a sample contract.

## What will be compared

- WordConfig field order and identifiers;
- Word custom-property names and enumeration order;
- Writer custom-property names after import;
- exact field-to-property / anchor associations;
- empty versus absent values;
- text decoding and encoding;
- image bytes, MIME type, and placement;
- signature metadata and visible output;
- final exported document behavior in Word-compatible format.

## Safety rules

- No positional mapping from Word index to Writer index unless the fixture
  proves the relationship for the supported template contract.
- No automatic property creation based only on a name resemblance.
- No fuzzy or case-insensitive write mapping; case-fold candidates are review
  hints only.
- No guessed twin delimiter, signData separator, signature encoding, or image
  serialization.
- Preserve unknown fields and metadata rather than silently dropping them.
- Every enabled mapping must have a regression fixture and expected result.

## Acceptance

A mapping is eligible for implementation only when the fixture can be parsed
reproducibly, the expected output is independently inspectable, and tests
prove the mapping and roundtrip behavior. A passing synthetic test alone does
not qualify as Almas compatibility evidence.
