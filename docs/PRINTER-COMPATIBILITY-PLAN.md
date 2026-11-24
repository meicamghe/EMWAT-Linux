# EMWAT printer compatibility — evidence and implementation plan

Date: 2026-11-24
Branch at analysis: `feature/recovery-retention-policy`

## Evidence currently available

The following observations were supplied by the project owner and are treated as high-value reverse-engineering leads, not as independently revalidated binary conclusions in this commit:

1. `EmwatMethods.bpl` contains printer-management methods named `GetPrinterIndex` and `SetPrinterIndex`.
2. `EmwatAgent.exe` calls Windows Spooler APIs including `OpenPrinterW`, `EnumPrintersW`, and `GetPrinterW`.
3. `GAMPrinterSetup.exe` is an InstallShield installer package.

The repository currently contains `analysis-input/EmwatMethods.bpl1` and generated string inventories for `EmwatMethods.bpl1` and `EmwatAgent.exe`. The relationship between the owner's `.bpl` filename and the repository's `.bpl1` artifact (same binary, renamed copy, or different build) must be verified by file hash and PE metadata before address-level traces are combined. String inventories alone do not establish callsites or runtime semantics.

## Newly recovered GAM Virtual Printer package evidence (2026-11-24)

Detailed payload, INI, rendering, and uncertainty inventory: [GAM Virtual Printer reverse-engineering evidence](GAM-VIRTUAL-PRINTER-REVERSE-ENGINEERING.md). The extracted package confirms a GAMPrinter queue configured over a Zan Image Printer-derived OEM graphics-driver/port-monitor stack. It also exposes color/BW/Fax profiles, filename templating and optional FTP/email/event features. Numeric format/compression/collision enums and the exact EMWAT output hand-off remain unresolved; do not select a Linux output format from the current enum values.

## What the Windows API evidence means

- `EnumPrintersW` is a discovery/enumeration boundary. Its flags, name/server filters, returned level, and buffer handling determine which printers are visible to EMWAT.
- `OpenPrinterW` opens a handle for a printer or print server. It is not itself a print-job submission operation.
- `GetPrinterW` reads printer metadata through an opened handle. The requested information level (for example, `PRINTER_INFO_2`) and the exact fields consumed by the caller must be recovered before defining the compatibility DTO.
- The existence of these imports does not prove that EMWAT submits jobs through this same code path. Actual submission APIs and their callers must be traced separately.
- `GetPrinterIndex` / `SetPrinterIndex` names suggest index-based selection, but do not prove whether the index is zero- or one-based, whether it indexes a filtered list, which list flags/order are used, or whether the selected index is persisted.

## Linux design boundary

Implement the printer subsystem as four independent operations:

1. **Discovery:** enumerate CUPS/IPP-visible destinations and expose stable destination identifiers, display names, descriptions, and availability where supported.
2. **Metadata:** retrieve destination attributes separately from enumeration. Missing CUPS/IPP attributes must remain explicitly unknown rather than being fabricated from a display name.
3. **Selection:** persist a stable destination identity, not a numeric list index. Provide a compatibility adapter that resolves a legacy index only against the exact ordered snapshot supplied by the corresponding request; reject stale/out-of-range indices.
4. **Submission:** submit a print job through the selected destination only after the original EMWAT print path, document format, options, and response semantics have been identified. Discovery and selection must not implicitly print.

A future backend contract should expose typed operations such as `list_destinations()`, `get_destination(destination_id)`, `get_default_destination()`, `set_default_destination(destination_id)`, and `submit_job(destination_id, document, options)`. The API names are a Linux-side design proposal, not recovered Windows ABI.

### Index compatibility rules

- Never store a numeric index as the durable selected-printer setting.
- Capture one ordered enumeration snapshot per legacy request and bind its generation/token to any index-based follow-up.
- Translate the legacy index to a stable destination ID only within that snapshot.
- Reject an index when the snapshot is absent, stale, ambiguous, or out of range; do not silently fall back to the system default.
- Keep the EMWAT-selected destination distinct from the operating-system default printer until traces prove they are the same setting.

## InstallShield investigation

Treat `GAMPrinterSetup.exe` as a separate installation/reconfiguration workflow. Before implementing an equivalent, extract and inspect its InstallShield metadata and payload inventory, identify custom actions/scripts, driver package names and architectures, registry writes, service dependencies, and whether it installs a vendor driver or merely configures a queue. Do not execute the installer as part of static analysis and do not copy Windows driver binaries into the Linux package. Linux support should use an appropriate CUPS/IPP driverless path or a separately licensed/redistributable vendor Linux driver when evidence supports it.

## Required reverse-engineering work

1. Verify SHA-256, PE timestamp, image size, architecture, and version/resource metadata for the exact `EmwatMethods.bpl`, `EmwatAgent.exe`, and `GAMPrinterSetup.exe` builds. Compare the BPL against the repository's `EmwatMethods.bpl1` artifact.
2. Resolve the BPL methods through TD32/RTTI and trace every caller/callee of `GetPrinterIndex` and `SetPrinterIndex`; recover argument/return types, index base, enumeration source, ordering, persistence location, and error behavior.
3. Inspect the Agent import table and callsites for `EnumPrintersW`, `OpenPrinterW`, and `GetPrinterW`; record enumeration flags, information levels, fields read, handle lifetime, and all relevant error codes.
4. Trace actual print submission separately (for example, spooler job/document APIs or a vendor-specific transport); do not infer it from metadata calls.
5. Inspect InstallShield tables/scripts and custom actions for queue creation, driver installation, port configuration, registry changes, and service dependencies.
6. Build sanitized fixtures with at least: no printers, one printer, multiple printers, reordered enumeration, removed destination, offline destination, access denied, and invalid/stale legacy index.

## Acceptance tests for the Linux implementation

- Discovery returns stable unique IDs and tolerates an empty CUPS destination list.
- A changed enumeration order does not change the persisted selected destination.
- Legacy index translation is deterministic within one snapshot and rejects stale/out-of-range references.
- An unavailable selected destination is reported explicitly; it does not silently switch to another printer.
- Metadata failures do not invalidate unrelated destinations or leak native handles.
- Print submission is not triggered by discovery, metadata lookup, or selection changes.
- Submission preserves document bytes and supported options, reports the CUPS/IPP job identifier, and surfaces failure/cancellation distinctly.
- Unit tests use a fake backend; integration tests use a controlled CUPS test destination. Physical printer acceptance remains a separate gate.

## Current implementation status

No Linux printer backend, legacy index adapter, persistent printer selection, or print-job submission path is present in the inspected Python/native source tree at this analysis point. The existing SANE scanner subsystem is unrelated and must not be reused as a printer abstraction. No claim of printer compatibility or installer equivalence is made.
