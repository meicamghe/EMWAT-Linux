# Scanner interface and acquisition contract — Run 61

Date: 2026-11-11  
Evidence: `EmwatMethods-target-disassembly.md` from workflow run `43001855137` (artifact `13846033438`), TD32-bounded x86 disassembly.

## Scope and confidence

This document records what is directly visible in the bounded machine code. It deliberately does not assign semantic names to undocumented interface slots, scanner mode integers, or ImageGear prototypes. The exact deployed `GEAR32PD.DLL` build and its matching SDK/header set have not yet been identified.

## Two distinct scanner entry paths

### `TfrmGScanPreview.SelectScanner` — VA `0x0061DEF4`

Observed sequence:

1. Clears form flag `[self+0x456]`.
2. If the incoming Boolean argument is true, invokes an earlier helper and may take an early-exit branch.
3. Sets ImageGear JPEG quality with `IG_save_JPEG_quality_set` (thunk `0x004AFF20`, immediate value `0x41`).
4. Reads the configured output path from `[self+0x458]`, performs Delphi string/file handling, and checks a global status field.
5. Calls `IG_scan_pages` (thunk `0x004AFF30`) in two branches. The pushed scalar arguments differ: one branch pushes `1` and `0x28`; the other pushes `1` and `2`. The device/object argument is obtained through helper `0x004049CC`. The code then passes callback/context data to helper `0x0061D100`.
6. Checks the global status again, calls helper `0x0061D3BC`, validates the current image handle at `[self+0x428]` with `IG_image_is_valid`, and returns a Boolean-like result.

Important: the two integer argument sets are recorded as raw evidence only. Do not label them as duplex, color, feeder, page mode, or any other scanner option until the exact ImageGear version/prototype is known. This bounded method contains no direct call to `IG_scan_source_select`.

### `TGearImgProc.SelectScanner` — VA `0x004EF9CC`

This is a separate orchestration path and must not be merged with the preview form path.

Observed object layout and dispatch:

- `[self+0x28]` holds an interface-like object. The method checks it for null.
- It invokes the object's VTable entry at byte offset `+0x0C`, passing an output pointer, then checks the returned/output value.
- It invokes the same `+0x0C` entry again later to obtain another interface-related value.
- It calls local helper `0x004EF048`, then invokes a virtual method through the `TGearImgProc` instance VMT at offset `+0`, and passes the resulting value, another object, and a Boolean-like argument to `IG_scan_pages` at `0x004EFA96`.
- The returned value from `IG_scan_pages` is stored in `[self+0x4C]`.
- Subsequent branches query status/error values through helper `0x004EF1DC`, retrieve additional objects via interface VTable offset `+4`, and in two branches create a form/object and invoke its VTable entry at byte offset `+0x13C`. The return value is compared with `1`.
- Other branches dispatch through the TGearImgProc VMT at offsets `+8` or `+4`.
- The method returns a small status value (observed values include 0, 1, and 2) after exception-safe cleanup.

The interface method names and the meaning of the status values are unresolved. The class's VMT candidate is `0x004EE074`, instance size `0x60`; the interface-like object at `[self+0x28]` is not itself identified by the current interface-table scan. The VMT slot `+0x13C` belongs to a dynamically obtained form/object; it is not a GEAR import.

## What this establishes

- EMWAT has at least two distinct scan orchestration paths: preview-form acquisition and TGearImgProc-mediated scanner selection.
- The preview path sets JPEG quality, prepares an output path, calls `IG_scan_pages`, passes callback/context data into a helper, then validates the active image handle.
- The TGear path depends on an interface-like device/provider object and several virtual callbacks, not merely on a direct call to an ImageGear scanner function.
- The static caller attribution for `IG_scan_source_select` remains suspect. Neither of the two SelectScanner bodies above provides evidence for a direct call to that import. The previously reported callsites attributed to `ShowCropRectangle` and `SetCurrentPage` must be rechecked at raw callsite/thunk level before being used.

## Linux architecture consequence

Keep the Linux design split into independently testable services:

1. **Device discovery/selection:** SANE device enumeration and explicit selected-device identity.
2. **Acquisition session:** source capabilities, options, start/read/cancel, and device errors, mapped from SANE rather than guessed ImageGear integer modes.
3. **Scan result delivery:** a callback/event interface that reports page-start, page data, page-complete, cancellation, and failure. Do not reproduce Delphi VMT layout.
4. **Image/page store:** owns decoded pixel buffers and metadata independently of scanner lifetime.
5. **Preview/editor:** consumes page-store objects and never owns the scanner handle.
6. **Export:** separate per-page and multipage writers with explicit partial-failure reporting.

Suggested neutral acquisition contract (design proposal, not recovered ABI):

- `ScanRequest`: device ID, requested options, output policy, cancellation token.
- `ScanEvent`: session ID, event kind, page index, optional image/page payload, optional structured error.
- `ScanResult`: ordered page IDs, selected device ID, effective options, completion status, warnings/errors.

A native implementation should not expose ImageGear file-descriptor handles or Delphi object pointers in its public interfaces.

## Next reverse-engineering tasks

1. Resolve the runtime type and method names for the interface object at `[TGearImgProc+0x28]` using RTTI/interface tables, constructor writes, and callsites that populate the field.
2. Trace the confirmed callees `GetEditorModalResult` (`0x004EF048`), `LoadPage` (`0x004EF1DC`), `TWinControl.GetHandle` (`0x004049CC`, imported from VCL), and `GetImagePageNumber` (`0x0061D100`) in their actual call contexts. These are not four anonymous scanner helpers.
3. Revalidate every `IG_scan_source_select` callsite by decoding the actual instruction target and following the import thunk to its IAT slot.
4. Identify the exact shipped `GEAR32PD.DLL` version before interpreting scanner constants or ABI.
5. Only then finalize the SANE option mapping and implement a native acquisition prototype with fake-device tests plus hardware tests.

## Explicit non-claims

This analysis does not establish the exact scanner interface method names, ImageGear calling convention/prototypes, the meaning of numeric mode values, or successful runtime acquisition on Linux. No native scanner backend has been implemented yet.


## Run 62 — address identity correction

The four extra target traces from Run 62 resolve the target identities and correct the earlier generic helper interpretation:

| Address | Actual identity | Consequence |
|---|---|---|
| `0x004EF048` | `TGearImgProc.GetEditorModalResult` (TD32 symbol) | A form/editor result query; not a scanner-specific helper. |
| `0x004EF1DC` | `TGearImgProc.LoadPage` (TD32 symbol) | A page-loading/status path; its bounded body queries a value through helper `0x00403270`, then calls `0x00401398` with `[self+0x0C]` and checks the returned integer. |
| `0x004049CC` | VCL import thunk `vcl230.bpl!TWinControl.GetHandle` via IAT `0x0062FC48` | The call in `TfrmGScanPreview.SelectScanner` obtains a native window handle; it is not an interface/provider callback. |
| `0x0061D100` | `TfrmGScanPreview.GetImagePageNumber` (TD32 symbol) | It enumerates image/page-related entries and updates UI/control state; it is not a callback passed to the scanner. |

The `GetEditorModalResult` disassembly shows a byte-sized selector in `DL`, a switch-like branch, and a Boolean result. Its exact selector meanings still need callsite/context correlation. `GetImagePageNumber` uses `IG_error_check`, iterates a count, and calls `IG_page_count_get`/related imported routines while constructing page-related state; its exact UI semantics need the DFM and caller context. `LoadPage` checks an interface-like object at `[self+0x0C]` using helper `0x00401398`, returning a Boolean-like status. These facts narrow the work but do not identify the object type stored at `[TGearImgProc+0x28]`.

**Correction to previous next-step wording:** these four addresses are now symbol-resolved identities, not four anonymous helper routines. The open scanner question is the runtime type and construction/population path of the object at `[TGearImgProc+0x28]`, plus the semantics of the virtual methods at offsets `+0x0C`, `+4`, and the instance VMT's slot `+0`.


## Run 62 — identifying the editor interface stored at `TGearImgProc+0x28`

Run 62 provides a much stronger identification than the earlier layout-only inference:

- The TD32 symbol for `TGearImgProc.SetEditorForm` explicitly declares its parameter as `System.DelphiInterface<ImageProcessing.IIPEditor>`.
- In `SetEditorForm` (`0x004EFF94`), the supplied interface is written into `[TGearImgProc+0x28]` and the code invokes its VTable slot `+0x20` to retrieve an integer result before updating the editor/page state.
- The RTTI/interface-table report decodes `IIPEditor` with IID `7834c511-9078-411c-ab08-8b15ef1fd700`.
- The only implementing class identified in this BPL is `TfrmSimpleImageEditor` (VMT `0x004F046C`), with interface VTable `0x004F03D4` and interface offset `0x430`.
- The interface VTable's first three entries are IUnknown methods. The interface-specific thunk entries include `+0x0C` → `TfrmSimpleImageEditor.GetModalRresult` (`0x004F1158`), `+0x10` → `Hello` (`0x004F1164`), `+0x14` → `Initial` (`0x004F116C`), and `+0x18` → `btnRegisterClick` (`0x004F17B4`).

Therefore `[TGearImgProc+0x28]` is the `IIPEditor` Delphi interface reference, not a scanner-driver/provider object. The `SelectScanner` calls through interface VTable `+0x0C` are calls to the editor's `GetModalRresult` method. The name and body indicate an editor-modal-result query, not scanner source enumeration. This materially changes the interpretation of the earlier scanner-selection sequence.

### Revised interpretation

`TGearImgProc.SelectScanner` is coordinating with the registered image editor (`IIPEditor`) while invoking ImageGear's `IG_scan_pages`; it is not obtaining a SANE-like device interface from `[self+0x28]`. Device/provider discovery remains unresolved and must be located elsewhere (likely in the scanner/preview form or a separate component path).

### Next targets

1. Trace `TGearImgProc.SetEditorForm` callers and the `IIPEditor` lifetime (interface assignment, AddRef/Release, and clearing on editor close).
2. Decode `TfrmSimpleImageEditor.GetModalRresult`, `Hello`, `Initial`, and `btnRegisterClick` in context to understand the editor handshake.
3. Revisit `TGearImgProc.SelectScanner` with this corrected type: identify the actual object passed to `IG_scan_pages` from the VMT call at `[self]`, plus the output stored at `[self+0x4C]`.
4. Search the full BPL and DFM resources for the true scanner-device selection/control path; do not assume the `IIPEditor` field represents a scanner interface.



## Run 63 — VMT slot zero resolves to HasError (2026-11-11)

The expanded VMT scan now includes the leading virtual slots of `TGearImgProc`. It resolves the class VMT at `0x004EE074` and establishes these first three entries:

| VMT slot | Target | TD32 identity |
|---|---:|---|
| `+0x00` | `0x004EF1C4` | `TGearImgProc.HasError` |
| `+0x04` | `0x004EEB60` | `TGearImgProc.CheckOutputParameter` |
| `+0x08` | `0x004EF9CC` | `TGearImgProc.SelectScanner` |

This corrects the earlier uncertainty about slot `+0`: it is not an unknown scanner callback. In `TGearImgProc.SelectScanner`, the call sequence at `0x004EFA91–0x004EFA98` loads the object's VMT, calls slot `+0`, pushes its return value, and then calls `IG_scan_pages` through thunk `0x004AFF30`. The method body at `0x004EF1C4` checks field `[self+0x24]`; if non-null, it invokes that object's interface VTable slot `+0x0C` and returns the result. The exact interface type and semantic meaning of the returned value remain unproven.

The neighboring slot `+4` is independently named `CheckOutputParameter`; its implementation examines the editor interface at `[self+0x28]`, compares an image/result-related object and performs cleanup/notification work. It should not be conflated with the `HasError` result.

### Consequences and next probes

1. Resolve the object stored at `[TGearImgProc+0x24]`: find all writes, constructor initialization, interface RTTI and lifetime operations. This is now a separate field from the confirmed `IIPEditor` reference at `+0x28`.
2. Inspect the full argument construction around `IG_scan_pages` at `0x004EFA53–0x004EFA98`, keeping each stack argument distinct. Do not assign meanings to the values until the deployed GEAR32PD version/prototype is established.
3. Trace `TGearImgProc` constructor, `GetParentHandle`, `ShowEditor`, and `SetCurrentPage`, plus `TfrmGScanPreview.ShowCropRectangle`, to resolve field population and revalidate scanner-source selection callsites.
4. Keep `IIPEditor` at `[self+0x28]` and the still-unidentified object at `[self+0x24]` separate in all future notes.

**Confidence:** VMT slot identities and the dataflow from slot `+0` to the `IG_scan_pages` call are high-confidence static findings. The runtime type at `+0x24`, the meaning of the return value, and the GEAR API argument semantics are unresolved.


## Run 64 — resolving the value passed through TGearImgProc VMT slot zero

Run 63's expanded VMT report and target disassembly establish the exact dispatch:

- TGearImgProc VMT is at 0x004EE074.
- Slot +0x00 points to TGearImgProc.HasError at 0x004EF1C4; slot +0x04 points to CheckOutputParameter; slot +0x08 points to SelectScanner.
- In SelectScanner, instructions 0x004EFA91–0x004EFA98 load the instance VMT, call slot zero, push the returned EAX value, then call the IG_scan_pages thunk at 0x004AFF30. This is a confirmed dataflow, not an inferred callback name.
- HasError checks [self+0x24]. If null it returns zero. If non-null it loads that object's VTable and invokes slot +0x0C, returning that method's EAX result unchanged.
- The object at [self+0x24] is separate from the confirmed IIPEditor interface at [self+0x28]. Its type, construction/assignment sites, reference-count lifetime and the meaning of its +0x0C result remain unknown.

The constructor TGearImgProc.$bctr at 0x004EEC7C was inspected. Its body obtains and compares image/processor-related objects through fields +0x28 and temporary interfaces; it does not visibly initialize [self+0x24] in the bounded constructor body. This is not proof that the field is never initialized: it may be populated later through a setter or inherited initialization.

Address correction: the TD32 procedure TGearImgProc.GetParentHandle is at 0x004EF1B4, not 0x004EE1B4. The latter address is not its entry point. The CI target has been corrected accordingly.

### Immediate next work

1. Find all code references that write to or clear [TGearImgProc+0x24], then identify the source interface and its implementation via RTTI.
2. Trace the corrected GetParentHandle method and its callers to determine which window handle/object is supplied to the scanner path.
3. Recover the exact IG_scan_pages prototype from the matching deployed GEAR32PD binary/SDK; keep its argument values unnamed until then.
4. Revalidate the two reported IG_scan_source_select callsites against raw instructions and the IAT.

Confidence: VMT slot identity, the HasError branch and the returned-value flow into IG_scan_pages are high confidence. The interface stored at +0x24, the semantics of its method result, and GEAR argument meanings remain unresolved.

## Run 64 — تعیین مسیر ثبت interface در فیلد +0x24

- گزارش Run 64 اسلات صفر VMT را به `TGearImgProc.HasError` متصل می‌کند. این متد فیلد `[self+0x24]` را بررسی می‌کند و در صورت وجود، slot `+0x0C` رابط ذخیره‌شده را فراخوانی می‌کند.
- مقدار برگشتی HasError در `SelectScanner` به یکی از آرگومان‌های `IG_scan_pages` تبدیل می‌شود؛ بنابراین هنوز باید نوع رابط و قرارداد متد `+0x0C` آن مشخص شود.
- فیلد `+0x24` مستقل از `IIPEditor` در `+0x28` است. در constructor بررسی‌شده، مقداردهی مستقیمی برای `+0x24` دیده نشده؛ این فقط نبود write در بدنه محدودشده constructor را ثابت می‌کند، نه نبود setter یا مقداردهی بیرونی.

### کار بعدی
1. استخراج تمام write/readهای offset `+0x24` در کل BPL، نه فقط متدهای شناخته‌شده کلاس.
2. ردیابی `GetParentHandle` و callerهایش برای یافتن منبع handle/context اسکن.
3. تحلیل آرگومان‌های stack در `IG_scan_pages` با تطبیق دقیق نسخه GEAR32PD؛ هیچ enum یا معنی عددی بدون prototype قطعی نام‌گذاری نشود.
4. بازبینی callsiteهای `IG_scan_source_select` با تطبیق آدرس thunk و IAT.


## Run 64 — قرارداد رفتاری interface ذخیره‌شده در فیلد +0x24

بازخوانی همه referenceهای offset `0x24` در محدوده متدهای TD32 کلاس `TGearImgProc` سه مسیر مستقل را نشان می‌دهد:

| متد TGearImgProc | آدرس | فراخوانی روی interface در `[self+0x24]` | نتیجه قابل اثبات |
|---|---:|---|---|
| `HasError` | `0x004EF1C4` | VTable `+0x0C` | مقدار برگشتی interface را بدون تغییر برمی‌گرداند؛ در حالت nil مقدار صفر |
| `GetErrorCode` | `0x004EF070` | VTable `+0x10` | مقدار برگشتی را به‌عنوان error-code candidate عبور می‌دهد؛ معنای دقیق هنوز نیازمند callsite است |
| `SaveAsType` | `0x004EF3D0` | VTable `+0x18` | dispatch مربوط به ذخیره/تعیین نوع خروجی؛ جزئیات آرگومان‌ها هنوز باید استخراج شود |

این سه dispatch نشان می‌دهند فیلد `+0x24` یک مرجع polymorphic/interface است که در چند مسیر خطا و خروجی استفاده می‌شود؛ اما نام interface یا کلاس پیاده‌ساز هنوز از RTTI متصل نشده است. گزارش field scan، referenceهای offset `0x24` در این سه متد را نشان می‌دهد ولی چون base register در همه توابع الزاماً Self نیست، صرف تطبیق displacement به‌تنهایی اثبات write/lifetime نیست.

در گزارش Run 64، constructor `TGearImgProc` در محدوده بررسی‌شده write مستقیمی به `+0x24` نداشت. بنابراین گام بعدی، استخراج کامل بدنه `SetForceSinglePage` و callsiteهای `GetErrorCode/SaveAsType`، سپس ردیابی setter یا مقداردهی interface است. تا آن زمان نام‌هایی مثل `IScanner` یا `IScanProvider` برای این interface استفاده نمی‌شود.


## Run 68 — editor return path and Gear VMT dispatch (2026-11-11)

Run 68 (43005618825; artifact 13847708592) completed successfully. The artifact confirms the first three TGearImgProc VMT entries at VMT 0x004EE074:

| Slot | Target | Symbol |
|---|---:|---|
| +0x00 | 0x004EF1C4 | HasError |
| +0x04 | 0x004EEB60 | CheckOutputParameter |
| +0x08 | 0x004EF9CC | SelectScanner |

The HasError body reads [self+0x24]; nil returns zero, otherwise it calls the referenced object's VTable +0x0C and returns EAX. Its return is pushed as one of the stack arguments immediately before the IG_scan_pages thunk call. This proves the dataflow but not the runtime type or meaning of the referenced object/result. It is distinct from the IIPEditor interface at [self+0x28].

The IIPEditor implementation body at 0x004F1158 (GetModalRresult) calls 0x004049CC, which is independently resolved as vcl230.bpl!TWinControl.GetHandle. Consequently, the symbol name alone is not enough to describe the return as a modal result; the actual code path reaches the VCL window-handle getter. Hello at 0x004F1164 returns [self+0x42C]. Initial stores its TImageProcessor argument at [editor+0x408], copies [editor+0x3C4] into [processor+0x1C], and then invokes additional editor/control helpers. btnRegisterClick uses the stored processor and branches on its action parameter; its full workflow still needs to be correlated with the form state and callbacks.

A new inconsistency was found: TGearImgProc.SetEditorForm calls interface VTable offset +0x20 on [self+0x28], while the previous special IIPEditor report stopped after +0x18. The next CI run expands the interface dump to 12 slots to resolve this missing method rather than assuming the four previously listed methods are the whole contract.

### Next probes

1. Decode IIPEditor VTable slots +0x1C and +0x20, especially the method invoked by SetEditorForm.
2. Inspect TfrmScanError VMT and its slot +0x0C as a candidate for the object stored at TGearImgProc+0x24; this is a candidate only, not an identification.
3. Resolve the complete stack argument construction to IG_scan_pages and match it to the exact deployed GEAR32PD ABI before assigning names or constants.
4. Trace editor registration/close paths to establish interface AddRef/Release and lifetime.

**Confidence:** VMT slot targets, the HasError field access and return-value flow, the IIPEditor method body reaching TWinControl.GetHandle, and the Initial field writes are high-confidence static findings. The +0x24 object's class/interface, the fifth IIPEditor method, and GEAR argument semantics remain unresolved.


## Run 69 — correction: IIPEditor is not the object at TGearImgProc+0x28

A fresh cross-check of the complete ShowEditor and SetEditorForm bodies supersedes the earlier field attribution in Run 62/63/68.

- SetEditorForm has the TD32 signature accepting DelphiInterface<IIPEditor>. Its incoming EDX value is copied to ESI and stored at [self+0x34] (instruction 0x004EFFE3). It then loads [self+0x28] and calls that object's VTable +0x20. Therefore this +0x20 dispatch is not a call through the IIPEditor vtable.
- ShowEditor stores its EDX argument at [self+0x28] (0x004F018D), invokes that object's VTable +0x04 (0x004F0197), and then clears [self+0x34] (0x004F01AC).
- SelectScanner clears [self+0x34] at 0x004EF9FC, then loads [self+0x28] and invokes VTable +0x0C and +0x04 at several points. The calls previously attributed to IIPEditor were therefore made on the separate +0x28 object.
- The IIPEditor RTTI identification itself remains valid: IID 7834c511-9078-411c-ab08-8b15ef1fd700, implemented by TfrmSimpleImageEditor at interface offset 0x430. What is withdrawn is the claim that this interface is stored at +0x28 or that SelectScanner's +0x0C call reaches GetModalRresult.
- The direct store to +0x34 is strong evidence that SetEditorForm writes the IIPEditor parameter there. However, other code (including SavePage) also reads +0x34 in a numeric comparison, and SelectScanner zeroes it. Do not finalize the field's semantic type/lifetime until the complete +0x34 cross-reference report resolves this apparent state/typing conflict.

### Revised object map

| TGearImgProc offset | Current evidence | Status |
|---|---|---|
| +0x24 | Read by HasError/GetErrorCode/SaveAsType; virtual dispatch through referenced object's +0x0C/+0x10/+0x18 | Unidentified error/result interface candidate |
| +0x28 | Assigned by ShowEditor; methods +0x00/+0x04/+0x0C/+0x20 used by Gear methods including SelectScanner | Separate processor/context object; exact class unresolved |
| +0x34 | SetEditorForm stores its IIPEditor argument here; ShowEditor/SelectScanner clear it; SavePage also reads it as numeric state | Conflicting use; investigate before naming field |

The new CI workflow scans displacements +0x28 and +0x34 across all TD32-bounded procedures and adds TImageProcessor to VMT discovery. The class name TImageProcessor appears in the editor interface signatures, but the actual runtime class for the +0x28 object is not yet confirmed.

### Next probes

1. Inspect the full +0x28 and +0x34 reference reports, class VMT candidates and the caller of ShowEditor.
2. Resolve the object passed to ShowEditor and its VTable slots +0x00, +0x04, +0x0C and +0x20.
3. Reconcile why SetEditorForm stores an IIPEditor pointer at +0x34 while SavePage treats +0x34 as numeric state and SelectScanner clears it.
4. Keep the +0x24 error/result interface, +0x28 processor/context object and IIPEditor parameter separate until a complete field/lifetime proof exists.

**Confidence:** The stores/loads at +0x28/+0x34 and the fact that SelectScanner's calls are through +0x28 are high-confidence static findings. The runtime class of +0x28 and semantic meaning/lifetime of +0x34 remain unresolved.


## Run 70 — IG_scan_source_select callsites confirmed (2026-11-11)

The full TD32-bounded method disassembly in artifact 13848571670 (run 43006403083) validates both previously disputed raw callsites. The import-caller report maps GEAR32PD.DLL!IG_scan_source_select to IAT 0x00630CE8 and thunk 0x004AFF28, and lists exactly these two callers:

| Caller | Callsite | Verified argument dataflow |
|---|---:|---|
| TfrmGScanPreview.ShowCropRectangle | 0x0061E3DF | Calls VCL TWinControl.GetHandle at 0x004049CC, pushes the returned window handle, then calls IG_scan_source_select. |
| TGearImgProc.SetCurrentPage | 0x004EFF83 | Calls TGearImgProc VMT slot +0x00, pushes its EAX return, then calls IG_scan_source_select. |

The correct mapped entry of TfrmGScanPreview.ShowCropRectangle is 0x0061E3C8 (not 0x0061D3C8). Its 0x28-byte body gets the form handle twice, calls helper 0x0045574C between those reads, and passes the second handle to IG_scan_source_select. The workflow target-address trace was corrected to 0x0061E3C8.

For TGearImgProc.SetCurrentPage, the bounded body at 0x004EFF6C calls helper 0x004F0258, loads the TGearImgProc VMT and invokes slot +0x00, then pushes that result into IG_scan_source_select. Slot +0x00 resolves to TGearImgProc.HasError at 0x004EF1C4. This establishes a second, distinct source-selection argument path; it does not establish what the returned value means to ImageGear.

This supersedes the earlier wording that the two IG_scan_source_select attributions were merely suspect. They are now confirmed by the actual CALL instructions, their import thunk, and the IAT mapping. Keep their arguments separate: one is a native window handle; the other is the return value of the Gear object's HasError dispatch.

### Next probes

1. Identify the object passed to ShowEditor and stored at TGearImgProc+0x28, including its runtime VMT and virtual slots.
2. Trace helper 0x004F0258 and the object/method used to produce the HasError result passed to IG_scan_source_select.
3. Trace helper 0x0045574C and determine what ShowCropRectangle prepares between its two GetHandle calls.
4. Recover the exact GEAR32PD prototype before naming the IG_scan_source_select argument types or behavior beyond the observed handle/result dataflow.


## Run 71 — field +0x34 is page state; symbol/ABI mismatch at 0x004EFF94

The complete displacement scan from artifact 13848168639 (run 43006657606) resolves the apparent +0x34 conflict from Run 69. The earlier interpretation that SetEditorForm stores an IIPEditor pointer at +0x34 is withdrawn.

- At 0x004EFF94, the TD32 name/signature is SetEditorForm(DelphiInterface<IIPEditor>), but the machine code treats EDX/ESI as a small integer: it compares it with 1, compares it with [self+0x30], and stores it into [self+0x34]. This is consistent with a page-index setter, not an interface assignment. The symbol/signature association is therefore not trusted for this routine until callers and metadata are reconciled.
- The write at 0x004EFFE3 is the current-page value. SavePage reads [self+0x34] and compares it against the page number being saved. ReNewPageCount and SaveCPinMultiPageFile also read +0x34. SelectScanner and ShowEditor clear +0x34. These accesses support +0x34 = current-page state.
- The range check at 0x004EFFB2–0x004EFFBA compares the input against 1 and [self+0x30]. This supports +0x30 = page-count/upper-bound state.
- ShowEditor writes its EDX argument to [self+0x28], calls that object's VTable +0x04, and clears +0x34. SelectScanner subsequently calls methods at +0x0C and +0x04 through the same +0x28 object. The exact runtime class of +0x28 remains unresolved. Adding TImageProcessor to the VMT scan found no VMT candidate in this BPL; the type name appears in method signatures, but that does not prove the runtime object class is defined in this package.
- The code at 0x004EF048, despite its TD32 name GetEditorModalResult, is a compact DL-to-constant mapper: DL=0 returns 0; DL=1 returns 0x80028; DL=2 returns 0x15; DL=3 returns 2; other values return 0. It does not query IIPEditor or a form's ModalResult. ShowEditor passes the value returned by helper 0x004ECF30 into this mapper and stores the mapped result at [self+0x14].

### Revised field map (current best evidence)

| Offset | Best-supported interpretation | Evidence/status |
|---|---|---|
| +0x14 | mapped result/status value | ShowEditor stores result of 0x004EF048 |
| +0x24 | error/result polymorphic reference | HasError/GetErrorCode/SaveAsType dispatch through it; concrete type unknown |
| +0x28 | processor/context object | assigned by ShowEditor; VTable slots +0,+4,+0x0C,+0x20 used; runtime class unresolved |
| +0x30 | page-count / maximum-page state | range check in 0x004EFF94; further full cross-reference requested |
| +0x34 | current-page state | written by integer-like setter body, cleared by SelectScanner/ShowEditor, read by SavePage and ReNewPageCount |
| +0x38 | string/object state returned by +0x04/+0x20 calls | helper 0x004012F8 assigns local result here; exact type to be checked with expanded scan |

This section supersedes Run 69's statement that +0x34 stores the IIPEditor parameter. The IIPEditor RTTI record and its implementation table on TfrmSimpleImageEditor remain valid, but its association with TGearImgProc fields is not established by the present code.

### Next probes

1. Inspect the new +0x30 and +0x38 reports and full ReNewPageCount/SaveCPinMultiPageFile bodies.
2. Find all callers of 0x004EFF94 and reconcile the TD32 signature mismatch with actual caller argument setup.
3. Identify the runtime type passed to ShowEditor and recover the VTable layout for its +0,+4,+0x0C,+0x20 methods.
4. Trace 0x004ECF30 and 0x004F0258 to understand the processor/context object's values and its use in IG_scan_pages / IG_scan_source_select.

**Confidence:** The integer comparisons and +0x34 page-state dataflow are high-confidence machine-code findings. The method's correct source-level name, the exact +0x28 class, and +0x38 type remain unresolved.
