#include "emwat/image_codec.hpp"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <vector>
#include <tiffio.h>

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

    // A TIFF whose payload/IFD data is cut off must fail instead of
    // returning a partially decoded document.
    const auto truncated_tif = root / "emwat-codec-test-truncated.tiff";
    std::filesystem::copy_file(tif, truncated_tif,
        std::filesystem::copy_options::overwrite_existing);
    const auto truncated_size = std::filesystem::file_size(truncated_tif);
    assert(truncated_size > 16);
    std::filesystem::resize_file(truncated_tif, truncated_size / 2);
    bool truncated_tiff_rejected = false;
    try { (void)load_image_file(truncated_tif); }
    catch (const CodecError&) { truncated_tiff_rejected = true; }
    assert(truncated_tiff_rejected);
    std::filesystem::remove(truncated_tif);

    // Corrupt the next-IFD pointer after the first valid page. The loader
    // must not silently return page one as though the document ended cleanly.
    const auto broken_chain_tif = root / "emwat-codec-test-broken-ifd-chain.tiff";
    {
        std::ifstream input(tif, std::ios::binary | std::ios::ate);
        assert(input.good());
        const auto length = input.tellg();
        assert(length > 16);
        std::vector<std::uint8_t> data(static_cast<std::size_t>(length));
        input.seekg(0);
        input.read(reinterpret_cast<char*>(data.data()), length);
        assert(input.good());
        const bool little_endian = data[0] == 'I' && data[1] == 'I';
        assert(little_endian || (data[0] == 'M' && data[1] == 'M'));
        const auto read16 = [&](std::size_t offset) -> std::uint16_t {
            assert(offset + 2 <= data.size());
            if (little_endian)
                return static_cast<std::uint16_t>(data[offset] | (data[offset + 1] << 8));
            return static_cast<std::uint16_t>((data[offset] << 8) | data[offset + 1]);
        };
        const auto read32 = [&](std::size_t offset) -> std::uint32_t {
            assert(offset + 4 <= data.size());
            if (little_endian)
                return static_cast<std::uint32_t>(data[offset]) |
                    (static_cast<std::uint32_t>(data[offset + 1]) << 8) |
                    (static_cast<std::uint32_t>(data[offset + 2]) << 16) |
                    (static_cast<std::uint32_t>(data[offset + 3]) << 24);
            return (static_cast<std::uint32_t>(data[offset]) << 24) |
                (static_cast<std::uint32_t>(data[offset + 1]) << 16) |
                (static_cast<std::uint32_t>(data[offset + 2]) << 8) |
                static_cast<std::uint32_t>(data[offset + 3]);
        };
        const auto first_ifd = static_cast<std::size_t>(read32(4));
        const auto entry_count = static_cast<std::size_t>(read16(first_ifd));
        const auto next_ifd_offset = first_ifd + 2 + entry_count * 12;
        assert(next_ifd_offset + 4 <= data.size());
        constexpr std::uint32_t invalid_ifd = 0xFFFFFFF0U;
        for (unsigned i = 0; i < 4; ++i) {
            const auto shift = little_endian ? i * 8 : (3 - i) * 8;
            data[next_ifd_offset + i] = static_cast<std::uint8_t>(invalid_ifd >> shift);
        }
        std::ofstream output(broken_chain_tif, std::ios::binary);
        output.write(reinterpret_cast<const char*>(data.data()),
                     static_cast<std::streamsize>(data.size()));
        assert(output.good());
    }
    bool broken_chain_rejected = false;
    try { (void)load_image_file(broken_chain_tif); }
    catch (const CodecError&) { broken_chain_rejected = true; }
    assert(broken_chain_rejected);
    std::filesystem::remove(broken_chain_tif);

    const auto gray_tif = root / "emwat-codec-test-gray.tiff";
    const ImagePage gray_page{PixelBuffer{3, 2, 3, PixelFormat::Gray8,
        {0, 32, 64, 128, 192, 255}}, 200.0, 180.0};
    save_image_file({gray_page}, gray_tif);
    const auto gray_pages = load_image_file(gray_tif);
    assert(gray_pages.size() == 1);
    assert(gray_pages[0].pixels.format == PixelFormat::Gray8);
    assert(gray_pages[0].pixels.bytes == gray_page.pixels.bytes);
    assert(gray_pages[0].dpi_x.has_value() && std::abs(*gray_pages[0].dpi_x - 200.0) < 0.1);
    assert(gray_pages[0].dpi_y.has_value() && std::abs(*gray_pages[0].dpi_y - 180.0) < 0.1);
    std::filesystem::remove(gray_tif);


    const auto miniswhite_tif = root / "emwat-codec-test-miniswhite.tiff";
    {
        TIFF* raw = TIFFOpen(miniswhite_tif.string().c_str(), "w");
        assert(raw != nullptr);
        TIFFSetField(raw, TIFFTAG_IMAGEWIDTH, 4);
        TIFFSetField(raw, TIFFTAG_IMAGELENGTH, 1);
        TIFFSetField(raw, TIFFTAG_SAMPLESPERPIXEL, 1);
        TIFFSetField(raw, TIFFTAG_BITSPERSAMPLE, 8);
        TIFFSetField(raw, TIFFTAG_ORIENTATION, ORIENTATION_TOPLEFT);
        TIFFSetField(raw, TIFFTAG_PLANARCONFIG, PLANARCONFIG_CONTIG);
        TIFFSetField(raw, TIFFTAG_PHOTOMETRIC, PHOTOMETRIC_MINISWHITE);
        TIFFSetField(raw, TIFFTAG_COMPRESSION, COMPRESSION_NONE);
        std::uint8_t miniswhite_row[] = {0, 64, 128, 255};
        assert(TIFFWriteScanline(raw, miniswhite_row, 0, 0) >= 0);
        TIFFClose(raw);
    }
    const auto miniswhite_pages = load_image_file(miniswhite_tif);
    assert(miniswhite_pages.size() == 1);
    assert(miniswhite_pages[0].pixels.format == PixelFormat::Gray8);
    assert((miniswhite_pages[0].pixels.bytes == std::vector<std::uint8_t>{255, 191, 127, 0}));
    std::filesystem::remove(miniswhite_tif);


    const auto associated_tif = root / "emwat-codec-test-associated-alpha.tiff";
    {
        TIFF* raw = TIFFOpen(associated_tif.string().c_str(), "w");
        assert(raw != nullptr);
        TIFFSetField(raw, TIFFTAG_IMAGEWIDTH, 2);
        TIFFSetField(raw, TIFFTAG_IMAGELENGTH, 1);
        TIFFSetField(raw, TIFFTAG_SAMPLESPERPIXEL, 4);
        TIFFSetField(raw, TIFFTAG_BITSPERSAMPLE, 8);
        TIFFSetField(raw, TIFFTAG_ORIENTATION, ORIENTATION_TOPLEFT);
        TIFFSetField(raw, TIFFTAG_PLANARCONFIG, PLANARCONFIG_CONTIG);
        TIFFSetField(raw, TIFFTAG_PHOTOMETRIC, PHOTOMETRIC_RGB);
        TIFFSetField(raw, TIFFTAG_COMPRESSION, COMPRESSION_NONE);
        std::uint16_t associated_extra = EXTRASAMPLE_ASSOCALPHA;
        TIFFSetField(raw, TIFFTAG_EXTRASAMPLES, static_cast<std::uint16_t>(1), &associated_extra);
        std::uint8_t associated_row[] = {64, 32, 16, 128, 20, 40, 60, 255};
        assert(TIFFWriteScanline(raw, associated_row, 0, 0) >= 0);
        TIFFClose(raw);
    }
    const auto associated_pages = load_image_file(associated_tif);
    assert(associated_pages.size() == 1);
    assert(associated_pages[0].pixels.format == PixelFormat::RGBA8);
    assert((associated_pages[0].pixels.bytes ==
        std::vector<std::uint8_t>{128, 64, 32, 128, 20, 40, 60, 255}));
    std::filesystem::remove(associated_tif);

    const auto unassociated_tif = root / "emwat-codec-test-unassociated-alpha.tiff";
    {
        TIFF* raw = TIFFOpen(unassociated_tif.string().c_str(), "w");
        assert(raw != nullptr);
        TIFFSetField(raw, TIFFTAG_IMAGEWIDTH, 3);
        TIFFSetField(raw, TIFFTAG_IMAGELENGTH, 1);
        TIFFSetField(raw, TIFFTAG_SAMPLESPERPIXEL, 4);
        TIFFSetField(raw, TIFFTAG_BITSPERSAMPLE, 8);
        TIFFSetField(raw, TIFFTAG_ORIENTATION, ORIENTATION_TOPLEFT);
        TIFFSetField(raw, TIFFTAG_PLANARCONFIG, PLANARCONFIG_CONTIG);
        TIFFSetField(raw, TIFFTAG_PHOTOMETRIC, PHOTOMETRIC_RGB);
        TIFFSetField(raw, TIFFTAG_COMPRESSION, COMPRESSION_NONE);
        std::uint16_t unassociated_extra = EXTRASAMPLE_UNASSALPHA;
        TIFFSetField(raw, TIFFTAG_EXTRASAMPLES, static_cast<std::uint16_t>(1), &unassociated_extra);
        // Unassociated alpha must preserve source RGB exactly, even at alpha=1.
        std::uint8_t unassociated_row[] = {7, 113, 241, 1, 128, 64, 32, 128, 20, 40, 60, 255};
        assert(TIFFWriteScanline(raw, unassociated_row, 0, 0) >= 0);
        TIFFClose(raw);
    }
    const auto unassociated_pages = load_image_file(unassociated_tif);
    assert(unassociated_pages.size() == 1);
    assert(unassociated_pages[0].pixels.format == PixelFormat::RGBA8);
    assert((unassociated_pages[0].pixels.bytes ==
        std::vector<std::uint8_t>{7, 113, 241, 1, 128, 64, 32, 128, 20, 40, 60, 255}));
    std::filesystem::remove(unassociated_tif);


    const auto mixed_pages_tif = root / "emwat-codec-test-mixed-pages.tiff";
    const ImagePage mixed_gray{PixelBuffer{3, 1, 3, PixelFormat::Gray8,
        {17, 83, 201}}, 150.0, 160.0};
    const ImagePage mixed_rgb{PixelBuffer{1, 2, 3, PixelFormat::RGB8,
        {9, 80, 170, 240, 30, 60}}, 300.0, 200.0};
    const ImagePage mixed_rgba{PixelBuffer{2, 1, 8, PixelFormat::RGBA8,
        {10, 20, 30, 128, 200, 150, 100, 255}}, 72.0, 96.0};
    save_image_file({mixed_gray, mixed_rgb, mixed_rgba}, mixed_pages_tif);
    const auto mixed_pages = load_image_file(mixed_pages_tif);
    assert(mixed_pages.size() == 3);
    assert(mixed_pages[0].pixels.width == 3 && mixed_pages[0].pixels.height == 1);
    assert(mixed_pages[0].pixels.format == PixelFormat::Gray8);
    assert(mixed_pages[0].pixels.bytes == mixed_gray.pixels.bytes);
    assert(mixed_pages[1].pixels.width == 1 && mixed_pages[1].pixels.height == 2);
    assert(mixed_pages[1].pixels.format == PixelFormat::RGB8);
    assert(mixed_pages[1].pixels.bytes == mixed_rgb.pixels.bytes);
    assert(mixed_pages[2].pixels.width == 2 && mixed_pages[2].pixels.height == 1);
    assert(mixed_pages[2].pixels.format == PixelFormat::RGBA8);
    assert(mixed_pages[2].pixels.bytes == mixed_rgba.pixels.bytes);
    assert(mixed_pages[0].dpi_x.has_value() && std::abs(*mixed_pages[0].dpi_x - 150.0) < 0.1);
    assert(mixed_pages[1].dpi_y.has_value() && std::abs(*mixed_pages[1].dpi_y - 200.0) < 0.1);
    assert(mixed_pages[2].dpi_x.has_value() && std::abs(*mixed_pages[2].dpi_x - 72.0) < 0.1);
    std::filesystem::remove(mixed_pages_tif);

    const auto oriented_tif = root / "emwat-codec-test-orientation.tiff";
    {
        TIFF* raw = TIFFOpen(oriented_tif.string().c_str(), "w");
        assert(raw != nullptr);
        TIFFSetField(raw, TIFFTAG_IMAGEWIDTH, 2);
        TIFFSetField(raw, TIFFTAG_IMAGELENGTH, 2);
        TIFFSetField(raw, TIFFTAG_SAMPLESPERPIXEL, 3);
        TIFFSetField(raw, TIFFTAG_BITSPERSAMPLE, 8);
        TIFFSetField(raw, TIFFTAG_ORIENTATION, ORIENTATION_BOTRIGHT);
        TIFFSetField(raw, TIFFTAG_PLANARCONFIG, PLANARCONFIG_CONTIG);
        TIFFSetField(raw, TIFFTAG_PHOTOMETRIC, PHOTOMETRIC_RGB);
        TIFFSetField(raw, TIFFTAG_COMPRESSION, COMPRESSION_NONE);
        std::uint8_t first_row[] = {255, 0, 0, 0, 255, 0};
        std::uint8_t second_row[] = {0, 0, 255, 255, 255, 255};
        assert(TIFFWriteScanline(raw, first_row, 0, 0) >= 0);
        assert(TIFFWriteScanline(raw, second_row, 1, 0) >= 0);
        TIFFClose(raw);
    }
    const auto oriented_pages = load_image_file(oriented_tif);
    assert(oriented_pages.size() == 1);
    assert(oriented_pages[0].pixels.width == 2 && oriented_pages[0].pixels.height == 2);
    assert(oriented_pages[0].pixels.format == PixelFormat::RGB8);
    assert((oriented_pages[0].pixels.bytes == std::vector<std::uint8_t>{
        255, 255, 255, 0, 0, 255, 0, 255, 0, 255, 0, 0}));
    std::filesystem::remove(oriented_tif);

    // Horizontal and vertical mirror orientations must also normalize to top-left.
    const auto write_oriented_fixture = [&](const std::filesystem::path& file,
                                            std::uint16_t orientation) {
        TIFF* raw = TIFFOpen(file.string().c_str(), "w");
        assert(raw != nullptr);
        TIFFSetField(raw, TIFFTAG_IMAGEWIDTH, 2);
        TIFFSetField(raw, TIFFTAG_IMAGELENGTH, 2);
        TIFFSetField(raw, TIFFTAG_SAMPLESPERPIXEL, 3);
        TIFFSetField(raw, TIFFTAG_BITSPERSAMPLE, 8);
        TIFFSetField(raw, TIFFTAG_ORIENTATION, orientation);
        TIFFSetField(raw, TIFFTAG_PLANARCONFIG, PLANARCONFIG_CONTIG);
        TIFFSetField(raw, TIFFTAG_PHOTOMETRIC, PHOTOMETRIC_RGB);
        TIFFSetField(raw, TIFFTAG_COMPRESSION, COMPRESSION_NONE);
        std::uint8_t top_row[] = {255, 0, 0, 0, 255, 0};
        std::uint8_t bottom_row[] = {0, 0, 255, 255, 255, 255};
        assert(TIFFWriteScanline(raw, top_row, 0, 0) >= 0);
        assert(TIFFWriteScanline(raw, bottom_row, 1, 0) >= 0);
        TIFFClose(raw);
    };
    const auto top_right_tif = root / "emwat-codec-test-orientation-topright.tiff";
    write_oriented_fixture(top_right_tif, ORIENTATION_TOPRIGHT);
    const auto top_right_pages = load_image_file(top_right_tif);
    assert(top_right_pages.size() == 1);
    assert((top_right_pages[0].pixels.bytes == std::vector<std::uint8_t>{
        0, 255, 0, 255, 0, 0, 255, 255, 255, 0, 0, 255}));
    std::filesystem::remove(top_right_tif);

    const auto bot_left_tif = root / "emwat-codec-test-orientation-botleft.tiff";
    write_oriented_fixture(bot_left_tif, ORIENTATION_BOTLEFT);
    const auto bot_left_pages = load_image_file(bot_left_tif);
    assert(bot_left_pages.size() == 1);
    assert((bot_left_pages[0].pixels.bytes == std::vector<std::uint8_t>{
        0, 0, 255, 255, 255, 255, 255, 0, 0, 0, 255, 0}));
    std::filesystem::remove(bot_left_tif);


    // The four rotated/mirrored TIFF orientations transpose the raster and
    // must also exchange the horizontal and vertical resolution metadata.
    const auto write_rotated_fixture = [&](const std::filesystem::path& file,
                                           std::uint16_t orientation) {
        TIFF* raw = TIFFOpen(file.string().c_str(), "w");
        assert(raw != nullptr);
        TIFFSetField(raw, TIFFTAG_IMAGEWIDTH, 3);
        TIFFSetField(raw, TIFFTAG_IMAGELENGTH, 2);
        TIFFSetField(raw, TIFFTAG_SAMPLESPERPIXEL, 3);
        TIFFSetField(raw, TIFFTAG_BITSPERSAMPLE, 8);
        TIFFSetField(raw, TIFFTAG_ORIENTATION, orientation);
        TIFFSetField(raw, TIFFTAG_PLANARCONFIG, PLANARCONFIG_CONTIG);
        TIFFSetField(raw, TIFFTAG_PHOTOMETRIC, PHOTOMETRIC_RGB);
        TIFFSetField(raw, TIFFTAG_COMPRESSION, COMPRESSION_NONE);
        TIFFSetField(raw, TIFFTAG_XRESOLUTION, 300.0F);
        TIFFSetField(raw, TIFFTAG_YRESOLUTION, 150.0F);
        TIFFSetField(raw, TIFFTAG_RESOLUTIONUNIT, RESUNIT_INCH);
        std::uint8_t first_row[] = {
            10, 0, 0, 20, 0, 0, 30, 0, 0
        };
        std::uint8_t second_row[] = {
            40, 0, 0, 50, 0, 0, 60, 0, 0
        };
        assert(TIFFWriteScanline(raw, first_row, 0, 0) >= 0);
        assert(TIFFWriteScanline(raw, second_row, 1, 0) >= 0);
        TIFFClose(raw);
    };
    const auto check_rotated_orientation = [&](std::uint16_t orientation,
                                                const std::vector<std::uint8_t>& expected) {
        const auto file = root / ("emwat-codec-test-orientation-" +
                                  std::to_string(orientation) + ".tiff");
        write_rotated_fixture(file, orientation);
        const auto decoded = load_image_file(file);
        assert(decoded.size() == 1);
        assert(decoded[0].pixels.width == 2 && decoded[0].pixels.height == 3);
        assert(decoded[0].pixels.format == PixelFormat::RGB8);
        assert(decoded[0].pixels.stride == 6);
        assert(decoded[0].pixels.bytes == expected);
        assert(decoded[0].dpi_x.has_value() && std::abs(*decoded[0].dpi_x - 150.0) < 0.1);
        assert(decoded[0].dpi_y.has_value() && std::abs(*decoded[0].dpi_y - 300.0) < 0.1);
        std::filesystem::remove(file);
    };
    // Source rows are A B C / D E F, with unique red-channel values.
    check_rotated_orientation(ORIENTATION_LEFTTOP, {
        10, 0, 0, 40, 0, 0,
        20, 0, 0, 50, 0, 0,
        30, 0, 0, 60, 0, 0
    });
    check_rotated_orientation(ORIENTATION_RIGHTTOP, {
        40, 0, 0, 10, 0, 0,
        50, 0, 0, 20, 0, 0,
        60, 0, 0, 30, 0, 0
    });
    check_rotated_orientation(ORIENTATION_RIGHTBOT, {
        60, 0, 0, 30, 0, 0,
        50, 0, 0, 20, 0, 0,
        40, 0, 0, 10, 0, 0
    });
    check_rotated_orientation(ORIENTATION_LEFTBOT, {
        30, 0, 0, 60, 0, 0,
        20, 0, 0, 50, 0, 0,
        10, 0, 0, 40, 0, 0
    });

    // PLANARCONFIG_SEPARATE forces the TIFF RGBA fallback. Verify that
    // rotated orientations retain the same geometry, pixel order and DPI axes.
    const auto separate_rotated_tif = root / "emwat-codec-test-separate-rotated.tiff";
    {
        TIFF* raw = TIFFOpen(separate_rotated_tif.string().c_str(), "w");
        assert(raw != nullptr);
        TIFFSetField(raw, TIFFTAG_IMAGEWIDTH, 3);
        TIFFSetField(raw, TIFFTAG_IMAGELENGTH, 2);
        TIFFSetField(raw, TIFFTAG_SAMPLESPERPIXEL, 3);
        TIFFSetField(raw, TIFFTAG_BITSPERSAMPLE, 8);
        TIFFSetField(raw, TIFFTAG_ORIENTATION, ORIENTATION_LEFTTOP);
        TIFFSetField(raw, TIFFTAG_PLANARCONFIG, PLANARCONFIG_SEPARATE);
        TIFFSetField(raw, TIFFTAG_PHOTOMETRIC, PHOTOMETRIC_RGB);
        TIFFSetField(raw, TIFFTAG_COMPRESSION, COMPRESSION_LZW);
        TIFFSetField(raw, TIFFTAG_XRESOLUTION, 300.0F);
        TIFFSetField(raw, TIFFTAG_YRESOLUTION, 150.0F);
        TIFFSetField(raw, TIFFTAG_RESOLUTIONUNIT, RESUNIT_INCH);
        std::uint8_t red0[] = {10, 20, 30}, red1[] = {40, 50, 60};
        std::uint8_t green0[] = {0, 0, 0}, green1[] = {0, 0, 0};
        std::uint8_t blue0[] = {0, 0, 0}, blue1[] = {0, 0, 0};
        std::uint8_t* planes[] = {red0, green0, blue0, red1, green1, blue1};
        for (std::uint16_t sample = 0; sample < 3; ++sample) {
            assert(TIFFWriteScanline(raw, planes[sample], 0, sample) >= 0);
            assert(TIFFWriteScanline(raw, planes[3 + sample], 1, sample) >= 0);
        }
        TIFFClose(raw);
    }
    const auto separate_rotated_pages = load_image_file(separate_rotated_tif);
    assert(separate_rotated_pages.size() == 1);
    assert(separate_rotated_pages[0].pixels.width == 2);
    assert(separate_rotated_pages[0].pixels.height == 3);
    assert(separate_rotated_pages[0].pixels.format == PixelFormat::RGB8);
    assert((separate_rotated_pages[0].pixels.bytes == std::vector<std::uint8_t>{
        10, 0, 0, 40, 0, 0,
        20, 0, 0, 50, 0, 0,
        30, 0, 0, 60, 0, 0}));
    assert(separate_rotated_pages[0].dpi_x.has_value() &&
           std::abs(*separate_rotated_pages[0].dpi_x - 150.0) < 0.1);
    assert(separate_rotated_pages[0].dpi_y.has_value() &&
           std::abs(*separate_rotated_pages[0].dpi_y - 300.0) < 0.1);
    std::filesystem::remove(separate_rotated_tif);

 
    // Grayscale TIFFs use the RGBA fallback path. Exercise a rotated,
    // compressed MINISBLACK page and verify both raster geometry and DPI axes.
    const auto gray_rotated_tif = root / "emwat-codec-test-gray-rotated.tiff";
    {
        TIFF* raw = TIFFOpen(gray_rotated_tif.string().c_str(), "w");
        assert(raw != nullptr);
        TIFFSetField(raw, TIFFTAG_IMAGEWIDTH, 3);
        TIFFSetField(raw, TIFFTAG_IMAGELENGTH, 2);
        TIFFSetField(raw, TIFFTAG_SAMPLESPERPIXEL, 1);
        TIFFSetField(raw, TIFFTAG_BITSPERSAMPLE, 8);
        TIFFSetField(raw, TIFFTAG_SAMPLEFORMAT, SAMPLEFORMAT_UINT);
        TIFFSetField(raw, TIFFTAG_ORIENTATION, ORIENTATION_LEFTTOP);
        TIFFSetField(raw, TIFFTAG_PLANARCONFIG, PLANARCONFIG_CONTIG);
        TIFFSetField(raw, TIFFTAG_PHOTOMETRIC, PHOTOMETRIC_MINISBLACK);
        TIFFSetField(raw, TIFFTAG_COMPRESSION, COMPRESSION_LZW);
        TIFFSetField(raw, TIFFTAG_XRESOLUTION, 240.0F);
        TIFFSetField(raw, TIFFTAG_YRESOLUTION, 120.0F);
        TIFFSetField(raw, TIFFTAG_RESOLUTIONUNIT, RESUNIT_INCH);
        std::uint8_t gray_first_row[] = {10, 20, 30};
        std::uint8_t gray_second_row[] = {40, 50, 60};
        assert(TIFFWriteScanline(raw, gray_first_row, 0, 0) >= 0);
        assert(TIFFWriteScanline(raw, gray_second_row, 1, 0) >= 0);
        TIFFClose(raw);
    }
    const auto gray_rotated_pages = load_image_file(gray_rotated_tif);
    assert(gray_rotated_pages.size() == 1);
    assert(gray_rotated_pages[0].pixels.width == 2);
    assert(gray_rotated_pages[0].pixels.height == 3);
    assert(gray_rotated_pages[0].pixels.format == PixelFormat::Gray8);
    assert(gray_rotated_pages[0].pixels.stride == 2);
    assert((gray_rotated_pages[0].pixels.bytes ==
        std::vector<std::uint8_t>{10, 40, 20, 50, 30, 60}));
    assert(gray_rotated_pages[0].dpi_x.has_value() &&
           std::abs(*gray_rotated_pages[0].dpi_x - 120.0) < 0.1);
    assert(gray_rotated_pages[0].dpi_y.has_value() &&
           std::abs(*gray_rotated_pages[0].dpi_y - 240.0) < 0.1);
    std::filesystem::remove(gray_rotated_tif);

    // MINISWHITE polarity must survive the RGBA fallback's orientation transform.
    // Centimeter resolution is converted to DPI and its axes are swapped on rotation.
    const auto miniswhite_rotated_tif = root / "emwat-codec-test-miniswhite-rotated.tiff";
    {
        TIFF* raw = TIFFOpen(miniswhite_rotated_tif.string().c_str(), "w");
        assert(raw != nullptr);
        TIFFSetField(raw, TIFFTAG_IMAGEWIDTH, 3);
        TIFFSetField(raw, TIFFTAG_IMAGELENGTH, 2);
        TIFFSetField(raw, TIFFTAG_SAMPLESPERPIXEL, 1);
        TIFFSetField(raw, TIFFTAG_BITSPERSAMPLE, 8);
        TIFFSetField(raw, TIFFTAG_SAMPLEFORMAT, SAMPLEFORMAT_UINT);
        TIFFSetField(raw, TIFFTAG_ORIENTATION, ORIENTATION_LEFTTOP);
        TIFFSetField(raw, TIFFTAG_PLANARCONFIG, PLANARCONFIG_CONTIG);
        TIFFSetField(raw, TIFFTAG_PHOTOMETRIC, PHOTOMETRIC_MINISWHITE);
        TIFFSetField(raw, TIFFTAG_COMPRESSION, COMPRESSION_LZW);
        TIFFSetField(raw, TIFFTAG_XRESOLUTION, 100.0F);
        TIFFSetField(raw, TIFFTAG_YRESOLUTION, 50.0F);
        TIFFSetField(raw, TIFFTAG_RESOLUTIONUNIT, RESUNIT_CENTIMETER);
        std::uint8_t first_row[] = {0, 64, 128};
        std::uint8_t second_row[] = {192, 224, 255};
        assert(TIFFWriteScanline(raw, first_row, 0, 0) >= 0);
        assert(TIFFWriteScanline(raw, second_row, 1, 0) >= 0);
        TIFFClose(raw);
    }
    const auto miniswhite_rotated_pages = load_image_file(miniswhite_rotated_tif);
    assert(miniswhite_rotated_pages.size() == 1);
    assert(miniswhite_rotated_pages[0].pixels.width == 2);
    assert(miniswhite_rotated_pages[0].pixels.height == 3);
    assert(miniswhite_rotated_pages[0].pixels.format == PixelFormat::Gray8);
    assert((miniswhite_rotated_pages[0].pixels.bytes ==
        std::vector<std::uint8_t>{255, 63, 191, 31, 127, 0}));
    assert(miniswhite_rotated_pages[0].dpi_x.has_value() &&
           std::abs(*miniswhite_rotated_pages[0].dpi_x - 127.0) < 0.1);
    assert(miniswhite_rotated_pages[0].dpi_y.has_value() &&
           std::abs(*miniswhite_rotated_pages[0].dpi_y - 254.0) < 0.1);
    std::filesystem::remove(miniswhite_rotated_tif);

    // RESUNIT_NONE means the stored resolution values are arbitrary units,
    // so they must not be exposed as DPI.
    const auto unitless_resolution_tif = root / "emwat-codec-test-unitless-resolution.tiff";
    {
        TIFF* raw = TIFFOpen(unitless_resolution_tif.string().c_str(), "w");
        assert(raw != nullptr);
        TIFFSetField(raw, TIFFTAG_IMAGEWIDTH, 2);
        TIFFSetField(raw, TIFFTAG_IMAGELENGTH, 2);
        TIFFSetField(raw, TIFFTAG_SAMPLESPERPIXEL, 1);
        TIFFSetField(raw, TIFFTAG_BITSPERSAMPLE, 8);
        TIFFSetField(raw, TIFFTAG_PLANARCONFIG, PLANARCONFIG_CONTIG);
        TIFFSetField(raw, TIFFTAG_PHOTOMETRIC, PHOTOMETRIC_MINISBLACK);
        TIFFSetField(raw, TIFFTAG_COMPRESSION, COMPRESSION_NONE);
        TIFFSetField(raw, TIFFTAG_XRESOLUTION, 100.0F);
        TIFFSetField(raw, TIFFTAG_YRESOLUTION, 50.0F);
        TIFFSetField(raw, TIFFTAG_RESOLUTIONUNIT, RESUNIT_NONE);
        std::uint8_t row0[] = {10, 20};
        std::uint8_t row1[] = {30, 40};
        assert(TIFFWriteScanline(raw, row0, 0, 0) >= 0);
        assert(TIFFWriteScanline(raw, row1, 1, 0) >= 0);
        TIFFClose(raw);
    }
    const auto unitless_pages = load_image_file(unitless_resolution_tif);
    assert(unitless_pages.size() == 1);
    assert(!unitless_pages[0].dpi_x.has_value());
    assert(!unitless_pages[0].dpi_y.has_value());
    std::filesystem::remove(unitless_resolution_tif);

    const auto rgba_tif = root / "emwat-codec-test-alpha.tiff";
    const ImagePage rgba_page{PixelBuffer{2, 2, 8, PixelFormat::RGBA8,
        {0, 0, 0, 0, 0, 255, 0, 64, 0, 0, 255, 128, 12, 34, 56, 255}}, 240.0, 240.0};
    save_image_file({rgba_page}, rgba_tif);
    const auto rgba_pages = load_image_file(rgba_tif);
    assert(rgba_pages.size() == 1);
    assert(rgba_pages[0].pixels.format == PixelFormat::RGBA8);
    assert(rgba_pages[0].pixels.bytes == rgba_page.pixels.bytes);
    std::filesystem::remove(rgba_tif);
    bool rejected = false;
    try { save_image_file({page(1), page(2)}, png); }
    catch (const CodecError&) { rejected = true; }
    assert(rejected);

    std::filesystem::remove(png);
    std::filesystem::remove(jpg);
    std::filesystem::remove(tif);
    std::filesystem::remove(gray_tif);
    std::filesystem::remove(bad_jpg);
    std::filesystem::remove(bad_tif);
    return 0;
}
