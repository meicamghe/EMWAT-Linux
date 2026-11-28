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

## 4. Important separation from SevenZip

The observed `SeparteImages` direct helper at `0x00454B9C` is `euGetASFileName` (EmailUtil). The current call graph does not establish that `T7zOutArchive` writes the TIFF page files. Keep the SevenZip output-archive investigation separate until a direct caller or output-stream hand-off connects it to this TIFF path.

## 5. Next checks

1. Resolve the exact GDI+ save API and caller from the GDI+ import scan.
2. Identify the output filename and per-page naming scheme, including the meaning of the Base64-decoded string.
3. Map the encoder parameter GUID/value pairs and compression mode.
4. Determine what `THidePrintingThread.Execute` waits for and how its result gates GDI+ processing.
5. Connect the Word queue-disappearance condition to the hidden worker and TIFF output completion.

No physical printer/Word/Almas run was performed. Static control flow is not end-to-end acceptance.
