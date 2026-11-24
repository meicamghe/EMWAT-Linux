# EMWAT Agent ↔ Service IPC and lifecycle analysis

Date: 2026-11-24  
Source: PE32 binaries extracted from the repository's EMWAT_Extracted.zip. Static disassembly and import-thunk callsite analysis only; no Windows runtime execution.

## 1. Exact binaries analyzed

| Binary | SHA-256 | ImageBase | Entry point |
|---|---|---:|---:|
| EmwatAgent.exe | 4553c4c65a5697b5e8121ac70e894a1b98a3def470a7165d931f078d258e4157 | 0x00400000 | 0x0066E198 |
| EmwatService.exe | 9b07e270fa216095fe6648694a4896f6f8a190e69002c6742dc894c11a002659 | 0x00400000 | 0x00481C30 |

Both are PE32/x86. All addresses below are valid only for these exact hashes.

## 2. Single-instance enforcement is confirmed in both processes

### Agent

At startup (entry point 0x0066E198), Agent calls its CreateMutexW wrapper at 0x00413324. The arguments identify:

- Mutex name: {4369E136-8FCE-4475-9520-045CC47013DD}
- Initial owner: TRUE (-1)
- Security attributes: NULL

The returned handle is stored at global 0x0067DACC. Agent then calls GetLastError and compares the result with 0xB7 (183, ERROR_ALREADY_EXISTS). The already-running branch exits through its shutdown path rather than starting a second instance.

### Service

During startup at 0x00481C30, Service calls its CreateMutexW wrapper at 0x00401D04:

- Mutex name: {E67A99F0-E7AF-4083-8FD3-B3EBB601C920}
- Initial owner: TRUE (-1)
- Security attributes: NULL

The handle is stored at 0x0048524C. The subsequent GetLastError result is compared with 0xB7 (ERROR_ALREADY_EXISTS), with a separate already-running branch.

**Conclusion:** each executable has its own named-mutex single-instance guard. The mutex names differ; neither process is simply relying on a shared lock.

## 3. Registered messages form an explicit shutdown protocol

The programs use RegisterWindowMessageW, so the numeric message IDs are assigned by Windows at runtime. The stable protocol identifiers are the registered strings, not hard-coded WM numbers.

### Agent registers two messages

At 0x006610F8 and 0x0066110A, Agent calls RegisterWindowMessageW with these UTF-16 strings:

1. {5964933A-7514-48F5-B980-FCB0CBFA97D1}_TERMINATE_EM_AGENT
2. {2EC42BF4-EA08-4476-AB86-466763F80E9A}_TERMINATE_EM_SERVICE

The resulting IDs are retained through the global message-ID slots referenced at 0x00677600 and 0x0067764C.

### Service registers the shared service-termination message

At 0x0047CE21, Service calls RegisterWindowMessageW with the UTF-16 string:

{2EC42BF4-EA08-4476-AB86-466763F80E9A}_TERMINATE_EM_SERVICE_

The Service literal has a **trailing underscore**. The Agent's second registered literal, at 0x0066110A, is:

{2EC42BF4-EA08-4476-AB86-466763F80E9A}_TERMINATE_EM_SERVICE

It has **no trailing underscore**. The two strings are not identical, so Windows assigns different registered-message IDs. The Service stores its own ID in form field +0x420.

### Agent message handler

The handler at 0x00661305 reads the incoming message identifier from the message structure at [edx+4], compares it against both registered IDs, and enters the shutdown path if either matches. The matching branch invokes the Agent's close/termination routines.

This proves Agent is prepared to react to both its own termination broadcast and Service termination broadcast.

### Service message handler and shutdown sequence

The Service window-message handler at 0x0047DF64 checks:

- its registered termination message stored at [form+0x420];
- message 0x11 (WM_QUERYENDSESSION);
- message 0x16 (WM_ENDSESSION).

The matching path enters 0x0047DF84. That routine:

1. Posts the registered Service-termination message to HWND_BROADCAST (0xFFFF) using PostMessageW at 0x0047DFD6, with wParam/lParam zero.
2. Calls GetCurrentProcess.
3. Calls TerminateProcess on the current process with exit code zero at 0x0047DFF5.

This establishes a shutdown broadcast from Service to all top-level windows before Service terminates itself. However, the exact Service string in this binary has a trailing underscore, while the Agent's corresponding string does not. Therefore the broadcast ID is **not the same** as the Agent's registered second ID in the exact binary pair analyzed here. Do not claim that this Service broadcast reaches the Agent's handler; a version mismatch, alternate listener, or separate shutdown path must be investigated.

### Agent shutdown broadcast

Agent also posts its own registered termination message to HWND_BROADCAST at 0x006602EB. The message ID is read from global 0x00677600, which is the slot populated by the Agent-termination registration. The routine then enters the Agent's own shutdown path.

## 4. Other confirmed coordination APIs

The byte-level callsite scan attributed the following calls in the current Agent build:

| API | Callsite count |
|---|---:|
| SendMessageW | 143 |
| PostMessageW | 26 |
| RegisterWindowMessageW | 13 |
| RegOpenKeyExW | 12 |
| CreateEventW | 9 |
| CreateFileW | 8 |
| SetEvent | 8 |
| WaitForSingleObject | 7 |
| RegQueryValueExW | 7 |
| GetCurrentProcessId | 7 |
| ResetEvent | 5 |
| GetWindowTextW | 5 |
| FindWindowW | 3 |
| EnumWindows | 3 |
| ShellExecuteW | 3 |
| CreateMutexW | 1 |

The selected Service imports have fewer callsites: CreateMutexW (1), FindWindowW (2), GetWindowTextW (1), RegisterWindowMessageW (1), PostMessageW (1), TerminateProcess (2), GetTempPathW (2), ShellExecuteW (1), and CreateFileW (1). It also calls GetCurrentThreadId/GetLastError through runtime wrappers.

These counts are static callsite counts for the selected imports, not runtime frequency.

## 5. Important correction: this Service binary is not proven to be an SCM service

For the exact Service hash above, the inspected import table does not contain OpenSCManagerW, OpenServiceW, StartServiceW, CreateServiceW, or WTS session-notification APIs. Instead, it creates a named mutex, registers a window message, handles WM_QUERYENDSESSION/WM_ENDSESSION, broadcasts a custom message, and terminates its own process.

The filename EmwatService.exe is not sufficient evidence that this PE is installed or managed by the Windows Service Control Manager. A separate installer wrapper or another binary version may provide SCM integration.

An earlier consolidated import report listed WTSRegisterSessionNotification for EmwatAgent. That API is absent from the exact Agent hash analyzed here. The current build's session-ending behavior is directly visible through the Service window-message handler; the older WTS finding remains version-unmatched and must not be applied to this build.

## 6. Native Linux design implications

The Windows implementation's observable contract suggests these Linux-side responsibilities:

1. Enforce one Agent instance and one Service instance independently.
2. Use an authenticated local IPC channel with explicit message types equivalent to TERMINATE_EM_AGENT and TERMINATE_EM_SERVICE.
3. On Service shutdown, notify Agent and wait for a bounded graceful-exit acknowledgement before terminating the Service process.
4. Handle Linux session shutdown/logoff signals explicitly; do not emulate Windows message IDs.
5. Keep lifecycle ownership and restart policy separate from the local HTTP document API.

A Unix-domain socket plus per-process lock files is a reasonable native design candidate, but the exact restart policy and process ownership still require tracing.

## 7. Remaining unknowns

- Exact names/semantics of the additional registered messages at Agent callsites outside the two termination GUIDs.
- The full meaning of the Agent's 143 SendMessageW callsites and event objects.
- The exact registered-message string mismatch: Service broadcasts `..._TERMINATE_EM_SERVICE_`, while Agent registers `..._TERMINATE_EM_SERVICE`.
- Which process launches the other, and whether either executable monitors/restarts its peer.
- Exact mutex-already-exists user-visible behavior.
- Whether a different installer package registers an SCM service or a different Agent build uses WTS.

## 9. Exact Agent ↔ Service heartbeat contract

The heartbeat URL is now connected to both the Agent request callsite and the Service response callsite in the exact binary hashes from Section 1.

### Agent request

In `EmwatAgent.exe`:
- The reliability-sentinel worker routine at `0x0066014A` constructs the URL `http://127.0.0.1:1984/?heartbeat` (string VA `0x0066048C`).
- The HTTP wrapper at `0x0065BB24` calls the request helper at `0x0065F7C0`; the inner method dispatch at `0x0065F8A8` passes the literal `GET` (VA `0x0065F93C`) to the HTTP client's virtual method at slot `+0xB8`.
- The returned response text is compared with the exact string `TickTack` (VA `0x006604DC`).
- A successful response clears the sequential-error state and reaches the `[Heartbeat] Cleared from error.` log path.

This confirms an HTTP GET request and an exact body token, not merely the presence of a URL string.

### Service response

In `EmwatService.exe`:
- The request handler checks the query-parameter collection for the key `heartbeat` (string VA `0x0047C9F0`).
- When present, it assigns `TickTack` (string VA `0x0047CA30`) to the response `ContentText` field at response-object offset `+0xBC`.
- It calls the Indy response writer at `0x004610FC`.

The Service binary also contains the startup error text: `Port binding failed. Make sure Emwat is not running and port 1984 is free.` This corroborates the local listener's port.

### Failure and recovery behavior in Agent

The bounded worker routine shows:
- A 1000 ms sleep in the polling loop before the next request cycle.
- A sequential failure counter compared with the worker object's field at offset `+0x4C` (the configured threshold source is not yet directly mapped to the registry value).
- On an even-numbered failure, it launches `taskkill.exe /f /im EmwatService.exe` and waits another 1000 ms. It then calls process/window cleanup helper `0x0062D088` and applies a further delay calculated as `2000 + 300 × failure_count` milliseconds.
- On reaching the maximum sequential-failure threshold, it logs `Max Sequential failure count reached. Terminate myself.`, broadcasts the Agent's own registered termination message to `HWND_BROADCAST`, and enters its termination path.
- Registry strings `LifeCheckInterval` and `MaxSequentialFailure` exist under the Agent configuration namespace, but their exact types/defaults and their mapping to worker fields remain to be confirmed.

The exact polling cadence is therefore not simply one second: the 1000 ms loop sleep is combined with failure-dependent backoff and the additional service-kill delay.

### Linux compatibility contract

The native service should implement a loopback-only health endpoint at `GET /?heartbeat` whose response body is exactly `TickTack`. It should be lightweight and independent of document-open, printer, scanner, or Word/LibreOffice work. The Linux supervisor should expose explicit health state and bounded restart behavior rather than copying `taskkill.exe` semantics. Do not silently change the response token or append JSON/newline content to it.

## 10. Registered-message version mismatch

The Agent and Service hashes in Section 1 do not register the same Service-termination string: Agent omits the final underscore; Service includes it. Although each side independently has a shutdown broadcast/handler path, this pair of binaries does not establish a matching cross-process registered-message handshake. Keep this discrepancy visible in compatibility tests and avoid treating the current Windows shutdown broadcast as a proven Agent notification.

## Evidence discipline

- Confirmed here: mutex names, initial-owner arguments, ERROR_ALREADY_EXISTS checks, registered message strings, message-ID comparisons, HWND_BROADCAST shutdown posts, and the Service's GetCurrentProcess/TerminateProcess sequence.
- Not claimed: complete Agent/Service state machine, runtime ordering under races, installer registration, or behavior on every Windows version.
- No customer documents, signatures, credentials, or runtime user data are included.


## 8. Additional heartbeat/configuration strings (same binary hashes)

A separate string/callsite pass on the exact Agent hash found:
- `http://127.0.0.1:1984/?heartbeat`
- `Heartbeat.Sentinel`
- `Max Sequential failure count reached. Terminate myself.`
- Registry namespace/value strings: `SOFTWARE\Emwat`, `Agent`, `LifeCheckInterval`, `LogFilePath`, `MaxSequentialFailure` and `MakeLog`.
- Embedded command strings: `taskkill.exe /f /im EmwatService.exe` and `taskkill.exe /f /im WINWORD.EXE`.

These add evidence for a health-check/configuration layer, but the URL string has not yet been tied to a complete HTTP client callsite and expected response. The exact registry hive/value types/defaults are not fully mapped; at least one registry-open callsite uses `HKEY_CURRENT_USER`. The taskkill strings have not yet been tied to the confirmed GUID broadcast shutdown path, so treat them as candidate fallback/legacy commands rather than confirmed normal shutdown behavior. The string `Heartbeat.Sentinel` is not yet mapped to a specific mutex/event callsite.

This section supplements, and does not replace, the exact mutex and registered-message shutdown sequence above.


## 11. Native Linux parity check (current branch)

The current Linux implementation already contains the captured heartbeat contract:

- `python/src/emwat_linux/bridge.py` handles `GET /?heartbeat` before the document dispatcher and returns HTTP 200 with exactly 8 body bytes: `TickTack`.
- The response content type is `text/html; charset=ISO-8859-1`, matching the tested compatibility response.
- `python/src/emwat_linux/application.py` configures the production bridge composition root to bind `127.0.0.1:1984` by default.
- `python/tests/test_bridge.py::test_legacy_agent_heartbeat_endpoint` asserts status, exact body, content length and content type.
- `test_document_post_waits_for_close_while_heartbeat_remains_responsive` deliberately blocks a document POST and verifies that the independent heartbeat GET still returns `TickTack`. This exercises the threaded HTTP-server design against the exact long-document/heartbeat concurrency concern.

The `Python bridge transport` workflow passed on commit `b54a414f37e91989b3fa7b615ce7bfc3b42d21cc` (run `45352644056`), including package installation/console-entrypoint verification and the bridge transport test step.

**Deployment boundary:** the GTK desktop shell intentionally does not create a production bridge supervisor by itself. A deployment must inject a configured supervisor/server factory with the required Almas Origin allowlist and the still-unresolved Cancel response contract. Thus the heartbeat route is implemented and CI-tested, but automatic production desktop startup is not claimed.


## 12. Agent registry configuration read/write contract

The Agent binary contains separate read and write routines for its configuration under:

`HKCU\SOFTWARE\Emwat\Agent`

The reader opens `HKEY_CURRENT_USER` (predefined handle `0x80000001`), opens `SOFTWARE\Emwat`, then the `Agent` subkey, and processes these values:

| Value | Registry type/operation observed | Configuration object offset |
|---|---|---:|
| `LifeCheckInterval` | DWORD read/write | `+0x00` |
| `MakeLog` | one-byte Boolean read/write | `+0x04` |
| `LogFilePath` | Unicode string read/write | `+0x08` |
| `MaxSequentialFailure` | DWORD read/write | `+0x10` |

The reader first checks whether each value exists. If it does, it reads the registry value; if it does not, it retains the value already present in the configuration object. Therefore the defaults are initialized elsewhere and are **not** recoverable from this registry routine alone. The writer stores the same four fields back to the same subkey.

The heartbeat worker compares its sequential failure counter against an object field at offset `+0x4C`. `MaxSequentialFailure` is the strongest candidate for the source of that threshold, but the copy/constructor path from the registry configuration object to the worker field has not yet been traced. Likewise, the traced worker's 1000 ms sleep is a literal constant; do not assume it is the value of `LifeCheckInterval` until the field-use path is proven.

### Linux configuration model

Preserve these as four separate settings:
- `life_check_interval` (integer; units/default still to be verified);
- `make_log` (Boolean);
- `log_file_path` (path/string);
- `max_sequential_failure` (integer).

Do not invent defaults. Use a native per-user configuration store, and keep the exact Windows registry names only in an import/migration adapter.


## 13. Agent Management form defaults and watchdog bounds (resource DFM)

The `EmwatAgent.exe` resource tree contains a Delphi form resource named `TMANAGEFORM` (resource data begins with `TPF0`). The decoded form is titled `Emwat Agent Management` and has `FormCreate` and `FormCloseQuery` handlers.

The DFM exposes the settings corresponding to the registry values:

| UI control | Label | Min | Max | DFM default |
|---|---|---:|---:|---:|
| `seInterval` | `Verify Interval (s):` | 1 | 3600 | 1 |
| `seSeqFailCount` | `Sequential failures to stop:` | 5 | 15 | 5 |
| `chkMakeLog` | `Write Events Log to file:` | — | — | no `Checked=true` property present |
| `edtFileName` | read-only path field | — | — | no literal Text property in DFM |

This gives a strong default/range mapping:
- `LifeCheckInterval`: seconds, UI range 1–3600, default 1 second.
- `MaxSequentialFailure`: UI range 5–15, default 5 consecutive failures.
- `MakeLog`: Boolean checkbox; DFM does not set it checked, so the form's component default is unchecked unless `FormCreate` changes it.
- `LogFilePath`: editable through the browse button but displayed in a read-only edit control; its runtime default still needs to be traced (the binary contains the filename `AgentLog.log`, but the assignment path is not yet proven).

The heartbeat worker's field at `+0x40` is used as the interval threshold: after 1000 ms sleeps it increments a counter until the field threshold is reached, then sends the heartbeat request. The exact `TManageForm.btnOkClick` update path copies `LifeCheckInterval` to worker `+0x40`, `LogFilePath` to `+0x44`, `MakeLog` to `+0x48`, and `MaxSequentialFailure` to `+0x4C`. The worker is temporarily suspended during this copy and its previous suspended/running state is restored afterward.

**Important:** the DFM proves the UI defaults and allowed ranges, not that every headless startup path uses those same defaults. The form-to-worker copy path is now resolved in Section 14; the remaining default question is the initializer that seeds the global config record before the registry reader runs.


## 14. Exact management-form → live watchdog update path

The DFM's event names map to a Delphi method table in the Agent PE. The recovered method addresses and behavior are:

| Method | VA | Behavior |
|---|---:|---|
| `FormCreate` | `0x00660E18` | Calls `0x00660E20` to populate controls from the global config record |
| `btnOkClick` | `0x00660D90` | Reads controls into the config record, writes registry, then updates the running worker if present |
| `btnStopAgentClick` | `0x00660DD8` | Sets the worker's termination state/waits for it, then posts the application quit path |
| `FormCloseQuery` | `0x00660E08` | Forces the `CanClose` output to false |
| `btnCancelClick` | `0x00660D88` | Closes the management dialog without the settings-save path |

### Save and live-update sequence

1. `btnOkClick` calls `0x00660E78`, which reads the four controls into the global config record at `0x00676DA8`.
2. It calls the registry writer `0x0062D944`, which stores the record under `HKCU\SOFTWARE\Emwat\Agent`.
3. If a worker object exists at global `0x00676E80`, it calls `0x006606E4` with the worker and config record.
4. `0x006606E4` copies the record fields to the worker object:

| Config record offset | Worker offset | Setting |
|---:|---:|---|
| `+0x00` | `+0x40` | `LifeCheckInterval` |
| `+0x08` | `+0x44` | `LogFilePath` |
| `+0x04` | `+0x48` | `MakeLog` |
| `+0x10` | `+0x4C` | `MaxSequentialFailure` |

5. Before writing those fields, `0x006606E4` records the worker's current suspended flag at `+0x0F` and calls `0x004BD7C8` to suspend it. After the field copies, it calls the same helper with the saved state, restoring whether the worker was previously suspended or running.

This proves that the UI can change the live watchdog interval, log path/toggle and maximum failure count without recreating the Agent process.

### Stop/close behavior

- `btnStopAgentClick` calls the worker stop helper `0x004BD8A0` when the worker exists, then calls the application shutdown helper at `0x005C1B00` and closes the dialog.
- `FormCloseQuery` calls its inherited/helper path and then explicitly writes zero to the `CanClose` output. The management form therefore vetoes ordinary close-query requests; use its explicit buttons/stop path rather than assuming the window close button terminates the Agent.

### Startup config load

The Agent startup routine at `0x006610B4` registers the two window messages, then calls `0x0062D6F8` with the global config record. This is the callsite that loads the registry values before the form/worker uses them. If the registry values are absent, the reader preserves the already initialized config-record fields. The exact initializer that seeds those fields before this call remains the last default-value question; the DFM separately proves the UI defaults/ranges listed in Section 13.


## 15. Word process termination in the Agent watchdog recovery path

The helper called from the even-failure branch, `0x0062D088`, is now decoded.

- It enumerates top-level windows using `FindWindowW`, `GetWindowTextW` and `GetWindow` (next-window traversal).
- It lowercases each window title and searches for the substring `GamElectronic EMWAT`.
- If that is absent, it searches for **both** substrings `efg` and `.doc` in the same title.
- When either title condition matches, it launches `taskkill.exe /f /im WINWORD.EXE`, waits 100 ms, and continues the window traversal.
- The helper is called by the heartbeat worker after the even-failure branch has attempted to terminate `EmwatService.exe`.

This is stronger than a generic "close stale Word window" interpretation: the launched command targets the **process image name** `WINWORD.EXE`, so it can terminate every Word process in the Windows session, not only the window that matched. The title check is the gate, but the command itself is process-wide.

### Migration safety consequence

Do **not** reproduce this as `pkill soffice`, `killall`, or a broad process-name kill on Linux. A native supervisor should identify the exact document/session it owns, request graceful close, preserve unsaved state, and only terminate that owned child process after a bounded failure policy. The original Windows behavior is a compatibility fact and a data-loss hazard, not a safe design requirement.
