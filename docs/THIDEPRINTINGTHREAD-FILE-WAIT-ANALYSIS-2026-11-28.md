# THidePrintingThread file-wait analysis — 2026-11-28

## Primary result

`THidePrintingThread.Execute` (`0x004A0E88–0x004A1A9F`) does not merely sleep for a fixed interval or wait only for the printer queue to empty. Its core completion gate polls file existence.

Evidence: Run-50 artifact `15253702066`, procedure `0x004A0E88`.

## File-existence predicate

At `0x004A1029`, `0x004A11E1`, and `0x004A121B`, the worker calls helper `0x004032C0` with a UnicodeString filename in EAX and `DL=1`. This matches Delphi `System.SysUtils.FileExists(const FileName: string; FollowLink: Boolean = True)` exactly. The official signature documents the second Boolean as `FollowLink`; see [System.SysUtils.FileExists](https://docwiki.embarcadero.com/Libraries/Alexandria/en/System.SysUtils.FileExists).

Observed flow:

1. **Stale-output preflight:** the path assembled at `0x004A0FFF–0x004A101C` is tested with `FileExists(..., True)`. If it already exists, the worker converts the string to a native filename pointer and calls the delete helper at `0x004026B4` before starting the wait. The exact delete API identity remains to be checked.
2. **Timed poll:** a second constructed path is tested at `0x004A11E1`. If absent, the worker sleeps 10 ms (`Sleep(10)` at `0x004A11B7`) and repeats while the computed time threshold has not elapsed.
3. **Completion gate:** a further constructed path is tested at `0x004A121B`. If it exists, control branches to `0x004A1370`, sets the worker's success byte, and proceeds to the successful return path.
4. **Failure/retry path:** if the expected file is still absent, the worker performs additional printer/status/configuration checks, with 3,000 ms and 50 ms delays in the retry path, before returning failure or retrying according to the branch state.

## What this proves — and what it does not

- The worker's Boolean is tied to appearance of one or more generated filesystem artifacts, not merely to queue disappearance.
- The initial preflight removes an existing/stale file before waiting, preventing an old artifact from satisfying the next conversion attempt.
- The 10 ms polling cadence and a computed deadline are explicit in the machine code.
- The exact path strings referenced from `0x004A1784` and the related string/data addresses are not yet decoded. Therefore the file's extension, producer process, and exact hand-off to `TCreateTiff.SeparteImages` are not yet named.
- The fallback launch path is now cross-mapped: `0x00402818` is `GetVersionExW`, the 276-byte structure at `0x004A1236` is `OSVERSIONINFOW`-sized (the decorated helper symbol says `OSVERSIONINFOEXW`, which conflicts with the caller's size), and `0x00404494` is `shell32!ShellExecuteW` (IAT `0x0062F9CC`). The exact launch target/argument strings remain undecoded.

## Next proof gates

1. Recover the literal path fragments at `0x004A1784` and the two subsequent path-construction sites.
2. Resolve `0x004026B4` (delete helper) and `0x00404494` (status/query helper) from their import/symbol targets.
3. Identify which exact-hash GAM component creates the awaited file and correlate its close/flush with `LcmEndDocPort` / `Render_SendPage`.
4. Keep file existence, spool queue disappearance, printer sentinel `JobFinishes.GAM`, and Agent heartbeat as four separate signals until a direct producer-consumer chain proves otherwise.

## OS-version-specific launch fallback — cross-artifact resolution

The previously unresolved `0x00404494` call is not a printer-status API. The printer helper artifact maps it to a six-argument thunk that jumps through IAT `0x0062F9CC` to `shell32.dll!ShellExecuteW`. The same artifact maps `0x00402818` to `GetVersionExW`.

At `0x004A1236`, the worker initializes the first DWORD of a 276-byte structure (`0x114`) and passes it to the `GetVersionEx` thunk. The byte size matches `OSVERSIONINFOW` (276 bytes), not the extended `OSVERSIONINFOEXW` layout (284 bytes); the TD32 decorated helper name carries an `OSVERSIONINFOEXW` suffix, so the symbol/type label and actual caller allocation disagree. Treat the runtime buffer as the basic `OSVERSIONINFOW` layout unless raw type metadata proves otherwise. The subsequent comparison at `0x004A1258` reads the `dwMajorVersion` field at structure offset `+0x04` and branches on whether it is greater than 5. The two OS-version branches use different operation-string pointers (`0x004A18B0` versus `0x004A18FC`) for their `ShellExecuteW` calls. Each branch can make up to three launch/open attempts; the observed inter-attempt delays include 3,000 ms and 50 ms. Every returned `HINSTANCE` is compared with `32`, matching the documented ShellExecute success threshold.

This narrows the fallback behavior but does not identify the executable/file/parameters because the strings at `0x004A1864`, `0x004A1894`, `0x004A18B0`, `0x004A18BC`, `0x004A18D8`, `0x004A18E0`, and `0x004A18FC` have not been recovered from raw data. Crucially, successful `ShellExecuteW` return alone does not set the worker's success byte. The success byte is set at `0x004A1370` only after the final `FileExists` check at `0x004A121B` succeeds.

**Correct completion contract:** stale-output deletion → timed file polling → optional OS-version-specific ShellExecuteW fallback → final file-existence predicate → worker success byte. Keep this separate from Word's `EnumJobsW` queue-disappearance loop and the `JobFinishes.GAM` sentinel.
