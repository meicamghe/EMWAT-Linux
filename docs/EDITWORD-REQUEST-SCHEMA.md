# EditWordDocument request configuration schema

Date: 2026-11-15  
Source: workflow `analyze-editword-request-params.yml`, run #3 (`43711758572`), artifact `14161075867`  
Input: captured `POST /?invoke=58351` request  
Privacy: this report records XML structure and field identifiers only. It deliberately excludes field contents and receiver/signatory values.

## 1. Outer method parameters

The captured XML method is `EditWordDocument` and includes these parameters:

- `wordConfig`: Base64 text; 13,668 encoded characters, decoding to 10,250 bytes of XML.
- `wordBody`: Base64 text; 1,163,948 encoded characters, decoding to 872,960 bytes of OLE Compound File / legacy DOC data.
- `signData`: empty in this particular capture.

The `wordConfig` decoded root is `<word-document status="edit">`.

## 2. Document permissions and settings

The observed `permission` element has:

| Attribute | Captured value |
|---|---|
| `allowCopy` | `true` |
| `allowPrint` | `false` |
| `allowSave` | `true` |

A `settings/setting` entry named `gam-print-dialog` is present. Its value is intentionally not reproduced here.

These are values from one captured request, not universal defaults for all Almas letters.

## 3. Field collection

The `fields` element contains 180 `field` entries in this capture.

### Main metadata fields

The base field set includes these identifiers (names only; captured values are omitted):

- Letter relationships and content: `RelatedLetters`, `LetterDescription`, `LetterSubject`, `Appendix`, `HasAppendix`, `Version`, `letterId`.
- Producer/sender: `LetterProducerName`, `LetterProducerDep`, `LetterProducerDepPhoneNumber`, `LetterProducerPhoneNumber`, `LetterProducerUnit`, `LetterProducerUnitCode`, `LetterSenderName`, `LetterSenderDep`, `LetterSenderAddress`, `LetterSenderUnit`, `LetterSenderUnitCode`, `LetterSenderIndexUnit`.
- Registration/classification: `ProduceDate`, `LetterRegistrationNo`, `LetterRegistrationDate`, `LetterRegistrationTime`, `Classification`, `TransferType`, `DocType`, `Priority`.
- Recipients: `Receivers`, `ReceiverDeps`, `ReceiverCeremonialUnits`, `ccReceivers`, `ccReceiverDeps`, `ccReceiverCeremonialUnits`.
- Sender/signature and visual assets: `SenderSignerBehalfName`, `SignNumberOfSender`, `SignOfSenderStart†SignOfSenderEnd`, `ShamsQRcodeStart†ShamsQRcodeEnd`, `shamsBarcode`, `Slogan`.

### Repeated signer slots

The capture defines 20 indexed slots (0–19) for each of these seven field families:

- `LetterSignerDep{n}`
- `LetterSignerPer{n}`
- `LetterSignerUnit{n}`
- `LetterSignerIndexUnit{n}`
- `SignNumberOfSigner{n}`
- `BehalfNameOfSigner{n}`
- `SignOfSignerStart{n}†SignOfSignerEnd{n}`

This repeated structure accounts for 140 fields. The remaining 40 fields are the base metadata/assets listed above.

## 4. Encoding and external parameter references

Observed encoding attributes include:

- `encryption="urlencoded"` on fields such as `RelatedLetters`, `LetterSubject`, `Receivers`, `ReceiverDeps`, and CC receiver fields.
- `encryption="base64"` with `mimetype="image/*"` on signature/QR/barcode image placeholders.
- A field `SignsStart†SignsEnd` declares `paramId="signData"`, `separator="&"`, `concater="\\n"`, `encryption="base64"`, and `mimetype="image/*"`.

The `optional-attributes` section contains `attribute id="tokenizedReceivers" type="compInfo"` with a nested `content encryption="urlencoded"` node. Its content is not copied into this document.

The `requested-types` section asks for `mimetype="application/msword"`.

## 5. Implications for the Linux implementation

1. Keep `wordConfig` parsing separate from the outer method envelope. It is a second XML document carried as Base64 text.
2. Preserve unknown field IDs and attributes; the 180-field sample is not a complete schema guarantee.
3. Treat each field's `encryption`, `mimetype`, `paramId`, `separator`, and `concater` attributes as per-field transformation metadata. Do not globally URL-decode or Base64-decode every field.
4. Model signer arrays with indexed slots, but preserve original IDs and order when serializing.
5. Keep document bytes opaque until the office-engine adapter has loaded/saved them. The captured `wordBody` is legacy DOC/CFB, not OOXML ZIP.
6. Respect per-request permissions such as `allowPrint`; do not hard-code the captured permission values as global defaults.
7. Do not log field values, `tokenizedReceivers`, signature data, or document contents.

## 6. Reproducibility

- Workflow: `.github/workflows/analyze-editword-request-params.yml`
- Run: `43711758572`
- Artifact: `14161075867`
- Reported `wordConfig` decoded size: 10,250 bytes.
- Reported `wordBody` decoded size: 872,960 bytes.
