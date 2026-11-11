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
- `pbImgViewerMouseUp` at `0x004F1404`: applies the selected edge/corner/interior drag delta to the crop coordinates at `[self+0x40C]`, `[self+0x410]`, `[self+0x414]`, and `[self+0x418]`; updates the crop-control edges through the same four helpers; and invalidates the viewer via VMT slot `+0xA8`. The full method ends at `0x004F15F8` and does not call `0x004EEE24`; pixel cropping is performed in the separate mouse-down path when the crop rectangle is submitted.

The mouse handlers establish a useful native-port model: keep crop geometry in image coordinates, transform pointer positions with separate X/Y scale factors, and treat the view-control rectangle as presentation geometry only. The exact interaction-mode enum and the helper setter signatures still need caller/callee cross-checking.

### Distinguish object setup from the crop algorithm

The TD32 symbol `TGearImgProc.Crop(TRect)` maps to `0x004EEDB4` (size `0x70`). Its body creates/initializes the object field at `[self+0x20]` through helper `0x004AFE78` and factory/constructor dispatch at `0x00404614`, passing three addresses in the method's local data area. It does not visibly call an image crop API or process pixels in this body. Therefore, do not implement this method as the actual crop pixel operation based on its name alone.

The editor command `DL=4` still invokes `TfrmSimpleImageEditor.CropImage` (`0x004F11E8`), then `TGearImgProc.Rotate90` and `ShowCropRectangle`. This command path is orchestration/UI refresh, not proof that the pixel crop occurs inside `CropImage`. The actual crop operation must be traced through the object initialized by `TGearImgProc.Crop` and its downstream calls.



## Run 53: the image-space crop operation

Run 53 provides a stronger link between the editor's crop rectangle and the image-processing layer.

### `TGearImgProc@$bdtr` — VA `0x004EEE24`

TD32 labels this procedure as a destructor (`$bdtr`), but its observed call sites and machine-level behavior show that it is also used as a rectangle-processing entry point in the crop interaction path:

- `pbImgViewerMouseDown` at `0x004F1274` passes the Gear processor in EAX and a pointer to a four-integer `TRect` in EDX.
- The method copies all four rectangle coordinates to local storage.
- It reads the image handle from `[self+0x10]`; if the handle is positive, it calls `0x004AFF38` with the handle and the rectangle pointer.
- It then calls `ReloadPage` (`0x004EF0E4`) and `GetImageResolution` (`0x004EEEC4`), and sets `[self+0x54]=1` (modified/dirty state).

The Run 55 PE thunk trace resolves `0x004AFF38` to the import `GEAR32PD.DLL!IG_IP_crop` through IAT slot `0x00630CE0`. This confirms that the call is the underlying ImageGear crop operation. The caller pushes the image handle followed by a pointer to the four-integer rectangle before invoking the thunk. The exact imported function prototype, stack-cleanup convention, and rectangle edge convention still need verification against the deployed GEAR32PD version.

The TD32 destructor label and the observed rectangle call convention are not fully reconciled. Treat the observed behavior as confirmed, but retain uncertainty about the source-level symbol/overload identity. Do not rename this method as a confirmed crop API yet.

### Consequence for native implementation

The editor's image-space rectangle is passed to the Gear layer as four integer coordinates. After that call, the processor reloads the active page, refreshes image resolution, and marks the image modified. A native implementation should preserve this sequencing, while the exact coordinate convention (inclusive/exclusive right and bottom edges) and the underlying crop API contract remain to be established.

## Native-port guidance

1. Implement a native editor interface adapter with IUnknown-equivalent lifetime semantics and four custom operations.
2. Preserve the original `0x430` offset only when analyzing the Win32 object; do not reproduce it in a native object layout.
3. Treat custom slot 6 as an enum/command dispatch pending confirmation of the Delphi calling convention and all call sites. Do not expose it as a raw `TObject*` API.
4. Analyze `Initial` (`0x004F116C`), `GetModalRresult` (`0x004F1158`), and `Hello` (`0x004F1164`) bodies and all call sites before implementing behavior.
5. Keep `Update` separate; trace its callers and the `TEditorNotificationType` values to determine its role in the editor lifecycle.


## Run 55: ImageGear crop import resolved

The PE thunk tracer follows `0x004AFF38` to the IAT and identifies the imported function as `GEAR32PD.DLL!IG_IP_crop` (IAT slot `0x00630CE0`). This removes the previous uncertainty about the operation's API identity: `TGearImgProc` forwards the image handle and image-space rectangle to ImageGear's crop function, then reloads the page, refreshes resolution, and marks the image dirty.

The mouse-up handler only updates the on-screen rectangle during dragging; it does not execute the pixel crop. The crop is submitted from the mouse-down handler through `0x004EEE24`. Native implementation should therefore separate interactive rectangle editing from the final `IG_IP_crop`-equivalent pixel operation. Do not assume the Win32 import's exact calling convention or inclusive/exclusive edge semantics without confirming the deployed GEAR32PD ABI.


## ImageGear crop API contract cross-check

The vendor's ImageGear C/C++ reference documents the crop declaration as `AT_ERRCOUNT ACCUAPI IG_IP_crop(HIGEAR hIGear, LPAT_RECT lpCropRect)`. It keeps the pixels on or inside the supplied `AT_RECT`, discards the remainder, and returns an ImageGear error count (zero indicates success in the v18 reference). The Win32 caller's two pushed arguments match this parameter order: image handle first, rectangle pointer second. The four consecutive `movsd` operations in `0x004EEE24` copy 16 bytes from the Delphi rectangle into a local buffer, consistent with a four-32-bit-field rectangle.

For the native port, model the operation as `crop(image_handle, Rect{left, top, right, bottom})` and return/propagate an error result. Do not copy the Win32 calling convention into the Linux ABI. The public reference consulted is for ImageGear v18; EMWAT's exact bundled `GEAR32PD.DLL` version remains unverified, so confirm the installed header/version before relying on any version-specific edge semantics. The vendor reference describes the rectangle as pixels kept inside/on the rectangle; it does not by itself prove whether EMWAT's Delphi-side right/bottom values are inclusive or exclusive.


## Run 57: crop coordinate conversion uses Delphi `System.Round`

The new PE thunk trace for `0x00401058` resolves through IAT slot `0x0062EE2C` to `rtl230.bpl!@System@@ROUND$qqrv`. Therefore the helper is Delphi's RTL `System.Round`, not an application-specific coordinate conversion routine.

### Confirmed mouse-down conversion

In `pbImgViewerMouseDown` at `0x004F1274`:

- X scale = image width `[processor+0x40]` divided by viewer width `[viewer+0x58]`.
- Y scale = image height `[processor+0x3C]` divided by viewer height `[viewer+0x5C]`.
- The four stored crop edges are multiplied by the appropriate scale and each floating-point result is passed through `System.Round`.
- The resulting local `TRect` is laid out in standard Delphi order: `Left, Top, Right, Bottom`. The instruction order is left (field `[self+0x40C]`, X scale), right (`[self+0x414]`, X scale), top (`[self+0x410]`, Y scale), bottom (`[self+0x418]`, Y scale); the local stack slots are arranged so the pointer passed to `0x004EEE24` reads as Left/Top/Right/Bottom.
- This is the final UI-to-image coordinate conversion immediately before the ImageGear crop call.

The x87 sequence is `FILD`, `FMUL`, then the `System.Round` thunk. Delphi's `Round` follows the active x87 floating-point rounding mode; the usual default mode is round-to-nearest-even (banker's rounding). A native port should explicitly choose and test the intended rounding mode rather than silently substituting truncation or always rounding half values away from zero.

### Native-port contract now supported by the binary

```text
scale_x = image_width  / viewer_width
scale_y = image_height / viewer_height

rect.left   = DelphiRound(ui.left   * scale_x)
rect.top    = DelphiRound(ui.top    * scale_y)
rect.right  = DelphiRound(ui.right  * scale_x)
rect.bottom = DelphiRound(ui.bottom * scale_y)

ImageGearCrop(image_handle, rect)
ReloadPage()
GetImageResolution()
modified = true
```

This confirms the crop rectangle's four-field shape, field ordering, independent axis scaling, and the RTL rounding function. It still does not establish whether the deployed ImageGear build treats right/bottom as inclusive or exclusive, nor the exact DLL version. The new generated trace is `EmwatMethods-crop-coordinate-helper.md` in the Run 57 artifact.


## Run 76 — IIPEditor is stored at TGearImgProc+0x24

The setter-like routine at 0x004F0084 assigns the interface field [TGearImgProc+0x24]. Its direct caller in TScanCommand.$bdtr adjusts an object pointer by +0x430 before passing it to the setter. This matches the confirmed IIPEditor IOffset 0x430 on TfrmSimpleImageEditor exactly (IID 7834c511-9078-411c-ab08-8b15ef1fd700; VTable 0x004F03D4). A second caller passes nil to the setter, consistent with clearing the reference during editor teardown.

This establishes [TGearImgProc+0x24] as the IIPEditor interface reference; it supersedes earlier descriptions of this field as an unidentified error/result interface. [TGearImgProc+0x28] remains a separate processor/context object and must not be conflated with IIPEditor.

The Gear wrapper at 0x004EF1C4 (TD32 label HasError) dispatches through IIPEditor slot +0x0C. The implementing method at 0x004F1158 calls TWinControl.GetHandle and returns the HWND. Thus the value passed from TGearImgProc to IG_scan_pages and IG_scan_source_select through this dispatch is an HWND, not an error flag. The wrapper symbol names should not be treated as semantic names for the underlying interface methods.
