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

The routine reads Word document-side state and iterates multiple viewer collections, including members at offsets +0x8C, +0x90, +0x94, +0x98, and +0x9C. It also accesses the current Word document interface at viewer offset +0x48 and calls the shared field lookup helper 0x004BFDB0.

This establishes that recipient/CC option handling is coupled to document field lookup and several internal collections. It does not establish the exact UI text, how each collection maps to To/CC, or whether the routine changes the returned document bytes.

## 3. FindWindowExtd in image-field processing

0x0045644C is identified as FindWindowExtd. The artifact shows one direct call from TWordViwer.FillImageField at 0x004BC38F. The routine tokenizes a supplied string around path-like separators and searches the resulting components through collection lookups. The exact source string and semantic target window are not yet established.

Do not treat this helper as an image codec or as proof of a particular UI-window protocol. Its placement in FillImageField makes it a relevant dependency to trace before implementing image placeholder selection.

## 4. Linux implementation implications

1. Preserve custom document property names and values as a separate Writer target category. The existing Writer inspector intentionally inventories names only; do not read values during diagnostics.
2. Keep Field.Result.Text and CustomDocumentProperties as distinct Writer target adapters. The earlier FillImageField trace established both destinations can occur; this artifact confirms dictionary helper use but does not yet supply a complete field-to-destination predicate.
3. Parse the U+2020 Twin Field identifier while retaining the original raw ID. The decoder now exposes the parsed pair without inventing a mapping to Writer elements.
4. Keep recipient/CC option processing separate from ordinary text/image substitution. The ShowRecAndCcOptionForm call path is a distinct concern and should not be collapsed into a generic field setter.
5. Keep FindWindowExtd unresolved behind a compatibility boundary until its input string and target object are traced.

## 5. Evidence and confidence

- Confirmed: helper identities and direct callsites listed above; ShowRecAndCcOptionForm is called by GetDocFieldName; FindWindowExtd is called by FillImageField.
- Not confirmed: full semantics of recipient/CC collections; the exact field names consumed by FindWindowExtd; universal mapping of EMWAT IDs to custom properties or Field.Result.Text; exact close-time POST/response registration path.
- Artifact: emwat-word-custom-property-pipeline, workflow run 43812565648, artifact ID 14200962076.

## 6. Next parallel targets

- Trace 0x004BFDB0 and its callers to classify the field lookup contract used by both standard field processing and recipient/CC handling.
- Trace the writer side of TDocumentCProperty construction and the callsites that populate the dictionary, not just its generic collection helpers.
- Resolve the Hidden_Customizable special field branch in GetDocFieldName and connect it to request wordConfig metadata.
- Continue close/registration tracing independently; no HTTP behavior should be inferred from these document-field helpers.
