# Bridge supervisor lifecycle

`BridgeSupervisor` is the application-level owner for starting and stopping
the local HTTP bridge. It is intentionally separate from GTK and from Almas
protocol configuration.

## Configuration boundary

A deployment injects a `server_factory` that returns a fully configured
`BridgeHTTPServer` (or compatible server). The factory is responsible for
providing the verified browser Origin allowlist, parent-page Origin allowlist,
method registry, and captured response contracts. The supervisor does not
supply defaults for these values and must not be wired to guessed Almas origins
or guessed Cancel/Discard responses.

## Lifecycle

- `IDLE` → `STARTING` → `RUNNING`: a fresh server and one-shot
  `BridgeRuntime` are created and started.
- Calling `start()` while running returns the current runtime; it does not
  create a second listener.
- `stop()` closes the runtime and reaches `STOPPED`.
- Starting after a successful stop asks the factory for a new server because a
  closed `HTTPServer` cannot be restarted.
- A failed start or stop is surfaced as `FAILED`. A failed cleanup must be
  retried with `stop()` before a new start is allowed. The supervisor
  never hides a potentially live serving thread by silently replacing it.
- An unexpected serving-loop exit is reflected as `FAILED` when the
  supervisor's `state` or `failure` property is next read; callers do not
  need to issue a second `start()` merely to discover the failure.
  Once `stop()` confirms cleanup, the supervisor may start a fresh server;
  the previous runtime failure remains available diagnostically until that
  next start clears it.
- `stop()` before the first start is safe and idempotent.

## GTK control boundary

The GTK shell accepts an optional, explicitly injected supervisor. When one is
provided, Start and Stop invoke it on worker threads; the GTK main thread is not
blocked by lifecycle operations. The displayed state is refreshed after each
operation and polled on the GTK main context so an unexpected serving-thread
exit can become visible without requiring another button click. Closing the
window stops the poll on its next tick.

The normal `main()` entrypoint still injects no supervisor. Consequently the
controls are intentionally disabled in the shipped default shell and no
listener starts automatically. Persistent deployment settings, a verified
Almas configuration, and desktop-session notifications remain future work.
