# EMWAT Word print dispatch and worker ownership — follow-up

Date: 2026-11-25  
Input: GitHub Actions artifacts from printer-pipeline run `45345628400` and print-handler/controller run `45347505938`, both successful.  
Scope: static TD32/disassembly evidence from the repository's `analysis-input/EmwatMethods.bpl1`. No Windows runtime print was performed.

## 1. Explicit GAM print call order

The `BGPrintWithGamPrintOptions` procedure (`0x004C5FF8`) provides a concrete sequence:

1. It obtains the active document's printer-name value and calls `Emwatutils.getPrinterNumJobs` (`0x00456258`). That helper calls `OpenPrinterW`; a zero result enters the early error/exit path. The helper's name is misleading: the inspected body does not itself enumerate jobs or calculate a count.
2. It prepares fifteen OleVariant argument records on its stack.
3. At `0x004C70B6`, it invokes the document interface through vtable slot `+0x3F0`.
4. At `0x004C70CA`, it then calls the generated `TWordApplication.PrintOutOld` wrapper (`0x00441E44`), which dispatches through the application interface slot `+0x1E4`.
5. After the application-level call, the routine continues with document-interface calls and its own completion/exception handling.

The order is important: the `+0x3F0` document-interface dispatch and the application `PrintOutOld` call are two distinct COM calls in the same routine. Do not collapse them into one call or assume that one is merely the wrapper for the other.

### Known wrapper slots for comparison

- `TWordDocument.PrintOutOld` wrapper at `0x004309F8` dispatches through document slot `+0x2BC`.
- `TWordDocument.PrintOut2000` wrapper at `0x004345FC` dispatches through document slot `+0x394`.
- `TWordApplication.PrintOutOld` wrapper at `0x00441E44` dispatches through application slot `+0x1E4`.

The current artifact does not identify the exact generated wrapper/typelib member corresponding to document slot `+0x3F0`. Its fifteen arguments are confirmed as OleVariant records at the callsite, but their semantic mapping and the reason for the subsequent application-level call remain unresolved. Do not assign names to the fifteen arguments from their count alone.

## 2. Timer-driven print is a separate call path

The `OnControlerNotify` callback (`0x004BB3B0`) calls `CostumizeRecAndCC` (`0x004D281C`) before the archive extraction path. The bounded `CostumizeRecAndCC` trace contains a normal document `PrintOutOld` dispatch through slot `+0x2BC`, with exception fallback attempts. This is distinct from the explicit `BGPrintWithGamPrintOptions` sequence above.

The wrapper at `0x004309F8` confirms that document slot `+0x2BC` is the `TWordDocument.PrintOutOld` wrapper's dispatch target. The retry structure must not be represented as three unconditional print jobs.

## 3. Print-handler execution and callback storage

The `TEmwatDocPrintHandler.Execute` method at `0x004A5EA8` is a small dispatcher, not a spooler API caller:

- In its exception-handling path, it passes the value at handler offset `+0x40`, a local string/argument record, and a local argument pointer to `0x004677B8`.
- The new TD32 symbol index identifies `0x004677B8` as `TETracer.LogException`; it calls `0x00467788`, identified as `TETracer.LogDebugF`. These are logging routines, not a worker dispatcher.
- No direct spooler submission API appears in this method's decoded body.

The constructor at `0x004A5C10` stores an interface reference at object offset `+0x44`, initializes helper/state objects at offsets `+0x48` and `+0xC8` through `+0xD8`, and writes the Execute code address `0x004A5EA8` plus the instance pointer into a method-record-shaped object at offsets `+0x18` and `+0x1C`. The method-record-shaped value is consistent with Delphi callback storage, but this evidence does not establish that `Execute` invokes it through `0x004677B8`. The actual helper is an exception logger. The complete owner/worker relation remains unresolved.

The `DoOnTerminate` method (`0x004A5D78`) releases the five helper/state references, releases and clears the `+0x48` reference, finalizes and clears the `+0x40` callback field, then releases the interface at `+0x44`. This gives a concrete cleanup order and confirms that the callback field has a managed lifetime.

`TEDPController.SetPrintThread` (`0x004D2F44`) stores the two supplied pointer-sized values at controller offsets `+0x10` and `+0x14`. `TEDPController.Notify` (`0x004D2EC8`) checks and dispatches its stored notification method record. These are method-record storage/dispatch operations; the precise relationship between this controller callback and the print worker's `+0x40` field still needs a caller/ownership trace.

## 4. What this changes in the Linux design

Keep these operations separate in the native design:

- print-option preparation and recipient/CC field preparation;
- document-level PrintOut request with its own argument contract;
- application-level PrintOutOld request;
- timer-driven PrintOutOld preparation/retry path;
- worker/callback lifecycle and completion notification;
- spool queue job discovery/correlation;
- GAM output artifact publication and EMWAT retrieval.

Do not equate worker completion with GAM artifact availability. The current static evidence still does not prove which job produces the TIFF, how its final path is chosen, or how EMWAT consumes it.

## 5. Next targeted investigations

1. Resolve document vtable slot `+0x3F0` against the exact Word type-library wrapper metadata; recover all fifteen argument names/types and their values at `0x004C70B6`.
2. Trace helper `0x004677B8` and the constructor's thread creation/start path to identify the exact callback owner and worker object.
3. Trace all indirect/VMT callers of `TEDPController.SetPrintThread` and `SetOnNotify`; correlate controller offsets `+0x10/+0x14` with the notification record read by `Notify`. The direct-caller scan for `SetPrintThread` returned no direct CALL xrefs, so indirect dispatch remains open.
4. Find the higher-level indirect caller of `ExtractFileNameEX` and correlate its document label with the queue/job ID and the GAM output artifact.
5. Only after a controlled Windows print capture, determine whether the explicit and timer-driven paths create separate jobs, share a job, or are intercepted/coalesced.

## Evidence and limits

- Printer-pipeline artifact: run `45345628400`, artifact `14897534290`.
- Print-handler/controller artifact: run `45347505938`, artifact `14898272788`.
- The workflows completed successfully as static-analysis jobs. Their success is not a runtime print test.
- No source binary, Wine prefix, printer configuration, or system configuration was modified by this analysis.


## 6. Exact identification of document vtable slot `+0x3F0` (2026-11-25)

The follow-up wrapper trace resolves the previously open member:

- TD32 identifies `0x00436030` as `TWordDocument.PrintOut` with fifteen `OleVariant` parameters.
- Its body prepares the Variant arguments, obtains the document interface, and calls `[vtable + 0x3F0]` at `0x004360B4`.
- The wrapper ends with `ret 0x34`, consistent with thirteen stack-passed arguments plus two register-passed arguments in the Delphi register calling convention; total = fifteen.
- The `BGPrintWithGamPrintOptions` callsite at `0x004C70B6` invokes the same vtable slot after preparing fifteen Variant argument records. This matches the wrapper's member and argument count exactly.

**Conclusion:** the call at `0x004C70B6` is `TWordDocument.PrintOut` (15-argument overload), not an unknown document-interface operation. The subsequent call at `0x004C70CA` remains a separate `TWordApplication.PrintOutOld` invocation through its own wrapper/interface slot.

The standard Word `Document.PrintOut` parameter order for this 15-argument overload is:

1. `Background`
2. `Append`
3. `Range`
4. `OutputFileName`
5. `From`
6. `To`
7. `Item`
8. `Copies`
9. `Pages`
10. `PageType`
11. `PrintToFile`
12. `Collate`
13. `FileName`
14. `ActivePrinterMacGX`
15. `ManualDuplexPrint`

The member identity and argument count are established by the wrapper/callsite match. The concrete value and VARIANT type of each argument at runtime still need to be mapped from the caller's local Variant records. Do not infer the values from the form's visible controls alone.

## 7. Correction from the expanded TD32 symbol/caller pass (2026-11-25)

The expanded trace resolved a prior ambiguity: `0x004677B8` is `TETracer.LogException`, and `0x00467788` is `TETracer.LogDebugF`. `TEmwatDocPrintHandler.Execute` calls `LogException` in its exception path. Therefore, the earlier interpretation of `0x004677B8` as a callback dispatcher is withdrawn. The constructor's method-record-shaped storage at `+0x18/+0x1C` and controller notification record still warrant investigation, but they must not be attributed to that logging helper. The new direct-caller scan found no direct CALL xrefs to `TEDPController.SetPrintThread`; this does not rule out VMT/indirect calls.
