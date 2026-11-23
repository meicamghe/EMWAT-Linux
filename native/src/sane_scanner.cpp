#include "emwat/scanner.hpp"
#include "emwat/scanner_detail.hpp"

#include <sane/sane.h>

#include <algorithm>
#include <cmath>
#include <cstring>
#include <array>
#include <cctype>
#include <limits>
#include <mutex>
#include <string>
#include <tuple>
#include <utility>

namespace emwat {
namespace {
constexpr std::size_t max_scan_bytes = 1024ULL * 1024ULL * 1024ULL;
constexpr SANE_Word max_capability_entries = 4096;
constexpr std::size_t max_capability_string_length = 256;
std::mutex& sane_mutex() {
    static std::mutex value;
    return value;
}

class SaneSession {
public:
    SaneSession() {
        SANE_Int version = 0;
        const auto status = sane_init(&version, nullptr);
        if (status != SANE_STATUS_GOOD)
            throw ScannerError(std::string("SANE initialization failed: ") + sane_strstatus(status));
        active_ = true;
    }
    ~SaneSession() { if (active_) sane_exit(); }
    SaneSession(const SaneSession&) = delete;
    SaneSession& operator=(const SaneSession&) = delete;
private:
    bool active_{};
};

class SaneHandle {
public:
    explicit SaneHandle(const std::string& id) {
        const auto status = sane_open(reinterpret_cast<const SANE_Char*>(id.c_str()), &handle_);
        if (status != SANE_STATUS_GOOD)
            throw ScannerError(std::string("Cannot open scanner: ") + sane_strstatus(status));
        active_ = true;
    }
    ~SaneHandle() { if (active_) sane_close(handle_); }
    SaneHandle(const SaneHandle&) = delete;
    SaneHandle& operator=(const SaneHandle&) = delete;
    [[nodiscard]] SANE_Handle get() const noexcept { return handle_; }
private:
    SANE_Handle handle_{};
    bool active_{};
};

void validate_device_id(const std::string& device_id) {
    if (device_id.empty())
        throw ScannerError("scanner device id cannot be empty");
    if (std::any_of(device_id.begin(), device_id.end(), [](unsigned char value) {
            return std::iscntrl(value) != 0;
        }))
        throw ScannerError("scanner device id contains a control character");
}

void validate_scan_options(const ScanOptions& options) {
    if (options.resolution_dpi &&
        (!std::isfinite(*options.resolution_dpi) ||
         *options.resolution_dpi <= 0.0 ||
         *options.resolution_dpi > 100000.0)) {
        throw ScannerError("Scan resolution must be finite and between 0 and 100000 DPI");
    }
    const auto validate_text = [](const std::optional<std::string>& value,
                                  const char* option_name) {
        if (!value) return;
        if (value->empty() ||
            std::any_of(value->begin(), value->end(), [](unsigned char ch) {
                return std::iscntrl(ch) != 0;
            })) {
            throw ScannerError(std::string("Invalid scanner ") + option_name + " option");
        }
    };
    validate_text(options.mode, "mode");
    validate_text(options.source, "source");
}

void set_string_option(SANE_Handle handle, const char* name, const std::string& value) {
    SANE_Int index = 0;
    const SANE_Option_Descriptor* descriptor = nullptr;
    for (index = 1; (descriptor = sane_get_option_descriptor(handle, index)) != nullptr; ++index) {
        if (descriptor->name && std::strcmp(reinterpret_cast<const char*>(descriptor->name), name) == 0)
            break;
    }
    if (!descriptor) throw ScannerError(std::string("Scanner does not support option: ") + name);
    if (!(descriptor->cap & SANE_CAP_SOFT_SELECT) || !(descriptor->cap & SANE_CAP_SOFT_DETECT) ||
        (descriptor->cap & SANE_CAP_INACTIVE) || descriptor->type != SANE_TYPE_STRING ||
        !detail::sane_string_option_size_valid(descriptor->size, value.size()))
        throw ScannerError(std::string("Scanner option is unavailable or incompatible: ") + name);
    std::vector<SANE_Char> buffer(static_cast<std::size_t>(descriptor->size), 0);
    std::memcpy(buffer.data(), value.c_str(), value.size() + 1);
    SANE_Int info = 0;
    const auto status = sane_control_option(handle, index, SANE_ACTION_SET_VALUE, buffer.data(), &info);
    if (status != SANE_STATUS_GOOD)
        throw ScannerError(std::string("Cannot set scanner option ") + name + ": " + sane_strstatus(status));
}

void set_resolution_option(SANE_Handle handle, double dpi) {
    if (!std::isfinite(dpi) || dpi <= 0.0 || dpi > 100000.0)
        throw ScannerError("Scan resolution must be finite and between 0 and 100000 DPI");
    SANE_Int index = 0;
    const SANE_Option_Descriptor* descriptor = nullptr;
    for (index = 1; (descriptor = sane_get_option_descriptor(handle, index)) != nullptr; ++index) {
        if (descriptor->name &&
            std::strcmp(reinterpret_cast<const char*>(descriptor->name), "resolution") == 0)
            break;
    }
    if (!descriptor) throw ScannerError("Scanner does not support resolution option");
    if (!(descriptor->cap & SANE_CAP_SOFT_SELECT) || !(descriptor->cap & SANE_CAP_SOFT_DETECT) ||
        (descriptor->cap & SANE_CAP_INACTIVE) || descriptor->size != static_cast<SANE_Int>(sizeof(SANE_Word)) ||
        (descriptor->type != SANE_TYPE_INT && descriptor->type != SANE_TYPE_FIXED))
        throw ScannerError("Scanner resolution option is unavailable or incompatible");
    SANE_Word value = 0;
    if (descriptor->type == SANE_TYPE_FIXED) {
        const auto fixed_value = detail::encode_sane_fixed_resolution(dpi);
        if (!fixed_value)
            throw ScannerError("Scan resolution cannot be represented by the scanner fixed-point option");
        value = static_cast<SANE_Word>(*fixed_value);
    } else {
        value = static_cast<SANE_Word>(std::lround(dpi));
    }
    SANE_Int info = 0;
    const auto status = sane_control_option(handle, index, SANE_ACTION_SET_VALUE, &value, &info);
    if (status != SANE_STATUS_GOOD)
        throw ScannerError(std::string("Cannot set scanner resolution: ") + sane_strstatus(status));
}


double sane_numeric_value(SANE_Word value, SANE_Value_Type type) {
    return type == SANE_TYPE_FIXED ? SANE_UNFIX(value) : static_cast<double>(value);
}

std::optional<double> read_numeric_option(SANE_Handle handle, const char* name) {
    for (SANE_Int index = 1; ; ++index) {
        const auto* descriptor = sane_get_option_descriptor(handle, index);
        if (!descriptor) return std::nullopt;
        if (!descriptor->name ||
            std::strcmp(reinterpret_cast<const char*>(descriptor->name), name) != 0)
            continue;
        if ((descriptor->cap & SANE_CAP_INACTIVE) ||
            !(descriptor->cap & SANE_CAP_SOFT_DETECT) ||
            descriptor->size != static_cast<SANE_Int>(sizeof(SANE_Word)) ||
            (descriptor->type != SANE_TYPE_INT && descriptor->type != SANE_TYPE_FIXED))
            return std::nullopt;
        SANE_Word value = 0;
        SANE_Int info = 0;
        const auto status = sane_control_option(handle, index, SANE_ACTION_GET_VALUE, &value, &info);
        if (status != SANE_STATUS_GOOD) return std::nullopt;
        const double dpi = sane_numeric_value(value, descriptor->type);
        if (!std::isfinite(dpi) || dpi <= 0.0 || dpi > 100000.0) return std::nullopt;
        return dpi;
    }
}

std::pair<std::optional<double>, std::optional<double>> read_scan_dpi(SANE_Handle handle) {
    const auto x = read_numeric_option(handle, "x-resolution");
    const auto y = read_numeric_option(handle, "y-resolution");
    if (x || y) return {x ? x : y, y ? y : x};
    const auto resolution = read_numeric_option(handle, "resolution");
    return {resolution, resolution};
}

void collect_string_values(SANE_Handle handle, const char* option_name,
                           std::vector<std::string>& values) {
    for (SANE_Int index = 1; ; ++index) {
        const auto* descriptor = sane_get_option_descriptor(handle, index);
        if (!descriptor) break;
        if (!descriptor->name ||
            std::strcmp(reinterpret_cast<const char*>(descriptor->name), option_name) != 0)
            continue;
        if ((descriptor->cap & SANE_CAP_INACTIVE) ||
            !(descriptor->cap & SANE_CAP_SOFT_DETECT) ||
            descriptor->type != SANE_TYPE_STRING ||
            descriptor->constraint_type != SANE_CONSTRAINT_STRING_LIST ||
            !descriptor->constraint.string_list)
            return;
        for (const SANE_Char* const* item = descriptor->constraint.string_list;
             *item && values.size() < 256; ++item) {
            const auto* text = reinterpret_cast<const char*>(*item);
            std::size_t length = 0;
            while (length < max_capability_string_length && text[length] != '\0') ++length;
            if (length > 0 && length < max_capability_string_length)
                values.emplace_back(text, length);
        }
        return;
    }
}

void collect_resolution_values(SANE_Handle handle, ScannerCapabilities& result) {
    for (SANE_Int index = 1; ; ++index) {
        const auto* descriptor = sane_get_option_descriptor(handle, index);
        if (!descriptor) break;
        if (!descriptor->name ||
            std::strcmp(reinterpret_cast<const char*>(descriptor->name), "resolution") != 0)
            continue;
        if ((descriptor->cap & SANE_CAP_INACTIVE) ||
            !(descriptor->cap & SANE_CAP_SOFT_DETECT) ||
            (descriptor->type != SANE_TYPE_INT && descriptor->type != SANE_TYPE_FIXED))
            return;
        if (descriptor->constraint_type == SANE_CONSTRAINT_RANGE && descriptor->constraint.range) {
            const auto* range = descriptor->constraint.range;
            const double minimum = sane_numeric_value(range->min, descriptor->type);
            const double maximum = sane_numeric_value(range->max, descriptor->type);
            if (std::isfinite(minimum) && std::isfinite(maximum) &&
                minimum > 0.0 && maximum >= minimum && maximum <= 100000.0) {
                result.min_resolution_dpi = minimum;
                result.max_resolution_dpi = maximum;
            }
        } else if (descriptor->constraint_type == SANE_CONSTRAINT_WORD_LIST &&
                   descriptor->constraint.word_list && descriptor->constraint.word_list[0] > 0) {
            const auto count = std::min(descriptor->constraint.word_list[0], max_capability_entries);
            for (SANE_Word i = 1; i <= count; ++i) {
                const double value = sane_numeric_value(descriptor->constraint.word_list[i], descriptor->type);
                if (std::isfinite(value) && value > 0.0 && value <= 100000.0)
                    result.discrete_resolutions_dpi.push_back(value);
            }
            auto& values = result.discrete_resolutions_dpi;
            std::sort(values.begin(), values.end());
            values.erase(std::unique(values.begin(), values.end()), values.end());
        }
        return;
    }
}

std::string safe_string(const SANE_Char* value) {
    return value ? reinterpret_cast<const char*>(value) : std::string{};
}
} // namespace

std::vector<ScannerDevice> SaneScannerBackend::list_devices() {
    std::lock_guard<std::mutex> lock(sane_mutex());
    SaneSession session;
    const SANE_Device** devices = nullptr;
    const auto status = sane_get_devices(&devices, SANE_FALSE);
    if (status != SANE_STATUS_GOOD)
        throw ScannerError(std::string("SANE device discovery failed: ") + sane_strstatus(status));

    std::vector<ScannerDevice> result;
    if (!devices) return result;
    for (auto current = devices; *current != nullptr; ++current) {
        result.push_back(ScannerDevice{
            safe_string((*current)->name), safe_string((*current)->vendor),
            safe_string((*current)->model), safe_string((*current)->type)
        });
    }
    return result;
}

ScannerCapabilities SaneScannerBackend::get_capabilities(const std::string& device_id) {
    validate_device_id(device_id);
    std::lock_guard<std::mutex> lock(sane_mutex());
    SaneSession session;
    SaneHandle device(device_id);
    ScannerCapabilities result;
    collect_string_values(device.get(), "mode", result.modes);
    collect_string_values(device.get(), "source", result.sources);
    collect_resolution_values(device.get(), result);
    return result;
}

namespace {
std::vector<std::uint8_t> read_sane_frame_bytes(
    SANE_Handle handle,
    const SANE_Parameters& params,
    std::uint64_t max_frame_bytes
) {
    if (params.pixels_per_line <= 0 || params.lines <= 0 || params.bytes_per_line <= 0)
        throw ScannerError("Scanner returned invalid or variable scan dimensions");

    const auto width = static_cast<std::size_t>(params.pixels_per_line);
    const auto height = static_cast<std::size_t>(params.lines);
    const auto stride = static_cast<std::size_t>(params.bytes_per_line);
    if (stride < width || max_frame_bytes == 0 ||
        static_cast<std::uint64_t>(height) >
            max_frame_bytes / static_cast<std::uint64_t>(stride)) {
        throw ScannerError("Scanner frame exceeds the active safety limit or has invalid stride");
    }

    const auto frame_bytes = stride * height;
    std::vector<std::uint8_t> bytes;
    bytes.reserve(frame_bytes);
    std::array<SANE_Byte, 64 * 1024> chunk{};
    for (;;) {
        SANE_Int received = 0;
        const auto status = sane_read(
            handle, chunk.data(), static_cast<SANE_Int>(chunk.size()), &received
        );
        if (received < 0 || static_cast<std::size_t>(received) > chunk.size())
            throw ScannerError("Scanner returned an invalid read length");
        if (received > 0) {
            if (static_cast<std::size_t>(received) > frame_bytes - bytes.size())
                throw ScannerError("Scanner returned more image data than declared");
            bytes.insert(bytes.end(), chunk.begin(), chunk.begin() + received);
        }
        if (status == SANE_STATUS_EOF) break;
        if (status != SANE_STATUS_GOOD)
            throw ScannerError(std::string("Scanner read failed: ") + sane_strstatus(status));
        if (received == 0)
            throw ScannerError("Scanner returned no data before end-of-frame");
    }
    if (bytes.size() != frame_bytes)
        throw ScannerError("Scanner returned an incomplete image frame");
    return bytes;
}

void copy_planar_channel(
    const std::vector<std::uint8_t>& plane,
    std::size_t plane_stride,
    PixelBuffer& output,
    std::size_t channel
) {
    detail::interleave_planar_rgb_channel(
        plane, plane_stride, output.width, output.height,
        output.bytes, output.stride, channel
    );
}

ImagePage read_started_sane_page(
    SANE_Handle handle,
    const std::optional<double>& dpi_x,
    const std::optional<double>& dpi_y,
    std::uint64_t remaining_batch_bytes = max_scan_bytes
) {
    SANE_Parameters params{};
    auto status = sane_get_parameters(handle, &params);
    if (status != SANE_STATUS_GOOD)
        throw ScannerError(std::string("Cannot read scan parameters: ") + sane_strstatus(status));

    const auto page_byte_limit = std::min<std::uint64_t>(
        remaining_batch_bytes, static_cast<std::uint64_t>(max_scan_bytes)
    );
    if (page_byte_limit == 0)
        throw ScannerError("Scanner page exceeds the active safety limit");

    if (params.depth != 8)
        throw ScannerError("Scanner output must be 8-bit grayscale or RGB");

    if (params.format == SANE_FRAME_GRAY || params.format == SANE_FRAME_RGB) {
        if (!params.last_frame)
            throw ScannerError("Scanner returned a non-terminal interleaved frame");
        const std::size_t channels = params.format == SANE_FRAME_GRAY ? 1 : 3;
        if (params.pixels_per_line <= 0 ||
            static_cast<std::size_t>(params.pixels_per_line) >
                std::numeric_limits<std::size_t>::max() / channels)
            throw ScannerError("Scanner returned invalid scan dimensions");

        const auto width = static_cast<std::size_t>(params.pixels_per_line);
        const auto stride = static_cast<std::size_t>(params.bytes_per_line);
        const auto row_bytes = width * channels;
        if (stride < row_bytes)
            throw ScannerError("Scanner returned an invalid interleaved stride");

        PixelBuffer pixels;
        pixels.width = static_cast<std::uint32_t>(params.pixels_per_line);
        pixels.height = static_cast<std::uint32_t>(params.lines);
        pixels.stride = stride;
        pixels.format = channels == 1 ? PixelFormat::Gray8 : PixelFormat::RGB8;
        pixels.bytes = read_sane_frame_bytes(handle, params, page_byte_limit);
        if (!pixels.valid())
            throw ScannerError("Scanner produced an invalid pixel buffer");
        return ImagePage{std::move(pixels), dpi_x, dpi_y};
    }

    if (params.format != SANE_FRAME_RED || params.last_frame)
        throw ScannerError("Scanner returned an unsupported or incomplete frame sequence");

    if (params.pixels_per_line <= 0 || params.lines <= 0 ||
        static_cast<std::size_t>(params.pixels_per_line) >
            std::numeric_limits<std::size_t>::max() / 3)
        throw ScannerError("Scanner returned invalid planar RGB dimensions");

    const auto width = static_cast<std::size_t>(params.pixels_per_line);
    const auto height = static_cast<std::size_t>(params.lines);
    const auto output_stride = width * 3;
    if (height > std::numeric_limits<std::size_t>::max() / output_stride)
        throw ScannerError("Scanner planar RGB image size overflow");
    const auto output_bytes = output_stride * height;
    if (output_bytes >= page_byte_limit)
        throw ScannerError("Scanner planar RGB image exceeds the active safety limit");

    PixelBuffer pixels;
    pixels.width = static_cast<std::uint32_t>(params.pixels_per_line);
    pixels.height = static_cast<std::uint32_t>(params.lines);
    pixels.stride = output_stride;
    pixels.format = PixelFormat::RGB8;
    pixels.bytes.resize(output_bytes);

    auto plane_stride = static_cast<std::size_t>(params.bytes_per_line);
    auto plane = read_sane_frame_bytes(
        handle, params, page_byte_limit - static_cast<std::uint64_t>(output_bytes)
    );
    copy_planar_channel(plane, plane_stride, pixels, 0);
    std::vector<std::uint8_t>().swap(plane);

    for (const auto [expected_format, channel, should_be_last] : {
             std::tuple<SANE_Frame, std::size_t, bool>{SANE_FRAME_GREEN, 1, false},
             std::tuple<SANE_Frame, std::size_t, bool>{SANE_FRAME_BLUE, 2, true}}) {
        status = sane_start(handle);
        if (status != SANE_STATUS_GOOD)
            throw ScannerError(std::string("Cannot start next planar RGB frame: ") + sane_strstatus(status));
        SANE_Parameters next{};
        status = sane_get_parameters(handle, &next);
        if (status != SANE_STATUS_GOOD)
            throw ScannerError(std::string("Cannot read planar RGB parameters: ") + sane_strstatus(status));
        if (next.format != expected_format || next.depth != 8 ||
            next.pixels_per_line != params.pixels_per_line ||
            next.lines != params.lines || next.last_frame != should_be_last ||
            next.bytes_per_line < next.pixels_per_line)
            throw ScannerError("Scanner returned an inconsistent planar RGB frame sequence");

        plane_stride = static_cast<std::size_t>(next.bytes_per_line);
        plane = read_sane_frame_bytes(
            handle, next, page_byte_limit - static_cast<std::uint64_t>(output_bytes)
        );
        copy_planar_channel(plane, plane_stride, pixels, channel);
        std::vector<std::uint8_t>().swap(plane);
    }

    if (!pixels.valid())
        throw ScannerError("Scanner produced an invalid planar RGB image");
    return ImagePage{std::move(pixels), dpi_x, dpi_y};
}

} // namespace

ImagePage SaneScannerBackend::scan_one(const std::string& device_id, const ScanOptions& options) {
    validate_device_id(device_id);
    validate_scan_options(options);
    std::lock_guard<std::mutex> lock(sane_mutex());
    SaneSession session;
    SaneHandle device(device_id);

    if (options.resolution_dpi) set_resolution_option(device.get(), *options.resolution_dpi);
    if (options.mode) set_string_option(device.get(), "mode", *options.mode);
    if (options.source) set_string_option(device.get(), "source", *options.source);

    const auto [dpi_x, dpi_y] = read_scan_dpi(device.get());
    const auto status = sane_start(device.get());
    if (status != SANE_STATUS_GOOD)
        throw ScannerError(std::string("Cannot start scan: ") + sane_strstatus(status));
    try {
        auto page = read_started_sane_page(device.get(), dpi_x, dpi_y);
        // SANE requires cancellation/reset after a completed single-image transfer.
        sane_cancel(device.get());
        return page;
    } catch (...) {
        sane_cancel(device.get());
        throw;
    }
}

std::vector<ImagePage> SaneScannerBackend::scan_pages(
    const std::string& device_id,
    const ScanOptions& options
) {
    validate_device_id(device_id);
    validate_scan_options(options);

    // Never repeatedly start a flatbed. Batch acquisition is enabled only when
    // the caller explicitly selected a source whose name identifies an ADF.
    if (!options.source || !detail::is_adf_source(*options.source)) {
        return {scan_one(device_id, options)};
    }

    constexpr std::size_t max_adf_pages = 100;
    constexpr std::uint64_t max_batch_bytes = 4ULL * 1024ULL * 1024ULL * 1024ULL;
    std::lock_guard<std::mutex> lock(sane_mutex());
    SaneSession session;
    SaneHandle device(device_id);

    if (options.resolution_dpi) set_resolution_option(device.get(), *options.resolution_dpi);
    if (options.mode) set_string_option(device.get(), "mode", *options.mode);
    set_string_option(device.get(), "source", *options.source);

    const auto [dpi_x, dpi_y] = read_scan_dpi(device.get());
    return detail::collect_bounded_pages<ImagePage>(
        [&]() {
            const auto status = sane_start(device.get());
            if (status == SANE_STATUS_NO_DOCS) return false;
            if (status != SANE_STATUS_GOOD)
                throw ScannerError(
                    std::string("Cannot continue ADF scan: ") + sane_strstatus(status)
                );
            return true;
        },
        [&](std::uint64_t remaining_bytes) {
            return read_started_sane_page(
                device.get(), dpi_x, dpi_y, remaining_bytes
            );
        },
        [](const ImagePage& page) { return page.pixels.bytes.size(); },
        [&]() { sane_cancel(device.get()); },
        max_adf_pages,
        max_batch_bytes
    );
}

} // namespace emwat
