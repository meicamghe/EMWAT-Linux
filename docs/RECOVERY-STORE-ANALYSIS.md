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

This establishes a recovery-open path involving `.easz`, `euResetMemory`, and a constructed `.easd` path. Later SevenZip interface tracing identifies the reader and its `OpenStream`/`SetPassword`/`IInArchive.Extract` call chain. It still does **not** prove whether `.easd` is the extracted document itself, a temporary working copy, or another intermediate.

Those initial targets have since been traced. Current follow-ups are the caller-side `IInStream` construction, the two callback type-info blocks (`0x0045391C` and `0x00453850`), the output/member destination, and the final `.easd` lifecycle.


## 12. Recovery file transformation helper — structural trace (path workflow run #5)

The `euResetMemory` procedure (`0x00456F00`) is not a simple filename rename. Its call chain uses helper `0x00452BBC`, which constructs an object using class/data metadata at `0x00452558`, then invokes a virtual method at slot `+0x4C`.

Within `euResetMemory`:
- A 16-byte block is copied from one of two global data areas (`0x0062A824` or `0x0062A858`) according to a Boolean argument.
- The constructed object's custom interface methods at `+0x0C` and `+0x3C` receive, respectively, an input-stream interface and a UnicodeString. The method at `+0x44` receives an optional UnicodeString when the second Boolean condition selects that branch.
- Later class/interface tracing identifies the object as `T7zInArchive` and maps the slots: `+0x0C` → `OpenStream(IInStream)`, `+0x3C` → `SetPassword(UnicodeString)`, and `+0x44` → the virtual `T7zArchive` constructor. `SetPassword` issues an all-items `IInArchive.Extract` request through a callback.

This section records the initial structural interpretation only. Sections 13–19 supersede its earlier uncertainty about the class identity and virtual slot names. The exact callback output destination and `.easd` contents remain open.


## 13. Archive implementation identified; password roles corrected (2026-11-15)

The run #7 artifact (`14163205743`) identifies the object constructed by `euResetMemory` as a SevenZip archive reader: TD32 names the class method `@Sevenzip@T7zInArchive@GetInArchive` at `0x00452ED8`, and the adjacent type information contains the class name `T7zInArchive`. Its metadata includes properties named `Password`, `PasswordSender`, `ProgressSender`, `Stream`, `PasswordIsDefined`, `SubArchiveMode`, `SubArchiveName`, and extraction callbacks. This is strong evidence that the recovery path uses the 7-Zip archive reader component, rather than a plain file rename or simple stream copy.

Two different password-like strings were found and must not be conflated:

- `euGetAutoSavePass` (`0x00456B78`) returns the Windows account name (or its fallback `@25*gamsign*25@`). Its direct caller `DoClearOldAutoSaveFiles` (`0x00456C0C`) concatenates that returned value with `@25*gamsign*25@` when its Boolean-like argument selects that branch. Another direct caller is `TfrmSendLog.lblFileNameClick`. This proves the helper's output construction, but does **not yet** prove that this exact string is the password used by the `.easz` recovery archive.
- `euResetMemory` (`0x00456F00`) supplies the literal `mW@Tlogs43end_+` to custom-interface slot `+0x44` when its optional string argument is null and the relevant flag is set. That slot is now mapped to the virtual `T7zArchive` constructor (`0x0045392C`), which stores the supplied string at `Self+0x44` and sets a flag at `Self+0x40`. This confirms where the fallback string is stored, but does not by itself prove its semantic role as the archive password.

**Correction to section 10:** do not describe the Windows username or `@25*gamsign*25@` as the confirmed `.easz` archive password. The helper returns/combines those strings in one AutoSave-related path, while the recovery-open path separately supplies `mW@Tlogs43end_+` to the SevenZip object. The recovery interface slots are now mapped; the meaning of the constructor string, the second password-like string, the callback output target, and the final `.easd` lifecycle remain unresolved.

The `.easd` path is still only a constructed path in the recovery `Delete` handler. The current evidence is consistent with it being an extracted or working document path, but does not yet establish its content or exact lifecycle.


## 14. SevenZip password setter and recovery dispatch narrowed (2026-11-15)

Artifacts from analyze-recovery-paths.yml runs #9 (14163436366) and #10 (14163367757) trace the SevenZip reader methods and the euResetMemory caller path.

### Password argument

The class method T7zInArchive.SetPassword at 0x00453860:
- copies the supplied Unicode string into the object field at +0x58;
- obtains the archive interface stored at +0x28;
- invokes that interface's method at vtable offset +0x1C, passing the password string;
- releases its temporary string/interface references on exit.

The `T7zInArchive` type metadata exposes `Password`, `PasswordIsDefined`, `PasswordSender`, `Stream`, and extraction-related properties. `euResetMemory` now has a proven slot mapping: `+0x44` calls the base `T7zArchive` virtual constructor with the optional string/fallback; `+0x0C` calls `T7zInArchive.OpenStream(IInStream)`; and `+0x3C` calls `T7zInArchive.SetPassword(UnicodeString)`. The Windows username / `@25*gamsign*25@` result from `euGetAutoSavePass` remains a separate cleanup/logging path and is not established as either recovery string.

### Reader operations

The reader implementation exposes these operations:
- `OpenFile` (`0x00452FB8`) accepts a UnicodeString and invokes internal archive-interface slot `+0x14`;
- `OpenStream` (`0x00452FDC`) accepts `IInStream`, creates an input-stream wrapper, and invokes the archive interface's open operation at `+0x0C`;
- `GetNumberOfItems`, `GetItemPath`, `GetItemName`, `GetItemSize`, and `GetItemProp` query archive entries;
- `ExtractItem`, `ExtractItems`, `ExtractAll`, and `ExtractTo` invoke the archive interface's extraction method.

`euResetMemory` constructs the reader and invokes the custom interface in this confirmed order: `+0x44` → `T7zArchive` constructor with the optional/fallback string; `+0x0C` → `OpenStream(IInStream)` with the first register argument; `+0x3C` → `SetPassword(UnicodeString)` with the second register argument. `SetPassword` then issues an all-items `IInArchive.Extract` request through its callback. The recovery-form Delete handler separately constructs a `.easd` path and proceeds into Word Automation. The exact input-stream construction, second string source, callback output/member path, archive format, and final `.easd` lifecycle remain open.

### What is now established vs. pending

Established:
- the recovery component is a SevenZip archive reader (T7zInArchive);
- the recovery path has a dedicated password-setting dispatch;
- the fallback string `mW@Tlogs43end_+` is passed to the `T7zArchive` constructor; its semantic role as a password is not yet proven;
- the reader exposes normal archive-open, entry-query, and extraction methods;
- .easz is the enumerated recovery-file mask under %TEMP%\\temp-emwatASwf\\.

Still pending:
- caller-side construction of the `IInStream` argument and source/meaning of the second UnicodeString;
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
- `T7zInArchive.SetPassword` (`0x00453860`) stores a UnicodeString at `Self+0x58`, creates a callback interface from `Self+8` using type-info `0x0045391C`, and invokes `IInArchive.Extract` (`+0x1C`) for all items. The direct custom-interface slot is `+0x3C`, not `+0x44`.
- In `euResetMemory` (`0x00456F00`), slot `+0x44` calls the `T7zArchive` virtual constructor with the optional/fallback string; slot `+0x0C` calls `OpenStream(IInStream)`; slot `+0x3C` calls `SetPassword(UnicodeString)`. The custom interface IID is `022cf785-3ece-46ef-9755-291fa84cc6c9` and its vtable is `0x00452420`.

### New direct caller evidence

The plugin constructor has a direct caller in `euUnArchive` (`0x00456E37`), which uses global `0x0062A824` and then operates on the returned object. This is a separate unarchive path from `euResetMemory`, which calls `CreateOutArchive` at `0x00452BBC`. Both paths use the shared SevenZip plugin layer, but they must not be collapsed into one identical operation until their GUIDs, input/output direction, and callback setup are decoded.

### Updated confidence

Confirmed: the 7z plugin wrapper, shared CreateObject factory, input/output wrapper methods, TObjectList initialization inside CryptoGetTextPassword2, and the distinct euUnArchive/euResetMemory entry paths.

Still unresolved: the input stream's caller-side construction, the source/meaning of the two strings passed through the constructor and `SetPassword`, callback type-info/output destination, the writer's actual password text/callback semantics, and the exact archive format/options used for `.easz`. The interface GUID and direction for the separate `euUnArchive` factory path also remain open.


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

The 20-slot interface table now proves the bindings: `+0x44` is the `T7zArchive` virtual constructor, `+0x0C` is `T7zInArchive.OpenStream(IInStream)`, and `+0x3C` is `T7zInArchive.SetPassword(UnicodeString)`. The helper's symbol is still `CreateOutArchive` even though it constructs `T7zInArchive`; preserve this naming/type discrepancy. Do not describe the second and third calls as `OpenFile`/`ExtractTo`: `SetPassword` itself calls `IInArchive.Extract` with a callback.

### Cleanup API targets independently resolved

- `0x004043BC` resolves to RTL `TDirectory.GetFiles`; the cleanup code enumerates `*.easz`.
- `0x004032B8` resolves to RTL `FileAge`; `0x00403330` resolves to `FileDateToDateTime`; `0x004033A0` resolves to `Now`; and `0x00404344` resolves to `HoursBetween`.
- The age comparison uses `0x18` hours (24 hours) before calling the file-delete helper. `0x004026B4` resolves to `kernel32!DeleteFileW`.
- These imports confirm the earlier cleanup interpretation; the exact archive format remains unverified.

### Confidence update

Confirmed: `euResetMemory` uses a custom `T7zInArchive` interface, opens an `IInStream`, and calls `SetPassword`, which issues an all-items `IInArchive.Extract` request through a callback. Still unproven: input-stream creation, the meaning of the two UnicodeStrings, callback output destination/member selection, exact `.easd` bytes/lifecycle, and archive format/options.


## 18. Separate euUnArchive helper path — 2026-11-15

Plugin follow-up run #2 (`43720247793`, artifact `14164382428`) traces the previously identified direct constructor caller `euUnArchive` (`0x00456DFC–0x00456EFF`).

- `euUnArchive` calls the `T7zPlugin` constructor at `0x00452C10) using global `0x0062A824`.
- It then calls object/interface slots `+0x28), `+0x10), and `+0x18). The function obtains a count from one of its collection-like arguments, iterates indices, retrieves corresponding values from two collection-like arguments through their slot `+0x0C), and passes those values to the plugin object's slot `+0x10). At the end it calls slot `+0x18) with the remaining path/context argument.
- The direct bounded caller scan for `euUnArchive` found no direct CALL sites. The T7zPlugin constructor's only direct bounded caller in this scan is `euUnArchive`.
- This is a distinct plugin-based multi-item extraction path. It is not the same call chain as `euResetMemory`, which uses the separate `CreateOutArchive` helper at `0x00452BBC) and calls slots `+0x44/+0x0C/+0x3C).

The exact meanings of the `euUnArchive` slots `+0x28/+0x10/+0x18), the two collection argument types, and the archive direction are not yet resolved. Keep it as a separate generic SevenZip operation; do not use it to infer the .easz recovery protocol.



## Appendix — supplemental SevenZip method-index findings (2026-11-15)

The completed class-index artifacts `14163436366`, `14163367757`, and `14164382428` include the full `T7zInArchive` and `T7zOutArchive` TD32 method indexes. The principal recovery conclusions are in sections 17–18; this appendix records additional wrapper details without changing those confidence labels.

### Reader wrapper details

- `T7zInArchive.GetInArchive` (`0x00452ED8`) initializes the internal archive-interface field at `Self+0x28` and calls `T7zPlugin.CreateObject` (`0x00452DB4`).
- `T7zInArchive.OpenStream` (`0x00452FDC`) creates an input-stream wrapper, obtains an item path through `GetItemPath` (`0x00452F08`), then invokes the resulting stream/interface method.
- `GetItemPath` lazily initializes the archive interface when `Self+0x28` is empty, then obtains the item path through the archive interface.
- `ExtractItem` (`0x004531D4`) forwards to the underlying archive interface's slot `+0x18`. `ExtractTo` (`0x0045375C`) configures transient extraction callback/context fields `+0x50/+0x54`, calls the archive interface's extraction slot `+0x1C`, and clears those fields on exit.
- `Close` (`0x00452DE8`) releases the internal archive interface when present.

### Writer wrapper details

- `T7zOutArchive` exposes `AddFile`, `AddFiles`, `AddStream`, `SaveToStream`, and progress/completion callbacks.
- `AddStream` (`0x00453FDC`) traverses a source collection, builds update-item records, and submits them to the underlying archive update interface. The trace shows a file/stream metadata path, but does not by itself establish which EMWAT caller creates recovery archives.
- `SaveToStream` (`0x00454668`) creates an output-stream wrapper and calls `SetCompleted` (`0x004546C4`).
- `T7zOutArchive.SetPassword` remains a stub; the constructor/callback path and the `TObjectList` created by `CryptoGetTextPassword2` do not yet reveal the actual writer password text or encryption settings.

These wrapper traces confirm the available archive operations, not the exact `.easz` container signature or the complete recovery writer configuration. Do not implement a format-specific reader/writer until the archive format and caller-supplied properties are verified.


## 19. `euResetMemory` interface identity resolved — 2026-11-15

The SevenZip interface-table artifact from plugin workflow run `43722345225` (artifact `14165136040`) establishes the concrete interface object used by `euResetMemory`:

- `CreateOutArchive` (`0x00452BBC`) constructs `T7zInArchive` using VMT `0x004525B0` (loaded from global `0x00452558`), then returns the interface pointer at `Self+0x70`.
- The `T7zInArchive` VMT has instance size `0x78` and interface table `0x00452474` with seven entries. Entry 6 has `IOffset=112 (0x70)`, matching the pointer returned by `CreateOutArchive` exactly.
- That entry's IID is `022cf785-3ece-46ef-9755-291fa84cc6c9` and its interface vtable is `0x00452420`.
- Therefore the three indirect calls in `euResetMemory` are confirmed to target this custom interface's vtable at slots `+0x44`, `+0x0C`, and `+0x3C`. This is a stronger result than merely correlating signatures with wrapper methods.

The 20-slot interface trace now resolves all three calls:

- `+0x0C` → thunk `0x004522E9` → `T7zInArchive.OpenStream` (`0x00452FDC`), whose signature accepts `Sevenzip.IInStream`. The first `euResetMemory` argument is therefore an input-stream interface.
- `+0x3C` → thunk `0x0045235F` → `T7zInArchive.SetPassword` (`0x00453860`), whose signature accepts a UnicodeString. It stores that string at `Self+0x58`, builds an extraction callback interface from `Self+8`, then calls the underlying `IInArchive.Extract` slot `+0x1C` with `indices=NULL`, `numItems=-1`, `testMode=0`, and that callback. This is an all-items extraction request; its exact callback/output semantics are still being traced.
- `+0x44` → thunk `0x00452373` → virtual constructor `T7zArchive.$bctr` (`0x0045392C`). It stores its UnicodeString argument at `Self+0x44` and sets the Boolean at `Self+0x40` according to whether the string is nonempty.

Thus `euResetMemory` receives an input stream in its first register argument, a password-like UnicodeString in its second register argument (passed to `SetPassword`), and an optional UnicodeString in its third register argument (passed to the base constructor, with fallback `mW@Tlogs43end_+` when selected). The exact meaning of the two string values and the extraction callback's output target remain open. `T7zInArchive.ExtractTo` (`0x0045375C`) is a separate wrapper that also calls the underlying archive interface `+0x1C`, but it is not one of the three direct `euResetMemory` slots.

`SetPassword` and `ExtractTo` use distinct callback type-info references: `SetPassword` passes `0x0045391C` to the interface-construction helper and uses the callback built from `Self+8`; `ExtractTo` passes `0x00453850`, first stores its two callback/context arguments in `Self+0x50/+0x54`, and then invokes the same underlying archive-interface slot `+0x1C`. `ExtractTo` sets the extraction `testMode` argument from its Boolean parameter (1 or 0), while `SetPassword` uses 0. Both pass `indices=NULL` and `numItems=-1` to the underlying `IInArchive.Extract` method. This method-name mapping is corroborated by `ExtractItem` and `ExtractTo` calling the same slot with their own item/test-mode arguments. The callback type metadata at `0x0045391C` and `0x00453850` is being inspected separately to identify the actual output/stream destination.
