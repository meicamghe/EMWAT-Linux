#pragma once

#include "emwat/image_document.hpp"

#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

namespace emwat {

struct ScannerDevice {
    std::string id;
    std::string vendor;
    std::string model;
    std::string type;
};

class ScannerError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

// Device discovery is independent of image decoding and editor state.
struct ScanOptions {
    std::optional<double> resolution_dpi;
    std::optional<std::string> mode;
    std::optional<std::string> source;
};

class ScannerBackend {
public:
    virtual ~ScannerBackend() = default;
    [[nodiscard]] virtual std::vector<ScannerDevice> list_devices() = 0;
    // Captures one 8-bit grayscale or RGB frame using the device's current defaults.
    [[nodiscard]] virtual ImagePage scan_one(const std::string& device_id,
                                             const ScanOptions& options = {}) = 0;
};

// SANE-backed discovery. Each call owns a complete SANE init/exit lifetime.
class SaneScannerBackend final : public ScannerBackend {
public:
    [[nodiscard]] std::vector<ScannerDevice> list_devices() override;
    [[nodiscard]] ImagePage scan_one(const std::string& device_id,
                                     const ScanOptions& options = {}) override;
};

} // namespace emwat
