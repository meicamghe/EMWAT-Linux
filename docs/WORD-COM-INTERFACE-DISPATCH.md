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

The controller-notify chain therefore reuses the current Word `_Document` COM interface; wrapper analysis maps its `+0x2BC` call to `PrintOutOld()`.

## What is established vs. unresolved

Established by static symbol/signature and instruction evidence:
- `TWordViwer.WordAppNewDocument` receives a `Wordxp._Document` interface.
- `TWordViwer.WordAppDocumentBeforeSave` also receives a `Wordxp._Document` interface and compares it with `Self+0x48`.
- `Self+0x48` is used as the current document interface in multiple Word viewer callbacks.
- Both `WordAppNewDocument` and the `OnControlerNotify -> 0x004D281C` path dispatch through byte offset `+0x2BC` on that document reference.

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


## Additional callback trace: WordAppNewDocument (run 18)

The expanded trace of `0x004CD54C` confirms the TD32 procedure name `TWordViwer.WordAppNewDocument`. Its signature includes `DelphiInterface<Wordxp._Document>`.

Relevant sequence:

- `[Self+0x48]` is checked against the incoming `_Document` interface pointer.
- If the document matches and the event/state flags permit processing, the code pushes that interface pointer and calls its vtable entry at `+0x2BC` (`0x004CD6BF`).
- The callback subsequently calls the same document interface's `+0xDC` entry at `0x004CD6F9`.
- The method also toggles internal state bytes at `Self+0x5C`, `Self+0x5E`, and `Self+0x5F`, indicating guarded event/state handling around the COM calls.

This makes the identification of the `+0x2BC` receiver as the Word `_Document` interface stronger: the receiver is not merely inferred from a neighboring field access; the method's incoming typed interface parameter is compared to the stored field and then used as the receiver of the virtual call.

A direct TD32 CALL-xref scan for `0x004CD54C` found no direct callers. This is consistent with an event callback being registered and invoked indirectly, but the registration-to-event firing chain still needs explicit proof. Do not interpret the absence of direct CALL xrefs as proof that the method is unused.

The `_Document` slot `+0x2BC` is now mapped with high confidence to `PrintOutOld()` from the generated `Wordxp.TWordDocument` wrapper. Remaining work is to explain the business reason for this call in the Word viewer callbacks and distinguish other interface types that reuse the same numeric offset.


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
- Run 27 resolves `[ebp+8]` as the parent procedure's EBP passed by `push ebp` at the direct callsite. Therefore `[[ebp+8]-0x0C]` is the parent procedure's local `[ebp-0x0C]`, which stores its incoming ECX value. The interface type of that ECX value remains unresolved pending caller analysis.
- The run-24 typed positive control confirms that `Wordxp.TWordDocument.Get_Tables` uses `_Document` slot `+0x38`, but it does **not** establish that the nested helper's receiver has that interface type. The earlier claim that the two target calls are likely `_Document.Get_Tables()` remains withdrawn pending identification of the caller's ECX list element.

The `Get_Tables` wrapper also clarifies its own acquisition pattern: it invokes `0x0042ABA0` with `EDX=&[ebp-4]`; that accessor checks `[self+0x78]), conditionally invokes the object's `+0x50` slot, then passes `[self+0x78]` to runtime helper `0x00401428` to populate the local interface. This is distinct from the BeforeClose receiver load. The wrapper's initial `0x00401420` call is an imported runtime thunk; the artifact resolves its IAT target outside the BPL image, so its semantic name is still unknown.

Run 24 also resolves `0x00401478` to `rtl230.bpl!@System@@CheckAutoResult`. This is compiler/runtime error checking after the interface dispatch, not an application connector call.

**Updated interpretation after run 27:** `[ebp+8]` is a Delphi nested-procedure static link to the caller's EBP, and the receiver is the caller's captured ECX local. Run 29 identifies the direct caller of `FillImgFldsForPrint` as `GetFieldIndexInList`; its ECX argument comes from an indexed list element. The remaining type-identification task is to inspect that list element's source and declaration. Keep the local POST / `invoke=5208` mapping open.


## Direct-call cross-reference and caller chain (lifecycle runs 26–29)

The TD32 direct-call scan found one direct call to `0x004CCBBC` from `FillImgFldsForPrint` at `0x004CCF8F`. Run 27 disassembled the complete caller (`0x004CCDC8–0x004CD153`) and proved that the call passes the caller's EBP as a nested-procedure static link. This resolves the target's `[[ebp+8]-0x0C]` receiver as the caller's captured incoming ECX value.

Run 29 then scanned callers of `FillImgFldsForPrint` and found one direct caller in TD32-bounded procedures:

- `TWordViwer.GetFieldIndexInList`, call at `0x004CB361)
- The caller loads ECX from `[array_or_list_base + ESI*4]` before calling `FillImgFldsForPrint`.

The current proven chain is therefore:

`GetFieldIndexInList list element → ECX → FillImgFldsForPrint local [ebp-0x0C] → nested static link → target receiver for both +0x38 calls`.

This strongly places the target in a field-index/list-processing path. The exact type of the list element and the interface methods at slot `+0x38` remain unresolved until the full `GetFieldIndexInList` procedure is reviewed. The direct-call scans do not exclude computed or indirect references, so independent callback registration is not categorically ruled out; it is simply not established by the current evidence.

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

This proves that the `ECX` value captured by `FillImgFldsForPrint` comes from an indexed element of the caller's array/list at `[caller EBP-8 + ESI*4]`. The next step is to inspect the full `GetFieldIndexInList` body to identify the list's element type and how that element is initialized. The scan found only one direct caller in TD32-bounded procedures; indirect calls and computed function pointers are outside its coverage.

This strengthens the classification of `0x004CCBBC` as a nested helper reached from a field-index/list-processing path, but it still does not establish the semantic type of the list element or completely exclude another indirect event-registration path.


## Field-list construction and interface-pointer evidence (lifecycle run 30)

The complete `GetFieldIndexInList` procedure (`0x004CB1B4–0x004CB5E3`) clarifies how the nested helper is reached.

At `0x004CB332–0x004CB338`, it calls `0x004CB638` with:
- EAX = the `TWordViwer` instance saved from the method entry;
- EDX = the method's second incoming argument, saved at `[ebp-4]`;
- ECX = address of local `[ebp-8]`, an output location for the resulting list/array reference.

The returned list/array pointer is then queried for its count at `0x004CB340`. The loop reads each 32-bit element from `[list_base + ESI*4]` and passes that value in ECX to `FillImgFldsForPrint` at `0x004CB361`. The callee captures ECX in its local `[ebp-0x0C]`.

The receiving code in `FillImgFldsForPrint` dereferences this value as an interface-like pointer and dispatches through its vtable:
- `+0x28` at `0x004CCE15`;
- `+0x38` at `0x004CCE55`, `0x004CCEE7`, and `0x004CCF35);
- the nested helper at `0x004CCBBC` uses the same captured value for its own `+0x38` calls.

This proves the list elements are pointer-sized values used as interface/vtable receivers. It does **not** yet identify the declared interface type or the method names at slots `+0x28` and `+0x38`. The positive-control mapping `Wordxp._Document.Get_Tables` at slot `+0x38` remains specific to its typed wrapper and cannot be transferred to these receivers without matching type evidence.

The list builder at `0x004CB638` and the caller of `GetFieldIndexInList` are now added to lifecycle run 31 for direct inspection. The current static chain is:

`GetFieldIndexInList → list/array output from 0x004CB638 → interface-like element in ECX → FillImgFldsForPrint → nested helper 0x004CCBBC`.

**Still unresolved:** the exact interface IID/type, method names at the relevant slots, and whether this helper is separately registered as a close event. The observed localhost POST (`127.0.0.1:1984`, `invoke=5208`) remains unmapped to this static path.
