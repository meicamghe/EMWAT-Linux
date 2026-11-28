# Almas loopback bridge — GTK startup wiring plan

## Evidence-backed deployment values

The native PCAP and browser screenshot establish the local bridge endpoints:

- Bind address: 127.0.0.1
- Port: 1984
- XHR Origin: http://127.0.0.1:1984
- Init Referer origin: http://127.0.0.1:1984
- Init query: /?init=<digits>_<digits>
- Heartbeat: /?heartbeat -> TickTack
- Invoke: POST /?invoke=<numeric nonce>
- Request Content-Type: text/plain;charset=UTF-8
- Success response Content-Type: text/html; charset=ISO-8859-1

The external Almas web page hostname is not the Origin of the captured loopback XHR. Do not require or guess an external hostname for the bridge's CORS allowlists. Keep the listener on IPv4 loopback only.

## Composition to inject

The GTK entry point should construct one fully configured BridgeSupervisor with a fresh service/server per start:

1. LibreOfficeAdapter configured with per-user temporary document/profile roots.
2. EditWordDocumentService wrapping that adapter.
3. create_editword_handler with a fail-closed explicit-discard response policy.
4. XMLMethodDispatcher with only the allowlisted class EditWordDocument registered.
5. BridgeHTTPServer configured with:
   - host 127.0.0.1
   - port 1984
   - allowed_origins = {http://127.0.0.1:1984}
   - allowed_parent_origins = {http://127.0.0.1:1984}
   - require_origin = true
   - max_body_bytes/max_response_bytes at least 16 MiB (captured request/response are about 1.18/1.17 MB)
6. BridgeSupervisor(server_factory), injected into create_desktop_application(bridge_supervisor=...).

The server factory must return a fresh server/service/adapter on every start because BridgeRuntime is one-shot. It must not reuse a closed HTTPServer or stale Writer session.

## Explicit-discard policy

The handler requires a cancel_response_factory only for an explicit DISCARDED operation result. This is not the same as the Writer close prompt:

- Save -> confirmed saved snapshot is returned.
- Don't Save -> last confirmed saved snapshot/original input is returned as a successful closed session.
- Cancel in Writer -> Writer stays open and the HTTP request remains pending.
- Explicit operation-level DISCARDED -> fail closed with a local 409/plain-text response until the Windows wire envelope is recovered.

The 409 response is a local safety policy, not a claim of Windows protocol parity. The initial GTK UI should not expose an explicit discard action.

## Startup and shutdown behavior

- Start the supervisor on normal GTK activation after required dependencies pass; keep manual Stop available for diagnostics.
- Do not auto-start if the port is already occupied or the deployment configuration is invalid.
- Keep the GTK close-request worker asynchronous. If Writer is open, bounded drain may fail; keep the GTK window open and allow the user to close Writer and retry. Never exit while silently abandoning an Almas POST or a Writer worker.
- On a successful stop, join the serving thread and drain accepted request workers before closing the socket.
- Use the existing bridge status poll to expose RUNNING/FAILED state and the failure reason.

## Acceptance before packaging

1. Launch the actual Almas page.
2. Confirm GET init and heartbeat from the browser.
3. Open an existing Word document; verify the POST stays pending while Writer is open.
4. Edit, Save, close Writer; verify Almas receives the captured response-word envelope and persists the returned DOC.
5. Reopen in Almas and verify a unique saved marker.
6. Repeat with Don't Save and Writer Cancel; verify original-body return and pending-request behavior respectively.
7. Close GTK while Writer is open; verify bounded drain keeps the window alive, then close Writer and retry shutdown.

No production startup wiring is implemented by this plan. It is the exact next implementation contract; no external origin or response behavior should be guessed.
