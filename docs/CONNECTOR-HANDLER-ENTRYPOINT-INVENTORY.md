# EMWAT connector handler entry-point inventory

Date: 2026-11-26
Sources: `docs/EMWAT-SERVICE-EXECUTABLE-ANALYSIS.md` (service class/VMT dispatch), run 30 connector body traces and run 31 string/helper traces.

This inventory distinguishes three separate identities:
1. the runtime Delphi class name selected by the XML `class` attribute;
2. the concrete `VMT+0x10` method address selected by the service;
3. the TD32 procedure label, which is demonstrably stale/misaligned for several methods.

Runtime VMT dispatch and the service's `GetClass("T"+className)` resolution take precedence over TD32 procedure labels.
The `TUpgradeEmwat` finalization helper also contains an old `[Invoke EditWordDocument]` log literal, but its runtime VMT target, `UpgradeEmwat method called` message, and updater filenames (`EmwatMethods.bpl`, `.zip`, `EmwatUpdate.exe`) identify the operation as upgrade. Do not use that single stale log string to relabel the handler.

## 1. Common service dispatch contract

The service-side dispatch is statically recovered as:

```text
HTTP XML class attribute
  → prefix "T"
  → System.Classes.GetClass("T" + className)
  → construct handler instance
  → store TEmwatInvokeParam* at instance +0x04
  → handler VMT slot +0x0C (0x0046C9E0, TD32 label Finalization)
  → TEmwatMethod.Invoke (0x0046C82C)
  → concrete handler VMT slot +0x10
  → handler PerformMethod(TDictionary<AnsiString, TValue>)
```

- The service enters base wrapper `TEmwatMethod.Finalization` at `0x0046C9E0` (VMT slot `+0x0C`). That wrapper calls `TEmwatMethod.Invoke` at `0x0046C82C` through VMT slot `+0x0C`, then dispatches through the instance's concrete `VMT+0x10` slot (the handler's `PerformMethod`).
- `TEmwatMethod.Invoke` enumerates/normalizes the incoming parameter dictionary. It is **not** itself the subclass handler call.
- For `EditWordDocument`, runtime VMT `0x005ED764` has `+0x10 = 0x005EE82C`. This confirms the class-resolution pattern and provides the positive control for the remaining connector VMT targets.

## 2. Runtime connector classes and concrete VMT targets

| Runtime class selected by XML | VMT+0x10 target | TD32 procedure label at that VA | Body/string evidence |
|---|---:|---|---|
| `TEditWordDocument` | `0x005EE82C` | `TScanDocument.PerformMethod` | Reads `wordConfig`, `wordBody`, `letterImages`, `signData`; calls `TWordViwer.LoadDocument` (`0x004B7724`). |
| `TScanDocument` | `0x005EEB48` | `TFaxDocument.PerformMethod` | Reads key `document`, converts it to a path, opens a file stream (`0x004041BC`), logs `[Invoke ScanDocument]`, constructs `TScanCommand` (`0x004F21DC`), calls method `0x004F2558` (TD32 label `GetNextPage`; RTTI published-method table says `DoRequest`), reads `FResponseXML` (field `+0x34`) through interface slot `+0x54`, then calls unresolved external helper `0x004012F8`. Output dictionary key, XML root/tag and serialization still pending. |
| `TFaxDocument` | `0x005EEDFC` | `TGetEmwatVersion.PerformMethod` | Reads key `fax`; opens two streams and passes the result through helper `0x00500C68`. Exact fax result/error contract pending. |
| `TGetEmwatVersion` | `0x005EF110` | `TSetEmwatVersion.PerformMethod` | Logs COM initialization/uninitialization, calls `UpgradeEmwatPlugin` helper `0x00502F70` with mode 0 and `SetEmwatVersion` helper `0x0050291C`. Version source/result still need mapping. |
| `TSetEmwatVersion` | `0x005EF218` | `TUpgradeEmwat.PerformMethod` | Calls `UpgradeEmwatPlugin` helper `0x00502F70` with mode 1; mutation/validation contract pending. |
| `TUpgradeEmwat` | `0x005EF24C` | `TImageEdition.PerformMethod` | Reads key `PlugIn`; delegates to `@Applicationactivities.Finalization` (`0x0050357C`), which logs `UpgradeEmwat method called`, references `EmwatMethods.bpl`/`.zip` and `EmwatUpdate.exe`, and handles update result/permission errors. |
| `TImageEdition` | `0x005EF300` | `TEditExcelWorkBook.PerformMethod` | Reads keys `data` and `config`; embedded log prefix `[Invoke EditImages]`; emits explicit null-parameter errors for either key, opens file streams, and builds result state. Exact image payload and response XML pending. |
| `TEditExcelWorkBook` | `0x005EF8AC` | `TCompareWordDocument.PerformMethod` | Reads `ExcelConfig` and `ExcelWorkBookContent`; embedded log prefix `[Invoke EditExcelWorkBook]`; rejects null content, opens streams and delegates to `0x005E72B8`. |
| `TCompareWordDocument` | `0x005EFC54` | `TShowEmwatSetting.PerformMethod` | Reads `documentsData`; delegates to `TCompareCommand.DoRequest` (`0x005E9B4C`) and its `Finalization` (`0x005E9BC0`). Exact comparison/result semantics pending. |
| `TShowEmwatSetting` | `0x005EFD4C` | `TShowLastEditedDocs.PerformMethod` | Creates a service object, invokes vtable slot `+0x13C`, then reads a response through `0x0044CE44`; response literal is `success`. |
| `TShowLastEditedDocs` | `0x005EFE4C` | `TShowSendLog.PerformMethod` | Same service-object pattern, with a different global service object; response literal is `success`. |
| `TShowSendLog` | `0x005EFF4C` | not yet identified in the current TD32 trace | Creates the service object through helper `0x00404D5C` using global object `0x0062B4F0`, invokes service vtable slot `+0x13C`, reads the returned interface value through slot `+0x54`, and inserts it into the result dictionary. Output key/value serialization still pending. |

**Critical correction:** the runtime `TScanDocument` endpoint is at `0x005EEB48` (TD32 label `TFaxDocument`). The TD32 label `TScanDocument.PerformMethod` at `0x005EE82C` is the Word handler `TEditWordDocument`. The actual `TImageEdition` runtime target is `0x005EF300` (TD32 label `TEditExcelWorkBook`); the `PlugIn`/Finalization method at `0x005EF24C` is the `TUpgradeEmwat` VMT target. These mappings come from the service-side class/VMT resolution, not from guessing based on log strings.

## 3. Implementation status

- Linux currently registers `EditWordDocument` by default.
- A public Windows `ScanDocument` connector is now confirmed. It delegates to `TScanCommand` and the `TResultImage` single-page/multipage result hierarchy; Linux has not yet implemented the matching handler. Run 34 also recovered the `TScanCommand` field table (`ImgProc`, `Options`, `ResultImage`, `FEditorForm`, state/flag fields, `FPreviousReturnedFileName`, `FRequsetXML`, `FResponseXML`, `FHasConstratints`); its parent VMT pointer remains outside the BPL image, so virtual-slot layout is not fully verified.
- `ImageEdition` is also confirmed as a distinct runtime connector with `data` and `config` inputs. Its output format and response schema remain open.
- Fax, version, upgrade, Excel, comparison, settings, last-edited-documents and send-log methods have runtime VMT targets, but their complete input/output contracts are not all recovered.
- No handler stubs or guessed success responses have been added.

## 4. Security and implementation constraints

- Any dictionary value that becomes a file/path argument (ScanDocument, Fax, ImageEdition, Excel, CompareWordDocument or scanner result XML) is untrusted. Canonicalize beneath an approved application data/output root and reject absolute-path or traversal escapes.
- Do not translate TD32 labels directly into runtime class names. Use the service's `GetClass`/VMT+0x10 map.
- Do not add stubs that return success or invent request keys. Implement only after request parsing, result ownership, error mapping and response serialization are grounded in captures or complete static/runtime evidence.

## 5. Next reverse-engineering targets

1. Cross-check runtime target `0x005EFF4C` (`TShowSendLog`) against its service-object caller and response schema; the body trace is now available.
2. Decode remaining connector response strings and map `TScanDocument`/Fax/ImageEdition request values to response fields.
3. Trace shared version/settings/compare helpers `0x00502F70`, `0x0050291C`, `0x005E72B8`, `0x005E9B4C`, and `0x005E9BC0`.
4. Trace `TImageEdition` target `0x005EF300` separately from `TUpgradeEmwat` target `0x005EF24C`.
5. Capture sanitized Almas requests/responses for each method before implementing its Linux counterpart.

Evidence:
- Service runtime class/VMT map: `docs/EMWAT-SERVICE-EXECUTABLE-ANALYSIS.md`, especially the concrete class dispatch correction.
- Connector body traces: run 30, `https://github.com/meicamghe/EMWAT-Linux/actions/runs/45765541247`.
- Handler string/helper traces: run 31, `https://github.com/meicamghe/EMWAT-Linux/actions/runs/45766302144`.
