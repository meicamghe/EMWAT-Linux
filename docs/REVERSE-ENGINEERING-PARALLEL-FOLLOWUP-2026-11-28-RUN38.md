# Reverse-engineering parallel follow-up — 2026-11-28 Run 38

## WordViewer load path and the Almas handler boundary

The automatically triggered Run-67 `word-print-com` artifact (`15260640277`) contains a full TD32 procedure trace for `TWordViwer.LoadDocument` at `0x004B7724`.

Two callsites in that method invoke `TCreateTiff.SeparteImages`:
- `0x004B7A9C`
- `0x004B7ABD`

The branch at `0x004B7A8E–0x004B7AC2` selects between the two argument paths, then checks the returned output handle and continues through the viewer's image/preview handling. This establishes a direct WordViewer-load -> SeparteImages -> THidePrintingThread -> TIFF/GDI+ conversion chain.

## Important boundary: this is not yet the EditWordDocument wire handler

The Run-67 connector symbol index and handler artifacts contain:
- `TEmwatMethod.Invoke` at `0x0046C82C`;
- `TScanDocument.PerformMethod`;
- `TFaxDocument.PerformMethod`;
- `TEditExcelWorkBook.PerformMethod`;
- `TCompareWordDocument.PerformMethod`;
- `TWordViwer.LoadDocument`.

They do not contain a `TEditWordDocument.PerformMethod` TD32 symbol or a direct Word-edit handler procedure. This is a discovery gap, not proof the handler is absent: the dispatcher uses dictionary-based data and indirect/VMT calls, and the direct-call scanner does not resolve those dynamic dispatches. The existing Almas bridge's `EditWordDocument` route must not be declared byte-for-byte compatible based on the WordViewer TIFF path.

The `TEmwatMethod.Invoke` trace confirms dictionary-driven generic dispatch, but its direct caller scan finds only a module finalization call because runtime handler calls are indirect. Further work must recover the handler's registration table/VMT identity and its input/output dictionary keys, then compare them with a sanitized real Windows HTTP request/response.

## Impact on the acceptance gate

- The Word-to-TIFF preview path is now connected to the viewer load operation.
- The actual browser EditWordDocument handler and the exact response serialization remain unproven.
- No conclusion about LibreOffice save persistence through Almas follows from the viewer/TIFF trace.
- Real Almas Origin/Referer values and sanitized request/response capture remain required.

Evidence:
- Run-67 artifact `15260640277`: `connector-handlers/procedure-004B7724.md`, `connector-handlers/procedure-0046C82C.md`, `connector-handlers/selected-symbols.txt`, and `printer-api/status-callers/wordviewer-load-document-procedure.md`.
- Updated acceptance gate: `docs/ALMAS-LIVE-END-TO-END-ACCEPTANCE.md`.

No production code or workflow source was changed in this run.


## TD32 naming caveat from the same artifact

The procedure labelled `TCompareWordDocument.PerformMethod` at `0x005EF8AC` actually reads the literal keys `ExcelConfig` and `ExcelWorkBookContent` (pointers `0x005EFAF0` and `0x005EFB20`). This is a concrete mismatch between the TD32 decorated class name and the request keys visible in the procedure. Therefore handler discovery must use string references, callsite data flow, VMT/registration identity, and runtime captures together; TD32 class names alone are not reliable evidence for the EditWordDocument handler identity.


**Qualification:** the `TEmwatMethod.Invoke` trace proves dictionary key/value processing and XML-node/value operations, but the direct-call scan finds only a module-finalization call. It is not yet proven to be the live request dispatcher. The runtime registration/indirect call chain remains open.


## Run 46 correction — authoritative handler identity now established

The earlier observation that the Run-67 symbol scan did not include TEditWordDocument.PerformMethod is superseded by the direct VMT/service-dispatch crosswalk in docs/WORD-LIFECYCLE-STATIC-TRACE.md and docs/WORD-DOCUMENT-PROTOCOL-ANALYSIS.md. TEditWordDocument VMT 0x005ED764 has slot +0x10 -> 0x005EE82C; the service resolves class EditWordDocument via GetClass("T"+className), calls TEmwatMethod VMT +0x0C Invoke, and the wrapper dispatches through subclass slot +0x10. TD32's TScanDocument.PerformMethod label on 0x005EE82C is stale. The handler identity is therefore confirmed; only the generic Run-67 VMT resolver produced a false negative.
