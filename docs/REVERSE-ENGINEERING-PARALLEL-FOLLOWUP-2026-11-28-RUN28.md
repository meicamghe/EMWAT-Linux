# Parallel reverse-engineering follow-up — 2026-11-28 (Run 28: exact bundled printer payload)

## Scope and correction

Run 28 cross-checked the existing repository's own extracted-package inventory, component resource/hash report, GAM virtual-printer analysis, printer configuration trace and Agent/Service IPC analysis.

**Important correction to Run 27:** the exact EMWAT-bundled `GAMPrinterSetup.exe` is already present in `EMWAT_Extracted.zip` in this repository and has been statically unpacked/analyzed. The public Zan 5.0.19 package discussed in Run 27 is only a family-level comparison; it is not the next prerequisite for analysis. The exact EMWAT payload is the primary evidence from here onward.

No new Actions run, binary execution, build, release, production-code change, merge or rebase was performed.

## 1. Exact EMWAT printer package and component hashes

The committed `EMWAT_Extracted.zip` is 24,018,540 bytes and its inventory records 70 files. The nested `GAMPrinterSetup.exe` is 4,008,872 bytes; its own analysis records an internal LZX CAB at offset 249,344, 3,759,528 bytes, with 49 files and approximately 15,060,720 extracted bytes.

Exact hashes from `EMWAT-COM-Resource-Report.txt`:

| Component | Size | SHA-256 |
|---|---:|---|
| `GAMPrinterSetup.exe` | 4,008,872 | `cdec0363d420d8b1e7109e2a5624e0ed834a82b43b437c8d1c85a3c6303a6d15` |
| `zvprtsrv_x86.exe` | 2,506,752 | `7ed0c5433d7429798dbfa5ddfa1205eb845d27b7af565f547dd039c27cb54f46` |
| `zvprtmon5_x86.dll` | 13,921 | `4110a7fa9e25d41fa6ce5cc103dc58c524afe639545e9062d71a3f4822431459` |
| `zvprtmonui5_x86.dll` | 9,443 | `8fc621f0f2ced5121933a5356ab1c1923b441b85f33fba81f6cd4eb1db813ed6` |
| `zvprtuni5_x86.dll` | 44,544 | `6862709326702e1e2cef24369185a218a0a01aaae6268f491707d3844e0c7236` |
| `zvprtui5_x86.dll` | 195,072 | `5d16f384a9c87d0e517ad617448c50d533a91a85afedfd4b165f9cb51fc9ff0f` |
| `sentineltemplate.txt` | 40 | `3813c0a65ad3f24416d34303c94f7ea2660401d4c58551c7f3c4a8831051c54e` |
| `general.ini` | 508 | `76dec37975ede9b9eea91155b2db12a27f62e7b7e47e31fd395b9a9123bf0162` |
| `save.ini` | 186 | `0efd0151b03f00ecdc642a1cff1966db62a810a397b09c774ed5de7fdcd92ccd` |

The inventory also contains x64 variants of the monitor, UI, OEM driver and server. The exact component hashes are stable identifiers for any subsequent static/runtime trace; use these, not public Zan sample hashes.

## 2. Printer lifecycle architecture — strongest supported static model

The exact-package analysis in `docs/GAM-VIRTUAL-PRINTER-REVERSE-ENGINEERING.md` already records:

- `zvprtmon5_x86.dll` has local print-monitor entry points `InitializePrintMonitor2`, `LcmOpenPort`, `LcmStartDocPort`, `LcmWritePort`, and `LcmEndDocPort`.
- `zvprtuni5_x86.dll` contains the render-stage names `Render_StartDoc`, `Render_StartPage`, `Render_StartBand`, `Render_NextBand`, `Render_EndBand`, `Render_SendPage`, and `Render_EndDoc`.
- `zvprtsrv_x86.exe` imports GDI document/page operations including `StartDocW`, `StartPage`, `EndPage`, `EndDoc`, `CreateDCW`, and `ResetDCW`; it contains BMP/JPEG/PDF/PNG/TIFF image-codec/filter strings.
- The driver/server evidence contains `Global\\zvprtapi...` shared-memory/event names and command strings such as `START_DOC`.
- The server has private `.zan` extension strings, but their role is unresolved.
- The package's `setup.ini` configures queue `GAMPrinter`, install=1, 200x200 DPI, A4, color, all-users=1 and autostart=0.
- The configuration utility's labelled examples confirm `image.fileformat=1` means TIFF and `image.fileformat=2` means JPEG. The shipped color/BW/Fax profiles use value 1 (TIFF).

This supports a pipeline of spooler monitor → OEM rendering/band callbacks → server IPC → file/image output. The exact order and ownership of each IPC message, and the exact point where the output file becomes durable, are not yet recovered.

## 3. Sentinel evidence — exact file identified, consumer still not assigned

Direct BPL evidence:
- EMWAT writes `general.ini` section `[general]` keys `sentinel=1` and `sentinelfile=JobFinishes.GAM`.
- The exact GAM payload includes `sentineltemplate.txt` (40 bytes; SHA-256 above).
- The default package `general.ini` profile records `zvprtsrvresident=0`, `zip=0`, and hidden UI pages `save,image,settings,proginfo`; the BPL's runtime writes must be kept distinct from the shipped default file.

What is not proven:
- The contents/format of `sentineltemplate.txt` are not present in the current text inventory; only its size and hash are recorded.
- No inspected BPL callsite writes `JobFinishes.GAM` or reads it back.
- The current component analysis does not identify whether the monitor DLL, OEM driver, server process, or another helper creates the sentinel.
- No evidence yet establishes whether the sentinel is created before or after TIFF close/flush, whether it is atomic, or whether it contains job/document identifiers.

**Do not infer the consumer from the filename alone.** The best next static targets are exact-hash `zvprtsrv_x86.exe`, `zvprtmon5_x86.dll`, `zvprtuni5_x86.dll`, and the 40-byte template. In particular, cross-reference file-creation APIs, `general.ini` reads, `sentineltemplate` strings, and the monitor's `LcmEndDocPort` path.

## 4. Keep EMWAT's reliability heartbeat separate from printer JobFinishes

The Agent/Service analysis documents a different `TEmwatSentinel` mechanism:
- `EmwatAgent.exe` issues `GET http://127.0.0.1:1984/?heartbeat`.
- A successful response body is exactly `TickTack`.
- This path updates sequential heartbeat-error state and logs `[Heartbeat] Cleared from error.`.

That is a loopback service-health sentinel, not evidence of a consumer for `JobFinishes.GAM`. The current Agent/Service resource report contains `TEmwatSentinel`/heartbeat strings but no identified `JobFinishes.GAM` consumer. Do not conflate the two sentinel systems.

## 5. Cross-workstream state after Run 28

| Workstream | Current static conclusion | Still open |
|---|---|---|
| GAM printer | Exact EMWAT package and component hashes known; monitor/driver/server roles and lifecycle names recovered | Which component writes `JobFinishes.GAM`; template contents; file durability/atomicity |
| Word close | Callback strongly maps to Application.DocumentBeforeClose; Save/Discard/Cancel and local HTTP release recovered | Numeric DISPID and Almas/browser response consumer |
| SevenZip | SaveToStream creates file and writes through ISequentialOutStream.Write | Callback owner, .easz format/options and output encryption |
| Scanner XML | Four numeric absent attributes return zero; present invalid numeric strings go through Variant conversion | String-field defaults/requiredness and runtime samples |
| GDI+ TIFF | Initial Save includes frame 0; first SaveAddImage is skipped; remaining frames appended then Flush | Runtime TIFF bytes/order and Almas acceptance |

## 6. Exact next proof gates

1. Recover the 40-byte `sentineltemplate.txt` content and trace exact-hash server/monitor/driver references to `sentinel`, `sentinelfile`, and file-create/write APIs.
2. Follow `LcmEndDocPort` into server IPC and correlate the final server-side page/document completion with the sentinel path.
3. Keep Word's HTTP response consumer and COM DISPID as independent open questions.
4. Map the string XML accessors and their XMLRTL helper semantics; do not assign empty defaults based only on TD32 labels.
5. Obtain a runtime-generated TIFF fixture before translating GDI+ encoder behavior into Linux output code.

No Linux behavior should be changed on the basis of an assumed sentinel owner or assumed archive/print hand-off.
