## Latest desktop lifecycle verification — 2026-11-23

- Python workflow [45195106455](https://github.com/meicamghe/EMWAT-Linux/actions/runs/45195106455) on code/test head `4c43ae3c836f845751b4e9d8c462758ab6a1a2c1`: success, 292 tests run, 289 passed and 3 optional skips.
- GTK workflow [45195106572](https://github.com/meicamghe/EMWAT-Linux/actions/runs/45195106572) on the same head: success, 7/7 runtime tests passed, including deterministic Start-versus-shutdown serialization. Per-user launcher install, desktop-file validation and uninstall passed.
- Native workflow [45195106435](https://github.com/meicamghe/EMWAT-Linux/actions/runs/45195106435) on the same head: build/CTest 4/4, ASan/UBSan 4/4, staged install and Debian package lifecycle passed.
- LibreOffice UNO workflow [45194019476](https://github.com/meicamghe/EMWAT-Linux/actions/runs/45194019476): 25 tests passed on parent head `4c521f0de592bf1a9e5fab2fabf85699e70bfa65`; no UNO source changed afterward. A current-head rerun is queued.
- This evidence does not close the product-level release blockers listed above.

# EMWAT Linux release acceptance matrix

Status: engineering checklist; this document does not declare a release.
Last reviewed: 2026-11-23
Current development branch: `feature/recovery-retention-policy`

This matrix separates automated evidence, manually observed component behavior,
and product-level acceptance. A green unit/CI run must never be presented as
proof of live Almas compatibility.

## Acceptance layers

| Layer | What is covered | Evidence / current status | Release interpretation |
|---|---|---|---|
| Python bridge and protocol | HTTP loopback transport, Origin/Host validation, XML dispatch, EditWord parsing/serialization, recovery and doctor tests | Code/test head `4c43ae3c836f845751b4e9d8c462758ab6a1a2c1`: Python workflow `45195106455` succeeded; **292 tests run, 289 passed, 3 optional skips**; package install and console-entrypoint checks passed | Automated component evidence only |
| Native core | CMake build, native tests, sanitizer checks, Debian development-package lifecycle | Code/test head `4c43ae3c836f845751b4e9d8c462758ab6a1a2c1`: Native workflow `45195106435` succeeded; build/CTest **4/4**, ASan/UBSan **4/4**, staged install and Debian package lifecycle passed | Native library/package evidence only; not complete application package |
| LibreOffice UNO | UNO runtime checks and Writer roundtrip integration | UNO workflow `45194019476` succeeded with **25 tests** on parent head `4c521f0de592bf1a9e5fab2fabf85699e70bfa65`; subsequent commits to `4c43ae3` changed GTK lifecycle and tests only, not UNO adapter sources. Current-head rerun is queued. | Does not prove Almas browser integration |
| Writer close decisions | Save, Don't Save and Cancel behavior in a real Writer session | Manual acceptance on 2026-11-23: saved marker persisted; discarded marker did not; Cancel left Writer open and pending until a later close | Confirms the observed Writer close boundary, not Almas response semantics |
| Runtime doctor | Installed `emwat-linux-doctor` console entrypoint and help invocation | Verified in Python workflow `45184251311`; package install and `emwat-linux-doctor --help` passed | Dependency preflight only; not a bridge launcher |
| GTK desktop shell and Recovery | Real GTK 4 runtime, recovery picker, injected supervisor controls, shutdown ordering, and per-user launcher lifecycle | GTK workflow `45195106572` on `4c43ae3` succeeded with **7/7 smoke tests**; installer path-with-spaces, desktop-file validation, install and uninstall passed | UI component evidence only; default entry point still has no production supervisor configuration |
| Physical scanner | SANE discovery/options, planar RGB frame assembly, bounded simplex ADF batching and cleanup/resource limits | Automated tests cover bounded batch sequencing, feeder-empty/error cleanup, planar RGB interleaving/metadata validation; no physical device fixture | Physical USB/network scanner acceptance remains open; duplex source labels are deliberately excluded from batch mode |
| Word-to-Writer semantic mapping | Candidate field audit and indexed signer catalog | Read-only audit tooling; no authoritative sanitized Word + WordConfig fixture | No automatic mapping should be enabled from candidates alone |
| Almas end-to-end | Real browser Origin, init, heartbeat, request, Writer lifecycle and returned response | Not yet accepted; requires controlled test account and sanitized complete request/response fixtures | Release blocker |
| Cancel / discard wire response | Exact response envelope Almas expects for each non-success close decision | Not yet established; factory intentionally remains injected | Release blocker; do not invent the response |
| Windows `.easz` interoperability | Archive creation/opening and password/error behavior | Static trace only; no validated interoperability fixture | Not implemented/verified |
| Desktop packaging and supervision | Per-user .desktop install/uninstall scripts with tested Exec-path quoting; GTK controls for explicitly injected supervisor; no complete Python bridge .deb, persistent user service, deployment settings or configured production supervisor | Partial launcher and lifecycle controls only | Release blocker |

## Required Almas acceptance fixture

Use a controlled test account and synthetic document content. Capture only what
is necessary to establish the protocol contract. Before storing a fixture:

- Replace session cookies, authorization values, user identifiers and personal
  data with deterministic placeholders.
- Replace letter text, signer details, signature images and attachments with
  synthetic values.
- Preserve XML element order, parameter names, encoding declarations, empty
  values, delimiters, and byte lengths only where those details are part of the
  behavior being tested.
- Include the full outer request envelope and the complete expected response;
  a partial XML fragment is insufficient.
- Keep separate expected outcomes for Save, Don't Save and application-level
  Cancel if Almas exposes those decisions differently.
- Do not commit HAR files, browser profiles, tokens, private documents or
  production customer data.

Minimum fixture set:

1. Successful editable-letter request with matching expected response bytes.
2. Save path, with a known changed document and expected returned payload.
3. Don't Save path, with an unsaved marker that must not appear in returned data.
4. Cancel path, including the exact browser-facing behavior and whether the
   request remains pending or is completed with a non-success response.
5. Field-mapping sample with synthetic Word custom properties, WordConfig,
   indexed signer fields, non-ASCII text, empty values and delimiter collisions.
6. If image/signature support is in scope for the tested workflow, synthetic
   image bytes and the exact expected `signData` transformation.

## Parallel work that can proceed without those fixtures

- Continue protocol and transport hardening with synthetic regression cases.
- Keep recovery storage, retention, key custody and scanner input validation
  isolated from the Almas response contract.
- Improve read-only diagnostics, packaging metadata and headless testability.
- Extend field catalog and mapping audit reports without enabling guessed
  Word-to-Writer mappings.
- Maintain Linux-only GTK 4 + Python/PyGObject control UI and LibreOffice UNO
  document editing boundaries.

## Release gate

Do not mark the project production-ready until all release blockers above have
either passed acceptance with recorded evidence or been explicitly removed from
the product scope by a documented decision. Keep the pull request Draft until
the live integration contract, user-facing runtime and packaging are reviewed.

## Latest bridge regression run — 2026-11-23

The Python bridge workflow on commit
`d3f2333dc24e38c706415b14d0be4cff8d195a9e` completed successfully:
242 tests passed, 2 skipped. This run includes strict Host-header rejection
cases and runtime-doctor minimum-Python / missing-dependency JSON cases. The
installed package console-entrypoint check also passed. This remains automated
component evidence, not live Almas end-to-end acceptance.

## Latest runtime-safety regressions

- Recovery store operations are serialized by a process-local reentrant lock shared by store instances using the same canonical root. Concurrent writer regression passed in Python workflow `45144581638` (244 tests, 2 optional skips). This is not an inter-process lock; do not share one recovery root across multiple EMWAT processes yet.
- HTTP request worker threads are non-daemon so `shutdown()` followed by `server_close()` waits for in-flight requests. The active-request shutdown regression passed in Python workflow `45144669416`.
- Neither change provides a production daemon, launcher, or Almas end-to-end acceptance.


## Verified PR head — 2026-11-23 (80fa1ec)

The current pull-request head was rechecked against GitHub's commit check-runs
API. All six checks attached to this exact commit completed successfully:

| Check | Result |
|---|---|
| Python bridge test | Success |
| GTK activation smoke test | Success |
| LibreOffice UNO roundtrip | Success |
| Native build/test | Success |
| Native ASan/UBSan | Success |
| Debian package lifecycle | Success |

Workflow runs:
- Python bridge: [45163915417](https://github.com/meicamghe/EMWAT-Linux/actions/runs/45163915417)
- GTK desktop: [45163915499](https://github.com/meicamghe/EMWAT-Linux/actions/runs/45163915499)
- LibreOffice UNO: [45163915318](https://github.com/meicamghe/EMWAT-Linux/actions/runs/45163915318)
- Native build, sanitizer and package lifecycle: [45163915407](https://github.com/meicamghe/EMWAT-Linux/actions/runs/45163915407)

This verification applies to commit `80fa1ec256f98622b80bc86d5b32425213e8b807`
only. It does not change the release blockers in this matrix: live Almas
integration, verified WordConfig semantic mapping, physical scanner/ADF/duplex,
Windows `.easz` interoperability, and complete desktop runtime packaging.
PR #2 remains open, Draft and unmerged.
