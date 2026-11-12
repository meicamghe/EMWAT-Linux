#include "emwat/scanner.hpp"

#include <sane/sane.h>

#include <algorithm>
#include <cmath>
#include <cstring>
#include <array>
#include <limits>
#include <mutex>
#include <string>
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
        descriptor->size <= 0 || value.size() >= static_cast<std::size_t>(descriptor->size))
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
    SANE_Word value = descriptor->type == SANE_TYPE_FIXED
        ? SANE_FIX(dpi) : static_cast<SANE_Word>(std::lround(dpi));
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
    if (device_id.empty()) throw ScannerError("scanner device id cannot be empty");
    std::lock_guard<std::mutex> lock(sane_mutex());
    SaneSession session;
    SaneHandle device(device_id);
    ScannerCapabilities result;
    collect_string_values(device.get(), "mode", result.modes);
    collect_string_values(device.get(), "source", result.sources);
    collect_resolution_values(device.get(), result);
    return result;
}

ImagePage SaneScannerBackend::scan_one(const std::string& device_id, const ScanOptions& options) {
    if (device_id.empty()) throw ScannerError("scanner device id cannot be empty");
    std::lock_guard<std::mutex> lock(sane_mutex());
    SaneSession session;
    SaneHandle device(device_id);

    if (options.resolution_dpi) set_resolution_option(device.get(), *options.resolution_dpi);
    if (options.mode) set_string_option(device.get(), "mode", *options.mode);
    if (options.source) set_string_option(device.get(), "source", *options.source);

    // Read the device-selected DPI after applying options; never infer it from a request.
    const auto [dpi_x, dpi_y] = read_scan_dpi(device.get());

    auto status = sane_start(device.get());
    if (status != SANE_STATUS_GOOD)
        throw ScannerError(std::string("Cannot start scan: ") + sane_strstatus(status));

    SANE_Parameters params{};
    status = sane_get_parameters(device.get(), &params);
    if (status != SANE_STATUS_GOOD) {
        sane_cancel(device.get());
        throw ScannerError(std::string("Cannot read scan parameters: ") + sane_strstatus(status));
    }

    PixelFormat format;
    std::size_t channels = 0;
    if (params.format == SANE_FRAME_GRAY && params.depth == 8) {
        format = PixelFormat::Gray8;
        channels = 1;
    } else if (params.format == SANE_FRAME_RGB && params.depth == 8) {
        format = PixelFormat::RGB8;
        channels = 3;
    } else {
        sane_cancel(device.get());
        throw ScannerError("Scanner output must be 8-bit grayscale or 8-bit RGB");
    }

    if (params.pixels_per_line <= 0 || params.lines <= 0 || params.bytes_per_line <= 0 ||
        static_cast<std::size_t>(params.pixels_per_line) >
            std::numeric_limits<std::size_t>::max() / channels) {
        sane_cancel(device.get());
        throw ScannerError("Scanner returned invalid or variable scan dimensions");
    }

    const auto width = static_cast<std::size_t>(params.pixels_per_line);
    const auto height = static_cast<std::size_t>(params.lines);
    const auto row_bytes = width * channels;
    const auto stride = static_cast<std::size_t>(params.bytes_per_line);
    if (stride < row_bytes || height > max_scan_bytes / stride) {
        sane_cancel(device.get());
        throw ScannerError("Scanner image exceeds the 1 GiB safety limit or has invalid stride");
    }

    PixelBuffer pixels;
    pixels.width = static_cast<std::uint32_t>(params.pixels_per_line);
    pixels.height = static_cast<std::uint32_t>(params.lines);
    pixels.stride = stride;
    pixels.format = format;
    pixels.bytes.reserve(stride * height);

    std::array<SANE_Byte, 64 * 1024> chunk{};
    for (;;) {
        SANE_Int received = 0;
        status = sane_read(device.get(), chunk.data(), static_cast<SANE_Int>(chunk.size()), &received);
        if (received < 0 || static_cast<std::size_t>(received) > chunk.size()) {
            sane_cancel(device.get());
            throw ScannerError("Scanner returned an invalid read length");
        }
        if (received > 0) {
            if (static_cast<std::size_t>(received) > stride * height - pixels.bytes.size()) {
                sane_cancel(device.get());
                throw ScannerError("Scanner returned more image data than declared");
            }
            pixels.bytes.insert(pixels.bytes.end(), chunk.begin(), chunk.begin() + received);
        }
        if (status == SANE_STATUS_EOF) break;
        if (status != SANE_STATUS_GOOD) {
            sane_cancel(device.get());
            throw ScannerError(std::string("Scanner read failed: ") + sane_strstatus(status));
        }
        if (received == 0) {
            sane_cancel(device.get());
            throw ScannerError("Scanner returned no data before end-of-frame");
        }
    }

    if (pixels.bytes.size() != stride * height) {
        throw ScannerError("Scanner returned an incomplete image frame");
    }
    if (!pixels.valid()) throw ScannerError("Scanner produced an invalid pixel buffer");
    return ImagePage{std::move(pixels), dpi_x, dpi_y};
}

} // namespace emwat
