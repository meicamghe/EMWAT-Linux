## 2026-11-28 — Run 48 WordViewer poll comparison target

- Run-67 import map identifies global 0x0062F850 as imported class reference @System@Classes@EFOpenError@.
- The WordViewer loop at 0x004B7D57 compares 0x004010A8(ESI) against this EFOpenError class pointer; it repeats while equal, with message pumping and 5 ms sleeps, up to 101 iterations.
- This is not a generic completion sentinel. Exact 0x004010A8 semantics and ESI object ownership remain open; do not label it a print-worker completion condition.
- Worker analysis commit f5deca4; Run 48 report 6949eca.

## 2026-11-28 — Run 47 GTK startup wiring plan

- Exact loopback values are evidence-backed: bind 127.0.0.1:1984; allowed XHR Origin http://127.0.0.1:1984; allowed parent Referer origin http://127.0.0.1:1984; numeric invoke nonce.
- Added docs/ALMAS-GTK-STARTUP-WIRING-PLAN.md with the exact factory composition: LibreOfficeAdapter -> EditWordDocumentService -> create_editword_handler -> XMLMethodDispatcher -> BridgeHTTPServer -> BridgeSupervisor -> GTK injection.
- Explicit DISCARDED gets a fail-closed local 409 policy only; this is not claimed to match Windows. Writer Don't Save is a successful return of last confirmed state; Writer Cancel keeps the request pending.
- Normal GTK entry point still does not inject/start BridgeSupervisor. The wiring plan is documented but not implemented.
- Startup plan commit cda1173; acceptance update commit 825618c.

## 2026-11-28 — Run 67 automatic workflow outcome

- Run 67 was automatically triggered by the push that changed Python code; it was not manually dispatched.
- Jobs `word-print-com` and `image-ui-and-vmt` completed successfully.
- In `native-regression`, the native build/regression step completed successfully, but the Python bridge regression step ended cancelled. The full Python suite therefore has no pass/fail result.
- Run ID `46136978712`, conclusion `cancelled`, updated `2026-11-28T11:15:17Z`. No local clone/test run succeeded because GitHub DNS was unavailable in the container.
- No additional workflow was dispatched. Do not report the Python suite as passed.

## 2026-11-28 — Run 46 authoritative handler/VMT and wire closure

- Correction to Run 40: the Run-67 generic VMT resolver's no-candidate result was a false negative. The direct VMT/interface crosswalk already establishes TEditWordDocument VMT 0x005ED764, parent TEmwatMethod, slot +0x10 -> 0x005EE82C. TScanDocument VMT 0x005ED884 slot +0x10 -> 0x005EEB48.
- The service constructs TEditWordDocument from XML class EditWordDocument via GetClass("T"+className), invokes TEmwatMethod VMT +0x0C wrapper 0x0046C9E0, then the concrete method through +0x10. Actual handler identity is now closed; TD32 procedure labels remain stale.
- Successful wire response is established by PCAP: HTTP 200, Content-Type text/html; charset=ISO-8859-1, response-word/status=success, return-types/type application/msword/base64, decoded legacy DOC/CFB. Native BPL writes ContentText, calls Indy WriteContent, then sets bResultSet.
- Request Origin and Referer evidence are loopback-local: http://127.0.0.1:1984. The captured deployment can use this explicit Origin allowlist while remaining bound to 127.0.0.1. Do not guess external Almas domain for XHR CORS.
- PCAP response still has 68 missing TCP payload bytes, so full response bytes/hash remain unverified. Live Almas persistence through LibreOffice remains the release gate.
- Updated acceptance doc commit 9aff17e; Run 40 correction commit 1cb571b; Run 46 report commit e3b3eb7.

## 2026-11-28 — Run 45 WordViewer ABI/output handoff

- Recovered loader call ABI at 0x005EE961: EAX=wordConfig, EDX=wordBody, ECX=letterImages; stack args are output-string pointer at [EBP+8], handler state [self+4] at [EBP+0xC], and signData at [EBP+0x10]. Callee `ret 0xC` confirms three stack args.
- Loader obtains a UnicodeString through the output slot; handler forwards it to the output collection at 0x005EE970 and sets a completion byte at 0x005EE988.
- Exact result meaning/output key remain unproven; do not assume it is the response `wordBody` without the Windows wire fixture.
- Updated Almas acceptance doc commit `c71ccb4`; Run 45 report `256f030`.

## 2026-11-28 — Run 44 WordViewer argument routing

- Full skipdata trace shows `wordBody` is decoded by 0x00457050/0x00454B9C, checked non-empty, and used to build the temporary source stream/file. This confirms non-empty body is required for successful native load.
- `letterImages` is passed into `SeparteImages` at 0x004B7A9C/0x004B7ABD; its proven use is TIFF/preview. Defer with TIFF while not required by live Almas fixture.
- `signData` enters XML/interface operations at 0x004B7AEB–0x004B7B2F. Preserve opaque; exact schema/field mapping unresolved.
- Updated Almas acceptance doc commit `0540a65`; Run 44 report `ee4c943`.

## 2026-11-28 — Run 43 WordViewer state wait

- Full Run-50 skipdata trace of `TWordViwer.LoadDocument` exposes a second bounded wait: counter 0..100, each cycle calls the application message-pump helper at `0x00404F04`, checks an object state via `0x004010A8` against sentinel `0x0062F850`, and sleeps 5 ms via `0x004028D0` while equal.
- Nominal maximum sleep is ~505 ms, plus message-pump/check time. Exact object/sentinel meaning remains open; it is not proven to be the printer-worker completion flag.
- This is distinct from spooler job disappearance and THidePrintingThread's output-file existence gate.
- Updated worker analysis commit `d4a6612`; Run 43 report `bfd5ad3`.

## 2026-11-28 — Run 42 correction: wordBody success-path requirement

- Correction after reading the full skipdata trace of `TWordViwer.LoadDocument` from Run-50 artifact `15253702066`: the connector's TryGetValue for `wordBody` is unchecked at the handler level, but the loader decodes it and tests the decoded length at `0x004B77AB–0x004B77B5`; zero enters an error path.
- Therefore a non-empty decoded `wordBody` is required for successful native document loading. The Linux parser's requirement is consistent with the native success path; only the exact missing/empty-body error envelope may differ.
- No evidence supports successful blank-document creation from WordConfig alone. The earlier Run42 wording suggesting that as a valid path is superseded.
- Correction commits: Run42 report `e456bb6`; Almas acceptance doc `907d679`.

## 2026-11-28 — Run 42 native wordBody optionality mismatch

- Full `0x005EE82C` trace proves `wordConfig` is required, but `wordBody`, `letterImages`, and `signData` default to empty strings when missing. The handler passes all four to `TWordViwer.LoadDocument` at `0x005EE961`.
- Current Linux `parse_editword_request()` incorrectly requires a non-empty Base64 `wordBody`. This is a concrete compatibility gap for body-less/new-document requests.
- Do not only relax the parser: the full empty-body branch of `TWordViwer.LoadDocument` is still not traced, and the Writer adapter needs a verified blank/template creation path.
- Almas acceptance update commit `77da960`; Run 42 report commit `bd32b58`.

## 2026-11-28 — Run 41 parity boundary refinement

- Corrected the image/signature parity statement after reviewing existing `word_assets.py` and `libreoffice_adapter.py`: inline Base64 `image/*` WordConfig inventory and controlled Writer graphic updates already exist; explicit text/image update APIs are available but require caller-supplied verified target maps and are not auto-applied at open.
- Outer `letterImages` is preserved in `extra_parameters`; WordConfig `paramId` external-image references are inventoried but not resolved against the outer parameter. `signData` remains opaque and is not split/applied. This is the remaining image/signature binding gap, not absence of all image support.
- Updated Run 41 and Almas acceptance docs: Run 41 refinement commit `0741bdf`; acceptance doc refinement `73bd75c`.

## 2026-11-28 — Run 41 Word handler input data flow

- Best-supported EditWordDocument data-flow candidate is procedure `0x005EE82C` (TD32 label `TScanDocument.PerformMethod`): requires `wordConfig`, reads `wordBody`, `letterImages`, and `signData`, then calls `TWordViwer.LoadDocument` at `0x005EE961`.
- Missing `wordConfig` raises `Requset XML is not valid (wordConfig parameter is null)`; other three fields default to empty when absent/empty according to the shared dictionary lookup helper.
- The separate `TFaxDocument`-labelled procedure at `0x005EEB48` reads `document` and calls `TScanCommand.GetNextPage`, consistent with ScanDocument. TD32 labels are demonstrably mismatched in this region.
- Linux currently preserves `signData` and `letterImages` as opaque data, but LibreOfficeAdapter does not apply them or EMWAT field substitutions. Basic open/edit/save is not full parity.
- `TWordViwer.AddImagesToDoc` exists at `0x004C0410`; its callsite/payload format remain open.
- Updated Almas acceptance doc commit `1aa7391`; Run 41 report commit `83a7964`.

## 2026-11-28 — Run 40 connector class VMT resolution boundary

- Run-67 artifact `15260427307` reports two shortstring occurrences each for `TEmwatMethod`, `TEditWordDocument`, and `TScanDocument`, but no standard-layout VMT candidate for any of them.
- The only `TWordViwer` candidate (`0x004B10A4`) is explicitly unverified and has an implausible parent/type profile; do not treat it as a true VMT.
- The Word-edit handler class name exists in the BPL, but its VMT/registration association is not resolved. Next analysis target is custom RTTI/interface/registration references, not more guessing from TD32 labels.
- Updated Almas acceptance doc commit `770af79`; Run 40 report commit `b1b66c9`.

## 2026-11-28 — Run 39 TD32 handler-name caveat

- In Run-67 artifact `15260640277`, the procedure labelled `TCompareWordDocument.PerformMethod` at `0x005EF8AC` actually reads `ExcelConfig` and `ExcelWorkBookContent` dictionary keys. This confirms a mismatch between at least one TD32 connector class label and the actual request data flow.
- Therefore no conclusion about the EditWordDocument handler's presence/absence can be drawn from the missing `TEditWordDocument.PerformMethod` symbol. Resolve via literal keys, VMT/registration data, and live Windows capture.
- Run 39 report commit `0c2add6`; Run 38 report refined in `f17293c`.
- No production code or workflow source changed.

## 2026-11-28 — Run 38 WordViewer/connector distinction

- Run-67 artifact `15260640277` shows `TWordViwer.LoadDocument` calls `TCreateTiff.SeparteImages` at `0x004B7A9C` and `0x004B7ABD`. This connects viewer document-load to the Word-to-TIFF path, not to the Almas browser edit protocol.
- The same connector symbol scan finds `TEmwatMethod.Invoke`, ScanDocument, FaxDocument, EditExcelWorkBook, and CompareWordDocument handlers, but no `TEditWordDocument.PerformMethod` TD32 symbol. Because runtime dispatch is indirect/VMT-based, this is an unresolved handler discovery gap, not proof of absence.
- Updated Almas acceptance doc commit `b2c0cc4`; Run 38 report commit `aad3209`.
- Exact EditWordDocument handler registration, dictionary keys, and Windows wire response remain unproven. Real sanitized request/response is still required.

## 2026-11-28 — Run 37 GDI+ VMT tooling coverage

- Audited `tools/resolve_delphi_vmt_slots.py`, called by the existing `image-ui-and-vmt` job. Its `TARGET_CLASSES` omits `TGPImage` and `TGPEncoderParameters`; therefore that automated VMT pass cannot close the raw GDI+ method table.
- Added the targeted extraction command to the GDI+ crosswalk:
  `python3 scripts/dump_pe_va_ranges.py analysis-input/EmwatMethods.bpl1 --range 0x00484700:0x300 --range 0x0047DD2C:0xA0 --range 0x0062EE88:0x90`.
- Run 37 report: `docs/REVERSE-ENGINEERING-PARALLEL-FOLLOWUP-2026-11-28-RUN37.md`; crosswalk update commit `c2aa4f0`; report commit `ca8553d`.
- No tool or workflow source was modified; no new workflow was triggered.

## 2026-11-28 — Run 36 diagnostic strings and automatic workflow status

- Decoded the exact SeparteImages/Worker diagnostics from Run-50 inline constants: 0x004A08F4 `Gam Printer is in "Paused" state! please check.`; 0x004A0960 `Error on setting gam printer parameters.`; 0x004A09C0 `Error occured during Convert Word Document to Tiff.` (original misspelling preserved).
- The Worker false-return path at 0x004A02C1 uses the last message. The exact path fragments and stale-output deletion helper remain open.
- Focused doc update: `docs/THIDEPRINTINGTHREAD-FILE-WAIT-ANALYSIS-2026-11-28.md` commit `bf167a2`; Run 36 report commit `86918cc`.
- Push of Python files automatically triggered the existing `EMWAT parallel reverse-engineering lanes` workflow, run 67 / ID `46136978712`. This was not manually dispatched. At last check, native-regression was running the full Python suite, while word-print-com and image-ui-and-vmt were continuing their static-analysis jobs.
- No further Python/workflow-triggering file changes are planned while run 67 is in progress. Docs-only updates do not match the workflow's push path filter. No release package was built.

## 2026-11-28 — Run 35 additional failure-path coverage

- Added `test_request_drain_releases_registration_if_worker_creation_raises`. It forces ThreadingMixIn worker creation to raise and verifies the synchronous active-request registration is rolled back, so the drain counter cannot remain permanently nonzero.
- Test commit: `eba0ddb803d264ad6c469394b866eb2d7806b64a`.
- Together with the delayed-worker test, the new tests cover both sides of the request counter: registration-before-thread-start and rollback-on-start-failure.
- Neither test has been executed; no Actions run was started.

# Engineering follow-up — 2026-11-28 Run 35

## Track A — bridge request-drain race

### Defect

The prior request-drain counter was incremented inside `process_request_thread`. Python's `ThreadingMixIn.process_request` starts a new thread and returns to the serving loop; the worker may not execute its first instruction before the accept loop observes shutdown. Therefore the serving thread could stop while an accepted worker had not yet incremented the counter. `wait_for_requests_idle()` could incorrectly return true, after which `ThreadingMixIn.server_close()` would join that non-daemon worker without a timeout.

### Correction

- Override `_ServingThreadingHTTPServer.process_request` and increment the active count synchronously in the accept-loop thread before delegating to `ThreadingMixIn`.
- If worker creation/start raises, decrement and notify in the exception path.
- Decrement only from `process_request_thread`'s `finally` block after the worker has completed.
- The runtime's shutdown order remains: stop/join accept loop -> bounded worker drain -> socket/server close -> serving-thread join.
- On drain timeout, socket closure remains deferred and retryable; non-daemon request workers are not abandoned.

Implementation commit: `eaa87e4903b47fecf1c5af7aa9503ba44fe16f63`.

### Regression coverage

Added `test_request_drain_counts_accepted_socket_before_worker_first_instruction`:
- Patches the worker entry point to pause before its first base-class instruction.
- Sends a loopback heartbeat request.
- Verifies the drain hook still sees one active request while the worker is paused.
- Releases the worker, verifies the HTTP 200 `TickTack` response, then closes the runtime.

Test commit: `063f0c63666040b2d4d149fae08a3382db168a30`.

The test has not been executed. A local shallow clone attempt could not resolve github.com in this environment; no GitHub Actions run was started.

## Track B — Almas shutdown acceptance gate

Updated `docs/ALMAS-LIVE-END-TO-END-ACCEPTANCE.md`: the implementation now has an explicit bounded drain/retry policy, but it remains unaccepted until the deterministic worker-start race test, existing pending-request drain test, GTK close-retry test, and live Almas workflow are executed/verified.

Documentation commit: `38f68dc0f0c2acbf8b9039f29d10287ded835358`.

## Remaining external gates

- Real Almas XHR Origin and parent-page Referer origins.
- Sanitized Windows `EditWordDocument` request and corresponding response bytes/headers.
- Confirmation that Almas accepts and persists the returned edited document.
- Local execution of the targeted Python tests and GTK tests on a machine with GTK 4/PyGObject.
- Actual Windows forced-termination behavior remains outside the bounded graceful-shutdown guarantee.

No release package was built, no CI workflow was started, and no PR was merged.
