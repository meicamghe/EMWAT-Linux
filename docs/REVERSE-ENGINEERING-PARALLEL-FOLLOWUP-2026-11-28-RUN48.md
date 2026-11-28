# Reverse-engineering parallel follow-up — 2026-11-28 Run 48

## WordViewer poll target resolves to EFOpenError class reference

The Run-67 import map artifact `15260640277/printer-api/all-imports.md` resolves global address `0x0062F850` as:

`@System@Classes@EFOpenError@`

This changes the interpretation of the state comparison in `TWordViwer.LoadDocument`:

- At `0x004B7D57`, the code calls `0x004010A8` with ESI.
- At `0x004B7D5C`, it compares EAX with the global at `0x0062F850`.
- If equal and the loop counter is below 0x64, it calls the application-level message pump, sleeps 5 ms, increments the counter, and repeats.
- The maximum is 101 iterations, approximately 505 ms of sleep plus message-pump/check time.

Therefore 0x0062F850 is not an arbitrary completion sentinel. It is an imported class reference for EFOpenError. The loop is polling a state/class value associated with an object in ESI while it equals that exception class.

The exact meaning of 0x004010A8 and the identity/construction of ESI are still unresolved. It is premature to call this a printer-worker completion flag or to assign a specific exception-recovery semantic. A direct trace of 0x004010A8 plus its callers and the ESI construction path is the next exact target.

This refines Run 43; the wait duration and message-pump behavior remain valid, but the compared value is now identified.

Evidence: Run-67 artifact `15260640277/printer-api/all-imports.md`; Run-50 artifact `15253702066/procedure-004B7724.md`.

No code or workflow source was modified.
