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

void require_page(const ImagePage& page) {
    if (!page.pixels.valid()) throw CodecError("invalid image page");
    if ((page.dpi_x && (!std::isfinite(*page.dpi_x) || *page.dpi_x <= 0)) ||
        (page.dpi_y && (!std::isfinite(*page.dpi_y) || *page.dpi_y <= 0)))
        throw CodecError("invalid image resolution metadata");
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
        std::vector<std::uint8_t> bytes(PNG_IMAGE_SIZE(image));
        if (!png_image_finish_read(&image, nullptr, bytes.data(), 0, nullptr)) {
            const std::string message = image.message;
            png_image_free(&image);
            throw CodecError("PNG read failed: " + message);
        }
        const auto channels = PNG_IMAGE_SAMPLE_CHANNELS(image.format);
        ImagePage page{PixelBuffer{image.width, image.height,
            static_cast<std::size_t>(image.width) * channels,
            channels == 1 ? PixelFormat::Gray8 : (channels == 4 ? PixelFormat::RGBA8 : PixelFormat::RGB8),
            std::move(bytes)}, {}, {}};
        png_image_free(&image);
        return {std::move(page)};
    }
    case ImageFileFormat::Jpeg: {
        FILE* file = std::fopen(path.string().c_str(), "rb");
        if (!file) throw CodecError("cannot open JPEG file");
        jpeg_decompress_struct decoder{};
        JpegError error{};
        decoder.err = jpeg_std_error(&error.base);
        error.base.error_exit = jpeg_fail;
        if (setjmp(error.jump)) {
            jpeg_destroy_decompress(&decoder);
            std::fclose(file);
            throw CodecError("JPEG decode failed");
        }
        jpeg_create_decompress(&decoder);
        jpeg_stdio_src(&decoder, file);
        jpeg_read_header(&decoder, TRUE);
        decoder.out_color_space = decoder.jpeg_color_space == JCS_GRAYSCALE ? JCS_GRAYSCALE : JCS_RGB;
        jpeg_start_decompress(&decoder);
        const auto width = decoder.output_width;
        const auto height = decoder.output_height;
        const auto channels = decoder.output_components;
        const auto total = static_cast<std::size_t>(width) * height * channels;
        auto* raw = static_cast<std::uint8_t*>(std::malloc(total));
        if (!raw) {
            jpeg_destroy_decompress(&decoder);
            std::fclose(file);
            throw CodecError("out of memory decoding JPEG");
        }
        while (decoder.output_scanline < decoder.output_height) {
            JSAMPROW row = raw + static_cast<std::size_t>(decoder.output_scanline) * width * channels;
            jpeg_read_scanlines(&decoder, &row, 1);
        }
        jpeg_finish_decompress(&decoder);
        jpeg_destroy_decompress(&decoder);
        std::fclose(file);
        std::vector<std::uint8_t> bytes(raw, raw + total);
        std::free(raw);
        ImagePage page{PixelBuffer{width, height, static_cast<std::size_t>(width) * channels,
            channels == 1 ? PixelFormat::Gray8 : PixelFormat::RGB8, std::move(bytes)}, {}, {}};
        return {std::move(page)};
    }
    case ImageFileFormat::Tiff: {
        TIFF* tif = TIFFOpen(path.string().c_str(), "r");
        if (!tif) throw CodecError("cannot open TIFF file");
        std::vector<ImagePage> pages;
        do {
            std::uint32_t width = 0, height = 0;
            if (!TIFFGetField(tif, TIFFTAG_IMAGEWIDTH, &width) ||
                !TIFFGetField(tif, TIFFTAG_IMAGELENGTH, &height) || width == 0 || height == 0) {
                TIFFClose(tif);
                throw CodecError("invalid TIFF page dimensions");
            }
            if (static_cast<std::uint64_t>(width) * height > std::numeric_limits<std::size_t>::max() / 4) {
                TIFFClose(tif);
                throw CodecError("TIFF page is too large");
            }
            std::vector<std::uint32_t> raster(static_cast<std::size_t>(width) * height);
            if (!TIFFReadRGBAImageOriented(tif, width, height, raster.data(), ORIENTATION_TOPLEFT, 0)) {
                TIFFClose(tif);
                throw CodecError("TIFF page decode failed");
            }
            std::vector<std::uint8_t> bytes(static_cast<std::size_t>(width) * height * 3);
            for (std::size_t i = 0; i < raster.size(); ++i) {
                bytes[i * 3] = TIFFGetR(raster[i]);
                bytes[i * 3 + 1] = TIFFGetG(raster[i]);
                bytes[i * 3 + 2] = TIFFGetB(raster[i]);
            }
            float rx = 0, ry = 0;
            const bool has_x = TIFFGetField(tif, TIFFTAG_XRESOLUTION, &rx) != 0;
            const bool has_y = TIFFGetField(tif, TIFFTAG_YRESOLUTION, &ry) != 0;
            std::uint16_t unit = RESUNIT_INCH;
            TIFFGetFieldDefaulted(tif, TIFFTAG_RESOLUTIONUNIT, &unit);
            const double factor = unit == RESUNIT_CENTIMETER ? 2.54 : 1.0;
            pages.push_back(ImagePage{PixelBuffer{width, height, static_cast<std::size_t>(width) * 3,
                PixelFormat::RGB8, std::move(bytes)},
                has_x && rx > 0 ? std::optional<double>(rx * factor) : std::nullopt,
                has_y && ry > 0 ? std::optional<double>(ry * factor) : std::nullopt});
        } while (TIFFReadDirectory(tif));
        TIFFClose(tif);
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
        const auto& p = pages.front().pixels;
        png_image image{};
        image.version = PNG_IMAGE_VERSION;
        image.width = p.width;
        image.height = p.height;
        image.format = p.format == PixelFormat::Gray8 ? PNG_FORMAT_GRAY :
                       (p.format == PixelFormat::RGBA8 ? PNG_FORMAT_RGBA : PNG_FORMAT_RGB);
        if (!png_image_write_to_file(&image, path.string().c_str(), 0, p.bytes.data(),
                                     static_cast<png_int_32>(p.stride), nullptr))
            throw CodecError(std::string("PNG write failed: ") + image.message);
        return;
    }
    case ImageFileFormat::Jpeg: {
        if (pages.size() != 1) throw CodecError("JPEG supports one page; export a page or use TIFF");
        if (options.jpeg_quality < 1 || options.jpeg_quality > 100)
            throw CodecError("JPEG quality must be between 1 and 100");
        const auto& p = pages.front().pixels;
        if (p.format == PixelFormat::RGBA8)
            throw CodecError("JPEG does not support alpha; convert the page to RGB first");
        FILE* file = std::fopen(path.string().c_str(), "wb");
        if (!file) throw CodecError("cannot create JPEG file");
        jpeg_compress_struct encoder{};
        JpegError error{};
        encoder.err = jpeg_std_error(&error.base);
        error.base.error_exit = jpeg_fail;
        if (setjmp(error.jump)) {
            jpeg_destroy_compress(&encoder);
            std::fclose(file);
            throw CodecError("JPEG encode failed");
        }
        jpeg_create_compress(&encoder);
        jpeg_stdio_dest(&encoder, file);
        encoder.image_width = p.width;
        encoder.image_height = p.height;
        encoder.input_components = static_cast<int>(p.channels());
        encoder.in_color_space = p.format == PixelFormat::Gray8 ? JCS_GRAYSCALE : JCS_RGB;
        jpeg_set_defaults(&encoder);
        jpeg_set_quality(&encoder, options.jpeg_quality, TRUE);
        jpeg_start_compress(&encoder, TRUE);
        while (encoder.next_scanline < encoder.image_height) {
            JSAMPROW row = const_cast<JSAMPROW>(p.bytes.data() +
                static_cast<std::size_t>(encoder.next_scanline) * p.stride);
            jpeg_write_scanlines(&encoder, &row, 1);
        }
        jpeg_finish_compress(&encoder);
        jpeg_destroy_compress(&encoder);
        std::fclose(file);
        return;
    }
    case ImageFileFormat::Tiff: {
        TIFF* tif = TIFFOpen(path.string().c_str(), "w");
        if (!tif) throw CodecError("cannot create TIFF file");
        for (const auto& page : pages) {
            const auto& p = page.pixels;
            const auto samples = static_cast<std::uint16_t>(p.channels());
            TIFFSetField(tif, TIFFTAG_IMAGEWIDTH, p.width);
            TIFFSetField(tif, TIFFTAG_IMAGELENGTH, p.height);
            TIFFSetField(tif, TIFFTAG_SAMPLESPERPIXEL, samples);
            TIFFSetField(tif, TIFFTAG_BITSPERSAMPLE, 8);
            TIFFSetField(tif, TIFFTAG_ORIENTATION, ORIENTATION_TOPLEFT);
            TIFFSetField(tif, TIFFTAG_PLANARCONFIG, PLANARCONFIG_CONTIG);
            TIFFSetField(tif, TIFFTAG_PHOTOMETRIC, p.format == PixelFormat::Gray8 ? PHOTOMETRIC_MINISBLACK : PHOTOMETRIC_RGB);
            TIFFSetField(tif, TIFFTAG_COMPRESSION, COMPRESSION_LZW);
            TIFFSetField(tif, TIFFTAG_ROWSPERSTRIP, TIFFDefaultStripSize(tif, 0));
            if (p.format == PixelFormat::RGBA8) {
                std::uint16_t extra = EXTRASAMPLE_UNASSALPHA;
                TIFFSetField(tif, TIFFTAG_EXTRASAMPLES, 1, &extra);
            }
            if (page.dpi_x) TIFFSetField(tif, TIFFTAG_XRESOLUTION, static_cast<float>(*page.dpi_x));
            if (page.dpi_y) TIFFSetField(tif, TIFFTAG_YRESOLUTION, static_cast<float>(*page.dpi_y));
            if (page.dpi_x || page.dpi_y) TIFFSetField(tif, TIFFTAG_RESOLUTIONUNIT, RESUNIT_INCH);
            for (std::uint32_t y = 0; y < p.height; ++y) {
                auto* row = const_cast<std::uint8_t*>(p.bytes.data() + static_cast<std::size_t>(y) * p.stride);
                if (TIFFWriteScanline(tif, row, y, 0) < 0) {
                    TIFFClose(tif);
                    throw CodecError("TIFF scanline write failed");
                }
            }
            if (&page != &pages.back() && !TIFFWriteDirectory(tif)) {
                TIFFClose(tif);
                throw CodecError("TIFF directory write failed");
            }
        }
        TIFFClose(tif);
        return;
    }
    }
    throw CodecError("unsupported image format");
}

} // namespace emwat
