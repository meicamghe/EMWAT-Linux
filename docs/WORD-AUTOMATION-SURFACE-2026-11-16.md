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
