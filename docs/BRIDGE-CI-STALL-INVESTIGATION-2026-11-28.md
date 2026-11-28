# Python Bridge CI stall investigation — 2026-11-28

## Scope

This report records a source-level audit of the Python bridge test suite and the diagnostic CI run after commit `adb12c4`. It does not claim to identify the blocked test. No runtime behavior was changed as part of this investigation.

## CI evidence

- PR #6 head: `6f07cbb31f04b23faf4c797f75fe47f8f0a27cb6`.
- Latest observed Python Bridge run: `46149684182`, job `140993392222`.
- Dependency installation and package/CLI entrypoint checks completed successfully.
- `Run bridge transport tests` remained `in_progress` on the latest poll.
- `Upload Python bridge diagnostics` was still pending; no artifact was available yet.
- Active job-log retrieval returned GitHub `BlobNotFound` (404), so no live traceback or current test name could be read.
- GTK desktop smoke test and Debian package lifecycle completed successfully on the same commit.

Do not interpret the pending Python step as either a pass or a test assertion failure. The workflow has a 12-minute test-process timeout inside a 15-minute job timeout; the diagnostic artifact is uploaded in an `if: always()` step after the test process exits.

## Source-level wait audit

The following test modules were inspected for waits, joins, sleeps, and server lifecycle operations:

- `python/tests/test_bridge.py`
- `python/tests/test_bridge_supervisor.py`
- `python/tests/test_application_runtime.py`
- `python/tests/test_gtk_desktop_runtime.py`
- `python/tests/test_libreoffice_integration.py`
- `python/src/emwat_linux/bridge.py`
- `python/src/emwat_linux/application_runtime.py`
- `python/src/emwat_linux/bridge_supervisor.py`

Most explicit test synchronization uses finite waits or joins (typically 0.05–3 seconds). The fake server implementations in the runtime/supervisor tests use event waits that are released by their corresponding shutdown path. The real HTTP bridge tests also use bounded request waits and thread joins.

### Remaining lifecycle risk

`BridgeRuntime.start()` calls `server.wait_until_serving()` synchronously. The protocol has no timeout parameter, and the real bridge implementation calls `_serving_event.wait()` without a timeout.

The concrete `_ServingThreadingHTTPServer` sets this event from `service_actions()` after the serve loop enters and also from `serve_forever()`'s `finally` block if the loop exits or startup raises. This makes the current implementation self-releasing for its ordinary code paths, but the interface is still unbounded if a future or injected server implementation violates that signaling contract.

This is a hardening candidate, not a proven explanation for the currently running CI stall. Do not change the startup lifecycle solely on this hypothesis before the per-test log/traceback identifies the blocked path.

## Next diagnostic sequence

1. Poll run `46149684182` until it completes or its timeout step advances.
2. Retrieve artifact `python-bridge-diagnostics-46149684182` after the upload step completes.
3. Read the last emitted `test_...` line and any recurring faulthandler thread dumps.
4. Reproduce only the identified test locally/under a bounded CI command.
5. Apply a narrow fix and add a regression test; do not increase the timeout or suppress the failing test as a workaround.

## Evidence boundaries

- No claim is made that the complete Python suite passed.
- No claim is made that the blocked test is a BridgeHTTPServer deadlock.
- No product/runtime code was modified in this investigation.
- No Windows/Almas live round-trip, physical printer, or scanner behavior is inferred from CI.
- PR #6 remains Draft/open/unmerged; do not merge without explicit user authorization.
