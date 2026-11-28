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
- `MaxFileSize` is interpreted in KiB: `TScanCommand.Finalization` multiplies the configured integer at object offset `+0x14` by 1024 (`shl eax, 10`) before comparing it with the 64-bit image-size value returned by `0x004ECD60`. The helper's exact stream/file source is being cross-checked, but the 1024-byte unit convention is explicit in the comparison.
- `ForceSinglePageFiles` is a separate output-level property, not a constraint field.

## Still open

1. Exact root document schema/version attributes and whether the XML helper serializes any namespace metadata.
2. Runtime XML samples for the complete request and output, including omitted/default-property behavior.
3. Exact `MaxFileSize` unit/conversion and the meaning of the opaque threshold comparison.
4. How `TXMLConfigType` properties are used by the scanner driver/Almas caller.

## Guardrails

These names are static-analysis evidence. Do not implement a serializer solely from the key list until root metadata, defaults, and runtime request/response samples are also recovered.


## Unit conversion cross-check (run 46118668134)

- `TResultImage.GetFileStream` at `0x004ECD60` returns the underlying stream's 64-bit `TStream.Size` value (bytes).
- `TScanCommand.Finalization` compares that byte count against `MaxFileSize << 10`; therefore `MaxFileSize` is definitively KiB (1024-byte units).
- `TGearImgProc.GearType` uses x87 constants 39.37008 and 0.3937. Selector 2 divides resolution by 39.37008; selector 3 leaves it unchanged; selector 4 divides by 0.3937. This is consistent with normalizing metric resolution units to DPI, but exact ImageGear enum labels and rounding need confirmation. See `docs/SCANNER-RESOLUTION-AND-FILESIZE-UNITS-2026-11-28.md`.


## XML root/property string closure (run 46120998177)

Recovered exact names: root `scan-document`; constraints object `constraints`; fields `colorDepth`, `minResolution`, `maxResolution`, `maxFileSize`; error property `error`. The error prefix is `<ScanDoc HasError>. ErrorXML: `. The root string is passed by `NewScanDocument` to XML interface slot +0x8C. See `docs/SCANNER-XML-ROOT-AND-PROPERTY-NAMES-2026-11-28.md`.

## Run 29 — generated getter helper crosswalk

Review of the scanner contract artifact `15252222043` confirms these helper call families:

| Generated getter | Helper call |
|---|---|
| `TXMLConfigType.Get_Type` (`0x004E9FFC`) | `0x0044B4D8` |
| `Get_DriverDialog` (`0x004EA164`) | `0x0044B4C0` |
| `Get_ImageEditor` (`0x004EA2AC`) | `0x0044B4C0` |
| `Get_MultiJpegSupport` (`0x004EA400`) | `0x0044B4C0` |
| `Get_PreviousImageName` (`0x004EA55C`) | `0x0044B4C0` |
| `TXMLOutputType.Get_ForceSinglePageFiles` (`0x004EA760`) | `0x0044B508`, followed by conversion helper `0x00401448` |

`Get_ForceSinglePageFiles` passes a zero-valued argument to `0x0044B508`; this alone does not establish the helper's absent-attribute default. The helper implementations/semantics remain to be resolved before claiming a Boolean default.

`VerifyConstraints` contains the literals `none`, `jpg`, `yes`, and `no` in several comparison branches. The current trace does not conclusively assign each pair to a specific XML property; do not map these values to `type`, `multiJpegSupport`, `driverDialog`, or `imageEditor` by adjacency or intuition.

The numeric getters remain a distinct case: they explicitly test `HasAttribute`, and absent numeric fields return zero before conversion. Present malformed/empty numeric values still enter Variant-to-integer conversion. String-field defaults, requiredness, empty-value behavior, and XML serialization order remain open.

## Run 30 correction — XMLRTL helper identities and generated accessor direction

Run 30 resolves the core helper roles from register/value flow: `0x0044B498` HasAttribute, `0x0044B488` GetAttribute, and `0x0044B4C0` SetAttribute. `0x0044B4D8` is used for the child-node collection/navigation path that resolves the `constraints` child. These correspond to the documented XMLRTL `IXMLNode` methods.

Important correction: TD32 names in this generated accessor range are not reliable for getter/setter direction. `0x004EA94C` reads the `constraints` child; `0x004EAA08`, `0x004EAB58`, `0x004EACB0`, and `0x004EAE08` are numeric getters (HasAttribute/GetAttribute/conversion); `0x004EAAD8`, `0x004EAC2C`, and `0x004EAD84` are SetAttribute-shaped setters. Use the exact literal property names and the Run-30 crosswalk, not the TD32 labels.

`0x0044B508` is still used by `Get_ForceSinglePageFiles`; its missing-attribute/default and conversion semantics remain unresolved. No boolean/string defaults should be inferred from the current call shape.


## Run 31 — XMLRTL child-node call chain cross-check

The `Get_ColorDepth` path at `0x004EA94C` calls `0x0044B4D8` with the current `IXMLNode` and an output interface slot. The returned interface is then called through its first custom-method slot with the literal node name `constraints`, and the result is retained as an `IXMLNode` interface. This call shape matches the XMLRTL chain:

1. `IXMLNode.ChildNodes` returns an `IXMLNodeList`.
2. `IXMLNodeList.FindNode(NodeName)` resolves and returns the named child `IXMLNode`.

The literal `constraints` and the interface return shape support identifying the second dispatch as `FindNode`; the official XMLRTL contracts confirm that `ChildNodes` is an `IXMLNodeList` and `FindNode` accepts a `NodeName` and returns the matching `IXMLNode`. References: [IXMLNode.ChildNodes](https://docwiki.embarcadero.com/Libraries/Alexandria/en/Xml.XMLIntf.IXMLNode.ChildNodes) and [IXMLNodeList.FindNode](https://docwiki.embarcadero.com/Libraries/Athens/en/Xml.XMLIntf.IXMLNodeList.FindNode).

This closes the practical `constraints` navigation chain. It does not identify the internal implementation split inside helper `0x0044B4D8` beyond its ChildNodes-return role. The `0x0044B508` ForceSinglePageFiles helper remains unresolved: the generated accessor supplies the key `forceSinglePageFiles`, a global interface/context argument, and a zero-valued fallback argument before Boolean conversion. Do not claim that missing attributes necessarily resolve to false until that helper's implementation is traced.
