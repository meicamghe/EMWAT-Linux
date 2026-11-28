# Reverse-engineering parallel follow-up — 2026-11-28 Run 34

## THidePrintingThread result is a hard precondition for GDI+ TIFF continuation

The hidden-worker artifact includes callers-004A0E88.md. It finds one direct callsite:
- TCreateTiff.SeparteImages at 0x004A02B8 calls THidePrintingThread.Execute.

The caller immediately tests AL,AL. A false return branches to the failure path at 0x004A02C1; only a true return reaches the continuation at 0x004A02D7. Therefore the worker's Boolean result is a hard gate before the GDI+ TIFF continuation.

Combined print-to-TIFF lifecycle:
1. The printer queue path waits for the spooler job to disappear.
2. THidePrintingThread performs stale-output cleanup, timed file polling, and the OS-version-specific ShellExecuteW fallback.
3. The worker returns true only after the final FileExists check succeeds.
4. SeparteImages rejects the operation when AL is false and continues into the GDI+ Save/SaveAdd path only on true.

This distinguishes queue completion from artifact completion: a vanished spooler job does not prove that the TIFF file exists or that the worker accepted it.

Evidence: hidden worker artifact 15253702066, callers-004A0E88.md; procedure-004A0148.md; printer import/queue artifact 15254533525; GDI+ slot crosswalk.

No tests or CI were run; no package was built.
