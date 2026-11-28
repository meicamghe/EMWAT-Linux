# Reverse-engineering parallel follow-up — 2026-11-28 Run 37

## Automated GDI+ VMT analysis coverage gap

Inspected the actual source of `tools/resolve_delphi_vmt_slots.py`, which is invoked by the existing `image-ui-and-vmt` workflow job.

Its hard-coded `TARGET_CLASSES` includes scanner/image UI classes such as `TMultiPageImage`, `TSetOfMultiPageImages`, and `TScanCommand`, but does not include `TGPImage` or `TGPEncoderParameters`. Consequently, the current automated VMT-resolution step cannot produce direct slot reports for the two GDI+ classes relevant to the TIFF Save/SaveAdd cycle.

This explains why the existing GDI+ artifacts stop at candidate metadata and interface pointers rather than a verified TGPImage method table. The operation-level Save/SaveAdd callsite mapping remains high-confidence, but the raw VMT is not yet closed.

Recommended targeted local extraction:

```bash
python3 scripts/dump_pe_va_ranges.py analysis-input/EmwatMethods.bpl1 \
  --range 0x00484700:0x300 \
  --range 0x0047DD2C:0xA0 \
  --range 0x0062EE88:0x90
```

The first range covers the class/VMT candidate area around `0x00484728`; the second covers interface metadata; the third covers candidate interface-pointer data. A future resolver enhancement should add `TGPImage` and `TGPEncoderParameters` to `TARGET_CLASSES`, then validate all method pointers against executable sections and TD32 procedure ranges.

No tool or workflow source was modified because `tools/**` is a push trigger for the parallel analysis workflow. No new workflow was dispatched.
