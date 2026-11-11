# IIPEditor ABI investigation

## Confirmed from Run 47

- Interface IID: `7834c511-9078-411c-ab08-8b15ef1fd700`
- Implementing class: `TfrmSimpleImageEditor`
- Class VMT: `0x004F046C`
- Interface table: `0x004F03F0`
- Interface vtable: `0x004F03D4`
- Interface offset: `0x430` (decimal 1072)
- Interface table entry count: 1
- `ImplGetter = 0`

The vtable contains seven executable entries before adjacent RTTI/data begins. The first three entries are the standard IUnknown slots; the remaining four are the interface-specific slots. Do not read beyond these seven entries as vtable pointers.

All seven entries point to small adjustment thunks around `0x004F0381..``0x004F03C7`. The disassembly begins with an adjustment by `-0x430`, consistent with converting the interface subobject pointer back to the containing `TfrmSimpleImageEditor` instance. The first three wrappers adjust a stack argument; the four custom wrappers adjust EAX. Full thunk bodies and jump destinations are being emitted by the updated analyzer; method-to-slot assignments remain unconfirmed until those destinations are inspected.

## Candidate class methods

The TD32 symbol stream identifies four methods on `TfrmSimpleImageEditor` that are plausible implementations of the four custom interface slots:

| Method | VA | TD32 size | Observed behavior |
|---|---:|---:|---|
| `GetHandle` | `0x004F1140` | `0x18` | Reads field `[self+0x408]`; if non-null, calls helper `0x004F0084`; returns result |
| `GetModalRresult` | `0x004F1158` | `0x0A` | Calls `0x004049CC` and returns |
| `Hello` | `0x004F1164` | `0x07` | Returns field `[self+0x42C]` |
| `Update` | `0x004F1730` | `0x81` | Uses editor controls/state and accepts `TEditorNotificationType` |

These are candidates, not a confirmed slot ordering. The original method signatures from TD32 are:

- `GetHandle()`
- `GetModalRresult()`
- `Hello(Imageprocessing::TImageProcessor)`
- `Update(Imageprocessing::TEditorNotificationType)`

## Implications for the native port

1. Model `IIPEditor` as a four-method interface in addition to IUnknown semantics.
2. Preserve the subobject offset `0x430` only when reproducing the original Win32 object layout; a native implementation should use an explicit interface adapter instead.
3. Do not implement the four methods based only on their names. In particular, `GetHandle` delegates to helper `0x004F0084`, and `GetModalRresult` delegates to `0x004049CC`; those helpers still need semantic analysis.
4. Confirm each custom vtable slot by following the corresponding adjustment thunk to its final jump/call target. The updated workflow now emits the full thunk instruction sequence.
