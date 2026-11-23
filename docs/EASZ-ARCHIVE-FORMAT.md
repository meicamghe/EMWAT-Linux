# Windows EMWAT .easz archive: evidence and Linux compatibility boundary

## Confirmed static-analysis findings

The reverse-engineering notes in `docs/SESSION-HANDOFF.md` record the following findings from the Windows EMWAT BPL analysis:

- The observed archive path constructs a 7z output-archive writer. Static analysis identifies a password-retrieval callback path (`CryptoGetTextPassword2`) that reads a global password value; this alone does not prove that encryption is enabled for every archive produced.
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
