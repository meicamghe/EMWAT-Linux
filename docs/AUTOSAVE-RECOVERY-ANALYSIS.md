# EMWAT AutoSave and recovery path analysis

Date: 2026-11-16

## Confirmed controller notification path

The TD32 trace of `TWordViwer.OnControlerNotify` at `0x004BB3B0–0x004BB777` and its string references establish that this is an AutoSave/recovery path:

- Fixed log string at `0x004BB6CC`: `AutoSave. EmwatAutoSaveDOC.Execute called.`
- The handler checks its internal state and the controller notification structure before entering the main branch.
- It toggles internal flags at viewer offsets `+0x79` and `+0x5E`.
- It calls `TWordViwer.CostumizeRecAndCC` at `0x004D281C`.
- It passes `-1` and the document interface stored at viewer `+0x48` to COM vtable slot `+0xDC`. The generated wrapper at `0x0042BDF8` identifies this slot as `TWordDocument.Get_Content`; this retrieves the document Content range and is not `Close` or `Save`.
- It subsequently processes path values through `FixDirectionInFarsiNumericMode` at `0x004563A8` and `euUnArchive` at `0x00456DFC`.

## Recovery file extensions

String decoding confirms:

- `0x004BB754`: `.easd`
- `0x004BB76C`: `.easz`

This matches the previously identified recovery subsystem that enumerates `*.easz` archives and extracts temporary `.easd` documents. The helper `0x00456DFC` is named `Emwatutils.euUnArchive`; its disassembly iterates archive entries and extracts them to the supplied destination. It is an extraction path, not an archive-creation routine.

## Method request dictionary

The TD32 symbol at `0x005EE82C` is `TScanDocument.PerformMethod`. It invokes `TWordViwer.LoadDocument` at `0x004B7724` and the decoded parameter keys are:

- `wordConfig`
- `wordBody`
- `letterImages`
- `signData`

The fixed validation message for a missing `wordConfig` is `Requset XML is not valid (wordConfig parameter is null)`.

## Important separation

The AutoSave/recovery handler and the final Almas correspondence registration must be treated as separate operations until a network trace proves otherwise. The controller-notify method's explicit AutoSave log and the `.easd/.easz` outputs prove local recovery activity; they do not prove the final HTTP request or response that registers the edited letter in Almas.

## Next trace targets

1. Trace the callers and archive-entry contract of `euUnArchive` at `0x00456DFC` to determine which of `.easz` and `.easd` is source versus destination.
2. Validate the exact string transform in `FixDirectionInFarsiNumericMode` at `0x004563A8`.
3. Trace the AutoSave callback's surrounding controller message and data source; the COM slot `+0xDC` is already mapped to `Get_Content`.
4. Continue searching for the final POST/response after the Word editor closes; do not infer the Almas registration payload from local AutoSave artifacts.


## Separation from the actual Word close callback

Generated Word wrapper traces map the relevant COM slots:

- `TWordDocument.Get_Saved` at `0x0042BD34` → `_Document` slot `+0xD4`.
- `TWordDocument.Set_Saved` at `0x0042BD94` → `_Document` slot `+0xD8`.
- `TWordDocument.Get_Content` at `0x0042BDF8` → `_Document` slot `+0xDC`.
- `TWordDocument.Save` at `0x004309A4` → slot `+0x2B8`.
- `TWordDocument.Close` overloads at `0x0042FF08` / `0x0042FF7C` / `0x0042FFF4` → slot `+0x29C`.

Therefore the `+0xDC` call inside `OnControlerNotify` is definitively a Content getter. It must not be reported as closing or saving the document. The separate `WordAppDocumentBeforeSave` callback at `0x004CD154` is the path that contains the user prompt and the COM Close dispatch; keep its lifecycle analysis separate from this local AutoSave/recovery routine.


## SevenZip archive creation versus extraction — 2026-11-16

Source: recovery-plugin workflow run 43815900302, artifact 14203070675.

### euUnArchive: input archive extraction

The routine at 0x00456DFC is Emwatutils.euUnArchive. It creates a T7zPlugin input/archive object, opens the supplied archive stream, enumerates archive entries, obtains each entry's metadata and content stream, and writes extracted entries through the supplied destination stream. This is the local extraction path used by the controller AutoSave/recovery handler.

### euResetMemory: output archive creation

The routine at 0x00456F00 is Emwatutils.euResetMemory. It creates a T7zOutArchive object using one of two global SevenZip class/plugin records selected by its first boolean argument. It then:
1. calls the output archive's SetPassword slot (+0x44) with the supplied/default string;
2. calls Open (+0x0C) with the output path;
3. calls the output archive's compression-setting slot (+0x3C).

Its only direct bounded callers are:
- Applicationactivities.Finalization at 0x00503779;
- TfrmShowAutoSaveFiles.Delete at 0x005EB938.

This is archive creation, not the euUnArchive extraction path.

### Password behavior is not proven

The output archive method T7zOutArchive.SetPassword at 0x004547DC is a stub: it returns immediately without storing or forwarding the supplied string. Therefore the string passed by euResetMemory is not proven to configure output encryption through this method.

The input archive method T7zInArchive.SetPassword at 0x00453860 is implemented: it stores the supplied UnicodeString at object offset +0x58 and calls the underlying SevenZip interface at slot +0x1C. However, the bounded direct-call scan found no direct CALL xref to this method; an indirect/VMT call remains possible.

T7zOutArchive.CryptoGetTextPassword2 at 0x004543C4 initializes an associated callback/interface object and clears adjacent state fields, but this trace does not reveal a literal password value. The fixed 15-character literal used by euUnArchive is now a high-confidence archive-password candidate: it is passed to the archive object's +0x28 virtual dispatch, and T7zInArchive.SetPassword at 0x00453860 stores its UnicodeString input at object offset +0x58. The exact +0x28-to-SetPassword mapping is not yet proven. The separate @25*gamsign*25@ marker is combined with the Windows username by DoClearOldAutoSaveFiles and has not been traced into that input SetPassword path. The output T7zOutArchive.SetPassword method is a stub, so actual encryption remains unproven. See [the detailed SevenZip analysis](SEVENZIP-ARCHIVE-ANALYSIS.md).

### Linux implications

- Keep archive creation and extraction as separate adapter operations.
- Do not add password encryption to the Linux recovery archive based only on euResetMemory's SetPassword call; the output SetPassword implementation is a no-op.
- Keep the input archive password optional and unresolved until the indirect SetPassword call or CryptoGetTextPassword2 output is traced.
- Preserve .easd and .easz as distinct observed suffixes; the exact mapping between archive and extracted document roles still needs caller-level validation.


## Parallel trace update — close decision versus AutoSave content (2026-11-24)

Fresh TD32 artifacts from the Word request-lifecycle and response workflows clarify two paths that must remain separate:

### 1. AutoSave/controller-notify path

At `TWordViwer.OnControlerNotify` (`0x004BB3B0`), the code pushes `-1`, pushes the document interface at viewer offset `+0x48`, then calls vtable slot `+0xDC`. The generated `TWordDocument.Get_Content` wrapper at `0x0042BDF8` maps that slot to the Content getter. Therefore the call is a Content-related operation, not a Document.Close call. The literal `-1` is passed at this callsite, but its precise meaning/ABI role remains unresolved; do not interpret it as SaveChanges.

The handler then performs the Farsi-direction transform and calls `euUnArchive` (`0x00456DFC)) using the `.easd/.easz` path values. This is the local AutoSave/recovery branch. It is not, by itself, proof that the edited letter has been registered in Almas.

### 2. User-facing BeforeSave decision

The separate `TWordViwer.WordAppDocumentBeforeSave` callback at `0x004CD154` contains the Persian prompt:

> محتويات اين سند تغيير كرده است. آيا مايل به ثبت تغييرات مي‌باشيد؟

The three button captions are `موافقم`, `خیر`, and `انصراف`. The code checks the dialog result as follows:

- Result `2` (Cancel): writes `-1` to the COM event's Cancel flag and exits the save/close path.
- Result `6` (Yes): prepares `-1` as the SaveChanges argument for a later Document.Close dispatch at vtable slot `+0x29C`.
- Other non-cancel result (the No branch): prepares `0` as SaveChanges for that Document.Close dispatch.

The `-1` / `0` mapping is consistent with Word's `wdSaveChanges` / `wdDoNotSaveChanges` values. This is static callsite evidence for the prompt's Yes/No/Cancel behavior, not a runtime test of every Word version.

### 3. HTTP response boundary

The LoadDocument path contains an Indy `TIdHTTPResponseInfo.WriteContent` call and a response-construction branch. The remaining question is how the controller-notify completion releases the original long-lived `invoke` request and which returned payload Almas consumes. Keep that separate from the local `.easz` recovery artifact.

**Implementation consequence:** Linux must model the close decision as a three-way state transition. Do not collapse No and Cancel: No closes without Word saving; Cancel vetoes the operation. Local recovery may still be a separate operation and must not be conflated with the final Almas registration response.
