# Scanner resolution and file-size unit conversions — 2026-11-28

## Evidence

- Workflow: `EMWAT scanner unit and size-source closure`
- Run: `46118668134`
- Artifact: `15252787473`
- Relevant methods:
  - `TGearImgProc.GearType` at `0x004EEF30`
  - `TResultImage.GetFileStream` at `0x004ECD60`
  - `TScanCommand.Finalization` at `0x004F32F4`

## 1. MaxFileSize is KiB; compared stream size is bytes

`TResultImage.GetFileStream`:

1. Obtains the underlying stream from the result image object.
2. Checks the stream reference.
3. Calls the stream's virtual size getter, which returns a 64-bit value in `EDX:EAX`.
4. Returns that 64-bit stream size to its caller.

`TScanCommand.Finalization` calls this method for the result image, then computes:

- configured threshold = `TScanCommand+0x14 << 10` (multiply by 1024)
- measured value = 64-bit `TStream.Size`

If the configured threshold is lower than the measured stream size, it reports the maximum-file-size error. This confirms `TXMLConstraintsType.MaxFileSize` is expressed in KiB (1024-byte units), compared against a byte count.

## 2. Resolution unit normalization

`TGearImgProc.GearType` reads a resolution-unit selector and normalizes the two resolution values before producing the value used by `Finalization`.

The two 80-bit x87 constants are:

- `0x004EF030` = `39.37008`
- `0x004EF03C` = `0.3937`

The branch behavior is:

| Unit selector | Operation |
|---:|---|
| 2 | Divide both resolution values by 39.37008 |
| 3 | Use the resolution values without unit conversion |
| 4 | Divide both resolution values by 0.3937 |
| Other | Unsupported/default path returns zero |

The factors correspond to inches-per-meter and inches-per-centimeter. The conversions are consistent with normalizing metric resolution values to pixels-per-inch (DPI), with selector 3 already in the target unit. The exact ImageGear enum labels should still be checked against the matching ImageGear metadata before using these numeric values in a compatibility layer.

## 3. Remaining caveats

- `0x004AFF08` is an import thunk to the external ImageGear API `IG_image_resolution_set`, not an internal helper. It is called by `TGearImgProc.GearType` and `TWordViewer.EmbedTextToImage`. Its exact argument-to-field semantics should be checked against the matching ImageGear SDK before naming the two values horizontal/vertical DPI.
- The exact external ImageGear enum names for selectors 2/3/4 remain to be matched.
- Runtime scanner samples are still needed to confirm rounding behavior and edge cases (zero/one resolution, unsupported unit, non-square DPI).

## Implementation guardrail

The safe compatibility contract is: treat MaxFileSize as KiB and compare against byte length; normalize resolution to DPI using the factors above only after verifying the ImageGear enum mapping and rounding rules.


## Run 51 — ColorDepth numeric values closed

The Run 51 scanner artifact (`15263439921`) cross-checks the XML input and finalization output paths. The exact internal `colorDepth` values are **1 = black/white, 4 = grayscale, 8 = grayscale-or-256-colour, 24 = 24-bit colour**. The XML value is written to `TScanCommand+0x08` as the same numeric byte; the default/unmatched branch stores zero. See `docs/SCANNER-XML-SERIALIZATION-CONTRACT-2026-11-28.md` for instruction ranges and both-direction evidence.

This resolves the static enum mapping only. It does not establish that every physical scanner/driver accepts all four modes or that the Linux SANE mapping is behaviorally identical.
