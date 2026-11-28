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
2. Resolve `0x004026B4` (stale-output delete helper) and recover the launch/argument string literals referenced by the ShellExecuteW fallback.
3. Identify which exact-hash GAM component creates the awaited file and correlate its close/flush with `LcmEndDocPort` / `Render_SendPage`.
4. Keep file existence, spool queue disappearance, printer sentinel `JobFinishes.GAM`, and Agent heartbeat as four separate signals until a direct producer-consumer chain proves otherwise.

## OS-version-specific launch fallback — cross-artifact resolution

The previously unresolved `0x00404494` call is not a printer-status API. The printer helper artifact maps it to a six-argument thunk that jumps through IAT `0x0062F9CC` to `shell32.dll!ShellExecuteW`. The same artifact maps `0x00402818` to `GetVersionExW`.

At `0x004A1236`, the worker initializes the first DWORD of a 276-byte structure (`0x114`) and passes it to the `GetVersionEx` thunk. The byte size matches `OSVERSIONINFOW` (276 bytes), not the extended `OSVERSIONINFOEXW` layout (284 bytes); the TD32 decorated helper name carries an `OSVERSIONINFOEXW` suffix, so the symbol/type label and actual caller allocation disagree. Treat the runtime buffer as the basic `OSVERSIONINFOW` layout unless raw type metadata proves otherwise. The subsequent comparison at `0x004A1258` reads the `dwMajorVersion` field at structure offset `+0x04` and branches on whether it is greater than 5. The two OS-version branches use different operation-string pointers (`0x004A18B0` versus `0x004A18FC`) for their `ShellExecuteW` calls. Each branch contains up to three staged ShellExecuteW operations. The second stage is reached only if the first return is greater than 32; the third is reached only if the second return is greater than 32. The observed delays between later stages are 3,000 ms and 50 ms. Every returned HINSTANCE is compared with 32, matching the documented ShellExecute success threshold.

This narrows the fallback behavior but does not identify the executable/file/parameters because the strings at `0x004A1864`, `0x004A1894`, `0x004A18B0`, `0x004A18BC`, `0x004A18D8`, `0x004A18E0`, and `0x004A18FC` have not been recovered from raw data. Crucially, successful `ShellExecuteW` return alone does not set the worker's success byte. The success byte is set at `0x004A1370` only after the final `FileExists` check at `0x004A121B` succeeds.

**Correct completion contract:** stale-output deletion → timed file polling → optional OS-version-specific ShellExecuteW fallback → final file-existence predicate → worker success byte. Keep this separate from Word's `EnumJobsW` queue-disappearance loop and the `JobFinishes.GAM` sentinel.


## Caller-side success gate

The direct caller scan contains exactly one direct callsite for THidePrintingThread.Execute: TCreateTiff.SeparteImages at 0x004A02B8. The caller immediately executes test AL,AL and branches to its failure path at 0x004A02C1 when the worker returns false; only a true return reaches the continuation at 0x004A02D7. The false branch routes the message string at 0x004A09C0 through the existing application error/logging helper; its literal is still part of the raw-string extraction target. This confirms that the worker's Boolean result is a hard precondition for the GDI+ TIFF continuation, not a detached background status signal.

The combined print-to-TIFF acceptance chain has two separate gates: the earlier spooler path waits for the print queue job to disappear; THidePrintingThread then waits for the generated output file and returns true only after the final FileExists predicate. Queue disappearance alone is not sufficient to accept the TIFF output.


## Exact SeparteImages diagnostic strings recovered from inline constants

The Run-50 `inline-constants.md` artifact contains the UTF-16LE literals referenced by the caller:

| VA | Exact text | Use established by caller flow |
|---|---|---|
| `0x004A08F4` | `Gam Printer is in "Paused" state! please check.` | Printer-paused error shown before TIFF conversion proceeds |
| `0x004A0960` | `Error on setting gam printer parameters.` | Configuration failure path |
| `0x004A09C0` | `Error occured during Convert Word Document to Tiff.` | Failure when `THidePrintingThread.Execute` returns false |

The misspelling `occured` is present in the original binary string and is quoted exactly. These are diagnostic strings only; they do not identify the hidden output path or the producer process. The Run-50 artifact also contains a Persian printer-paused message at `0x004A07F4`, but the extracted byte window ends before the full string boundary, so its complete text is intentionally not reconstructed here.
