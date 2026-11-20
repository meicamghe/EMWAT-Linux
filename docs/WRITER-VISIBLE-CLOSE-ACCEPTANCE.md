# Writer visible close acceptance matrix

Date: 2026-11-20

## Objective

Verify the user's observed workflow: the Writer/Word window is closed without requiring an explicit Save button, then control returns to Almas. The test must distinguish Save, Don't Save, and Cancel rather than treating every close callback as the same outcome.

## Fixture and evidence

Use a disposable document with:
- one baseline marker already saved in the source document;
- one unique marker inserted after opening and deliberately left unsaved;
- a unique run/session identifier that is not embedded in document text.

Use `LibreOfficeAdapter.inspect_close_lifecycle_trace(handle)` to retrieve the in-memory callback trace. It records only fixed event names, attempt ordinals, sequence numbers, and monotonic timestamps. It does not infer the user's choice and does not include document content, field values, file paths, or exception messages.

Capture only diagnostic metadata:
- monotonic timestamp and callback name;
- close-attempt ordinal;
- whether the document reports modified (when queryable);
- snapshot/export success or sanitized error category;
- final response status and byte length;
- whether baseline and unsaved markers are present in the returned fixture.

Do not log letter text, field values, image bytes, signatures, or `signData`.

## Required scenarios

| Scenario | User action | Writer expected state | Almas/bridge expected state | Returned document |
|---|---|---|---|---|
| Save | Close title-bar window, choose Save | Closed | One final response after terminal close | Baseline and unsaved markers present |
| Don't Save | Close title-bar window, choose Don't Save | Closed | One final response after terminal close | Baseline present; unsaved marker absent |
| Cancel | Close title-bar window, choose Cancel | Remains open | Request remains pending; no final response | No final document emitted |
| Retry after Cancel | After Cancel, close again and choose Save or Don't Save | Closes only on accepted attempt | Exactly one final response | Matches the final accepted choice |

## Acceptance criteria

1. Run with a visible Writer instance on each supported Ubuntu/LibreOffice version.
2. Close using the actual window close control, not `document.close(True)` or a headless test.
3. Record the callback order for every attempt, including `queryClosing`, `notifyClosing`, `disposing`, `OnSaveDone`, and `OnSaveAsDone` when observed. The in-memory trace uses normalized fixed names such as `query_closing`, `notify_closed`, `save_done`, and `save_as_done`.
4. Verify the final output content against the expected markers; callback order alone is not a pass.
5. Verify Cancel does not complete the bridge request and a subsequent close attempt can complete it exactly once.
6. Repeat the test to rule out timing-dependent behavior.

## Current implementation guardrail

The current adapter takes a `storeToURL` snapshot from `queryClosing`. That snapshot may not represent the user's final Save/Don't Save choice. Do not infer discard from `notifyClosed` or `disposing`, and do not change the final response contract until the visible acceptance matrix passes or an equivalent interaction contract is independently verified.