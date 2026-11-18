#include "emwat/scanner.hpp"

#include <stdexcept>
#include <utility>

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>

using namespace emwat;

class FakeScannerBackend final : public ScannerBackend {
public:
    std::vector<ScannerDevice> devices;
    bool fail{};

    ScannerCapabilities get_capabilities(const std::string&) override {
        if (fail) throw ScannerError("simulated capability failure");
        ScannerCapabilities result;
        result.modes = {"Color", "Gray"};
        result.sources = {"Flatbed"};
        result.min_resolution_dpi = 75.0;
        result.max_resolution_dpi = 600.0;
        result.discrete_resolutions_dpi = {75.0, 150.0, 300.0, 600.0};
        return result;
    }

    ImagePage scan_one(const std::string&, const ScanOptions& = {}) override {
        if (fail) throw ScannerError("simulated scan failure");
        PixelBuffer pixels{1, 1, 1, PixelFormat::Gray8, {42}};
        return ImagePage{std::move(pixels), 300.0, 300.0};
    }

    std::vector<ScannerDevice> list_devices() override {
        if (fail) throw ScannerError("simulated discovery failure");
        return devices;
    }
};

int main() {
    // Invalid identifiers must be rejected before touching the SANE runtime.
    SaneScannerBackend sane_backend;
    bool invalid_id_rejected = false;
    try { (void)sane_backend.get_capabilities(""); }
    catch (const ScannerError&) { invalid_id_rejected = true; }
    assert(invalid_id_rejected);
    invalid_id_rejected = false;
    try { (void)sane_backend.scan_one(""); }
    catch (const ScannerError&) { invalid_id_rejected = true; }
    assert(invalid_id_rejected);

    FakeScannerBackend backend;
    backend.devices.push_back({"test:scanner0", "Example", "Virtual Scanner", "flatbed"});
    const auto devices = backend.list_devices();
    assert(devices.size() == 1);
    assert(devices[0].id == "test:scanner0");
    assert(devices[0].vendor == "Example");
    assert(devices[0].model == "Virtual Scanner");
    assert(devices[0].type == "flatbed");

    backend.devices.clear();
    assert(backend.list_devices().empty());

    const auto capabilities = backend.get_capabilities("test:scanner0");
    assert(capabilities.modes.size() == 2);
    assert(capabilities.modes[0] == "Color");
    assert(capabilities.sources.size() == 1);
    assert(capabilities.min_resolution_dpi == 75.0);
    assert(capabilities.max_resolution_dpi == 600.0);
    assert(capabilities.discrete_resolutions_dpi.size() == 4);

    const auto scanned = backend.scan_one("test:scanner0");
    assert(scanned.pixels.valid());
    assert(scanned.pixels.bytes[0] == 42);
    assert(scanned.dpi_x == 300.0);
    assert(scanned.dpi_y == 300.0);

    backend.fail = true;
    bool threw = false;
    try { (void)backend.list_devices(); }
    catch (const ScannerError&) { threw = true; }
    assert(threw);
    threw = false;
    try { (void)backend.get_capabilities("test:scanner0"); }
    catch (const ScannerError&) { threw = true; }
    assert(threw);
    threw = false;
    try { (void)backend.scan_one("test:scanner0"); }
    catch (const ScannerError&) { threw = true; }
    assert(threw);
    return 0;
}
