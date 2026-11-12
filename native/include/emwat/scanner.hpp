#pragma once

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
class ScannerBackend {
public:
    virtual ~ScannerBackend() = default;
    [[nodiscard]] virtual std::vector<ScannerDevice> list_devices() = 0;
};

// SANE-backed discovery. Each call owns a complete SANE init/exit lifetime.
class SaneScannerBackend final : public ScannerBackend {
public:
    [[nodiscard]] std::vector<ScannerDevice> list_devices() override;
};

} // namespace emwat
