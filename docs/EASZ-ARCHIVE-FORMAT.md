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
