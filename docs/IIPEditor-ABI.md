# IIPEditor ABI investigation

## Confirmed interface metadata

- IID: `7834c511-9078-411c-ab08-8b15ef1fd700`
- Implementing class: `TfrmSimpleImageEditor`
- Class VMT: `0x004F046C`
- Interface table: `0x004F03F0`
- Interface vtable: `0x004F03D4`
- Interface subobject offset: `0x430` (1072 bytes)
- Interface table entry count: 1
- `ImplGetter = 0`
- Seven vtable entries: three IUnknown entries and four custom entries.

The adjustment thunks subtract `0x430` from the interface pointer to recover the containing form instance.

## Confirmed custom vtable mapping

| Slot | Thunk VA | Final destination | TD32 symbol | Confidence |
|---:|---:|---:|---|---|
| 3 | `0x004F0381` | `0x004F1158` | `TfrmSimpleImageEditor.GetModalRresult` | High |
| 4 | `0x004F038B` | `0x004F1164` | `TfrmSimpleImageEditor.Hello` | High |
| 5 | `0x004F0395` | `0x004F116C` | `TfrmSimpleImageEditor.Initial` | High |
| 6 | `0x004F039F` | `0x004F17B4` | `TfrmSimpleImageEditor.btnRegisterClick` | High, target; signature requires ABI reconciliation |

The fourth custom thunk does **not** target `Update`. It lands exactly at the TD32 entry for `btnRegisterClick` (procedure size `0xAA`). The disassembly at `0x004F17B4` immediately branches on `DL`:

- `DL=0`: main registration/confirmation path; checks image state, updates control state, and invokes helper `0x00404B9C`.
- `DL=1`: calls `chkForceSinglePageClick`.
- `DL=4`: calls the editor's `CropImage` method, then `TGearImgProc.Rotate90` and `ShowCropRectangle`.
- Other values branch to the common epilogue.

These values follow directly from the instruction sequence `sub dl,1; jb; je; sub dl,3; je`; the earlier values 2 and 5 were incorrect and are superseded by this instruction-level reading.

This strongly indicates the fourth interface slot is a command/notification entry accepting a small enum-like value in `DL`, even though the TD32 symbol labels the target as a VCL event handler with a `TObject` parameter. The thunk adjusts EAX (Self) but leaves EDX untouched, and the target immediately branches on DL. The binary behavior is authoritative; the high-level signature needs further validation.

## IUnknown wrappers

- Slot 0 thunk `0x004F03A9`: adjusts the interface pointer/stack argument and dispatches QueryInterface through class VMT offset `+0x38`.
- Slot 1 thunk `0x004F03BA`: adjusts and jumps to `0x004042F4` (AddRef wrapper).
- Slot 2 thunk `0x004F03C7`: adjusts and jumps to `0x004042FC` (Release wrapper).

## Candidate methods that are not direct custom slots

- `GetHandle` at `0x004F1140`: separate class method; reads `[self+0x408]` and calls helper `0x004F0084` when non-null.
- `Update` at `0x004F1730`: separate method accepting `TEditorNotificationType`; not the destination of the fourth custom thunk.

## Crop-path distinction established by Run 51

The binary contains two distinct methods with similar names:

- `TGearImgProc.Crop` at `0x004EEDB4`, size `0x70`: constructor-like initialization routine. It allocates/initializes the object field at `[self+0x20]` through helper calls; it is not the editor's crop operation.
- `TfrmSimpleImageEditor.CropImage` at `0x004F11E8`: editor-side orchestration method. The `DL=4` command path calls this method before rotating the processor and refreshing the crop rectangle.

Do not equate these two methods or implement either as the crop pixel algorithm without tracing their downstream calls. The actual image crop operation remains to be located in the GEAR/ImageEn call chain.


## Run 52: crop interaction and geometry

The Run 52 target disassembly adds `chkForceSinglePageClick` and confirms the crop UI's coordinate model.

### `chkForceSinglePageClick` — VA `0x004F1A04`

- Reads the image-view control client rectangle through VMT slot `+0x64` on `[self+0x3C0]`.
- Uses a 10-pixel inset when deriving the available display rectangle.
- Reads image dimensions from the processor object at `[self+0x408]`: width at `+0x40`, height at `+0x3C`.
- Compares available display width/height against image width/height, computes a scale ratio using x87 floating-point operations, and fits/centers a rectangle within the available view.
- Writes the resulting left/top/right/bottom coordinates to the crop-control object `[self+0x3C4]` through four helper calls: `0x00404844`, `0x00404854`, `0x0040484C`, and `0x0040485C`.

This is crop-rectangle fitting/constraint logic, not pixel manipulation. The helper calls appear to set the four rectangle edges; their public semantic names remain unresolved.

### Mouse interaction

- `pbImgViewerMouseDown` at `0x004F1274`: if crop mode is active (`[self+0x428]`), converts the stored mouse coordinates to image-space using independent width and height scale factors. It then passes a four-coordinate rectangle to `0x004EEE24).
- `pbImgViewerMouseMove` at `0x004F1308`: hit-tests near the four crop edges and inside the rectangle. It stores an interaction mode in `[self+0x41C]` (values 1–5) and the active mouse coordinates in `[self+0x420]` / `[self+0x424]`.
- `pbImgViewerMouseUp` at `0x004F1404`: applies the selected edge/corner/interior drag delta to the crop coordinates at `[self+0x40C]`, `[self+0x410]`, `[self+0x414]`, and `[self+0x418]`; updates the crop-control edges through the same four helpers; and invalidates the viewer via VMT slot `+0xA8`.

The mouse handlers establish a useful native-port model: keep crop geometry in image coordinates, transform pointer positions with separate X/Y scale factors, and treat the view-control rectangle as presentation geometry only. The exact interaction-mode enum and the helper setter signatures still need caller/callee cross-checking.

### Distinguish object setup from the crop algorithm

The TD32 symbol `TGearImgProc.Crop(TRect)` maps to `0x004EEDB4` (size `0x70`). Its body creates/initializes the object field at `[self+0x20]` through helper `0x004AFE78` and factory/constructor dispatch at `0x00404614`, passing three addresses in the method's local data area. It does not visibly call an image crop API or process pixels in this body. Therefore, do not implement this method as the actual crop pixel operation based on its name alone.

The editor command `DL=4` still invokes `TfrmSimpleImageEditor.CropImage` (`0x004F11E8`), then `TGearImgProc.Rotate90` and `ShowCropRectangle`. This command path is orchestration/UI refresh, not proof that the pixel crop occurs inside `CropImage`. The actual crop operation must be traced through the object initialized by `TGearImgProc.Crop` and its downstream calls.


## Native-port guidance

1. Implement a native editor interface adapter with IUnknown-equivalent lifetime semantics and four custom operations.
2. Preserve the original `0x430` offset only when analyzing the Win32 object; do not reproduce it in a native object layout.
3. Treat custom slot 6 as an enum/command dispatch pending confirmation of the Delphi calling convention and all call sites. Do not expose it as a raw `TObject*` API.
4. Analyze `Initial` (`0x004F116C`), `GetModalRresult` (`0x004F1158`), and `Hello` (`0x004F1164`) bodies and all call sites before implementing behavior.
5. Keep `Update` separate; trace its callers and the `TEditorNotificationType` values to determine its role in the editor lifecycle.
