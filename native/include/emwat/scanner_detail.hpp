#pragma once

#include <cmath>
#include <cstddef>
#include <cctype>
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
            Page page = read_page();
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
    } catch (...) {
        cancel_once();
        throw;
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
    return normalized.rfind("adf", 0) == 0 ||
           normalized.rfind("automatic document feeder", 0) == 0;
}

} // namespace emwat::detail
