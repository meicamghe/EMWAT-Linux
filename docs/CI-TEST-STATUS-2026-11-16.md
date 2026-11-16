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


## Writer structure inspection checkpoint — 2026-11-16

| Workflow | Run ID | Commit | Result |
|---|---:|---|---|
| LibreOffice UNO integration | 43810592239 | 83e15a565a3d83f0be4b1f758d8f92f3bd61f3e5 | success |
| Python bridge transport | 43810584813 | d6693b806ec0a4dcb956ba3a6a2f840b6654c4af | success |

- UNO integration remains **8/8 passed**. The DOCX fixture now includes a bookmark named LetterSubject; the adapter inventories it through UNO before closing and exporting.
- Python bridge suite is now **86/86 passed** (the optional live UNO test is skipped in this suite and executed by the dedicated integration workflow).
- writer_inspector.py reports structural metadata only and does not read document text or field values.


## Packaged template asset check — 2026-11-16

- Inventory workflow run: 43810767154 — success.
- Artifact: 14200411503 (metadata-only Word asset inventory).
- The tracked EMWAT_Extracted.zip contains **zero files with Word-family extensions** (.doc, .docx, .dot, .dotx, .dotm, .rtf).
- Therefore the installer extraction currently available in the repository cannot supply a representative Word template for field-to-Writer mapping. The live UNO tests remain synthetic fixtures; they must not be described as full template compatibility.


## Twin-field and Custom Document Properties checkpoint — 2026-11-16

| Workflow | Run ID | Commit | Result |
|---|---:|---|---|
| Python bridge transport | 43812324657 | 739bfb7bc9043f81898e2226f80050ce75ab22dd | success |
| LibreOffice UNO integration | 43811929904 | 92462de2caf66cc79b373da91f02077c49b1ae5d | success |
| Word custom-property helper analysis | 43812127854 | 1bfc8a94f3029e0c88dc72aa426e56f07e465043 | success |
| Word field pipeline analysis | 43811074616 | 8a49f1c9b357bd319d67b6c84bf8f57562e842ce | success |

- Python bridge suite: **87 tests passed**, one optional UNO-only test skipped.
- Live LibreOffice integration: **8/8 tests passed**. The fixture adds a synthetic UserDefinedProperty and verifies that the Writer catalog reports its name without retrieving its value.
- Reverse-engineering artifacts confirmed the twin-field delimiter as Unicode dagger `†` (U+2020). The new `parse_word_field_identifier` helper splits only the first delimiter and treats empty-side forms as single identifiers.
- The custom-property analysis pipeline produced and uploaded its artifact; it traced the custom-property dictionaries, field-name enumeration, and conditional SilentSave path.
- These checks still do not validate the complete Almas letter template or final server-side registration against a live Almas environment.


## Word custom-property value helper checkpoint — 2026-11-16

- Helper analysis run: **43812565648 — success**.
- Artifact: **14200962076**.
- `FillImageField` helper lookup confirms `TDictionary<UnicodeString,TDocumentCProperty>.ContainsValue` and `SetItem` are invoked on the custom-property dictionary.
- The same artifact identifies `0x004D1B30` as `ShowRecAndCcOptionForm` and `0x0045644C` as `FindWindowExtd`; their complete semantic roles remain under analysis.


## Writer custom-property write adapter — 2026-11-16

| Workflow | Run ID | Commit | Result |
|---|---:|---|---|
| Python bridge transport | 43813400123 | 0099717df9db0c10c94a9bb7deda184375c2ff58 | success |
| LibreOffice UNO integration | 43813378877 | 0749b11f55cc86244601da14a4d89da9febef168 | success |

- Python suite: **91 tests passed**, one optional UNO-only test skipped.
- UNO integration: **8/8 tests passed**.
- Added `writer_properties.py`: updates only an existing user-defined property by exact name; unknown properties fail instead of being implicitly created. The setter does not read the current property value.
- Real UNO fixture adds a synthetic custom property, updates it through the new adapter, verifies the fixture value, and confirms the structural catalog still reports the property name.



## Twin-field decode and Writer custom-property update — 2026-11-16

| Workflow | Run ID | Commit | Result |
|---|---:|---|---|
| Python bridge transport | 43813400123 | 0099717df9db0c10c94a9bb7deda184375c2ff58 | success |
| LibreOffice UNO integration | 43813378877 | 0749b11f55cc86244601da14a4d89da9febef168 | success |
| Word custom-property helper analysis | 43813303321 | 6024f9ffa14dd75885215929bdcda80de9eb9071 | success |

- Python bridge suite: **91 tests run, 90 passed, 1 optional UNO test skipped**. DecodedWordField now exposes both the original field_id and parsed single/twin identifier.
- Live LibreOffice integration: **8 tests passed**. The synthetic DOCX fixture adds a custom property, updates that existing property through writer_properties.set_custom_document_property, verifies the value in the test, inventories its name without value access, then closes and exports to legacy DOC/CFB.
- The custom-property reverse-engineering artifact is **14201306994**. It completed successfully; the next pipeline revision expands the trace to shared field lookup, XML-config ingestion, and custom-property population helpers.
- Intermediate commits during concurrent implementation produced temporary red Python runs because tests landed before the matching DecodedWordField field. The subsequent code commit 0099717df9db0c10c94a9bb7deda184375c2ff58 fixed the mismatch and the latest Python run is green.
- These tests validate the strict existing-property update adapter and decoder structure, not the mapping of all 180 EMWAT fields or a real Almas Gam letter template.
