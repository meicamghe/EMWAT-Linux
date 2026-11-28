# XMLRTL helper and schema-access crosswalk — 2026-11-28

## Scope

Run 30 reconciles the generated scanner XML accessors by machine-level argument flow rather than TD32 procedure labels. Several TD32 names are demonstrably stale or shifted; do not infer getter/setter direction from the symbol alone.

Evidence: scanner artifacts `15253432241`, `15253908265`, `15252222043`; procedures `0x004EA94C`, `0x004EAA08`, `0x004EAAD8`, `0x004EAB58`, `0x004EAC2C`, `0x004EACB0`, `0x004EAD84`, `0x004EAE08`, and `0x004EA760`.

## Confirmed XMLRTL helper identities

| Helper VA | Identity | Machine-level evidence |
|---|---|---|
| `0x0044B498` | `IXMLNode.HasAttribute` wrapper | Called with node + attribute name; AL is tested as Boolean before the read path |
| `0x0044B488` | `IXMLNode.GetAttribute` wrapper | Called only after HasAttribute succeeds; returns a Variant used by the typed conversion path |
| `0x0044B4C0` | `IXMLNode.SetAttribute` wrapper | Called with node, attribute name and the converted value in the setter-shaped path; matches the XMLRTL SetAttribute contract |

These identities match the public `Xml.XMLIntf.IXMLNode` contracts: HasAttribute tests for an attribute, GetAttribute reads an OleVariant, and SetAttribute writes an OleVariant. References: [HasAttribute](https://docwiki.embarcadero.com/Libraries/Alexandria/en/Xml.XMLIntf.IXMLNode.HasAttribute), [GetAttribute](https://docwiki.embarcadero.com/Libraries/Athens/en/Xml.XMLIntf.IXMLNode.GetAttribute), [SetAttribute](https://docwiki.embarcadero.com/Libraries/Athens/en/Xml.XMLIntf.IXMLNode.SetAttribute).

`0x0044B4D8` is the child-node navigation path, not a plain attribute getter: the call obtains a child-node collection/interface, then the caller looks up the named child `constraints` through the returned list interface (slot `+0x10`). This is consistent with `IXMLNode.ChildNodes` and `IXMLNodeList` name/index access. The exact low-level thunk split between the property getter and list lookup remains to be verified from the helper body.

`0x0044B508` remains a separate output-property helper used by `Get_ForceSinglePageFiles`; its default/variant conversion semantics are not yet proven. Do not treat the zero stack argument as proof of the absent-attribute default.

## Corrected property direction and names

- `0x004EA94C` contains the literal `constraints` and follows the ChildNodes/list lookup path. Despite its TD32 label `TXMLConstraintsType.Get_ColorDepth`, its body is the root `Constraints` child navigation accessor.
- `0x004EAA08` reads the `colorDepth` attribute: HasAttribute → GetAttribute → Variant/integer conversion. Despite its TD32 `Set_ColorDepth` label, the body is a getter.
- `0x004EAB58` reads `minResolution` using the same HasAttribute/GetAttribute/conversion pattern; its TD32 `Set_MinResolution` label is misleading.
- `0x004EACB0` reads `maxResolution` using the same pattern; its TD32 `Set_MaxResolution` label is misleading.
- `0x004EAE08` reads `maxFileSize` using the same pattern; its TD32 `Set_MaxFileSize` label is misleading.
- `0x004EAAD8`, `0x004EAC2C`, and `0x004EAD84` use the `minResolution`, `maxResolution`, and `maxFileSize` names in a value-in/name-out call pattern to `0x0044B4C0`, matching SetAttribute rather than a getter. Their TD32 `Get_*` labels are misleading.

## Numeric absent-value behavior

The four numeric getter bodies (`0x004EAA08`, `0x004EAB58`, `0x004EACB0`, `0x004EAE08`) explicitly branch on HasAttribute. If absent, their zero-initialized result is returned without GetAttribute or conversion. If present, GetAttribute is read and converted to integer; empty or malformed values are not silently defaulted to zero.

`MaxFileSize` remains KiB (`<< 10`) before comparison with `TStream.Size` bytes.

## Remaining XMLRTL gates

1. Disassemble the bodies at `0x0044B488`, `0x0044B498`, `0x0044B4C0`, `0x0044B4D8`, and `0x0044B508` directly to close exact thunk-to-IXMLNode vtable dispatch and exception/Variant ownership.
2. Resolve the `ForceSinglePageFiles` default and its XML attribute string.
3. Recover the complete root and output schema and runtime XML examples; do not serialize based on names alone.
4. Map the `none`, `jpg`, `yes`, and `no` literals to their exact properties only after tracing each branch to its originating getter.