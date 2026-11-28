# Reverse-engineering parallel follow-up — 2026-11-28 Run 43

## Three distinct completion/wait gates in the Word print path

The full Run-50 skipdata artifact `15253702066/procedure-004B7724.md` decodes all 4,960 bytes of `TWordViwer.LoadDocument`. It reveals a second wait loop separate from the THidePrintingThread file poll.

### WordViewer bounded state poll

Procedure: `TWordViwer.LoadDocument`, `0x004B7724–0x004B8A83`.

- Loop initialization: `0x004B7C07`, counter set to zero.
- Each iteration calls `0x00404F04` on the global object at `0x00630138`. The same helper is called after sleeps in other VCL UI procedures; this is strongly consistent with an application message-pump helper such as `TApplication.ProcessMessages`, but its exact identity is not proven.
- It obtains a state value from object `ESI` via `0x004010A8` and compares it to global sentinel `0x0062F850` at `0x004B7D57–0x004B7D64`.
- If the value still equals the sentinel and counter is below `0x64`, it calls `Sleep(5)` through `0x004028D0` at `0x004B7D78`, increments the counter, and repeats.
- The loop allows 101 iterations (counter 0 through 100; exit when it reaches 101), for a nominal maximum of about 505 ms of sleep, plus message-pump and state-check time.
- On state change or timeout it logs using the string at `0x004B8768` and continues through the caller's result handling.

The exact semantic meaning of the ESI object state and sentinel `0x0062F850` is open. Do not label this a printer-worker completion flag until the object constructor and `0x004010A8` method are mapped.

### Combined lifecycle (do not conflate gates)

1. **Spooler gate:** printer queue job disappearance.
2. **Worker artifact gate:** `THidePrintingThread.Execute` performs stale-output cleanup, its timed file poll and OS-version-specific ShellExecuteW fallback; it returns true only after the final FileExists check.
3. **WordViewer UI state gate:** `TWordViwer.LoadDocument` performs the bounded 5 ms message-pumped state poll described above.

The Worker Boolean is then checked by `SeparteImages` before continuing to the GDI+ TIFF stage. The WordViewer state poll is a separate later gate and has not yet been mapped to a named event or object state.

Evidence:
- Run-50 artifact `15253702066`: `procedure-004B7724.md`, `procedure-004A0E88.md`, `callers-00404F04.md`, `procedure-004028D0.md`.
- Run-50 artifact `15253702066`: `callers-004A0148.md`.

No production code or workflow source was modified.
