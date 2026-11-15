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


## 8. Shared AutoSave file enumeration path (2026-11-15)

The caller scan for `euGetTempFileName` (`0x00454A58`) shows three direct call sites:
- `euClearOldAutoSaveFiles` at `0x00456CC4`;
- `TfrmShowAutoSaveFiles.lslFilesDblClick` at `0x005EC26B`;
- `euRandomFileName` at `0x00454CC6`.

Both the recovery UI and the old-AutoSave cleanup routine therefore use the same helper before passing a second string constant into `0x004043BC` to build/process a file collection. In the UI path that constant is `*.easz`; the cleanup path uses constant `0x00456DCC`, which is being decoded in the follow-up run. This is stronger evidence of a shared AutoSave file-store workflow than the isolated string hits alone.

`euGetAutoSavePass` (`0x00456B78`) has direct callers in `DoClearOldAutoSaveFiles` (`0x00456C0C`) and `TfrmSendLog.lblFileNameClick` (`0x005ECFE5`). Its exact input/output semantics are still unresolved; the symbol name alone is not enough to claim a decryption algorithm.

The path/helper rerun is resolving the constants around `euGetTempFileName`, the file enumeration helper, and the file-delete API target before a concrete directory or retention policy is documented.


## 9. Confirmed file enumeration and filesystem APIs (path workflow run #2)

Artifact `14162601983` from `analyze-recovery-paths.yml` run #2 resolved several previously unknown helper targets:

- `0x004043BC` is an IAT thunk to `rtl230.bpl!TDirectory.GetFiles`.
- Both the recovery UI (`lslFilesDblClick`) and `euClearOldAutoSaveFiles` pass the wildcard `*.easz` to this file-enumeration path. This confirms `.easz` is an actual file-listing mask used by the recovery subsystem, not merely an unrelated embedded string.
- `0x004026B4` resolves to `kernel32!DeleteFileW`. The cleanup loop conditionally passes an enumerated file path to this API.
- `euGetLocalAppDataPath` uses `shell32!SHGetSpecialFolderLocation` and `SHGetPathFromIDListW` with CSIDL `0x1C` (Local AppData). This establishes a Windows Local AppData path helper, but does not yet prove that the `.easz` store is located directly beneath it.
- `euGetWinTempPath` uses the Local AppData helper and the literal `emwt.tmp` as part of a separate temporary-path routine. Do not assume this temp-file path is the AutoSave archive directory.

The cleanup routine `euClearOldAutoSaveFiles` enumerates `*.easz`, calculates a file-age value, compares it with `0x18`, and conditionally calls `DeleteFileW`. The exact age helper and unit still need confirmation; if the value is a Delphi `TDateTime` day delta, `0x18` would represent 24 days, but that interpretation is not yet promoted to a confirmed retention policy.

`DoClearOldAutoSaveFiles` supplies either a fallback constant (redacted in this report) or a value returned by `euGetAutoSavePass` to the cleanup routine. The password helper uses a 0x400-byte buffer and is also called by `TfrmSendLog.lblFileNameClick`; its exact encoding/decryption behavior remains unresolved.

A separate helper, `DeleteTempRAW`, contains the command strings `taskkill.exe` and `/f /im WINWORD.EXE`, along with `GamElectronic EMWAT` and `.doc` markers. This is a distinct Word/temp cleanup path; it must not be confused with the `.easz` archive deletion loop. A native Linux port should manage only its own office-engine processes rather than blindly reproducing a global `taskkill` of all Word/office processes.


## 10. AutoSave password and retention interval resolved (path workflow run #3)

Artifact `14162781931` from `analyze-recovery-paths.yml` run #3 provides two important resolutions:

### AutoSave password source

`euGetAutoSavePass` (`0x00456B78`) calls `advapi32!GetUserNameW` with a 0x400-character buffer. On success it sets the returned Delphi string length to the returned character count minus the terminating NUL. If the API fails, the function clears the output and assigns the literal fallback `@25*gamsign*25@`.

Therefore, the recovery/cleanup password is the **current Windows account user name**, with `@25*gamsign*25@` as the fallback when `GetUserNameW` fails. This is code-path evidence, not an inference from the helper's name. The exact downstream encryption/decryption algorithm for `.easz` remains unresolved.

### Retention interval

The cleanup loop uses `FileAge(path)`, converts the timestamp with `FileDateToDateTime`, obtains `Now`, calculates elapsed time with `DateUtils.HoursBetween`, and compares the result against `0x18` (24). Files at least **24 hours old** are passed to `DeleteFileW`. This corrects the earlier uncertainty: the threshold is 24 hours, not 24 days.

### Temporary AutoSave directory (partially resolved)

`euGetTempFileName` (`0x00454A58`) calls `euGetWinTempPath` (`0x0044A47C`) when its cached path is empty, then appends `temp-emwatASwf\\`. The resulting path is the base for `*.easz` enumeration. The exact implementation of the Windows temp-path helper and its API call chain is the remaining path question.

Evidence: `GetUserNameW` `0x0040264C`; `FileAge` `0x004032B8`; `FileDateToDateTime` `0x00403330`; `Now` `0x004033A0`; `HoursBetween` `0x00404344`; `DeleteFileW` `0x004026B4`.


## 11. Exact AutoSave root path and recovery-open pipeline (path workflow run #4)

Artifact `14162323614` from `analyze-recovery-paths.yml` run #4 resolves the missing OS API:

- `euGetWinTempPath` (`0x0044A47C`) calls `kernel32!GetTempPathW` (`0x004027F8`) with a 260-character buffer.
- `euGetTempFileName` (`0x00454A58`) appends the literal `temp-emwatASwf\\` to that returned path.
- The AutoSave list and cleanup routines enumerate `*.easz` under that directory.

The Windows-side recovery store path is therefore:

```text
%TEMP%\\temp-emwatASwf\\*.easz
```

This is the process user's Windows temp directory, not the separate Local AppData helper or the `emwt.tmp` marker path.

### Selected-file open path — unresolved transformation details

The recovery form's `Delete` handler first collects selected list-item values, calls `FormClose` on the recovery form, and then passes the selected path plus the temp directory into `euResetMemory` (`0x00456F00`). It next appends a value derived from the temp path and the literal `.easd` to a path variable, creates/connects a Word Automation application wrapper, and performs late-bound Automation calls.

This establishes a recovery-open transformation path involving `.easz`, `euResetMemory`, and a constructed `.easd` path. It does **not yet** prove whether `.easd` is a decrypted file, a temporary working copy, or another intermediate; the implementation of `euResetMemory` and its internal object methods must be resolved before naming the transformation.

Next trace targets: `0x00452BBC` (called inside `euResetMemory`), the VMT/object pointers at `0x0062A824` and `0x0062A858`, and the `euResetMemory` callsites.


## 12. Recovery file transformation helper — structural trace (path workflow run #5)

The `euResetMemory` procedure (`0x00456F00`) is not a simple filename rename. Its call chain uses helper `0x00452BBC`, which constructs an object using class/data metadata at `0x00452558`, then invokes a virtual method at slot `+0x4C`.

Within `euResetMemory`:
- A 16-byte block is copied from one of two global data areas (`0x0062A824` or `0x0062A858`) according to a Boolean argument.
- The constructed object's virtual methods at `+0x0C` and `+0x3C` receive the two path arguments.
- Another virtual method at `+0x44` may receive an optional string argument.
- The second Boolean argument changes whether that optional method is invoked.

This shape is consistent with a stateful file/memory transformation object, but the class identity, key meaning, and transform direction are not yet known. It is not yet safe to call this AES, encryption, decryption, compression, or decompression. Run #6 adds object/VMT and global-data reference inspection.


## 13. Archive implementation identified; password roles corrected (2026-11-15)

The run #7 artifact (`14163205743`) identifies the object constructed by `euResetMemory` as a SevenZip archive reader: TD32 names the class method `@Sevenzip@T7zInArchive@GetInArchive` at `0x00452ED8`, and the adjacent type information contains the class name `T7zInArchive`. Its metadata includes properties named `Password`, `PasswordSender`, `ProgressSender`, `Stream`, `PasswordIsDefined`, `SubArchiveMode`, `SubArchiveName`, and extraction callbacks. This is strong evidence that the recovery path uses the 7-Zip archive reader component, rather than a plain file rename or simple stream copy.

Two different password-like strings were found and must not be conflated:

- `euGetAutoSavePass` (`0x00456B78`) returns the Windows account name (or its fallback `@25*gamsign*25@`). Its direct caller `DoClearOldAutoSaveFiles` (`0x00456C0C`) concatenates that returned value with `@25*gamsign*25@` when its Boolean-like argument selects that branch. Another direct caller is `TfrmSendLog.lblFileNameClick`. This proves the helper's output construction, but does **not yet** prove that this exact string is the password used by the `.easz` recovery archive.
- `euResetMemory` (`0x00456F00`) supplies the literal `mW@Tlogs43end_+` to object virtual slot `+0x44` when its optional string argument is null and the relevant flag is set. The class metadata has a `Password` property, but the exact mapping of virtual slot `+0x44` to the property setter and the exact archive-open method are still being resolved.

**Correction to section 10:** do not describe the Windows username or `@25*gamsign*25@` as the confirmed `.easz` archive password. The helper returns/combines those strings in one AutoSave-related path, while the recovery-open path separately supplies `mW@Tlogs43end_+` to the SevenZip object. The archive password and transformation sequence remain unresolved until the SevenZip VMT method mapping and call semantics are confirmed.

The `.easd` path is still only a constructed path in the recovery `Delete` handler. The current evidence is consistent with it being an extracted or working document path, but does not yet establish its content or exact lifecycle.


## 14. SevenZip password setter and recovery dispatch narrowed (2026-11-15)

Artifacts from analyze-recovery-paths.yml runs #9 (14163436366) and #10 (14163367757) trace the SevenZip reader methods and the euResetMemory caller path.

### Password argument

The class method T7zInArchive.SetPassword at 0x00453860:
- copies the supplied Unicode string into the object field at +0x58;
- obtains the archive interface stored at +0x28;
- invokes that interface's method at vtable offset +0x1C, passing the password string;
- releases its temporary string/interface references on exit.

The T7zInArchive type metadata independently exposes a Password property, alongside PasswordIsDefined, PasswordSender, Stream, and extraction-related properties. In euResetMemory (0x00456F00), the optional password argument is passed to the archive object's virtual dispatch at slot +0x44; if that argument is null while the password flag is enabled, the literal mW@Tlogs43end_+ is supplied instead. The class method body and property metadata show that T7zInArchive has a Password setter, but the exact mapping from euResetMemory's virtual slot +0x44 to that setter is not yet proven. The later raw pointer scan found no direct static pointer to T7zInArchive.SetPassword (0x00453860), so retain this as a strong candidate rather than a confirmed VMT binding. The Windows username / @25*gamsign*25@ result from euGetAutoSavePass remains a separate cleanup/logging path and is not the recovery-open password.

### Reader operations

The reader implementation exposes these operations:
- OpenFile (0x00452FB8) opens the archive interface using a filename;
- OpenStream (0x00452FDC) wraps an input stream and invokes the archive interface's open operation;
- GetNumberOfItems, GetItemPath, GetItemName, GetItemSize, and GetItemProp query archive entries;
- ExtractItem, ExtractItems, ExtractAll, and ExtractTo invoke extraction methods on the archive interface.

The euResetMemory body constructs the reader object, conditionally supplies the password, then dispatches two path arguments through object virtual slots +0x0C and +0x3C. The method index/VMT mapping for those two path slots is not yet independently decoded, so this report does not label them as a proven OpenFile + ExtractTo pair. The separate recovery-form Delete handler subsequently constructs a .easd path and proceeds into Word Automation. This supports an archive-to-working-file recovery pipeline, but does not yet establish the exact extracted member name, archive format variant, output bytes, or complete file lifecycle.

### What is now established vs. pending

Established:
- the recovery component is a SevenZip archive reader (T7zInArchive);
- the recovery path has a dedicated password-setting dispatch;
- the fallback password passed by euResetMemory is mW@Tlogs43end_+;
- the reader exposes normal archive-open, entry-query, and extraction methods;
- .easz is the enumerated recovery-file mask under %TEMP%\\temp-emwatASwf\\.

Still pending:
- exact VMT method names for euResetMemory slots +0x0C and +0x3C;
- whether the archive is standard 7z or another SevenZip-supported format/configuration;
- whether .easd is the extracted document itself or a subsequent intermediate;
- the archive writer path and the exact creation/encryption settings for .easz.


## 15. Writer-side SevenZip password hook inspected (2026-11-15)

The T7zOutArchive class trace adds an important constraint to the archive-creation investigation:
- T7zOutArchive.SetPassword at 0x004547DC is a tiny stub that returns zero and does not store the supplied string or call the archive interface. Do not treat this wrapper as proof that the writer is configured with a password through this method.
- T7zOutArchive.CryptoGetTextPassword2 at 0x004543C4 calls helper 0x00404734, resolved as rtl230.bpl!TObjectList.$bctr$qqrv. It passes the class pointer from global 0x0062FBB8, stores the constructed TObjectList at instance offset +0x2C, and zeroes +0x30 and +0x34. This is collection initialization, not evidence of the writer password value or provider.
- T7zOutArchive exposes AddFile, AddFiles, AddStream, SaveToFile, and SaveToStream. Direct bounded CALL scans did not find callers for the wrapper methods, so writer usage is likely through indirect/VMT dispatch or a helper not yet mapped.

Consequently, the recovery reader password path is substantially better understood than the .easz creation path. The exact archive writer, output format, password callback value, and compression/encryption properties remain open questions.


## 16. SevenZip plugin factory and password callback boundary — 2026-11-15

The plugin-focused workflow run #1 (`43719323732`, artifact `14164146310`) traces the shared SevenZip plugin class and both archive wrappers. It adds a useful separation between the reader's password setter and the plugin-level callback provider.

### Plugin class and factory

- TD32 identifies `T7zPlugin` constructor at `0x00452C10`, destructor at `0x00452C64`, and `CreateObject` at `0x00452DB4`.
- The plugin constructor calls `T7zOutArchive.CryptoGetTextPassword2` (`0x004543C4`) with the class/data pointer at `0x004529E8`. That method constructs a `TObjectList` using the class pointer at global `0x0062FBB8` and stores it at instance offset `+0x2C`; the constructor then adjusts/stores a returned object reference and invokes a plugin virtual method at slot `+0x30`. Do not interpret this as proof of the actual writer password provider.
- `T7zPlugin.CreateObject` is directly called by both `T7zInArchive.GetInArchive` (`0x00452ED8`) and `T7zOutArchive.GetOutArchive` (`0x00454450`). Thus the same plugin factory is shared by the reader and writer wrappers.
- The recovery helper `CreateOutArchive` (`0x00452BBC`) constructs the wrapper using the literal `7z.dll` at `0x00452C00`, passes a 16-byte value copied from one of the globals `0x0062A824` / `0x0062A858`, then invokes a virtual method at slot `+0x4C`. The helper name and its factory call alone do not prove which archive interface GUID is selected or whether the object is configured for input versus output.

### Password paths — keep the layers distinct

- `T7zOutArchive.CryptoGetTextPassword2` (`0x004543C4`) initializes a `TObjectList`: helper `0x00404734` is the RTL TObjectList constructor, with class pointer from global `0x0062FBB8`; the new list is stored at instance offset `+0x2C`. Its only direct bounded caller is the `T7zPlugin` constructor at `0x00452C25`. This does not reveal the password text or prove a provider implementation.
- `T7zOutArchive.SetPassword` (`0x004547DC`) remains a no-op stub; it does not write a password or configure the archive interface.
- `T7zInArchive.SetPassword` (`0x00453860`) stores a Unicode string at instance offset `+0x58`, creates a callback-like helper object, and invokes the archive interface's extraction-style slot `+0x1C`. The raw static-pointer scan found no direct pointer to this method, so the recovery call through slot `+0x44` remains a strong but unproven mapping.
- In `euResetMemory` (`0x00456F00`), slot `+0x44) receives the caller-supplied password or fallback `mW@Tlogs43end_+`; slots `+0x0C) and `+0x3C) receive the two path arguments. The precise VMT slot names and the archive-interface GUID remain open.

### New direct caller evidence

The plugin constructor has a direct caller in `euUnArchive` (`0x00456E37`), which uses global `0x0062A824` and then operates on the returned object. This is a separate unarchive path from `euResetMemory`, which calls `CreateOutArchive` at `0x00452BBC`. Both paths use the shared SevenZip plugin layer, but they must not be collapsed into one identical operation until their GUIDs, input/output direction, and callback setup are decoded.

### Updated confidence

Confirmed: the 7z plugin wrapper, shared CreateObject factory, input/output wrapper methods, TObjectList initialization inside CryptoGetTextPassword2, and the distinct euUnArchive/euResetMemory entry paths.

Still unresolved: the exact interface GUIDs and direction selected by each factory, the VMT method names for euResetMemory slots +0x0C/+0x3C/+0x44, the writer's actual password text/callback semantics, and the exact archive format/options used for .easz.


### Correction from recovery path workflow run #10 — TObjectList constructor resolution

The additional API target trace resolves `0x00404734` as `rtl230.bpl!TObjectList.$bctr$qqrv`. Therefore, the previous description of `T7zOutArchive.CryptoGetTextPassword2` as obtaining a provider/interface from `0x0062FBB8` was too strong. The confirmed operation is construction of a TObjectList using the class pointer at that global, stored at `Self+0x2C`, followed by zeroing `Self+0x30` and `Self+0x34`. The writer password provider/value remains unresolved.


## 17. Reader password and extract path correlation — 2026-11-15

The completed recovery path workflow run #10 (`43719180035`, artifact `14164088249`) provides deeper traces for the reader wrapper and cleanup helpers.

### Reader method semantics

- `T7zInArchive.OpenFile` (`0x00452FB8`) accepts one UnicodeString path and invokes the archive interface at `Self+0x28`, vtable slot `+0x14`, before a follow-up helper call.
- `T7zInArchive.ExtractTo` (`0x0045375C`) accepts one UnicodeString destination path, stores transient fields at `Self+0x50` and `Self+0x54`, then invokes interface slot `+0x1C` with an extraction-style argument set. It clears the transient fields on exit.
- `T7zInArchive.SetPassword` (`0x00453860`) stores the supplied UnicodeString at `Self+0x58`. It then creates a helper/callback object and invokes the same interface slot `+0x1C` with a callback-style argument set. This is not a direct call that forwards the password string as a COM setter.
- `T7zInArchive.PrepareOperation` (`0x004532E4`) reads the stored password field `Self+0x58` and has separate branches for the callback/context fields at `+0x50) and `+0x54). This supports the interpretation that the password is consumed through the extraction callback path.
- `T7zInArchive.CryptoGetTextPassword` (`0x00453480`) and `SetPasswordCallback` (`0x00453534`) are tiny stubs returning zero; do not attribute the working password flow to either stub.

### euResetMemory virtual-call correlation

`euResetMemory` calls the returned object's virtual/interface slots in this order:

1. `+0x44` with the optional password or fallback `mW@Tlogs43end_+`.
2. `+0x0C` with the first path argument.
3. `+0x3C` with the second path argument.

The signatures and semantics align closely with the reader wrapper's `SetPassword(UnicodeString)`, `OpenFile(UnicodeString)`, and `ExtractTo(UnicodeString)` methods, respectively. This is now the leading working hypothesis for recovery: set the password, open the `.easz` archive, then extract to the `.easd` working path. However, the class VMT/interface slot table has not yet been mapped well enough to call these three bindings proven. The factory helper's symbol is `CreateOutArchive`, while the class metadata identifies `T7zInArchive`; preserve this naming/type discrepancy instead of silently resolving it.

### Cleanup API targets independently resolved

- `0x004043BC` resolves to RTL `TDirectory.GetFiles`; the cleanup code enumerates `*.easz`.
- `0x004032B8` resolves to RTL `FileAge`; `0x00403330` resolves to `FileDateToDateTime`; `0x004033A0` resolves to `Now`; and `0x00404344` resolves to `HoursBetween`.
- The age comparison uses `0x18` hours (24 hours) before calling the file-delete helper. `0x004026B4` resolves to `kernel32!DeleteFileW`.
- These imports confirm the earlier cleanup interpretation; the exact archive format remains unverified.

### Confidence update

Leading hypothesis: `euResetMemory` is a password-aware SevenZip reader/extract path that opens an `.easz` file and extracts to a temporary `.easd` path. Confirmed pieces: reader wrapper methods, password field and callback handling, cleanup enumeration, 24-hour age threshold, and DeleteFileW. Still unproven: the exact VMT slot bindings, exact content of `.easd`, and archive format/options.


## 18. Separate euUnArchive helper path — 2026-11-15

Plugin follow-up run #2 (`43720247793`, artifact `14164382428`) traces the previously identified direct constructor caller `euUnArchive` (`0x00456DFC–0x00456EFF`).

- `euUnArchive` calls the `T7zPlugin` constructor at `0x00452C10) using global `0x0062A824`.
- It then calls object/interface slots `+0x28), `+0x10), and `+0x18). The function obtains a count from one of its collection-like arguments, iterates indices, retrieves corresponding values from two collection-like arguments through their slot `+0x0C), and passes those values to the plugin object's slot `+0x10). At the end it calls slot `+0x18) with the remaining path/context argument.
- The direct bounded caller scan for `euUnArchive` found no direct CALL sites. The T7zPlugin constructor's only direct bounded caller in this scan is `euUnArchive`.
- This is a distinct plugin-based multi-item extraction path. It is not the same call chain as `euResetMemory`, which uses the separate `CreateOutArchive` helper at `0x00452BBC) and calls slots `+0x44/+0x0C/+0x3C).

The exact meanings of the `euUnArchive` slots `+0x28/+0x10/+0x18), the two collection argument types, and the archive direction are not yet resolved. Keep it as a separate generic SevenZip operation; do not use it to infer the .easz recovery protocol.
