# Word close-wait, periodic recovery timer and HTTP response correlation — 2026-11-17

## Evidence basis

This addendum reconciles the branch's earlier bounded artifact `14314903496` with the more complete mainline static trace in `docs/WORD-LIFECYCLE-STATIC-TRACE.md` (Run 153), the captured exchange in `docs/PCAP-EDITWORD-DOCUMENT-ROUNDTRIP.md`, and the request schema in `docs/EDITWORD-REQUEST-SCHEMA.md`. These are static disassembly and one captured network exchange; they do not establish full Almas-side persistence or byte-for-byte parity for all templates.

## Corrected `OnTmrAutoSave` model

TD32 labels `0x004B8A84` as `TWordViwer.OnTmrAutoSave`. The function is called synchronously by `TWordViwer.LoadDocument` at `0x004B7A58`. It performs more than the initial OLE/Word-engine setup:

1. It initializes the Word automation/event-sink object held at viewer offset `+0x44` and installs the callback/owner pairs previously documented: BeforeSave (`0x004CD154`), NewDocument (`0x004CD54C`), WindowActivate (`0x004CD9C0`), plus the conditional print-related callback (`0x004D00AC` or `0x004CE030`).
2. It installs `OnControlerNotify` (`0x004BB3B0`) as the `OnTimer` callback on the VCL `TTimer` stored at viewer offset `+0x7C`.
3. It sets the timer interval in viewer field `+0x88`, clamping it to at least `0x2710` (10,000 ms), and enables the timer.
4. It then synchronously waits at `0x004B9AE8`: `kernel32!Sleep(5)`, `TApplication.ProcessMessages`, and a test of viewer field `+0x58`. The loop repeats while that field is nonzero. The every-200-iteration maintenance/check path is a repeating one-second cycle, not a one-second total timeout.

Therefore the correct model has **two separate behaviors** inside this routine: (a) a periodic VCL timer that calls `OnControlerNotify`, and (b) a synchronous wait that keeps the `EditWordDocument` HTTP request open until viewer field `+0x58` becomes zero. The routine is not itself a simple Word `Document.Save` call, and no direct call from it to `SilentSaveEmwatDoc` has been established.

The earlier branch note that described the body only as Word-engine/event setup was incomplete. The timer callback and close-wait behavior above supersede that incomplete interpretation.

## Periodic `OnControlerNotify`: local recovery/archive, not final HTTP response

The timer callback at `0x004BB3B0` is distinct from the registered Word BeforeSave callback. The trace shows it:

- reads Word document content through the generated Word document interface slot `+0xDC`;
- uses the document path retained in viewer field `+0xA0`;
- creates/updates the paired `.easd` and `.easz` recovery files;
- packages the `.easd` document entry into a 7z output archive at the `.easz` path.

The source document path is passed to `T7zOutArchive.AddFiles` as the source file; the archive member name is derived from viewer base path `+0x80` plus `.easd`. `T7zOutArchive.SaveToStream` creates/truncates the `.easz` target with a `TFileStream(fmCreate)` and completes the archive. This is a local periodic recovery/archive mechanism. It must not be equated with the final Almas response body or claimed as a final registration POST.

The read-side linkage is established by the main `TWordViwer` constructor at `0x004D0D24–0x004D0FE6`: it opens `HKCU\\Software\\Emwat\\Dynamic Config`, conditionally reads integer `AutoSaveInterval`, stores it in viewer field `+0x88` (default `0`), and the timer setup clamps that field to at least `10000 ms`. The settings form's write path stores lookup-table values multiplied by 1000 for indices 1–5 and writes `10000` for index 0/out-of-range. Exact lookup DWORDs and combo labels remain to be recovered.

## Close callback releases the waiting request

The callback target at `0x004CD154` is TD32-labelled `WordAppDocumentBeforeSave` and is explicitly stored in the event-sink callback record. Its observed close path calls Word's `Document.Close` through interface slot `+0x29C` at `0x004CD31C`, then clears viewer field `+0x58`. That zero transition releases the `OnTmrAutoSave` wait loop.

This establishes the static state transition that releases the long-running request. It does not, by itself, settle the formal COM event DISPID or prove that the callback is a conventional BeforeClose event; preserve the symbol name and observed close behavior separately. The routine at `0x004CCBBC` remains a different method and must not be substituted as the registered callback.

## Actual successful HTTP response

After the wait exits, `LoadDocument` takes its successful branch and:

1. obtains `AResponseInfo` from `TEmwatInvokeParam+0x0C`;
2. assigns the generated XML to `AResponseInfo.ContentText` at offset `+0xBC`;
3. calls Indy `TIdHTTPResponseInfo.WriteContent` through BPL import thunk `0x0040448C`;
4. sets `bResultSet` at invoke-record offset `+0x05`.

The captured exchange documents HTTP 200 with a `response-word status="success"` XML envelope. Its `return-types/type` entry declares `mimetype="application/msword"` and `encryption="base64"`; the decoded payload begins with the OLE Compound File signature `D0 CF 11 E0 A1 B1 1A E1`. The PCAP has TCP payload gaps, so do not claim a complete payload hash or byte-for-byte comparison.

The captured first response byte arrives approximately 54.558 seconds after the request body completes. That is consistent with the synchronous wait lasting for the user's Word editing session and ending when the close path clears viewer `+0x58`.

`TEditWordDocument.PerformMethod` sets `bUnloadPkg` after `LoadDocument` returns; it does not itself set `bResultSet`. The BPL `LoadDocument` success branch writes the HTTP response and sets that flag, so the generic service fallback writer is skipped.

## Keep these mechanisms separate in the Linux design

| Windows behavior | Evidence-backed role | Linux design boundary |
|---|---|---|
| VCL timer / `OnControlerNotify` | Periodic local document-content recovery archive | Separate recovery snapshot service; do not conflate with final HTTP response |
| Word event callback at `0x004CD154` | Prompts/handles close path and clears the wait state after `Document.Close` | Close-driven session completion; distinguish save/discard/cancel only where captured |
| `OnTmrAutoSave` wait loop | Keeps original invoke request pending until viewer `+0x58 == 0` | Keep per-document HTTP request open while the visible office document remains open |
| `LoadDocument` response branch | Returns the final Word-compatible DOC/CFB bytes in Base64 XML | Export final legacy DOC/CFB and serialize the captured response envelope |
| `SilentSaveEmwatDoc` | Separate field-value collection/print helper path via `StoreFieldValuesForPrint` | Do not use it as the periodic recovery or final response implementation |

The current LibreOffice adapter already models a close-driven session and snapshots a Word 97 `.doc` on the UNO close callback. It does not yet implement the separate periodic local recovery archive. Any Linux recovery format should be explicitly versioned and should not pretend to read/write the Windows encrypted `.easz` format until the archive password/format contract is safely verified.

## Remaining work

- Recover the exact DWORD values at lookup table pointer slot `0x0062A808` and the corresponding `cbbAutoSaveInterval` labels; verify the index-zero/default behavior.
- Recover the exact COM event identity/DISPID and initial setter of viewer field `+0x58`.
- Implement and test a separate periodic recovery snapshot mechanism in the Linux adapter, with cancellation/close synchronization and atomic replacement.
- Confirm save/discard/cancel response envelopes and whether each path returns a DOC/CFB body.
- Validate the response against a complete sanitized PCAP/template fixture and perform an end-to-end Almas round trip.
