# Reverse-engineering run 48 — GetNextPage and connector helper follow-up

Date: 2026-11-26  
Workflow run: [45786665652](https://github.com/meicamghe/EMWAT-Linux/actions/runs/45786665652)  
Analyzed workflow commit: `35ffc42ef1717aecfdd065378c9cd249c3ff0ce8`  
Branch: `feature/recovery-retention-policy`  
Inputs: preserved `analysis-input/EmwatMethods.bpl1` and preserved form resources. Static analysis only.

## CI result

All three jobs completed successfully:

- `native-regression`: C++ build/CTest and Python bridge regression passed.
- `image-ui-and-vmt`: scanner/image/UI/VMT trace lane passed and uploaded artifact `15102155195`.
- `word-print-com`: Word/COM/Winspool trace lane passed and uploaded artifact `15101725038`.

Both analysis artifacts were downloaded and inspected. This is not physical scanner/printer or Wine runtime acceptance.

## GetNextPage: full procedure coverage

The skipdata-aware trace now covers all 1,340 bytes of `TScanCommand.GetNextPage` at `0x004F2558–0x004F2A93`. It reports 16 `.byte` pseudo-instructions. Those bytes remain undecoded data, not instructions; control-flow interpretation is limited to paths reached through valid branch/call targets.

Newly visible behavior:

1. The routine calls `VerifyConstraints` with the caller-supplied string, then `LoadRequestXML`; an XML-load error exits through the error path.
2. It branches on `TScanCommand+0x29` (`FIsNextPageRequest`).
3. In the next-page branch, it compares `FPreviousReturnedFileName` (`+0x2C`) against a four-entry global string table, stores the matched index in byte field `+0x1D`, and checks for the `_P` marker. A positive marker test sets byte field `+0x1E` to 2.
4. It constructs/replaces the `ResultImage` object (`+0x20`) through the `TResultImage` constructor at `0x004EC8B4`, using the selected string/format arguments, then calls `HasError`.
5. The new-document path also constructs a `TResultImage`; the selected constructor format depends on the state byte at `+0x1D`. The exact enum-to-format mapping is not established.
6. The routine updates the response XML object (`FResponseXML`, `+0x34`) through virtual calls, obtains a value from the result-image object, assigns it into the response object, and finalizes the result image through one of two virtual slots selected by command state. The exact XML property names and virtual method semantics are not inferred from slot numbers alone.

This makes the paging state and result/response handoff more concrete, but it does not yet establish the final response collection cardinality, exact filename policy, or serialized XML tags.

## Helper findings and limits

- `0x00454B9C` is reached from `TFaxDocument.PerformMethod` with the literal `.tmp` and an output local string. Its body performs Delphi string/list operations and constructs a derived string value. The precise filename/path semantics remain unresolved; do not label it a full path or a temporary file name without further evidence.
- The `document` argument in `TFaxDocument.PerformMethod` remains a dictionary write through `0x0046D2E4` (`TDictionary<String, Variant>.SetItem`), not a dictionary read.
- The newly traced helpers `0x0046D210` and `0x0046D2C0` are generic dictionary lookup/hash machinery. Their callers include `AddOrSetValue`, `ContainsKey`, and `ContainsValue`; they do not identify the semantic meaning of the stored `document` Variant.
- `0x004738CC` is a string/Base64-related conversion wrapper. This helper trace alone does not establish that it is used on the `.tmp` value or the `document` Variant in this call path.

## Next probes

1. Recover the four global strings compared with `FPreviousReturnedFileName`, and map the state bytes `+0x1D/+0x1E` to observed XML/configuration values.
2. Trace the response XML virtual targets used by `GetNextPage` to identify the exact `Scanedimage` collection update and filename/encoding setters.
3. Trace `TResultImage` constructor arguments and finalization methods to establish file ownership and page append/replace behavior.
4. Resolve `0x00454B9C`'s caller-specific string semantics without assuming that `.tmp` is itself a dictionary key or a complete path.
5. Keep the native result metadata model unchanged until these contracts are independently established.

No production native scanner behavior was changed in this run.
