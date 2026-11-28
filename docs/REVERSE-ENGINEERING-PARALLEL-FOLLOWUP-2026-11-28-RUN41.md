# Reverse-engineering parallel follow-up — 2026-11-28 Run 41

## Best-supported EditWordDocument handler data flow

Run-67 artifact `15260427307` includes `image-io/connector-contract/dictionary-and-xml-keys.md`; artifact `15260640277` includes `connector-handlers/procedure-005EE82C.md`.

The procedure at `0x005EE82C` is labelled by TD32 as `TScanDocument.PerformMethod`, but its actual input data flow is Word-specific:

| Key | Address | Observed behavior |
|---|---:|---|
| `wordConfig` | `0x005EE9F4` | Required. Missing key raises `Requset XML is not valid (wordConfig parameter is null)` at `0x005EEA0C`. |
| `wordBody` | `0x005EEA88` | Looked up; absent/empty value is normalized to an empty string. |
| `letterImages` | `0x005EEAA0` | Looked up; shared helper zero-initializes output, so missing key defaults empty. |
| `signData` | `0x005EEABC` | Looked up; missing key defaults empty. |

The method calls `TWordViwer.LoadDocument` at `0x004B7724` from callsite `0x005EE961`, passing the Word request values and an output slot. It then adds the returned string to its output collection. This is the strongest static candidate for the EditWordDocument handler path, based on the actual keys and the WordViewer call, rather than its stale/mismatched TD32 class label.

The separate procedure labelled `TFaxDocument.PerformMethod` at `0x005EEB48` reads the `document` key and calls `TScanCommand.GetNextPage` at `0x004F2558`. That is consistent with the real ScanDocument path and confirms that the TD32 connector class labels in this region are mismatched.

## Current Linux request/office parity gap

Current implementation inspection shows:

- `editword_request.py` decodes `wordConfig` and `wordBody`.
- `signData` is preserved as opaque text.
- Unknown fields, including `letterImages`, remain in `extra_parameters`.
- `LibreOfficeAdapter.open_document` currently writes and opens only `request.document_bytes`; it does not apply `letterImages`, `signData`, or EMWAT WordConfig field substitutions.
- A TD32 symbol exists for `TWordViwer.AddImagesToDoc` at `0x004C0410`, with a signature involving Word fields, two integers, a UnicodeString, and an `IXMLFieldType`. The actual callsite and payload format have not yet been proven.

Therefore the Linux route can exercise the basic document open/edit/save lifecycle, but cannot yet claim full Windows parity for embedded letter images, signatures, and EMWAT field substitution. Do not invent the `letterImages` or `signData` encodings.

## Remaining exact targets

1. Resolve the registration mapping from external method name `EditWordDocument` to the procedure/class instance that owns the `0x005EE82C` data flow.
2. Trace the full `TWordViwer.LoadDocument` body and its call to `AddImagesToDoc` at `0x004C0410`.
3. Recover the output collection key and exact response dictionary/XML serialization.
4. Capture the real Windows request/response pair and compare all fields/headers.
5. Add explicit opaque fields to the Linux request model before implementing their format-specific behavior; only after a confirmed fixture should image/signature processing be added.

No production code or workflow source was changed in this run.
