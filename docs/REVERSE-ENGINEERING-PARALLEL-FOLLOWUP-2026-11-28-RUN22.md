# Parallel reverse-engineering follow-up — 2026-11-28 (Run 22 results)

## Scope and verification

- Repository: `meicamghe/EMWAT-Linux`
- Branch: `feature/recovery-retention-policy`
- Analysis input: `analysis-input/EmwatMethods.bpl1`
- Workflow run: `46112005385` (run 22), workflow commit `9ac31f053c3fe8724f2d00819c7e49562f93a7d6`
- Final job result: all four jobs completed successfully: `native-regression`, `scanner-result-ownership`, `imageen-acquisition`, `word-printer-thread`.
- Artifacts reviewed: scanner `15250485683`, ImageEn `15250475053`, Word/Printer `15250471963`.
- Static-analysis/CI success is not proof of physical scanner, printer, Office, or Almas end-to-end behavior.

## 1. Scanner request/constraint contract

The scanner artifact confirms these direct relationships:

- `TScanCommand.DoRequest` (`0x004F22E4`) calls `LoadRequestXML` (`0x004F2B18`), `Finalization` (`0x004F32F4`) and `HasError` (`0x004F2A94`).
- `TScanCommand.GetNextPage` (`0x004F2558`) calls `VerifyConstraints` (`0x004F2C4C`) and `HasError`.
- `Finalization` reads selector byte `+0x08`; values 1, 4, 8 and 24 map to the localized labels سیاه/سفید, طیف سیاه و سفید, طیف سیاه و سفید یا 256 رنگ, and رنگی 24 بیت.
- Fields `+0x0C` and `+0x10` participate in minimum/maximum resolution checks through `TGearImgProc.GearType`. Field `+0x14` is the previously mapped `TXMLConstraintsType.MaxFileSize` field: it is compared with an image-derived stream-size value scaled by 1024. The precise external unit/conversion contract still needs confirmation.
- Validation errors distinguish requested image mode, minimum resolution, bounded resolution and maximum resolution. Failure can expose Retry/Cancel; a future adapter must not silently coerce invalid images.
- Exact XML serialized names/root-child contract and the precise MaxFileSize unit/conversion remain open. Do not infer strict-vs-maximum mode semantics solely from the labels.

## 2. ImageEn acquisition boundary

- `0x004B012C` is the import thunk to `PKIECtrl23.bpl!TImageEnMIO.Acquire`, called by `TfrmImageTools.InsertPicture` at `0x0050A364`.
- `0x004B0154` is the `TImageEnMIO.PrintImage` thunk; `TfrmImageTools.DoPrintingPanel` calls it at `0x0050A7C3`, `0x0050A8A6`, `0x0050A999`, and `0x0050AA85`.
- `TImageEnMView` multi-selection/count/sort methods are identified. `TfrmImageTools.ScanPicture` at `0x0050A298` is a one-byte RET stub in this build.
- The actual Acquire implementation is external to the current analysis input. No TWAIN/WIA internals can be claimed as reversed until the matching `PKIECtrl23.bpl` is available.

## 3. Word COM callback cross-check

- The event-record pointer at `0x004CD154` is `WordAppDocumentBeforeSave`; it is not BeforeClose.
- `0x004CCBBC` is separately named `WordAppDocumentBeforeClose`, but its active registration/dispatch role remains unproven.
- The callback registration/crosswalk analysis completed successfully. The exact parent-page message and close-time HTTP bridge correlation remain unresolved.

## 4. Printer worker and TIFF preparation

- `TCreateTiff.SeparteImages` at `0x004A0148` is the orchestration entry. Its trace shows printer preflight (`CheckPrinterPaused`, `Zanprinter.Finalization`), calls `THidePrintingThread.Execute` at `0x004A0E88`, then iterates an image collection through virtual count/item slots and continues per-image processing.
- `THidePrintingThread.Execute` spans `0x004A0E88–0x004A1A9F` (3096 bytes). The artifact covers all bytes using Capstone skipdata, but contains 28 `.byte` pseudo-instructions. This is not equivalent to full semantic decoding.
- Its body contains polling/progress and UI/error branches; this artifact still does not prove a Winspool submission call, job completion, or the final GAM TIFF hand-off. No direct `StartDocPrinter`/`WritePrinter` proof was recovered.
- Therefore retain the boundary: printer enumeration/paused-state checks and TIFF preparation are known; the actual spool-submission/completion chain remains open.

## 5. SevenZip output callback boundary

- `T7zOutArchive.SetPropertie` at `0x00454800` stores two supplied values at object offsets `+0x30` and `+0x34`.
- `T7zOutArchive.SetOperationResult` at `0x004547B0` checks `+0x30` and, when nonzero, invokes that stored callback with the stored context and operation-result data. This is callback plumbing; the semantic identity of the callback/context is not yet proven.
- `T7zOutArchive.SetPassword` at `0x004547DC` is a nine-byte stub returning zero. `CryptoGetTextPassword2` at `0x004543C4` initializes an interface field at `+0x2C`, but this alone does not prove whether output archives are encrypted or what password is used.
- `euResetMemory` at `0x00456F00` is a separate helper. It selects a global archive/config object, and calls virtual slots `+0x44`, `+0x0C`, and `+0x3C` with separate values. Its direct callers include `Applicationactivities.Finalization` and auto-save deletion. Do not conflate this helper's `+0x44` slot with the SevenZip output object's `+0x30` callback.
- Output encryption, archive entry naming and the exact `euResetMemory` virtual-slot identities remain unresolved. No password or encryption policy should be hard-coded from the current static evidence.

## 6. Next parallel work packages

1. Trace the exact Word `PrintOut` COM call ABI/Variant argument count and reconcile the 15-vs-18 discrepancy using caller stack construction and imported type-library metadata.
2. Trace `EnumJobsW`/job-document-name matching and any indirect Winspool/VCL calls from the printer worker; connect the job to the produced TIFF/GAM artifact.
3. Resolve `T7zOutArchive` callback object construction, `CryptoGetTextPassword2` consumers and the `euResetMemory` object VMT/slot identities; prove or exclude encryption.
4. Continue scanner XML serialized-name recovery and confirm the `MaxFileSize` conversion/unit against the request/result consumer path.
5. Keep ImageEn Acquire explicitly blocked at the external `PKIECtrl23.bpl` boundary; continue caller-side source/format/ownership analysis without guessing its internals.
6. Trace Word BeforeClose registration and parent-page close bridge independently from BeforeSave.

## Guardrails

No production Linux code was changed by this static pass. No Windows or Linux release build was started. No merge/rebase was performed. Keep Windows binaries as evidence inputs only; do not start implementation until the reverse-engineering contracts are sufficiently closed.
