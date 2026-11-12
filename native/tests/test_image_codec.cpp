#include "emwat/image_codec.hpp"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <vector>

using namespace emwat;

static ImagePage page(std::uint8_t seed) {
    return ImagePage{PixelBuffer{2, 2, 6, PixelFormat::RGB8,
        {seed, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12}}, 300.0, 300.0};
}

int main() {
    const auto root = std::filesystem::temp_directory_path();
    const auto png = root / "emwat-codec-test.png";
    const auto jpg = root / "emwat-codec-test.jpg";
    const auto tif = root / "emwat-codec-test.tiff";
    const auto bad_jpg = root / "emwat-codec-test-corrupt.jpg";
    const auto bad_tif = root / "emwat-codec-test-corrupt.tiff";

    save_image_file({page(1)}, png);
    auto png_pages = load_image_file(png);
    assert(png_pages.size() == 1);
    assert(png_pages[0].pixels.width == 2 && png_pages[0].pixels.height == 2);
    assert(png_pages[0].pixels.format == PixelFormat::RGB8);
    assert(png_pages[0].pixels.bytes == page(1).pixels.bytes);
    assert(png_pages[0].dpi_x.has_value() && std::abs(*png_pages[0].dpi_x - 300.0) < 0.1);
    assert(png_pages[0].dpi_y.has_value() && std::abs(*png_pages[0].dpi_y - 300.0) < 0.1);

    save_image_file({page(1)}, jpg, CodecOptions{95});
    auto jpg_pages = load_image_file(jpg);
    assert(jpg_pages.size() == 1);
    assert(jpg_pages[0].pixels.width == 2 && jpg_pages[0].pixels.height == 2);
    assert(jpg_pages[0].dpi_x.has_value() && *jpg_pages[0].dpi_x == 300.0);
    assert(jpg_pages[0].dpi_y.has_value() && *jpg_pages[0].dpi_y == 300.0);

    {
        std::ofstream out(bad_jpg, std::ios::binary);
        out << "this is not a JPEG stream";
    }
    bool corrupt_rejected = false;
    try { (void)load_image_file(bad_jpg); }
    catch (const CodecError&) { corrupt_rejected = true; }
    assert(corrupt_rejected);

    {
        std::ofstream out(bad_tif, std::ios::binary);
        out << "not a TIFF file";
    }
    bool corrupt_tiff_rejected = false;
    try { (void)load_image_file(bad_tif); }
    catch (const CodecError&) { corrupt_tiff_rejected = true; }
    assert(corrupt_tiff_rejected);

    save_image_file({page(1), page(20)}, tif);
    auto tif_pages = load_image_file(tif);
    assert(tif_pages.size() == 2);
    assert(tif_pages[0].pixels.width == 2 && tif_pages[1].pixels.height == 2);
    assert(tif_pages[0].pixels.bytes == page(1).pixels.bytes);
    assert(tif_pages[1].pixels.bytes == page(20).pixels.bytes);
    assert(tif_pages[0].dpi_x.has_value());

    bool rejected = false;
    try { save_image_file({page(1), page(2)}, png); }
    catch (const CodecError&) { rejected = true; }
    assert(rejected);

    std::filesystem::remove(png);
    std::filesystem::remove(jpg);
    std::filesystem::remove(tif);
    std::filesystem::remove(bad_jpg);
    std::filesystem::remove(bad_tif);
    return 0;
}
