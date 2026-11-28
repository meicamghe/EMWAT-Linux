# Word BeforeClose-named helper and print-field call chain — 2026-11-28

## Evidence

- Workflow: `EMWAT parallel next contract closure`
- Run: `46120657637`
- Artifact: `15253243404`
- Procedures:
  - `TWordViewer.GetFieldIndexInList` calls `FillImgFldsForPrint` at `0x004CB361`.
  - `FillImgFldsForPrint` at `0x004CCDC8`.
  - `WordAppDocumentBeforeClose` at `0x004CCBBC`.

## Call chain

`GetFieldIndexInList` iterates a list of fields and calls `FillImgFldsForPrint` for each candidate. `FillImgFldsForPrint` then:

1. Reads the current field index/type from the viewer's field arrays at offsets `+0xE8` and `+0xEC`.
2. Calls Word document interface methods to inspect the corresponding field and its metadata.
3. For one field-validation branch, calls `WordAppDocumentBeforeClose` at `0x004CCF8F`, passing the current viewer/document context and a Boolean-like field flag.
4. Uses the returned Boolean in the loop to decide whether to continue processing the field.

The helper itself also reads the viewer field arrays at `+0xE8` and `+0xEC`, calls document interface slot `+0x38`, and delegates to `0x004BCA88`; it returns a Boolean result. Its code is field-metadata logic, not a Word close operation.

## Corrected interpretation

Despite the TD32 symbol name `WordAppDocumentBeforeClose`, the only direct caller in this binary is `FillImgFldsForPrint`, itself called by `GetFieldIndexInList`. It is therefore a print-field helper in the observed call graph, not evidence of a COM DocumentBeforeClose event callback.

The `OnTmrAutoSave` registration block still wires BeforeSave, NewDocument, WindowActivate, and a conditional LoadOptions/BeforePrintBGPrint callback; it does not install this helper. The actual Word-close-to-Almas return bridge remains unresolved and must be traced through another mechanism.

## Guardrail

Do not invoke this helper as a close lifecycle callback in a Linux implementation. Its observed contract is Boolean field filtering/validation during print-field discovery.
