# GAM Virtual Printer — reverse-engineering evidence

Date: 2026-11-24  
Repository branch: `feature/recovery-retention-policy`  
Evidence source: owner-supplied static-analysis output from the extracted `GAMPrinterSetup.exe` payload on Ubuntu. This document records observed strings, INI values and PE imports; it does not claim runtime validation of the Windows installer or a working Linux printer backend.

## Executive summary

The GAM package is a customized deployment of a Zan Image Printer virtual-printer stack. The configured primary queue is named `GAMPrinter`. The payload contains a Windows OEM printer graphics driver, OEM configuration UI, local port monitor/UI extension, and a user-mode rendering/server executable. The current evidence supports a file/image-generation workflow rather than a conventional physical-printer driver path.

Do not treat this as proof that EMWAT consumes a particular generated file or that the Linux implementation should reproduce the entire vendor UI. The original EMWAT print submission callsite and its hand-off contract remain to be traced.

## Installer and component evidence

- `GAMPrinterSetup.exe` is a PE32 x86 InstallShield self-extracting package.
- Recorded SHA-256: `cdec0363d420d8b1e7109e2a5624e0ed834a82b43b437c8d1c85a3c6303a6d15`.
- Recorded size: 4,008,872 bytes.
- 7-Zip inspection exposed an internal CAB at offset 249344, physical size 3,759,528 bytes, LZX:21, one volume, 49 files, approximately 15,060,720 extracted bytes.
- The extracted payload contains x86/x64 variants of `zvprtsrv`, `zvprt5_setup`, `zvprtcfg`, `zvprtmon5`, `zvprtmonui5`, `zvprtui5`, `zvprtuni5`, and uninstallers.
- `zvprt5.ini` maps `OEMConfigFile1=zvprtui5.dll` and `OEMDriverFile1=zvprtuni5.dll`. PE exports and internal names are consistent with an OEM UI COM server (`OEMUI.dll`) and OEM driver COM server (`OEMUNI.dll`).
- `zvprtmon5` exposes/contains local print-monitor entry points such as `InitializePrintMonitor2`, `LcmOpenPort`, `LcmStartDocPort`, `LcmWritePort`, and `LcmEndDocPort`; `zvprtmonui5` contains `InitializePrintMonitorUI`.
- `zvprtsrv_x86.exe` imports GDI document/page operations, spooler metadata APIs, OLE/COM and WinINet FTP APIs. It contains image codecs/handlers for BMP, JPEG, PDF, PNG and TIFF and strings for a private `.zan` extension. The role of `.zan` is not yet known.
- PE timestamps cluster around 2011-11-05; this is a build-time clue, not a verified product release date.
- The GUID string `{ADB880A6-D8FF-11CF-9377-00AA003B7A11}` appeared in installer/configuration executables but has not been tied to the OEM UI class. Do not identify it as the driver CLSID.

## Queue defaults from `setup.ini`

The active configured queue is:

| Property | Observed value |
|---|---|
| Product label | GAM Virtual Printer |
| Queue name | `GAMPrinter` |
| Install | `1` |
| Default DPI | `200x200` |
| Default paper | `A4` |
| Default color | `color` |
| All users | `1` |
| Autostart | `0` |

The BW queue (`Zan Image Printer (BW)`) and Fax queue (`Zan Image Printer (Fax)`) have `install=0` in this setup. The setup file also contains other queue-specific defaults; the values above are the relevant active GAM queue settings observed in the supplied output.

## Save and output configuration

Observed `save.ini`:

```ini
[save]
folder=x
basefilename=[%DocName]
filenameindex=1
filexistact=2
popupdialog=2
```

- The base filename template is `[%DocName]`.
- `folder=x` is a literal observed value; its path-resolution meaning is not established.
- `filenameindex=1`, `filexistact=2`, and `popupdialog=2` are numeric settings whose enum meanings remain unresolved.
- Binary strings include “Always overwrite”, “Append to existing file”, “overwrite”, “append”, and rename-related messages. This proves that multiple collision strategies exist, not which numeric value selects each strategy.

The color profile observed in `image_color.ini`:

```ini
[image]
fileformat=1
imagecolor=1
compression=6
pagetype=0
rowsperstrip=1
qfactor=75
color2bwthreshold=200
```

The BW profile (`image_bw.ini`) has `fileformat=1`, `imagecolor=0`, `compression=2`, `rowsperstrip=0`, `qfactor=75`, and threshold 200. The Fax profile (`image_fax.ini`) has the same base format/color/compression values as BW, but `rowsperstrip=1`, `pagenumber=1`, `adjustwidth=1`, and `adjustheight=1`. All three observed profiles use `fileformat=1`; the numeric file-format enum is not yet decoded. TIFF-FAX/T.4 configuration strings and structures exist, but are not sufficient to assert that enum value 1 is TIFF.

Additional observed image settings:
- `[tiff-fax]`: `datetime=1`, `fillorder=2`, `t4options=4`, `lineheight=2200`, `ifdfirst=0`; Fax profile additionally sets page numbering and width/height adjustment.
- `orientation.ini`: landscape auto-rotation enabled, angle 90 degrees.
- `advimage.ini`: trim, scale, crop, invert, transpose, rotate and flip all disabled in the captured defaults (rotate angle field is 90).
- `watermark.ini`: global watermark disabled and all listed watermark slots disabled.
- `text.ini`: text output disabled; BOM enabled and encoding value 3 are present but inactive until text output is enabled.

## Encoding and ancillary features

The following extracted INI files are UTF-16 little-endian with CRLF line endings. They must be decoded accordingly; a plain ASCII `strings` pass can appear empty:

- `image_bw.ini`, `image_fax.ini`
- `docuname.ini`, `event.ini`, `message.ini`
- `ftp.ini`, `email.ini`
- `histdb_docuname.ini`, `histdb_emailserver.ini`, `histdb_ftpusername.ini`

Ancillary defaults:
- `docuname.ini`: remove path; configured unwanted prefix `Microsoft Word -`; `removestrings=0`.
- `event.ini`: disabled; names are supplied for start/end document and start/end page signals.
- `message.ini`: disabled; progress message name `MessagePrintProgress`.
- `ftp.ini`: disabled; passive mode enabled; port 21; URL and credentials blank.
- `email.ini`: disabled; method 2, port 25, SSL off, zip off, maximum size 50, delete-files off, shared-session on, MAPI off. SMTP identity/host/recipient fields are blank.
- `app.ini`: external application launch disabled; run-default-app enabled; wait-for-completion disabled.
- `general.ini`: `zvprtsrvresident=0`, `zip=0`, and UI pages hidden as `save,image,settings,proginfo`.

The presence of FTP/email APIs and configuration is not evidence that these features are enabled in the default GAM queue. Keep them optional and separately gated in a Linux design.

## Decoded configuration CLI examples (2026-11-24 follow-up)

Static strings from `zvprtcfg_x86.exe` include a usage guide and numbered examples. These examples are stronger evidence for the file-format enum than the INI defaults alone:

| CLI example | Confirmed interpretation |
|---|---|
| `image.fileformat=1` | Save as TIFF (explicitly labelled Example 5) |
| `image.fileformat=2` | Save as JPEG (explicitly labelled Example 6) |
| `save.folder=c:\\temp` | Change the saving folder |
| `save.basefilename=[%%DocName]` | Change the output filename template |

The tool documents `-silent`, `-show`, `-listprinters`, and `-setdefault` options. Its examples also expose configuration controls for supported/default paper size (`gpd.papersize`), DPI (`gpd.dpi`), color (`gpd.color`) and orientation (`gpd.orientation`). It can request batch printing of HTML files recursively (`print.html`) or shell-execute selected TXT/DOC/XLS files (`print.shellexecute`). These are capabilities of the configuration utility; they are not evidence that the GAM deployment enables all of them.

The following numeric values remain unresolved from the current evidence:
- `image.compression`
- `save.filexistact`
- `save.filenameindex`
- `save.popupdialog`
- `save.removeextension`

The CLI strings expose these settings as integer parameters, but do not provide their enum tables. The binary contains phrases such as “Always overwrite” and “Append to existing file”; without a controlled mapping, do not assign those actions to a numeric `filexistact` value.

## Rendering and hand-off clues

- `zvprtuni5` contains rendering-stage names including `Render_StartDoc`, `Render_StartPage`, `Render_StartBand`, `Render_NextBand`, `Render_EndBand`, `Render_SendPage`, and `Render_EndDoc`.
- `zvprtsrv` contains named shared-memory/event synchronization objects under the `Global\\zvprtapi...` family, command identifiers such as `START_DOC`, and server-side print lifecycle strings.
- `zvprtsrv` contains image output filters for BMP, PDF, PNG, TIFF and JPEG/JPEG 2000-related strings. These are supported-codec clues, not a complete statement of selectable output modes.
- The server imports GDI operations such as `StartDocW`, `StartPage`, `EndPage`, `EndDoc`, `CreateDCW`, and `ResetDCW`. The monitor imports spooler operations including `OpenPrinterW`, `ClosePrinter`, and `SetJobW`.
- No direct `WritePrinter` import was observed in the inspected Agent/server/driver/monitor import tables summarized in the investigation. This absence does not exclude dynamically resolved calls or other modules.
- The current Wine prefix had the Wine spooler service running but no GAM printer queue, GAM port monitor or GAM driver registered. This describes that prefix only; it does not establish general Wine incompatibility.

## Evidence interpretation and confidence

| Finding | Status |
|---|---|
| Active queue name is GAMPrinter; install=1 | Directly observed in setup.ini |
| OEM config UI and OEM driver filenames | Directly observed in zvprt5.ini |
| OEMUI/OEMUNI roles | Supported by exports/internal PE names and config mapping |
| Local print monitor and UI extension | Supported by exports and monitor API strings |
| Document rendering is band/page oriented | Strong static-analysis evidence |
| Color/BW/Fax INI defaults | Directly observed in extracted INIs |
| INI files listed above are UTF-16LE | Confirmed by `file` output |
| `image.fileformat=1` = TIFF; `image.fileformat=2` = JPEG | Confirmed by labelled `zvprtcfg` Examples 5 and 6 |
| Compression and save/collision/dialog enum meanings | Unknown |
| Exact output path resolution and generated extension | Unknown |
| Meaning and producer/consumer of `.zan` | Unknown |
| Exact EMWAT → printer → output-file hand-off | Not traced |
| Full installer runtime behavior on Windows | Not tested in this analysis |
| Linux CUPS backend or physical printer support | Not implemented/validated |

## Linux implementation implications

1. Keep printer discovery, metadata, selection and submission as separate operations, as specified in [the printer compatibility plan](PRINTER-COMPATIBILITY-PLAN.md).
2. Do not copy the Windows OEM driver, monitor DLLs or service executable into the Linux product.
3. The utility explicitly documents `image.fileformat=1` as TIFF and `image.fileformat=2` as JPEG. Still verify actual output bytes/extension and discover other enum values before implementing the Linux output contract.
4. Treat document-name normalization and collision handling as explicit policy, not a side effect of the CUPS spool directory.
5. Prefer a controlled native output contract (likely a generated PDF or raster document) only after tracing what EMWAT actually reads/receives from the Windows printer flow.
6. Keep FTP, email, events, watermarks, external-app launch and text-output features out of the minimum compatible path until a real EMWAT workflow demonstrates that they are required.

## Next reverse-engineering tasks

1. Decode `image.compression`, `save.filexistact`, `save.filenameindex`, `save.popupdialog`, and `save.removeextension` numeric enums from server/config code paths and corroborate them with controlled output files; `image.fileformat` values 1 (TIFF) and 2 (JPEG) are now established by the utility's labelled examples.
2. Recover `folder=x` path resolution, output extension, filename numbering and overwrite/append/rename/prompt behavior.
3. Trace `Render_SendPage` and shared-memory IPC through the OEM driver to the server; establish where a completed file is published and how EMWAT retrieves it.
4. Inspect all installer actions/registry writes and determine how `GAMPrinter` queue, port and driver are installed.
5. Trace EMWAT's actual print invocation and consumer path; do not infer it from printer enumeration APIs.
6. Build sanitized test cases for color/BW/Fax, multipage output, filename collisions, missing destination folder, Unicode document names and cancellation.
