# Scanner XML root and constraint property names — 2026-11-28

## Evidence

- Workflow: `EMWAT scanner XML root and property string closure`
- Run: `46120998177`
- Artifact: `15253432241`
- Procedures: `NewScanDocument` (`0x004E9D5C`), `LoadRequestXML` (`0x004F2B18`), `VerifyConstraints` (`0x004F2C4C`), and `TXMLConstraintsType` property accessors.

## XML names recovered

The inline UTF-16 strings and their use sites establish:

- Document root: `scan-document` (string at `0x004E9DE4`, passed by `NewScanDocument` to XML interface slot `+0x8C`).
- Constraints child/object name: `constraints` (string at `0x004EA9C7`).
- Constraint properties:
  - `colorDepth`
  - `minResolution`
  - `maxResolution`
  - `maxFileSize`
- Error property: `error` (string at `0x004F2BF8`).
- Error prefix: `<ScanDoc HasError>. ErrorXML: ` (string at `0x004F2C0C`).

The property names appear in both getter/setter-related code paths. The XML property `maxFileSize` is the value already confirmed as KiB (1024-byte units); resolution values are normalized by the GearType path described in `docs/SCANNER-RESOLUTION-AND-FILESIZE-UNITS-2026-11-28.md`.

## Important distinction

`scan-document` is the document root passed into the XML creation interface. The string `constraints` is the constraints object/property name used by the constraint type. Do not infer unobserved attributes, namespace URIs, XML declaration/version, or default values from these strings alone.

## Remaining XML contract work

1. Confirm the XML interface slot `+0x8C` operation name and whether it creates a root element or binds a document node.
2. Trace `LoadRequestXML` field-by-field to establish required/optional fields and defaults.
3. Determine whether `colorDepth` accepts only the four selector values already observed (1, 4, 8, 24) or has string aliases.
4. Confirm serialization order and exact handling of absent/empty constraints.
