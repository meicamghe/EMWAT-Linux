#include "emwat/image_document_io.hpp"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <filesystem>
#include <stdexcept>

using namespace emwat;

static ImagePage sample_page(std::uint8_t seed) {
    return ImagePage{PixelBuffer{2, 2, 6, PixelFormat::RGB8,
        {seed, static_cast<std::uint8_t>(seed + 1), static_cast<std::uint8_t>(seed + 2),
         static_cast<std::uint8_t>(seed + 3), static_cast<std::uint8_t>(seed + 4),
         static_cast<std::uint8_t>(seed + 5), static_cast<std::uint8_t>(seed + 6),
         static_cast<std::uint8_t>(seed + 7), static_cast<std::uint8_t>(seed + 8),
         static_cast<std::uint8_t>(seed + 9), static_cast<std::uint8_t>(seed + 10),
         static_cast<std::uint8_t>(seed + 11)}}, 300.0, 300.0};
}

int main() {
    const auto root = std::filesystem::temp_directory_path();
    const auto tiff = root / "emwat-document-io.tiff";
    const auto missing = root / "emwat-document-io-missing.png";

    ImageDocument document;
    document.append_page(sample_page(10));
    document.mark_saved();
    document.append_page(sample_page(20));
    assert(document.page_count() == 2 && document.dirty());

    save_document(document, tiff);
    assert(!document.dirty());

    ImageDocument loaded;
    loaded.append_page(sample_page(99));
    load_into_document(loaded, tiff);
    assert(loaded.page_count() == 2);
    assert(!loaded.dirty());
    assert(loaded.active_page() == 0);
    assert(loaded.page(0).pixels.bytes == sample_page(10).pixels.bytes);
    assert(loaded.page(0).dpi_x == 300.0);
    assert(loaded.page(1).pixels.bytes == sample_page(20).pixels.bytes);

    loaded.flip_active(FlipAxis::Horizontal);
    assert(loaded.dirty());
    const auto before = loaded.page(0).pixels.bytes;
    bool failed = false;
    try { load_into_document(loaded, missing); }
    catch (const CodecError&) { failed = true; }
    assert(failed);
    assert(loaded.dirty());
    assert(loaded.page(0).pixels.bytes == before);

    std::filesystem::remove(tiff);
    return 0;
}
