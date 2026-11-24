# EMWAT SevenZip AutoSave archive analysis

Date: 2026-11-24  
Input: analysis-input/EmwatMethods.bpl1  
Method: TD32 procedure traces, class/interface metadata and bounded callsite analysis. Static evidence only.

## 1. Two separate archive operations

### Input: euUnArchive (0x00456DFC)

The controller-notify path calls this routine after the document Content-related operation. It creates/uses the SevenZip input wrapper, prepares archive-entry mappings, and invokes the extraction path using the supplied source and destination values.

The recovery picker enumerates the wildcard *.easz. The controller-notify code also builds/uses the .easd suffix. Current evidence supports .easz as the archive-listing extension and .easd as an extracted/intermediate document suffix; the exact full directory and all entry names remain unresolved.

### Output: euResetMemory (0x00456F00)

This is a distinct archive-writing helper, not the euUnArchive extraction path. Its bounded code:

1. Selects one of two global SevenZip plugin records based on a Boolean argument.
2. Creates the archive wrapper through the plugin.
3. Optionally calls the output object's vtable slot +0x44 with a supplied or default string.
4. Calls the output object's Open slot +0x0C with the destination path.
5. Calls the compression/property slot +0x3C with the supplied setting.

Its two direct callers are:
- Applicationactivities.Finalization at 0x00503779.
- TfrmShowAutoSaveFiles.Delete at 0x005EB938.

The recovery-form Delete routine calls euResetMemory before it builds a .easd path and starts a Word Automation close/open sequence. This shows the recovery UI performs archive rewrite/temporary-document work, but the exact transaction order and user-visible deletion semantics still need a complete caller trace.

## 2. Embedded password candidate and setter evidence

The same fixed 15-character UTF-16LE string (value intentionally omitted from this public analysis document) appears in two relevant places:

- euUnArchive at 0x00456E3C pushes the string and the archive object, then dispatches through object vtable slot +0x28 before it adds/extracts archive entries.
- euResetMemory uses the same string at 0x00456F7B as its default argument before dispatching the output object's +0x44 slot.

The class method T7zInArchive.SetPassword at 0x00453860 is implemented. It stores its UnicodeString argument at object offset +0x58 and then calls the underlying archive interface at offset +0x1C. This makes the fixed literal a **high-confidence archive-password candidate**. However, the exact VMT/interface slot mapping from the euUnArchive +0x28 dispatch to this method is not yet proven, so do not hard-code it into Linux until that mapping is confirmed.

Important counter-evidence/limitations:

- T7zOutArchive.SetPassword at 0x004547DC is a stub that returns immediately. Therefore euResetMemory's output +0x44 call is not proof that encryption is actually configured.
- T7zInArchive.CryptoGetTextPassword at 0x00453480 and SetPasswordCallback at 0x00453534 are short stubs that return zero without an evident output assignment.
- T7zOutArchive.CryptoGetTextPassword2 at 0x004543C4 initializes associated object/list state; its inspected body does not reveal a password output value.
- No controlled .easz archive has yet been tested for encrypted headers/data.

**Conclusion:** EMWAT passes a fixed password-like literal through archive object dispatch, but the observed setter/callback stubs mean actual encryption remains unproven. Keep password handling configurable and do not assume all .easz archives are encrypted.

## 3. Separate username-derived cleanup token

The helper euGetAutoSavePass at 0x00456B78 calls GetUserNameW with a 0x400-character buffer and returns the current Windows account name.

DoClearOldAutoSaveFiles at 0x00456C0C combines that result with a separate marker literal at 0x00456C78 in one branch. The helper is called from euClearOldAutoSaveFiles and the SendLog file-click path. This username-derived value has not been traced into the input archive's SetPassword method or the output archive callback; do not conflate it with the fixed archive-password candidate above.

## 4. Recovery file paths and retention

- The recovery form resource contains *.easz and a date/time display pattern.
- euGetLocalAppDataPath passes CSIDL 0x1C to the shell-folder helper, consistent with Local AppData; the complete subdirectory is not yet resolved.
- euClearOldAutoSaveFiles enumerates *.easz and conditionally calls DeleteFileW after comparing file-age/time values against 0x18. The exact age unit and retention policy are still unknown.
- .easd is used by the recovery form's temporary-document path construction. Its complete creation/open/delete lifecycle needs confirmation.

## 5. Required next traces

1. Resolve the concrete class/interface identity behind euUnArchive's vtable +0x28 dispatch and prove whether it lands on T7zInArchive.SetPassword.
2. Resolve the output archive's +0x44 dispatch and confirm why the named T7zOutArchive.SetPassword implementation is a no-op.
3. Capture one synthetic Windows .easz file and inspect its 7z header, encryption flags, entry names, timestamps and data encryption using 7-Zip tooling.
4. Trace euResetMemory callers in Applicationactivities.Finalization and TfrmShowAutoSaveFiles.Delete with their full argument setup.
5. Resolve the full Local AppData directory and retention-age units.

## 6. Linux implementation guidance

- Keep input extraction, output archive creation, cleanup and UI restore as separate operations.
- Preserve both .easz and .easd as distinct observed suffixes.
- Do not copy a suspected password literal into the Linux implementation before dispatch and archive-header behavior are verified.
- Do not add encryption to the Linux recovery store solely because a setter is called; the output setter is currently a stub.
- Use synthetic test archives and never commit real customer documents or signature payloads.
