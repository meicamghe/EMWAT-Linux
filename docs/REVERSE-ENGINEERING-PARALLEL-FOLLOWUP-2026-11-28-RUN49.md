# Reverse-engineering parallel follow-up — 2026-11-28 Run 49

## Resolve helper 0x004010A8 and the WordViewer wait state

Cross-correlated the Run-50 WordViewer trace with Run-67 GearImgProc procedures in artifact `15260427307`.

### Helper identity

`0x004010A8` is a high-confidence TObject.ClassType/VMT accessor:

- In `TGearImgProc.SaveCPinMultiPageFile` at `0x004EF40C`, the code calls it on object `[EBX+0x28]` and compares the returned pointer with ESI, which is the class/VMT pointer passed to the routine.
- In the GearImgProc constructor, it calls the same helper on two object instances and compares the returned class pointers before choosing the image-processing path.
- This is consistent with Delphi TObject.ClassType semantics: object pointer in EAX, class/VMT pointer returned in EAX.

### WordViewer wait-loop interpretation

At `0x004B7D57`, the WordViewer loop calls `0x004010A8` with ESI and compares the returned ClassType pointer to global `0x0062F850`, which the import map resolves to `@System@Classes@EFOpenError@`.

Thus the loop repeats while:

`ESI.ClassType == EFOpenError`

Each iteration pumps the application message queue through `0x00404F04`, sleeps 5 ms through `0x004028D0`, and increments the counter. It allows 101 iterations (nominal ~505 ms sleep plus processing).

This is not a generic completion sentinel and not the THidePrintingThread file-existence gate. It is a bounded wait for the object referenced by ESI to stop being of class EFOpenError. The exact object constructor/owner and the operation that replaces or changes this object remain open. Do not infer the object's semantic name until its creation and mutation callsites are traced.

Evidence:
- Run-50 artifact `15253702066/procedure-004B7724.md`.
- Run-67 artifact `15260427307/image-ui/procedure-004EF40C.md`, `image-ui/callers-004EF40C.md`, `image-ui/callers-004ECF30.md`, and `image-io/imports.md`.

No production code or workflow source was modified.
