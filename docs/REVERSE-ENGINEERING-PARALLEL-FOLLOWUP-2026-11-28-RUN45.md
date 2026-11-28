# Reverse-engineering parallel follow-up — 2026-11-28 Run 45

## WordViewer loader ABI recovered from callsite and epilogue

The caller in `TScanDocument.PerformMethod` at `0x005EE961` prepares the arguments:

```asm
push    [ebp-0x10]        ; signData
push    [ebx+4]           ; handler field / owner state
lea     eax, [ebp-0x20]   ; output UnicodeString slot
push    eax
mov     ecx, [ebp-0x0C]   ; letterImages
mov     edx, [ebp-0x08]   ; wordBody
mov     eax, [ebp-0x04]   ; wordConfig
call    0x004B7724
```

The callee prologue stores EAX/EDX/ECX at `[EBP-0x18]`, `[EBP-0x1C]`, and `[EBP-0x20]` respectively. Its epilogue uses `ret 0xC`, confirming three stack arguments. The recovered ABI is therefore:

| Location | Argument |
|---|---|
| EAX | wordConfig |
| EDX | wordBody |
| ECX | letterImages |
| [EBP+8] | output UnicodeString pointer |
| [EBP+0xC] | handler field `[self+4]` |
| [EBP+0x10] | signData |

The callee accesses the output slot at `[EBP+8]` through an object method at VMT offset `+0x54` around `0x004B7F83`. Back in the handler, the result string at `[EBP-0x20]` is passed to `0x004012F8` at `0x005EE970`, then a completion byte is set at `[self+4]`/the handler state around `0x005EE988`.

This gives a concrete native hand-off chain:

`EditWordDocument candidate handler -> TWordViwer.LoadDocument(wordConfig, wordBody, letterImages, signData, out result) -> output collection -> response serialization`.

The exact meaning of `result` and the output collection key remain open. It may be the updated document body, but that must be confirmed against the response XML or a real Windows HTTP capture. Do not bind it to the Linux `wordBody` response field solely from the variable type.

## TD32 caveat

The decorated TD32 signature for `TWordViwer.LoadDocument` names only one UnicodeString argument and is incompatible with the observed six-argument call ABI. This is another direct example of stale/mismatched TD32 method metadata; use callsite register/stack flow and callee cleanup to reconstruct the ABI.

Evidence: Run-50 artifact `15253702066/procedure-004B7724.md`; Run-67 artifact `15260640277/connector-handlers/procedure-005EE82C.md`.

No production code or workflow source was modified.
