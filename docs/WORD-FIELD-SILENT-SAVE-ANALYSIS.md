# Word field extraction and SilentSaveEmwatDoc: deeper lifecycle findings

Source: GitHub Actions artifact `emwat-word-lifecycle-run117`, analysis input `EmwatMethods.bpl1`.

## 1. Confirmed call path

`TWordViwer.GetDocFieldName(UnicodeString)` is a 0x954-byte procedure at `0x004BB81C–0x004BC16F`.

At `0x004BBA72–0x004BBA86`, it compares a value obtained from the Word/document-side object against the constant at `0x004BBEE8`. If the comparison is equal, it directly calls:

```asm
004BBA72  mov eax, [ebp - 0x48]
004BBA75  mov edx, 0x4bbee8
004BBA7A  call 0x403248
004BBA7F  test eax, eax
004BBA81  jne 0x4bba8b
004BBA83  mov eax, [ebp - 0x2c]
004BBA86  call 0x4d23d8
```

The target is `TWordViwer.SilentSaveEmwatDoc` at `0x004D23D8`. This establishes a real non-close call path: the silent-save routine can be entered during document-field lookup, conditionally, before the field extraction loop continues. The literal string at `0x004BBEE8` has not yet been decoded, so its field name/meaning must remain unknown.

## 2. What SilentSaveEmwatDoc visibly does

Procedure range: `0x004D23D8–0x004D281B` (1092 bytes).

Observed control flow:

- It first checks a string/configuration condition using constants at `0x004D2728` and `0x004D2758`. The exact text/value has not yet been recovered.
- It tests four collection-like members at object offsets `+0x8C`, `+0x94`, `+0x98`, and `+0x9C`; if all are empty, it exits through the common cleanup path.
- It creates/initializes an object stored through global `0x0062A828`, then calls helper `0x004AEA78` (`TfrmWordPrintOption.SetLetterReceivers`).
- It creates two temporary objects and copies values from members at `+0x90`, `+0x94`, `+0x98`, and `+0x9C` into them through virtual/interface calls.
- It calls helper `0x004AEBBC` (`TfrmWordPrintOption.FreePrinters`), then marks a flag at offset `+0x44C` on the global object and invokes a virtual method at vtable offset `+0x13C`.
- It also calls `0x004D2948`, which TD32 identifies as `TWrapRecord.LineCount`, and conditionally updates global state.

The helper names and data movement strongly connect this routine to the letter-recipient/printer-option state used by EMWAT. They do **not**, by themselves, prove the exact file-save mechanism or the complete semantics of the temporary objects. No claim is made here that this routine simply performs a Word SaveAs.

## 3. Implication for the Word lifecycle model

The previous assumption that `SilentSaveEmwatDoc` is only a BeforeClose action is not supported. The directly observed path is:

```
GetDocFieldName(requested field)
  -> compare document-side value with special constant (literal unresolved)
  -> SilentSaveEmwatDoc (conditional)
  -> continue field extraction
```

Separately, `OnTmrAutoSave` (`0x004B8A84`) registers Word event callback records, including `0x004CD154`, `0x004CD54C`, `0x004CD9C0`, and either `0x004D00AC` or `0x004CE030` depending on an object flag. Therefore, the current evidence supports at least two distinct lifecycle mechanisms:
1. Word event callback registration during viewer initialization.
2. A conditional silent-save path triggered from field lookup.

Do not collapse these into one periodic timer without further evidence.

## 4. Next reverse-engineering targets

1. Recover the literal string at `0x004BBEE8` and constants at `0x004D2728` / `0x004D2758`.
2. Identify the object type and semantics of fields `+0x8C` through `+0x9C` and the global object at `0x0062A828`.
3. Resolve the virtual method at vtable offset `+0x13C` and determine whether it writes a document, synchronizes recipients, or updates print state.
4. Trace the caller/request path into `GetDocFieldName` to identify which web/API command requests the special field.
5. Correlate this path with the captured `POST /?invoke=58351` request/response once payload decoding is available.

## Confidence boundaries

- **Confirmed:** direct conditional call from `GetDocFieldName` to `SilentSaveEmwatDoc`.
- **Confirmed:** helper symbols for recipient setup and printer cleanup are invoked by the silent-save routine.
- **Confirmed:** `OnTmrAutoSave` registers multiple callback records.
- **Unknown:** special field literal, exact serialization, exact persistence destination, and semantic meaning of the virtual `+0x13C` call.


## 5. Callback target identities resolved

TD32 symbols in the same artifact resolve several callback addresses written by `OnTmrAutoSave` into the Word event sink:

| Address | TD32 method identity | Meaning |
|---|---|---|
| `0x004CD154` | `WordAppDocumentBeforeSave` | Word document BeforeSave callback |
| `0x004CD54C` | `WordAppNewDocument` | NewDocument callback |
| `0x004CD9C0` | `WordAppWindowActivate` | WindowActivate callback |
| `0x004CE030` | `WordAppDocumentBeforePrintBGPrint` | BeforePrint callback path with background-print handling |
| `0x004D00AC` | `LoadOptions` | Alternative callback target selected by the `[viewer + 0x3C]` flag; not a Word event name in the TD32 symbol table |

The registration code at `0x004B8C9C–0x004B8D12` writes callback function pointers and their `TWordViwer` context into the Word application/event sink object. It selects `0x004D00AC` when `[TWordViwer + 0x3C] != 0`, otherwise `0x004CE030`. The other three callback/context pairs are registered unconditionally in this path.

This narrows the lifecycle model: EMWAT explicitly hooks Word's **BeforeSave**, **NewDocument**, **WindowActivate**, and a **BeforePrint/background-print** path, plus a mode-dependent `LoadOptions` callback. The event registration is therefore not merely generic timer setup. It is the central integration point for reacting to Word document and window lifecycle events.

The exact COM event interface slot-to-name mapping is supported here by the Delphi TD32 procedure symbols and the registration sequence; the detailed side effects of every callback still require separate procedure-level analysis.


### BeforeSave callback behavior (procedure-level observations)

The callback at `0x004CD154` is not an empty notification hook:

- It first checks that the Word document passed by COM matches the viewer's tracked document pointer at `[TWordViwer + 0x48]`; unrelated documents are ignored.
- It checks viewer state byte `+0x5E`. When that state is false, it writes `0xFFFF` to the callback's `WordBool`-sized argument at the supplied pointer and exits. In the Word BeforeSave event signature, this is consistent with setting the event's Cancel flag.
- When active, it invokes `TWordViwer.PreparePrintDocument` at `0x004CB108`, then inspects the Word document through a virtual/interface call at vtable offset `+0xD8`.
- A further branch controlled by viewer byte `+0x5F` creates/shows a Delphi form/dialog and can also set the Cancel flag. It then updates viewer state bytes `+0x5C` and `+0x5E`, and performs additional Word document operations.
- The routine therefore participates in controlling Word's native Save event and coordinating EMWAT's own document preparation/state. It should not be implemented as a passive event logger.

The exact user-facing dialog text and all branch meanings still require decoding of the referenced string constants and form resources. The callback's Cancel writes are directly visible; their business meaning is not yet fully established.


## 6. BeforePrint callback: confirmed control flow

The callback at `0x004CE030` is now traced through its full procedure range (`0x004CE030–0x004CE36A`).

Observed sequence:

1. It compares the COM document argument with the viewer's tracked document at `[TWordViwer + 0x48]`. A different document is ignored.
2. It obtains a Word document property through the document interface (vtable offset `+0xB4`, then `+0xAC`) and compares the resulting string against a constant at `0x004CEB9C`.
3. If that comparison does not match, it constructs a Delphi dialog using constants at `0x004CEBB4`, `0x004CEBCC`, `0x004CEC04`, and `0x004CEC18`, sets the event Cancel argument to `0xFFFF`, and exits.
4. If it matches, it initially clears the event Cancel argument, reads a viewer option/state string (constants at `0x004CEC64` and `0x004CEC94`), and may set Cancel again if the option/state check fails.
5. On the continuing path, it creates the same global print-option object used by `SilentSaveEmwatDoc` (`0x0062A828`), copies viewer state at `+0x58` into it through helper `0x0040496C`, and copies a local value into object offset `+0x448`.
6. It creates two temporary string/list-like objects and transfers values from viewer members `+0x90` / `+0x94` and `+0x98` / `+0x9C`, then calls `TfrmWordPrintOption.FreePrinters` (`0x004AEBBC`).

This confirms that the BeforePrint callback is an active print-preparation/validation gate. It can cancel printing for a document mismatch or a failed state/option check, and on the accepted path it prepares the global print-option state and recipient/printer-related data. The exact meaning of the compared document property and option strings is still unresolved because the referenced string constants have not yet been decoded.

## 7. PreparePrintDocument is small but significant

`TWordViwer.PreparePrintDocument` at `0x004CB108` is only 172 bytes. It obtains a Word document object from viewer member `+0x44`, invokes a document-interface method at vtable offset `+0x160` with argument `-1`, then invokes another method at offset `+0x108` with either the viewer byte at `+0x4D` or the constant `10`.

This is the complete observed body; the COM interface slot names are not resolved. It is called from the accepted BeforeSave path. It is therefore safe to say it applies a pair of document-level operations before EMWAT's save handling continues, but not safe yet to label those operations as a particular Word setting.

## 8. Autosave recovery UI is a separate feature

The same binary contains `TfrmShowAutoSaveFiles` in module `uSendLog`, with handlers for listing, opening, deleting, and closing Word documents. The form's `Delete` method iterates selected list entries and performs file deletion operations; `CloseWordApp` iterates tracked Word instances and closes them; `FormClose` releases the tracked document/application objects and associated state.

This is evidence of a user-visible autosave/recovery-file management feature, distinct from the viewer's `OnTmrAutoSave` callback registration. The Linux design should therefore treat these as separate capabilities:
- in-session Word lifecycle and print/save interception;
- recovery-file discovery, preview/open, and deletion.

The actual autosave directory, filename pattern, and recovery file format have not yet been established from this trace.


## 9. BeforePrint string constants decoded

The adjacent PE data dump resolves several previously opaque constants used by `WordAppDocumentBeforePrintBGPrint`:

- `0x004CEB9C`: UTF-16LE string `false`.
- `0x004CEC64`: UTF-16LE string `Word Print Dialog`.
- `0x004CEC94`: UTF-16LE string `SOFTWARE\\Emwat\\Dynamic Config`.
- `0x004CECDC`: UTF-16LE string `setting as you print with "Gam" print dialog` (the literal appears to contain `Gam`; preserve the binary spelling until the complete resource/context is checked).

The callback's first comparison is therefore against the literal `false`. If the document-side property is not equal to `false`, EMWAT constructs a dialog whose caption/title input is `Word Print Dialog`, uses the message beginning `setting as you print with "Gam" print dialog`, sets the Word BeforePrint Cancel argument, and exits. This is a much more concrete finding than the earlier generic "document mismatch" interpretation: the branch is tied to a document property and a print-dialog warning/confirmation path.

The callback then reads configuration under `HKCU\\Software\\Emwat\\Dynamic Config` through the same registry helper family used elsewhere in EMWAT. The two arguments supplied to that helper are `Word Print Dialog` and the registry path, so `Word Print Dialog` is the candidate registry value name. The subsequent string comparison determines whether printing proceeds or is cancelled. The separate text at `0x004CECDC` is passed as a message/logging string in this path; the trace does not prove it is a registry value name.

**Implementation consequence:** the Linux print workflow needs a per-user configuration option corresponding to the `Word Print Dialog` setting, and a print gate that can cancel before dispatching the job. Do not hardcode the current Windows registry storage; map the setting into Winux's per-user configuration model.


## 10. Autosave/recovery form lifecycle: more precise findings

### FormShow is initialization, not file discovery

`TfrmShowAutoSaveFiles.FormShow` (`0x005EC1B4–0x005EC223`) resets the form's Word-application tracking member at offset `+0x3D0` to nil, creates/obtains a Word automation wrapper, and stores an interface/reference at `+0x3D8`. It does not enumerate recovery files in this procedure. Therefore the actual file-discovery operation is elsewhere (or performed by the wrapper/component before this handler).

### Double-click handler is a list transformation, not direct proof of opening

`lslFilesDblClick` (`0x005EC224–0x005EC567`) iterates a collection associated with the list control, obtains each entry's text, converts/parses a numeric/date-like value, applies a comparison involving constant `0x18`, and rewrites the displayed list item text using string slicing/formatting helpers. The procedure does not visibly call Word's `Documents.Open` or an equivalent document-open interface method. Consequently, despite the event name, this handler appears to normalize/reformat list entries and filter/mark entries; it is not evidence by itself of the actual recovery-file open operation. The precise meaning of the 24-unit comparison is unresolved (it may be a time/duration threshold, but the units and direction are not established).

### BeforeClose handler on the recovery form

`TfrmShowAutoSaveFiles.WordAppDocumentBeforeClose` is only 18 bytes. It checks the first word of the event's document-related argument against `0x2E`; when equal, it calls `CloseWordApp`. This is a narrow conditional hook, not a general handler that processes every document close.

### CloseWordApp tracks and closes automation objects

`CloseWordApp` (`0x005EBDA8–0x005EBF1F`) iterates a collection stored under form member `+0x3C0`, accesses each entry's object/reference at offset `+0x20`, invokes interface methods on it, and releases the collection entry. After iteration, it checks a separate object at `+0x3C0` and conditionally invokes another method before clearing state. This is consistent with cleanup/closing of tracked Word automation objects, but the exact COM methods (including whether a given call is Quit, Close, or Release) are not symbolically resolved.

### FormClose performs deterministic cleanup

`FormClose` (`0x005EBF20–0x005EC1A7`) performs cleanup only when member `+0x3D0` is non-null. It iterates the tracked automation collection, obtains each tracked document/object, invokes a method at vtable offset `+0x29C`, clears the tracking member, then releases the Word automation wrapper at `+0x3D8` and associated list/object state. The interface slot is unresolved, so describe this as per-item COM cleanup rather than asserting a specific Word Close call.

## 11. Recovery-file path remains unknown

The current run-117 artifact does not expose a confirmed recovery directory, filename extension, or stable naming template. The FormShow routine does not enumerate files, and the double-click routine alone does not identify the open operation. Avoid implementing a guessed `.asd`, `.wbk`, or EMWAT-specific path in Linux until the file-discovery caller and its constants are recovered.

## 12. Revised Linux implementation requirements

The evidence supports these independent components:

1. **Word lifecycle adapter:** track the document owned by EMWAT and handle BeforeSave, BeforePrint, NewDocument, WindowActivate, and close-related callbacks.
2. **Print gate:** validate the active document and per-user print-dialog setting before dispatching a print job; cancellation must be possible before printing.
3. **Document preparation:** preserve the two currently unidentified document-interface operations from `PreparePrintDocument` as explicit adapter hooks until their semantics are resolved.
4. **Recovery manager:** keep recovery discovery, listing, preview/open, deletion, and Word-process cleanup separate from the in-session autosave/event subsystem.
5. **Per-user settings:** represent Windows Dynamic Config values in a Linux per-user config store; do not emulate the Windows registry as the native storage backend.

### Confidence

- **Confirmed:** FormShow initializes a Word automation wrapper and resets a tracking field; it does not itself enumerate recovery files.
- **Confirmed:** the double-click handler rewrites/transforms list entries and contains a `0x18` comparison; no direct Word Documents.Open call is visible in that procedure.
- **Confirmed:** recovery-form close hooks conditionally invoke tracked Word automation cleanup.
- **Unknown:** recovery directory, filename pattern, file format, exact COM interface method names, and the semantic units of the `0x18` comparison.


## 10. Recovery form lifecycle rechecked against the actual procedure bodies

A more conservative re-read of the TD32 traces refines the earlier interpretation:

### FormShow does not scan files

`TfrmShowAutoSaveFiles.FormShow` (`0x005EC1B4–0x005EC223`) is only 112 bytes. It:
- clears the form member at offset `+0x3D0`;
- calls a helper against global `0x00464720`;
- stores the returned interface/reference in the form member at `+0x3D8`.

There is no visible directory enumeration, wildcard search, or file-open operation in this method. Therefore the earlier suggestion that FormShow itself initializes the recovery-file list is not established. The actual population path is elsewhere (possibly form construction, a helper, or code outside this traced method).

### Double-click is a list transformation, not proven file opening

`lslFilesDblClick` (`0x005EC224–0x005EC567`) iterates an internal set/list of selected indexes, reads associated list-item data, performs numeric/date-like conversions and string slicing/reformatting, and writes a transformed string back through a list-view item interface. The visible body does not call Word `Documents.Open`, `Workbooks.Open`, ShellExecute, or an obvious file-open API. The method appears to format/update displayed list information; its name alone is not evidence that it opens the selected recovery document.

### Delete is a multi-stage operation

`Delete` (`0x005EB828–0x005EBDA7`) first gathers selected list entries from the list control into a temporary string list. If there are selections, it:
- calls the form's `FormClose` handler as part of its cleanup/preparation path;
- creates a secondary form/object and wires its owner/callback fields;
- invokes its virtual method at vtable offset `+0x50`;
- performs further list/string processing and calls another virtual method at offset `+0x54`;
- stores the resulting value in form member `+0x3D4`, waits 100 ms, and calls a further helper on the selected list data.

The actual filesystem deletion primitive is not yet identified in this trace. It would be incorrect to say that this procedure definitely calls Win32 `DeleteFile` directly; deletion may be delegated to the created helper object or another layer.

### CloseWordApp has a tracked-instance collection

`CloseWordApp` (`0x005EBDA8–0x005EBF1F`) iterates a collection exposed through form member `+0x3C0` and nested member `+0x2BC`. For each entry whose state/flag at offset `+0x20` is true, it obtains a referenced object and calls its virtual method at offset `+0x10`, then clears/releases that entry through a helper. It subsequently checks a separate object from member `+0x3C0`, sets a flag, and invokes virtual method `+0x104`.

This confirms that the form tracks multiple Word-related objects and performs controlled teardown. The exact COM interface names for these slots remain unresolved.

### BeforeClose callback is only a small gate

`TfrmShowAutoSaveFiles.WordAppDocumentBeforeClose` is 18 bytes:
- compare the first word of its event argument with `0x2E`;
- if equal, call `CloseWordApp`;
- return.

This callback is a narrow condition-triggered cleanup gate, not a general recovery-file save implementation.

## 11. Recovery subsystem confidence update

What is now supported:
- a recovery/management form exists;
- it tracks Word-related object/interface collections;
- it has selection, formatting, delete, and controlled Word teardown paths;
- the BeforeClose callback can trigger teardown under a specific event-argument condition.

What remains unproven:
- the directory or directories containing recovery files;
- the file naming convention and extension;
- the component that enumerates and populates the list;
- the actual open/recover operation;
- the exact filesystem deletion primitive and confirmation flow.

The Linux implementation should not yet assume Word's standard `.asd` / `.wbk` locations. Recovery discovery should remain behind a pluggable provider until the native format and location are identified.


## 12. Additional correction: the recovery form's "Show File" handler is misnamed at the code level

The TD32 symbol `btnShowFileClick` at `0x005EB81C` is only 10 bytes and directly calls `TfrmShowAutoSaveFiles.CloseWordApp` (`0x005EBDA8`). It does not itself open a selected file. This may be a UI naming mismatch, a handler whose actual behavior is cleanup, or an incomplete view of work delegated elsewhere; the disassembly is unambiguous about the direct call.

The form's `FormShow` also does not enumerate a directory. Consequently, neither the button handler nor FormShow currently provides the missing recovery-file discovery/open implementation. Further tracing must locate the code that populates the list and the helper object created by `Delete`.

## 13. Practical consequence for implementation scope

Do not implement the recovery window as if the binary already proved a conventional "browse autosave files and reopen document" workflow. The defensible feature contract at this point is narrower:
- a UI with a selectable list and display-string transformation;
- a tracked collection of Word-related objects;
- a selected-item deletion workflow delegated partly to helper objects;
- cleanup of tracked Word instances on a conditional BeforeClose event.

The actual recovery semantics remain an open reverse-engineering item.


## 14. Delete path: shared Word Automation class identified

Cross-procedure comparison resolves an important ambiguity. The global class reference at `0x00420250`, instantiated by `Delete` at `0x005EB9B5`, is also instantiated by `TWordViwer.LoadDocument` at `0x004D0EA3` and by `BGPrintWithGamPrintOptions` at `0x004C605C`. In the viewer constructor its instance is stored as the viewer's Word-side object at offset `+0x44`. This strongly identifies the class as the shared Word Automation wrapper, not an arbitrary background worker.

In `Delete`, the new instance is stored in form member `+0x3D0`; the form instance and callback address `0x005EC594` are written into the new object's fields at `+0x84` and `+0x80`. It is initialized through helper `0x00404FBC`, configured through calls at `0x00440B2C`, `0x00440950`, and `0x0043F308`, then a virtual method at offset `+0x50` is invoked. The code subsequently accesses the object's event/interface member at `+0x3D8`, builds a string argument, and performs a conditional loop with further virtual calls. This is consistent with a dedicated Word Automation session being used during the selected-item deletion workflow.

The exact semantics of the virtual slots and event member are not yet resolved. This does not prove that the object opens each selected file or that it is a worker thread. The earlier generic-worker interpretation should be discarded.

## 15. FormClose performs Word-side per-item operations

When form member `+0x3D0` is non-null, `FormClose`:
- obtains a collection-like value from that object through an interface call at vtable offset `+0x20`;
- iterates the resulting count;
- for each item, builds an index/format string and obtains an item interface from the object at `+0x3D0`;
- invokes a method at vtable offset `+0x30` on that item interface;
- invokes a method at vtable offset `+0x29C` on a second interface associated with the iteration;
- clears the form's `+0x3D0` reference;
- waits 100 ms, then processes and clears a separate list stored at `+0x3D4`.

This establishes that FormClose iterates Word-side collection items and invokes operations on each. The collection and method names remain unresolved; it is not yet safe to label them Documents.Close, Save, or Delete.

## 16. UI resource facts

The `TFRMSHOWAUTOSAVEFILES` Delphi form resource confirms a button event named `btnRemoveClick`, a plausible UI source for the `Delete` action. It also contains the standard `OnCreate`, `OnShow`, and `OnClose` event names. It exposes no recovery directory, wildcard, extension, or definitive open-file action.

The code-level `btnShowFileClick` remains a 10-byte wrapper that calls `CloseWordApp`; despite its name, its direct body does not open a file. Treat this as an unresolved naming/dispatch discrepancy.

## 17. Revised recovery conclusions

- The deletion workflow creates and configures the same Word Automation wrapper class used by the main viewer.
- The form's close handler performs per-item operations through Word-side collection interfaces.
- A separate list at form offset `+0x3D4` is processed after a 100 ms delay.
- The Delphi resource confirms a Remove button event.
- Still unknown: collection interface type, vtable slot names, file paths/extensions, list population source, and whether selected items are Word documents, recovery files, or another Word-side collection.

Next high-value target: resolve the shared Word Automation class VMT/interface slots `+0x20`, `+0x30`, `+0x50`, and `+0x29C`, then trace how selected-item strings from `Delete` reach that object.


## 18. The `+0x29C` calls are late-bound Automation dispatch, not a named VMT method

A cross-check against the generated Word type-library wrapper resolves the nature of one previously ambiguous call.

The generated `TWordDocument.Close` overloads in module `EmwatConsts` (addresses `0x0042FEB0`, `0x0042FF08`, `0x0042FF7C`, and `0x0042FFF4`) all:
1. obtain the underlying document interface through `TWordDocument.GetDefaultInterface` at `0x0042ABA0`;
2. invoke the interface entry at vtable offset `+0x29C`;
3. release the temporary interface reference.

The no-argument, one-argument, two-argument, and three-argument Close wrappers all use this same slot. A separate generated `SaveAs2000` wrapper at `0x00430070` also uses `+0x29C`. This is characteristic of the type-library's late-bound Automation invocation entry, where the actual operation is selected by the dispatch metadata/arguments; it is not a uniquely named native VMT method.

### Reinterpretation of the recovery FormClose loop

The recovery form's `FormClose` loop also invokes `+0x29C` on a temporary interface after building per-item string/variant arguments. This means it is performing a late-bound Automation call on each iterated item. The exact dispatch member cannot be named from the slot alone. Although `TWordDocument.Close` uses the same slot, it would be an overclaim to conclude that the recovery loop calls `Document.Close` without recovering its DISPID/name and argument layout.

The `+0x30` call in the same loop is made on a separate temporary interface returned by the wrapper after an index/string lookup. Its method identity is also unresolved.

### Evidence boundary

- **Confirmed:** `+0x29C` is used by generated Word Automation wrappers for multiple named methods, including `TWordDocument.Close` and `SaveAs2000`.
- **Strong inference:** the recovery FormClose loop uses the same late-bound Automation dispatch mechanism on per-item interfaces.
- **Unknown:** which dispatch member the recovery loop invokes, what the generated index/string arguments mean, and whether the operation closes, saves, or otherwise processes a document.
- **Unknown:** the identity of the separate `+0x30` interface method.

This corrects the earlier wording: describe the FormClose loop as per-item Automation dispatch, not as a confirmed Close call.


## 19. Recovery cleanup dispatch cross-checked against Word type-library wrappers

The same artifact contains generated `TWordDocument` wrappers in module `EmwatConsts`:

- `TWordDocument.Close()`: `0x0042FEB0`
- `TWordDocument.Close(OleVariant)`: `0x0042FF08`
- `TWordDocument.Close(OleVariant, OleVariant)`: `0x0042FF7C`
- `TWordDocument.Close(OleVariant, OleVariant, OleVariant)`: `0x0042FFF4`
- `TWordDocument.SaveAs2000(...)`: `0x00430070`

Each wrapper obtains the underlying COM interface through `0x0042ABA0` and calls vtable offset `+0x29C`. This validates that `+0x29C` is the late-bound Automation invocation entry used by the imported Word type-library wrapper. The operation name is supplied by the generated wrapper/dispatch metadata and arguments, not by the vtable offset itself.

The recovery form's `FormClose` similarly builds per-item string/variant values, obtains temporary interfaces from the Word Automation wrapper, and calls `+0x29C` on one of them. Thus it is definitely issuing a per-item late-bound Automation command. It is not yet possible to identify the exact command as Close or another Word method from this callsite alone.

## 20. Recovery filesystem search: negative evidence only

A targeted scan of the extracted run-117 analysis documents found no direct references to common filesystem enumeration/deletion APIs or standard Word recovery extensions:
- no `FindFirst` / `FindNext` procedure evidence;
- no `DeleteFile` or `FileExists` string/procedure evidence;
- no `TSearchRec`, `*.asd`, or `*.wbk` references.

This is only a negative result for the extracted artifact corpus, not proof that EMWAT never uses those APIs. File discovery/deletion may be inside another BPL/DLL, imported through an unresolved helper, or represented by an Automation call.

The current best next target is the helper/object contract behind `0x0043EAB8` and the event callback `0x005EC594`, plus the selected-item string construction at `0x005EBB15–0x005EBC25`. Those are the remaining links between the recovery UI and the Word Automation command.
