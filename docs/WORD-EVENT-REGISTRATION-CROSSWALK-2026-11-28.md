# Word COM event registration crosswalk — 2026-11-28

## Source and run

- Workflow: `EMWAT parallel contract closure v2`
- Run: `46118303840`
- Word event artifact: `15252384254`
- Registration procedure: `TWordViwer.OnTmrAutoSave` at `0x004B8A84`

## Exact callback slots written by OnTmrAutoSave

The procedure obtains the event/sink object from `TWordViewer+0x44`, then writes callback pointer/context pairs:

| Event object offset | Callback pointer | TD32 symbol | Context offset |
|---:|---:|---|---:|
| `+0x80` | `0x004CD154` | `WordAppDocumentBeforeSave` | `+0x84` |
| `+0x88` | conditional | see below | `+0x8C` |
| `+0x90` | `0x004CD54C` | `WordAppNewDocument` | `+0x94` |
| `+0x98` | `0x004CD9C0` | `WordAppWindowActivate` | `+0x9C` |

The `+0x88` callback is selected from the viewer flag at `+0x3C`:

- If nonzero: `0x004D00AC` — `LoadOptions`.
- If zero: `0x004CE030` — `WordAppDocumentBeforePrintBGPrint`.

The stored context for each pair is the current `TWordViewer` instance.

## BeforeClose and BeforePrint findings

- `0x004CCBBC` has TD32 symbol name `WordAppDocumentBeforeClose`, but the exact registration block above does not store it.
- A raw code-pointer scan found no static pointer reference to `0x004CCBBC`.
- Its only bounded direct caller is `FillImgFldsForPrint` at `0x004CCF8F`. That call is an internal helper path; it does not establish that Word's COM DocumentBeforeClose event is connected.
- `0x004CDC2C` (`WordAppDocumentBeforePrint`) has no direct callsites or code-pointer references in this scan.
- `0x004CE030` (`WordAppDocumentBeforePrintBGPrint`) is the callback conditionally installed at `+0x88`; do not confuse it with `WordAppDocumentBeforePrint`.

## Corrected interpretation

The active `OnTmrAutoSave` event wiring proves BeforeSave, NewDocument, WindowActivate, and one conditional callback (LoadOptions or BeforePrintBGPrint). It does **not** prove a Word BeforeClose event handler is registered. The method name `WordAppDocumentBeforeClose` is not sufficient evidence of an active COM event connection.

This does not mean Word close behavior is absent. It means the actual close-driven return to Almas may be implemented through another route: application shutdown, a separate event sink/connection point, process/window monitoring, timer polling, or the parent-page bridge. Those candidates remain unproven.

## Remaining checks

1. Find all event sink/connection-point creation and Advise/Unadvise calls; inspect any event slots not initialized by `OnTmrAutoSave`.
2. Trace `FillImgFldsForPrint` to understand why it calls the BeforeClose-named method.
3. Correlate Word process/window exit with the parent-page message or HTTP bridge.
4. Keep the existing BeforeSave `Saved` property setter semantics separate from BeforeClose behavior.

No close lifecycle should be implemented from the callback name alone.


## Follow-up: BeforeClose-named routine is a print-field helper

The next trace closes the direct-call context: `TWordViewer.GetFieldIndexInList` calls `FillImgFldsForPrint` at `0x004CB361`; that routine calls `WordAppDocumentBeforeClose` at `0x004CCF8F` while iterating field metadata. The callee reads viewer arrays at `+0xE8/+0xEC`, calls Word document interface slot `+0x38`, delegates to `0x004BCA88`, and returns a Boolean used to filter/continue field processing. This is not a close operation in the observed call graph. See `docs/WORD-BEFORECLOSE-NAMED-HELPER-AND-PRINT-FIELD-CHAIN-2026-11-28.md`.


## WindowActivate body cross-check

The registered `WordAppWindowActivate` callback at `0x004CD9C0` does not call a local close/quit handler. Its observed body queries the Word Window interface through slot `+0x29C`, then releases temporary interface values. The registered `WordAppNewDocument` callback manages document/window state and may close a prior document when a new one arrives, but it is not a DocumentBeforeClose event. Combined with the print-field-only `WordAppDocumentBeforeClose` helper, no active COM DocumentBeforeClose callback has been established in this registration path. The Word-close-to-Almas return mechanism remains an explicit unresolved item.

## Run 29 reconciliation — callback behavior versus COM event identity

The callback at `0x004CD154` remains the function that performs the close/save decision and clears viewer state `+0x58` after calling Word `Document.Close` through slot `+0x29C`. It is stored at event-record offset `+0x80` by `OnTmrAutoSave`, with the current viewer as context. Run 153's `Sleep(5)` / `ProcessMessages` wait loop and the subsequent `response-word` write remain consistent with this functional release path.

However, the formal COM event DISPID for that record is still not mapped. Use the neutral description **registered close/save-decision callback at `0x004CD154`**; do not assert that the event is definitively `DocumentBeforeClose` or `DocumentBeforeSave` from the TD32 label or diagnostic string alone.

`0x004CCBBC`, despite its `WordAppDocumentBeforeClose` TD32 label, is a different routine. Its bounded direct caller is `FillImgFldsForPrint` (`0x004CCF8F`), where its Boolean return participates in print-field filtering. It is not the callback that releases the HTTP request.

Evidence crosswalk: Run-153 request/wait artifacts; Run 50 Word/Printer artifact `15104841284`; Run 29 re-audit of event registration and helper callers.
