# Windows EMWAT .easz archive: evidence and Linux compatibility boundary

## Confirmed static-analysis findings

The reverse-engineering notes in `docs/SESSION-HANDOFF.md` record the following findings from the Windows EMWAT BPL analysis:

- The observed archive path constructs a 7z output-archive writer and exposes a method named `CryptoGetTextPassword2`. The currently resolved method body initializes an internal object list; static evidence has not yet established a returned password value or its provider. The callback name alone does not prove that encryption is enabled.
- The source file passed to the archive writer is the temporary document path held by the Word viewer (field `+0xA0`).
- The archive entry name is derived from the viewer base path (field `+0x80`) with the `.easd` suffix.
- The output file path uses the same base path with the `.easz` suffix.
- The archive writer's `SaveToStream` path creates/truncates the `.easz` file using a file stream opened with `fmCreate`.
- The analyzed output class exposes `CryptoGetTextPassword2`, while the mapped `SetPassword` implementation appears ineffective. The global password source, call ordering, encryption flags and actual runtime behavior remain unverified.

These findings identify a 7z archive-writing path containing the temporary document under an `.easd` entry name. They do not yet establish that the emitted archive is encrypted in the captured runtime configuration. The helper name `euUnArchive` is misleading for this observed path: the traced operation writes an archive.

## What is not implemented or proven on Linux

- The Linux recovery store uses its own DOC/DOCX snapshot plus JSON manifest format, separate from the Windows `.easz` container.
- The Linux store supports opt-in AES-256-GCM encryption when the application injects an externally managed 32-byte key; its default configuration remains plaintext.
- The Linux store does **not** read or write Windows `.easz` archives.
- Whether a particular Windows `.easz` file is encrypted, the password value/derivation/encoding, archive header/encryption parameters, entry metadata, and exact 7z compatibility profile have not been validated with a captured synthetic archive.
- No claim is made that a generic 7z command or library can reproduce all EMWAT-specific behavior.

## Safe implementation sequence

1. Obtain an authorized, synthetic Windows test archive with no customer document or personal data.
2. Record only non-sensitive metadata: 7z signature/header properties, entry names, compression/encryption flags, sizes, and password handling behavior.
3. Verify archive extraction and creation independently with a known test password and synthetic DOC payload.
4. Implement a dedicated adapter behind a format-specific interface; do not mix Windows archive compatibility into the Linux recovery store's existing manifest format.
5. Add cross-platform fixtures and negative tests for wrong password, corrupt header, missing entry, path traversal, oversized expansion, and unsupported archive features.
6. Keep Linux-native recovery usable when the optional Windows archive adapter is unavailable.

Until those tests exist, describe `.easz` support as reverse-engineering evidence only, not as a working Linux feature.


## 2026-11-24 — reader-side password callback cross-check

Source: workflow run 45343331334, artifact 14896429368.

The additional TD32 trace covers the **input** SevenZip wrapper (`T7zInArchive`), not the output archive writer:

- `T7zInArchive.CryptoGetTextPassword` at `0x00453480` is a 9-byte stub whose body returns zero and does not populate a password output value.
- `T7zInArchive.SetPasswordCallback` at `0x00453534` is likewise a 9-byte stub returning zero without storing a callback.
- `T7zInArchive.SetPassword` at `0x00453860` copies a supplied UnicodeString into object field `+0x58`, then invokes an interface method through the object stored at `+0x28`. The direct TD32 caller scan found no direct CALL site; VMT/interface invocation or another registration path remains possible.
- `euGetAutoSavePass` at `0x00456B78` has two direct callers in the analyzed module: `DoClearOldAutoSaveFiles` and `TfrmSendLog.lblFileNameClick`. Neither is the traced `OnControlerNotify` archive-writer path. Therefore this helper is **not yet evidence** for the password used by the `.easz` writer.
- The reader-side stubs do not resolve whether the output-side `T7zOutArchive` enables encryption. Do not infer that Windows archives are plaintext or encrypted from these input-class methods.

The recovery form's `TfrmShowAutoSaveFiles` is also a distinct subsystem. Its `Delete` path iterates selected list entries and initializes a Word Automation wrapper; its `CloseWordApp` method iterates Word documents and invokes a late-bound interface slot. The exact restore/delete filename and archive password contract still needs the helper-path and output-writer traces.

**Conclusion:** the password question remains open, but the reader-side analysis rules out treating `euGetAutoSavePass` as a proven `.easz` password source. A controlled synthetic archive is still required to settle encryption and interoperability.


## 2026-11-24 — extraction path and password/write-side limits

Sources: workflow runs 45343331334 (SevenZip callback/class trace), 45344189109 (recovery UI/path trace), and 45345628398 (OnControlerNotify path).

- `TWordViewer.OnTmrAutoSave` assigns `OnControlerNotify` as the timer event handler and clamps the timer interval to at least 10 seconds. The callback constructs `.easd` and `.easz` path variants and calls `euUnArchive`.
- `euUnArchive` creates a `T7zPlugin`, obtains an input archive interface, enumerates archive entries, gets item paths and extracts entries. This is the concrete AutoSave-side archive **read/extract** path.
- `euArchive` at `0x00456DDC` is not an archive writer; the bounded trace shows a `TStringList` construction/helper path used by the recovery UI.
- `T7zInArchive.CryptoGetTextPassword` and `SetPasswordCallback` are 9-byte stubs that do not populate a password value. `T7zInArchive.SetPassword` does store a supplied UnicodeString at object offset `+0x58`, but no direct caller was found in the traced AutoSave extraction path.
- `euGetAutoSavePass` has two direct callers: `DoClearOldAutoSaveFiles` and `TfrmSendLog.lblFileNameClick`. It is not proven to supply the `.easz` archive password.
- `T7zOutArchive` exposes output-side methods such as `AddFile`, `AddStream`, `SaveToFile` and `SaveToStream`, but no direct application callsite from the AutoSave callback was identified. Its `Password` property setter (`0x004547DC`) is a stub. `CryptoGetTextPassword2` (`0x004543C4`) has a nontrivial bounded body that initializes a helper object/fields, but no explicit password string assignment is visible. `GetOutArchive` has no direct application caller in the analyzed call graph.

**Conclusion:** the input/extraction path is established; the component that actually creates or updates `.easz`, the password source, encryption flags and exact internal entry mapping are still unknown. Do not claim that the observed `T7zOutArchive` wrapper is the active writer merely because its methods exist.


## 2026-11-24 — hardcoded input-archive password and writer boundary

Source: workflow run 45347505914 (controller-content-unpack / SevenZip trace).

The `euUnArchive` helper at `0x00456DFC` creates a `T7zPlugin` and passes a hardcoded 15-character Unicode string at VA `0x00456EE0` to the plugin's virtual method at slot `+0x28` before enumerating/extracting entries. This is strong evidence that the input-archive acquisition path supplies a built-in archive password. The literal is intentionally **redacted from this public document**; it should not be copied into logs, test fixtures or public commits.

The helper then obtains the archive item count, iterates item paths from the supplied lists, invokes the plugin extraction method at slot `+0x10`, and closes through slot `+0x18`. The `.easd` and `.easz` strings are constructed by the timer callback before this call.

Writer-side distinction:
- `T7zOutArchive.SaveToStream` creates a `TFileStream` and calls its completion/update path; this is a real output-side callback implementation.
- `T7zOutArchive.SaveToFile` at `0x00454644` is only a short metadata/out-parameter routine in the bounded trace, not proof of an application-level archive write.
- `T7zOutArchive.SetPassword` at `0x004547DC` is a 9-byte stub.
- The `T7zOutArchive` class exposes output methods, but no application-level call chain from the AutoSave callback to `GetOutArchive/SaveToStream` has been proven.
- `T7zInArchive.SetPassword` is implemented; the exact virtual path from the hardcoded argument to that setter remains to be traced.

**Conclusion:** the built-in input-archive password argument is now identified (literal redacted), and extraction is confirmed. The actual `.easz` writer call chain and output encryption behavior remain unresolved.


## 2026-11-24 correction — output archive helper identified

A separate trace now identifies `euResetMemory` at `0x00456F00` as an output-archive helper. It selects one of two SevenZip plugin records, creates an output wrapper, dispatches an output-object method at slot `+0x44` with a supplied/default string, opens the destination path through slot `+0x0C`, and applies a compression/property value through slot `+0x3C`. Direct callers are `Applicationactivities.Finalization` and `TfrmShowAutoSaveFiles.Delete`.

This supersedes the earlier statement that no output helper had been identified. The helper is now known, but the exact output-object class and the +0x44 method identity remain unresolved. The same fixed 15-character string is supplied in both the input `euUnArchive` path and the output `euResetMemory` path; this is a password candidate, not proof that output encryption is active.

The SevenZip callback trace also shows `T7zOutArchive.SaveToStream` creates a `TFileStream` and calls its completion/update path. `T7zOutArchive.SetPassword` remains a stub, so the output password/encryption behavior must be proven from the +0x44 dispatch and a synthetic archive header. See [the detailed SevenZip analysis](SEVENZIP-ARCHIVE-ANALYSIS.md).


## 2026-11-24 — output archive wrapper is constructed but writer calls remain unreferenced

The expanded SevenZip TD32 graph clarifies why the output side remains unresolved:

- `T7zPlugin.Create` at `0x00452C10` constructs a `T7zOutArchive` callback/wrapper through `0x004543C4` and stores the resulting object at plugin offset `+0x44`. This occurs during plugin construction, including the input-archive path.
- The output class has methods `GetOutArchive` (`0x00454450`), `SaveToStream` (`0x00454668`), `SaveToFile` (`0x00454644`), `AddFile`, `AddStream`, `AddFiles` and `CrearBatch`.
- The TD32 direct-caller scans report **zero application-level direct callers** for `GetOutArchive`, `SaveToStream`, `SaveToFile`, `AddFile` and `CrearBatch`. `AddStream` is called only internally by the output class's own `AddFiles`/`CrearBatch` paths.
- `SaveToStream` itself creates a temporary `TMemoryStream` and calls `SetCompleted`; this describes a library capability, not proof that EMWAT invokes it.
- `T7zOutArchive.SetPassword` at `0x004547DC` is a nine-byte no-op routine (`xor eax,eax; ret 8`). No output password-setting callsite has been identified.

**Conclusion:** the SevenZip output wrapper is instantiated as part of `T7zPlugin`, but the bounded application call graph does not reach its archive-writing methods. This makes the current output-writer path a library capability without a proven EMWAT caller. It does not prove that no writer exists elsewhere: another module/process or an indirect interface dispatch may create the `.easz` file.

Next trace:
1. Search indirect/VMT/interface references to the `T7zOutArchive` object stored at plugin offset `+0x44`.
2. Inspect all writes/renames of `.easz`/ `.easd` paths outside the SevenZip unit.
3. Correlate a real Windows-created `.easz` file with the responsible process and file-I/O callsites.
