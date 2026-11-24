# EMWAT Word XML image-field and caption pipeline

Date: 2026-11-24  
Source: TD32 procedure traces and GEAR32PD PE import-thunk crosswalk.  
Scope: image values embedded in Word XML fields; separate from the standalone GScan and ImageTools UI.

## 1. Entry path and routing

- `TWordViwer.FillImageField` at `0x004BC30C` is the Word field-level entry.
- `TWordViwer.AddImagesToDoc` at `0x004C0410` checks the XML field MIME type against the literal `image/*`.
- Image MIME entries route through `TWordViwer.GetCaptionItemFont` at `0x004C19C0`.
- `GetCaptionItemFont` calls `GetImageResolution` (`0x004C2DE0`) and `EmbedTextToImage` (`0x004C436C`), then continues through helper calls at `0x004C4DBC` and `0x004C009C` before returning to the field pipeline.

The `0x004C4DBC` helper is now bounded and its caller/branch are mapped below. The method at `0x004C009C` is identified by TD32 as `TWordViwer.FillMSWFields` and accepts a `Word.Fields` interface; its internal COM field-update operations still need mapping. Do not equate the path with a simple `InlineShapes.AddPicture` call.

## 2. Caption metadata and style

`GetCaptionItems` at `0x004C2B20` copies each `TCaptionItem` as an eight-DWORD record and builds caption/font properties from the XML field metadata.

Confirmed style tokens:
- Font family default: `Tahoma`.
- Style flags: `bold`, `italic`, `underline`, `strikeout`.

The helper at `0x004C2DE0`, symbol-named `GetImageResolution`, compares these direction tokens and returns the following numeric values:

| Token | Value |
|---|---:|
| `right` | 1 |
| `center` | 2 |
| `left` | 3 |
| `top` | 4 |
| `middle` | 5 |
| `bottom` | 6 |

These values are more consistent with horizontal/vertical placement or alignment than with a DPI resolution. The function's TD32 symbol name is preserved, but its semantic label remains provisional until the consumer at `0x004C19C0` is fully mapped.

## 3. GEAR32PD resolution helper — `EmbedTextToImage`

Procedure: `0x004C436C` (`ScanRequestXML` module).

The bounded disassembly proves this call sequence:

| Callsite | Thunk | GEAR32PD API | Role |
|---:|---:|---|---|
| `0x004C43C7` | `0x004AFE88` | `IG_load_file` | Load image file and obtain image handle |
| `0x004C43EE` | `0x004AFF08` | `IG_image_resolution_get` | Read resolution/metadata tuple |
| `0x004C44D7` | `0x004AFF10` | `IG_image_resolution_set` | Write normalized tuple; mode argument is 3 |
| `0x004C44E0` | `0x004AFEB8` | `IG_image_delete` | Release loaded image handle |

The function examines a metadata type field. Type values 2 and 4 take separate branches that divide four returned values by different 80-bit extended constants. The normalized tuple is passed to `IG_image_resolution_set`; the exact units and constants still need decoding.

The function returns a calculated output value and updates a viewer-side property. **No text-drawing API is called in this bounded procedure.** Although its symbol is `EmbedTextToImage`, the current trace proves image loading, resolution read/normalization/write, and handle cleanup only. Caption rasterization is not established.

## 4. Word field storage boundary

The broader field pipeline has separate storage routes:
- Word `Field.Result.Text` can receive a field value; the binary logs `field value stored on Field.Result.Text area.`
- `CustomDocumentProperties` is another field storage route, with its own logging.
- A `field locked.` branch is explicitly logged.
- `urlencoded` and `base64` are recognized encodings by `SetFieldValue`; do not infer the image payload encoding from MIME type alone.

Preserve MIME type, payload encoding, caption item metadata, and regular/twin field identity independently in the Linux model.

## 5. Linux compatibility consequences

1. Treat source image bytes, resolution metadata, caption styling, and Word insertion as separate stages.
2. Preserve the original image and record the normalized DPI/dimension tuple rather than destructively overwriting source assets.
3. Implement caption style tokens and the six position tokens as explicit enums; do not name the latter `resolution` in the Linux schema until confirmed.
4. Use a replaceable native image backend. Do not port GEAR32PD DLL calls into Linux or assume ImageEn is the backend for this Word XML path.
5. Keep Word document insertion behind a document-adapter interface so LibreOffice behavior can be validated independently.

## 6. Open questions

1. Decode the two 80-bit extended constants at `0x004C4590` and `0x004C459C` and identify the two metadata-type branches.
2. Resolve the argument contract of `IG_image_resolution_set` mode 3.
3. Identify the pixel-write/save operation and the Boolean meaning of `0x004C4DBC`; map the internal Word COM field-update calls inside `FillMSWFields` (`0x004C009C`).
4. Resolve the consumer semantics of the six position values returned by `GetImageResolution`.
5. Determine the temporary image/file naming and cleanup path for image fields.
6. Validate image field insertion against representative XML fixtures and real Word documents before choosing the native image backend.

## 7. Evidence status

- `AddImagesToDoc` image MIME routing: confirmed.
- Caption font/style tokens: confirmed.
- Six direction tokens and numeric values: confirmed; semantic category provisional.
- GEAR32PD image load/resolution set/delete calls: confirmed.
- Caption rasterization and final Word insertion operation: unresolved.


## 3. Caption composition helper and Word-field fallback

`GetCaptionItemFont` calls the large helper at `0x004C4DBC` from callsite `0x004C2259`. The helper:

- receives the current image/caption data and works with an image-view object stored through global `0x0062F810`;
- creates/uses that view object and reads image dimensions;
- calls `GetCaptionItems` at `0x004C2B20` (callsite `0x004C54B9`);
- uses font/text measurement methods through the view/canvas object VMT (including calls through slots `+0x30`, `+0x14`, and `+0x90`);
- iterates caption entries and calculates horizontal/vertical placement and text extents;
- returns a Boolean to `GetCaptionItemFont`.

The caller then branches:
- If `0x004C4DBC` returns true, it takes the handled/cleanup path.
- If it returns false, `GetCaptionItemFont` calls `TWordViwer.FillMSWFields` at `0x004C009C` (callsite `0x004C2294`).

The `FillMSWFields` TD32 signature explicitly accepts a `Word.Fields` COM interface, so this is a Word-side field fallback, not a GEAR32PD API. Its internal field/COM operations and the precise meaning of the Boolean return remain open.

**Interpretation boundary:** the helper's image-view object, caption iteration and font metrics strongly indicate caption composition/placement. The bounded trace has not yet identified a definitive pixel-write or image-save call, so do not claim that text is certainly rasterized into the bitmap. The GEAR32PD `EmbedTextToImage` helper remains a separate resolution-metadata operation.
