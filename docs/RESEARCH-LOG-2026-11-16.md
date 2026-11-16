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
