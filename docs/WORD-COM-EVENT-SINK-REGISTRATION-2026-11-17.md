# Word COM event-sink registration and BeforeSave behavior — 2026-11-17

## Evidence scope

Static BPL analysis artifact: `emwat-word-event-sink-analysis`, workflow run `44053390597`, commit `9060bb725a69f0a457934a65c1923084ae998d2b`. The analysis job completed successfully. The observations below are based on the TD32-bounded `TWordViwer.OnTmrAutoSave`, `WordAppDocumentBeforeSave`, and `WordAppDocumentBeforeClose` traces; no live Microsoft Word session was exercised.

## Event sink registration

The auto-save setup code at `0x004B8C60` writes callback pointers and matching `Self` pointers into an event-sink object reached through `TWordViwer` field `+0x44`.

| Event callback | Function target | Event-sink method slot | Self slot |
|---|---:|---:|---:|
| `WordAppDocumentBeforeSave` | `0x004CD154` | `+0x80` | `+0x84` |
| `WordAppNewDocument` | `0x004CD54C` | `+0x90` | `+0x94` |
| `WordAppWindowActivate` | `0x004CD9C0` | `+0x98` | `+0x9C` |
| conditional callback | `0x004D00AC` | `+0x88` | `+0x8C` |

The final callback is installed only when the flag at the controller object offset `+0x3C` is nonzero. The trace identifies the pointer/slot assignments but does not establish the semantic name of that conditional callback. Do not assign it a guessed event name.

The direct-reference scans also find the BeforeSave callback pointer inside the auto-save setup code and the event callback body. The registration is therefore supported by explicit pointer stores, not just by a string or symbol-name match.

## BeforeSave callback: document identity and cancellation

The callback at `0x004CD154` first compares its document argument with the active document stored at `TWordViwer+0x48`. If they do not match, it exits without applying the active-document save path.

For the active document:
- It logs `Document.OnBeforeClose Called.` (the string says BeforeClose although the procedure is BeforeSave).
- If the controller flag at `TWordViwer+0x5E` is false, it writes `0xFFFF` to the COM event's Cancel argument and exits. This is an explicit cancellation path.
- It queries a document save-related property through a virtual call at offset `+0xD8`.
- When that result is zero and the flag at `TWordViwer+0x5F` is set, it displays a three-choice Persian prompt:

  - `موافقم`
  - `خیر`
  - `انصراف`

  The prompt text is: `محتويات اين سند تغيير كرده است. آيا مايل به ثبت تغييرات مي‌باشيد؟` (the document contents have changed; asking whether to save changes).

- A dialog result of `2` writes `0xFFFF` to Cancel and exits the save path. A result of `6` takes a distinct flag-update path; other results follow the default path.
- On the callback's non-cancel completion path, it sets the controller state byte at `+0x5E` to true, calls a document virtual method at `+0x29C`, releases the document reference, clears the active-document pointer at `+0x58`, and logs `Document.OnBeforeClose succeed.`

The exact meaning of the virtual method at document slot `+0x29C`, and the application-level meaning of each numeric dialog result beyond the observed branches, remain unresolved.

## BeforeClose callback

The callback at `0x004CCBBC` receives the document-close event and a Boolean-like argument. It derives field/record information from internal arrays and invokes `TWordViwer.GetXmlFieldInfo` at `0x004BCA88`. It therefore participates in extracting or reconciling document field information during close; it is not merely a generic close notification.

The current bounded trace does not prove that this callback alone serializes the final HTTP response. Keep the close callback, field extraction, worker completion, and HTTP response writer as separate stages.

## Implementation implications

1. A Linux Writer adapter needs an explicit document identity check before applying save/close actions to a document.
2. Save cancellation must be represented explicitly; do not treat every BeforeSave callback as an unconditional save.
3. Preserve the three user choices as distinct outcomes in the compatibility layer. Do not collapse Cancel, “No”, and “Yes” into one Boolean until the original result-to-state mapping is fully established.
4. Model callback registration/lifetime and callback execution separately. The original event sink stores both function pointers and `Self` pointers; stale callbacks after document teardown would be unsafe.
5. The current native/Linux project has not yet implemented the full Word event-sink equivalent. This evidence should guide the future LibreOffice UNO event/listener adapter, but must not be described as an already passing integration.

## Open questions

- Exact semantic name of the conditional callback at `0x004D00AC`.
- Exact mapping of dialog results `2` and `6` to user-visible actions and subsequent document state.
- Meaning of the controller flags at offsets `+0x5E` and `+0x5F` across all document lifecycle paths.
- Meaning of the Word document virtual slot `+0x29C`.
- Whether the close callback's field extraction is the only source of the response document or one stage in a larger wait/COM handoff.
- Runtime differences between the original Word event sink and LibreOffice UNO listeners.

