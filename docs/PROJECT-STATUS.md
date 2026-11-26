## 2026-11-26 — connector VMT, public ScanDocument, and image-result ownership

- Runtime service/VMT mapping is now reconciled with TD32 symbols. See `CONNECTOR-HANDLER-ENTRYPOINT-INVENTORY.md` and `EMWAT-SERVICE-EXECUTABLE-ANALYSIS.md`. TD32 procedure labels are shifted for multiple methods and must not be treated as runtime class names.
- Public runtime `TScanDocument` is confirmed at `0x005EEB48` (TD32 label `TFaxDocument.PerformMethod`). It reads `document`, opens it as a stream, constructs `TScanCommand`, calls method `0x004F2558` (TD32 label `GetNextPage`; RTTI method table says `DoRequest`), then reads `FResponseXML` at `TScanCommand+0x34` through interface slot `+0x54`. The output dictionary key/XML response schema and Linux handler remain unimplemented.
- `TScanCommand` constructor `0x004F21DC` and class metadata are recovered: instance size `0x40`; fields include `ResultImage +0x20`, `FRequestXML +0x30`, `FResponseXML +0x34`. The response XML factory `0x004EB7F4`, callback `0x004F22A4`, and response interface slots still need tracing.
- Runtime `TEditWordDocument` is `0x005EE82C`; runtime `TImageEdition` is `0x005EF300` with keys `data/config`; runtime `TUpgradeEmwat` is `0x005EF24C` with key `PlugIn`. The upgrade helper references `EmwatMethods.bpl`, a `.zip` package and `EmwatUpdate.exe`.
- Windows scanner result classes include `TSetOfSinglePageImages` and `TSetOfMultiPageImages`; their exact one-to-one mapping to native `ScanOutput` variants is still open. Path literals `%.3d`, `_P`, and `_P000` show page/serial naming but not final concatenation or file ownership.
- ImageEn I/O callers are mapped to `TfrmImageTools`: `Acquire` in `InsertPicture`, `LoadFromFileAuto` in `FreeRotate`/`DeletePicture`, `SaveToFileTIFF` in `btnPrinterSetupClick`, `SaveToFile` in `CreateParams`, and `PrintImage` in `DoPrintingPanel`. Keep this UI path separate from ImageGear preview and public `ScanDocument`.
- GAM printer detection is confirmed through `EnumPrintersA` Level-2 enumeration, stride `0x54`, and driver-name match `zvprt1`; the matching `pPrinterName` is copied to active-printer storage. Full INI/registry contract is in `docs/GAM-PRINTER-CONFIGURATION-RECOVERY.md`.
- Runs 31 (`45766302144`), 32 (`45767912737`), and 34 (`45768861461`) completed successfully, including native regression. Runs 33 (`45768755921`) and 35 (`45769864678`) were cancelled when newer workflow commits superseded them; neither is a test failure. Run 36 (`45769890366`) is active: all three jobs started; native/Word/Image results are pending.
- No production scanner/ImageEdition handler was added. Request paths remain untrusted and must be confined to approved application data/output roots before Linux file access.

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

- **Almas ↔ Writer contract:** added `docs/ALMAS-WRITER-LIFECYCLE-CONTRACT.md` to separate the implemented synthetic success path from unverified live Almas behavior. It records that Save, accepted Close, close-veto/Cancel, and confirmed Discard are distinct; no unknown Cancel/Discard HTTP/XML response is guessed.
- **Word/Writer mapping:** hardened custom-property descriptor construction to reject non-string property keys before parsing. Added regression coverage for `None`, integers, booleans, and bytes. This is input-contract hardening only; it does not claim full semantic field/signature mapping.
- **Save/Close/Cancel:** documented the known close-driven behavior and the remaining evidence needed for Cancel/Don't Save. A vetoed close remains non-terminal; engine Save does not return the document; only accepted close finalization exports bytes. The current UNO adapter still lacks a verified distinct discard/cancel path.
- **GTK 4 / Ubuntu:** added an optional GTK 4 recovery picker view over `RecoveryPickerController`. It displays metadata only, supports refresh/selection, uses a native Save chooser for restore, and asks for explicit confirmation before discard. GTK imports lazily, preserving headless service operation. Added an import-boundary test and documented Ubuntu runtime packages.
- **Packaging boundary:** the existing Debian package remains the native-core development package only. No production Python bridge entrypoint, supervised user service, desktop launcher, or complete EMWAT .deb is claimed.
- Commits: GTK view `ba54acd`; GTK import test `048db89`; mapping validation `71dc461`; mapping tests `0585b1d`; Almas/Writer lifecycle contract `323edb0`; Ubuntu GTK integration docs `52d8ea6`; README refresh follows.
- CI for this new combined code head must be checked before calling these changes verified. The GTK window itself still requires a real Ubuntu GTK 4 desktop runtime test.

## EditWordDocument transport capacity alignment — 2026-11-18

- Found and fixed a real configuration mismatch: the EditWordDocument service accepted up to 64 MiB decoded Word documents and up to 24 MiB encoded configuration, but the default HTTP body and XML dispatcher caps were only 16 MiB. Such documents could never reach the service.
- Default application bridge request cap is now 128 MiB. This is bounded and accommodates Base64 expansion of the 64 MiB document, encoded config, and XML framing.
- Default HTTP and serialized response cap is now 96 MiB, enough for Base64 expansion of a 64 MiB final document plus the observed response XML envelope.
- Both `create_bridge_server` and `create_libreoffice_bridge_server` pass the same request cap to HTTP and XML parsing, and the same response cap to HTTP and the response serializer.
- Added regression tests asserting the defaults at the HTTP and dispatcher boundaries.
- This changes only configured upper bounds; it does not claim that real Almas documents of this size have been tested. Deployments can explicitly lower either cap.
- Fresh CI is required before treating this change as verified.

## Accepted Linux product decisions — 2026-11-18

- Project owner confirmed the product target is **Linux only**. The existing Windows implementation is a compatibility/reference source; no new Windows application, GUI, or installer is in scope.
- **GTK 4 + Python/PyGObject** is the selected lightweight, free/open-source control UI. Qt/PySide is not selected and must not be introduced unless the owner explicitly changes this decision.
- **LibreOffice Writer via UNO** is the Linux document editor. GTK is not a Word replacement or document editor; it is limited to EMWAT status, settings, recovery, scanner entry points, and diagnostics.
- EMWAT's primary purpose is to bridge the Almas correspondence system to Writer: receive the Almas document/request, validate and coordinate the editing workflow, obtain the final document, and return it using the evidenced Almas-compatible response contract.
- Keep the protocol bridge, document coordinator, UNO adapter, recovery, and scanner services independent of GTK. GUI dependencies must not be required by headless protocol tests or core services.
- No paid toolkit, subscription, or mandatory cloud service is acceptable. Record and comply with all dependency licenses; zero purchase cost does not remove license obligations.
- Authoritative decision record: [LINUX-PRODUCT-DECISIONS.md](LINUX-PRODUCT-DECISIONS.md).

## Latest PR-head verification — 2026-11-18

- PR #2 head checked before this documentation update: `6bedd5c64019c77d3a3fc09f6936d139e3095e29`.
- Python bridge run [44327516656](https://github.com/meicamghe/EMWAT-Linux/actions/runs/44327516656): completed successfully.
- LibreOffice UNO run [44327516796](https://github.com/meicamghe/EMWAT-Linux/actions/runs/44327516796): completed successfully.
- Native image core run [44327516916](https://github.com/meicamghe/EMWAT-Linux/actions/runs/44327516916): completed successfully.
- These are results for the checked head before the new documentation-only commits. New documentation commits do not change code, but no new CI result is claimed for the later documentation head until queried.
- PR #2 remains open, Draft, and unmerged.

## Recovery picker state and current-head validation — 2026-11-18

- The immutable picker view-state implementation and regression tests are on the current PR head.
- Python bridge CI on current head `61a0a80860603053050a689ea75c705326baa5ac` passed: run `44326008488`, **209 tests run, 207 passed, 2 optional skips**.
- LibreOffice UNO integration on the same current head passed: run `44326008410`; UNO runtime verification and real Writer roundtrip steps completed successfully.
- Native image core run `44326008415` was still executing its build and sanitizer jobs at this status update. Earlier native run `44324686807` passed on the prior head, including the staged CMake install check.
- The PR remains Draft/open/unmerged. No claim of complete application packaging or GUI is made.

## Recovery picker view-state contract — 2026-11-18

- Added immutable `RecoveryPickerState` and `RecoveryPickerController.state()` as a toolkit-neutral presentation boundary.
- Empty catalogs are explicit; the newest snapshot is selected by default; a still-valid caller selection is preserved; stale/unknown selection IDs are cleared rather than silently selecting a different document.
- The projection contains only the service's safe metadata and never exposes the private store path or document bytes.
- Added tests for default selection, explicit selection, stale selection, empty state, restore behavior, and strict discard confirmation.
- Implementation commit: `86bf845ea0df19aa40e470856a53034763ce3e90`; tests commit: `a3d6b06afdfdae092c39e6468b6d24fc635e2682`.
- This remains a view-state contract, not a graphical UI; no toolkit has been selected.

## Parallel follow-up: staged native install and recovery confirmation — 2026-11-18

- Native CI now exercises the CMake install rules instead of only compiling the library: it installs into a temporary staging prefix and asserts that the static library plus public image/scanner headers are present.
- The staged install step passed in Native image core run `44324464761` on commit `f4edf25549d3a613a671a52de281047a1715cc22`; both normal build/CTest and ASan/UBSan jobs passed.
- Recovery picker discard tests now verify that only the literal boolean `True` is accepted as confirmation; `False`, `None`, integer `1`, and string `"yes"` are rejected without deleting the snapshot.
- Python bridge run `44324505028` on the combined code/test head `6aa0af6bfea79451e60826602a315dce901baa3a` passed: **206 tests run, 204 passed, 2 optional LibreOffice tests skipped**.
- Native CI on the same head passed both build/CTest and ASan/UBSan jobs (run `44324505210`). The separate LibreOffice UNO workflow for that exact head was still running when this entry was written; do not treat it as passed until it completes.
- The install check proves staging installation of the reusable native library and headers only. It does not create a .deb, daemon, GUI, desktop launcher, or service unit.

## Preflight Base64 response-size calculation — 2026-11-18

- The observed Word success response Base64-expands the final document. The serializer now calculates the exact XML envelope length before allocating the encoded copy and rejects over-limit responses before expansion.
- The emitted XML byte length is checked against the precomputed exact size to detect serializer behavior drift.
- Added a regression test using a synthetic 1 MiB document and a deliberately small response cap.
- Implementation/test commits: `2b5f6d3`, `abe1ed5`; documentation: `9f3f67e`.
- CI for response-size code commit `abe1ed5ea514372331bbc7407c8ebac5305cf49d` passed: Python `44301296592`, Native build + ASan/UBSan `44301296564`, and LibreOffice UNO `44301296574`. The later PR head `646bcad` contains documentation-only updates.

## Document session boundary validation — 2026-11-18

- Document session IDs now require text, non-empty and already-trimmed values; non-string inputs fail with a stable ValueError instead of leaking AttributeError.
- A final document return now rejects empty bytes. The session remains FINALIZING on this validation error and the coordinator marks the operation failed rather than reporting an empty file as a successful return.
- Added session and coordinator regression tests for non-string IDs and empty final documents.
- Implementation/test commits: `8e651b7`, `d46a6be`, `b8e0189`.
- Latest full CI result predates this follow-up; fresh verification is pending.

## Scanner preflight option validation — 2026-11-18

- SANE scan options are now validated before SANE initialization or opening a physical device.
- Requested resolution must be finite and within the supported safety interval (greater than zero and at most 100000 DPI).
- Explicit mode/source strings must be non-empty and contain no control characters; invalid values are rejected before hardware access.
- Added native regression cases for NaN, infinity, zero, over-limit resolution, empty mode, newline-containing mode and embedded-NUL source.
- Implementation/test commits: `06ad29f`, `f4e7054`, `628ffad`, `cd6d6a8`.
- This is preflight validation only. It does not establish physical scanner compatibility, ADF, duplex or multi-frame support; native CI for this newest head is pending.

## Loopback transport and EditWord response-bound hardening — 2026-11-18

- Bridge constructor rejects non-built-in-integer TCP ports and body/response byte limits, invalid/non-string bind hosts, and non-finite/non-positive socket timeouts (including bool, NaN, infinities and oversized integers).
- Added constructor regression tests for all rejected input classes.
- EditWord success response serialization now receives the configured `max_response_bytes` from `create_libreoffice_bridge_server`, so the serializer and HTTP transport enforce the same configured cap instead of the serializer silently retaining its default 16 MiB ceiling.
- Added handler tests for configured response bounds and strict limit typing.
- Design and validation notes: `docs/EDITWORD-INPUT-VALIDATION.md`.
- Bridge constructor implementation/test commits: `f76d01c`, `7f1c0e6`; response cap wiring/tests: `8a00051`, `a37ec60`, `abf3520`; documentation: `94cb903`.
- CI for bridge constructor changes at `7f1c0e6`: Python run `44300445278`, Native run `44300445365`, and UNO run `44300445339` passed. The newer response-cap changes are awaiting Python CI; do not infer their result from the prior head.
- This remains transport/input hardening. No live Almas origin, actual customer document, or Windows cancel/discard response contract is claimed.

## Recovery manifest and input-validation hardening — 2026-11-18

- Recovery manifest loading now explicitly rejects valid JSON scalars/arrays instead of allowing an AttributeError to escape the catalog path. The catalog skips malformed non-object manifests and continues listing other valid sessions.
- Added regression cases for JSON array, null, and string manifests.
- Retention numeric inputs now reject booleans and non-numeric values instead of accepting bool as an integer/time value.
- Scanner device IDs are checked for control characters before SANE initialization/open, for both capability lookup and scan; regression tests include newline and embedded NUL.
- Word/Writer audit exposes only unique one-to-one case-folded name differences as review candidates; exact matching remains case-sensitive and ambiguous collisions are not suggested.
- Latest Python manifest tests were added after the latest observed CI run; final-head verification is still pending. Runs 44252073741/44252073807/44252073729 were queued at the last poll for the earlier scanner/mapping changes.

## Parallel hardening follow-up — 2026-11-18

- Recovery retention now rejects booleans and non-numeric values for age limits and the supplied current-time argument; this avoids Python's bool-is-int behavior silently accepting invalid policy input.
- SANE scanner identifiers are validated before entering the runtime: empty IDs and embedded control characters (including NUL/newline) are rejected for both capability lookup and scan operations.
- Word/Writer audit now reports a case-only candidate only when the folded identifier is unique on both sides. It excludes ambiguous case-fold collisions and never converts these candidates into mappings.
- Added regression tests for all three hardening areas. Final-head CI is pending.

## Secret Service application integration and nonce validation — 2026-11-18

- Added a strict freedesktop Secret Service key provider with get-or-create, read-after-write persistence verification, malformed/short key rejection, and refusal of plaintext fallback backends.
- Added create_libreoffice_bridge_server(encrypt_recovery=True, recovery_root=...) to inject an encrypted recovery store into the default LibreOffice adapter. Default remains plaintext; a caller-supplied adapter cannot be combined with this flag.
- Added regression coverage for Secret Service persistence failure, backend rejection, key reuse, encrypted store construction, application injection, and ambiguous custom-adapter rejection.
- Added AES-GCM envelope/manifest nonce equality validation and its tampering regression test.
- Latest branch head at this status update: ab304921215fb84a3bddb68a1f27a8ddb436b5dc. Python/Native/UNO CI runs 44249093187, 44249093242, and 44249093182 were still queued; they predate the last two key-provider test commits and must not be treated as validation of the final head.
- The live DBus Secret Service backend has not been exercised in a desktop session. CI mocks the backend and validates the fail-closed policy.

## Application-level encrypted recovery opt-in — 2026-11-18

- `create_libreoffice_bridge_server(encrypt_recovery=True, recovery_root=...)` now explicitly creates the Secret Service-backed encrypted store and injects it into `LibreOfficeAdapter`.
- Default behavior remains unchanged (plaintext recovery). A caller-supplied office adapter combined with `encrypt_recovery=True` is rejected to avoid a false security guarantee.
- Added composition tests verifying store injection and rejection of the ambiguous custom-adapter combination.
- The key provider's real DBus/Secret Service behavior remains unverified in a live desktop session; CI uses a strict mocked Secret Service backend.

## Secret Service key-provider integration — 2026-11-18

- Added `recovery_key_provider.py` with explicit Secret Service get-or-create behavior for a stable 256-bit AES key.
- The provider accepts only the freedesktop Secret Service backend; it refuses plaintext/file fallback and other unreviewed backends.
- Existing malformed or wrong-length secrets fail closed and are not silently replaced. Newly created keys are read back to verify persistence.
- Added an explicit factory to construct an encrypted `RecoverySnapshotStore`; the LibreOffice adapter's default remains unchanged and plaintext unless the application calls the factory and injects the returned store.
- Added mock-backed tests for key persistence, backend rejection, malformed/short secrets, and encrypted-store roundtrip.
- Added optional package extras for encryption and keyring support. Actual desktop DBus/Secret Service integration still requires a live Linux desktop session and has not been exercised in CI.

## Recovery encryption hardening follow-up — 2026-11-18

- Encrypted snapshot filenames now use opaque random identifiers instead of exposing the plaintext SHA-256 in the path. The SHA-256 is bound into AES-GCM associated data and verified after decryption.
- Plaintext snapshot filenames retain the SHA-256 prefix plus a unique per-write suffix to keep writes immutable and crash-safe.
- Manifest schema version is checked with strict integer typing; booleans are rejected.
- Added a regression assertion that encrypted filenames do not disclose the plaintext digest.
- Fresh Python bridge CI run `44248272905` passed after the opaque encrypted-filename and strict-schema changes. Native build-test and ASan/UBSan run `44248272884` also passed. LibreOffice UNO integration run `44248272886` was still running at the last check.

## Optional AES-256-GCM recovery encryption — 2026-11-18

- `RecoverySnapshotStore` now supports opt-in AES-256-GCM encryption when a trusted caller injects a 32-byte key. The key is never stored in the recovery directory or manifest.
- Encrypted snapshots use a versioned envelope, random 96-bit nonce, authenticated encryption, and associated data binding the session ID, document name, plaintext size, and plaintext SHA-256. The plaintext SHA-256 is checked after decryption.
- Encrypted snapshots use opaque random filenames, fail closed when the key is absent or incorrect, and reject legacy plaintext snapshots when a key is configured rather than silently mixing formats.
- Added tests for plaintext confidentiality, round-trip, wrong/missing key, tampering, legacy plaintext rejection, and crash-safe repeated writes.
- Python CI run 44247873577 exposed two issues (AES-GCM envelope offset and a stale catalog filename assertion); both have been corrected in subsequent commits. Do not claim the correction is green until a fresh Python run completes.
- Encryption remains opt-in. The application can now opt into the strict freedesktop Secret Service provider through create_libreoffice_bridge_server(encrypt_recovery=True); key rotation, migration of existing plaintext snapshots, and default activation are not implemented.
- `LibreOfficeAdapter` can already receive a configured `RecoverySnapshotStore`; the current default construction remains plaintext until the application supplies an encrypted store.

## Recovery manifest integrity and Windows archive evidence — 2026-11-18

- Recovery snapshot loading now validates that the manifest timestamp is a finite, non-negative numeric value and that the content-addressed filename hash matches the verified snapshot bytes. Invalid metadata is rejected and excluded from the recovery catalog.
- Added regression tests for malformed timestamps and a manifest filename that does not match the content hash.
- Added `docs/EASZ-ARCHIVE-FORMAT.md` documenting the evidence-bounded Windows archive path: password-protected 7z output, `.easd` entry, and `.easz` output file.
- This documentation does not claim Linux `.easz` read/write compatibility. Linux recovery remains a separate DOC/DOCX snapshot format with optional AES-256-GCM encryption when a trusted application injects an external key.
- Python bridge CI run `44246971008` completed successfully after the manifest hardening and regression tests. Native image core run `44246938174` passed build-test and ASan/UBSan; LibreOffice UNO integration run `44246938243` passed the real UNO roundtrip job. These native/UNO runs validate the corresponding workflow commits; the new manifest code is covered by the Python run.

## تست ورودی اسکنر و CI — 2026-11-18 (PR #2)

- تست‌های بدون سخت‌افزار اضافه شدند: شناسه خالی در `SaneScannerBackend.get_capabilities` و `scan_one` پیش از تماس با runtime مربوط به SANE رد می‌شود.
- Native image core run `44244437647` روی commit `ed811a14f9d151a8a386c67b80b26b3d155f5c24` کامل و موفق شد؛ هر دو job یعنی build-test و ASan/UBSan sanitizer-test، شامل مرحله Test، سبز شدند.
- این نتیجه فقط قرارداد ورودی و build/test backend را تأیید می‌کند؛ اسکنر فیزیکی، ADF و Duplex هنوز تست نشده‌اند.

## پیاده‌سازی retention بازیابی — 2026-11-18 (PR #2)

- ماژول `recovery_retention.py` محدودیت سن snapshot و/یا حداکثر تعداد را فقط با فراخوانی صریح اعمال می‌کند؛ snapshotهای معتبر جدیدتر حفظ می‌شوند و شناسه‌های حذف‌شده برگردانده می‌شوند.
- `RecoverySnapshotService.apply_retention()` این قابلیت را در لایه سرویس در دسترس قرار می‌دهد. هیچ سیاست پیش‌فرض، timer پس‌زمینه یا حذف ضمنی وجود ندارد؛ حداقل یک محدودیت مثبت لازم است و تعداد snapshotها نمی‌تواند صفر باشد.
- تست‌های اعتبارسنجی policy، حذف بر اساس سن، حفظ جدیدترین‌ها، اتصال service و حالت بدون حذف اضافه شدند.
- Python CI روی head نهایی PR با SHA برابر `f1a8260589d6f5fbd8fda0a2e45bd29c7741ff4e` موفق شد: runهای `44244362768` و `44244353561` هر دو موفق.
- این تغییر در PR پیش‌نویس #2 است و هنوز وارد main نشده. retention جایگزین رمزنگاری نیست؛ رمزنگاری at-rest، کنترل کاربر و UI واقعی Recovery همچنان باز هستند.

## تکمیل موازی Native scanner و اعتبارسنجی — 2026-11-18

- سند scanner اکنون مرز دقیق کد SANE موجود و قابلیت‌های هنوز تأییدنشده را تفکیک می‌کند: یک frame هشت‌بیتی Gray/RGB، محدودیت 1 GiB، گزینه‌های mode/source/DPI و نبود تأیید ADF/duplex/multi-frame یا سخت‌افزار واقعی.
- workflow ساخت Native اصلاح شد؛ تکرار بی‌دلیل بسته `libsane-dev` حذف شد. مسیرهای build و sanitizer موجودند و باید نتیجهٔ workflow را ملاک دانست.
- تست Python روی commit `697766a367c1cf0023c57c2827ce98c45dea7c51` موفق است: run `44237865553`؛ 147 تست، 145 پاس و 2 تست اختیاری UNO skip.
- Recovery UI گرافیکی، رمزنگاری at-rest، سیاست retention اجرایی، mapping معنایی کامل و Almas E2E همچنان باز هستند.

## کار موازی جدید — 2026-11-18

- `recovery_controller.py` یک مرز in-process و مستقل از toolkit برای اتصال UI بومی فراهم می‌کند: فهرست metadata امن، restore به مقصد انتخاب‌شده، و الزام تأیید صریح پیش از discard. این هنوز پنجرهٔ گرافیکی GTK/Qt نیست و به HTTP متصل نشده است.
- `field_mapping_audit.py` تطبیق دقیق و case-sensitive نام propertyهای Word و Writer را گزارش می‌کند؛ نام‌های مشترک، Word-only، Writer-only و نام‌های فیلدهای `DocInfo.Custom` جدا هستند. ترتیب Word و UNO برابر فرض نمی‌شود و هیچ مقدار سندی خوانده نمی‌شود.
- تست‌های جدید controller و mapping audit به Python suite افزوده شدند.
- Python bridge workflow run `44237776415` روی commit `448090b0c7625bac5cfb086fcdf10b0ef1f17a19` موفق شد: **147 تست اجرا، 145 پاس و 2 تست اختیاری LibreOffice skip**.
- این مرحله UI واقعی، نگاشت معنایی کامل، رمزنگاری/retention، پاسخ‌های لغو/Discard در پروتکل ویندوز یا E2E با Almas را تکمیل نمی‌کند.

## سرویس کاتالوگ بازیابی و شناسایی فیلدهای signer — 2026-11-17

- ماژول `recovery_service.py` یک مرز کاربردی برای Recovery Picker فراهم می‌کند: فهرست snapshotهای معتبر را به‌شکل metadata امن (بدون مسیر خصوصی یا محتوای سند) می‌دهد و عملیات restore بدون overwrite و discard را به store واگذار می‌کند. این هنوز UI گرافیکی یا endpoint HTTP نیست.
- حذف session اکنون symlink بودن خود session directory را صریحاً رد می‌کند؛ تست تضمین می‌کند فایل‌های مقصد symlink دست‌نخورده بمانند.
- `emwat_field_catalog.py` هفت خانواده‌ی تکرارشونده‌ی signer را از روی شناسه‌ی خام طبقه‌بندی می‌کند و index و ترتیب ورودی را نگه می‌دارد. twin signature image فقط وقتی پذیرفته می‌شود که دو index یکسان باشند. این ابزار ساختاری است و هنوز Word Custom Property را به Writer field/property نگاشت نمی‌کند.
- Python CI روی commit `17c75859ab0541073874f8dbe84d92a9aac21f98` موفق شد: **140 تست اجرا، 138 پاس و 2 skip**؛ run `44101952864`.
- تغییرات بازیابی و کاتالوگ فیلدها روی `main` هستند؛ Recovery UI، اتصال HTTP، رمزنگاری/retention و نگاشت واقعی فیلدها همچنان باز هستند.

## سخت‌سازی بیشتر Recovery Store — 2026-11-17

- مسیر ریشه‌ی recovery اکنون در مرز ورودی بررسی می‌شود و اگر خود مسیر به symlink تبدیل شده باشد، ساخت session و دسترسی به snapshot رد می‌شود؛ enumeration نیز از دنبال‌کردن root symlink خودداری می‌کند.
- تست رگرسیون جدید تلاش می‌کند یک recovery root را به پوشه‌ی بیرونی symlink کند و ثابت می‌کند snapshotهای بیرون فهرست یا خوانده نمی‌شوند.
- Python bridge CI روی commit `79a5301e4d2aa86012808a20179f5e205f23276d` موفق شد: **132 تست اجرا، 130 پاس و 2 skip**؛ run `44084346290`.
- این تغییر فقط حفاظت مسیر ذخیره‌سازی را تقویت می‌کند؛ رمزنگاری snapshotها، retention و Recovery UI هنوز پیاده‌سازی نشده‌اند.
 
# وضعیت پروژه EMWAT-Linux
آخرین به‌روزرسانی: 2026-11-17

## ادامه پیاده‌سازی Native — 2026-11-17 (main)

- مسیر HTTP اکنون قبل از خواندن بدنه، query مربوط به POST را اعتبارسنجی می‌کند: دقیقاً یک پارامتر غیرخالی `invoke` لازم است؛ query تکراری، ناقص یا نامرتبط با پاسخ 400 رد می‌شود.
- `RecoverySnapshotStore` به شاخه main منتقل شده است: snapshotهای DOC/DOCX با SHA-256 و محدودیت پیش‌فرض 128 MiB، مجوزهای owner-only، اعتبارسنجی symlink/manifest/container، فهرست‌کردن فقط snapshotهای معتبر و restore اتمیک بدون overwrite.
- `LibreOfficeAdapter` اکنون برای هر سند یک recovery session مستقل می‌سازد و worker دوره‌ای (پیش‌فرض 10 ثانیه) دارد. snapshot موقت با UNO و فیلتر Word 97 گرفته و در store ذخیره می‌شود؛ خطای موقت snapshot مانع ادامه ویرایش نیست. هنگام close worker متوقف و join می‌شود؛ پس از export موفق session پاک می‌شود و در خطای پیش از تکمیل، آخرین snapshot معتبر حفظ می‌شود.
- تست Python bridge روی commit `a92822d1aa83edba4e811ebebe1edd111e7dfab2` موفق شد: **131 تست، 2 skip**؛ run `44081916126`.
- LibreOffice UNO integration روی همین commit موفق شد: **13 تست پاس**؛ run `44081916143`.
- محدودیت باقی‌مانده: recovery picker/UI هنوز به کاربر وصل نشده؛ store رمزنگاری‌شده نیست و جایگزین آرشیو رمزدار Windows `.easz` محسوب نمی‌شود. سازگاری end-to-end با Almas Gam و mapping کامل فیلدهای 180گانه نیز هنوز اثبات نشده است.

آخرین به‌روزرسانی: 2026-11-17

## تکمیل مسیر DOCPROPERTY در Writer — 2026-11-16

- Python CI run `43815297715` سبز شد: **96 تست پاس** و یک تست اختیاری UNO skip.
- UNO integration run `43815162036` سبز شد: **8/8 تست**. Fixture واقعی DOCX دارای `docProps/custom.xml` و complex `DOCPROPERTY` field بود؛ property موجود به‌روزرسانی شد، Writer text fields refresh شدند و متن نمایشی مقدار جدید را نشان داد.
- `writer_fields.py` تابع `refresh_writer_text_fields` را اضافه کرد تا پس از batch تغییر propertyها، فیلدهای Writer یک‌بار refresh شوند.
- `writer_inspector.py` اکنون برای service نوع `com.sun.star.text.TextField.DocInfo.Custom` فقط property name فیلد را inventory می‌کند؛ مقدار فیلد یا presentation خوانده نمی‌شود.
- `word_fields.py` در URL decode از `unquote_plus` استفاده می‌کند؛ trace native در `0x00455314` مسیر جداگانهٔ `+` را دارد و تست `A+B%20C → A B C` اضافه شده است.
- این نتیجه مسیر custom property → DOCPROPERTY field result را در Writer تأیید می‌کند، اما مسیر مستقیم Word `Field.Result.Text` و mapping کامل 180 شناسه هنوز باز هستند.

## به‌روزرسانی تست و parser فیلدها — 2026-11-16

- Python CI run `43814423443` موفق شد: **94 تست پاس** و یک تست اختیاری UNO skip.
- `word_fields.py` اکنون `extract_docproperty_identifier` را برای استخراج شناسه از Word field codeهای `DOCPROPERTY` دارد؛ رفتار فاصله‌گذاری و fallback مطابق trace بومی تست شده است.
- دو شاخهٔ واقعی `SetFieldValue` از ثابت‌ها decode شدند: `urlencoded` و `base64`؛ مقادیر دیگر مستقیم به setter می‌رسند.
- helperهای decode در workflow run `43814583673` و artifact `14201588063` بررسی شدند: `0x00455314` درصدهای `%HH` را decode می‌کند و `+` را به فاصله تبدیل می‌کند؛ Python با `unquote_plus` و تست `A+B%20C → A B C` هم‌راستا شد.
- custom-property helper run `43815255639` موفق شد و artifact `14201569927` را تولید کرد؛ workflow بعدی `43815667035` رشته‌های Rec/CC را هم decode می‌کند. close-response VMT/interface trace run `43815434200` هنوز در حال اجراست.

## به‌روزرسانی تأییدشده — 2026-11-16 (مرحله موازی بعدی)

- پل Python در run `43813400123` موفق است: **91 تست پاس** و یک تست اختیاری UNO skip شده است.
- تست یکپارچه LibreOffice در run `43813378877` موفق است: **8/8 تست**؛ این تست روی fixture ساختگی DOCX/UNO انجام شده و هنوز سازگاری با قالب واقعی Almas را اثبات نمی‌کند.
- ماژول `writer_properties.py` اضافه شده است. فقط Custom Document Property موجود را با نام دقیق به‌روزرسانی می‌کند؛ نام ناشناخته یا خالی رد می‌شود و property جدید ساخته نمی‌شود.
- `FindWindowExtd` در `0x0045644C` با disassembly کامل بررسی شد: tokenها و جداکننده‌های `/` و `-` جدا می‌شوند و componentها در ترتیب معکوس بازسازی می‌شوند. این helper فقط در شاخه ویژه `FillImageField` دیده شده؛ قاعده locale و مقدار واقعی نمونه هنوز نیازمند اعتبارسنجی است.
- pipeline تکمیلی TD32 به‌روزرسانی شده تا parser TD32 را به‌عنوان dependency ردیابی کند و helperهای `0x00403248`، `0x00401378`، `0x00401328`، `0x00401368` و `0x00401380` را هم disassemble کند. runهای `43813533418` و `43813557802` هنگام ثبت این یادداشت هنوز در حال اجرا هستند؛ نتیجه آن‌ها تا پایان CI قطعی نیست.

## پیشرفت اجرایی جدید — 2026-11-16

- **تحلیل SevenZip مسیر بازیابی:** run `43815900302` مشخص کرد `euUnArchive` مسیر extraction و `euResetMemory` مسیر ساخت archive است؛ این دو نباید یکی فرض شوند. `euResetMemory` فقط از Finalization و Delete فراخوانی مستقیم دارد. مهم‌تر اینکه `T7zOutArchive.SetPassword` در `0x004547DC` یک stub بدون عملیات است؛ پس رشته‌ای که به آن داده می‌شود رمزگذاری خروجی را ثابت نمی‌کند. `T7zInArchive.SetPassword` پیاده‌سازی واقعی دارد، اما direct CALL xref ندارد و فراخوانی indirect هنوز بررسی می‌شود.

- **تست URL decode نهایی:** `urlencoded` اکنون رفتار native را دارد: `+` به فاصله و `%2B` به علامت `+` تبدیل می‌شود. تست‌های اصلاح‌شده در Python run `43816293635` سبز شدند (۹۹ تست، ۹۸ پاس و یک skip اختیاری). مسیر Base64 متنی از مسیر bytes تصاویر جدا نگه داشته شده تا trace زیرلایه encoding کامل شود.

- **کشف مسیر واقعی Event Sink ورد:** run `43815900228` موفق شد. `TWordApplication.ConnectTo` از مسیر COM event interface متصل می‌شود و رکورد callbackها در `OnTmrAutoSave` شامل `WordAppDocumentBeforeSave`، `WordAppNewDocument` و `WordAppWindowActivate` است. بنابراین BeforeSave به‌صورت صریح در event sink نصب شده؛ `WordAppDocumentBeforeClose` در این رکورد نیست و direct caller آن فعلاً فقط مسیر FillImgFldsForPrint است. این اتصال هنوز به‌تنهایی POST نهایی به الماس را اثبات نمی‌کند.

- **تست end-to-end متد Adapter:** `LibreOfficeAdapter.apply_custom_property_updates()` اکنون در fixture واقعی فراخوانی می‌شود؛ دو run UNO شماره 43815561042 و 43815592590 هر دو ۸/۸ پاس شدند. Python run `43815578467` نیز ۹۹ تست را پاس کرد (۹۸ پاس و یک skip). مسیر DOCPROPERTY به‌روزرسانی property، refresh فیلد و export DOC/CFB در تست واقعی تأیید شد.

- **همسان‌سازی URL decoder با native:** ثابت `0x00455454` برابر یک فاصله است؛ helper native در `urlencoded` مقدار `+` را به space و `%2B` را به `+` تبدیل می‌کند. decoder پایتون به `unquote_plus` تغییر کرد و تست هر دو حالت اضافه شد. helper نهایی تبدیل Base64 به Unicode در `0x004738CC` هنوز باید بررسی شود؛ مسیر تصویر همچنان باید bytes خام را حفظ کند.

- **عملیات batch برای propertyها:** `writer_properties.set_custom_document_properties` قبل از هر تغییر، تمام نام‌های دقیق را validate می‌کند و اگر property ناشناخته باشد هیچ بخشی از batch اعمال نمی‌شود؛ مقدارهای غیرمتنی هم رد می‌شوند. `LibreOfficeAdapter.apply_custom_property_updates` این batch را اعمال و پس از آن Writer fieldها را یک‌بار refresh می‌کند. Python run `43815578467` سبز شد: ۹۹ تست، ۹۸ پاس و یک skip اختیاری. تست UNO مخصوص متد جدید هنوز در حال اجراست.

- **یکپارچه‌سازی واقعی DOCPROPERTY در LibreOffice:** fixture DOCX اکنون یک Word field واقعی با دستور `DOCPROPERTY EMWATIntegrationMarker` و Custom Document Property متناظر دارد. تست UNO مقدار property را تغییر می‌دهد، `refresh_writer_text_fields()` را اجرا می‌کند و ثابت می‌کند متن نمایشی سند مقدار جدید را گرفته است؛ سپس سند به DOC/CFB صادر می‌شود. Inspector نیز service نوع `DocInfo.Custom` و نام property را بدون خواندن presentation یا مقدارها ثبت می‌کند.
- **CI پس از ادغام DOCPROPERTY:** Python run `43815297715` سبز شد (۹۶ تست، ۹۵ پاس، یک skip اختیاری) و UNO run `43815162036` نیز ۸/۸ تست را پاس کرد.

- **تأیید نهایی روی HEAD جدید:** Python run `43814937717` سبز شد (۹۴ تست، ۹۳ پاس و یک skip اختیاری) و LibreOffice UNO run `43814937834` نیز ۸/۸ تست را پاس کرد. تحلیل Close/response run `43814822927` هم موفق است. pipeline گسترده Custom Property با run `43814583673` هنوز در حال اجراست و نتیجه‌اش باز اعلام نمی‌شود.

- **تفکیک AutoSave محلی از ثبت نامه:** artifact run `43814607589` نشان داد `OnControlerNotify` رشته `AutoSave. EmwatAutoSaveDOC.Execute called.` را دارد، دو مسیر را از state داخلی می‌سازد، پسوندهای `.easd` و `.easz` را اضافه می‌کند و به `euUnArchive` می‌دهد. بنابراین این handler در مسیر آرشیو/بازیابی محلی نقش دارد؛ هیچ POST یا ثبت نهایی در الماس از آن اثبات نشده است. `TWordDocument.Save` نیز slot `+0x2B8` را صدا می‌زند و direct CALL xref در scan فعلی ندارد.

- **تعیین هویت slot مربوط به Controller Notify:** wrapper `TWordDocument.Get_Content` در `0x0042BDF8` از COM slot `+0xDC` استفاده می‌کند؛ بنابراین فراخوانی `OnControlerNotify` به `+0xDC` مسیر Content سند است، نه Saved getter/setter. مقدار `-1` که در آن call ارسال می‌شود هنوز معنای دقیقش مشخص نیست. wrapperهای Saved نیز قطعی‌اند: `Get_Saved`=`+0xD4` و `Set_Saved`=`+0xD8`.
- **CI تکمیلی Close/Content:** run شماره 43814460258 موفق شد و artifact شماره 14201473774 را تولید کرد.

- **parser اختصاصی DOCPROPERTY:** تابع `extract_docproperty_identifier` به decoder اضافه شد و رفتار native `FindFieldInActivefields` را با حساسیت به حروف، جداکننده دو فاصله و محدودیت ۲۵۵ کاراکتر بازسازی می‌کند. تست‌های edge-case از جمله triple-space و field ناقص اضافه شدند.
- **CI پایتون پس از parser:** run شماره 43814423443 سبز شد: ۹۴ تست اجرا، ۹۳ پاس و یک skip اختیاری UNO.

- **اصلاح مهم در تفسیر Saved:** wrapperهای تولیدشده نشان دادند `Get_Saved` از slot `+0xD4` و `Set_Saved` از slot `+0xD8` استفاده می‌کند. بنابراین استفاده callback `WordAppDocumentBeforeSave` از `+0xD8` خواندن Saved نیست؛ مقدار OleVariant ورودی و علت این setter هنوز باید ردیابی شود. slot `+0xDC` در `OnControlerNotify` نیز هیچ‌کدام از این دو نیست و بررسی `Get_Content` در حال اجراست.

- **تکمیل decode ثابت‌های native:** در `SetFieldValue` ثابت `0x004BFEE8` برابر `urlencoded` و `0x004BFF0C` برابر `base64` شناسایی شد؛ این دو شاخه با decoder فعلی Python هم‌راستا هستند. تابع `FindFieldInActivefields` نیز token واقعی `DOCPROPERTY` و جداکننده‌های فاصله را پردازش می‌کند. شناسه ویژه `Hidden_Customizable` هم از مسیر `GetDocFieldName` به `SilentSaveEmwatDoc` می‌رسد؛ این مسیر مستقل از callback بستن سند است.
- **چرخه‌ی viewer و dictionaryها:** routine در `0x004D1148` با شواهد VMT/RTTI به‌عنوان `TWordViwer.Destroy` شناسایی شد، نه `AddXmlWordConfigFieldsToDic`: VMT candidate در `0x004B10A4`، destroy slot در `0x004B10A0` و RTTI method record در `0x004B1629` هر سه این هویت را تأیید می‌کنند. این destructor دیکشنری‌های `+0x64/+0x68/+0x6C` را آزاد می‌کند و `ScreenRefresh` را صدا می‌زند؛ متن‌های log و برچسب TD32 قدیمی/گمراه‌کننده‌اند. `LoadDocument` routine initializer-like در `0x004D0D24` را صدا می‌زند که همین سه دیکشنری را می‌سازد. `AddCustomDocPropertiesToDic` در `0x004D1454` مجموعه CustomDocumentProperties ورد را enumerate می‌کند، برای هر property با index صفرمبنا XML field متناظر را از viewer+0x40 می‌خواند، نام را در اولین `†` split می‌کند و descriptor تک/twin را با Add wrapper در mapهای viewer+0x68/+0x6c درج می‌کند. کلید map نام اصلی و unsplit property است. wrapperهای `0x004D531C` و `0x004D68D4` در TD32 به‌اشتباه `Remove` نام‌گذاری شده‌اند، اما بدنه آن‌ها Add است. دیکشنری runtime جداگانه viewer+0x64 از نوع `TDictionary<UnicodeString,TDocumentCProperty>` است.

- **ردیابی چرخه Close در Word:** run شماره 43813684507 موفق شد. wrapper بستن بدون آرگومان از slot `+0x4D4` و wrapper سه‌آرگومانی `OleVariant` از slot `+0x29C` استفاده می‌کند؛ callback مربوط به BeforeSave wrapper سه‌آرگومانی را پس از منطق Cancel/Prompt فراخوانی می‌کند. مسیر OnControlerNotify نیز CostumizeRecAndCC را اجرا می‌کند که به slot `+0x2BC` (PrintOutOld) می‌رسد؛ slot جداگانه `+0xDC` هنوز در حال تعیین هویت است و هیچ اتصال مستقیم به HTTP ثبت نشده.

- **تفکیک قطعی دو helper فیلد:** فهرست TD32 مشخص کرد `0x004BFDB0` تابع `TWordViwer.SetFieldValue(TXmlWordConfigField, UnicodeString)` است و `0x004BC170` تابع جداگانه `FindFieldInActivefields(UnicodeString)` است. اولی شاخه‌های تبدیل/اعمال مقدار را بر اساس دو ثابت رشته‌ای بررسی می‌کند؛ دومی برای تطبیق شناسه در فهرست active fieldها استفاده می‌شود. مقادیر ثابت‌ها در pipeline بعدی decode می‌شوند.
- **مسیر ساخت dictionaryها:** `LoadDocument` در `0x004B78E9` routine initializer-like در `0x004D0D24` را فراخوانی می‌کند. این routine دیکشنری‌های `+0x64/+0x68/+0x6C` را با helperهای `0x004D4670`، `0x004D5C28` و `0x004D71E0` ایجاد می‌کند. `0x004D1148` destructor مجازی viewer است و نباید به‌عنوان AddXml/population استفاده شود. `AddCustomDocPropertiesToDic` در `0x004D1454` مستقیماً از LoadDocument فراخوانی می‌شود.

- **Writer Custom Property update adapter:** ماژول writer_properties.py فقط property موجود با نام دقیق و تأییدشده را به‌روزرسانی می‌کند؛ property ناشناخته را ایجاد نمی‌کند و مقدار قبلی را نمی‌خواند. تست UNO واقعی نیز یک property آزمایشی را اضافه و از طریق همین adapter به‌روزرسانی کرد و سپس سند را بست و DOC/CFB خروجی گرفت.
- **تأیید پس از ادغام Twin Field:** run پایتون 43813400123 موفق شد: ۹۱ تست اجرا، ۹۰ پاس و یک skip اختیاری UNO. run یکپارچه LibreOffice شماره 43813378877 نیز ۸/۸ تست را پاس کرد. تحلیل custom-property run 43813303321 نیز موفق و artifact آن 14201306994 است.
- **تحلیل موازی بعدی:** pipeline جدید در commit 0f5622a گسترش یافت تا 0x004BFDB0، 0x004BC170، 0x004D08B4، 0x004D1148، 0x004D1454 و 0x004D3B78 را در کنار مسیرهای قبلی ردیابی کند؛ run 43813533418 در صف اجراست و هنوز نتیجه‌ای برای آن ادعا نمی‌شود.

- **یکپارچه‌سازی Twin Field در مدل decode:** شناسه‌های فیلد اکنون هنگام decode نیز به ساختار single/twin تبدیل می‌شوند؛ شناسه خام اصلی حفظ شده و دو سمت Twin جداگانه در دسترس adapter قرار می‌گیرد. این تغییر صرفاً مدل‌سازی شناسه است و هیچ mapping حدسی به bookmark یا Writer range انجام نمی‌دهد.
- **تحلیل مسیر Custom Properties:** artifact شماره 14200962076 (run 43812565648) مسیر dictionary سفارشی را عمیق‌تر کرد. helperهای ContainsValue و SetItem در مسیر FillImageField/FillPrintDocFields به کار می‌روند؛ 0x004D1B30 در TD32 به ShowRecAndCcOptionForm نام‌گذاری شده و از GetDocFieldName فراخوانی می‌شود. FindWindowExtd در 0x0045644C از مسیر FillImageField استفاده می‌شود. این توابع هنوز به‌تنهایی معنای wire یا نگاشت همه ۱۸۰ فیلد را تعیین نمی‌کنند.

- **تکمیل موجودی ساختاری Writer:** بر اساس trace جدید `AddCustomDocPropertiesToDic`، catalog اکنون نام Custom Document Properties را هم بدون خواندن مقدارشان ثبت می‌کند. تست واحد، عدم دسترسی به مقادیر را assert می‌کند و تست UNO واقعی نیز یک property ساختگی اضافه کرده و نام آن را از catalog می‌گیرد.
- **تفکیک دقیق‌تر فیلد متن/تصویر:** trace نشان داد `FillTextField` بیشتر نقش تشخیص MIME و dispatch به `FillImageField` را دارد؛ نباید آن را setter متنی فرض کرد. قرارداد واقعی setter و mapping فیلدها هنوز در حال بررسی است.
- **شناخت قرارداد Twin Field:** trace جدید delimiter واقعی `†` (U+2020) را پیدا کرد. فیلدهای نام‌گذاری‌شده با دو سمت غیرخالی به `TXmlWordConfigTwinField` می‌روند؛ ورودی‌های بدون delimiter یا با یک سمت خالی single محسوب می‌شوند. تابع `parse_word_field_identifier` و تست‌های آن اضافه شده‌اند.
- **مقصدهای واقعی مقداردهی Word:** trace `FillImageField` نشان داد مقدار فیلد می‌تواند در `CustomDocumentProperties[index]` یا `Field.Result.Text` نوشته شود؛ مسیر Field.Result.Text وضعیت قفل فیلد را هم بررسی می‌کند. این دو مقصد در مدل Linux باید جدا بمانند.
- **CI جدید:** Python bridge run `43812324657` با 87 تست (یک skip اختیاری UNO) سبز است؛ UNO run `43811929904` نیز 8/8 تست را پاس کرده است. اجرای helper pipeline `43812127854` هم موفق بوده است.
- **تکمیل lookup مقدار Custom Property:** helper pipeline run `43812565648` موفق شد؛ `0x004D3DF8` برابر `TDictionary<UnicodeString,TDocumentCProperty>.ContainsValue` و `0x004D34B0` برابر `SetItem` است. `0x004D1B30` نیز `ShowRecAndCcOptionForm` و `0x0045644C` تابع `FindWindowExtd` است؛ نقش دقیق آن در special-caseها هنوز باز است.
- **نوشتن Custom Document Property در Writer:** ماژول `writer_properties.py` فقط property موجود با نام دقیق را به‌روزرسانی می‌کند؛ property ناشناخته را ایجاد نمی‌کند و مقدار قبلی را نمی‌خواند. تست UNO واقعی این عملیات را روی fixture ساختگی تأیید کرد.
- **فهرست نمادهای TD32:** run `43813303321` موفق شد و 611 procedure مرتبط با `TDocumentCProperty` و single/twin field classes را index کرد؛ `SetFieldValue` در `0x004BFDB0` و `GetXmlFieldInfo` در `0x004BFC18` برای trace دقیق‌تر مشخص شدند.
- **مسیر Controller Notify:** run `43813684507` موفق شد؛ `OnControlerNotify` پس از `CostumizeRecAndCC` مقدار `-1` را به COM slot `+0xDC` روی document interface می‌دهد و سپس flagها را reset و مقادیر را از مسیر اصلاح جهت فارسی عبور می‌دهد. نوع دقیق COM method و ارتباطش با ثبت نهایی هنوز در حال تطبیق است.
- **CI نهایی این مرحله:** Python run `43813400123` با 91 تست (یک skip اختیاری UNO) سبز است؛ UNO run `43813378877` نیز 8/8 تست را پاس کرده است.
- **اجرای مهندسی معکوس فیلدها:** run `43811074616` با موفقیت تمام شد و artifact شامل ۴۱ فایل disassembly/callsite/strings دریافت و بررسی شد. مسیر custom document properties و نقش شرطی `SilentSaveEmwatDoc` مستند شد.

- **LibreOffice UNO واقعی:** ماژول python/src/emwat_linux/libreoffice_adapter.py اضافه شده است. برای هر سند یک process و profile مستقل LibreOffice و یک socket محلی UNO ساخته می‌شود؛ ورودی DOC/CFB و DOCX شناخته می‌شود؛ listenerهای تغییر، Save و Close ثبت می‌شوند؛ هنگام Close یک snapshot با فیلتر Word 97 به فایل DOC جداگانه نوشته می‌شود.
- **تست موتور واقعی:** workflow 43810592239 موفق است؛ ۸ تست شامل یک roundtrip واقعی DOCX → LibreOffice UNO → Close → DOC/CFB خروجی و شناسایی bookmark واردشده از DOCX پاس شده‌اند. این تست هنوز از fixture ساختگی استفاده می‌کند، نه فایل محرمانه نامه واقعی.
- **ترکیب سرویس:** create_libreoffice_bridge_server در application.py مسیر EditWordDocument را به EditWordDocumentService و LibreOffice adapter وصل می‌کند. سیاست پاسخ Cancel عمداً باید از بیرون تزریق شود؛ envelope اصلی Windows هنوز تأیید نشده و حدس زده نشده است.
- **Decode فیلدها:** word_fields.py هر field را بر اساس encryption خودش decode می‌کند: URL-encoded متن، Base64 تصویر و متن بدون encoding را جدا نگه می‌دارد. signData با paramId خارجی همچنان opaque است و separator/concater آن حدس زده نمی‌شود.
- **تست Python:** workflow 43810584813 موفق است؛ ۸۶ تست پاس شده‌اند و یک تست اختیاری UNO به‌دلیل اجرا نشدن در آن workflow skip شده است. تست UNO واقعی در workflow جداگانه ۸/۸ پاس شده است.
- **مرزهای باقی‌مانده:** catalog ساختار Writer اکنون bookmarkها و text fieldها را بدون افشای محتوای نامه فهرست می‌کند؛ نگاشت ۱۸۰ فیلد EMWAT به bookmark/content-control/Writer range هنوز انجام نشده؛ تصویر امضا، signData، تنظیمات/مجوزهای سند، prompt لغو، و ثبت واقعی در Almas Gam هنوز end-to-end تأیید نشده‌اند.

گزارش تفصیلی معماری و مرزهای تأیید: docs/LINUX-NATIVE-IMPLEMENTATION-PLAN.md.

## وضعیت اجرایی و شواهد جدید — 2026-11-15

- **مسیر پایتون:** آخرین CI پل پایتون، run `43721449170`، موفق است: **۶۹ تست** اجرا شده و همگی پاس شده‌اند. تست‌های جدید هماهنگ‌کننده سند و سرویس دامنه EditWordDocument نیز در این اجرا موفق‌اند.
- **هماهنگ‌کننده سند:** `office_adapter.py` قرارداد مستقل موتور آفیس را تعریف می‌کند؛ `document_coordinator.py` مسیر open → wait for close → export final bytes را اجرا می‌کند و `editword_service.py` parser درخواست را به این هماهنگ‌کننده وصل می‌کند. callbackهای تغییر سند و Save موتور جدا هستند؛ رویدادهای زمان initialization نادیده گرفته می‌شوند و Save باعث بازگشت پاسخ نمی‌شود. factory مربوط به handler در `editword_handler.py` اضافه شده و serializer موفقیت را به dispatcher وصل می‌کند، اما هنوز در application ثبت نشده و LibreOffice UNO واقعی وجود ندارد.
- **قرارداد درخواست:** parser برای `EditWordDocument` و `wordConfig` وجود دارد؛ سند ورودی Base64 به bytes تبدیل می‌شود، اما `signData` عمداً به‌صورت متن opaque نگه داشته می‌شود. این adapter هنوز handler تولیدی نیست.
- **شبکه:** heartbeat واقعی پاسخ `TickTack` و init script capture-matched در پل پایتون پیاده شده‌اند. مقدار `invoke` فقط nonce هر درخواست است، نه شناسه جلسه.
- **بازیابی:** `.easz` در `%TEMP%\\temp-emwatASwf\\` فهرست می‌شود؛ مسیر بازیابی از کلاس `T7zInArchive` استفاده می‌کند. متد `SetPassword` در `0x00453860` رشته را در فیلد `+0x58` نگه می‌دارد و با یک helper شبیه callback مسیر استخراج را فراخوانی می‌کند؛ نگاشت dispatch `euResetMemory +0x44` به این متد هنوز قطعی نیست. مقدار پیش‌فرضی که مسیر `euResetMemory` به dispatch رمز می‌دهد `mW@Tlogs43end_+` است؛ نام کاربری Windows و `@25*gamsign*25@` متعلق به مسیر مجزای cleanup/logging هستند و نباید با رمز بازیابی یکی فرض شوند.
- **محدودیت بازیابی:** وجود reader و عملیات استخراج تأیید شده، اما نوع دقیق فرمت آرشیو، نگاشت قطعی دو dispatch مسیرها در `euResetMemory`، محتوای `.easd` و تنظیمات writer هنوز باز هستند. wrapper متد `T7zOutArchive.SetPassword` یک stub بی‌اثر است؛ مسیر callback رمز writer هنوز باید ردیابی شود.
- **Word lifecycle:** پاسخ EditWordDocument در capture پس از حدود ۵۴٫۵۶ ثانیه انتظار صادر شده است. این با نشست طولانی و انتظار برای پایان ویرایش سازگار است، اما callback دقیق Close که پاسخ را آزاد می‌کند هنوز اثبات نشده است.
- **تحلیل خطاها:** جدول پیام‌های خطا در `docs/WORD-ERROR-MAP.md` از جدول event/COM جدا شده است؛ رشته‌های آن error map هستند، نه فهرست callbackها. نگاشت واقعی event DISPIDها هنوز نامعلوم است.
- **تحلیل موازی جاری:** تحلیل مستقل SevenZip plugin، run `43719323732`، با موفقیت تمام شده و artifact `14164146310` بررسی شده است؛ workflow تکمیلی مسیر recovery با شناسه `43719180035` هنوز در مرحله ردیابی reader/writer بود.

گزارش‌های تفصیلی: `docs/RECOVERY-STORE-ANALYSIS.md`، `docs/PCAP-EDITWORD-DOCUMENT-ROUNDTRIP.md`، `docs/WORD-ERROR-MAP.md` و `docs/LINUX-NATIVE-IMPLEMENTATION-PLAN.md`.

## هدف قطعی
بازسازی بومی EMWAT برای Linux با حفظ رفتار و گردش‌کارهای واقعی نسخه Windows. اجرای نسخه Windows با Wine راهکار محصول نهایی نیست. LibreOffice به‌عنوان جایگزین/پل تعامل با اسناد و صفحه‌گسترده‌ها در نظر گرفته شده، اما روش اتصال تا روشن‌شدن رفتار واقعی برنامه تعیین نمی‌شود.

## وضعیت مخزن و شواهد موجود
- مخزن: https://github.com/meicamghe/EMWAT-Linux
- شاخه اصلی: `main`
- فایل مرجع استخراج‌شده: `EMWAT_Extracted.zip`
- گزارش‌های رشته‌ای موجود:
  - `EmwatService.exe-strings.txt`
  - `EmwatAgent.exe-strings.txt`
  - `EmwatMethods.bpl1-strings.txt`
  - `EMWAT-Analysis-Results.txt` (خروجی فیلترشده و تجمیع‌شده)
- گزارش‌ها شواهد استخراج رشته‌ها هستند، نه سورس‌کد. رشته‌های تصادفی/خراب و نام کلاس‌ها به‌تنهایی اثبات نمی‌کنند یک قابلیت در نسخه نصب‌شده فعال یا قابل استفاده است.

## شناسایی فنی تأییدشده
- محصول در فراداده با نام Empowered Web Application Technology (Emwat) / Emwat Service و شرکت GamElectronics معرفی شده است.
- فایل‌های اصلی بررسی‌شده PE32 و x86 هستند.
- فایل‌های BPL با پسوند/شماره بسته `230` با Delphi 10 Seattle سازگارند.
- سرویس از اجزای Indy مانند `TIdHTTPServer` و `TIdCustomHTTPServer` استفاده می‌کند.
- سرویس نام/رشته‌های مربوط به `EmwatMethods.bpl` را دارد و بارگذاری این BPL در رشته‌ها دیده می‌شود.
- پورت محلی پیش‌فرضی که در رشته‌ها صریحاً دیده شده `1984` است؛ پیام خطا می‌گوید اگر پورت اشغال باشد binding شکست می‌خورد.
- Agent رشته heartbeat به نشانی `http://127.0.0.1:1984/?heartbeat` دارد و نام/رشته‌های sentinel و reliability نیز در آن دیده می‌شود.
- در Service یک bridge جاوااسکریپت دیده شده که پیام `postMessage` را با HTTP POST به `127.0.0.1:<myport>?invoke=<random>` می‌فرستد و پاسخ `responseText` را به پنجره والد برمی‌گرداند. این شواهد معماری ارتباط UI وب‌مانند با سرویس محلی را تقویت می‌کند؛ مرورگر/موتور دقیق هنوز قطعی نشده است.
- رشته‌های XML برای متدهای `ShowEmwatSetting`، `ShowLastEditedDocs` و `ShowSendLog` وجود دارند.
- رشته‌های کلید رجیستری `Software\\Emwat\\Dynamic Config` دیده شده‌اند.
- در BPL اصلی نام‌ها و type informationهای فراوانی برای اتوماسیون Word/Excel، XML، تصویر/اسکن/WIA، چاپ، ایمیل/SMTP، فکس و نمودار وجود دارد. این‌ها سرنخ قابلیت‌ها هستند و باید با رفتار اجرایی/نمونه گردش‌کار تأیید شوند.
- رشته‌های `.mdb` و ODBC که در برخی فایل‌ها دیده شده‌اند، به‌تنهایی اثبات نمی‌کنند دیتابیس برنامه Microsoft Access یا ODBC است. موتور پایگاه داده هنوز شناسایی نشده است.

## اجزای شناخته‌شده
- `EmwatService.exe`: سرویس اصلی؛ میزبان HTTP محلی بر اساس رشته‌های Indy.
- `EmwatAgent.exe`: Agent با heartbeat به سرویس محلی و رشته‌های sentinel/reliability.
- `EmwatMethods.bpl1`: کتابخانه منطق/متدها و wrapperهای اتوماسیون؛ جزئیات داخلی هنوز نیازمند تحلیل بیشتر است.
- `EmwatUpdate.exe`: ابزار به‌روزرسانی؛ رفتار و endpointهای آن هنوز روشن نیست.
- `GAMPrinterSetup.exe` و پوشه `GAMPrinterSetup`: ابزارها و DLL/EXEهای متعدد مرتبط با زیرساخت چاپ؛ جزئیات پروتکل/وابستگی باید جداگانه بررسی شود.
- `klc.exe`: فراداده آن «Farsi Keyboard in Office Automation Forms» را نشان می‌دهد؛ KLC، نسخه 1.0.3.9411.

## مواردی که هنوز نباید قطعی فرض شوند
1. نوع، schema و محل پایگاه داده.
2. API کامل سرویس، مسیرها، verbها، قالب درخواست/پاسخ و احراز هویت.
3. اینکه UI دقیقاً از Internet Explorer، WebBrowser control یا موتور دیگری استفاده می‌کند.
4. فهرست قابلیت‌های واقعاً فعال و گردش‌کارهای اصلی کاربر.
5. قالب فایل‌های داده، الگوها، فرم‌ها و گزارش‌ها.
6. رفتار به‌روزرسانی، ارتباط شبکه‌ای خارجی و وابستگی‌های امنیتی.
7. امکان جایگزینی کامل Office Automation با LibreOffice و نقاط تفاوت.

## تصمیم‌های معماری نسخه Linux
- هدف نسخه بومی Linux است؛ عدم اتکا به Wine.
- پیاده‌سازی اولیه با Python قابل بررسی است، اما انتخاب framework نهایی پس از تکمیل تحلیل رفتار و مرزهای سرویس انجام شود.
- ارتباط داخلی می‌تواند از یک API محلی امن استفاده کند؛ طراحی دقیق باید پس از استخراج قرارداد واقعی درخواست/پاسخ انجام شود.
- برای فایل‌ها و اسناد، ODF/OOXML و LibreOffice بررسی شوند؛ تبدیل قالب نباید بدون تست سازگاری انجام شود.
- تا روشن‌شدن دیتابیس، هیچ موتور خاصی را به‌عنوان انتخاب نهایی تثبیت نکنید.
- داده‌های مشتریان، کلیدها، اطلاعات ورود و داده‌های شخصی نباید در مخزن یا گزارش‌های عمومی قرار بگیرند. پیش از commit گزارش‌های خام، آن‌ها را از نظر اطلاعات حساس بازبینی کنید.

## تحلیل تکمیلی انجام‌شده در 2026-11-10
- سند مستقل [تحلیل HTTP محلی و bridge](HTTP-LOCAL-API-ANALYSIS.md) اضافه شد.
- شواهد heartbeat و invoke در قالب جدول مستند شدند و مدل ارتباطی موقت ترسیم شد.
- موارد نامعلوم API و ملاحظات امنیتی نسخه Linux تفکیک شدند.
- Import Table سه فایل Service، Agent و Methods استخراج و در [گزارش تحلیل Importها](IMPORT-TABLE-ANALYSIS.md) مستند شد.
- COM/OLE در Agent، dependencyهای Indy در Service/Methods، چاپگرهای Windows، ImageEn/WIA/TWAIN، GEAR32PD و GDI+ شناسایی شدند.
- در importهای مستقیم گزارش‌شده، driver صریح دیتابیس و import مستقیم شناخته‌شده مرورگر پیدا نشد؛ این موارد همچنان باز هستند، چون بارگذاری پویا ممکن است.
- تحلیل تکمیلی typeinfo نشان داد wrapperهای صریح Word و Excel در Methods وجود دارند؛ COM/OLE و Office Automation اکنون با اطمینان بسیار بالا تأیید شده‌اند. جزئیات در [تحلیل Office/COM](OFFICE-COM-ANALYSIS.md) ثبت شد.
- رشته‌های CLSID/ProgID literal هنوز یافت نشده‌اند؛ نبود literal، activation پویا یا GUIDهای binary/typeinfo را رد نمی‌کند.
- نماد `TWordApplication.Get_Browser` به object model خود Word تعلق دارد و نباید به‌عنوان اثبات embedded browser استفاده شود.
- ابزار مرحله بعد [EMWAT-COM-Resource-Analyzer.py](../tools/EMWAT-COM-Resource-Analyzer.py) به مخزن اضافه شد. این ابزار GUID/ProgIDهای محتمل را در فایل‌ها و resourceهای PE جست‌وجو می‌کند و resourceها را محلی استخراج می‌کند.
- ابزار روی 70 فایل در `D:\\emwat revers\\EmwatInstaller` اجرا شد و گزارش `EMWAT-COM-Resource-Report.txt` با موفقیت در مخزن قرار گرفت؛ فایل‌های resource خام آپلود نشده‌اند.
- گزارش Resource Analyzer در [تحلیل COM و PE Resourceها](RESOURCE-ANALYSIS.md) ثبت شد: literal `Word.Application` در مسیر چاپ تأیید شد؛ hitهای MIME/charset از ProgIDهای واقعی تفکیک شدند؛ GUIDهای terminate سرویس/Agent از CLSIDهای Office جدا شدند.
- فرم `TfrmWordPrintOption` از `EmwatMethods.bpl1` از مسیر `analysis-input/RCDATA_TFRMWORDPRINTOPTION_19.bin` دریافت و decode شد: 34 component، عنوان «تنظیمات چاپ»، انتخاب چاپگر، گیرندگان/CC، محدوده صفحات و شمارنده‌های نسخه استخراج شدند. جزئیات در [WORD-PRINT-OPTION-DFM.md](WORD-PRINT-OPTION-DFM.md) است. سه فرم Scan Preview، Image Tools و Simple Image Editor هنوز decode نشده‌اند.

## گام‌های بعدی تحلیل
1. بررسی strings و typeinfo انجام شد؛ Word/Excel Automation مستند شد.
2. تحلیل گزارش COM/Resource انجام شد؛ فرم Word Print به‌صورت کامل از Binary DFM decode شد. گام بعد decode سه فرم اسکن/تصویر و بررسی هدفمند Registry فقط برای Word/Excel است.
3. بررسی فایل‌های config/INI/REG و محتوای پوشه چاپ؛ ثبت فقط مقادیر غیرحساس.
4. شناسایی دقیق قرارداد heartbeat و invoke: پارامترها، payload، پاسخ‌ها و مسیرهای دیگر HTTP.
5. شناسایی دیتابیس از روی فایل‌های واقعی، importها، driverها و تنظیمات؛ نه از روی MIME string.
6. تهیه ماتریس قابلیت‌ها: شاهد، سطح اطمینان، روش اعتبارسنجی و معادل پیشنهادی Linux.
7. پس از تکمیل شواهد، نوشتن specification و سپس پیاده‌سازی ماژول‌به‌ماژول همراه تست.

## نقطه شروع جلسه بعد
از [گزارش وضعیت](PROJECT-STATUS.md)، [تحلیل HTTP](HTTP-LOCAL-API-ANALYSIS.md)، [تحلیل Importها](IMPORT-TABLE-ANALYSIS.md) و [تحلیل Office/COM](OFFICE-COM-ANALYSIS.md) شروع کن. Office Automation اکنون تأیید شده؛ Import Table را تکرار نکن. گام بعدی decode فرم‌های Scan Preview و Image Tools و بررسی هدفمند COM Registry برای Word/Excel است. فرم Word Print دیگر در صف decode نیست؛ گزارش آن در [WORD-PRINT-OPTION-DFM.md](WORD-PRINT-OPTION-DFM.md) موجود است. از ادعای استخراج ZIP از سمت GitHub خودداری کن. ZIP و فایل‌های گزارش در مخزن قرار دارند، اما محتوای باینری ZIP از طریق نمایشگر متنی GitHub تحلیل نشده است.


- فرم `TfrmGScanPreview` نیز از مسیر `analysis-input/RCDATA_TFRMGSCANPREVIEW_13.bin` دریافت و decode شد: 25 component، PaintBox، ابزارهای rotate/crop/flip، انتخاب صفحه و گزینه‌های TIFF/JPEG استخراج شدند. جزئیات در [SCAN-PREVIEW-DFM.md](SCAN-PREVIEW-DFM.md) ثبت شده است. handlerهای پردازش تصویر هنوز از BPL استخراج نشده‌اند.


- فرم `TfrmImageTools` از مسیر `analysis-input/RCDATA_TFRMIMAGETOOLS_14.bin` دریافت و decode شد: مدیریت صفحات، ورود فایل/اسکن، ویرایش تصویر، زوم، قلم، Undo/Redo، درج تصاویر و تنظیمات چاپ استخراج شدند. کلاس‌های ImageEn در UI تأیید شدند. جزئیات در [IMAGE-TOOLS-DFM.md](IMAGE-TOOLS-DFM.md) است؛ رفتار handlerها هنوز باید از BPL بررسی شود.


## تکمیل تحلیل سه فرم اسکن و تصویر در 2026-11-10
- فایل `analysis-input/RCDATA_TFRMSIMPLEIMAGEEDITOR_18.bin` دریافت و decode شد: امضای `TPF0`، اندازه 11,451 بایت، 19 جزء و مصرف کامل stream بدون بایت باقی‌مانده.
- فرم `TfrmSimpleImageEditor` با عنوان «پیش‌نمایش اسکن» شناسایی شد. UI شامل PaintBox، انتخاب صفحه، Rotate، Crop، Flip افقی/عمودی، بازگشت به تصویر اصلی، گزینه TIFF/JPEG، گزینه ارسال هر صفحه به‌صورت فایل جدا و دکمه‌های تأیید/انصراف است.
- جزئیات و component inventory در [SIMPLE-IMAGE-EDITOR-DFM.md](SIMPLE-IMAGE-EDITOR-DFM.md) ثبت شد.
- مقایسه سه فرم در همان سند اضافه شد: `TfrmGScanPreview` برای پیش‌نمایش/اصلاح در مسیر اسکن، `TfrmSimpleImageEditor` برای ویرایش سبک پیش از تأیید/ارسال، و `TfrmImageTools` برای مدیریت گسترده صفحات، ورود فایل/اسکن، ویرایش و چاپ. این تقسیم نقش فعلاً برداشت مبتنی بر UI/نام‌هاست و باید با handlerها تأیید شود.
- هر سه فرم اکنون از Binary DFM با موفقیت decode شده‌اند؛ مرحله decode فرم‌های اصلی اسکن/تصویر تکمیل است. مرحله بعدی تحلیل کد handlerها در `EmwatMethods.bpl1` و استخراج قرارداد ورودی/خروجی این workflowهاست.

## نقطه ادامه به‌روز
گام بعد: ردیابی `doCommand` و Tagهای 11 تا 16 در `TfrmSimpleImageEditor`، سپس handlerهای Paint/Mouse و ثبت/ارسال؛ تطبیق آن‌ها با `TfrmGScanPreview` و `TfrmImageTools`. پس از آن specification قابل تست برای ماژول Native Linux نوشته شود. از decode دوباره این سه DFM خودداری کن مگر فایل یا شواهد جدیدی ارائه شود.


## تحلیل کد مسیرهای تصویر و اسکن در 2026-11-11

- ابزار ردیابی importها اصلاح شد تا thunkهای x86 را از روی PE import table/IAT شناسایی کند و سپس دستورهای CALL را فقط در محدوده توابع TD32 معتبر بررسی کند.
- اجرای Run 60 موفق شد: 110 import slot مرتبط با ImageGear/ImageEn، تعداد 101 thunk، نگاشت 8,411 تابع TD32 و بررسی 46,620 دستور CALL.
- مسیرهای اصلی ImageGear از روی کد تابعی تأیید شدند: Crop، RotateLeft/Right، FlipHorizontal/Vertical، SaveToFile و ScanToFile. جزئیات و آدرس‌ها در [GEAR-API-CALLS.md](GEAR-API-CALLS.md) و [IMAGE-CALL-GRAPH.md](IMAGE-CALL-GRAPH.md) ثبت شده‌اند.
- یک اشتباه مهم در helper-symbolهای قدیمی اصلاح شد: thunk `0x004AFEC8` برابر `IG_IP_rotate_multiple_90` و thunk `0x004AFED0` برابر `IG_IP_flip` است. از این پس PE import descriptor + IAT + thunk مبنای تشخیص نام API است.
- مشخص شد نام بعضی handlerهای GScan با API واقعی و مقدار direction هم‌خوانی ظاهری ندارد؛ بنابراین رفتار چرخش/برگرداندن را نباید فقط از نام دکمه یا مقدار عددی حدس زد. نسخه دقیق ImageGear و enumهای آن هنوز نامشخص‌اند.
- ImageEn نیز مسیرهای مجزایی در `TfrmImageTools` دارد: Acquire، LoadFromFileAuto، CropSel، RotateAndCrop، Flip، viewer zoom/coordinates و multi-image.
- وابستگی‌ها و روش پیاده‌سازی بومی در [Imaging-Dependency-Map.md](Imaging-Dependency-Map.md) به‌روزرسانی شده‌اند. هنوز هیچ backend بومی تصویر پیاده‌سازی نشده و parity تأیید نشده است.

### تحلیل تکمیلی Run 61 — 2026-11-11

- اجرای GitHub Actions با شناسه `43001855137` موفق شد؛ artifact `13846033438` دریافت و بررسی شد.
- متدهای `TfrmGScanPreview.SelectScanner`, `Scan`, `LoadImageToGearHandle`, `GetImagePageNumber`, `GetImgSize` و نیز `TGearImgProc.SelectScanner`, `SavePage`, `ReloadPage` با نگاشت segment-relative و confidence بالا به کد اجرایی وصل شدند.
- `TfrmGScanPreview.SelectScanner` مستقیماً `IG_save_JPEG_quality_set` و `IG_scan_pages` را فراخوانی می‌کند؛ در بدنه محدودشده فراخوانی مستقیمی به `IG_scan_source_select` دیده نشد.
- انتساب‌های قبلی `IG_scan_source_select` به `ShowCropRectangle` و `SetCurrentPage` مشکوک‌اند و تا بازبینی callsite/thunk نباید مبنای معماری اسکنر شوند.
- `Scan` و `SavePage` برای صفحات غیرجاری `IG_load_FD` و برای خروجی هر صفحه `IG_save_FD` را استفاده می‌کنند؛ هندل موقت با `IG_image_delete` آزاد می‌شود و هندل صفحه جاری حفظ می‌شود.
- جزئیات flagهای ذخیره و ABI فایل‌دسکریپتور هنوز به نسخه دقیق GEAR32PD یا آزمون کنترل‌شده نیاز دارند.
- جزئیات در [GEAR-API-CALLS.md](GEAR-API-CALLS.md) ثبت شده است.

### نقطه ادامه بعدی

1. اعتبارسنجی import thunkها و callsiteهای `IG_scan_source_select`؛ رفع انتساب‌های مشکوک.
2. استخراج و مستندسازی کامل قراردادهای callback/VMT در `TGearImgProc.SelectScanner` و کلاس/اینترفیس دستگاه.
3. شناسایی نسخه دقیق `GEAR32PD.DLL` و enum/prototypeهای همان نسخه؛ بدون این‌ها ABI فایل‌دسکریپتور را حدس نزن.
4. نوشتن specification قابل تست برای مدل تصویر بومی (pixel buffer، color model، DPI، چندصفحه‌ای، error/dirty/undo).
5. سپس پیاده‌سازی لایه‌ی SANE و مدل مستقل صفحه/تصویر؛ مسیر ImageEn باید جداگانه حفظ شود.


## Scanner interface dispatch analysis — 2026-11-11

- Run 61 artifact was unpacked and its bounded target disassembly inspected directly.
- `TfrmGScanPreview.SelectScanner` and `TGearImgProc.SelectScanner` are confirmed as distinct orchestration paths. The former sets JPEG quality, prepares an output path, invokes `IG_scan_pages` in two branches with distinct raw integer arguments, passes callback/context values through a helper, and validates the active image handle. The numeric values are not semantically decoded.
- The latter uses an interface-like object at `[self+0x28]`, dispatches through VTable offsets `+0x0C` and `+4`, stores the `IG_scan_pages` result at `[self+0x4C]`, and invokes further virtual callbacks including a dynamically obtained object's slot `+0x13C`. Method names and status meanings remain unresolved.
- Neither bounded SelectScanner body directly calls `IG_scan_source_select`; prior static caller attribution to `ShowCropRectangle` and `SetCurrentPage` remains untrusted pending raw callsite/thunk validation.
- Added [SCANNER-INTERFACE-ANALYSIS.md](SCANNER-INTERFACE-ANALYSIS.md) with evidence, confidence boundaries, a proposed native SANE-facing contract, and the next reverse-engineering tasks.
- No native scanner backend is claimed or implemented at this stage.

### Immediate next work

1. Resolve the runtime type and population path of `[TGearImgProc+0x28]` using constructor writes, RTTI and cross-references.
2. Disassemble helpers `0x004EF048`, `0x004EF1DC`, `0x004049CC`, and `0x0061D100`.
3. Revalidate `IG_scan_source_select` raw callsites and import thunk targets.
4. Identify the exact deployed `GEAR32PD.DLL` version before assigning meanings to scanner constants or implementing an ABI.

## Run 62 — scanner interface identity correction (2026-11-11)

- Run 62 (`43002726572`, artifact `13846956913`) succeeded. Four target-address traces exposed important symbol identities: `0x004EF048` = `TGearImgProc.GetEditorModalResult`; `0x004EF1DC` = `TGearImgProc.LoadPage`; `0x004049CC` = VCL `TWinControl.GetHandle`; `0x0061D100` = `TfrmGScanPreview.GetImagePageNumber`.
- Major correction: `[TGearImgProc+0x28]` is not a scanner/provider object. `SetEditorForm`'s TD32 signature explicitly accepts `DelphiInterface<IIPEditor>` and stores it at `+0x28`. RTTI confirms IID `7834c511-9078-411c-ab08-8b15ef1fd700`, implemented by `TfrmSimpleImageEditor` (VMT `0x004F046C`, interface offset `0x430`).
- The interface's `+0x0C` method is `TfrmSimpleImageEditor.GetModalRresult`; `+0x10` is `Hello`; `+0x14` is `Initial`; `+0x18` maps to `btnRegisterClick`. Thus the earlier interpretation of these virtual calls as scanner-provider dispatch was wrong and has been corrected in `SCANNER-INTERFACE-ANALYSIS.md`.
- Consequence: `TGearImgProc.SelectScanner` coordinates with the registered image editor while calling `IG_scan_pages`; the actual scanner device/provider selection path remains to be located independently. Do not design SANE around `[self+0x28]`.
- Next: trace `IIPEditor` registration/lifetime and the object passed through the `TGearImgProc` VMT slot at `+0` into `IG_scan_pages`; separately locate the true scanner source/device selection path.

## Run 63 — شناسایی اسلات صفر VMT در 2026-11-11

- دو اجرای قبلی (`43003809774` و `43003826485`) موفق شدند و هر دو artifact بررسی شد.
- VMT کلاس `TGearImgProc` در `0x004EE074` بررسی شد: اسلات `+0` = `HasError` در `0x004EF1C4`؛ اسلات `+4` = `CheckOutputParameter` در `0x004EEB60`؛ اسلات `+8` = `SelectScanner` در `0x004EF9CC`.
- در `SelectScanner` مقدار بازگشتی اسلات `+0` مستقیماً به‌عنوان یکی از آرگومان‌های `IG_scan_pages` push می‌شود. بدنه `HasError` فیلد `[self+0x24]` را بررسی می‌کند و در صورت غیرتهی بودن، متد VTable `+0x0C` شیء ذخیره‌شده در آن را صدا می‌زند.
- بنابراین `[self+0x24]` یک مرجع مستقل و هنوز ناشناخته است؛ نباید آن را با `IIPEditor` تأییدشده در `[self+0x28]` یکی دانست.
- workflow گسترش یافت تا constructor، `HasError`، `GetParentHandle`، `ShowEditor`، `SetCurrentPage` و `TfrmGScanPreview.ShowCropRectangle` را نیز در CI ردیابی کند.
- جزئیات و مرز اطمینان در [SCANNER-INTERFACE-ANALYSIS.md](SCANNER-INTERFACE-ANALYSIS.md) ثبت شد. هنوز هیچ backend اسکنر بومی پیاده‌سازی یا ادعای تکمیل نشده است.

### Run 77 — بازیابی ترتیب آرگومان‌های IG_scan_pages

- بدنه کامل `TGearImgProc.SelectScanner` در `0x004EF9CC` ترتیب چهار آرگومان فراخوانی `IG_scan_pages` در `0x004EFA96` را مشخص می‌کند.
- آرگومان اول HWND است؛ از slot مجازی +0x0C رابط IIPEditor در فیلد +0x24 به دست می‌آید.
- آرگومان دوم مقدار path-like است که از slot +0x0C آبجکت جداگانه +0x28 گرفته و از helper رشته‌ای `0x004012E0` عبور می‌کند؛ نوع pointer و encoding هنوز مشخص نیست.
- آرگومان سوم کد فرمت خروجی است که mapper در `0x004EF048` تولید می‌کند؛ نام ثابت‌های فرمت هنوز ناشناخته است.
- آرگومان چهارم یک byte از `[EBP+8]` است که zero-extend می‌شود؛ احتمالاً flag مربوط به UI/control است، اما معنای دقیقش به caller وابسته است.
- مقدار برگشتی IG_scan_pages در `[TGearImgProc+0x4C]` ذخیره و سپس از مسیر CheckOutputParameter بررسی می‌شود.
- امضای TD32 برای SelectScanner پارامترها را جا انداخته است: در machine code، EDX به BL، ECX به selector byte و آرگومان stack در `[EBP+8]` خوانده می‌شود؛ مسیر داخلی از طریق VMT slot +8 با EDX=1 دوباره وارد همین تابع می‌شود. معنی دقیق flag و قرارداد caller هنوز نیازمند تأیید است.
- شش trace مربوط به اسلات‌های VMT والد فرضی در Run 76 کد اجرایی معتبر نشان ندادند؛ برای شناسایی کلاس والد استفاده نمی‌شوند.

### Run 78 — TScanCommand state-machine evidence (static trace)

- The TD32-derived class map identifies `TScanCommand` with candidate instance size `0x40`; its VMT candidate is not structurally valid, so virtual-slot mapping remains unresolved.
- `TScanCommand.DoRequest` writes byte field `[self+0x28]` with states `1`, `2`, and `3` along distinct request paths.
- `TScanCommand.HasError` first checks byte `[self+0x29]`; when enabled, it queries the object/interface stored at `[self+0x20]` (including virtual slot +0x10) and calls helper `0x004ECFC8`. It then writes state `2` when the nested error check is true, otherwise state `4`.
- Helper `0x004ECFC8` checks a non-null interface at `[object+0x10]`, calls the object's VMT slot +0x04 to obtain an output value, then passes that value to a Boolean helper. This is consistent with a nested error/output validation path, but exact interface and helper semantics are not named.
- The trace target used for `GetNextPage` began inside the procedure rather than at a verified entry boundary; no behavioral conclusion is drawn from that partial disassembly. Run 79 adds wider context traces around constructor, DoRequest, GetNextPage, and HasError.
- No SANE implementation or scanner ABI emulation has been added yet.

### گام بعدی
1. ردیابی همه writeها و lifetime شیء `[TGearImgProc+0x24]`.
2. بازسازی جداگانه ترتیب آرگومان‌های `IG_scan_pages`؛ بدون حدس درباره prototype یا enumها.
3. بازبینی واقعی callsiteهای `IG_scan_source_select` در دو مسیر `SetCurrentPage` و `ShowCropRectangle`.


## Run 64 — تشخیص مقدار عبوری از HasError

- VMT اسلات صفر TGearImgProc به HasError در 0x004EF1C4 می‌رسد؛ این متد در صورت تهی بودن فیلد +0x24 مقدار صفر برمی‌گرداند و در غیر این صورت متد +0x0C شیء رابط ذخیره‌شده در آن فیلد را فراخوانی کرده و نتیجه را بدون تغییر برمی‌گرداند.
- در SelectScanner مقدار برگشتی HasError دقیقاً به‌عنوان یکی از آرگومان‌های IG_scan_pages push می‌شود. بنابراین این مقدار یک callback نیست؛ خروجی یک interface method ناشناخته است.
- فیلد +0x24 مستقل از IIPEditor تأییدشده در +0x28 است. نوع، محل مقداردهی و معنای خروجی آن هنوز مشخص نیست.
- آدرس GetParentHandle در workflow اصلاح شد: آدرس درست 0x004EF1B4 است، نه 0x004EE1B4.
- تحلیل هنوز ایستا است؛ prototype دقیق GEAR و معنی آرگومان‌ها بدون نسخه دقیق DLL/SDK قابل اعلام نیست.

### Run 68 — اصلاح تحلیل interface و VMT

- اجرای Run 68 (43005618825) موفق شد؛ artifact 13847708592 بررسی شد.
- VMT کلاس TGearImgProc تأیید می‌کند: +0x00=HasError، +0x04=CheckOutputParameter و +0x08=SelectScanner.
- HasError فیلد +0x24 را می‌خواند و در صورت غیرتهی بودن، متد +0x0C شیء ذخیره‌شده را فراخوانی می‌کند. نتیجه آن در آرگومان‌های IG_scan_pages مصرف می‌شود؛ نوع شیء هنوز مشخص نیست.
- بدنه TfrmSimpleImageEditor.GetModalRresult به vcl230.bpl!TWinControl.GetHandle می‌رسد؛ بنابراین نباید صرفاً از روی نام متد نتیجه گرفت که ModalResult برمی‌گرداند.
- Initial پردازشگر را در فیلد +0x408 ویرایشگر ذخیره می‌کند. همچنین مشخص شد SetEditorForm از VTable رابط IIPEditor در offset +0x20 هم استفاده می‌کند؛ dump قبلی فقط تا +0x18 را نشان می‌داد.
- ابزارها اصلاح شدند تا ۱۲ slot از VTable رابط و VMT کلاس TfrmScanError را بررسی کنند و بدنه متدهای مرتبط TGearImgProc را کامل‌تر disassemble کنند.

گام بعد: شناسایی slot +0x20 رابط IIPEditor، بررسی VMT فرم TfrmScanError و تعیین دقیق آرگومان‌های IG_scan_pages بدون حدس درباره ABI.


## Run 69 — اصلاح نسبت‌دادن IIPEditor به فیلدهای TGearImgProc

- تحلیل کامل ShowEditor نشان داد آرگومان EDX در offset +0x28 ذخیره می‌شود و سپس متدهای مجازی +0x04 و سایر slotها روی همان شیء فراخوانی می‌شوند.
- SetEditorForm با امضای DelphiInterface<IIPEditor>، آرگومان خود را در offset +0x34 ذخیره می‌کند؛ بنابراین نتیجه قبلی که +0x28 را IIPEditor می‌دانستیم پس گرفته شد.
- SelectScanner نیز +0x34 را صفر می‌کند و سپس روی شیء +0x28 متدهای VTable +0x0C و +0x04 را اجرا می‌کند. پس dispatchهای آن مسیر متعلق به IIPEditor نیستند.
- RTTI مربوط به IIPEditor و پیاده‌سازی آن توسط TfrmSimpleImageEditor همچنان معتبر است؛ فقط انتساب فیلد +0x28 به آن interface اشتباه بود.
- برای حل تعارض، CI اکنون تمام referenceهای displacementهای +0x28 و +0x34 را استخراج می‌کند و TImageProcessor را هم در کشف VMT بررسی می‌کند. SavePage نیز +0x34 را در مقایسه عددی می‌خواند؛ پس معنای نهایی این فیلد تا تکمیل cross-referenceها قطعی اعلام نمی‌شود.

گام بعد: شناسایی کلاس شیء +0x28، callerهای ShowEditor، و حل lifecycle/نوع فیلد +0x34.


## Run 70 — تأیید فراخوانی‌های واقعی IG_scan_source_select

- artifact اجرای 43006403083 نشان داد دو callsite مورد اختلاف واقعاً به thunk تابع IG_scan_source_select در 0x004AFF28 و IAT برابر 0x00630CE8 می‌رسند.
- در TfrmGScanPreview.ShowCropRectangle (ورودی صحیح 0x0061E3C8)، Handle پنجره از TWinControl.GetHandle گرفته و به IG_scan_source_select داده می‌شود. آدرس قبلی 0x0061D3C8 اشتباه بود و workflow اصلاح شد.
- در TGearImgProc.SetCurrentPage، خروجی VMT slot +0 یعنی HasError به IG_scan_source_select داده می‌شود.
- بنابراین دو مسیر انتخاب منبع اسکنر تأیید شدند: یکی با HWND فرم و دیگری با خروجی dispatch داخلی Gear. معنی دقیق آرگومان دوم تا بازیابی prototype نسخه دقیق GEAR32PD مشخص نیست.

گام بعد: شناسایی شیء +0x28، تحلیل helperهای 0x004F0258 و 0x0045574C و بازیابی ABI واقعی IG_scan_source_select.


## Run 71 — اصلاح نقشه فیلدهای Gear و تشخیص mapper وضعیت

- اسکن کامل فیلدها نشان داد +0x34 وضعیت صفحه جاری است: تابع 0x004EFF94 ورودی را با 1 و مقدار +0x30 مقایسه می‌کند و در +0x34 ذخیره می‌کند؛ SavePage و ReNewPageCount نیز آن را می‌خوانند.
- بنابراین فرض Run 69 که +0x34 محل ذخیره IIPEditor است پس گرفته شد. نام/امضای TD32 برای 0x004EFF94 با رفتار machine code سازگار نیست و تا بررسی callerها قابل اتکا نیست.
- +0x30 به احتمال زیاد تعداد/حداکثر صفحات است. +0x28 شیء پردازشگر/زمینه‌ای است که ShowEditor آن را مقداردهی می‌کند و SelectScanner از slotهای +0x0C و +0x04 آن استفاده می‌کند؛ کلاس runtime هنوز مشخص نیست. VMT scan برای TImageProcessor در همین BPL کاندیدایی پیدا نکرد.
- 0x004EF048 با وجود نام TD32 به‌عنوان GetEditorModalResult، در واقع DL را به ثابت‌های 0، 0x80028، 0x15 و 2 نگاشت می‌کند و برای سایر مقادیر صفر می‌دهد؛ این تابع مستقیماً ModalResult یا IIPEditor را نمی‌خواند.
- اسکن‌های جدید +0x30 و +0x38 و disassembly کامل ReNewPageCount و SaveCPinMultiPageFile به CI اضافه شدند.

گام بعد: پیدا کردن callerهای 0x004EFF94، تعیین نوع واقعی شیء +0x28 و تحلیل helperهای 0x004ECF30 و 0x004F0258.


## Run 72 — callerها، شیء پردازشگر و page setter

- اجرای 43007155812 موفق شد و گزارش callerها نشان داد 0x004EFF94 در چهار مسیر با عدد صفحه فراخوانی می‌شود: SaveCPinMultiPageFile، Flip، TfrmSimpleImageEditor.doCommand و Finalization. بنابراین امضای TD32 که آن را DelphiInterface<IIPEditor> نشان می‌دهد با ABI واقعی سازگار نیست؛ رفتار کد یک setter/update صفحه است.
- بدنه 0x004EFF94 ورودی را بین 1 و [self+0x30] محدود می‌کند، در +0x34 ذخیره می‌کند و سپس متد +0x20 شیء +0x28 را صدا می‌زند.
- شیء +0x28 یک object دارای VMT و lifecycle است؛ در SaveCPinMultiPageFile متد +0x1C آن اجرا و سپس reference آزاد/جایگزین می‌شود. TImageProcessor یک سرنخ از signatureهاست، ولی VMT محلی آن در این BPL پیدا نشد.
- helper 0x004ECF30 فقط byte فیلد +4 شیء را برمی‌گرداند. تابع 0x004EF048 نیز DL را به ثابت‌های status نگاشت می‌کند و ModalResult را نمی‌خواند.
- +0x30 تعداد صفحات و +0x34 صفحه جاری هستند؛ +0x38 مقدار string/object-like دریافت‌شده از متدهای +0x28 است.
- ابزار جدید trace_td32_callers.py اضافه شد و callsiteهای مستقیم 0x004EFF94 و helperهای مهم را در CI استخراج می‌کند.

گام بعد: تعیین parent VMT در 0x004EDE18، گسترش disassembly helperهای 0x004F0258 و 0x004ECF38، و شناسایی slot +0x20 و داده +0x38.


## Run 73 — مسیر NotifyEditor و فیلد مسیر خروجی

- 0x004EF240 به‌طور قطعی TGearImgProc.NotifyEditor است، نه helper ناشناس. ReNewPageCount و setter صفحه آن را با مقدار +0x34 صدا می‌زنند.
- NotifyEditor handle تصویر در +0x10 را اعتبارسنجی می‌کند، مقدار path/string-like از +0x38 می‌گیرد و دو بار IG_save_FD را از thunk 0x004AFE98 فراخوانی می‌کند؛ سپس CheckOutputParameter را بررسی می‌کند، dirty flag را پاک می‌کند و ReloadPage/GetImageResolution را اجرا می‌کند.
- +0x38 به احتمال زیاد مسیر فایل/خروجی است و در page setter از VTable +0x20 شیء +0x28 مقدار می‌گیرد. نوع دقیق string و قرارداد FD هنوز مشخص نیست.
- helper 0x004ECF38 مقدار فیلد +8 شیء +0x28 را از طریق helper 0x00401240 به خروجی کپی می‌کند؛ helper 0x004ECF30 هم byte فیلد +4 را می‌خواند.
- بررسی header آدرس parent VMT در 0x004EDE18 با offsetهای استاندارد Delphi سازگار نبود؛ تا تحلیل بدنه slotها، آن را TImageProcessor نام‌گذاری نمی‌کنیم.

گام بعد: تحلیل بدنه slotهای parent در 0x004EDE18، شناسایی +0x28 و تعیین قرارداد IG_save_FD و path.


## Run 74 — اصلاح توابع FD و تشخیص فرمت خروجی

- thunk 0x004AFE98 تابع IG_load_FD است (IAT 0x00630D2C)؛ thunk 0x004AFEA0 تابع IG_save_FD است (IAT 0x00630D28). برداشت قبلی Run 73 درباره IG_save_FD در NotifyEditor اصلاح شد.
- SavePage در 0x004EF60B با ترتیب آرگومان‌های IG_load_FD، صفحه را از file descriptor به HIGEAR موقت می‌خواند؛ سپس در 0x004EF64E همان صفحه را با IG_save_FD و format code ذخیره می‌کند.
- NotifyEditor دو بار IG_load_FD صدا می‌زند و خروجی را در [self+0x10] قرار می‌دهد؛ صفحه اول با EDX و بار دوم صفحه 1 خوانده می‌شود.
- فیلد +0x14 آرگومان پنجم IG_save_FD یعنی lFormatType است. تابع 0x004EF048 byte انتخاب‌شده را به format constant نگاشت می‌کند؛ نام TD32 آن GetEditorModalResult گمراه‌کننده است.
- +0x38 مقدار backing path/stream است که برای بازکردن file descriptor استفاده می‌شود. معماری EMWAT برای ویرایش چندصفحه‌ای از یک page store مبتنی بر descriptor استفاده می‌کند.
- امضای عمومی توابع با مستندات Accusoft برای ImageGear v18.7/v21 تطبیق دارد، اما نسخه دقیق GEAR32PD.DLL هنوز مشخص نیست.

گام بعد: تعیین file-open flags و نوع رشته +0x38، معنی format constantها و تحلیل parent slotها.


## Run 75 — آرگومان‌های واقعی مسیر اسکن و محدودیت VMT والد

اجرای workflow با شناسه 43008058751 موفق شد؛ artifact برابر 13850020148 است.

- در TfrmGScanPreview.SelectScanner، IG_scan_pages چهار مقدار می‌گیرد: HWND از TWinControl.GetHandle، رشته/مسیر از فیلد +0x458، یکی از ثابت‌های 0x28 یا 2 و مقدار 1.
- در TGearImgProc.SelectScanner منشأ چهار آرگومان متفاوت است: خروجی VMT slot +0 یعنی HasError، مقدار رشته‌ای از آبجکت +0x28 از طریق virtual +0x0C، خروجی mapper در 0x004EF048 و byte ورودی متد.
- خروجی IG_scan_pages در مسیر Gear داخل [self+0x4C] ذخیره می‌شود؛ در مسیر Preview بلافاصله مصرف نمی‌شود.
- مقدار HasError از interface ناشناخته در [self+0x24] و slot +0x0C آن می‌آید؛ فعلاً نباید آن را HWND یا شناسه دستگاه فرض کرد.
- امضای TD32 تابع @Gear@IG_scan_pages$qqsp6HWND__pxcuio است، اما تفاوت منشأ آرگومان اول بین دو caller هنوز با prototype دقیق GEAR32PD حل نشده است.
- دو callsite تأییدشده IG_scan_source_select نیز داده‌های متفاوت می‌فرستند: مسیر Preview یک HWND واقعی و مسیر Gear خروجی slot صفر VMT را.
- شش target اسلات والد در 0x004EDE18 به محدوده‌های TD32 قابل اتکا وصل نشدند و header استاندارد Delphi هم با این آدرس سازگار نیست؛ بنابراین هنوز نمی‌توان آن را TImageProcessor نامید.

### گام بعد
1. تمام writeها و referenceهای فیلد [TGearImgProc+0x24] را استخراج و منبع interface را پیدا کنیم.
2. نوع runtime شیء [TGearImgProc+0x28] را از constructor، setter و VMT معتبر شناسایی کنیم؛ نه از parent pointer فعلی.
3. نسخه دقیق GEAR32PD.DLL یا header/import library متناظر را پیدا کنیم تا ABI دو تابع اسکن قطعی شود.
4. تا آن زمان مقادیر عددی و نوع آرگومان‌ها را نام‌گذاری نکنیم؛ backend لینوکس همچنان مستقل و مبتنی بر SANE طراحی شود.


## Run 76 — شناسایی قطعی‌تر interface فیلد +0x24 و حل HWND

اجرای 43027580174 موفق شد؛ artifact برابر 13857623235 است.

- فیلد [TGearImgProc+0x24] همان interface از نوع IIPEditor است، نه interface خطا. تابع setter در 0x004F0084 آن را با helper مدیریت interface مقداردهی می‌کند.
- در caller مربوط به TScanCommand.$bdtr، مقدار EDX با offset برابر 0x430 تنظیم و به setter داده می‌شود. این offset دقیقاً با IOffset رابط IIPEditor در TfrmSimpleImageEditor برابر است.
- caller دوم در 0x004F1151 مقدار nil را به همان setter می‌دهد؛ این با پاک‌کردن/release رابط هنگام teardown سازگار است.
- IID رابط 7834c511-9078-411c-ab08-8b15ef1fd700 و VTable آن 0x004F03D4 است؛ پیاده‌سازی در TfrmSimpleImageEditor با offset برابر 0x430 ثبت شده.
- TGearImgProc.HasError در واقع slot +0x0C رابط IIPEditor را صدا می‌زند. پیاده‌سازی متناظر در 0x004F1158 تابع TWinControl.GetHandle را اجرا و مقدار HWND را برمی‌گرداند.
- بنابراین مقدار ارسالی از Gear به IG_scan_pages و IG_scan_source_select هم HWND است؛ تفاوت قبلی فقط تفاوت مسیر دستیابی به handle بود، نه تفاوت نوع مقدار.
- فیلد +0x28 همچنان یک آبجکت جداگانه با VMT و stateهای +4/+8 است و کلاس runtime آن هنوز مشخص نشده.
- RTTI اسمی IImageProcessor هم پیدا شد، اما GUID آن صفر است و در این BPL پیاده‌سازی متناظری پیدا نشد؛ این یافته دلیل نمی‌شود +0x24 را IImageProcessor بدانیم.

### گام بعد
1. شناسایی runtime class و قرارداد virtualهای آبجکت مستقل +0x28.
2. تعیین رفتار واقعی slotهای IIPEditor در +0x10، +0x14 و +0x18؛ نام‌های TD32 برای wrapperهای Gear قابل اتکا نیستند.
3. بازیابی prototype کامل IG_scan_pages و IG_scan_source_select؛ HWND اکنون مشخص است اما آرگومان‌های دیگر و ثابت‌ها هنوز نه.
4. ادامه طراحی backend لینوکس با SANE، بدون تقلید layout و ABI ویندوز.


## Run 77 — منشأ context پردازش صفحه

در artifact اجرای موفق 43029566665 مشخص شد:

- فیلد TScanCommand+0x20 در DoRequest خوانده و به TGearImgProc.ShowEditor داده می‌شود.
- همین فیلد در GetNextPage در سه مسیر (0x004F2637، 0x004F268B و 0x004F26A9) نوشته می‌شود؛ هر سه مقدار از helper/factory در 0x004EC8B4 می‌آیند.
- ShowEditor همان pointer را در TGearImgProc+0x28 ذخیره می‌کند و از virtual slot +4 آن یک رشته می‌گیرد که به +0x38 منتقل می‌شود.
- TScanCommand.HasError از virtual slot +0x10 همین آبجکت استفاده و سپس helper 0x004ECFC8 را صدا می‌زند؛ بر اساس نتیجه، status byte در TScanCommand+0x28 را به 2 یا 4 تغییر می‌دهد.
- پس TGearImgProc+0x28 یک processing context واقعی و تولیدشده برای request/page است؛ هنوز نباید آن را با IIPEditor در +0x24 یا با interface اسمی IImageProcessor یکی دانست.

اجرای بعدی 43030170561 برای بررسی کامل GetNextPage و بدنه helperهای 0x004EC8B4 و 0x004ECFC8 اضافه شده است.


## Run 79 — بازیابی contextهای سازنده و چرخه صفحه

اجرای 43032078996 موفق شد و چهار فایل context اکنون در Artifact موجودند. نتایج قابل اتکا:

- سازنده در 0x004F21F0 ابتدا constructor پایه را از طریق 0x004EEDB4 اجرا می‌کند و نتیجه را در [self+0x04] می‌گذارد؛ سپس interface جداگانه‌ای را با 0x00404D5C می‌سازد و در +0x24 ذخیره می‌کند. این بخش با مالکیت IIPEditor در +0x24 سازگار است.
- سازنده یک شیء دیگر را از 0x004EB7F4 دریافت و در +0x34 قرار می‌دهد و سپس virtual slot +0xB8 آن را فراخوانی می‌کند؛ کلاس و معنای دقیق این dependency هنوز مشخص نیست.
- بخش معتبر GetNextPage در محدوده 0x004F25CC به بعد نشان می‌دهد state دو بایتی از +0x1D و +0x1E نگهداری می‌شود. تابع 0x004EC8B4 با دو byte mode/selector و یک مقدار موقت، context جدید می‌سازد و خروجی در +0x20 قرار می‌گیرد.
- در مسیر عادی، helper با mode byte فعلی و byte همراه آن فراخوانی می‌شود؛ در مسیر جایگزین، اگر mode برابر 2 باشد، mode ورودی به factory برابر 3 می‌شود. در مسیرهای دیگر، mode فعلی حفظ می‌شود.
- helper 0x004F29E0 از طریق 0x00401398 با پارامتر ثابت 1 اجرا می‌شود؛ اگر نتیجه مثبت باشد، byte وضعیت +0x1E به 2 تغییر می‌کند. سپس HasError فراخوانی می‌شود.
- بلوک بعدی، context را مجدداً از روی pair بایت‌های +0x1D/+0x1E می‌سازد؛ بنابراین context +0x20 به وضعیت جاری صفحه وابسته است و یک شیء ثابت برای کل عمر ScanCommand نیست.

محدودیت: traceهای نقطه‌ای 0x004F2250 و 0x004F25C0 وسط دستور/بلوک افتاده‌اند و trace HasError از 0x004F2A80 نیز هم‌ترازی کد ندارد. بنابراین از آن‌ها برای نام‌گذاری متد یا نتیجه‌گیری درباره بدنه کامل استفاده نمی‌کنیم. اجرای بعدی، traceهای هم‌تراز از 0x004F2274، 0x004F25CC، 0x004F26F2، 0x004F27C4 و 0x004F29E0 را اضافه کرده است.


## Run 80 — تحلیل dispatch چرخه ScanCommand (2026-11-11)

اجرای 43033266952 موفق شد و artifact 13861452924 بررسی شد.

- trace هم‌تراز GetNextPage از 0x004F25CC نشان می‌دهد پیش از ساخت context، یک loop مقدار byte وضعیت [self+0x1D] را از چهار ورودی/مقدار مقایسه‌شده انتخاب می‌کند؛ اگر match پیدا شود index در فیلد ذخیره می‌شود. بنابراین +0x1D صرفاً یک mode ثابت نیست و در این بخش از انتخاب بین چهار گزینه نیز استفاده می‌شود.
- پس از آن helper فراخوانی‌شده از طریق 0x00401398 با آرگومان ثابت 1 نتیجه عددی می‌دهد؛ نتیجه مثبت byte دوم [self+0x1E] را 2 می‌کند. سپس context با 0x004EC8B4 از هر دو byte ساخته و در +0x20 قرار می‌گیرد و HasError اجرا می‌شود.
- در continuation، pointer context از +0x20 به تابع 0x004F0174 داده می‌شود؛ سپس word حاصل از دو state byte در فیلدهای +0x55 و +0x57 شیء پایه [self+0x04] کپی می‌شود. پس از آن توابع 0x004F22E4 و 0x004F2B18 فراخوانی می‌شوند.
- dispatch بعدی بر اساس status byte [self+0x28] مقادیر 1 تا 4 را از هم جدا می‌کند. در شاخه status=2، context فعلی +0x20 از طریق 0x004ECE2C خوانده و مقدار خروجی به helper 0x004735C4 داده می‌شود. شاخه‌های 3 و 4 مسیرهای آماده‌سازی جدا دارند.
- مسیر dispatch سپس روی dependency ذخیره‌شده در +0x34 virtual slotهای +0xB8 و +0xB4 را اجرا می‌کند و روی context +0x20 نیز slotهای +0x08 و متدهای کمکی دیگر را فراخوانی می‌کند. نام و قرارداد این virtualها هنوز حل نشده است.
- traceهای 0x004F2274 و 0x004F29E0 هیچ دستور معتبری decode نکردند؛ بنابراین این دو آدرس را entry قطعی DoRequest یا تابع مستقل request-helper تلقی نمی‌کنیم. trace قدیمی 0x004F2250 نیز وسط دستور/epilogue افتاده است.
- trace dispatch در 0x004F27C4 فقط تا 0x004F28C0 ادامه دارد؛ برای تکمیل شاخه‌ها باید ادامه بدنه و targetهای 0x004F22E4 و 0x004F2B18 بررسی شوند.

گام بعد: trace از 0x004F2278 و 0x004F28C0، سپس تحلیل 0x004F22E4 و 0x004F2B18 و تطبیق statusها با DoRequest/HasError. تا زمان بازیابی entry واقعی، نام‌گذاری متد DoRequest و helper در محدوده‌های مبهم متوقف بماند.


## به‌روزرسانی مسیر اسکن — Run 81 (2026-11-12)
- اجرای `43036386819` موفق شد و Traceهای ادامه‌ی `0x004F22E4`، انتهای helper و cleanup بررسی شدند.
- مسیر جدید نشان می‌دهد helper در بعضی وضعیت‌ها callback record می‌سازد، آن را از `0x0044ABE4` عبور می‌دهد و اگر نتیجه 6 باشد، context را از VMT slot `+0x1C` ادامه داده و `0x004F22E4` را دوباره اجرا می‌کند؛ در غیر این صورت status داخلی را 3 می‌گذارد.
- تحلیل با جزئیات و مرزبندی اطمینان در [SCANNER-INTERFACE-ANALYSIS.md](SCANNER-INTERFACE-ANALYSIS.md) ثبت شد.
- هنوز معنای callbackها، layout رکورد و قرارداد `0x0044ABE4` مشخص نیست؛ بنابراین این بخش را نباید به‌عنوان ABI قطعی اسکنر تفسیر کرد.
- گام بعد: trace کردن callbackهای `0x004F2454` و `0x004F2474`، رکورد `0x004F2490`، dispatcher `0x0044ABE4` و مسیر exception/finally.


## اصلاح تحلیل Run 81 — شناسایی RemoveTempFiles (2026-11-12)
- نماد TD32 مشخص کرد آدرس `0x0044ABE4` تابع `Emwat.Sys.RemoveTempFiles` است، نه dispatcher مربوط به callback اسکن.
- همین تابع از `TfrmSimpleImageEditor.ToggleCropMode` نیز فراخوانی می‌شود؛ بنابراین utility مشترکی است، اما صرف نام نماد برای اثبات حذف فایل کافی نیست.
- آدرس‌های `0x004F2454`، `0x004F2474` و `0x004F2490` disassembly معتبر x86 ندارند و نباید callback یا ABI اجرایی تلقی شوند.
- در مسیر ScanCommand فقط می‌توان گفت نتیجه تابع با عدد 6 مقایسه می‌شود؛ در صورت برابری، context از VMT slot `+0x1C` ادامه می‌یابد و helper `0x004F22E4` دوباره اجرا می‌شود. معنای عدد 6 هنوز نامشخص است.
- Traceهای بعدی برای شناسایی قرارداد آرگومان‌ها و helperهای داخلی RemoveTempFiles به workflow افزوده شدند.


## Run 82 — بازبینی RemoveTempFiles (2026-11-12)
- اجرای `43157168446` موفق شد؛ artifact `13916526235` بررسی شد.
- بدنه `0x0044ABE4` به‌جای API حذف فایلِ قابل مشاهده، componentهای یک object را با `TComponent.GetComponentCount/GetComponent` پیمایش می‌کند؛ Run 83 نشان داد که componentهای منطبق با یک کلاس global، متن می‌گیرند و virtual slot `+0x13C` اجرا می‌شود.
- در همان مسیر، thunkهای `0x00404894` و `0x00404E34` به `TControl.SetText` و `TCustomForm.SetFormStyle` resolve شدند؛ virtual slotهای `+0x94` و `+0x13C` نیز اجرا می‌شوند.
- بنابراین برداشت «قطعاً پاک‌سازی فایل موقت» فعلاً تأیید نشده است؛ ممکن است نام TD32 قدیمی/گمراه‌کننده باشد یا عملیات نهایی از virtual/helper خارج از image انجام شود.
- در caller اسکن، return value با 6 مقایسه می‌شود؛ معنای آن همچنان نامشخص است.
- traceهای تکمیلی انتهای تابع، helperهای string/array/exception و callerهای دیگر به workflow افزوده شدند.
- جزئیات و محدودیت استنباط در [SCANNER-INTERFACE-ANALYSIS.md](SCANNER-INTERFACE-ANALYSIS.md) ثبت شد.


## Run 83 — قرارداد داخلی helper عمومی VCL (2026-11-12)
- اجرای `43158235892` موفق شد؛ artifact `13917012048` بررسی شد.
- `0x0044ABE4` componentهای یک container را با `TComponent.GetComponentCount/GetComponent` پیمایش می‌کند؛ برای هر مورد، `System.IsClass` را با کلاس global در `0x62FE28` اجرا می‌کند.
- در صورت match، مقدار open-array را به `TControl.SetText` می‌دهد؛ سپس `TCustomForm.SetFormStyle(3)` و virtual slot `+0x13C` اجرا می‌شوند. مقدار خروجی از همین virtual slot می‌آید.
- helperهای RTL به `System.IsClass`، `TObject.Free`، `System.AddRefArray` و `System.UStrAddRef` resolve شدند.
- بنابراین نام TD32 یعنی `RemoveTempFiles` رفتار واقعی تابع را به‌تنهایی توصیف نمی‌کند؛ حذف فایل از بدنه قابل مشاهده اثبات نشده است.
- در ScanCommand، مقدار 6 با نتیجه virtual slot مقایسه می‌شود؛ معنای این status و کلاس هدف هنوز نامشخص است.
- جزئیات در [SCANNER-INTERFACE-ANALYSIS.md](SCANNER-INTERFACE-ANALYSIS.md) ثبت شد.


## Run 84 — شناسایی helper پنجرهٔ محاوره‌ای (2026-11-12)
- اجرای `43159971265` موفق شد؛ artifact `13917817103` بررسی شد.
- تفسیر قبلی TD32 برای `0x0044ABE4` اصلاح شد: این تابع فایل موقت حذف نمی‌کند؛ componentهای فرم را می‌گردد، متن برخی کنترل‌ها را تنظیم می‌کند، `TCustomForm.SetFormStyle(3)` را اجرا می‌کند و از virtual slot `+0x13C` نتیجهٔ modal می‌گیرد.
- importهای VCL وجود `TCustomForm.ShowModal` را تأیید می‌کنند؛ slot مذکور با اطمینان بالا همان ShowModal است. `3=fsStayOnTop` و `6=mrYes`.
- callerهای Scan Error، ToggleCropMode و ScanCommand از انتخاب Yes برای تغییر state/ادامهٔ مسیر استفاده می‌کنند.
- در پورت Linux این بخش باید به dialog abstraction تبدیل شود، نه فایل‌پاک‌کن.
- جزئیات و شواهد در [SCANNER-INTERFACE-ANALYSIS.md](SCANNER-INTERFACE-ANALYSIS.md) ثبت شد.


## Run 85 — جداسازی callerهای اسکن و helperهای عمومی (2026-11-12)
- اجرای `43160920858` موفق شد؛ artifact `13917599363` بررسی شد.
- helper عمومی با `System.IsClass`، `TComponent.GetComponentCount/GetComponent`، `TControl.SetText` و `TCustomForm.SetFormStyle` کار می‌کند؛ کلاس مرجع runtime در `0x0023D27E` خارج از image است و هنوز نامش معلوم نیست.
- callerهای جدید modal در Scan Error، ToggleCropMode و TIFF بررسی شدند؛ نتیجهٔ 6 در callerهای مشخص‌شده به‌عنوان شرط ادامه/تغییر state مصرف می‌شود.
- نقشهٔ importها دو caller مستقل برای `IG_scan_pages` نشان می‌دهد: Preview و GearImgProc. همچنین دو caller مستقل `IG_scan_source_select` در `ShowCropRectangle` و `SetCurrentPage` ثبت شده‌اند.
- گام بعدی: trace آرگومان‌ها و stateهای هر چهار callsite اسکن، بدون فرض یکسان بودن دو مسیر.


## Run 86 — call graph قطعی اسکنر
- اجرای `43162207819` موفق شد و artifact بررسی شد.
- دو orchestrator مستقل برای `IG_scan_pages` شناسایی شد: Preview (دو call) و GearImgProc (یک call).
- دو callsite مستقل `IG_scan_source_select` در Preview.ShowCropRectangle و GearImgProc.SetCurrentPage تأیید شد.
- گام بعدی: trace کامل بدنهٔ متدهای `SelectScanner` و ثبت stack/arguments هر call، به‌خصوص دو فراخوانی Preview.


## Run 87 — استخراج state و چرخهٔ ذخیره/بارگذاری تصویر
- اجرای `43163883733` موفق شد؛ trace کامل متدهای GearImgProc بررسی شد.
- ShowEditor context را در +0x28 و backing path/descriptor را در +0x38 تنظیم می‌کند؛ +0x34 صفحهٔ فعال، +0x30 تعداد صفحات و +0x54 وضعیت dirty است.
- SetCurrentPage بازهٔ صفحه را اعتبارسنجی می‌کند، در صورت dirty بودن امکان SaveToFile را از طریق modal Yes می‌دهد، سپس context virtual +0x20 را برای صفحهٔ جدید فراخوانی و NotifyEditor را اجرا می‌کند.
- NotifyEditor با IG_load_FD صفحه را از backing descriptor به HIGEAR فعال reload می‌کند؛ SavePage روی همهٔ صفحات loop می‌زند و برای صفحات غیرفعال HIGEAR موقت می‌سازد؛ SaveToFile و ScanToFile دو مسیر جدا هستند.
- RotateLeft/Right dirty state را تغییر می‌دهند، اما عملیات pixel-level در helperهای خارجی/virtual انجام می‌شود و هنوز ABI آن‌ها مشخص نیست. نام قبلی Crop برای تابع 0x004EEDB4 تأیید نشد؛ بدنه بیشتر شبیه constructor یک context object است.
- تحلیل تفصیلی و مرزهای اطمینان در [SCANNER-INTERFACE-ANALYSIS.md](SCANNER-INTERFACE-ANALYSIS.md) ثبت شد.
- گام بعد: resolve کردن helperهای rotation و context، callerهای آن‌ها، و تابع‌های GEAR مربوط به save/load/scan؛ سپس تبدیل این یافته‌ها به قرارداد ماژول مستقل image document در Linux.


## Run 88 — تفکیک rotation و page refresh
- اجرای `43164659373` با موفقیت کامل شد؛ artifact `13919407916` بررسی شد.
- importهای مهم ImageGear به‌صورت قطعی‌تر به thunkها متصل شدند: `IG_image_delete`، `IG_image_is_valid`، `IG_IP_rotate_multiple_90`، `IG_image_dimensions_get` و `IG_page_count_get`.
- نکتهٔ اصلاحی: متد TD32 با نام `Rotate90` مستقیماً pixelها را rotate نمی‌کند؛ page count را از backing document می‌خواند و context virtual slot صفر را صدا می‌زند. چرخش واقعی در `RotateLeft` از طریق `IG_IP_rotate_multiple_90` انجام می‌شود و سپس ReloadPage/refresh resolution و dirty flag رخ می‌دهد.
- این تفکیک برای طراحی native مهم است: page/document refresh، pixel transform و lifecycle آزادسازی image handle باید APIهای جدا باشند.
- جزئیات و disassembly در [SCANNER-INTERFACE-ANALYSIS.md](SCANNER-INTERFACE-ANALYSIS.md) ثبت شد.
- گام بعد: تکمیل قرارداد dimensions/page-count/delete و context virtualها، سپس تثبیت مدل Document/Page/PixelBuffer و شروع پیاده‌سازی native.


## Run 89 — ImageGear lifecycle و قرارداد اولیهٔ Document/Page
- اجرای `43165458320` موفق شد؛ artifact `13919863021` بررسی شد.
- `IG_image_dimensions_get` در `ReloadPage` با HIGEAR و سه output pointer در offsetهای `+0x40`، `+0x3C` و `+0x44` فراخوانی می‌شود؛ معنای دقیق هر خروجی هنوز قطعی نیست.
- `IG_page_count_get` علاوه بر `Rotate90` در `SaveToFile` و مسیرهای Preview نیز استفاده می‌شود؛ بنابراین page count بخشی از metadata سند است، نه عملیات چرخش پیکسل.
- `IG_image_delete` در مسیرهای teardown/replacement در Preview و همچنین `NotifyEditor`، `PaintCanvas` و `SavePage` دیده می‌شود؛ این موضوع اهمیت lifecycle/ownership روشن را تأیید می‌کند.
- `IG_image_is_valid` پیش از چند عملیات reload، metadata، paint و save بررسی می‌شود.
- سند معماری اولیهٔ مستقل از ImageGear در [NATIVE-IMAGE-DOCUMENT-DESIGN.md](NATIVE-IMAGE-DOCUMENT-DESIGN.md) ایجاد شد؛ شامل Document/Page/PixelBuffer، مرز API، ownership، تست‌های parity و سؤال‌های باز.
- گام بعد: resolve کردن قرارداد سه خروجی dimensions و context virtualها؛ سپس ساخت اسکلت ماژول native و تست‌های واحد برای transformهای pixel بدون وابستگی به GEAR.

## پیاده‌سازی اولیه کشف اسکنر در Linux (2026-11-12)

- رابط مستقل ScannerBackend و ساختار ScannerDevice در `native/include/emwat/scanner.hpp` اضافه شد؛ لایه UI و مدل سند تصویر به API اختصاصی SANE وابسته نیستند.
- پیاده‌سازی SaneScannerBackend در `native/src/sane_scanner.cpp` از `sane_init`، `sane_get_devices` و `sane_exit` استفاده می‌کند و شناسه، سازنده، مدل و نوع دستگاه را برمی‌گرداند.
- چرخه عمر SANE در هر درخواست کشف دستگاه محدود و با mutex سریال شده است؛ خطاهای init و discovery به ScannerError تبدیل می‌شوند.
- تست قرارداد backend با fake backend اضافه شد. CI اکنون `libsane-dev` و `pkg-config` را نصب و کتابخانه SANE را در build لینک می‌کند.
- **محدودیت فعلی:** این milestone فقط کشف و فهرست‌کردن دستگاه‌هاست؛ هنوز تنظیم گزینه‌ها، شروع اسکن، خواندن فریم‌ها، لغو اسکن و تحویل صفحه به ImageDocument پیاده‌سازی نشده‌اند. این‌ها باید در گام بعد و با fake acquisition tests و تست سخت‌افزار واقعی اضافه شوند.

## دریافت اولین فریم و تنظیمات اسکن از SANE (2026-11-12)

- قرارداد `ScannerBackend` متد `scan_one(device_id, options)` دارد که یک `ImagePage` برمی‌گرداند و `get_capabilities(device_id)` قابلیت‌های هر دستگاه را گزارش می‌کند.
- قابلیت‌یابی، فهرست حالت‌های رنگ و منبع را از string-listهای SANE و رزولوشن را از range یا word-list descriptor استخراج می‌کند؛ گزینه‌های inactive یا غیرقابل تشخیص به‌عنوان قابلیت قابل انتخاب گزارش نمی‌شوند. `ScanOptions` سه تنظیم اختیاری دارد: رزولوشن برحسب DPI، حالت اسکن و منبع کاغذ.
- پیاده‌سازی SANE دستگاه را باز می‌کند، در صورت درخواست گزینه‌های `resolution`، `mode` و `source` را از طریق descriptorهای فعال و قابل تنظیم SANE اعمال می‌کند، سپس اسکن را شروع می‌کند، پارامترهای فریم را می‌خواند و داده‌ها را در بلوک‌های 64 KiB دریافت می‌کند.
- نام گزینه‌های SANE برای رزولوشن/حالت/منبع به‌ترتیب `resolution`، `mode` و `source` است؛ اگر دستگاه گزینه‌ای را ارائه نکند یا نوع/قابلیت آن ناسازگار باشد، درخواست با `ScannerError` روشن رد می‌شود. انتخاب مقادیر مجاز رشته‌ای و محدودیت‌های سخت‌افزاری نهایی به backend SANE واگذار می‌شود.
- خروجی فعلی محدود به Gray8 و RGB8 است؛ ابعاد متغیر، عمق‌های دیگر، فرمت‌های دیگر و فریم ناقص با خطای روشن رد می‌شوند.
- سقف حافظه هر اسکن 1 GiB است؛ طول داده دریافتی، stride و اندازه فریم بررسی می‌شوند. در خطاهای حین دریافت، اسکن لغو می‌شود و handle/session به‌صورت RAII بسته می‌شوند.
- تست fake backend اکنون مسیر قرارداد دریافت یک ImagePage و خطای اسکن را هم پوشش می‌دهد.
- **محدودیت‌های زمان ثبت این مرحله:** اسکن چندفریمی یا duplex، خطوط با ارتفاع نامعلوم، عمق 16-bit، lineart و لغو از UI هنوز پشتیبانی نمی‌شوند. DPI در مرحله بعد از اعمال تنظیمات از گزینه‌های فعال SANE خوانده می‌شود؛ مقدار درخواستی به‌عنوان DPI واقعی ثبت نمی‌شود.


## ثبت DPI واقعی خروجی اسکن (2026-11-12)

- پس از اعمال تنظیمات اختیاری و پیش از شروع فریم، backend مقدار واقعی گزینه‌های فعال SANE را با `SANE_ACTION_GET_VALUE` می‌خواند.
- در دستگاه‌هایی که `x-resolution` و `y-resolution` جدا دارند، هر محور جداگانه ثبت می‌شود؛ اگر فقط یکی قابل خواندن باشد همان مقدار برای هر دو محور استفاده می‌شود. در دستگاه‌های دارای گزینهٔ عمومی `resolution`، مقدار آن برای هر دو محور ثبت می‌شود.
- مقدار ناموجود، غیرفعال، نامعتبر یا غیرقابل خواندن به‌صورت `nullopt` باقی می‌ماند؛ DPI از مقدار درخواستی یا مقدار پیش‌فرض حدس زده نمی‌شود.
- تست قرارداد ScannerBackend ثبت DPI در `ImagePage` را پوشش می‌دهد. خواندن مقدار از دستگاه واقعی همچنان به سخت‌افزار/درایور SANE وابسته است.


## محدودسازی ورودی قابلیت‌های SANE (2026-11-12)

- خواندن فهرست قابلیت‌های driver محدود شد: حداکثر 256 مقدار رشته‌ای و حداکثر 256 نویسه برای هر مقدار پذیرفته می‌شود.
- word-list رزولوشن حداکثر تا 4096 ورودی بررسی می‌شود؛ مقادیر نامعتبر، غیرمثبت یا بزرگ‌تر از 100000 DPI کنار گذاشته می‌شوند.
- بازه رزولوشن نیز باید محدود، مثبت و حداکثر 100000 DPI باشد. مقادیر discrete مرتب و تکراری‌ها حذف می‌شوند.
- هدف، محدودکردن مصرف منابع و جلوگیری از انتشار داده‌های نامعتبر driver در لایه قابلیت‌هاست؛ این محدودیت‌ها جایگزین اعتبارسنجی نهایی خود backend نمی‌شوند.


## Run 90 — بازتعریف دامنه محصول بر اساس گردش‌کار واقعی الماس گام (2026-11-12)

- کاربر توضیح داد EMWAT در استفاده اصلی، سرویس/واسط محلی متصل به اتوماسیون تحت وب الماس گام است؛ هنگام ایجاد یا ویرایش نامه، Word را باز می‌کند، اطلاعات و قالب تنظیم‌شده در الماس گام (مانند موضوع، شماره، امضاکنندگان، سربرگ، لوگو، فونت، حاشیه و محل امضا) را در سند اعمال می‌کند و کاربر متن نامه را ویرایش می‌کند.
- طبق توضیح کاربر، پس از بستن Word فایل نهایی به الماس گام برمی‌گردد و ذخیره نهایی در خود الماس گام انجام می‌شود. جزئیات اینکه بدون Save نیز تغییرات ارسال می‌شوند، با قطعیت پایین‌تر بیان شده و باید با آزمایش کنترل‌شده تأیید شود.
- کاربر تأیید کرد بعضی نامه‌ها کاملاً تصویری هستند؛ اما ساخت و ویرایش آن‌ها، از جمله حذف/افزودن صفحات، هنوز از تجربه مستقیم کاربر تأیید نشده است. بنابراین موتور اسکن و تصویر حفظ می‌شود.
- این شناخت، اولویت پروژه را تغییر می‌دهد: ابتدا باید قرارداد واقعی مرورگر ↔ سرویس محلی، dispatch متدها و انتقال فایل استخراج شود؛ سپس نمونه انتها‌به‌انتها برای نامه متنی و LibreOffice ساخته شود. قابلیت‌های تصویر در دامنه باقی می‌مانند.
- شواهد ایستای bridge در EmwatService.exe نشان می‌دهد JavaScript پیام message را دریافت می‌کند، event.data را با POST به 127.0.0.1 و مسیر invoke می‌فرستد و responseText را با postMessage به source/origin اولیه بازمی‌گرداند. این شواهد قرارداد کامل payload یا مدیریت فایل را ثابت نمی‌کنند.
- سند تفصیلی [PRODUCT-WORKFLOW-ANALYSIS.md](PRODUCT-WORKFLOW-ANALYSIS.md) ایجاد شد و README با هدف واقعی پروژه و اولویت‌های جدید هم‌راستا شد.
- **وضعیت پیاده‌سازی:** این مرحله مستندسازی و بازتنظیم اولویت‌هاست؛ هنوز سرویس Linux سازگار با پروتکل واقعی الماس گام یا چرخه بازگشت سند پیاده‌سازی نشده است.
- **گام بعد:** تحلیل دقیق متدهای قابل فراخوانی در EmwatMethods.bpl1 و اتصال نام/آرگومان/نوع خروجی آن‌ها به bridge؛ سپس طراحی آزمایش runtime امن با یک نامه ساختگی.


## Run 91 — شناسایی connector و مدل XML گردش‌کار Word (2026-11-12)

- تحلیل RTTI/symbolهای EmwatMethods.bpl1 کلاس Emwatconnector.TEditWordDocument.PerformMethod، dispatcher عمومی Emwatmethod.TEmwatMethod.Invoke/PerformMethod و Wordviewer.OpenDoc را نشان داد.
- مدل request در Wordrequestxml دارای Worddocument با Body، Fields، Optionalattributes، Permission، Requestedtypes، Settings، Status و ViewMode است؛ Field دارای Id، Concator، Mimetype، Separator و Encryption؛ Style دارای Align، FontName، FontSize، FontStyle و Valign است.
- مدل response در Wordresponsexml دارای Status، ErrorCode و Returntypes است؛ نوع return نیز Encryption و Mimetype دارد.
- در Wordviewer متدهای LoadDocument، PrepareDocument، FillField، FillImageField، AddImagesToDoc، SetFieldValue، GetFieldValue و دیگر helperهای سند دیده شدند.
- وجود SilentSaveEmwatDoc، OnTmrAutoSave، WordAppDocumentBeforeClose و WordAppDocumentBeforeSave نشان می‌دهد lifecycle ذخیره‌سازی/بسته‌شدن در EMWAT مدیریت می‌شود؛ اما ارسال قطعی تغییرات ذخیره‌نشده یا زمان دقیق بازگشت به الماس گام هنوز runtime-validated نیست.
- connectorهای TEditExcelWorkBook، TCompareWordDocument، TFaxDocument، TImageEdition و TScanDocument نیز در RTTI دیده شدند؛ این موضوع حفظ معماری چندماژوله Word/Excel/scan/image/fax را تقویت می‌کند.
- سند [WORD-DOCUMENT-PROTOCOL-ANALYSIS.md](WORD-DOCUMENT-PROTOCOL-ANALYSIS.md) ایجاد و به README و تحلیل گردش‌کار اضافه شد.
- **گام بعد:** اتصال این نمادها به handlerهای واقعی و استخراج schema XML/dispatch از بدنه کد/نمونه runtime؛ سپس ثبت trace پاک‌سازی‌شده از یک نامه آزمایشی.


## Run 92 — تکمیل ساختار collectionهای Word XML (2026-11-12)

- RTTI تکمیلی Wordrequestxml وجود collectionهای Fields و Settings را نشان می‌دهد؛ Word Body نیز metadata مربوط به Encryption دارد.
- ParamsToXML به‌عنوان تبدیل dictionary پارامترها به XML در unit Emwatmethod ثبت شد.
- مدل‌های Field و Return Type هر دو metadataهای MIME type و Encryption دارند؛ این یافته احتمال وجود payloadهای غیرمتنی/رمزشده را برای برخی فیلدها مطرح می‌کند، اما encoding و الگوریتم هنوز ناشناخته است.
- سند [WORD-DOCUMENT-PROTOCOL-ANALYSIS.md](WORD-DOCUMENT-PROTOCOL-ANALYSIS.md) با این جزئیات تکمیل شد.
- **گام بعد:** استخراج بدنه/نمونه‌های واقعی XML و mapping متدهای connector؛ سپس runtime trace کنترل‌شده. تا آن زمان هیچ schema یا رمزنگاری فرضی در کد production پیاده‌سازی نمی‌شود.


## Run 93 — مشاهده runtime اولین درخواست invoke از الماس گام (2026-11-12)

- کاربر در Firefox درخواست واقعی با Method برابر POST را مشاهده کرد.
- URL کپی‌شده: `http://127.0.0.1:1984/?invoke=83011`.
- صفحه caller / Referer گزارش‌شده: `automation.bsi.ir/secretariat/ClientSingleton.do`.
- این شاهد runtime تأیید می‌کند که حداقل یک درخواست عملیاتی از صفحه ClientSingleton به endpoint ریشه سرویس محلی روی پورت 1984 ارسال می‌شود.
- مقدار `83011` فعلاً فقط مقدار مشاهده‌شده پارامتر invoke است؛ نقش آن (شناسه متد، شناسه درخواست یا مقدار دیگر) نامشخص است.
- هنوز Request Body، Content-Type، پاسخ و معنای عملیات استخراج نشده‌اند؛ بنابراین هیچ wire schema یا dispatch mapping بر اساس این مقدار حدس زده نمی‌شود.
- سند [HTTP-LOCAL-API-ANALYSIS.md](HTTP-LOCAL-API-ANALYSIS.md) با این مشاهده runtime تکمیل شد.
- **گام بعد:** دریافت Request Body و Content-Type و Response از همان درخواست، با حذف کامل Cookie/Authorization/token و محتوای محرمانه؛ سپس اتصال payload به متدهای RTTI در EmwatMethods.bpl1.


## Run 94 — تحلیل HAR و استخراج نمونه EditWordDocument (2026-11-12)

- HAR خروجی Firefox 158 شامل دو POST به سرویس محلی روی 127.0.0.1:1984 است: invoke=83011 بدون body ثبت‌شده و invoke=92123 با بدنه بزرگ.
- درخواست دوم دارای Content-Type برابر text/plain;charset=UTF-8 و Content-Length برابر 1391942 است و XML بیرونی آن متد EditWordDocument را dispatch می‌کند.
- پارامتر wordConfig شامل XML سند Base64 است. بخش قابل decode شده با word-document status="view" viewMode="protected" شروع می‌شود.
- مجوزهای نمونه view شامل غیرفعال بودن save/copy/print است. fieldهای امضا، شماره/تاریخ ثبت، نام امضاکننده، QR/barcode، گیرندگان و رونوشت‌ها دیده شدند؛ چند field تصویری با Base64 منتقل می‌شوند.
- HAR فقط 1,048,576 بایت از بدنه را نگه داشته، در حالی که Content-Length برابر 1,391,942 است؛ پس نمونه ناقص است. پاسخ هر دو درخواست محلی در HAR با status 0 ثبت شده و نتیجه واقعی پردازش از این فایل قابل تعیین نیست.
- این شاهد dispatch متد EditWordDocument و قالب لایه بیرونی/درونی را تقویت می‌کند، اما نمونه موجود حالت view/protected است و چرخه ویرایش/ذخیره را اثبات نمی‌کند.
- جزئیات ساختاری بدون محتوای نامه، تصاویر، کوکی‌ها یا tokenها در HTTP-LOCAL-API-ANALYSIS.md ثبت شد. فایل خام HAR به مخزن اضافه نشد.
- **گام بعد:** capture کامل و پاک‌سازی‌شده از یک نامه قابل ویرایش، سپس تغییر متن، بستن سند و مقایسه request/responseها برای کشف lifecycle ذخیره و بازگشت داده.


## Run 95 — مشاهده runtime پاسخ EditWordDocument هنگام بستن Word (2026-11-12)

- در Firefox، کاربر هنگام باز بودن نامه قابل ویرایش، یک POST به `127.0.0.1:1984` با `Content-Type: text/plain;charset=UTF-8` و query برابر `invoke=5208` مشاهده کرد.
- تغییر متن و فشردن `Ctrl+S` درخواست تازه‌ای به پورت 1984 ایجاد نکرد.
- هنگام بستن Word، POST به همان endpoint و با همان مقدار گزارش‌شده `invoke=5208` مشاهده شد؛ status برابر HTTP 200 بود و Response دارای XML بود.
- ابتدای Response شامل XML declaration، ریشه `<emwat version="1.0">`، متد `EditWordDocument` و پارامتر `wordConfig` بود.
- کاربر در ادامه XML، تگ‌های status/ErrorCode/Returntypes/Error را پیدا نکرد؛ محتوای کامل و ساختار پاسخ هنوز استخراج نشده است.
- **نتیجه محتاطانه:** چرخه بستن سند با یک پاسخ HTTP 200 از نوع XML همراه است. هنوز ثابت نشده که پاسخ حاوی متن ویرایش‌شده یا تأیید ذخیره نهایی در الماس گام است. HTTP 200 به‌تنهایی موفقیت ذخیره را اثبات نمی‌کند.
- مشاهده‌نشدن درخواست جدید هنگام ویرایش یا Ctrl+S فقط به همین نشست محدود است؛ timer/autosave یا مسیرهای دیگر هنوز بررسی نشده‌اند.
- جزئیات و محدودیت استنباط در [HTTP-LOCAL-API-ANALYSIS.md](HTTP-LOCAL-API-ANALYSIS.md) ثبت شد.
- **گام بعد:** مقایسه ساختاری Request و Response کامل `EditWordDocument` پس از حذف کامل اطلاعات نامه، تصاویر/امضاها، Cookie، Authorization و tokenها؛ سپس اتصال پاسخ runtime به مدل Wordresponsexml شامل Status، ErrorCode و Returntypes.


## Run 96 — decode ساختار XML سند قابل ویرایش (2026-11-12)

- کاربر مقدار کدشده `wordConfig` در Response مربوط به `EditWordDocument` را به‌صورت محلی decode کرد و XML داخلی را بررسی کرد.
- ریشه سند `word-document status="edit"` بود؛ permissionهای نمونه: چاپ غیرفعال، کپی فعال و ذخیره فعال.
- ساختار سطح بالا شامل `settings`، `fields`، `optional-attributes` و `requested-types` بود.
- `requested-types` مقدار `application/msword` داشت؛ این فقط MIME type اعلام‌شده است و قالب باینری واقعی خروجی را اثبات نمی‌کند.
- encodingهای مستقیم مشاهده‌شده در metadata فیلدها: CDATA ساده، `urlencoded` برای برخی فیلدهای متنی، و `base64` همراه `image/*` برای فیلدهای تصویری.
- خانواده‌های فیلد شامل metadata تولیدکننده/فرستنده، گیرندگان، امضاکنندگان با indexهای 0 تا 19، امضاها، QR و barcode است. وجود 20 slot به معنی پر بودن همه آن‌ها نیست.
- `optional-attributes` شامل `tokenizedReceivers` با type برابر `compInfo` مشاهده شد.
- نکته کلیدی: در همین XML decodeشده عنصر `<body>` وجود نداشت، در حالی که RTTI مدل request یک property به نام Body دارد. محل بدنه نامه و علت نبودن آن در این نمونه همچنان نامشخص است.
- XML ارسالی شامل مقادیر واقعی مکاتبه بود؛ فقط ساختار و نام فیلدها ثبت شدند و هیچ متن، نام، شناسه، تصویر، Base64 یا token در مخزن اضافه نشد.
- اسناد [WORD-DOCUMENT-PROTOCOL-ANALYSIS.md](WORD-DOCUMENT-PROTOCOL-ANALYSIS.md) و [HTTP-LOCAL-API-ANALYSIS.md](HTTP-LOCAL-API-ANALYSIS.md) با جزئیات پاک‌سازی‌شده به‌روزرسانی شدند.
- **گام بعد:** ردیابی در باینری برای مشخص‌کردن منبع Body در `LoadDocument/PrepareDocument` و ترتیب واقعی lifecycle بین autosave، BeforeClose و serialization پاسخ. تا پیش از اثبات، schema پاسخ و قالب فایل خروجی hard-code نمی‌شود.


## Run 97 — بازبینی انتساب نمادهای Word و تفکیک مسیر چاپ (2026-11-12)

- گزارش تجمیعی `EMWAT-Analysis-Results.txt` دوباره از روی مخزن بررسی شد؛ فایل مستقل `EmwatMethods.bpl1-strings.txt` در مسیر ریشه در پاسخ GitHub محتوای متنی برنگرداند، بنابراین تحلیل این مرحله بر خطوط تجمیع‌شده همان گزارش تکیه دارد.
- نماد `Emwatdocprinthandlerunit.TEmwatDocPrintHandler.FillField` و متدهای هم‌خانواده `PrepareDoc`، `Execute`، `CollectCustomField`، `GetDocFieldName` و تنظیم گیرندگان در کلاس PrintHandler قرار دارند. بنابراین `FillField` را نباید بدون شواهد بیشتر به مسیر اصلی بازکردن/ویرایش نامه نسبت داد.
- نمادهای مستقل `Wordviewer.OpenDoc`، `Wordviewer.TWordViwer.SilentSaveEmwatDoc`، `StoreFieldValuesForPrint` و `OnControlerNotify` وجود دارند. این‌ها وجود مرزهای جداگانه Word viewer و PrintHandler را تقویت می‌کنند، اما ترتیب اجرا یا caller/callee را اثبات نمی‌کنند.
- RTTI پراکنده برای `IXMLWorddocumentType.Get_Body`، `Get_Fields`، `Get_Status`، `Get_Permission`، `Get_Requestedtypes` و `Get_Optionalattributes` نیز در گزارش دیده می‌شود؛ این metadata ساختار مدل XML را تأیید می‌کند، نه اینکه Body در هر پیام runtime حاضر باشد.
- در این مرحله بدنه اجرایی متدهای `LoadDocument`، `PrepareDocument`، `SilentSaveEmwatDoc` یا eventهای BeforeClose استخراج نشد؛ بنابراین هیچ call graph یا ترتیب lifecycle جدیدی ادعا نمی‌شود.
- **گام بعد:** تهیه disassembly قابل اتکا از PE/BPL با mapping صحیح RVA/section و TD32 segment، سپس دنبال‌کردن entry pointهای Wordviewer و connector. تا آن زمان طراحی adapter بر اساس تفکیک مسئولیت‌های اثبات‌شده انجام می‌شود و FillField چاپ از مسیر ویرایش جدا می‌ماند.


## Run 98 — گسترش تحلیل ایستای چرخهٔ Word (2026-11-12)

- بررسی مجدد فایل تجمیعی `EMWAT-Analysis-Results.txt` نشان داد نام‌های قابل مشاهدهٔ Wordviewer در گزارش موجود محدودند؛ از جمله `Wordviewer.OpenDoc`، `TWordViwer.SilentSaveEmwatDoc`، `StoreFieldValuesForPrint`، `OnControlerNotify`، `TEDPController.Notify` و `TEditWordDocument.PerformMethod`.
- فایل گزارش تجمیعی، نام‌های صریحی برای `LoadDocument`، `PrepareDocument`، `OnTmrAutoSave` و eventهای BeforeClose/BeforeSave در بخش نمادهای قابل مشاهده نشان نداد. این به معنی نبودن متدها در باینری نیست؛ ممکن است RTTI-only، بدون نماد procedure یا خارج از این گزارش باشند.
- اسکریپت `disassemble_emwat_targets.py` برای probe کردن همین نام‌های تأییدشده و نام‌های موردنظر lifecycle گسترش یافت. خروجی همچنان فقط وقتی روش را disassemble می‌کند که TD32 procedure record و نگاشت PE معتبر وجود داشته باشد.
- اسکریپت `resolve_td32_helpers.py` نیز برای ساخت direct-call graph از متدهای Wordviewer/connector گسترش یافت؛ dispatchهای virtual/indirect همچنان unresolved می‌مانند و مسیر PrintHandler از مسیر ویرایش تفکیک شده است.
- اجرای workflow تحلیل BPL با commitهای `2c792c4` و `0eef619` آغاز شده است؛ تا زمان ثبت این Run نتیجهٔ نهایی و artifactها هنوز در دسترس نبودند. بنابراین هنوز هیچ آدرس، call graph یا ترتیب lifecycle جدیدی ادعا نمی‌شود.
- **گام بعد:** بررسی خروجی TD32 disassembly و helper graph پس از پایان workflow؛ اگر متدهای اصلی نماد/بازهٔ معتبر نداشته باشند، مسیر بعدی باید از RTTI/VMT و callerهای مستقیم `OpenDoc` و `SilentSaveEmwatDoc` ادامه پیدا کند، نه حدس‌زدن آدرس‌ها.


## Run 99 — بررسی artifact و تحلیل Wordviewer (2026-11-12)

- هر دو اجرای workflow مربوط به commitهای `2c792c4` و `0eef619` با نتیجه `success` تمام شدند؛ اجرای دارای آخرین تغییرات اسکریپت‌ها 145 مرحله را بدون failure گذراند.
- artifact با نام `emwat-bpl-static-analysis` دریافت شد؛ گزارش disassembly شامل 77 متد match‌شده است.
- mapping segment-relative برای متدهای Wordviewer در PE section `.text` با امتیاز plausibility حدود 85 تا 90 به دست آمد. entryهای `OpenDoc`، `LoadDocument`، `OnTmrAutoSave`، `PrepareDocument`، `BeforeClose`، `BeforeSave` و `SilentSaveEmwatDoc` اکنون قابل بررسی هستند.
- `OnTmrAutoSave` pointer یک handler را به آدرس دقیق `WordAppDocumentBeforeSave` ثبت می‌کند؛ این وجود اتصال timer/event به BeforeSave را نشان می‌دهد، نه اینکه به‌تنهایی ذخیره یا ارسال خودکار هر tick را ثابت کند.
- `WordAppDocumentBeforeSave` وضعیت سند را بررسی می‌کند و در branchهایی مقدار cancel را تنظیم می‌کند؛ رفتار Ctrl+S و ارسال به سامانه هنوز از این کد اثبات نشده است.
- `WordAppDocumentBeforeClose` به helper داخلی `0x004BCA88` می‌رسد، اما فراخوانی مستقیم قابل‌تشخیص به `SilentSaveEmwatDoc` در بدنه آن نیست.
- `SilentSaveEmwatDoc` بدنه اجرایی دارد: چند collection/property داخلی را می‌خواند، helper `0x004AEBBC` را اجرا می‌کند، flag داخلی را تنظیم می‌کند و virtual dispatch دارد. مقصد ذخیره و رابطه مستقیم آن با پاسخ HTTP هنوز نامعلوم است.
- مسیر `StoreFieldValuesForPrint` از طریق `Base64Decode` و helperهای focus/window به مسیر چاپ مربوط می‌ماند و به‌عنوان serializer عمومی نامه تفسیر نمی‌شود.
- جزئیات پاک‌سازی‌شده در [WORD-DOCUMENT-PROTOCOL-ANALYSIS.md](WORD-DOCUMENT-PROTOCOL-ANALYSIS.md) ثبت شد.
- **گام بعد:** disassemble کردن callbackهای ثبت‌شده در timer، helper مربوط به BeforeClose، و حل caller/VMT dispatchهای OpenDoc و SilentSaveEmwatDoc؛ سپس اتصال شواهد استاتیک به request/response runtime.


## Run 100 — caller scan و اصلاح برداشت از SilentSave (2026-11-12)

- workflow جدید با SHA `44718f0` با موفقیت تمام شد: 147/147 مرحله، بدون failure.
- artifact جدید بررسی شد؛ چهار callback ثبت‌شده در مسیر timer، helper مورد استفاده BeforeClose و direct callerهای چند متد Word استخراج شدند.
- **اصلاح Run 99:** متد `SilentSaveEmwatDoc` با وجود نامش، از روی بدنه فعلی به‌عنوان serializer/ذخیره‌کننده نامه قابل تأیید نیست. بدنه آن به `SetRegistryValue`، `TfrmWordPrintOption.SetLetterReceivers`، `TfrmWordPrintOption.FreePrinters` و `TWrapRecord.LineCount` متصل است. caller مستقیم دیده‌شده `TWordViwer.GetDocFieldName` است، نه BeforeClose/BeforeSave. نقش دقیق آن تا حل virtual dispatchها نامشخص می‌ماند.
- **اصلاح Run 99:** آدرس `0x004BCA88` صرفاً helper مخصوص BeforeClose نیست؛ از دو محل `GetCaptionItemFont` نیز فراخوانی می‌شود. نقش آن نامشخص است.
- برای `OpenDoc` direct CALL xref در procedureهای TD32 دیده نشد؛ callback/VMT و callerهای خارج از محدوده همچنان ممکن‌اند.
- برای `LoadDocument` یک caller مستقیم در `TScanDocument.PerformMethod` دیده شد؛ بنابراین نباید آن را فقط به مسیر بازشدن نامه متنی نسبت داد.
- callbackهای timer هنوز به‌علت virtual/interface dispatch مقصد نهایی روشنی ندارند.
- جزئیات و اصلاحات در [WORD-DOCUMENT-PROTOCOL-ANALYSIS.md](WORD-DOCUMENT-PROTOCOL-ANALYSIS.md) ثبت شد.
- **گام بعد:** disassembly متد `TWordViwer.GetDocFieldName` و callerهای آن، حل interface/VMT callbackها، و یافتن مسیر غیرمستقیم فراخوانی `OpenDoc`. هیچ پیاده‌سازی save-letter بر مبنای نام `SilentSaveEmwatDoc` انجام نشود.


### Run 101 — Word lifecycle уточнения (2026-11-12)

- GitHub Actions run `43217998439` завершился успешно; artifact скачан и проверен.
- Добавлены disassembly для `TWordViwer.GetDocFieldName` (`0x004BB81C`) и `TWordViwer.GetCaptionItemFont` (`0x004C19C0`).
- `GetDocFieldName` вызывает `SilentSaveEmwatDoc` по адресу `0x004BBA86`, но это не подтверждает, что тот сериализует или отправляет тело письма. Контекст вызова — процедура получения/обработки имени поля.
- `GetCaptionItemFont` связан с caption/font и ImageGear (`IG_ext_load/unload`); он тоже вызывает общий helper `0x004BCA88`. Поэтому этот helper не является специфичным только для BeforeClose.
- Прямое назначение `SilentSaveEmwatDoc` и helper `0x004BCA88` остаётся открытым. Схема HTTP/XML и runtime trace пока не дают подтверждённого полного цикла сохранения текста письма.
- Подробности и ограничения интерпретации внесены в `docs/WORD-DOCUMENT-PROTOCOL-ANALYSIS.md`.


### Run 102 — Word XML field helpers (2026-11-12)

- Workflow `43219502021` завершился успешно: 147/147 шагов, без ошибок.
- Caller scan уточнил: `GetCaptionItemFont` вызывается из `AddImagesToDoc`; helper `0x004BCA88` имеет три прямых caller: два в `GetCaptionItemFont`, один в `WordAppDocumentBeforeClose`.
- Новый helper `0x004BC980` используется в `GetXmlFieldInfo`, `GetDocFieldIndex` и `FillImgFldsForPrint`; вероятная зона ответственности — работа с XML field metadata/lookup, но точный интерфейс пока не установлен.
- Для следующего цикла добавлены disassembly targets: `GetXmlFieldInfo`, `GetDocFieldIndex`, `AddImagesToDoc`, `FillImgFldsForPrint`.
- Протокол текста письма и фактическое сохранение пока не подтверждены; дальнейшая работа направлена на различение text-field и image-field путей.


### Run 103 — XML field lookup و مسیر تصاویر Word (2026-11-12)

- اجرای `43220472439` موفق شد: 147/147 مرحله، بدون failure؛ artifact شماره `13946301787` بررسی شد.
- overload کوچک `GetXmlFieldInfo` در `0x004BFC18` دو collection داخلی را برای resolve کردن نام/metadata فیلد جست‌وجو می‌کند و index/مشخصه‌های رکورد را خروجی می‌دهد.
- `AddImagesToDoc` در `0x004C0410` از interface مربوط به XML field داده می‌خواند و در مسیر شرطی `GetCaptionItemFont` را فراخوانی می‌کند؛ این مسیر به پردازش تصویر/caption مربوط است، نه اثبات ذخیره متن نامه.
- در artifact این اجرا بدنه مستقلی برای `GetDocFieldIndex` و `FillImgFldsForPrint` match نشد؛ جزئیات آن‌ها همچنان باز است.
- هنوز serializer متن Body یا سازوکار قطعی ذخیره نهایی در Almas Gam پیدا نشده است. جزئیات و محدودیت‌ها در `WORD-DOCUMENT-PROTOCOL-ANALYSIS.md` ثبت شده‌اند.


### تکمیل schema پاسخ Word از RTTI (2026-11-12)

- گزارش نمادهای پروژه interface IXMLResponseWordType را با propertyهای Status، ErrorCode و Returntypes نشان می‌دهد.
- IXMLReturntypesType دارای Type و IXMLBodyType دارای Encryption است.
- IXMLWorddocumentType getter مربوط به Body و propertyهای Fields، Status، Settings، Permission، Requestedtypes و Optionalattributes دارد.
- این شواهد وجود Body و مدل response را در schema تأیید می‌کند، اما مقداردهی Body، قالب واقعی Returntypes و نقطه serializer هنوز مشخص نیست. نبودن body در نمونه decodeشده کاربر فقط به همان نمونه محدود است.
- جزئیات در WORD-DOCUMENT-PROTOCOL-ANALYSIS.md ثبت شد؛ مرحله بعد اتصال این interfaceها به بدنه اجرایی TEditWordDocument.PerformMethod و ParamsToXML است.


### Run 103 — XML field lookup and image-field path

- CI run 43222525062 completed successfully (147/147 steps).
- GetXmlFieldInfo overload at 0x004BFC18 performs lookups against XML field collections at object offsets +0x68 and +0x6C, returning a matching index and associated string metadata. This is field metadata lookup, not body serialization.
- Another GetXmlFieldInfo overload is named at 0x004BCA88. This supersedes the earlier tentative generic-helper label for that address; callers from caption/image and close paths are consistent with shared XML-field lookup.
- AddImagesToDoc at 0x004C0410 delegates to GetCaptionItemFont for a field-processing branch. It does not by itself reveal the full image transfer or save protocol.
- TEmwatMethod.Invoke at 0x0046C82C traverses a dictionary/enumerator-like structure. ParamsToXML at 0x0046AD10 is only a jump thunk to 0x00401068, so its implementation still needs resolving.
- The analysis still has not found TEditWordDocument.PerformMethod or the document-body extraction/response serializer. Details and caveats are in WORD-DOCUMENT-PROTOCOL-ANALYSIS.md.


### بررسی مقصد ParamsToXML (2026-11-12)

- `ParamsToXML` در `0x0046AD10` فقط یک jump thunk به `0x00401068` است؛ آن آدرس نیز به‌صورت غیرمستقیم از IAT slot `0x0062EE24` پرش می‌کند. نام import نهایی هنوز استخراج نشده، بنابراین فعلاً نمی‌توان آن را serializer پاسخ XML دانست.
- commit افزودن trace به workflow با SHA `d4577ce` وجود دارد، اما اجرای CI متناظر در فهرست Actions مشاهده نشد. در نتیجه این مرحله هنوز artifact تأییدشده جدید ندارد.
- جزئیات و محدودیت نتیجه در [WORD-DOCUMENT-PROTOCOL-ANALYSIS.md](WORD-DOCUMENT-PROTOCOL-ANALYSIS.md) ثبت شد.
- **گام بعد:** resolve کردن import در IAT، caller scan برای `ParamsToXML` و `TEmwatMethod.Invoke`، و یافتن ماژول حاوی `TEditWordDocument.PerformMethod`.


### Run 104 — نتیجه تحلیل import و callerهای مستقیم (2026-11-12)

Workflow run `43226336477` با موفقیت کامل (148/148 مرحله) پایان یافت. در artifact، slot آدرس `0x0062EE24` به `rtl230.bpl!@System@@AbstractError$qqrv` resolve شد؛ این نتیجه هیچ پیوندی با serializer نامه ثابت نمی‌کند. برای `ParamsToXML` در `0x0046AD10` و `TEmwatMethod.Invoke` در `0x0046C82C` نیز direct CALL reference پیدا نشد. این اسکن فقط فراخوانی مستقیم داخل executable sectionهای همین PE را پوشش می‌دهد و dispatch غیرمستقیم یا callerهای خارج از ماژول را نمی‌بیند.

از آنجا که `ParamsToXML` یک thunk پنج‌بایتی به `0x00401068` است، workflow در commit `2b440ed3ebe1e6b3d1a144941cefe43a5cf70ad9` برای disassemble کردن مقصد thunk و جست‌وجوی callerهای مستقیم آن گسترش یافت. تا دریافت artifact بعدی، مسیر serialization هنوز حل نشده است.


### Run 105 — اصلاح انتساب ParamsToXML

Run `43232846364` با موفقیت کامل (148/148 مرحله) پایان یافت. رکورد TD32 برای `ParamsToXML` در `0x0046AD10` یک candidate پنج‌بایتی unresolved است که فقط به `0x00401068` jump می‌کند. مقصد، import thunk به slot `0x0062EE24` است و این slot به `rtl230.bpl!@System@@AbstractError$qqrv` resolve می‌شود. بنابراین این trace بدنه serializer را نشان نمی‌دهد و انتساب فعلی آدرس به implementation واقعی ParamsToXML قابل اتکا نیست؛ احتمال forwarding به package دیگر یا mapping/alias نامعتبر وجود دارد.

این نتیجه به معنی آن نیست که ParamsToXML واقعاً AbstractError را اجرا می‌کند. در حال حاضر نباید از آن درباره ساخت XML یا ذخیره نامه نتیجه‌گیری کرد. بررسی package/import metadata و BPLهای وابسته گام بعدی است. مسیر serialization/بازگشت سند همچنان حل‌نشده باقی می‌ماند.


### Run 105 — مسیر ParamsToXML به احتمال زیاد abstract dispatch است

تحلیل artifact نشان داد نماد TD32 با نام `@Emwatmethod@ParamsToXML...` فقط پنج بایت دارد و به یک import thunk برای `rtl230.bpl!@System@@AbstractError$qqrv` پرش می‌کند. این با stub متد abstract در Delphi سازگار است و احتمال می‌دهد implementation واقعی از طریق override/VMT یا package دیگری ارائه شود؛ اما هنوز override واقعی شناسایی نشده و این فرض باید با VMT تأیید شود. متد `GetXmlFieldInfo` در کلاس `TWordViwer` و آدرس `0x004BFC18` تابع جداگانه‌ای است و نباید با `ParamsToXML` یکی گرفته شود.

برای ادامه، ابزار inventory نمادهای TD32 و گسترش تحلیل VMT به کلاس‌های `TEmwatMethod` و `TEditWordDocument` اضافه شد. اجرای CI جدید در حال تولید گزارش‌های این دو مسیر است. تا تأیید override، پیاده‌سازی serializer و چرخه save/return همچنان نامشخص است.


## Runهای 27 تا 31 — زنجیرهٔ فیلد و nested helper (2026-11-14)

- Runهای lifecycle شمارهٔ 27، 28، 29 و 30 با موفقیت پایان یافتند؛ artifactهای آن‌ها بررسی شده‌اند. Run 31 برای trace ساختار فهرست/آرایه و callerهای بالادستی در حال اجراست.
- اصلاح مهم receiver: تابع `0x004CCBBC` با نماد TD32 `WordAppDocumentBeforeClose` در callsite تابع `FillImgFldsForPrint`، از طریق Delphi nested-procedure static link فراخوانی می‌شود. عبارت receiver آن یعنی `[[ebp+8]-0x0C]` به local تابع والد می‌رسد که مقدار ورودی ECX را نگه می‌دارد.
- اسکن direct CALLها یک caller برای `FillImgFldsForPrint` پیدا کرد: `TWordViwer.GetFieldIndexInList` در `0x004CB361`.
- بدنهٔ کامل `GetFieldIndexInList` در Run 30 نشان داد تابع ابتدا از `0x004CB638` یک pointer به فهرست/آرایه دریافت می‌کند، تعداد عناصر را می‌خواند و عناصر ۳۲بیتی را با stride چهار بایت پیمایش می‌کند. هر عنصر در ECX به `FillImgFldsForPrint` داده می‌شود.
- در `FillImgFldsForPrint` این pointer به‌عنوان receiver دارای vtable استفاده می‌شود و dispatchهای `+0x28) و `+0x38` دارد. این شواهد، interface-like بودن عناصر را اثبات می‌کنند، اما IID/type و نام متدهای این slotها هنوز مشخص نیست.
- تابع `0x004CCBBC` فعلاً به‌عنوان nested helper در مسیر پردازش فیلد فهرست‌بندی می‌شود؛ نام TD32 به‌تنهایی event registration یا close-time execution را اثبات نمی‌کند. هیچ ارتباط مستقیم اثبات‌شده‌ای از این بدنه به POST محلی، `invoke=5208` یا XML `EditWordDocument/wordConfig` پیدا نشده است.
- رفتار محصول در سطح کاربر قطعی است: بستن سند تغییرات را اعمال می‌کند، حتی اگر Save زده نشده باشد. سازوکار داخلی این رفتار همچنان موضوع تحلیل است.
- مستندات جزئی در `WORD-COM-INTERFACE-DISPATCH.md` و `PRODUCT-WORKFLOW-ANALYSIS.md` به‌روز شدند.
- **گام بعد:** Run 31 را بررسی کن؛ تابع سازندهٔ فهرست `0x004CB638)، callerهای `GetFieldIndexInList` و helperهای field lookup را تحلیل کن. سپس نوع interface و مسیر مستقل ثبت رویداد Close را پیدا کن.


### Run 31 — شناسایی نوع interface فهرست فیلدهای Word (2026-11-14)

- Run 31 با موفقیت پایان یافت و artifact آن بررسی شد.
- نماد TD32 تابع `0x004CB638` برابر `TWordViwer.FillPrintDocFields` است. امضای تابع ورودی `DelphiInterface<Wordxp._Document>` و خروجی `DynamicArray<DelphiInterface<Wordxp.Fields>>` را مشخص می‌کند.
- `GetFieldIndexInList` خروجی آرایه را پیمایش می‌کند و هر عنصر `Wordxp.Fields` را در ECX به `FillImgFldsForPrint` می‌دهد. از طریق static link همان receiver در دو dispatch داخلی تابع `0x004CCBBC` استفاده می‌شود.
- بنابراین نوع receiver برای dispatchهای `+0x28) و `+0x38) در این مسیر اکنون **به‌صورت ایستا و با امضای تایپ‌شده** `Wordxp.Fields` شناسایی شده است؛ دیگر نباید آن را فقط interface-like یا `_Document` توصیف کرد.
- caller مستقیم `GetFieldIndexInList` تابع `TWordViwer.BGPrintWithGamPrintOptions` در `0x004C6F3F` است؛ این موضوع مسیر بررسی‌شده را به پردازش فیلدها در مسیر print-options مرتبط می‌کند، نه اینکه event واقعی Close را اثبات کند.
- Workflow بعدی برای استخراج VMT/RTTI wrapperهای `TWordFields`، `TWordField` و `TWordDocument` و بررسی امضای interfaceهای Word گسترش یافت.
- **گام بعد:** نگاشت slotهای `Wordxp.Fields +0x28) و `+0x38) به نام متدهای wrapper، و جست‌وجوی مستقل registration واقعی close event و dispatcher درخواست `invoke=5208`.


### Run 33 — تطبیق IID و معنای slotهای Word Fields (2026-11-14)

- Run 33 با موفقیت پایان یافت؛ artifact شامل `Word-interface-tables.md` و disassembly کامل `BGPrintWithGamPrintOptions` بود.
- RTTI رابط‌های WordXP این GUIDها را تأیید کرد: `Fields=00020930-0000-0000-C000-000000000046`، `Field=0002092F-0000-0000-C000-000000000046`، `_Document=0002096B-0000-0000-C000-000000000046)، `Tables=0002094D-0000-0000-C000-000000000046`. دو IID نخست با مستندات Microsoft Word مطابقت دارند.
- روی receiver از نوع `Wordxp.Fields)، slot `+0x28) با الگوی getter تعداد و استفاده به‌عنوان loop bound، به‌احتمال بسیار زیاد `Count` است؛ slot `+0x38) با ورودی index و خروجی interface، به‌احتمال بسیار زیاد `Item(index)` است که `Wordxp.Field` می‌دهد. این نام‌گذاری‌ها inference با اطمینان بالا هستند، نه استخراج declaration کامل vtable.
- تنها caller مستقیم `GetFieldIndexInList` در procedureهای TD32، تابع `BGPrintWithGamPrintOptions` در `0x004C6F3F` است. بنابراین مسیر بررسی‌شده در یک مسیر print-options/field-processing استفاده می‌شود؛ registration واقعی close-event هنوز اثبات نشده است.
- اسکن VMT نام‌محور، VMT کلاس‌های `TWordFields` و `TWordField` را در همین BPL پیدا نکرد؛ این نتیجه عدم وجود interfaceها را رد نمی‌کند، چون خود RTTI interfaceها را تأیید کرده است.
- **گام بعد:** بررسی slotهای `Wordxp.Field` و `Wordxp.Range` در `FillPrintDocFields`، تکمیل inventory wrapper symbols و جست‌وجوی مستقل callback registration و dispatcher واقعی invoke/response.


### Run 34 — نمادهای typed برای Word Field و Image Field (2026-11-14)

- Inventory شماره 34 علاوه بر interface RTTI، چند تابع با امضای صریح `Wordxp.Field` و `Wordxp.Fields` را پیدا کرد:
  - `TWordDocument.Get_Fields` در ماژول `EmwatConsts`، segment 1، section offset برابر `0x2A55C).
  - `TWordViwer.FillField` با `Wordxp._Document`، نوع XML فیلد و `Wordxp.Field`.
  - `TWordViwer.FillImageField` با `Wordxp._Document` و `Wordxp.Field` و پارامترهای تصویر.
  - `TWordViwer.FillMSWFields` و `AddImagesToDoc` با `Wordxp.Fields`.
  - `TEmwatDocPrintHandler.FillField` با `Wordxp.Field`.
- VMT inventory کلاس‌هایی با نام `TWordFields`، `TWordField` و `TWordFieldCollection` پیدا نکرد؛ اما RTTI خود interfaceها و IIDهای آن‌ها را تأیید کرده است.
- Workflow به trace کامل این توابع typed و getter `TWordDocument.Get_Fields` گسترش یافت. در این مسیرها می‌توان slotهای مربوط به `Wordxp.Field` را از استفادهٔ واقعی و نه از حدس نام کلاس شناسایی کرد.
- **گام بعد:** بررسی artifact اجرای workflow 41/42، استخراج بدنهٔ کامل `Get_Fields)، `FillField`، `FillImageField`، `FillMSWFields` و `AddImagesToDoc)، و تطبیق dispatchها با Code/Result و سایر propertyهای `Wordxp.Field`.


### Run 41 — getter تایپ‌شدهٔ Fields و مسیر FillImageField (2026-11-14)

- Run 41 با موفقیت پایان یافت و trace کامل getter و helperهای تایپ‌شده استخراج شد.
- `Wordxp.TWordDocument.Get_Fields` در `0x0042B55C) پس از گرفتن interface از accessor `0x0042ABA0)، روی interface slot `+0x80) را فراخوانی می‌کند. این یک positive control تایپ‌شده برای getter به نام `Get_Fields` است.
- اسکن direct CALL برای `0x0042B55C) هیچ caller مستقیمی پیدا نکرد؛ بنابراین ممکن است این getter از VMT/property path استفاده شود یا در مسیرهای بررسی‌شده استفاده نشده باشد.
- **اصلاح مهم:** این getter با slot `+0x80) است؛ بنابراین dispatch جداگانهٔ `+0x12C) در `FillPrintDocFields` را نباید بدون شناسایی signature آن، `Get_Fields` نامید. آن فراخوانی چند آرگومان خروجی دارد و معنایش هنوز باز است.
- `TWordViwer.FillImageField` امضای تایپ‌شدهٔ `Wordxp._Document` و `Wordxp.Field` دارد و در بدنه از slotهای `+0x40)، `+0x38)، `+0x20) روی receiverهای interface استفاده می‌کند. نام متدهای این slotها هنوز مشخص نیست.
- `FillMSWFields` و `AddImagesToDoc` نیز trace شدند؛ اولی روی آرایه/فیلدهای داخلی و دومی از interface `Wordxp.Fields` برای افزودن تصویر به سند استفاده می‌کند.
- **گام بعد:** شناسایی IIDهای `Wordxp.Range` و `StoryRanges`، تطبیق slotهای `Wordxp.Field` در `FillImageField`، و بررسی نتایج caller scans برای این helperها.


### Run 43 — caller graph برای field/image helperها (2026-11-14)

- Run 43 با موفقیت پایان یافت.
- `FillImageField` دو caller مستقیم دارد که هر دو از `FillTextField` هستند (`0x004BC9CB` و `0x004BCA10)) و هر دو EBP والد را به‌عنوان static link می‌فرستند؛ پس image-field branch یک nested path در text-field processing است.
- `FillMSWFields` چهار caller مستقیم دارد: سه مورد از `GetDocFieldIndex` و یک مورد از `GetCaptionItemFont`.
- `AddImagesToDoc` فقط یک caller مستقیم در scan دارد: `GetDocFieldIndex` در `0x004C0A5D).
- `FillField` و `TWordDocument.Get_Fields` هیچ CALL مستقیم در procedureهای TD32-bounded ندارند؛ indirect/VMT/property paths همچنان ممکن‌اند.
- این caller graph، `GetDocFieldIndex` را در مرکز field processing قرار می‌دهد: آن routine روی مجموعهٔ Word حرکت می‌کند، `FillMSWFields` را برای موارد منتخب صدا می‌زند و در یک branch، `AddImagesToDoc` را اجرا می‌کند.
- **گام بعد:** trace کامل والد `FillTextField` در `0x004BC980)، بررسی callerهای `GetDocFieldIndex)، و تعیین slotهای `Wordxp.Field` در nested `FillImageField`.


### Run 44 — audit pointerهای ثبت callback در PE (2026-11-14)

- Run 44 با موفقیت پایان یافت؛ ابزار جدید `tools/scan_pe_pointer_refs.py` تمام raw sectionهای PE را برای آدرس‌های ۳۲بیتی callback جست‌وجو کرد.
- برای routine `0x004CCBBC` هیچ exact pointer referenceای در کل PE پیدا نشد.
- در مقابل، آدرس‌های callbackهای شناخته‌شده در کد `OnTmrAutoSave` دیده شدند: `0x004CD154) در `0x004B8CA8)، `0x004CD54C) در `0x004B8CBE)، `0x004CE030) در `0x004B8D0E) و `0x004B8E81)، و `0x004D00AC) در `0x004B8CF6) و `0x004B8E60).
- بدنهٔ `OnTmrAutoSave` انتساب این callbackها را به زوج فیلدهای event object تأیید می‌کند: BeforeSave در `+0x80/+0x84)، NewDocument در `+0x90/+0x94)، `0x004CD9C0) در `+0x98/+0x9C)، و BeforePrint در `+0x88/+0x8C) (با انتخاب `0x004CE030) یا `0x004D00AC)).
- این نتیجه، فرض ثبت ایستای `0x004CCBBC) به‌عنوان BeforeClose را در همین BPL بسیار نامحتمل می‌کند؛ اما computed/runtime registration یا package دیگر هنوز کاملاً رد نشده است. چون همین تابع از مسیر print/field فراخوانی مستقیم دارد، فعلاً آن را nested print/field helper طبقه‌بندی کن، نه callback قطعی Close.
- **گام بعد:** یافتن event/connector دیگری که POST مشاهده‌شده به `127.0.0.1:1984/?invoke=5208` را هنگام بستن سند ایجاد می‌کند؛ هم‌زمان بررسی RTTI برای `Range` و `StoryRanges` و slotهای Wordxp.Field ادامه یابد.


### Run 45 — RTTI مربوط به StoryRanges و FormFields (2026-11-14)

- Run 45 با موفقیت پایان یافت.
- سه interface جدید WordXP از RTTI استخراج شد: `StoryRanges` با IID `0002098C-0000-0000-C000-000000000046)، `FormFields` با IID `00020929-0000-0000-C000-000000000046)، و `FormField` با IID `00020928-0000-0000-C000-000000000046).
- اسکن هدفمند، TypeInfo برای `Range` یا `_Range` در همین BPL پیدا نکرد؛ این موضوع وجود object/interfaceهای Range را رد نمی‌کند، اما فعلاً مانع نام‌گذاری slotهای آن است.
- `StoryRanges` یک candidate معقول برای بررسی dispatch تایپ‌نشدهٔ `_Document +0x12C) در `FillPrintDocFields` است، اما هنوز هیچ wrapper یا خروجی IID آن را اثبات نکرده است. این slot را فعلاً StoryRanges ننام.
- وجود `FormFields/FormField` نشان می‌دهد کد علاوه بر Fields/Field عادی Word، مدل جداگانهٔ فرم‌فیلدها را هم import کرده است.
- **گام بعد:** بررسی symbol inventory جدید برای getter/consumerهای StoryRanges و FormFields؛ سپس بررسی callerها و signature تابع FillTextField و slotهای Wordxp.Field.


### Run 47 — زنجیرهٔ FillTextField و nested FillImageField (2026-11-14)

- Run 47 با موفقیت پایان یافت؛ بدنهٔ کامل `FillTextField` در `0x004BC980) و caller scans استخراج شد.
- `FillTextField` دو بار nested helper `FillImageField` را صدا می‌زند (`0x004BC9CB)، `0x004BCA10)) و هر دو بار EBP والد را به‌عنوان static link می‌فرستد.
- `FillTextField` نه caller مستقیم دارد: چهار call از `GetXmlFieldInfo)، سه call از `GetDocFieldIndex)، و دو call از `FillImgFldsForPrint`.
- `GetDocFieldIndex` یک caller مستقیم دارد: `GetDocFieldName` در `0x004BBB2B).
- زنجیرهٔ جدید: `GetDocFieldName → GetDocFieldIndex → FillTextField → FillImageField)، با ورودی‌های اضافی از `GetXmlFieldInfo` و `FillImgFldsForPrint`.
- این ساختار، پردازش محتوای فیلدها و تصاویر را توضیح می‌دهد و به‌خودی‌خود event بستن سند نیست.
- **گام بعد:** trace کامل `GetDocFieldName) و callerهایش برای مشخص‌کردن اینکه فیلدها از کدام XML/config path انتخاب می‌شوند.


### Run 49 — کشف close callback دوم در uSendLog (2026-11-14)

- Run 49 با موفقیت پایان یافت و symbol inventory نام‌های دارای close را استخراج کرد.
- یک routine دوم با نام `WordAppDocumentBeforeClose` پیدا شد: `uSendLog.TfrmShowAutoSaveFiles.WordAppDocumentBeforeClose` در `0x005EC580)، اندازه `0x12) بایت، با امضای شامل `TObject` و `Wordxp._Document`.
- همان فرم شامل `CloseWordApp` در `0x005EBDA8) و `FormClose` در `0x005EBF20) است.
- wrapperهای `TWordDocument.Close()` در `0x0042FEB0) و overloadها در `0x0042FF08)، `0x0042FF7C)، `0x0042FFF4) نیز در inventory پیدا شدند؛ `ClosePrintPreview` در `0x00433A84) و `CloseMyDoc` در `0x005E9174) هم ثبت شدند.
- این‌ها هنوز candidate هستند؛ handler مربوط به `TfrmShowAutoSaveFiles` ممکن است فقط برای UI فایل‌های autosave باشد و لزوماً close سند اصلی نیست.
- Workflow بعدی بدنه، callerها، immediate refs و raw pointer refs این handler و wrapperهای Close را استخراج می‌کند.
- **گام بعد:** تحلیل run 52 برای تعیین اینکه کدام close path واقعاً به Word document اصلی و POST محلی مرتبط است.


### Run 53 — GetDocFieldName و انتخاب فیلدهای Word (2026-11-14)

- Run 53 با موفقیت پایان یافت؛ بدنهٔ کامل `TWordViwer.GetDocFieldName` در `0x004BB81C` استخراج شد.
- این routine رابط سند فعلی را از viewer می‌گیرد، `FillPrintDocFields` را برای ساخت آرایهٔ `DynamicArray<Wordxp.Fields>` در فیلد داخلی `+0xA4` فراخوانی می‌کند، سپس نام فیلدهای تنظیم‌شده را پیمایش کرده و برای هرکدام `GetDocFieldIndex` را صدا می‌زند.
- نتیجهٔ Boolean هر lookup در state/flagهای viewer اعمال می‌شود. بنابراین `GetDocFieldName → GetDocFieldIndex` یک مسیر مشخص برای تطبیق نام فیلدهای config با فیلدهای واقعی Word است.
- اسکن direct CALL برای `GetDocFieldName` هیچ caller مستقیمی در procedureهای TD32-bounded پیدا نکرد؛ ورود از VMT/property/indirect path یا legacy code هنوز ممکن است.
- **گام بعد:** ادامهٔ بررسی close callback دوم `uSendLog` و wrapperهای `TWordDocument.Close`؛ همچنین تعیین entry path تابع `GetDocFieldName` و اتصال field config به invoke/response.


### Run 54–55 — callback مربوط به فرم autosave و wrapperهای Close (2026-11-14)

- Run 54 و 55 با موفقیت پایان یافتند.
- `uSendLog.TfrmShowAutoSaveFiles.WordAppDocumentBeforeClose` در `0x005EC580` فقط ۱۸ بایت است: مقدار word در `[ecx]` را با `0x2E` مقایسه می‌کند و در صورت تطبیق `CloseWordApp` را در `0x005EBDA8` صدا می‌زند.
- `CloseWordApp` دو caller مستقیم دارد: `btnShowFileClick` و همین callback. این تابع مجموعهٔ documentهای فرم autosave را پیمایش می‌کند و سپس یک متد در slot `+0x104` روی object application-like صدا می‌زند. نوع دقیق interface هنوز نیاز به نگاشت دارد.
- raw pointer scan برای `0x005EC580` دو occurrence در `.text` پیدا کرد (`0x005EB524` و `0x005EB607`)؛ resource scan فرم `TFRMSHOWAUTOSAVEFILES` در workflow بعدی برای اثبات event binding اجرا می‌شود.
- wrapperهای WordXP: `TWordDocument.Close()` بدون آرگومان slot `+0x4D4` را صدا می‌زند؛ overloadهای ۱، ۲ و ۳ `OleVariant` به‌ترتیب slot `+0x29C` را؛ `ClosePrintPreview` slot `+0x36C` را. caller مستقیم برای wrapper بدون آرگومان پیدا نشد.
- `WordCompareCommandUnit.CloseMyDoc` با وجود نامش slot `+0x2BC` را صدا می‌زند که از positive control قبلی به `_Document.PrintOutOld()` نگاشت شده است؛ این مسیر close واقعی نیست.
- **طبقه‌بندی فعلی:** handler دوم یک close-related event واقعی برای UI فایل‌های autosave است، اما هنوز callback اصلی نامه نیست. `0x004CCBBC` نیز helper داخلی مسیر print/field است. مسیر POST اصلی هنگام بستن نامه همچنان نامشخص است.


### Run 57 — resource فرم autosave و event wiring (2026-11-14)

- ابزار جدید `scan_named_pe_resource.py` با موفقیت resourceهای RCDATA را استخراج و رشته‌های آن‌ها را بررسی کرد.
- resource `TFRMSHOWAUTOSAVEFILES` (۱۱۴۹ بایت) شامل `OnClose=FormClose`، `OnCreate=FormCreate` و `OnShow=FormShow` و eventهای list/button است؛ رشته‌ای برای `WordAppDocumentBeforeClose` یا event component مربوط به Word در آن دیده نشد.
- resource `TFRMSENDLOG` نیز فقط eventهای UI فرم را نشان داد.
- بنابراین handler دوم `WordAppDocumentBeforeClose` به‌صورت آشکار در DFM فرم autosave ثبت نشده است. اگر به Word متصل می‌شود، احتمالاً اتصال در runtime در `FormCreate`، `btnShowFileClick` یا helper بازکردن preview انجام می‌شود؛ هنوز اثبات نشده.
- **گام بعد:** trace `FormCreate` و `btnShowFileClick` در `TfrmShowAutoSaveFiles` برای پیدا کردن ساخت Word.Application و اتصال event؛ سپس تعیین اینکه این مسیر صرفاً preview/autosave است یا به close نامهٔ اصلی ارتباط دارد.


### Run 58 — symbol inventory برای فرم‌ها و method dispatcher (2026-11-14)

- Inventory نام‌های lifecycle جدید را پیدا کرد: `TfrmShowAutoSaveFiles.FormCreate` در `0x005EC1A8`، `FormShow` در `0x005EC1B4` و `btnShowFileClick` در `0x005EB81C`.
- در ماژول `EmwatConnector`، `TfrmSendLog.FormCreate` در `0x005ECB88` (اندازه `0x3CC`) و `FormShow` در `0x005ECF54` پیدا شد؛ این فرم ممکن است به connector/log UI مربوط باشد و بدنهٔ FormCreate باید بررسی شود.
- `TEmwatMethod.Invoke` در `0x0046C82C` (اندازه `0x1B1`) و چند `PerformMethod` از connector classes پیدا شدند: `TCompareWordDocument` در `0x005EF8AC`، `TEditExcelWorkBook` در `0x005EF300` و `TShowSendLog` در `0x005EFE4C`.
- Workflow به trace بدنهٔ این فرم‌ها و dispatcher گسترش یافت تا مسیر `invoke=5208` و تولید پاسخ XML بهتر شناخته شود.


### Run 59 — تأیید cleanup مسیر فرم autosave

- `TfrmShowAutoSaveFiles.btnShowFileClick` فقط ۱۰ بایت است و تنها `CloseWordApp` را فراخوانی می‌کند و برمی‌گردد.
- دو caller مستقیم `CloseWordApp` دقیقاً همین دکمه و handler `WordAppDocumentBeforeClose` فرم autosave هستند.
- این pair یک مسیر cleanup برای preview/autosave است؛ در بدنهٔ traceشده سند اصلی، field pipeline یا local connector را فراخوانی نمی‌کند. بنابراین این close handler را از مسیر اصلی نامه جدا نگه می‌داریم.


### Run 60 — بررسی reachability wrapperهای Word Close

- Run 60 با موفقیت پایان یافت.
- برای چهار overload تابع `TWordDocument.Close` در آدرس‌های `0x0042FEB0`، `0x0042FF08`، `0x0042FF7C`، `0x0042FFF4` و نیز `ClosePrintPreview` در `0x00433A84` هیچ direct CALL در procedureهای TD32-bounded پیدا نشد.
- هر overload Close یک raw pointer occurrence در `.text` نزدیک metadata/VMT کلاس WordXP دارد، اما این occurrenceها callsite نیستند.
- در نتیجه این wrapperها ممکن است از طریق VMT/property قابل دسترسی باشند، ولی فعلاً مسیر اصلی close-time update محسوب نمی‌شوند.


### Run 62 — TEmwatMethod.Invoke و connector PerformMethodها (2026-11-14)

- Run 62 با موفقیت پایان یافت.
- `TEmwatMethod.Invoke` در `0x0046C82C`، با ورودی `TDictionary<AnsiString, TValue>`، پارامترهای dictionary را استخراج/پیمایش کرده و در `0x0046C921` از یک dispatch غیرمستقیم در slot `+0x68` استفاده می‌کند.
- این slot candidate فراخوانی پیاده‌سازی method است، چون چند connector class متدهای `PerformMethod(TDictionary<AnsiString, TValue>)` دارند؛ نوع receiver و slot declaration هنوز با VMT اثبات نشده است.
- تنها CALL مستقیم پیدا شده به `TEmwatMethod.Invoke` از `Finalization` در `0x0046CA67` است؛ بنابراین مسیر درخواست معمول احتمالاً indirect/VMT یا از ماژول دیگری وارد می‌شود.
- پیاده‌سازی‌های نمونه trace شدند: `TCompareWordDocument.PerformMethod` در `0x005EF8AC`، `TEditExcelWorkBook.PerformMethod` در `0x005EF300` و `TShowSendLog.PerformMethod` در `0x005EFE4C`.
- هنوز هیچ‌کدام از این شواهد، شناسهٔ `invoke=5208` یا تولید XML `EditWordDocument/wordConfig` را مشخص نمی‌کند.
- **گام بعد:** یافتن VMT مربوط به `TEmwatMethod`، mapping slot `+0x68`، و tracing parser/registry که request ID را به object متد وصل می‌کند.


### Run 64 — اسکن همهٔ RCDATA formها

- Run 64 با موفقیت پایان یافت و ۱۴ named RCDATA resource پیدا شد.
- فرم‌های دارای `OnClose` قابل مشاهده فقط image-tools، autosave-files و simple-image-editor هستند؛ همگی UI cleanup paths هستند. `TFRMWORDPRINTOPTION` رویداد close سند Word ندارد.
- در هیچ resource رشتهٔ `WordAppDocumentBeforeClose`، `OnDocumentBeforeClose` یا event property مربوط به WordApplication پیدا نشد.
- `PACKAGEINFO` واحدهای Word مانند `WordViewer`، `WordConfigRequestXML`، `WordRequestXML`، `WordResponseXML` و `WordProcessing` را همراه `EmwatConnector` و `uSendLog` فهرست می‌کند. فرم اصلی ویرایش Word به‌صورت RCDATA form مجزا وجود ندارد؛ `TWordViwer` یک code class در `ScanRequestXML` است.
- این نتیجه DFM binding را رد می‌کند، اما runtime COM connection-point یا browser-side close/request path هنوز ممکن است.


## Connector dispatcher investigation — run 62 and follow-up scans (2026-11-14)

### Statically confirmed in run 62

- `TEmwatMethod.Invoke` is a TD32-bounded routine at `0x0046C82C–0x0046C9DC` (433 bytes) in the `Base64` module.
- Its TD32 signature takes `TDictionary<AnsiString, TValue>`. The body reads and iterates dictionary data, extracts invocation values, and performs an indirect call through slot `+0x68` at `0x0046C921` on the interface/object held in local `[ebp-8]`.
- Concrete methods named `PerformMethod(TDictionary<AnsiString, TValue>)` are present:
  - `TCompareWordDocument.PerformMethod` at `0x005EF8AC`
  - `TEditExcelWorkBook.PerformMethod` at `0x005EF300`
  - `TShowSendLog.PerformMethod` at `0x005EFE4C`
- These are structural matches for a connector-method dispatch design, but **the slot +0x68 receiver type, VMT/interface mapping and association between any concrete implementation and invoke ID 5208 remain unproven**.
- The only direct TD32-bounded CALL to `TEmwatMethod.Invoke` found in run 62 is from `Finalization` at `0x0046CA67`. This does not reveal the ordinary request entry path; an indirect dispatch or another module may call it.
- The run-62 VMT scan did not recover a validated VMT candidate for `TEmwatMethod` or `TEditWordDocument`. This is a limitation of the current candidate scan, not proof that no such VMT or implementation exists.

### Workflow extension committed

The lifecycle workflow now additionally:
- scans object/interface field references at displacement `+0x68`;
- scans TD32 direct callers and immediate references for the three known concrete `PerformMethod` routines;
- scans exact raw PE pointer occurrences for `TEmwatMethod.Invoke` and those concrete methods.

The resulting evidence should distinguish ordinary CALL xrefs, code immediates, metadata pointers and actual candidate VMT entries. A raw pointer match alone is not proof of registration.

### Current next actions

1. Decode the TXMLMethodType +0xC8 attribute-name literal at 0x0044C6A4 (implementation 0x0044C62C, reached via thunk 0x0044BA59). The method-name string is passed to TXMLNode.SetAttribute; the service parser expects method@class, so confirm whether the literal is class. Then map TXMLEmwatType +0x54 serializer getter at VTable address 0x0044B8CC (thunk 0x0044B7A9), which returns the serialized XML string at callsite 0x0046C937. TXMLParamType parameter serialization is proven: +0xB0 sets attribute name and +0x68 calls TXMLNode.SetText.
2. Keep the second +0x68 call at 0x0046CBB7 separate; it uses a different local receiver in the shared base wrapper's exception/response path.
3. Continue tracing the service parser/registry only where necessary to establish how XML method classes are resolved. The browser's `invoke=5208` value is already proven to be a random per-request nonce, not a method ID; the server-generated `TEmwatInvokeParam.SessionId` is separate.
4. Trace the registered BeforeSave callback at 0x004CD154 and the parent-page `postMessage` that initiates the close-time `EditWordDocument` request. Do not call 0x004CD154 a BeforeClose handler. The user's close-applies-changes observation remains a hard requirement.



## Browser bridge random invoke value — correction (2026-11-14)

The `EmwatService.exe-strings.txt` dump contains the complete obfuscated JavaScript bridge. Deobfuscating the string array and reading the script shows:

- The bridge listens for `window.addEventListener("message", ...)`.
- For each received message it extracts `event.origin`, `event.source` and `event.data`.
- It creates `requestId = Math.floor(Math.random() * 99999)`.
- It POSTs `event.data` to `http://127.0.0.1:$V{myport}?invoke=` plus that random integer.
- When readyState reaches 4, it returns `responseText` to the source window via `postMessage(responseText, origin)`.

**This supersedes the earlier assumption that the observed value `invoke=5208` might be a stable method ID.** The embedded bridge generates it with `Math.floor(Math.random()*99999)` solely to vary the XHR URL (`?invoke=` + nonce). It is a per-request URL nonce/cache-buster, not a method ID or response-correlation token. The service checks the presence of the `invoke` key but does not copy its numeric value into `TEmwatInvokeParam.SessionId`; that field is generated independently server-side. The bridge sends `event.data` as the POST body and posts `responseText` back to the original `event.source` and `event.origin`. The actual operation is named in the XML body, e.g. `<method class="EditWordDocument">`.

The service string dump also contains `TEmwatInvokeParam`, `ParseMethod`, `Calling ParseMethod exception:`, `Emwat method called from`, and `Unable to call "invoke" method:`. This confirms parser/invoke-related code paths exist by string evidence, but does not reveal their implementation.

### Revised investigation sequence

1. Map the service-created method instance's VMT slot `+0x0C` to the exact BPL base-class method and follow it into the BPL connector dispatch.
2. Resolve the BPL `TEmwatMethod.Invoke` slot `+0x68` receiver and map the concrete class/VMT entry for `TEditWordDocument`.
3. Identify the request-info object at `[ARequestInfo+0xD4]` and its size/read methods to prove the HTTP body extraction.
4. Trace the server-generated `TEmwatInvokeParam.SessionId` through response/context handling; keep it distinct from the browser's random `invoke` query value.
5. Link the `EditWordDocument` method to `wordConfig` serialization, response transport, and the user-observed apply-on-close behavior.


## Original service executable recovered from installer (2026-11-14)

The project Library contained the original `EmwatInstaller.exe`. Its embedded CAB was extracted locally with libarchive, revealing `EmwatService.exe`, `EmwatAgent.exe`, and the full package set. The extracted BPL is byte-for-byte identical to `analysis-input/EmwatMethods.bpl1` in the repository (Git blob SHA-1 match), validating the current BPL analysis against the installer package.

New document: `docs/EMWAT-SERVICE-EXECUTABLE-ANALYSIS.md`.

Key additional facts:
- The extracted `EmwatService.exe` is a 679,936-byte PE32 executable. It imports Indy 23 packages and contains RTTI for `TIdHTTPServer`, `TIdHTTPRequestInfo`, and `TIdHTTPResponseInfo`, consistent with the loopback HTTP bridge.
- Its embedded JavaScript bridge is confirmed in the executable, with the per-message random `invoke` value and request/response `postMessage` flow.
- The service PE contains `TEmwatInvokeParam` RTTI: a 20-byte Delphi record with managed fields `System.string` at offset 0 and `System.AnsiString` at offset 8, and named fields `SessionId`, `bUnloadPkg`, `bResultSet`, `BufferIn`, `AResponseInfo`, and `AContext`.
- The same record is declared in BPL unit `Emwat.Sys`; `Wordviewer.OpenDoc` at `0x004B7430` has a `PEmwatInvokeParam` parameter. The service handler's record fields and dynamic class dispatch are now statically traced, and the record pointer is stored at offset `+0x04` of the instantiated connector object. The direct concrete-method-to-`Wordviewer.OpenDoc` call chain is still being resolved.

The service executable has no TD32 debug section. Continue with PE/RTTI/import/x86 analysis locally; do not claim full symbolic reconstruction. See the new service analysis document for hashes, offsets and evidence limits.



## Service XML dispatch and concrete Word method target (2026-11-14)

Lifecycle run 76 plus local disassembly of the extracted service executable establish the main request pipeline:

- `TMainForm.IdHTTPServerCommandGet` at `0x0047BF30) constructs the 20-byte `TEmwatInvokeParam` record.
- Internal `SessionId` is generated by the service with `System.Random(900000)+100000` and converted with `IntToStr`. It is separate from the browser's `invoke=<random>` query value; the handler checks the query parameter collection but does not copy its value into `SessionId`.
- The POST body is stored in `BufferIn`; `AResponseInfo` and `AContext` are copied into the record.
- XML parser helper `0x00470B38) reads the `method` element's `class` attribute and the `param name` values into a `TMethodInfo` object.
- Dispatcher `0x00470D00) prefixes `T` to the class name, resolves it with `System.Classes.GetClass`, creates the instance, and calls its VMT slot `+0x0C`.
- The common base routine at `0x0046C9E0) calls `TEmwatMethod.Invoke` (`0x0046C82C)) and then invokes the concrete class's VMT slot `+0x10`.

**Concrete Word-edit entry found:** `TEditWordDocument` VMT `0x005ED764), slot `+0x10 = 0x005EE82C`. This target has executable code even though no TD32 procedure record covers it. The method reads the `document` parameter and calls helper `0x004B7724`; the next trace will identify that helper and follow document opening/automation.

The VMT scanner was corrected to inspect Delphi class RTTI directly and to include small 12-byte connector classes. It now finds the full connector class family. Some TD32 procedure labels do not align with the VMT class whose slot points at that address; VMT slot targets are the authoritative dynamic-dispatch mapping, while symbol-name discrepancies remain explicitly unresolved.

New repeatable tool: `tools/trace_pe_range.py`, used by the lifecycle workflow to disassemble VMT-target code ranges even when TD32 procedure records are missing. The workflow now traces all connector VMT slot `+0x10` bodies and the `0x004B7724` helper.



## Service HTTP-to-BPL dispatch recovered (2026-11-14)

The original service PE was extracted from the Library installer and analyzed directly. The handler is identified by RTTI as `TMainForm.IdHTTPServerCommandGet` (entry `0x0047BF30`). It initializes a local `TEmwatInvokeParam` record and calls the shared dispatcher at `0x00470D00` (`CALL` at `0x0047C0C5`).

**Statically confirmed:**
- Request routes inspect the keys `invoke`, `init`, and `heartbeat` in the request parameter collection.
- `invoke` enters the XML method-dispatch path; `init` returns the embedded JavaScript bridge; `heartbeat` handles the Agent heartbeat.
- The record layout is `SessionId +0x00`, `bUnloadPkg +0x04`, `bResultSet +0x05`, `BufferIn +0x08`, `AResponseInfo +0x0C`, and `AContext +0x10`.
- The service generates `SessionId` with `Random(900000)+100000` followed by `IntToStr`; it is not the browser's `invoke=5208` value.
- The request-body source at `[ARequestInfo+0xD4]` is identified with high confidence as `TIdHTTPRequestInfo.PostStream`; the handler reads a size-like value and then calls virtual slot `+0x0C` with a buffer/length pair. The exact stream virtual method names/signatures remain unresolved. `[ARequestInfo+0xD0]` maps to `Params`, and `[ARequestInfo+0xDC]` to `RemoteIP`.
- The shared dispatcher parses the XML, reads `method@class`, prefixes the class name with `T`, resolves it with Delphi `GetClass`, creates the class instance, stores the request-record pointer at object offset `+0x04`, then calls virtual slot `+0x0C`.
- Three additional internal service routines call the same dispatcher with embedded XML (including `ShowEmwatSetting` and `ShowSendLog`).

Service-side virtual slot `+0x0C` is now mapped to shared BPL routine `0x0046C9E0`, which calls `TEmwatMethod.Invoke` (`0x0046C82C`) and then the subclass's VMT slot `+0x10`. XML `class="EditWordDocument"` resolves to `TEditWordDocument`; its slot `+0x10` target is `0x005EE82C`, which reads the `document` parameter and calls helper `0x004B7724`. The remaining work is to trace this concrete method/helper through document opening, response serialization/transport, and the upstream close event. Full evidence: `docs/EMWAT-SERVICE-EXECUTABLE-ANALYSIS.md` and `docs/WORD-COM-INTERFACE-DISPATCH.md`.


### Correction to run-62 connector dictionary and call-path interpretation (run 76)

The run-62 generic signature was initially read as `TDictionary<AnsiString, TValue>`; this was incorrect. The BPL's concrete generic RTTI and the service's `TMethodInfo.Params` type establish `TDictionary<AnsiString, AnsiString>`. The XML parser's string values therefore flow into the connector methods as a string-to-string dictionary.

The run-62 statement that the only direct CALL to `TEmwatMethod.Invoke` came from `Finalization` was also incomplete. The routine at `0x0046C9E0` (TD32 label `Emwatmethod.Finalization`) is the shared `TEmwatMethod` virtual wrapper at VMT slot `+0x0C`. The service dispatcher invokes that slot; the wrapper calls `TEmwatMethod.Invoke` at `0x0046C82C`, then invokes the concrete class's VMT slot `+0x10`. Thus the apparent finalization call is part of the ordinary request dispatch path.

The corrected class-RTTI scan also found the previously missed small connector classes (instance size `0x0C`). Their VMT slot `+0x10` targets are documented in `WORD-COM-INTERFACE-DISPATCH.md`; for `TEditWordDocument`, the concrete target is `0x005EE82C`. TD32 procedure labels for some other targets differ from the VMT class mapping, so keep those names and target addresses separate until code behavior is reconciled.


## TEditWordDocument payload keys and response generation (run 77)

The concrete `TEditWordDocument` VMT slot `+0x10` target `0x005EE82C` reads four named dictionary parameters: `wordConfig`, `wordBody`, `letterImages`, and `signData`. It starts a worker thread, logs `CoInitializing thread`, and passes those values plus the `TEmwatInvokeParam*` request context and an output-string reference to helper `0x004B7724`.

After the helper returns, `TEditWordDocument` copies the output string to the base dispatcher's result string and sets `bUnloadPkg=true`. Correction from the complete `LoadDocument` body: on a non-empty result path, `TWordViwer.LoadDocument` itself assigns the output to `AResponseInfo.ContentText` (`AResponseInfo` at record `+0x0C`, ContentText at object `+0xBC`), calls imported `IdCustomHTTPServer.TIdHTTPResponseInfo.WriteContent` via thunk `0x0040448C` / IAT `0x0062F9C0`, then sets `bResultSet=true` at record `+0x05`. Therefore the generic service dispatcher skips its fallback response branch for this successful path; the fallback remains for methods that do not set `bResultSet` themselves.

This statically connects the runtime `EditWordDocument` XML request to the generic HTTP response path. The exact response XML and Word automation/commit behavior are now narrowed to helper `0x004B7724` and its downstream calls. Run 77 captures the helper's complete TD32 procedure and caller references.


## Word lifecycle callback classification — superseded correction (2026-11-14)

The earlier section that called 0x004CD154 the main-editor BeforeClose callback was incorrect and is superseded by runs 25–26. The confirmed mapping is: 0x004CD154 is the registered TWordViwer.WordAppDocumentBeforeSave callback at event-record +0x80; 0x004CD54C is registered at +0x90; 0x004CD9C0 at +0x98; and the conditional BeforePrint callback at +0x88 is 0x004D00AC or 0x004CE030. The callback at 0x004CD154 calls PreparePrintDocument (0x004CB108), calls _Document slot +0xD8, which the generated wrapper maps to Set_Saved; therefore that instruction is not evidence of a Saved getter. The callback still presents Yes/No/Cancel, but the value being assigned and the prompt condition need further tracing, sets Cancel to 0xFFFF on Cancel, and directly calls interface slot +0x29C with three OleVariant arguments on Yes/No. This slot is also used by the three-argument TWordDocument.Close wrapper at 0x0042FFF4. The wrapper at 0x00430070 is SaveAs2000, not Close.

The separate TD32-named TWordViwer.WordAppDocumentBeforeClose at 0x004CCBBC has only one direct bounded caller found (FillImgFldsForPrint at 0x004CCF8F) and no raw-pointer registration reference; its active event role is unproven. The browser bridge remains a generic postMessage → XHR → postMessage forwarder. The parent-page message that initiates the close-time POST and the final apply/commit semantics remain unresolved. The user's observed apply-on-close behavior remains a requirement.


## Run 82 and focused Invoke receiver workflow (2026-11-14)

- Lifecycle run 82 completed successfully. It confirms the decoded static parameter literals used by the concrete Word connector: `wordConfig`, `wordBody`, `letterImages`, and `signData`. The new repeatable tool `tools/decode_pe_strings.py` reads Delphi ANSI/UTF-16LE strings from PE virtual addresses; its output records the Delphi refcount/length header where available.
- A focused workflow, `.github/workflows/analyze-invoke-enumerator.yml` (workflow display name: **Analyze EMWAT Invoke receiver**), was added so the generic Invoke/XML receiver trace can run independently of the much larger lifecycle analysis.
- Focused run 1 traced helper 0x0044C238 and proved its TD32 symbol is `Emwatxml.TXMLEmwatType.AfterConstruction`; the only direct caller is `TEmwatMethod.Invoke` at 0x0046C877, passing the address of local `[ebp-4]`.
- RTTI identifies `TXMLEmwatType` at VMT 0x0044B9AC, instance size 0x5C, with one implemented interface at object offset +0x50 and interface VTable 0x0044B878 (IID e7e941dd-cf1c-4856-9cec-8b6d2370c439).
- Focused run 3 shows the class VMT's +0x68 slot is null, so the unresolved +0x68 call cannot be made on a plain `TXMLEmwatType` class VMT. Its implemented interface has a valid +0x68 VTable entry (thunk 0x0044B7D1), which is only a candidate until the dataflow proves the local receiver is that interface pointer.
- The class VMT's +0x68 slot is null; bytes at class-relative +0xB0/+0xCC are not valid pointer slots. The actual +0xB0 call is through the `TXMLEmwatType` implemented-interface VTable at `0x0044B878`. `TXMLMethodType` and `TXMLParamType` are present in RTTI with interface offsets +0x70 and +0x50 respectively.
- The dictionary enumeration helpers `0x0046DE84` and `0x0046E324` are separate from the +0x68 receiver dispatch. The earlier hypothesis that local `[ebp-8]` itself was a `TDictionary.TPairEnumerator` is withdrawn: that class's VMT has only its own leading enumerator slots and +0x68 falls in metadata/data, not an executable class virtual slot.

**Evidence boundary:** this advances the type of the first receiver in the chain and narrows the likely XML class/interface family, but the exact types of `[ebp-0x1C]` and `[ebp-8]`, plus the method name at +0x68, remain unresolved. See [WORD-COM-INTERFACE-DISPATCH.md](WORD-COM-INTERFACE-DISPATCH.md).


## Invoke XML-interface receiver investigation (2026-11-14)

The focused receiver workflow has now narrowed the unresolved `TEmwatMethod.Invoke` indirect dispatch at `0x0046C921` beyond the earlier dictionary-enumerator hypothesis:

- `Invoke` accepts `TDictionary<AnsiString,AnsiString>` and stores its first receiver in local `[ebp-4]`. The only direct caller of helper `0x0044C238` is `Invoke` at `0x0046C877`; TD32 labels the helper `TXMLEmwatType.AfterConstruction`. Treat that symbol as a helper label until its full factory/dataflow is resolved.
- Class RTTI identifies `TXMLEmwatType` at VMT `0x0044B9AC`, instance size `0x5C`, implementing IID `e7e941dd-cf1c-4856-9cec-8b6d2370c439` at interface offset `0x50` with VTable `0x0044B878`.
- That interface's `+0xB0` slot is at `0x0044B928` and points to thunk `0x0044B709`; its `+0x68` slot points to thunk `0x0044B7D1`. This is an interface VTable dispatch, not a class-VMT `+0xB0` slot.
- The next `+0xCC` call at `0x0046C8E6` acts on the returned object `[ebp-0x1C]`, not the original `TXMLEmwatType` interface. `TXMLMethodType` is a separate class with IID `55d7b886-a428-4f24-8766-6af7ab8f792d`, interface offset `0x70`, and VTable `0x0044BBF8`; its `+0xCC` and `+0x68` slots point to thunks `0x0044BA61` and `0x0044BB51` respectively.
- `TXMLMethodType` remains a candidate for a returned XML interface, not a proven runtime type for either local. The exact type of `[ebp-0x1C]` and `[ebp-8]` remains unresolved until the interface thunk bodies and out-parameter dataflow are traced.

The implementation-body trace adds a major semantic step: `TXMLEmwatType` interface slot `+0xB0` resolves to `TXMLMethodType.AfterConstruction` (`0x0044C458`), which constructs the method-type interface returned into `[ebp-0x1C]`. The `TXMLMethodType` interface slot `+0xCC` resolves to `TXMLMethodType.Insert` (`0x0044C754`), which inserts a child at index `-1` and returns an interface into `[ebp-8]`. RTTI identifies `TXMLParamType` as the child-parameter class; its implemented interface VTable is `0x0044BF5C`, with candidate `+0xB0` slot pointer `0x0044BDF5` and `+0x68` slot pointer `0x0044BEB5`. `Invoke` then passes the two dictionary pair strings to the returned child's `+0xB0` and `+0x68` slots respectively. This strongly indicates that `Invoke` constructs XML parameter child nodes and assigns each key/value pair; the exact property names still await the TXMLParamType thunk traces.

The initial focused dictionary/enumerator workflow completed successfully (run `43570769839`). The XML interface VTable workflow completed successfully (run `43571030574`). Latest thunk-trace workflow: `43571171939`; artifact pending at the time of this update. Detailed address evidence is in `docs/WORD-COM-INTERFACE-DISPATCH.md` and the `emwat-invoke-receiver-analysis` workflow artifact.


## Invoke XML interface chain — focused runs 6–9 (2026-11-14)

- The first receiver chain is now mapped through interface implementations, not just numeric VTable slots:
  - [ebp-4] is a TXMLEmwatType interface; its +0xB0 thunk 0x0044B709 adjusts Self by -0x50 and jumps to 0x0044C458.
  - 0x0044C458 is TD32-labelled TXMLMethodType.AfterConstruction. It returns a TXMLMethodType interface into the output pointer supplied by TEmwatMethod.Invoke.
  - [ebp-1C] is therefore a TXMLMethodType interface; its +0xCC thunk 0x0044BA61 adjusts Self by -0x70 and jumps to 0x0044C754.
  - 0x0044C754 is TD32-labelled TXMLMethodType.Insert. It invokes its own VMT slot +0x20 with index -1, then returns the created child interface into the caller's output pointer [ebp-8].
  - RTTI identifies the child interface candidate as TXMLParamType (interface offset +0x50, VTable 0x0044BF5C). Its +0xB0 and +0x68 VTable entries are 0x0044BDF5 and 0x0044BEB5; the Invoke loop passes the first dictionary-pair string to +0xB0 and the second to +0x68.
- This strongly maps [ebp-8] to TXMLParamType. The two TXMLParamType interface thunks are now resolved: +0xB0 pointer `0x0044BDF5` adjusts Self by -0x50 and jumps to `0x0044C8E4`; +0x68 pointer `0x0044BEB5` adjusts Self by -0x50 and jumps to shared XML-interface body `0x0044B568`. The `+0x68` implementation is now confirmed as `xmlrtl230.bpl!TXMLNode.SetText`, so the second dictionary-pair string is the XML parameter node's text/value. The `+0xB0` implementation at `0x0044C8E4` passes the first string to helper `0x0044B4C0` with literal `0x0044C95C`; its imported target and literal are being decoded to identify the key attribute.
- The generic dictionary enumerator is now separated from the XML receiver: helpers 0x0046DE84 and 0x0046E324 produce/iterate pair data, while TXMLParamType receives the pair fields through its own interface methods.
- Detailed instruction traces and VTable evidence are in [WORD-COM-INTERFACE-DISPATCH.md](WORD-COM-INTERFACE-DISPATCH.md).


Run `43571520321` completed successfully and produced artifact `14104388028` with the TXMLParamType thunk mapping. Run `43571683744` is tracing the two resolved implementation bodies (`0x0044C8E4` and `0x0044B568`) to establish the exact field semantics. 

## Invoke XML parameter serialization — confirmed (2026-11-14)

Focused run 11 (`43571811038`, artifact `14105075475`) closes the key/value setter question. In `TEmwatMethod.Invoke`, each dictionary pair is materialized as a child XML parameter node:

- Pair key → XML attribute `name`: `0x0044C8E4` passes the key and constant `0x0044C95C` to `0x0044B4C0`; the latter is the `xmlrtl230.bpl!TXMLNode.SetAttribute(UnicodeString, OleVariant)` import thunk, and the constant decodes to `name`.
- Pair value → XML node text: interface thunk `0x0044BEB5` reaches `0x0044B568`, the `xmlrtl230.bpl!TXMLNode.SetText(UnicodeString)` import thunk.

This is statically confirmed parameter-node structure, not yet runtime-confirmed end-to-end request XML. Next: resolve the method object's `+0xC8` attribute literal (likely the method/class discriminator based on service parser schema, but do not assume until decoded), and map `TXMLEmwatType` interface slot `+0x54` to the actual XML serialization getter. Then compare complete request/response XML with runtime captures.

## Invoke XML method envelope and serializer — confirmed (2026-11-14)

Focused run 16 (`43573798242`, artifact `14105735885`) maps the XML serialization getter and method-name attribute:

- `TXMLEmwatType` interface slot `+0x54` points to thunk `0x0044B7A9`, which adjusts `Self` by `-0x50` and jumps to `0x0044B590`.
- `0x0044B590` is the IAT thunk for `xmlrtl230.bpl!TXMLNode.GetXML`; this is the getter used to serialize the constructed XML node tree into Invoke's output string.
- `TXMLMethodType` implementation `0x0044C62C` calls `TXMLNode.SetAttribute` with literal `class` and the incoming method name.
- `TXMLMethodType.AfterConstruction` (`0x0044C458`) passes literal `method` into the XML element setup path. It also calls helper `0x00401430` with constant pointer `0x0044C4FC`; the second constant's semantic role remains pending.
- `TXMLMethodType.Insert` appends each parameter child. Every child node receives `name=` dictionary key and text equal to dictionary value, as confirmed in focused run 11.

The proven structure is therefore a `method` element with `class=` method-name and parameter children with `name` attributes and text values; `TXMLNode.GetXML` returns the serialized XML string. This remains static-analysis evidence; complete document envelope/encoding and runtime request capture comparison are still open.

## Generic Invoke XML serialization — current confirmed state (2026-11-14)

Focused runs 11 and 16 close the previous XML dispatch questions: TXMLMethodType.AfterConstruction initializes a method element; its +0xC8 setter assigns the incoming method name to attribute class; each dictionary pair becomes a parameter child with key in name and value in text; and TXMLEmwatType +0x54 calls xmlrtl230.bpl!TXMLNode.GetXML to serialize the tree. The constructor additional constant 0x0044C4FC remains unresolved. Complete envelope/encoding and runtime HTTP comparison remain open. Detailed evidence: docs/WORD-COM-INTERFACE-DISPATCH.md and docs/WORD-DOCUMENT-PROTOCOL-ANALYSIS.md.

## XML constructor follow-up — run 17

Focused run 17 (`43574768657`, artifact `14106455607`) confirms `0x0044B4D8` is `xmlrtl230.bpl!TXMLNode.GetChildNodes`, called by `TXMLMethodType.AfterConstruction` before the `method` element is inserted. The constructor's second argument constant `0x0044C4FC` is not a valid Delphi string. The call to `0x00401430` is an IAT thunk via slot `0x0062EC40`, but its import identity is not yet resolved. Run 18 now inspects that exact import slot and nearby bytes. Do not infer an extra XML attribute or node from this unresolved call.


## XML constructor import lookup — run 19

Focused run 19 (`43575191082`, artifact `14106206890`) confirms that `0x0062EC40` is located in `.idata` but does not match any parsed import descriptor entry. Its on-disk DWORD is `0x00231274`; the target is outside the BPL image and may be unresolved/relocated. Therefore the helper at `0x00401430` and the IID-like constant at `0x0044C4FC` remain semantically unresolved. Do not describe the helper as QueryInterface or claim an extra XML field. Run 20 directly traces `TXMLParamType.AfterConstruction` (VMT `+0x0C`, address `0x0044B4F8`) to recover the parameter element tag.
 

## XML parameter element constructor — run 20 correction

Run 20 (`43576636790`, artifact `14106479073`) shows that `TXMLParamType` VMT `+0x0C` (`0x0044B4F8`) is an import-style jump thunk through `0x006302B4`, not a TD32 constructor procedure; the slot's on-disk target `0x0024060C` is outside the BPL image. The parameter XML element tag remains unknown. A TD32 decorated-symbol indexer was added as `tools/find_td32_class_procedures.py`; the next run uses it to locate actual `TXMLParamType` and `TXMLMethodType` procedure addresses before tracing constructors.

## XML constructor comparison — run 22

Run 22 (`43578292246`, artifact `14106852706`) completed successfully. TD32 indexing found `TXMLParamType.AfterConstruction` at `0x00614EC8` only in the separate `WordRequestXML` module, not in the indexed `XmlResponse` class procedures. The WordRequestXML constructor calls `0x0044B4D8` (`xmlrtl230.bpl!TXMLNode.GetChildNodes`) and then the still-unresolved helper `0x00401430` with binary GUID-like constant `0x00614F2C`; that constant is not a readable Delphi string. The XmlResponse VMT parent pointers (`0x00630314` for TXMLParamType and `0x0063030C` for TXMLMethodType) point outside the BPL image, so their parent class identities are not established.

**No parameter tag was recovered.** Do not treat the WordRequestXML constructor as the XmlResponse constructor without evidence that the classes share the relevant construction path. The exact child element tag, full XML envelope, encoding and runtime wire representation remain unknown. The generic Invoke tree facts established in runs 11 and 16 remain confirmed: `method` element, `class` method-name attribute, parameter `name` key attribute, value as node text, serialized via `TXMLNode.GetXML`.

Next analysis: resolve external parent VMT/class references and trace how XmlResponse creates/initializes the parameter node returned by `TXMLMethodType.Insert`; then return to the parent-page close-time POST and response protocol. Do not spend another run repeating the TD32 symbol index unless new module inputs arrive.

## XmlResponse parameter insertion trace — run 23

Run 23 (`43579138098`, artifact `14107224578`) completed successfully. The XmlResponse `TXMLMethodType.Insert` implementation calls its child-node collection's virtual slot `+0x20` with index `-1`, then converts the returned node to the `TXMLParamType` interface using a GUID-like constant. It does not pass a literal child-element name. `TXMLParamType.Set_Name` operates on the wrapped node's name-related attribute path; it does not establish the element tag. The method constructor separately passes literal `method` to the child-node collection's `+0x10` method, confirming the method element.

The external parent VMT pointers and helper `0x00401430` remain unresolved; the latter is an indirect jump through a slot not matched to a parsed import descriptor. **Parameter child tag is still unknown.** The next useful target is the external XML node-list virtual method/class contract and then the parent-page close-time POST. No native Linux runtime behavior is claimed by this static-analysis result.

## XML node-list Add/Get_Param comparison — run 24 (2026-11-14)

Run 24 (`43579618380`, artifact `14106929511`) traced the paired `TXMLMethodType.Add` and `Get_Param` procedures in `XmlResponse` and `.EmwatMethods`.

- Both `Add` implementations follow the same pattern: obtain the wrapped node's child-node collection and invoke collection virtual slot `+0x10` with a string argument and an output interface. This matches the method-construction path that explicitly supplies `method`.
- Both `Insert` paths instead invoke child-collection virtual slot `+0x20` with index `-1`; no element-name string is supplied at this level. The parameter element tag must therefore be established deeper in the collection/node-list implementation or its class metadata.
- The paired `Get_Param` bodies in the two modules are structurally equivalent. The XmlResponse implementation uses the already decoded literal `class` as the attribute name and the incoming string as its value.
- The direct-call scan reports no direct immediate CALL xrefs for these interface methods; use is expected through virtual/interface dispatch.

**Boundary unchanged:** no parameter child tag, complete XML envelope, or exact wire serialization was recovered. Next target is the node-list implementation behind child collection virtual slots `+0x10` and `+0x20`; prioritize the page-side close-time `postMessage` sender and corresponding HTTP response path in parallel. Do not treat this static analysis as proof of native Linux runtime behavior.

## Close callback deep trace queued — 2026-11-14

The lifecycle workflow now has a follow-up step for the registered `WordAppDocumentBeforeClose` body and pointer/caller references, `RollBackOriginalOptions`, and the three-argument Word `Close` wrapper. Commit: `b88451617f3500f8ec64e239902533b21ab82a4d`. This is an analysis-only extension; no native runtime behavior is implemented by it. The run output must be reviewed before drawing conclusions.
 
## Correction — run 25 address/symbol verification (2026-11-14)

Run 25 (`43580008821`, artifact `14108665890`) exposed incorrect target labels in the preceding analysis step. The TD32 symbol at `0x004CD154` is `TWordViwer.WordAppDocumentBeforeSave`, not `WordAppDocumentBeforeClose`. The LoadDocument/OnTmrAutoSave registration code at `0x004B8C9C–0x004B8CCE` explicitly stores `0x004CD154` at callback field `+0x80`, `0x004CD54C` at `+0x90`, and `0x004CD9C0` at `+0x98`; the conditional callback at `+0x88` is `0x004D00AC` or `0x004CE030`. Thus `0x004CD154` is conclusively the registered BeforeSave callback. Do not call it a close callback.

The actual TD32 procedure named `TWordViwer.WordAppDocumentBeforeClose` begins at `0x004CCBBC`, but its only direct immediate caller found is `FillImgFldsForPrint` at `0x004CCF8F`; no registration reference was found in the scanned raw pointer data. Therefore its name alone does not prove that this procedure is the live Word application close-event handler.

A second address error: `0x00430070` is `TWordDocument.SaveAs2000`, not a Close wrapper. The actual `TWordDocument.Close` overload procedures are TD32-labeled at `0x0042FEB0`, `0x0042FF08`, `0x0042FF7C`, and `0x0042FFF4`; the latter is the three-argument overload. A three-argument Close invocation in the callback body dispatches through document interface VMT slot `+0x29C`, but the exact runtime target for that interface dispatch must be established by matching the interface VMT and wrapper semantics, not by assigning `0x00430070`.

Run 25 itself completed successfully, but its added trace commands targeted the wrong symbols for a close-event investigation. Treat its other outputs as useful only where the TD32 labels and address semantics are independently verified. Next analysis must trace the actual Close overload(s), find the genuine callback registration (if present), and distinguish the BeforeSave callback from document-close lifecycle. No claim about the page-side POST is changed by this correction.


## Word lifecycle — corrected Close overload trace (run 26, 2026-11-14)

Run 26 (43584217243, artifact 14109926135) completed successfully with all 16 workflow steps passing. 0x004CD154 is the registered TWordViwer.WordAppDocumentBeforeSave callback at viewer field +0x80, not BeforeClose. The separate TD32-named WordAppDocumentBeforeClose is 0x004CCBBC; its only direct bounded caller found is FillImgFldsForPrint at 0x004CCF8F, and no raw-pointer registration reference was found. Do not claim it is the live close event without further evidence.

TWordDocument.Close overloads: no-arg 0x0042FEB0 dispatches through interface slot +0x4D4; one-arg 0x0042FF08, two-arg 0x0042FF7C, and three-arg 0x0042FFF4 dispatch through +0x29C. The registered BeforeSave callback calls PreparePrintDocument (0x004CB108), uses Word _Document slot +0xD8, now mapped by TWordDocument.Set_Saved rather than Get_Saved; the earlier Saved-getter interpretation is withdrawn, conditionally displays the changed-document prompt, sets Cancel to 0xFFFF on Cancel, and directly invokes interface slot +0x29C with three OleVariant arguments (the same dispatch slot used by the three-argument wrapper at 0x0042FFF4) for Yes/No. 0x00430070 is SaveAs2000, not Close.

Still unresolved: concrete runtime target behind +0x29C; any separate close-event registration; page-side postMessage and close-time POST response semantics. The user's observed close behavior (changes apply even without pressing Save) remains authoritative and is not contradicted by this static trace. No native Linux runtime implementation is claimed.


## به‌روزرسانی Run 29 — 2026-11-14

Run 29 با شناسه `43589571290` و artifact `14111108881` با موفقیت تمام شد.

- `TWordViwer.GetDocFieldName` در بازه `0x004BB81C–0x004BC16F` فقط در شاخهٔ fallback و پس از ناموفق‌بودن مقایسهٔ نام فیلد، `SilentSaveEmwatDoc` را صدا می‌زند. این مسیر lookup فیلد است، نه شاهدی برای callback بستن سند.
- آدرس `0x004AEA78` در واقع `TfrmWordPrintOption.SetLetterReceivers` و `0x004AEBBC` تابع `TfrmWordPrintOption.FreePrinters` است؛ این دو helper عمومی ذخیره‌سازی سند نیستند و به وضعیت پنجرهٔ تنظیمات چاپ مربوط‌اند.
- `DeleteTempRAW` در `0x0044B01C` تابع `CloseAllWords` را فراخوانی می‌کند، اما فقط در شاخه‌ای پس از بررسی‌های فایل/فرآیند موقت.
- با وجود نام TD32 تابع `CloseAllWords`، چهار فراخوانی داخلی آن به `0x0044B0F8` می‌روند که TD32 آن را `GetFileVersion` نام‌گذاری کرده است. بنابراین از نام `CloseAllWords` نمی‌توان نتیجه گرفت که Word را می‌بندد؛ رفتار واقعی آن هنوز به‌طور مستقل اثبات نشده است. این مسیر نیز به cleanup فایل RAW مربوط است، نه connector اصلی نامه.

**نتیجه:** Run 29 رویداد Close یا POST نهایی هنگام بستن نامه را پیدا نکرد. اولویت بعدی باید کد صفحهٔ وبِ فرستندهٔ `postMessage` و نحوهٔ اعمال پاسخ HTTP باشد؛ از تکرار تحلیل نمادهای چاپ/cleanup که caller مرتبطی ندارند خودداری شود. رفتار مشاهده‌شدهٔ کاربر (اعمال تغییرات با بستن سند، حتی بدون Save) همچنان الزام قطعی محصول است.


## اصلاح برداشت از Save در آزمون بستن Word — 2026-11-14

کاربر دوباره آزمایش کرد و تأیید کرد که بدون فشردن دکمهٔ Save، با بستن Word فایل در الماس گام ثبت/ظاهر می‌شود. این نتیجهٔ انتها‌به‌انتها قطعی و الزام محصول است؛ اما ثابت نمی‌کند که خود Word در پشت صحنه سند را ذخیره نمی‌کند.

فرضیهٔ فنی محتمل این است که هنگام بستن، Word یا EMWAT یک Save/Silent Save انجام می‌دهد و سپس EMWAT خروجی نهایی را از مسیر پاسخ HTTP به مرورگر تحویل می‌دهد. این فقط فرضیه است و باید با trace زمان‌بندی‌شدهٔ COM و HTTP اثبات شود.

در ادامه سه مرحله جداگانه بررسی شوند: (۱) ذخیره‌شدن واقعی سند در Word هنگام close، (۲) جمع‌آوری artifact نهایی توسط EMWAT، (۳) تحویل پاسخ به مرورگر و ثبت آن در الماس گام. در مستندات از عبارت «ثبت بدون Save کاربر» استفاده شود، نه «انتقال بدون ذخیره‌شدن سند».


## Native Linux bridge transport — initial implementation (2026-11-14)

A first protocol-neutral Python transport layer now exists under `python/`. It binds only to IPv4 loopback, exposes `GET /healthz`, accepts opaque POST bodies at `/`, preserves the query string/body bytes for a future verified dispatcher, applies a configurable body-size limit and exact Origin allowlist, rejects unsupported methods/routes and sanitizes handler exceptions. It intentionally does not parse or synthesize the legacy XML envelope: the parameter child tag and complete close-response contract remain unproven.

Files: `python/src/emwat_linux/bridge.py`, `python/tests/test_bridge.py`, `python/pyproject.toml`; CI: `.github/workflows/python-bridge.yml`. This is a transport foundation only, not yet an end-to-end EMWAT connector. Verify the dedicated CI run before treating the milestone as green.


### Bridge transport CI correction and verification (2026-11-14)

The first CI attempts failed before meaningful tests because the workflow tried to install the package with `--no-build-isolation` while setuptools was not installed. CI was simplified to run the stdlib unittest suite with `PYTHONPATH=src`. The next test run exposed a fixture error: the valid XML sample exceeded the test server's 32-byte configured limit. The test limit was raised to 128 bytes and the oversized-body test to 129 bytes.

The transport also now returns `Access-Control-Allow-Origin` and `Vary: Origin` only when the request Origin exactly matches the configured allowlist. No wildcard CORS is used. This is necessary for browser JavaScript to read the localhost XHR response, but the actual Almas Gam origin must be configured and validated during integration.

**Verified:** Python bridge workflow run `43592145701`, commit `c705ed34ad9a9e87b42d7e2d85d3aa60aea83815`, conclusion `success`. Seven unit/integration tests passed. This verifies the transport behavior only; no legacy XML, Word, LibreOffice, or Almas Gam end-to-end compatibility is claimed.


## XML method-envelope parser added (2026-11-14)

Runtime response evidence confirms the observed close response begins with `<emwat version="1.0"><method class="EditWordDocument"><param name="wordConfig">`. This establishes the `param` child tag for that observed path. Added `python/src/emwat_linux/protocol.py` with a conservative UTF-8 parser for the outer `emwat → method → param` envelope. It preserves parameter values as opaque strings and rejects malformed XML, unsupported versions, duplicate names, nested markup, DTD/entity declarations and oversized input. It does not decode or interpret document data and does not implement a fake method response.

Tests: `python/tests/test_protocol.py`. CI verification is pending at the time of this entry. Service analysis also confirms query branches `invoke`, `init`, and `heartbeat`; exact init/heartbeat response contracts are still unknown.


## Protocol parser and allowlisted dispatcher — CI green (2026-11-14)

- Runtime evidence confirms the observed envelope: `emwat version="1.0"` → `method class="EditWordDocument"` → `param name="wordConfig"`.
- `python/src/emwat_linux/protocol.py` parses only this outer UTF-8 envelope and preserves parameter text as opaque strings. It rejects DTD/entities, malformed XML, unsupported versions, duplicate parameters, nested markup and oversized payloads.
- `python/src/emwat_linux/dispatcher.py` dispatches only explicitly registered method names. It never dynamically imports a class. Unknown methods return 501; malformed envelopes return 400. No real `EditWordDocument` handler has been registered and no success XML is fabricated.
- Transport security now includes IPv4-loopback-only bind, exact Host-header validation, required exact-allowlisted Origin by default, socket timeout, request/response size bounds, duplicate Content-Length rejection and sanitized exceptions.
- **CI:** `Python bridge transport` run #20, run ID `43592721635`, commit `2fa217ae83f33b80a7799ede4c75f2cc58b40d76`, conclusion **success**. 24 tests passed across transport, parser and dispatcher.

Next: recover exact heartbeat/init responses and remaining Word response schema; implement a real `EditWordDocument` adapter only after close-time document content and response semantics are understood. Keep the legacy apply-on-close behavior as a mandatory acceptance test.


### Strict HTTP framing — verified in CI run #22

The bridge now additionally rejects Host headers containing path/query/fragment components and validates Content-Length as one ASCII decimal value. Transfer-Encoding is rejected before body framing is considered. Tests were added for Host path injection, duplicate Content-Length and non-decimal Content-Length.

**CI:** `Python bridge transport` run #22 (`43593083176`), commit `22a803912b0fa92c3bb5537fb1f0c7952fda7615`, **success**; 27 tests passed.


## Application composition factory — CI green (2026-11-14)

Added `python/src/emwat_linux/application.py` with `create_bridge_server(...)`. It composes the IPv4 loopback HTTP server, conservative XML parser and explicit dispatcher registry. It requires callers to provide an exact Origin allowlist and explicit handler mapping; it does not silently enable any legacy operation. Integration tests verify the complete HTTP POST → XML parse → explicitly registered handler → HTTP response path and reject missing/unlisted origins.

**CI:** Python bridge transport run #24, ID `43593185429`, commit `27986ee96b45009283cd96eecde95110e1b9e448`, **success**; 29 tests passed. The registered handler in the integration test is only a fixture; no real `EditWordDocument` implementation exists yet.


## تحلیل جدید LoadDocument — Run 89
- Workflow #89 با موفقیت تمام شد و artifact آن بررسی شد.
- آدرس 0x00457050 تابع Emwatutils.Finalization در ماژول EmailUtil است؛ تنها caller مستقیم پیدا‌شده در TD32، TWordViwer.LoadDocument است. تابع دو رشته سراسری را با ورودی UnicodeString مقایسه می‌کند؛ معنی دقیق رشته‌ها هنوز باید decode شود.
- آدرس 0x00454B9C تابع Emwatutils.euGetASFileName(UnicodeString, UnicodeString) است و علاوه بر LoadDocument در توابع TIFF و تصویر نیز استفاده می‌شود. بنابراین مسیر به احتمال قوی filename/path normalization دارد، نه اینکه این تابع parser بایت‌های بدنه Word باشد.
- پس از این دو مرحله، LoadDocument از thunkهای runtime در 0x004012F8، 0x00401270 و 0x004012E0 استفاده می‌کند، سپس با global 0x0062F800 و constructor helper 0x004041BC یک object می‌سازد و virtual slot +0x10 را با data pointer و length فراخوانی می‌کند. نوع object و ماهیت دقیق عملیات هنوز قطعی نیست.
- بنابراین wordBody فعلاً باید به‌عنوان ورودی UnicodeString با semantics نامشخص ثبت شود؛ نه «قطعاً بایت خام» و نه «قطعاً مسیر فایل».
- Run #90 تکمیل شده است؛ نتیجه شناسایی TFileStream و مسیر نوشتن ورودی در بخش جدید همین سند ثبت شده است.


## تکمیل شواهد نام فایل در LoadDocument
- در رشته‌های LoadDocument پیام دقیق `DocFileName can not be null.` وجود دارد و مسیر کنترل تابع، رشته محلی تبدیل‌شده را از نظر طول صفر بررسی می‌کند و در صورت خالی بودن به این خطا می‌رود. این شاهد قوی است که آرگومان LoadDocument به‌عنوان نام فایل سند پردازش می‌شود، نه صرفاً بایت‌های بدنه.
- رشته‌های `word-document`، `ConfigXML data loaded.` و `Word Calling Mode: ` نیز در همان تابع وجود دارند. رشته‌های `.doc` و `.docx` در مسیر helper اعتبارسنجی/نرمال‌سازی نام فایل دیده می‌شوند؛ معنای دقیق شاخه‌ها هنوز بررسی می‌شود.
- تفسیر فعلی اصلاح شد: کلید بیرونی `wordBody` به LoadDocument داده می‌شود، اما درون LoadDocument مانند یک UnicodeString از نوع DocFileName بررسی و تبدیل می‌شود. اسم کلید به‌تنهایی نوع واقعی مقدار را اثبات نمی‌کند.


## Run 90 — شناسایی قطعی File Stream
- Run #90 (`43595049501`) با موفقیت تمام شد.
- تابع `0x004041BC` یک thunk به `rtl230.bpl!TFileStream.Create(UnicodeString, Word)` است؛ بنابراین object ساخته‌شده در `LoadDocument` یک `TFileStream` است، نه MemoryStream.
- `LoadDocument` یک رشته نام فایل را به سازنده می‌دهد و سپس از طریق virtual slot `+0x10`، pointer داده و طولی را که از ورودی `wordBody` گرفته شده به stream می‌نویسد. در نتیجه شواهد فعلی نشان می‌دهد ورودی `wordBody` در این مرحله داده/محتوای فایل است، در حالی که رشته محلی جداگانه نام فایل مقصد را تأمین می‌کند. Encoding، واحد دقیق length و مسیر مقصد هنوز قطعی نیست.
- مقدار mode برابر `0xFF00` است؛ تا بررسی calling convention و RTL دقیق، آن را به نام ثابت Delphi تبدیل نمی‌کنیم.
- رشته‌های `Word document file created.`، `word-document`، `ConfigXML data loaded.`، `Word Calling Mode: `، `image/tif`، `base64` و `Result word file content read successfully. try (%d)` وجود دارند و با ایجاد فایل/پردازش محتوای ورودی سازگارند.
- `0x00457050` تابع `Emwatutils.Finalization` و `0x00454B9C` تابع `Emwatutils.euGetASFileName` است؛ این دو را parser بدنه سند در نظر نمی‌گیریم.
- Run #90 هنوز قرارداد POST هنگام بستن Word و نحوه اعمال پاسخ در Almas Gam را مشخص نکرده است. گام بعدی: ردیابی مسیر مقصد فایل، stream دوم در `0x004B7C39` و ارتباط فایل تولیدشده با XML پاسخ.

- در ادامه همان تابع، یک `TFileStream` دوم در `0x004B7C3E` با همان مسیر مشتق‌شده و mode برابر صفر ساخته می‌شود؛ سپس اندازه stream گرفته شده و virtual slot `+0x0C` با buffer/count فراخوانی می‌شود. این مسیر با بازکردن مجدد و خواندن فایل سازگار است؛ نام دقیق متد تا resolve شدن slot در RTL قطعی اعلام نمی‌شود.


## Run 91 — چرخه قطعی ساخت و خواندن فایل
- Run #91 (43595953793) موفق شد؛ artifact 14114711446.
- 0x0062F800 به کلاس TFileStream در rtl230.bpl resolve شد و 0x004041BC سازنده TFileStream.Create(UnicodeString, Word) است.
- مسیر اول با mode 0xFF00 (fmCreate) فایل را ایجاد می‌کند و virtual slot +0x10 را با pointer/count صدا می‌زند؛ این slot در layout استاندارد TStream برابر Write است.
- مسیر دوم با mode صفر (fmOpenRead) همان stream را باز می‌کند و slot +0x0C را با buffer/count فراخوانی می‌کند؛ این slot برابر Read است. بنابراین چرخه create/write و سپس open-read/read تأیید شد.
- مسیر فایل و مقصد نهایی داده خوانده‌شده هنوز معلوم نیست. helperهای رشته‌ای 0x401270، 0x4012E0 و 0x401348 به slotهای unresolved می‌روند؛ نام یا encoding آن‌ها حدس زده نمی‌شود.
- گام بعد: trace ادامه LoadDocument بعد از خواندن فایل، مسیر مقصد و انتقال داده به Word/TIFF و پاسخ HTTP.


### Reverse engineering — Run 92

- Run #92 (43597403349) موفق بود؛ artifact 14114738491 بررسی شد.
- `LoadDocument` پس از خواندن فایل واسط، `TWordViwer.OnTmrAutoSave` را در 0x004B7A58 فراخوانی می‌کند. این یک anchor جدید برای تحلیل چرخه پس از بارگذاری Word است؛ هنوز callback بستن سند یا مسیر HTTP response بودن آن اثبات نشده است.
- `TWordViwer.AddCustomDocPropertiesToDic` در 0x004D1454 مستقیماً از LoadDocument فراخوانی می‌شود؛ این تابع CustomDocumentProperties را enumerate می‌کند و descriptorهای single/twin را با Add در mapهای مربوطه populate می‌کند.
- مسیر مستقل تصاویر/TIFF شناسایی شد: `CreateImageFile` فایل‌های مجزا را با `PrintWordDoc` و `TFileStream(fmCreate).Write` می‌سازد. `CreateTIFF.SeparteImages` نیز در ماژول چاپ/TIFF موجود است، اما caller مستقیم در محدوده اسکن‌شده پیدا نشد.
- هنوز هیچ قرارداد close-time POST یا payload نهایی HTTP از این run به دست نیامده است. این مسیرهای چاپ/TIFF را نباید با upload یا پاسخ اصلی EMWAT یکی دانست.
- بعدی: تحلیل بدنه کامل OnTmrAutoSave، callbackها و timer/VMT؛ سپس registration/callerهای مسیر TIFF/Print و بررسی اینکه آیا این مسیرها به Word editor اصلی متصل‌اند.


### Reverse engineering — Run 94

- Run #94 (43598550321) موفق بود؛ artifact 14115756587 بررسی شد.
- `TWordViwer.OnTmrAutoSave` در 0x004B8A84، تنها از `LoadDocument` در 0x004B7A58 به‌صورت CALL مستقیم فراخوانی شده است. در این مسیر، بدنه علاوه بر تنظیم حالت view/readonly/protected، اتصال OLE Word را برقرار می‌کند و callbackهای 0x004CD154، 0x004CD54C، 0x004CD9C0 و یکی از 0x004D00AC/0x004CE030 را ثبت می‌کند. پس نام تابع را نباید معادل «ذخیره خودکار هنگام بسته‌شدن» تفسیر کرد.
- 0x004CDB54 در واقع `TWordViwer.QuitWord` و 0x004C5D68 تابع `SetDocCaption` است. دو آدرس 0x004D68D4 و 0x004D531C نیز متدهای Remove دیکشنری Custom Document Properties هستند، نه helperهای AutoSave.
- پیام فعال‌نبودن Word در بدنه وجود دارد، اما ارتباطی با ارسال پاسخ نهایی ندارد.
- Run #95 برای trace مستقل handlerهای ثبت‌شده و helperهای اتصال OLE شروع شده است. هنوز close-time POST/payload نهایی کشف نشده است.


## Reverse-engineering update — Run 95 (2026-11-14)

- GitHub Actions analysis run `43599550286` succeeded; artifact `14115498934` inspected.
- TD32 names now identify `0x004CD154` as `TWordViwer.WordAppDocumentBeforeSave`, `0x004CD54C` as `WordAppNewDocument`, `0x004CD9C0` as `WordAppWindowActivate`, `0x004CE030` as `WordAppDocumentBeforePrintBGPrint`, and `0x004D00AC` as `LoadOptions`.
- `OnTmrAutoSave` stores callback addresses `0x004CD154` and `0x004CD54C` into object fields during the LoadDocument setup path. This supports callback registration, but exact COM event wiring/semantics remain unverified.
- `WordAppDocumentBeforeClose` at `0x004CCBBC` remains unproven as an active editor close callback; its only direct caller found is `FillImgFldsForPrint`.
- No close-time HTTP request/response or final document-return payload was established. Do not implement guessed protocol behavior.
- User-confirmed product requirement: closing Word is sufficient for the edited file to appear in Almas Gam; the native implementation must preserve this behavior using a verified LibreOffice lifecycle path.


### Run 96 — callback record layout

- Analysis run `43600693760` succeeded; artifact `14116641628` inspected.
- In `OnTmrAutoSave`, a Word-related object at `viewer + 0x44` receives callback/context pairs: `(+0x80,+0x84) → WordAppDocumentBeforeSave`, `(+0x90,+0x94) → WordAppNewDocument`, `(+0x98,+0x9C) → WordAppWindowActivate`, and `(+0x88,+0x8C) → LoadOptions or WordAppDocumentBeforePrintBGPrint`.
- The fourth callback selection tests `[viewer + 0x3C]`; later code can assign the same pair again. Exact event dispatch ABI is not yet resolved.
- Helpers identified: `0x0043F360` = Get_ScreenUpdating; `0x00440950` = Get_DisplayAutoCompleteTips; `0x00441C68` = WordApplication.Quit. No close-time payload/POST found.

## به‌روزرسانی تحلیل Word — 2026-11-14 (Run 97)

- Run 97 با موفقیت کامل شد و artifact آن بررسی شد.
- 0x00404FBC اکنون به‌طور قطعی به vcl230.bpl!TOleServer.SetConnectKind resolve شده است؛ این فراخوانی در راه‌اندازی OLE Word انجام می‌شود.
- 0x004013F8، 0x00401398 و 0x00401368 به‌ترتیب helperهای RTL برای پاک‌سازی آرایه، جست‌وجوی رشته و الحاق رشته هستند؛ آن‌ها dispatcher رویداد نیستند.
- 0x004C5D68 دو property از OLE را می‌خواند و در فیلدهای viewer ذخیره می‌کند؛ معنای نام‌گذاری‌شدهٔ propertyها هنوز معلوم نیست.
- 0x004CDB54 یک بررسی مبتنی بر System.Pos انجام می‌دهد؛ معنای رشته/شرط هنوز نیازمند بررسی است.
- teardown در OnTmrAutoSave شامل شاخه‌ای با TWordApplication.Quit و فراخوانی‌های interface از طریق VMT است. معنای slotهای teardown هنوز resolve نشده است.
- WordAppDocumentBeforeClose همچنان فقط یک direct caller قطعی در FillImgFldsForPrint دارد؛ اتصال آن به بستن عادی سند ثابت نشده است.
- هیچ payload یا درخواست HTTP زمان‌بندی‌شده در لحظهٔ close در Run 97 پیدا نشد.
- Run 98 برای بررسی helper 0x004BCA88 و slotهای teardown اضافه شده است.

## اصلاح یافته‌های Run 98 — 2026-11-14

- `0x004CDB54` در TD32 با نام `TWordViwer.QuitWord` ثبت شده است. تابع propertyای را از OLE می‌خواند و وجود literal ناشناخته در آن را بررسی می‌کند. اگر literal پیدا شود False و اگر پیدا نشود True برمی‌گرداند. caller بر اساس نتیجه یا از teardown عبور می‌کند یا شاخه‌ای با `TWordApplication.Quit` و interface calls را اجرا می‌کند. literal `0x004CDC14` هنوز decode نشده است.
- `0x004C5D68` نام نمادین `TWordViwer.SetDocCaption` دارد و از `OnTmrAutoSave` فراخوانی می‌شود. بدنه دو property از OLE می‌خواند و در `viewer+0x4C/+0x4D` ذخیره می‌کند؛ تفسیر قبلی به‌عنوان options sync قطعی نیست.
- `0x004BCA88` در واقع `TWordViwer.GetXmlFieldInfo` با اندازهٔ 12,688 بایت است؛ در `GetCaptionItemFont` و `WordAppDocumentBeforeClose` استفاده می‌شود، نه یک helper اختصاصی close.
- `WordAppDocumentBeforeClose` داده‌های field از مجموعه‌های `+0xE8/+0xEC` را پردازش و `GetXmlFieldInfo` را فراخوانی می‌کند. ثبت آن به‌عنوان event عادی close هنوز اثبات نشده است.
- Run 99 برای decode literal شرط QuitWord و بررسی interface tableها افزوده شد.


## Run 101 — تفکیک شرط فعال‌سازی Office از چرخه بستن سند (2026-11-15)

- GitHub Actions workflow run #101 با شناسه `43680106253` روی commit `cdf542e4bd486a63d92a1b26c41a05f30028ae70` با موفقیت پایان یافت؛ artifact `14148322936` دریافت و بررسی شد.
- خطای Run 100 صرفاً از فراخوانی scanner بدون آرگومان selector لازم بود؛ workflow با selector صریح `*` اصلاح شد و Run 101 کامل شد.
- literal در `0x004CDC14` اکنون decode شده است: `Activation` (UTF-16LE). تابع `TWordViwer.QuitWord` در `0x004CDB54` این substring را در رشته‌ای که از property شیء OLE در `viewer+0x44` می‌خواند جست‌وجو می‌کند.
- اگر `Activation` پیدا شود، `QuitWord` مقدار False می‌دهد؛ اگر پیدا نشود، True می‌دهد. در caller یعنی `OnTmrAutoSave`، نتیجه True شاخه‌ای را فعال می‌کند که پیام `<Office LISENCE>: Word is not activated. Close Method.` را ثبت/نمایش می‌دهد و سپس `TWordApplication.Quit` را فراخوانی می‌کند. بنابراین این شاخه کنترل فعال‌سازی Office و خروج از Word است؛ مدرکی برای ذخیره سند یا ارسال آن به Almas Gam نیست.
- در resourceهای BPL، فرم `TEmSettingForm` شامل کنترل‌های `rbAutoSave`، `rbDontSave`، `chkDntAskForSave` و `cbbAutoSaveInterval` است. این‌ها وجود تنظیمات ذخیره خودکار/عدم ذخیره و فاصله زمانی را ثابت می‌کنند، اما به‌تنهایی نشان نمی‌دهند که کدام گزینه در نصب کاربر فعال بوده یا مسیر ثبت نهایی نامه چگونه عمل می‌کند.
- یک مسیر جدا در ماژول `uSendLog` شناسایی شد: `TfrmShowAutoSaveFiles.WordAppDocumentBeforeClose` در `0x005EC580`، تابع `CloseWordApp` در `0x005EBDA8` را فراخوانی می‌کند؛ caller دیگر `btnShowFileClick` است. نام کلاس، فرم `TfrmShowAutoSaveFiles` و callerهای مستقیم نشان می‌دهند این handler متعلق به پنجره نمایش فایل‌های AutoSave است، نه اینکه لزوماً handler اصلی ویرایش نامه باشد. بدنه CloseWordApp روی مجموعه‌ای از اشیای Word/Document loop می‌زند و متدهای interface را صدا می‌زند؛ معنای دقیق هر slot هنوز resolve نشده است.
- این مسیر جدا را نباید با `TWordViwer.WordAppDocumentBeforeClose` در `0x004CCBBC` یکی دانست. دومی همچنان فقط caller مستقیم شناخته‌شده `FillImgFldsForPrint` دارد.
- نتیجه منفی پابرجاست: Run 101 هیچ close-time POST تازه، payload نهایی، یا اتصال اثبات‌شده‌ای از `CloseWordApp` به پاسخ HTTP ارائه نکرد.
- گام بعد: trace بدنه `TEmSettingForm` و ذخیره/خواندن گزینه‌های AutoSave، resolve کردن interface slotهای `CloseWordApp`، و بررسی اینکه callbackهای ثبت‌شده در WordViewer چگونه به مسیر پاسخ نهایی `EditWordDocument` می‌رسند. تا آن زمان production handler یا close protocol حدس زده نشود.


## Run 102 — AutoSave settings and separate AutoSave viewer lifecycle

- GitHub Actions run #102 (43681595513, commit 168793fd5e2dfaeff6036894409e7a5385944d31) completed successfully; artifact 14148712060 was inspected.
- TEmSettingForm.chkDntAskForSaveClick at 0x005EAA20 opens the current-user registry hive (0x80000001, HKCU) and performs multiple registry value writes. The values include settings associated with controls at instance offsets +0x3E0, +0x3D8, +0x3C4, +0x3C8, +0x3CC, and the AutoSave interval control at +0x3F4. For interval values 1–5 it multiplies a lookup-table value by 1000; otherwise it writes 0x2710 (10000 ms). Registry value names and complete semantic mapping still require resolving the referenced string constants and registry helper APIs.
- The settings resource confirms controls rbAutoSave, rbDontSave, chkDntAskForSave, chkSaveIOxmls, and cbbAutoSaveInterval. This proves the UI exposes AutoSave-related options; it does not prove which options were selected in the user's session or how the main editor's final registration works.
- TEmSettingForm.FormCreate at 0x005EAD94 delegates to inherited form creation, then invokes helper 0x00402A50 and 0x0040496C; those helper semantics and the exact read-side settings mapping remain unresolved.
- The small btnOkClick handler at 0x005EAA14 calls TCustomForm.Close via thunk 0x00404E84; it does not itself show persistence logic. The checkbox click handler is the one containing registry operations.
- The separate TfrmShowAutoSaveFiles.FormClose at 0x005EBF20 is called from its own Delete/FormCreate/finalization paths. Its WordAppDocumentBeforeClose callback at 0x005EC580 calls CloseWordApp only when a document interface's first word equals 0x2E; this is tied to the AutoSave-files viewer, not proven to be the main Word editor's close event.
- CloseWordApp at 0x005EBDA8 iterates a Word Documents collection, conditionally inspects/updates document items, and invokes interface slot +0x29C; exact COM method semantics remain unresolved. It does not establish an HTTP POST or final registration payload.
- No evidence in Run 102 links these registry settings or the AutoSave viewer teardown to the main editor's final Almas Gam registration request. Keep that protocol unknown until a concrete caller/payload/response chain is found.
- Next target: resolve registry helper APIs and string constants to map each setting key/value; separately resolve the +0x29C Word interface slot and identify actual event registration/dispatch for the main viewer's BeforeClose callback. Continue tracing the main editor's save/close-to-HTTP response path without conflating it with the AutoSave viewer.


## Run 103 — registry settings and Word lifecycle follow-up (2026-11-15)

- GitHub Actions run #103 (run ID `43682606812`, commit `b0f92c0f3298b1d92b41906691e84960f75f6ee7`) completed successfully: 36/36 steps; artifact `14149148019` (`emwat-word-lifecycle-analysis`).
- The settings handler `TEmSettingForm.chkDntAskForSaveClick` at `0x005EAA20` confirms a current-user registry flow: it creates/uses a registry object, selects root `HKEY_CURRENT_USER` (`0x80000001`), opens `Software\\Emwat\\Dynamic Config`, writes integer and Boolean values, then releases the registry object. The IAT/thunk map identifies `0x00404414` as `TRegistry.WriteInteger(UnicodeString, Integer)` and `0x00404424` as `TRegistry.WriteBool(UnicodeString, Boolean)`.
- Confirmed value names extracted from the Delphi UTF-16 string headers: `Logging Level`, `Save I/O Trace Files`, `Background Priniting` (original spelling), `Dont Ask Save On Print`, `Save Before Print`, and `AutoSaveInterval`.
- Handler mapping from the observed writes: component/object offsets `+0x3E0` → integer `Logging Level`; `+0x3D8` → Boolean `Save I/O Trace Files`; `+0x3C4` → Boolean `Background Priniting`; `+0x3C8` → Boolean `Dont Ask Save On Print`; `+0x3CC` → Boolean `Save Before Print`; `+0x3F4` → integer `AutoSaveInterval`. For interval selection values 1–5, the selected lookup-table value is multiplied by 1000 before writing; other values write 10000 ms. This is the save-side mapping; don't assume startup reads use the same helper path until found.
- Corrected a prior lead: `TEmSettingForm.FormCreate` at `0x005EAD94` calls `0x00402A50` (`user32!GetDesktopWindow`) and `0x0040496C` (`TWinControl.SetParentWindow`), not registry-read routines. Its short body does not load the persisted settings. The exact settings-load path remains unresolved.
- The `BeforeSave` callback body still performs a prompt and may dispatch the 3-argument Word `Close` overload through interface slot `+0x29C`; direct CALL xref scans do not resolve its callback wiring because the stored function pointer is assigned as data in `OnTmrAutoSave`. This is evidence of callback pointer storage, not yet proof of the COM event-sink ABI or final server registration.
- All four `TWordDocument.Close` overload wrappers were traced. The no-argument overload dispatches slot `+0x4D4`; overloads with one, two, or three optional arguments dispatch slot `+0x29C`. TD32 direct-call scans show no direct CALL xrefs for these wrappers; raw pointer matches occur in debug metadata, so do not infer which overload is used by the main editor solely from those scans.
- No verified close-time HTTP POST, response payload, or final Almas Gam registration operation was found. The user's observed behavior (closing Word without manually pressing Save still registers the document) remains an important runtime fact to reconcile, not a protocol proven by this static trace.
- Next targets: locate the *read-side* registry operations for `Dynamic Config` and the actual settings form initialization; trace callback record consumption / COM connection-point wiring around `OnTmrAutoSave`; identify real main-editor close and final local HTTP request/response chain. Keep the AutoSave files viewer's separate close handler isolated from the main editor.


### Run 104 update — 2026-11-15

- Word lifecycle analysis workflow #104 completed successfully (37/37 steps), artifact `14150300042`.
- Registry-related imports are present in the PE, including Win32 registry APIs and Delphi `TRegistry` read/write methods. The initial direct-thunk-only scan found zero call sites and is not sufficient to conclude that reads are absent.
- The initial post-read trace range began in non-code data and decoded zero instructions. The workflow was corrected to begin at the observed continuation address `0x004B7DE1`.
- Follow-up commits `743e6378` (IAT-indirect registry call scanner) and `a4027a70` (post-read range correction) trigger a new validation run. Do not promote their expected findings until the resulting artifact is inspected.
- Startup settings-read path, active main-editor close callback, close-time server registration request, and final registration payload remain unresolved.


### Run 113 update — main Word Viewer startup settings read (2026-11-15)

Workflow #113 (run ID `43688755518`) completed successfully; artifact `14151906706`. The startup registry-read path is now located in the main `TWordViwer` constructor at `0x004D0D24–0x004D0FE6` (correcting the previous “unresolved” status in Runs 103/104).

It opens `HKCU\\Software\\Emwat\\Dynamic Config` and conditionally reads:
- `Background Priniting` Boolean → viewer field `+0x3C` (default true).
- `Dont Ask Save On Print` Boolean → viewer field `+0x3D` (default true).
- `Save Before Print` Boolean → viewer field `+0x3E` (default false).
- `AutoSaveInterval` integer → viewer field `+0x88` (default 0; clamped to at least 10000 ms).

The constructor uses `ValueExists`, then `ReadBool` / `ReadInteger`, and releases the registry object. `Logging Level` and `Save I/O Trace Files` are not read in this constructor and remain unlocated. The exact timer/save semantics remain unproven. The close-time Almas Gam registration request and payload also remain unresolved.


### Runs 116–117 update — TETracer registry references (2026-11-15)

- Run #116 (ID `43699248792`) and Run #117 (ID `43703253785`) both completed successfully (37/37 and 38/38 steps respectively).
- Run #117 confirms a registry **write** path inside `TETracer.GetUniquePostfix`: it constructs `TRegistry` at `0x00467C99`, selects `HKEY_CURRENT_USER` at `0x00467CB7`, then calls `TRegistry.WriteBool` at `0x00467D63` and `TRegistry.WriteInteger` at `0x00467D75`.
- The two value-name pointers (`0x00467F2C`, `0x00467F64`) are not decoded in the artifact. Do not identify them as `Save I/O Trace Files` / `Logging Level` without string evidence.
- The `0x00466D16` hit is a raw pointer-reference result, not a proven call site. Its bounded context at `0x00466CE0` is incomplete (only one instruction decoded).
- Therefore `Logging Level` and `Save I/O Trace Files` remain unresolved on the read side. The four constructor-read settings from Run 113 remain confirmed. Main-editor close-time registration is still unresolved.


## Parallel analysis status — 2026-11-15

The project now has independent CI analysis lanes for Word request lifecycle, registry settings, filename/temp cleanup, and Python bridge transport.

### Latest verified runs

- Word lifecycle #121 (run 43707049641): completed successfully; artifact 14158949168. Reconfirmed callback record layout, registry contexts, and LoadDocument response path.
- Word request lifecycle #3 (run 43709706063): completed successfully, 13/13 steps; artifact 14159833681. Added complete LoadDocument ranges, BeforeSave prompt strings, and helper traces.
- Registry settings #4 (run 43709607471): completed successfully; artifact 14159692702. Confirmed TETracer read-side values and image/print registry subkey.
- Filename/temp cleanup #7 (run 43709510495): completed successfully; artifact 14160380463. Confirmed DeleteTempRAW process termination and temp-file cleanup helpers.
- Python bridge #42 (run 43709846976): completed successfully; 45 tests passed.

### Current confirmed findings

- Word's registered 0x004CD154 handler presents the Persian register-changes prompt and calls Document.Close on non-cancel paths. The TD32 symbol says BeforeSave; internal log strings say OnBeforeClose. Event-sink slot naming remains unresolved.
- Main Word settings read from HKCU\Software\Emwat\Dynamic Config include the four operational viewer values plus TETracer's Logging Level and Save I/O Trace Files. TETracer's Created IO Trace Count is a 15-count diagnostic trace quota.
- Image/print settings are stored separately under HKCU\SOFTWARE\Emwat\PrintParams.
- Exported CloseAllWords (0x0044AE98) can taskkill WINWORD.EXE and then invoke exported RemoveTempFiles (0x0044AD30), which calls exported DeleteTempRAW (0x0044B0F8) for temp-file masks. Exported GetFileVersion is at 0x0044B2DC. TD32 labels are mismatched; the external service invocation point remains unknown.
- Packet-level timing confirms the EditWordDocument request body is complete at 0.002154 s and the first response byte arrives at 54.560037 s: a 54.557883-second server-side wait. The 1.166 MB response transfers in about 1.362 ms. The returned DOC is rewritten: input 872,960 bytes; estimated complete response 875,008 bytes (+2,048); OLE first-directory-sector pointer changes 1698 → 1702 at offset 48. The exact Word/COM release event remains under investigation.
- The BPL writes wordBody bytes directly to a temp file. The Base64Decode call at 0x004B7E44 targets a different local value, not proven to be wordBody.

### Native implementation state

The Python bridge now matches the captured heartbeat and init routes, can serialize the observed response-word success envelope, and has separate local-XHR and parent-page origin allowlists. All 45 Python tests pass. The actual EditWordDocument handler, LibreOffice document lifecycle, and Almas registration integration are still unimplemented.

### Open questions

1. Map the callback-record offset +0x80 to the exact Word COM event name.
2. Trace the full close-to-registration path, including any other local invoke methods or browser-side response handling.
3. Identify where the service decodes the Base64 wordBody before it reaches the BPL.
4. Find the caller/invocation point for DeleteTempRAW.
5. Decode the remaining temp-path and image-print helpers before implementing their Linux equivalents.


### Response document comparison

The response-word payload is not an echo of the input wordBody. The pcap contains 17 sequence gaps (68 missing Base64 characters / 51 decoded bytes) inside the response document. Accounting for those missing capture bytes yields an estimated response size of 875,008 bytes versus 872,960 input bytes (+2,048). The OLE header's first-directory-sector pointer changes from 1698 to 1702. Full-file equality remains unverified because the capture is incomplete.


### Invoke wrapper/helper address clarification — 2026-11-15

The BPL export/API analysis resolves the earlier naming ambiguity. The public TEmwatMethod.Invoke entry is 0x0046C9E0 (export name; shared descendant VMT slot +0x0C). It calls the 433-byte inner dictionary/XML helper at 0x0046C82C, then dispatches the concrete PerformMethod through VMT slot +0x10. TD32 labels are misleading: 0x0046C82C is symbolized as Invoke, while 0x0046C9E0 is symbolized as Finalization. Use the wrapper/helper distinction in current work.


## به‌روزرسانی تکمیلی — 2026-11-15

- تحلیل PCAP برای درخواست `POST /?invoke=58351` پاسخ HTTP 200 با XML ریشه `response-word` و سند برگشتی `application/msword` با Base64 را نشان داده است. سند برگشتی در prefix سالم ضبط با ورودی یکسان نیست؛ به‌علت 17 شکاف TCP و 68 بایت گمشده، مقایسه کامل و اندازه دقیق پاسخ هنوز تأیید نشده‌اند. جزئیات در `docs/PCAP-EDITWORD-DOCUMENT-ROUNDTRIP.md` است.
- ساختار request در artifact مستقل تأیید می‌کند `wordBody` نمونه، Base64 سند OLE Compound File / DOC است و `requested-types` شامل `application/msword` می‌شود.
- `python/src/emwat_linux/protocol.py` اکنون serializer محدود و تست‌شده برای envelope موفق `response-word` دارد؛ این فقط codec است و handler تولیدی EditWordDocument محسوب نمی‌شود.
- CI پل پایتون در run #42 موفق شد: 45 تست.
- CI هسته بومی در run #104 موفق شد: 4 تست build/test و 4 تست sanitizer.
- workflow مستقل تحلیل Recovery Store اضافه شده و run #2 در حال اجراست؛ تا دریافت artifact هیچ مسیر یا پسوند recovery قطعی اعلام نمی‌شود.


- شاخه Recovery Store اکنون workflow مستقل دارد و run #2 آن موفق شده است. تحلیل فرم `TfrmShowAutoSaveFiles`، رویدادهای `FormClose` و `WordAppDocumentBeforeClose` و اتصال آن به Word Automation ثبت شده است.
- در کد فرم، literal فیلتر `*.easz` و literal `.easd` در string construction دیده شده‌اند. این‌ها شواهد مهم فرمت AutoSave هستند، اما هنوز نقش نهایی هر پسوند و مسیر ذخیره‌سازی قطعی نشده است.
- helperهای `euGetAutoSavePass`، `DoClearOldAutoSaveFiles`، `euClearOldAutoSaveFiles`، `euGetLocalAppDataPath` و `euGetWinTempPath` شناسایی و trace شده‌اند. workflow دوم برای resolve کردن مسیر، ماسک فایل و APIهای filesystem در حال اجراست.
- مستند جدید: `docs/RECOVERY-STORE-ANALYSIS.md`.


- در تحلیل بازیابی، `0x004043BC` به `TDirectory.GetFiles` و `0x004026B4` به `DeleteFileW` resolve شد. هر دو مسیر UI بازیابی و پاک‌سازی AutoSave از ماسک `*.easz` استفاده می‌کنند؛ بنابراین این پسوند اکنون به‌عنوان ماسک واقعی فهرست‌سازی فایل در این زیرسیستم تأیید شده است.
- helper `euGetLocalAppDataPath` از `SHGetSpecialFolderLocation` با CSIDL `0x1C` و `SHGetPathFromIDListW` استفاده می‌کند. هنوز اتصال مستقیم این ریشه به پوشه `.easz` ثابت نشده است.
- cleanup بر اساس سن فایل تصمیم به `DeleteFileW` می‌گیرد و مقدار مقایسه `0x18` است؛ واحد/معنای دقیق retention تا trace helper زمان تأیید نشده. workflow recovery-path run #3 برای همین و برای خواندن AutoSave password در حال اجراست.


## تکمیل شواهد 2026-11-15 (شاخه‌های موازی بعدی)

- رمز AutoSave در مسیر کد به `GetUserNameW` متصل است: نام حساب Windows، و در صورت شکست API مقدار fallback برابر `@25*gamsign*25@` است. الگوریتم رمزگذاری/بازکردن فایل هنوز جداگانه باید resolve شود.
- سیاست پاک‌سازی `.easz` با `FileAge`، `FileDateToDateTime`، `Now` و `HoursBetween` تأیید شد: فایل‌های با سن حداقل 24 ساعت به `DeleteFileW` سپرده می‌شوند.
- مسیر پایه AutoSave اکنون مشخص است: `GetTempPathW` + `temp-emwatASwf\\`; فایل‌های `*.easz` در این پوشه enumerate می‌شوند. در مستند به شکل `%TEMP%\\temp-emwatASwf\\*.easz` ثبت شد.
- در handler بازیابی، فایل انتخاب‌شده به `euResetMemory` داده می‌شود و مسیر دیگری با پسوند `.easd` ساخته می‌شود؛ رابطه دقیق این دو فایل هنوز در بررسی است.
- مستند ساختار درخواست: `docs/EDITWORD-REQUEST-SCHEMA.md`. نمونه request شامل `wordConfig` به‌صورت Base64 XML با 180 فیلد، 20 slot برای هرکدام از 7 خانواده فیلد امضاکننده، و `wordBody` به‌صورت Base64 فایل DOC/OLE است. مقادیر نامه و گیرندگان در مستند کپی نشده‌اند.
- workflow بازیابی run #5 (`43716527945`) برای تحلیل `euResetMemory` و اشیای داخلی در حال اجراست.
- workflow رویدادهای Word run #8 (`43716384031`) پس از اصلاح استخراج جدول callback در حال اجراست؛ نسخه قبلی به‌خاطر regex اشتباه فهرست callbackهای تولیدشده را خالی می‌گذاشت.


- parser مستقل `python/src/emwat_linux/word_config.py` اضافه شد تا لایه داخلی Base64/XML یعنی `wordConfig` را از envelope بیرونی جداگانه بخواند؛ مقادیر فیلدها را opaque نگه می‌دارد و decoding سراسری URL/Base64 انجام نمی‌دهد. تست‌های امنیتی/ساختاری این parser اضافه شد.
- CI پل پایتون بعد از این تغییر در run #44 با **53 تست موفق** پایان یافت. run #43 مربوط به commit میانی (45 تست) نیز موفق بود.

- **تصحیح مهم رمز AutoSave:** helper نام کاربر (`euGetAutoSavePass`) را برمی‌گرداند و caller مشخصی آن را با `@25*gamsign*25@` ترکیب می‌کند؛ اما هنوز ثابت نشده این رشته رمز آرشیو `.easz` باشد. مسیر بازیابی از SevenZip `T7zInArchive` استفاده می‌کند و در `euResetMemory` در صورت نبودن رمز، رشته دیگری (`mW@Tlogs43end_+`) به slot مجازی `+0x44` داده می‌شود. تا تعیین setter و متدهای آرشیو، رمز واقعی `.easz` نامشخص است. جزئیات در `docs/RECOVERY-STORE-ANALYSIS.md`.
- یک لایه نرمال‌سازی مستقل برای درخواست واقعی `EditWordDocument` اضافه شد: `python/src/emwat_linux/editword_request.py`، که `wordConfig` را با parser داخلی می‌خواند، `wordBody` را به بایت‌های سند تبدیل می‌کند و `signData` را عمداً به‌صورت متن opaque نگه می‌دارد. CI پل Python run #46 با **58 تست موفق** پایان یافت.

## اصلاح برداشت‌ها و نتایج جدید — 2026-11-15

- **اصلاح شاخه رویداد Word:** آدرس‌های استخراج‌شده از `0x00627B74` callback نیستند؛ run #9 نشان داد آن‌ها pointer به رشته‌های خطا مانند `Request XML is invalid.`، `Can not open document.` و `Temp path not Found.` هستند. workflow از run #11 به‌جای disassemble کردن این ناحیه، کل error-string map را decode می‌کند. callback اصلی `BeforeSave` در `0x004CD154` همچنان مستقل و قطعی است.
- **شناسایی آرشیو بازیابی:** run #7 کلاس `Sevenzip.T7zInArchive` را در مسیر `euResetMemory` شناسایی کرد. این مسیر از یک reader هفت‌زیپ استفاده می‌کند؛ پس `.easz` به‌احتمال زیاد یک archive است، اما فرمت دقیق فایل و password آن تا تکمیل نگاشت متدهای VMT قطعی نیست.
- رشته `mW@Tlogs43end_+` در مسیر `euResetMemory` به slot مجازی `+0x44` داده می‌شود؛ `euGetAutoSavePass` نیز نام حساب را برمی‌گرداند و caller دیگری آن را با `@25*gamsign*25@` ترکیب می‌کند. هیچ‌کدام را تا نگاشت setter و مسیر بازکردن آرشیو، رمز قطعی `.easz` اعلام نمی‌کنیم.
- run #7 تحلیل recovery-path موفق شد؛ run #9 و #10 برای فهرست و trace متدهای `T7zInArchive`/`T7zOutArchive` در حال اجرا هستند. run #10 شاخه event error-map نیز موفق شد؛ run #11 نسخه کامل‌تر جدول را decode می‌کند.
- پل Python اکنون 58 تست موفق دارد؛ دو جزء جدید `word_config.py` و `editword_request.py` هنوز به handler تولیدی و موتور LibreOffice متصل نشده‌اند.

- run #11 شاخه error-map با موفقیت تمام شد و رشته‌های خطای Word/Excel، خطای تصویر، لغو عملیات، سطح‌های log و گزینه‌های زمان AutoSave را استخراج کرد. مستند جدید `docs/WORD-ERROR-MAP.md`؛ این جدول callbackهای COM نیست.

## به‌روزرسانی تحلیل AutoSave و بازیابی — 2026-11-15

- دو اجرای موازی recovery-paths (#9 و #10) با موفقیت تمام شدند؛ artifactها `14163436366` و `14163367757` هستند.
- مسیر بازیابی به کلاس SevenZip `T7zInArchive` متصل شد. متد `SetPassword` در `0x00453860` رشته را در فیلد `+0x58` قرار می‌دهد و از مسیر callback استخراج استفاده می‌کند؛ ارتباط دقیق آن با dispatch `euResetMemory +0x44` هنوز فرضیه قوی است، نه اثبات نهایی. مسیر `euResetMemory` در `0x00456F00` در صورت نیاز مقدار پیش‌فرض `mW@Tlogs43end_+` را از طریق dispatch مربوط به رمز عبور می‌فرستد.
- نام کاربری ویندوز و fallback `@25*gamsign*25@` متعلق به مسیر جداگانه `euGetAutoSavePass`/پاک‌سازی هستند؛ آن‌ها را رمز بازیابی `.easz` فرض نکنید.
- متدهای بازکردن آرشیو، فهرست‌کردن آیتم‌ها و استخراج در `T7zInArchive` ردیابی شده‌اند. نگاشت دقیق slotهای `+0x0C` و `+0x3C` در `euResetMemory` و ماهیت دقیق فایل `.easd` هنوز باز است.
- جزئیات و محدودیت‌های شواهد در [RECOVERY-STORE-ANALYSIS.md](RECOVERY-STORE-ANALYSIS.md) ثبت شده است.


### یافته تکمیلی SevenZip plugin

- کلاس `T7zPlugin` و factory مشترک `CreateObject` شناسایی شدند؛ `GetInArchive` و `GetOutArchive` هر دو از این factory استفاده می‌کنند.
- مسیر `euUnArchive` یک caller مستقیم برای constructor پلاگین است؛ مسیر `euResetMemory` از helper جداگانه `CreateOutArchive` استفاده می‌کند. این دو مسیر نباید یکی فرض شوند.
- `CryptoGetTextPassword2` از طریق thunk `0x00404734` سازنده `TObjectList` را صدا می‌زند؛ class pointer آن از global `0x0062FBB8` می‌آید و list در offset `+0x2C` ذخیره می‌شود. این هنوز منبع متن رمز writer را مشخص نمی‌کند. `T7zOutArchive.SetPassword` همچنان stub بی‌اثر است.
- نگاشت دقیق dispatch رمز `euResetMemory +0x44` به `T7zInArchive.SetPassword` هنوز اثبات نشده؛ گزارش recovery این عدم قطعیت را صریحاً اصلاح کرده است.


- آخرین تحلیل مستقل plugin run `43719323732` با موفقیت تمام شده و artifact آن بررسی شده است. تحلیل تکمیلی برای ردیابی `euUnArchive` با run `43720247793` با موفقیت تمام شد؛ artifact `14164382428` بررسی شده است. اجرای class-base analysis با run `43721251511` نیز موفق شد؛ artifact `14164434028` بررسی شده است.


### فرضیه تازه مسیر استخراج بازیابی

- traceهای جدید `T7zInArchive.OpenFile`، `ExtractTo`، `SetPassword` و `PrepareOperation` نشان می‌دهند رمز در فیلد `+0x58` نگه‌داری و از مسیر callback استخراج مصرف می‌شود؛ `CryptoGetTextPassword` و `SetPasswordCallback` خودشان stub هستند.
- سه dispatch در `euResetMemory` از نظر امضا و رفتار با ترتیب `SetPassword` → `OpenFile` → `ExtractTo` سازگارند. این فعلاً فرضیه قوی است، نه نگاشت قطعی VMT.
- پاک‌سازی فایل‌ها به‌طور مستقل با RTL resolve شد: `TDirectory.GetFiles("*.easz")`، `FileAge`، `HoursBetween` و حذف فایل‌های قدیمی‌تر از ۲۴ ساعت با `DeleteFileW`.
- جزئیات و محدودیت‌ها در بخش ۱۷ `docs/RECOVERY-STORE-ANALYSIS.md` ثبت شده‌اند.


- مسیر `euUnArchive` جدا از `euResetMemory` است: از constructor کلاس `T7zPlugin` استفاده می‌کند و با slotهای `+0x28/+0x10/+0x18` روی مجموعه‌ای از آیتم‌ها کار می‌کند. معنای دقیق slotها هنوز مشخص نیست؛ این مسیر را نباید با پروتکل بازیابی .easz یکی دانست.


- handler adapter جدید در `editword_handler.py` پاسخ موفق را با serializer ثبت‌شده `response-word` می‌سازد. پاسخ لغو باید با factory اجباری تزریق شود؛ تا وقتی payload لغو اصلی معلوم نیست، status/body حدس زده نمی‌شود. CI run `43721322012` با ۶۹ تست موفق است.


- تحلیل بعدی برای تعیین ارث‌بری و VMT کلاس پایه `T7zArchive` با run `43721583502` شروع شده است. index کلاس پایه جدا ذخیره می‌شود تا traceهای سنگین فقط روی wrapperهای reader/writer انجام شوند؛ run قبلی گسترده‌تر `43721251511` هنوز در حال اجراست.


## همگام‌سازی اجرای اخیر — 2026-11-15

- هماهنگ‌کننده سند در `document_coordinator.py` اکنون callbackهای تغییر/ذخیره را با `RLock` در برابر پایان نشست همگام می‌کند. بعد از دریافت Close، callbackها پیش از export غیرفعال می‌شوند؛ eventهای دیررس هنگام export یا بعد از بازگشت پاسخ دیگر state نهایی را تغییر نمی‌دهند.
- تست جدید این رفتار را در زمان export و پس از برگشت پاسخ پوشش می‌دهد. Python CI run `43722184809` موفق شد: **۷۰ تست** پاس شدند. اجرای قبلی `43722182876` نیز با ۶۹ تست موفق بود.
- تحلیل SevenZip base-class run `43721583502` موفق شد؛ artifact `14165155588` بررسی شد. برای نگاشت قطعی interface slots، workflow جدیدتر اکنون `resolve_delphi_vmt_slots.py` و `trace_delphi_interfaces.py` را روی کلاس‌های `T7zArchive`، `T7zPlugin`، `T7zInArchive` و `T7zOutArchive` اجرا می‌کند.
- شاخه‌های موازی جدید: SevenZip interface/VMT run `43722345225`، Word lifecycle `43722341754`، Word event sink `43722341799` و BPL method index `43722341778`؛ هنوز نتیجه نهایی آن‌ها را اعلام نمی‌کنیم.


- اصلاح تکمیلی هماهنگ‌کننده: غیرفعال‌سازی callbackها بلافاصله پس از برگشت `wait_for_close` انجام می‌شود، پیش از تفکیک نتیجه `CLOSED` یا `CANCELLED`. تست جدید رویدادهای دیررس پس از لغو را نیز پوشش می‌دهد. CI run `43722805637` موفق شد: **۷۱ تست** پاس شدند.


### هویت interface بازیابی SevenZip مشخص شد — 2026-11-15

- artifact `14165136040` از run `43722345225` بررسی شد. `CreateOutArchive` در واقع شیء `T7zInArchive` را با VMT `0x004525B0` می‌سازد و interface pointer را از `Self+0x70` برمی‌گرداند.
- جدول interface کلاس ۷ ورودی دارد؛ ورودی ششم با `IOffset=0x70` دقیقاً با pointer برگشتی منطبق است. IID آن `022cf785-3ece-46ef-9755-291fa84cc6c9` و VTable آن `0x00452420` است.
- پس سه dispatch مسیر `euResetMemory` در slotهای `+0x44/+0x0C/+0x3C` روی همین interface سفارشی اجرا می‌شوند. نام متدهای متناظر هنوز نهایی نیست؛ workflow بعدی خروجی vtable را تا slot `+0x4C` گسترش داده تا نگاشت دقیق تأیید شود.


## همگام‌سازی شاخه‌های COM و بازیابی — 2026-11-15

- Methods BPL run `43722341778` / artifact `14165431103`: `WordAppDocumentBeforeClose` در `0x004CCBBC` helper `0x004BCA88` را صدا می‌زند؛ این helper همچنین از `GetCaptionItemFont` استفاده می‌شود، بنابراین close-specific یا network/save نیست. caller مستقیم `0x004CCBBC` همچنان `FillImgFldsForPrint` است؛ ثبت زنده‌ی event هنوز اثبات نشده.
- Word event sink run `43722990625` / artifact `14165586257`: GUIDهای server-data با COM metadata ورد همخوانی دارند؛ `000209FF` مربوط به ApplicationClass و `00020906` مربوط به DocumentClass است. فهرست شامل IIDهای ApplicationEvents و ApplicationEvents2 هم هست. این metadata، callback-pointer table نیست.
- runهای در حال اجرا: SevenZip vtable با ۲۰ slot (`43722990639`)، Word event RTL helper trace (`43723423283`)، recovery Delete handler (`43723328264`)، Word lifecycle (`43722990611`) و Methods BPL (`43722990637`). نتیجه‌ی هیچ‌کدام تا زمان بررسی artifact نهایی اعلام نمی‌شود.


- نگاشت `+0x0C` اصلاح و قطعی شد: thunk `0x004522E9` به `T7zInArchive.OpenStream` می‌رسد؛ `IInStream` نوع خروجی متد است، نه ورودی آن. متد یک UnicodeString مسیر آرشیو می‌گیرد و stream را می‌سازد/برمی‌گرداند. caller فرم Delete نیز مسیر `.easz` را به‌صورت UnicodeString پاس می‌دهد.


- نگاشت هر سه slot رابط بازیابی از artifact `14165676602` تأیید شد: `+0x0C → OpenStream(UnicodeString) -> IInStream`، `+0x3C → SetPassword(UnicodeString)` و `+0x44 → T7zArchive` virtual constructor. `SetPassword` پس از ذخیره رشته در `Self+0x58`، callback می‌سازد و `IInArchive.Extract` را برای همه‌ی آیتم‌ها فراخوانی می‌کند. trace کامل Delete نشان داد آرگومان اول مسیر آرشیو و آرگومان دوم رشته‌ی تولیدشده توسط helper `0x0044A998` است.


- جزئیات callback آرشیو هم تفکیک شد: `SetPassword` از typeinfo آدرس `0x0045391C` استفاده می‌کند؛ `ExtractTo` از `0x00453850` و contextهای `Self+0x50/+0x54`. هر دو روی interface داخلی slot `+0x1C` را با `indices=NULL` و `numItems=-1` صدا می‌زنند؛ `testMode` در `SetPassword` صفر و در `ExtractTo` وابسته به پارامتر Boolean است. نوع دقیق callback و مقصد خروجی هنوز در شاخه‌ی جاری بررسی می‌شود.


- slot داخلی `+0x1C` اکنون با اطمینان به‌عنوان `IInArchive.Extract` شناخته می‌شود: متدهای wrapper به نام‌های `ExtractItem` و `ExtractTo` نیز همین slot را با آرگومان‌های item/test-mode خود فراخوانی می‌کنند. بنابراین `SetPassword` در این مسیر عملاً یک درخواست Extract برای همه‌ی آیتم‌ها با callback اختصاصی می‌فرستد؛ مقصد callback هنوز در دست بررسی است.


## تکمیل trace فراخواننده‌ی بازیابی — 2026-11-15

- Recovery workflow run `43723328264` / artifact `14165058222`، handler کامل `TfrmShowAutoSaveFiles.Delete` را استخراج کرد.
- مسیر آرشیو انتخاب‌شده از فیلد `+0x20` آیتم لیست با `UStrLAsg` به local `[ebp-4]` کپی می‌شود؛ این همان آرگومان اول `euResetMemory` است و به `OpenStream(UnicodeString) -> IInStream` می‌رسد.
- local `[ebp-8]` بلافاصله قبل از فراخوانی توسط helper `0x0044A998` تولید می‌شود و آرگومان دوم `euResetMemory` است؛ این رشته به `SetPassword` می‌رسد. معنای دقیق helper و رشته هنوز باید decode شود.
- caller، `ECX=0` و دو Boolean برابر 1 می‌فرستد؛ بنابراین شاخه‌ی fallback constructor با `mW@Tlogs43end_+` فعال است.
- بعد از `euResetMemory`، helper `0x004563A8` با همان دو رشته مسیر/مقدار دیگری می‌سازد و سپس `0x004565DC` و `0x004555D8` اجرا می‌شوند. این سه helper در شاخه‌ی بعدی trace می‌شوند تا مقصد `.easd` مشخص شود.


### تکمیل تحلیل callbackهای SevenZip و registry — 2026-11-15

- artifact 14166161804 از run 43723896564 نشان داد T7zInArchive.SetPassword فقط مقدار رمز را ذخیره نمی‌کند: callback استخراج را می‌سازد و IInArchive.Extract را برای تمام آیتم‌ها با testMode=0 فراخوانی می‌کند.
- PrepareOperation مسیر callback/context در Self+0x50/+0x54 را از مسیر استفاده از رشته‌ی Self+0x58 جدا می‌کند. مقصد نهایی stream هنوز اثبات نشده است.
- ExtractTo از callback type-info متفاوت (0x00453850) استفاده می‌کند؛ SetPassword از 0x0045391C.
- artifact 14165369436 توابع registry را resolve کرد: 0x404414=WriteInteger، 0x404424=WriteBool، 0x40441C=ReadInteger، 0x40442C=ReadBool و 0x404454=ValueExists.
- مستندات تفصیلی در بخش‌های ۲۱ و ۲۲ docs/RECOVERY-STORE-ANALYSIS.md ثبت شد؛ commit: d17a801d0d02f12e4a6b286af7aa1e21a9e691ac.
- recovery-path run 43724386278 در آخرین بررسی در حال اجرا بود. Word lifecycle run 43722990611 با موفقیت کامل شد. مقصد استخراج و ثبت نهایی نامه هنوز قطعی نیست.


### Recovery caller trace correction and parallel callback analysis — 2026-11-15

- Recovery-path run 13 completed successfully (run ID `43724386278`, artifact `14165938809`). The full `euResetMemory` call sequence and the recovery form's `Delete` caller were rechecked.
- `0x0044A998` is TD32-symbolized as `Emwat.Sys.MyMessageDialog`; it is the producer of the second string passed by the recovery Delete handler into `euResetMemory`, and that string reaches `T7zInArchive.SetPassword` via interface slot `+0x3C`. Its exact dialog/output semantics remain unknown. It is not `euGetAutoSavePass`.
- `euGetAutoSavePass` at `0x00456B78` remains a separate `GetUserNameW` helper used by cleanup/logging paths; its result is not proven to be the `.easz` password.
- `0x004563A8` is `FixDirectionInFarsiNumericMode`; `0x004565DC` is `DirIsEmpty`; `0x004555D8` is `ForceForegroundWindow`; `0x0045574C` is `euGetFileSize`. These helpers are now classified and no longer treated as unknown password/extraction helpers.
- The `.easd` suffix is appended in the recovery Delete path after a string-normalization helper call, but the actual archive extraction output destination and the relation of the `.easd` path to that output remain unresolved.
- A new independent workflow, `analyze-recovery-callback-contracts.yml`, is tracing the SevenZip interface slot `+0x44`, callback RTTI at `0x0045391C`/`0x00453850`, and the recovery caller chain. Workflow runs 1 and 2 are queued/in progress as of this update.
- Detailed findings and correction are recorded in `docs/RECOVERY-STORE-ANALYSIS.md` section 23 (commit `b753390bd421047e22d072b1012d9be3d829015a`).


### تکمیل ردیابی callbackهای آرشیو بازیابی — 2026-11-15

- اجرای recovery callback-contracts شماره ۲ با موفقیت تمام شد؛ artifact `14165994624` متد `T7zArchive.$bctr` در `0x0045392C` را تأیید کرد: رشته‌ی آرگومان در `Self+0x44` ذخیره می‌شود و پرچم `Self+0x40` بر اساس خالی نبودن آن تنظیم می‌شود.
- در مسیر `euResetMemory`، رشته‌ی fallback یعنی `mW@Tlogs43end_+` به همین سازنده می‌رسد؛ این رشته جدا از مقدار دوم است که از `MyMessageDialog` می‌آید و به `SetPassword` می‌رسد.
- دو اشاره‌گر callback در `0x00453850` و `0x0045391C` به رکوردهای ۱۶‌بایتی یکسان با IID رابط `IArchiveExtractCallback` اشاره می‌کنند؛ دو مسیر callback از یک قرارداد COM استفاده می‌کنند.
- `PrepareOperation` شاخه‌های متفاوتی بر اساس `Self+0x3C`، callback/context در `Self+0x50/+0x54` و رشته‌ی `Self+0x58` دارد. نگاشت قطعی فیلدها به نام propertyها و مقصد واقعی فایل خروجی هنوز در حال بررسی است.
- مستندات به‌روزشده: `docs/RECOVERY-STORE-ANALYSIS.md` بخش‌های ۲۴ و ۲۵؛ commit `f81be2be436a1ec042ee77c15f79611c4997a89d` و commit قبلی callback IID `9cd603b96648220b84c878eb3782b36dd3e02cc4`.
- workflow مستقل callback-contracts شماره ۳ برای disassembly هدف‌های غیر-TD32 و decode رشته‌های prompt در صف اجراست.


## همگام‌سازی موازی — 2026-11-16 (صبح)

- چهار شاخهٔ تحلیل مستقل از commit `cfdb4c0c` به‌طور هم‌زمان در حال اجرا هستند: recovery/SevenZip، Word lifecycle، Word event sink و close/response chain. تا زمان تکمیل و بررسی artifactها، هیچ نتیجه‌ای از آن‌ها قطعی گزارش نمی‌شود.
- Artifact close/response chain run `43815879141` بررسی شد: wrapperهای `TWordDocument` نگاشت `Get_Saved → slot +0xD4`، `Set_Saved → +0xD8`، `Get_Content → +0xDC` و `Save → +0x2B8` را تأیید می‌کنند. بنابراین slot `+0xDC` در `OnControlerNotify` با Save/Close یکی نیست؛ قرارداد آرگومان `-1` و payload خروجی همچنان باز است.
- Python bridge run `43816121607` پس از اصلاح fixture مربوط به encoding با موفقیت کامل شد. خطا از انتظار اشتباه تست برای decode کردن فیلد plain بدون `encryption=urlencoded` بود؛ رفتار decoder دست‌نخورده ماند.
- چهار workflow قدیمی Python/UNO/asset inventory همچنان سبز هستند: 86 تست Python، 8 تست UNO و صفر template Word در آرشیو نصب‌کننده. این نتایج به‌تنهایی صحت end-to-end با Almas را ثابت نمی‌کنند.


### تکمیل شاخهٔ event sink — 2026-11-16

- Event sink artifact run `43815900228` بررسی شد. در مسیر `OnTmrAutoSave`، event recordهای `+0x80/+0x90/+0x98` به‌ترتیب به callbackهای BeforeSave، NewDocument و WindowActivate متصل می‌شوند؛ `+0x88` نیز به callback `0x004D00AC` به‌صورت شرطی اشاره می‌کند.
- برای `WordAppDocumentBeforeClose` در `0x004CCBBC` نه pointer reference مستقیم پیدا شد و نه assignment در event-record block؛ تنها caller مستقیم bounded آن `FillImgFldsForPrint` است. پس فعال بودن آن به‌عنوان main-editor event هنوز اثبات نشده.
- مستندات COM dispatch با این تفکیک به‌روزرسانی شد؛ اتصال event recordها به COM connection point و نام callback چهارم همچنان در شاخهٔ Word lifecycle دنبال می‌شود.
- Python bridge run `43816293635` پس از اصلاح دو انتظار plus/escaped-plus موفق شد؛ این run وضعیت سبز فعلی تست‌های Python را تأیید می‌کند.

## تکمیل trace مسیر Rec/CC — 2026-11-16

- Word custom-property helper run `43816241948` موفق شد؛ artifact `14201844295` رشته‌های کلیدی `FillPrintOptionForm` را decode کرد.
- `0x004D1B30` با logهای `FillPrintOptionForm method called/succeed` شناخته شد؛ نام موقت `ShowRecAndCcOptionForm` کنار گذاشته شد.
- کلید `tokenizedReceivers` و delimiter برابر U+2020 (`†`) تأیید شدند.
- چهار شناسهٔ config literal نیز تأیید شدند: `Receivers`، `ReceiverDeps`، `ccReceivers` و `ccReceiverDeps`.
- این تابع پنج بار `SetFieldValue` را صدا می‌زند و collectionهای موازی viewer را پردازش می‌کند. اتصال دقیق هر collection به فیلد نهایی و معنای payloadها هنوز نیازمند config واقعی/نمونهٔ بی‌خطر است.
- Python run `43816293635` سبز است: **99 تست، 98 پاس و 1 تست اختیاری skip**. آزمون URL-encoding اکنون رفتار native یعنی `+` به فاصله و `%2B` به علامت جمع را پوشش می‌دهد.



### شاخهٔ دوم SevenZip در Controller Notify — 2026-11-16

- مسیر `TWordViwer.OnControlerNotify` علاوه بر خواندن Word `Content`، شاخه‌ای جداگانه دارد که دو stream می‌سازد، دو مسیر با پسوندهای `.easd` و `.easz` آماده می‌کند و آن‌ها را به `euUnArchive` می‌دهد.
- `euUnArchive` یک `T7zPlugin` می‌سازد و وارد مسیر archive-facing SevenZip می‌شود؛ کلاس `T7zOutArchive` در همان BPL متدهای AddStream و SaveToFile دارد. جهت دقیق عملیات و اینکه این مسیر همان recovery Delete است هنوز قطعی نیست.
- این شاخه به‌عنوان «paired stream/archive workflow» ثبت شد؛ هنوز آن را با ثبت نهایی نامه در Almas یکی نمی‌دانیم.


### تکمیل مسیر رمزگشایی Base64 فیلدهای Word — 2026-11-16

- مسیر `encryption=base64` در `SetFieldValue` به helper بومی `0x00473700` ختم می‌شود: جدول ۶۴کاراکتری در `0x00627F98`، decode چهارتایی، مدیریت padding و رد lookup نامعتبر تأیید شد.
- `0x00473608` طول خروجی را با توجه به padding انتهایی محاسبه می‌کند؛ `0x00402908` نیز thunk تابع Windows `WideCharToMultiByte` است.
- decoder پایتون فعلی سخت‌گیرانه‌تر از مسیر باینری به‌نظر می‌رسد؛ فعلاً validation را شل نمی‌کنیم و تست‌های سازگاری برای Base64 معتبر/نامعتبر و delimiter نقطه‌ای اضافه/بررسی می‌شوند.


### تعیین callback چاپ در event sink — 2026-11-16

- آدرس `0x004D00AC` که به‌صورت شرطی در رکورد event ثبت می‌شد، به `TWordViwer.LoadOptions` تعلق دارد؛ log ابتدای تابع صریحاً `Document.OnBeforePrint called.` را نشان می‌دهد.
- بنابراین event record شامل BeforeSave، BeforePrint، NewDocument و WindowActivate است. این یافته callback چهارم را از مسیر close جدا می‌کند؛ برای BeforeClose همچنان registration اثبات نشده است.


### Python Base64 compatibility checkpoint — 2026-11-16

- Run `43818155017` passed: 99 tests, 1 skipped. Tests now cover padded Base64 with one and two padding characters, unpadded complete quartets, invalid alphabet, incomplete quartet, and whitespace rejection.
- Decoder no longer strips whitespace before Base64 decoding, matching the native lookup-table path where whitespace is not normalized. The separate outer `wordConfig` XML Base64 parser still has its own whitespace handling and was not changed.
- Current test suite is green after this compatibility change; earlier failures in runs `43817515071`, `43817520122`, and `43817688638` were transient implementation/test-literal issues and are superseded by the green run.


### ساختار XML field model — 2026-11-16

- VMT/TD32 اطلاعات `TXMLFieldType` را تثبیت کرد: interface با offset `0x50` و propertyهای واقعی `Id`, `Mimetype`, `Encryption`, `Separator`, `Concater`, `ParamId`, `IsNew`.
- مدل viewer جداگانه شامل `TXmlWordConfigField` با اندازهٔ instance برابر `0x10` و `TXmlWordConfigTwinField` با اندازهٔ `0x18` است؛ `TDocumentCProperty` نیز type مستقل دارد.
- معنی عملیاتی separator/concater هنوز مشخص نیست؛ workflow جدید getter/setterها و VMT این کلاس‌ها را بررسی می‌کند تا قبل از پیاده‌سازی، join behavior حدس زده نشود.


### LibreOffice process lifecycle hardening — 2026-11-16

- Added a shared child-process shutdown helper. Both failed-open cleanup and normal handle cleanup now attempt `wait()` after `kill()`, avoiding an unreaped soffice child/zombie; already-exited processes are left untouched.
- Python bridge workflow `43818676999`: 101 tests passed, 1 skipped.
- LibreOffice UNO integration workflow `43818676967`: 10 tests passed, including a live DOCX open/close/export to legacy Word format.
- This is lifecycle hardening only; it does not change EMWAT field mapping, cancellation protocol, or Almas registration semantics.


### رفع ابهام چرخهٔ بستن Word — 2026-11-16

- مسیر اصلی اکنون مشخص است: callback ثبت‌شده `WordAppDocumentBeforeSave` در `0x004CD154` است، نه `WordAppDocumentBeforeClose`.
- callback ابتدا `Saved=False` را از COM slot `+0xD8` تنظیم می‌کند، سپس prompt ثبت تغییرات را نشان می‌دهد.
- Yes → آرگومان اول `_Document.Close` برابر `-1`؛ No → برابر `0`؛ Cancel → فیلد Cancel رویداد برابر `0xFFFF` و سند باز می‌ماند.
- برای Yes/No از overload سه‌آرگومانی `TWordDocument.Close` و COM slot `+0x29C` استفاده می‌شود؛ overloadهای 1/2/3 آرگومان همگی به همین slot ختم می‌شوند.
- این یافته رفتار مشاهده‌شدهٔ کاربر را توضیح می‌دهد: بستن Word بدون فشردن Save هم می‌تواند ثبت را آغاز کند. اما POST/response نهایی Almas هنوز اثبات نشده است.


### XML twin-field attribute spelling — 2026-11-16

- Parser-side XML methods confirm incoming keys `separator`, `concator`, and `paramId` through `TXMLNode.GetAttributeNodes`.
- Existing schema transcription contains `concater`; this conflicts with native `concator`. No alias is proven. The runtime keeps raw attributes unchanged and does not normalize either spelling.
- Serializer-side TD32 `Get_*` labels do not consistently match their string literals; parser-side `Set_*` methods are the reliable incoming-attribute evidence.


### Parallel controller callback ownership checkpoint — 2026-11-16

- Word custom-property/controller-init run `43820125640` completed successfully; artifact `14204196789`.
- `TEDPController.Notify` (`0x004D2EC8`) calls `TEmwatDocPrintHandler.GetDocFieldName` (`0x004A8F78`) with the controller's `+0x1C` member. This is not a direct call to `TWordViwer.OnControlerNotify`; do not conflate the two notification paths.
- `TEDPController.SetOnNotify` (`0x004D2F2C`) invokes a stored method pointer from `+0x10/+0x14`; `SetPrintThread` (`0x004D2F44`) writes the two method-pointer words to those offsets. Direct call-site scans found no direct callers, so the registration/dispatch relationship still needs pointer/VMT evidence.
- A new independent workflow, `analyze-word-controller-callback-ownership.yml`, was added to trace the viewer constructor/destructor, timer callback, controller dispatch, and print-handler ownership in parallel. Its result must be checked before assigning event semantics.
- Python bridge run `43820250444`: **101 tests run, 100 passed, 1 optional UNO test skipped**. It verifies that the literal XML attribute spelling and backslash-n value are preserved without interpreting the unresolved concatenation semantics.
- Native XML parser reads `concator`; the captured schema transcription currently says `concater`. Python retains raw attributes and does not alias or normalize the two spellings.

### Native close-choice parity remains a production blocker — 2026-11-16

- The binary's active Word BeforeSave callback asks the user Yes/No/Cancel; Yes closes with SaveChanges=True, No closes with SaveChanges=False, and Cancel vetoes closing.
- The current LibreOffice close listener snapshots the document in `queryClosing` and does not yet implement this three-way decision. The live UNO roundtrip proves DOCX open/close/export only; it does not prove equivalent close-choice behavior.
- Do not mark the desktop workflow production-ready or claim exact No/Cancel response parity until this behavior and the corresponding HTTP response semantics are implemented and tested.


### Legacy DOC input round-trip verified — 2026-11-16

- Added a second stage to the live UNO integration test: the DOCX fixture is exported to legacy Word CFB `.doc`, then that `.doc` payload is reopened through `LibreOfficeAdapter` as an actual incoming request.
- The second pass verifies the `.doc` input path, document text, bookmark inventory, and preservation of the updated custom document property before exporting another CFB `.doc`.
- Python bridge run `43821455825`: **101 tests run, 100 passed, 1 optional UNO test skipped**.
- LibreOffice UNO integration run `43821455852`: **10/10 passed**, including the DOCX → DOC → DOC roundtrip. This validates synthetic legacy DOC import/export, not an original Almas template or registration response.

### Additional parallel reverse-engineering tracks

- Controller ownership workflow `43821043328` completed successfully (artifact `14204701301`). It separates `TEDPController.Notify` / print-handler cleanup from the main viewer `OnControlerNotify` path; no unsupported event equivalence was inferred.
- Print-handler/controller wiring workflow `43821379564` and image/text-field workflow `43821526090` were launched as separate jobs and were still in progress at the last check. Their results are not yet included in the confirmed findings.


### Real UNO → EditWordDocument handler → wire response verified — 2026-11-16

- Added a live integration test that constructs a captured-format `<emwat><method class="EditWordDocument">` request, parses `wordConfig`/`wordBody`, opens the DOCX through real LibreOffice UNO, auto-closes the test document, and runs the actual `EditWordDocumentService`/handler response path.
- The test validates HTTP-layer result status/content type and the exact successful `response-word` envelope, including `mimetype=application/msword`, `encryption=base64`, and a decoded legacy CFB `.doc` payload.
- Python bridge run `43821716274`: **102 tests run, 100 passed, 2 optional integration tests skipped**.
- LibreOffice UNO run `43821716306`: **11/11 passed**, including the new real UNO → service → handler → response test and the legacy CFB `.doc` reopen test.
- This verifies the success path through the native bridge composition layers. It does not prove the user-facing close-choice behavior, exact No/Cancel envelope, or fidelity against an original Almas template.

### Controller and image-field traces — 2026-11-16

- Print-handler/controller workflow `43821379564` succeeded (artifact `14204039496`). `IEDPController` is implemented by `TEDPController` (IID `34959712-4691-4b92-ae62-c740dc955895`); its interface table maps `+0x0C` to `SetPrintThread`, `+0x10` to `SetOnNotify`, and `+0x14` to `Finalization`. The `TEmwatDocPrintHandler` methods are in `frmWordPrintOptionUnit` and include separate Rec/CC and selected-receiver processing; this remains distinct from the main editor's BeforeSave registration path.
- The controller trace confirms `TEDPController.Notify` calls `TEmwatDocPrintHandler.GetDocFieldName` with its `+0x1C` member. No direct call to `TWordViwer.OnControlerNotify` was established from that method.
- Image/text-field workflow `43821526090` succeeded (artifact `14204287692`). `FillImageField` branches on XML-field attributes and calls Word field/document COM interfaces; `AddImagesToDoc` delegates caption/font work to `GetCaptionItemFont`. The precise image anchor/field mapping is still not known because no original Almas template is available.
- Both workflows are analysis-only; their output is evidence for the next mapping stage, not proof of a complete image/signature implementation.


### Word image-field storage branches and service PE checkpoint — 2026-11-16

- Image-field trace run `43822121391` succeeded (artifact `14204378458`). `FillImageField` contains two explicit storage/log branches: a mapped field value is stored in `CustomDocumentProperties[index]`; otherwise the value is written to `Field.Result.Text`. It also checks a document-field lock state and has explicit twin-filling start/end diagnostics.
- The same routine checks special field names `LetterRegistrationDate`, `LetterRegistrationNo`, `ProduceDate`, `Receivers`, `ReceiverDeps`, `ccReceivers`, and `ccReceiverDeps`; these are recorded as observed special cases, not assumed to be image IDs.
- `AddImagesToDoc` delegates to `GetCaptionItemFont`; caption/image positioning constants include `right`, `center`, `left`, `top`, `middle`, and `bottom`. Exact field-to-anchor mapping remains template-dependent.
- The `EmwatService.exe` scan run `43822306144` succeeded (artifact `14204299947`). It is PE32 (ImageBase `0x00400000`, entry `0x00481C30`) and contains Indy HTTP response RTTI strings (`TIdHTTPResponseInfo`, `ContentText`, `WriteContent`) plus the `invoke=` script token. It has no usable TD32 symbols; this scan alone does not identify the final HTTP handler.
- The service-analysis workflow was extended with a Delphi VMT scan for Indy HTTP server/response classes. The updated run is pending; no VMT slot result is claimed yet.
- Added `DecodedWordField.is_image`, based strictly on the preserved MIME prefix `image/`, with tests. This is metadata classification only; it does not insert image content or guess a Writer anchor.


### HTTP server VMT and print-handler symbol correction — 2026-11-16

- The service executable VMT scan found `TIdHTTPServer` at `0x00461CFC` (instance size `0x1BC`). Its virtual slot `+0x74` targets `0x0045E85C`; that method calls through response/request-related interface slots `+0xDC` and `+0x108`, then dispatches to `0x00438A2C`.
- No VMT candidate passed validation for `TIdHTTPResponseInfo` or `TIdHTTPRequestInfo`; these may be interface/record metadata rather than normal Delphi classes. The response-info method chain is not yet resolved.
- A follow-up service trace now disassembles `0x00438A2C`, `0x0045E03C`, `0x004391B0`, and decodes the relevant dispatch strings. Run is pending.
- Print-handler review corrected a misleading TD32 label: `0x004A5014` is called by `IsCustomField` and its callers test AL as a Boolean. It is not evidence of a `TEmwatDocPrintHandler` constructor. The class's print-option `SetCCValueForMain` calls `ForgotMe`; this path remains separate from main editor registration.
- `GetImageResolution` (`0x004C2DE0`) explicitly maps `right/center/left/top/middle/bottom` to enum values `1..6`. `EmbedTextToImage` is a separate image/caption rendering helper; the exact template anchors remain unknown.


### Correction: Indy HTTP request/response VMTs resolved — 2026-11-16

- The first custom VMT scan produced false negatives for `TIdHTTPRequestInfo` and `TIdHTTPResponseInfo`. The subsequent Delphi RTTI/interface-table scan (workflow `43823328027`, artifact `14205910254`) resolved their actual VMTs:
  - `TIdHTTPRequestInfo`: `0x0045B704` (instance size `0x11C`)
  - `TIdHTTPResponseInfo`: `0x0045BDE8` (instance size `0xDC`)
  - `TIdCustomHTTPServer`: `0x0045D024` (instance size `0x1BC`)
  - `TIdHTTPServer`: `0x00461CFC` (instance size `0x1BC`)
- The earlier statement that no request/response VMT candidates existed is superseded; it was a limitation of the first scanner, not evidence that those classes were records.
- A follow-up job now inventories the virtual method slots of all four classes to map request properties and response-writing methods. Its result is pending.


### Native Word BeforeSave event registration and exact choice mapping — 2026-11-16

- The event-record setup at `0x004B8C60–0x004B8D10` writes handler `0x004CD154` (`TWordViwer.WordAppDocumentBeforeSave`) and the viewer instance pointer into the Word event sink record (`+0x80/+0x84`). This is positive registration evidence, not just a method-name guess.
- The native callback checks the document's `Saved` state. When the configured prompt path is active, the dialog result maps as follows: result `2` sets the COM `Cancel` flag (`0xFFFF`); result `6` closes with `SaveChanges=True`; other non-cancel results close with `SaveChanges=False`.
- It invokes `_Document.Close` through the COM vtable at `+0x29C`, passing the SaveChanges choice, then clears the active document reference. A guard failure also sets Cancel and leaves the document open.
- `TWordViwer.WordAppDocumentBeforeClose` (`0x004CCBBC`) is still a separate path: its only direct caller is `FillImgFldsForPrint`; it is not the main editor close-registration callback.
- A follow-up CI job was added to decode the exact native Persian prompt and button strings from the BeforeSave handler. The new event-sink workflow run is pending.


## همسان‌سازی مدل چرخه سند با سه‌گزینه‌ای بستن Word — 2026-11-16

- تحلیل event-sink در run `43824067943` و artifact `14206405476` متن واقعی پنجره را استخراج کرد: عنوان «ام وات»، پیام «محتويات اين سند تغيير كرده است. آيا مايل به ثبت تغييرات مي‌باشيد؟» و گزینه‌های «موافقم»، «خیر»، «انصراف».
- نگاشت native از بدنه BeforeSave تأیید می‌کند: موافقم → `Close(SaveChanges=True)`؛ خیر → `Close(SaveChanges=False)`؛ انصراف → `Cancel=0xFFFF` و سند باز می‌ماند.
- مدل دامنه دو نتیجه واقعی پایان سند را جدا می‌کند: `CLOSED` (مسیر ثبت/بازگشت) و `DISCARDED` (بستن بدون بازگشت payload). coordinator در حالت discard هیچ export یا payload موفقی تولید نمی‌کند.
- اصلاح مهم lifecycle: گزینه «انصراف» پایان session نیست؛ فقط همان close attempt را veto می‌کند و سند باز می‌ماند. بنابراین adapter باید در `wait_for_close` منتظر تلاش بعدی بماند و هرگز آن را به‌عنوان terminal `CANCELLED` برنگرداند. `DocumentState.CANCELLED` برای لغو صریح خود session در سطح برنامه باقی می‌ماند، نه برای دکمه Cancel پنجره Word.
- تست‌ها اکنون ثابت می‌کنند close attempt لغوشده مانع close نهایی بعدی نمی‌شود و مسیر discard بدون export می‌ماند. انتخاب‌گر گرافیکی LibreOffice و پاسخ HTTP دقیق برای گزینه «خیر» هنوز پیاده‌سازی/اثبات نشده‌اند و عمداً حدس زده نشده‌اند.
- تحلیل موازی سرویس HTTP در run `43823657154` (artifact `14205656649`) مسیر VMT سرور Indy را تا handler داخلی `0x0045E85C` و dispatch بعدی `0x00438A2C` محدود کرده است؛ مرحله بعد، resolve کردن این زنجیره به متد واقعی درخواست و writer پاسخ است.


## Parallel milestone — close-state semantics and Indy response writer (2026-11-16)

- Main branch commit 74454d70bbeff1a55de214775e6a5d118581ffb2 passed Python bridge CI: 104 tests run, 102 passed, 2 optional UNO tests skipped.
- The lifecycle state machine now distinguishes CLOSED (return final document) and DISCARDED (close without returning edited bytes). Native Cancel is a veto of the close attempt and must leave the session open; the adapter must keep waiting.
- Parallel static analysis resolved the Indy published method names: WriteContent=0x004610FC, ServeFile=0x00460E48, SmartServeFile=0x00460FAC. WriteContent has stream, text, and fallback HTML response-body branches and omits bodies for status 100/204/304.
- Two new CI workflows now separately trace the Word-controller close chain, service HTTP response chain, and response-writer helpers. All completed successfully.
- Remaining critical work: implement the real three-choice LibreOffice close dialog/veto, prove the No/discard wire response, resolve the indirect caller of WriteContent, and obtain an anonymized representative Almas document template for visual/field fidelity.


## Word timer callback path resolved — 2026-11-16

The OnTmrAutoSave procedure installs OnControlerNotify as the OnTimer event of the TTimer stored at TWordViwer offset +0x7C. The helper addresses resolve through the package IAT to VCL TTimer.SetOnTimer, SetInterval, and SetEnabled. The timer interval is clamped to at least 10 seconds (0x2710 ms) and enabled. This establishes a periodic document-notification/content-read path distinct from WordAppDocumentBeforeSave, which handles the close-time registration prompt. Helper 0x00456DFC remains under analysis.


## MainForm HTTP entrypoint mapped — 2026-11-16

The service RTTI resolves TMainForm.IdHTTPServerCommandGet to 0x0047BF30. It reads the invoke query parameter and routes that branch through the package/request helper at 0x0047E0EC. Separate init and heartbeat routes are present: init returns the embedded HTML/JavaScript bootstrap with CORS headers, and heartbeat returns a small response. The init/heartbeat branches directly set TIdHTTPResponseInfo.ContentText (+0xBC) and call WriteContent (0x004610FC). This confirms ContentText is +0xBC and ContentStream is +0xB8. The exact invoke-branch response payload remains unresolved.


## Invoke XML parser mapped — 2026-11-16

The MainForm invoke route reaches ParseMethod (0x00470D00) and parser worker 0x00470B38. The parser recognizes the XML root emwat with version, then method/class/param elements and the param name attribute. Token dispatch is in 0x0046ADBC; 0x0046A7A4 appends three-value records to an internal collection. The exact mapping from these records into the BPL TEmwatMethod.Invoke dictionary and the final invoke response remains under analysis.


## BPL method class hierarchy resolved — 2026-11-16

The BPL VMT scan establishes that TEditWordDocument inherits TEmwatMethod; TScanDocument, TFaxDocument, TGetEmwatVersion, TSetEmwatVersion, TUpgradeEmwat, TImageEdition, TEditExcelWorkBook, and TCompareWordDocument share that same base. TEmwatMethod.Invoke (0x0046C82C) accepts TDictionary<AnsiString,AnsiString> and iterates key/value pairs. Its request-time caller remains indirect/unresolved; the only direct TD32 caller found is a unit-finalization path.


## Latest reverse-engineering pipeline verification — 2026-11-16

- BPL method invoke/VMT workflow 43832553168 completed successfully (artifact 14208369288).
- Confirmed inheritance: TEditWordDocument derives from TEmwatMethod; the common base is also used by the other method classes listed in docs/EDITWORD-REQUEST-SCHEMA.md.
- TEmwatMethod.Invoke accepts TDictionary<AnsiString,AnsiString> and iterates key/value entries. The service's runtime call into this inherited method is still an indirect/RTTI dispatch target, not a proven direct callsite.


## Dispatch crosswalk review and Word VMT discrepancy — 2026-11-16

- Re-inspected the successful BPL artifact from run `43832553168` / artifact `14208369288`, including the complete TD32 procedure and VMT/interface outputs.
- `TEmwatMethod.Invoke` (`0x0046C82C`) walks dictionary key/value pairs. `0x0046E324` is identified as `TPairEnumerator.DoGetCurrent`; `0x0046E3CC` is associated with `TPairEnumerator.MoveNext` in RTTI/VMT metadata even though its TD32 decorated name says `TList<TPair>.GetCapacity`. Preserve this naming conflict in analysis.
- A raw pointer scan found no exact static references to `0x0046C82C`, and the only direct TD32 caller found is unit finalization. Its runtime role is still unresolved; do not label it the request dispatcher based on its name.
- `TEditWordDocument` VMT `0x005ED764` has `+0x10 = 0x005EE82C`. That target reads `wordConfig`, `wordBody`, `letterImages`, and `signData`, validates `wordConfig`, and reaches `TWordViwer.LoadDocument` (`0x004B7724`). TD32 decorates the same target as `TScanDocument.PerformMethod`. `TScanDocument` VMT `0x005ED884` has `+0x10 = 0x005EEB48`, while TD32 labels that target `TFaxDocument.PerformMethod`. This VMT/TD32 class-name mismatch is now documented; no source-level rename is asserted.
- New reference: `docs/WORD-LIFECYCLE-STATIC-TRACE.md`.

### New analysis workflow status

- Added `.github/workflows/analyze-emwat-dispatch-crosswalk.yml` with separate service, BPL-dispatch, and Word-lifecycle jobs.
- The public repository's `analysis-input/` currently contains `EmwatMethods.bpl1` and resource binaries, but not `EmwatService.exe`. The service job now writes an explicit missing-input report and skips that trace rather than failing or implying that service disassembly ran.
- Expanded BPL and Word traces include the Invoke helpers, AutoSave, controller notification, BeforeClose/BeforeSave, document callbacks, SilentSave, and field/configuration routines.
- Commits: workflow `1a3f17f99a892d157b792c4090b90b5bbbd5d140`; static trace `84de233435f61cb7b79758b7ad86f6f91b7f774f`; README link `3838964260a87a641b5fe06f254f23c78abc9e68`.
- The newly expanded workflow run and artifacts have not yet been independently verified. Do not report those jobs as passed until their run outputs are inspected.

### Immediate unresolved target

Resolve the class-registration/dispatch bridge that maps the incoming XML `method class="EditWordDocument"` to the concrete class/VMT and its `PerformMethod` slot. In parallel, determine whether `TEmwatMethod.Invoke` is an XML response builder or another helper, and connect the service's invoke branch to the selected method and final response writer.


## Controller archive pipeline and VMT cross-check — 2026-11-16

### Verified successful analysis runs
- Dispatch crosswalk run `43867641761`: all three jobs completed successfully. Artifacts: BPL `14225499151`, Word lifecycle `14226866454`, service missing-input note `14226172178`. The service job succeeded by explicitly skipping PE tracing because the binary was absent from the checkout; it did not analyze the service.
- Expanded VMT run `43868190188`: all three jobs completed successfully. BPL artifact `14225224443` includes exact-address VMT inspection for `TEmwatMethod`, `TEditWordDocument`, `TScanDocument`, `TWordViwer`, and `TEDPController`.
- Controller unpack run `43868321797`: job completed successfully, artifact `14226342809`.

### Corrected VMT conclusions
- `TEmwatMethod` VMT `0x0046ABFC` slot `+0x0C` points to `0x0046C9E0`, the shared public virtual Invoke wrapper (TD32 misleadingly labels it `Emwatmethod.Finalization`). Slot `+0x10` is the abstract/error stub `0x00401068`.
- The wrapper at `0x0046C9E0` calls the inner dictionary/XML helper `0x0046C82C` and then calls the concrete subclass's VMT slot `+0x10`. The raw-pointer scan's lack of references to `0x0046C82C` does not negate this direct relative CALL from the wrapper.
- `TEditWordDocument` VMT `0x005ED764` has parent pointer `0x0046ABA4` (the `TEmwatMethod` VMT header self-pointer) and slot `+0x10` points to `0x005EE82C`; TD32 labels that routine `TScanDocument.PerformMethod`.
- `TScanDocument` VMT `0x005ED884` has the same `TEmwatMethod` parent and slot `+0x10` points to `0x005EEB48`; TD32 labels that routine `TFaxDocument.PerformMethod`.
- Therefore the class inheritance and BPL wrapper-to-concrete-method dispatch are confirmed. Preserve the TD32/VMT naming discrepancies rather than renaming the routines. The service-side `GetClass("T"+className)` and VMT slot `+0x0C` chain are detailed in `docs/EMWAT-SERVICE-EXECUTABLE-ANALYSIS.md`.

### Controller content and archive processing
- `TWordViwer.OnControlerNotify` obtains Word content via the `_Document` COM interface slot `+0xDC`, then calls `Emwatutils.euUnArchive` at `0x00456DFC`.
- `0x004563A8` is `FixDirectionInFarsiNumericMode`; it is not an object/list constructor. It transforms the base path at `TWordViwer+0x80`.
- The decoded suffixes are `.easd` (`0x004BB754`) and `.easz` (`0x004BB76C`). The `.easd` path is passed through an object method; the `.easz` path is passed to `euUnArchive`.
- The two indexed inputs are `TStringList` instances. `T7zPlugin` creates a `T7zOutArchive` object and returns its interface pointer at offset `+0x44`.
- Interface slot `+0x10` reaches `T7zOutArchive.AddFiles` (`0x00453F34`): source path from `TWordViwer+0xA0`, archive member name from base path + `.easd`.
- Interface slot `+0x18` reaches `SaveToStream` (`0x00454668`), which creates a stream from the supplied path and saves the archive to base path + `.easz`.
- Interface slot `+0x28` reaches `0x004547E8`; despite its TD32 label `SetProgressCallback`, its body stores the input UnicodeString in field `+0x38`, identified as `FPassword`. Thus `mW@Tlogs43end_+` is the archive password in this path. The separate `SetPassword` at `0x004547DC` is a no-op.
- This statically establishes a password-protected 7z archive-writing path after Word content retrieval. Exact stream class at global `0x0062F800` and runtime archive bytes remain to be verified.
- Detailed write-up: `docs/WORD-COM-INTERFACE-DISPATCH.md`, Run 148.

### New focused pipelines
- `.github/workflows/analyze-emwat-controller-unarchive.yml` now has an expanded run that traces `0x0040414C`, `0x004543C4`, SevenZip class procedures, VMT slots, and interface tables. Run 2 is queued at this checkpoint.
- `.github/workflows/analyze-emwat-service-dispatch.yml` downloads the preserved `emwat-mainform-invoke-handler` artifact from run `43831365563` and traces the service parser/dispatch/response chain without committing the EXE into the public repository. Run 1 is queued at this checkpoint.

### Next highest-value tasks
1. Resolve `T7zPlugin` vtable slot methods and the class/type of the two paired indexed objects.
2. Determine whether `.easd` is a sidecar/data stream and `.easz` the archive target, using only static traces and synthetic content.
3. Use the preserved service artifact to close the XML `class` lookup → concrete class/VMT `PerformMethod` → result/response path.
4. Connect the archive output to the `invoke` HTTP response; do not equate periodic controller timer notifications with final Almas registration.


### Service PE artifact workflow correction — 2026-11-16

- The preserved service artifact `emwat-mainform-invoke-handler` from run `43831365563` was successfully downloaded in service workflow run `43868531786`; the binary was present and valid.
- That first deep-trace attempt failed because `EmwatService.exe` has no TD32 debug signature. The failure was in the analysis method, not the artifact download or executable.
- The workflow was corrected to use PE-only disassembly (`trace_pe_target.py`), raw pointer-reference scans (`scan_pe_pointer_refs.py`), VA inspection, and string decoding. TD32-only tools were removed from the service job.
- Corrected service workflow run `43868823284` was queued at this checkpoint; its result and artifact still need inspection.
- This preserves the service EXE as a CI artifact only; it is not committed into the public repository.


### SevenZip interface correction — 2026-11-16

The exact VMT/COM-interface inspection supersedes the earlier tentative password interpretation:
- `T7zPlugin.$bctr` returns an interface pointer at offset `+0x44` of a `T7zOutArchive` instance; the interface IID is `baa9d5dc-9ff4-4382-9bfd-ec9065bd0125`.
- Through that interface, `euUnArchive` slot `+0x10` maps to `T7zOutArchive.AddFiles` (`0x00453F34`), slot `+0x18` maps to `SaveToStream` (`0x00454668`), and slot `+0x28` maps to `SetProgressCallback` (`0x004547E8`).
- The hardcoded literal `mW@Tlogs43end_+` is passed to slot `+0x28`; it is **not proven to be a password**. The class has a separate `SetPassword` method at `0x004547DC`, but that is not the target of this observed interface call.
- The `TStringList` inputs and `.easz` string do not obviously match the TD32 signatures of AddFiles/SaveToStream. Keep the helper's archive direction and slot argument semantics unresolved until the target bodies and wrapper layer are traced.
- Detailed correction: Run 146 in `docs/WORD-COM-INTERFACE-DISPATCH.md`.


### Invoke bridge and XML version confirmation — 2026-11-16

- Service PE trace run `43869039523`, artifact `14226099734`, decodes the embedded init script: it listens for parent-frame `message`, POSTs `message.data` to `http://127.0.0.1:$V{myport}?invoke=<random nonce>`, and posts the HTTP `responseText` back to the original frame source/origin.
- The service-side XML parser literals are now independently decoded: `emwat`, `version`, `method`, `class`, `param`, and `name`. The root validator parses `version` numerically and compares it to exactly `1`.
- `0x0047E0EC` is the `EmwatMethods.bpl` package-load helper, not the concrete method dispatcher; `0x0047E2D4` unloads the package. The invoke path calls load → ParseMethod → unload. The actual concrete class invocation/result path remains open.
- The exact XML envelope is recorded in `docs/EDITWORD-REQUEST-SCHEMA.md`; the browser bridge/package lifecycle is in `docs/HTTP-LOCAL-API-ANALYSIS.md`.


- Additional confirmation from artifact `14226742624`: helper `0x0040414C` is an import thunk to `rtl230.bpl!TStringList.$bctr`. The two indexed inputs to `euUnArchive` are therefore TStringList instances. The first receives `TWordViwer+0xA0`; the second receives the direction-normalized `TWordViwer+0x80` path with `.easd` appended. They are iterated in lockstep and passed to the `T7zOutArchive` interface.


### Archive direction and password now resolved statically — 2026-11-16

Artifact `14227611377` resolves the earlier interface-signature uncertainty:
- `T7zOutArchive.AddFiles` at `0x00453F34` receives the source file path and archive-entry name; it verifies the source file and creates a batch entry.
- `T7zOutArchive.SaveToStream` at `0x00454668` constructs a stream from the supplied output path and invokes the archive save routine.
- The interface slot `+0x28` reaches `0x004547E8`; although TD32 calls it `SetProgressCallback`, the procedure writes the input UnicodeString to object field `+0x38`, which the T7zOutArchive field table identifies as `FPassword`. The separate `SetPassword` at `0x004547DC` is a no-op.
- Therefore the literal `mW@Tlogs43end_+` is the password assigned to `FPassword` in this archive path.
- `euUnArchive` is assembling a password-protected 7z output archive: source path from `TWordViwer+0xA0`, archive member name from the base path + `.easd`, output archive path from the base path + `.easz`.
- Exact stream class behind global `0x0062F800` and the password callback consumption path remain to be confirmed. No runtime archive file has yet been captured.
- Full evidence: Run 148 in `docs/WORD-COM-INTERFACE-DISPATCH.md`.


- Run 5 artifact `14227002967` resolves the final stream detail: `0x004041BC` is the IAT thunk to `rtl230.bpl!TFileStream.$bctr(UnicodeString, Word)`. `T7zOutArchive.SaveToStream` passes the `.easz` path to it with mode `0xFF00` (`fmCreate`), then passes the resulting stream to `T7zOutArchive.SetCompleted` at `0x004546C4`. The archive output is therefore a real file created/truncated at the `.easz` path.


### Word save/close event wiring — 2026-11-16

- `OnTmrAutoSave` (`0x004B8A84`) registers WordApp callbacks: BeforeSave `0x004CD154`, NewDocument `0x004CD54C`, WindowActivate `0x004CD9C0`, and BeforePrintBGPrint `0x004CE030` or alternate `0x004D00AC`.
- `WordAppDocumentBeforeSave` checks active-document identity and viewer state; if not ready it sets Word's Cancel output to `-1`. For a dirty document it can show a three-choice dialog, and one choice cancels. The exact labels and downstream method semantics are pending.
- `WordAppDocumentBeforeClose` (`0x004CCBBC`) calls helper `0x004BCA88`; `SilentSaveEmwatDoc` (`0x004D23D8`) builds two TStringLists and calls `0x004AEBBC`. These are the next close/commit targets.
- Keep BeforeSave, BeforeClose, timer-side autosave, and `OnControlerNotify` archive creation distinct until the full-range traces link them. See Run 150 in `docs/WORD-LIFECYCLE-STATIC-TRACE.md`.


- `TWordViwer.LoadDocument` calls `OnTmrAutoSave` with the document path (`0x004B7A58`); the timer handler stores it in viewer field `+0xA0` (`0x004B8AE8`). `OnControlerNotify` later reads `+0xA0` as the source file for `T7zOutArchive.AddFiles`. `LoadDocument` also creates a `TFileStream` for that path and writes document data. Thus the file created during document loading is the source later packaged as the `.easd` entry inside `.easz`. The sibling/base path at viewer field `+0x80` remains to be mapped.


### EditWordDocument payload and result contract — 2026-11-16

- `TEditWordDocument.PerformMethod` reads `wordConfig` (required), `wordBody`, `letterImages`, and `signData`. `wordConfig` missing triggers `Requset XML is not valid (wordConfig parameter is null)`.
- It calls `CoInitialize`, passes the four values plus `TEmwatInvokeParam` and an output string to `TWordViwer.LoadDocument`, stores the returned string as method result, sets `bResultSet=1`, and calls `CoUninitialize`.
- `LoadDocument` extracts `DocFileName` from `wordBody`, creates a local file via `TFileStream(fmCreate)` and writes document data, parses `wordConfig` XML, then calls `OnTmrAutoSave` with the document path. This path becomes `TWordViwer+0xA0` and is later archived as `.easd` inside `.easz`.
- The final mapping of the method result/bResultSet to the HTTP response is still the key unresolved protocol boundary. Full details: `docs/WORD-LIFECYCLE-STATIC-TRACE.md` Run 151.


## تکمیل تحلیل آرشیو اصلی EMWAT و همسان‌سازی Bridge — 2026-11-16

### ورودی‌های باینری و CI

- آرشیو عمومی EMWAT_Extracted.zip در مخزن موجود است؛ فایل‌های EmwatMethods.bpl1، EmwatService.exe و EmwatAgent.exe از آن در CI استخراج می‌شوند.
- تحلیل موازی سرویس و BPL در run 43883105610 موفق شد:
  - BPL dispatch artifact: 14232698133
  - Service dispatch artifact: 14233736412
  - Word controller-close artifact: 14234120250
- تحلیل سه‌گانه Word در run 43882925143 موفق شد:
  - lifecycle: 14232038748
  - save/print: 14232159665
  - field mapping: 14232259712

### یافته‌های جدید سرویس

- تابع 0x0047E0EC در واقع package-load gate برای EmwatMethods.bpl است، نه route/authentication helper. رشته‌های واقعی آن پیام‌های موفقیت/شکست بارگذاری BPL هستند.
- handler پس از عبور از این gate به parser می‌رود. parser نام‌های method، class، param و name را با ثابت‌های دقیق مقایسه می‌کند.
- helper 0x0046A7A4 رکوردهای سه‌خانه‌ای با stride دوازده بایت می‌سازد؛ معنای دقیق همه خانه‌ها هنوز باید از token callerها استخراج شود.
- رشته‌های invoke و CORS نیز decode شدند. امضای دقیق یکی از headerها در باینری Access-Control-Allow-Method:* است (مفرد).

### یافته‌های جدید Word/BPL

- ثابت‌های SetFieldValue: urlencoded در 0x004BFEE8 و base64 در 0x004BFF0C.
- ثابت 0x004D1768 برابر † (U+2020 DAGGER) است و در مسیر split کردن شناسه‌های twin در custom properties استفاده می‌شود.
- WordAppDocumentBeforeSave دارای prompt تصمیم‌گیری و امکان set کردن Cancel به 0xFFFF است؛ رشته‌های UI شامل «موافقم»، «خیر» و «انصراف» هستند.
- TWordDocument.Get_Content از COM vtable slot +0xDC استفاده می‌کند. تابع 0x00456DFC در حقیقت euUnArchive است و از OnControlerNotify فراخوانی می‌شود؛ این دو مسیر نباید یکی فرض شوند.
- CostumizeRecAndCC در 0x004D281C در مسیر controller notify، field-name lookup، protection و rollback استفاده می‌شود.

### تغییر Bridge و تست

- Bridge برای POST پاسخ‌ها headerهای بازیابی‌شده Access-Control-Allow-Headers: * و Access-Control-Allow-Method: * را اضافه می‌کند، اما سیاست Origin allowlist پروژه حفظ شده است.
- query مقدار invoke در لایه transport opaque باقی مانده؛ باینری client-side nonce تصادفی را ثابت می‌کند، ولی اعتبارسنجی عددی server-side از این شواهد ثابت نشده است.
- Python bridge run 43883570154 موفق شد: **104 تست، 2 skip اختیاری**.

### وضعیت واقعی

پروژه اکنون parser/bridge/dispatcher، چرخه session، adapter مربوط به LibreOffice و بخش‌هایی از field/property pipeline را دارد. تست‌های قبلی Python و UNO نیز در fixtureهای مشخص موفق بوده‌اند. با این حال، سازگاری کامل end-to-end با سامانه عملیاتی Almas، همه فیلدهای 180+گانه، تصاویر/امضاها، چاپ واقعی و همه حالت‌های cancel/discard هنوز تأیید نشده است.


## اصلاح مهم در event sink ورد و Parser سرویس — 2026-11-16

- اسکن کامل TD32 نشان داد `OnTmrAutoSave` این callbackها را در event-sink ثبت می‌کند: `WordAppDocumentBeforeSave`، `WordAppNewDocument`، `WordAppWindowActivate` و `WordAppDocumentBeforePrintBGPrint` (یا callback جایگزین `0x004D00AC` بر اساس flag داخلی).
- با وجود نام TD32 تابع `WordAppDocumentBeforeClose` در آدرس `0x004CCBBC`، تنها فراخوان مستقیم آن در اسکن فعلی از `FillImgFldsForPrint` است؛ این تابع به `GetXmlFieldInfo` می‌رسد و در بلوک event-sink ثبت نشده است. بنابراین نباید آن را رویداد واقعی Close فرض کرد.
- `SilentSaveEmwatDoc` از مسیر `GetDocFieldName` و فیلد ویژه `Hidden_Customizable` فراخوانی می‌شود؛ دو TStringList موقت می‌سازد، helper `0x004AEBBC` را صدا می‌زند و در شرایطی `TWrapRecord.LineCount` را اجرا می‌کند. معنای دقیق خروجی این ساختار هنوز قطعی نیست.
- رکورد Parser برای هر `param` اکنون در سطح ساختار decode شده است: slot صفر hash نام، slot یک نام پارامتر و slot دو مقدار متنی. اتصال نهایی این collection به دیکشنری BPL هنوز نیازمند trace dispatch است.
- شواهد: service artifact `14233736412` و Word artifact `14234120250`، هر دو از run `43883105610`.


## تکمیل crosswalk فیلد و تصویر Word — 2026-11-16

- `FillPrintDocFields` فقط به رویداد Print محدود نیست؛ callerهای مستقیم آن `GetDocFieldName` و `GetFieldIndexInList` هستند و در مسیر جست‌وجوی نام/اندیس فیلد هم اجرا می‌شود.
- `AddImagesToDoc` از `GetDocFieldIndex` فراخوانی می‌شود و تابع `GetCaptionItemFont` در `0x004C19C0` را فراخوانی می‌کند؛ این تابع مربوط به فونت کپشن است و helper درج تصویر محسوب نمی‌شود.
- `FillImageField` از دو شاخه `FillTextField` فراخوانی می‌شود و در وضعیت خاص از `FindWindowExtd` استفاده می‌کند.
- `FillField` فقط field interface را به collection داخلی اضافه می‌کند و عملیات نهایی تغییر متن/تصویر نیست.
- مستند شواهد: `docs/WORD-AUTOMATION-SURFACE-2026-11-16.md` و artifact شماره `14232259712`.


## تحلیل تکمیلی تصویر و فیلدهای چاپ — کار در صف CI

Workflow تحلیل Word گسترش یافت تا helper مرکزی درج تصویر `0x004C19C0)، resolver فیلد `0x004BC170)، رشته‌های شاخه‌های `FillImageField` و رشته‌های شرطی `FillPrintDocFields` را decode کند. تغییرات در commitهای `367e4aa58514029278624c65837059f13807394a` و `c159c69141da56ea1bba0c8d829e4839febaf135` ثبت شده‌اند. خروجی این batch هنوز باید از GitHub Actions دریافت و بررسی شود؛ تا آن زمان helper و برچسب‌های شرطی را ناشناخته نگه می‌داریم.


## تکمیل تحلیل GetDocFieldIndex و بازبینی CI — 2026-11-16

- تابع `0x004C0550` با سمبل TD32 به‌صورت قطعی `TWordViwer.GetDocFieldIndex` شناسایی شد.
- زنجیره تطبیق فیلد: Word Fields → `FindFieldInActivefields` → `GetXmlFieldInfo` → شاخه‌های `FillMSWFields` و `SetFieldValue`؛ مسیر متن از `FillTextField` و شاخه تصویر/کپشن از `AddImagesToDoc` ادامه پیدا می‌کند.
- `GetCaptionItemFont` از مسیر `AddImagesToDoc` فراخوانی می‌شود و خودش `GetXmlFieldInfo`، `SetFieldValue`، `EmbedTextToImage` و `FillMSWFields` را اجرا می‌کند.
- `GetCaptionItems` از `ResizeBitmapCanvas` و `ProcessWords` فراخوانی می‌شود. `GetImageResolution` در مسیر `StrToAlign` به‌عنوان تبدیل رشته به مقدار enum با شش حالت دیده شده؛ نام سمبل به‌تنهایی معنای DPI را ثابت نمی‌کند.
- خطای مسیر خروجی decoder در Workflow اصلاح شد. اجرای `43886833015` هر سه job تحلیل lifecycle، field mapping و save/print را با موفقیت تمام کرد.
- CI کد: Python bridge اجرا `43886698595` با ۱۰۴ تست موفق و ۲ skip اختیاری؛ LibreOffice UNO اجرا `43886698714` با ۱۱ تست موفق.
- مستند تفصیلی: `docs/WORD-AUTOMATION-SURFACE-2026-11-16.md`. اجرای جدید برای decode رشته‌های دقیق branchها با run `43887016674` در صف/حال اجراست.


## نکته جدید در مسیر چاپ — 2026-11-16

در trace تابع `FillPrintDocFields` رشته خاص `EMBED Equation` در آدرس `0x004CCB0C` decode شد و یک شاخه جداگانه برای آن وجود دارد. مسیر دیگر این تابع با کلیدهای `CustomDocumentProperties` و `count` کار می‌کند؛ decode دقیق شروع بایتی این دو رشته در اجرای بعدی Workflow انجام می‌شود. برای تعیین رفتار نهایی، trace توابع `0x004D3DF8`، `0x004D34B0` و `0x004D3B78` در حال اضافه شدن است.


## جزئیات تازه مسیر امضا و تصویر — 2026-11-16

- تابع TD32 با نام `GetCaptionItemFont` در آدرس `0x004C19C0` از مسیر `AddImagesToDoc` فراخوانی می‌شود، اما بدنه آن عملاً پردازش تصویر/امضا را انجام می‌دهد: `signData` و `signText` را بررسی می‌کند، `igLzw32s.Dll` را بارگذاری می‌کند، فایل‌های تصویر را اعتبارسنجی می‌کند، image list می‌سازد و پیام موفقیت `AddImageToDoc succeed` دارد.
- کلیدهای خاص فیلد در `FillImageField`: `LetterRegistrationDate`، `LetterRegistrationNo`، `ProduceDate`، `Receivers`، `ReceiverDeps`، `ccReceivers` و `ccReceiverDeps`.
- همین تابع بین ذخیره مقدار در `CustomDocumentProperties` و `Field.Result.Text` تفاوت می‌گذارد و وضعیت قفل بودن فیلد را بررسی می‌کند.
- `GetDocFieldIndex` الگوی نام فیلدهای امضا، فیلدهای twin، موارد skip شده و خطای نبود twin را مدیریت می‌کند. در نبود twin، مسیر abort و بستن سند بدون نگه‌داشتن تغییرات وجود دارد.
- برچسب‌های شش حالت تابع `GetImageResolution` هنوز در صف decode هستند؛ از نام تابع درباره DPI یا pixel resolution نتیجه‌گیری نمی‌کنیم.
- مستند تفصیلی: `docs/WORD-AUTOMATION-SURFACE-2026-11-16.md`.


## پیاده‌سازی matcher امضای native و تست‌ها — 2026-11-16

- آدرس `0x004B032C` به `TRegEx.IsMatch` در `rtl230.bpl` resolve شد.
- الگوی native برای فیلدهای انتهایی امضا دقیقاً `^sign.*end[0-2]?[0-9]?$` و case-sensitive است.
- تابع `is_native_business_signature_end()` به `word_fields.py` اضافه شد. فعلاً فقط روی نام فیلد resolve‌شده قابل استفاده است؛ به‌صورت خودکار روی XML field ID اعمال نشده تا تفاوت این دو بدون مدرک فرض نشود.
- تست اولیه به‌علت استفاده از `End` با حروف بزرگ شکست خورد؛ تست‌ها با الگوی دقیق lowercase اصلاح شدند.
- Python bridge run `43888658420`: **۱۰۵ تست موفق، ۲ skip اختیاری**.


## تفکیک سه ساختار فیلد و Custom Property — 2026-11-16

ردیابی `AddCustomDocPropertiesToDic` سه ساختار مجزا را مشخص کرد:
- `viewer + 0x68`: descriptorهای فیلد تکی از نوع `TXmlWordConfigField`.
- `viewer + 0x6C`: descriptorهای twin از نوع `TXmlWordConfigTwinField` که دو شناسه جداشده با `†` را نگه می‌دارند.
- `viewer + 0x64`: دیکشنری runtime جداگانه از نوع `TDictionary<UnicodeString,TDocumentCProperty>`.

در نسخه لینوکس این سه ساختار نباید به یک دیکشنری تخت تبدیل شوند. جزئیات و offsetها در `docs/RESEARCH-LOG-2026-11-16.md` ثبت شده‌اند.


## اصلاح تطبیق parser فیلدهای Word با باینری — 2026-11-16

ردیابی `FindFieldInActivefields` نشان داد استخراج شناسه `DOCPROPERTY` از `Pos` و `Copy` دلفی استفاده می‌کند. رفتار edge-case در Python اصلاح شد: نبودن delimiter دو فاصله باعث شروع Copy از کاراکتر دوم می‌شود و اگر فاصله بعدی وجود نداشته باشد، همان segment برگردانده می‌شود. تست جدید این دو حالت را پوشش می‌دهد.

- Python CI اجرا `43889681823`: **۱۰۵ تست موفق، ۲ skip اختیاری**.
- helper امضای business نیز با regex دقیق و case-sensitive باینری پیاده‌سازی شده است.


## تکمیل شاخه MIME و alignment — 2026-11-16

- مقدار MIME شاخه متن در `FillTextField` دقیقاً `text/plain` است؛ فیلد بدون interface یا با MIME غیر از `text/plain` به `FillImageField` می‌رود.
- مقادیر alignment: `right`، `center`، `left`، `top`، `middle`، `bottom`.
- سبک‌های caption: `bold`، `italic`، `underline`، `strikeout`.
- اجرای Workflow `43889057276` هر سه job را موفق تمام کرد و artifactهای field mapping و save/print تولید شدند.


## مدل‌سازی descriptorهای single و twin در Python — 2026-11-16

تابع `build_word_custom_property_field_maps()` و مدل‌های `SingleWordFieldDescriptor` / `TwinWordFieldDescriptor` در `word_fields.py` نگه داشته شدند. تابع اکنون نام‌های ordered Custom Document Property و در صورت وجود `xml_fields` متناظر از `wordConfig` را می‌گیرد و reference به خود `WordField` node (attributes و text) را ذخیره می‌کند؛ اگر XML field node ارائه نشود، reference برابر `None` می‌ماند. طول دو sequence هنگام ارائه هر دو باید برابر باشد.

- Python CI اجرا `43890539219`: **۱۰۷ تست موفق، ۲ skip اختیاری**.

## اصلاح semantics دیکشنری و مقایسه Twin — 2026-11-16

- `0x004D531C` و `0x004D68D4` در TD32 به‌اشتباه `TDictionary.Remove` نام‌گذاری شده‌اند؛ بدنه هر دو Add است و در `AddCustomDocPropertiesToDic` فراخوانی می‌شوند. آن‌ها duplicate key را رد می‌کنند و entry جدید را درج می‌کنند.
- `0x00403248` به `System.SysUtils.CompareText` resolve شد؛ جست‌وجوی Twin نسبت به بزرگی/کوچکی حروف حساس نیست. تابع Python نیز با `casefold()` اصلاح شد.
- Python CI اجرا `43891288399`: **۱۰۷ تست موفق، ۲ skip اختیاری**.
- LibreOffice UNO اجرا `43890949051`: **۱۱ تست موفق**.

## مرزبندی inventory Writer و descriptorهای native — 2026-11-16

ردیابی نهایی نشان داد `AddCustomDocPropertiesToDic` خودش descriptor mapها را از Word CustomDocumentProperties populate می‌کند. بااین‌حال `WriterDocumentCatalog` هم نام‌های مرتب‌شده برای نمایش و هم نام‌ها در ترتیب `PropertySetInfo` خود UNO را جداگانه گزارش می‌کند؛ این ترتیب هنوز با enumeration ورد تطبیق داده نشده و `WordField` node متناظر نیز باید از `wordConfig.fields` با همان index گرفته شود، پس اتصال خودکار catalog به descriptor map عمداً انجام نشده است. helper Python برای split نام‌ها باقی مانده و می‌تواند `WordField` node متناظر را با همان index دریافت کند؛ این helper به‌تنهایی ادعای mapping کامل ندارد.

## اتصال runtime Custom Property به مسیر تصویر و چاپ — 2026-11-16

- `FillImageField` دیکشنری runtime در `viewer+0x64` را با `TDictionary<UnicodeString,TDocumentCProperty>.SetItem` به‌روزرسانی می‌کند.
- `FillImageField` و `FillPrintDocFields` از `ContainsValue` استفاده می‌کنند؛ `FillPrintDocFields` و `FillPrintOptionForm` در مسیرهای مشخص `Remove` را اجرا می‌کنند.
- این دیکشنری runtime از descriptorهای single/twin در `viewer+0x68/+0x6C` جداست. trace روش‌های `SetItem/TryGetValue/Clear` برای دو map descriptor در batch بعدی اضافه شده است.

## اثبات هویت دیکشنری Parser سرویس — 2026-11-16

- `TMethodInfo` با VMT `0x0047097C` و constructor در `0x00471214` ساخته می‌شود.
- Constructor از class reference `0x004699E4`، که به VMT `TDictionary<AnsiString,AnsiString>` در `0x00469A3C` اشاره می‌کند، برای ساخت دیکشنری با helper `0x0046AA70` استفاده می‌کند.
- pointer دیکشنری در `TMethodInfo+0x08` ذخیره می‌شود و `ParseMethod` همان pointer را به XML parser می‌دهد.
- بنابراین نوع پارامترهای سرویس با ورودی `TEmwatMethod.Invoke` در BPL یکسان است. فقط dispatch نهایی و غیرمستقیم بین سرویس و BPL هنوز نیاز به اثبات دارد.

## تفکیک descriptorهای XML و داده‌های CustomDocumentProperties — 2026-11-16

- دیکشنری `viewer+0x68` برای `TXmlWordConfigField` و `viewer+0x6C` برای `TXmlWordConfigTwinField` است.
- `GetXmlFieldInfo` ابتدا descriptor تک‌فیلدی را بررسی می‌کند و در صورت نیاز به مسیر twin می‌رود؛ ساختارهای خروجی شامل index و یک یا دو نام/کلید فیلد هستند.
- helper `0x004BC170` در مسیرهای XML field، twin fill، index lookup، print و image-print تکرار می‌شود و نقش نرمال‌سازی/تقسیم رشته ورودی را دارد؛ جزئیات delimiter پس از artifact جدید قطعی می‌شود.
- `AddCustomDocPropertiesToDic` نام propertyهای Word را با `†` تفکیک می‌کند، XML field متناظر را با index می‌خواند، رکورد single/twin می‌سازد و با Add wrapper در descriptor map درج می‌کند؛ بنابراین این تابع مسیر population mapهاست.
- مسیر population descriptor mapها اکنون مشخص است: AddCustomDocPropertiesToDic از wrapperهای `0x004D531C` و `0x004D68D4` استفاده می‌کند که بدنه آن‌ها Add است، با وجود TD32 label اشتباه Remove. AddOrSetValueهای جداگانه (`0x004D552C` و `0x004D6AE4`) در این مسیر استفاده نمی‌شوند.

## کشف فیلدهای Option Form گیرنده و رونوشت — 2026-11-16

Constructor مربوط به `TWordViwer` چهار فیلد `Receivers`، `ReceiverDeps`، `ccReceivers` و `ccReceiverDeps` را برای option form مقداردهی می‌کند. سپس برای هر گزینه `field index`، نام، `xmlfidx` و `isInDoc` را log می‌کند. این مسیر، UI/metadata اختصاصی گیرنده و رونوشت را تأیید می‌کند؛ منطق کامل انتخاب گیرنده و serialization آن هنوز باز است.

## کشف APIهای بارگذاری Package و ساخت کلاس در سرویس — 2026-11-16

Import Table در `EmwatService.exe` شامل `LoadPackage`، `UnloadPackage`، `StartExe`، `GetClass`، `ClassCreate`، `ClassDestroy`، `TObject.InheritsFrom`، `ClassParent`، `ClassName` و دو `GetProcAddress` است. این موضوع توانایی سرویس برای بارگذاری BPL و resolve/create کلاس Delphi در زمان اجرا را اثبات می‌کند، اما هنوز زنجیره دقیق فراخوانی `GetClass → ClassCreate → TEmwatMethod.Invoke` قطعی نشده است. به همین دلیل workflow جدید علاوه بر pointer refs، opcodeهای `FF 15` و `FF 25` مربوط به فراخوانی/پرش مستقیم به IAT را اسکن می‌کند.

## بازیابی Method Table فرم اصلی سرویس — 2026-11-16

از VMT کلاس `TMainForm` در `0x0047B284`، method table در `0x0047B84E` پیدا شد. تعداد entryها 17 است و ساختار هر entry شامل اندازه، آدرس کد و نام shortstring است. اولین entry دقیقاً `IdHTTPServerCommandGet` در `0x0047BF30` است؛ بنابراین هویت handler درخواست HTTP تأیید شد. `FormCreate`، `Terminate`، `Log`، `ShowMainForm`، `HideMainForm` و `FormClose` نیز در ابتدای جدول بازیابی شدند.

## فهرست کامل ۱۷ متد منتشرشده TMainForm — 2026-11-16

جدول RTTI فرم اصلی ۱۷ متد را تأیید کرد. علاوه بر `IdHTTPServerCommandGet` در `0x0047BF30`، متد `IdHTTPServerException` در `0x0047CA44`، `FormCreate` در `0x0047CCD8`، `FormClose` در `0x0047CCC8`، `Terminate` در `0x0047E3EC` و `LoadQuickConfig` در `0x0047E7E4` بازیابی شدند. workflow اکنون مسیرهای startup/shutdown و HTTP exception را نیز trace می‌کند.

## اتصال قطعی EmwatService به BPL و Invoke — 2026-11-16

- `ParseMethod` کلاس را با `GetClass` resolve و با `TObject.Create` نمونه‌سازی می‌کند.
- سپس سرویس slot مجازی `VMT+0x0C` را فراخوانی می‌کند.
- در BPL، این slot در `TEmwatMethod` به `Finalization` در `0x0046C9E0` می‌رسد و آن تابع `TEmwatMethod.Invoke` در `0x0046C82C` را صدا می‌زند.
- بنابراین زنجیره service→BPL تا ورود به `Invoke` اثبات شده است. تابع `Finalization` پس از `Invoke`، slot مجازی `+0x10` را فراخوانی می‌کند؛ در VMT کلاس `TEditWordDocument` این slot به `0x005EE82C` می‌رسد و آن تابع `LoadDocument` را اجرا می‌کند.

## نتیجه CI پل Python — 2026-11-16

پس از تغییر مستندات dispatcher برای تطبیق با prefix واقعی Delphi، workflow `python-bridge.yml` با موفقیت اجرا شد: **107 تست موفق، 2 تست اختیاری skip**؛ run `43953680591`.

## تکمیل زنجیره dispatch تا LoadDocument — 2026-11-16

`Finalization` ابتدا `Invoke` را در `0x0046CA67` اجرا می‌کند و سپس در `0x0046CA88` از VMT slot `+0x10`، `PerformMethod` کلاس فرزند را فراخوانی می‌کند. در VMT `TEditWordDocument`، این slot به `0x005EE82C` می‌رسد؛ بدنه آن `TWordViwer.LoadDocument` در `0x004B7724` را فراخوانی می‌کند. بنابراین زنجیره از HTTP/XML سرویس تا شروع Word automation در BPL مشخص شده است.

## ردیابی VMT دیکشنری‌های descriptor — 2026-11-17

دو VMT واقعی برای mapهای descriptor مشخص شدند: `TDictionary<string,TXmlWordConfigField>` در `0x004B4C38` و `TDictionary<string,TXmlWordConfigTwinField>` در `0x004B6A70`. همچنین `TWordViwer` VMT candidate در `0x004B10A4`، destroy slot `0x004B10A0` و method RTTI `Destroy` در `0x004B1629` نشان می‌دهند `0x004D1148` destructor است، نه AddXml. routine در `0x004D0D24` دیکشنری‌ها را می‌سازد؛ `AddCustomDocPropertiesToDic` با wrapperهای Add که TD32 به‌اشتباه Remove نام‌گذاری کرده، descriptorهای single/twin را در mapهای مربوطه درج می‌کند؛ مسیر population با callsiteهای `0x004D15C6` و `0x004D1635` اثبات شده است.

workflow بعدی روی جزئیات XML field accessorهای `+0xBC/+0xC0` و تطبیق ترتیب property enumeration در Writer با Word متمرکز می‌شود؛ منبع population دیگر unresolved نیست.

## تأیید CI پس از اصلاح مستندات descriptor — 2026-11-17

workflow `python-bridge.yml` پس از تغییرات docstring و تفکیک روشن descriptorهای موقت reconciliation از mapهای اولیه با موفقیت اجرا شد: **108 تست موفق، 2 تست اختیاری skip**؛ run `44023065489` (latest confirmed run).

ردیابی جدید `CreateOptionFormFields` (`0x004CFC74`) نیز به workflow تحلیل BPL افزوده شده است؛ این تابع نامزد تازه‌ای برای یافتن مسیر ساخت اولیه mapهای single/twin است، اما تا دریافت artifact هنوز نتیجه‌ای به آن نسبت داده نمی‌شود.

## وضعیت جدید مهندسی معکوس — 2026-11-17

- اسکن دقیق Import Table، thunk واقعی و caller مستقیم APIهای Delphi را جدا کرد: `LoadPackage` در `0x0047E15F`، `GetClass` در `0x00470E07`، `StartExe` در `0x004014BA` و `GetProcAddress` در `0x00401720` / `0x00401DA8` / `0x00401DCA`.
- `ClassCreate` و `ClassDestroy` در سرویس callsiteهای متعدد دارند؛ برای اتصال قطعی آن‌ها به مسیر درخواست، trace کامل `ParseMethod` و دو callsite اصلی در workflow جدید اضافه شده است.
- `GetXmlFieldInfo` اکنون دقیق‌تر مدل شده: اول single-map را جست‌وجو می‌کند، سپس twin-map را؛ در مسیر twin با `CompareText` عضو مقابل را برمی‌گرداند. تابع `resolve_twin_field_partner` و تست آن اضافه شد.
- CI پایتون: **108 تست موفق، 2 مورد optional skip** در run `44023065489`.
- نسخهٔ کامل لینوکس و سازگاری end-to-end با Almas هنوز تأیید نشده‌اند؛ پروتکل بازگشت در حالت cancel/discard، همهٔ فیلدها، تصاویر/امضاها و چاپ واقعی همچنان نیازمند fixture و آزمون یکپارچه‌اند.

## تأیید callsiteهای LoadPackage و GetClass در سرویس — 2026-11-17

- `LoadPackage` از thunk آدرس `0x00402174` در `0x0047E15F` و داخل gate بارگذاری BPL فراخوانی می‌شود.
- `GetClass` از thunk آدرس `0x00402354` در `0x00470E07` و پس از prefix شدن `T` به مقدار XML `class` فراخوانی می‌شود.
- `ClassCreate` و `ClassDestroy` در `0x00471220` و `0x0047127F` به ساخت/پاک‌سازی شیء metadata به نام `TMethodInfo` تعلق دارند؛ این‌ها را نباید با ساخت کلاس متد واقعی BPL اشتباه گرفت.
- workflow جدید، callsiteهای `StartExe` و `GetProcAddress` را نیز با محدوده کد اطرافشان بررسی می‌کند.

## تکمیل چرخه‌ی TMethodInfo و تفکیک توابع runtime — 2026-11-17

- `TMethodInfo` در `0x00471214` ساخته می‌شود؛ `ClassCreate` در `0x00471220` و مقداردهی دیکشنری Params در `0x00471232` انجام می‌شود.
- تابع cleanup از `0x00471258` آغاز می‌شود، دیکشنری Params در offset `+0x08` را آزاد می‌کند و `ClassDestroy` را در `0x0047127F` فراخوانی می‌کند.
- `StartExe` در `0x004014BA` بخشی از package startup و `GetProcAddress` در `0x00401720` بخشی از dynamic-symbol lookup است؛ هیچ‌کدام مسیر dispatch جداگانه‌ی EMWAT نیستند.
- callsiteهای اصلی `LoadPackage` و `GetClass` در بخش service executable analysis ثبت شده‌اند.

### تکمیل مسیر ParseMethod — 2026-11-17

- `GetClass` در `0x00470E07` نام کلاس استخراج‌شده از XML را resolve می‌کند؛ در صورت شکست، پیام `Unable to load "<class>" class.` ساخته می‌شود.
- بعد از resolve، نام کلاس با `TUpgradeEmwat` مقایسه و نتیجه در `method-info+4` ذخیره می‌شود؛ سپس instance از طریق `TObject.$bctr` ساخته و pointer مربوط به method-info در `instance+4` قرار می‌گیرد.
- فراخوانی غیرمستقیم `0x00470EF6` از `[instance.VMT+0x0C]` انجام می‌شود؛ در VMT کلاس پایه `TEmwatMethod` این slot به wrapper عمومی `Invoke` در `0x0046C9E0` می‌رسد. این wrapper helper داخلی `0x0046C82C` را اجرا می‌کند و سپس از slot `+0x10`، `PerformMethod` کلاس فرزند را فراخوانی می‌کند.
- prefix کلاس قطعی است: ثابت `T` در `0x004710E0` و مقدار XML `class` به helper `0x00401310` داده می‌شوند؛ این thunk به `System.@UStrCat3` می‌رود و رشته `T` + نام کلاس را می‌سازد، سپس `GetClass` آن را resolve می‌کند.

## چرخه‌ی واقعی ساخت و اجرای کلاس BPL مشخص شد — 2026-11-17

- `GetClass` در `0x00470E07` کلاس Delphi متناظر با XML را resolve می‌کند.
- `TObject.ClassName` در `0x00470E5D` نام کلاس را با `TUpgradeEmwat` مقایسه می‌کند و نتیجه را در `TMethodInfo+0x04` می‌گذارد.
- `TObject.Create` در `0x00470EDC` نمونه‌ی واقعی متد BPL را می‌سازد.
- اشاره‌گر `TMethodInfo` در offset `+0x04` نمونه قرار می‌گیرد و VMT slot `+0x0C` در `0x00470EF6` فراخوانی می‌شود.
- `TObject.Free` در `0x00470F42` نمونه را آزاد می‌کند.

این چرخه با ساخت/تخریب شیء metadata یعنی `TMethodInfo` از طریق `ClassCreate`/`ClassDestroy` متفاوت است.

## مسیر ارسال پاسخ HTTP شناسایی شد — 2026-11-17

تابع `0x004610FC` با RTTI name به‌عنوان `TIdHTTPResponseInfo.WriteContent` شناسایی شد. این helper پاسخ Indy را با توجه به status/content ارسال می‌کند و pointer موقت `ContentText` را پاک‌سازی می‌کند. callsiteهای تأییدشده: `ParseMethod` در `0x00470F34` و شاخه‌های `init` و `heartbeat` در `0x0047C237` و `0x0047C2A9`. مسیر پاسخ عادی connector همچنان به `bResultSet` وابسته است: اگر connector پاسخ را خودش ثبت کند handler مسیر پیش‌فرض را رد می‌کند؛ در غیر این صورت خروجی را در `AResponseInfo.ContentText` می‌گذارد و `WriteContent` را صدا می‌زند.

## تفکیک دو مسیر WriteContent — 2026-11-17

- `0x004610FC` در خود سرویس، sender عمومی Indy است؛ برای fallback عمومی و مسیرهای `init`/`heartbeat` استفاده می‌شود.
- `0x0040448C` در BPL، thunk واردشده‌ی `IdCustomHTTPServer.TIdHTTPResponseInfo.WriteContent` است؛ `LoadDocument` پس از قرار دادن XML `response-word` در `ContentText` آن را صدا می‌زند و `bResultSet=true` می‌کند. در نتیجه پاسخ موفق EditWordDocument از fallback عمومی سرویس عبور نمی‌کند.

## اصلاح مسیر احتمالی ساخت mapهای فیلد — 2026-11-17

`CrateOptionFormFields` در `0x004CFC74` از `LoadOptions` فراخوانی می‌شود و mapهای descriptor را populate نمی‌کند؛ این نامزد رد شد. در generic dictionaryها، نام‌های TD32 برای بعضی متدها با method-table واقعی جابه‌جا هستند: `0x004D552C` در method table با نام `AddOrSetValue` ثبت شده و در بدنه واقعاً از `DoSetValue` برای درج/به‌روزرسانی استفاده می‌کند؛ `0x004D559C` در مسیر `GetXmlFieldInfo` نقش key-presence دارد، با وجود برچسب TD32 `ContainsValue`.

هر entry دیکشنری سه slot دارد: hash، کلید UnicodeString و pointer مقدار descriptor. constructor از نوع `TDictionary.Create(IEnumerable<TPair>)` در `0x004D5100` pairها را پیمایش و با `AddOrSetValue` وارد map می‌کند؛ اما caller مستقیم برای این constructor هنوز پیدا نشده و منبع enumerable مشخص نیست.

## اصلاح هویت destructor و initializer viewer — 2026-11-17

`0x004D1148` دیگر به‌عنوان `AddXmlWordConfigFieldsToDic` ثبت نمی‌شود. VMT/RTTI آن را `TWordViwer.Destroy` نشان می‌دهند: destroy slot در `0x004B10A0` به این آدرس اشاره می‌کند و method record در `0x004B1629` نام `Destroy` دارد. routine در `0x004D0D24` که `LoadDocument` در `0x004B78E9` صدا می‌زند، برخلاف TD32 label `$bdtr`، flags و منابع viewer را initialize می‌کند و سه dictionary را در `+0x64/+0x68/+0x6C` می‌سازد. constructor helperهای تک/دو فیلدی به‌ترتیب `0x004D5C28` و `0x004D71E0` هستند؛ semantics و منبع اولیه‌ی داده‌ی آن‌ها هنوز در حال ردیابی است.

## رفع ابهام نهایی dispatch سرویس به BPL — 2026-11-17

- `0x00401310` thunk به `System.@UStrCat3` است؛ پس ساخت `T` + مقدار XML `class` پیش از `GetClass` اثبات شد.
- VMT slot `+0x0C` روی instance متد BPL به wrapper `TEmwatMethod.Invoke` در `0x0046C9E0` می‌رسد. برچسب TD32 برای این wrapper (`Finalization`) گمراه‌کننده است؛ خود method-table/VMT و بدنه نشان می‌دهند این wrapper، helper داخلی `0x0046C82C` را صدا می‌زند.
- wrapper سپس VMT slot `+0x10` را فراخوانی می‌کند؛ برای `TEditWordDocument` این slot به `0x005EE82C` می‌رسد و آن `PerformMethod`، `LoadDocument` را اجرا می‌کند.
- مستند کامل این crosswalk در `docs/EMWAT-SERVICE-EXECUTABLE-ANALYSIS.md` ثبت شد.

## ساختار واقعی mapهای descriptor و نام‌های گمراه‌کننده TD32 — 2026-11-17

- routine `0x004D0D24` که از `LoadDocument` در `0x004B78E9` فراخوانی می‌شود، با وجود label اشتباه `$bdtr`، مسیر setup/constructor-like است و سه dictionary را می‌سازد: `+0x64` برای `TDocumentCProperty`، `+0x68` برای single descriptor و `+0x6C` برای twin descriptor.
- constructorهای descriptor map به‌ترتیب `0x004D5C28` و `0x004D71E0` هستند؛ هر دو TObjectDictionary با ظرفیت اولیه صفر و comparer/ownership configuration می‌سازند.
- `TWordViwer.$bctr` در `0x004D08B4` مسیر جداگانه option form است و فقط از `ShowRecAndCcOptionForm` فراخوانی می‌شود؛ این routine فیلدهای Rec/CC را می‌سازد و مسیر populate اولیه descriptor map نیست.
- `0x004D552C` برای single و `0x004D6AE4` برای twin در عمل AddOrSetValue هستند، هرچند TD32 هر دو را `ContainsKey` نام‌گذاری کرده است. در حالت key موجود، به helper update و در حالت key جدید، پس از grow به helper insert می‌روند.
- هر entry سه slot دارد: hash، UnicodeString key و pointer به descriptor. helperهای update/insert نیز بعضاً TD32 label نامتناسب دارند؛ semantics از بدنه disassembly تعیین می‌شود.
- منبع اولیه‌ی insertion هنوز پیدا نشده است. batch جدید trace کامل `LoadDocument`، همه‌ی دسترسی‌های `TWordViwer` به offsets `+0x64/+0x68/+0x6C` و helperهای update-existing را اجرا می‌کند.

## آزمون transport برای session همگام و close-driven — 2026-11-17

- تست جدید `test_document_post_waits_for_close_while_heartbeat_remains_responsive` اضافه شد.
- تست ثابت می‌کند POST مربوط به سند تا آزاد شدن رویداد close پاسخ نهایی نمی‌دهد، اما به‌دلیل `ThreadingHTTPServer`، درخواست مستقل heartbeat در همان زمان پاسخ‌گو می‌ماند.
- اجرای CI در run `44029314633` موفق شد: **109 تست** در 5.105 ثانیه.

## نتیجه‌ی منفیِ تقویت‌شده برای مسیر populate کردن descriptor mapها — 2026-11-17

Artifact `14304323294` با موفقیت تولید شد. trace کامل `LoadDocument` از `0x004B7724` تا `0x004B8A84` و scan پنجاه متد `TWordViwer` برای offsets `+0x64/+0x68/+0x6C` اجرا شد. 39 reference پیدا شد؛ در کلاس viewer، نوشتن روی `+0x68/+0x6C` فقط هنگام انتساب dictionaryهای ساخته‌شده در setup (`0x004D0F98/0x004D0FB3`) دیده شد. در scan کل PE و byte-level rel32 نیز callsite مستقیمی برای helperهای insertion single/twin پیدا نشد. این نتیجه مسیر populate را هنوز قطعی نمی‌کند، چون dispatch غیرمستقیم/VMT، callback یا object خارجی ممکن است؛ اما شواهد فعلی هیچ مسیر insertion مستقیم را تأیید نمی‌کنند.

## اصلاح builder descriptorها بر اساس مسیر واقعی Add — 2026-11-17

`build_word_custom_property_field_maps()` به‌روزرسانی شد تا دیگر property name را به‌اشتباه معادل XML field name فرض نکند. اکنون `xml_fields` را به‌صورت اختیاری و هم‌تراز با ترتیب property enumeration می‌پذیرد و خود `WordField` node را نگه می‌دارد؛ در صورت نبود آن، reference در descriptor برابر `None` می‌ماند. تست‌ها نگهداری XML node با index مشترک و ردکردن sequenceهای ناهم‌طول را پوشش می‌دهند. Writer catalog فعلاً به این builder وصل نشده، چون enumeration order مرتب‌شده‌ی catalog هنوز با ترتیب Word ثابت نشده است.

## CI پس از اصلاح descriptor builder — 2026-11-17

Python bridge CI در run `44030420508` موفق شد: **111 تست موفق، 2 skip اختیاری** در 5.163 ثانیه. تست‌های جدید هم‌ترازی `property_names` و `xml_fields`، رد sequenceهای ناهم‌طول و حفظ reference برابر `None` هنگام نبود XML node را پوشش می‌دهند.

## حفظ ترتیب خام Custom Propertyهای Writer — 2026-11-17

`WriterDocumentCatalog` اکنون علاوه بر فهرست sorted قبلی، فیلد `custom_document_properties_in_info_order` را هم از ترتیب خام `XPropertySetInfo.getProperties()` برمی‌گرداند. این داده فقط نام‌ها را می‌خواند، نه valueها. تست FakeDocument ثابت می‌کند ترتیب خام با sorted display اشتباه گرفته نمی‌شود؛ تست UNO واقعی نیز برابری آن با sequence مستقیم API را assert می‌کند. این قدم زیرساخت مقایسه‌ی ترتیب Word/Writer را فراهم می‌کند، اما هنوز ثابت نمی‌کند UNO order همان Word CustomDocumentProperties index order است.

## UNO integration پس از حفظ ترتیب خام propertyها — 2026-11-17

LibreOffice UNO integration در run `44030867583` موفق شد: **11 تست** در 3.974 ثانیه. تست جدید `custom_document_properties_in_info_order` را با ترتیب مستقیم `XPropertySetInfo.getProperties()` مقایسه می‌کند و ثابت می‌کند adapter ترتیب خام API را بدون sort حفظ می‌کند؛ این هنوز معادل بودن ترتیب Writer با Word را اثبات نمی‌کند.

## CI پس از تبدیل descriptor payload به WordField node — 2026-11-17

Python bridge CI در run `44031548179` موفق شد: **111 تست موفق، 2 skip اختیاری** در 5.120 ثانیه. تست‌ها اکنون به‌جای string فرضی، reference به خود `WordField` node متناظر در `wordConfig.fields` را بررسی می‌کنند.


## سخت‌سازی تکمیلی HTTP و CI — 2026-11-17

- تست‌های transport اکنون علاوه بر duplicate Origin، Referer، Content-Type و Content-Length، duplicate Host و ارسال هم‌زمان Transfer-Encoding با Content-Length را نیز پوشش می‌دهند.
- رفتار مورد انتظار در هر دو حالت جدید رد درخواست با 400 است؛ در تست Transfer-Encoding بررسی می‌شود handler برنامه اصلاً فراخوانی نشود.
- CI روی commit 18fe366e8be5badcdd5a5edfeea5be8ff33aeff1 موفق شد: **117 تست موفق**؛ run 44075572673.


## Recovery catalog JSON contract — 2026-11-17

- `RecoverySnapshotService.catalog_json()` now emits a versioned (`schema_version: 1`) metadata-only JSON catalog for native UI clients. The contract contains newest-first snapshot metadata and deliberately excludes absolute private-store paths and document bytes.
- Restore remains a separate explicit operation requiring a caller-selected destination; the service still delegates validation and atomic no-overwrite publication to `RecoverySnapshotStore`. Discard remains explicit by session ID.
- Added a serialization regression test for schema version, content-addressed document names, and absence of private paths/content. Python CI run `44102938620` was queued at the time of this update; do not report it green until its result is checked.
- This is a UI integration boundary, not yet a graphical recovery picker or HTTP endpoint. The desktop/UI composition still needs to provide a trusted file-save dialog and explicit discard confirmation.


## Recovery catalog CI result — 2026-11-17

- The first serialization-test run `44102938620` exposed a test-fixture assumption: snapshot filenames are content-addressed by SHA-256, not by session ID. The production code behaved as designed; the assertion was corrected to validate the documented content-addressed filename shape.
- Corrected run `44103059363` on commit `2f7c771a213a9769c5a0d1e112b4b9edf3e2d74e` passed: **141 tests run, 139 passed, 2 optional LibreOffice tests skipped**.


## Indexed signer slot alignment — 2026-11-17

- Added `IndexedSignerSlot` and `build_indexed_signer_slots()` to align the seven observed repeated signer-field families by numeric index.
- The catalog reports absent families explicitly, orders slots numerically, and preserves the original capture order of fields inside each slot. It does not synthesize missing fields or infer Word-to-Writer property mappings.
- Added regression coverage for sparse indices, incomplete slots, and capture-order preservation. This improves schema auditing before mapping work; it is not evidence that all 180 EMWAT fields are understood.


## Signer-slot catalog verification and recovery consumer spec — 2026-11-17

- Added `build_indexed_signer_slots()` / `IndexedSignerSlot` to align recognized signer fields by numeric index, preserve capture order within each slot, and report absent families without synthesizing values or guessing mappings.
- The first CI attempt found an incorrect expectation in the new test (the fixture included `SignNumberOfSigner3`); the assertion was corrected. The corrected run `44105991823` on `ef95c118111a4e2909657e9e06f75a87a68a326b` passed: **142 tests run, 140 passed, 2 optional LibreOffice tests skipped**.
- Added `docs/RECOVERY-CATALOG.md` specifying the in-process JSON consumer contract, explicit save-dialog restore flow, confirmation requirement for discard, and prohibition on exposing the service as an unauthenticated HTTP endpoint.


## Recovery snapshot bound validation — 2026-11-18

- `RecoverySnapshotStore` now requires `max_snapshot_bytes` to be a positive built-in integer; booleans, floats, strings, zero, negative values, and `None` are rejected before filesystem access.
- Added constructor regression coverage for all rejected input classes and documented the bound contract in `docs/RECOVERY-RETENTION.md`.
- Implementation commit: `1a9cd2843c2fd37d6b547ddd668668ec116d5d6f` (restores the full prior implementation and applies the strict validation as a one-condition change); regression tests: `2d16580d94c6c4a8021799464d2d31d0c2fb16b0`; documentation commits: `3df46fcbfafdbf3d7abd4f4abb12bbe99f272c19` and this status update.
- CI for this follow-up is pending; no test pass is claimed until the new branch head completes all relevant workflows.


## EditWord request bounds and dispatcher validation — 2026-11-18

- The EditWord request parser exposes independent positive-integer limits for decoded Word bytes, encoded Word characters, decoded wordConfig bytes and encoded wordConfig characters. The service constructor now exposes and forwards all four limits instead of silently relying on parser defaults.
- Public `MethodCall` input is checked for expected class/parameter container and text values; `signData` remains opaque text because its complete wire encoding has not been established.
- The XML dispatcher now rejects non-built-in-integer payload limits (including bool/float/string), non-text/blank class names and non-callable handlers at registration time.
- Regression tests cover malformed request objects, every invalid limit category, configured encoded-config bounds, service forwarding, and dispatcher registration validation.
- Implementation and test changes are committed in the EditWord request parser, service and dispatcher modules; documentation commits include `75573fa` and `df39bb9`. Service commits: `120f7fc` / `dcfab72`; dispatcher commits: `f8a6edf` / `5487ef4`.
- CI verified before service and dispatcher follow-ups: Python bridge `44302976157`, Native image core including ASan/UBSan `44302976163`, and LibreOffice UNO `44302976143` all passed. Service/dispatcher follow-up commits are not yet covered by those earlier runs; new CI status must be checked separately.


### Dispatcher request-boundary validation — 2026-11-18
- `XMLMethodDispatcher` now rejects non-`BridgeRequest` inputs and non-bytes request bodies with the same sanitized HTTP 400 response used for malformed XML, rather than leaking AttributeError/TypeError from the public callable boundary.
- Added regression cases for None, arbitrary objects and a BridgeRequest carrying a non-bytes body.
- Implementation commit: `7956525e4974256dd726ae19cb1363cb694a53a5`; tests: `0e3a590b3419d0846ad9cbb7d7fb4a01125e38f5`.
- Full CI on the combined branch head `0231f31705ce2a9e97f932161d07a6acf71dae14` passed: Python bridge run `44304965568` (**196 tests, 194 passed, 2 optional LibreOffice skips**); Native image core run `44304965055` (build and ASan/UBSan jobs passed); LibreOffice UNO roundtrip run `44304965075` (UNO runtime and real Writer roundtrip job passed).


### HTTP response status type validation — 2026-11-18
- The loopback transport now requires response status codes to be built-in integers in the HTTP 200–599 range. Floats, strings, booleans, null and out-of-range values are rejected and converted to the existing sanitized 500 response.
- Added transport regression coverage for all invalid status classes.
- Implementation commit: `104aa3181ae36df9db6c0dfce447dceb230f698f`; tests: `82f39637440b19d215491e2c90c4a0eebb6a63e2`.
- This bridge follow-up is newer than the green combined CI above; fresh Python/native/UNO results are pending.


### HTTP response and Origin allowlist boundary hardening — 2026-11-18
- Bridge responses now require a built-in integer status code in the 200–599 range; malformed status values are sanitized to HTTP 500.
- Both Origin allowlists now require set/frozenset containers containing only non-empty strings. This prevents accidentally passing a string as an allowlist, where Python substring membership could weaken exact Origin matching.
- Parent-Origin allowlist entries are type-checked before URL parsing; malformed values fail at server construction.
- Added regression coverage for invalid status types and malformed allowlist containers/entries.
- Commits: status implementation `104aa318` / tests `82f3963`; allowlist implementation `9231fd6`, `95c735f` / tests `a978d0e`, `4ea99bb`.
- Full CI on code/test head `4ea99bb3b1cf2b1ed664e5420c640d657e7df61a` passed: Python bridge run `44305529480` (**198 tests, 196 passed, 2 optional LibreOffice skips**); Native image core run `44305529408` (build and ASan/UBSan jobs passed); LibreOffice UNO run `44305529564` (runtime verification and real Writer roundtrip passed). The subsequent project-status commit is documentation-only.


## Recovery manifest read hardening — 2026-11-18

- Recovery metadata reads now have a strict 64 KiB ceiling and use a bounded read (limit + 1 byte) rather than unbounded `read_text()`.
- Manifest access opens with `O_NOFOLLOW` where supported, checks the opened descriptor is a regular file, and parses strict UTF-8 JSON objects only.
- Oversized, symlinked, malformed and non-regular manifests fail closed; catalog enumeration skips invalid entries.
- Added regression tests for an oversized manifest and a symlinked manifest targeting a file outside the recovery session.
- Implementation: `cced3b65a7485fcde9503c7df94f1abd773411d9`; tests: `513e6c819e0e7eb952cd75e02090199029c636c7`; documentation: `186e94b354583655b83a0bd716aac0e8dd30d184`.
- Full CI on the combined code/test state through `26c831ebf80cb94178912158f1c712f93082582d` completed successfully: Python bridge run `44318451374` (**201 tests, 199 passed, 2 optional LibreOffice skips**); Native build + ASan/UBSan run `44318451310` (both jobs passed); LibreOffice UNO run `44318451381` (UNO runtime and real Writer roundtrip passed). The branch head `d93601fa0f418b378b73982d4c5a962b5a297ba0` is documentation-only beyond that tested code/test state.

- Follow-up review also catches JSON parser recursion-depth failures inside the same bounded manifest reader; deeply nested metadata now fails closed with `recovery_manifest_invalid`. Commits: implementation `570fb8de7c22f73bda8e37f29adc058b699fc793`, regression test `26c831ebf80cb94178912158f1c712f93082582d`, documentation `b2e12ab948c638ac4c0e91d035927d5ccbc224c4`.

## Recovery snapshot payload read hardening — 2026-11-18

- Snapshot payloads now open with `O_NOFOLLOW` where supported and must be regular files.
- The descriptor size is checked against the configured snapshot cap plus encryption envelope overhead; the actual read is also capped at limit + 1 byte to handle file growth after `fstat`.
- Added regression tests for oversized payloads and a simulated symlink-replacement race between path precheck and descriptor open.
- Implementation: `4e4bc2b4363ff69804f7bb219d15caace1fd45b6`; tests: `fb56e821129aa0ad665556f5e6fa3b434af0a0c7`. Python bridge run `44319343914` passed (**203 tests, 201 passed, 2 optional skips**); LibreOffice UNO run `44319344050` passed (**14 tests**, including real EditWord response-handler roundtrip); Native ASan/UBSan job in run `44319343995` passed. Native `build-test` job in that run was still installing dependencies at the time of this status update, so full native workflow completion remains pending.


## تأیید نهایی CI روی سر فعلی PR — 2026-11-18

- اجرای تازه روی commit فعلی PR یعنی `8b9f74dce8d7c5648bc53b4668212c76ae8e90d9` هر سه workflow را با موفقیت کامل کرد:
  - Python Bridge، run `44319637922`: **203 تست اجرا شد؛ 201 موفق و 2 تست اختیاری skip**.
  - Native image core، run `44319637947`: هر دو job ساخت/CTest و ASan/UBSan موفق؛ چهار CTest شامل image document، codec، scanner contract و document I/O همگی پاس شدند.
  - LibreOffice UNO، run `44319637936`: **14 تست موفق**؛ شامل Writer roundtrip و اجرای سند واقعی از مسیر EditWord response handler.
- این نتایج مستقیماً به head فعلی PR متصل‌اند؛ وضعیت قبلی مبنی بر pending بودن Native build-test دیگر معتبر نیست.
- PR #2 همچنان Open، Draft و Unmerged است. مقایسه با `main`: 160 commit جلوتر و صفر commit عقب‌تر.
- این CI هنوز سازگاری زنده با Almas، اسکنر فیزیکی، parity معنایی کامل Word/Writer، فرمت Windows `.easz` و قرارداد واقعی Cancel/Discard را اثبات نمی‌کند.


## Native SANE fixed-point conversion safety — 2026-11-18

- Review found that the generic 100000-DPI input ceiling could still reach `SANE_FIX(dpi)` for a scanner exposing a `SANE_TYPE_FIXED` resolution option. SANE fixed values are signed 16.16 `SANE_Word`; values above the representable range could overflow during floating-point-to-integer conversion.
- Added `scanner_detail.hpp` with a checked conversion to signed 16.16, rejecting non-finite, non-positive and out-of-range values before casting. The scanner now uses this helper instead of invoking `SANE_FIX` on unbounded-by-format values. Integer-valued SANE resolution options retain their existing path.
- Added native tests for normal conversion, the 32768-DPI overflow boundary, infinity and NaN. No physical scanner is required for these pure conversion tests.
- Commits: helper `c020d17`, implementation `5b253e0`, tests `8360337`.
- Fresh Python/Native/UNO CI for this follow-up is pending; do not treat the preceding green PR-head run as validation of these new native changes.


## تأیید CI اصلاح fixed-point اسکنر — 2026-11-18

- تغییر native در code/test commit `83603371b8cfbae3b1e7817a79b0d3e62ed0ca4a` در هر سه workflow موفق شد:
  - Python Bridge run `44320784317`: **203 تست؛ 201 موفق، 2 تست اختیاری skip**.
  - Native image core run `44320784491`: build-test و ASan/UBSan هر دو موفق؛ هر چهار CTest در هر دو پیکربندی پاس شدند.
  - LibreOffice UNO run `44320784298`: **14 تست موفق**، شامل Writer roundtrip و EditWord response-handler.
- بنابراین اصلاح fixed-point در build عادی و sanitizer تأیید شده است. UNO نیز روی همان کد/test commit سبز است.
- PR head فعلی پس از مستندسازی `b35a3b8513abebd391bc5dc69aef7e7a71877f69` است؛ تغییرات پس از code/test commit صرفاً مستندات و metadata هستند.


## Bridge constructor contract follow-up — 2026-11-18

- `BridgeHTTPServer` now validates the request handler is callable and `require_origin` is an actual boolean at construction time. Invalid configuration fails immediately rather than producing a request-time 500 or relying on truthiness.
- Added regression tests for non-callable handler values and non-boolean Origin policy values; both supported boolean settings are covered.
- Implementation: `bb50f32fedb25e9d561c6886bdd36365058c9087`; tests: `966c666545ff9851e569ecffe0e57fcde44d1a5b`.
- Fresh CI is running for the combined branch head; results are pending and are not claimed passed.


## Invoke query parser field-count bound — 2026-11-18

- The loopback bridge now calls `parse_qsl(..., max_num_fields=1)` because the captured route accepts exactly one non-empty `invoke` parameter. Extra query fields are rejected before dispatch without materializing an arbitrarily large parameter list.
- Added a transport regression test proving a query with extra fields returns the existing sanitized 400 response and never invokes the application handler.
- Implementation: `6e20a554e71db777aec8b133596814d45a800365`; test: `673eecda6f486eceda12447f9e53821ab2b2b2bc`.
- CI for the updated code/test head is pending.


## Parallel workstreams follow-up — 2026-11-18

### Browser/Almas E2E
- Strengthened the synthetic application composition test: it now parses the complete HTTP response, validates the observed `response-word`/MIME/Base64 structure, and decodes the returned bytes to assert byte-for-byte equality with the final Office adapter output.
- This proves the mocked loopback → XML dispatch → EditWord service → Office adapter → response serializer path. It is not a live Almas Gam or physical LibreOffice UI test.
- Test commit: `afb7e4d003d678f3bccbfb08fc26edf54e02d551`.

### Ubuntu packaging
- Added CMake install rules for the native image/scanner library and public headers, using GNUInstallDirs.
- This is a staged library installation foundation only. There is still no production bridge daemon, desktop entry, GUI, service unit, or complete .deb package.
- CMake commit: `34f23f303329c8781ba41af3dd6e75545e140522`; follow-up kept install rules dependency-neutral: `50044deab7259f17295824c9581421b6cecdae97`.

### Recovery UI, Word mapping, EASZ and scanner
- Confirmed existing toolkit-neutral RecoverySnapshotService/RecoveryPickerController supports metadata listing, explicit-destination restore, and confirmed discard; it is not a graphical UI.
- Confirmed the Word field pipeline handles declared URL/Base64 encodings, indexed signer field families and evidence-bounded property audits. `signData` remains opaque because separator/concater semantics are not proven.
- Confirmed .easz is still not implemented: no authorized synthetic encrypted archive fixture exists.
- Confirmed SANE native support remains single-frame Gray/RGB; ADF, duplex, multi-page, cancellation and physical hardware are not validated.

### Integration/install documentation
- Added `docs/UBUNTU-INSTALLATION-AND-INTEGRATION.md` with reproducible native build/install commands, Python/UNO setup boundaries, synthetic E2E coverage, field/signData limits, recovery UI boundary, .easz fixture requirements, scanner acceptance criteria and release blockers.
- Linked it from README.
- Documentation commits: `b845e45f9b6da5d2c19874229f1f2c56f851f7de`, `8d7073a88615f3be71716c5124140d0b6666db5a`.

CI for the new E2E test and CMake install rules is pending on the latest code/test head; no result is claimed until GitHub Actions completes.


## E2E test correction — 2026-11-18

- The first Python workflow for the strengthened E2E assertion exposed a test-only UnboundLocalError: a function-local import base64 shadowed the module-level import used earlier in that test.
- Removed the redundant local import. The failure was in test setup, not the bridge or response implementation.
- Correction commit: `3f2bf37d90fa12d8a828106263f794b4a812a61a`.
- CI for the corrected head is pending; the earlier failed run is retained as evidence and is not represented as passing.


## Debian native-core package lifecycle — 2026-11-18

- Added CPack DEB metadata for `emwat-native-core-dev`, a host-architecture development package containing the native static library and public headers.
- Package version follows the native CMake project version (currently 0.1.0); the CPack version is configurable for reproducible upgrade testing.
- Declared package dependencies: `libpng-dev`, `libjpeg-dev`, `libtiff-dev`, `libsane-dev`. The package does not include the Python bridge, daemon, GUI, desktop entry, or user data.
- Added a dedicated CI lifecycle job that builds 0.1.0 and 0.1.1 packages, installs the first, upgrades to the second, verifies the installed library/header, removes the package, and verifies the files are removed.
- This is the first real Debian package lifecycle for the native development component only. A complete EMWAT desktop package remains blocked on the production entrypoint, selected GUI toolkit, service lifecycle, Python/UNO runtime policy, and desktop integration.
- Implementation commits: CPack metadata `4e359951`; native-architecture correction `95291d4e`; package lifecycle CI `68291cdb` and version assertions `c654cb25`.


## Recovery picker UX design — 2026-11-18

- Added `docs/RECOVERY-PICKER-UX.md`: toolkit-neutral view states, newest-first list, selection preservation/stale-selection clearing, native Save-dialog restore, explicit destructive discard confirmation, accessibility, encryption/key-unavailable behavior, and opt-in retention boundaries.
- The design maps the same contract to GTK ListView/ColumnView or Qt QListView/QTableView without selecting either toolkit or adding GUI dependencies.
- Implementation commit: `bc363e2aa784afd84682a8fc568b93b24a5412d9`.


### Debian package lifecycle CI result — 2026-11-18

- Native workflow run `44327277244` completed the Debian package lifecycle job successfully.
- CI generated `emwat-native-core-dev` packages for versions 0.1.0 and 0.1.1, installed 0.1.0, upgraded to 0.1.1, verified the package version and installed library/header, removed the package, and verified the installed files were gone.
- The same run's native `build-test` and staged CMake install jobs passed. At the time of this note, the sanitizer job was still running; no sanitizer result is inferred from the package lifecycle result.
- Python and UNO runs on code head `97c89c3` completed successfully: Python `44327277074`, UNO `44327277376`. The latest Recovery UX document commit is documentation-only beyond that code state.
- This validates install/upgrade/remove for the native development package only. It does not validate a full desktop application's configuration migration, service restart, Python/UNO runtime, or user-data preservation.



## GTK Recovery picker hardening — 2026-11-19

- Recovery rows now use the supported GTK widget-name API for stable session identity rather than attaching arbitrary attributes to GI wrappers.
- Catalog timestamps are formatted defensively; extreme but finite timestamps no longer crash the GTK refresh/render path.
- Restore and discard refresh stale selections and show a bounded user-facing error if the selected snapshot disappears between listing and action.
- Added a headless regression test for extreme timestamp formatting while preserving lazy PyGObject import.
- Commits: GTK implementation `3660bdf`, follow-up stale-selection handling `88fa00e`; tests `fa008a6`; Ubuntu integration documentation `8182dec`.
- These changes do not establish a live GTK window/runtime test. The Python/Native/UNO CI for the new head is pending and will be recorded only after completion.
- The Debian package remains `emwat-native-core-dev` only; no full desktop installer or production user-service entrypoint is claimed.


## Writer lifecycle regression coverage — 2026-11-19

- Added adapter tests proving a failed close-time snapshot attempt is reset on a later close attempt, and that the session is not marked closed until UNO reports `notifyClosed`.
- Added save-event tests: only `OnSaveDone` and `OnSaveAsDone` are treated as confirmed engine saves; pre-save and generic save notifications are ignored.
- Updated the Almas/Writer lifecycle contract to record these boundaries and keep Cancel/Discard response semantics explicitly unresolved pending a sanitized reference capture.
- Test commit: `33adcbfc18886933c6e4e47f52d1f359a10ec568`; contract update: `b3a22d10c2be0e14f4fb8caed7c07fa07cf6193b`.
- Previous head `6ce47620` CI completed successfully: Python run `44549072545`, UNO run `44549072601`, Native run `44549072522`; all jobs passed. At the time of this update, GitHub reported no workflow runs associated with exact head `8da682e9`; the new lifecycle tests are committed but their CI result is not yet available.
- No live Almas fixture, confirmed Writer discard/cancel implementation, or full desktop package is claimed.


## Close-driven Writer handoff regression — 2026-11-20

- Recorded the operator-confirmed reference behavior: closing the Word window without pressing Save returns control to Almas. This establishes a close-driven handoff requirement, but does not identify whether a Save/Don't Save/Cancel prompt appeared or which choice was selected.
- Added a focused adapter regression proving that final close-time snapshot creation and terminal-close signaling do not require a preceding `OnSaveDone`/`OnSaveAsDone` event.
- Test commit: `2776d889b330b88177ce7caeb86f659df56e4934`; lifecycle contract commit: `ddc95ce24bd6b7185fcb4b2c073d9f53e293ebdb`.
- No workflow runs are currently associated with the latest PR head `ddc95ce24bd6b7185fcb4b2c073d9f53e293ebdb`; the new regression is committed but not yet CI-verified. No live Almas or interactive Writer prompt test is claimed.


## Writer close/discard evidence checkpoint — 2026-11-20

- Added `docs/WRITER-CLOSE-DISCARD-INVESTIGATION.md` to separate the documented UNO close-listener contract from the still-unverified interactive Writer Save / Don't Save / Cancel prompt ordering.
- Guardrail: `queryClosing` snapshot creation plus `notifyClosed` is not proof that the user chose Save or Don't Save. Do not infer `DISCARDED` from close/disposal callbacks.
- Required visible-Writer acceptance cases are now explicit: Save must return the edited marker; Don't Save must omit the unsaved marker; Cancel must leave Writer open and the Almas request pending. Capture callback order and returned bytes.
- Latest PR head at this checkpoint: `79c017e757485dbd5fb19b7a7e1fd13beb05353c`.
- CI for that head:
  - Python bridge run `44784556864`: completed successfully.
  - LibreOffice UNO run `44784556817`: completed successfully; the job log reports **17 tests passed**, including the real UNO roundtrip through the EditWord response handler and Word 97 export.
  - Native run `44784556764`: Debian package lifecycle and normal build/CTest/staged install jobs passed; ASan/UBSan job was still running at this checkpoint.
- The native package lifecycle remains limited to `emwat-native-core-dev`; it is not a complete EMWAT desktop installer.
- These CI results do not prove interactive Save / Don't Save / Cancel behavior, live Almas/browser compatibility, full semantic Word/Writer field parity, physical scanner support, or Windows `.easz` interoperability.
- PR #2 remains open, Draft, and unmerged. No release-readiness claim is made.


## Word/Writer runtime mapping boundary — 2026-11-20

- Source review confirmed that the current `EditWordDocumentService` parses and retains `wordConfig`, then passes the request to the coordinator; `LibreOfficeAdapter.open_document()` opens the Word payload but explicitly does not apply the config fields.
- `decode_word_fields()`, native-shaped descriptor construction, Writer metadata inspection, and exact custom-property updates exist as separate building blocks. They are not yet composed into an automatic request-to-Writer mapping step.
- Consequently, current real UNO CI validates open/close/export and the synthetic response path, not complete population of Almas-provided fields, signatures, or `signData`.
- Updated `docs/WORD-WRITER-MAPPING-AUDIT.md` with the exact runtime boundary and safe fixture gate.
- Release blocker: obtain one sanitized matching Word document + `wordConfig` fixture and expected field results; verify property enumeration, twin-field associations, image/signature handling and output roundtrip before enabling automatic writes. Do not infer order or `signData` encoding.


## Read-only Word/Writer evidence audit and visible close matrix — 2026-11-20

- Added `word_writer_evidence.py` with a metadata-only report of WordConfig field IDs, MIME/encoding declarations, external parameter IDs, duplicate IDs, settings/optional attributes/requested types, and Writer structural/property names.
- Added `LibreOfficeAdapter.audit_word_writer_evidence(handle, config)` as a lock-protected, read-only entry point. It does not read field values or body text and does not mutate Writer.
- Added regression tests for sensitive-value exclusion, duplicate IDs, image/text metadata, external parameter metadata, empty inputs, and adapter integration.
- Added `docs/WORD-WRITER-EVIDENCE-REPORT.md` and `docs/WRITER-VISIBLE-CLOSE-ACCEPTANCE.md`.
- Python CI run `44796731919` passed **219 tests, 217 passed, 2 optional skips** for the initial evidence-report commit. The subsequent adapter integration/test commit `4c571a74` has fresh Python, Native, and UNO workflows queued; do not mark those newer tests verified until their runs finish.
- The previous current-head UNO run `44796732049` and Native run `44796731888` completed successfully, but they predate the adapter entry-point follow-up.
- The evidence report is diagnostic only. It does not establish Word/Writer field equivalence or enable automatic writes. Visible Save / Don't Save / Cancel behavior remains unverified.

## Follow-up verification — adapter evidence audit integration

- Added `LibreOfficeAdapter.audit_word_writer_evidence()`, protected by the document snapshot lock and requiring a parsed `WordDocumentConfig`.
- Python bridge run `44796996459` for code/test commit `4c571a74be9c75ad6fa0b7b823bcd6a3e8d88f28` passed **220 tests, 218 passed, 2 optional skips**.
- LibreOffice UNO run `44796996426` on the same code/test commit passed **18 tests**, including the new adapter audit regression and the real Writer roundtrip.
- The separate docs-triggered UNO run `44797006712` also passed.
- Native build/CTest and staged install passed in run `44796996414`; its Debian package lifecycle and ASan/UBSan jobs were still running at this checkpoint.
- An earlier intermediate push had failed Python/UNO CI before the adapter test imports were corrected. The corrected code/test head above is green for Python and UNO; do not conflate the intermediate failures with the corrected head.


## Full CI verification for read-only evidence audit — 2026-11-20

- Code/test head `4c571a74be9c75ad6fa0b7b823bcd6a3e8d88f28` passed all three workflows:
  - Python Bridge run `44796996459`: **220 tests, 218 passed, 2 optional skips**.
  - LibreOffice UNO run `44796996426`: **18 tests passed**, including adapter evidence audit and real Writer roundtrip.
  - Native run `44796996414`: build/CTest, staged install, Debian package lifecycle, and ASan/UBSan all passed; normal and sanitizer CTest each report **4/4 tests passed**.
- Documentation-only follow-up UNO run `44797006712` passed.
- Later commits `315cb5d`, `c327662`, and `bb1d920` update documentation only; the verified code/test tree is unchanged.
- PR #2 remains open, Draft, unmerged. This verification does not establish Almas end-to-end compatibility, automatic WordConfig mapping, visible Save/Don't Save/Cancel behavior, full application packaging, or physical scanner support.


## Expanded Word/Writer evidence and close-retry coverage — 2026-11-20

- Expanded the metadata-only evidence report to include WordConfig root/permission attribute names, field indices, declared twin-delimiter members, duplicate/case-fold collision groups, duplicate setting names, optional-attribute type/encoding and content-element presence, requested-type metadata, and Writer custom-property case-fold collisions.
- The report continues to exclude all field/settings/optional-attribute values, document text, image bytes, and custom-property values. Twin syntax is parsed, but no twin-to-Writer association or automatic mapping is inferred.
- Updated `OptionalAttribute` parsing to preserve whether a `<content>` element exists independently of whether it contains text. This distinguishes absent content from an explicitly empty content element; the new field has a default for compatibility with direct constructors.
- Added tests for duplicate and case-fold collisions, empty versus missing optional content, missing optional IDs, declared twin syntax, invalid input types, and sensitive-value exclusion.
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
