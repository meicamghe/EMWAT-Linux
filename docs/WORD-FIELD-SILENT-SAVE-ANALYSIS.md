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
