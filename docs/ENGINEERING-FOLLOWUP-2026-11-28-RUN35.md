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

Test commits: `063f0c63666040b2d4d149fae08a3382db168a30` (worker-start race) and `eba0ddb803d264ad6c469394b866eb2d7806b64a` (counter rollback when worker creation raises).

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
