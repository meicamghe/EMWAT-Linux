# EMWAT connector handler entry-point inventory

Date: 2026-11-26
Source: run 30 parallel static analysis, artifacts `15092201094` (Word/connector lane) and `15091712828` (Image lane), plus the prior runtime VMT cross-check in `docs/WORD-DOCUMENT-PROTOCOL-ANALYSIS.md`.

This document separates **discovered Windows connector methods** from Linux methods that are actually implemented. A TD32 symbol label is not automatically the runtime class name; runtime VMT/dispatch evidence takes precedence.

## 1. Common dispatch contract

### `TEmwatMethod.Invoke` — `0x0046C82C`

- Signature takes a generic `TDictionary` with `System.AnsiString` keys and a result dictionary.
- Obtains an enumerator for the incoming dictionary and iterates its entries using generic dictionary/enumerator helpers (`0x0046DE84`, `0x0046E324`, `0x0046E3CC`).
- Extracts key/value entries, invokes a handler through an interface/vtable method at slot `+0x54`, and inserts the returned value into the result dictionary.
- The exact class-name/method-name routing fields, exception mapping and HTTP response serializer still require string/helper tracing.

This is the common connector dispatch layer. The `PerformMethod` methods below are not independent HTTP servers; they are handler targets invoked through this layer.

## 2. Connector methods discovered

All listed `PerformMethod` symbols have a generic `TDictionary<AnsiString, T>` parameter shape. The concrete dictionary value type is not inferred from the generic debug symbol alone.

| Runtime connector / TD32 label | Procedure VA | Observed body shape | Contract status |
|---|---:|---|---|
| `TEditWordDocument.PerformMethod` (TD32 label `TScanDocument.PerformMethod`) | `0x005EE82C` | Reads `wordConfig`, `wordBody`, `letterImages`, `signData`; delegates to `TWordViwer.LoadDocument` (`0x004B7724`). | Word input keys confirmed; response serialization remains separate work. |
| `TFaxDocument.PerformMethod` | `0x005EEB48` | Reads one dictionary value, opens a file stream, constructs/uses the `TScanCommand` request path and calls `GetNextPage` (`0x004F2558`). | Key literal and fax result mapping pending. |
| `TGetEmwatVersion.PerformMethod` | `0x005EEDFC` | Reads a dictionary value, accesses version/service helpers, and writes a result dictionary entry. | Key/value schema and version source pending. |
| `TSetEmwatVersion.PerformMethod` | `0x005EF110` | Delegates through helpers `0x00502F70` and `0x0050291C`, then returns through the common result path. | Exact version mutation and validation contract pending. |
| `TUpgradeEmwat.PerformMethod` | `0x005EF218` | Delegates through helper `0x00502F70`. | Upgrade side effects and response contract pending. |
| `TImageEdition.PerformMethod` | `0x005EF24C` | Reads key `PlugIn`; delegates to `@Applicationactivities.Finalization` (`0x0050357C`) in module `imageEditionResposeXML`. | Key confirmed; plugin payload/path format and response schema pending. |
| `TEditExcelWorkBook.PerformMethod` | `0x005EF300` | Reads two dictionary values, opens file streams and builds result state. | Both keys, workbook operation and response schema pending. |
| `TCompareWordDocument.PerformMethod` | `0x005EF8AC` | Reads two dictionary values, opens file streams, delegates to helper `0x005E72B8`, and writes the returned value. | Both keys and compare result format pending. |
| `TShowEmwatSetting.PerformMethod` | `0x005EFC54` | Reads key at `0x005EFD3C`; delegates through `0x005E9B4C` and `0x005E9BC0`; inserts a result value. | Key literal and settings schema pending. |
| `TShowLastEditedDocs.PerformMethod` | `0x005EFD4C` | Creates a service object through `0x00404D5C`, invokes vtable slot `+0x13C`, then reads a response through helper `0x0044CE44` and interface slots `+0xB4` / `+0x54`. | Service method and returned document-list schema pending. |
| `TShowSendLog.PerformMethod` | `0x005EFE4C` | Same service-object pattern as `TShowLastEditedDocs`, using a separate global service object and response getter. | Service method and log schema pending. |

The symbol index also contains `TCompareWordDocument`, `TEditExcelWorkBook`, `TFaxDocument`, `TGetEmwatVersion`, `TSetEmwatVersion`, `TShowEmwatSetting`, `TShowLastEditedDocs`, `TShowSendLog`, and `TUpgradeEmwat`. The table above is based on body traces, not class-name presence alone.

## 3. Runtime naming reconciliation

The TD32 name at `0x005EE82C` is `TScanDocument.PerformMethod`, but runtime VMT/dispatch evidence maps the same VA to `TEditWordDocument.PerformMethod` for the `EditWordDocument` request. Its four embedded keys match the Word protocol analysis. Do not count this as a separate public scanner connector.

The internal `TScanCommand` class and its XML validation/page/result lifecycle are separate from the `TEditWordDocument` handler. Its existence does not prove that a public `ScanDocument` method is registered. The actual scanner connector endpoint remains unidentified.

## 4. Linux implementation status and constraints

- Linux currently registers `EditWordDocument` by default; the other connector handlers are not implemented as wire-compatible methods.
- `TImageEdition` is the next concrete image-related connector target, but its `PlugIn` payload and response XML are not yet decoded.
- `TFaxDocument` reaches `TScanCommand` and the result-image hierarchy, but its request key, page/file ownership and response contract remain unknown.
- `TEditExcelWorkBook`, `TCompareWordDocument`, version, settings, last-edited-documents and send-log methods require their dictionary keys and response structures to be recovered.
- Do not register stubs that return success, invent dictionary keys, or translate handler names directly into HTTP methods. Implement only after request parsing, result ownership, error mapping and response serialization are grounded in captures or complete static/runtime evidence.
- Any dictionary value that becomes a file/path argument (Fax, ImageEdition, Excel, CompareWordDocument, or scanner result XML) must be treated as untrusted. Canonicalize beneath an approved application data/output root and reject absolute-path or traversal escapes; the Windows program's working-directory assumptions are not a Linux security policy.

## 5. Next reverse-engineering targets

1. Decode string constants for all handler methods to recover dictionary keys and response labels.
2. Trace shared helpers `0x00502F70`, `0x0050291C`, `0x005E72B8`, `0x005E9B4C`, `0x005E9BC0`, `0x00404D5C`, `0x0044CE44`, and dictionary enumerator helpers.
3. Trace the `TImageEdition.Finalization` helper and decode its embedded path/response strings.
4. Correlate `TFaxDocument` with `TScanCommand` and `TResultImage` without assuming the public method name.
5. Capture sanitized Almas requests/responses for each method before implementing its Linux counterpart.

Evidence:
- Run 30: `https://github.com/meicamghe/EMWAT-Linux/actions/runs/45765541247`
- Word artifact: `15092201094`
- Image artifact: `15091712828`
- Procedure traces: `connector-handlers/procedure-*.md`
