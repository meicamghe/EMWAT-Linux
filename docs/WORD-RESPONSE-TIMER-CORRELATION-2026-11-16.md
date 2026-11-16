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

Therefore, the method named `OnControlerNotify` is registered as the timer's OnTimer callback, with a minimum 10-second interval. It is not the `WordAppDocumentBeforeClose` event.

## 3. What that timer callback does

The callback at `0x004BB3B0`:

- checks viewer state before proceeding;
- calls `TWordViwer.CostumizeRecAndCC`;
- calls the Word document Content getter through interface slot `+0xDC`, passing `-1` (the argument's semantics remain unknown);
- uses the stored document path at viewer offset `+0xA0`;
- derives sibling paths from viewer offset `+0x80`, appending `.easd` and `.easz`;
- passes those paths and archive objects to `euUnArchive` at `0x00456DFC`.

This is a periodic local archive/recovery path. It is not, on current evidence, the HTTP POST or the `response-word` envelope. Do not equate this archive with the final Almas document commit.

## 4. Keep the Word events distinct

- The callback pointer written at Word application event-record offset `+0x80` is `0x004CD154`, whose TD32 symbol is `WordAppDocumentBeforeSave`.
- **Event identity is under recheck:** the first diagnostic string inside `0x004CD154` is `Document.OnBeforeClose Called.`, and its control flow displays the Persian register-changes prompt before calling the three-argument Word `Document.Close` wrapper. The method's TD32 name therefore cannot, by itself, prove that the event-record slot is the COM `DocumentBeforeSave` DISPID.
- `WordAppDocumentBeforeClose` at `0x004CCBBC` is a separate TD32 procedure; no active event registration reference was found in the analyzed range.
- The timer-driven `OnControlerNotify` at `0x004BB3B0` is separate from both Word events.
- The registered BeforeSave handler has a Yes/No/Cancel path and invokes Word Close wrappers. The `Set_Saved` wrapper correction is documented in `docs/WORD-FIELD-SILENT-SAVE-ANALYSIS.md`.

## 5. Network capture cross-check

The captured exchange on loopback port 1984 contains:

- `POST /?invoke=<nonce>` with the EditWordDocument request body;
- HTTP 200 response;
- XML root `response-word`, `status="success"`;
- `return-types/type` with `mimetype="application/msword"` and `encryption="base64"`;
- a returned legacy OLE Compound File document that differs from the request document.

The first response payload arrived about 54.558 seconds after the final request-body byte. This is direct evidence of a long-lived invoke request and a returned document, but it does not alone identify which internal wait/event releases the request. The response PCAP has 17 four-byte TCP sequence gaps (68 captured-payload bytes missing; estimated 51 decoded document bytes), so the full returned file and its hash are not verified.

## 6. Next analysis now running

Three existing workflows were extended and triggered:

- `Analyze EMWAT Word wait and COM call chain` — run `43873345452`
- `Analyze EMWAT Word request lifecycle` — run `43873354906`
- `Analyze EMWAT controller callback ownership` — run `43873363849`

They extend the OnTmrAutoSave body and timer registration, inspect the remaining request/response path, and trace `TEDPController.Notify` ownership. Results are not yet marked complete; the run artifacts must be inspected before treating any new trace as confirmed.

## 7. Remaining questions

1. Which call or wait mechanism holds the original HTTP invoke open until the user finishes editing?
2. Which exact Word event or state transition releases that wait?
3. Does the periodic `.easz` archive feed a separate recovery channel, or is it consumed by another part of the desktop/browser bridge?
4. What exact response XML is produced for non-DOC, image, and DOCX workflows?
5. Can a complete gap-free response capture be obtained for a definitive document diff?

No document contents, Base64 bodies, cookies, or authorization values are included in this note.


## 8. Controller name collision resolved

The separate `TEDPController.Notify` method at `0x004D2EC8` is not the timer callback. Its body checks a stored callback at object offset `+0x18`, calls `TEmwatDocPrintHandler.GetDocFieldName` at `0x004A8F78`, and clears the temporary interface/reference. Its VMT has a `SetOnNotify` property setter and `SetPrintThread` setter. Direct immediate CALL xrefs to `Notify` are absent, consistent with event/VMT invocation. The method belongs to the print-handler controller and is a separate control path from `TWordViwer.OnControlerNotify`.

Evidence: controller-callback-ownership run `43873363849`, artifact `14229520023`, including `procedure-004D2EC8.md`, `controller-symbols.md`, and `timer/OnTmrAutoSave-timer-registration.md`.


## 9. BeforeSave / BeforeClose identity discrepancy

The native callback at `0x004CD154` is named `WordAppDocumentBeforeSave` in TD32, but its first log string is `Document.OnBeforeClose Called.`. Its prompt text is Persian: “محتويات اين سند تغيير كرده است. آيا مايل به ثبت تغييرات مي‌باشيد؟” (“The contents of this document have changed. Do you want to register the changes?”). The Yes/No branches call the three-argument `Document.Close` wrapper with SaveChanges True/False; Cancel sets the event Cancel flag. This is close/registration behavior, but the COM event DISPID corresponding to event-record offset `+0x80` has not yet been proven.

A new event-dispatch workflow is tracing the generated Word event method table at `0x00627B74` and its callback dispatch thunks to determine whether the callback is actually bound to DocumentBeforeClose or DocumentBeforeSave. Until that completes, use the neutral label “registered close/save decision callback at 0x004CD154” rather than asserting the COM event identity.
