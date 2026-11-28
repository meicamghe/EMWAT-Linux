# TIFF output pipeline — GDI+ and printer orchestration — 2026-11-28

## Evidence

- Workflow: `EMWAT TIFF output lifecycle follow-up`
- Run: `46118848571`
- Artifact: `15252563510`
- Relevant procedures:
  - `TWordViewer.LoadDocument` at `0x004B7724`
  - `TCreateTiff.SeparteImages` at `0x004A0148`
  - `TCreateTiff.THidePrintingThread.Execute` at `0x004A0E88`

## 1. LoadDocument enters the TIFF pipeline

`TWordViewer.LoadDocument` calls `TCreateTiff.SeparteImages` twice through two branches:

- `0x004B7A9C`
- `0x004B7ABD`

Before that, it calls `euGetASFileName` at `0x00454B9C` to derive a filename from the supplied UnicodeString. This helper is a filename utility, not a SevenZip archive method.

## 2. Printer preflight and hidden worker

`SeparteImages` performs the printer/worker orchestration before its GDI+ page-processing loop:

1. Calls `Zanprinter.GetPrinterName` to find the printer whose driver is `zvprt1`.
2. If the printer is not present, calls `GetZanInstallDir`; that helper includes a bounded retry loop of up to 300 × 100 ms while waiting for the printer to appear.
3. Calls `Zanprinter.Finalization`, which reads `PRINTER_INFO_2A.Status` and checks for paused status.
4. Calls `Zanprinter.CheckPrinterPaused` as a separate check.
5. Calls `TCreateTiff.THidePrintingThread.Execute` at `0x004A0E88`.
6. If the hidden worker reports success, proceeds to page/image processing; otherwise it enters the error path.

The exact relationship between the two pause-related methods and the hidden worker's completion signal remains open.


## 2A. Hidden-worker wait primitives

The wait API cross-check confirms `0x004028D0` is `kernel32!Sleep`, despite its stale TD32 label `SuspendThread`. `THidePrintingThread.Execute` uses Sleep intervals of 10 ms, 50 ms, 3000 ms, and 5000 ms at different branches, and calls `TApplication.ProcessMessages` through `0x00404F04` at two points. The exact branch conditions and whether the 3/5-second waits are retry timeouts or delayed status checks still need to be mapped.

## 3. GDI+ page-processing evidence

After the worker stage, `SeparteImages`:

- Obtains the page/image count through an object VMT call.
- Constructs `Gdiplus.TGPEncoderParameters` at `0x0048F8C0`.
- Sets encoder parameter values through VMT slot `+0x20` using globals `0x0062A84C` and `0x0062A804`.
- Constructs `Gdiplus.TGPImage` objects at `0x0048FF60` for page/image items.
- Calls `Gdiplus.TGPImageFormat.InitializeCodecs` at `0x0048ED8C`.
- Uses GDI+ image VMT slots `+0x48`, `+0x1C`, `+0x70`, `+0x74`, `+0x5C`, and `+0x58` during per-page processing.
- Calls `Base64Decode` at `0x004735C4` on a result string in a later branch.

This is strong evidence that GDI+ is involved in page/image conversion and encoding. The exact GDI+ save API, output filename, encoder GUID, compression parameter values, and final output-file hand-off are not yet proven.


## 3A. GDI+ save API surface confirmed

The CreateTiff module imports these GDI+ APIs:

- `GdipSaveImageToFile` (thunk `0x00481C64`)
- `GdipSaveImageToStream` (thunk `0x00481C6C`)
- `GdipSaveAdd` (thunk `0x00481C74`)
- `GdipSaveAddImage` (thunk `0x00481C7C`)
- `GdipGetImageEncoders` (thunk `0x00482394`)
- `GdipCreateBitmapFromFile` / `GdipCreateBitmapFromStream` (thunks `0x00481D7C` / `0x00481D74`)

TD32 also contains `TGPImage.Save` file/stream overloads at `0x004908AC`, `0x004908E4`, `0x00490950`, and `0x004909B4`, plus `SaveAdd` overloads at `0x00490A18` and `0x00490A84`. This confirms the GDI+ save surface exists in the exact module. The direct VMT/call path from `SeparteImages` to the specific Save/SaveAdd overload and the encoder GUID/value pair are being cross-checked.



## 3B. Encoder GUIDs resolve to multipage LZW TIFF

The GDI+ VMT/data pass follows the two globals passed to the encoder-parameter interface at `SeparteImages`:

- Global `0x0062A84C` points to GUID bytes at `0x00628198`: `{e09d739d-ccd4-44ee-8eba-3fbf8be4fc58}`, the GDI+ `EncoderCompression` GUID. The caller passes value `2`, which is `EncoderValueCompressionLZW`.
- Global `0x0062A804` points to GUID bytes at `0x00628228`: `{292266fc-ac40-47bf-8cfc-a85b89a655de}`, the GDI+ `EncoderSaveFlag` GUID. The caller passes value `18`, which is `EncoderValueMultiFrame`.

This is strong direct evidence that the TIFF encoder is configured for LZW compression and a multi-frame/multipage save sequence. The exact interface VMT slots used for initial Save, subsequent SaveAdd, and final flush are still being mapped; do not yet infer page ordering or finalization behavior.


### Interface-dispatch boundary

In `SeparteImages`, the `TGPEncoderParameters` instance is constructed via `0x0048F8C0` using the VMT pointer loaded from global slot `0x00483F4C` (that global contains `0x00483FA4`); its interface reference is taken from object offset `+0x28`, then interface slot `+0x20` is called twice with the two GUID/value pairs above. The `TGPImage` instance is constructed via `0x0048FF60` using the VMT pointer loaded from global slot `0x00484728` (that global contains `0x00484780`); later calls dispatch through its interface reference at slots `+0x48`, `+0x70`, `+0x74`, `+0x5C`, and `+0x58`. The raw interface metadata blocks at `0x0047DD2C` and `0x0062EE88` are Delphi interface/RTTI structures, not simple method-pointer arrays. Exact Save/SaveAdd/final-flush method identities remain unresolved.

The corrected VMT pass confirms the constructor inputs (`0x00483FA4` for TGPEncoderParameters and `0x00484780` for TGPImage), but the pointed structures contain Delphi class/interface metadata and interleaved method records rather than a flat pointer array. The interface slot calls described above therefore remain the reliable observed contract; do not infer Save/SaveAdd identity from the raw VMT dump alone.


### Symbol/import discrepancy to resolve

The PE import scan and TD32 thunk labels disagree for the GDI+ save thunks. The PE import table maps `0x00481C64` to `GdipSaveImageToFile`, `0x00481C6C` to `GdipSaveImageToStream`, `0x00481C74` to `GdipSaveAdd`, and `0x00481C7C` to `GdipSaveAddImage`. TD32 labels at those addresses are shifted/different (for example, it labels `0x00481C64` as `GdipSaveImageToStream`). Since the same TD32 symbol table mislabeled the confirmed `Sleep` thunk as `SuspendThread`, do not use those thunk symbols alone to identify the APIs. A second parser (`GNU objdump -p`) independently confirms the PE import names and IAT order: IAT RVA `0x2307C8` = `GdipGetImageGraphicsContext`, `0x2307CC` = `GdipSaveAddImage`, `0x2307D0` = `GdipSaveAdd`, `0x2307D4` = `GdipSaveImageToStream`, and `0x2307D8` = `GdipSaveImageToFile`. Therefore the PE import mapping is confirmed; TD32 thunk labels are stale/shifted. The actual TGPImage interface VMT callsites still need mapping before assigning a specific Save overload to a specific API.


## 3C. TIFF extension, printer messages, and Base64 boundary

Inline constants in `SeparteImages` establish the `.tif` extension at `0x004A071C`. The routine also contains the exact printer/error messages:

- Persian: `پرينتر (مجازي) گام در حالت توقف قرار دارد. لطفا صف وظايف آن را ...`
- English: `Gam Printer is in "Paused" state! please check.`
- `Error on setting gam printer parameters.`
- `Error occured during Convert Word Document to Tiff.`

`Base64Decode` is called from `SeparteImages` at `0x004A05EF`, but it is a shared utility: other direct callers include `TWordViewer.StoreFieldValuesForPrint` and `TfrmImageTools.FreeRotate`. Therefore its presence in `SeparteImages` does not by itself prove it decodes an output filename; the exact source string and decoded destination still need to be traced. The TD32-named `TGPImage.FromFile` wrapper at `0x00490048` calls the `GdipDisposeImage` thunk on an existing native handle, so its symbol name alone also does not prove that this call loads a file. GDI+ file/stream load imports exist, but their callsites remain open.



### SeparteImages selects the file-load branch

The callsite resolves the constructor flag: at `0x004A03C9` and `0x004A03F9`, `SeparteImages` pushes `0`, obtains a UnicodeString path through an object interface slot `+0x0C`, and calls the `TGPImage` constructor at `0x0048FF60`. The zero flag selects the constructor branch that calls `0x00481C3C`, confirmed by the PE import table as `GdipLoadImageFromFile`. This happens for two image objects. Therefore the observed `SeparteImages` input is file-backed, not the alternate stream branch.

## 3D. TGPImage constructor load branch

The `TGPImage` constructor at `0x0048FF60` has two load branches. Based on the constructor's stack flag, it calls either thunk `0x00481C4C` or `0x00481C3C`, then wraps the returned native image handle. The PE import scan maps `0x00481C3C` to `GdipLoadImageFromFile`; the import behind `0x00481C4C` is not yet identified. The separate TD32-named `TGPImage.FromFile` method at `0x00490048` only disposes an existing native handle via `GdipDisposeImage` and resets the object; its name is not evidence of a load call. The exact file-vs-stream branch used by `SeparteImages` remains to be confirmed from its stack argument and the `0x00481C4C` import.

## 4. Important separation from SevenZip

The observed `SeparteImages` direct helper at `0x00454B9C` is `euGetASFileName` (EmailUtil). The current call graph does not establish that `T7zOutArchive` writes the TIFF page files. Keep the SevenZip output-archive investigation separate until a direct caller or output-stream hand-off connects it to this TIFF path.

## 5. Next checks

1. Resolve the exact GDI+ save API and caller from the GDI+ import scan.
2. Identify the output filename and per-page naming scheme, including the meaning of the Base64-decoded string.
3. Map the encoder parameter GUID/value pairs and compression mode.
4. Determine what `THidePrintingThread.Execute` waits for and how its result gates GDI+ processing.
5. Connect the Word queue-disappearance condition to the hidden worker and TIFF output completion.

No physical printer/Word/Almas run was performed. Static control flow is not end-to-end acceptance.
