#include "emwat/scanner.hpp"

#include <sane/sane.h>

#include <algorithm>
#include <array>
#include <limits>
#include <mutex>
#include <string>
#include <utility>

namespace emwat {
namespace {
constexpr std::size_t max_scan_bytes = 1024ULL * 1024ULL * 1024ULL;
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

ImagePage SaneScannerBackend::scan_one(const std::string& device_id) {
    if (device_id.empty()) throw ScannerError("scanner device id cannot be empty");
    std::lock_guard<std::mutex> lock(sane_mutex());
    SaneSession session;
    SaneHandle device(device_id);

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
    return ImagePage{std::move(pixels), std::nullopt, std::nullopt};
}

} // namespace emwat
