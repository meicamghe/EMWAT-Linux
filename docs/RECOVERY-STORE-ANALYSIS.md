# Recovery / AutoSave form — initial static-analysis findings

Date: 2026-11-15  
Source: GitHub Actions workflow `analyze-recovery-store.yml`, corrected run #2 (`43715017039`), artifact `14162835454`  
Input: `analysis-input/EmwatMethods.bpl1`  
Method: TD32 procedure traces and named PE resource inspection. This is static analysis only.

## 1. Recovery form is a distinct subsystem

A named PE resource `TFRMSHOWAUTOSAVEFILES` was found (resource type 10, language 0, 1,149 bytes). TD32 identifies the form class as `TfrmShowAutoSaveFiles` in module `uSendLog`.

The class has these recovered procedures:

| Procedure | VA | Range |
|---|---:|---|
| `FormCreate` | `0x005EC1A8` | `0x005EC1A8–0x005EC1B1` |
| `FormShow` | `0x005EC1B4` | `0x005EC1B4–0x005EC223` |
| `lslFilesDblClick` | `0x005EC224` | `0x005EC224–0x005EC567` |
| `Delete` | `0x005EB828` | `0x005EB828–0x005EBDA7` |
| `CloseWordApp` | `0x005EBDA8` | `to be fully traced in the next branch` |
| `FormClose` | `0x005EBF20` | `0x005EBF20–0x005EC1A7` |
| `WordAppDocumentBeforeClose` | `0x005EC580` | `0x005EC580–0x005EC591` |

This form is separate from the main `TWordViwer` editor. Its callbacks must not be mistaken for the main editor's Word lifecycle callbacks.

## 2. Form initialization and list interaction

- `FormShow` clears the object field at offset `+0x3D0`, calls helper `0x00467088` using a global object at `0x00464720`, then assigns a returned object/reference into field `+0x3D8`. The helper's exact type and purpose are not yet resolved.
- `lslFilesDblClick` iterates a list-like collection and uses multiple string/collection helpers to process selected entries. Its exact open/restore semantics are not yet established.
- `Delete` iterates the list-view item collection at form offset `+0x3C0), checks item selection, and extracts an item-associated value at offset `+0x20`. When at least one selected entry is present, it creates a Word Automation application wrapper, assigns a recovery-form event callback at `0x005EC594`, and performs further late-bound Automation calls.
- The above establishes that the recovery UI is coupled to Word Automation and a selected-item list. It does not prove the recovery file path, extension, or the exact deletion semantics.

## 3. FormClose and Word event callback

`FormClose` checks the Word application wrapper stored at form offset `+0x3D0). If present, it obtains a Word collection and iterates its items. For each item it constructs Automation arguments and invokes dispatch slot `+0x29C`. It then disconnects/releases the wrapper and clears the form field.

The slot `+0x29C` remains an unresolved late-bound dispatch call. It must not be named `Document.Close` until the DISPID and argument list are recovered.

The recovery form's `WordAppDocumentBeforeClose` callback at `0x005EC580` conditionally calls `CloseWordApp` at `0x005EBDA8`. This is distinct from `TWordViwer.WordAppDocumentBeforeClose` at `0x004CCBBC`.

## 4. Recovery-related helper names found in embedded symbols

The string/symbol inventory includes these candidates:

- `Emwatutils.euGetAutoSavePath`
- `Emwatutils.euGetAutoSavePass`
- `Emwatutils.DoClearOldAutoSaveFiles`
- `Emwatutils.euClearOldAutoSaveFiles`
- `Emwat.Sys.euGetLocalAppDataPath`
- `Emwat.Sys.euGetTempPath`
- `Emwat.Sys.euGetWinTempPath`
- `Emwat.Sys.DeleteTempRAW`
- `Emwat.Sys.RemoveTempFiles`
- `Emwat.Sys.euClearTempFiles`
- `EmwatConsts.gsEMWTTempPath`

These are symbol/string discoveries, not yet proof of which helper the recovery form calls or where it stores entries. In particular, no `.asd`, `.wbk`, or other extension is confirmed as EMWAT's recovery format.

## 5. Next analysis

A second workflow, `.github/workflows/analyze-recovery-paths.yml`, has been added to trace the helper implementations and callers independently. It also traces helper calls made from the recovery form and decodes the form's referenced data constants.

The next evidence needed is:
1. the implementation and callers of `euGetAutoSavePath` and `euGetAutoSavePass`;
2. the implementation of old-autosave cleanup helpers and their actual filesystem operations;
3. the exact source of the list items shown by `TfrmShowAutoSaveFiles`;
4. the Automation DISPID/arguments used by `FormClose` and `Delete`;
5. whether the form restores a selected entry, deletes it, or both in different user actions.

Until those are resolved, Linux should expose a recovery-store interface but should not hard-code a directory, extension, password format, or cleanup policy.

## 6. Artifacts and reproducibility

- Corrected recovery form run #2: `43715017039`, success, artifact `14162835454` (`emwat-recovery-store-analysis`).
- Initial run #1: `43714978859`, success, artifact `14161843667`; superseded because its report formatting was corrected in run #2.
- Parallel helper-path workflow: `analyze-recovery-paths.yml`, run #1 (`43715289876`); running while this report was updated.


## 7. New filename/filter constants recovered (2026-11-15)

The recovery-form data references were decoded in workflow `analyze-recovery-paths.yml`, run #1 (`43715289876`), artifact `14162565730`:

- `0x005EC49C`: `*.easz`. In `lslFilesDblClick` (`0x005EC224`), this constant is passed to helper `0x004043BC` while constructing/processing a file collection. Its wildcard syntax strongly suggests an AutoSave-file filter, but the helper semantics and directory are not yet resolved.
- `0x005EBD3C`: `.easd`. This literal is used in string construction inside the `Delete` procedure (`0x005EB828`); its exact role as a suffix, temporary-file extension, or Automation argument remains to be proven.
- `0x005EBD18`: `AutoSave. `.
- `0x005EBD54`: `AutoSave. WordAppp.Connect.1st`.

The coexistence of `.easz` and `.easd` means the recovery UI may interact with more than one AutoSave-related file form. Do not collapse them into a single confirmed file extension yet.

The helper index also resolved:
- `euGetAutoSavePass` at `0x00456B78`;
- `DoClearOldAutoSaveFiles` at `0x00456C0C`;
- `euClearOldAutoSaveFiles` at `0x00456C98`;
- `euGetLocalAppDataPath` at `0x0044A2C4` / `0x0044A300`;
- `euGetWinTempPath` at `0x0044A47C`;
- `euGetTempPath` at `0x0044A7A0`;
- `DeleteTempRAW` at `0x0044AE98`.

Initial control-flow evidence in `euClearOldAutoSaveFiles` shows it enumerates a file collection, obtains file-age/time values, compares an age against `0x18`, and conditionally calls a deletion helper at `0x004026B4`. The exact time unit, file mask, and directory are not yet established. The helper-path workflow is being extended to resolve those constants and imported API targets.
