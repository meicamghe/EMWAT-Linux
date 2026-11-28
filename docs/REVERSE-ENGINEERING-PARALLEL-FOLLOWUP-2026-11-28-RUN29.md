# Parallel reverse-engineering follow-up — 2026-11-28 (Run 29: cross-lane correction and proof-boundary audit)

## Scope and evidence set

Run 29 re-opened existing artifacts from the scanner XML, Word event, GAM queue, TIFF worker/GDI+, and SevenZip workstreams. This was artifact-level static analysis; no new GitHub Actions workflow was dispatched and no vendor binary was executed.

Reviewed artifacts:
- Run 50 TIFF/Word artifact `15253702066` (`procedure-004A0148.md`, `procedure-004A0E88.md`, inline constants and caller traces).
- GDI+ interface artifacts `15253721199` and `15253761384` (interface slots, bounded metadata ranges, and candidate methods).
- Scanner artifacts `15252222043`, `15252222334`, `15253432241`, and `15252787473` (generated XML accessors, serialized-name candidates, `LoadRequestXML`, `VerifyConstraints`, and unit conversion).
- TIFF stream/Base64 artifact `15254320056`.
- Existing Word event crosswalk and Run-153 request/wait evidence, plus GAM queue and SevenZip ownership reports.

## 1. Word event identity — functional close path retained, formal DISPID not proven

Two different procedures had been conflated by their TD32 labels:

- `0x004CCBBC` (`WordAppDocumentBeforeClose`) is called from `FillImgFldsForPrint` (`0x004CCF8F`) while `GetFieldIndexInList` iterates print-field metadata. It returns a Boolean used by the field-filtering path. It is not the close callback.
- `0x004CD154` is a separate callback pointer stored by `TWordViwer.OnTmrAutoSave` at event-record offset `+0x80` (context at `+0x84`). Its TD32 label is `WordAppDocumentBeforeSave`, but its first diagnostic says `Document.OnBeforeClose Called.`; its body presents the register-changes decision, handles Cancel/Save/Discard, calls Word `Document.Close` through interface slot `+0x29C`, and clears viewer state `+0x58`.

The Run-153 wait chain remains supported: `LoadDocument` calls `OnTmrAutoSave` synchronously; the loop performs `Sleep(5)` plus `TApplication.ProcessMessages` while viewer `+0x58` is nonzero; the callback at `0x004CD154` clears that state after the close call; then `LoadDocument` writes the `response-word` HTTP response.

**Correct conclusion:** `0x004CD154` is the registered close/save-decision callback that functionally releases the long-lived request. Its formal COM event DISPID is unresolved. Do not label it definitively `DocumentBeforeClose` or `DocumentBeforeSave` until the Word type-library/connection-point dispatch is mapped. Keep `0x004CCBBC` classified as the print-field helper.

## 2. TIFF/print pipeline — worker byte coverage improved; GDI+ save mapping still open

The Run-50 `THidePrintingThread.Execute` trace (`0x004A0E88–0x004A1A9F`) now covers all 3,096 bytes using Capstone skipdata, with 28 `.byte` pseudo-instructions. This supersedes the earlier 1,885/3,096 decoded-byte coverage figure, but **does not mean all bytes were decoded as executable instructions**.

The worker contains repeated polling/retry control flow, including a `Sleep(10)` loop, a `TApplication.ProcessMessages` call, and additional 3,000 ms / 50 ms delays. The exact predicate and identity of the checked object/file at each branch remain unresolved; do not translate the delays into a Linux timeout policy yet.

`TCreateTiff.SeparteImages` (`0x004A0148`) is more firmly bounded:
1. It obtains the `.tif` output-name value through `euGetASFileName`.
2. It checks GAM printer presence/configuration/paused state and invokes `THidePrintingThread.Execute`.
3. A false worker result takes the `Error occured during Convert Word Document to Tiff.` path.
4. It obtains the page-file list from the separate list-like input through `0x004A0BA8`, copies indexed paths into a local `TStringList`, and loads those files through the non-ICM `GdipLoadImageFromFile` constructor branch.
5. The encoder configuration is `EncoderCompression=2` (LZW) and `EncoderSaveFlag=18` (MultiFrame).

The exact GDI+ Save/SaveAdd/final-flush interface mapping is still not closed. The raw Delphi interface metadata is not a flat method-pointer array; the `TGPImage` interface calls at `+0x48`, `+0x70`, `+0x74`, `+0x5C`, and `+0x58` cannot safely be named from the candidate dump. The separately identified `GetNativeHandle`/`SetNativeHandle` wrappers do not resolve those calls.

The page-file list, `.tif` output path, and Base64-decoded ANSI string are distinct values. Do not treat the Base64 call as a filename decoder or connect the SevenZip writer to this TIFF path without a direct hand-off.

## 3. Scanner XML — accessor helper families mapped, defaults still bounded

The serialized root and keys remain confirmed: `scan-document`, `constraints`, `type`, `driverDialog`, `imageEditor`, `multiJpegSupport`, `previousImageName`, `forceSinglePageFiles`, `colorDepth`, `minResolution`, `maxResolution`, and `maxFileSize`.

New accessor-level observations:
- `TXMLConfigType.Get_Type` (`0x004E9FFC`) calls helper `0x0044B4D8`.
- `Get_DriverDialog` (`0x004EA164`), `Get_ImageEditor` (`0x004EA2AC`), `Get_MultiJpegSupport` (`0x004EA400`), and `Get_PreviousImageName` (`0x004EA55C`) call helper `0x0044B4C0`.
- `TXMLOutputType.Get_ForceSinglePageFiles` (`0x004EA760`) calls helper `0x0044B508` with a zero-valued argument, then converts the returned value through `0x00401448`.
- The four numeric constraint getters retain the explicit `HasAttribute` branch: absent attributes return zero; present values proceed through Variant-to-integer conversion.

`VerifyConstraints` contains string constants `none`, `jpg`, `yes`, and `no`, and uses them in several branches that update internal state bytes. The present artifact does not prove which exact XML property each comparison belongs to. Likewise, the zero argument passed by the `ForceSinglePageFiles` getter is not enough to claim its absent-value default until helper `0x0044B508` is identified. String requiredness, empty-value behavior, serialization order, and the property-to-option mapping remain open.

`MaxFileSize` remains confirmed in KiB (`MaxFileSize << 10` compared with `TStream.Size` bytes). `GearType` selectors 2/3/4 use the recovered conversion constants, but exact ImageGear enum labels and rounding remain unresolved.

## 4. GAM queue and SevenZip boundaries remain separate

- GAM discovery matches `PRINTER_INFO_2A.pDriverName == zvprt1`; paused state is read from `PRINTER_INFO_2A.Status == 1`.
- Word polls `EnumJobsW` / `JOB_INFO_1W.pDocument`, normalizes the candidate document name, and repeats `Sleep(5)` plus `ProcessMessages` while a match exists. Queue disappearance is the program's advance condition, not proof of successful TIFF generation; no explicit timeout was observed.
- `JobFinishes.GAM` writer/consumer and the exact `sentineltemplate.txt` contents remain unresolved. Keep this separate from the Agent heartbeat (`/?heartbeat` → `TickTack`).
- `T7zOutArchive.SaveToStream` is the implemented output path; `SaveToFile` and `SetPassword` are stubs. Progress callback `+0x38` is separate from operation-result callback/context `+0x30/+0x34`. No encryption or direct TIFF hand-off is proven.

## 5. Next proof gates

1. Resolve the Word event sink's actual DISPID/connection-point mapping for `0x004CD154`, without changing the already-supported functional wait/release chain.
2. Identify the hidden print worker's polling predicate and file/object ownership; correlate its Boolean result with the page-file list.
3. Map the TGPImage interface calls to initial Save, SaveAddImage, SaveAdd(Flush), then obtain a real multipage TIFF fixture before changing Linux output behavior.
4. Resolve XMLRTL helpers `0x0044B4C0`, `0x0044B4D8`, and `0x0044B508`; only then assign string/boolean defaults and map `none/jpg/yes/no` to exact properties.
5. Continue exact-hash GAM monitor/server sentinel tracing; do not run the vendor installer or conflate the printer sentinel with the service heartbeat.
6. Keep SevenZip `.easz` investigation separate until its callback owner and stream consumer are directly identified.

## Change boundary

No production code, runtime behavior, build, release, merge, rebase, or new Actions run was performed. This update records static evidence and its limits only.