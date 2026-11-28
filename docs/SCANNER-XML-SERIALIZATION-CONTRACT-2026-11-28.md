# Scanner XML serialization contract — 2026-11-28

## Evidence

- Contract-closure workflow run: `46117085322`, scanner artifact `15252222043`.
- String-constant recovery workflow run: `46117637962`, artifact `15252222334`.
- Accessor symbols and callsites are from `analysis-input/EmwatMethods.bpl1`; the serialized constants are UTF-16LE and were decoded from the actual addresses passed by the generated setters.

## Root and child names

`ScanResponseXML.NewScanDocument` at `0x004E9D5C` passes the UTF-16LE root name:

- `scan-document`

The output object's constraints child is:

- `constraints`

## Exact UTF-16LE serialized keys

The generated setters pass these exact property keys to the XML helper layer:

| XML object/property | Serialized key |
|---|---|
| `TXMLConfigType.Type` | `type` |
| `TXMLConfigType.DriverDialog` | `driverDialog` |
| `TXMLConfigType.ImageEditor` | `imageEditor` |
| `TXMLConfigType.MultiJpegSupport` | `multiJpegSupport` |
| `TXMLConfigType.PreviousImageName` | `previousImageName` |
| `TXMLOutputType.ForceSinglePageFiles` | `forceSinglePageFiles` |
| `TXMLOutputType.Constraints` child | `constraints` |
| `TXMLConstraintsType.ColorDepth` | `colorDepth` |
| `TXMLConstraintsType.MinResolution` | `minResolution` |
| `TXMLConstraintsType.MaxResolution` | `maxResolution` |
| `TXMLConstraintsType.MaxFileSize` | `maxFileSize` |

The property names are case-sensitive as shown in the UTF-16LE data. Do not change capitalization or introduce alternate spellings in an eventual serializer.

## Known value semantics

- `ColorDepth` selector values are 1, 4, 8 and 24, with labels already recovered in the Run-22 scanner report.
- `MinResolution` and `MaxResolution` feed the corresponding resolution constraints.
- `MaxFileSize` is compared with an image-derived size after scaling by 1024. Its public unit and whether this is a KiB conversion or another legacy unit convention remain unverified.
- `ForceSinglePageFiles` is a separate output-level property, not a constraint field.

## Still open

1. Exact root document schema/version attributes and whether the XML helper serializes any namespace metadata.
2. Runtime XML samples for the complete request and output, including omitted/default-property behavior.
3. Exact `MaxFileSize` unit/conversion and the meaning of the opaque threshold comparison.
4. How `TXMLConfigType` properties are used by the scanner driver/Almas caller.

## Guardrails

These names are static-analysis evidence. Do not implement a serializer solely from the key list until root metadata, defaults, and runtime request/response samples are also recovered.
