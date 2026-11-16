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
