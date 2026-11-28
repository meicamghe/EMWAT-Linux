# Print worker, TIFF and SignData crosswalk — 2026-11-28

## Evidence and confidence

- Binary: `analysis-input/EmwatMethods.bpl1`, SHA-256 `6ff7d262f46ab009e3eecf20fca40cd41ec8ad937adf7bbfe2f6eddd56aaea2d`.
- VMT/property/worker traces: workflow run `46153864129`, artifact `15267235867`.
- CFG, VMT and helper traces: workflow run `46154581970`, artifact `15267456134`.
- Static analysis only. No live Windows/Almas print acceptance run is implied.

## Print pipeline — proven links

1. `TWordViwer.BeforeSave` callback `0x004CD54C` calls `PrintWithGamPrintOptions` (`0x004C5E04`) when the document-window condition matches `GamElectronic EMWAT`.
2. `PrintWithGamPrintOptions` creates/uses `TPrintOptions` and calls a Word document interface method at vtable slot `+0x6C`. The exact COM method name for that slot is not yet independently mapped.
3. `TWordViwer.LoadDocument` calls `TCreateTiff.SeparateImages` (`0x004A0148`) at `0x004B7A9C` and `0x004B7ABD`. These are two separate call sites; which request field each processes still needs argument-level confirmation.
4. `TCreateTiff.SeparateImages` checks the GAM printer state before conversion. If paused, it displays:
   - Persian: `پرينتر (مجازي) گام در حالت توقف قرار دارد. لطفا صف وظايف آن را خالي نموده و پرينتر را فعال نماييد.`
   - English: `Gam Printer is in "Paused" state! please check.`
   - It also has an error path: `Error occured during Convert Word Document to Tiff.`
5. The conversion path configures TIFF compression `LZW (2)`, encoder save flag `MultiFrame (18)`, and a frame/page value `0x17`. The code iterates frames and invokes the GDI+/image wrapper's save/add/flush-like virtual methods. The exact vtable slot-to-GDI+ API names remain partially unresolved.
6. `TCreateTiff.SeparateImages` creates/starts a `THidePrintingThread` helper during the conversion path.
7. `THidePrintingThread.Execute` is VMT slot target `0x004A1AA0`. It repeatedly calls `FindWindowW(NULL, L"Printing")`, hides a matching window with `ShowWindow(hwnd, SW_HIDE)`, and sleeps for 15 ms between attempts. It runs at most 500 iterations (about 7.5 seconds) when its byte flag at `Self+0x0E` is nonzero, or 10,000 iterations (about 150 seconds) when zero. This thread hides the Word printing progress window; it is not the TIFF-output completion waiter.
8. The main `TEmwatDocPrintHandler.Execute` VMT slot target is `0x004A609C`. Its control-flow trace reaches 1,480 instructions and 264 direct calls; the full procedure is 11,708 bytes, so some bytes remain unreachable/inline data in this CFG pass.

## Print-thread control and job tracking

### TEmwatDocPrintHandler

- VMT class pointer: `0x004A22F0`; Execute virtual slot `+0x08` points to `0x004A609C`.
- Constructor: `0x004A5C10`; destructor: `0x004A5D78`; `ForgotMe`: `0x004A8F78`.
- Relevant fields from class metadata:
  - `FAbort +0x34`
  - `fWordApp +0x48`
  - `fWordDoc +0x4C`
  - `fJob +0x50`
  - `fDocFileName +0x68`
  - `fPrintingOption +0x6C`
  - `fDocProtectionType +0x70`
  - `fovProtectionPass +0x74`
  - `fovCurPageNo +0x78`
- `ForgotMe` sets `FAbort`, then invokes the thread termination/wait path. `TWordViwer.TEDPController.Notify` calls this method, establishing a controller-to-worker cancellation path.
- The TD32 label at `0x004A609C` is `TrimLF`, but the VMT slot and body field accesses identify it as the worker Execute method. Treat that TD32 name as stale.

### TPrintJobs / TPrintJob

- `TPrintJobs.GetJob` at `0x004AA148` searches for an existing job keyed by the supplied thread handle and creates a `TPrintJob` if none exists.
- `TPrintJob.Create` at `0x004AA340` stores the key in `finsPid +0x0C`; `TPrintJob.gettid` at `0x004AA33C` returns that field.
- The key is obtained via `GetCurrentThread` thunk `0x0040271C`, which returns the Windows current-thread pseudo-handle. Therefore, despite the field name `finsPid`, this observed path is keyed by a thread pseudo-handle, not a process ID.
- `TPrintJobs.Remove` is at `0x004AA310`; it manages the shared job-list lifetime.
- The TD32 labels for several of these routines disagree with the VMT/extended method metadata and body semantics; use the validated method crosswalk, not the stale labels.

## SignData and caption-image path

- The WordConfig field with `paramId="signData"` is declared in the captured fixture with `mimetype="image/png"` and `encryption="base64"`; `separator`, `concater`, and `concator` remain independent metadata and are preserved by the resolver.
- `TWordViwer.SignData` is stored at `+0xF4`.
- `GetCaptionItemFont` begins at `0x004C19C0`. It checks the `SignData` field and compares a caption-item key against the native string `signData` at `0x004C2718`. On the matching branch, it copies `Self+0xF4` into the local caption value.
- The caption processing path calls `EmbedTextToImage` at `0x004C436C`. That method receives a UnicodeString and a dynamic array of `TCaptionItem`, performs dimension/unit conversion, and calls image/rendering helpers.
- `GetCaptionItems` at `0x004C2B20` parses a caption-item structure and maps multiple attributes into XML nodes. Its decorated signature identifies a dynamic array of `TCaptionItem`.
- This proves that SignData is not merely stored: it is substituted into the caption-item processing path and passed toward image embedding. It does **not** yet prove the precise base64 decoding, separator handling, image input/output format, or final GDI+ object semantics. Keep the external payload opaque until helper-level and byte-level comparisons are complete.

## VMT and property cross-checks

- `THidePrintingThread` class pointer `0x004A00E8`; Execute slot `+0x08` → `0x004A1AA0`.
- `TEmwatDocPrintHandler` class pointer `0x004A22F0`; Execute slot `+0x08` → `0x004A609C`.
- `TWordViwer` class pointer `0x004B10A4`; VMT Destroy slot `-0x04` → `0x004D1148`. The class method table maps Create to `0x004D0D24` and Destroy to `0x004D1148`; TD32 labels around `0x004D08B4`–`0x004D1148` are stale/misaligned and should not override VMT plus body evidence.
- The `TWordViwer` class has no published or extended properties in the parsed property tables. `OpenAsFree` is a private field, not a published property; no direct write to `+0x5F` was found in the BPL. Its host-side initialization remains unresolved.
- `TWordApplication` property metadata confirms `OnDocumentBeforeClose`, `OnDocumentBeforePrint`, `OnDocumentBeforeSave`, and `OnNewDocument` event properties.
- `TWordDocument` has an `OnClose` event field at `+0x70`; the `Saved` property wrapper methods are `0x0042BD94` (getter) and `0x0042BDF8` (setter). Its callback registration/use remains unmapped.

## Remaining work

1. Decode the remaining image helper methods `0x004AFE88`, `0x004AFF08`, `0x004AFF10`, `0x004AFEB8`, and the caption XML attribute strings around `0x004C2D28`–`0x004C2DDC`.
2. Trace the printer-status string references and the main worker's helpers (`0x004A5F68`, `0x004A90D4`, `0x004A9464`, `0x004AA85C`, `0x004A9884`, `0x004A9CB8`, `0x004A9A08`).
3. Map the GDI+/image wrapper vtable slots to exact Save, SaveAdd, Flush operations.
4. Map `TWordDocument.OnClose` and the Word automation connection point/IID/Advise path.
5. Locate the host-side writer of `OpenAsFree`.
6. Run live Windows/Almas acceptance and byte-level TIFF/PNG output comparison before claiming parity.

## Tool artifacts

- Seed merge: [workflow run 46153451750](https://github.com/meicamghe/EMWAT-Linux/actions/runs/46153451750), artifact `rea-combined-seeds.tsv` (8,411 unique function addresses).
- CFG/VMT/worker analysis: [workflow run 46154581970](https://github.com/meicamghe/EMWAT-Linux/actions/runs/46154581970), artifact `emwat-undelphi-rtti-and-rea-seeds`.
- REA/Ghidra itself has not yet been run; the generated seed file is prepared for import.
