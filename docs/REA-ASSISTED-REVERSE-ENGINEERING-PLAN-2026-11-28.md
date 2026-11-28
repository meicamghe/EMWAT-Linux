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
