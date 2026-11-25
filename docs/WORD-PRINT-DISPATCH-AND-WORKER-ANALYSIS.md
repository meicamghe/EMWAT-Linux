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

The follow-up wrapper trace resolves the member and overload:

- TD32 identifies `0x004361B0` as `TWordDocument.PrintOut` with seventeen `OleVariant` parameters.
- Its body prepares the Variant arguments, obtains the document interface, and calls `[vtable + 0x3F0]` at `0x00436234`.
- The wrapper ends with `ret 0x3c`, consistent with fifteen stack-passed arguments plus two register-passed arguments in the Delphi register calling convention; total = seventeen.
- The adjacent overloads provide a useful cross-check: `0x00436030` is the 15-Variant overload (`ret 0x34`), and `0x004360F0` is the 16-Variant overload (`ret 0x38`). All three dispatch through the same `+0x3F0` slot.
- The caller setup in `BGPrintWithGamPrintOptions` at `0x004C6F90–0x004C70B6` prepares and pushes eighteen distinct local Variant-record addresses, then pushes the document interface pointer separately. The eighteen locals comprise fifteen records initialized in this block through `0x00403550` and three earlier Variant records at `[ebp-0x58]`, `[ebp-0x88]`, and `[ebp-0x78]` that were prepared earlier in the procedure. This does **not** match the 17-Variant wrapper's 15 stack + 2 register parameter shape on a simple count. The exact dispatch ABI/hidden-argument interpretation is unresolved; the prior statement that the caller matched the 17-Variant wrapper is withdrawn.

**Conclusion:** the call at `0x004C70B6` is `TWordDocument.PrintOut` using the 17-argument Variant overload. The subsequent call at `0x004C70CA` remains a separate `TWordApplication.PrintOutOld` invocation through its own wrapper/interface slot.

The semantic names and concrete values/types of the seventeen arguments have **not** yet been proven from the caller's local Variant records or the exact WordXP type-library metadata. A previously considered 15-parameter standard Word signature is not a safe mapping for this 17-argument overload and is withdrawn here. Do not assign argument names based only on a generic Word documentation signature.

## 7. Correction from the expanded TD32 symbol/caller pass (2026-11-25)

The expanded trace resolved a prior ambiguity: `0x004677B8` is `TETracer.LogException`, and `0x00467788` is `TETracer.LogDebugF`. `TEmwatDocPrintHandler.Execute` calls `LogException` in its exception path. Therefore, the earlier interpretation of `0x004677B8` as a callback dispatcher is withdrawn. The constructor's method-record-shaped storage at `+0x18/+0x1C` and controller notification record still warrant investigation, but they must not be attributed to that logging helper. The new direct-caller scan found no direct CALL xrefs to `TEDPController.SetPrintThread`; this does not rule out VMT/indirect calls.

## 8. Caller-arity discrepancy discovered in the expanded trace (2026-11-25)

- The generated wrapper TWordDocument.PrintOut at 0x004361B0 remains independently proven to accept 17 OleVariant parameters: it receives two through Delphi register arguments (EDX/ECX) and fifteen from stack slots [ebp+8] through [ebp+0x40], then dispatches through slot +0x3F0.
- The BGPrintWithGamPrintOptions callsite, however, emits eighteen local Variant-record addresses in this order: -0x2cc, -0x2dc, -0x2ec, -0x2fc, -0x30c, -0x31c, -0x32c, -0x33c, -0x34c, -0x88, -0x58, -0x35c, -0x36c, -0x37c, -0x38c, -0x78, -0x39c, -0x3ac (frame offsets relative to EBP). It then separately pushes the document interface pointer at 0x004C70B3 before the indirect slot call.
- The first fifteen listed records are initialized immediately before their addresses are pushed using helper 0x00403550. The three pre-existing records are prepared earlier: -0x58 via 0x004034E8 from an application/document property path, -0x88 via Variant initialization and copy helper 0x00403520, and -0x78 via 0x004034E8 with an integer-like value. Their exact VARTYPEs and semantic values still require helper and source-property tracing.
- Do not report the 17-parameter wrapper as the proven signature of this specific caller until the eighteen-address discrepancy is resolved. The next workflow pass traces the Variant helpers and interface-construction helper 0x0042ABA0; the COM call convention and any hidden/result argument must be established from that evidence, not guessed.

