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

## BeforeClose callback is a separate dispatch path

The full trace of `TWordViwer.WordAppDocumentBeforeClose` at `0x004CCBBC` is distinct from the `+0x2BC` `PrintOutOld` path:

- It performs two indirect calls through slot `+0x38` (`0x004CCC2C` and `0x004CCCB2`) on the same temporary interface/object reference.
- It then calls `TWordViwer.GetXmlFieldInfo` at `0x004BCA88` with values assembled from the callback's local/event context.
- No direct HTTP, `127.0.0.1:1984`, `invoke=5208`, or `EditWordDocument` call appears in this callback body.
- The receiver type and exact method represented by slot `+0x38` are not yet identified. The next workflow adds a package-wide `+0x38` callsite scan to compare the receiver against generated WordXP wrapper methods.

This makes the current priority clearer: `PrintOutOld()` explains the `+0x2BC` calls in the Word viewer event paths, but the close-time integration path is more likely to continue through the separate `BeforeClose -> +0x38 dispatches -> GetXmlFieldInfo` sequence. That is a tracing priority, not yet proof that this sequence sends the observed local POST.
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

Thus `+0x38` is interface-specific just like `+0x2BC`. The BeforeClose receiver still needs to be typed from its dataflow/event-record source. The next BPL analysis adds the `TWordDocument.Get_Tables` wrapper body as a positive control and compares it with the BeforeClose callsite.

## Superseded preliminary BeforeClose receiver hypothesis

The initial run-22/run-23 reading incorrectly treated `[ebp-0x0C]` as the receiver for the two `+0x38` calls. The full run-24 disassembly shows that the receiver is loaded from `[[ebp+8]-0x0C]`; the stack local `[ebp-0x0C]` is a separate managed temporary passed later to `GetXmlFieldInfo`. See the run-24 correction below. Do not use the earlier _Document.Get_Tables hypothesis for BeforeClose unless the context field's type is independently established.


## BeforeClose slot +0x38 positive-control wrapper (lifecycle run 23)

Lifecycle run 23 completed successfully (run ID `43510769743`, commit `fec8b0f3f9f5c888129e2a56dee0ee169b5ca706`). Its artifact includes a trace at `0x0042AF00`, inside the TD32-bounded `Wordxp.TWordDocument.Get_Tables` wrapper:

- The wrapper obtains an interface pointer through `0x0042ABA0`, stores it in a local interface temporary, then calls its vtable slot `+0x38` at `0x0042AF21`.
- The package-wide `+0x38` scan independently labels this callsite as `Wordxp.TWordDocument.Get_Tables`.
- This is a typed positive control for the `_Document` interface slot: `_Document.Get_Tables()` is the supported mapping for slot `+0x38` on this interface.
- The trace begins at `0x0042AF00`, after the method's true prologue, so the current artifact does not contain the complete wrapper entry/exit sequence. The next run expands the trace around the method start and the shared interface accessor at `0x0042ABA0`.

**Superseded by lifecycle run 24:** the two BeforeClose-target `+0x38` calls do not use the local interface temporary at `[ebp-0x0C]`. They use the context-derived receiver `[[ebp+8]-0x0C]`. The positive-control wrapper establishes `_Document.Get_Tables()` for slot `+0x38` on a typed `_Document` receiver only; it does not type the context-derived receiver. Do not apply the `Get_Tables` name to the target's two calls without further type evidence.

The run-23 trace of helpers `0x00401420` and `0x00401478` also shows why these addresses should not be mistaken for application business logic: `0x00401420` is an indirect runtime helper thunk whose IAT target is outside the analyzed BPL image, while `0x00401478` resolves to `rtl230.bpl!@System@@CheckAutoResult`. The helper trace alone does not identify the interface value's origin.

The next step is to trace both the complete TD32 procedure containing the direct caller `FillImgFldsForPrint` and the complete target procedure at `0x004CCBBC`, then reconcile these call paths with any independent callback registration. The local POST and `invoke=5208` remain a separate unresolved runtime-to-static mapping.


## Correction: BeforeClose receiver is not the local at EBP-0x0C (lifecycle run 24)

The full run-24 disassembly disproves the earlier receiver-local interpretation above. The two slot calls at `0x004CCC2C` and `0x004CCCB2` do **not** load their receiver from `[ebp-0x0C]`:

- At both sites, the code loads `eax = [ebp+8]`, then `eax = [eax-0x0C]`, then dereferences `[eax]` and calls `[eax+0x38]`.
- The stack-local `[ebp-0x0C]` is separately initialized at callback entry via the runtime helper thunk `0x00401420`; it is later passed as an argument at `0x004CCC34) into `GetXmlFieldInfo` at `0x004BCA88`. It is not the slot-call receiver.
- The actual receiver is therefore a pointer reached through the callback's stack argument/context pointer at `[ebp+8]), offset `-0x0C`. The precise type and origin of that context field remain unresolved.
- The run-24 typed positive control confirms that `Wordxp.TWordDocument.Get_Tables` uses `_Document` slot `+0x38`, but it does **not** establish that the BeforeClose receiver has that interface type. The earlier claim that BeforeClose's two calls are likely `_Document.Get_Tables()` must be treated as unproven and withdrawn pending identification of the context field.

The `Get_Tables` wrapper also clarifies its own acquisition pattern: it invokes `0x0042ABA0` with `EDX=&[ebp-4]`; that accessor checks `[self+0x78]), conditionally invokes the object's `+0x50` slot, then passes `[self+0x78]` to runtime helper `0x00401428` to populate the local interface. This is distinct from the BeforeClose receiver load. The wrapper's initial `0x00401420` call is an imported runtime thunk; the artifact resolves its IAT target outside the BPL image, so its semantic name is still unknown.

Run 24 also resolves `0x00401478` to `rtl230.bpl!@System@@CheckAutoResult`. This is compiler/runtime error checking after the interface dispatch, not an application connector call.

**Updated next step:** trace the producer/caller of `WordAppDocumentBeforeClose` and identify the object/context pointer passed at `[ebp+8]), then trace its field at `-0x0C). Only after that type is established should the `+0x38` method be named. Keep the local POST / `invoke=5208` mapping open.


## Direct-call cross-reference correction: BeforeClose target is also used by image-field printing (run 26)

The TD32 direct-call scan for target `0x004CCBBC` found one direct call site:

- Caller procedure: `FillImgFldsForPrint`
- Call instruction: `0x004CCF8F`
- Call setup immediately before the call:
  - `movzx edx, byte ptr [ebp-0x11]`
  - `mov eax, ebx`
  - `call 0x004CCBBC`

This is important because the target at `0x004CCBBC`, despite its TD32 symbol/name being treated as `WordAppDocumentBeforeClose` in the earlier lifecycle notes, is directly invoked from a procedure named `FillImgFldsForPrint`. The evidence establishes a direct call relationship; it does not yet establish why this helper is called there, whether the caller is preparing image fields for print, or whether the target is also independently registered as a Word close event callback.

Consequently, do not describe `0x004CCBBC` as exclusively an event callback until its complete caller procedure, TD32 signature, and callback-registration references are reconciled. The existing receiver analysis remains valid at the instruction level: the two `+0x38` dispatches use the context-derived pointer `[[ebp+8]-0x0C]`, while the local `[ebp-0x0C]` is a separate temporary. The actual interface type remains unresolved.

A new workflow helper, `tools/trace_td32_procedure.py`, was added to disassemble the entire TD32 procedure containing an arbitrary VA. Lifecycle run 27 uses it on `0x004CCF8F` to capture the complete `FillImgFldsForPrint` body. Its result must be reviewed before assigning semantics to the call or changing the broader close/save model.

### Evidence boundary

- **Proven:** one TD32-bounded direct `CALL 0x004CCBBC` exists inside `FillImgFldsForPrint`.
- **Proven:** the call site passes a value in `EAX` and a byte-derived value in `EDX`.
- **Not proven:** the complete purpose of the call, whether the target is also registered as a close event, or whether either interface dispatch triggers the observed localhost POST.
- **Not proven:** that this helper call is itself the user-visible document-close action.
