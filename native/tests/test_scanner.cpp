#include "emwat/scanner.hpp"
#include "emwat/scanner_detail.hpp"

#include <stdexcept>
#include <limits>
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
    // SANE backend string-option sizes are untrusted; reject oversized allocations.
    assert(detail::sane_string_option_size_valid(16, 15));
    assert(!detail::sane_string_option_size_valid(16, 16));
    assert(!detail::sane_string_option_size_valid(0, 0));
    assert(!detail::sane_string_option_size_valid(-1, 0));
    assert(detail::sane_string_option_size_valid(256, 255));
    assert(!detail::sane_string_option_size_valid(257, 1));
    assert(!detail::sane_string_option_size_valid(256, 256));

    // Exercise the real bounded batch state machine without a physical scanner.
    {
        const std::vector<bool> starts{true, true, false};
        std::size_t start_index = 0;
        std::size_t read_index = 0;
        bool cancelled = false;
        const auto pages = detail::collect_bounded_pages<int>(
            [&]() { return starts.at(start_index++); },
            [&](std::uint64_t) { return read_index++ == 0 ? 4 : 6; },
            [](int bytes) { return static_cast<std::size_t>(bytes); },
            [&]() { cancelled = true; },
            10, 32
        );
        assert((pages == std::vector<int>{4, 6}));
        assert(start_index == 3);
        assert(read_index == 2);
        assert(cancelled);
    }
    {
        const std::vector<bool> starts{true, true, false};
        std::size_t start_index = 0;
        bool cancelled = false;
        const auto pages = detail::collect_bounded_pages<int>(
            [&]() { return starts.at(start_index++); },
            [](std::uint64_t) { return 1; },
            [](int bytes) { return static_cast<std::size_t>(bytes); },
            [&]() { cancelled = true; },
            2, 2
        );
        assert(pages.size() == 2);
        assert(cancelled);
    }
    {
        const std::vector<bool> starts{true, true, true};
        std::size_t start_index = 0;
        bool cancelled = false;
        bool rejected = false;
        try {
            (void)detail::collect_bounded_pages<int>(
                [&]() { return starts.at(start_index++); },
                [](std::uint64_t) { return 1; },
                [](int bytes) { return static_cast<std::size_t>(bytes); },
                [&]() { cancelled = true; },
                2, 8
            );
        } catch (const std::runtime_error& error) {
            rejected = std::string(error.what()) == "scan_batch_page_limit_exceeded";
        }
        assert(rejected);
        assert(cancelled);
    }
    {
        const std::vector<bool> starts{true, true};
        std::size_t start_index = 0;
        bool cancelled = false;
        bool rejected = false;
        try {
            (void)detail::collect_bounded_pages<int>(
                [&]() { return starts.at(start_index++); },
                [&](std::uint64_t remaining) {
                    assert(remaining == (start_index == 1 ? 5U : 1U));
                    return start_index == 1 ? 4 : 2;
                },
                [](int bytes) { return static_cast<std::size_t>(bytes); },
                [&]() { cancelled = true; },
                10, 5
            );
        } catch (const std::runtime_error& error) {
            rejected = std::string(error.what()) == "scan_batch_byte_limit_exceeded";
        }
        assert(rejected);
        assert(cancelled);
    }
    {
        bool cancelled = false;
        bool rejected = false;
        try {
            (void)detail::collect_bounded_pages<int>(
                []() { return true; },
                [](std::uint64_t) -> int {
                    throw std::runtime_error("synthetic_read_failure");
                },
                [](int bytes) { return static_cast<std::size_t>(bytes); },
                [&]() { cancelled = true; },
                10, 32
            );
        } catch (const std::runtime_error& error) {
            rejected = std::string(error.what()) == "synthetic_read_failure";
        }
        assert(rejected);
        assert(cancelled);
    }

    {
        bool cancelled = false;
        const auto pages = detail::collect_bounded_pages<int>(
            []() { return false; },
            [](std::uint64_t) { return 1; },
            [](int bytes) { return static_cast<std::size_t>(bytes); },
            [&]() { cancelled = true; },
            10, 32
        );
        assert(pages.empty());
        assert(cancelled);
    }
    {
        bool cancelled = false;
        bool rejected = false;
        try {
            (void)detail::collect_bounded_pages<int>(
                []() -> bool { throw ScannerError("synthetic_feeder_jam"); },
                [](std::uint64_t) { return 1; },
                [](int bytes) { return static_cast<std::size_t>(bytes); },
                [&]() { cancelled = true; },
                10, 32
            );
        } catch (const ScannerError& error) {
            rejected = std::string(error.what()) == "synthetic_feeder_jam";
        }
        assert(rejected);
        assert(cancelled);
    }

    {
        std::size_t reads = 0;
        bool cancelled = false;
        const auto pages = detail::collect_bounded_pages<int>(
            []() { return true; },
            [&](std::uint64_t) -> int {
                if (reads++ == 0) return 7;
                throw detail::ScanBatchEnd{};
            },
            [](int bytes) { return static_cast<std::size_t>(bytes); },
            [&]() { cancelled = true; },
            10, 32
        );
        assert((pages == std::vector<int>{7}));
        assert(cancelled);
    }

    // Planar RGB frames are interleaved by channel and row; padding is ignored.
    {
        const std::vector<std::uint8_t> red{1, 2, 99, 3, 4, 99};
        const std::vector<std::uint8_t> green{5, 6, 99, 7, 8, 99};
        const std::vector<std::uint8_t> blue{9, 10, 99, 11, 12, 99};
        std::vector<std::uint8_t> rgb(12, 0);
        detail::interleave_planar_rgb_channel(red, 3, 2, 2, rgb, 6, 0);
        detail::interleave_planar_rgb_channel(green, 3, 2, 2, rgb, 6, 1);
        detail::interleave_planar_rgb_channel(blue, 3, 2, 2, rgb, 6, 2);
        assert((rgb == std::vector<std::uint8_t>{
            1, 5, 9, 2, 6, 10, 3, 7, 11, 4, 8, 12
        }));
    }
    {
        bool rejected = false;
        try {
            const std::vector<std::uint8_t> short_plane{1};
            std::vector<std::uint8_t> rgb(6, 0);
            detail::interleave_planar_rgb_channel(short_plane, 2, 2, 1, rgb, 6, 0);
        } catch (const std::invalid_argument&) {
            rejected = true;
        }
        assert(rejected);
    }

    // Only explicit feeder-source names may activate repeated page acquisition.
    assert(detail::is_adf_source("ADF"));
    assert(detail::is_adf_source("ADF Front"));
    assert(detail::is_adf_source("ADF Duplex"));
    assert(detail::is_adf_source("Automatic Document Feeder"));
    assert(detail::is_adf_source("automatic document feeder (duplex)"));
    assert(!detail::is_adf_source("Flatbed"));
    assert(!detail::is_adf_source("Not ADF"));
    assert(!detail::is_adf_source("Document Table"));
    assert(!detail::is_adf_source(""));

    // Fixed-point DPI conversion must not overflow signed 16.16 SANE_Word.

    // SANE_TYPE_FIXED uses a signed 16.16 SANE_Word. Keep conversion in range
    // and reject non-finite values without relying on an overflowing SANE_FIX.
    assert(detail::encode_sane_fixed_resolution(300.0).value() == 300 * 65536);
    assert(detail::encode_sane_fixed_resolution(32767.0).has_value());
    assert(!detail::encode_sane_fixed_resolution(32768.0).has_value());
    assert(!detail::encode_sane_fixed_resolution(
        std::numeric_limits<double>::infinity()).has_value());
    assert(!detail::encode_sane_fixed_resolution(
        std::numeric_limits<double>::quiet_NaN()).has_value());

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

    invalid_id_rejected = false;
    try { (void)sane_backend.get_capabilities("test:\nscanner"); }
    catch (const ScannerError&) { invalid_id_rejected = true; }
    assert(invalid_id_rejected);
    invalid_id_rejected = false;
    try { (void)sane_backend.scan_one(std::string("test:scanner\0hidden", 19)); }
    catch (const ScannerError&) { invalid_id_rejected = true; }
    assert(invalid_id_rejected);

    // Invalid scan options are rejected before SANE initialization/open.
    const auto expect_invalid_options = [&](const ScanOptions& options) {
        bool rejected = false;
        try { (void)sane_backend.scan_one("test:nonexistent", options); }
        catch (const ScannerError&) { rejected = true; }
        assert(rejected);
    };
    expect_invalid_options(ScanOptions{std::numeric_limits<double>::quiet_NaN(), {}, {}});
    expect_invalid_options(ScanOptions{std::numeric_limits<double>::infinity(), {}, {}});
    expect_invalid_options(ScanOptions{0.0, {}, {}});
    expect_invalid_options(ScanOptions{100001.0, {}, {}});
    expect_invalid_options(ScanOptions{{}, std::string{}, {}});
    expect_invalid_options(ScanOptions{{}, std::string("Color\n"), {}});
    expect_invalid_options(ScanOptions{{}, {}, std::string("Flatbed\0hidden", 15)});

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

    // Legacy backends inherit a safe one-page batch fallback.
    const auto scanned_pages = backend.scan_pages("test:scanner0");
    assert(scanned_pages.size() == 1);
    assert(scanned_pages[0].pixels.valid());
    assert(scanned_pages[0].pixels.bytes[0] == 42);

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
