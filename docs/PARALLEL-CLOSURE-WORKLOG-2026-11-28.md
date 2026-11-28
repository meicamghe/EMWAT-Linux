# Parallel Closure Work Log — 2026-11-28

## Scope and safety

This work log is based on a read-only inspection of the repository at:

- Branch: `feature/recovery-retention-policy`
- Inspected HEAD: `00bb6a3387dddc7b25d331f879ad5c60db846fa8`
- Working branch: `work/parallel-closure-2026-11-28`

No local hardware, Almas installation, Windows EMWAT executable, or LibreOffice desktop session was available to this GitHub-only inspection. No runtime, hardware, or end-to-end acceptance result is claimed here. Unknown wire fields and response envelopes must not be guessed.

## Parallel workstreams and verified boundaries

### 1. Almas HTTP bridge and desktop lifecycle

Relevant implementation:
- `python/src/emwat_linux/application.py`
- `python/src/emwat_linux/application_runtime.py`
- `python/src/emwat_linux/bridge_supervisor.py`
- `python/src/emwat_linux/gtk_desktop.py`
- `python/src/emwat_linux/editword_service.py`

Verified:
- A supervised, restartable bridge lifecycle exists.
- The runtime uses a non-daemon serving thread, waits for serving readiness, drains active request workers with a bounded timeout, and permits cleanup retry after a drain timeout.
- GTK already supports an injected supervisor, background start/stop operations, state polling, and stop-before-window-close.
- The initial feature branch left the ordinary `main()` entry point without a supervisor. This work branch now adds `deployment.py`, using the captured loopback bind/Origin/Referer values and a fresh server factory per start.
- The normal GTK entry point now injects that supervisor and requests auto-start after required dependency checks pass. The existing manual Stop control, state polling, and bounded shutdown flow remain in place.
- Explicit operation-level discard is mapped to a local HTTP 409/plain-text response only when the session state is exactly `DISCARDED`. This is a fail-closed local policy, not Windows wire parity. Writer Don't Save and close-prompt Cancel remain distinct.
- New composition tests cover the exact loopback values, request/response limits, and discard guard. They have not yet been executed.

Remaining closure criteria:
- Execute Python and GTK test suites on this exact branch.
- Verify port-conflict and missing-dependency behavior on a target desktop.
- Complete a real Almas request → Writer → user decision → HTTP response → Almas acceptance test.

Do not enable wildcard Origin policy or represent the local 409 as the native Windows discard envelope.

### 2. Writer lifecycle, document mapping, and recovery

Relevant implementation:
- `python/src/emwat_linux/editword_handler.py`
- `python/src/emwat_linux/editword_request.py`
- `python/src/emwat_linux/editword_service.py`
- `python/src/emwat_linux/libreoffice_adapter.py`
- `python/src/emwat_linux/word_config.py`
- `python/src/emwat_linux/word_config_updates.py`
- `python/src/emwat_linux/word_fields.py`
- `python/src/emwat_linux/image_mapping.py`
- `python/src/emwat_linux/word_assets.py`
- `python/src/emwat_linux/recovery_*.py`

Verified:
- The EditWordDocument service and LibreOffice adapter are implemented as separate layers.
- Word configuration, field, image, asset, recovery, retention, and key-provider modules exist.
- Prior manual acceptance evidence (2026-11-23) reported Save retaining the new marker, Discard retaining only the baseline, and Cancel leaving Writer open with the original output unchanged.

Closure criteria:
- Turn the reverse-engineered WordConfig and XML field evidence into a field-by-field mapping table with confidence and source evidence.
- Keep unknown fields explicitly unsupported rather than silently dropping or inventing values.
- Add fixtures for images, signatures, recipients, custom properties, and document metadata.
- Re-run the Save / Discard / Cancel acceptance script against the current branch and compare output bytes and document semantics.
- Verify recovery retention and encryption on the actual deployed desktop environment.

### 3. XMLRTL and native protocol evidence

Relevant implementation:
- `python/src/emwat_linux/protocol.py`
- `python/src/emwat_linux/editword_request.py`
- `python/src/emwat_linux/field_mapping_audit.py`
- `python/src/emwat_linux/emwat_field_catalog.py`
- `python/src/emwat_linux/word_writer_evidence.py`

Verified:
- XML/protocol parsing and field catalog/audit modules exist.
- This source tree does not, by itself, prove complete semantic parity with Delphi XMLRTL.
- A Python parser passing its own tests is not proof that all Delphi interface ownership, variant conversion, encoding, whitespace, and serialization semantics are reproduced.

Closure criteria:
- Maintain a crosswalk for each observed XMLRTL class/helper: Delphi symbol, call site, input/output type, ownership/lifetime, Python counterpart, fixture, and confidence.
- Capture round-trip fixtures from the Windows implementation for representative request and response payloads.
- Test encoding, namespaces, empty/null values, repeated nodes, numeric/boolean conversions, and malformed payload behavior.
- Do not mark XMLRTL parity complete until byte-level or explicitly justified semantic comparisons pass.

### 4. GDI+, TIFF, print worker, and GAM printer

Relevant implementation:
- `native/src/image_document_io.cpp`
- `native/src/image_document.cpp`
- `native/src/image_codec.cpp`
- `native/include/emwat/image_document_io.hpp`
- `native/tests/test_image_document_io.cpp`
- Reverse-engineering workflows under `.github/workflows/emwat-gdiplus-*.yml`, `.github/workflows/emwat-tiff-*.yml`, and `.github/workflows/emwat-print-*.yml`.

Verified:
- The Linux native image core and codec/test surface exist.
- Reverse-engineering workflows cover GDI+ VMT, Save/SaveAdd, TIFF output, Winspool, and print-queue analysis.
- The production native source tree inspected here does not contain a completed GAM/Winspool-compatible printer backend.
- The source tree and workflow names are not proof that a real multi-page TIFF has been accepted against Windows output or that a print job completes through CUPS.

Closure criteria:
- Build a symbol/slot/call-site table for GDI+ Save and SaveAdd, including exact argument types and encoder parameter ownership.
- Add deterministic multi-page TIFF fixtures and verify page count, dimensions, pixel format, compression, metadata, and final stream closure.
- Correlate one real Windows print job from queue insertion through worker wait, TIFF creation, queue completion, and final file delivery.
- Implement a printer adapter only after the job lifecycle and output contract are established.
- Validate through a real CUPS queue and compare resulting TIFF/document output to the Windows reference.

### 5. Scanner, GTK recovery UI, and packaging

Relevant implementation:
- `native/src/sane_scanner.cpp`
- `native/include/emwat/scanner.hpp`
- `native/tests/test_scanner.cpp`
- `python/src/emwat_linux/gtk_desktop.py`
- `python/src/emwat_linux/gtk_recovery_view.py`
- `.github/workflows/gtk-desktop.yml`
- `.github/workflows/application-package.yml`

Verified:
- SANE discovery, capability inspection, bounded scan reads, grayscale/RGB and planar RGB handling, and bounded simplex ADF page collection exist.
- Duplex ADF batch scanning is explicitly rejected with `duplex_adf_batch_not_supported`; it must not be advertised as implemented.
- GTK recovery and diagnostics controls exist.
- Packaging workflows exist, but their presence alone does not prove installation and upgrade on a clean target workstation.

Closure criteria:
- Add device-independent tests for option negotiation and feeder error recovery.
- Test flatbed, simplex ADF, and duplex ADF separately; implement duplex only after confirming the target device's SANE option model and page ordering.
- Verify GTK flows on a real display session, including recovery selection and service lifecycle.
- Validate package install, upgrade, removal, desktop entry, permissions, and user-data retention on a clean Ubuntu installation.

## Cross-cutting release gates

1. Python unit suite passes on the exact release commit.
2. Native CTest and ASan/UBSan suites pass on the exact release commit.
3. GTK tests pass with the supported desktop dependencies.
4. Writer Save / Discard / Cancel acceptance passes on the exact release commit.
5. Live Almas round-trip is accepted by Almas itself.
6. TIFF and printer acceptance use real generated output and a real queue.
7. Scanner acceptance distinguishes flatbed, simplex ADF, and duplex ADF.
8. Package install/upgrade/remove is validated on a clean supported Linux installation.
9. Every unsupported Windows behavior is listed explicitly; no silent success or inferred compatibility.

## Execution rule

Workstreams may proceed independently, but changes that affect shared protocol contracts must be integrated only after their evidence and tests are available. Keep changes isolated, avoid merging the long-lived feature branch into `main` until its nine-commit divergence is reconciled, and never report a workflow or hardware path as passed without an observed result.
