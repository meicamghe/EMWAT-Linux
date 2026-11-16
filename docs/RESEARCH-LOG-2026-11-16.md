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

The append helper then calls the collection's virtual methods at offsets `+0x08` and `+0x0C` with the two strings. This resolves the prior unknown record schema at the structural level. The exact collection class implementation and subsequent bridge into the BPL `TDictionary<AnsiString,AnsiString>` remain to be proven; do not conflate this service-side parser collection with the BPL dictionary until that dispatch is traced.

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
