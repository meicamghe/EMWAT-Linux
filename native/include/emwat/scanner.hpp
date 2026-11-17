#pragma once

#include "emwat/image_document.hpp"

#include <optional>
#include <stdexcept>
#include <string>
#include <vector>
#include <utility>

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
struct ScannerCapabilities {
    std::vector<std::string> modes;
    std::vector<std::string> sources;
    std::optional<double> min_resolution_dpi;
    std::optional<double> max_resolution_dpi;
    std::vector<double> discrete_resolutions_dpi;
};

struct ScanOptions {
    std::optional<double> resolution_dpi;
    std::optional<std::string> mode;
    std::optional<std::string> source;
};

class ScannerBackend {
public:
    virtual ~ScannerBackend() = default;
    [[nodiscard]] virtual std::vector<ScannerDevice> list_devices() = 0;
    [[nodiscard]] virtual ScannerCapabilities get_capabilities(const std::string& device_id) = 0;
    // Captures one 8-bit grayscale or RGB frame using the device's current defaults.
    [[nodiscard]] virtual ImagePage scan_one(const std::string& device_id,
                                             const ScanOptions& options = {}) = 0;
    // Multi-frame devices (for example ADF scanners) may return several pages.
    // Backends without multi-frame support safely fall back to one page.
    [[nodiscard]] virtual std::vector<ImagePage> scan_all(
        const std::string& device_id, const ScanOptions& options = {}) {
        return {scan_one(device_id, options)};
    }
};

// SANE-backed discovery. Each call owns a complete SANE init/exit lifetime.
class SaneScannerBackend final : public ScannerBackend {
public:
    [[nodiscard]] std::vector<ScannerDevice> list_devices() override;
    [[nodiscard]] ScannerCapabilities get_capabilities(const std::string& device_id) override;
    [[nodiscard]] ImagePage scan_one(const std::string& device_id,
                                     const ScanOptions& options = {}) override;
    [[nodiscard]] std::vector<ImagePage> scan_all(
        const std::string& device_id, const ScanOptions& options = {}) override;
};

} // namespace emwat


// Acquire a complete scan before changing the document. Invalid/incomplete
// batches leave the existing document untouched.
inline void scan_into_document(
    ScannerBackend& scanner,
    const std::string& device_id,
    ImageDocument& document,
    const ScanOptions& options = {}) {
    auto pages = scanner.scan_all(device_id, options);
    document.append_pages(std::move(pages));
}
