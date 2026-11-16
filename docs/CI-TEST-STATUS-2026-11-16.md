# CI verification report — 2026-11-16

## Summary

The three analysis workflows that previously failed because private capture inputs were absent have been hardened. Missing private inputs now produce an explicit SKIPPED report and still upload the artifact; when the input is present, the original analysis command runs normally and its failure remains visible.

## Verified workflow runs

| Workflow | Run ID | Commit | Result |
|---|---:|---|---|
| Analyze EditWordDocument request parameters | 43806872630 | b552706606398528f68012b04e3e57dc227b1a16 | success |
| Analyze EMWAT TCP capture | 43806875027 | 3008f411e735a73ca71f195fc042fd8231f5acb3 | success |
| Analyze EMWAT HTTP capture timing | 43806878471 | 80f62635b1a5d46a8b4fd226b4b38f21be929c0e | success |

All three jobs completed their analysis/report step and uploaded artifacts. Because `emwat.pcapng` and `tcp-payloads.txt` are intentionally absent from the repository, these runs verified the safe-skip path, not a fresh re-analysis of the underlying packet capture.

## Python bridge test baseline

The latest available Python bridge CI run at this checkpoint is run `43722805637`, conclusion `success`. Its test step completed successfully; the project handoff records **71 passing tests**. This run validates the fake-office/domain orchestration and bridge tests. It does not validate a live LibreOffice UNO adapter, which has not yet been implemented.

## Earlier failures

Runs `43736828611`, `43736860267`, and `43736828559` failed because their required capture files were missing from the checkout. They are superseded for CI hygiene by the three successful runs above; their original conclusions remain in GitHub history.

## Remaining verification gaps

- No fresh native-core CMake/CTest or sanitizer run was triggered by this workflow-only change.
- No live LibreOffice Writer/UNO integration exists yet.
- No fresh packet-capture analysis was possible without the private capture files.
- The exact Windows close-time callback and cancellation response envelope remain unconfirmed.

## Changes made

- `.github/workflows/analyze-editword-request-params.yml`: explicitly skips with a report when `emwat.pcapng` is absent.
- `.github/workflows/analyze-network-capture.yml`: explicitly skips with a report when `tcp-payloads.txt` is absent.
- `.github/workflows/analyze-pcap-timing.yml`: explicitly skips timing and document-comparison steps when `emwat.pcapng` is absent.


## Subsequent native document-engine verification — 2026-11-16

| Workflow | Run ID | Commit | Result |
|---|---:|---|---|
| LibreOffice UNO integration | 43810188525 | 63ae7210110720535f8b02ca27d91542a9efc972 | success |
| Python bridge transport | 43810428599 | e10053ea99e1c75fd3b2a237937c550a3cbaec33 | success |

- UNO integration: **8/8 tests passed**. The test installed LibreOffice Writer and python3-uno, opened a generated DOCX using a real isolated UNO process, closed the document through UNO, and verified a legacy Word CFB output snapshot.
- Python bridge: **85 tests passed**, with one optional UNO test skipped because the separate integration workflow owns that test.
- The Python application composition test verifies HTTP POST → EditWordDocument parser → domain service → injected OfficeAdapter → response-word serializer.
- Field decoder tests cover URL-encoded text, Base64 image bytes, plain-text preservation, optional attributes, and opaque external signData binding.

These checks validate the adapter and composition boundary. They do not establish compatibility with the original Almas Gam Word template, all 180 field IDs, or the live close/cancel/registration workflow.
