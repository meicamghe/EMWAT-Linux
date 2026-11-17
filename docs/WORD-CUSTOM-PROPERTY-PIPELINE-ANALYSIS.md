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

SetFieldValue compares the field's encryption metadata against two decoded constants: 0x004BFEE8 is urlencoded and 0x004BFF0C is base64. The urlencoded branch transforms the input through a URL-decoding helper before returning the result; the base64 branch uses a separate binary-decoding path; unknown/other labels follow the untransformed path in this routine. Its callers include GetDocFieldIndex, GetCaptionItemFont, and ShowRecAndCcOptionForm. This confirms the two encoding labels implemented by python/src/emwat_linux/word_fields.py. The native URL decoder's plus behavior is now confirmed by the constant at 0x00455454: a literal + becomes a space, while %2B decodes to a literal plus. Python now uses unquote_plus and tests both cases.

FindFieldInActivefields is called repeatedly by GetXmlFieldInfo and from the TWordViwer constructor path at 0x004D08B4. Its implementation first looks for the literal DOCPROPERTY token (0x004BC23C), then parses the field-code text around a two-space separator (0x004BC260) and a single-space separator (0x004BC274) before checking the active-field list. This is evidence that the Word side distinguishes DOCPROPERTY fields from other field codes; the Linux Writer adapter should keep DocInfo.Custom/DOCPROPERTY-like fields separate from ordinary text and bookmarks.

The routine at `0x004D1148` was initially attributed to `AddXmlWordConfigFieldsToDic` from its TD32 label and embedded diagnostics. Stronger class metadata now reclassifies it as `TWordViwer.Destroy`: the `TWordViwer` VMT candidate at `0x004B10A4` has its Delphi `vmtDestroy` slot at `VMT-0x04` (`0x004B10A0`) pointing to `0x004D1148`, and the associated RTTI method record at `0x004B1629` names that entry `Destroy`. Its body frees the viewer-owned dictionaries/collections at `+0x64/+0x68/+0x6C`, releases other viewer resources, calls `TWordApplication.ScreenRefresh`, and emits stale `AddXmlWordConfigFieldsToDic` diagnostics. The TD32 label and log strings must not override the VMT/RTTI identity.

`LoadDocument` calls the initialization-like routine at `0x004D0D24` (`0x004B78E9`), whose body allocates the three dictionary objects at viewer offsets `+0x64`, `+0x68`, and `+0x6C` (constructor helpers at `0x004D4670`, `0x004D5C28`, and `0x004D71E0`). This establishes allocation and destruction, but not how the single/twin descriptor dictionaries are initially populated. The routine at `0x004D1454` is `TWordViwer.AddCustomDocPropertiesToDic` and is called directly from `LoadDocument` at `0x004B7994`. It enumerates Word's `CustomDocumentProperties`, splits names on the first `†` (U+2020), constructs single/twin descriptor-shaped records, and removes matching keys from the pre-existing descriptor maps at `viewer+0x68` or `viewer+0x6C`. It is a reconciliation/consumption pass, not map population.

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

- Confirmed: SetFieldValue encoding labels urlencoded/base64; FindFieldInActivefields recognizes DOCPROPERTY field codes; `0x004D1148` is the `TWordViwer.Destroy` VMT slot despite stale TD32/log labels that say `AddXmlWordConfigFieldsToDic`; the viewer initializer at `0x004D0D24` allocates the `+0x64/+0x68/+0x6C` dictionaries; `AddCustomDocPropertiesToDic` at `0x004D1454` enumerates `CustomDocumentProperties`, splits names at U+2020, builds single/twin descriptor-shaped records, and removes matching keys from the pre-existing descriptor maps. Hidden_Customizable is the special GetDocFieldName field; ShowRecAndCcOptionForm is called by GetDocFieldName; FindWindowExtd is called by FillImageField.
- Not confirmed: full semantics of recipient/CC collections; the exact field names consumed by FindWindowExtd; universal mapping of EMWAT IDs to custom properties or Field.Result.Text; exact close-time POST/response registration path.
- Artifact: emwat-word-custom-property-pipeline, workflow run 43812565648, artifact ID 14200962076.

## 8. Next parallel targets

- Finish tracing the base64 byte-to-Unicode conversion helper at 0x004738CC and decide how the native text-field branch differs from the separate image-field byte path.
- Resolve initial population of the single/twin descriptor maps. The next trace batch inspects the dictionary constructor helpers called by the viewer initializer (`0x004D5C28`, `0x004D71E0`), enumerable-constructor method-table references, and AddOrSetValue callsites; `CrateOptionFormFields` (`0x004CFC74`) has been rejected as unrelated to descriptor-map population.
- Trace the writer-side TDocumentCProperty construction and the custom-property dictionary insertion path, not just generic collection helpers.
- Resolve the Hidden_Customizable special-field branch in GetDocFieldName and connect it to request wordConfig metadata.
- Continue close/registration tracing independently; no HTTP behavior should be inferred from these document-field helpers.
