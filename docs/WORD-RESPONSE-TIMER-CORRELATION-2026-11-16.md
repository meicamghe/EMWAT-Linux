# EMWAT Word response and periodic timer correlation — 2026-11-16

Repository: `meicamghe/EMWAT-Linux`  
Scope: static reverse engineering of the Windows EMWAT implementation, cross-checked against the captured local HTTP exchange.

## 1. The successful EditWordDocument response writer is now mapped

The BPL response branch at `0x004B7F9C–0x004B7FD8` establishes the following:

1. It obtains the `TEmwatInvokeParam` record from the second procedure argument.
2. It obtains the `AResponseInfo` object from that record at offset `+0x0C`.
3. It assigns the generated response XML string to `AResponseInfo.ContentText` at offset `+0xBC`.
4. It calls `TIdHTTPResponseInfo.WriteContent` through import thunk `0x0040448C` (resolved to `IndyProtocols230.bpl!TIdHTTPResponseInfo.WriteContent`).
5. It sets `TEmwatInvokeParam.bResultSet` at record offset `+0x05` to 1.

This is the concrete BPL response-writing branch. The method-level return string and the HTTP response are not separate unrelated outputs: the non-empty response branch places the generated XML into the Indy response object and writes it to the HTTP client. See artifact `14228851062`, files `load-document-response-branch.md`, `004B7F9C.md`, and `0040448C.md`.

Correction applied to `docs/EDITWORD-REQUEST-SCHEMA.md`: `TEditWordDocument.PerformMethod` copies the returned string into its inherited method result and sets `bUnloadPkg`; the `bResultSet` flag is set in the `LoadDocument` response-writing branch, not in `PerformMethod` itself.

## 2. OnControlerNotify is a periodic timer callback, not a Word close event

The timer registration is now directly confirmed by the `OnTmrAutoSave` code and imported VCL symbols. A separate controller-owner trace also resolves `TEDPController.Notify` at `0x004D2EC8`: it invokes `TEmwatDocPrintHandler.GetDocFieldName` through a stored callback at object offset `+0x18`. This is the print-handler controller and must not be confused with `TWordViwer.OnControlerNotify` at `0x004BB3B0`, which is the timer callback:

- Viewer field `+0x7C` is used as the `TTimer` instance.
- `0x00404B94` resolves to `Vcl.ExtCtrls.TTimer.SetOnTimer`; the code assigns callback `0x004BB3B0` (`TWordViwer.OnControlerNotify`).
- Viewer field `+0x88` is used as the interval. The code clamps it to at least `0x2710` (10,000 ms), calls `TTimer.SetInterval` through `0x00404B8C`, and enables the timer through `TTimer.SetEnabled` at `0x00404B84`.

Therefore, the method named `OnControlerNotify` is registered as the timer's OnTimer callback, with a minimum 10-second interval. The associated metadata strings include selectable intervals `10 seconds`, `30 seconds`, `1 minute`, `3 minutes`, `5 minutes`, and `15 minutes`; their exact binding to viewer `+0x88` is likely but not yet proven. It is not the Word close/save callback.

## 3. What that timer callback does

The callback at `0x004BB3B0`:

- checks viewer state before proceeding;
- calls `TWordViwer.CostumizeRecAndCC`;
- calls the Word document Content getter through interface slot `+0xDC`, passing `-1` (the argument's semantics remain unknown);
- uses the stored document path at viewer offset `+0xA0`;
- derives sibling paths from viewer offset `+0x80`, appending `.easd` and `.easz`;
- passes those paths and archive objects to `euUnArchive` at `0x00456DFC`.

This is a periodic local archive/recovery path. It is not itself the HTTP POST or the `response-word` envelope. Do not equate this archive with the final Almas document commit.

## 4. Keep the Word events distinct

- The callback pointer written at `TWordApplication` event field `+0x80` is `0x004CD154`. Run-27 RTTI identifies this field as `OnDocumentBeforeClose`; the TD32 symbol `WordAppDocumentBeforeSave` is misleading.
- The first diagnostic string inside `0x004CD154` is `Document.OnBeforeClose Called.`; its body displays the Persian register-changes prompt, calls the three-argument Word `Document.Close` wrapper, and clears viewer `+0x58`. The wrapper RTTI confirms the event property as `OnDocumentBeforeClose`; the numeric COM DISPID and event-source IID are still not decoded.
- `WordAppDocumentBeforeClose` at `0x004CCBBC` is a separate TD32 procedure; no active event registration reference was found in the analyzed range.
- The timer-driven `OnControlerNotify` at `0x004BB3B0` is separate from both Word events.
- The registered OnDocumentBeforeClose handler has a Yes/No/Cancel path and invokes Word Close wrappers. The `Set_Saved` wrapper correction is documented in `docs/WORD-FIELD-SILENT-SAVE-ANALYSIS.md`.

## 5. Network capture cross-check

The captured exchange on loopback port 1984 contains:

- `POST /?invoke=<nonce>` with the EditWordDocument request body;
- HTTP 200 response;
- XML root `response-word`, `status="success"`;
- `return-types/type` with `mimetype="application/msword"` and `encryption="base64"`;
- a returned legacy OLE Compound File document that differs from the request document.

The first response payload arrived about 54.558 seconds after the final request-body byte. This is direct evidence of a long-lived invoke request and a returned document, but it does not alone identify which internal wait/event releases the request. The response PCAP has 17 four-byte TCP sequence gaps (68 captured-payload bytes missing; estimated 51 decoded document bytes), so the full returned file and its hash are not verified.

## 6. Completed analysis batch

The three workflows listed in the original investigation batch completed and their artifacts were inspected:

- `Analyze EMWAT Word wait and COM call chain` — run `43873345452`
- `Analyze EMWAT Word request lifecycle` — run `43873354906`
- `Analyze EMWAT controller callback ownership` — run `43873363849`

The resulting timer registration, synchronous wait/release chain, and separate `TEDPController.Notify` ownership are recorded in sections 8–10 below. The wrapper event property is now identified as OnDocumentBeforeClose; the numeric COM DISPID and the semantic type of the first nonzero `+0x58` value remain unresolved.

## 7. Remaining questions

1. What exact object/token does helper `0x004565DC` return to the first known writer of viewer `+0x58`?
2. Which numeric COM event DISPID and event-source IID map to the RTTI-confirmed `OnDocumentBeforeClose` field `+0x80`?
3. Does the periodic `.easz` archive feed a separate recovery channel, or is it consumed by another part of the desktop/browser bridge?
4. What exact response XML is produced for non-DOC, image, and DOCX workflows?
5. Can a complete gap-free response capture be obtained for a definitive document diff?

No document contents, Base64 bodies, cookies, or authorization values are included in this note.


## 8. Controller name collision resolved

The separate `TEDPController.Notify` method at `0x004D2EC8` is not the timer callback. Its body checks a stored callback at object offset `+0x18`, calls `TEmwatDocPrintHandler.GetDocFieldName` at `0x004A8F78`, and clears the temporary interface/reference. Its VMT has a `SetOnNotify` property setter and `SetPrintThread` setter. Direct immediate CALL xrefs to `Notify` are absent, consistent with event/VMT invocation. The method belongs to the print-handler controller and is a separate control path from `TWordViwer.OnControlerNotify`.

Evidence: controller-callback-ownership run `43873363849`, artifact `14229520023`, including `procedure-004D2EC8.md`, `controller-symbols.md`, and `timer/OnTmrAutoSave-timer-registration.md`.


## 9. RTTI resolves the BeforeClose event property despite the TD32 symbol mismatch

The native callback at `0x004CD154` is named `WordAppDocumentBeforeSave` in TD32, but its first log string is `Document.OnBeforeClose Called.`. Its prompt text is Persian: “محتويات اين سند تغيير كرده است. آيا مايل به ثبت تغييرات مي‌باشيد؟” (“The contents of this document have changed. Do you want to register the changes?”). The Yes/No branches call the three-argument `Document.Close` wrapper with SaveChanges True/False; Cancel sets the event Cancel flag. This is close/registration behavior. The wrapper RTTI maps event-record offset `+0x80` to `OnDocumentBeforeClose`; only the numeric COM DISPID and event-source IID remain unproven.

The metadata block at `0x00627B74` has now been decoded: it is an error-message/resource map (`Err_20000`, `Request XML is invalid`, `Error on connect to MS-Word`, etc.) plus logging levels and auto-save interval labels, not the Word event DISPID table. It does not resolve the callback's formal COM event identity. Use “registered `TWordApplication.OnDocumentBeforeClose` callback at `0x004CD154`”; retain the numeric DISPID as unresolved.


## 10. Long-lived HTTP request release — confirmed static chain

The request/response delay is now explained by a synchronous state-wait loop inside `TWordViwer.OnTmrAutoSave`:

1. `TWordViwer.LoadDocument` calls `OnTmrAutoSave` synchronously at `0x004B7A58`.
2. The wait loop at `0x004B9AE8` calls `kernel32!Sleep(5)`, then `TApplication.ProcessMessages`, then tests viewer field `+0x58`.
3. While viewer `+0x58` remains nonzero, the loop repeats. Every 200 iterations (about one second) it resets the counter and runs the maintenance/check calls at `0x00445B10` and `0x00455108`, then continues waiting. **The 200-iteration cycle is not a one-second total timeout; it repeats until the state changes.**
4. When the close/registration callback at `0x004CD154` completes the Word `Document.Close` call, it writes zero to viewer `+0x58` at `0x004CD31C`.
5. The wait loop observes zero, disables the 10-second timer, and returns from `OnTmrAutoSave`.
6. `LoadDocument` then follows its success branch at `0x004B7F31`, writes the `response-word` XML through Indy `WriteContent`, and sets `bResultSet`.

This provides a direct static explanation for why the HTTP invoke remains open while Word is being used and why the response arrives after the close/registration path. The observed ~54.558-second PCAP delay is consistent with that wait duration. The numeric COM DISPID/event-source IID and the semantic type of the first nonzero `+0x58` token remain to be resolved.

Evidence: request-lifecycle artifact `14229047092` (notably `LoadDocument-complete-range.md`, `target-004B999A.md`, and `BeforeSave-control-flow.md`); wait-mechanism artifact `14229716255` (`OnTmrAutoSave-004B9AE8.md`, exact Sleep thunk); controller ownership artifact `14229520023`.

### WaitForSingleObject false lead excluded

The exact thunk/caller scan shows the only direct `WaitForSingleObject` call in this BPL is from `GraphicCompression.FireEvent` (`0x00607240–0x0060786B`), a separate GraphicCompression worker/event pump. It is not in the `TWordViwer` request lifecycle and should not be treated as the Word-close wait. The Word request wait is the `Sleep(5)` + `ProcessMessages` loop inside `OnTmrAutoSave` that polls viewer `+0x58`.


## 2026-11-25 reconciliation — request wait, HTTP response, and close decisions

The static wait chain remains the best-supported explanation for the long-lived request: `LoadDocument` enters the synchronous `OnTmrAutoSave` wait, the loop polls viewer `+0x58`, and the response writer runs after that state clears. This is consistent with the approximately 54.558-second PCAP delay. The local service must keep this long-lived invoke isolated from heartbeat handling; heartbeat must remain serviceable while the Word request is pending.

The wrapper RTTI now identifies callback `0x004CD154` at field `+0x80` as `OnDocumentBeforeClose`, despite the TD32 label `WordAppDocumentBeforeSave`. The numeric COM DISPID remains unresolved. The first nonzero setter for viewer `+0x58` is now located in `PrintWithGamPrintOptions` (`0x004C5E44`); helper `0x004565DC` supplies the token whose exact meaning remains unresolved.

The independent DevTools capture for `invoke=29501` matches the PCAP `invoke=58351` response length (1,166,820 bytes) and HTTP content type/charset, but its body is unavailable. The PCAP's inner `response-word` / Base64 `application/msword` structure is confirmed only for `58351`. See `docs/RUNTIME-CAPTURE-2026-11-25.md` and `docs/PCAP-EDITWORD-DOCUMENT-ROUNDTRIP.md`.

The Linux close contract is now explicit in `docs/WORD-CLOSE-RESPONSE-CONTRACT-2026-11-25.md`: Save returns the latest successfully saved snapshot; Don't Save returns the last approved snapshot (initial input if no Save completed); Cancel leaves the session open and the pending request waiting. A generic close callback must never snapshot the live unsaved buffer. This is the required Linux behavior; it does not claim that the Windows callback's COM DISPID or exact wire branch has been fully resolved.


## 2026-11-25 update — event RTTI and initial wait-token writer

Run 27 artifact `15008774182` identifies `TWordApplication` field `+0x80` as `OnDocumentBeforeClose`, and `OnTmrAutoSave` stores `0x004CD154` at that field. The TD32 symbol `WordAppDocumentBeforeSave` is therefore a misleading procedure label, not the event-property identity.

The full-class field scan also found the first known nonzero write to viewer `+0x58`: `OnTmrAutoSave` calls `PrintWithGamPrintOptions` at `0x004B937C`; it writes the return from `0x004565DC` to `Self+0x58` at `0x004C5E44`. The close callback clears the field at `0x004CD31C`. The value's semantic type remains pending a dedicated helper trace.
