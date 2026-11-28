# Reverse-engineering parallel follow-up — 2026-11-28 Run 39

## Connector handler symbol-name mismatch

The Run-67 `word-print-com` artifact contains a procedure labelled by TD32 as:

`TCompareWordDocument.PerformMethod` at `0x005EF8AC`.

However, its actual code reads the literal dictionary keys:
- `ExcelConfig` at `0x005EFAF0`;
- `ExcelWorkBookContent` at `0x005EFB20`.

These keys are visible in the procedure's string references and are not consistent with the decorated `TCompareWordDocument` name. This is direct evidence that at least some TD32 handler class labels in this connector area are stale, mismatched, or otherwise insufficient to identify the actual runtime request type.

Consequences:
1. The absence of a `TEditWordDocument.PerformMethod` symbol cannot be used to prove the Word edit handler is absent.
2. The presence of a `TCompareWordDocument` label cannot by itself establish that the code handles Word comparison.
3. Future handler mapping must correlate literal request keys, dictionary lookup callsites, VMT/registration identity, and a sanitized live Windows capture.
4. The bridge's current `EditWordDocument` request parser and response serializer must remain explicitly provisional until matched to the real Almas wire exchange.

Evidence: Run-67 artifact `15260640277`, `connector-handlers/procedure-005EF8AC.md`, and `connector-handlers/handler-string-constants.md`.

No code or workflow change was made.
