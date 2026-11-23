#pragma once

#include <cctype>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <optional>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace emwat::detail {

// SANE option descriptors originate in backend drivers. Bound string-buffer
// allocations so a malformed driver cannot request an unbounded allocation.
inline bool sane_string_option_size_valid(std::int32_t descriptor_size,
                                          std::size_t value_size) noexcept {
    constexpr std::int32_t max_option_bytes = 256;
    return descriptor_size > 0 && descriptor_size <= max_option_bytes &&
           value_size < static_cast<std::size_t>(descriptor_size);
}

// SANE fixed-point values are signed 16.16 integers. Convert without invoking
// SANE_FIX on values that would overflow its signed SANE_Word representation.
inline std::optional<std::int32_t> encode_sane_fixed_resolution(double dpi) noexcept {
    if (!std::isfinite(dpi) || dpi <= 0.0) return std::nullopt;

    constexpr double scale = 65536.0;
    const double scaled = dpi * scale;
    if (!std::isfinite(scaled)) return std::nullopt;

    const auto rounded = std::llround(scaled);
    if (rounded <= 0 ||
        rounded > static_cast<long long>(std::numeric_limits<std::int32_t>::max())) {
        return std::nullopt;
    }
    return static_cast<std::int32_t>(rounded);
}

class ScanBatchEnd final : public std::runtime_error {
public:
    ScanBatchEnd() : std::runtime_error("scan_batch_end_of_feeder") {}
};

template <typename Page, typename StartNext, typename ReadPage, typename PageSize, typename Cancel>
std::vector<Page> collect_bounded_pages(
    StartNext&& start_next,
    ReadPage&& read_page,
    PageSize&& page_size,
    Cancel&& cancel,
    std::size_t max_pages,
    std::uint64_t max_total_bytes
) {
    if (max_pages == 0 || max_total_bytes == 0)
        throw std::invalid_argument("invalid_scan_batch_limits");

    std::vector<Page> pages;
    std::uint64_t total_bytes = 0;
    bool cancel_called = false;
    const auto cancel_once = [&]() {
        if (!cancel_called) {
            cancel_called = true;
            cancel();
        }
    };

    try {
        while (pages.size() < max_pages) {
            if (!start_next()) {
                cancel_once();
                return pages;
            }
            Page page = read_page(max_total_bytes - total_bytes);
            const auto bytes = static_cast<std::uint64_t>(page_size(page));
            if (bytes > max_total_bytes - total_bytes)
                throw std::runtime_error("scan_batch_byte_limit_exceeded");
            total_bytes += bytes;
            pages.push_back(std::move(page));
        }

        // A final probe distinguishes exactly-at-limit completion from truncation.
        if (!start_next()) {
            cancel_once();
            return pages;
        }
        throw std::runtime_error("scan_batch_page_limit_exceeded");
    } catch (const ScanBatchEnd&) {
        cancel_once();
        return pages;
    } catch (...) {
        cancel_once();
        throw;
    }
}

inline bool planar_rgb_frame_matches(
    int actual_format,
    int expected_format,
    int actual_depth,
    int expected_depth,
    int actual_width,
    int expected_width,
    int actual_lines,
    int expected_lines,
    int actual_stride,
    bool actual_last_frame,
    bool expected_last_frame
) noexcept {
    return actual_format == expected_format &&
           actual_depth == expected_depth &&
           actual_width > 0 && actual_width == expected_width &&
           actual_lines > 0 && actual_lines == expected_lines &&
           actual_stride >= actual_width &&
           actual_last_frame == expected_last_frame;
}

inline void interleave_planar_rgb_channel(
    const std::vector<std::uint8_t>& plane,
    std::size_t plane_stride,
    std::size_t width,
    std::size_t height,
    std::vector<std::uint8_t>& output,
    std::size_t output_stride,
    std::size_t channel
) {
    if (width == 0 || height == 0 || width > std::numeric_limits<std::size_t>::max() / 3 ||
        plane_stride < width || output_stride < width * 3 || channel >= 3 ||
        plane_stride > std::numeric_limits<std::size_t>::max() / height ||
        output_stride > std::numeric_limits<std::size_t>::max() / height ||
        plane.size() < plane_stride * height || output.size() < output_stride * height)
        throw std::invalid_argument("invalid_planar_rgb_channel_buffer");

    for (std::size_t y = 0; y < height; ++y) {
        const auto source_offset = y * plane_stride;
        const auto target_offset = y * output_stride;
        for (std::size_t x = 0; x < width; ++x)
            output[target_offset + x * 3 + channel] = plane[source_offset + x];
    }
}

inline bool is_adf_source(const std::string& source) {
    std::string folded;
    folded.reserve(source.size());
    for (const unsigned char ch : source)
        folded.push_back(static_cast<char>(std::tolower(ch)));
    const auto first = folded.find_first_not_of(" \\t");
    if (first == std::string::npos) return false;
    const auto normalized = folded.substr(first);
    if (normalized.find("duplex") != std::string::npos ||
        normalized.find("double-sided") != std::string::npos ||
        normalized.find("two-sided") != std::string::npos)
        return false;
    return normalized.rfind("adf", 0) == 0 ||
           normalized.rfind("automatic document feeder", 0) == 0;
}

} // namespace emwat::detail
