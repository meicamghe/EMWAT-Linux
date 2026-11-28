# REA-assisted reverse-engineering plan — 2026-11-28

## Purpose

Use [Reverse Engineer Anything (REA)](https://github.com/morluto/rea) as an optional analyst-side tool to accelerate evidence collection for EMWAT-Linux. REA is not a runtime dependency of EMWAT-Linux and must not be bundled into the desktop application.

The target is behavioral compatibility with EMWAT/Almas on Linux, not a superficial port of Windows implementation details.

## Current repository boundary

- Work branch: `work/parallel-closure-2026-11-28`
- Integration PR: [#6](https://github.com/meicamghe/EMWAT-Linux/pull/6), Draft, targeting `feature/recovery-retention-policy`.
- The GTK entry point now composes the loopback BridgeSupervisor through `python/src/emwat_linux/deployment.py`.
- This is implementation evidence only. Real Almas acceptance and persistence remain unverified.
- The native Windows artifacts and sanitized PCAP are the evidence sources. A REA report is secondary analysis and must retain links/hashes to its input artifact.

## REA work lanes

### A. Native Delphi / PE lane

Use REA's binary-analysis capabilities where supported to independently inspect:

- `TEditWordDocument.PerformMethod` at `0x005EE82C`, its VMT dispatch and the `TWordViwer.LoadDocument` call path.
- `TWordViwer.LoadDocument` signData handling around `0x004B7AEB–0x004B7B2F`.
- XMLRTL helper callsites and Variant/interface ownership.
- GDI+ Save / SaveAdd / Flush call sequence and TIFF encoder parameter lifetimes.
- GAM printer queue, monitor DLL and sentinel producer/consumer boundaries.

For every finding record: input SHA-256, tool/version, image base, address/RVA, raw disassembly or pseudocode reference, caller/callee evidence, and confidence. Never accept a symbol label alone when the actual ABI/callsite disagrees.

### B. PCAP / protocol lane

Use REA packet inspection to correlate the sanitized Windows capture with the Linux bridge:

- POST path and numeric invoke nonce.
- Content-Type, Origin, Referer and request parameter inventory.
- Response status, XML envelope, MIME type and Base64 CFB payload.
- TCP sequence gaps and missing payload bytes.

Keep the existing capture limitation visible: the known successful response has 17 TCP gaps / 68 missing payload bytes. A reconstructed or gap-filled response must not be represented as a byte-exact Windows capture.

### C. Runtime and filesystem lane

If a controlled Windows runtime trace becomes available, record:

- Process tree and thread lifecycle around Writer open/close.
- File creation/deletion and the exact output paths used by the print worker.
- Queue transitions, TIFF page files and `JobFinishes.GAM` sentinel behavior.
- Scanner acquisition calls and page-file ownership.

REA runtime observation cannot replace a real Windows/Almas fixture. Do not infer a producer or consumer solely from temporal correlation.

## Evidence-to-implementation contract

Each REA-derived result must be stored as a small reproducible artifact under a dedicated analysis report, not copied directly into production code. The report must contain:

| Field | Required content |
| --- | --- |
| Input | Artifact name and SHA-256 |
| Tool | REA revision/version and backend used |
| Location | File offset, VA/RVA, packet number or runtime event |
| Observation | Raw evidence plus concise interpretation |
| Cross-check | Independent callsite, import, PCAP or runtime corroboration |
| Confidence | Confirmed / strong / tentative / unresolved |
| Linux consequence | Exact test or implementation change justified by the evidence |

If REA's output conflicts with existing direct VMT, call-ABI, import-table or PCAP evidence, preserve both observations and resolve the discrepancy. Do not silently overwrite the established evidence.

## Immediate experiments

1. Verify REA's current install/runtime prerequisites and supported binary-analysis backends in a disposable analyst environment.
2. Run a read-only pilot against the existing EMWAT PE/BPL artifacts; do not execute the Windows binary as part of static analysis.
3. Compare REA output for the WordViewer loader, XMLRTL helpers and GDI+ thunks against the existing address-level crosswalks.
4. Run a read-only pilot against the sanitized PCAP and compare request/response metadata with the current protocol report.
5. Keep only reproducible, independently corroborated findings; record unsupported backend operations as limitations.

## Safety and scope

- No Windows application execution, printer installation, registry mutation or user-data access is implied by this plan.
- Do not upload unsanitized documents, cookies, credentials, personal data or proprietary payloads to an external model/provider.
- REA is an analysis aid, not a source of ground truth and not a replacement for live Almas acceptance.
- Do not add REA to Python/native package dependencies.
- Do not mark signData, TIFF, printer, scanner or XMLRTL parity complete until their independent acceptance criteria pass.

## Completion criteria

The REA pilot is useful only if it produces at least one reproducible, cross-checked finding that either closes a currently unresolved native question or yields a deterministic Linux regression fixture. Otherwise keep REA optional and continue with the existing scripts/workflows.


## REA Delphi/Ghidra compatibility finding — 2026-11-28

A current-source review of REA adds an important implementation constraint:

- REA's Ghidra provider supports native analysis on Linux x64/arm64 with an existing compatible Ghidra installation and full JDK; the Linux process supervisor also requires a procps-compatible system `ps`. REA does not install Ghidra or Java. Exact version requirements must be taken from the selected REA release's installation guide and verified with `rea doctor --json`, because the current `main` guide and the tagged `rea-agents-6.5.0` guide have different Ghidra/JDK minimums.
- REA issue [#2811](https://github.com/morluto/rea/issues/2811) is still an open/proposed feature request for a provider-free Delphi VMT/class/method/field parser. The issue explicitly states that REA has no built-in Delphi VMT parser in the described 6.4.0 environment. Do not assume a native Delphi symbol-recovery tool is already available.
- The issue demonstrates an external-parser-to-Ghidra path: generate a seed file and set `REA_GHIDRA_SEED_FILE`. The documented seed line format is `address<TAB>kind[<TAB>name]`; for named methods use `function` plus the recovered class/method name. Ghidra applies seeds before auto-analysis. The seed digest is part of the analysis profile and failed/overlapping seeds are reported rather than silently accepted.
- The issue's author reports a Delphi 7 PE32 experiment where an external VMT parser produced 1,610 published method labels and Ghidra imported all 1,610 with zero failures. This is evidence that the seed mechanism can work for one sample, not proof of compatibility with EMWAT's exact compiler/runtime.
- `REA_GHIDRA_COMPILER_SPEC_ID=borlanddelphi` was tested in that report against five pseudocode outputs and was byte-identical for those five only. Treat it as a controlled experiment, not a default to apply without checking Ghidra's installed language catalog and EMWAT's compiler profile.

### Revised EMWAT-specific pilot

1. Preserve the exact EMWAT PE/BPL SHA-256 and verify PE32 image base and section mapping before opening the target in Ghidra.
2. Run the selected REA release's doctor/provider checks first; do not install or mutate the user's analysis host from this repository workflow.
3. Use an external, read-only Delphi VMT parser only after validating the actual layout against multiple structural invariants (self pointer, class-name string, parent pointer, and method/field table bounds). Record VA, RVA and file offset separately.
4. Do not assume Delphi 7 merely because the target is PE32. First test candidate VMT anchors against known class/method addresses from the existing EMWAT disassembly and the actual VMT metadata.
5. Emit a seed file only for method entries whose code address is validated as an executable PE mapping. Keep class/field metadata in a separate report; do not turn arbitrary field addresses into function seeds.
6. Import the original PE into an isolated Ghidra project through REA, apply the seed file, and compare the recovered names and call graph around `TWordViwer.LoadDocument`, `TEditWordDocument.PerformMethod`, and the Word close callback against the existing static crosswalks.
7. Keep all seed lines, parser version, input digest, Ghidra/REA versions, rejected candidates and collision counts as a reproducible analysis artifact.

### What this does not close

- REA has not been run against the EMWAT PE/BPL in this work session.
- The Delphi compiler/VMT layout for the exact EMWAT binary is not yet proven.
- No EMWAT class count, method count, or newly recovered symbol is claimed.
- This is an analyst-side workflow only; REA remains outside EMWAT-Linux runtime dependencies.

Primary references: [REA README](https://github.com/morluto/rea), [REA Ghidra provider](https://github.com/morluto/rea/blob/main/docs/providers/ghidra-provider.md), [REA installation guide](https://github.com/morluto/rea/blob/main/docs/getting-started/installation.md), [REA Delphi VMT issue #2811](https://github.com/morluto/rea/issues/2811).


### EMWAT VMT profile cross-check from existing artifacts

The current EMWAT artifact set already contains a candidate Delphi class metadata record for `TScanCommand` at `0x004F1F94` (scanner artifact `15263439921`):

- The existing repository script `tools/resolve_delphi_vmt_slots.py` explicitly documents and uses a later Win32 layout: self pointer at VMT `-0x58`, class-name field at `-0x38`, instance size at `-0x34`, and parent pointer at `-0x30`.
- The candidate record at `0x004F1F94` has a matching self pointer, class-name target `0x004F20D7` decoding to `TScanCommand`, instance size `0x40`, and parent pointer `0x0062EEA4`. Address `0x004F1F3C` is not a second/false VMT candidate: it is the self-pointer slot at `VMT-0x58`, whose stored value is `0x004F1F94`.
- The field-table pointer is `0x004F1FB6`; its raw target bytes contain candidate names such as `ImgProc`, `Options`, `ResultImage`, `FEditorForm`, `FCommandState`, `FIsNextPageRequest`, `FPreviousReturnedFileName`, `FRequestXML`, `FResponseXML`, and `FHasConstratints`, alongside type/offset metadata. The exact extended field-table record layout has not yet been parsed and cross-validated; use independent field-reference scans for offsets until then.
- The method-table pointer is `0x004F20B9`, and the current parser reads its leading count as zero. Bytes following that count also contain other RTTI/type metadata and are not yet safely attributable to method entries. Do not call them recovered method records or infer a parser bug until the table boundary/layout is independently established.

This is a material profile warning: REA issue #2811 discusses Delphi 2–2007 Win32 VMT recovery, while the existing EMWAT script targets a later Win32 VMT layout. Do not apply the issue's Delphi 7 offsets blindly to EMWAT. The exact compiler version is still not conclusively identified; the current later-layout candidate is a working profile backed by repository evidence, not a complete compiler fingerprint.

Next VMT step: reconcile the raw method-table and field-table record formats against this exact `TScanCommand` candidate, validate the same negative-offset layout against at least two unrelated classes, then emit only executable method-entry seeds. Keep the zero-entry method-table parse as an explicit unresolved discrepancy.


## Actual EMWAT BPL pilot with undelphi — 2026-11-28

- The read-only `tools/undelphi_probe` was executed against the committed `analysis-input/EmwatMethods.bpl1` (SHA-256 `6ff7d262f46ab009e3eecf20fca40cd41ec8ad937adf7bbfe2f6eddd56aaea2d`).
- undelphi 0.5.1 identified Delphi 10 Seattle, compiler version 30.0, Win32, with high confidence.
- The probe recovered 526 classes, 3,862 extended methods, 1,192 extended fields and emitted 3,834 unique in-.text method seeds in `rea-method-seeds.tsv`.
- This is a successful independent parser run, **not** an execution of REA itself. REA/Ghidra still needs to consume the seed file.
- VMT address convention is now reconciled: undelphi reports the VMT header start `0x004F1F3C` for `TScanCommand`; the class pointer used by `inspect_delphi_vmt_address.py` is `0x004F1F94`, stored in the self-pointer slot at header offset `+0x58`. `0x004F1F3C` is not a false second candidate.
- The TScanCommand extended field table parses into ten typed field entries, and its extended method metadata contains Create/Destroy/DoRequest. The legacy published-method-table count of zero is not evidence that the class has no methods; Delphi 10 extended method metadata is separate.
- `TWordViwer` metadata identifies VMT header `0x004B104C`, instance size `0x11C`, and the state fields documented in `WORD-AUTOMATION-CLOSE-SAVE-EVENT-CROSSWALK-2026-11-28.md`.
- The separate TD32 symbol pass is now implemented in `tools/emit_td32_ghidra_seeds.py`: 8,411 executable procedure addresses were parsed with no ambiguous addresses, then merged with the 3,834 undelphi RTTI seeds into 8,411 combined addresses. The Word/scan index contains 859 relevant procedures. Artifact: workflow run `46153451750`, artifact `15265729959`. Next import `rea-combined-seeds.tsv` into REA/Ghidra.


### TD32 seed merge result — 2026-11-28

- TD32 stream: 204 directory entries, 8,411 procedures parsed, 8,411 validated executable addresses, zero ambiguous addresses.
- undelphi RTTI seeds: 3,834 addresses; all were covered by the TD32 address set.
- Combined REA/Ghidra seed file: 8,411 unique function addresses. Word/scan procedure index: 859 rows.
- Artifact: [workflow run 46153451750](https://github.com/meicamghe/EMWAT-Linux/actions/runs/46153451750), artifact `emwat-undelphi-rtti-and-rea-seeds`.
- Actual REA/Ghidra execution remains pending; generated seeds are static-analysis inputs only.
