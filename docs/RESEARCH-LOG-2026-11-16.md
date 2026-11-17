# EMWAT reverse-engineering session log — 2026-11-16

Repository: https://github.com/meicamghe/EMWAT-Linux  
Scope: EMWAT reverse engineering only. Winux is outside this workstream.

## Repository state verified

- Repository default branch: `main`.
- Previous analyzed HEAD: `0fdb7caa328563cc94760bf8639c4d5042184c1c`.
- New analysis workflow commit: `718894674e5019ff595878b0f69c1498a12a2b64`.
- Workflow file: `.github/workflows/analyze-emwat-dispatch-crosswalk.yml`.

## Existing evidence independently rechecked

GitHub Actions run `43832553168` completed successfully. Its artifact `14208369288` (`emwat-bpl-method-invoke-contract`) was downloaded and inspected.

The artifact confirms:

1. TD32 identifies `TEmwatMethod.Invoke` at `0x0046C82C` with parameter type `TDictionary<AnsiString,AnsiString>`.
2. The routine enumerates key/value entries and creates XML parameter nodes through virtual/interface calls. The prior XMLRTL analysis establishes the parameter `name` attribute and text-value behavior.
3. `TEditWordDocument`, `TScanDocument`, `TFaxDocument`, `TGetEmwatVersion`, `TSetEmwatVersion`, `TUpgradeEmwat`, `TImageEdition`, `TEditExcelWorkBook`, and `TCompareWordDocument` share the `TEmwatMethod` base class.
4. The direct TD32 caller scan finds only a unit-finalization call to `TEmwatMethod.Invoke`. The request-time invocation is still indirect/unresolved; do not claim a complete service-parser-to-method-class dispatch chain yet.
5. The `TScanDocument.PerformMethod` procedure at `0x005EE82C` calls `TWordViwer.LoadDocument` at `0x004B7724`. `LoadDocument` is therefore a key entry point for the Word document workflow, but its relationship to the specific runtime class selection still needs the VMT dispatch trace.

The artifact contains 9 trace files, including the Invoke disassembly/TD32 procedure, direct callers, class procedure inventory, VMT slots, interface tables, and LoadDocument trace.

## Known protocol boundary

The service-side parser at `0x00470D00` recognizes the XML envelope:
- root `emwat` and its `version` attribute;
- child `method`;
- method `class`;
- child `param` with a `name` attribute.

Parser helper `0x0046A7A4` appends a three-value record to an internal collection. The exact semantics of those three values and the conversion from parser records into the BPL dictionary remain unproven. The exact invoke response envelope is also still open.

## New parallel analysis pipeline

The new workflow adds three independent GitHub Actions jobs:

### 1. Service request dispatch
Targets in `EmwatService.exe`:
- `0x0047BF30` — MainForm HTTP command handler
- `0x0047E0EC` — invoke-route helper
- `0x00470D00`, `0x00470B38` — XML ParseMethod wrapper/worker
- `0x0046ADBC`, `0x0046A7A4` — token dispatch and parser-record collection
- service class procedure, VMT, and interface inventories

### 2. BPL method dispatch
Targets in `EmwatMethods.bpl1`:
- `0x0046C82C` — inherited dictionary Invoke
- `0x0046DE84`, `0x0046E324`, `0x0046E3CC` — Invoke enumeration/dispatch helpers to resolve
- `0x005EE82C` — PerformMethod entry
- `0x004B7724` — LoadDocument
- BPL class procedure, VMT, and interface inventories

### 3. Word controller / close chain
Targets in `EmwatMethods.bpl1`:
- `0x004BB3B0` — OnControlerNotify
- `0x004CD154` — registered BeforeSave callback
- `0x0042ABA0`, `0x0042BDF8` — Word document content wrapper path
- `0x004309A4` — Word Save wrapper
- `0x00456DFC` — helper after content retrieval

The workflow commit is confirmed on `main`. At the time this note was written, the Actions execution/artifacts for this newly added workflow had not yet been independently verified. Do not report the three jobs as passed until their run and artifacts are inspected.

## Immediate next actions after workflow completion

1. Inspect each of the three job artifacts and correlate service parser records with BPL method invocation.
2. Resolve the dynamic/RTTI/VMT call into `TEmwatMethod.Invoke` and the concrete `PerformMethod` implementation.
3. Trace the `OnControlerNotify → Get_Content` return value through helper `0x00456DFC`, then compare it with the long-lived HTTP invoke response.
4. Keep the registered Word BeforeSave Yes/No/Cancel path separate from the periodic controller-notify path.
5. Update `docs/PROJECT-STATUS.md`, `docs/SESSION-HANDOFF.md`, and the relevant protocol analysis only after the new artifact evidence is confirmed.

## Evidence discipline

Use explicit labels: user-observed, statically confirmed, runtime-confirmed, inferred, or unknown. A workflow being committed is not the same as it having run successfully. A trace artifact is not runtime confirmation. Never include customer document contents, signature payloads, tokens, cookies, or unredacted traces in the public repository.

## Update — close-driven HTTP response release identified

The central request-lifecycle wait is no longer unknown:

- `TWordViwer.LoadDocument` calls `OnTmrAutoSave` synchronously at `0x004B7A58`.
- `OnTmrAutoSave` loops at `0x004B9AE8`: `kernel32!Sleep(5)` → `TApplication.ProcessMessages` → test viewer field `+0x58`.
- While `+0x58` is nonzero, the loop repeats. Every 200 iterations it performs a maintenance/check block (`0x00445B10`, `0x00455108`) and starts another cycle. The 200 × 5 ms cycle is not a total timeout.
- The close/registration callback at `0x004CD154` calls Word `Document.Close` and clears viewer `+0x58` at `0x004CD31C`.
- The wait then exits; `LoadDocument` continues to the successful response branch at `0x004B7F31`, writes `response-word` through Indy `WriteContent`, and sets `bResultSet`.

This directly explains why the local HTTP request remains pending during Word editing and why the returned document arrives after the close/registration path. The ~54.558-second PCAP delay is consistent with that wait. Formal COM event identity for `0x004CD154` and the initial setter of viewer `+0x58` are still being resolved.

Artifacts: wait-mechanism run `43874638245` / artifact `14229716255`; request-lifecycle run `43873354906` / artifact `14229047092`; response-writer run `43872534265` / artifact `14228851062`.

Correction to the earlier checkpoint: the 200-iteration block is a repeating ~1-second maintenance cycle, not a maximum 1-second wait. The loop continues until the close callback clears the state field.


## Follow-up: Word automation type signatures (verified from the downloaded TD32 artifact)

A further pass over the full class-procedure index found a much more decisive signal than the earlier executable strings: EMWAT's compiled method signatures explicitly reference the Word type library interfaces `Wordxp._Document`, `Wordxp.Fields`, `Wordxp.Field`, and Word application event callback signatures. Relevant routines include `FillField`, `FillImageField`, `FillMSWFields`, `FillPrintDocFields`, `WordAppDocumentBeforeClose`, `WordAppDocumentBeforeSave`, `WordAppNewDocument`, `WordAppWindowActivate`, `WordAppDocumentBeforePrint`, and `QuitWord`.

This means Windows file-association changes cannot substitute LibreOffice for the Word object model. A drop-in replacement would need to satisfy the actual Word automation interfaces and event contracts, or EMWAT would need its Word-dependent code path replaced by another backend.

The complete procedure index and evidence boundary are recorded in `docs/WORD-AUTOMATION-SURFACE-2026-11-16.md`.

## Additional parallel workflow commits

- `a5dee4d9345017ce37fa1621e681aaa23e8c7581`: added lifecycle, field-mapping, and save/print trace jobs.
- `d420c63b41203dd27c336352776e40049c7a1153`: included Word controller constructor/destructor targets.
- `2dd31ccd7438a4c6c6eca232aab1f5b1e5a41bcd`: added the Word automation interface-surface document.

The connected GitHub workflow-run lookup returned no runs for these commits at verification time. The workflows are committed but their newly requested artifacts are not yet available; no pass result is claimed.


## Follow-up — LoadDocument lifecycle and metadata cross-links

A second cross-check against the extracted `TWordViwer.LoadDocument` TD32 disassembly confirms:

- `LoadDocument` directly calls `TWordViwer.$bdtr` at `0x004D0D24` (`0x424` bytes) at `0x004B78E9`.
- `LoadDocument` directly calls `AddCustomDocPropertiesToDic` at `0x004D1454` at `0x004B7994`.
- `LoadDocument` directly calls `OnTmrAutoSave` at `0x004B8A84` at `0x004B7A58`, then branches on the returned Boolean at `0x004B7A5F–0x004B7A61`.
- The TD32 class index identifies `TWordViwer.$bctr` at `0x004D08B4` (size `0x470`), `$bdtr` at `0x004D0D24` (size `0x424`), `AddXmlWordConfigFieldsToDic` at `0x004D1148` (size `0x30C`), and `AddCustomDocPropertiesToDic` at `0x004D1454` (size `0x3B4`).

Interpretation boundary: the destructor call and metadata-collection call are direct static evidence. They do not independently prove COM shutdown order, property names, or the final XML/HTTP response schema. Constructor activation and event hookup remain open until the constructor body is inspected.

The Word automation surface document was updated in commit `6e650578c35f372ebbdff7aa11960a5308446b9e`.


## Follow-up — Word backend compatibility inventory

The TD32 class procedure index was reorganized into functional groups in `docs/WORD-AUTOMATION-SURFACE-2026-11-16.md`: lifecycle, XML/config field mapping, document field mutation, custom metadata extraction, save/close callbacks, print pipeline, and formatting/protection. This establishes the minimum scope of a LibreOffice-compatible backend beyond opening DOCX files. It remains a symbol/signature-derived requirements inventory; exact Word calls and serialization details are not yet proven.

Documentation commit: `7f5f7340c514c43c47171539292ad53beaa5b678`.


## Follow-up — CI input preflight correction (2026-11-16)

A repository-content check for `analysis-input/EmwatMethods.bpl1` returned HTTP 404 on the default branch. The current public checkout therefore does not expose the BPL file at the path assumed by the Word-analysis jobs. This explains why committing a workflow is not sufficient evidence that its binary-analysis commands can run.

Corrective changes:
- `.github/workflows/analyze-word-automation-surface.yml`: all three trace steps now have a step-level `hashFiles(...)` guard; each job emits a visible GitHub Actions notice when the BPL input is absent; artifact upload is conditional on the input being present.
- `.github/workflows/analyze-emwat-dispatch-crosswalk.yml`: the BPL method-dispatch and Word-controller jobs use the same guarded behavior. The service job already had a missing-input guard for `EmwatService.exe`.

The guards are step-level (not job-level) so the jobs can report the missing input instead of disappearing as unexplained skipped jobs. This is a workflow robustness fix only; it does not supply the binary or generate new disassembly.

Commits:
- Word workflow guard: `a3ac41be0201e45e05004067ebbdc966347c0eef`
- Word missing-input notice: `e26bfcdde20528e1bbf8fe0196aea627a3f186f7`
- Dispatch workflow guard: `7f9211b7a2825b55baadc3f0f58d5b0a1036bb89`
- Dispatch missing-input notice: `663c55ec26a243b3c77a009772933433be542761`

Evidence boundary: the file-path 404 is confirmed against the connected repository's default branch. It does not prove that no private/local copy exists elsewhere. No new Actions run or artifact has been verified after these changes.


## Follow-up — service handler to XML parser control-flow checkpoint

The locally retained service trace artifact `14208144442` was cross-read against the earlier parser findings. The MainForm handler at `0x0047BF30` calls route helper `0x0047E0EC`; on a true return it calls XML ParseMethod wrapper `0x00470D00` at `0x0047C0C5`; on false it takes a separate error/logging branch. The handler then reaches finalizer helper `0x0047E2D4`.

The route helper reads an object pointer from `self + 0x428`, invokes its first virtual method, and returns a Boolean based on an output value. The object's class and method meaning are not resolved. The finalizer conditionally logs, invokes a helper on the supplied value, and clears it; its exact exception/ownership semantics remain open.

A focused checkpoint was added at `docs/SERVICE-REQUEST-LIFECYCLE-2026-11-16.md` (commit `de3276f4ec1a4ac0801cb2c476f273b7c6bec614`).

This is a static disassembly cross-reference only. It does not establish the exact HTTP route, the virtual object's semantic role, or the XML response contract.


## Follow-up — LibreOffice replacement contract and parity test plan

Added `docs/LIBREOFFICE-BACKEND-CONTRACT-2026-11-16.md` to turn the recovered Word/HTTP lifecycle into an implementation boundary. It separates the loopback compatibility service, XML parser, method registry, office adapter, document-field mapping, and lifecycle coordinator. It also defines layered parser/dispatcher/UNO/lifecycle/end-to-end tests and explicit evidence needed before claiming parity.

Important design decisions:
- Do not treat default file associations as a COM replacement.
- Keep UNO behind a backend-neutral adapter and test protocol logic with a fake office backend.
- Model the pending HTTP request as an event-driven document session; do not reproduce the original message-pumping busy wait.
- Treat bookmarks, Writer fields, and custom properties as candidate mappings only until the original Word field rules and sanitized templates are available.
- Compare semantic document output and response behavior rather than requiring binary DOCX package equality.

This is a design/test contract, not an implemented or runtime-verified Linux replacement. The exact HTTP route/response schema, BPL method dispatch, field-name mapping, and print semantics remain open.


## Follow-up — avoid unnecessary CI setup when binaries are absent

The two analysis workflows were tightened so `actions/setup-python` and the `pefile`/`capstone` installation run only when their corresponding binary input exists. This avoids consuming runner time and dependency-install work on a checkout that only needs to report missing inputs.

Commits:
- Word automation workflow: `b8e36f71b91533398d629dcb97a1cf36e5167537`
- Service/BPL dispatch workflow: `1312ed0d42db82063e9202f7f0459b1e272f2f13`

The trace and artifact-upload guards remain in place. This change has been committed, but no new Actions run has been verified; it is not a test-pass claim.


## Critical input correction — binaries are present in EMWAT_Extracted.zip

The public repository contains `EMWAT_Extracted.zip` (24,018,540 bytes). The committed `EMWAT_zip_contents.txt` inventory lists 70 entries and confirms:
- `EmwatMethods.bpl1` — 11,106,148 bytes
- `EmwatService.exe` — 679,936 bytes
- `EmwatAgent.exe` — 2,924,032 bytes

The BPL is also present directly at `analysis-input/EmwatMethods.bpl1` in the current main tree. The earlier missing-input conclusion was incorrect because the archive and then-current repository tree were not checked together.

Both `analyze-word-automation-surface.yml` and `analyze-emwat-dispatch-crosswalk.yml` now extract the three named binaries from the root of `EMWAT_Extracted.zip` into `analysis-input/` before analysis. The archive path is included in each workflow's push filters.

Runs triggered by those workflow commits:
- Word automation: `43882530570`, observed running at review time.
- Service/BPL crosswalk: `43882543797`; its service trace extracted all three binaries and completed six target disassemblies, then failed because optional TD32 class/VMT/interface metadata probes returned non-zero when that PE did not expose the expected debug signature.

The service workflow was corrected in commit `ce79705a41d97baf90a8b19219a1eb606fe02290` so those optional metadata probes no longer fail the whole job. Follow-up execution has not yet been verified complete.

The first run log confirms extraction of all three binaries with the exact sizes above. This is current-run confirmation that CI can consume the archive, not merely an inventory-file assertion.


## Archive-backed analysis completed — Word procedures and service parser

The archive extraction change was validated by GitHub Actions run `43882530570`: all three jobs completed successfully:
- `word-lifecycle`
- `word-field-mapping`
- `word-save-print`

Artifacts downloaded and inspected:
- `14232038437` — `emwat-word-lifecycle`
- `14231224902` — `emwat-word-field-mapping`
- `14231834659` — `emwat-word-save-print`

New findings are documented in `docs/WORD-AUTOMATION-SURFACE-2026-11-16.md` (commit `f82996959e60440fcb590b3ead9f1609db8b8ee7`):
- `GetXmlFieldInfo` at `0x004BCA88` explicitly accepts `IXMLFieldType` and UnicodeString parameters and builds an internal XML-driven field model.
- `FillMSWFields` at `0x004C009C` accepts Word `Fields` and performs a distinct collection iteration/update pass.
- `SetFieldValue` at `0x004BFDB0` has two separate conversion/assignment branches selected by string constants at `0x004BFEE8` and `0x004BFF0C`; the key constants are queued for decoding.
- `AddCustomDocPropertiesToDic` at `0x004D1454` enumerates Word custom document properties, splits selected property names at U+2020, and calls `TDictionary.Remove` on the single/twin descriptor maps (`viewer+0x68` / `viewer+0x6C`) to consume matching descriptors. The separate runtime custom-property map at `viewer+0x64` is a `TDictionary<UnicodeString,TDocumentCProperty>`.
- `WordAppDocumentBeforeSave` at `0x004CD154` can set its 16-bit Cancel argument to `0xFFFF`, calls a pre-save helper, performs a Word document operation through vtable offset `+0x29C`, and clears viewer state `+0x58`.
- `FillPrintDocFields` at `0x004CB638` is a separate 5,508-byte Word document/Fields transformation pass.

The archive-backed service job in run `43882629052` completed successfully after the optional metadata-probe correction and uploaded `14232189125`. Its extracted trace shows a token-driven XML parser and a 12-byte-stride three-slot record table; the record slot semantics remain open. See `docs/SERVICE-REQUEST-LIFECYCLE-2026-11-16.md` (commit `c00cf511fcb053cbf3240c6826160cf03fba427b`).

Additional CI refinements:
- `ce79705a41d97baf90a8b19219a1eb606fe02290`: optional service TD32/VMT/interface probes no longer fail a job when metadata is unavailable.
- `ab98d4a70efdf9fbea206f87b12b6b039f12d554`: add full-range parser/token/route traces and decode service parser/route string constants.
- `4bfd627dee5b33e9a57fea5cb37cde3a6ea3ae89` and `752c5b5718684975f40487401b7094617698a39d`: add and correct the output path for decoding Word field/custom-property key constants.

Runs `43882768547`, `43882896421`, and `43882925143` were observed in progress at the time of this log update. Their final conclusions/artifacts must be checked before reporting them as passed.


## Follow-up — service package-load gate and controller/content crosswalk corrections

The expanded service string trace revealed that `0x0047E0EC` is a package-load gate, not a generic route helper. It references `EmwatMethods.bpl` and logs either `Unable to load "EmwatMethods.bpl".` or `"EmwatMethods.bpl" loaded.`. The handler tests this Boolean before parsing XML. It also uses the literal `invoke` and contains CORS-like header strings, including the exact literal `Access-Control-Allow-Method:*`. See service lifecycle doc update commit `85d61cb325e00655d39ccd1fe1956dd6a6bd729b`.

The controller-close artifact `14232349256` establishes:
- `TWordDocument.Get_Content` at `0x0042BDF8` calls a Word document interface method at vtable offset `+0xDC`.
- `0x00456DFC` is `euUnArchive` (EmailUtil), called directly from `TWordViwer.OnControlerNotify` at `0x004BB5E9`; it is not the Word content getter.
- `TWordViwer.CostumizeRecAndCC` at `0x004D281C` is called from controller notification, field-name lookup, document protection, and option rollback; it sets/clears viewer flag `+0x5C` around a Word interface call at vtable offset `+0x2BC`.
- `TWrapRecord.LineCount` at `0x004D2948` is called by `SilentSaveEmwatDoc` at `0x004D25F6`.
- The save/close prompt strings include Persian choices `موافقم`, `خیر`, `انصراف`, and a result log. The callback's method name is BeforeSave while its embedded log says OnBeforeClose; do not assume event hookup semantics from that string alone.

These findings are documented in `docs/WORD-AUTOMATION-SURFACE-2026-11-16.md` (commit `907907345e1211901df3ec944d7421bc72bd86a8`). The earlier association of `0x00456DFC` with content extraction is explicitly corrected.


## Final archive-backed analysis and transport compatibility pass

All three archive-backed analysis jobs completed successfully in service run `43883105610`:
- `bpl-method-dispatch` — artifact `14232698133`;
- `service-request-dispatch` — artifact `14233736412`;
- `word-controller-close` — artifact `14234120250`.

The complete Word surface workflow also passed in run `43882925143`:
- `word-lifecycle` — artifact `14232038748`;
- `word-save-print` — artifact `14232159665`;
- `word-field-mapping` — artifact `14232259712`.

The field/property constant artifact confirms:
- `0x004BFEE8` = `urlencoded`;
- `0x004BFF0C` = `base64`;
- `0x004D1768` = `†` (U+2020 DAGGER), the delimiter used by the custom-property split path.

The Word surface report was updated in commit `aa8d8f61b48214a4811402217be0d0844bf3b559`. It now resolves the earlier pending labels/delimiter.

The service artifact was renamed to `package-loader-full.md` and confirms `0x0047E0EC` loads/checks `EmwatMethods.bpl`; it is not an authentication or route-selection helper. Exact parser child-name literals and CORS header spellings are recorded in the service lifecycle report.

The Linux POST bridge was updated to emit the recovered legacy `Access-Control-Allow-Headers: *` and singular `Access-Control-Allow-Method: *` headers while retaining the project's allowlisted Origin policy as a deliberate security hardening. A temporary strict `invoke` query validator was removed because the native trace confirms the client-generated nonce but does not establish server-side numeric validation. The transport keeps the query opaque. Final Python bridge run `43883570154` passed: 104 tests, 2 optional skips. Relevant commits: `7cf67752672f7787983e05677fd50a5909434a1c`, `cdf434e688e73d227dcad77dd3a586e3b23d8329`, `e858f14d0dbcf52ca7496ef43354160aa4c337a8`.

The LibreOffice backend contract was corrected to reflect the existing Python/UNO prototype and prior verification (Python 96 tests with one skip; UNO integration 8/8 on a synthetic DOCX/DOCPROPERTY fixture), while explicitly distinguishing those component tests from full Almas end-to-end compatibility. Contract update commit: `02b3d4fe9133be0d08b3fb98b5f1cf0c9887a028`.


## Follow-up — exact parameter-record layout and Word event-sink correction

The service artifact `14233736412` was re-opened and the parser helper chain was traced through `0x0046A620`, `0x0046A570`, and `0x0046A7A4`.

For a `param` token, `0x00470B38` extracts the `name` attribute into the EDX-side string and passes the parser token's text value through the ECX-side string. `0x0046A620` computes the name hash; `0x0046A570` probes the internal collection for the key/insertion position. The append helper stores a 12-byte record as:
- slot 0: computed hash;
- slot 1: parameter name;
- slot 2: parameter text value.

The append helper writes the standard 12-byte dictionary entry (hash, key, value) and increments the dictionary count. The constructor/VMT chain now proves this is the `TDictionary<AnsiString,AnsiString>` owned by `TMethodInfo`, not merely a structurally similar custom collection. The same generic key/value type is used by BPL `TEmwatMethod.Invoke`.

The Word controller-close artifact `14234120250` also resolves the event registration more precisely:
- `OnTmrAutoSave` writes `WordAppDocumentBeforeSave` (`0x004CD154`), `WordAppNewDocument` (`0x004CD54C`), and `WordAppWindowActivate` (`0x004CD9C0`) into the event-sink callback record.
- It installs `WordAppDocumentBeforePrintBGPrint` (`0x004CE030`) or alternate callback `0x004D00AC` based on viewer flag `+0x3C`.
- The TD32-named `WordAppDocumentBeforeClose` (`0x004CCBBC`) has only one direct caller in the current scan: `FillImgFldsForPrint` at `0x004CCF8F`. Its body calls `GetXmlFieldInfo`; it is not installed by the observed event-sink registration block. Treat the name as a symbol label, not proof of an actual close event hookup.
- `SilentSaveEmwatDoc` is called from `GetDocFieldName` on the `Hidden_Customizable` special-field path. It builds two temporary string lists, invokes `0x004AEBBC`, sets viewer flag `+0x44C`, and conditionally calls `TWrapRecord.LineCount`. The latter's only direct caller is this routine. Exact list semantics and serialization remain open.

These corrections are recorded in `docs/WORD-AUTOMATION-SURFACE-2026-11-16.md`.


## Follow-up — Word field lookup and image pipeline boundaries

Re-opened Word field-mapping artifact `14232259712` and checked direct caller scans:

- `FillPrintDocFields` (`0x004CB638`) has direct callers `GetDocFieldName` (`0x004BB8AE`) and `GetFieldIndexInList` (`0x004CB338`). Its logic therefore participates in field-name/index resolution, not only a user-triggered Print event.
- `AddImagesToDoc` (`0x004C0410`) is called by `GetDocFieldIndex` at `0x004C0A5D` and delegates to `0x004C19C0) after a field-collection string check. The latter remains the core image-placement trace target.
- `FillImageField` (`0x004BC30C`) is reached from `FillTextField` at two branches. It conditionally calls `FindWindowExtd` when viewer flag `+0xF0) is set and required metadata strings are missing, then branches on Word Field type/code.
- `FillField` (`0x004BC2C4`) only appends a field interface to viewer collection `+0x60`; it is not the actual visible field mutation routine.

These findings are documented in `docs/WORD-AUTOMATION-SURFACE-2026-11-16.md` (commit `0715b91c997375fe0f5062f695f9d826b86f72ea`). Keep field inventory, field mutation, and document-level image insertion as separate backend layers.


## Lifecycle contract hardening after event-sink correction

The Python adapter/state-machine documentation previously described a native “close-prompt Cancel” and native Word “No” choice as if a separate BeforeClose event had been established. That wording was too strong. The binary evidence confirms the BeforeSave event sink and its Cancel argument, but does not prove that `WordAppDocumentBeforeClose` is registered or fully decode all save/no/cancel outcomes. Updated:
- `python/src/emwat_linux/office_adapter.py`: a close veto is terminal only when the office engine reports an actual close-veto event; do not infer a BeforeClose event from BeforeSave.Cancel.
- `python/src/emwat_linux/sessions.py`: `discard()` now documents an explicit discard outcome and warns that BeforeSave cancellation alone is not proof of discard.

These are contract/documentation corrections; runtime state transitions are unchanged. Commits: `4511d9722bf46dca8c4d3e6c2379346051c117b9`, `1f29002809a6e7170ea3f251fe45fa6a8424df6b`.


## Next parallel trace batch queued — image insertion and print-field labels

Expanded `.github/workflows/analyze-word-automation-surface.yml` in two passes:
- Added TD32 procedure/caller/PE traces for `AddImagesToDoc` helper `0x004C19C0` and field resolver `0x004BC170`.
- Added string decoding for the `FillImageField` branch constants `0x004BC6D4` through `0x004BC910`.
- Added print-field comparison/branch string decoding for `0x004CCB0C`, `0x004CCB2C`, `0x004CCB38`, `0x004CCB44`, `0x004CCB60`, `0x004CCB6C`, `0x004CC280`, `0x004CC26C`, `0x004CC6DD`, `0x004CC6C9`, `0x004CCB84`, and `0x004CCAA7`.

Workflow commits: `367e4aa58514029278624c65837059f13807394a` and `c159c69141da56ea1bba0c8d829e4839febaf135`. The run/artifact for these latest additions is not yet verified; do not report these traces as completed until the artifact is available.


## CI correction — image branch string output path

The expanded analysis run `43886359961` exposed a workflow-only failure in the `word-save-print` job: the new decoder wrote to `word-automation/fields/`, which is not created in that job. The lifecycle and field-mapping jobs both succeeded; only save-print failed at the shell redirection. Corrected the decoder output to `word-automation/save-print/image-field-branch-strings.md` in commit `1cb8397930047bb6612872d463b6ced688cd323f`. A fresh workflow run `43886833015` was queued. The earlier in-progress run `43886492031` predates this path fix and is expected to retain the same save-print failure; use the new run for validation.


## Verified expanded field/caption trace and CI rerun

The field-mapping job in run `43886492031` succeeded and produced artifact `14233429328`. It resolves `0x004C0550` as `TWordViwer.GetDocFieldIndex`; its caller is `GetDocFieldName` at `0x004BBB2B`. The trace links Word Fields enumeration, `FindFieldInActivefields`, `GetXmlFieldInfo`, `FillMSWFields`, `SetFieldValue`, `FillTextField`, and the `AddImagesToDoc` branch. Caption processing is further linked: `GetCaptionItemFont` → `EmbedTextToImage`, while `GetCaptionItems` is called by `ResizeBitmapCanvas` and `ProcessWords`.

The workflow-only save-print failure was corrected in commit `1cb8397930047bb6612872d463b6ced688cd323f`. The subsequent run `43886833015` completed all three jobs successfully:
- lifecycle;
- field mapping;
- save/print.

The expanded decoder constants were then added in commit `a74fd95dfecc4cf9d7dd42c984e966a980f9dd46`; run `43887016674` was queued/in progress at the time of this update.

CI after the Python adapter docstring clarification:
- Python bridge run `43886698595`: 104 tests passed, 2 optional skips.
- LibreOffice UNO run `43886698714`: 11 tests passed.
These tests validate existing isolated behaviors, not full EMWAT field/image parity.


## Typed custom-property dictionary and print-image helper — artifact 14235092844

New TD32 symbols:
- `0x004D34B0`: `TDictionary<System.UnicodeString,TDocumentCProperty>.SetItem`.
- `0x004D3DF8`: `TDictionary<System.UnicodeString,TDocumentCProperty>.ContainsValue`.
- `0x004D3B78`: `TDictionary<System.UnicodeString,TDocumentCProperty>.Remove`.

These helpers establish that print/document-property handling uses a typed dictionary of `TDocumentCProperty` objects, not a plain string-to-string map. `TDocumentCProperty` instance size is `0x1C`; its internal payload fields remain to be decoded.

The routine at `0x004CCDC8` is `FillImgFldsForPrint`, called directly from `GetFieldIndexInList` at `0x004CB361`. It calls TD32-named `WordAppDocumentBeforeClose` (`0x004CCBBC`) only on a conditional print/image-field branch at `0x004CCF8F`. This reinforces that the symbol name does not represent a registered close event.


## Native signature-end matcher and test correction

The address `0x004B032C` is confirmed as an import thunk to `rtl230.bpl!System.RegularExpressions.TRegEx.IsMatch`. `GetDocFieldIndex` passes the exact pattern `^sign.*end[0-2]?[0-9]?$` to this helper and logs matching active-field names as skipped by business rules. The pattern is case-sensitive; the resolved active-field name is the input (not necessarily the original XML field ID).

Added `is_native_business_signature_end()` in `python/src/emwat_linux/word_fields.py` and tests. The first test run failed because the fixture used mixed-case `End`, which does not match the native lower-case regex. Corrected the test cases to lower-case; rerun `43888658420` was queued. The production helper preserves native case sensitivity and is not wired into XML field IDs until the active-field-name normalization is proven.


## Three separate native field/custom-property maps

The `AddCustomDocPropertiesToDic` trace at `0x004D1454` plus VMT sizes resolves three distinct viewer-owned structures:
- `viewer + 0x68`: single-field descriptor map (`TDictionary<UnicodeString,TXmlWordConfigField>`). `AddCustomDocPropertiesToDic` calls its `Remove` method at `0x004D531C` with the property identifier, consuming/returning a matching descriptor rather than inserting one at this call site.
- `viewer + 0x6C`: twin-field descriptor map (`TDictionary<UnicodeString,TXmlWordConfigTwinField>`). On U+2020 (`†`) split, the routine calls its `Remove` method at `0x004D68D4` using the split key. The exact lifetime/ownership of the returned descriptor still needs tracing.
- `viewer + 0x64`: separate runtime custom-property map, whose TD32 methods are `TDictionary<System.UnicodeString,TDocumentCProperty>.SetItem` (`0x004D34B0`), `ContainsValue` (`0x004D3DF8`), and `Remove` (`0x004D3B78`).

Do not flatten these into one string dictionary in the Linux port. The native implementation distinguishes XML single-field descriptors, XML twin-field descriptors, and runtime custom-property objects.


## Correction: native DOCPROPERTY extraction edge case

The newly recovered `FindFieldInActivefields` body confirms the implementation uses `TRegEx.IsMatch` for the signature pattern and performs the DOCPROPERTY extraction with Delphi `Pos` and `Copy`:
1. If `DOCPROPERTY` is absent, preserve the original field code.
2. Otherwise copy 255 characters starting at `Pos("  ") + 2` (Delphi 1-based); if the double-space delimiter is absent, `Pos` returns zero and the copy begins at character 2.
3. If the copied segment contains a single space, truncate before it; if not, return the copied segment unchanged.

This exposed a mismatch in the previous Python helper: it returned the original field code when the copied segment had no trailing space. Corrected `extract_docproperty_identifier()` and updated edge-case tests. CI runs `43889650755` and `43889681823` were started for the code and test commits; results are pending.


## Completed field normalization / MIME branch trace batch

Run `43889057276` completed all three jobs successfully (lifecycle, field mapping, save/print). The save/print artifact `14236156376` resolves:
- `FindFieldInActivefields` delimiters: `DOCPROPERTY`, double-space, single-space. This directly supports the corrected Python extractor.
- `FillTextField` MIME discriminator: `text/plain`. When the field XML interface is absent or its MIME type is not `text/plain`, the native helper delegates to `FillImageField`.
- `GetCaptionItems` style labels: `bold`, `italic`, `underline`, `strikeout`.
- `GetImageResolution` alignment labels: `right`, `center`, `left`, `top`, `middle`, `bottom`.
- Image/signature path strings include `signData`, `signText`, `igLzw32s.Dll`, `MakeImageList`, and `AddImageToDoc succeed`.

The field-mapping artifact `14236151592` includes the expanded `GetDocFieldIndex`, `FillTwinFields`, `FillTextField`, and regex-thunk traces. All jobs in this run succeeded.


## Twin-field lookup mirrored in Python

The `FillTwinFields` routine (`0x004C02EC`) scans the Word Fields collection from a one-based starting index through the collection count, extracts each `Field.Code` using `FindFieldInActivefields`, and compares the normalized identifier to the requested twin name. It returns the first matching one-based index, or `0` when no match exists. `GetDocFieldIndex` calls this routine on the twin-field path and aborts when the required twin is absent.

Added `find_native_twin_field_index()` to `word_fields.py` with one-based indexing and native zero-on-miss behavior, plus tests for start offsets, missing partners, and invalid zero-based input. Python CI run `43890223183`: 106 tests passed, 2 optional skips.


## Native custom-property field map builder implemented

Added `SingleWordFieldDescriptor`, `TwinWordFieldDescriptor`, `WordCustomPropertyFieldMaps`, and `build_word_custom_property_field_maps()` in `word_fields.py`. This is a Linux-side inventory classifier using the native zero-based enumeration and first-dagger split rules; it does not yet reproduce the native `TDictionary.Remove` consumption/lifetime behavior. Tests verify indices and separation. Python CI run `43890539219`: 107 tests passed, 2 optional skips.


## Correction: generic dictionary helpers and twin comparison semantics

The expanded helper trace corrects the earlier interpretation:
- `0x004D531C` is `TDictionary<UnicodeString,TXmlWordConfigField>.Remove`.
- `0x004D68D4` is `TDictionary<UnicodeString,TXmlWordConfigTwinField>.Remove`.
- `AddCustomDocPropertiesToDic` uses these to consume/return matching descriptors from viewer maps `+0x68` and `+0x6C`; these call sites do not insert new descriptors.
- `0x00403248` is RTL `System.SysUtils.CompareText`; therefore `FillTwinFields` uses case-insensitive comparison. Updated `find_native_twin_field_index()` to compare with `casefold()` and added mixed-case coverage.

Post-change CI: Python bridge run `43891288399`: 107 tests passed, 2 optional skips. LibreOffice UNO run `43890949051`: 11 tests passed.

## Descriptor dictionary population trace queued

Expanded the archive-backed Word analysis workflow to enumerate all TD32 symbols for `TXmlWordConfigField`, `TXmlWordConfigTwinField`, `TDocumentCProperty`, and `TDictionary`. The goal is to locate the actual Add/SetItem/population methods that precede the confirmed `Remove` consumption calls at `0x004D531C` and `0x004D68D4`. The next workflow run will include `field-descriptor-symbols.md` and `generic-dictionary-symbols.md`; no insertion method is claimed until those symbols are reviewed.

## Conservative boundary for Writer descriptor mapping

A trial integration that classified Writer custom-property names into single/twin maps was removed after reviewing the native dataflow: `AddCustomDocPropertiesToDic` calls `TDictionary.Remove` on pre-existing descriptor maps, so the source/population stage of those maps is not yet proven to be the Writer document's custom-property enumeration. `WriterDocumentCatalog` therefore remains metadata-only and reports custom-property names without attaching the descriptor classifier. `build_word_custom_property_field_maps()` remains a pure split-rule utility, not a claim of full native map construction.

## Dictionary Add/SetItem methods found; call-site tracing queued

The new `generic-dictionary-symbols.md` inventory reveals that the single/twin descriptor dictionaries do have insertion methods, separate from the previously traced `Remove` methods:
- `TDictionary<UnicodeString,TXmlWordConfigField>.Add` at `0x004D52DC`; `AddOrSetValue` at `0x004D54E0`.
- `TDictionary<UnicodeString,TXmlWordConfigTwinField>.Add` at `0x004D6894`; `AddOrSetValue` at `0x004D6A98`.
- Runtime `TDictionary<UnicodeString,TDocumentCProperty>.Add` at `0x004D3B38`; `AddOrSetValue` at `0x004D3D3C`.

The expanded workflow now traces these methods and their direct callers, along with `0x00441DD4` (which is actually `TWordApplication.ScreenRefresh`, called by `AddXmlWordConfigFieldsToDic`). This should identify where descriptor maps are actually populated; no caller mapping is claimed yet.

## Correction: AddXmlWordConfigFieldsToDic body and ScreenRefresh identity

The trace of `0x00441DD4` identifies it as `TWordApplication.ScreenRefresh`, not a generated XML-field helper. In `AddXmlWordConfigFieldsToDic` (`0x004D1148`), the routine clears/releases several viewer-owned collections and dictionaries (`+0x64`, `+0x68`, `+0x6C`), calls ScreenRefresh through the Word Application wrapper, emits refresh/clear/success diagnostics, and resets viewer flags. Its TD32 symbol name therefore does not prove that it populates the single/twin descriptor dictionaries. The actual Add/SetItem methods and their direct callers are being traced separately.

## Service parser: dictionary layout cross-check

Re-opened service artifact `14233736412`. `ParseMethod` (`0x00470D00`) constructs an object using class reference at `0x00470924` via `0x00471214`, then passes that object to XML parser `0x00470B38`. The parser helper chain computes the parameter-name hash (`0x0046A620`), probes the bucket table (`0x0046A570`), and appends a three-slot entry at `0x0046A7A4`: hash, key/name, value/text. The object layout uses entries pointer at `+0x04`, count at `+0x08`, comparer at `+0x0C`, and capacity at `+0x10`.

The same service PE exposes `TDictionary<System.AnsiString,System.AnsiString>` VMT `0x00469A3C` (typeinfo `0x0046A054`). The parser entry layout and object field offsets now have a direct constructor/VMT link: `TMethodInfo` (VMT `0x0047097C`, instance size `0x10`) is created by `0x00471214`; its constructor loads class reference `0x004699E4`, which points to dictionary VMT `0x00469A3C`, and calls `0x0046AA70` to create the `TDictionary<AnsiString,AnsiString>` instance stored at `TMethodInfo + 0x08`. `ParseMethod` passes this exact dictionary pointer to the XML parser. The same type is accepted by BPL `TEmwatMethod.Invoke`; only the final indirect dispatch edge remains unresolved.

## Service PE symbol-list limitation

The first service dictionary-symbol workflow attempt (`43893061863`) failed because `EmwatService.exe` has no TD32 debug signature; `list_td32_symbols.py` cannot be used on this PE. Removed that step in commit `a626848729948f448dc345b57490a92c2d473d00`. Service-side dictionary identity will be established through RTTI/VMT pointer references and static caller/dataflow traces, not TD32 symbol names. The BPL remains TD32-symbolized and continues to use the separate generic-dictionary symbol workflow.

## Runtime custom-property map dataflow found

Caller scans from the expanded field artifact resolve the `viewer + 0x64` runtime map:
- `FillImageField` calls `TDictionary<UnicodeString,TDocumentCProperty>.SetItem` (`0x004D34B0`) at `0x004BC45E`.
- `FillImageField` and `FillPrintDocFields` call `ContainsValue` (`0x004D3DF8`); `FillPrintDocFields` has six direct sites.
- `FillPrintDocFields` calls `Remove` (`0x004D3B78`) at four sites, and `FillPrintOptionForm` calls it once.

This establishes that the runtime custom-property map is populated/updated from the image-field path and then checked/consumed during print processing. The single/twin descriptor maps at `+0x68/+0x6C` remain separate: `AddCustomDocPropertiesToDic` calls their `Remove` methods, while direct call scans show no callers yet for their generic `Add`/`AddOrSetValue` methods. The next workflow batch now traces their `SetItem`, `TryGetValue`, `ContainsKey`, and `Clear` methods to locate population.

## Whole-PE direct-call scanner added

Added `tools/scan_pe_call_refs.py`, which disassembles all executable PE sections and finds direct immediate CALL references without requiring TD32 procedure boundaries. It complements `trace_td32_callers.py` (symbol-bounded only) and `scan_pe_pointer_refs.py` (raw pointer bytes). The Word workflow now scans the descriptor dictionary's GetItem/SetItem/Add/AddOrSetValue/DoSetValue and enumerable-constructor addresses; the service workflow scans the dictionary constructor and parser helpers. Both workflows run `py_compile` before using the tool. This is intended to catch callsites in unsymbolized or incorrectly bounded regions.

## Confirmed service parser dictionary object identity

Artifact `14238566198` now closes the identity gap. `TMethodInfo` has VMT `0x0047097C` and instance size `0x10`; its constructor `0x00471214` loads the class reference at `0x004699E4`, whose pointer is the `TDictionary<System.AnsiString,System.AnsiString>` VMT `0x00469A3C`, and calls `0x0046AA70` to construct the dictionary. The dictionary pointer is stored at `TMethodInfo + 0x08`. `ParseMethod` passes this same `+0x08` pointer to `0x00470B38`; the parser's `0x0046ADBC`/`0x0046A570`/`0x0046A7A4` chain hashes, probes, and writes entries. This matches the BPL `TEmwatMethod.Invoke(TDictionary<AnsiString,AnsiString>)` contract exactly. The cross-module call to Invoke remains indirect and is still a separate unresolved dispatch edge.

## Native duplicate parameter handling confirmed

`0x0046ADBC` checks the result of `0x0046A570` before appending a parameter. An existing key enters the exception path through `0x0040211C` and `0x00401198`; a missing key is appended by `0x0046A7A4`. This confirms that the service's `TDictionary.Add` semantics reject duplicate parameter names instead of overwriting them. The existing Python `parse_method_call()` `duplicate_parameter` check matches this behavior.

## Descriptor map lookup and reconciliation path clarified

The latest Word field artifact (`14238059843`) provides a concrete lookup/reconciliation sequence. `viewer+0x68` and `viewer+0x6C` are the single and twin descriptor dictionaries. `GetXmlFieldInfo` (`0x004BFC18`) probes the single map, then falls back to the twin map, and returns the descriptor's index plus its one or two associated property-name strings. The `0x004BC170` normalizer is shared by XML-field lookup, twin-field filling, document-field index resolution, print-field handling, image-print handling, and viewer construction. `AddCustomDocPropertiesToDic` enumerates Word custom properties, splits names on `†`, creates single/twin record-shaped objects, and removes the corresponding descriptor keys from the maps. This proves reconciliation/consumption, not map population. The actual initial population path remains unresolved; enumerable constructors and Add/SetItem caller traces have been added to the next workflow batch.

### Diagnostic-string/name mismatch at the custom-property routine

One important naming trap: the TD32 procedure at `0x004D1454` is definitively `TWordViwer.AddCustomDocPropertiesToDic`, and its body enumerates Word custom properties and removes matched single/twin descriptor keys. However, its log string at `0x004D1704` says `AddXmlWordConfigFieldsToDic method called.` and its success log at `0x004D1778` repeats `AddXmlWordConfigFieldsToDic succeed.` The log text is stale/misleading and must not override the procedure symbol and observed behavior. The separate routine at `0x004D1148` has the same name-like theme but its observed body clears viewer collections/maps and calls `TWordApplication.ScreenRefresh`.

## Service-to-BPL dispatch: next unresolved callsite isolated

The service request handler trace at `0x0047BF30` shows a clear sequence: package-load gate `0x0047E0EC`; XML `ParseMethod` at `0x00470D00`; then a call to `0x0047E2D4` at handler site `0x0047C0E0`. `ParseMethod` constructs `TMethodInfo` and its `TDictionary<AnsiString,AnsiString>` as already documented. Follow-up artifact `14266235060` shows `0x0047E2D4` is a cleanup/exception-reporting helper: it checks and clears an interface/pointer slot, emits diagnostics through `0x0047D2C8`, and releases the referenced object through `0x0040217C`. The whole-PE direct-call scan found no direct caller, consistent with a cleanup path reached through a finally/indirect edge. It is **not** evidence of the BPL method dispatch. The trace workflow now captures the complete MainForm handler range `0x0047BF30–0x0047C341` rather than stopping at its first internal RET; that full body is the next target for locating the actual dispatch.

## Recipient/CC option-form field identifiers recovered

The latest field-mapping artifact (`14265228751`) decodes the `TWordViwer.$bctr` constants at `0x004D0BD0`, `0x004D0BF0`, `0x004D0C18`, and `0x004D0C3C` as `Receivers`, `ReceiverDeps`, `ccReceivers`, and `ccReceiverDeps`. The constructor initializes these four option fields, then logs each created option-form entry with its field index, name, XML field index (`xmlfidx`), and `isInDoc` flag. This confirms a dedicated recipient/CC option-form metadata path; serialization/selection behavior remains open.

## Descriptor-map constructor caller scan: no viewer population call found yet

The latest field artifact (`14265228751`) finds five direct callers of the single-field dictionary's enumerable constructor at `0x004D5048`, but those callers are generic dictionary constructor overloads (`0x004D4FEB`, `0x004D5028`, `0x004D5140`, `0x004D522E`) plus a `TPair<UnicodeString,TXmlWordConfigTwinField>` constructor (`0x004D5CE4`). None is a `TWordViwer` method or an obvious population routine. The overloaded enumerable constructor at `0x004D5100` has no direct caller. Likewise, direct TD32 caller scans found no direct caller of the descriptor maps' `Add`/`AddOrSetValue` methods. This does not rule out indirect/VMT dispatch, but it means the initial map population is still unproven. The next trace batch now includes the dictionary getter/bucket helpers and enumerable constructors so their exact behavior and method-slot mapping can be checked before drawing conclusions.

## Full MainForm handler reveals post-parse processing helper

The full `0x0047BF30–0x0047C341` trace (`14265996115`) confirms that the first `RET` at `0x0047C0E5` is inside nested exception/finally structure, not the end of the entire handler. The main success path calls `ParseMethod` at `0x0047C0C5`, then executes cleanup at `0x0047E2D4`. Separate status/error branches later call `0x004610FC` at `0x0047C237` and `0x0047C2A9`; this is now a candidate for the service's post-parse/request-completion behavior and has been added to the service trace and whole-PE direct-call scan. Its role is not yet assigned. Do not treat `0x0047E2D4` as dispatch.

## Byte-level rel32 CALL scanner added after linear-sweep false negative

The full handler trace proves direct relative calls to `0x004610FC` at `0x0047C237` and `0x0047C2A9`, but the first whole-PE Capstone linear-sweep scanner reported zero references. This is a false negative caused by instruction-boundary loss when linearly disassembling mixed code/data sections. Added `tools/scan_pe_rel32_call_bytes.py`, which scans executable-section bytes for `E8 + signed rel32` targets without relying on a linear disassembly. Results are deliberately labelled candidates, not confirmed calls, because byte patterns can occur inside data/immediates. Both service and BPL workflows now run this byte-level scan alongside the disassembly-based scanner; the BPL scan targets descriptor-map Add/AddOrSetValue and `AddXmlWordConfigFieldsToDic` references.

## Byte-level scan validates post-parse helper callsites

Artifact `14267210294` shows five E8-rel32 candidates targeting `0x004610FC`; two are confirmed instructions inside the complete MainForm handler (`0x0047C237` and `0x0047C2A9`). Three additional candidates occur at `0x0045EB81`, `0x0045F883`, and `0x00470F34` and require surrounding-function validation. The same scan finds four candidates targeting `0x0047E2D4`: `0x0047C0E0` (confirmed MainForm cleanup call) and three additional sites `0x0047D92F`, `0x0047DB73`, `0x0047DDB7`. These candidates support the helper's reuse in cleanup/error paths, not a dispatch role. The service workflow now emits bounded disassembly windows around all seven additional callsites and pointer refs for `0x004610FC`.

## TMainForm RTTI/VMT inspection added

The service interface inventory identifies `TMainForm` at VMT `0x0047B284`, instance size `0x434`, with class typeinfo at `0x0047BF0C`. The HTTP handler body begins at `0x0047BF30`, immediately after the class typeinfo area. The service workflow now inspects this VMT, scans pointers to the VMT and class typeinfo, and traces the full handler/callsite windows. This should help map the handler to the form's published event/method table and distinguish request dispatch from response finalization.

## Service PE import inventory added

Added `tools/list_pe_imports.py` and wired it into the service dispatch workflow. It records every imported symbol with its exact IAT VA. This will allow checking whether the service uses Delphi class/package resolution APIs or whether dispatch is mediated through a package callback/VMT rather than a direct static import. The import inventory itself is descriptive; no API semantics are inferred until the actual import list is available.

## Delphi package/class factory imports found in EmwatService.exe

Artifact `14265623608` includes the service PE import inventory. Relevant imports include:
- `LoadPackage` at IAT `0x00487680` and `UnloadPackage` at `0x0048767C`.
- `StartExe` at IAT `0x004873E0`.
- `GetClass` at IAT `0x00487B9C`.
- `ClassCreate` at IAT `0x00487410` and `ClassDestroy` at `0x0048740C`.
- `TObject.InheritsFrom`, `ClassParent`, and `ClassName` helpers.
- `GetProcAddress` at IAT `0x0048753C` and `0x004875CC`.

This is strong evidence that the service can load the BPL and resolve/create Delphi classes dynamically. It does not by itself prove which XML attribute becomes the class name or which object receives `TEmwatMethod.Invoke`. The service workflow now scans all pointer references to these IAT slots to recover the actual callsites and surrounding dispatch logic.

## Caution: generic dictionary TD32 names do not match several observed bodies

The latest descriptor-method artifact (`14265603782`) shows that some TD32 generic-method labels must not be treated as semantic proof without inspecting the body:
- `0x004D4C54` is symbol-labelled `SetItem`, but its body hashes/probes the key and returns the stored value pointer from the entry; it behaves as an indexed getter in this call path.
- `0x004D54E0` is symbol-labelled `AddOrSetValue`, but its body performs a key lookup, writes the found value pointer through an output argument, and returns a Boolean; it behaves like `TryGetValue`.
- `0x004D559C` is symbol-labelled `ContainsValue`, but it hashes the supplied string key and returns whether the key bucket exists; it behaves like `ContainsKey`.
- `0x004D552C` is symbol-labelled `ContainsKey`, but its body calls internal mutation helpers `0x004D4DA8` / `0x004D4D58` depending on the bucket result. Its exact semantic identity requires tracing those helpers.

This appears to be a generic-method symbol/implementation mapping mismatch in this binary's TD32 metadata. Consequently, earlier statements that direct scans found no callers of the *symbol-named* Add/SetItem methods are not sufficient to conclude that no insertion occurs. The next workflow batch now traces `DoAdd` (`0x004D4D08`), `DoSetValue` (`0x004D4D58`), and `DoRemove` (`0x004D4DA8`) to establish the actual mutation behavior and call graph from machine code.

## Import thunk caller tracing added

The raw IAT pointer-reference results locate import-jump stubs rather than their high-level callsites. Each stub begins with a two-byte `mov eax,eax` prefix, followed by `jmp dword ptr [IAT]`; the IAT operand match is four bytes after the stub start, while the actual jump instruction (and rel32 CALL target) is two bytes before the operand. Example: `LoadPackage` IAT `0x00487680` is jumped through `0x00402174` (stub start `0x00402172`), and `GetClass` IAT `0x00487B9C` through `0x00402354` (stub start `0x00402352`). Follow-up trace of `0x0047E0EC` confirms a direct CALL at `0x0047E15F` to `0x00402174`, proving the package-load gate invokes `LoadPackage`. The service workflow now targets the actual jump-instruction addresses for CALL-site scanning of `GetClass`, `ClassCreate`, `ClassDestroy`, `LoadPackage`, `GetProcAddress`, and `StartExe`.

## Descriptor dictionary VMT/method pointer scan added

Because direct-call scans cannot resolve VMT/interface calls, the Word workflow now scans raw pointer references to the descriptor dictionary's `DoAdd`, `DoSetValue`, `DoRemove`, `Add`, `AddOrSetValue`, `ContainsKey`/`ContainsValue`-labelled methods, and twin-map Add/AddOrSetValue methods. These matches will be reviewed as candidate method-table/data references, not assumed callsites. This complements the direct rel32 byte scan and TD32 procedure traces.

## Absolute IAT CALL/JMP scanner added for Delphi runtime imports

The import-thunk trace confirms that service import wrappers are `mov eax,eax; jmp dword ptr [IAT]` stubs, and no rel32 CALL candidates target those wrapper addresses. Delphi-generated code can instead issue `FF 15 <IAT>` directly. Added `tools/scan_pe_ff15_iat_refs.py` to scan executable bytes for absolute indirect CALL (`FF 15`) and JMP (`FF 25`) references to each imported IAT slot. The service workflow now scans `LoadPackage`, `GetClass`, `ClassCreate`, `ClassDestroy`, `GetProcAddress`, and `StartExe` this way. This should recover the real callsites that a rel32 scan cannot see.

## IAT thunk scan result and next pointer-xref layer

The absolute IAT scanner (`14266043661`) finds only the expected `JMP [IAT]` stubs for `LoadPackage`, `GetClass`, `ClassCreate`, `ClassDestroy`, `GetProcAddress`, and `StartExe`; it finds no direct `CALL [IAT]` sites. The rel32 scan also found no direct CALLs to the thunk entries. This indicates the API references may be mediated by stored function pointers, runtime package tables, or other indirect dispatch. The service workflow now additionally scans raw pointer references to the thunk code addresses themselves, to locate registration tables or callback fields before deciding the imports are unused.

### Confirmed LoadPackage callsite

The service trace at `0x0047E0EC` executes `call 0x00402174` at `0x0047E15F`. The target is the `jmp dword ptr [0x00487680]` thunk for imported `LoadPackage`. The helper constructs the package path/name around literal `EmwatMethods.bpl`, invokes this loader, stores the returned module pointer, and logs either `Unable to load "EmwatMethods.bpl".` or `"EmwatMethods.bpl" loaded.` This closes the actual package-loading edge. The class-resolution side (`GetClass`/`ClassCreate`) remains to be traced at their corrected jump-instruction targets.

## TMainForm published-method RTTI table inspection

Extended `tools/inspect_delphi_vmt_address.py` to expose Delphi VMT method-table and field-table pointers (`VMT-0x40` and `VMT-0x44`) and emit bounded raw-byte/ASCII views of those tables. The service workflow now compiles the inspector and runs it on `TMainForm` VMT `0x0047B284`. This is intended to recover published event/method names and code addresses despite the service PE lacking TD32 symbols; table layout will be decoded only after validating the raw structure.

### Corrected rel32 thunk target offset

The first rel32 scan targeted the start of each import stub (`mov eax,eax`) and therefore missed calls that enter two bytes later at the actual `jmp [IAT]` instruction. The service workflow now scans the corrected targets: `ClassCreate 0x00401158`, `ClassDestroy 0x00401160`, `StartExe 0x004011B8`, `GetProcAddress 0x00401464/0x00401D7C`, `LoadPackage 0x00402174`, and `GetClass 0x00402354`. `LoadPackage` at `0x00402174` is already independently confirmed from `0x0047E15F`.

## TMainForm published method table partially decoded

The `TMainForm` VMT method-table pointer at `VMT-0x40` is `0x0047B84E`. Its raw layout is confirmed as a 16-bit entry count followed by repeated `{uint16 entry_size, uint32 code_address, shortstring method_name}` records. The table count is 17. The first seven entries recovered from the initial 128-byte sample are:
- `IdHTTPServerCommandGet` → `0x0047BF30` (the complete HTTP handler traced earlier).
- `FormCreate` → `0x0047CCD8`.
- `Terminate` → `0x0047E3EC`.
- `Log` → `0x0047D2C8`.
- `ShowMainForm` → `0x0047DF4C`.
- `HideMainForm` → `0x0047DF58`.
- `FormClose` → `0x0047CCC8`.

This confirms that the HTTP handler is a published `TMainForm` method, not an arbitrary code-range guess. `inspect_delphi_vmt_address.py` now decodes the full published method table (up to a bounded 512-byte read) so the remaining ten entries can be inventoried and followed.

## GetClass callsite found inside ParseMethod

Corrected thunk-target scan artifact `14267877222` finds one rel32 CALL candidate to the `GetClass` import jump instruction at `0x00402354`: callsite `0x00470E07`, inside `ParseMethod` (`0x00470D00`). This directly links the XML method parser to Delphi runtime class resolution. The current short trace of `ParseMethod` stops at an internal exception/finally RET before reaching `0x00470E07`; the service workflow now captures the complete bounded range `0x00470D00–0x00471033` to identify the class-name input, resulting TClass, object construction, and any subsequent method dispatch.

### Full TMainForm published method inventory recovered

The expanded VMT inspector output (`14266199135`) decodes all 17 published methods in `TMainForm`:
- `IdHTTPServerCommandGet` → `0x0047BF30`
- `FormCreate` → `0x0047CCD8`
- `Terminate` → `0x0047E3EC`
- `Log` → `0x0047D2C8`
- `ShowMainForm` → `0x0047DF4C`
- `HideMainForm` → `0x0047DF58`
- `FormClose` → `0x0047CCC8`
- `Write2Reg` → `0x0047E68C`
- `LoadQuickConfig` → `0x0047E7E4`
- `ClearLog` → `0x0047CCB0`
- `FormShow` → `0x0047D0DC`
- `mniSettingClick` → `0x0047D870`
- `mniRestartClick` → `0x0047D864`
- `SendLogsMenuItemClick` → `0x0047DAB4`
- `ShowLastEditedDocsMenuItemClick` → `0x0047DCF8`
- `tmrCheckCrashTimer` → `0x0047E474`
- `IdHTTPServerException` → `0x0047CA44`

The service workflow now traces `FormCreate`, `FormClose`, `Terminate`, `LoadQuickConfig`, and `IdHTTPServerException` in addition to the already traced request handler and package loader.

### ClassCreate callsite belongs to TMethodInfo construction

The corrected rel32 scan found a `ClassCreate` thunk call at `0x00471220`, but the surrounding trace (`0x00471214`) proves this is the Delphi constructor prologue for `TMethodInfo` (`0x0047097C`): when the constructor flag is set, it calls `ClassCreate` via thunk `0x00401158`, then creates the `TDictionary<AnsiString,AnsiString>` at `0x00471232` and stores it at `TMethodInfo+0x08`. This is allocation of the parser's metadata object, not proof of creation of the XML-selected method class. The `GetClass` candidate at `0x00470E07` remains a separate path to validate.

### GetClass callsite confirmed in ParseMethod code island

The code-island trace (`14268370537`) resolves the previous boundary uncertainty. `ParseMethod` at `0x00470D00` branches from `0x00470D74` to `0x00470DB2`; that reachable block reads the XML class attribute, obtains the class-name string, and calls `GetClass` through thunk `0x00402354` at `0x00470E07`. If the returned class is null, it constructs/logs an error and exits; otherwise it continues with class validation and object preparation. This is now a confirmed `ParseMethod` → `GetClass` edge. The remaining `0x00470E58–0x00470F80` block is being traced to identify inheritance checks, instance creation, and the final Invoke dispatch.

## ParseMethod class-validation block and class RTTI APIs queued

The reachable `GetClass` path stores the returned class pointer in `EBX`, tests for nil, then calls a helper at `0x004010B8` with the class pointer and an output slot; it subsequently compares the resulting string/value against a constant at `0x00471128` and stores a Boolean in `TMethodInfo+0x04`. The following code block (`0x00470E58–0x00470F80`) likely performs class validation and method-object preparation, but its exact semantics are not yet assigned. Added a bounded trace for this entire block and decoded its nearby string constants (`0x004710E0`, `0x004710F0`, `0x00471110`, `0x00471128`, `0x00471150`, `0x004711FC`). The service import scan now also includes `TObject.InheritsFrom`, `AsClass`, `IsClass`, `ClassName`, and `ClassType` to map which RTTI helpers are used.

## BPL published-method RTTI tables queued for dispatch crosswalk

The BPL VMT inventory shows `TEmwatMethod` at `0x0046ABFC` and `TEditWordDocument` at `0x005ED764`. The former's class-name-adjacent RTTI bytes include the published method name `Invoke`, while the subclass VMT slot `+0x10` points to `TEditWordDocument.PerformMethod` (`0x005EE82C`). The service-side `GetClass`/class-creation chain needs to be matched to this BPL class/method metadata. The Word workflow now runs the enhanced VMT inspector on both class VMTs to decode their full published method tables, including code addresses, and to confirm whether `Invoke` is a published method or a normal virtual slot.

## ParseMethod constructs request class and performs indirect virtual call

The class-validation block (`14269340064`) reveals the next part of the request path:
1. `GetClass` returns a class reference in `EBX`.
2. A helper at `0x004010B8` obtains a class-related string/value, which is compared against literal `TUpgradeEmwat` at `0x00471128`; the result is stored as a Boolean at `TMethodInfo+0x04`.
3. The class is instantiated through helper `0x004010D8`; the returned object pointer is stored in `EBX`.
4. The service stores the `TMethodInfo` pointer at `[object+0x04]`.
5. It loads the parsed parameter dictionary from `[TMethodInfo+0x08]` and makes an indirect virtual call through `[object.VMT+0x0C]` at `0x00470EF6`, passing the request context and dictionary.

This is the first concrete class-instance → virtual-dispatch edge in the service path and is the strongest candidate for the BPL `Invoke` bridge. The slot identity is not yet asserted: the current BPL VMT dump labels `TEmwatMethod+0x0C` as `Finalization`, while `TEmwatMethod.Invoke` is at `0x0046C82C` and `PerformMethod` is a separate virtual slot at `+0x10`. The enhanced BPL method-table/VMT trace and service helper traces must resolve whether the service object uses an interface-adjusted VMT, a wrapper class, or another slot mapping before calling this `Invoke`.

### Service class-validation helpers resolved

The service helper traces (`14266694185`) resolve the three calls in `ParseMethod`:
- `0x004010B8` is the import thunk for `TObject.ClassName` (IAT `0x00487460`). It obtains the selected class's name.
- `0x00401320` is the import thunk for `System.UStrEqual` (IAT `0x0048732C`). It compares the returned class name against literal `TUpgradeEmwat` at `0x00471128`, and the equality result is stored at `TMethodInfo+0x04`.
- `0x004010D8` is the import thunk for `TObject.Create` (IAT `0x00487450`). It constructs an instance of the class returned by `GetClass`.

Thus the class-name validation and object-construction sequence is confirmed, not inferred. The subsequent VMT `+0x0C` call remains the final dispatch slot to map to the BPL method.

## Service-to-BPL dispatch edge closed through TEmwatMethod VMT

The service call at `0x00470EF6` is `call dword ptr [object.VMT+0x0C]`. The BPL VMT for `TEmwatMethod` (`0x0046ABFC`) has slot `+0x0C = 0x0046C9E0`, TD32-labelled `@Emwatmethod@Finalization$qqrv`. The TD32 direct-caller artifact for `TEmwatMethod.Invoke` (`0x0046C82C`) shows that this `Finalization` routine calls `Invoke` at `0x0046CA67`. Therefore the cross-module chain is now proven:

`EmwatService.ParseMethod` → `GetClass` → `TObject.Create` → object VMT slot `+0x0C` → `TEmwatMethod.Finalization` (`0x0046C9E0`) → `TEmwatMethod.Invoke` (`0x0046C82C`).

The full `Invoke` range (`0x0046C82C–0x0046C9DD`) is now decoded. `Invoke` processes the `TMethodInfo`/parameter data but does not itself call `PerformMethod`. The subsequent virtual call is in the enclosing `TEmwatMethod.Finalization` wrapper at `0x0046CA88`, through the object's VMT slot `+0x10`. For the `TEditWordDocument` VMT (`0x005ED764`), slot `+0x10` points to `0x005EE82C` (TD32 procedure symbol `TScanDocument.PerformMethod`), which calls `TWordViwer.LoadDocument` (`0x004B7724`). Thus the complete chain is service → VMT+0x0C Finalization → Invoke → VMT+0x10 PerformMethod → LoadDocument; the `Invoke`/`PerformMethod` distinction is now explicit.

## Full Invoke body trace added

The TD32 procedure size for `TEmwatMethod.Invoke` at `0x0046C82C` is `0x1B1`, ending at `0x0046C9DD`. The previous `trace_pe_target` stopped at its first internal RET at `0x0046C95B`, so it omitted the remaining exception/finally and dispatch paths. The BPL workflow now adds a caller-bounded full-range disassembly from `0x0046C82C` through `0x0046C9DD` to locate the exact VMT `+0x10` `PerformMethod` invocation and parameter mapping.

### XML class attribute is prefixed with `T` before GetClass

The `ParseMethod` code island at `0x00470DF4–0x00470E07` resolves the exact class-name transformation: it reads the XML `class` attribute, loads the one-character string literal `T` at `0x004710E0`, concatenates it with the supplied class name through helper `0x00401310`, then passes the resulting string to `GetClass` at `0x00470E07`. Thus XML `class="EditWordDocument"` resolves Delphi class `TEditWordDocument`; this matches the BPL VMT at `0x005ED764`. The special comparison against `TUpgradeEmwat` is performed on the resolved class's actual `ClassName`, not the raw XML attribute.

## FormCreate wires the HTTP server event callback

The `TMainForm.FormCreate` trace (`0x0047CCD8`) creates the `TIdHTTPServer` component and stores it at `TMainForm+0x428`. It then writes a Delphi method pointer into the server object: code address `0x0047DF64` at server offset `+0x120`, and the `TMainForm` instance pointer at `+0x124`. This indicates the actual Indy `OnCommandGet` event callback is `0x0047DF64`; the published method `IdHTTPServerCommandGet` at `0x0047BF30` may be called by this wrapper or represent a separate entry. The service workflow now traces `0x0047DF64` to resolve the exact callback chain. `IdHTTPServerException` at `0x0047CA44` is a small wrapper that calls helper `0x0047D5A4`; that helper is also now traced to identify HTTP error handling.

## Indy HTTP event callback wrapper identified

`TMainForm.FormCreate` installs a method pointer on the `TIdHTTPServer` instance: code `0x0047DF64`, data `TMainForm`. The callback at `0x0047DF64` inspects the request/event argument at `[EDX+4]` against the form's state at `+0x420` and constants `0x16`/`0x11`; on matching cases it calls `0x0047DF84`. This establishes `0x0047DF64` as the actual server event callback wrapper, not the published `IdHTTPServerCommandGet` method itself. The next helper `0x0047DF84` is now traced to see whether it routes to `IdHTTPServerCommandGet` (`0x0047BF30`) or a related command handler.

## Finalization wrapper calls Invoke and then PerformMethod

The full `TEmwatMethod.Finalization` trace (`0x0046C9E0–0x0046CC98`) shows the exact order:
- `0x0046CA67`: direct call to `TEmwatMethod.Invoke` (`0x0046C82C`) with the request metadata object.
- `0x0046CA88`: indirect call through `[object.VMT+0x10]`, passing the same request metadata and context.

The full `Invoke` body (`0x0046C82C–0x0046C9DD`) handles the parameter data and collection enumeration; it does not itself call `PerformMethod`. The `+0x10` call is in `Finalization`, after `Invoke` returns. For the BPL VMT named `TEditWordDocument` at `0x005ED764`, slot `+0x10` points to `0x005EE82C`; its TD32 procedure name is `TScanDocument.PerformMethod` (a symbol/class-name mismatch worth preserving), and that implementation calls `TWordViwer.LoadDocument` at `0x004B7724`. This closes the full service-to-document-load dispatch path.

### TD32 sizes for dispatch wrapper and Invoke

The BPL TD32 trace (`14269626143`) confirms `TEmwatMethod.Finalization` spans `0x0046C9E0–0x0046CDF7` (size `0x418`), while `TEmwatMethod.Invoke` spans `0x0046C82C–0x0046C9DD` (size `0x1B1`). The full Finalization workflow range has been extended to the exact TD32 end address `0x0046CDF7`; the earlier `0x0046CC98` range omitted its exception/finally tail, though it already contained the key Invoke and PerformMethod calls.

## Virtual AddXml method and map population boundary clarified

The newest field artifact (`14271907043`) confirms `TWordViwer.AddXmlWordConfigFieldsToDic` at `0x004D1148` is installed in the `TWordViwer` VMT at slot `+0x2A4` (`bpl-vmt.md`, around line 6411). This explains why direct CALL scans find no caller: invocation is virtual. Its decoded body, however, does not insert descriptor entries: it clears viewer collections at `+0x64`, `+0x68`, and `+0x6C`, runs XML/interface cleanup around `+0x44`, calls `TWordApplication.ScreenRefresh` (`0x00441DD4`), and logs completion. Its method name/diagnostics therefore cannot be treated as proof of dictionary population.

The paired `TWordViwer.AddCustomDocPropertiesToDic` (`0x004D1454`) is directly called by `LoadDocument` (`0x004B7994`). It enumerates Word custom properties, splits property names on `†`, and calls the generic dictionary `Remove` methods: single-field map `Remove` at `0x004D531C` and twin-field map `Remove` at `0x004D68D4`. This is consistent with removing descriptors matched by Word custom properties. The generic `Add` / `AddOrSetValue` implementations exist (`0x004D52DC`, `0x004D54E0`, `0x004D6894`, `0x004D6A98`), but no direct code CALL sites were found; raw pointer matches for these addresses occur in Delphi RTTI/method metadata and are not proven runtime calls. Thus the initial descriptor-map population path remains unresolved.

## Service import-reference scan interpretation corrected

The service artifact (`14266461337`) shows each imported Delphi API's exact IAT address appears once in a compiler-generated import thunk (`jmp dword ptr [IAT]`), not at its actual high-level callsites. For example `GetClass` IAT `0x00487B9C` is referenced by thunk `0x00402356`, `LoadPackage` IAT `0x00487680` by thunk `0x00402176`, and `ClassCreate` IAT `0x00487410` by thunk `0x0040115A`. Those raw pointer references are not themselves dispatch callsites. The service workflow now traces each thunk body and scans direct/rel32 callers of the thunk addresses to recover actual usage. Until that run completes, the import table proves runtime capability but not the exact call chain.

## Descriptor dictionary VMT-based population trace batch — 2026-11-17

The latest BPL inventory identifies the concrete generic dictionary VMTs for the two unresolved descriptor maps:
- `TDictionary<string,TXmlWordConfigField>` VMT `0x004B4C38`.
- `TDictionary<string,TXmlWordConfigTwinField>` VMT `0x004B6A70`.

The generic `Add`/`AddOrSetValue` implementations (`0x004D52DC`, `0x004D54E0`, `0x004D6894`, `0x004D6A98`) have no direct TD32 CALL xrefs. The `AddXmlWordConfigFieldsToDic` body (`0x004D1148`) clears/releases the viewer's `+0x64/+0x68/+0x6C` collections and emits refresh diagnostics; it does not show direct Add calls in its decoded body. `AddCustomDocPropertiesToDic` (`0x004D1454`) enumerates Word custom properties, constructs descriptor-shaped values, then calls `Remove` on the single/twin dictionaries. Thus the initial population path remains the principal open edge.

The next artifact batch now inspects both concrete dictionary VMTs, scans their VMT and Add-method pointer references, and decodes the two code windows containing raw references to `0x004D1148` (`0x004B1080–0x004B10D0` and `0x004B15F0–0x004B1660`). This is intended to distinguish virtual method registration/callback paths from ordinary direct calls before assigning any map-population semantics.

### Exact IAT thunk scanner replaces misaligned pointer-offset traces

The first thunk-trace batch (`14300914213`) was invalid for caller attribution: the raw pointer-reference address is the location of the four-byte IAT operand, not necessarily the beginning of the `FF 25` instruction. Some requested trace addresses consequently began mid-thunk/import-jump table and produced nonsense linear disassembly. Added `tools/scan_pe_iat_callers.py`, which matches the full `FF 25 <IAT>` / `FF 15 <IAT>` instruction and separately scans `E8 rel32` calls to the exact thunk address. The service workflow now uses this scanner directly for `LoadPackage`, `GetClass`, `ClassCreate`, `ClassDestroy`, `StartExe`, and `GetProcAddress`. Treat the previous guessed thunk-entry addresses as superseded; the new output is the source of truth.

### Add-method internal helper chain expanded

The latest TD32 body comparison shows the public single-field dictionary `Add` at `0x004D52DC` calls `0x004D5404` and then `0x004D48A8`; the twin-field `Add` at `0x004D6894` calls `0x004D69BC` and `0x004D5E60`. These internal routines are more promising than the public Add wrappers for finding the real population path. The field workflow now traces these helpers and their dictionary search/entry-management dependencies (`0x004D610C`, `0x004D6138`, `0x004D61E8`, `0x004D6310`, `0x004D48D0`, `0x004D49E0`, `0x004D49D4`, `0x004D4B80`) with direct caller scans. No map population claim is made until the helper bodies and callsites are cross-checked.

### Additional likely initializer: CreateOptionFormFields

A further candidate for the unresolved descriptor-map initialization is `TWordViwer.CrateOptionFormFields` at `0x004CFC74` (TD32 spelling preserved). It sits immediately before the viewer constructor/option-form routines in the class procedure inventory and was not included in the earlier dictionary-only trace batch. The field workflow now traces its full body and callers, cross-checking writes to viewer offsets `+0x68/+0x6C` and calls into the single/twin dictionary helpers. It remains a candidate, not an assigned population routine, until the new artifact confirms those operations.

## GetXmlFieldInfo now decoded down to twin-member selection

Artifact `14271907043` gives the full `TWordViwer.GetXmlFieldInfo` (`0x004BFC18`) branch logic. It probes the single map at `viewer+0x68` first; on hit it returns descriptor index `+0x04` and string `+0x08`. Otherwise it probes the twin map at `viewer+0x6C`; on hit it compares the requested name against descriptor members `+0x08` and `+0x0C` through `0x00403248`, resolved by the import-thunk metadata as `System.SysUtils.CompareText`. It returns the opposite member, index `+0x04`, associated string `+0x10`, and sets the twin flag. Added `resolve_twin_field_partner()` in `python/src/emwat_linux/word_fields.py` and a test covering case-insensitive matching and no-match behavior. The implementation uses Python `casefold()`; Windows locale-specific CompareText behavior remains an explicit compatibility caveat.

## Exact service Delphi import callsites recovered (run 44022802959)

The exact IAT scanner output (`14302370292`) identifies the real import thunk instruction addresses and direct callsites:
- `LoadPackage` IAT `0x00487680` → thunk `0x00402174` → direct call at `0x0047E15F`.
- `GetClass` IAT `0x00487B9C` → thunk `0x00402354` → direct call at `0x00470E07`.
- `StartExe` IAT `0x004873E0` → thunk `0x004011B8` → direct call at `0x004014BA`.
- `GetProcAddress` IAT `0x0048753C` → thunk `0x00401464` → call at `0x00401720`; second IAT `0x004875CC` → thunk `0x00401D7C` → calls at `0x00401DA8` and `0x00401DCA`.
- `ClassCreate` IAT `0x00487410` → thunk `0x00401158`, with many direct callsites across service runtime/class creation code.
- `ClassDestroy` IAT `0x0048740C` → thunk `0x00401160`, likewise with many callsites.

The key request-path pair is now localized: `ParseMethod` at `0x00470D00` reaches `GetClass` at `0x00470E07`, and the package-loading path reaches `LoadPackage` at `0x0047E15F`. This materially strengthens the dynamic class-dispatch model, but does not yet prove the final `ClassCreate`/`Invoke` sequence. The service workflow now traces the full ParseMethod range `0x00470D00–0x00471080` plus bounded contexts around the two key callsites.

## Direct service runtime import callsites confirmed — 2026-11-17

The fresh service artifact (`14300914213`) validates three key import edges by exact rel32 callsite and thunk target:

- `LoadPackage` IAT `0x00487680` is reached through thunk `0x00402174`, called from the BPL package gate at `0x0047E15F`.
- `GetClass` IAT `0x00487B9C` is reached through thunk `0x00402354`, called from `ParseMethod` at `0x00470E07` after the XML class value is prefixed with `T`.
- `ClassCreate` IAT `0x00487410` is reached through thunk `0x00401158`, called at `0x00471220` from the `TMethodInfo` constructor (`0x00471214`). The nearby `ClassDestroy` thunk `0x00401160` is called at `0x0047127F` during metadata-object cleanup. These are parser metadata allocation/cleanup callsites; do not misattribute them to the dynamically resolved BPL method instance, which is created later through the class-reference constructor path in `ParseMethod`.

Additional rel32 candidates identify `StartExe` at `0x004014BA` and `GetProcAddress` at `0x00401720`; their surrounding helper bodies are now included in the next service workflow batch. The two GetProcAddress imports may be Delphi package/runtime infrastructure and are not yet assigned to the request method path.

## GetDocFieldIndex and FillTwinFields close the Word-side matching loop

The field artifact `14271907043` shows `GetDocFieldIndex` at `0x004C0550` iterating the live Word Fields collection. Each field code is normalized by `FindFieldInActivefields` (`0x004BC170`), then resolved through `GetXmlFieldInfo` (`0x004BFC18`). If the returned twin flag is set, the caller invokes `FillTwinFields` (`0x004C02EC`) with the current one-based Word field index and the partner field name. `FillTwinFields` scans subsequent Word fields, extracts each candidate DOCPROPERTY identifier, and uses `CompareText` (`0x00403248`) to find the first case-insensitive match; it returns the matching one-based index or zero. The caller then branches into paired handling or ordinary field/image filling, with call edges to `FillField`, `FillImageField`, `FillMSWFields`, and `AddImagesToDoc`. This connects the twin metadata map to the actual Word document's two fields and confirms the one-based search behavior already modeled in `find_native_twin_field_index()`.

### Runtime import callsite owner clarification

The bounded context confirms `TMethodInfo` construction at `0x00471214`: it calls `ClassCreate` (`0x00401158`) at `0x00471220`, initializes its Params dictionary through `0x0046AA70`, then calls the `AfterConstruction` thunk (`0x00401168`) at `0x00471240`. The `ClassDestroy` call candidate at `0x0047127F` lies in the following function, whose likely entry is `0x00471258`; the workflow now traces that function from its start and asks TD32 for its owner before finalizing the destructor attribution. `StartExe` is called at `0x004014BA` from the helper beginning around `0x00401490`, and `GetProcAddress` at `0x00401720` from a dynamic-symbol lookup loop; both owning procedures are now queried through TD32. These APIs currently look like Delphi package/runtime infrastructure, not additional method dispatch edges.

## Cross-module Invoke receiver/slot proof: targeted RTTI/VMT trace added

The service ParseMethod class-validation island shows a class reference returned by `GetClass`, a class-name comparison against the special `TUpgradeEmwat` type, construction of a method object, and an indirect call through `[object.VMT+0x0C]` at `0x00470EF6`. The BPL symbol table independently identifies `TEmwatMethod.Invoke` at `0x0046C82C`, whose parameter type is the parsed `TDictionary<AnsiString,...>` used for method parameters. This is a strong candidate match but is not yet a proven slot mapping: the current VMT inspector's `TEmwatMethod` candidate at `0x0046ABFC` has inconsistent leading-slot interpretation, and the `Invoke` entry may be represented in method/interface RTTI rather than the inspected leading slots. Added targeted BPL traces for the `0x0046ABFC–0x0046AC90` RTTI/VMT region, raw pointer references and immediate references to `0x0046C82C`, and class metadata strings. The next evidence needed is a verified table entry or a bounded cross-module ABI match tying service `call [VMT+0x0C]` to the BPL `Invoke` method.

### TMethodInfo destructor and package-runtime helper classification confirmed

Artifact `14301877366` traces the function beginning at `0x00471258`: it obtains the `TMethodInfo` instance, frees its Params dictionary at object offset `+0x08`, runs the destruction helper, and calls `ClassDestroy` through thunk `0x00401160` at `0x0047127F`. This closes the constructor/destructor pair: `TMethodInfo` is created at `0x00471220` via `ClassCreate`, its Params dictionary is initialized at `0x00471232`, and the object is destroyed through the `0x00471258` cleanup routine.

The `StartExe` call at `0x004014BA` is inside a small package startup helper that prepares global package-info pointers and then calls `StartExe`; it is runtime/package initialization, not the HTTP request dispatch path. `GetProcAddress` at `0x00401720` is inside a dynamic-symbol lookup loop; a second wrapper at `0x00401D84` handles name/ordinal forms and calls the imported GetProcAddress thunk. Neither helper is currently evidence of another EMWAT method dispatch edge.

## ParseMethod class resolution and object invocation island decoded

Aligned trace artifact `14301682420` confirms the GetClass callsite at `0x00470E07` and the subsequent runtime sequence. The class name comes from the parsed XML method element; a null GetClass result formats/logs `Unable to load "<class>" class.` On success, the service calls `TObject.ClassName`, compares against the special hard-coded `TUpgradeEmwat` class name through `@UStrEqual`, and stores the boolean at method-info `+0x04`. It then invokes `TObject.$bctr` (`0x004010D8`) on the resolved class reference, stores the method-info pointer at the new instance `+0x04`, and performs an indirect call through `[instance.VMT+0x0C]` at `0x00470EF6`. This confirms the runtime class factory/indirect invocation shape. The target slot's exact mapping to `TEmwatMethod.Invoke` (`0x0046C82C`) is still unproven; the BPL workflow now examines the `TEmwatMethod` class RTTI/VMT bytes and Invoke pointer references to settle it.

## TD32 batch scanner added to shorten repeated binary-analysis runs — 2026-11-17

The field workflow previously reparsed the same TD32 subsection directory twice per target (`trace_td32_procedure.py` and `trace_td32_callers.py`) across 69 target addresses. Added `tools/trace_td32_batch.py`: it loads/parses TD32 once, decodes each procedure once, then emits the same per-target `*-td32.md` and `*-callers.md` artifacts. The workflow now uses the batch tool while retaining bounded linear traces for each target. This preserves the existing report naming and content contract while avoiding repeated debug-directory scans.

## Class-name prefix before GetClass identified as a targeted question

The aligned ParseMethod island shows `mov edx, 0x004710E0` immediately before `call 0x00401310`, then loads the resulting local string into EAX and calls `GetClass` at `0x00470E07`. The decoded string at `0x004710E0` is exactly `T`. This strongly suggests the service prefixes the XML class attribute with Delphi's conventional `T` class prefix before runtime lookup (e.g. request `EditWordDocument` → registered class `TEditWordDocument`), which matches the recovered BPL class symbol. The semantics of helper `0x00401310` have not yet been decoded; a dedicated helper/caller trace is now in the service workflow before this is treated as confirmed string concatenation.
