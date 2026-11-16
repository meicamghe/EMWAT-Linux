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


## TD32 class-method symbol index — 2026-11-16

- Helper analysis run: **43813303321 — success**.
- Artifact: **14201306994**.
- Added `tools/list_td32_symbols.py`, which enumerates TD32 procedures matching class/type fragments and reports their PE virtual addresses and procedure sizes.
- The artifact indexed 611 procedures containing `TDocumentCProperty`, `TXmlWordConfigField`, or `TXmlWordConfigTwinField` in their TD32 symbol names.
- This index surfaced `TWordViwer.SetFieldValue` at `0x004BFDB0`, `GetXmlFieldInfo` at `0x004BFC18`, and typed dictionary `Add` / `AddOrSetValue` helpers for the single and twin field maps. A focused follow-up trace has been queued in the custom-property workflow.



## Word close/response-chain reverse-engineering — 2026-11-16

- Workflow run **43813684507** completed successfully.
- Artifact: **14200889822** (emwat-word-close-response-chain).
- The artifact traces both generated Word Close wrappers: no-argument Close dispatches through _Document byte offset +0x4D4; three-OleVariant Close dispatches through +0x29C. The BeforeSave callback uses the three-argument wrapper after its Cancel/prompt logic.
- OnControlerNotify calls CostumizeRecAndCC, which invokes _Document slot +0x2BC (PrintOutOld on the generated wrapper mapping), then calls a separate _Document slot +0xDC with -1. The +0xDC meaning and HTTP/registration connection are not yet established.
- A follow-up workflow revision adds Get_Saved and Set_Saved wrapper traces to resolve the +0xDC slot mapping.


## Controller notify close-side trace — 2026-11-16

- Workflow run: **43813684507 — success**.
- Artifact: **14200889822**.
- Traced `TWordViwer.OnControlerNotify` at `0x004BB3B0`, `TScanDocument.PerformMethod` at `0x005EE82C`, and `TWordViwer.LoadDocument` at `0x004B7724`.
- Controller notification invokes `CostumizeRecAndCC`, then passes `-1` and the document interface to COM vtable slot `+0xDC`; this is a candidate finalize/close action, but the exact method is being compared with generated Word `Close` and `Save` wrappers.
- This does not yet prove the final Almas POST/response payload.


## Native DOCPROPERTY identifier parsing — 2026-11-16

- Latest Python bridge run **43814423443** completed successfully: **94 tests run, 93 passed, 1 optional UNO test skipped**.
- The decoder now includes extract_docproperty_identifier(), mirroring the native FindFieldInActivefields behavior: case-sensitive DOCPROPERTY recognition, extraction after the first double-space delimiter, and the legacy first-token/255-character behavior.
- Tests cover standard DOCPROPERTY, non-DOCPROPERTY, case sensitivity, unterminated fields, and the native parser's unusual triple-space result.
- This is a compatibility parser for the observed native behavior, not a general-purpose Word field-code parser.


## Word Content/Save COM slot resolution — 2026-11-16

- Close/response-chain workflow run **43814460258** completed successfully.
- Artifact: **14201473774**.
- Generated wrapper traces map Word document COM slots exactly: Get_Saved → +0xD4, Set_Saved → +0xD8, Get_Content → +0xDC.
- OnControlerNotify's call to +0xDC is therefore the document Content member, not a Saved getter/setter. Its -1 argument remains unexplained and must not be interpreted as a registration flag.
- This corrects the earlier assumption that +0xDC was an unidentified Saved-related call.


## Word close-slot and field-code extraction checkpoint — 2026-11-16

| Workflow | Run ID | Result |
|---|---:|---|
| Python bridge transport | 43814423443 | success — 94 tests, 1 optional skip |
| Word close/response chain | 43814460258 | success |
| Word close/response chain (wrapper comparison) | 43814449282 | success |

- Generated wrapper trace confirms `TWordDocument.Get_Content` at `0x0042BDF8` uses COM slot `+0xDC`; the controller-notify call is a Content getter, not a Close/Save call.
- `TWordDocument.Get_Saved` uses `+0xD4`, `Set_Saved` uses `+0xD8`, `Save` uses `+0x2B8`, and the generated `Close` overloads use `+0x29C`.
- `OnControlerNotify` emits the explicit AutoSave log and works with local `.easd/.easz` recovery paths. This is separate from the user-visible Almas registration operation until the final HTTP exchange is captured.
- The native field-name parser uses the case-sensitive `DOCPROPERTY` keyword and two-space delimiter; Python tests now cover the legacy Copy offset and fallback behavior.


## Local auto-save archive path — 2026-11-16

- Close/controller analysis run **43814607589** completed successfully.
- Artifact: **14202031457**.
- OnControlerNotify logs an auto-save execution message, constructs .easd and .easz paths from viewer state, applies Farsi-direction normalization, and passes them to euUnArchive.
- This confirms a local auto-save/archive workflow. It does not prove a POST to Almas or the final response-word registration trigger.
- TWordDocument.Save at 0x004309A4 dispatches through _Document slot +0x2B8; no direct bounded CALL xref was found.


## Latest repository-wide verification after concurrent integration — 2026-11-16

| Workflow | Run ID | Commit | Result |
|---|---:|---|---|
| Python bridge transport | 43814937717 | c8d756adbab824999156c72dfa41f566316282c7 | success |
| LibreOffice UNO integration | 43814937834 | c8d756adbab824999156c72dfa41f566316282c7 | success |
| Word close/response-chain analysis | 43814822927 | 6165d9f324c92f21f7a777b85ed943cf2fb8195e | success |

- Python: **94 tests run, 93 passed, 1 optional UNO test skipped**.
- LibreOffice UNO: **8 tests passed**, including the real Writer open/close/export path and strict existing custom-property update.
- The custom-property helper pipeline run 43814583673 is still in progress; no result is claimed for it here.


## Imported DOCPROPERTY field refresh integration — 2026-11-16

| Workflow | Run ID | Commit | Result |
|---|---:|---|---|
| Python bridge transport | 43815297715 | c4292b8100d57545f300e2a285bbdf1b8e143a7e | success |
| LibreOffice UNO integration | 43815162036 | 2ebb2564f3d5320ac33bd8b299845f7611437875 | success |

- Python suite: **96 tests run, 95 passed, 1 optional UNO test skipped**.
- LibreOffice UNO suite: **8/8 passed**.
- The synthetic DOCX now contains an actual Word DOCPROPERTY field instruction bound to a custom document property. The integration test opens it in Writer, updates the existing custom property, calls refresh_writer_text_fields(), and confirms the rendered document text contains the updated property value before exporting back to legacy DOC/CFB.
- Writer inspector now identifies fields using the DocInfo.Custom service and returns the custom-property Name without reading field presentation or property values. This preserves the metadata-only privacy boundary.
- This proves the basic DOCPROPERTY → custom-property → refresh flow in the synthetic fixture. It does not prove all 180 EMWAT fields or real Almas template fidelity.


## DOCPROPERTY field roundtrip and parser parity — 2026-11-16

| Workflow | Run ID | Commit | Result |
|---|---:|---|---|
| Python bridge transport | 43815297715 | c4292b8100d57545f300e2a285bbdf1b8e143a7e | success |
| LibreOffice UNO integration | 43815162036 | 2ebb2564f3d5320ac33bd8b299845f7611437875 | success |

- Python suite: **96 tests run, 95 passed, 1 optional UNO-only test skipped**.
- UNO integration: **8/8 tests passed**. The DOCX fixture contains a custom property in `docProps/custom.xml` and a complex Word `DOCPROPERTY` field. The test updates the existing property, refreshes Writer text fields, and verifies that the displayed field result changes to the new value.
- `writer_fields.py` exposes `refresh_writer_text_fields`; `writer_inspector.py` inventories custom field names only for `com.sun.star.text.TextField.DocInfo.Custom`, without reading field presentations or document text.
- `word_fields.py` mirrors the legacy DOCPROPERTY token extraction and uses `unquote_plus`. Custom-property helper run `43815255639` (artifact `14201569927`) confirmed that native helper `0x00455314` decodes `%HH` and maps `+` to the literal space at `0x00455454`.
- The temporary red Python runs at 43815149109, 43815162148, and 43815235425 were caused by a fake Writer field lacking the UNO `getSupportedServiceNames` API; the fixture was corrected, and run 43815297715 is green.
- These checks prove the synthetic DOCX/Writer custom-property path, not the original Almas template, all direct Word Field.Result.Text semantics, or live Almas close-time registration.



## Batched Writer property application API — 2026-11-16

- Python bridge run **43815578467** passed: **99 tests run, 98 passed, 1 optional UNO test skipped**.
- writer_properties.py now validates every exact custom-property name before applying a batch, rejects non-text values, and avoids partial mutation when any property name is unknown.
- LibreOfficeAdapter.apply_custom_property_updates() now exposes the production operation: apply a verified mapping of existing custom properties, then refresh Writer text fields once.
- The live UNO integration run for this adapter-level operation is still in progress at the time of this update; no UNO result is claimed yet.


## Rec/CC field-name trace expansion — 2026-11-16

- Custom-property helper run **43815255639** succeeded; artifact **14201569927** also confirmed the literal XML-config names `Receivers`, `ReceiverDeps`, `ccReceivers`, and `ccReceiverDeps`.
- Follow-up analysis run **43816241948** succeeded; artifact **14201844295** decoded the `FillPrintOptionForm` constants at `0x004D21D4–0x004D239C`, including `tokenizedReceivers` and U+2020 delimiter.
- The native URL decoder at `0x00455314` scans percent escapes and maps plus to a space; this is now matched by Python `unquote_plus` and covered by a test.



## Adapter-level custom-property batch round-trip — 2026-11-16

| Workflow | Run ID | Commit | Result |
|---|---:|---|---|
| Python bridge transport | 43815578467 | adf239d6ae2375f8c31c81ab420a02e20dc4e1db | success |
| LibreOffice UNO integration | 43815561042 | 82c437067c58ef64eca6c1b1e2745cd2a9ff97df | success |
| LibreOffice UNO integration | 43815592590 | 2ab9657e3d458be50c00177125c6c9b6824b7607 | success |

- Python: **99 tests run, 98 passed, 1 optional UNO test skipped**.
- Both UNO runs: **8/8 tests passed**.
- The integration now calls LibreOfficeAdapter.apply_custom_property_updates() rather than invoking property mutation and field refresh separately. The adapter validates exact existing property names, applies the batch, then refreshes Writer text fields once.
- The UNO fixture confirms the imported DOCPROPERTY display updates to the new custom-property value and the document exports to legacy DOC/CFB.


## Word Application event-sink wiring — 2026-11-16

- Workflow run **43815900228** completed successfully.
- Artifact: **14202173024**.
- TWordApplication.ConnectTo connects the Word Application event interface. The callback record contains explicit registrations for WordAppDocumentBeforeSave, WordAppNewDocument, and WordAppWindowActivate.
- WordAppDocumentBeforeClose is not in the observed callback record; its only direct bounded caller remains FillImgFldsForPrint.
- This establishes how BeforeSave is wired into Word automation, but not the final Almas HTTP registration handoff.


## URL decode parity and Rec/CC pipeline — 2026-11-16

| Workflow | Run ID | Artifact | Result |
|---|---:|---:|---|
| Python bridge transport | 43816293635 | — | success |
| Word custom-property helpers | 43816241948 | 14201844295 | success |

- Python: **99 tests run, 98 passed, 1 optional UNO-only test skipped**.
- URL decoder parity: native `0x00455314` converts `%HH` escapes and maps literal `+` to a space (`0x00455454)); encoded `%2B` remains a literal plus. Python `unquote_plus` and the test cases now match.
- `0x004D1B30` is `FillPrintOptionForm`, confirmed by its start/success log strings. It reads optional key `tokenizedReceivers`, uses U+2020 as its separator, and processes the config keys `Receivers`, `ReceiverDeps`, `ccReceivers`, and `ccReceiverDeps`.
- Exact per-list semantics and mapping to final recipient/CC UI fields remain unresolved; do not infer values from the field names alone.



## URL-encoded plus semantics parity — 2026-11-16

- Native helper 0x00455314 explicitly maps a literal plus to the one-character string at 0x00455454; that string decodes to a space. Percent-encoded %2B still becomes a literal plus.
- word_fields.py now uses urllib.parse.unquote_plus and tests both cases with encryption="urlencoded".
- Python bridge run **43816293635** passed: **99 tests run, 98 passed, 1 optional UNO test skipped**.
- Base64 text conversion is still distinct from image-byte decoding. Native SetFieldValue decodes Base64 bytes and passes them through 0x004735D0 → 0x004738CC; the lower-level encoding-selection helpers 0x00473608 and 0x00473700 are being traced before changing Python's base64 value representation.


## SevenZip recovery archive semantics — 2026-11-16

- Recovery plugin workflow run **43815900302** completed successfully.
- Artifact: **14203070675**.
- euUnArchive is an input archive extraction path; euResetMemory creates output archives and has direct callers only in ApplicationActivities.Finalization and the recovery form Delete handler.
- T7zOutArchive.SetPassword at 0x004547DC is a no-op stub. The output archive password argument is therefore not proof of encryption.
- T7zInArchive.SetPassword is implemented but has no direct bounded CALL xref; indirect invocation remains possible.
- Keep .easd/.easz roles and any archive password unresolved until caller and callback data flow is complete.


## Latest verified checkpoint — 2026-11-16

- Python bridge transport: workflow `43818155017` — **99 tests passed, 1 skipped**.
- Added native Base64 compatibility coverage: valid padded quartets with one and two `=`, unpadded complete quartet, invalid alphabet, incomplete quartet, and whitespace rejection.
- Field decoder now preserves whitespace as invalid Base64 rather than stripping it. This is distinct from outer `wordConfig` Base64 parsing, which still accepts XML whitespace.
- Previous historical 86-test snapshot remains recorded above; this 99-test result supersedes it for the current branch.


## Latest LibreOffice lifecycle checkpoint — 2026-11-16

- Python bridge transport `43818676999`: **101 passed, 1 skipped**.
- LibreOffice UNO integration `43818676967`: **10 passed**; includes process cleanup tests and a real headless UNO DOCX → legacy .doc close/export roundtrip.
- Process cleanup now reaps after forced termination and skips already-exited processes.


## Latest XML attribute preservation and controller trace — 2026-11-16

- Python bridge run `43820250444` completed successfully: **101 tests run, 100 passed, 1 optional UNO test skipped**.
- Tests verify preservation of the literal XML attribute key/value, including the backslash-n sequence; the implementation does not normalize `concater` to `concator` or infer concatenation behavior.
- Native parser-side evidence identifies `concator` as the incoming XML key. The captured schema transcription's `concater` spelling remains a documented discrepancy until the raw request is checked.
- Controller-init trace run `43820125640` succeeded (artifact `14204196789`). Its controller `Notify` method calls `TEmwatDocPrintHandler.GetDocFieldName`, not the main viewer's `OnControlerNotify`; the two paths remain separate pending further pointer analysis.
- The current LibreOffice UNO success covers the document roundtrip only. Interactive Yes/No/Cancel equivalence and exact Almas response handling remain unverified.
