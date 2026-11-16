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
4. Parse the observed U+2020 dagger delimiter into an optional two-part Twin Field identifier while preserving the original raw ID and field order. Empty-side identifiers remain single IDs, matching the observed native branch.
5. Model signer arrays with indexed slots, but preserve original IDs and order when serializing.
6. Keep document bytes opaque until the office-engine adapter has loaded/saved them. The captured `wordBody` is legacy DOC/CFB, not OOXML ZIP.
7. Respect per-request permissions such as `allowPrint`; do not hard-code the captured permission values as global defaults.
8. Do not log field values, `tokenizedReceivers`, signature data, or document contents.

## 6. Reproducibility

- Workflow: `.github/workflows/analyze-editword-request-params.yml`
- Run: `43711758572`
- Artifact: `14161075867`
- Reported `wordConfig` decoded size: 10,250 bytes.
- Reported `wordBody` decoded size: 872,960 bytes.


## 7. Twin-field identifier convention

The Word field-processing disassembly confirms that the Unicode character `†` (U+2020 DAGGER) is a structural separator in field/property identifiers:

- A name with two non-empty sides, such as `SignOfSenderStart†SignOfSenderEnd`, is represented internally as a `TXmlWordConfigTwinField`.
- The first dagger is the split point; the right side retains any later dagger characters.
- Names without the delimiter, or with an empty left/right side, follow the single-field path (`TXmlWordConfigField`).
- This identifier delimiter is distinct from the `separator="&"` and `concater="\\n"` attributes on the external `signData` parameter. It does not establish the concatenation semantics of signData.
- Python helper: `parse_word_field_identifier`; tests cover single, twin, multiple delimiters, and empty-side fallbacks.


> **Binary parser spelling note (2026-11-16):** The native `TXMLFieldType.Set_Concator` method reads the XML attribute key `concator` (not `concater`) via `TXMLNode.GetAttributeNodes`. The currently transcribed capture line above uses `concater`. No alias is proven; preserve the raw spelling and verify against the original request before normalizing. The Python parser currently preserves both as raw attributes and does not interpret either.


## Invoke request parser trace — 2026-11-16

Source: workflow 43832144163, artifact 14209690263.

- TMainForm.IdHTTPServerCommandGet (0x0047BF30) routes the invoke query branch through ParseMethod wrapper 0x00470D00.
- 0x00470D00 calls parser worker 0x00470B38 and contains exception text references for "Calling ParseMethod exception" and "XML is not valid".
- The parser recognizes root tag "emwat", its "version" attribute, and child tags "method", "class", and "param"; the "param" child uses the "name" attribute.
- Parser token helper 0x0046ADBC compares the token names and routes recognized elements. Helper 0x0046A7A4 appends a three-value record to the parser's dynamic collection (three adjacent string/value slots); exact semantic names for all three record fields remain unconfirmed.
- This is the service-side XML parsing stage. The full service analysis in `docs/EMWAT-SERVICE-EXECUTABLE-ANALYSIS.md` resolves the next steps: the parser fills `TMethodInfo.ClassName` and its `Params` dictionary; the dispatcher prefixes the class name with `T`, calls `System.Classes.GetClass`, constructs the class instance, and invokes VMT slot `+0x0C`. The exact response payload remains open.


## BPL class hierarchy and Invoke contract — 2026-11-16

Source: workflow 43832553168, artifact 14208369288.

- TD32 identifies TEmwatMethod.Invoke at 0x0046C82C with parameter type TDictionary<AnsiString,AnsiString>.
- The Delphi VMT/interface scan resolves TEmwatMethod VMT method-table base at 0x0046ABFC. TEditWordDocument VMT is 0x005ED764 and its parent pointer resolves to the TEmwatMethod VMT header start (0x0046ABA4 = 0x0046ABFC - 0x58). This establishes TEditWordDocument inherits TEmwatMethod.
- TScanDocument, TFaxDocument, TGetEmwatVersion, TSetEmwatVersion, TUpgradeEmwat, TImageEdition, TEditExcelWorkBook, and TCompareWordDocument also point to the same TEmwatMethod parent header.
- The public virtual `TEmwatMethod.Invoke` wrapper is at `0x0046C9E0` (VMT slot `+0x0C`; TD32 misleadingly labels it `Finalization`). It calls the inner dictionary/XML helper at `0x0046C82C`, then dispatches the concrete subclass through VMT slot `+0x10` (callsite `0x0046CA88`).
- The inner helper `0x0046C82C` walks the dictionary's key/value pairs and builds XML parameter nodes; it is not itself the subclass dispatcher. Its XML node builder uses `TXMLEmwatType`, `TXMLMethodType`, and `TXMLParamType`.
- `TEmwatMethod` VMT slot `+0x10` is the abstract/error stub `0x00401068`; the concrete subclasses override this slot.
- `TEditWordDocument` VMT slot `+0x10` points to `0x005EE82C`; TD32 decorates this routine as `TScanDocument.PerformMethod`. `TScanDocument` VMT slot `+0x10` points to `0x005EEB48`, TD32 decorates it as `TFaxDocument.PerformMethod`. Preserve these VMT-owner/TD32-name discrepancies.
- The service-side `GetClass("T"+className)` and VMT `+0x0C` invocation path are now confirmed; the remaining unknown is the exact response serialization and how the method result/Word archive is returned to the browser.


## Service parser confirmation — version 1

The latest PE-only trace independently confirms the outer request envelope:
- root element: `emwat`;
- root attribute: `version`;
- accepted numeric value: exactly `1`;
- child element: `method`;
- method attribute: `class`;
- child elements: `param`;
- parameter attribute: `name`.

Evidence: `EmwatService.exe` addresses `0x00470A58`, `0x00470B38`, constants `0x00470B1C` (`emwat`), `0x00470B30` (`version`), `0x00470CBC` (`method`), `0x00470CD0` (`class`), `0x00470CE4` (`param`), and `0x00470CF8` (`name`); artifact `14227870162`.

The parser's three-field internal record is still not fully semantically named, and the class string has not yet been connected to the concrete BPL VMT call.


## EditWordDocument.PerformMethod parameter contract — confirmed

The concrete `TEditWordDocument.PerformMethod` at `0x005EE82C` reads these dictionary keys:

| Key | Observed behavior |
|---|---|
| `wordConfig` | Required; converted to a string and passed to `TWordViwer.LoadDocument` as the XML configuration. Missing value raises `Requset XML is not valid (wordConfig parameter is null)`. |
| `wordBody` | Converted to a string and passed to `LoadDocument`; `LoadDocument` extracts `DocFileName`, creates a local file with `TFileStream(fmCreate)`, and writes the document data. |
| `letterImages` | Retrieved and forwarded to `LoadDocument`; exact type and full use still open. |
| `signData` | Retrieved and forwarded to `LoadDocument`; exact type and full use still open. |

`PerformMethod` calls `CoInitialize`, invokes `LoadDocument` with these four values plus the `TEmwatInvokeParam` pointer and an output string, copies the returned string to the inherited method result, then calls `CoUninitialize`. It sets `bUnloadPkg` after the helper returns; **it does not set `bResultSet` itself**.

The non-empty-result branch inside `LoadDocument` is the component that handles the HTTP response: it obtains `AResponseInfo` from `TEmwatInvokeParam` offset `+0x0C`, assigns the generated XML string to `ContentText` (`+0xBC`), calls `TIdHTTPResponseInfo.WriteContent` through BPL import thunk `0x0040448C`, and then sets `bResultSet` at record offset `+0x05`. The service dispatcher consequently skips its fallback response branch for this successful path.

`LoadDocument` calls `OnTmrAutoSave` with the local document path. The timer routine stores that path in `TWordViwer+0xA0`; `OnControlerNotify` later uses it as the source file for the `.easd` member in the password-protected `.easz` archive. This archive path is a separate static finding and is not, by itself, proof that the close-time Almas registration/commit is complete. See `docs/EMWAT-SERVICE-EXECUTABLE-ANALYSIS.md` and `docs/WORD-LIFECYCLE-STATIC-TRACE.md`.
