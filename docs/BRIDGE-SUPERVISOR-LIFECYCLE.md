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
- An unexpected serving-loop exit is detected on the next `start()` call.
  Once `stop()` confirms cleanup, the supervisor may start a fresh server;
  the previous runtime failure remains available diagnostically until that
  next start clears it.
- `stop()` before the first start is safe and idempotent.

The supervisor does not yet own a persistent settings store, desktop-session
notifications, automatic crash restart, or a GTK start/stop control. Those
require deployment configuration and user-visible failure handling first.
