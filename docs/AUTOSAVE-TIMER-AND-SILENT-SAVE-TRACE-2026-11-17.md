# AutoSave timer, interval table and silent-save path — 2026-11-17

## Evidence scope

This note reconciles the successful Word lifecycle artifact from workflow run `44053390645` (artifact `14314903496`) with the bounded PE/TD32 traces in that artifact. It distinguishes observed control flow from assumptions based on Delphi symbol names. No runtime behavior or end-to-end Almas transaction is claimed.

## AutoSaveInterval registry encoding

The `TEmSettingForm.chkDntAskForSaveClick` handler at `0x005EAA20` opens the existing per-user key under:

```
HKEY_CURRENT_USER\\Software\\Emwat\\Dynamic Config
```

It writes several setting values through Delphi's `TRegistry.WriteBool` / `WriteInteger` imports. For `AutoSaveInterval` specifically:

1. It reads the `ItemIndex` of `cbbAutoSaveInterval` at form offset `+0x3F4`.
2. If the index is greater than zero and less than six, it reads a DWORD from the array addressed by the pointer stored at global slot `0x0062A808`, using that ItemIndex as the DWORD index.
3. It multiplies the selected DWORD by `1000` and writes the result as an integer under the registry value name `AutoSaveInterval`.
4. For index zero or an index greater than or equal to six, it writes `10000`.

Thus the stored value is in milliseconds and the normal UI path uses lookup-table values, not the combo index itself. The lookup table contents and the human-readable combo labels are not present in the prior decoded resource-string report. A new CI trace now dumps the global pointer and its target DWORD table from the PE image; exact intervals should only be documented after that artifact is inspected.

## Settings control dependency

The handler named `chkThrdPrntClick` at `0x005EACDC` reads the checkbox at form offset `+0x3C8` (the `chkDntAskForSave` field) and its Enabled state, then applies the resulting boolean to the Enabled property of both radio controls at offsets `+0x3CC` and `+0x3D0` (`rbAutoSave` and `rbDontSave`). It does not write registry values or change either radio button's Checked state in this procedure. The handler name alone should not be used to infer the radio buttons' business meaning.

The save-settings handler also writes the current states of the logging level, XML I/O trace, threaded-print, and save-confirmation controls. The original registry spelling `Background Priniting` remains intentional evidence and is not silently corrected.

## What the method named OnTmrAutoSave actually proves

The TD32 procedure named `TWordViwer.OnTmrAutoSave` begins at `0x004B8A84`. The direct-call scan finds one direct caller: `TWordViwer.LoadDocument` at `0x004B7A58`. Within the decoded routine it:

- initializes the Word automation/event-sink interface held at viewer offset `+0x44`;
- writes callback/owner pairs for BeforeSave (`0x004CD154`), NewDocument (`0x004CD54C`) and WindowActivate (`0x004CD9C0`);
- selects a conditional callback at `0x004D00AC` or `0x004CE030` based on viewer flag `+0x3C`;
- calls the method named `QuitWord` at `0x004CDB54` and, on the alternate branch, calls `SetDocCaption` at `0x004C5D68`.

The method name and its setup path are evidence of a timer-related Word lifecycle routine, but the decoded path does not establish that every tick calls Word's Save method. In particular, there is no direct call from this routine to `SilentSaveEmwatDoc` in the direct-call inventory.

## SilentSaveEmwatDoc is a separate field-inspection path

The BPL procedure `TWordViwer.SilentSaveEmwatDoc` begins at `0x004D23D8`. Its only direct caller found by the executable-wide call scan is `TWordViwer.GetDocFieldName` at `0x004BBA86`, guarded by the preceding comparison at `0x004BBA7A`–`0x004BBA81`. This is not the AutoSave timer routine.

The method first checks the counts of four viewer-owned lists at offsets `+0x8C`, `+0x94`, `+0x98` and `+0x9C`; if all are empty, it exits through the no-work path. On the work path it creates a helper object, calls `TfrmWordPrintOption.SetLetterReceivers` at `0x004AEA78`, and later calls `TfrmWordPrintOption.FreePrinters` at `0x004AEBBC`. It sets a flag at helper-object offset `+0x44C`, invokes a virtual method at `+0x13C`, and calls the routine at `0x004D2948` (TD32 labels this target `TWrapRecord.LineCount`). It then builds field/value lists and passes them to helper `0x004BFF1C` at viewer offsets `+0xB4`, `+0xC4` and `+0xD4`.

The procedure name is retained as a symbol, but the observed body does not by itself prove a Word COM Save call or a durable file write. It appears in the GetDocFieldName/field-inspection path; the exact persistence semantics remain open.

## CloseWordApp virtual-slot correction

In `TfrmShowAutoSaveFiles.CloseWordApp` at `0x005EBDA8`, the virtual call at `0x005EBE9D` (`[edx+0x104]`) is made on the object reached through the form's `+0x3C0` component/list field. It is not a call on a Word document interface. Therefore the previous shorthand description of this as an unresolved Word COM method was too broad. The exact VCL component class and virtual method identity still need to be resolved from the form field's type/VMT evidence.

## Implementation consequences

- Model the interval preference as a persisted millisecond duration, but do not hard-code guessed UI labels or guessed interval choices.
- Keep the timer/event-sink lifecycle separate from field-inspection and serialization helpers.
- Do not implement `SilentSaveEmwatDoc` as an alias for `XStorable.store` until its field-list and output semantics are proven.
- Treat BeforeSave cancellation and the original event callbacks as a separate integration contract from periodic autosave.
- Preserve the distinction between Word COM interfaces and VCL form/list controls when mapping virtual slots.

## Remaining verification

- Inspect the new `autosave-interval-table.md` artifact to recover the exact DWORD lookup values.
- Decode the `cbbAutoSaveInterval` item labels and index convention from the original form resource or runtime form state.
- Resolve the timer enable/interval assignment and establish whether a periodic event is actually wired to this method.
- Trace `GetDocFieldName`'s conditional `SilentSaveEmwatDoc` path through the helper `0x004BFF1C` to its output/persistence boundary.
- Resolve the VCL component type at form offset `+0x3C0` and the virtual slot `+0x104`.


## اصلاح تکمیلی Run 153 — تایمر واقعی و انتظار close

این بخش برداشت قبلی این سند را تکمیل می‌کند: `OnTmrAutoSave` در `0x004B8A84` فقط event-sink setup نیست. این routine `OnControlerNotify` در `0x004BB3B0` را روی `TTimer.OnTimer` در viewer+`0x7C` نصب می‌کند، interval در viewer+`0x88` را حداقل 10 ثانیه قرار می‌دهد و timer را فعال می‌کند. سپس loop همگام `Sleep(5) → ProcessMessages → test viewer+0x58` را اجرا می‌کند تا close callback مقدار را صفر کند. `OnControlerNotify` یک recovery/archive محلی `.easd/.easz` می‌سازد و با HTTP response نهایی یکی نیست.

پس از صفر شدن viewer+`0x58`، `LoadDocument` پاسخ موفق `response-word` را می‌نویسد: HTTP 200، MIME داخلی `application/msword`، Base64 و محتوای legacy OLE DOC/CFB. پاسخ از `AResponseInfo.ContentText`، Indy `WriteContent` و سپس `bResultSet` عبور می‌کند. PCAP حدود 54.558 ثانیه تأخیر را نشان می‌دهد؛ این با طول جلسه و wait loop سازگار است. شرح کامل در `docs/WORD-CLOSE-WAIT-AND-RESPONSE-CORRELATION-2026-11-17.md` است.
