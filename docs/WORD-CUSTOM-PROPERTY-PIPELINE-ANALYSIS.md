# Word Custom Document Properties and field helper analysis

Date: 2026-11-16  
Source: EMWAT BPL1 reverse-engineering artifact from workflow run 43812565648 (artifact 14200962076).  
Scope: procedure traces and direct-call sites only; no customer letter values are reproduced.

## 1. Confirmed helper identities

The artifact resolves two generic dictionary helpers used by the Word field pipeline:

- 0x004D3DF8: TDictionary<UnicodeString,TDocumentCProperty>.ContainsValue.
- 0x004D34B0: TDictionary<UnicodeString,TDocumentCProperty>.SetItem helper.

The first helper is called from TWordViwer.FillImageField and from multiple branches in FillPrintDocFields. The second is called from FillImageField and FillPrintDocFields, where the returned record/item is subsequently dereferenced. These are implementation-level dictionary operations; they do not reveal a universal rule that every EMWAT field maps to a custom property.

## 2. Recipient/CC option helper

TD32 identifies 0x004D1B30 as TWordViwer.ShowRecAndCcOptionForm. Its only direct bounded caller in the artifact is TWordViwer.GetDocFieldName at 0x004BBA51.

The routine reads Word document-side state and iterates multiple viewer collections, including members at offsets +0x8C, +0x90, +0x94, +0x98, and +0x9C. It also accesses the current Word document interface at viewer offset +0x48 and calls 0x004BFDB0, which the TD32 symbol index identifies as TWordViwer.SetFieldValue—not as the active-field lookup routine.

This establishes that recipient/CC option handling is coupled to document field lookup and several internal collections. It does not establish the exact UI text, how each collection maps to To/CC, or whether the routine changes the returned document bytes.

## 3. Separate field lookup and value-setting helpers

The expanded TD32 symbol index resolves two distinct helpers:

- 0x004BFDB0: TWordViwer.SetFieldValue(TXmlWordConfigField, UnicodeString).
- 0x004BC170: TWordViwer.FindFieldInActivefields(UnicodeString).

SetFieldValue compares the field's encryption metadata against two decoded constants: 0x004BFEE8 is urlencoded and 0x004BFF0C is base64. The urlencoded branch transforms the input through a URL-decoding helper before returning the result; the base64 branch uses a separate binary-decoding path; unknown/other labels follow the untransformed path in this routine. Its callers include GetDocFieldIndex, GetCaptionItemFont, and ShowRecAndCcOptionForm. This confirms the two encoding labels implemented by python/src/emwat_linux/word_fields.py. The exact plus-sign behavior of the native URL decoder remains to be checked before claiming byte-for-byte parity.

FindFieldInActivefields is called repeatedly by GetXmlFieldInfo and from the TWordViwer constructor path at 0x004D08B4. Its implementation first looks for the literal DOCPROPERTY token (0x004BC23C), then parses the field-code text around a two-space separator (0x004BC260) and a single-space separator (0x004BC274) before checking the active-field list. This is evidence that the Word side distinguishes DOCPROPERTY fields from other field codes; the Linux Writer adapter should keep DocInfo.Custom/DOCPROPERTY-like fields separate from ordinary text and bookmarks.

The request-field dictionary routine at 0x004D1148 is named AddXmlWordConfigFieldsToDic; its embedded diagnostics confirm both entry and successful completion. It resets multiple field/config collections, enumerates the XML field collection, and uses the dagger delimiter at 0x004D1768 to split twin identifiers. The custom-property population routine at 0x004D1454 is named AddCustomDocPropertiesToDic and has a direct call from LoadDocument at 0x004B7994. It enumerates Word's CustomDocumentProperties collection, reads each property name, splits names containing the dagger delimiter into two non-empty parts, constructs TDocumentCProperty records, and updates the associated dictionaries. The bounded direct-call scan found no direct CALL xref for AddXmlWordConfigFieldsToDic, so its invocation path still requires an indirect/VMT trace.

## 4. Hidden_Customizable special field

The string at 0x004BBEE8 is now decoded as Hidden_Customizable. GetDocFieldName compares the requested field name against this exact value and conditionally calls SilentSaveEmwatDoc at 0x004D23D8 before continuing field extraction. This is a field-lookup-triggered special path, not evidence that SilentSaveEmwatDoc is itself the Word BeforeClose callback or the HTTP response writer.

## 5. FindWindowExtd in image-field processing

0x0045644C is identified as FindWindowExtd. The artifact shows one direct call from TWordViwer.FillImageField at 0x004BC38F. The routine tokenizes a supplied string around path-like separators and searches the resulting components through collection lookups. The exact source string and semantic target window are not yet established.

Do not treat this helper as an image codec or as proof of a particular UI-window protocol. Its placement in FillImageField makes it a relevant dependency to trace before implementing image placeholder selection.

## 6. Linux implementation implications

1. Preserve custom document property names and values as a separate Writer target category. The existing Writer inspector intentionally inventories names only; do not read values during diagnostics.
2. Keep Field.Result.Text and CustomDocumentProperties as distinct Writer target adapters. The earlier FillImageField trace established both destinations can occur; this artifact confirms dictionary helper use but does not yet supply a complete field-to-destination predicate.
3. Parse the U+2020 Twin Field identifier while retaining the original raw ID. The decoder now exposes the parsed pair without inventing a mapping to Writer elements.
4. Keep recipient/CC option processing separate from ordinary text/image substitution. The ShowRecAndCcOptionForm call path is a distinct concern and should not be collapsed into a generic field setter.
5. Keep FindWindowExtd unresolved behind a compatibility boundary until its input string and target object are traced.

## 7. Evidence and confidence

- Confirmed: SetFieldValue encoding labels urlencoded/base64; FindFieldInActivefields recognizes DOCPROPERTY field codes; AddXmlWordConfigFieldsToDic logs entry/success and splits Twin IDs on U+2020; AddCustomDocPropertiesToDic enumerates CustomDocumentProperties and splits twin names; Hidden_Customizable is the special GetDocFieldName field; ShowRecAndCcOptionForm is called by GetDocFieldName; FindWindowExtd is called by FillImageField.
- Not confirmed: full semantics of recipient/CC collections; the exact field names consumed by FindWindowExtd; universal mapping of EMWAT IDs to custom properties or Field.Result.Text; exact close-time POST/response registration path.
- Artifact: emwat-word-custom-property-pipeline, workflow run 43812565648, artifact ID 14200962076.

## 8. Next parallel targets

- Trace native URL decoding helper 0x00455314 for plus-sign and malformed-escape behavior, and trace the base64 helper path for binary/empty-value behavior.
- Resolve the indirect/VMT invocation path of AddXmlWordConfigFieldsToDic and determine whether it is invoked before or after AddCustomDocPropertiesToDic.
- Trace the writer-side TDocumentCProperty construction and the custom-property dictionary insertion path, not just generic collection helpers.
- Resolve the Hidden_Customizable special-field branch in GetDocFieldName and connect it to request wordConfig metadata.
- Continue close/registration tracing independently; no HTTP behavior should be inferred from these document-field helpers.
