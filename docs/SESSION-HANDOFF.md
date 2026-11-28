## 2026-11-28 — Run 37 GDI+ VMT tooling coverage

- Audited `tools/resolve_delphi_vmt_slots.py`, called by the existing `image-ui-and-vmt` job. Its `TARGET_CLASSES` omits `TGPImage` and `TGPEncoderParameters`; therefore that automated VMT pass cannot close the raw GDI+ method table.
- Added the targeted extraction command to the GDI+ crosswalk:
  `python3 scripts/dump_pe_va_ranges.py analysis-input/EmwatMethods.bpl1 --range 0x00484700:0x300 --range 0x0047DD2C:0xA0 --range 0x0062EE88:0x90`.
- Run 37 report: `docs/REVERSE-ENGINEERING-PARALLEL-FOLLOWUP-2026-11-28-RUN37.md`; crosswalk update commit `c2aa4f0`; report commit `ca8553d`.
- No tool or workflow source was modified; no new workflow was triggered.

## 2026-11-28 — Run 36 diagnostic strings and automatic workflow status

- Decoded the exact SeparteImages/Worker diagnostics from Run-50 inline constants: 0x004A08F4 `Gam Printer is in "Paused" state! please check.`; 0x004A0960 `Error on setting gam printer parameters.`; 0x004A09C0 `Error occured during Convert Word Document to Tiff.` (original misspelling preserved).
- The Worker false-return path at 0x004A02C1 uses the last message. The exact path fragments and stale-output deletion helper remain open.
- Focused doc update: `docs/THIDEPRINTINGTHREAD-FILE-WAIT-ANALYSIS-2026-11-28.md` commit `bf167a2`; Run 36 report commit `86918cc`.
- Push of Python files automatically triggered the existing `EMWAT parallel reverse-engineering lanes` workflow, run 67 / ID `46136978712`. This was not manually dispatched. At last check, native-regression was running the full Python suite, while word-print-com and image-ui-and-vmt were continuing their static-analysis jobs.
- No further Python/workflow-triggering file changes are planned while run 67 is in progress. Docs-only updates do not match the workflow's push path filter. No release package was built.

## 2026-11-28 — Run 35 additional failure-path coverage

- Added `test_request_drain_releases_registration_if_worker_creation_raises`. It forces ThreadingMixIn worker creation to raise and verifies the synchronous active-request registration is rolled back, so the drain counter cannot remain permanently nonzero.
- Test commit: `eba0ddb803d264ad6c469394b866eb2d7806b64a`.
- Together with the delayed-worker test, the new tests cover both sides of the request counter: registration-before-thread-start and rollback-on-start-failure.
- Neither test has been executed; no Actions run was started.

# Engineering follow-up — 2026-11-28 Run 35

## Track A — bridge request-drain race

### Defect

The prior request-drain counter was incremented inside `process_request_thread`. Python's `ThreadingMixIn.process_request` starts a new thread and returns to the serving loop; the worker may not execute its first instruction before the accept loop observes shutdown. Therefore the serving thread could stop while an accepted worker had not yet incremented the counter. `wait_for_requests_idle()` could incorrectly return true, after which `ThreadingMixIn.server_close()` would join that non-daemon worker without a timeout.

### Correction

- Override `_ServingThreadingHTTPServer.process_request` and increment the active count synchronously in the accept-loop thread before delegating to `ThreadingMixIn`.
- If worker creation/start raises, decrement and notify in the exception path.
- Decrement only from `process_request_thread`'s `finally` block after the worker has completed.
- The runtime's shutdown order remains: stop/join accept loop -> bounded worker drain -> socket/server close -> serving-thread join.
- On drain timeout, socket closure remains deferred and retryable; non-daemon request workers are not abandoned.

Implementation commit: `eaa87e4903b47fecf1c5af7aa9503ba44fe16f63`.

### Regression coverage

Added `test_request_drain_counts_accepted_socket_before_worker_first_instruction`:
- Patches the worker entry point to pause before its first base-class instruction.
- Sends a loopback heartbeat request.
- Verifies the drain hook still sees one active request while the worker is paused.
- Releases the worker, verifies the HTTP 200 `TickTack` response, then closes the runtime.

Test commit: `063f0c63666040b2d4d149fae08a3382db168a30`.

The test has not been executed. A local shallow clone attempt could not resolve github.com in this environment; no GitHub Actions run was started.

## Track B — Almas shutdown acceptance gate

Updated `docs/ALMAS-LIVE-END-TO-END-ACCEPTANCE.md`: the implementation now has an explicit bounded drain/retry policy, but it remains unaccepted until the deterministic worker-start race test, existing pending-request drain test, GTK close-retry test, and live Almas workflow are executed/verified.

Documentation commit: `38f68dc0f0c2acbf8b9039f29d10287ded835358`.

## Remaining external gates

- Real Almas XHR Origin and parent-page Referer origins.
- Sanitized Windows `EditWordDocument` request and corresponding response bytes/headers.
- Confirmation that Almas accepts and persists the returned edited document.
- Local execution of the targeted Python tests and GTK tests on a machine with GTK 4/PyGObject.
- Actual Windows forced-termination behavior remains outside the bounded graceful-shutdown guarantee.

No release package was built, no CI workflow was started, and no PR was merged.
