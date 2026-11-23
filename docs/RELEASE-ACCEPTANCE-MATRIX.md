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
| Python bridge and protocol | HTTP loopback transport, Origin/Host validation, XML dispatch, EditWord parsing/serialization, recovery and doctor tests | Latest branch head `a1067bd4923dd4a448b37f754484ec9dc638ff7f`: Python workflow `45143990955` succeeded; 243 tests run, 241 passed, 2 optional skips | Automated component evidence only |
| Native core | CMake build, native tests, sanitizer checks, Debian development-package lifecycle | Latest branch head `a1067bd4923dd4a448b37f754484ec9dc638ff7f`: Native workflow `45143991103` succeeded, including build/test, ASan/UBSan and package lifecycle jobs | Native library/package evidence only; not desktop installer |
| LibreOffice UNO | UNO runtime checks and Writer roundtrip integration | Latest branch head `a1067bd4923dd4a448b37f754484ec9dc638ff7f`: UNO workflow `45143990759` succeeded | Does not prove Almas browser integration |
| Writer close decisions | Save, Don't Save and Cancel behavior in a real Writer session | Manual acceptance on 2026-11-23: saved marker persisted; discarded marker did not; Cancel left Writer open and pending until a later close | Confirms the observed Writer close boundary, not Almas response semantics |
| Runtime doctor | Installed `emwat-linux-doctor` console entrypoint and help invocation | Verified in Python CI `45143990955` on latest branch head; package install and `--help` passed | Dependency preflight only; not a bridge launcher |
| GTK Recovery view | Headless import boundary and controller behavior | Headless tests exist; live GTK desktop session not yet accepted | Optional UI component, not a complete application |
| Physical scanner | SANE device discovery and option/frame validation | Contract/fake tests only | Physical USB/network scanner, ADF and duplex remain unverified |
| Word-to-Writer semantic mapping | Candidate field audit and indexed signer catalog | Read-only audit tooling; no authoritative sanitized Word + WordConfig fixture | No automatic mapping should be enabled from candidates alone |
| Almas end-to-end | Real browser Origin, init, heartbeat, request, Writer lifecycle and returned response | Not yet accepted; requires controlled test account and sanitized complete request/response fixtures | Release blocker |
| Cancel / discard wire response | Exact response envelope Almas expects for each non-success close decision | Not yet established; factory intentionally remains injected | Release blocker; do not invent the response |
| Windows `.easz` interoperability | Archive creation/opening and password/error behavior | Static trace only; no validated interoperability fixture | Not implemented/verified |
| Desktop packaging and supervision | User-facing app entrypoint, settings, launcher, lifecycle supervision, install/upgrade/uninstall | Not complete | Release blocker |

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
