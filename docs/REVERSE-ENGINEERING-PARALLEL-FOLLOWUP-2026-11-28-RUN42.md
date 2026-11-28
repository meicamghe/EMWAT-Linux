# Reverse-engineering parallel follow-up — 2026-11-28 Run 42

## Native request parameter requiredness

Rechecked the full 796-byte procedure at `0x005EE82C` from Run-67 artifact `15260640277`.

The call flow is explicit:

1. Initialize local strings for `wordConfig`, `wordBody`, `letterImages`, and `signData`.
2. Lookup `wordConfig` at callsite `0x005EE87B`. The Boolean result is tested; false raises the literal at `0x005EEA0C`: `Requset XML is not valid (wordConfig parameter is null)`.
3. Lookup `wordBody` at `0x005EE8C5`. The Boolean result is tested; false skips assignment and retains the initialized empty string. An empty string is normalized at `0x005EE8E4–0x005EE8F2`.
4. Lookup `letterImages` at `0x005EE908` and `signData` at `0x005EE91E`. Their TryGetValue results are not tested; because the output locals were initialized first, missing values remain empty.
5. Call `TWordViwer.LoadDocument` at `0x005EE961` with:
   - EAX: `wordConfig`
   - EDX: `wordBody`
   - ECX: `letterImages`
   - stack arg: `signData`
   - additional owner/output arguments on the stack.
6. The returned string is written to the handler's output collection at `0x005EE970`; a completion byte is set at `0x005EE988`.

## Linux parser mismatch

Current `python/src/emwat_linux/editword_request.py` requires both `wordConfig` and `wordBody`, and rejects an empty document payload. The handler-level dictionary lookup only requires `wordConfig`; `wordBody`, `letterImages`, and `signData` default to empty strings when absent. However, the full `TWordViwer.LoadDocument` trace immediately decodes `wordBody` and checks the decoded string length at `0x004B77AB–0x004B77B5`; a zero-length body enters an error path at `0x004B77B7`. Therefore a non-empty decoded `wordBody` is required for successful document loading, even though the handler itself does not reject a missing dictionary key.

The current parser's non-empty-body requirement is consistent with the native success path. Its error timing/envelope may differ from Windows because Linux rejects the request during parsing rather than reaching the native loader's empty-body error path, but there is no evidence that a body-less request successfully creates a blank document. Do not weaken the parser or add blank-document creation based on the handler's unchecked TryGetValue alone.

## Required next trace

The Run-67 artifact only decodes the first 1494 of the 4960 bytes in `TWordViwer.LoadDocument`. The next trace must extend the full procedure, especially the empty-body path, and identify:
- the branch selected for an empty `wordBody`;
- any template/temp-file path used;
- when `wordConfig` fields are applied;
- where `letterImages` and `signData` are consumed;
- the returned string's exact meaning and the output collection key.

No production code was changed in this run. The existing parser mismatch is documented, not silently accepted.
