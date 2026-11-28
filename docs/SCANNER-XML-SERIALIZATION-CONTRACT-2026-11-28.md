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

## Run 30 helper map — superseded by Run 32 call-shape cross-check

The initial Run 30 label set assigned `0x0044B488` to GetAttribute and `0x0044B4C0` to SetAttribute. Run 32 rechecked the actual generated getter/setter callsites and found that assignment too coarse. Use the corrected Run 32 map below instead.

TD32 names in this generated accessor range are not reliable for getter/setter direction. The callsite behavior and interface return types are more reliable than the symbol labels. The exact property keys remain those listed above.

`0x0044B508` is still used by `Get_ForceSinglePageFiles`; its missing-attribute/default and conversion semantics remain unresolved. No Boolean/string defaults should be inferred from the current call shape.


## Run 31 — XMLRTL child-node call chain cross-check

The `Get_ColorDepth` path at `0x004EA94C` calls `0x0044B4D8` with the current `IXMLNode` and an output interface slot. The returned interface is then called through its first custom-method slot with the literal node name `constraints`, and the result is retained as an `IXMLNode` interface. This call shape matches the XMLRTL chain:

1. `IXMLNode.ChildNodes` returns an `IXMLNodeList`.
2. `IXMLNodeList.FindNode(NodeName)` resolves and returns the named child `IXMLNode`.

The literal `constraints` and the interface return shape support identifying the second dispatch as `FindNode`; the official XMLRTL contracts confirm that `ChildNodes` is an `IXMLNodeList` and `FindNode` accepts a `NodeName` and returns the matching `IXMLNode`. References: [IXMLNode.ChildNodes](https://docwiki.embarcadero.com/Libraries/Alexandria/en/Xml.XMLIntf.IXMLNode.ChildNodes) and [IXMLNodeList.FindNode](https://docwiki.embarcadero.com/Libraries/Athens/en/Xml.XMLIntf.IXMLNodeList.FindNode).

This closes the practical `constraints` navigation chain. It does not identify the internal implementation split inside helper `0x0044B4D8` beyond its ChildNodes-return role. The `0x0044B508` ForceSinglePageFiles helper remains unresolved: the generated accessor supplies the key `forceSinglePageFiles`, a global interface/context argument, and a zero-valued fallback argument before Boolean conversion. Do not claim that missing attributes necessarily resolve to false until that helper's implementation is traced.


## Run 32 — XMLRTL node-list and attribute access crosswalk

Reinspection of the scanner accessor artifact distinguishes attribute-list access from child-node access:

| Helper | Observed call shape | Best-supported XMLRTL role | Confidence |
|---|---|---|---|
| `0x0044B498` | node + property-name; Boolean in AL | `IXMLNode.HasAttribute(Name)` | High |
| `0x0044B488` | node + out interface; returned list receives `FindNode(name)` | `IXMLNode.AttributeNodes` getter | High |
| `0x0044B4C0` | node + property-name + out value in generated getters | `IXMLNode.GetAttribute(AttrName)`-style value getter | Medium-high |
| `0x0044B4D8` | node + out interface; returned list receives `FindNode("constraints")` | `IXMLNode.ChildNodes` getter | High |
| `0x0044B508` | ForceSinglePageFiles key + context/default arguments, then Boolean conversion | unresolved specialized getter/default wrapper | Open |

Why the distinction matters: the numeric accessors test HasAttribute, obtain AttributeNodes, find the named attribute node, and read its value. The string-property setter traces similarly obtain the attribute-node list and find the named node before operating on its value. By contrast, the Get_ColorDepth path obtains ChildNodes and resolves the nested `constraints` element. Embarcadero explicitly documents AttributeNodes as an IXMLNodeList of attribute nodes and notes that attributes are not child nodes; this matches the separate helper addresses and call paths.

The 0x0044B4C0 identification as GetAttribute is based on generated getters passing the literal property key and an output-value slot; it should remain medium-high rather than absolute until the helper body is directly disassembled. No direct SetAttribute helper is proven in this range: the observed setter paths navigate AttributeNodes.FindNode(name) and operate on the returned attribute node.

References:
- [IXMLNode.AttributeNodes](https://docwiki.embarcadero.com/Libraries/Alexandria/en/Xml.XMLIntf.IXMLNode.AttributeNodes)
- [IXMLNode.HasAttribute](https://docwiki.embarcadero.com/Libraries/Alexandria/en/Xml.XMLIntf.IXMLNode.HasAttribute)
- [IXMLNode.GetAttribute](https://docwiki.embarcadero.com/Libraries/Athens/en/Xml.XMLIntf.IXMLNode.GetAttribute)
- [IXMLNode.ChildNodes](https://docwiki.embarcadero.com/Libraries/Alexandria/en/Xml.XMLIntf.IXMLNode.ChildNodes)
- [IXMLNodeList.FindNode](https://docwiki.embarcadero.com/Libraries/Athens/en/Xml.XMLIntf.IXMLNodeList.FindNode)


## Run 51 — exact ColorDepth selector mapping

The successful deep scanner artifact from run `46146595651` (artifact `15263439921`) contains complete callsite traces for `TScanCommand.VerifyConstraints` at `0x004F2C4C` and `TScanCommand.Finalization` at `0x004F32F4`. Cross-reading both directions closes the internal selector mapping:

| `colorDepth` numeric selector | Internal byte at `TScanCommand+0x08` | Finalization label |
|---:|---:|---|
| 1 | `1` | `سياه/سفيد` (black/white) |
| 4 | `4` | `طيف سياه و سفيد` (grayscale) |
| 8 | `8` | `طيف سياه و سفيد يا 256 رنگ` (grayscale or 256 colours) |
| 24 | `0x18` | `رنگي 24 بيت` (24-bit colour) |

Evidence chain:

- `VerifyConstraints` reads the XML constraint value and writes exactly `1`, `4`, `8`, or `0x18` to byte offset `+0x08`; the unmatched/default branch writes zero (`0x004F2F34–0x004F2F67`).
- `Finalization` reads that same byte and maps the four values back to the four string globals at `0x00628260`, `0x00628264`, `0x00628268`, and `0x0062826C` (`0x004F334A–0x004F33B2`).
- The selector is therefore a numeric value, not an ordinal 0–3 enum. Preserve the exact values 1/4/8/24. Do not normalize them to 0/1/2/3.
- Zero is the no-match/default representation in this code path; it is not one of the four supported colour labels. Do not silently treat it as a valid colour depth.

The four contiguous option values begin at `TScanCommand+0x08`: colour selector byte at `+0x08`, minimum resolution at `+0x0C`, maximum resolution at `+0x10`, and maximum file size at `+0x14`. `VerifyConstraints` stores the latter three values at those exact offsets. This agrees with the previously recovered KiB conversion for MaxFileSize and the constraint property names.

`FHasConstraints` at `+0x38` is computed by summing the colour byte and the three numeric option values and testing whether the sum is positive. This is the literal implementation; do not replace it with a guessed null/empty policy without checking signed-value behavior and upstream validation.

This is static callsite evidence, not a live scanner capture. It closes the numeric selector mapping but does not prove the physical scanner driver's accepted modes, bit-depth behavior, or SANE backend equivalence.
