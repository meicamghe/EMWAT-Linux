# Ubuntu installation and integration workstreams

Status: implementation scaffolding; not a release-ready installer. Product target and UI toolkit are decided: Linux-only, GTK 4 + PyGObject, LibreOffice Writer via UNO.
Date: 2026-11-18

This document separates the components that can already be installed/tested from
the runtime contracts and product decisions that still block a supported desktop
release. It intentionally does not claim Almas Gam compatibility, physical
scanner support, Windows `.easz` compatibility, or a finished GUI.

## 1. Native library installation

The native CMake project now installs the reusable image/scanner library and
public C++ headers. It does not install a daemon, GUI, or desktop launcher.

Build dependencies on Ubuntu:

```sh
sudo apt update
sudo apt install --no-install-recommends \
  build-essential cmake pkg-config \
  libpng-dev libjpeg-dev libtiff-dev libsane-dev
```

Build, test, and stage-install:

```sh
cmake -S native -B build/native -DCMAKE_BUILD_TYPE=Release
cmake --build build/native --parallel
ctest --test-dir build/native --output-on-failure
sudo cmake --install build/native --prefix /usr/local
```

For package staging rather than modifying the host:

```sh
DESTDIR="$PWD/package-root" cmake --install build/native --prefix /usr
```

The native install rules are intentionally library/header-only until a stable
application entrypoint and dependency/export policy exist.

A Debian development package can now be generated from the same CMake build:

```sh
cmake -S native -B build/native -DCMAKE_BUILD_TYPE=Release
cmake --build build/native --parallel
cpack --config build/native/CPackConfig.cmake
```

This produces `emwat-native-core-dev` for the host architecture, with the
static library and public headers under `/usr`. Its declared build-time
dependencies are `libpng-dev`, `libjpeg-dev`, `libtiff-dev`, and `libsane-dev`.
It is a development package only: it does not install the Python bridge, a
service/daemon, desktop launcher, GUI, or Almas integration. The CI lifecycle
job installs version 0.1.0, upgrades to 0.1.1, verifies the installed files,
then removes the package and verifies those files are gone. This validates
dpkg mechanics for this library package, not a complete end-user application
upgrade or data-migration policy.

## 2. Python bridge and LibreOffice runtime

The Python project metadata is under `python/pyproject.toml`. Install the
bridge package in a dedicated environment:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install ./python
```

LibreOffice and the distro-provided UNO bindings must be installed from the
Ubuntu package manager and made visible to the Python interpreter that runs
the bridge. The exact `python3-uno` import path varies by distro Python build;
do not assume a pip wheel is interchangeable with the system UNO runtime.

No production daemon command is declared yet: startup still requires explicit
Almas Origin allowlists, a verified Cancel/Discard response policy, and an
application lifecycle supervisor. Do not expose the bridge on a non-loopback
interface.

## 3. End-to-end acceptance boundary

The automated application composition test now verifies the full synthetic
path:

1. HTTP POST to the loopback bridge with an EMWAT 1.0 envelope.
2. XML method dispatch to `EditWordDocument`.
3. Base64 request normalization.
4. Office adapter receives the exact source bytes.
5. Close returns synthetic final Word bytes.
6. Browser-facing `response-word` XML contains Base64 bytes that decode
   byte-for-byte to the final Office output.

This is a mocked Office adapter integration test, not a live Almas Gam or
real LibreOffice UI session. Runtime acceptance still needs a sanitized,
complete editable-letter request/response capture and a controlled test account.
Never commit HAR files, cookies, authorization headers, letter text, or signature
images from a real user session.

## 4. Word fields and signData

The current implementation:
- preserves XML field order and per-field metadata;
- decodes only declared `urlencoded` and `base64` field encodings;
- recognizes the seven captured indexed signer families;
- builds Word custom-property single/twin descriptors using the observed
  dagger delimiter and ordered XML field association;
- audits Writer property names without assuming enumeration order is equivalent;
- preserves `signData` as opaque text and exposes external parameter bindings.

The current parser deliberately does not split or concatenate `signData`.
The observed `separator`, `concator`, and `concater` attributes are not enough
to prove the exact native byte/string transformation or its interaction with
each field's encoding. The next acceptance fixture must include synthetic values
with delimiter collisions, empty values, non-ASCII text, and image bytes, plus
the exact expected Word-side field result. Until then no heuristic concatenation
is permitted.

## 5. Recovery UI boundary

`RecoverySnapshotService` and `RecoveryPickerController` already provide:
- newest-first validated metadata without exposing private store paths;
- restore to a caller-selected destination without overwriting;
- explicit confirmation before discard;
- optional retention policy operations;
- an immutable `RecoveryPickerState` projection for native UI clients, including an explicit empty-catalog state, selected-entry metadata, default selection of the newest snapshot, and safe clearing of stale selections.

`RecoveryPickerController.state()` performs no filesystem writes. A UI can refresh this projection after each action and bind it to GTK, Qt, or another toolkit later. This is a toolkit-neutral controller, not a graphical picker. The detailed toolkit-neutral interaction and accessibility contract is in
[RECOVERY-PICKER-UX.md](RECOVERY-PICKER-UX.md). A future view must display
metadata only, use a native Save dialog for restore, require a destructive
confirmation for discard, and show errors without exposing private paths or
document contents. **GTK 4 + PyGObject is the accepted toolkit.** Implement the picker as a thin GTK view over this controller. Do not add Qt/PySide or move filesystem/business logic into GTK callbacks. Keep GTK optional so headless services and protocol tests run without a display server.

## 6. Windows .easz compatibility

Static analysis indicates a password-protected 7z output with an `.easd` entry,
but no authorized synthetic fixture has been captured. The Linux recovery store
is a separate format and must remain usable independently.

Required fixture evidence before implementing an adapter:
- synthetic DOC/DOCX input and known test password;
- archive header and encryption metadata;
- exact entry name and extracted bytes;
- wrong-password and corrupt-header behavior;
- password lifecycle evidence, not merely a guessed string from a static field.

Until this exists, the Ubuntu package must not advertise .easz import/export.

## 7. Scanner compatibility

The native SANE backend currently supports device discovery, capability
inspection, and a single 8-bit Gray/RGB frame. It validates option types,
resolution representation, frame dimensions/stride, and a 1 GiB frame cap.
Native fake/contract tests do not prove a physical scanner works.

Before release, test at least one USB flatbed and one network scanner where
available, then separately verify:
- source selection and supported resolution/mode options;
- ADF and multi-page acquisition;
- cancellation and unplug/device-loss behavior;
- page order, partial scans, and output encoding;
- preview/edit/export handoff.

Do not map undocumented ImageGear integer modes to SANE options by guesswork.

## 8. Product UI and cost boundary

The accepted product decision is Linux-only with a lightweight GTK 4 + Python/PyGObject control interface. LibreOffice Writer remains the document editor through UNO; GTK is not a document editor. Prefer distribution-provided free/open-source packages and do not introduce paid toolkit or cloud dependencies. The GUI must remain a thin optional layer over the existing service/controller APIs. See [LINUX-PRODUCT-DECISIONS.md](LINUX-PRODUCT-DECISIONS.md) for the binding decision.

## 9. Release blockers

A supported Ubuntu desktop release requires all of the following:
- a production bridge entrypoint and supervised user-session lifecycle;
- real Almas Origin and complete editable-letter fixtures;
- verified Cancel/Discard wire envelopes;
- real LibreOffice UNO close/save/cancel behavior on supported Ubuntu versions;
- selected native GUI toolkit and recovery picker implementation;
- tested package install/upgrade/remove and desktop integration;
- synthetic .easz interoperability fixture if that compatibility is advertised;
- physical scanner validation for every advertised acquisition mode.

