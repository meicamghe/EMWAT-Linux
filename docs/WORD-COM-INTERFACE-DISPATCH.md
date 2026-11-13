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


## Additional callback trace: WordAppNewDocument (run 18)

The expanded trace of `0x004CD54C` confirms the TD32 procedure name `TWordViwer.WordAppNewDocument`. Its signature includes `DelphiInterface<Wordxp._Document>`.

Relevant sequence:

- `[Self+0x48]` is checked against the incoming `_Document` interface pointer.
- If the document matches and the event/state flags permit processing, the code pushes that interface pointer and calls its vtable entry at `+0x2BC` (`0x004CD6BF`).
- The callback subsequently calls the same document interface's `+0xDC` entry at `0x004CD6F9`.
- The method also toggles internal state bytes at `Self+0x5C`, `Self+0x5E`, and `Self+0x5F`, indicating guarded event/state handling around the COM calls.

This makes the identification of the `+0x2BC` receiver as the Word `_Document` interface stronger: the receiver is not merely inferred from a neighboring field access; the method's incoming typed interface parameter is compared to the stored field and then used as the receiver of the virtual call.

A direct TD32 CALL-xref scan for `0x004CD54C` found no direct callers. This is consistent with an event callback being registered and invoked indirectly, but the registration-to-event firing chain still needs explicit proof. Do not interpret the absence of direct CALL xrefs as proof that the method is unused.

The exact method name at `_Document` slot `+0x2BC` remains unresolved. The next scan targets every TD32 procedure that accesses `[reg+0x2BC]` and prioritizes generated `Wordxp.TWordDocument` wrappers, which may expose the method's Pascal wrapper name.


## Callback registration cross-check (run 15)

The full `TWordViwer.OnTmrAutoSave` trace at `0x004B8A84` resolves the previously missing indirect registration for `WordAppNewDocument`.

At `0x004B8CB2..0x004B8CB8`, the code writes:
- callback owner/context: `[event-record+0x94] = Self`
- callback function: `[event-record+0x90] = 0x004CD54C`

TD32 identifies `0x004CD54C` as `TWordViwer.WordAppNewDocument`. The same registration block assigns:
- `+0x80 = 0x004CD154` (`WordAppDocumentBeforeSave`), owner at `+0x84)
- `+0x98 = 0x004CD9C0` (`WordAppWindowActivate`), owner at `+0x9C`)
- `+0x88 = 0x004D00AC` or `0x004CE030`, selected by `TWordViwer+0x3C`, owner at `+0x8C`)

This establishes that `WordAppNewDocument` is installed as an event callback through the registration structure. Therefore, the zero direct-CALL-xref result for `0x004CD54C` is expected and does not indicate dead code. The callback registration and its typed `_Document` parameter now provide a coherent path to the COM `_Document` vtable call at `+0x2BC`.

The workflow artifact name has also been corrected to `WordAppNewDocument-4CD54C.md`; the old temporary label “BeforeSave-callback” was inaccurate.

## Slot collision scan (run 19)

A full TD32 displacement scan found 28 references to +0x2BC across the package. Relevant call instructions include:

| Procedure | Callsite | Current interpretation |
|---|---:|---|
| `Wordxp.TWordDocument.PrintOutOld` | `0x00430A1E` | Word document wrapper; receiver still needs register/dataflow validation |
| `Wordxp.TWordApplication.ToggleKeyboard` | `0x00445A26` | Different Word interface type; same numeric offset must not be conflated |
| `Wordviewer.TWordViwer.WordAppNewDocument` | `0x004CD6BF` | Typed `Wordxp._Document` event parameter; strong COM document receiver evidence |
| `Wordviewer.TWordViwer.CostumizeRecAndCC` | `0x004D2844`, `0x004D2895`, `0x004D28D5` | Additional Word viewer paths; receiver type/dataflow still to validate |
| `CloseMyDoc` | `0x005E9258` | Likely relevant to document lifecycle; body trace pending |
| `UnprotectMyDoc` | `0x005E9769` | Likely relevant to document protection; body trace pending |

The scan also finds non-call reads of displacement +0x2BC in fax-related UI code, so displacement matching alone cannot identify an interface method. The +0xDC scan likewise finds many unrelated Word/Excel interface calls.

The important distinction is now explicit: +0x2BC is a byte displacement used by multiple COM interface types and possibly ordinary object fields. Only callsites where the receiver is proven to be the current Wordxp._Document interface can be used to map the _Document method at slot index 175.

The next analysis compares the complete bodies of CloseMyDoc, UnprotectMyDoc, TWordDocument.PrintOutOld, TWordApplication.ToggleKeyboard, and TWordViwer.CostumizeRecAndCC, with special attention to how each receiver is loaded.
