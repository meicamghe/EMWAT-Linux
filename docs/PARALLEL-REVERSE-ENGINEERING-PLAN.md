# Parallel reverse-engineering workstreams — run 117

Source: existing GitHub Actions artifact `emwat-word-lifecycle-run117` and its TD32 disassembly/metadata files. This document records independent findings that can be pursued in parallel; it does not claim the complete EMWAT protocol is decoded.

## Workstream A — request/command dispatch and TEmwatMethod.Invoke

### Confirmed observations
- `TEmwatMethod.Invoke` is a 433-byte procedure at `0x0046C82C–0x0046C9DC`.
- Its Delphi signature contains a `TDictionary<AnsiString, ...>`.
- It constructs/initializes a `TXMLEmwatType` object through `0x0044C238`.
- It enumerates dictionary pairs using `TEnumerable.ToArrayImpl` (`0x0046DE84`) and `TPairEnumerator.DoGetCurrent` (`0x0046E324`).
- It uses `TDictionary.AddOrSetValue` (`0x0046DC8C`) to insert/update values in a dictionary during this traversal.
- The only direct TD32-bounded caller currently identified is `TEmwatMethod.Finalization` at `0x0046CA67`. This is important: the current evidence does **not** establish that this method is the HTTP `invoke` route handler.

### Implication
Treat this as a dictionary-to-XML/type-object transformation/finalization helper until the caller chain and request dispatcher are resolved. Do not equate its name with the HTTP query parameter `?invoke=`.

### Next targets
1. Trace `TEmwatMethod.Finalization` around `0x0046CA67` and identify the dictionary's producer and consumer.
2. Resolve the class/VMT method that dispatches the HTTP `invoke` parameter.
3. Correlate command metadata with the observed `POST /?invoke=58351` payload only after the request parser is identified.

## Workstream B — Word document lifecycle

### Confirmed observations
- The event callback `TWordViwer.WordAppDocumentBeforeClose` occupies `0x004CCBBC–0x004CCD59`.
- It derives indexes and values from viewer-owned structures at offsets `+0xE8` and `+0xEC`, obtains an XML field interface, and calls `TWordViwer.GetXmlFieldInfo` at `0x004BCA88`.
- The return value from `GetXmlFieldInfo` is retained in a local boolean-like register/value and the callback performs a subsequent global reporting/logging call with selector `6`.
- `GetXmlFieldInfo` is a large XML/Word field-processing routine (12,688 bytes), with an `IXMLFieldType` parameter in its TD32 signature.

### Implication
The BeforeClose callback is not merely a call to Word's Close method. It performs EMWAT-side field/XML processing during the close event. The exact business meaning of the field and whether the returned flag cancels or changes close behavior must be established from the event interface signature and caller contract.

### Next targets
1. Decode the string constants and XML field names used by `GetXmlFieldInfo`.
2. Trace the event's COM argument and the returned boolean to determine whether it is a Cancel flag or a status result.
3. Compare this callback with `BeforeSave` and `BeforePrint` to identify common field serialization logic.

## Workstream C — print and letter preparation

### Confirmed observations
- `BGPrintWithGamPrintOptions` is a large routine (`0x004C5FF8–0x004C9EA7`) and creates the shared Word Automation wrapper.
- It reads the global print-option state at `0x0062A828`, performs validation, and proceeds through a substantial print preparation path.
- `WordAppDocumentBeforePrintBGPrint` separately gates the Word BeforePrint event and prepares the same global print-option object.
- `PreparePrintDocument` is called from the BeforeSave path.

### Next targets
1. Recover all option names and values consumed by the print routine.
2. Identify the Word document properties and fields changed before print.
3. Map the printer-related state to a Linux CUPS/IPP workflow without attempting to load the Windows kernel printer driver.

## Workstream D — AutoSave/recovery

### Confirmed observations
- The recovery form's Delete path creates the same Word Automation wrapper class used by LoadDocument and BGPrint.
- FormClose iterates Word-side collection items and issues late-bound Automation dispatch calls; the dispatch slot alone does not reveal the method name.
- The artifact does not yet establish the recovery directory, filename extension, list-population function, or exact deletion operation.

### Next targets
1. Resolve the selected-item arguments passed into the Automation wrapper.
2. Trace the wrapper's event callback at `0x005EC594`.
3. Search other modules/resources for list population and recovery path construction.

## Workstream E — Native Linux implementation contracts

Keep implementation separate from reverse engineering, but only encode behavior supported by evidence:
- local loopback HTTP service with route/command registry;
- per-user configuration replacing HKCU registry values;
- document lifecycle event adapter;
- print preparation/validation service;
- recovery provider interface with pluggable discovery backend;
- structured trace/logging around each operation.

Do not implement guessed Word field names, recovery paths, or opaque invoke serialization as if they were known.

## Parallel execution order

The five workstreams can proceed independently against the same immutable artifact. Merge only at explicit interfaces:
1. command dispatcher ↔ XML/request model;
2. document lifecycle ↔ field serializer;
3. field serializer ↔ print preparation;
4. recovery provider ↔ Word Automation adapter;
5. all subsystems ↔ local HTTP API and per-user configuration.

## Confidence summary
- **Confirmed:** dictionary enumeration and update behavior in `TEmwatMethod.Invoke`; direct caller currently points to Finalization, not a proven HTTP handler.
- **Confirmed:** BeforeClose invokes the large `GetXmlFieldInfo` XML/field-processing routine.
- **Confirmed:** print routine and BeforePrint callback share the global print-option state and Word Automation wrapper.
- **Unresolved:** actual HTTP command dispatch mapping, XML field schema, close cancellation semantics, recovery file paths, and full print side effects.
