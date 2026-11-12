#include "emwat/image_codec.hpp"

#include <png.h>
#include <jpeglib.h>
#include <tiffio.h>

#include <algorithm>
#include <cctype>
#include <cstdio>
#include <cmath>
#include <limits>
#include <cstdlib>
#include <cstring>
#include <memory>
#include <setjmp.h>
#include <string>
#include <memory>

namespace emwat {
namespace {
struct JpegError {
    jpeg_error_mgr base;
    jmp_buf jump;
};
extern "C" void jpeg_fail(j_common_ptr info) {
    auto* error = reinterpret_cast<JpegError*>(info->err);
    longjmp(error->jump, 1);
}

struct JpegDecodeState {
    jpeg_decompress_struct decoder{};
    JpegError error{};
    FILE* file{};
    std::uint8_t* raw{};
    bool created{false};

    ~JpegDecodeState() {
        if (created) jpeg_destroy_decompress(&decoder);
        std::free(raw);
        if (file) std::fclose(file);
    }
};

struct JpegEncodeState {
    jpeg_compress_struct encoder{};
    JpegError error{};
    FILE* file{};
    bool created{false};

    ~JpegEncodeState() {
        if (created) jpeg_destroy_compress(&encoder);
        if (file) std::fclose(file);
    }
};

constexpr std::uint64_t kMaxDecodedBytes = 1024ULL * 1024ULL * 1024ULL;
constexpr std::size_t kMaxTiffPages = 10000;

std::size_t checked_image_bytes(std::uint32_t width, std::uint32_t height,
                                std::size_t channels, const char* format) {
    if (width == 0 || height == 0 || channels == 0)
        throw CodecError(std::string(format) + " has invalid dimensions");
    const auto pixels = static_cast<std::uint64_t>(width) * height;
    if (pixels > kMaxDecodedBytes / channels)
        throw CodecError(std::string(format) + " exceeds the 1 GiB decoded-image limit");
    return static_cast<std::size_t>(pixels * channels);
}

void require_page(const ImagePage& page) {
    if (!page.pixels.valid()) throw CodecError("invalid image page");
    if ((page.dpi_x && (!std::isfinite(*page.dpi_x) || *page.dpi_x <= 0)) ||
        (page.dpi_y && (!std::isfinite(*page.dpi_y) || *page.dpi_y <= 0)))
        throw CodecError("invalid image resolution metadata");
}

std::pair<std::optional<double>, std::optional<double>>
read_png_resolution(const std::filesystem::path& path) {
    FILE* file = std::fopen(path.string().c_str(), "rb");
    if (!file) throw CodecError("cannot open PNG metadata");
    png_structp png = png_create_read_struct(PNG_LIBPNG_VER_STRING, nullptr, nullptr, nullptr);
    if (!png) {
        std::fclose(file);
        throw CodecError("cannot allocate PNG reader");
    }
    png_infop info = png_create_info_struct(png);
    if (!info) {
        png_destroy_read_struct(&png, nullptr, nullptr);
        std::fclose(file);
        throw CodecError("cannot allocate PNG metadata");
    }
    if (setjmp(png_jmpbuf(png))) {
        png_destroy_read_struct(&png, &info, nullptr);
        std::fclose(file);
        throw CodecError("PNG metadata read failed");
    }
    png_init_io(png, file);
    png_read_info(png, info);
    png_uint_32 xppm = 0, yppm = 0;
    int unit = PNG_RESOLUTION_UNKNOWN;
    std::optional<double> dpi_x, dpi_y;
    if (png_get_pHYs(png, info, &xppm, &yppm, &unit) && unit == PNG_RESOLUTION_METER) {
        if (xppm > 0) dpi_x = static_cast<double>(xppm) * 0.0254;
        if (yppm > 0) dpi_y = static_cast<double>(yppm) * 0.0254;
    }
    png_destroy_read_struct(&png, &info, nullptr);
    std::fclose(file);
    return {dpi_x, dpi_y};
}

void write_png_file(const ImagePage& page, const std::filesystem::path& path) {
    const auto& pixels = page.pixels;
    png_uint_32 xppm = 0, yppm = 0;
    if (page.dpi_x && page.dpi_y) {
        const auto to_ppm = [](double dpi) -> png_uint_32 {
            const double ppm = std::round(dpi / 0.0254);
            if (ppm > static_cast<double>(std::numeric_limits<png_uint_32>::max()))
                throw CodecError("PNG resolution metadata is out of range");
            return static_cast<png_uint_32>(ppm);
        };
        xppm = to_ppm(*page.dpi_x);
        yppm = to_ppm(*page.dpi_y);
    }
    FILE* file = std::fopen(path.string().c_str(), "wb");
    if (!file) throw CodecError("cannot create PNG file");
    png_structp png = png_create_write_struct(PNG_LIBPNG_VER_STRING, nullptr, nullptr, nullptr);
    if (!png) {
        std::fclose(file);
        throw CodecError("cannot allocate PNG writer");
    }
    png_infop info = png_create_info_struct(png);
    if (!info) {
        png_destroy_write_struct(&png, nullptr);
        std::fclose(file);
        throw CodecError("cannot allocate PNG metadata");
    }
    if (setjmp(png_jmpbuf(png))) {
        png_destroy_write_struct(&png, &info);
        std::fclose(file);
        throw CodecError("PNG write failed");
    }
    png_init_io(png, file);
    const int color_type = pixels.format == PixelFormat::Gray8 ? PNG_COLOR_TYPE_GRAY :
        (pixels.format == PixelFormat::RGBA8 ? PNG_COLOR_TYPE_RGBA : PNG_COLOR_TYPE_RGB);
    png_set_IHDR(png, info, pixels.width, pixels.height, 8, color_type,
                 PNG_INTERLACE_NONE, PNG_COMPRESSION_TYPE_DEFAULT, PNG_FILTER_TYPE_DEFAULT);
    if (page.dpi_x && page.dpi_y)
        png_set_pHYs(png, info, xppm, yppm, PNG_RESOLUTION_METER);
    png_write_info(png, info);
    for (std::uint32_t y = 0; y < pixels.height; ++y) {
        png_bytep row = const_cast<png_bytep>(
            pixels.bytes.data() + static_cast<std::size_t>(y) * pixels.stride);
        png_write_row(png, row);
    }
    png_write_end(png, info);
    png_destroy_write_struct(&png, &info);
    std::fclose(file);
}

}

ImageFileFormat image_format_from_extension(const std::filesystem::path& path) {
    auto ext = path.extension().string();
    std::transform(ext.begin(), ext.end(), ext.begin(),
                   [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    if (ext == ".png") return ImageFileFormat::Png;
    if (ext == ".jpg" || ext == ".jpeg") return ImageFileFormat::Jpeg;
    if (ext == ".tif" || ext == ".tiff") return ImageFileFormat::Tiff;
    throw CodecError("unsupported image file extension");
}

std::vector<ImagePage> load_image_file(const std::filesystem::path& path) {
    switch (image_format_from_extension(path)) {
    case ImageFileFormat::Png: {
        png_image image{};
        image.version = PNG_IMAGE_VERSION;
        const auto name = path.string();
        if (!png_image_begin_read_from_file(&image, name.c_str()))
            throw CodecError(std::string("PNG read failed: ") + image.message);
        if (image.width == 0 || image.height == 0) {
            png_image_free(&image);
            throw CodecError("PNG has zero dimensions");
        }
        if ((image.format & PNG_FORMAT_FLAG_COLOR) != 0)
            image.format = (image.format & PNG_FORMAT_FLAG_ALPHA) ? PNG_FORMAT_RGBA : PNG_FORMAT_RGB;
        else image.format = PNG_FORMAT_GRAY;
        const auto channels = PNG_IMAGE_SAMPLE_CHANNELS(image.format);
        const auto expected_bytes = checked_image_bytes(image.width, image.height, channels, "PNG");
        if (PNG_IMAGE_SIZE(image) != expected_bytes) {
            png_image_free(&image);
            throw CodecError("PNG decoded size is inconsistent");
        }
        std::vector<std::uint8_t> bytes(expected_bytes);
        if (!png_image_finish_read(&image, nullptr, bytes.data(), 0, nullptr)) {
            const std::string message = image.message;
            png_image_free(&image);
            throw CodecError("PNG read failed: " + message);
        }
        const auto [dpi_x, dpi_y] = read_png_resolution(path);
        ImagePage page{PixelBuffer{image.width, image.height,
            static_cast<std::size_t>(image.width) * channels,
            channels == 1 ? PixelFormat::Gray8 : (channels == 4 ? PixelFormat::RGBA8 : PixelFormat::RGB8),
            std::move(bytes)}, dpi_x, dpi_y};
        png_image_free(&image);
        return {std::move(page)};
    }
    case ImageFileFormat::Jpeg: {
        auto state = std::make_unique<JpegDecodeState>();
        state->file = std::fopen(path.string().c_str(), "rb");
        if (!state->file) throw CodecError("cannot open JPEG file");
        state->decoder.err = jpeg_std_error(&state->error.base);
        state->error.base.error_exit = jpeg_fail;
        if (setjmp(state->error.jump)) {
            throw CodecError("JPEG decode failed");
        }
        jpeg_create_decompress(&state->decoder);
        state->created = true;
        jpeg_stdio_src(&state->decoder, state->file);
        if (jpeg_read_header(&state->decoder, TRUE) != JPEG_HEADER_OK) {
            jpeg_destroy_decompress(&state->decoder);
            state->created = false;
            std::fclose(state->file);
            state->file = nullptr;
            throw CodecError("invalid JPEG header");
        }
        std::optional<double> dpi_x;
        std::optional<double> dpi_y;
        if (state->decoder.density_unit == 1) {
            if (state->decoder.X_density > 0) dpi_x = state->decoder.X_density;
            if (state->decoder.Y_density > 0) dpi_y = state->decoder.Y_density;
        } else if (state->decoder.density_unit == 2) {
            if (state->decoder.X_density > 0) dpi_x = state->decoder.X_density * 2.54;
            if (state->decoder.Y_density > 0) dpi_y = state->decoder.Y_density * 2.54;
        }
        state->decoder.out_color_space =
            state->decoder.jpeg_color_space == JCS_GRAYSCALE ? JCS_GRAYSCALE : JCS_RGB;
        jpeg_start_decompress(&state->decoder);
        const auto width = state->decoder.output_width;
        const auto height = state->decoder.output_height;
        const auto channels = state->decoder.output_components;
        if (channels != 1 && channels != 3) {
            jpeg_destroy_decompress(&state->decoder);
            state->created = false;
            std::fclose(state->file);
            state->file = nullptr;
            throw CodecError("unsupported JPEG output channel count");
        }
        const auto total = checked_image_bytes(width, height, channels, "JPEG");
        state->raw = static_cast<std::uint8_t*>(std::malloc(total));
        if (!state->raw) {
            jpeg_destroy_decompress(&state->decoder);
            state->created = false;
            std::fclose(state->file);
            state->file = nullptr;
            throw CodecError("out of memory decoding JPEG");
        }
        while (state->decoder.output_scanline < state->decoder.output_height) {
            JSAMPROW row = state->raw +
                static_cast<std::size_t>(state->decoder.output_scanline) * width * channels;
            jpeg_read_scanlines(&state->decoder, &row, 1);
        }
        jpeg_finish_decompress(&state->decoder);
        jpeg_destroy_decompress(&state->decoder);
        state->created = false;
        std::fclose(state->file);
        state->file = nullptr;
        std::vector<std::uint8_t> bytes(state->raw, state->raw + total);
        std::free(state->raw);
        state->raw = nullptr;
        ImagePage page{PixelBuffer{width, height, static_cast<std::size_t>(width) * channels,
            channels == 1 ? PixelFormat::Gray8 : PixelFormat::RGB8, std::move(bytes)}, dpi_x, dpi_y};
        return {std::move(page)};
    }
    case ImageFileFormat::Tiff: {
        using TiffHandle = std::unique_ptr<TIFF, decltype(&TIFFClose)>;
        TiffHandle tif(TIFFOpen(path.string().c_str(), "r"), &TIFFClose);
        if (!tif) throw CodecError("cannot open TIFF file");
        std::vector<ImagePage> pages;
        do {
            std::uint32_t width = 0, height = 0;
            if (!TIFFGetField(tif.get(), TIFFTAG_IMAGEWIDTH, &width) ||
                !TIFFGetField(tif.get(), TIFFTAG_IMAGELENGTH, &height) || width == 0 || height == 0) {
                throw CodecError("invalid TIFF page dimensions");
            }
            if (pages.size() >= kMaxTiffPages) {
                throw CodecError("TIFF exceeds the 10000-page limit");
            }
            const auto pixel_count = checked_image_bytes(width, height, 1, "TIFF");
            if (pixel_count > kMaxDecodedBytes / 7) {
                throw CodecError("TIFF page exceeds the 1 GiB decode working-set limit");
            }
            std::vector<std::uint32_t> raster(pixel_count);
            if (!TIFFReadRGBAImageOriented(tif.get(), width, height, raster.data(), ORIENTATION_TOPLEFT, 0)) {
                throw CodecError("TIFF page decode failed");
            }
            std::vector<std::uint8_t> bytes(checked_image_bytes(width, height, 3, "TIFF"));
            for (std::size_t i = 0; i < raster.size(); ++i) {
                bytes[i * 3] = TIFFGetR(raster[i]);
                bytes[i * 3 + 1] = TIFFGetG(raster[i]);
                bytes[i * 3 + 2] = TIFFGetB(raster[i]);
            }
            float rx = 0, ry = 0;
            const bool has_x = TIFFGetField(tif.get(), TIFFTAG_XRESOLUTION, &rx) != 0;
            const bool has_y = TIFFGetField(tif.get(), TIFFTAG_YRESOLUTION, &ry) != 0;
            std::uint16_t unit = RESUNIT_INCH;
            TIFFGetFieldDefaulted(tif.get(), TIFFTAG_RESOLUTIONUNIT, &unit);
            const double factor = unit == RESUNIT_CENTIMETER ? 2.54 : 1.0;
            pages.push_back(ImagePage{PixelBuffer{width, height, static_cast<std::size_t>(width) * 3,
                PixelFormat::RGB8, std::move(bytes)},
                has_x && rx > 0 ? std::optional<double>(rx * factor) : std::nullopt,
                has_y && ry > 0 ? std::optional<double>(ry * factor) : std::nullopt});
        } while (TIFFReadDirectory(tif.get()));
        tif.reset();
        if (pages.empty()) throw CodecError("TIFF contains no pages");
        return pages;
    }
    }
    throw CodecError("unsupported image format");
}

void save_image_file(const std::vector<ImagePage>& pages, const std::filesystem::path& path,
                     CodecOptions options) {
    if (pages.empty()) throw CodecError("cannot save an empty document");
    for (const auto& page : pages) require_page(page);
    switch (image_format_from_extension(path)) {
    case ImageFileFormat::Png: {
        if (pages.size() != 1) throw CodecError("PNG supports one page; export a page or use TIFF");
        write_png_file(pages.front(), path);
        return;
    }
    case ImageFileFormat::Jpeg: {
        if (pages.size() != 1) throw CodecError("JPEG supports one page; export a page or use TIFF");
        if (options.jpeg_quality < 1 || options.jpeg_quality > 100)
            throw CodecError("JPEG quality must be between 1 and 100");
        const auto& p = pages.front().pixels;
        if (p.format == PixelFormat::RGBA8)
            throw CodecError("JPEG does not support alpha; convert the page to RGB first");
        auto state = std::make_unique<JpegEncodeState>();
        state->file = std::fopen(path.string().c_str(), "wb");
        if (!state->file) throw CodecError("cannot create JPEG file");
        state->encoder.err = jpeg_std_error(&state->error.base);
        state->error.base.error_exit = jpeg_fail;
        if (setjmp(state->error.jump)) {
            throw CodecError("JPEG encode failed");
        }
        jpeg_create_compress(&state->encoder);
        state->created = true;
        jpeg_stdio_dest(&state->encoder, state->file);
        state->encoder.image_width = p.width;
        state->encoder.image_height = p.height;
        state->encoder.input_components = static_cast<int>(p.channels());
        state->encoder.in_color_space = p.format == PixelFormat::Gray8 ? JCS_GRAYSCALE : JCS_RGB;
        jpeg_set_defaults(&state->encoder);
        const auto& metadata = pages.front();
        if (metadata.dpi_x || metadata.dpi_y) {
            const auto to_density = [](const std::optional<double>& dpi) -> std::uint16_t {
                if (!dpi) return 0;
                if (*dpi > 65535.0)
                    throw CodecError("JPEG resolution metadata exceeds 65535 DPI");
                return static_cast<std::uint16_t>(std::lround(*dpi));
            };
            state->encoder.density_unit = 1;
            state->encoder.X_density = to_density(metadata.dpi_x);
            state->encoder.Y_density = to_density(metadata.dpi_y);
        }
        jpeg_set_quality(&state->encoder, options.jpeg_quality, TRUE);
        jpeg_start_compress(&state->encoder, TRUE);
        while (state->encoder.next_scanline < state->encoder.image_height) {
            JSAMPROW row = const_cast<JSAMPROW>(p.bytes.data() +
                static_cast<std::size_t>(state->encoder.next_scanline) * p.stride);
            jpeg_write_scanlines(&state->encoder, &row, 1);
        }
        jpeg_finish_compress(&state->encoder);
        jpeg_destroy_compress(&state->encoder);
        state->created = false;
        std::fclose(state->file);
        state->file = nullptr;
        return;
    }
    case ImageFileFormat::Tiff: {
        using TiffHandle = std::unique_ptr<TIFF, decltype(&TIFFClose)>;
        TiffHandle tif(TIFFOpen(path.string().c_str(), "w"), &TIFFClose);
        if (!tif) throw CodecError("cannot create TIFF file");
        for (const auto& page : pages) {
            const auto& p = page.pixels;
            const auto samples = static_cast<std::uint16_t>(p.channels());
            TIFFSetField(tif.get(), TIFFTAG_IMAGEWIDTH, p.width);
            TIFFSetField(tif.get(), TIFFTAG_IMAGELENGTH, p.height);
            TIFFSetField(tif.get(), TIFFTAG_SAMPLESPERPIXEL, samples);
            TIFFSetField(tif.get(), TIFFTAG_BITSPERSAMPLE, 8);
            TIFFSetField(tif.get(), TIFFTAG_ORIENTATION, ORIENTATION_TOPLEFT);
            TIFFSetField(tif.get(), TIFFTAG_PLANARCONFIG, PLANARCONFIG_CONTIG);
            TIFFSetField(tif.get(), TIFFTAG_PHOTOMETRIC, p.format == PixelFormat::Gray8 ? PHOTOMETRIC_MINISBLACK : PHOTOMETRIC_RGB);
            TIFFSetField(tif.get(), TIFFTAG_COMPRESSION, COMPRESSION_LZW);
            TIFFSetField(tif.get(), TIFFTAG_ROWSPERSTRIP, TIFFDefaultStripSize(tif.get(), 0));
            if (p.format == PixelFormat::RGBA8) {
                std::uint16_t extra = EXTRASAMPLE_UNASSALPHA;
                TIFFSetField(tif.get(), TIFFTAG_EXTRASAMPLES, 1, &extra);
            }
            if (page.dpi_x) TIFFSetField(tif.get(), TIFFTAG_XRESOLUTION, static_cast<float>(*page.dpi_x));
            if (page.dpi_y) TIFFSetField(tif.get(), TIFFTAG_YRESOLUTION, static_cast<float>(*page.dpi_y));
            if (page.dpi_x || page.dpi_y) TIFFSetField(tif.get(), TIFFTAG_RESOLUTIONUNIT, RESUNIT_INCH);
            for (std::uint32_t y = 0; y < p.height; ++y) {
                auto* row = const_cast<std::uint8_t*>(p.bytes.data() + static_cast<std::size_t>(y) * p.stride);
                if (TIFFWriteScanline(tif.get(), row, y, 0) < 0) {
                    throw CodecError("TIFF scanline write failed");
                }
            }
            if (&page != &pages.back() && !TIFFWriteDirectory(tif.get())) {
                throw CodecError("TIFF directory write failed");
            }
        }
        tif.reset();
        return;
    }
    }
    throw CodecError("unsupported image format");
}

} // namespace emwat
