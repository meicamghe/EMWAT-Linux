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

    ImagePage scan_one(const std::string&) override {
        if (fail) throw ScannerError("simulated scan failure");
        PixelBuffer pixels{1, 1, 1, PixelFormat::Gray8, {42}};
        return ImagePage{std::move(pixels), std::nullopt, std::nullopt};
    }

    std::vector<ScannerDevice> list_devices() override {
        if (fail) throw ScannerError("simulated discovery failure");
        return devices;
    }
};

int main() {
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

    const auto scanned = backend.scan_one("test:scanner0");
    assert(scanned.pixels.valid());
    assert(scanned.pixels.bytes[0] == 42);

    backend.fail = true;
    bool threw = false;
    try { (void)backend.list_devices(); }
    catch (const ScannerError&) { threw = true; }
    assert(threw);
    threw = false;
    try { (void)backend.scan_one("test:scanner0"); }
    catch (const ScannerError&) { threw = true; }
    assert(threw);
    return 0;
}
