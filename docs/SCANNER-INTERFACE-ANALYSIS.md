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


## Run 72 — processor object, page setter callers and helper semantics

Run 72 (43007155812; artifact 13848178593) completed successfully. The new direct-call xref report resolves the callers of 0x004EFF94 and clarifies the page-state fields.

### 0x004EFF94 is called as an integer page setter

The TD32 record labels 0x004EFF94 as TGearImgProc.SetEditorForm with a DelphiInterface<IIPEditor> parameter, but all four direct callers pass small integer page values in EDX:

| Caller | Callsite | EDX value/dataflow |
|---|---:|---|
| TGearImgProc.SaveCPinMultiPageFile | 0x004EF498 | Loop page index, starting at 1 |
| TGearImgProc.Flip | 0x004F01FD | Constant 1 |
| TfrmSimpleImageEditor.doCommand | 0x004F1D21 | UI page index plus 1; EAX is [editor+0x408] |
| ScanCommandUnit.Finalization | 0x004F333A | Constant 1 |

The body compares EDX against 1 and [self+0x30], writes the value to [self+0x34], then calls VTable +0x20 on [self+0x28] and stores a returned value/string-like object at [self+0x38]. The machine-code behavior is a page-selection/update operation. The TD32 symbol name/signature is not reliable for this routine and is superseded by the direct caller evidence.

### Refined field/object map

- +0x28 is a class-like processor/context object with a VMT. Gear code calls its slots +0, +4, +0x0C, +0x14, +0x1C and +0x20 in different paths. ShowEditor stores the supplied object here. SaveCPinMultiPageFile invokes its +0x1C method and then releases/replaces the reference. The exact runtime class is not resolved; TImageProcessor is a candidate association from editor signatures, but the VMT scan found no local TImageProcessor VMT candidate.
- Helper 0x004ECF30 is a simple byte getter: movzx EAX, byte ptr [EAX+4]; ret. It is used on the +0x28 object in TGearImgProc constructor, ShowEditor and SaveCPinMultiPageFile. It is not an editor-modal-result call.
- +0x30 is the page-count/upper-bound field. Rotate90 writes the computed page count here; the 0x004EFF94 range check and SavePage/SaveCPinMultiPageFile read it.
- +0x34 is the current-page index. The 0x004EFF94 body writes it, SavePage compares it to the requested page, ReNewPageCount forwards it to 0x004EF240, and ShowEditor/SelectScanner reset it.
- +0x38 is a string/object state populated by helper 0x004012F8 from values returned through the +0x28 object's virtual methods; its exact type remains unresolved.
- +0x24 remains a separate error/result interface-like field, used by HasError/GetErrorCode/SaveAsType.

### Helper corrections

- 0x004EF048, named GetEditorModalResult by TD32, maps DL to constants: 0→0, 1→0x80028, 2→0x15, 3→2, and other values→0. It is a status/result mapper, not a query to IIPEditor or a form's ModalResult.
- 0x004F0258 is called from SelectScanner and SetCurrentPage. Its entry calls the processor object's VMT slot +0, then passes the result to helper 0x00402AE0. Full routine semantics still need a wider disassembly.
- 0x0045574C is a shared form/handle helper called from ShowCropRectangle, GearErrorHandling and unrelated forms. Its first instructions use a window handle and call 0x00404D5C; do not treat it as a scanner callback.

This supersedes the Run 71 provisional statement that +0x28 was merely an unidentified interface pointer and further confirms +0x30/+0x34 as page count/current page. It also withdraws any use of the TD32 SetEditorForm parameter signature as proof of an IIPEditor assignment to +0x34.

### Next probes

1. Resolve the parent VMT 0x004EDE18 and determine whether TImageProcessor is an ancestor or external class.
2. Expand disassembly for 0x004F0258, 0x004ECF38 and 0x0045574C; correlate their object fields and return values.
3. Trace the VTable slot +0x20 on the +0x28 processor object and identify the value stored at +0x38.
4. Trace the IIPEditor interface's actual registration/lifetime separately from the TGearImgProc page-state methods.


## Run 73 — NotifyEditor and the +0x38 output path

The full TD32-bounded disassembly in artifact 13849710458 identifies 0x004EF240 as TGearImgProc.NotifyEditor (size 0x190), not an anonymous helper. ReNewPageCount calls it with [self+0x34], and the 0x004EFF94 page-index routine calls it after updating the current page.

NotifyEditor uses the notification value in EDX, validates the active ImageGear handle at [self+0x10], and obtains a file/path value from [self+0x38]. It then calls the IG_save_FD thunk 0x004AFE98 twice with the active image handle and notification/page arguments. After successful delivery it checks the processor's virtual CheckOutputParameter slot (+0x04), performs further editor notification/control work, clears the dirty flag [self+0x54], and finally calls ReloadPage and GetImageResolution. This is a concrete image-to-editor update path, not scanner acquisition itself.

The +0x38 field is therefore best interpreted as a path/string-like value used by SavePage, SaveToFile, ScanToFile, SaveCPinMultiPageFile and NotifyEditor. In the page-index routine it is assigned from the return value of the +0x20 method on the +0x28 processor object via helper 0x004012F8. The exact string type and whether the path is per-page or a temporary descriptor path still require the helper/prototype analysis.

Helper 0x004ECF38 copies the value at [object+0x08] through helper 0x00401240 into an output local; it is called from the TGearImgProc constructor and SaveCPinMultiPageFile. Together with 0x004ECF30 (byte getter at [object+0x04]), this establishes that the +0x28 processor object exposes at least byte state at +4 and a value at +8, in addition to the virtual methods previously traced.

The VMT-parent inspection at 0x004EDE18 did not validate the standard Delphi header offsets (self pointer/class-name/instance-size fields are not plausible). Do not label this parent as TImageProcessor yet. The next run traces the actual method targets found in its leading slots; only those code bodies, not the malformed header interpretation, should be used to identify it.

### Updated object/page map

| Offset | Current interpretation | Evidence |
|---|---|---|
| +0x10 | active ImageGear image handle | NotifyEditor validates and saves this handle |
| +0x24 | separate error/result interface-like reference | HasError/GetErrorCode/SaveAsType dispatch |
| +0x28 | processor/editor-context object | byte getter +4, value getter +8, virtual methods +0/+4/+0x0C/+0x14/+0x1C/+0x20; exact type unknown |
| +0x30 | page count | Rotate90 computes and writes it; page-index range check reads it |
| +0x34 | current page index | page setter writes; SavePage/ReNewPageCount/NotifyEditor read it |
| +0x38 | output path/string-like state | passed into file/FD save paths and assigned from +0x28 virtual +0x20 result |

**Confidence:** NotifyEditor identity, its calls to IG_save_FD, and the +0x34/+0x38 dataflow are high-confidence static findings. Exact GEAR FD semantics, path encoding and the runtime class of +0x28 remain unresolved.


## Run 74 — correct FD API identities and image-format field

A final import-thunk cross-check corrects the Run 73 interpretation. Thunk 0x004AFE98 is GEAR32PD.DLL!IG_load_FD (IAT 0x00630D2C), not IG_save_FD. Thunk 0x004AFEA0 is GEAR32PD.DLL!IG_save_FD (IAT 0x00630D28).

### Verified argument order

The SavePage call at 0x004EF60B pushes five arguments in reverse order matching the documented IG_load_FD prototype:

- fd = ESI (opened descriptor for the file/path in [self+0x38])
- lOffset = 0
- nPage = current loop page [ebp-0x10]
- nTile = 0
- lphIGear = address of local HIGEAR handle [ebp-0x14]

The subsequent call at 0x004EF64E matches IG_save_FD:

- hIGear = local handle [ebp-0x14]
- fd = ESI
- nPage = current loop page
- nReserved = 0
- lFormatType = [self+0x14]

NotifyEditor calls IG_load_FD twice, at 0x004EF2D3 and 0x004EF2F9. Both write to [self+0x10]; the first uses EDX as nPage and the second uses nPage=1. In both calls lOffset=0 and nTile=1. Therefore NotifyEditor reloads image data from an already-open file descriptor into the active HIGEAR handle; it does not call IG_save_FD. This supersedes Run 73's statement that NotifyEditor saves through IG_save_FD.

### Revised +0x14 and +0x38 meanings

The fifth argument to IG_save_FD is lFormatType, and SavePage passes [self+0x14] there. Thus +0x14 is the ImageGear save-format/compression constant, not a generic status value. The routine at 0x004EF048 maps the byte selector DL to the constants 0, 0x80028, 0x15 and 2 (other values map to 0); ShowEditor stores that result at +0x14. This is best described as a format-code mapper, not GetEditorModalResult.

The +0x38 value is used to obtain/open the file descriptor consumed by IG_load_FD and IG_save_FD. It is therefore a path/stream backing value, likely a string path, but its exact Delphi string type and file-open mode remain to be proven from the helper and the caller.

The observed call stacks match the public ImageGear prototypes documented by Accusoft:

- IG_load_FD(fd, lOffset, nPage, nTile, lphIGear): https://help.accusoft.com/ImageGear/v18.7/Linux/IGDLL-19-566.html
- IG_save_FD(hIGear, fd, nPage, nReserved, lFormatType): https://help.accusoft.com/ImageGear/v21.0/Linux/IGDLL-19-684.html

These documents are corroborating references for the argument layout only. They are not proof that EMWAT's deployed GEAR32PD.DLL is v18.7 or v21; the exact 32-bit Windows DLL build and matching headers remain unidentified.

### Revised page/image workflow

1. The processor stores page count at +0x30, current page at +0x34, format code at +0x14, and a file/path backing value at +0x38.
2. SavePage opens the backing file, loads a requested page from its descriptor into a temporary HIGEAR handle with IG_load_FD, then writes the edited handle back into the same descriptor/page position with IG_save_FD and the selected format code.
3. NotifyEditor reopens/uses the descriptor and loads the requested page into the active HIGEAR handle at +0x10, then performs editor/page refresh and clears the dirty flag.

This is strong evidence that EMWAT's page editor uses a descriptor-backed multipage file as an intermediate page store. A Linux implementation should model that with an explicit page store and file/stream API, not reproduce Windows file descriptors or HIGEAR handles.

**Confidence:** Import identities and stack argument order are high-confidence. Prototype correspondence is strong but version-qualified. The exact +0x38 string type, file open flags, and semantics of the four format constants remain unresolved.


## Run 75 — IG_scan_pages argument provenance and parent-VMT limitation (2026-11-11)

Workflow run 43008058751 completed successfully (artifact 13850020148). The extended traces did not identify the runtime class behind parent pointer 0x004EDE18: the six sampled targets (0x004EDE70, 0x004EDE7C, 0x004EDF68, 0x004EDE8E, 0x004EDEAC, 0x004EDEC2) do not resolve to TD32 procedure ranges, and the standard Delphi header interpretation remains implausible. Do not label this parent as TImageProcessor or infer virtual method names from these traces.

### Full IG_scan_pages caller argument flow

The bounded procedure bodies expose two distinct four-argument call patterns to thunk 0x004AFF30 (GEAR32PD.DLL!IG_scan_pages):

| Caller | Arg 1 | Arg 2 | Arg 3 | Arg 4 | Return |
|---|---|---|---|---|---|
| TfrmGScanPreview.SelectScanner (0x0061DEF4) | HWND from TWinControl.GetHandle | converted path/string from [self+0x458] | 0x28 or 2 | 1 | not consumed immediately |
| TGearImgProc.SelectScanner (0x004EF9CC) | return from VMT slot +0 (HasError) | converted value from [self+0x28] virtual +0x0C | mapper 0x004EF048 (0, 0x80028, 0x15, or 2) | byte [ebp+8] | stored in [self+0x4C] |

The Gear path's first argument is returned by TGearImgProc.HasError (0x004EF1C4), which dispatches through slot +0x0C of the still-unidentified object at [self+0x24]. This is value provenance only; it does not establish that the value is a window handle. The preview path demonstrably passes an HWND. Preserve this discrepancy rather than normalizing both callers to a guessed parameter type.

The decorated TD32 symbol is @Gear@IG_scan_pages$qqsp6HWND__pxcuio. It is useful signature evidence but does not resolve all four stack values. Public Accusoft material describes the related IG_TWAIN_scan_pages family, but does not prove that IG_scan_pages in this deployed GEAR32PD.DLL is ABI-identical. Do not equate the APIs or name numeric options without the matching binary/header set.

### IG_scan_source_select discrepancy retained

TfrmGScanPreview.ShowCropRectangle passes the HWND returned by TWinControl.GetHandle. TGearImgProc.SetCurrentPage passes the result of VMT slot +0 (HasError). The decorated symbol @Gear@IG_scan_source_select$qqsp6HWND__ names an HWND-like parameter, but the second caller's value provenance is different. This remains an unresolved static type/dataflow discrepancy.

### Next probes

1. Find every write, clear, and reference to [TGearImgProc+0x24] and identify its runtime interface.
2. Resolve the [self+0x28] object's class/VMT using constructor/setter callsites and a validated VMT header; do not rely on parent pointer 0x004EDE18.
3. Obtain the exact GEAR32PD.DLL build or matching import library/header to settle both scanner prototypes.
4. Keep Linux acquisition based on SANE; recovered Windows values are behavioral clues, not a Linux ABI or SANE option map.

Confidence: callsites, import thunk identity, and argument value provenance are high-confidence. Semantic argument types, exact prototypes, option meanings, and the parent runtime class remain unresolved.


## Run 76 — identify the +0x24 interface as IIPEditor and resolve HWND flow (2026-11-11)

Workflow run 43027580174 completed successfully (artifact 13857623235). This run adds the missing assignment/caller evidence for the interface stored at [TGearImgProc+0x24].

### Why +0x24 is IIPEditor

- The setter-like routine at 0x004F0084 receives an interface pointer in EDX, takes an interface reference, compares it with [self+0x24], assigns it to that field through Delphi's interface-assignment helper, and—when non-null—calls interface VTable slot +0x14 with the TGearImgProc instance.
- A direct caller in TScanCommand.$bdtr (call at 0x004F2233) takes an object pointer in EDX and adds 0x430 before passing it to 0x004F0084. The IIPEditor interface table for TfrmSimpleImageEditor has IOffset 0x430 (1072), so this pointer adjustment matches the actual interface subobject exactly.
- A second direct caller at 0x004F1151 passes nil to the same setter, consistent with clearing/releasing the interface during editor teardown.
- The interface RTTI identifies IID 7834c511-9078-411c-ab08-8b15ef1fd700, implemented by TfrmSimpleImageEditor at VMT 0x004F046C with interface VTable 0x004F03D4 and offset 0x430.

Therefore [TGearImgProc+0x24] is the IIPEditor interface reference. This supersedes earlier Run 63–75 descriptions of +0x24 as an unidentified error/result interface. The TD32 names on wrappers such as HasError, GetErrorCode, SaveAsType and SetForceSinglePage are not reliable semantic labels for these dispatches.

### HWND dataflow now reconciled

- TGearImgProc.HasError at 0x004EF1C4 calls [IIPEditor VTable+0x0C].
- The corresponding TfrmSimpleImageEditor interface entry targets 0x004F1158. Its body calls vcl230.bpl!TWinControl.GetHandle (thunk 0x004049CC) and returns that EAX value.
- Consequently the value returned by the Gear slot +0 dispatch is an HWND, despite the misleading TD32 name HasError.
- This resolves the earlier apparent mismatch: TfrmGScanPreview.SelectScanner passes HWND directly; TGearImgProc.SelectScanner and TGearImgProc.SetCurrentPage obtain the same kind of value indirectly through the IIPEditor interface.
- The two confirmed IG_scan_source_select callsites therefore both pass an HWND-like value; the Gear call obtains it through IIPEditor rather than directly through GetHandle.

### Revised TGearImgProc field map

| Offset | Revised interpretation | Evidence |
|---|---|---|
| +0x24 | IIPEditor interface reference | interface assignment at 0x004F0084; TScanCommand caller adjusts object by +0x430; IID/VTable match |
| +0x28 | separate processor/context object | ShowEditor stores EDX here; virtual slots and +4/+8 fields are used; runtime class still unresolved |
| +0x30 | page count | existing Run 71/72 evidence |
| +0x34 | current page index | existing caller/range-check evidence |
| +0x38 | path/string-like backing state | existing Run 74 descriptor-backed page-store evidence |

The generic RTTI scan also found IImageProcessor type information with a zero IID and no implementing class in the current BPL. It is not evidence that +0x24 stores IImageProcessor; the +0x430 pointer adjustment and concrete IIPEditor interface table provide the stronger match for +0x24.

### Run 77 — IG_scan_pages call-site argument order

The full `TGearImgProc.SelectScanner` body at `0x004EF9CC` confirms the four stack arguments pushed immediately before the call to `IG_scan_pages` at `0x004EFA96`:

1. First argument: HWND, returned by the IIPEditor-backed `TGearImgProc.HasError` virtual slot (+0x0C).
2. Second argument: the scanner/output path obtained from the separate context object at `[TGearImgProc+0x28]` through its virtual slot +0x0C, then passed through RTL helper `0x004012E0`.
3. Third argument: the format code returned by `TGearImgProc.GetEditorModalResult` at `0x004EF048` (this routine is a byte-selector-to-constant mapper, not a modal-result getter).
4. Fourth argument: the byte parameter read from `[EBP+8]` and zero-extended before pushing; likely a Boolean UI/control flag, but its exact caller-level meaning is not yet established.

The return value from `IG_scan_pages` is stored in `[TGearImgProc+0x4C]`, then checked through the processor's virtual `CheckOutputParameter` slot (+0x04). This recovers argument order and HWND provenance, but not the exact C prototype, string encoding, or format-code names.

The TD32 method label `SelectScanner$qqrv` omits parameters that are visible in the machine code: entry EDX is copied to BL, entry ECX is saved as a selector byte, and a further byte is read from `[EBP+8]`. The routine later re-enters itself through VMT slot +0x08 with EDX=1 while preserving the selector and stack byte. This supports treating EDX as an internal re-entry/mode flag and ECX as the format-selector byte, but the exact external caller contract still needs confirmation.

The context object at +0x28 remains distinct from IIPEditor at +0x24. The six attempted parent-VMT slot traces from Run 76 produced non-code-looking disassembly and are not valid evidence for identifying the parent class; keep that parent relationship unresolved.

### Run 78 — TScanCommand state wrapper

The application-side scanner request is mediated by `TScanCommand`, a Delphi class whose candidate instance size is `0x40` bytes (its recovered VMT candidate is not structurally valid, so virtual slots are not assigned from it).

- `DoRequest` writes state byte `[self+0x28]` to `1`, `2`, or `3` on separate request paths.
- `HasError` checks enable byte `[self+0x29]`; if enabled, it queries the nested object at `[self+0x20]`, invokes its virtual slot +0x10, and then calls helper `0x004ECFC8`.
- The result sets `[self+0x28]` to `2` (nested error check true) or `4` (false). This is an application-level state update, not proof that numeric states map directly to success/failure without examining the caller.
- `0x004ECFC8` checks a nested interface-like reference at `[object+0x10]`, invokes VMT slot +0x04 to retrieve an output value, and passes it to a Boolean helper. Exact interface type and helper semantics remain unresolved.

The earlier GetNextPage trace began mid-procedure; the next run adds broader context around its likely entry and the surrounding ScanCommand methods. Do not treat the partial disassembly at `0x004F2600` as a complete method body.

### Remaining work

1. Identify the runtime class and virtual contract of the distinct object at +0x28; do not conflate it with IIPEditor at +0x24.
2. Map IIPEditor slots +0x10, +0x14, +0x18 to their concrete editor methods and actual argument/return behavior; wrapper TD32 names are unreliable.
3. Resolve the exact GEAR32PD.DLL prototypes for IG_scan_pages and IG_scan_source_select. IG_scan_pages argument order is now recovered from the callsite (HWND, path-like value, format code, byte flag), but exact parameter types, encoding, and constants remain unresolved.
4. Continue the native SANE design independently of the Win32 interface layout.

**Confidence:** +0x24 = IIPEditor and the HWND provenance through slot +0x0C are high-confidence cross-checks from the interface RTTI, interface offset, direct callers, and method body. The runtime class at +0x28 and the exact GEAR scanner ABI remain unresolved.


## Run 77 — trace the processor context source (+0x28) (2026-11-11)

Workflow run 43029566665 completed successfully (artifact 13861172120). The field scan for TScanCommand+0x20 shows:
- DoRequest reads [self+0x20] and passes it in EDX to TGearImgProc.ShowEditor (call 0x004F237E).
- GetNextPage writes [self+0x20] in three branches at 0x004F2637, 0x004F268B and 0x004F26A9.
- TScanCommand.HasError reads the same field at 0x004F2AD3/0x004F2ADB; Finalization also reads it.

In GetNextPage, the three writes store the return value of helper 0x004EC8B4. The arguments are assembled from the request's mode/format bytes and a string/value produced by helper 0x0044A998. Thus +0x20 is a generated per-request/per-page processing context, not a fixed HWND or the IIPEditor interface.

TGearImgProc.ShowEditor stores the exact pointer received from TScanCommand+0x20 into [TGearImgProc+0x28], then calls that object's virtual slot +4 with an out-string destination; the returned string is copied into [TGearImgProc+0x38]. This confirms that +0x28 is the same context object created by TScanCommand.GetNextPage.

TScanCommand.HasError calls the context object's virtual slot +0x10 and then helper 0x004ECFC8, using the result to update TScanCommand status byte +0x28 (values 2 or 4). The concrete class name and exact virtual method contract remain unresolved; do not assume this is the IImageProcessor interface merely because that interface RTTI exists in the module.

The next probes are the full bodies of 0x004EC8B4 and 0x004ECFC8 plus the complete GetNextPage procedure. Workflow 43030170561 adds those traces.


### Run 79 — ScanCommand constructor and page-context lifecycle

Workflow run 43032078996 succeeded. The aligned constructor trace at 0x004F21F0 shows a base object created by 0x004EEDB4 and stored at [self+0x04], a separately created interface stored at [self+0x24], and another object returned by 0x004EB7F4 stored at [self+0x34] before virtual slot +0xB8 is called. The +0x24 interface path is consistent with the previously confirmed IIPEditor ownership; the +0x34 dependency remains unidentified.

The useful GetNextPage block begins around 0x004F25CC, not at the earlier requested trace boundary. It uses two state bytes at [self+0x1D] and [self+0x1E]. Helper 0x004EC8B4 creates the per-page processing context stored at [self+0x20], using the mode/selector byte pair. In one branch, a mode value of 2 is remapped to factory mode 3; otherwise the current mode is passed through. A helper call through 0x00401398 with constant argument 1 checks request/page data; a positive result changes [self+0x1E] to 2, after which HasError is invoked. A later block rebuilds [self+0x20] from the updated state-byte pair. Thus +0x20 is a state-dependent processing context, not a single immutable object for the entire command lifetime.

The broader context probes at 0x004F2250 and 0x004F25C0 begin mid-instruction, and the 0x004F2A80 probe is not aligned to code. They are not used to infer complete method boundaries. Run 80 adds aligned probes at 0x004F2274, 0x004F25CC, 0x004F26F2, 0x004F27C4, and 0x004F29E0.


### Run 80 — ScanCommand status dispatch and context hand-off

Workflow run 43033266952 succeeded; artifact 13861452924 was inspected.

- The aligned GetNextPage trace beginning at 0x004F25CC first loops over four candidate values and stores the matching index in [self+0x1D]. This field therefore participates in a four-way selection step and should not be described as a static mode alone.
- A helper invoked through 0x00401398 with constant argument 1 returns a numeric result; a positive result sets [self+0x1E] to 2. The method then creates a fresh context through 0x004EC8B4 using both state bytes, stores it at +0x20, and invokes HasError.
- The continuation passes the context pointer at +0x20 to 0x004F0174. It copies the packed state-byte pair into words at offsets +0x55 and +0x57 of the base object at [self+0x04], then calls 0x004F22E4 and 0x004F2B18.
- The subsequent dispatcher branches on status byte [self+0x28], distinguishing values 1 through 4. In the status=2 branch it reads the current +0x20 context through 0x004ECE2C and passes the resulting value to 0x004735C4. Status 3 and 4 take separate preparation paths.
- The dispatcher then invokes virtual slots +0xB8 and +0xB4 on the dependency stored at +0x34, and slot +0x08 plus additional helpers on the context at +0x20. Exact class identities and virtual contracts remain unresolved.
- The requested probes at 0x004F2274 and 0x004F29E0 did not decode valid instructions. They are not accepted as confirmed DoRequest or standalone request-helper entries. The earlier 0x004F2250 probe also begins inside an instruction/epilogue.
- The dispatch trace at 0x004F27C4 ends at 0x004F28C0; the remaining branch body and targets 0x004F22E4 and 0x004F2B18 need further inspection.

Next: probe 0x004F2278 and 0x004F28C0, then inspect 0x004F22E4 and 0x004F2B18 and correlate status transitions with DoRequest/HasError. Avoid naming ambiguous code ranges as complete methods until their true entries are recovered.


## Run 81 — ScanCommand continuation callback and status transition (2026-11-12)

Workflow run `43036386819` completed successfully (artifact `13863571297`). The added traces extend the helper beginning at `0x004F22E4` through its callback-dispatch branch and cleanup.

### Correction — helper identity and callback interpretation

The TD32 symbol map in the same Run 81 artifact identifies `0x0044ABE4` as `@Emwat@Sys@RemoveTempFiles$qqrv`. Its direct callsite at `0x004F23FC` is also reached from `TfrmSimpleImageEditor.ToggleCropMode` at `0x004F18C4`, which independently confirms that this is a shared temporary-file cleanup routine, not a scan callback dispatcher.

The probes at `0x004F2454`, `0x004F2474`, and `0x004F2490` decode as invalid x86 instruction streams and are inside/adjacent to the Delphi method's exception/finalization data region. They must not be treated as executable callback targets or as proof of a callback-record ABI. The previous subsection's wording about callback-record construction and callback targets was therefore too strong and is superseded by this correction.

What is directly established at the ScanCommand callsite is narrower: it prepares a local managed value through `0x00401370`, loads a 16-bit constant from `0x004F2554`, sets a byte argument to 3, calls `RemoveTempFiles`, and compares the returned EAX with 6. If equal, it invokes context VMT slot `+0x1C` and re-enters `0x004F22E4`; otherwise it stores internal status 3. The meaning of return value 6 and the exact argument contract of `RemoveTempFiles` remain unresolved pending the new helper traces.

The same cleanup routine is called by `TfrmSimpleImageEditor.ToggleCropMode`; therefore it is a shared system utility and not scanner-specific. Its internal loop appears to enumerate a supplied collection and perform object/file-related operations, but the exact deletion/filter semantics are not assigned until its helper calls and string arguments are resolved.

### Newly confirmed control flow

- The helper first checks the global/context condition through `0x004F2B18`; a true result exits through the exception-safe cleanup path.
- It reads the nested context at `[ScanCommand+0x20]`, obtains a byte from `[self+0x18]`, calls the base object's VMT slot `+0x08`, and passes the resulting selector to `0x004F0160` with mode `0x64`.
- The result switch has three relevant outcomes in this range: result 0 stores status 1; result 1 enters the context/editor hand-off and may store status 2; result 2 stores status 3.
- In the result-1 branch, the helper calls `0x004EEC7C`. If that check is false, status 1 is stored. If true, `0x004F32F4` is called with an output pointer; a true return stores status 2.
- If `0x004F32F4` returns false, the code builds a callback/record structure using code pointers `0x004F2454` and `0x004F2474`, a record/descriptor address `0x004F2490`, and constant data at `0x004F2554`. It passes the constructed record through helper `0x00401370`, then calls `0x0044ABE4` with a selector value of 3.
- The return from `0x0044ABE4` is compared with 6. When equal, the current context's VMT slot `+0x1C` is invoked and `0x004F22E4` is called again, forming a repeat/continuation path. Otherwise the status byte `[self+0x28]` is set to 3.
- The helper restores the Delphi exception frame and finalizes its local managed values before returning. The cleanup tail at `0x004F298B` is a conventional register/stack epilogue, not a separate processing operation.

### Interpretation boundaries

The control-flow relationship is high-confidence, but the semantic identity of the callback targets, the record layout at `0x004F2490`, the purpose of `0x0044ABE4`, and the meaning of its return value 6 are not yet established. Do not label these as a scanner callback ABI or a particular device event until their target bodies and callers are traced. The status values 1–4 remain internal state codes, not user-facing success/error enums.

### Next probes

Trace callback targets `0x004F2454`, `0x004F2474`, `0x004F2490`, the helper `0x0044ABE4`, and the exception/finalization target around `0x004F2440`. Then correlate their callers with the state transition at `[self+0x28]`.

**Confidence:** the branch structure, callback-record construction, comparison with 6, context VMT dispatch, recursive continuation, and status=3 fallback are directly visible in aligned disassembly. Callback semantics and helper contracts remain unresolved.


## Run 82 — بازبینی داخلی RemoveTempFiles و رد برداشت callback (2026-11-12)

Workflow run `43157168446` با موفقیت اجرا شد؛ artifact `13916526235` بررسی شد.

### آنچه از بدنه تابع قابل اثبات است

- TD32 آدرس `0x0044ABE4` را `@Emwat@Sys@RemoveTempFiles$qqrv` نام‌گذاری می‌کند؛ با این حال، در بدنه قابل مشاهده، عملیات مستقیم فایل‌سیستمی یا فراخوانی API حذف فایل دیده نمی‌شود.
- تابع یک آرایه/مجموعه از pointerها را از آرگومان‌های stack بازسازی می‌کند، سپس روی یک object تعداد componentها را از طریق thunk `0x004042B4` می‌گیرد و componentها را با `0x004042AC` واکشی می‌کند.
- این دو thunk به‌ترتیب `TComponent.GetComponentCount` و `TComponent.GetComponent` در `rtl230.bpl` resolve می‌شوند.
- در حلقه، تابع componentها را از طریق VCL/RTL دستکاری می‌کند: `0x00404894` به `TControl.SetText` و `0x00404E34` به `TCustomForm.SetFormStyle` resolve می‌شوند. همچنین virtual slotهای `+0x94` و `+0x13C` فراخوانی می‌شوند.
- thunk `0x00404F64` به آدرس `0x0023F672` منتقل می‌شود که خارج از محدوده image فعلی است؛ هویت مقصد هنوز معلوم نیست.
- helper `0x00401128` روی مقادیری که از componentها به دست می‌آیند شرطی را ارزیابی می‌کند و در صورت برقرار بودن، componentهای اضافی از آرایه ورودی به مسیر `SetText` داده می‌شوند. معنای شرط و رشته/متن مورد استفاده هنوز تعیین نشده است.
- تابع در پایان مقدار خروجی را در local ذخیره می‌کند و مسیر exception/finally را اجرا می‌کند؛ trace بعدی انتهای دقیق بدنه و helperهای مدیریت آرایه/رشته را بررسی می‌کند.

### نتیجه و محدودیت

نام نماد به‌تنهایی کافی نیست تا نتیجه بگیریم این routine واقعاً فایل‌های موقت را حذف می‌کند. شواهد فعلی بیشتر با پیمایش و تغییر componentهای VCL سازگارند، اما هنوز ممکن است پاک‌سازی از طریق virtual call یا helper خارج از image انجام شود. بنابراین نه «حذف فایل» و نه «تغییر UI» را به‌عنوان معنای نهایی تابع ثبت نمی‌کنیم.

در caller مربوط به `TScanCommand`، نتیجه `EAX` با عدد 6 مقایسه می‌شود؛ caller دوم در `TfrmSimpleImageEditor.ToggleCropMode` نیز همین مقایسه را انجام می‌دهد. معنای 6 تا زمان شناسایی قرارداد خروجی تابع نامشخص می‌ماند.

### گام بعد

1. ادامه disassembly از `0x0044ACDF` برای بازیابی epilogue و مقدار خروجی.
2. شناسایی helperهای `0x00401128`، `0x004010E8`، `0x004013C8` و `0x00401230`.
3. استخراج تمام callerهای `RemoveTempFiles` و مقایسه آرگومان‌های آن‌ها.
4. شناسایی مقصد خارج از image در `0x0023F672` یا تعیین اینکه این آدرس به package/module بارگذاری‌شده دیگری تعلق دارد.

**Confidence:** هویت دو متد TComponent و دو متد VCL فوق بالا است؛ تفسیر کلی routine و معنای return value 6 هنوز باز است.


## Run 83 — بازسازی قرارداد واقعی RemoveTempFiles (2026-11-12)

اجرای `43158235892` موفق شد؛ artifact `13917012048` بررسی شد. این اجرا برداشت قبلی درباره «حذف فایل موقت» را بیشتر تضعیف می‌کند.

### قرارداد قابل مشاهده در machine code

- تابع `0x0044ABE4` یک آرایه از pointerها را از stack به local stack frame کپی می‌کند و با `System.AddRefArray` و `System.UStrAddRef` مدیریت عمر آرایه/رشته را انجام می‌دهد.
- آرگومان‌های قابل مشاهده شامل object/container در `EAX`، byte در `EDX`، مقدار word در `ECX`، یک UnicodeString در `[EBP+0x0C]` و open-array در `[EBP+0x10]/[EBP+0x14]` هستند. prototype سطح منبع هنوز قطعی نیست.
- تابع با `TComponent.GetComponentCount` و `TComponent.GetComponent` componentها را پیمایش می‌کند.
- برای هر component، `System.IsClass` را با کلاس مرجع global در `[0x62FE28]` اجرا می‌کند. در صورت match، یکی از مقادیر open-array را به `TControl.SetText` می‌دهد.
- سپس مقدار 3 را به `TCustomForm.SetFormStyle` می‌دهد و virtual slot `+0x13C` را روی همان component اجرا می‌کند.
- نتیجه virtual slot در local ذخیره می‌شود و در مسیر خروج، object/local مدیریت‌شده با `TObject.Free` آزاد می‌شود.
- helperهای `0x00401128`، `0x004010E8`، `0x004013C8` و `0x00401230` به‌ترتیب `System.IsClass`، `TObject.Free`، `System.AddRefArray` و `System.UStrAddRef` هستند.
- `0x00404F64` به آدرس خارج از image یعنی `0x0023F672` می‌رود؛ نقش آن و هویت کلاس global هنوز نامشخص است.

### اثر روی تحلیل ScanCommand

- این routine یک helper عمومی مبتنی بر componentهای VCL است؛ callerهای آن در Word، Fax، Scan Error، Simple Image Editor و ScanCommand دیده شده‌اند.
- در callerهای ScanCommand و ToggleCropMode مقدار بازگشتی با 6 مقایسه می‌شود. چون مقدار خروجی در این بدنه از virtual slot `+0x13C` می‌آید، مقدار 6 احتمالاً نتیجه/وضعیت component هدف است؛ معنای دقیق آن هنوز اثبات نشده است.
- نام TD32 یعنی `RemoveTempFiles` را صرفاً نام نماد نگه می‌داریم و رفتار حذف فایل را بر اساس آن پیاده‌سازی نمی‌کنیم.

### گام بعد

1. تعیین نوع کلاس global در `0x62FE28` و مقصد خارج از image در `0x0023F672`.
2. تطبیق callerهای ScanCommand، Scan Error و ToggleCropMode برای استخراج نقش byte mode و open-array.
3. بازگشت به قرارداد context slot `+0x1C` در ScanCommand و معنای retry پس از return=6.

**Confidence:** پیمایش TComponent، type test، SetText، SetFormStyle، virtual slot `+0x13C` و TObject.Free از روی thunkها/دستورها با اطمینان بالا تأیید شده‌اند؛ نوع کلاس، prototype سطح منبع و معنای return=6 هنوز باز هستند.
