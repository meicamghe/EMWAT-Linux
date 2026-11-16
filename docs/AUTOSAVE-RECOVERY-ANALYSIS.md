# EMWAT AutoSave and recovery path analysis

Date: 2026-11-16

## Confirmed controller notification path

The TD32 trace of `TWordViwer.OnControlerNotify` at `0x004BB3B0–0x004BB777` and its string references establish that this is an AutoSave/recovery path:

- Fixed log string at `0x004BB6CC`: `AutoSave. EmwatAutoSaveDOC.Execute called.`
- The handler checks its internal state and the controller notification structure before entering the main branch.
- It toggles internal flags at viewer offsets `+0x79` and `+0x5E`.
- It calls `TWordViwer.CostumizeRecAndCC` at `0x004D281C`.
- It passes `-1` and the document interface stored at viewer `+0x48` to COM vtable slot `+0xDC`. The exact method represented by this slot is not yet proven.
- It subsequently processes two path values through `FixDirectionInFarsiNumericMode` at `0x004563A8` and helper `0x00456DFC`.

## Recovery file extensions

String decoding confirms:

- `0x004BB754`: `.easd`
- `0x004BB76C`: `.easz`

This matches the previously identified recovery subsystem that enumerates `*.easz` archives and extracts temporary `.easd` documents. The helper `0x00456DFC` is the next target to determine whether it creates, packages, renames, or registers these paths.

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

1. `0x00456DFC` — two-path helper used after the controller-triggered COM action.
2. `0x004563A8` — Farsi numeric/direction transform applied to the path values.
3. Compare COM slot `+0xDC` with generated `TWordDocument.Close` and `TWordDocument.Save` wrappers.
4. Continue searching for the final POST/response after the Word editor closes; do not infer the Almas registration payload from local AutoSave artifacts.
