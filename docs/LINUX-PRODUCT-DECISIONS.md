# Linux product scope and architecture decisions

Status: **accepted project decisions**
Date: 2026-11-18
Decision owner: project owner

This document is the authoritative record of the product and architecture decisions
confirmed for EMWAT-Linux. If an older planning document conflicts with this
record, update the older document; do not silently reverse these decisions.

## 1. Product purpose

EMWAT-Linux is a native Linux implementation of the existing EMWAT integration
used by the Almas Gam administrative correspondence system. It is **not** a
replacement for Almas, a new correspondence-management product, or a Linux
version of Microsoft Word.

The concrete user workflow is:

1. The Almas correspondence system initiates its existing document-editing
   workflow and sends the document/configuration to the local EMWAT integration.
2. EMWAT receives and validates the request using the observed Almas/EMWAT
   protocol.
3. EMWAT opens or hands the document to **LibreOffice Writer** on Linux and
   applies the required document-field/signature integration.
4. The user performs the requested editing in Writer.
5. EMWAT obtains the final document and returns it to Almas in the exact
   response format required by the compatible protocol.
6. Almas continues its normal correspondence workflow.

The Windows EMWAT implementation is an analysis and compatibility reference.
The project owner explicitly does **not** want another Windows implementation:
the target deliverable is Linux only.

## 2. Supported platform scope

- Primary target: Linux desktop, with Ubuntu as the first installation and
  acceptance target.
- Do not create a Windows GUI/application target or spend implementation effort
  on Windows packaging.
- Windows binaries and runtime behavior may be inspected only as evidence for
  reproducing the existing protocol and document behavior.
- Keep distro-specific assumptions isolated so other Linux distributions can
  be considered later without changing the product's primary target.

## 3. GUI toolkit decision

**GTK 4 is selected** for the small native Linux control interface.

Implementation direction:
- Python application code with PyGObject bindings.
- GTK 4 widgets for the local control/settings/recovery interface.
- Use distro-provided GTK/PyGObject packages where practical.
- Do not introduce Qt, PySide, Qt Designer, or commercial Qt licensing into
  this project unless the project owner explicitly reopens this decision.

The GTK interface is not the document editor. **LibreOffice Writer is the
document-editing UI.** GTK is only for EMWAT functions that need a local
application surface, such as status, configuration, recovery selection,
scanner selection/preview entry points, and diagnostics.

Keep the protocol bridge, document coordinator, LibreOffice UNO adapter,
recovery services, and scanner core independent of GTK. The headless service
and automated tests must remain usable without importing GTK. GTK is an
optional presentation layer, not a dependency of the protocol or document
business logic.

## 4. Cost and licensing requirements

The project must remain usable without paid software licenses or subscription
services.

- Prefer free/open-source software and packages available from Linux
  distribution repositories.
- GTK 4 and PyGObject are selected as the free/open-source GUI stack.
- LibreOffice is the free/open-source office suite used for Writer editing.
- Python and the existing native toolchain remain the implementation base.
- Do not add commercial Qt dependencies, proprietary runtime services, paid
  cloud APIs, or mandatory paid components.
- Before release, record the licenses of bundled/distributed dependencies and
  comply with their notices and redistribution requirements.

"Free" here means no purchase or subscription is required for the chosen
software stack. It does not waive third-party license obligations or guarantee
that every optional codec, driver, font, or system component has identical terms.

## 5. Architecture boundary

The intended runtime responsibilities are:

- **Almas protocol/HTTP bridge:** local loopback communication, request
  validation, dispatch, response serialization, and strict origin/security
  policy.
- **Document workflow coordinator:** document lifecycle, state transitions,
  cancellation/finalization boundaries, and safe handoff.
- **LibreOffice adapter:** UNO connection, Writer document opening/editing,
  field/property integration, save/close behavior, and final byte retrieval.
- **Recovery service:** local snapshots, catalog, restore/discard, optional
  encryption and explicit retention policy.
- **Scanner/image subsystem:** SANE and native image processing for workflows
  that require scanned or image-based correspondence.
- **GTK 4 UI:** small Linux control surface only; it calls service/controller
  APIs and must not implement protocol or document business rules itself.

The central success criterion is faithful Almas ↔ EMWAT ↔ LibreOffice Writer
document exchange, not the number or visual complexity of GTK screens.

## 6. Priorities

Work in this order unless new evidence changes the dependency order:

1. Establish the real Almas request/response and browser-to-local-bridge
   contracts from captured, sanitized evidence.
2. Complete the text-document EditWordDocument workflow through LibreOffice
   Writer and return the final document to Almas.
3. Verify Word-to-Writer field mapping, signatures, images, formatting, and
   document fidelity using controlled fixtures.
4. Complete the Linux application lifecycle: startup, monitoring, error
   handling, recovery, and safe shutdown.
5. Build the minimal GTK 4 control interface over existing service/controller
   APIs.
6. Provide a free Linux installation package and test install/upgrade/remove.
7. Validate scanner, multi-page, and image-based correspondence workflows.
8. Implement Windows .easz interoperability only after a valid authorized
   fixture and format evidence are available.

This ordering does not remove scanner/recovery work already implemented; it
prevents those supporting features from displacing the core Almas/Writer
integration.

## 7. Explicit non-goals and evidence boundaries

- No Windows product/GUI/installer target.
- No Microsoft Word dependency on Linux.
- No attempt to recreate the full Almas correspondence application.
- No paid toolkit or mandatory paid service.
- No claim of live Almas compatibility based solely on synthetic loopback tests.
- No guessed Cancel/Discard response envelope, signData encoding, or archive
  encryption behavior.
- No claim that the current native-core .deb is a complete EMWAT installer.

## 8. Change control

Reopen these decisions only when the project owner explicitly requests a
change. Any accepted change must update this file, README, project status,
installation guide, and session handoff together so future development sessions
do not revive superseded alternatives.
