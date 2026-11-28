# Parallel reverse-engineering follow-up — 2026-11-28 (Run 24)

## Scope and execution

- Repository: meicamghe/EMWAT-Linux
- Branch: feature/recovery-retention-policy
- Analysis input: analysis-input/EmwatMethods.bpl1
- This pass remained static reverse engineering and CI artifact analysis. No production Linux/Windows code was changed; no merge/rebase or release build was performed.
- All targeted final runs passed:
  - Word close/event follow-up: run 46124030841, artifact 15255360751.
  - GAM printer install/API follow-up: run 46124104850, artifact 15254533525.
  - GDI+ Save/import/VMT follow-up: run 46124227390, artifacts 15255092521 and 15254911990.
  - Scanner XML inline/interface follow-up: run 46123192414, artifacts 15253544912 and 15254995277.
  - Supporting GDI+ import map: run 46123647362, artifact 15254299895.
  - Supporting Word activation trace: run 46123764032, artifact 15254722339.
- Two earlier printer workflow attempts failed because the analysis script did not build its PE import-address dictionary; the corrected final workflow did. This was a tooling failure, not an application/test failure.

## 1. Word window events are not the close bridge

The TWordViewer.OnTmrAutoSave event-source setup registers several callbacks. The additional callback pair is now identified:

- 0x004CDB2C — WordAppWindowDeactivate, stored at event-record offset +0xA0, with the viewer context at +0xA4. It checks the incoming window against the viewer's stored window at +0x48 and clears the active flag at +0x78.
- 0x004CDB3C — WordIsActivated, stored at +0xA8, with context at +0xAC. It performs the same window identity check, sets +0x78 to 1, then calls SaveOriginalOptions at 0x004C5CDC.
- SaveOriginalOptions reads/stores original Word option state through internal XML/config interfaces. It is not evidence of a parent-page close message or Almas return.
- The existing callback crosswalk remains: 0x004CD154 is WordAppDocumentBeforeSave, not BeforeClose; 0x004CD54C is NewDocument; 0x004CD9C0 is WindowActivate. The conditional event slot at +0x88 selects LoadOptions or the background-print callback.

The TD32-named WordAppDocumentBeforeClose at 0x004CCBBC remains a misleading name in this call graph:

- Its observed caller is FillImgFldsForPrint (0x004CCDC8), and it calls GetXmlFieldInfo (0x004BCA88).
- GetXmlFieldInfo is also called by GetCaptionItemFont, supporting a generic XML field-metadata role rather than a close-only role.
- No active COM close registration or parent-page message/HTTP bridge was proven by these traces.
- QuitWord (0x004CDB54) is called from OnTmrAutoSave and compares a string against the literal Activation after invoking the Word Application Caption wrapper. Its exact purpose remains unresolved; do not equate it with Document.Close or Application.Quit.

Conclusion: window activation/deactivation is now mapped, but the actual Word close → Save/Discard/Cancel → return-to-Almas contract remains open.

## 2. GAM printer installation and queue API boundary

### Installer launch

- Zanprinter.InstallZanPrinter is at 0x0047CC6C. Its call to 0x00401240 is a thunk to rtl230.bpl!@System@@UStrAsg (UnicodeString assignment), via IAT 0x0062ED38. This is a string assignment, not an installation side effect.
- Zanprinter.GetZanInstallDir is at 0x0047CC94. It constructs a path containing GAMPrinterSetup.exe and calls ShellExecuteW through thunk 0x00404494 / IAT 0x0062F9CC.
- The ShellExecute operation is selected from OS version: Open for major version 5 or earlier, RunAs for versions newer than 5. The function uses GetVersionExW and then waits/rechecks for the printer in a 300-iteration loop with 100 ms delays (about 30 seconds maximum).
- The EMWAT module imports no AddPrinter or AddPrinterDriver function. Actual driver installation is delegated to the external GAMPrinterSetup.exe; EMWAT launches it and checks for the resulting queue.

### Winspool imports and status

The thunk-to-import mapping is now explicit:

| Code thunk | IAT | Imported API |
|---|---:|---|
| 0x004044E4 | 0x0062F9E4 | OpenPrinterA |
| 0x004044DC | 0x0062F9E8 | OpenPrinterW |
| 0x004044D4 | 0x0062F9EC | GetPrinterA |
| 0x004044CC | 0x0062F9F0 | EnumPrintersA |
| 0x004044C4 | 0x0062F9F4 | EnumPrintersW |
| 0x004044BC | 0x0062F9F8 | EnumJobsW |
| 0x004044B4 | 0x0062F9FC | ClosePrinter |

- Zanprinter.Finalization (0x0047D8BC) opens the selected printer, queries PRINTER_INFO_2A using GetPrinterA, reads Status at offset +0x48, and tests the paused status.
- This confirms printer discovery/status and queue-query APIs, not successful job submission or completion. No direct StartDocPrinter/WritePrinter path was established.

### GAM output configuration

- WritePrivateProfileStringW is called through thunk 0x00402910 / IAT 0x0062F07C; GetPrivateProfileStringW and GetPrivateProfileIntW are also imported.
- CheckPrinterPaused writes configuration across save.ini, image.ini, and general.ini. The decoded settings include TIFF format, 256-color image mode, LZW compression, “Each page as a single strip”, rows-per-strip, hidden status-dialog behavior, and the sentinel filename JobFinishes.GAM.
- The general.ini sentinel keys include sentinel and sentinelfile. The save.ini and configure.ini key/value order is documented in docs/GAM-PRINTER-CONFIGURATION-RECOVERY.md; preserve that corrected section/key mapping.
- SetPrinterForTiffout also references configure.ini, policy, allusersfolder, and zvprt50\.

Conclusion: the external GAM driver setup, printer status checks, and INI-based TIFF/sentinel configuration are now substantially mapped. The consumer of JobFinishes.GAM, actual spool completion, and final TIFF/archive hand-off remain open.

## 3. GDI+ save imports: PE imports override stale TD32 names

The corrected PE import parser maps the code thunks to their actual imported functions:

| Code thunk | IAT | Actual GDI+ import |
|---|---:|---|
| 0x00481C5C | 0x006307DC | GdipDisposeImage |
| 0x00481C64 | 0x006307D8 | GdipSaveImageToFile |
| 0x00481C6C | 0x006307D4 | GdipSaveImageToStream |
| 0x00481C74 | 0x006307D0 | GdipSaveAdd |
| 0x00481C7C | 0x006307CC | GdipSaveAddImage |
| 0x00481D14 | 0x00630780 | GdipImageRotateFlip |

The TD32 labels at these thunk addresses are shifted/stale and must not be used as the API identity. Direct callsites found:

- GdipDisposeImage: 0x0049005A
- GdipSaveImageToFile: 0x00490923, 0x00490A57
- GdipSaveImageToStream: 0x0049098A, 0x004909EE
- GdipSaveAdd: 0x00490AFE
- GdipSaveAddImage: 0x00490ABF
- GdipImageRotateFlip: 0x004908BB

The class/interface metadata is still not a flat VMT. Raw pointer scans for the candidate TGPImage Save/SaveAdd wrapper addresses found no runtime-section references (one match was in .debug only). Therefore the exact interface-slot → wrapper → initial Save/SaveAdd/final-flush sequence used by SeparteImages remains unresolved. Keep the already proven encoder settings separate: Compression value 2 = LZW; SaveFlag value 18 = MultiFrame.

## 4. Scanner XML inline evidence

- LoadRequestXML (0x004F2B18) passes the inline literal error at 0x004F2BF8 to an XML interface call (slot +0xB8).
- The adjacent diagnostic prefix is <ScanDoc HasError>. ErrorXML: .
- The request root/constraints names remain scan-document and constraints; fields remain colorDepth, minResolution, maxResolution, and maxFileSize.
- The inline error use is confirmed, but the concrete external XMLRTL/IXMLNode slot implementation and required/optional/default semantics remain open. Do not treat nearby non-text pointer 0x004E9E00 as a recovered property name.

## 5. Current boundaries and next parallel tasks

1. Resolve TGPImage interface dispatch from SeparteImages to the exact GDI+ Save/SaveAdd/final-flush imports; use runtime interface/VMT construction evidence, not stale TD32 method names.
2. Find where JobFinishes.GAM is written/consumed and connect the printer queue disappearance heuristic to the final TIFF/archive output.
3. Continue Word BeforeClose/close-to-Almas return tracing independently of BeforeSave and window activation; Save/Discard/Cancel semantics are not yet closed.
4. Resolve SevenZip output callback ownership and prove or exclude encryption; do not infer a password from the current stubs.
5. Close scanner XML required/optional/default rules and external XMLRTL interface slot semantics.
6. Keep ImageEn Acquire explicitly bounded by the absent matching PKIECtrl23.bpl; continue caller-side analysis without inventing Acquire internals.

No Linux or Windows implementation/release build was started in this pass. No merge or rebase was performed.
