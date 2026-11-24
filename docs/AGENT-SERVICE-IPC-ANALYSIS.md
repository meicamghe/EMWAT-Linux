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

At 0x0047CE21, Service calls RegisterWindowMessageW with:

{2EC42BF4-EA08-4476-AB86-466763F80E9A}_TERMINATE_EM_SERVICE

It stores the returned message ID in its form field at offset +0x420. This is the same string Agent registers as its second termination message.

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

This establishes a shutdown broadcast from Service to all top-level windows before Service terminates itself. Because Agent registers the same Service-termination message, Agent can receive that broadcast and close.

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
- Which process launches the other, and whether either executable monitors/restarts its peer.
- Exact mutex-already-exists user-visible behavior.
- Whether a different installer package registers an SCM service or a different Agent build uses WTS.

## Evidence discipline

- Confirmed here: mutex names, initial-owner arguments, ERROR_ALREADY_EXISTS checks, registered message strings, message-ID comparisons, HWND_BROADCAST shutdown posts, and the Service's GetCurrentProcess/TerminateProcess sequence.
- Not claimed: complete Agent/Service state machine, runtime ordering under races, installer registration, or behavior on every Windows version.
- No customer documents, signatures, credentials, or runtime user data are included.
