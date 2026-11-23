#pragma once

#include <cmath>
#include <cstdint>
#include <limits>
#include <optional>

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

} // namespace emwat::detail
