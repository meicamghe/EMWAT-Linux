# Native Linux Image Document — Design Contract (Draft)

Status: architecture draft grounded in static reverse engineering; not yet an implementation or a claim of binary/API parity.

## 1. Evidence boundary

The Windows implementation uses ImageGear handles (HIGEAR), file descriptors/backing streams, and a Delphi editor/controller object. Linux must not expose HIGEAR or emulate its ABI. The native model below is an application-level contract.

Confirmed imports and call paths:
- `IG_image_delete`: imported thunk `0x004AFEB8`; callers include preview form teardown/replacement, `TGearImgProc.NotifyEditor`, `PaintCanvas`, and `SavePage`.
- `IG_image_is_valid`: `0x004AFEC0`; used before image operations in ReloadPage, GetImageResolution, NotifyEditor, PaintCanvas, SaveToFile and ScanToFile.
- `IG_IP_rotate_multiple_90`: `0x004AFEC8`; used by RotateLeft and preview rotate/flip controls.
- `IG_page_count_get`: `0x004AFEA8`; used by Rotate90, SaveToFile and preview metadata paths.
- `IG_image_dimensions_get`: `0x004AFF00`; ReloadPage passes HIGEAR and three output addresses at object offsets +0x40, +0x3C, +0x44. Their exact semantic mapping (width/height/resolution or related metadata) is not yet proven.
- `IG_image_resolution_get/set`: separate imports exist; resolution metadata is not interchangeable with pixel dimensions.

Important distinction: TD32's `Rotate90` method name does not prove a pixel transform. Its body calls page-count retrieval and a context virtual method. Pixel rotation is directly evidenced in `RotateLeft` via `IG_IP_rotate_multiple_90`, followed by reload/metadata refresh and dirty-state update.

## 2. Proposed domain model

### Document
Owns an ordered collection of pages and backing-file metadata.
- `pages: vector<Page>`
- `active_page: PageIndex`
- `backing_uri: optional filesystem path / stream identity`
- `format: ImageFormat`
- `dirty: bool`
- `read_only: bool`
- `generation: monotonically increasing revision`

Invariants:
- A document has zero or more pages; active_page is valid only when pages are non-empty.
- Saving must preserve page order and all pages unless the selected export mode explicitly requests a single page.
- A failed page load/save must not silently replace the current valid page or clear dirty state.

### Page
Represents one independently addressable image page.
- `pixels: PixelBuffer`
- `pixel_width, pixel_height: uint32`
- `dpi_x, dpi_y: optional rational/float metadata`
- `color_model: Gray | RGB | RGBA | Indexed | Unknown`
- `bit_depth: uint16`
- `source_page_index: optional uint32`
- `metadata: key/value map`

Pixel dimensions and DPI must remain separate. Rotation by 90/270 degrees swaps pixel width and height; DPI axes should be transformed consistently if the image format stores anisotropic resolution.

### PixelBuffer
- Explicit width, height, stride, channel layout, bit depth and owned byte storage.
- Row stride must not be assumed equal to width × channel count.
- Pixel operations must validate buffer length and overflow before allocation.
- Use a single documented in-memory channel order (recommend RGB/RGBA) and convert at codec boundaries.

### ImageOperationResult
Every operation returns structured success/error information; no modal UI or global last-error state in the image core.
- `ok`
- `error_code`
- `message`
- optional `warnings`
- optional updated dimensions/metadata

## 3. Core API boundary

Proposed C++-style interface (language-neutral intent):

```cpp
struct ImageDocument {
    std::vector<ImagePage> pages;
    std::size_t active_page = 0;
    bool dirty = false;
    std::uint64_t generation = 0;
};

Result<std::size_t> page_count(const ImageDocument&);
Result<ImageMetadata> metadata(const ImagePage&);
Result<void> select_page(ImageDocument&, std::size_t index);
Result<void> rotate(ImageDocument&, std::size_t index, QuarterTurn turn);
Result<void> flip(ImageDocument&, std::size_t index, Axis axis);
Result<void> crop(ImageDocument&, std::size_t index, Rect region);
Result<void> load_document(ImageDocument&, const std::filesystem::path&);
Result<void> save_document(const ImageDocument&, const std::filesystem::path&, SaveOptions);
Result<void> export_page(const ImagePage&, const std::filesystem::path&, SaveOptions);
```

The interface deliberately separates:
1. document/page navigation,
2. pixel transforms,
3. metadata refresh,
4. persistence/codec operations,
5. scanner acquisition.

Scanner acquisition should produce a normal `ImagePage`/document and must use the Linux scanner backend (SANE), not WIA/TWAIN compatibility shims.

## 4. Lifecycle and ownership rules

The native implementation must use RAII/value ownership:
- A page owns its pixel buffer; no raw image handle may outlive its owner.
- Replacing/reloading a page is transactional: decode into a temporary page, validate, then swap.
- Temporary pages used for multi-page save must be scoped and released automatically.
- Deleting/replacing a page must not invalidate unrelated pages or the editor's active page reference.
- Save success clears dirty only if the document generation is unchanged since the save snapshot. Save failure preserves dirty.
- Editor/UI code observes immutable metadata snapshots or explicit change notifications; it does not own codec internals.

These rules mirror the observed repeated create/load/delete lifecycle without reproducing ImageGear's handle API.

## 5. Compatibility behaviors to test

- Single-page and multi-page open/save.
- Page count and page selection boundaries (Windows setter accepts 1..page_count; Linux API should use zero-based indexes internally and convert only at UI boundaries).
- Dirty prompt behavior before page switch/close.
- Rotate left/right, horizontal flip, vertical flip, crop and restore-original.
- Pixel dimensions and DPI after each transform.
- TIFF multi-page save and JPEG quality/compression settings.
- Failed load/save must retain original content and dirty state.
- Round-trip tests compare page count, dimensions, color model, bit depth, DPI (within codec tolerance), and pixel checksums or perceptual tolerances.

## 6. Open questions before implementation parity

1. Exact output semantics/order of the three `IG_image_dimensions_get` output pointers at GearImgProc offsets +0x40/+0x3C/+0x44.
2. Exact context-object virtual slot contracts (notably slots 0 and +0x20) used for page count/state and page selection.
3. Exact image format/compression enum mapping in `TGearImgProc+0x14`.
4. Whether backing value `+0x38` is always a filesystem path or can be a stream/descriptor abstraction.
5. Exact multi-page format behavior and per-page metadata preservation.

Until these are resolved, implement the data model and codec-independent transforms first; keep persistence and scanner adapters behind interfaces.
