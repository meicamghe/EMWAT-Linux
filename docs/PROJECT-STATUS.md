Warning: truncated output (original token count: 109813)
Total output lines: 3242

## 2026-11-25 — Wine 11 runtime Base64 decoder probe

- The Wine 11 installation's `EmwatMethods.bpl` (`6ff7d262f46ab009e3eecf20fca40cd41ec8ad937adf7bbfe2f6eddd56aaea2d`) matches the checked-in analysis snapshot byte-for-byte. A 32-bit probe called internal decoder RVA `0x73700` after loading the BPL with `DONT_RESOLVE_DLL_REFERENCES` in a fresh disposable prefix; the existing `/home/m/.wine-emwat` prefix was not launched or modified.
- Wine 11 results: `TWFu` → `Man`, `QQ==` → `A`, `QUI=` → `AB`; invalid `QQ?=` returned false after writing a partial `A`; non-multiple-of-four `TWE` returned false without writing; raw decoder input `QQ=A` returned success as `A`, ignoring the trailing character.
- The direct probe does not call wrapper `0x004738CC` or the preceding `0x00455108` conversion. Wrapper clearing-on-failure is static evidence; acceptance of noncanonical padding is confirmed only for the inner decoder. The temporary prefix and harness executable were removed after confirming the original Wine binary hashes remained unchanged.
- Reproducible, non-production harness: `tools/reverse_engineering/probe_emwat_base64_decoder.c`. Full conditions and limits are in `WORD-FIELD-VALUE-DECODING.md`.

## 2026-11-25 — ACP conversion helper trace

- Disassembly of `0x00455108` confirms Delphi `WideString` → `AnsiString` conversion with the caller's code page (the Base64 field path supplies code page 0 / ACP), flags `0x270`, and NUL-terminated input. It queries required size `N`, sets length `N-1`, then calls `WideCharToMultiByte` with capacity `N-1`; the return value is ignored.
- A disposable Wine 11 WinAPI probe found the query size is 2 for `A`, `é`, and an unrepresentable CJK character. The write call with capacity 1 returns 0 / `ERROR_INSUFFICIENT_BUFFER` (122) but writes the first converted byte (`41`, `e9`, `3f` respectively). The `0x270` flags did not prevent this behavior. This validates the API-level short-buffer effect in Wine, not the complete BPL helper or full `SetFieldValue` behavior.
- The probe prefix was removed and the installed BPL hash was rechecked against the repository snapshot. Full evidence and limits are in `WORD-FIELD-VALUE-DECODING.md`.

## 2026-11-25 — Base64 field decoder static trace

- Traced `SetFieldValue`'s Base64 branch (`0x004BFDB0`) through `0x004735D0` / `0x004738CC` into decoder `0x00473700` in `analysis-input/EmwatMethods.bpl1`. The decoder requires a multiple-of-four input length, validates bytes through a 256-byte character-translation table, emits three bytes per full group, and interprets terminal `=` padding to produce one or two bytes. Its wrapper clears the output on a reported decode failure.
- The `0x00455108` ACP conversion and short-buffer call pattern are now statically traced and its WinAPI effect was probed on Wine 11; end-to-end behavior through the BPL helper remains unverified. Linux intentionally rejects malformed Base64; this differs from the native helper's clear-output failure path and is not described as exact malformed-input parity.
- Updated `WORD-FIELD-VALUE-DECODING.md`; no Almas-to-Writer field mapping is enabled by this static codec trace.

## 2026-11-25 — URL field decoder evidence reconciliation

- Re-disassembled the `urlencoded` helper in the checked-in `analysis-input/EmwatMethods.bpl1` snapshot. At `0x004553CE–0x004553E1`, `+` selects the one-byte constant at `0x00455454`; the constant is `0x20`, so native decoding turns `+` into a space. The `%HH` branch routes the following two characters through the hexadecimal conversion helper at `0x004551FC`.
- This confirms the existing Python `unquote_plus` behavior and the `A+B%20C` regression case. The binary’s malformed/truncated escape behavior remains unresolved; Python’s strict rejection remains fail-closed and is not claimed as native parity.
- The detailed field-decoding note was corrected; no production field mapping or live Almas compatibility claim changes.

## 2026-11-24 — real LibreOffice path through loopback bridge

- Extended the gated UNO integration to POST a generated, synthetic EditWordDocument request through the actual loopback HTTP server, run it through the service and a real LibreOffice UNO process, then validate the returned `response-word` envelope and legacy Word/CFB payload. The Writer close is automated only to keep this component test deterministic; it does not simulate a user's close choice.
- Full Python suite with `EMWAT_RUN_LIBREOFFICE_INTEGRATION=1`: **326 tests passed, no skips**. The test uses an empty synthetic `wordConfig` and empty `signData`; it does not validate field mapping or live Almas behavior.
- No current-head GitHub Actions run is claimed. The remaining product gates—matching Almas/Word fixture, semantic field mapping, live browser exchange, exact non-success response contract, and configured desktop startup—remain open.

## 2026-11-24 — Wine 11 ImageGear ABI trace and current-head verification

- Confirmed the existing reference prefix reports Wine **11.0** and inspected its installed `IGLZW32S.DLL` in place (PE32, SHA-256 `5cbb9352d71b74836c99429a1eaf39f77db753bfae6d5307199aaffbdeeee6cd`). The prefix was not launched or modified during this static pass.
- Static disassembly now establishes the `GearExtInfoGet/Set` x86 boundary (`ret 8`, two stack slots), the setter's successful numeric selector cases (9, 11, 23, 24, 27), and that getter selector 14 in state value 1 returns `TIF_Proc_LZW_Comp` at `0x10005650`.
- A complete installed-DLL trace establishes `TIF_Proc_LZW_Comp` callee cleanup of `0x4c` bytes: 19 four-byte x86 stack slots. It routes buffers through host allocation/release callbacks and reports allocation failures through the host error callback. Argument names/types, remaining callback prototypes, final return semantics, and runtime activation are still unknown; no wrapper is implemented.
- Hardened two composition-root tests to bind an ephemeral port instead of occupying the default EMWAT port `1984`. This keeps policy-bound assertions independent of a running local service.
- Local Python suite after that change: **326 tests, 324 passed, 2 optional skips**. Local CMake/Native tests were unavailable because CMake is not installed in this execution environment; no system package was installed.
- GitHub Actions at upstream commit `def0b9e55ca73cf9607abd60157489a3d7d12b31` succeeded: Python `45376123624`, LibreOffice UNO `45376123603`, Native image core `45376123231`, GTK `45376123242`, and application Debian package `45376123408`. These results cover the upstream commit before the current local test-only change.
- Reverse-engineering evidence and unresolved items are in [IMAGEGEAR-LZW-GIF-REVERSE-ENGINEERING.md](IMAGEGEAR-LZW-GIF-REVERSE-ENGINEERING.md). GAM printer profile evidence still identifies TIFF as the first native compatibility target; no native CUPS queue/job implementation or verified printer workflow is claimed.
- Direct SSH inspection of the Ubuntu host confirms the CUPS scheduler and socket are active, but `lpstat` reports no configured destinations and no system default. The earlier sandbox-only “scheduler is not running” result was an isolation artifact. Existing Wine trace evidence shows `libcups.so.2` loaded, Wine enumerated zero printers, and opening `GAMPrinter` failed with error 1801. No CUPS/Wine printer configuration was changed, and no printer workflow is verified.

## Latest desktop lifecycle regression — 2026-11-23

- Code/test head: `4c43ae3c836f845751b4e9d8c462758ab6a1a2c1`.
- Python Bridge workflow [45195106455](https://github.com/meicamghe/EMWAT-Linux/actions/runs/45195106455): success; **292 tests run, 289 passed, 3 optional skips**. Package install and console-entrypoint checks passed.
- GTK workflow [45195106572](https://github.com/meicamghe/EMWAT-Linux/actions/runs/45195106572): success; **7/7 runtime smoke tests passed**. The per-user launcher installer was exercised with an executable path containing spaces; desktop-file validation, install and uninstall passed.
- The new GTK regression confirms application shutdown waits for an active Start operation and then stops the injected supervisor. The normal entry point still injects no production supervisor.
- Native workflow [45195106435](https://github.com/meicamghe/EMWAT-Linux/actions/runs/45195106435) on code/test head `4c43ae3c836f845751b4e9d8c462758ab6a1a2c1`: normal build/CTest **4/4**, ASan/UBSan **4/4**, staged install and Debian package lifecycle all passed.
- LibreOffice UNO workflow [45194019476](https://github.com/meicamghe/EMWAT-Linux/actions/runs/45194019476): **25 tests passed** on parent code head `4c521f0de592bf1a9e5fab2fabf85699e70bfa65`; subsequent commits changed GTK lifecycle code/tests and documentation only, not UNO adapter sources. A current-head rerun is queued.
- These are component and integration-test results, not a release declaration. Live Almas browser E2E, exact Cancel/Discard wire behavior, full WordConfig/signature/image mapping, `.easz` fixture interoperability, physical scanner acceptance, and complete application packaging remain release blockers.

## GTK bridge shutdown lifecycle — 2026-11-23

- The GTK shell now serializes bridge Start/Stop operations against application shutdown. Shutdown marks the UI as closing while holding the same operation lock, preventing a queued Start worker from launching a listener after shutdown has begun.
- If an explicitly injected supervisor is RUNNING or FAILED, the application shutdown handler requests cleanup before GTK exits. A failed cleanup remains surfaced by the supervisor; the UI does not pretend a still-running worker was forcibly terminated.
- This is lifecycle protection for an injected supervisor, not production bridge configuration. The normal `emwat-linux` entry point still injects no supervisor, so the service controls remain disabled until evidence-backed Almas Origin and response configuration exists.
- The GTK runtime suite now includes a deterministic shutdown-race regression: an in-flight Start is held while the application shutdown signal is emitted from another thread; shutdown must wait for Start to finish, then stop the supervisor in order. This test passed in GTK workflow 45195106572 on code/test head 4c43ae3c836f845751b4e9d8c462758ab6a1a2c1.

## Parallel implementation checkpoint — 2026-11-23

- **Word/Writer inventory:** opening a Writer document now captures metadata-only WordConfig evidence and a separate exact-name template candidate inventory from one UNO catalog snapshot. Partial UNO inventory failures are represented by value-free warning codes. No XML field index is associated with a Writer property index because Word COM/UNO enumeration equivalence is still unproven.
- **SANE scanner:** added bounded simplex ADF page batching (100-page / 4-GiB batch limits, with remaining memory budget passed into the page reader), feeder-empty handling from start/read boundaries, and ordered 8-bit RED → GREEN → BLUE planar RGB assembly. Duplex-labelled sources are excluded. The batch collector, metadata sequence validator, padded-stride interleaver and production page reader have deterministic fake-device coverage. Physical scanner acceptance remains open.
- **Desktop launcher:** added a tested emwat-linux-desktop-entry console helper, safe Desktop Entry Exec quoting, per-user install/uninstall scripts, and GTK workflow coverage for actual install, validation and removal. This remains a launcher helper, not a complete bridge package or production service.
- Python bridge workflow [45184251311](https://github.com/meicamghe/EMWAT-Linux/actions/runs/45184251311) on code head 05dacb1e00ad0ab26b145d2e63c462c9036695fd: success, **289 tests**; package installation and all three console-entrypoint help checks passed.
- GTK desktop workflows [45184020754](https://github.com/meicamghe/EMWAT-Linux/actions/runs/45184020754) and [45184251362](https://github.com/meicamghe/EMWAT-Linux/actions/runs/45184251362): success, **6 smoke tests** each; per-user launcher install, desktop-file validation and uninstall also passed.
- LibreOffice UNO workflow [45182739787](https://github.com/meicamghe/EMWAT-Linux/actions/runs/45182739787): success, **25 tests** on the preceding code-equivalent head.
- Native workflow [45186091897](https://github.com/meicamghe/EMWAT-Linux/actions/runs/45186091897) on code head 79e15f427eb67168d2023ecfbd4e3bfbff0bdb10: success; normal build/CTest passed **4/4**, ASan/UBSan passed **4/4**, and Debian package lifecycle passed. It includes the injectable fake SANE page-reader tests. The current branch adds only additional cancellation assertions and documentation after that code-equivalent run.
- Remaining release blockers are unchanged: live Almas browser end-to-end and exact Cancel/Discard wire contract, full WordConfig/signature/image mapping with a sanitized Windows fixture, .easz interoperability, physical scanner/duplex acceptance, and complete production bridge packaging/supervision.
- PR #2 remains open, Draft and unmerged.
## GTK smoke-test correction — 2026-11-23

- The first GTK run exposed a test-fixture issue, not a product-code failure: the test attempted to register a second `Gtk.Application` under the same D-Bus application ID already owned by the class fixture.
- Updated the isolated supervisor-control test to use a distinct test-only application ID, restoring the production constant immediately after application construction. The production application ID and runtime behavior are unchanged.
- The corrected GTK test and the full workflow set have been retriggered on the new head; results are pending.

## GTK Bridge lifecycle visibility — 2026-11-23

- Added a one-second GTK-main-context poll for an injected `BridgeSupervisor`. Unexpected serving-loop exits are now reflected in the visible status without requiring the user to click Start or Stop.
- The poll stops when the main window is closed. Start/Stop work remains on worker threads, and state refresh remains on GTK's main context.
- Extended the GTK smoke test to simulate an asynchronous supervisor failure, verify the error appears, and confirm Stop remains available for cleanup.
- The default `main()` still injects no supervisor, so controls remain disabled and no listener auto-starts. This is intentional until verified deployment configuration (especially Almas Origin and Cancel response) exists.
- New GTK/Python/Native/UNO CI for this combined head is pending; do not treat the added polling/test changes as verified until those workflows finish.


## GTK Bridge controls — 2026-11-23

- Added GTK runtime regression coverage for the explicit Bridge controls introduced in the desktop shell.
- The unconfigured application must display Start/Stop controls as disabled and state clearly that the Bridge is not configured; creating the window must not start a listener.
- An injected fake supervisor is exercised through both controls. The test verifies that start/stop run on worker threads, GTK remains responsive while the operation completes, and the status/buttons refresh on the GTK main context.
- This validates the GUI-to-supervisor control boundary only. The production `main()` still injects no supervisor; no real Almas Origin, Cancel response contract, or production bridge startup is configured by this test.
- Current PR head `4eeb68ba02247cae1a3c830d546fe19afbddf59d` has passed Python, GTK, Native (build, sanitizer, and DEB package lifecycle), and LibreOffice UNO workflows. The added regression tests require a new CI run before they can be considered verified.
- PR #2 remains open, Draft, and unmerged.

## Headless bridge supervisor — 2026-11-23

- Added `BridgeSupervisor`, an application-level lifecycle owner independent of GTK. It receives an injected factory for a fully configured bridge server; it does not guess Almas origins, method handlers, or Cancel/Discard response envelopes.
- Start is idempotent while running; a successful stop allows a fresh one-shot runtime/server to be created on the next start.
- Failed start/stop is surfaced as FAILED. A failed cleanup must be retried before a new server can be created, preventing silent replacement of a possibly live listener. A factory failure before runtime creation can be explicitly acknowledged with stop and retried.
- Added headless tests for idempotent start, fresh-server restart, cleanup retry, factory failure, safe stop-before-start, and invalid factories.
- Design and lifecycle contract: `docs/BRIDGE-SUPERVISOR-LIFECYCLE.md`.
- CI for the combined head containing this work is running; no test pass is claimed until all workflows finish.
- The GTK shell is not yet wired to start the supervisor. Deployment-specific persistent settings, user-visible runtime controls, crash notifications, and verified Almas configuration remain prerequisites.

## Latest verified runtime-safety changes — 2026-11-23

- Latest code head: `3a8a2d96ad08fcc2194f0534e87fcdb4785e2040`.
- Recovery snapshot operations now serialize within one process across store instances sharing the same canonical recovery root. This prevents concurrent writers/readers from interleaving manifest replacement and old-snapshot cleanup. Regression test: `test_concurrent_store_instances_keep_manifest_and_snapshot_consistent`.
- Bridge HTTP request worker threads are now non-daemon. A caller performing the documented shutdown sequence (`shutdown()`, then `server_close()`) waits for active requests to finish instead of abandoning an in-flight document-edit request. Regression test: `test_server_close_waits_for_active_document_request`.
- Python workflow [45144669416](https://github.com/meicamghe/EMWAT-Linux/actions/runs/45144669416) on the latest code head passed: **245 tests run, 243 passed, 2 optional skips**. Package installation and `emwat-linux-doctor --help` also passed.
- All three workflows passed on code head `3a8a2d96ad08fcc2194f0534e87fcdb4785e2040`: Python [45144676001](https://github.com/meicamghe/EMWAT-Linux/actions/runs/45144676001), UNO [45144676160](https://github.com/meicamghe/EMWAT-Linux/actions/runs/45144676160), and Native [45144676190](https://github.com/meicamghe/EMWAT-Linux/actions/runs/45144676190). Native included build/test, ASan/UBSan, and DEB package lifecycle.
- The recovery lock is process-local, not an inter-process file lock. A future multi-process deployment must use a single recovery-owning process or add OS-level locking before sharing one recovery root across processes.
- These tests do not establish live Almas integration or a production-ready desktop launcher/service. PR #2 remains open, Draft, and unmerged.

## Current verified state — 2026-11-23 (latest branch head)

- Latest branch head: `a1067bd4923dd4a448b37f754484ec9dc638ff7f`.
- Recovery retention ordering now has a stable `session_id` tie-breaker when snapshot timestamps are equal. A regression test covers the count-limit case with identical timestamps.
- Python bridge workflow [45143990955](https://github.com/meicamghe/EMWAT-Linux/actions/runs/45143990955): success; **243 tests run, 241 passed, 2 optional skips**. Package build/install and `emwat-linux-doctor --help` also passed.
- LibreOffice UNO workflow [45143990759](https://github.com/meicamghe/EMWAT-Linux/actions/runs/45143990759): success.
- Native core workflow [45143991103](https://github.com/meicamghe/EMWAT-Linux/actions/runs/45143991103): success; normal build/test, AddressSanitizer + UndefinedBehaviorSanitizer build/test, and Debian package lifecycle all passed.
- These are automated component-level results. They do not establish live Almas browser integration, real Almas cancellation/discard response semantics, physical scanner compatibility, or a complete desktop installer.
- PR #2 remains open, Draft, and unmerged. Do not merge without explicit owner approval.

## Four parallel implementation tracks — 2026 11 18

- **Almas ↔ Writer contract:** added `docs/ALMAS-WRITER-LIFECYCL…99813 tokens truncated…Added tests for duplicate and case-fold collisions, empty versus missing optional content, missing optional IDs, declared twin syntax, invalid input types, and sensitive-value exclusion.
- Added a Writer close regression test: after a successful snapshot on a cancelled close attempt, a subsequent attempt must take a fresh snapshot and must not mark the session closed until `notifyClosed`.
- Python run `44798087534` on code/test commit `491ca49a`: **224 tests, 222 passed, 2 optional skips**.
- Native run `44798087414` on the same code/test commit: normal CTest **4/4**, ASan/UBSan CTest **4/4**, and Debian package lifecycle all passed.
- UNO run `44797952771` on close-retry test commit `226e0205`: **19 tests passed**. A further adapter integration test now checks twin metadata and explicitly empty optional content; fresh Python, UNO, and Native workflows for commit `41e15bbe` are queued.
- An intermediate Python run failed on an obsolete assertion after the evidence schema changed; the assertion was corrected, and the subsequent 224-test run passed. No unresolved test failure is being hidden.
- Automatic WordConfig writes remain disabled pending a sanitized matching Almas Word + wordConfig fixture and verified expected output. Visible Save / Don't Save / Cancel remains an outstanding interactive acceptance test.


## Privacy-safe Writer callback trace — 2026-11-20

- Added `close_trace.py`: an in-memory trace of fixed callback names, close-attempt ordinal, sequence number, and monotonic timestamp only.
- Wired the trace into `_DocumentCloseListener` and `_DocumentEventListener`, and exposed it through `LibreOfficeAdapter.inspect_close_lifecycle_trace(handle)`.
- Trace events include query/snapshot success or failure/notify-closing/notify-closed/disposing/save-done/save-as-done. It deliberately does not infer Save/Don't Save/Cancel and stores no document content, field values, file paths, or exception messages.
- Added unit tests for event ordering, attempt ordinals, event-name allowlisting, adapter exposure, and redaction.
- Python run `44798818684` on code/test commit `2feff5bf`: **227 tests, 225 passed, 2 optional skips**.
- UNO run `44798818677` and Native run `44798818848` were still running at this checkpoint; poll before claiming their results.


## Latest close-trace CI update — 2026-11-20

- Python run `44798818684`: **227 tests, 225 passed, 2 optional skips**.
- Native run `44798818848`: build/CTest, ASan/UBSan, and Debian package lifecycle all completed successfully.
- UNO run `44798818677` has completed package installation and runtime verification; its adapter/unit and real UNO roundtrip test step remains in progress. Do not mark the trace integration as UNO-verified until this run completes.
- Current PR head is documentation-only commit `e2e3719`; code/test head for the trace is `2feff5bf`.


## Writer interactive close acceptance — 2026-11-23

The visible LibreOffice Writer acceptance probe has now been run by the operator
on the Linux branch. All three cases passed:

- Save returned the confirmed saved marker `EMWAT_SAVE_FIXED_004`.
- Don't Save retained baseline `EMWAT_BASELINE_KEEP_20261123` and excluded
  the unsaved marker.
- Cancel left Writer open and the adapter wait pending; a later Don't Save
  completed the run without returning the new test information.

The adapter implementation now returns a separately maintained last-confirmed
saved-state file. `queryClosing` records close lifecycle only and no longer
snapshots dirty live edits. Periodic recovery remains separate from the final
bridge response. See `docs/WRITER-CLOSE-ACCEPTANCE-TEST.md` and
`docs/ALMAS-WRITER-LIFECYCLE-CONTRACT.md`.

This closes the local Writer Save / Don't Save / Cancel-retry acceptance item.
It does **not** close live Almas/browser HTTP integration, exact Windows
discard/cancel response envelopes, full WordConfig semantic mapping, or
production desktop packaging. Do not mark the product production-ready.

## Current-head verification and parallel work queue — 2026-11-23

- Branch head at this check: `0029482142a29331f9ce59c07f83d81ba55594cc`.
- GitHub Actions for this exact commit completed successfully:
  - Python bridge transport: run `45130315312` — success.
  - LibreOffice UNO integration: run `45130315321` — success.
  - Native image core: run `45130315395` — success.
- The successful workflows validate the repository's automated suites at this commit. They do not replace interactive GTK acceptance or live Almas/browser interoperability.
- The operator's 2026-11-23 Writer Save / Don't Save / Cancel-retry acceptance is recorded in `docs/WRITER-CLOSE-ACCEPTANCE-TEST.md`; it validates the local Writer close behavior only.

### Parallel work queue (do not conflate evidence levels)

1. **Almas browser bridge:** compare heartbeat/init/invoke behavior against the captured HTTP/JavaScript evidence; keep live Origin, parent-page and response-envelope assumptions explicit.
2. **WordConfig → Writer:** keep automatic field writes disabled until a sanitized matching Word + WordConfig fixture and expected output are available. Continue read-only metadata auditing and test fixture tooling.
3. **Desktop/runtime packaging:** GTK recovery picker exists as an optional view, but a supervised production entrypoint, settings/origin configuration, desktop launcher and complete install/uninstall lifecycle remain unfinished.
4. **Recovery/scanner/native:** retain the headless service boundaries; scanner preflight and native package CI are not physical hardware acceptance.

### Immediate integration gate

The next meaningful Almas acceptance input is a sanitized, synthetic-or-test-account request fixture containing the complete outer request structure and a matching expected successful response. Separate fixtures are required for Save, Don't Save and application-level Cancel if those branches are exposed by Almas. Do not infer missing wire envelopes from the local Writer close dialog.

## Browser XHR Origin configuration hardening — 2026-11-23

- The loopback bridge now validates configured XHR allowlist entries as bare HTTP(S) origins (no path, credentials, query or fragment) and canonicalizes scheme/host case plus default ports to match browser Origin serialization.
- Added constructor regressions for canonical equivalence and malformed/non-origin values. The request-side allowlist remains exact after canonicalization; no wildcard or relaxed origin matching is introduced.
- This is configuration validation only. It does not establish a live Almas deployment origin; deployments must still supply the actual local browser XHR Origin explicitly.

## Explicit empty-port rejection in browser Origin allowlist — 2026-11-23

- Follow-up review found that Python's URL parser reports `None` for both an omitted port and an explicitly empty port (for example, `https://office.example:`). The previous normalization therefore accepted a malformed authority as if no port had been supplied.
- The XHR Origin allowlist validator now rejects an authority ending in a colon, including bracketed IPv6 authorities with an empty port.
- Added regression inputs for empty ports on DNS and IPv6 hosts. This is strict configuration validation; it does not change the allowlist matching policy or infer a deployment Origin.
- Fresh CI for this follow-up is pending; do not treat the code as verified until the Python, UNO and Native workflows finish.


## Almas parent-page Origin canonicalization — 2026-11-23

- The init route's Referer-derived parent Origin now uses the same canonical form as its configured allowlist: lowercase scheme/host, omitted default ports, retained non-default ports, and bracketed IPv6 literals.
- Parent allowlist configuration now rejects malformed/empty ports and whitespace hostnames instead of preserving an authority that cannot match the browser's serialized Origin.
- Added regression tests for default-port equivalence, case normalization, non-default ports and empty-port rejection.
- The HTTP bridge still requires the deployment to provide the real Almas parent-page Origin; this change only makes exact allowlist matching consistent.


## Parallel hardening: signer catalog order and handler startup validation — 2026-11-23

- Indexed signer slot construction now records each recognized field's actual input position in one pass. Repeated identical field IDs retain every occurrence and original order; the previous `field_ids.index()` implementation could collapse duplicate positions and perform quadratic repeated scans. This is structural audit behavior only and does not infer Word-to-Writer mappings.
- The EditWordDocument handler now validates that its required non-success response factory is callable during construction. A misconfigured deployment fails at startup instead of waiting for a user to close/discard a document before surfacing an internal method error.
- Added regression tests for interleaved duplicate signer IDs and invalid response-factory inputs.
- CI for this head is pending; these changes are not yet declared verified.


## Read-only runtime diagnostics — 2026-11-23

- Added `emwat-linux-doctor` as a Python package console command, with
  `python -m emwat_linux.doctor` as an equivalent module invocation.
- The diagnostic checks Python version, LibreOffice executable discovery,
  importability of the UNO module in the active interpreter, and optional
  GTK 4/PyGObject availability. It supports human-readable and JSON output.
- The command is read-only and does not start a bridge, inspect documents,
  create settings, or touch recovery files. Missing required Python/LibreOffice/
  UNO dependencies produce a non-zero exit status; missing GTK is informational.
- Added unit coverage for successful/missing dependencies, optional GTK behavior,
  and JSON output.
- This is a dependency preflight utility only. It does not add the production
  Almas bridge daemon, desktop launcher, service supervisor, or installer.
- Fresh CI for this new code is pending; do not mark it verified until all
  Python, UNO, and Native workflows for the updated PR head complete.


## Runtime doctor and package-entrypoint CI — 2026-11-23

- Latest code/workflow head before this status note:
  `4422083a7a16a318efe1b191dc96914d9d31cb03`.
- Python bridge run `45135940090`: success; **239 tests passed**, including
  all four new doctor tests. The workflow also builds/installs the Python
  package and verifies `emwat-linux-doctor --help` resolves as an installed
  console command.
- LibreOffice UNO run `45135940200`: success.
- Native image core run `45135940438`: success; build/test, sanitizer, and
  Debian package lifecycle jobs all passed.
- The doctor command is verified as a packaged diagnostic entrypoint, not as
  a production bridge launcher. The product remains blocked on the real Almas
  request/response fixtures and a verified non-success response contract,
  plus supervised desktop runtime and complete end-user packaging.

## Release acceptance matrix and fixture gates — 2026-11-23

- Added `docs/RELEASE-ACCEPTANCE-MATRIX.md` and linked it from the README.
- The matrix separates Python/native/UNO CI, real Writer close acceptance,
  headless GTK checks, physical scanner acceptance, semantic field mapping,
  live Almas integration, Cancel/Discard response compatibility, and final
  desktop packaging. Passing one layer is not represented as passing another.
- It records the exact evidence needed before Almas integration: sanitized
  complete request/response fixtures from a controlled test account, including
  Save, Don't Save and application-level Cancel where applicable.
- No protocol response was guessed and no production launcher was added:
  those would require the real Almas wire contract and explicit Origin
  configuration.
- This is documentation-only after the verified code/workflow head
  `4422083a7a16a318efe1b191dc96914d9d31cb03`; the latest CI evidence remains
  the Python (239 tests), Native (build/test, sanitizer and package lifecycle),
  and LibreOffice UNO workflows recorded above.
- PR #2 remains open, Draft and unmerged.

## Bridge Host and runtime doctor regression coverage — 2026-11-23

- Added negative HTTP Host-header cases for wrong loopback address, hostname
  substitution, wrong port, empty port, userinfo, and appended path. The
  transport must reject these before routing to the application handler.
- Added runtime-doctor coverage for Python below the supported 3.10 minimum
  and JSON output when required dependencies are missing; optional GTK absence
  remains non-fatal.
- Latest Python bridge workflow run `45143243027` succeeded on commit
  `d3f2333dc24e38c706415b14d0be4cff8d195a9e`: 242 tests passed, 2 skipped;
  package installation and the installed `emwat-linux-doctor --help`
  entrypoint check also succeeded.
- Earlier runs for the first draft of these new tests exposed fixture and
  assertion mistakes; the tests were corrected and the final run above is
  green. No production protocol behavior was changed.


## Bridge runtime startup/shutdown race hardening — 2026-11-23

- Review found a real lifecycle hazard: Python `socketserver.BaseServer.shutdown()`
  may wait indefinitely if called before its `serve_forever()` loop has entered.
  Starting a thread is not, by itself, proof that the loop has begun.
- `BridgeHTTPServer` now exposes a readiness handshake signaled from the actual
  serve loop (and released if the loop exits before its first poll).
  `BridgeRuntime.start()` waits for this handshake while holding its lifecycle
  lock, so a concurrent `close()` cannot call shutdown too early.
- Added deterministic coverage for a deliberately delayed server startup,
  close-vs-start ordering, and immediate start/close against a real loopback
  `BridgeHTTPServer`.
- An intermediate Python run on commit `d8f17f1` correctly exposed incomplete
  fake-server test doubles that lacked the new readiness method. The fixtures
  were corrected; the final code/test head `e9b4818` passed **253 tests, 251
  passed and 2 optional skips**.
- Final current workflow head `5b439509` passed all three workflows:
  - Python bridge run `45150413887`: **253 tests, 2 optional skips**.
  - LibreOffice UNO run `45150413911`: success.
  - Native image core run `45150413915`: build/CTest, ASan/UBSan, and Debian
    package lifecycle all passed; normal and sanitizer CTest each report 4/4.
- The Ubuntu integration guide records the readiness contract and its limits.
  These results validate automated startup/shutdown regression coverage, not
  desktop logout/signal handling or live Almas/browser integration.
- PR #2 remains open, Draft, and unmerged. No production launcher, service
  unit, or complete desktop installer is claimed.


## Bridge runtime cleanup failure handling — 2026-11-23

- Hardened `BridgeRuntime.close()` so an exception from `shutdown()` does not
  skip the attempt to close the listening socket or join the serve thread.
  Cleanup failures are retained on the runtime and transition it to FAILED.
- A socket-close failure is no longer mislabeled as STOPPED. A later close
  attempt retries socket closure when the socket has not been confirmed closed.
  Closing a never-started runtime follows the same confirmed-close rule.
- Added regression tests for shutdown failure with continued cleanup and
  retrying a failed close-before-start.
- Python bridge run `45150705819` on code/test head `a300e25f`: **255 tests,
  253 passed and 2 optional skips**.
- LibreOffice UNO run `45150705730`: success.
- Native image core run `45150705790`: build/CTest, ASan/UBSan, and Debian
  package lifecycle all passed.
- The cleanup logic is headless lifecycle infrastructure; it does not add
  desktop signal handling, a GTK application entrypoint, or a production
  launcher. PR #2 remains open, Draft, and unmerged.


## GTK desktop control shell — 2026-11-23

- Added `emwat_linux.gtk_desktop`: a lazy-import GTK 4 application shell with
  local dependency diagnostics and an optional Recovery-window injection
  point. Added the `emwat-linux` Python console entrypoint.
- The shell deliberately does not start `BridgeRuntime` or compose the
  LibreOffice bridge. It displays that startup is not configured until a
  deployment supplies the actual Almas Origin allowlist and captured Cancel
  response behavior. This avoids silently creating an unusable or unsafe
  local listener from guessed values.
- Added headless tests for lazy imports, CLI help, and the no-bridge-start
  boundary; added a separate GTK 4/Xvfb workflow and a real application
  activation smoke test for environments with PyGObject installed.
- Recovery view remains opt-in through an injected controller; no default
  recovery root, encryption key, or retention policy is invented.
- Added a freedesktop `.desktop` launcher and per-user installer that resolves the active `emwat-linux` executable (including a virtual-environment path). The GTK workflow validates the desktop file and exercises installation into a temporary user data directory.
- GTK runtime smoke run `45152724036` on code/test head `72c7b6e5`
  passed on Ubuntu 24.04 under Xvfb: both the main control window and the empty
  Recovery picker window were created successfully. This validates GTK widget
  construction in CI, not a user's Wayland/X11 session or accessibility flow.
- GTK workflow run `45152999912` on head `1664f661` passed: the
  freedesktop desktop file validated, the per-user installer wrote the
  resolved executable path into a temporary XDG applications directory, and
  both GTK window-construction tests passed.
- A later regression test now also covers main-window reactivation while the
  Recovery window remains open. The separate bounded BridgeRuntime shutdown
  changes and this additional GTK test are newer than that successful GTK run
  and remain pending current-head CI.
- The shell is not yet a full production desktop application: persistent
  configuration, configured bridge supervision, desktop-session shutdown
  handling, and Almas/browser E2E remain outstanding.


## Bounded BridgeRuntime shutdown retry — 2026-11-23

- A follow-up review found that a failing server `shutdown()` could be followed
  by an unbounded `thread.join()`. If the server had not signaled its loop to
  stop, this could block the desktop caller indefinitely even though socket
  closure had been attempted.
- `BridgeRuntime` now has a validated, finite `join_timeout_seconds`
  (default five seconds). A failed shutdown performs socket cleanup and a
  bounded join, records FAILED, and raises. A later `close()` retries shutdown
  if the serve thread remains alive; a successful retry clears a resolved
  cleanup failure and reaches STOPPED. A real serve-thread failure remains
  FAILED and is retained.
- Added regression coverage for a shutdown failure that initially leaves the
  serve thread alive, a successful second shutdown attempt, and invalid timeout
  values including an overflowing integer.
- The serving thread now also reports an unexpected normal return (without a
  shutdown request) as FAILED instead of leaving a stale RUNNING state; a
  regression test verifies the retained diagnostic.
- Current code/test CI for this follow-up is pending. The previous successful
  runtime tests predate this bounded-join change; do not claim it verified
  until the new Python run completes.


## Recovery picker UX follow-up — 2026-11-23

- The GTK Recovery view now explicitly states that local recovery snapshots are
  working copies, not the final document registered in Almas.
- Discard confirmation uses Cancel as its default response.
- After a confirmed discard, the view requests a fresh state with no stale
  selection so the controller selects the newest remaining valid snapshot.
- Added a GTK smoke test for rendering a populated catalog and selecting the
  controller-provided newest entry. Current-head GTK CI is pending.
