# EMWAT Word automation surface — static evidence checkpoint

Date: 2026-11-16  
Repository: `meicamghe/EMWAT-Linux`  
Input artifact: `emwat-bpl-method-invoke-contract`, run `43832553168`, artifact `14208369288`

## New finding: Word is an explicit COM type-library dependency

The TD32 symbol inventory for `analysis-input/EmwatMethods.bpl1` identifies numerous methods with Delphi interface parameters from the `Wordxp` unit, including:

- `FillField`: `Wordxp._Document`, `Wordconfigrequestxml.IXMLFieldType`, `Wordxp.Field`
- `FillImageField`: `Wordxp._Document`, `Wordxp.Field`
- `FillMSWFields`: `Wordxp.Fields`
- `PreparePrintDocument`: `Wordxp._Document`
- `CollectFieldsSets`: `Wordxp._Document` and dynamic arrays of `Wordxp.Fields`
- `FillPrintDocFields`: `Wordxp._Document` and `Wordxp.Fields`
- `WordAppDocumentBeforeClose`, `WordAppDocumentBeforeSave`, `WordAppNewDocument`, `WordAppWindowActivate`, `WordAppWindowDeactivate`, `WordAppDocumentBeforePrint`, and `WordAppDocumentBeforePrintBGPrint`: Word event callback signatures
- `QuitWord` and `SilentSaveEmwatDoc`

This is materially stronger than merely finding the string `WINWORD.EXE`: the compiled type signatures show that the document/field layer is written against Word automation interfaces. Changing Windows file associations cannot replace these interfaces. LibreOffice would need a compatibility bridge implementing the used Word COM interfaces/events, or EMWAT would need an alternate backend that replaces these calls.

## Confirmed procedure index from the TD32 artifact

| Procedure | VA | Size |
|---|---:|---:|
| `LoadDocument` | `0x004B7724` | `0x1360` |
| `OnTmrAutoSave` | `0x004B8A84` | `0x292C` |
| `OnControlerNotify` | `0x004BB3B0` | `0x3C8` |
| `GetDocFieldName` | `0x004BB81C` | `0x954` |
| `FillField` | `0x004BC2C4` | `0x46` |
| `FillImageField` | `0x004BC30C` | `0x674` |
| `GetXmlFieldInfo` | `0x004BCA88` | `0x3190` |
| `GetXmlFieldInfo` overload | `0x004BFC18` | `0x11D` |
| `GetFieldValue` | `0x004BFD38` | `0x77` |
| `SetFieldValue` | `0x004BFDB0` | `0x16C` |
| `FillMSWFields` | `0x004C009C` | `0x250` |
| `AddImagesToDoc` | `0x004C0410` | `0x140` |
| `FillPrintDocFields` | `0x004CB638` | `0x1584` |
| `WordAppDocumentBeforeClose` | `0x004CCBBC` | `0x20C` |
| `WordAppDocumentBeforeSave` | `0x004CD154` | `0x3F8` |
| `WordAppNewDocument` | `0x004CD54C` | `0x474` |
| `WordAppWindowActivate` | `0x004CD9C0` | `0x16C` |
| `QuitWord` | `0x004CDB54` | `0xD8` |
| `WordAppDocumentBeforePrint` | `0x004CDC2C` | `0x404` |
| `WordAppDocumentBeforePrintBGPrint` | `0x004CE030` | `0x1128` |
| `SilentSaveEmwatDoc` | `0x004D23D8` | `0x444` |

## What the current LoadDocument trace does and does not prove

The direct caller scan establishes that `TScanDocument.PerformMethod` calls `TWordViwer.LoadDocument` at `0x005EE961`. The trace also shows extensive interface dispatch and document/template preparation. It does not yet prove the exact COM activation ProgID, the full Word application creation sequence, or the complete set of interface methods used. Those need to be resolved from constructor/event registration routines and the imported/type-library call sites.

## New parallel workflow

`.github/workflows/analyze-word-automation-surface.yml` adds three independent analysis jobs:

1. lifecycle: LoadDocument, timer autosave, controller notification, BeforeClose/BeforeSave, NewDocument, WindowActivate, QuitWord;
2. field mapping: XML field metadata, field value get/set, image fields, Word Fields collection and document fill;
3. save/print: print preparation, field filling for print, foreground/background print callbacks, silent save, VMT/interface inventories.

The workflow has been committed, but its Actions run and artifacts must be checked before treating the new traces as completed.

## Next reverse-engineering targets

1. Trace `TWordViwer.$bctr` (`0x004D08B4`) and `$bdtr` (`0x004D0D24`) for COM object creation and event hookup/teardown.
2. Trace `WordAppDocumentBeforeSave` and `WordAppDocumentBeforeClose` to establish cancel/save behavior and the exact bridge callback sequence.
3. Trace `OnTmrAutoSave` and `OnControlerNotify` separately; do not conflate periodic content sync with the Word BeforeSave event.
4. Resolve Word interface VMT/dispinterface calls in `LoadDocument`, `FillMSWFields`, and `FillPrintDocFields`.
5. Build an API compatibility matrix for a potential LibreOffice bridge only after the exact used methods/events are enumerated.

## Evidence labels

- Static-confirmed: TD32 symbol names, procedure addresses/sizes, type signatures, direct call to LoadDocument.
- Inferred: COM automation dependency and the need for a Word-interface compatibility layer.
- Unknown: exact activation ProgID, all DISPIDs, complete event registration order, and end-to-end response/save protocol.


## Follow-up: LoadDocument lifecycle call sites cross-checked against TD32

The downloaded `TWordViwer.LoadDocument` procedure trace gives three useful cross-links into the class-procedure index:

- At `0x004B78E4–0x004B78E9`, `LoadDocument` calls `TWordViwer.$bdtr` at `0x004D0D24`. The destructor's TD32 procedure record is `0x004D0D24`, size `0x424`. This is a direct call-site confirmation that the document-load path explicitly tears down a `TWordViwer` instance at this point; it does not, by itself, establish the complete COM shutdown semantics.
- At `0x004B7991–0x004B7994`, `LoadDocument` calls `AddCustomDocPropertiesToDic` at `0x004D1454`. TD32 indexes this method as a `TWordViwer` method, size `0x3B4`. This places custom document-property extraction in the load/response preparation path.
- At `0x004B7A55–0x004B7A58`, `LoadDocument` calls `OnTmrAutoSave` at `0x004B8A84` synchronously and tests its Boolean result immediately afterwards. The detailed wait-loop and response-release evidence is recorded in the research log; this is distinct from Word's registered BeforeSave event.

The TD32 index also confirms:
- `TWordViwer.$bctr`: `0x004D08B4`, size `0x470`
- `TWordViwer.$bdtr`: `0x004D0D24`, size `0x424`
- `TWordViwer.AddXmlWordConfigFieldsToDic`: `0x004D1148`, size `0x30C`
- `TWordViwer.AddCustomDocPropertiesToDic`: `0x004D1454`, size `0x3B4`

The constructor is now a high-priority trace target, but its actual COM activation and event-subscription instructions have **not** yet been inspected. Likewise, the call to `AddCustomDocPropertiesToDic` proves that custom properties are collected on this path, not the exact property names or response schema. Do not infer either until the constructor and callee bodies are available.

## Revised next steps

1. Inspect the constructor and destructor bodies, then identify imported COM activation APIs and event connection points/dispatch interfaces.
2. Trace `AddXmlWordConfigFieldsToDic` and `AddCustomDocPropertiesToDic` together to derive the exact metadata returned from the Word document.
3. Trace the complete `OnTmrAutoSave` and `OnControlerNotify` bodies independently and correlate their state changes with the close-triggered HTTP response.
4. Only after the exact Word methods and event contracts are enumerated, define the LibreOffice bridge compatibility surface.


## Functional map from the TD32 class index

The class-procedure index allows the Word-facing implementation to be divided into independently testable contracts. This is a symbol-level map, not yet a full behavioral trace.

| Subsystem | Procedures / addresses | What can be established |
|---|---|---|
| Document lifecycle | `LoadDocument` `0x004B7724`; `PrepareDocument` `0x004BB77C`; constructor `0x004D08B4`; destructor `0x004D0D24`; `QuitWord` `0x004CDB54` | Dedicated load, prepare, construction, teardown and Word-quit routines exist |
| Request/config field mapping | `GetXmlFieldInfo` `0x004BCA88`; overload `0x004BFC18`; `GetDocFieldName` `0x004BB81C`; `FindFieldInActivefields` `0x004BC170`; `AddFieldInActivefields` `0x004BC278` | XML field definitions are resolved and tracked in an active-fields collection |
| Document field mutation | `FillField` `0x004BC2C4`; `FillImageField` `0x004BC30C`; `GetFieldValue` `0x004BFD38`; `SetFieldValue` `0x004BFDB0`; `FillMSWFields` `0x004C009C`; `AddImagesToDoc` `0x004C0410` | The implementation has distinct text/value and image-field paths and explicitly consumes Word `_Document`, `Field` and `Fields` interfaces |
| Content and custom metadata | `AddXmlWordConfigFieldsToDic` `0x004D1148`; `AddCustomDocPropertiesToDic` `0x004D1454` | One routine is named `AddXmlWordConfigFieldsToDic` but its observed body clears viewer maps and calls `TWordApplication.ScreenRefresh`; the second enumerates Word custom properties and consumes matching single/twin descriptors with dictionary Remove. The descriptor-map population path remains unresolved |
| Save and close callbacks | `WordAppDocumentBeforeSave` `0x004CD154`; `WordAppDocumentBeforeClose` `0x004CCBBC`; `SilentSaveEmwatDoc` `0x004D23D8`; `OnTmrAutoSave` `0x004B8A84`; `OnControlerNotify` `0x004BB3B0` | Save events, close events, silent save, timer-driven waiting and controller notification are separate code paths |
| Print pipeline | `PreparePrintDocument` `0x004CB108`; `CollectFieldsSets` `0x004CB5E4`; `FillPrintDocFields` `0x004CB638`; `PrintWithGamPrintOptions` `0x004C5E04`; `BGPrintWithGamPrintOptions` `0x004C5FF8`; print event callbacks `0x004CDC2C`, `0x004CE030` | Print preparation, field substitution, foreground/background print and Word print callbacks have dedicated routines |
| Document formatting/protection | `ProtectDocument` `0x004C9EA8`; `SaveOriginalOptions` `0x004C5CDC`; `RollBackOriginalOptions` `0x004CA4B0`; `SetDocCaption` `0x004C5D68` | EMWAT also manages document protection and temporary document options; these behaviors must not be omitted from a replacement |

### Consequence for a LibreOffice-compatible backend

A viable replacement is not just “open the DOCX in LibreOffice.” At minimum, the compatibility boundary must account for:
1. document open/create/close and lifecycle state;
2. mapping EMWAT XML field definitions to document bookmarks/content controls/fields or another stable anchor;
3. text and image insertion plus field-value readback;
4. custom document properties and EMWAT metadata round-trip;
5. save/close notifications and the delayed HTTP response contract;
6. print preparation, print-specific field substitutions, and background-print behavior;
7. protection and restoration of document options.

This is a requirements inventory derived from compiled symbols and signatures. The exact Word calls, field-name conventions, and serialized response values still require disassembly/runtime capture before implementing the backend.


## Archive-backed procedure traces — 2026-11-16

The current archive-backed Word analysis run `43882530570` produced three artifacts:
- `emwat-word-lifecycle` — artifact `14232038437`
- `emwat-word-save-print` — artifact `14231834659`
- `emwat-word-field-mapping` — artifact `14231224902`

The artifacts were downloaded and inspected. These are static PE/TD32 traces from the committed `EmwatMethods.bpl1`, not runtime tests.

### XML field metadata extraction

`TWordViwer.GetXmlFieldInfo` at `0x004BCA88` is a 12,688-byte procedure whose TD32 signature explicitly accepts `IXMLFieldType` plus multiple UnicodeString parameters. It uses the XML field interface to retrieve multiple values and iterates the resulting field collection. This confirms that EMWAT translates XML field definitions into an internal field model; it is not merely replacing arbitrary document text.

The exact mapping of each XML interface getter to the internal field-model property is not yet decoded. The procedure's extensive interface calls should be cross-referenced with the `Wordconfigrequestxml` type information and string constants before assigning semantic names.

### Word Fields collection update

`TWordViwer.FillMSWFields` at `0x004C009C` explicitly accepts `Wordxp.Fields`. Its trace iterates the Word Fields collection and calls per-field virtual methods. This establishes a distinct pass over Word's native field collection, separate from XML field parsing.

`TWordViwer.SetFieldValue` at `0x004BFDB0` accepts a `TXmlWordConfigField` and UnicodeString value. It branches on the decoded labels `urlencoded` (`0x004BFEE8`) and `base64` (`0x004BFF0C`), then uses different conversion/assignment helper paths. Other labels are passed through without this decoding. These are per-field encoding labels, not Word field types.

### Custom document properties

`TWordViwer.AddCustomDocPropertiesToDic` at `0x004D1454` obtains Word's `CustomDocumentProperties` collection and iterates its entries. It splits each selected property name at `†` (U+2020 DAGGER; constant at `0x004D1768`), constructs a single/twin descriptor-shaped record, then calls `TDictionary.Remove` on the corresponding pre-existing descriptor map at viewer `+0x68` or `+0x6C`. This is a reconciliation/consumption pass, not map population. The routine's embedded diagnostics misleadingly use the `AddXmlWordConfigFieldsToDic` label; the TD32 symbol and body identify it as `AddCustomDocPropertiesToDic`.

This is a significant compatibility requirement: the Linux backend must preserve EMWAT custom-property extraction and round-trip behavior, not only visible document text.

### BeforeSave event behavior

`WordAppDocumentBeforeSave` at `0x004CD154` is a 1,016-byte procedure with a TD32 signature containing the Word `_Document` interface and an event argument. The trace:
- verifies the callback's document against the viewer's active document reference;
- calls pre-save helper `0x004CB108`;
- consults viewer state flags at offsets `+0x5E` and `+0x5F`;
- calls Word document interface methods and can set the event's 16-bit cancel flag to `0xFFFF` in specific branches;
- performs a prompt/decision path through helper `0x0044ABE4`;
- reaches a Word document operation through vtable offset `+0x29C`;
- clears viewer state field `+0x58` near the end of the callback.

The prompt labels are decoded in the controller-close crosswalk below; the meaning of every decision code and exact event-sink hookup remains bounded by the evidence described there. The callback is evidence of a real BeforeSave cancellation/decision contract, so the Linux lifecycle coordinator must not assume every save request is unconditional.

### Print-field transformation

`TWordViwer.FillPrintDocFields` at `0x004CB638` is a 5,508-byte procedure with a TD32 signature accepting both Word `_Document` and `Wordxp.Fields`. It iterates field-related collections and performs repeated per-field processing, including helper calls that resolve metadata and mutate values. This confirms print preparation is a separate transformation pass over Word fields, not just a generic call to PrintOut.

The exact substitutions, field codes, and output values still need the remainder of the trace and constant decoding. The print path must remain a separate backend capability.

### Current implementation implications

The minimum LibreOffice backend now has additional statically confirmed responsibilities:
1. parse `IXMLFieldType`-derived configuration into a structured internal field model;
2. separately enumerate and update Writer document fields/anchors;
3. preserve custom document properties, including EMWAT's internal split/collection behavior;
4. implement BeforeSave cancellation/decision semantics and active-document state transitions;
5. apply a dedicated print-field transformation before printing.

No exact LibreOffice UNO mapping is asserted yet. Bookmarks, Writer fields, user-defined properties, and document event listeners remain candidate primitives pending decoded field keys and sanitized templates.


## Controller-close crosswalk — additional findings

Run `43882768547` produced `emwat-word-controller-close-crosswalk` (artifact `14232349256`), which was downloaded and inspected.

### BeforeSave decision prompt

The string decode confirms the callback's prompt labels are Persian:
- `موافقم`
- `خیر`
- `انصراف`

It also logs `Save msgBox triggered. result: %d`, `Document.OnBeforeClose Called.`, and `Document.OnBeforeClose succeed.`. The callback can set the event's Cancel argument to `0xFFFF` when the decision result is `2`. Another branch distinguishes result `6`. The exact semantic mapping of every result and whether this callback is wired to BeforeSave, BeforeClose, or both still requires event-sink hookup evidence; the TD32 method name remains `WordAppDocumentBeforeSave`, while its embedded log text says `OnBeforeClose`.

### Custom record/content-control state

`TWordViwer.CostumizeRecAndCC` at `0x004D281C` is called from:
- `OnControlerNotify` at `0x004BB506`;
- `GetDocFieldName` at `0x004BBC2D`;
- `ProtectDocument` at `0x004C9F00` and `0x004C9F7B`;
- `RollBackOriginalOptions` at `0x004CAAC5`.

It sets viewer flag `+0x5C`, calls a Word document interface method at vtable offset `+0x2BC`, and clears `+0x5C` on exit. The routine name and callsites establish that this customization path participates in field-name lookup, protection, rollback, and controller notifications. The exact COM method semantics behind vtable offset `+0x2BC` remain unresolved.

### Content getter and archive helper correction

The wrapper `TWordDocument.Get_Content` at `0x0042BDF8` calls the Word document interface at vtable offset `+0xDC` and returns its result through the wrapper. This is the Word content-getter path.

Important correction: helper `0x00456DFC`, previously treated as a post-content helper, is actually `euUnArchive` in module `EmailUtil`. Its only direct TD32 caller found is `TWordViwer.OnControlerNotify` at `0x004BB5E9`. It is an archive/unarchive utility called from controller notification handling, not a direct caller of `TWordDocument.Get_Content`. The earlier association between `0x00456DFC` and content extraction should be discarded.

### Silent save line-count helper

`TWrapRecord.LineCount` at `0x004D2948` is called by `TWordViwer.SilentSaveEmwatDoc` at `0x004D25F6`. It iterates several viewer-held range/record collections and composes line-count-related values. The exact output representation and relationship to the response payload remain open.


## Event-sink and close-name correction — artifact 14234120250

A full TD32 trace of `OnTmrAutoSave` (`0x004B8A84`) resolves the event callback registration more precisely. The routine installs callback targets into the Word event-sink record:

- `0x004CD154` — `WordAppDocumentBeforeSave`;
- `0x004CD54C` — `WordAppNewDocument`;
- `0x004CD9C0` — `WordAppWindowActivate`;
- `0x004CE030` — `WordAppDocumentBeforePrintBGPrint`, or alternate target `0x004D00AC` depending on viewer flag `+0x3C`.

The callback pointers are written at record offsets `+0x80`, `+0x90`, `+0x98`, and `+0x88` respectively, with the associated viewer object pointer stored in the neighboring fields. This is direct event-sink registration evidence for BeforeSave, NewDocument, WindowActivate, and the selected print-background callback.

**Important correction:** TD32 names `0x004CCBBC` `WordAppDocumentBeforeClose`, but the direct-call scan finds only one direct caller: `TWordViwer.FillImgFldsForPrint` at `0x004CCF8F`. The function's body obtains indexed values from viewer-held collections and calls `GetXmlFieldInfo` (`0x004BCA88`). It is therefore not established as a registered Word DocumentBeforeClose event callback. Its name alone must not be used to implement a close event in LibreOffice. The observed event-sink registration block does not install `0x004CCBBC`.

The BeforeSave callback remains a separate, confirmed event path. It checks active-document identity, calls pre-save helper `0x004CB108`, may set the COM Cancel argument to `0xFFFF`, and uses the three-choice prompt path. Its embedded diagnostic strings mention `OnBeforeClose`, but those strings do not override the TD32 method identity or prove a separate close event.

### Silent-save and line-count boundary

The full trace of `SilentSaveEmwatDoc` (`0x004D23D8`) confirms it is called directly from `GetDocFieldName` (`0x004BBA86`) when the special `Hidden_Customizable` field path is selected. It constructs two temporary string-list objects, gathers values from viewer collections, calls helper `0x004AEBBC`, sets viewer flag `+0x44C`, and conditionally calls `TWrapRecord.LineCount` (`0x004D2948`). The latter has only this direct caller in the current TD32 scan. This is a field-lookup-triggered silent-save/record-building path; it is not proof of an HTTP response writer or a Word close callback.

The exact meaning of the two temporary lists, the COM slot `+0x13C`, and the final serialized record representation remain unresolved. Do not map these to response fields until the helper and caller data are traced.

Evidence: Word controller-close artifact `14234120250`, run `43883105610`.


## Field lookup and image-dispatch crosswalk — artifact 14232259712

The expanded field-mapping artifact adds important caller context to the Word-field procedures:

- `FillPrintDocFields` (`0x004CB638`) has two direct callers in the TD32-bounded scan: `GetDocFieldName` at `0x004BB8AE` and `GetFieldIndexInList` at `0x004CB338`. In the `GetDocFieldName` call, the viewer passes the active document reference and its collection at `+0xA4`. Therefore, although the routine name and BeforePrint callback establish a print-related role, its work is also reached during field-name/index lookup. Do not implement it only as a handler that runs after the user clicks Print.
- `AddImagesToDoc` (`0x004C0410`) is called directly from `GetDocFieldIndex` at `0x004C0A5D`. It checks a field-collection string and, on the matching branch, calls `0x004C19C0`, which TD32 identifies as `TWordViwer.GetCaptionItemFont` (not an image-insertion routine). The call is therefore caption-font preparation within the AddImagesToDoc path; it does not establish that this helper inserts an image. The likely rendering-related procedures `GetCaptionItems` (`0x004C2B20`), `GetImageResolution` (`0x004C2DE0`), and `EmbedTextToImage` (`0x004C436C`) are now queued for direct tracing.
- `FillImageField` (`0x004BC30C`) has two direct callers from `FillTextField` (`0x004BC9CB` and `0x004BCA10`). It conditionally calls `FindWindowExtd` (`0x0045644C`) when viewer flag `+0xF0` is set and one of three field metadata strings is missing. It also examines the Word Field object's type/code and follows separate branches for special field-code patterns. This confirms that the image-named helper participates in the field-fill pipeline, but the unresolved code strings and downstream COM slots prevent a reliable semantic mapping yet.
- `FillField` (`0x004BC2C4`) is a short collection-append helper: it appends the supplied field interface to the viewer collection at `+0x60`. It does not itself perform the visible Word field mutation.

Implementation consequence: keep three distinct layers in the Linux backend—field/config inventory, Word/Writer field mutation, and document-level image insertion. Do not collapse `AddImagesToDoc`, `FillImageField`, and `FillField` into one generic image setter.

Evidence: `emwat-word-field-mapping`, run `43882925143`, artifact `14232259712`.


## Image-field branch analysis — additional trace targets queued

A closer read of the existing TD32 trace narrows the next image-field work:

- `AddImagesToDoc` (`0x004C0410`) obtains a string-valued property from the supplied `IXMLFieldType` interface through vtable offset `+0xB0`, normalizes/copies it, and compares it against a constant at `0x004C0510`. Only the non-equal branch calls `0x004C19C0`, whose TD32 symbol is `TWordViwer.GetCaptionItemFont`. The literal at `0x004C0510` is still undecoded; no field-type label is assigned here.
- The helper call at `0x004C048C` receives the current Word Fields interface, the XML field object, the caller's field metadata, and additional string/record arguments. This is a document-level path distinct from `FillImageField`.
- `FillImageField` (`0x004BC30C`) has two major branches. When viewer flag `+0xF0) is set, it checks three metadata strings before invoking `FindWindowExtd` (`0x0045644C`). In the later branch it inspects a field/index-related value and conditionally uses Word Fields/Field COM calls, including vtable offsets `+0x40), `+0x20), `+0x2EC), and `+0x2F0). These offsets are intentionally left unmapped until the imported WordXP interface method order is established; guessing their names would risk implementing the wrong operation.
- The final helper path also reaches `0x004C19C0) through `AddImagesToDoc`; this helper is now included as a first-class trace target in the Word field-analysis workflow, together with `0x004BC170) and the branch-string constants at `0x004BC6D4) through `0x004BC910).

Workflow expansion commit: `367e4aa58514029278624c65837059f13807394a`. The next run's artifact is required before treating the helper or branch strings as decoded evidence.


## GetDocFieldName caller-chain detail

The TD32 body for `GetDocFieldName` (`0x004BB81C`) gives a useful ordering constraint:

1. It reads viewer field `+0x48) and passes it to helper `0x004D1808`.
2. It invokes `FillPrintDocFields` (`0x004CB638`) with the active document/field context and viewer collection at `+0xA4).
3. It then iterates the entries in viewer collection `+0xA4) and calls helper `0x004C0550` for each entry.
4. The special `Hidden_Customizable` comparison follows; on that branch it calls `SilentSaveEmwatDoc` (`0x004D23D8`).

This confirms print-field preparation happens before the per-entry resolver loop in this routine. It also identifies `0x004C0550` as the next field-resolution target (the current trace does not yet prove its TD32 symbolic name). The workflow now traces `0x004C0550` and the separately named `GetFieldIndexInList` (`0x004CB1B4`) to establish whether they share lookup or collection semantics.

Workflow trace additions: commit `e5933a10905c5edb6075767aa4d25be800698b11`.


## Confirmed GetDocFieldIndex and caption/image sub-pipeline — artifact 14233429328

The expanded field-mapping artifact from run `43886492031` resolves `0x004C0550` as `TWordViwer.GetDocFieldIndex` (procedure range `0x004C0550–0x004C1793`). Its direct caller is `GetDocFieldName` at `0x004BBB2B`. This is the per-configured-field resolver, not an anonymous helper.

The trace establishes this order within `GetDocFieldIndex`:
- Enumerates the Word `Fields` collection and obtains per-field data through its COM interface.
- Calls `FindFieldInActivefields` (`0x004BC170`) on the extracted field name.
- Calls `GetXmlFieldInfo` (`0x004BFC18`) to retrieve the matching XML field metadata.
- Uses `FillMSWFields` (`0x004C009C`) in several branches and `SetFieldValue` (`0x004BFDB0`) in multiple branches.
- Calls `AddImagesToDoc` (`0x004C0410`) at `0x004C0A5D` in the image/caption branch.
- Uses `FillTextField` (`0x004BC980`) on multiple paths and returns a Boolean result to the caller.

This provides the first connected mapping pipeline from Word Field enumeration through active-field filtering, XML metadata resolution, text/property updates, and the separate image/caption branch. The exact semantics of every branch and the string constants are still being decoded; the implementation must preserve this order rather than simply mapping config IDs to bookmarks or properties.

### Caption and bitmap helpers

The same artifact cross-checks these symbols and call relationships:
- `GetCaptionItemFont` (`0x004C19C0`) is called only by `AddImagesToDoc` in the current direct-call scan. Despite the symbol name, its body is the substantial image-generation/insertion path: it calls `GetXmlFieldInfo`, `SetFieldValue` (two observed sites), `EmbedTextToImage` (`0x004C436C`), and `FillMSWFields`; it logs `AddImageToDoc method called`, loads/unloads `igLzw32s.Dll`, processes `signData` and `signText`, validates image files, creates an image list, and logs `AddImageToDoc succeed`. The routine therefore cannot be reduced to a font getter; its body is responsible for image and signature processing.
- `GetCaptionItems` (`0x004C2B20`) is called by `ResizeBitmapCanvas` and `ProcessWords`. It builds/returns a `TCaptionItem` object from a record and several parsed values.
- `GetImageResolution` (`0x004C2DE0`) is called by `StrToAlign` at six sites. Its body compares an input string against six constants and returns enum-like values 1 through 6 (or 0 for no match). The six literal labels are now decoded as `right`, `center`, `left`, `top`, `middle`, and `bottom`. Together with the six call sites in `StrToAlign`, this establishes that the routine converts alignment/position strings to enum-like values; the TD32 symbol name `GetImageResolution` is misleading for this call path.
- `EmbedTextToImage` (`0x004C436C`) is called from `GetCaptionItemFont`; it parses numeric image/caption parameters, converts dimensions through floating-point unit scaling, and invokes helper routines `0x004AFF10` and `0x004AFEB8`. Exact units and final rendering side effects remain open.

Workflow evidence: field-mapping job succeeded in run `43886492031`, artifact `14233429328`. The companion save-print job in that run failed only because its decoder output directory was wrong; this was corrected separately and a new run was queued.


## Print-field special cases — decoded string evidence

The save/print artifact from run `43887016674` confirms the string constant at `0x004CCB0C) is exactly `EMBED Equation`. `FillPrintDocFields` compares the current Word field-code string against this value before entering a separate branch. The routine also constructs/uses a property key around `CustomDocumentProperties` and `count` in the custom-property branch (the string is embedded at an unaligned address; the workflow now decodes the exact byte-aligned starts `0x004CCB45` and `0x004CCB61` to verify both labels).

Do not treat this as a generic field rewrite rule yet: the surrounding helper calls `0x004D3DF8`, `0x004D34B0`, and `0x004D3B78` still need their full traces to determine how custom property fields are selected and stored.

Artifact: `emwat-word-save-print`, run `43887016674`, artifact `14234129463`.


### Field resolver and image-path string evidence

The expanded decoder also resolves important strings used by `GetDocFieldIndex` and `FillImageField`:

- `GetDocFieldIndex` checks a regex-like field-name pattern `^sign.*end[0-2]?[0-9]?$` and emits distinct skip reasons for business rules, exceptions, and repeated processing.
- It logs whether a field's XML value is a single value or a multi-value set, logs twin-field matches, and has a `SignsArea` special case.
- A missing twin field triggers an abort path; the decoded Persian prompt says the field was not found and the document will close while discarding changes. A separate branch aborts if the GAM document is protected with an invalid password.
- `FillImageField` includes special metadata keys `LetterRegistrationDate`, `LetterRegistrationNo`, `ProduceDate`, `Receivers`, `ReceiverDeps`, `ccReceivers`, and `ccReceiverDeps`. Its diagnostics distinguish values stored in `CustomDocumentProperties` from values stored in `Field.Result.Text`, and it checks whether a field is locked.

These are concrete special cases to preserve in the Linux resolver; they are not generic assumptions that all fields map to custom properties. Evidence: `emwat-word-save-print` run `43887016674`, artifact `14234129463`.


The same string-decoding artifact resolves the four `TCaptionItem` text-style labels as `bold`, `italic`, `underline`, and `strikeout`. The `GetCaptionItems` routine parses these style switches while constructing caption-item metadata. The alignment enum labels are `right`, `center`, `left`, `top`, `middle`, and `bottom`; these correspond to the six branches in `GetImageResolution` when called by `StrToAlign`.


## Print-time image field dispatch

The `FillImgFldsForPrint` routine (`0x004CCDC8`) is now traced end-to-end. It enumerates the supplied Word Fields collection, resolves each field through `FindFieldInActivefields` and `GetFieldIndexInList`, and uses `FillTextField` on specific fallback/metadata branches. For an indexed field, it consults viewer-side arrays at `+0xE8) and `+0xEC); one conditional path calls the misleadingly named `WordAppDocumentBeforeClose` routine. This routine is therefore part of print-time image-field substitution, not document-close lifecycle handling.

This explains the only direct caller previously found for `WordAppDocumentBeforeClose`: `FillImgFldsForPrint` at `0x004CCF8F`. The direct call chain is `GetFieldIndexInList` → `FillImgFldsForPrint` → conditional field substitution helper.


## Exact active-field name extraction

`FindFieldInActivefields` (`0x004BC170`) is not a generic case-folding lookup. It searches the Word field code for the literal `DOCPROPERTY`; if present, it applies Delphi `Pos`/`Copy` operations using the first double-space delimiter and then the first single space in the copied segment. If the keyword is absent, it preserves the original code. The implementation and tests in `word_fields.py` now mirror the observed edge cases, including Delphi's `Pos = 0) behavior when the double-space delimiter is absent. This normalized output is the name passed to `FindFieldInActivefields` consumers and to the signature-end regex check.


## Text-versus-image MIME dispatch

The completed string decoder identifies the discriminator at `0x004BCA70` as `text/plain`. In `FillTextField` (`0x004BC980`), the native code delegates to `FillImageField` when the XML field interface is absent, the MIME property is absent, or its value does not match `text/plain`. Thus `text/plain` is the ordinary text-field path; other declared MIME types enter the alternate field/image path. This provides a concrete branch condition for the Linux resolver.


## Twin-field lookup algorithm

`FillTwinFields` (`0x004C02EC`) scans the Word Fields collection from the caller-supplied one-based start index to `Fields.Count). For each item it reads `Field.Code`, normalizes it through `FindFieldInActivefields`, and compares the result to the requested twin identifier. It returns the first matching one-based field index or `0` when no match exists. `GetDocFieldIndex` uses this return value to detect a missing twin and enter its abort/close-without-changes path.

The Python mirror is `find_native_twin_field_index()` in `python/src/emwat_linux/word_fields.py`; its test suite covers one-based indexing, start offsets, no-match behavior, and invalid zero-based starts.


## Correction: descriptor dictionaries are consumed with Remove; twin comparison uses CompareText

The helper symbols at `0x004D531C` and `0x004D68D4` are not insertion methods:
- `0x004D531C` is `TDictionary<UnicodeString,TXmlWordConfigField>.Remove`.
- `0x004D68D4` is `TDictionary<UnicodeString,TXmlWordConfigTwinField>.Remove`.

`AddCustomDocPropertiesToDic` calls these methods while enumerating Word custom properties. It therefore consumes/returns matching descriptors from the single/twin maps at viewer offsets `+0x68` and `+0x6C`; the exact object lifetime and subsequent use of the returned descriptor remain open. Do not describe these call sites as adding descriptors. The separate runtime map at viewer `+0x64` is the `TDictionary<UnicodeString,TDocumentCProperty>` map with its own SetItem/ContainsValue/Remove methods.

The comparison helper `0x00403248` resolves to RTL `System.SysUtils.CompareText`. Consequently, `FillTwinFields` compares the normalized Word field identifier case-insensitively. The Python `find_native_twin_field_index()` now mirrors this with `casefold()`; the signature-end regular-expression branch remains separately case-sensitive.

## Runtime custom-property map: image-fill to print consumption

The runtime dictionary at viewer `+0x64` (`TDictionary<UnicodeString,TDocumentCProperty>`) has a concrete caller chain:
- `FillImageField` updates it through `SetItem` (`0x004D34B0`) at `0x004BC45E`.
- `FillImageField` and `FillPrintDocFields` query it through `ContainsValue` (`0x004D3DF8`).
- `FillPrintDocFields` removes entries through `Remove` (`0x004D3B78`) at four sites; `FillPrintOptionForm` removes entries at one site.

This separates the runtime custom-property values from the single/twin XML descriptor maps at viewer `+0x68/+0x6C`, which `AddCustomDocPropertiesToDic` accesses through their own Remove methods. The runtime map therefore participates in the image-field and print-value lifecycle, not merely in static field inventory.

## Descriptor dictionaries: normalized field lookup and paired-property records

The 2026-11-16 field-mapping artifact adds a concrete call graph around the two descriptor maps:

- `viewer + 0x68` is `TDictionary<UnicodeString,TXmlWordConfigField>`; `viewer + 0x6C` is `TDictionary<UnicodeString,TXmlWordConfigTwinField>`.
- `TWordViwer.GetXmlFieldInfo` (`0x004BFC18`) first checks the single-field map and retrieves its descriptor; if that path does not match, it checks the twin-field map and retrieves the paired descriptor. The returned records expose an integer field/index at `+0x04`; the single descriptor also exposes a string at `+0x08`, while the twin descriptor exposes strings at `+0x08`, `+0x0C`, and another string slot at `+0x10` used by the custom-property path.
- The string normalizer/splitter `0x004BC170` is called repeatedly from the XML-field `GetXmlFieldInfo` overload, `FillTwinFields`, `GetDocFieldIndex`, `FillPrintDocFields`, `FillImgFldsForPrint`, and the viewer constructor. It splits/transforms incoming field/property names before downstream comparisons; exact delimiter semantics remain to be validated from the new decoded constants.
- `AddCustomDocPropertiesToDic` (`0x004D1454`) enumerates Word custom document properties, splits the property name on `†` (U+2020), constructs a single or twin descriptor-shaped record, and removes the matching key from the corresponding descriptor map (`+0x68` or `+0x6C`). This is consistent with consuming matched descriptors during reconciliation; it is not evidence that this routine populates the maps.

The actual initial population path for the two descriptor maps remains open. Direct caller scans of their generic `Add`/`AddOrSetValue` methods did not identify a direct static callsite; the next trace batch now checks enumerable constructors, map insertion callers, and the normalizer's constant strings. Do not equate these XML descriptor maps with the separate runtime `TDocumentCProperty` map at `viewer + 0x64`.

## Recipient/CC option-form fields seeded by the viewer constructor

The expanded constructor artifact (`14265228751`) decodes four field identifiers referenced by `TWordViwer.$bctr` (`0x004D08B4`): `Receivers`, `ReceiverDeps`, `ccReceivers`, and `ccReceiverDeps`. The constructor builds option-form field entries from these names and emits `OptionForm fields have been created:` followed by records formatted as `field[%d]: "%s", xmlfidx: %d, isInDoc:%s.` This gives a concrete native inventory for the recipient/CC option UI and shows that each option entry tracks its XML-field index and whether the field is present in the Word document. It does not establish the full semantics of recipient selection, department expansion, or how those values are serialized back to Almas.
