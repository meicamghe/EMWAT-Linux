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
| Content and custom metadata | `AddXmlWordConfigFieldsToDic` `0x004D1148`; `AddCustomDocPropertiesToDic` `0x004D1454` | Two distinct document-to-dictionary extraction routines are present; exact key names and serialization remain unknown |
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
