# Word viewer field-offset ownership — 2026-11-25

## Scope

This note separates two distinct objects that both use numeric offset `+0x80` in the Word lifecycle path. It is based on the controller-notify workflow artifact `15016516836` (run `45602986551`) and event-sink artifact `15015875555` (run `45599975084`).

## 1. TWordApplication event-record field

In `TWordViwer.OnTmrAutoSave` (`0x004B8A84`):

- The method loads `[TWordViwer+0x44]`.
- That nested object is used by TWordApplication methods `SetConnectKind` (`0x00404FBC`) and `Get_DisplayAutoCompleteTips` (`0x00440950`).
- Callback/context pairs are then written through the nested object pointer:
  - `[object+0x80] = 0x004CD154`, `[object+0x84] = TWordViwer Self`
  - `[object+0x90] = 0x004CD54C`, `[object+0x94] = Self`
  - `[object+0x98] = 0x004CD9C0`, `[object+0x9C] = Self`
  - `[object+0x88]` is conditionally `0x004D00AC` or `0x004CE030`, with context at `+0x8C`.

The TWordApplication RTTI crosswalk maps its event field `+0x80` to `OnDocumentBeforeClose`. This is the event callback slot.

## 2. TWordViwer base-path field

In `TWordViwer.OnControlerNotify` (`0x004BB3B0`), the method's own viewer instance pointer is read directly:

- `[Self+0xA0]` is passed to the archive object's first list as the source document path.
- `[Self+0x80]` is read at `0x004BB596` and `0x004BB5C4`.
- Both values are passed to `FixDirectionInFarsiNumericMode` (`0x004563A8`).
- The resulting sibling/base paths receive `.easd` and `.easz` suffixes and are used by the archive helper.

This is a different object from the TWordApplication event record above. The matching numeric offset does not imply matching storage or semantics.

## 3. Why the field scan was easy to misread

The controller workflow's class-field scan reports references grouped under TD32 procedures belonging to `TWordViwer`. In `OnTmrAutoSave`, however, the relevant instruction is:

```asm
mov eax, [TWordViwer+0x44]
mov [eax+0x84], TWordViwer
mov [eax+0x80], 0x004CD154
```

The write is through the nested pointer at `Self+0x44`, not through `Self`. It must not be reported as a write to `TWordViwer+0x80`.

## 4. Remaining work

The current artifacts establish the use of `TWordViwer+0x80` as a path base, but do not identify where that string is initialized or assigned. The controller-notify workflow now traces:

- `TWordViwer.$bctr` at `0x004D08B4`
- `TWordViwer.$bdtr` at `0x004D0D24`
- Direct callers of both routines

Do not infer the path's directory, filename, or normalization rules until those traces or sanitized runtime evidence establish them.

## Evidence boundary

- Statically observed instructions and class/RTTI cross-references are distinguished above.
- The actual filesystem naming semantics and initial value of the viewer base path remain unresolved.
- No customer document content, credentials, cookies, or private runtime payloads are included.
