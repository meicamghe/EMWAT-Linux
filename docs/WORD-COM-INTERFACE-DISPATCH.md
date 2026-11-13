# Word COM document interface dispatch findings

Date: 2026-11-14  
Source workflow: Word lifecycle run 15  
Run ID: `43507464067`  
Analyzed BPL revision: `75e77e2d0e331626f19f9582acd3b39a85062012`

## Executive finding

The unresolved call at VMT byte offset `+0x2BC` is strongly tied to the Word COM document interface stored by `TWordViwer`, not to an independently discovered Delphi class VMT.

This changes the reverse-engineering target: the next task is to identify the Word `_Document` interface method represented by vtable byte offset `0x2BC` (DWORD slot index 175), rather than trying to force the call into the candidate Delphi VMTs.

## Evidence chain

### 1. The field at TWordViwer +0x48 is the Word document interface

The TD32 procedure signature for `TWordViwer.WordAppNewDocument` explicitly includes:

```
TObject, DelphiInterface<Wordxp._Document>
```

The field-reference scan for displacement `0x48` finds accesses to `[TWordViwer+0x48]` inside this method, including the checks and interface calls at:
- `0x004CD59B`
- `0x004CD5A1`
- `0x004CD600`
- `0x004CD695`
- `0x004CD6F3`

The same field is used in `TWordViwer.WordAppDocumentBeforeSave`, whose TD32 signature also explicitly accepts `DelphiInterface<Wordxp._Document>`. The method compares the incoming document interface against `[Self+0x48]` at `0x004CD180`, then calls methods through that interface.

Together, the declared parameter type and repeated field use strongly identify `TWordViwer+0x48` as the current Word `_Document` interface reference.

### 2. WordAppNewDocument directly dispatches through slot +0x2BC

The trace beginning at `0x004CD54C` is the `TWordViwer.WordAppNewDocument` procedure. It accesses the current document interface in `[Self+0x48]` and performs an indirect virtual/interface call using byte offset `+0x2BC` on the document object.

This is independent evidence that `+0x2BC` is a method slot on the Word document interface. It is not evidence for a method in the Delphi VMT of `TWordViwer`.

### 3. OnControlerNotify reaches the same document field

The procedure `TWordViwer.OnControlerNotify` at `0x004BB3B0` accesses `[Self+0x48]` at `0x004BB510`, then invokes its interface slot `+0xDC`.

Before that call it invokes helper `0x004D281C`. The helper reads the same `TWordViwer+0x48` field and dispatches through slot `+0x2BC`. This matches the independent `WordAppNewDocument` dispatch path.

The controller-notify chain therefore appears to reuse the current Word `_Document` COM interface. The exact semantics of the `+0x2BC` method are still unknown.

## What is established vs. unresolved

Established by static symbol/signature and instruction evidence:
- `TWordViwer.WordAppNewDocument` receives a `Wordxp._Document` interface.
- `TWordViwer.WordAppDocumentBeforeSave` also receives a `Wordxp._Document` interface and compares it with `Self+0x48`.
- `Self+0x48` is used as the current document interface in multiple Word viewer callbacks.
- Both `WordAppNewDocument` and the `OnControlerNotify -> 0x004D281C` path dispatch through byte offset `+0x2BC` on that document reference.

Not yet established:
- The exact Word type-library method name at vtable byte offset `+0x2BC`.
- Whether the method performs close, save, refresh, or another document operation.
- Whether this COM call itself triggers the local POST observed at `127.0.0.1:1984`.
- The exact connection from the COM call to `EditWordDocument`, `invoke=5208`, and `wordConfig`.

## Consequence for the VMT investigation

The earlier search for an internal EMWAT Delphi class owning slot `+0x2BC` was targeting the wrong table for this call path. Keep the existing VMT resolver as a general diagnostic, but do not use its class-name candidates to explain this Word callback dispatch.

The relevant table is the COM vtable for `Wordxp._Document`. Since COM vtables include the inherited `IUnknown`/`IDispatch` entries, the byte offset corresponds to DWORD index:

```
0x2BC / 4 = 175
```

The index is not a method name. It must be mapped against the exact Word type-library version represented by the generated `Wordxp` wrapper.

## Next steps

1. Scan all TD32 procedures for indirect calls through `[reg+0x2BC]` and `[reg+0xDC]`, prioritizing `Wordxp.TWordDocument` wrappers and `Wordviewer.TWordViwer` callbacks.
2. Match the observed slot index to the exact Word `_Document` type-library declaration/version.
3. Trace the interface reference lifecycle: where `TWordViwer+0x48` is assigned, replaced, and released.
4. Continue the controller callback and connector tracing independently; do not infer HTTP or XML behavior from the COM dispatch alone.
5. Preserve the user-confirmed behavior: closing the document applies/registers changes even without pressing Save.
