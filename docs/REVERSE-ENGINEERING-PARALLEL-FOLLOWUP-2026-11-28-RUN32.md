# Reverse-engineering parallel follow-up — 2026-11-28 Run 32

## Scope

Recheck the XMLRTL helper identity claims against all available generated scanner accessor callsites. This run corrects the over-broad Run 30 assignment of AttributeNodes/ChildNodes/GetAttribute helpers.

## Corrected helper crosswalk

| Address | Call shape in generated code | Best-supported role | Confidence |
|---|---|---|---|
| 0x0044B498 | IXMLNode + property-name; Boolean returned in AL | IXMLNode.HasAttribute(Name) | High |
| 0x0044B488 | IXMLNode + output interface; returned list is called with FindNode(name) | IXMLNode.AttributeNodes getter | High |
| 0x0044B4C0 | IXMLNode + property-name + output-value slot in generated getters | IXMLNode.GetAttribute(AttrName)-style getter | Medium-high |
| 0x0044B4D8 | IXMLNode + output interface; returned list resolves FindNode("constraints") | IXMLNode.ChildNodes getter | High |
| 0x0044B508 | ForceSinglePageFiles key + context/default arguments, followed by Boolean conversion | specialized getter/default wrapper | Open |

## Evidence

1. Numeric accessors at 0x004EAA08 / 0x004EAB58 / 0x004EACB0 / 0x004EAE08 call HasAttribute, then obtain the list through 0x0044B488, find the named property, and read the value from the returned attribute node. The TD32 method names are not reliable for getter/setter direction.
2. String-property setters such as Set_DriverDialog at 0x004EA1E8 and Set_ForceSinglePageFiles at 0x004EA7A8 also obtain the list through 0x0044B488 and call FindNode with the property name before operating on the returned node's value.
3. Get_ColorDepth at 0x004EA94C instead calls 0x0044B4D8, resolves the literal child name constraints through the returned list, and reads the nested node value. This is the ChildNodes path, distinct from AttributeNodes.
4. Get_DriverDialog and related getters call 0x0044B4C0 with the literal property name and an output-value slot, which matches the IXMLNode.GetAttribute contract. Keep this medium-high until helper implementation bytes are available.

This is consistent with the official XMLRTL contract: AttributeNodes returns an IXMLNodeList of attribute nodes, and attributes are not members of ChildNodes. References:
- https://docwiki.embarcadero.com/Libraries/Alexandria/en/Xml.XMLIntf.IXMLNode.AttributeNodes
- https://docwiki.embarcadero.com/Libraries/Alexandria/en/Xml.XMLIntf.IXMLNode.HasAttribute
- https://docwiki.embarcadero.com/Libraries/Athens/en/Xml.XMLIntf.IXMLNode.GetAttribute
- https://docwiki.embarcadero.com/Libraries/Alexandria/en/Xml.XMLIntf.IXMLNode.ChildNodes
- https://docwiki.embarcadero.com/Libraries/Athens/en/Xml.XMLIntf.IXMLNodeList.FindNode

## Open boundary

The body of 0x0044B508 is still not available. Its zero-valued call argument and subsequent Boolean conversion do not establish whether a missing attribute becomes false, an empty string, a Null Variant, or another fallback. The helper body or a real output XML fixture is required.

No tests or CI were run; no package was built.
