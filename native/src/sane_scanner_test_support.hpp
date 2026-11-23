#pragma once

#include "emwat/scanner.hpp"

#include <sane/sane.h>

#include <cstdint>
#include <optional>

namespace emwat::sane_detail {

// Narrow SANE I/O seam for deterministic page-reader tests. Production uses
// the real SANE functions; tests provide callbacks over an in-memory fake device.
struct SaneScanApi {
    SANE_Status (*start)(SANE_Handle);
    SANE_Status (*get_parameters)(SANE_Handle, SANE_Parameters*);
    SANE_Status (*read)(SANE_Handle, SANE_Byte*, SANE_Int, SANE_Int*);
    void (*cancel)(SANE_Handle);
    const SANE_Char* (*status_string)(SANE_Status);
};

[[nodiscard]] const SaneScanApi& real_sane_scan_api() noexcept;

[[nodiscard]] ImagePage read_started_sane_page(
    SANE_Handle handle,
    const std::optional<double>& dpi_x,
    const std::optional<double>& dpi_y,
    const SaneScanApi& api,
    std::uint64_t remaining_batch_bytes,
    bool allow_feeder_empty
);

} // namespace emwat::sane_detail
