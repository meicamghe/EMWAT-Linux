# IIPEditor ABI investigation

## Confirmed from Run 47 and Run 49

- Interface IID: `7834c511-9078-411c-ab08-8b15ef1fd700`
- Implementing class: `TfrmSimpleImageEditor`
- Class VMT: `0x004F046C`
- Interface table: `0x004F03F0`
- Interface vtable: `0x004F03D4`
- Interface offset: `0x430` (decimal 1072)
- Interface table entry count: 1
- `ImplGetter = 0`
- Seven vtable entries are present: three IUnknown entries and four interface-specific entries.

The interface pointer is an embedded subobject at offset `0x430`. The adjustment thunks subtract `0x430` from the interface pointer to recover the containing `TfrmSimpleImageEditor` instance.

## Vtable mapping from the actual thunk destinations

| Interface slot | Thunk VA | Destination / behavior | Status |
|---:|---:|---|---|
| 0 — QueryInterface | `0x004F03A9` | Adjusts stack argument, then dispatches through class VMT offset `+0x38` | IUnknown wrapper |
| 1 — AddRef | `0x004F03BA` | Adjusts stack argument, jumps to `0x004042F4` | IUnknown wrapper |
| 2 — Release | `0x004F03C7` | Adjusts stack argument, jumps to `0x004042FC` | IUnknown wrapper |
| 3 | `0x004F0381` | Adjusts EAX by `-0x430`, jumps to `0x004F1158` | Direct target identified as `GetModalRresult` |
| 4 | `0x004F038B` | Adjusts EAX by `-0x430`, jumps to `0x004F1164` | Direct target identified as `Hello` |
| 5 | `0x004F0395` | Adjusts EAX by `-0x430`, jumps to `0x004F116C` | Direct target identified as `Initial` |
| 6 | `0x004F039F` | Adjusts EAX by `-0x430`, jumps to `0x004F17B4` | Destination is adjacent to `Update`; exact symbol/ABI needs verification |

The analyzer prints several instructions after each thunk because it disassembles a fixed byte window. Those later instructions belong to the next thunk and must not be interpreted as part of the current thunk. The actual thunk bodies are the initial pointer-adjustment instruction followed by its unconditional jump.

## Important correction to earlier hypotheses

The earlier candidate list incorrectly treated `GetHandle` and `Update` as confirmed interface methods. The vtable does **not** contain a direct thunk to `GetHandle` at `0x004F1140`, nor to the TD32 entry for `Update` at `0x004F1730`.

- `GetHandle` at `0x004F1140` is a separate class method. It reads `[self+0x408]` and calls helper `0x004F0084` when non-null.
- `GetModalRresult` at `0x004F1158` is a direct vtable target.
- `Hello` at `0x004F1164` is a direct vtable target.
- `Initial` at `0x004F116C` is a direct vtable target.
- `Update` at `0x004F1730` accepts `TEditorNotificationType`, but is not the direct destination of the fourth custom thunk.
- The fourth thunk lands at `0x004F17B4`. This is close to the end of `Update` and must be resolved against TD32 procedure boundaries and raw bytes before assigning a method name or signature.

## Native-port implications

1. Represent the interface with IUnknown semantics plus four custom entries, but do not finalize the fourth method's signature yet.
2. Do not preserve the Win32 subobject offset `0x430` in a native object layout. Use an explicit adapter/interface object and translate calls to native methods.
3. Analyze the code at `0x004F17B4` and its TD32 procedure boundary before writing the interface adapter.
4. Separately inspect `GetHandle`, `GetModalRresult`, `Hello`, and `Initial` bodies. Their names alone are insufficient to define safe native behavior.
