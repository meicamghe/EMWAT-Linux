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

The TD32 procedure trace at `0x004CD54C` labels this routine `TWordViwer.WordAppNewDocument`, but the BPL export table names the same address `WordAppDocumentBeforeSave`, and its body logs `Document.OnBeforeSave called.` / `Document.Save`. For event classification, the export name and body strings identify it as the BeforeSave callback; retain the TD32 symbol as a naming discrepancy. It accesses the current document interface in `[Self+0x48]` and performs an indirect virtual/interface call using byte offset `+0x2BC` on the document object.

This is independent evidence that `+0x2BC` is a method slot on the Word document interface. It is not evidence for a method in the Delphi VMT of `TWordViwer`.

### 3. OnControlerNotify reaches the same document field

The procedure `TWordViwer.OnControlerNotify` at `0x004BB3B0` accesses `[Self+0x48]` at `0x004BB510`, then invokes its interface slot `+0xDC`.

Before that call it invokes helper `0x004D281C`. The helper reads the same `TWordViwer+0x48` field and dispatches through slot `+0x2BC`. This matches the independent `WordAppNewDocument` dispatch path.

The controller-notify chain therefore reuses the current Word `_Document` COM interface; wrapper analysis maps its `+0x2BC` call to `PrintOutOld()`.

## What is established vs. unresolved

Established by static signature, export-table and instruction evidence:
- The TD32-labelled `TWordViwer.WordAppNewDocument` procedure at `0x004CD54C` has an export-name/body-string discrepancy; the export table and body strings identify it as `WordAppDocumentBeforeSave`.
- The `0x004CD54C` BeforeSave callback receives a `Wordxp._Document` interface and compares it with `Self+0x48`.
- `Self+0x48` is used as the current document interface in multiple Word viewer callbacks.
- Both the `0x004CD54C` BeforeSave callback (TD32 label `WordAppNewDocument`) and the `OnControlerNotify -> 0x004D281C` path dispatch through byte offset `+0x2BC` on that document reference.

Not yet established:
- The exact method name is now mapped with high confidence to `Wordxp._Document.PrintOutOld()` through wrapper analysis in BPL run 132.
- Whether the method performs close, save, refresh, or another document operation.
- Whether this COM call itself triggers the local POST observed at `127.0.0.1:1984`.
- The exact connection from the COM call to `EditWordDocument`, `invoke=5208`, and `wordConfig`.

## Consequence for the VMT investigation

The earlier search for an internal EMWAT Delphi class owning slot `+0x2BC` was targeting the wrong table for this call path. Keep the existing VMT resolver as a general diagnostic, but do not use its class-name candidates to explain this Word callback dispatch.

The relevant table is the COM vtable for `Wordxp._Document`; byte offset `0x2BC` is DWORD slot index 175. The generated WordXP wrapper maps this `_Document` slot to the zero-argument `PrintOutOld()` method. The same numeric offset maps to different methods on other interfaces, such as `_Application.ToggleKeyboard`.

## Next steps

1. Scan all TD32 procedures for indirect calls through `[reg+0x2BC]` and `[reg+0xDC]`, prioritizing `Wordxp.TWordDocument` wrappers and `Wordviewer.TWordViwer` callbacks.
2. Match the observed slot index to the exact Word `_Document` type-library declaration/version.
3. Trace the interface reference lifecycle: where `TWordViwer+0x48` is assigned, replaced, and released.
4. Continue the controller callback and connector tracing independently; do not infer HTTP or XML behavior from the COM dispatch alone.
5. Preserve the user-confirmed behavior: closing the document applies/registers changes even without pressing Save.


## Additional callback trace: BeforeSave at 0x004CD54C (TD32 label mismatch, run 18)

The expanded trace of `0x004CD54C` confirms the TD32 procedure label `TWordViwer.WordAppNewDocument` and a `DelphiInterface<Wordxp._Document>` signature. The export table instead names this address `WordAppDocumentBeforeSave`, and the body strings explicitly log `Document.OnBeforeSave called.`; preserve this discrepancy rather than treating the TD32 label as the event's final semantic name.

Relevant sequence:

- `[Self+0x48]` is checked against the incoming `_Document` interface pointer.
- If the document matches and the event/state flags permit processing, the code pushes that interface pointer and calls its vtable entry at `+0x2BC` (`0x004CD6BF`).
- The callback subsequently calls the same document interface's `+0xDC` entry at `0x004CD6F9`.
- The method also toggles internal state bytes at `Self+0x5C`, `Self+0x5E`, and `Self+0x5F`, indicating guarded event/state handling around the COM calls.

This makes the identification of the `+0x2BC` receiver as the Word `_Document` interface stronger: the receiver is not merely inferred from a neighboring field access; the method's incoming typed interface parameter is compared to the stored field and then used as the receiver of the virtual call.

A direct TD32 CALL-xref scan for `0x004CD54C` found no direct callers. This is consistent with the callback being registered and invoked indirectly; `OnTmrAutoSave` stores its address at event-record `+0x90`. Do not interpret the absence of direct CALL xrefs as proof that the method is unused.

The `_Document` slot `+0x2BC` is now mapped with high confidence to `PrintOutOld()` from the generated `Wordxp.TWordDocument` wrapper. Remaining work is to explain the business reason for this call in the Word viewer callbacks and distinguish other interface types that reuse the same numeric offset.


## Historical callback registration cross-check — superseded by run-27 RTTI

The full OnTmrAutoSave trace stores callback/data pairs in TWordApplication event fields. Run-27 RTTI at 0x00429128 maps +0x80 to OnDocumentBeforeClose, +0x88 to OnDocumentBeforePrint, +0x90 to OnDocumentBeforeSave, and +0x98 to OnNewDocument. The corresponding callback pointers are +0x80 → 0x004CD154 (TD32 label WordAppDocumentBeforeSave), +0x88 → 0x004D00AC or 0x004CE030, +0x90 → 0x004CD54C (TD32 label WordAppNewDocument), and +0x98 → 0x004CD9C0 (TD32 label WordAppWindowActivate). Thus the earlier run-25/26 interpretation of +0x80 as BeforeSave is superseded: 0x004CD154 is the registered OnDocumentBeforeClose callback. It calls PreparePrintDocument at 0x004CB108, accesses _Document slot +0xD8 (the TD32 wrapper label Set_Saved is misleading: its wrapper at 0x0042BD94 calls +0xD8 with an output pointer and returns WordBool, so +0xD8 is the Saved getter), conditionally prompts, sets event Cancel to 0xFFFF on Cancel, and invokes interface slot +0x29C with three OleVariant arguments on Yes/No. This is the same dispatch slot used by the three-argument TWordDocument.Close wrapper at 0x0042FFF4. 0x00430070 is SaveAs2000, not Close. The no-argument Close wrapper 0x0042FEB0 uses +0x4D4; one/two/three-argument wrappers use +0x29C. The event-source IID is `00020A00-0000-0000-C000-000000000046` (`ApplicationEvents3`), and `DocumentBeforeClose` is DISPID `0x00000006` per Word interop event metadata; direct decoding of the embedded typelib member record remains optional confirmation.

The separate TD32-named WordAppDocumentBeforeClose at 0x004CCBBC is a different routine: it has only the bounded caller FillImgFldsForPrint at 0x004CCF8F and is not the callback pointer installed at +0x80. The registered OnDocumentBeforeClose callback at 0x004CD154 contains no direct HTTP request call. The parent-page message and close-time POST/response path remain to be mapped.


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

## Slot +0x2BC method mapping from the WordXP wrapper (BPL run 132)

The method name can now be mapped with high confidence for the `Wordxp._Document` interface:

- TD32 identifies `0x004309F8` as `Wordxp.TWordDocument.PrintOutOld` with no arguments.
- Its body obtains the underlying interface reference through helper `0x0042ABA0`, pushes that interface pointer, loads its vtable, and calls `[vtable+0x2BC]` at `0x00430A1E`.
- The overload `TWordDocument.PrintOutOld(OleVariant)` at `0x00430A4C` calls `[vtable+0x2C0]`; following overloads advance through `+0x2C4`, `+0x2C8`, and so on.
- This is direct wrapper-level evidence that `_Document` slot `+0x2BC` is the zero-argument `PrintOutOld()` method.
- `Wordxp.TWordApplication.ToggleKeyboard` independently calls `[vtable+0x2BC]` on an `_Application` interface. This demonstrates why the numeric slot must always be interpreted together with its interface type: on `_Application` the wrapper name is `ToggleKeyboard`, while on `_Document` it is `PrintOutOld`.

Consequently, the call at `TWordViwer.WordAppNewDocument` `0x004CD6BF`, whose receiver is the typed `_Document` event parameter, is a call to `_Document.PrintOutOld()` with no arguments. The `OnControlerNotify -> 0x004D281C` path also dispatches through `TWordViwer+0x48`, which is the same `_Document` field, so that path likewise invokes `PrintOutOld()`.

This is an important correction to the earlier open question: the `+0x2BC` dispatch in these Word viewer paths is not a save/close method. It maps to the legacy no-argument Word document print method. This does not yet explain why the callback invokes it or how the observed local POST is initiated; continue tracing the surrounding conditions and subsequent calls. Do not conflate other `+0x2BC` callsites (for example `CloseMyDoc` or `UnprotectMyDoc`) until their receiver interface types are established.

## Routine symbol at 0x004CCBBC: +0x38 dispatch path (classification unresolved)

TD32 labels the routine at `0x004CCBBC` as `TWordViwer.WordAppDocumentBeforeClose`. Its body performs two indirect calls through slot `+0x38` (`0x004CCC2C` and `0x004CCCB2`) and then calls `GetXmlFieldInfo` at `0x004BCA88).

However, the run-26 direct-call scan and run-27 full caller trace establish that this address is directly called from `FillImgFldsForPrint` in module `ScanRequestXML`. The caller passes its own EBP as a hidden static link. Thus the receiver for both `+0x38` calls is the caller's incoming ECX value, captured in its local `[ebp-0x0C]`; it is not a local interface temporary created by the target, nor has it yet been typed as a Word `_Document` interface.

The target also calls `GetXmlFieldInfo` using values assembled from the parent procedure's frame. This is consistent with a nested helper used during image-field processing. It does **not** by itself prove that this routine is registered as a Word document-close event callback. The symbol name should be treated as a TD32 procedure label, not as proof of event registration or exclusive close semantics.

- **Proven:** two `+0x38` dispatches and a subsequent `GetXmlFieldInfo` call occur in this routine.
- **Proven:** `FillImgFldsForPrint` is a direct caller, and the target receives the caller's EBP as a static link.
- **Unresolved:** whether another independent event-registration path also references this routine.
- **Unresolved:** the interface type/method at slot `+0x38), and any direct relation to the observed POST at `127.0.0.1:1984`, `invoke=5208`, or `EditWordDocument/wordConfig`.

The complete target and caller are now traced. The remaining type-identification task is to follow the incoming ECX list element from `GetFieldIndexInList`. Until independent event registration is found, do not call the `0x004CCBBC` path the proven close-time integration path.
## CostumizeRecAndCC confirms the same Word document method (BPL run 133)

TD32 resolves helper `0x004D281C` as `TWordViwer.CostumizeRecAndCC` (procedure range `0x004D281C..0x004D28F6`). Its body:

- Reads the same `TWordViwer+0x48` document interface reference.
- Calls that interface's `+0x2BC` slot at `0x004D2844`, `0x004D2895`, and `0x004D28D5` (three times).
- Sets `TWordViwer+0x5C` while processing and clears it on exit.

Combined with the `TWordDocument.PrintOutOld` wrapper mapping, these three dispatches are also calls to `_Document.PrintOutOld()` with no arguments. The method name `CostumizeRecAndCC` is proven by TD32; the exact business reason for invoking the print method three times in this routine is not yet established. Do not infer that this helper performs the local HTTP request.
## OnControlerNotify guard around the PrintOutOld calls

The full `TWordViwer.OnControlerNotify` trace (`0x004BB3B0`, BPL run 133) shows that `CostumizeRecAndCC` is not called unconditionally:

1. It obtains an event-related interface from `TWordViwer+0x44` and invokes slot `+0xE0`.
2. It obtains the event value through another interface call at `+0x1C`, then converts/reads the value and compares it with `0x14`.
3. Only when the resulting value is greater than `0x14` does it enter `CostumizeRecAndCC`.
4. After that helper returns, it invokes slot `+0xDC` on the current `_Document` interface at `TWordViwer+0x48`.

The numeric event value's business meaning is still unknown. The trace proves a guarded event-notification path and the ordering of `PrintOutOld()` calls; it does not establish that this is the close event or the local bridge POST.
## BeforeClose slot +0x38 scan (lifecycle run 22)

The package-wide scan found 462 references to displacement `+0x38`. The two `WordAppDocumentBeforeClose` calls at `0x004CCC2C` and `0x004CCCB2` are therefore not enough by themselves to identify a method.

Useful typed comparison points from the same scan:
- `Wordxp.TWordDocument.Get_Tables` calls `[vtable+0x38]` at `0x0042AF21` on a Word document wrapper's underlying interface.
- Other WordXP wrappers use the same numeric offset for different interface types, including `TWordFont.Get_Hidden`, `TWordParagraphFormat.Get_KeepTogether`, `TWordOLEControl.Get_Name`, `TWordLetterContent.Get_PageDesign`, and `TWordApplication.Get_Selection`.
- `TWordViwer.GetXmlFieldInfo` itself calls `+0x38` repeatedly on objects typed as `Wordconfigrequestxml.IXMLFieldType` in its TD32 signature.

Thus `+0x38` is interface-specific just like `+0x2BC`. The target receiver still needs to be typed from its parent-frame dataflow. The `TWordDocument.Get_Tables` wrapper is only a positive control for slot `+0x38` on a typed `_Document` interface; it does not identify the target's receiver.

## Superseded preliminary BeforeClose receiver hypothesis

The initial run-22/run-23 reading incorrectly treated the target's `[ebp-0x0C]` local as the receiver for the two `+0x38` calls. Run 24 showed the receiver load `[[ebp+8]-0x0C]`; run 27 later proved `[ebp+8]` is the caller's EBP static link, so this expression resolves to the caller's captured ECX local. The target's own `[ebp-0x0C]` is a separate managed temporary passed later to `GetXmlFieldInfo`. Do not use the earlier `_Document.Get_Tables` hypothesis until the caller's ECX list element is typed.


## BeforeClose slot +0x38 positive-control wrapper (lifecycle run 23)

Lifecycle run 23 completed successfully (run ID `43510769743`, commit `fec8b0f3f9f5c888129e2a56dee0ee169b5ca706`). Its artifact includes a trace at `0x0042AF00`, inside the TD32-bounded `Wordxp.TWordDocument.Get_Tables` wrapper:

- The wrapper obtains an interface pointer through `0x0042ABA0`, stores it in a local interface temporary, then calls its vtable slot `+0x38` at `0x0042AF21`.
- The package-wide `+0x38` scan independently labels this callsite as `Wordxp.TWordDocument.Get_Tables`.
- This is a typed positive control for the `_Document` interface slot: `_Document.Get_Tables()` is the supported mapping for slot `+0x38` on this interface.
- The trace begins at `0x0042AF00`, after the method's true prologue, so the current artifact does not contain the complete wrapper entry/exit sequence. The next run expands the trace around the method start and the shared interface accessor at `0x0042ABA0`.

**Superseded by lifecycle run 24:** the two BeforeClose-target `+0x38` calls do not use the local interface temporary at `[ebp-0x0C]`. They use the context-derived receiver `[[ebp+8]-0x0C]`. The positive-control wrapper establishes `_Document.Get_Tables()` for slot `+0x38` on a typed `_Document` receiver only; it does not type the context-derived receiver. Do not apply the `Get_Tables` name to the target's two calls without further type evidence.

The run-23 trace of helpers `0x00401420` and `0x00401478` also shows why these addresses should not be mistaken for application business logic: `0x00401420` is an indirect runtime helper thunk whose IAT target is outside the analyzed BPL image, while `0x00401478` resolves to `rtl230.bpl!@System@@CheckAutoResult`. The helper trace alone does not identify the interface value's origin.

The complete caller and target procedures are now traced. The next step is to identify the incoming ECX argument by tracing callers of `FillImgFldsForPrint` and inspecting the parent list element. The local POST and `invoke=5208` remain a separate unresolved runtime-to-static mapping.


## Correction: BeforeClose receiver is not the local at EBP-0x0C (lifecycle run 24)

The full run-24 disassembly disproves the earlier receiver-local interpretation above. The two slot calls at `0x004CCC2C` and `0x004CCCB2` do **not** load their receiver from the target's own `[ebp-0x0C]` local:

- At both sites, the code loads `eax = [ebp+8]`, then `eax = [eax-0x0C]`, then dereferences `[eax]` and calls `[eax+0x38]`.
- The target's stack-local `[ebp-0x0C]` is separately initialized via runtime helper thunk `0x00401420`; it is later passed as an argument at `0x004CCC34` into `GetXmlFieldInfo` at `0x004BCA88`. It is not the slot-call receiver.
- Run 27 resolves `[ebp+8]` as the parent procedure's EBP passed by `push ebp` at the direct callsite. Therefore `[[ebp+8]-0x0C]` is the parent procedure's local `[ebp-0x0C]`, which stores its incoming ECX value. **Resolved by run 31:** the value is an element of the `DynamicArray<DelphiInterface<Wordxp.Fields>>` output by `TWordViwer.FillPrintDocFields`; see the run-31 section below.
- The run-24 typed positive control confirms that `Wordxp.TWordDocument.Get_Tables` uses `_Document` slot `+0x38`, but it does **not** establish that the nested helper's receiver has that interface type. The earlier claim that the two target calls are likely `_Document.Get_Tables()` remains withdrawn pending identification of the caller's ECX list element.

The `Get_Tables` wrapper also clarifies its own acquisition pattern: it invokes `0x0042ABA0` with `EDX=&[ebp-4]`; that accessor checks `[self+0x78]), conditionally invokes the object's `+0x50` slot, then passes `[self+0x78]` to runtime helper `0x00401428` to populate the local interface. This is distinct from the BeforeClose receiver load. The wrapper's initial `0x00401420` call is an imported runtime thunk; the artifact resolves its IAT target outside the BPL image, so its semantic name is still unknown.

Run 24 also resolves `0x00401478` to `rtl230.bpl!@System@@CheckAutoResult`. This is compiler/runtime error checking after the interface dispatch, not an application connector call.

**Updated interpretation after run 27:** `[ebp+8]` is a Delphi nested-procedure static link to the caller's EBP, and the receiver is the caller's captured ECX local. Run 29 identifies the direct caller of `FillImgFldsForPrint` as `GetFieldIndexInList`; its ECX argument comes from an indexed list element. Run 31 resolves the list element's declared interface type as `Wordxp.Fields`. The interface slot names and independent event-registration question remain open. Keep the local POST / `invoke=5208` mapping open.


## Direct-call cross-reference and caller chain (lifecycle runs 26–29)

The TD32 direct-call scan found one direct call to `0x004CCBBC` from `FillImgFldsForPrint` at `0x004CCF8F`. Run 27 disassembled the complete caller (`0x004CCDC8–0x004CD153`) and proved that the call passes the caller's EBP as a nested-procedure static link. This resolves the target's `[[ebp+8]-0x0C]` receiver as the caller's captured incoming ECX value.

Run 29 then scanned callers of `FillImgFldsForPrint` and found one direct caller in TD32-bounded procedures:

- `TWordViwer.GetFieldIndexInList`, call at `0x004CB361)
- The caller loads ECX from `[array_or_list_base + ESI*4]` before calling `FillImgFldsForPrint`.

The current proven chain is therefore:

`GetFieldIndexInList list element → ECX → FillImgFldsForPrint local [ebp-0x0C] → nested static link → target receiver for both +0x38 calls`.

This strongly places the target in a field-index/list-processing path. Run 31 later resolves the list element's declared type as `Wordxp.Fields` through the `FillPrintDocFields` signature. The method names at slot `+0x38` remain unresolved. The direct-call scans do not exclude computed or indirect references, so independent callback registration is not categorically ruled out; it is simply not established by the current evidence.

No direct HTTP, localhost POST, `invoke=5208`, or `EditWordDocument/wordConfig` call has been identified in the target body. Do not describe `0x004CCBBC` as the proven close-time connector path.

## Nested-procedure static-link proof for the BeforeClose target (lifecycle run 27)

The complete TD32 procedure trace for `FillImgFldsForPrint` (module `ScanRequestXML`, VA range `0x004CCDC8–0x004CD153`) resolves the previously ambiguous `[ebp+8]` value in the target at `0x004CCBBC`.

At the direct callsite:

```asm
004CCF88  push     ebp
004CCF89  movzx    edx, byte ptr [ebp - 0x11]
004CCF8D  mov      eax, ebx
004CCF8F  call     0x4ccbbc
```

The target is entered with the caller's EBP as its first stack argument (the Delphi nested-procedure static link). In `FillImgFldsForPrint`, the prologue stores the incoming ECX in its local `[ebp-0x0C]`:

```asm
004CCDDD  push     edi
004CCDDE  mov      dword ptr [ebp - 0xc], ecx
004CCDE1  mov      dword ptr [ebp - 8], edx
004CCDE4  mov      dword ptr [ebp - 4], eax
```

Therefore, in the target procedure, the receiver expression `[[ebp+8]-0x0C]` resolves exactly to the caller's local `[ebp-0x0C]`, which contains the caller's incoming ECX value. This establishes the dataflow chain:

`FillImgFldsForPrint incoming ECX → caller local [ebp-0x0C] → hidden static-link pointer passed with push ebp → target [ebp+8]-0x0C → receiver for both +0x38 dispatches`.

This corrects the earlier generic description of the value as an unidentified event-record/context field. It is a captured parent-frame local supplied through the nested-procedure static link. The exact type and semantic role of the caller's incoming ECX value are still unresolved; do not yet name the two `+0x38` methods.

The surrounding caller code also shows the target is called from a loop that iterates image-field entries: `EBX` is passed in EAX, and the byte counter/flag at caller local `[ebp-0x11]` is passed in EDX. The return value is copied to EBX and tested as a Boolean. This is consistent with the target participating in image-field processing, but the exact business meaning of its return value is not established.

**Evidence status:**
- **Proven:** the target is directly called by `FillImgFldsForPrint`.
- **Proven:** the call passes the caller's EBP as a hidden static link.
- **Proven:** both target `+0x38` dispatches use the caller's incoming ECX value through local `[ebp-0x0C]`.
- **Proven:** EAX carries the loop index and EDX carries a byte-derived argument at this callsite.
- **Unresolved:** the declared type/meaning of incoming ECX, the interface methods at `+0x38`, and whether the target is separately registered as a Word close event.
- **Unresolved:** any direct causal connection from this code to the runtime POST at `127.0.0.1:1984`, `invoke=5208`, or `EditWordDocument/wordConfig`.

Lifecycle run 28 adds a complete TD32 trace of the target at `0x004CCBBC` to capture its complete procedure symbol and body alongside this caller-side static-link proof.


## Complete target symbol and procedure bounds (lifecycle run 28)

The full TD32 procedure trace identifies the exact symbol string:

`@Wordviewer@TWordViwer@WordAppDocumentBeforeClose$qqrp14System@TObjectx43System@%DelphiInterface$16Wordxp@_Document%rus`

- Module: `ScanRequestXML`
- Procedure range: `0x004CCBBC–0x004CCDC7`
- Size: `0x20C` bytes

The TD32 symbol name contains both `System.TObject` and `DelphiInterface<Wordxp._Document>` type encodings. However, the direct callsite in `FillImgFldsForPrint` passes the parent EBP as a static link and register values in EAX/EDX. The name's type encodings should therefore not be naively treated as a complete reconstruction of the nested helper's runtime argument values. The caller-side ECX capture is proven, but its declared type still needs to be recovered from the callers of `FillImgFldsForPrint`.

The target's complete body confirms the existing instruction-level sequence and does not add a direct HTTP or XML connector call: it performs the two context-derived `+0x38` dispatches, prepares arguments, then calls `0x004BCA88` (`GetXmlFieldInfo`). The observed localhost POST remains unmapped.


## Parent argument source: GetFieldIndexInList (lifecycle run 29)

The direct-call and immediate-reference scans for `FillImgFldsForPrint` at `0x004CCDC8` found one TD32-bounded direct caller:

- Caller: `TWordViwer.GetFieldIndexInList`
- Call instruction: `0x004CB361`

The call setup is:

```asm
004CB355  mov      eax, dword ptr [ebp - 8]
004CB358  mov      ecx, dword ptr [eax + esi*4]
004CB35B  mov      edx, dword ptr [ebp - 4]
004CB35E  mov      eax, dword ptr [ebp - 0x2c]
004CB361  call     0x4ccdc8
```

This proves that the `ECX` value captured by `FillImgFldsForPrint` comes from an indexed element of the caller's array/list at `[caller EBP-8 + ESI*4]`. Run 30 inspected the full `GetFieldIndexInList` body; run 31 traced its list builder and established the declared element type. The scan found only one direct caller in TD32-bounded procedures; indirect calls and computed function pointers are outside its coverage.

This strengthens the classification of `0x004CCBBC` as a nested helper reached from a field-index/list-processing path, but it still does not establish the semantic type of the list element or completely exclude another indirect event-registration path.


## Field-list construction and typed interface identification (lifecycle runs 30–31)

Run 30 established that `GetFieldIndexInList` calls `0x004CB638) with:
- EAX = the `TWordViwer` instance;
- EDX = its incoming document-interface argument;
- ECX = address of local `[ebp-8]`, used as an output location for a dynamic-array/list reference.

Run 31 recovered the full TD32 symbol for `0x004CB638`:

`@Wordviewer@TWordViwer@FillPrintDocFields$qqr43System@%DelphiInterface$16Wordxp@_Document%x40System@%DelphiInterface$13Wordxp@Fields%`

The signature identifies the input as `DelphiInterface<Wordxp._Document>` and the output as `DynamicArray<DelphiInterface<Wordxp.Fields>>`. The body begins with a `_Document` dispatch at `+0x12C` that has multiple output arguments, then uses further interface dispatches to populate the typed dynamic array. The exact meaning of the `+0x12C`, `+0x30`, and `+0x88` calls is not yet mapped. `GetFieldIndexInList` then walks this array and passes each element in ECX to `FillImgFldsForPrint`.

This resolves the receiver type chain:

`Wordxp._Document → TWordViwer.FillPrintDocFields → DynamicArray<Wordxp.Fields> → ECX → FillImgFldsForPrint → nested helper 0x004CCBBC`.

**Now proven:** the receiver used by the `+0x28` and `+0x38` dispatches in `FillImgFldsForPrint), and by both `+0x38` dispatches in the nested `0x004CCBBC) helper, is a `Wordxp.Fields` interface element. The previous generic phrase “interface-like pointer” is superseded by this declared type evidence.

**Still unresolved:** the method names/signatures corresponding to `Wordxp.Fields` slots `+0x28) and `+0x38`; whether the TD32-named nested helper is separately registered as an actual Word close callback; and the causal link to the observed local POST `127.0.0.1:1984/?invoke=5208` / `EditWordDocument/wordConfig`. Do not map these slots to `_Document.Get_Tables`; the receiver type is now explicitly `Wordxp.Fields`, not `Wordxp._Document`.

Run 31 also found one direct caller of `GetFieldIndexInList`: `TWordViwer.BGPrintWithGamPrintOptions` at `0x004C6F3F`. This places the observed nested helper path under a print-options/field-list routine, further weakening any assumption that its TD32 name alone proves it is the live close-event callback. The direct-call scan still cannot rule out indirect references or a separate event-registration path.

The next analysis extends the VMT inventory to Word wrapper classes (`TWordDocument`, `TWordFields`, `TWordField`) so that the `Wordxp.Fields` interface slots can be mapped to typed wrapper methods. It also continues to search for the independently registered close callback and the actual invoke/response dispatch.


## Word Fields/Field IID and collection-slot mapping (lifecycle run 33)

The expanded interface RTTI scan recovered the WordXP interface identities directly from the BPL:

| Interface | IID recovered from RTTI | External identity check |
|---|---|---|
| `Wordxp.Fields` | `00020930-0000-0000-C000-000000000046` | Microsoft Learn identifies this GUID as Word's `Fields` collection |
| `Wordxp.Field` | `0002092F-0000-0000-C000-000000000046` | Microsoft Learn identifies this GUID as Word's `Field` interface |
| `Wordxp._Document` | `0002096B-0000-0000-C000-000000000046` | Matches Word's `_Document` interface |
| `Wordxp.Tables` | `0002094D-0000-0000-C000-000000000046` | Matches Word's `Tables` collection |

Microsoft's Word object-model documentation describes `Fields` as a collection of `Field` objects, with a `Count` property and indexed `Fields(index)` access returning one `Field` object ([Fields interface](https://learn.microsoft.com/en-us/dotnet/api/microsoft.office.interop.word.fields?view=word-pia), [Field interface](https://learn.microsoft.com/en-us/dotnet/api/microsoft.office.interop.word.field?view=word-pia), [Fields object model](https://learn.microsoft.com/en-us/office/vba/api/word.fields)).

The call shapes in this BPL strongly support the following slot interpretation for the `Wordxp.Fields` receiver:
- `+0x28` is **very likely `Fields.Count`**: the call supplies an output location for an integer count, and the result is used as a loop bound in `FillPrintDocFields` and `FillImgFldsForPrint`.
- `+0x38` is **very likely `Fields.Item(index)`**: the call supplies an index and an output interface location; the returned interface is subsequently used as a `Wordxp.Field` receiver.

These are high-confidence semantic mappings from the typed receiver, argument layout and use of the results, corroborated by Microsoft's documented collection behavior. They are not yet a complete reconstruction of the WordXP type-library vtable declaration, because no concrete `TWordFields` wrapper VMT candidate was found in the current BPL scan. Keep the distinction between **statically proven receiver type/IID** and **strongly inferred slot names**.

Run 33 also found the only direct caller of `GetFieldIndexInList` in the scanned TD32 procedures: `TWordViwer.BGPrintWithGamPrintOptions` at `0x004C6F3F`. Thus the current call chain is explicitly under the print-options routine:

`BGPrintWithGamPrintOptions → GetFieldIndexInList → FillPrintDocFields → Fields.Count/Item → FillImgFldsForPrint → nested helper`.

This confirms the investigated `0x004CCBBC` helper is reached in a print/field-list code path. It does not exclude a separate indirect event registration, but it makes the symbol name `WordAppDocumentBeforeClose` insufficient evidence that this is the actual close-event callback.

The next type-directed trace should map methods on the returned `Wordxp.Field` interface and the `Wordxp.Range` interface, then independently locate the callback registration and the invoke=5208 return path.


## Typed Word Field helper inventory (lifecycle run 34)

The TD32 symbol inventory now exposes additional procedures with explicit Word COM interface types:

- `TWordDocument.Get_Fields` in module `EmwatConsts`, segment 1, section offset `0x2A55C`.
- `TWordViwer.FillField` takes `Wordxp._Document`, an XML field type and `Wordxp.Field`, plus two strings.
- `TWordViwer.FillImageField` takes `Wordxp._Document` and `Wordxp.Field`, plus image-related parameters and a string list.
- `TWordViwer.FillMSWFields` takes `Wordxp.Fields`.
- `TWordViwer.AddImagesToDoc` takes `Wordxp.Fields`, indices, a string and an XML field type.
- `TEmwatDocPrintHandler.FillField` also takes `Wordxp.Field` and a string.

The VMT inventory did not find Delphi wrapper classes named `TWordFields`, `TWordField`, or `TWordFieldCollection` in this BPL, while the WordXP interface RTTI itself does contain `Fields` and `Field` with the Microsoft Word IIDs recorded above. Therefore, the next useful path is to inspect the typed consumers (`FillField`, `FillImageField`, `FillMSWFields`, `AddImagesToDoc`) rather than assume a missing wrapper class exists.

The lifecycle workflow now traces these typed procedures and the `TWordDocument.Get_Fields` wrapper. Their call shapes should help identify which `Wordxp.Field` properties are read or written and whether the image-field helper at `0x004CCBBC` shares behavior with the real field-fill path.


## Typed `_Document.Get_Fields` wrapper positive control (lifecycle run 41)

The symbol inventory located `Wordxp.TWordDocument.Get_Fields` in module `EmwatConsts`; the complete procedure is at VA `0x0042B55C`. Its body calls the existing `TWordDocument` interface accessor `0x0042ABA0`, then dispatches slot `+0x80` on the returned interface. This is a typed wrapper positive control for the `Get_Fields` property on the wrapper's underlying Word document interface.

The direct-call scan found no immediate CALL xrefs to `0x0042B55C`; this wrapper may be reached through a VMT/property path or may be unused in the analyzed call paths. Importantly, this wrapper's `+0x80` dispatch does **not** identify the separate `+0x12C` dispatch in `FillPrintDocFields`. The latter has multiple output arguments and its method identity remains unresolved. Do not describe `FillPrintDocFields`'s `+0x12C` call as the proven `Get_Fields` getter until the interface method signature is mapped.


## Typed field-helper caller graph (lifecycle run 43)

Direct TD32 call-site scans established these caller relationships:

- `FillImageField` (`0x004BC30C`) has two direct calls, both from `FillTextField` at `0x004BC9CB` and `0x004BCA10`. Each call uses `push ebp` as a nested-procedure static link. Thus image-field processing is a nested branch of the text-field routine, not an independently called top-level operation in the scanned direct-call graph.
- `FillMSWFields` (`0x004C009C`) has four direct calls: three from `GetDocFieldIndex` and one from `GetCaptionItemFont`.
- `AddImagesToDoc` (`0x004C0410`) has one direct caller: `GetDocFieldIndex` at `0x004C0A5D`.
- `FillField` (`0x004BC2C4`) and `TWordDocument.Get_Fields` (`0x0042B55C`) have no direct immediate CALL xrefs in TD32-bounded procedures. Indirect/VMT/property access remains outside this scan.

This makes `GetDocFieldIndex` a central field-processing routine: it iterates a Word collection, calls `FillMSWFields` for selected entries and conditionally calls `AddImagesToDoc`; the text-field routine separately dispatches into its nested image-field helper. The exact `Wordxp.Field` property names used by `FillImageField` remain unresolved; its typed body uses slots `+0x40`, `+0x38`, and `+0x20` on interface receivers. Lifecycle run 46 adds a complete trace of the parent `FillTextField` procedure and caller scans for `GetDocFieldIndex`.


## Historical raw PE callback-pointer audit — superseded by run-27 RTTI

The whole-PE pointer scan found no raw pointer to 0x004CCBBC; its only direct bounded caller is FillImgFldsForPrint at 0x004CCF8F. Run-27 RTTI maps the callback field +0x80 to OnDocumentBeforeClose, so pointer 0x004CD154 is the registered BeforeClose callback despite TD32's WordAppDocumentBeforeSave label. The complete field crosswalk is +0x80 OnDocumentBeforeClose → 0x004CD154; +0x88 OnDocumentBeforePrint → 0x004D00AC/0x004CE030; +0x90 OnDocumentBeforeSave → 0x004CD54C; +0x98 OnNewDocument → 0x004CD9C0. Earlier name-based classifications are superseded.

The registered OnDocumentBeforeClose callback at 0x004CD154 has no direct HTTP call. It reads _Document.Saved through slot +0xD8 (the TD32 wrapper label Set_Saved is reversed; its wrapper returns WordBool), conditionally prompts, sets event Cancel on Cancel, and invokes interface slot +0x29C with three OleVariant arguments on Yes/No. The separate TD32-named WordAppDocumentBeforeClose at 0x004CCBBC is not the installed pointer and has only the FillImgFldsForPrint caller in the bounded scan. The bridge's parent-page message and final commit path remain to be mapped.


## Additional WordXP collection RTTI (lifecycle run 45)

The expanded interface scan recovered three more WordXP interfaces:

- `StoryRanges`: IID `0002098C-0000-0000-C000-000000000046`.
- `FormFields`: IID `00020929-0000-0000-C000-000000000046`.
- `FormField`: IID `00020928-0000-0000-C000-000000000046`.

The targeted scan did not recover a `Range`/`_Range` interface RTTI record in this BPL, even though typed Word field operations call methods on interface values returned from `Wordxp.Field`. The new `StoryRanges` IID is a plausible lead for the still-unmapped `_Document +0x12C` dispatch in `FillPrintDocFields`, because that routine calls `_Document +0x12C` with a story-like selector and then enumerates returned interface data. However, this is only a candidate: the method has multiple output arguments, and no typed wrapper currently maps it to `StoryRanges`. Do not label `+0x12C` as `StoryRanges` until its output IID or a matching wrapper is proven.

The presence of `FormFields` and `FormField` RTTI also shows that this BPL imports Word's separate form-field collection model in addition to ordinary `Fields`/`Field`. The next symbol inventory now includes `StoryRanges`, `FormFields`, and `FormField` names to locate typed getters/consumers and avoid conflating the two field models.


## Text-field parent and field-name lookup chain (lifecycle run 47)

The full `FillTextField` procedure at `0x004BC980` is now traced. Its two calls to the nested `FillImageField` helper at `0x004BC9CB` and `0x004BCA10` both pass the parent EBP as a static link. The helper is therefore a nested branch of text-field handling, with the `Wordxp.Field` receiver and document context captured from the parent frame.

The direct-call scan found nine callers of `FillTextField`:
- four from `GetXmlFieldInfo` (`0x004BCB1E`, `0x004BCB38`, `0x004BE89C`, `0x004BE8B6`);
- three from `GetDocFieldIndex` (`0x004C0937`, `0x004C0BEF`, `0x004C0DF3`);
- two from `FillImgFldsForPrint` (`0x004CCF04`, `0x004CCF5B`).

The direct-call scan for `GetDocFieldIndex` found one caller: `GetDocFieldName` at `0x004BBB2B`. This makes the current field-resolution graph:

`GetDocFieldName → GetDocFieldIndex → FillTextField → nested FillImageField`

with additional entry paths from `GetXmlFieldInfo` and `FillImgFldsForPrint`. This is a content/field processing graph, not evidence of a document-close event. The next trace expands `GetDocFieldName` to identify its inputs, callers and relationship to the XML field configuration.


## Second close-callback symbol candidate from uSendLog (lifecycle run 49)

The expanded TD32 name inventory found a second routine named `WordAppDocumentBeforeClose`, distinct from the nested print helper at `0x004CCBBC`:

- Unit/form: `uSendLog.TfrmShowAutoSaveFiles.WordAppDocumentBeforeClose`
- VA: `0x005EC580`
- TD32 signature includes `System.TObject` and `DelphiInterface<Wordxp._Document>`.
- Procedure size: `0x12` bytes.

The same unit contains `TfrmShowAutoSaveFiles.CloseWordApp` at `0x005EBDA8` and `TfrmShowAutoSaveFiles.FormClose` at `0x005EBF20`. The inventory also finds Word wrapper methods `TWordDocument.Close()` at `0x0042FEB0` and three overloads at `0x0042FF08`, `0x0042FF7C`, and `0x0042FFF4`, plus `TWordDocument.ClosePrintPreview` at `0x00433A84`. `WordCompareCommandUnit.CloseMyDoc` is at `0x005E9174`.

These are **candidates, not yet the proven letter-editor close path**. The `uSendLog` handler belongs to the autosave-files form and may be limited to that UI. Lifecycle run 52 now traces its full body, direct/indirect references and raw PE pointer references, together with `CloseWordApp`, `FormClose`, `CloseMyDoc`, and the `TWordDocument.Close` wrappers. The next classification depends on those bodies and caller chains, not the TD32 names alone.


## GetDocFieldName field-resolution routine (lifecycle run 53)

The complete TD32 trace identifies `TWordViwer.GetDocFieldName` at `0x004BB81C` (size `0x954`). It obtains the current Word document interface from the viewer object, calls `FillPrintDocFields` to populate the typed `DynamicArray<Wordxp.Fields>` at viewer field `+0xA4`, then iterates the configured field-name strings stored in that array and calls `GetDocFieldIndex` for each entry. The Boolean result is used to update viewer state/flags.

This provides the parent context for the `GetDocFieldIndex` calls seen in run 47: it is a field-name-to-Word-field resolution routine operating over the configured field list. The direct CALL scan found no direct callers of `GetDocFieldName` inside TD32-bounded procedures; an indirect/VMT/property caller or an unreferenced legacy path remains possible. Its call graph is therefore proven downward, while its entry path remains unresolved.


## uSendLog close handler and Word Close wrappers (lifecycle runs 54–55)

The second `WordAppDocumentBeforeClose` candidate is now fully disassembled:

```asm
005EC580  push ebp
005EC581  mov ebp, esp
005EC583  cmp word ptr [ecx], 0x2e
005EC587  jne 0x5ec58e
005EC589  call 0x5ebda8  ; TfrmShowAutoSaveFiles.CloseWordApp
005EC58E  pop ebp
005EC58F  ret 4
```

This is a tiny event handler on `TfrmShowAutoSaveFiles`: it checks a word at the event argument pointer in ECX and, when equal to `0x2E`, calls the form's `CloseWordApp`. It has no direct CALL xrefs and no TD32 immediate references. The raw pointer scan does find the address bytes at `0x005EB524` and `0x005EB607` in `.text`, consistent with static method metadata/table references; the form resource scan is now being added to verify the DFM event binding.

`CloseWordApp` has exactly two direct callers in the scan: the form's `btnShowFileClick` handler at `0x005EB81F` and the `WordAppDocumentBeforeClose` event handler at `0x005EC589`. It iterates the autosave form's document collection at `[this+0x3C0]`, performs per-document operations, then calls a method at interface slot `+0x104` on the application-like object at `[this+0x3C0]`. The exact interface type/method name still needs mapping. This path belongs to the autosave-files form; it is not evidence that the main letter editor's close event is handled here, and no local POST/`invoke=5208` call appears in this 18-byte handler.

The corrected WordXP wrapper traces show:
- no-argument TWordDocument.Close at 0x0042FEB0 dispatches interface slot +0x4D4;
- one-, two-, and three-OleVariant Close overloads at 0x0042FF08, 0x0042FF7C, and 0x0042FFF4 dispatch slot +0x29C;
- ClosePrintPreview at 0x00433A84 dispatches slot +0x36C;
- 0x00430070 is SaveAs2000, not Close.

The registered BeforeSave callback at 0x004CD154 directly calls interface slot +0x29C with three OleVariant arguments on Yes/No. This is the same dispatch slot used by the three-argument Close wrapper at 0x0042FFF4. The underlying Word COM type-library metadata is not independently resolved. Separately, WordCompareCommandUnit.CloseMyDoc dispatches slot +0x2BC, which the typed positive control maps to _Document.PrintOutOld(); despite its name, this is not a document-close call.

**Current classification:** the `uSendLog` callback is a real close-related handler for the autosave-files UI, but not yet the main letter-editing close path. The original `0x004CCBBC` remains a nested print/field helper with no exact raw pointer references. The main close-triggered update and localhost POST still need a separate event/connector trace.


## Autosave form DFM resource evidence (lifecycle run 57)

The named RCDATA resource `TFRMSHOWAUTOSAVEFILES` was extracted and scanned (1,149 bytes; SHA256 recorded in the CI artifact). Its printable properties include `OnClose=FormClose`, `OnCreate=FormCreate`, and `OnShow=FormShow`, plus the list/button event handlers. The resource contains no `WordAppDocumentBeforeClose` or Word-application event property string. `TFRMSENDLOG` likewise contains only its form/UI event properties.

This confirms that the second `WordAppDocumentBeforeClose` handler is not wired by a visible DFM event property in `TFRMSHOWAUTOSAVEFILES`. If it is connected to Word, that connection is likely established by runtime code in `FormCreate`, `btnShowFileClick`, or a helper that creates/opens the preview Word instance; that remains to be traced. Do not describe the handler as a statically DFM-bound Word event.


### btnShowFileClick confirmation (lifecycle run 59)

The complete `TfrmShowAutoSaveFiles.btnShowFileClick` body is only ten bytes and consists of a direct call to `CloseWordApp` followed by return. The two direct callers of `CloseWordApp` are exactly this button handler and the autosave form's `WordAppDocumentBeforeClose` handler. Thus this callback/button pair is self-contained autosave-preview cleanup; it does not open the main letter, invoke the Word field pipeline, or call the local connector in the traced body.


### Close wrapper reachability audit (lifecycle run 60)

Direct-call scans found **zero** TD32-bounded CALL sites for all four `TWordDocument.Close` wrappers (`0x0042FEB0`, `0x0042FF08`, `0x0042FF7C`, `0x0042FFF4`) and for `ClosePrintPreview` (`0x00433A84`). Each Close wrapper has one exact raw pointer occurrence in `.text` near WordXP class metadata. The three overload pointers at `0x00412AB6`, `0x00412ADB`, and `0x00412B15` are immediately followed by method-name metadata for `Close` and argument-count markers (1, 2, and 3 respectively); these are published method/RTTI entries, not callsites. The no-argument pointer at `0x0041CB94` is likewise a static metadata occurrence. This suggests the wrappers are exposed through class metadata or property dispatch and are not directly called in the analyzed BPL paths. Do not treat these wrappers as the main close-time update path without a VMT/property caller or runtime trace.


## EMWAT method dispatcher entry (lifecycle run 62)

The complete TD32 trace at `0x0046C82C` (433 bytes; symbolized as `TEmwatMethod.Invoke`) is the inner dictionary/XML helper. It accepts a `TDictionary<AnsiString, AnsiString>`, iterates dictionary data, constructs XML method/parameter nodes, and performs an indirect dispatch through slot `+0x68` at `0x0046C921`. The public virtual `TEmwatMethod.Invoke` wrapper is at `0x0046C9E0` (the BPL export name and shared VMT slot `+0x0C`); it calls this helper, then dispatches the concrete connector's `PerformMethod` through VMT slot `+0x10`. The concrete connector signatures and service-side `TMethodInfo.Params` are both typed as `TDictionary<System.AnsiString, System.AnsiString>`. The exact receiver type for the helper's `+0x68` call remains unresolved.

The TD32 direct-call scan found only one direct CALL to `TEmwatMethod.Invoke`, from `Finalization` at `0x0046CA67`. Therefore, the normal request path may enter it indirectly through a VMT/interface dispatch or another module. The trace does not itself identify the numeric request ID `5208`, the HTTP query parser, or the `EditWordDocument/wordConfig` response generator.

Representative concrete connector implementations now traced include `TCompareWordDocument.PerformMethod` (`0x005EF8AC`), `TEditExcelWorkBook.PerformMethod` (`0x005EF300`), and `TShowSendLog.PerformMethod` (`0x005EFE4C`). These are useful structural comparisons for the missing/undecoded Word-edit method implementation, but should not be assumed to be the Word method itself.


## Whole-package RCDATA form audit (lifecycle run 64)

The wildcard RCDATA scan found 14 named resources, including `TFRMIMAGETOOLS`, `TFRMSENDLOG`, `TFRMSHOWAUTOSAVEFILES`, `TFRMSIMPLEIMAGEEDITOR`, `TFRMWORDPRINTOPTION`, and `TPROCESSINGFORM`. The only form resources with visible `OnClose` properties are the image-tools, autosave-files, and simple-image-editor forms; their handlers are UI cleanup paths. `TFRMWORDPRINTOPTION` exposes `OnCreate` and other dialog properties but no Word document close event. No resource contains a `WordAppDocumentBeforeClose`, `OnDocumentBeforeClose`, or WordApplication event binding string.

The package metadata also lists the Word-related units `WordViewer`, `WordConfigRequestXML`, `WordRequestXML`, `WordResponseXML`, and `WordProcessing`, alongside `EmwatConnector` and `uSendLog`. There is no named RCDATA form resource for the main Word editor in this package; `TWordViwer` is implemented as a code class in `ScanRequestXML`. This further points away from a DFM-bound close handler and toward a runtime COM connection point or browser-side close/request logic. It does not rule out non-DFM event hookup.


## Run 30: complete GetFieldIndexInList list traversal

Lifecycle run 30 produced the complete TD32 body for `TWordViwer.GetFieldIndexInList` (`0x004CB1B4–0x004CB5E3`). Relevant sequence:

1. At `0x004CB338`, it calls `0x004CB638`, passing the viewer instance, the incoming string parameter, and an output address for a local at `[ebp-8]`.
2. It obtains the resulting collection count via `0x004CB340 → 0x004013E0`.
3. It iterates from index zero; at `0x004CB355–0x004CB361`, each 32-bit element at `[array_base + ESI*4]` is loaded into ECX and passed to `FillImgFldsForPrint`.
4. The Boolean result is stored in local `[ebp-0x2D]`; a true result stops further work in the loop.
5. After the loop, it invokes slot `+0xDC` on the incoming object stored in `[ebp-4]` at `0x004CB36D–0x004CB37B`.
6. A later conditional branch invokes slot `+0x2EC` on that same incoming object at `0x004CB3FE–0x004CB41E`, passing the saved list/result values.

This makes the source of the nested helper receiver precise: it is an element in a collection returned by `0x004CB638`, not an independently discovered close-event context. The collection element's interface type remains to be established by tracing the provider and comparing typed consumers.

**Caution:** the routine's TD32 signature labels the explicit parameter as `System.UnicodeString`; the array provider and element representation must be inspected before assigning semantic names to the local collection or its elements. A 32-bit pointer-sized element alone does not prove a particular COM interface.

Run 31 extends the workflow to capture the array provider `0x004CB638`, its direct callers, the typed `FillImageField` control at `0x004BC5D8`, and the field-index helper at `0x004CB5E4`.


## Service-driven TEmwatMethod virtual dispatch (lifecycle run 76)

The corrected class-RTTI scanner now finds the small connector classes (instance size `0x0C`) that the earlier `0x20` size threshold excluded. It validates each class typeinfo's direct `ClassType` pointer against the VMT self-pointer. The following classes derive from `TEmwatMethod` and share the same VMT slot `+0x0C = 0x0046C9E0`:

| Class | VMT | Slot `+0x0C` | Slot `+0x10` |
|---|---:|---:|---:|
| `TEditWordDocument` | `0x005ED764` | `0x0046C9E0` | `0x005EE82C` |
| `TScanDocument` | `0x005ED884` | `0x0046C9E0` | `0x005EEB48` |
| `TFaxDocument` | `0x005ED99C` | `0x0046C9E0` | `0x005EEDFC` |
| `TGetEmwatVersion` | `0x005EDAB4` | `0x0046C9E0` | `0x005EF110` |
| `TSetEmwatVersion` | `0x005EDBD4` | `0x0046C9E0` | `0x005EF218` |
| `TUpgradeEmwat` | `0x005EDCF4` | `0x0046C9E0` | `0x005EF24C` |
| `TImageEdition` | `0x005EDE0C` | `0x0046C9E0` | `0x005EF300` |
| `TEditExcelWorkBook` | `0x005EDF24` | `0x0046C9E0` | `0x005EF8AC` |
| `TCompareWordDocument` | `0x005EE04C` | `0x0046C9E0` | `0x005EFC54` |
| `TShowEmwatSetting` | `0x005EE174` | `0x0046C9E0` | `0x005EFD4C` |
| `TShowLastEditedDocs` | `0x005EE294` | `0x0046C9E0` | `0x005EFE4C` |
| `TShowSendLog` | `0x005EE3BC` | `0x0046C9E0` | `0x005EFF4C` |

The base `TEmwatMethod` VMT at `0x0046ABFC` has slot `+0x0C = 0x0046C9E0` and slot `+0x10 = 0x00401068` (the RTL abstract-error thunk). Subclasses override slot `+0x10` with their own method target.

The body at `0x0046C9E0` (TD32 symbol label: `Emwatmethod.Finalization`, BPL export name: `TEmwatMethod.Invoke`) is the public virtual wrapper in this call path. The service dispatcher calls class VMT slot `+0x0C`; this body then:
1. calls the inner dictionary/XML helper at `0x0046C82C` with the parameter dictionary;
2. calls the same object's virtual slot `+0x10` at `0x0046CA88`, passing the parameter dictionary and output string.

This proves the two-stage dispatch:
`service GetClass("T"+className) → instance VMT+0x0C (public Invoke wrapper 0x46C9E0) → inner XML/dictionary helper (0x46C82C) → instance VMT+0x10 (concrete method)`.

**Most important result:** the XML request class `EditWordDocument` resolves to `TEditWordDocument`, whose VMT slot `+0x10` points to `0x005EE82C`. This provides the previously missing concrete entry address for the Word-edit method, even though the current TD32 procedure inventory has no procedure record at that address. Its machine code is present and can be traced as a raw PE range.

**Symbol-label caveat:** several TD32 `PerformMethod` labels do not align with the class whose VMT slot points at that address (for example, `TEditExcelWorkBook` VMT slot `+0x10` points at `0x005EF8AC`, while the TD32 procedure label at that address says `TCompareWordDocument.PerformMethod`). Treat the class VMT slot target as the authoritative dynamic-dispatch address; reconcile the name mismatch by inspecting each body and its actual behavior. Do not silently relabel the TD32 procedure.

The `TEditWordDocument` method target `0x005EE82C` begins a substantial body that reads the `document` parameter from the parsed dictionary and calls helper `0x004B7724`. The next step is to identify that helper and trace the complete method body through document creation/Word automation and response handling.


## TEmwatMethod.Invoke +0x68 receiver: XML-object path under investigation (runs 79–83)

The complete TD32 procedure for TEmwatMethod.Invoke is 0x0046C82C–0x0046C9DC. Its signature explicitly accepts TDictionary<System.AnsiString,System.AnsiString>; on entry EAX is the TEmwatMethod instance, EDX is the parameter dictionary, and ECX is the output-string reference.

The receiver dataflow at the unresolved +0x68 call (0x0046C921) is:

- Local [ebp-4] is dispatched through +0xB0 at 0x0046C8D8.
- The resulting object in [ebp-0x1C] is dispatched through +0xCC at 0x0046C8E6, with output address [ebp-8].
- The object stored in [ebp-8] is then the receiver for the +0x68 call at 0x0046C921.

Run 1 of the focused receiver workflow resolves an important part of this chain: the only direct caller of helper 0x0044C238 is TEmwatMethod.Invoke at 0x0046C877, and TD32 identifies 0x0044C238 as Emwatxml.TXMLEmwatType.AfterConstruction. The caller passes the address of local [ebp-4] as EAX. The corresponding class RTTI in the same BPL identifies TXMLEmwatType at VMT 0x0044B9AC, instance size 0x5C, with one implemented interface at IOffset +0x50 and interface VTable 0x0044B878 (IID e7e941dd-cf1c-4856-9cec-8b6d2370c439).

The XML interface chain is now mapped substantially further:
- [ebp-4] is a managed interface variable initialized by TXMLEmwatType.AfterConstruction (0x0044C238). Its interface VTable is 0x0044B878, with interface offset +0x50.
- The +0xB0 call on [ebp-4] dispatches through TXMLEmwatType's interface VTable entry at 0x0044B928. Its thunk 0x0044B709 adjusts EAX by -0x50 and jumps to 0x0044C458, whose TD32 symbol is TXMLMethodType.AfterConstruction. That routine receives the output address in EDX and initializes a TXMLMethodType interface into the caller's local.
- The +0xCC call on [ebp-1C] dispatches through TXMLMethodType's interface VTable entry at 0x0044BCC4. Its thunk 0x0044BA61 adjusts EAX by -0x70 and jumps to 0x0044C754, whose TD32 symbol is TXMLMethodType.Insert. The routine calls its own VMT slot +0x20 with index -1 and an output local, then returns the resulting interface through the caller-provided output pointer.
- The resulting [ebp-8] is a managed interface variable. The next two calls on it use +0xB0 with the first dictionary-pair member ([ebp-0x24]) and +0x68 with the second member ([ebp-0x28]). RTTI identifies TXMLParamType with interface offset +0x50 and interface VTable 0x0044BF5C; that VTable has entries at +0xB0 (thunk 0x0044BDF5) and +0x68 (thunk 0x0044BEB5). This strongly identifies [ebp-8] as the TXMLParamType interface returned by TXMLMethodType.Insert.
- The TXMLParamType +0xB0 interface thunk at 0x0044BDF5 adjusts EAX by -0x50 and jumps to implementation target 0x0044C8E4. Its TD32 symbol is misleadingly labelled Emwatxml.Finalization, but the body calls 0x0044B4C0 with the first dictionary-pair member as the value and the static string at 0x0044C95C as the attribute name. The helper's IAT mapping is xmlrtl230.bpl!TXMLNode.SetAttribute(UnicodeString, OleVariant), and the decoded constant at 0x0044C95C is exactly name. Therefore TXMLParamType +0xB0 sets the XML node's name attribute to the dictionary key. Its +0x68 thunk at 0x0044BEB5 adjusts EAX by -0x50 and jumps to shared implementation target 0x0044B568, whose IAT mapping is xmlrtl230.bpl!TXMLNode.SetText(UnicodeString); therefore the second dictionary-pair member is written as the XML parameter node's text. The pair is serialized as an XML parameter element with name attribute and text content.

After the parameter loop, Invoke calls the TXMLEmwatType interface at slot +0x54 (callsite 0x0046C937), passing an output reference at [ebp-0x34]. The returned XML string is then copied into the caller-provided output string through runtime helper 0x004012F8. This establishes the XML serialization boundary inside Invoke. The interface VTable slot address is 0x0044B8CC; its target method name is not yet mapped, so describe it as the XML-string getter/serializer by behavior only. The TXMLMethodType interface +0xC8 method-name call at 0x0046C8BE resolves through thunk 0x0044BA59 (Self adjustment -0x70) to implementation target 0x0044C62C. TD32 labels this target TXMLMethodType.Get_Param, but its body passes the incoming method-name string and a static constant at 0x0044C6A4 to xmlrtl230.bpl!TXMLNode.SetAttribute; the exact attribute name is pending string decoding. The TXMLEmwatType +0x54 serializer getter at VTable address 0x0044B8CC points to thunk 0x0044B7A9; its implementation remains to be mapped.

Run 3's VMT/interface dump adds a useful exclusion and candidate:
- The TXMLEmwatType class VMT at 0x0044B9AC has a null value at class slot +0x68 (address 0x0044BA14). Therefore the +0x68 receiver cannot be this class object using its ordinary class VMT.
- TXMLEmwatType implements IID e7e941dd-cf1c-4856-9cec-8b6d2370c439 through interface offset +0x50, VTable 0x0044B878. That interface VTable has a valid +0x68 entry at 0x0044B8E0, containing thunk pointer 0x0044B7D1. This is a candidate only; no dataflow yet proves [ebp-8] is this interface pointer.
- The TXMLEmwatType class VMT slot +0x68 is null (address 0x0044BA14), so the `+0x68` receiver is not this class object through its ordinary class VMT. The bytes at class-VMT-relative addresses +0xB0 (0x0044BA5C) and +0xCC (0x0044BA78) decode as relative-JMP code stubs rather than valid 32-bit VMT function-pointer entries; do not interpret those code bytes as the class's dispatch table. The observed `Invoke` call at +0xB0 is instead consistent with the implemented-interface VTable at 0x0044B878, whose +0xB0 slot is the pointer at 0x0044B928.
- RTTI also identifies TXMLMethodType (VMT 0x0044BD48, interface offset +0x70, VTable 0x0044BBF8) and TXMLParamType (VMT 0x0044C08C, interface offset +0x50, VTable 0x0044BF5C). Their VMT/interface slot windows are now being traced to test whether TXMLMethodType is the +0xCC receiver and TXMLParamType is the +0x68 receiver.


**Correction to the preliminary enumerator hypothesis:** Invoke also calls 0x0046DE84 and 0x0046E324 while processing the parameter dictionary. The latter is TD32-labelled TDictionary<System.AnsiString,System.AnsiString>.TPairEnumerator.DoGetCurrent, and its two direct calls are separate from the +0x68 dispatch at 0x0046C921. The VMT inspection of TDictionary.TPairEnumerator (VMT 0x0046BEE8) shows DoMoveNext at +0x00 and its constructor at +0x04; the area at +0x68 is RTTI/data, not an executable class virtual slot. Therefore the earlier suggestion that [ebp-8] itself was the TPairEnumerator is withdrawn. Dictionary enumeration is present in the routine, but it does not identify the +0x68 receiver.



### XML interface VTable mapping (receiver run 84)

The follow-up VTable inspection resolves the dispatch domain of the first call and rules out treating every displacement as a class-VMT slot:

- `TXMLEmwatType` has VMT `0x0044B9AC` and one implemented interface: IID `e7e941dd-cf1c-4856-9cec-8b6d2370c439`, interface offset `0x50`, VTable `0x0044B878`.
- The first `+0xB0` call in `Invoke` is therefore consistent with the `TXMLEmwatType` interface VTable slot at `0x0044B928`, whose pointer is `0x0044B709`. The same interface's `+0x68` slot is at `0x0044B8E0` and points to thunk `0x0044B7D1`.
- The `+0xC8` and `+0xCC` addresses are beyond this interface VTable's mapped entries; in the PE they overlap the following interface-table metadata. Therefore the `+0xCC` call at `0x0046C8E6` must be made on the object returned into `[ebp-0x1C]`, not on the original `TXMLEmwatType` interface.
- `TXMLMethodType` is a separate class at VMT `0x0044BD48`; its implemented interface has IID `55d7b886-a428-4f24-8766-6af7ab8f792d`, interface offset `0x70`, and VTable `0x0044BBF8`. Its `+0x68` and `+0xCC` slots are present at `0x0044BC60` and `0x0044BCC4`, pointing to thunks `0x0044BB51` and `0x0044BA61` respectively.

This makes `TXMLMethodType` a concrete candidate for one of the returned XML interface objects, but does not yet prove that it is the runtime type of `[ebp-0x1C]` or `[ebp-8]`. The thunk traces now resolve the implementation entry addresses: `0x0044B709` adjusts EAX by `-0x50` and jumps to `0x0044C458` (the `TXMLEmwatType +0xB0` implementation); `0x0044BA61` adjusts by `-0x70` and jumps to `0x0044C754` (the `TXMLMethodType +0xCC` implementation); `0x0044B7D1` adjusts by `-0x50` and jumps to `0x0044B568`; and `0x0044BB51` adjusts by `-0x70` and jumps to the same `0x0044B568` body for the respective `+0x68` interface slots. These are now the implementation entry points to correlate with the out parameters in `Invoke`; their complete TD32 bodies are being traced in the focused receiver workflow.



### Invoke's XML parameter-object construction (receiver run 85)

The implementation bodies now identify the middle of the chain:

- The `TXMLEmwatType` interface `+0xB0` thunk `0x0044B709` adjusts the interface pointer by `-0x50` and jumps to `0x0044C458`. TD32 labels this body `TXMLMethodType.AfterConstruction`. It builds/initializes a `TXMLMethodType` interface and writes the result through its out parameter, matching `[ebp-0x1C]` in `Invoke`.
- The `TXMLMethodType` interface `+0xCC` thunk `0x0044BA61` adjusts by `-0x70` and jumps to `0x0044C754`. TD32 labels this body `TXMLMethodType.Insert`. It calls the method interface's `+0x20` slot with index `-1`, then assigns the returned interface to its own out parameter, matching `[ebp-8]` in `Invoke`.
- RTTI identifies a separate `TXMLParamType` class at VMT `0x0044C08C`, with implemented-interface VTable `0x0044BF5C` at interface offset `0x50`. Its interface `+0x68` slot is at `0x0044BFC4` (pointer `0x0044BEB5`); its `+0xB0` slot is at `0x0044C00C` (pointer `0x0044BDF5`). These are the candidate setters invoked on the returned parameter interface. The thunk bodies resolve `+0xB0` (`0x0044BDF5`) to `0x0044C8E4`, and `+0x68` (`0x0044BEB5`) to shared XML-interface implementation `0x0044B568`. The `+0x68` target is shared by the `TXMLEmwatType`, `TXMLMethodType`, and `TXMLParamType` interface VTables after their respective `this` adjustments. The `+0x68` body is now identified by its IAT target as `xmlrtl230.bpl!TXMLNode.SetText`; therefore the second dictionary-pair string is assigned as the XML parameter node's text/value. The `+0xB0` body at `0x0044C8E4` calls helper `0x0044B4C0` with the first pair string and a string constant at `0x0044C95C`; its imported target and that literal are being resolved to identify the key attribute exactly.

In `Invoke`, the two dictionary strings from the `TPairEnumerator` are then passed separately to that returned object: the first pair string goes to interface slot `+0xB0` at `0x0046C8FE`, and the second goes to `+0x68` at `0x0046C921`. This strongly supports the interpretation that `Invoke` materializes each dictionary entry as a child XML parameter object and assigns its two string fields. The exact published property names for those two setters remain pending the TXMLParamType thunk/body trace.

A second, distinct +0x68 dispatch exists in the shared base wrapper at 0x0046CBB7 (TD32 range 0x0046C9E0–0x0046CDF7). It uses a different local receiver [ebp-4], created in the exception/response path. Do not assume the two +0x68 calls share an interface or class type.

The focused receiver workflow adds the TXMLEmwatType class VMT window and its implemented-interface VTable window around offsets +0x68, +0xB0, and +0xCC, plus a trace of helper 0x0044B468. These will determine whether the +0xB0 call belongs to the class VMT and help identify the XML child/interface returned into [ebp-8].

**Still unresolved:** the exact type of [ebp-0x1C], the exact type and +0x68 method of [ebp-8], and the distinct receiver type at 0x0046CBB7. Continue from the XML class/interface tables and the constructor/helper dataflow; do not infer method names from the numeric displacement alone.


## XML parameter key/value setter confirmation (focused run 11)

Focused GitHub Actions run `43571811038` completed successfully (artifact `14105075475`). The new traces resolve both sides of the `TXMLParamType` setter pair:

- The `+0xB0` interface thunk `0x0044BDF5` adjusts `Self` by `-0x50` and enters `0x0044C8E4`.
- At `0x0044C91F`, that implementation calls `0x0044B4C0` with the first pair string and constant pointer `0x0044C95C`.
- `0x0044B4C0` is an IAT thunk to `xmlrtl230.bpl!TXMLNode.SetAttribute(UnicodeString, OleVariant)`.
- The Delphi string at `0x0044C95C` decodes to exactly `name`.
- The `+0x68` interface thunk `0x0044BEB5` enters `0x0044B568`, an IAT thunk to `xmlrtl230.bpl!TXMLNode.SetText(UnicodeString)`.

Therefore, statically confirmed: each `TDictionary<AnsiString,AnsiString>` entry processed by `TEmwatMethod.Invoke` becomes a child XML parameter node whose `name` attribute is the dictionary key and whose text content is the dictionary value. This is the precise parameter serialization shape; it does not yet establish the complete enclosing method/request XML or its wire encoding.

The workflow artifact contains the helper disassembly and string decode. The prior run-9 wording that called the attribute and literal unresolved is superseded by this section.

## XML serializer and method envelope confirmation (focused run 16)

Focused run 16 (`43573798242`, artifact `14105735885`) resolves the serializer dispatch and method metadata:

- The `TXMLEmwatType` implemented-interface `+0x54` slot points to thunk `0x0044B7A9`. The thunk adjusts `Self` by `-0x50` and jumps to `0x0044B590`.
- `0x0044B590` is an IAT thunk to `xmlrtl230.bpl!TXMLNode.GetXML`. Therefore the interface getter used by `TEmwatMethod.Invoke` to produce its output string is the XML node serialization getter, not an EMWAT-specific custom encoder.
- The method-name setter implementation at `0x0044C62C` calls `TXMLNode.SetAttribute` with literal `class` and the supplied method name.
- The method-node constructor at `0x0044C458` passes literal `method` into its XML element setup path. It also invokes a second helper with constant pointer `0x0044C4FC`; that constant/helper path still needs exact decoding before assigning its semantic meaning.
- The constructor creates the method node, and `TXMLMethodType.Insert` appends parameter child nodes. Each child has `name=` dictionary key and text equal to dictionary value (confirmed in the previous section).

Thus the statically confirmed shape is a `method` XML element with a `class` attribute containing the dispatched method name and child parameter elements carrying `name` plus text values. Calling the root XML node's `GetXML` produces the output string. Do not yet claim the full document envelope, encoding, XML declaration, or any extra method attributes: the constructor's second constant at `0x0044C4FC` remains under investigation, and no runtime capture has been compared.

The older preliminary paragraphs above that say the `+0x54` getter, `class` literal, or parameter key attribute are unresolved are superseded by this section.

## Constructor helper correction (focused run 17)

Focused run 17 (`43574768657`, artifact `14106455607`) adds two useful constraints to the `TXMLMethodType.AfterConstruction` analysis:

- The helper at `0x0044B4D8` is an IAT thunk to `xmlrtl230.bpl!TXMLNode.GetChildNodes`. Its direct caller includes `TXMLMethodType.AfterConstruction` at `0x0044C47C`, where the returned child-node collection is used before adding the `method` element.
- The argument passed in `ECX` as `0x0044C4FC` is not a Delphi string: decoding it as UTF-16LE produces invalid data and its preceding DWORDs do not form a plausible string header. Do not assign it a textual XML meaning.
- `0x00401430` is another thunk through IAT slot `0x0062EC40`; the prior target trace only resolved the slot to an address outside the BPL image. Its actual imported symbol is pending a dedicated import-table lookup. It is called with `EAX=ESI`, `EDX=[EBP-4]`, and `ECX=0x0044C4FC`.

The constructor's remaining side effect is therefore unresolved. Run 18 adds an exact import-slot lookup and byte-context dump before any semantic conclusion is made.
 

## Constructor import-slot correction (focused run 19)

Focused run 19 (`43575191082`, artifact `14106206890`) performed the exact import-descriptor lookup for `0x0062EC40`. The address is in the `.idata` section, but **no parsed import descriptor entry has this exact IAT address**; the on-disk DWORD is `0x00231274`, which may be unresolved or relocated. Thus the previous description “IAT thunk” is only an observed indirect jump through that slot, not proof that the slot is a normal imported symbol. Its semantic identity remains unknown. The constant at `0x0044C4FC` contains bytes matching the `TXMLMethodType` IID layout, but this alone does not prove the called helper's contract. Do not label it QueryInterface or infer an XML field.

Run 20 adds a direct probe of `TXMLParamType.AfterConstruction` at the class VMT `+0x0C` slot (`0x0044B4F8`) to identify the actual parameter element tag from its constructor behavior.
 

## Parameter-constructor probe correction (focused run 20)

Focused run 20 (`43576636790`, artifact `14106479073`) disproved the shortcut of treating the `TXMLParamType` VMT `+0x0C` entry (`0x0044B4F8`) as its `AfterConstruction` body. That address is an import-style jump thunk through slot `0x006302B4`, whose on-disk target is `0x0024060C` outside the BPL image; no TD32 procedure range contains `0x0044B4F8`. The other nearby addresses are part of a thunk table, not constructor code. The run therefore does **not** identify the parameter element tag. The next workflow revision indexes TD32 decorated procedure names for `TXMLParamType` and `TXMLMethodType` and will trace the actual class procedure by its symbol address.

## TD32 constructor comparison — focused run 22

Focused run 22 (`43578292246`, artifact `14106852706`) completed successfully and extends the constructor investigation:

- The TD32 class index identifies `TXMLParamType.AfterConstruction` only in the separate `WordRequestXML` module at `0x00614EC8`; the `XmlResponse` module used by the generic Invoke path has no own TD32 `TXMLParamType.AfterConstruction` symbol in the indexed results. Do not transfer the WordRequestXML constructor semantics to XmlResponse without class-layout/dispatch evidence.
- The WordRequestXML constructor calls the same helper `0x0044B4D8`, which resolves to `xmlrtl230.bpl!TXMLNode.GetChildNodes`, and then calls `0x00401430` with a constant at `0x00614F2C`. The bytes at that constant are binary GUID-like data, not a readable Delphi string. Its semantic role and the unresolved helper contract remain unknown.
- The `XmlResponse.TXMLParamType` VMT parent pointer is `0x00630314`, outside the BPL image; the `TXMLMethodType` parent pointer is `0x0063030C`. Their common-looking imported/external placement is not sufficient to name the parent class or identify a constructor/tag.
- The helper `0x00401430` remains an indirect jump through `0x0062EC40`; exact import-descriptor matching finds no entry at that slot, and its on-disk value `0x00231274` is outside the image. The call must remain semantically unresolved.

**Conclusion:** run 22 does not identify the parameter element tag or the full XML envelope. It confirms that a separate WordRequestXML parameter constructor exists, but that code is not yet proven to be the constructor used by the XmlResponse interface returned by generic `Invoke`. The confirmed generic Invoke facts remain: method element, `class` attribute containing the method name, parameter key in `name`, parameter value as text, and serialization through `TXMLNode.GetXML`. Next, resolve the external parent VMT/class references and the XmlResponse parameter-object construction/dispatch path rather than guessing the tag from the sibling module.

## XmlResponse parameter-node construction — focused run 23

Focused run 23 (`43579138098`, artifact `14107224578`, success) adds the following evidence:

- `TXMLMethodType.AfterConstruction` (`0x0044C458`) obtains the node's child-node collection through `xmlrtl230.bpl!TXMLNode.GetChildNodes`, then invokes the collection's virtual slot `+0x10` with the literal `method`. The returned node is converted to the `TXMLMethodType` interface using the GUID-like constant at `0x0044C4FC`. This supports the already confirmed method-element name `method`.
- `TXMLMethodType.Insert` (`0x0044C754`) obtains the child-node collection, calls its virtual slot `+0x20` with index `-1`, then converts the returned node to the `TXMLParamType` interface using constant `0x0044C7AC`. No explicit child-element name is passed by this method. Therefore this trace does **not** identify the parameter element tag.
- `TXMLParamType.Set_Name` (`0x0044C830`) accesses the wrapped node/attribute interface and uses the name-related XML attribute path; this is consistent with the separately confirmed `name` attribute mapping. `Get_Name` uses the same wrapped-node interface path. Neither method reveals the parameter element tag.
- The `XmlResponse.TXMLParamType` parent VMT pointer at `0x00630314` and `TXMLMethodType` parent pointer at `0x0063030C` point to external package/runtime metadata outside the BPL image. Their class identities remain unknown.
- The helper at `0x00401430` is an indirect jump through `0x0062EC40`; it is used at several interface-cast-like call sites with GUID-like constants, but the slot does not match a parsed import descriptor. Do not label it as a specific Delphi RTL routine until its external target is resolved.

**Current boundary:** the method node name `method`, its `class` attribute, parameter `name` attribute, parameter text value, and `GetXML` serialization are supported. The parameter child element name, complete XML envelope, declaration/encoding, and exact HTTP wire bytes remain unknown. Next, inspect the XML node-list virtual method contract and class metadata/imports, then prioritize the page-side close-time POST/response path rather than repeating generic XML getter work.

## XML node-list Add/Get_Param comparison — run 24

Run 24 (`43579618380`, artifact `14106929511`) traces both XmlResponse and `.EmwatMethods` class variants:

- `TXMLMethodType.Add` in both modules gets the wrapped node's child-node collection, then calls collection virtual slot `+0x10` with the provided string and an output interface. This is the explicit named-child creation path used for the `method` element.
- `TXMLMethodType.Insert` calls collection virtual slot `+0x20` with index `-1`, without an element-name argument. The XML parameter tag is not selected in this wrapper.
- Both `Get_Param` implementations use the same setter pattern; XmlResponse's literal attribute name is `class`, and the supplied method name is the value.
- No direct immediate CALL xrefs were found for the traced Add/Get_Param methods, consistent with invocation through interfaces/VMTs.

The collection's virtual method implementation and external class metadata remain the useful next static-analysis targets. The parameter tag is still unknown; do not infer it from `TXMLParamType` or from sibling modules.
 
## Correction — run 25 address/symbol verification (2026-11-14)

Run 25 (`43580008821`, artifact `14108665890`) identified the TD32 symbol `WordAppDocumentBeforeSave` at `0x004CD154` and the callback field assignment `+0x80`, but did not decode the TWordApplication RTTI event-property offsets. Run 27 later maps `+0x80` to `OnDocumentBeforeClose`; the earlier conclusion that the callback was not a close callback is superseded.

The actual TD32 procedure named `TWordViwer.WordAppDocumentBeforeClose` begins at `0x004CCBBC`, but its only direct immediate caller found is `FillImgFldsForPrint` at `0x004CCF8F`; no registration reference was found in the scanned raw pointer data. Therefore its name alone does not prove that this procedure is the live Word application close-event handler.

A second address error: `0x00430070` is `TWordDocument.SaveAs2000`, not a Close wrapper. The actual `TWordDocument.Close` overload procedures are TD32-labeled at `0x0042FEB0`, `0x0042FF08`, `0x0042FF7C`, and `0x0042FFF4`; the latter is the three-argument overload. A three-argument Close invocation in the callback body dispatches through document interface VMT slot `+0x29C`, but the exact runtime target for that interface dispatch must be established by matching the interface VMT and wrapper semantics, not by assigning `0x00430070`.

Run 25 itself completed successfully, but its added trace commands targeted the wrong symbols for a close-event investigation. Treat its other outputs as useful only where the TD32 labels and address semantics are independently verified. Next analysis must trace the actual Close overload(s), find the genuine callback registration (if present), and distinguish the BeforeSave callback from document-close lifecycle. No claim about the page-side POST is changed by this correction.


## Run 26 — Word Close overload dispatch (2026-11-14)

Run 26 (43584217243, artifact 14109926135) completed successfully. TD32 symbols and wrapper bodies establish four TWordDocument.Close overloads:

| Overload | Procedure VA | Interface dispatch |
|---|---:|---:|
| No arguments | 0x0042FEB0 | VMT slot +0x4D4 |
| One OleVariant | 0x0042FF08 | VMT slot +0x29C |
| Two OleVariants | 0x0042FF7C | VMT slot +0x29C |
| Three OleVariants | 0x0042FFF4 | VMT slot +0x29C |

The three-argument wrapper forwards its three OleVariant arguments through document interface slot +0x29C. The concrete runtime target and effective argument meanings are not identified by this wrapper alone.

Run-27 callback identity correction: 0x004CD154 is installed at TWordApplication.OnDocumentBeforeClose field +0x80 despite the TD32 symbol WordAppDocumentBeforeSave. It reads _Document.Saved through slot +0xD8 (the TD32 wrapper label Set_Saved is reversed; its wrapper returns WordBool), calls PreparePrintDocument at 0x004CB108, conditionally prompts, sets event Cancel to 0xFFFF on Cancel, and invokes interface slot +0x29C with three OleVariant arguments on Yes/No. The separate TD32-named WordAppDocumentBeforeClose at 0x004CCBBC is not the installed callback; its bounded direct caller is FillImgFldsForPrint at 0x004CCF8F.

The no-argument overload's +0x4D4 slot must not be conflated with the optional-argument overloads' +0x29C slot. 0x00430070 is SaveAs2000, not Close. Remaining work: resolve the COM interface implementation behind +0x29C, find any actual close-event registration, and trace the page-side close-time POST. No apply-on-close explanation is established.


## Close overload cross-check — lifecycle run 26

Run 26 (`43584217243`, artifact `14109926135`) independently traced the generated `Wordxp.TWordDocument.Close` wrappers:

| Wrapper | TD32 address | Interface dispatch |
|---|---:|---:|
| `Close()` | `0x0042FEB0` | `+0x4D4` |
| `Close(OleVariant)` | `0x0042FF08` | `+0x29C` |
| `Close(OleVariant, OleVariant)` | `0x0042FF7C` | `+0x29C` |
| `Close(OleVariant, OleVariant, OleVariant)` | `0x0042FFF4` | `+0x29C` |

The wrappers obtain the underlying interface through `0x0042ABA0` and invoke the corresponding vtable slot. The three-argument overload is called from the registered `OnDocumentBeforeClose` callback at `0x004CD154` (TD32 label `WordAppDocumentBeforeSave`) in the Yes/No prompt branches. The no-argument overload uses a different slot. Until the `_Document` type-library declarations or a matching wrapper map both slots, do not assign method names to raw offsets beyond the TD32 wrapper names.

The separate `WordAppDocumentBeforeClose` symbol at `0x004CCBBC` is not the registered callback; its known direct caller is `FillImgFldsForPrint`. The user's observed close-time HTTP POST is not yet tied to the COM callback's parent-page message.


### Invoke wrapper/helper naming clarification — 2026-11-15

The BPL export/API trace resolves the apparent symbol conflict:

- Public virtual/exported TEmwatMethod.Invoke is 0x0046C9E0, shared by descendants at VMT slot +0x0C.
- The wrapper calls 0x0046C82C at 0x0046CA67; this 433-byte inner routine builds/serializes the dictionary-backed XML method/parameter structure.
- The wrapper then calls the subclass VMT slot +0x10 at 0x0046CA88.
- TD32 labels are shifted/misleading at this boundary: 0x0046C82C carries the Invoke symbol, while 0x0046C9E0 carries the Finalization symbol. Export metadata, VMT mapping, and executable call flow establish the public wrapper/helper relationship above.
- The +0x68 indirect call at 0x0046C921 belongs to the inner helper. A second +0x68 call at 0x0046CBB7 belongs to the wrapper and has a different receiver; do not conflate them.


## Generated Word event callback table — extraction corrected (2026-11-15)

Word event-sink workflow run #8 (`43716384031`), artifact `14162362638`, fixes a bug in the earlier callback-target extraction step. The table at `0x00627B74` contains 20 callback code pointers, beginning at `0x004499B8` and ending at `0x00449D98`. The corrected parser now extracts all 20 targets rather than returning an empty index.

The first attempt to trace those targets with TD32 procedure boundaries reports no TD32 procedure range for any of them. This is a limitation of the symbol-based procedure tracer, not evidence that the callback targets are invalid. They are pointers read from the generated Word event metadata table. A follow-up run (#9) disassembles the contiguous code range directly and expands both the event-map and server-data tables.

The event sink remains distinct from the TWordViwer callback record assignments. The latter prove that the main viewer registers its BeforeSave handler at `0x004CD154`; the 20 generated event-table targets still need to be mapped to event DISPIDs/names before they can be associated with specific Word events.


## Correction — 2026-11-15: 0x00627B74 is TServerData with trailing error strings, not an event callback table

The run #8 extraction correctly found 20 pointers, but the initial interpretation of those pointers as Word event callbacks was wrong. Run #9 (`43716905570`, artifact `14162568118`) decoded the targets as Delphi string literals, not executable callback routines. The raw disassembly attempt at `0x004499B8–0x00449E20` yielded data-like bytes and is not valid evidence of callback code.

The decoded strings include:

- `Err_0`, `Err_20000`, `Err_20001` … `Err_20008`, `Err_Ignore`;
- `Exception: `;
- `Request XML is invalid.`;
- `Request Doc is Empty.`;
- `Error on connect to MS-Word. Exception: `;
- `Can not open document.`;
- `Error on insert sign to word document. Exception: `;
- `Field "%s" of Twin fields not found in Doc.`;
- `Temp path not Found.`;
- `Scan failed on %s. The error code(s)= %s\\r%s`.

Therefore the pointer region beginning at `0x00627BB0` is the trailing error-message/string mapping portion of the TWordApplication server-data record. The record itself begins at `0x00627B74` with Word.Application CLSID `000209FF-0000-0000-C000-000000000046`, default interface IID `00020970-0000-0000-C000-000000000046`, and event-source IID `00020A00-0000-0000-C000-000000000046` (ApplicationEvents3). The 20 pointers are error strings, not callback functions; the record's leading GUIDs still provide the event-source identity. The earlier subsection titled “Generated Word event callback table — extraction corrected” is superseded by this correction.

The live main-viewer event registration evidence is unchanged: `OnTmrAutoSave` assigns `TWordViwer.WordAppDocumentBeforeSave` (`0x004CD154`) to callback field `+0x80`, plus other event handlers at `+0x90`, `+0x98`, and conditional `+0x88`. The 20 string pointers provide error handling text for the Word/EMWAT subsystem, not a map of those event registrations.

Workflow run #10 (`analyze-word-event-sink.yml`) now labels this analysis as a server error-map string extraction and no longer attempts to trace the string pointers as procedures. A separate event-dispatch investigation is still required to map actual COM event DISPIDs to the registered callback records.


The full expanded scan in run #11 (`43717625474`, artifact `14162998865`) adds `Err_Ignore` → `The operation was canceled by user.`, `Err_20010` → image-load failure, `Err_20016`/`Err_20017` → Excel connection/workbook-open errors, and `Err_20018` → missing user-local folder. It also finds log-level labels (`None`, `Info`, `Debug`) and Persian AutoSave interval labels. The normalized list is in `docs/WORD-ERROR-MAP.md`.


## Generated Word server-data follow-up — 2026-11-15

Word event-sink workflow run #3 (`43722341799`, artifact `14164794063`) adds the generated wrapper-class traces and server-data inspection:

- `TWordApplication.InitServerData` (`0x0043E070`) passes the data record at `0x00627A38` to helper `0x0040479C`.
- `TWordDocument.InitServerData` (`0x0042AA20`) does the same with a separate data record at `0x00627768`.
- The broad Delphi interface-table scan reports `TWordApplication` VMT `0x004202A8` with a null interface-table pointer. This does not rule out its generated OLE event connection-point machinery; it means the event source is not represented as a direct Delphi VMT interface-table entry in this scan.
- The `0x00627B74` block is the TWordApplication server-data record: its leading GUIDs identify Word.Application, `_Application`, and ApplicationEvents3; its trailing 20 pointers are the error-string map. It is not an event callback table.

A targeted follow-up run (`43722702804`) traces helper `0x0040479C` and the separate `TWordDocument` server-data record at `0x00627768`. The TWordApplication event source is now identified from the third GUID in its server-data record at `0x00627B74`; RTTI maps the callback field to OnDocumentBeforeClose, and Word interop metadata corroborates DISPID `0x00000006`.


## `WordAppDocumentBeforeClose` helper cross-reference — 2026-11-15

Methods BPL analysis run `43722341778` (artifact `14165431103`) adds a direct cross-reference for the `0x004CCBBC` routine:

- `TWordViwer.WordAppDocumentBeforeClose` calls `0x004BCA88` at `0x004CCCC9` and returns the helper result.
- The same helper `0x004BCA88` is also called twice by `TWordViwer.GetCaptionItemFont` (`0x004C1A82` and `0x004C2329`). It is therefore a shared caption/font helper, not a close-specific network or save routine.
- The direct caller scan for `0x004CCBBC` still shows only `FillImgFldsForPrint` at `0x004CCF8F`. The method body contains no proven bridge POST, final response write, or document-close call.

This strengthens the caution around the TD32 method name: `WordAppDocumentBeforeClose` is a real named method and is used by print/image preparation, but the static evidence still does not prove that it is registered as the live main-editor close event. It must not be used to explain the observed Almas registration on close without the missing event-registration/response path.


## Word OLE server-data GUID correlation — 2026-11-15

The expanded metadata at `0x00627A38` and `0x00627768` contains GUID-shaped records. The leading values correlate with Microsoft Word's generated COM classes:

- `0x00627A38` begins with `000209FF-0000-0000-C000-000000000046`, the GUID on Microsoft Learn's `ApplicationClass`.
- `0x00627768` begins with `00020906-0000-0000-C000-000000000046`, the GUID on Microsoft Learn's `DocumentClass`.
- The adjacent GUID inventory includes `000209F7` (`ApplicationEvents`) and `000209FE` (`ApplicationEvents2`). Microsoft Learn identifies `000209FE` as the `ApplicationEvents2` IID and lists `DocumentBeforeClose`, `DocumentBeforePrint`, and `DocumentBeforeSave` among its methods.
- The Word `DocumentEvents` IID `000209F6` is also present immediately before the `0x00627768` block in the captured data region.

This supports interpreting these blocks as generated Word OLE server/type-library metadata, not as a raw callback-pointer table. The `WordAppDocumentBeforeClose` method signature/name is consistent with an ApplicationEvents2 `DocumentBeforeClose` handler, but the code path that advises/registers that event sink is still not recovered. Do not equate GUID presence with a confirmed live event subscription.

References:
- ApplicationClass: https://learn.microsoft.com/en-us/dotnet/api/microsoft.office.interop.word.applicationclass?view=word-pia
- DocumentClass: https://learn.microsoft.com/en-us/dotnet/api/microsoft.office.interop.word.documentclass?view=word-pia
- ApplicationEvents2 IID and method list: https://learn.microsoft.com/en-us/dotnet/api/microsoft.office.interop.word.applicationevents2?view=word-pia
- DocumentEvents IID: https://learn.microsoft.com/en-us/dotnet/api/microsoft.office.interop.word.documentevents?view=word-pia


## Server-data helper resolution — 2026-11-15

Word event-sink follow-up run `43723423283` (artifact `14165491351`) resolved the important helper thunks:

- `0x0040479C` is an IAT thunk to `rtl230.bpl!System.Win.ComObj.CreateRemoteComObject(WideString, GUID)`. `TWordApplication.InitServerData` and `TWordDocument.InitServerData` therefore feed their static server-data records into Delphi's OLE/COM wrapper initialization path.
- `0x00401358` resolves to `WStrFromUStr`; `0x00401210` to `WStrClr`; and `0x00401248` to `UStrLAsg`. These are RTL string-management helpers, not EMWAT event callbacks.
- The `0x00627A38` and `0x00627768` blocks contain Word class/interface GUID metadata. Their presence helps identify generated COM wrappers but does not provide the event-handler method pointer or prove which `IConnectionPoint::Advise` call subscribes the main editor.
- `0x00401420` and `0x00401430` remain external/import thunks not resolved to a file-backed implementation in this package; do not assign them a semantic name from these traces alone.

The TWordApplication connection path is now cross-identified: its server-data record at `0x00627B74` names ApplicationEvents3, and RTTI maps event field `+0x80` to OnDocumentBeforeClose callback `0x004CD154`. Word interop metadata corroborates DISPID `0x00000006`. Remaining COM work is direct extraction of the embedded typelib member record and a complete mapping of the other callback fields; the main close-event identity is no longer open.



## Close-wrapper and controller-notify cross-check — 2026-11-16

Source: close/response-chain workflow run 43813684507, artifact 14200889822.

### Word document Close wrappers

TD32 resolves two distinct generated Word wrapper methods:

- 0x0042FEB0 — TWordDocument.Close() with no arguments. It dispatches through the current Word _Document interface at byte offset +0x4D4.
- 0x0042FFF4 — TWordDocument.Close(OleVariant, OleVariant, OleVariant). It dispatches through the same _Document interface at byte offset +0x29C.

The Word BeforeSave callback at 0x004CD154 uses the three-argument Close wrapper after its Cancel/prompt logic. Do not collapse this into SaveAs or a direct HTTP call: the callback controls the Word document close decision, while the HTTP response writer is a separate path still to be connected.

### Controller notification and recipient/CC customization

The TD32 procedure at 0x004BB3B0 is TWordViwer.OnControlerNotify(TCtrlMsgs). It has no direct bounded CALL xrefs in the current scan, consistent with indirect message/event dispatch but not proof of a particular invocation.

Within its body it:
1. checks viewer state and controller-related data;
2. temporarily changes viewer state byte +0x5E;
3. calls 0x004D281C, named TWordViwer.CostumizeRecAndCC;
4. calls the current Word _Document interface at byte offset +0xDC with -1;
5. restores viewer state and continues controller-message handling.

CostumizeRecAndCC at 0x004D281C calls the Word _Document interface at byte offset +0x2BC on its guarded paths. The generated Wordxp wrapper maps this slot to PrintOutOld(). This is a Word automation/controller path, not evidence of a local HTTP POST or of the final Almas registration trigger.

The meaning of the +0xDC interface slot and the exact controller message that reaches OnControlerNotify remain open. A follow-up trace now includes the generated Get_Saved and Set_Saved wrappers at 0x0042BD34 and 0x0042BD94 to resolve the slot mapping directly.

### Evidence boundary

- Confirmed: the two Close wrapper dispatch slots; BeforeSave calls the three-argument Close wrapper; OnControlerNotify calls CostumizeRecAndCC and a document-interface slot +0xDC; CostumizeRecAndCC uses slot +0x2BC.
- Not confirmed: the business meaning of the +0xDC call; the exact message/event that invokes OnControlerNotify; any direct causal link from these methods to the close-time HTTP response or Almas registration.


### Saved property slot mapping correction

The follow-up wrapper traces (run 43814055308, artifact 14200974814) resolve the adjacent Word document property slots:

- TWordDocument.Get_Saved at 0x0042BD34 dispatches through _Document byte offset +0xD4.
- TWordDocument.Set_Saved at 0x0042BD94 dispatches through _Document byte offset +0xD8.

Therefore, the direct call at 0x004CD1F5 inside the callback at 0x004CD154 uses slot +0xD8, whose TD32 wrapper label is Set_Saved. Wrapper call-shape analysis resolves this slot as the actual get_Saved getter: it returns a WordBool through an output pointer. The callback reads Document.Saved; the earlier withdrawal of that interpretation is superseded. The wrapper name, not the callsite, was misleading.

The OnControlerNotify call at 0x004BB514 uses slot +0xDC. The follow-up trace resolves TWordDocument.Get_Content at 0x0042BDF8 to the same slot +0xDC. Thus the controller path is calling the Word document Content member, not a Saved getter/setter. OnControlerNotify supplies -1 in the argument position; the precise meaning of that value in this call context remains unresolved.


### Content slot mapping resolved

The Get_Content wrapper at 0x0042BDF8 dispatches through _Document byte offset +0xDC. This matches the call in OnControlerNotify at 0x004BB514. The three adjacent property slots are now mapped:

| Wrapper | Address | _Document slot |
|---|---:|---:|
| Get_Saved | 0x0042BD34 | +0xD4 |
| Set_Saved | 0x0042BD94 | +0xD8 |
| Get_Content | 0x0042BDF8 | +0xDC |

The OnControlerNotify call passes -1 before invoking +0xDC. The generated wrapper's hidden result/argument handling means the business meaning of this -1 still needs to be traced; do not infer that it is a SaveChanges flag or a registration signal.

Evidence: close/response-chain run 43814460258, artifact 14201473774.


## Word Application event-sink registration — 2026-11-16

Source: event-sink workflow run 43815900228, artifact 14202173024.

### Application connection setup

TD32 traces show:

- TWordApplication.InitServerData at 0x0043E070 loads its COM server/type metadata from 0x00627A38 and stores the related event metadata pointer 0x00627B74.
- TWordApplication.ConnectTo at 0x0043E0FC obtains the default Application interface through its VMT slot +0x48, then calls 0x00404FAC to connect the event interface and stores the connected interface at object offset +0x124.
- TWordApplication.InvokeEvent at 0x0043E270 and TWordDocument.InvokeEvent at 0x0042ABF8 route event dispatch through shared helper 0x00404F8C and the generic dispatch helper 0x00401188.

### Callback record assignments

The bounded callback-registration code at 0x004B8C60–0x004B8D10 writes callback/data pairs into the event-record object referenced by viewer offset +0x44:

| Event callback pointer | Context pointer | TD32 method |
|---:|---:|---|
| 0x004CD154 at record +0x80 | viewer at +0x84 | RTTI: OnDocumentBeforeClose; TD32: TWordViwer.WordAppDocumentBeforeSave |
| 0x004CD54C at record +0x90 | viewer at +0x94 | TWordViwer.WordAppNewDocument |
| 0x004CD9C0 at record +0x98 | viewer at +0x9C | TWordViwer.WordAppWindowActivate |
| 0x004D00AC at record +0x88, conditional on viewer byte +0x3C | viewer at +0x8C | callback target not yet resolved |

This confirms that the callback pointer is explicitly installed as the application OnDocumentBeforeClose event property, according to TWordApplication RTTI. The TD32 procedure name is misleading.

### Separate TD32-named routine at `0x004CCBBC`

WordAppDocumentBeforeClose at 0x004CCBBC has one direct bounded caller in the current artifact: FillImgFldsForPrint at 0x004CCF8F. It is not one of the callback pointers listed in the event-record assignments above. This supports keeping the registered OnDocumentBeforeClose callback at `0x004CD154` separate from the distinct TD32-named helper at `0x004CCBBC`.

### Evidence boundary

The event-sink wiring explains how the OnDocumentBeforeClose callback is reached from Word automation. It does not prove that the callback itself posts the final document to Almas. The exact response-word HTTP handoff and registration trigger remain separate unresolved protocol steps.


## Run 130 — ردیابی رکوردهای event sink و جایگاه BeforeClose

Source: artifact اجرای Word event sink، run `43815900228`، artifact `14202173024`.

### ثبت callbackها در مسیر OnTmrAutoSave

در بدنه‌ی `TWordViwer.OnTmrAutoSave` (procedure از `0x004B8A84`)، بلوک `0x004B8C60–0x004B8D10` روی شیء event/controller در `viewer+0x44` رکوردهای callback را مقداردهی می‌کند:

- offset `+0x80` ← `OnDocumentBeforeClose` در RTTI، callback `0x004CD154` (TD32 label: `WordAppDocumentBeforeSave`).
- offset `+0x90` ← `OnDocumentBeforeSave` در RTTI، callback `0x004CD54C` (TD32 label: `WordAppNewDocument`).
- offset `+0x98` ← `OnNewDocument` در RTTI، callback `0x004CD9C0` (TD32 label: `WordAppWindowActivate`).
- offset `+0x88` ← callback در `0x004D00AC`، با شرط flag در `viewer+0x3C`.

این شواهد ثبت callback در event record را ثابت می‌کند؛ اما نام/معنای callback چهارم و اینکه این رکورد دقیقاً در کدام مرحله به connection point ورد متصل می‌شود، هنوز باید با trace چرخه‌ی WordApplication تکمیل شود.

### وضعیت BeforeClose

- pointer scan آدرس `0x004CCBBC` هیچ reference مستقیمی در داده/کد پیدا نکرد.
- bounded direct-call scan تنها caller مستقیم آن را `FillImgFldsForPrint` در `0x004CCF8F` نشان می‌دهد.
- در بلوک event-record assignment بالا، هیچ فیلدی به `0x004CCBBC` تنظیم نشده است.

بنابراین routine جداگانه‌ی `WordAppDocumentBeforeClose` در `0x004CCBBC` callback ثبت‌شده‌ی main editor نیست. اما run 27 با RTTI ثابت می‌کند که callback `0x004CD154` در فیلد `+0x80` به event property واقعی `OnDocumentBeforeClose` متصل است؛ TD32 label آن misleading است.

### ارتباط با BeforeSave

بدنه‌ی callback ثبت‌شده به‌عنوان `OnDocumentBeforeClose` در `0x004CD154` از `_Document` slot `+0xD8` استفاده می‌کند؛ wrapper crosswalk آن را `TWordDocument.Set_Saved` می‌نامد، اما callsite یک local صفرشده را با reference به آن می‌دهد و سپس همان local را می‌خواند، بنابراین getter/setter semantics در این callsite هنوز نیازمند type-library cross-check است. سپس در شاخه‌ی ادامه‌ی close، wrapper سه‌آرگومانی `TWordDocument.Close` را از slot `+0x29C` فراخوانی می‌کند. این مسیر با getter محتوای `+0xDC` در `OnControlerNotify` متفاوت است.

**Confidence:** ثبت سه callback اول در event record تأییدشده؛ اتصال نهایی به COM connection point و نقش callback چهارم هنوز باز؛ فعال بودن BeforeClose در main editor اثبات‌نشده.


## Run 132 — هویت callback چهارم event record مشخص شد

Artifact اجرای callback trace (run `43816996023`, artifact `14203047153`) نام TD32 هدف `0x004D00AC` را به‌صورت `TWordViwer.LoadOptions` resolve می‌کند. رشته‌ی log در ابتدای بدنه نیز صریحاً `Document.OnBeforePrint called.` است.

بنابراین نگاشت event record در `OnTmrAutoSave` اکنون چنین است:

| offset در رکورد | callback | نتیجه |
|---|---|---|
| `+0x80` | `OnDocumentBeforeClose` (`0x004CD154`; TD32 `WordAppDocumentBeforeSave`) | ثبت شده |
| `+0x88` | `LoadOptions` / `Document.OnBeforePrint` (`0x004D00AC`) | ثبت شرطی با flag در `viewer+0x3C` |
| `+0x90` | `OnDocumentBeforeSave` (`0x004CD54C`; TD32 `WordAppNewDocument`) | ثبت شده |
| `+0x98` | `OnNewDocument` (`0x004CD9C0`; TD32 `WordAppWindowActivate`) | ثبت شده |

`LoadOptions` در این بدنه تنظیمات چاپ را بارگذاری/نمایش می‌دهد و رشته‌های `Word Print Dialog`، `SOFTWARE\\Emwat\\Dynamic Config` و پیام دسترسی چاپ را مصرف می‌کند؛ این callback به close/registration مربوط نیست.

این تطبیق ابهام callback چهارم را برطرف می‌کند، اما نتیجه‌ی قبلی درباره‌ی `WordAppDocumentBeforeClose` تغییر نمی‌کند: در این event record هیچ assignment برای `0x004CCBBC` وجود ندارد و فعال بودن آن در main editor هنوز اثبات نشده است.


## Run 134 — main Word close/save lifecycle resolved

Artifact: Word lifecycle run `43817445960`, artifact `14203757393`.

### Active callback is OnDocumentBeforeClose; TD32 label is misleading

- The event record from `OnTmrAutoSave` stores `0x004CD154` at field `+0x80`; TWordApplication RTTI names this property `OnDocumentBeforeClose`.
- The main editor's `WordAppDocumentBeforeClose` at `0x004CCBBC` still has no proven event-record assignment and only the separate print-handler caller. It is not the demonstrated main close path.

### Exact user-choice → COM Close flow

In the callback at `0x004CD154` (TD32 symbol `TWordViwer.WordAppDocumentBeforeSave`, RTTI event property `OnDocumentBeforeClose`):

1. It verifies that the event's document matches `viewer+0x48` and that the viewer state permits handling.
2. It passes a zero-initialized local by reference through COM slot `+0xD8`; the call returns the actual `get_Saved` WordBool, despite the TD32 wrapper label `Set_Saved`. The callback reads `Document.Saved` and uses it to decide whether to prompt; it does not write `Saved=False`.
3. It displays the registration prompt. The dialog result is then mapped as follows:
   - Yes (`MessageDlg` result 6): the first `OleVariant` passed to Close is set to `-1` (True / SaveChanges).
   - No: the first `OleVariant` remains `0` (False / do not save changes).
   - Cancel (`MessageDlg` result 2): it sets the Word event's `Cancel` field to `0xFFFF` and exits without closing the document.
4. For Yes/No, it invokes the three-argument `TWordDocument.Close` overload through COM slot `+0x29C`; the other two `OleVariant` arguments are initialized but left empty. It then clears the active document pointer and updates viewer close state.

### Overload verification

TD32 procedure traces show the one-, two-, and three-argument `TWordDocument.Close` wrappers at `0x0042FF08`, `0x0042FF7C`, and `0x0042FFF4`. All resolve through `0x0042ABA0` to the underlying Word document interface and dispatch slot `+0x29C`. The main OnDocumentBeforeClose callback uses the three-argument form, matching Word's `_Document.Close(SaveChanges, OriginalFormat, RouteDocument)` signature.

### What this proves — and what it does not

This explains why closing Word can register/return a document even when the user did not press the Word Save button: the registered OnDocumentBeforeClose handler asks whether to register changes and then explicitly closes the Word document with SaveChanges True/False. Cancel sets the event Cancel value and leaves Word open.

It still does **not** identify the exact HTTP POST/response envelope used to return the resulting document to Almas. The controller-notify/Get_Content and paired `.easd/.easz` paths remain under analysis; do not conflate COM Close with the final local HTTP response.


## Run 136 — exact BeforeSave prompt and three-way close decision

Artifact: event-sink run `43824067943`, artifact `14206405476`.

The native Persian dialog strings were decoded from the active `WordAppDocumentBeforeSave` callback:

- Title: `ام وات`
- Message: `محتويات اين سند تغيير كرده است. آيا مايل به ثبت تغييرات مي‌باشيد؟`
- Buttons: `موافقم`, `خیر`, `انصراف`

The already-traced callback maps the choices to Word COM as follows:

| User choice | Native behavior |
|---|---|
| موافقم | `_Document.Close(SaveChanges=True)` |
| خیر | `_Document.Close(SaveChanges=False)` |
| انصراف | Set event `Cancel=0xFFFF`; keep the document open |

This is the exact native user-facing choice contract. It does not yet establish the HTTP envelope returned for the No/discard path. The Python lifecycle now has a distinct `DISCARDED` terminal state so it cannot be confused with Cancel or successful registration; the LibreOffice UI prompt and wire response remain separate implementation tasks.


## Run 138 — controller close and HTTP response writer crosswalk

Source: workflow 43829491814 (both jobs succeeded), artifacts 14207688343 and 14207717380.

- The Word-controller range 0x004BB3B0–0x004BB777 confirms a call to TWordViwer.CostumizeRecAndCC at 0x004D281C, followed by a COM call through the document interface slot +0xDC and then helper 0x00456DFC. This is the main viewer controller-notify path and remains distinct from the print-handler controller path.
- The service crosswalk reconfirms TIdHTTPResponseInfo.WriteContent as a published method at 0x004610FC, alongside the HTTP request/response VMT methods. The response writer itself is traced in run 140.
- The crosswalk did not yet connect the controller notification to the exact final HTTP response serialization; do not treat this as proof of the Almas registration envelope.


## Run 141 — periodic Word controller timer callback

Source: workflow 43830743301, artifact 14208303183.

The complete TD32 procedure trace identifies the setup code as TWordViwer.OnTmrAutoSave (0x004B8A84). Within it:

- At 0x004B9999, the code passes the TWordViwer instance and callback address 0x004BB3B0 to helper 0x00404B94, using the timer object at instance offset +0x7C.
- IAT resolution maps 0x00404B94 to VCL TTimer.SetOnTimer.
- Helper 0x00404B8C maps to TTimer.SetInterval; the code enforces a minimum interval of 0x2710 ms (10,000 ms).
- Helper 0x00404B84 maps to TTimer.SetEnabled; the timer is enabled.

Therefore TWordViwer.OnControlerNotify is the periodic timer callback for this path. It is not the Word BeforeSave event. Its body reads the active Word document and calls 0x00456DFC; the exact semantics of that helper and its controller-message interfaces are not yet resolved. The periodic callback must not be mistaken for the final close-time response/registration path.


## MainForm CommandGet and concrete response-write callsites — 2026-11-16

Source: workflow 43831365563, artifact 14208144442.

- Delphi method RTTI resolves TMainForm.IdHTTPServerCommandGet to 0x0047BF30.
- The handler reads the request parameter named invoke (UTF-16 string at 0x0047C360) and routes the invoke path through helper 0x0047E0EC; package lifecycle/logging helpers include 0x0047E2D4 and 0x0047D2C8. The exact close-time response body for this invoke branch still needs to be traced.
- The same handler has separate init and heartbeat routes. The init branch reads parameter init, applies CORS response headers (Access-Control-Allow-Origin, Access-Control-Allow-Headers, Access-Control-Allow-Method), and returns the embedded initialization HTML/JavaScript at 0x0047C59C. The embedded script sends POST requests to 127.0.0.1:$V{myport}?invoke=<nonce> and forwards responseText to the parent window.
- The init branch assigns the response text to TIdHTTPResponseInfo.ContentText at object offset +0xBC and directly calls WriteContent at 0x004610FC from 0x0047C237. The heartbeat branch checks parameter heartbeat and also calls WriteContent at 0x0047C2A9.
- This direct callsite confirms the field layout: ContentText is +0xBC; ContentStream is +0xB8. Earlier draft notes that reversed these fields have been corrected.
- Evidence boundary: the generic HTTP response writer is now directly tied to the MainForm handler for init/heartbeat. The invoke branch's plugin result serialization and exact close-time Almas response envelope remain the next target.


## BPL class hierarchy and Invoke contract — 2026-11-16

Source: workflow 43832553168, artifact 14208369288.

- TD32 identifies TEmwatMethod.Invoke at 0x0046C82C with parameter type TDictionary<AnsiString,AnsiString>.
- The Delphi VMT/interface scan resolves TEmwatMethod VMT method-table base at 0x0046ABFC. TEditWordDocument VMT is 0x005ED764 and its parent pointer resolves to the TEmwatMethod VMT header start (0x0046ABA4 = 0x0046ABFC - 0x58). This establishes TEditWordDocument inherits TEmwatMethod.
- TScanDocument, TFaxDocument, TGetEmwatVersion, TSetEmwatVersion, TUpgradeEmwat, TImageEdition, TEditExcelWorkBook, and TCompareWordDocument also point to the same TEmwatMethod parent header.
- TEmwatMethod.Invoke iterates the dictionary's key/value enumerator and dispatches each entry through an instance virtual/interface slot. Direct TD32 caller scan finds only one direct call in unit finalization; the service's runtime invocation is therefore not yet a proven direct callsite and likely uses RTTI/dynamic dispatch. This must be resolved before claiming the complete request-to-class call chain.


## Run 144 — controller content post-processing reaches euUnArchive

Source: workflow `43867641761`, job `word-controller-close` succeeded, artifact `14226866454`.

The new full TD32 trace resolves helper `0x00456DFC` as:

- `Emwatutils.euUnArchive`
- VA range: `0x00456DFC–0x00456EFF`
- Procedure size: `0x104`
- The only direct TD32 caller found is `TWordViwer.OnControlerNotify` at callsite `0x004BB5E9`.

The callsite sits after the controller callback:
1. `OnControlerNotify` obtains the active Word document's content through the COM interface call at `0x004BB516` (document interface slot `+0xDC`).
2. It checks that the returned string is non-empty and longer than `0x14` characters before entering the transformation path.
3. It constructs two objects using helper `0x0040414C` and class/global reference `0x0062F810`; their exact class type is still to be resolved.
4. It passes the base path at `TWordViwer+0x80` through `0x004563A8`, which TD32 identifies as `FixDirectionInFarsiNumericMode`, using two different flag combinations. The resulting strings have suffixes appended by helper `0x00401368`: the decoded constants are `.easd` (`0x004BB754`) and `.easz` (`0x004BB76C`).
5. It passes the `.easd`-suffixed value to one of the constructed objects through its vtable slot `+0x3C`, then calls `euUnArchive` with the two constructed objects and the `.easz`-suffixed path.

Inside `euUnArchive`, helper `0x00452C10` constructs a `T7zPlugin`. The code passes the hardcoded string `mW@Tlogs43end_+` to plugin slot `+0x28`, iterates the two indexed objects in lockstep, passes each pair of strings to plugin slot `+0x10`, and finally passes the `.easz` path to plugin slot `+0x18`. This is strong evidence that the controller path uses the SevenZip plugin to process a custom archive/sidecar representation. The hardcoded string is a likely archive password, but the exact meaning of slots `+0x28`, `+0x10`, and `+0x18` remains to be resolved from the `T7zPlugin` VMT/TD32 methods before assigning names such as SetPassword/AddFile/Extract.

The helper name, the `T7zPlugin` constructor, the two extensions, and the paired-entry loop together are much stronger evidence than the name `euUnArchive` alone. The exact mapping between the `.easd` and `.easz` paths and the content returned by Word still needs confirmation.

The new artifact confirms that the periodic controller-notify path performs a SevenZip-backed transformation after `Get_Content`; it does **not** yet connect the transformed object to the invoke HTTP response or prove that every timer tick is a close-time registration. The next trace batch targets `0x0040414C`, `0x004543C4`, and the `T7zPlugin` VMT/methods to resolve the two object types and the archive operations.

Evidence boundary: static TD32 disassembly and direct-call scan; no runtime payload capture was added.


## Run 146 — SevenZip interface-slot cross-check (correction to password hypothesis)

Source: controller-unarchive workflow `43869120325`, artifact `14227121005`.

Exact VMT inspection confirms:
- `T7zPlugin` VMT: `0x00451E08`, instance size `0x18`, destructor at `0x00452C64`.
- `T7zOutArchive` VMT: `0x00452A40`, instance size `0x4C`, interface table at `0x00452984`, three interface entries.
- `T7zPlugin.$bctr` at `0x00452C10` uses the `T7zOutArchive` class reference at `0x004529E8`, calls `0x004543C4` (TD32 label `T7zOutArchive.CryptoGetTextPassword2`), adjusts the returned object pointer by `+0x44`, and stores that interface pointer for the caller.
- The interface at object offset `+0x44` has IID `baa9d5dc-9ff4-4382-9bfd-ec9065bd0125` and VTable `0x0045294C`.

The interface thunk table maps the slots used by `euUnArchive` as follows:
- interface slot `+0x10` → thunk `0x00452899` → `T7zOutArchive.AddFiles` at `0x00453F34`;
- interface slot `+0x18` → thunk `0x004528AD` → `T7zOutArchive.SaveToStream` at `0x00454668`;
- interface slot `+0x28` → thunk `0x004528D5` → `T7zOutArchive.SetProgressCallback` at `0x004547E8`.

**Correction:** the earlier hypothesis that the literal `mW@Tlogs43end_+` is directly passed to `SetPassword` is not supported by this interface mapping. The mapped slot is `SetProgressCallback`; the literal's role remains unknown. `T7zOutArchive.SetPassword` exists at `0x004547DC`, but it is not the target of the observed `+0x28` call through this interface.

There are still signature/argument-shape mismatches to resolve: `euUnArchive` passes two TStringList values through slot `+0x10`, and a `.easz` UnicodeString through slot `+0x18`, while TD32 labels the targets `AddFiles` and `SaveToStream`. The helper may be using a wrapper/interface layer with additional semantics, or the current interface-to-method association may need further verification. Do not rename `euUnArchive` as an archive writer or extractor yet. Trace the three target method bodies and the `T7zPlugin` factory path before assigning archive direction or password semantics.


### Run 147 — the two indexed inputs are TStringList instances

Artifact `14226742624` identifies `0x0040414C` as an import thunk to `rtl230.bpl!TStringList.$bctr`. Therefore the two objects created in `OnControlerNotify` are `TStringList` instances, not arbitrary indexed interfaces.

The observed sequence is:
- first list receives the string from `TWordViwer+0xA0`;
- second list receives the direction-normalized `TWordViwer+0x80` path with `.easd` appended;
- `euUnArchive` reads both lists by matching index and passes each pair to the returned `T7zOutArchive` interface;
- it then passes the `.easz` path to interface slot `+0x18`.

This strengthens the archive-packaging interpretation, but the interface target bodies and the parameter-type mismatch still prevent a final claim about whether the method writes, transforms, or extracts the archive.


## Run 148 — euUnArchive is a passworded archive-writer path

Source: controller-unarchive workflow run `43869599848`, artifact `14227611377`.

The target method bodies resolve the earlier signature mismatch:

1. The `T7zPlugin` factory returns an interface pointer to a `T7zOutArchive` object at offset `+0x44`.
2. `euUnArchive` calls interface slot `+0x28`, which reaches `0x004547E8`. Although TD32 decorates this procedure as `SetProgressCallback`, its body assigns the incoming UnicodeString to object field `+0x38`. The T7zOutArchive field table identifies `+0x38` as `FPassword`. Therefore the literal `mW@Tlogs43end_+` is the archive password value used by this path. The separately named `SetPassword` at `0x004547DC` is a no-op stub.
3. Interface slot `+0x10` reaches `T7zOutArchive.AddFiles` at `0x00453F34`. Its body checks the first string as a source file path, reads its file attributes, and stores the first and second strings into a batch item before adding that item to the archive batch list.
4. The caller supplies the first TStringList value (from `TWordViwer+0xA0`) as the source path and the second list value (base path + `.easd`) as the archive entry name.
5. Interface slot `+0x18` reaches `T7zOutArchive.SaveToStream` at `0x00454668`. Its body constructs a stream object using the supplied UnicodeString path and then calls the archive save routine. The supplied path is base path + `.easz`.

This establishes the direction much more strongly: despite its helper name, `euUnArchive` is assembling a password-protected 7z output archive from file entries and saving it to the `.easz` path. The `.easd` value is used as the archive entry name for the source file path held at `TWordViwer+0xA0`.

Remaining verification: resolve the class pointer at `0x0062F800` used by `SaveToStream` to name the exact stream class, and trace the password callback path that consumes `FPassword`. The static evidence now supports the password and archive-writing interpretation; runtime archive bytes have not yet been captured.


## Run 149 — .easz is created as a TFileStream output file

Source: controller-unarchive workflow run `43870202851`, artifact `14227002967`.

The remaining stream-class question is resolved:
- `0x004041BC` is an IAT thunk to `rtl230.bpl!System.Classes.TFileStream.$bctr(UnicodeString, Word)`.
- `T7zOutArchive.SaveToStream` at `0x00454668` passes its supplied path string to this constructor, with mode `0xFF00` (Delphi `fmCreate`), creating/truncating the output file.
- It then passes the resulting stream to `T7zOutArchive.SetCompleted` at `0x004546C4`, which performs the archive completion path.

Therefore the `.easz` path is not merely an abstract stream name: the routine creates a real file at that path and hands the file stream to the 7z output archive. This closes the static file-output side of the archive pipeline; runtime bytes and actual extraction/consumer behavior remain untested.


## 2026-11-25 authoritative RTTI and wait-state correction

Run 27 artifact `15008774182` proves the wrapper event-property mapping. The TWordApplication RTTI at `0x00429128` identifies fields `+0x80/+0x88/+0x90/+0x98` as `OnDocumentBeforeClose`, `OnDocumentBeforePrint`, `OnDocumentBeforeSave`, and `OnNewDocument`, respectively. The callback pointer assignments map as follows:

| Event field | Actual wrapper event property | Callback pointer | TD32 symbol |
|---|---|---|---|
| `+0x80` | `OnDocumentBeforeClose` | `0x004CD154` | `WordAppDocumentBeforeSave` |
| `+0x88` | `OnDocumentBeforePrint` | `0x004D00AC` / `0x004CE030` | conditional print handler |
| `+0x90` | `OnDocumentBeforeSave` | `0x004CD54C` | `WordAppNewDocument` |
| `+0x98` | `OnNewDocument` | `0x004CD9C0` | `WordAppWindowActivate` |

The TD32 labels are misleading; use RTTI property names for event identity. Event-source IID `00020A00-0000-0000-C000-000000000046` (`ApplicationEvents3`) is read from the server-data record at `0x00627B74`; `DocumentBeforeClose` is DISPID `0x00000006` per Word interop event metadata. The embedded type-library record itself has not yet been decoded directly. The separate routine `0x004CCBBC` is not the registered close event.

The first known writer of viewer `+0x58` is `PrintWithGamPrintOptions` (`0x004C5E04`), called from `OnTmrAutoSave` and from the actual BeforeSave callback `0x004CD54C`. It stores the return of `Emwatutils.DirIsEmpty` (`0x004565DC`) at `Self+0x58` (`0x004C5E44`). That helper enumerates a directory with FindFirst/FindNext and returns the final enumeration status; the close callback `0x004CD154` clears the field at `0x004CD31C`. `0x004563A8` is now identified as `Emwatutils.FixDirectionInFarsiNumericMode`, which normalizes the UnicodeString before enumeration. `PrintWithGamPrintOptions` passes the `+0x54` result to `System.SysUtils.StringReplace` (`0x00403430`) and stores the transformed result at `+0x50`; the BeforeSave call supplies the same `Gamelectronics EMWAT` literal for both replacement parameters. Timer-side parameters still need confirmation.

The `+0xD8` Saved-accessor conflict is resolved by wrapper call shape. `TWordDocument.Set_Saved` at `0x0042BD94` calls vtable `+0xD8` with an output pointer and returns the resulting WordBool, so `+0xD8` is the actual `get_Saved` getter despite the TD32 name. `TWordDocument.Get_Saved` at `0x0042BD34` passes an input value to vtable `+0xD4` and returns void, so `+0xD4` is the actual `put_Saved` setter despite its TD32 name. The close callback at `0x004CD154` calls `+0xD8` and branches on the returned WordBool; it reads `Document.Saved`, not writes `Saved=False`.


### Event-source IID and DISPID cross-check

The TWordApplication server-data record at `0x00627B74` begins with:

- CLSID: `000209FF-0000-0000-C000-000000000046` (Word.Application)
- default interface IID: `00020970-0000-0000-C000-000000000046`
- event-source IID: `00020A00-0000-0000-C000-000000000046` (Word `ApplicationEvents3`)

Microsoft's Word PIA documents `ApplicationEvents3.DocumentBeforeClose`; the Word interop event contract assigns `DocumentBeforeClose` DISPID `0x00000006`. This matches the RTTI property mapping and the callback signature/control flow. The exact DISPID value was corroborated against interop metadata rather than extracted from the BPL's embedded type-library member record.

References:
- Microsoft Learn, [ApplicationEvents3 interface](https://learn.microsoft.com/en-us/dotnet/api/microsoft.office.interop.word.applicationevents3?view=word-pia)
- Microsoft Learn, [ApplicationEvents3.DocumentBeforeClose](https://learn.microsoft.com/en-us/dotnet/api/microsoft.office.interop.word.applicationevents3.documentbeforeclose?view=word-pia)
- Word interop event test, [JNA ComEventCallbacks2_Test](https://github.com/java-native-access/jna/blob/c24bbfad90e49730202cc439f436c1a6820f2dba/contrib/platform/test/com/sun/jna/platform/win32/COM/util/ComEventCallbacks2_Test.java)
- Microsoft VBA docs, [Application.DocumentBeforeClose](https://github.com/microsoftdocs/vba-docs/blob/cfee1b35b419270636defdbee0ac96e5ded071bb/api/Word.Application.DocumentBeforeClose.md)


### Saved property accessor crosswalk — wrapper names are reversed

The TD32-named wrapper procedures are:

- `TWordDocument.Get_Saved` at `0x0042BD34–0x0042BD91`: accepts a value through EDX, passes it to COM vtable slot `+0xD4`, and returns void. This is the actual `put_Saved` setter.
- `TWordDocument.Set_Saved` at `0x0042BD94–0x0042BDF6`: allocates an output WordBool, passes its address to COM vtable slot `+0xD8`, reads the returned WordBool, and returns it. This is the actual `get_Saved` getter.

Thus the imported wrapper names are reversed relative to the COM property accessors. The callback at `0x004CD154` passes a zero-initialized local to slot `+0xD8`, then branches on the returned word. It is reading the actual `Document.Saved` property. It does not set `Saved=False`.

Reference: Microsoft Learn, [Document.Saved property](https://learn.microsoft.com/en-us/dotnet/api/microsoft.office.interop.word._document.saved?view=word-pia).
