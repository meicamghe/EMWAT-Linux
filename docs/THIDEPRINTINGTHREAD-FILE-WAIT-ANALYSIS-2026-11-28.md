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
- The additional printer/status helper at `0x00404494` and the 276-byte status buffer around `0x004A1236` still need their exact API/structure mapping.

## Next proof gates

1. Recover the literal path fragments at `0x004A1784` and the two subsequent path-construction sites.
2. Resolve `0x004026B4` (delete helper) and `0x00404494` (status/query helper) from their import/symbol targets.
3. Identify which exact-hash GAM component creates the awaited file and correlate its close/flush with `LcmEndDocPort` / `Render_SendPage`.
4. Keep file existence, spool queue disappearance, printer sentinel `JobFinishes.GAM`, and Agent heartbeat as four separate signals until a direct producer-consumer chain proves otherwise.