# Reverse-engineering parallel follow-up — 2026-11-28 Run 36

## Exact TIFF conversion diagnostics

Re-examined the existing Run-50 artifact `15253702066`, specifically `inline-constants.md`, alongside the SeparteImages caller at `0x004A0148`.

Three UTF-16LE strings are now decoded exactly:

| VA | Exact text | Meaning from callsite |
|---|---|---|
| 0x004A08F4 | `Gam Printer is in "Paused" state! please check.` | Printer-paused diagnostic before conversion |
| 0x004A0960 | `Error on setting gam printer parameters.` | GAM printer parameter/configuration failure |
| 0x004A09C0 | `Error occured during Convert Word Document to Tiff.` | Error displayed when the hidden printing Worker returns false |

The spelling `occured` is retained exactly as found in the executable. The callsite at `0x004A02B8` calls `THidePrintingThread.Execute`, tests AL, and routes false to the message at `0x004A09C0`; true alone reaches the TIFF/GDI+ continuation.

A Persian printer-paused string begins at `0x004A07F4`, but the available extraction window truncates it. Its complete wording is not inferred.

## Impact

This closes the user-facing error identity for the TIFF conversion worker, but does not close its filesystem hand-off. The exact path fragments, stale-file delete helper identity, and GAM producer remain open. Do not conflate these diagnostic strings with the Almas HTTP response contract.

Evidence:
- Run-50 artifact `15253702066`: `inline-constants.md`, `procedure-004A0148.md`, `callers-004A0E88.md`.
- Focused update: `docs/THIDEPRINTINGTHREAD-FILE-WAIT-ANALYSIS-2026-11-28.md`.

No new workflow was dispatched for this analysis. No production code or release package was changed.
