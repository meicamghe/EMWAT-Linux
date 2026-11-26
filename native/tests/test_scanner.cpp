#include "emwat/scanner.hpp"
#include "emwat/scanner_detail.hpp"
#include "sane_scanner_test_support.hpp"

#include <algorithm>
#include <array>
#include <cstring>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>

using namespace emwat;

namespace {
struct FakeSaneFrame {
    SANE_Parameters parameters{};
    std::vector<std::uint8_t> bytes;
    SANE_Status terminal_status{SANE_STATUS_EOF};
};

struct FakeSaneState {
    std::vector<FakeSaneFrame> frames;
    std::size_t next_frame{};
    std::size_t current_frame{std::numeric_limits<std::size_t>::max()};
    std::size_t offset{};
    std::size_t start_calls{};
    std::size_t cancel_calls{};
    SANE_Status next_start_status{SANE_STATUS_GOOD};
};

FakeSaneState& fake_sane_state(SANE_Handle handle) {
    return *static_cast<FakeSaneState*>(handle);
}

SANE_Status fake_sane_start(SANE_Handle handle) {
    auto& state = fake_sane_state(handle);
    ++state.start_calls;
    if (state.next_start_status != SANE_STATUS_GOOD) {
        const auto status = state.next_start_status;
        state.next_start_status = SANE_STATUS_GOOD;
        return status;
    }
    if (state.next_frame >= state.frames.size()) return SANE_STATUS_NO_DOCS;
    state.current_frame = state.next_frame++;
    state.offset = 0;
    return SANE_STATUS_GOOD;
}

SANE_Status fake_sane_get_parameters(SANE_Handle handle, SANE_Parameters* params) {
    auto& state = fake_sane_state(handle);
    if (!params || state.current_frame >= state.frames.size())
        return SANE_STATUS_INVAL;
    *params = state.frames[state.current_frame].parameters;
    return SANE_STATUS_GOOD;
}

SANE_Status fake_sane_read(
    SANE_Handle handle, SANE_Byte* buffer, SANE_Int length, SANE_Int* received
) {
    auto& state = fake_sane_state(handle);
    if (!buffer || !received || length <= 0 ||
        state.current_frame >= state.frames.size())
        return SANE_STATUS_INVAL;
    const auto& frame = state.frames[state.current_frame];
    const auto remaining = frame.bytes.size() - state.offset;
    if (remaining == 0) {
        *received = 0;
        return frame.terminal_status;
    }
    const auto count = std::min<std::size_t>(
        static_cast<std::size_t>(length), remaining
    );
    std::memcpy(buffer, frame.bytes.data() + state.offset, count);
    state.offset += count;
    *received = static_cast<SANE_Int>(count);
    return state.offset == frame.bytes.size() ? frame.terminal_status : SANE_STATUS_GOOD;
}

void fake_sane_cancel(SANE_Handle handle) {
    ++fake_sane_state(handle).cancel_calls;
}

const SANE_Char* fake_sane_status_string(SANE_Status) {
    return "fake SANE status";
}

const sane_detail::SaneScanApi fake_sane_api{
    &fake_sane_start,
    &fake_sane_get_parameters,
    &fake_sane_read,
    &fake_sane_cancel,
    &fake_sane_status_string,
};

FakeSaneFrame fake_frame(
    SANE_Frame format,
    bool last_frame,
    std::vector<std::uint8_t> bytes,
    SANE_Status terminal_status = SANE_STATUS_EOF
) {
    FakeSaneFrame frame;
    frame.parameters.format = format;
    frame.parameters.last_frame = last_frame ? SANE_TRUE : SANE_FALSE;
    frame.parameters.depth = 8;
    frame.parameters.pixels_per_line = 2;
    frame.parameters.lines = 1;
    frame.parameters.bytes_per_line = 2;
    frame.bytes = std::move(bytes);
    frame.terminal_status = terminal_status;
    return frame;
}
} // namespace

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
    // Duplex sources fail before SANE initialization/device access; a one-sided
    // result must never be reported as a successful duplex batch.
    {
        SaneScannerBackend backend;
        ScanOptions options;
        options.source = "ADF Duplex";
        bool rejected = false;
        try {
            (void)backend.scan_pages("synthetic-device", options);
        } catch (const ScannerError& error) {
            rejected = std::string(error.what()) == "duplex_adf_batch_not_supported";
        }
        assert(rejected);
    }

    // The production page reader consumes ordered planar RGB frames through an injectable SANE API.
    {
        FakeSaneState state;
        state.frames = {
            fake_frame(SANE_FRAME_RED, false, {1, 2}),
            fake_frame(SANE_FRAME_GREEN, false, {3, 4}),
            fake_frame(SANE_FRAME_BLUE, true, {5, 6}),
        };
        const auto handle = reinterpret_cast<SANE_Handle>(&state);
        assert(fake_sane_api.start(handle) == SANE_STATUS_GOOD);
        const auto page = sane_detail::read_started_sane_page(
            handle, 300.0, 300.0, fake_sane_api, 1024 * 1024, false
        );
        assert(page.pixels.format == PixelFormat::RGB8);
        assert(page.pixels.width == 2 && page.pixels.height == 1);
        assert((page.pixels.bytes == std::vector<std::uint8_t>{1, 3, 5, 2, 4, 6}));
        assert(state.start_calls == 3);
        fake_sane_api.cancel(handle);
        assert(state.cancel_calls == 1);
    }

    // Planar output is rejected before allocation/read when the remaining budget is too small.
    {
        FakeSaneState state;
        state.frames = {fake_frame(SANE_FRAME_RED, false, {1, 2})};
        const auto handle = reinterpret_cast<SANE_Handle>(&state);
        assert(fake_sane_api.start(handle) == SANE_STATUS_GOOD);
        bool rejected = false;
        try {
            (void)sane_detail::read_started_sane_page(
                handle, std::nullopt, std::nullopt, fake_sane_api, 5, false
            );
        } catch (const ScannerError&) {
            rejected = true;
        }
        fake_sane_api.cancel(handle);
        assert(rejected);
        assert(state.offset == 0);
        assert(state.cancel_calls == 1);
    }

    // Interleaved RGB is preserved without channel reordering.
    {
        FakeSaneState state;
        auto frame = fake_frame(SANE_FRAME_RGB, true, {1, 2, 3, 4, 5, 6});
        frame.parameters.bytes_per_line = 6;
        state.frames = {std::move(frame)};
        const auto handle = reinterpret_cast<SANE_Handle>(&state);
        assert(fake_sane_api.start(handle) == SANE_STATUS_GOOD);
        const auto page = sane_detail::read_started_sane_page(
            handle, std::nullopt, std::nullopt, fake_sane_api, 1024, false
        );
        assert(page.pixels.format == PixelFormat::RGB8);
        assert((page.pixels.bytes == std::vector<std::uint8_t>{1, 2, 3, 4, 5, 6}));
        fake_sane_api.cancel(handle);
        assert(state.cancel_calls == 1);
    }

    // SANE permits unknown line counts. Interleaved frames are read to EOF,
    // then their height is derived from the complete row-stride byte count.
    {
        FakeSaneState state;
        auto frame = fake_frame(SANE_FRAME_GRAY, true, {1, 2, 3, 4});
        frame.parameters.lines = -1;
        state.frames = {std::move(frame)};
        const auto handle = reinterpret_cast<SANE_Handle>(&state);
        assert(fake_sane_api.start(handle) == SANE_STATUS_GOOD);
        const auto page = sane_detail::read_started_sane_page(
            handle, std::nullopt, std::nullopt, fake_sane_api, 1024, false
        );
        assert(page.pixels.width == 2 && page.pixels.height == 2);
        assert((page.pixels.bytes == std::vector<std::uint8_t>{1, 2, 3, 4}));
        fake_sane_api.cancel(handle);
        assert(state.cancel_calls == 1);
    }

    // Unknown-height planar RGB resolves the same height for all three planes.
    {
        FakeSaneState state;
        auto red = fake_frame(SANE_FRAME_RED, false, {1, 2, 3, 4});
        auto green = fake_frame(SANE_FRAME_GREEN, false, {5, 6, 7, 8});
        auto blue = fake_frame(SANE_FRAME_BLUE, true, {9, 10, 11, 12});
        red.parameters.lines = green.parameters.lines = blue.parameters.lines = -1;
        state.frames = {std::move(red), std::move(green), std::move(blue)};
        const auto handle = reinterpret_cast<SANE_Handle>(&state);
        assert(fake_sane_api.start(handle) == SANE_STATUS_GOOD);
        const auto page = sane_detail::read_started_sane_page(
            handle, std::nullopt, std::nullopt, fake_sane_api, 1024, false
        );
        assert(page.pixels.width == 2 && page.pixels.height == 2);
        assert((page.pixels.bytes == std::vector<std::uint8_t>{
            1, 5, 9, 2, 6, 10, 3, 7, 11, 4, 8, 12
        }));
        fake_sane_api.cancel(handle);
        assert(state.cancel_calls == 1);
    }

    // Variable-height output must end on a complete row and remain within budget.
    {
        FakeSaneState state;
        auto frame = fake_frame(SANE_FRAME_GRAY, true, {1, 2, 3});
        frame.parameters.lines = -1;
        state.frames = {std::move(frame)};
        const auto handle = reinterpret_cast<SANE_Handle>(&state);
        assert(fake_sane_api.start(handle) == SANE_STATUS_GOOD);
        bool rejected = false;
        try {
            (void)sane_detail::read_started_sane_page(
                handle, std::nullopt, std::nullopt, fake_sane_api, 1024, false
            );
        } catch (const ScannerError&) {
            rejected = true;
        }
        fake_sane_api.cancel(handle);
        assert(rejected);
        assert(state.cancel_calls == 1);
    }
    {
        FakeSaneState state;
        auto frame = fake_frame(SANE_FRAME_GRAY, true, {1, 2, 3, 4});
        frame.parameters.lines = -1;
        state.frames = {std::move(frame)};
        const auto handle = reinterpret_cast<SANE_Handle>(&state);
        assert(fake_sane_api.start(handle) == SANE_STATUS_GOOD);
        bool rejected = false;
        try {
            (void)sane_detail::read_started_sane_page(
                handle, std::nullopt, std::nullopt, fake_sane_api, 3, false
            );
        } catch (const ScannerError&) {
            rejected = true;
        }
        fake_sane_api.cancel(handle);
        assert(rejected);
        assert(state.cancel_calls == 1);
    }

    // Interleaved row padding is retained in PixelBuffer stride and bytes.
    {
        FakeSaneState state;
        auto frame = fake_frame(SANE_FRAME_RGB, true, {1, 2, 3, 0, 4, 5, 6, 0});
        frame.parameters.bytes_per_line = 8;
        state.frames = {std::move(frame)};
        const auto handle = reinterpret_cast<SANE_Handle>(&state);
        assert(fake_sane_api.start(handle) == SANE_STATUS_GOOD);
        const auto page = sane_detail::read_started_sane_page(
            handle, std::nullopt, std::nullopt, fake_sane_api, 1024, false
        );
        assert(page.pixels.stride == 8 && page.pixels.valid());
        assert((page.pixels.bytes == std::vector<std::uint8_t>{1, 2, 3, 0, 4, 5, 6, 0}));
        fake_sane_api.cancel(handle);
        assert(state.cancel_calls == 1);
    }

    // The production page reader and bounded collector cooperate across ADF pages.
    {
        FakeSaneState state;
        state.frames = {
            fake_frame(SANE_FRAME_GRAY, true, {10, 11}),
            fake_frame(SANE_FRAME_GRAY, true, {12, 13}),
        };
        const auto handle = reinterpret_cast<SANE_Handle>(&state);
        const auto pages = detail::collect_bounded_pages<ImagePage>(
            [&]() {
                const auto status = fake_sane_api.start(handle);
                if (status == SANE_STATUS_NO_DOCS) return false;
                if (status != SANE_STATUS_GOOD) throw ScannerError("fake_start_failed");
                return true;
            },
            [&](std::uint64_t remaining) {
                return sane_detail::read_started_sane_page(
                    handle, std::nullopt, std::nullopt, fake_sane_api, remaining, true
                );
            },
            [](const ImagePage& page) { return page.pixels.bytes.size(); },
            [&]() { fake_sane_api.cancel(handle); },
            10, 1024
        );
        assert(pages.size() == 2);
        assert((pages[0].pixels.bytes == std::vector<std::uint8_t>{10, 11}));
        assert((pages[1].pixels.bytes == std::vector<std::uint8_t>{12, 13}));
        assert(state.start_calls == 3);
        assert(state.cancel_calls == 1);
    }

    // SANE start failures propagate and still trigger one batch cancellation.
    {
        FakeSaneState state;
        state.next_start_status = SANE_STATUS_IO_ERROR;
        const auto handle = reinterpret_cast<SANE_Handle>(&state);
        bool rejected = false;
        try {
            (void)detail::collect_bounded_pages<ImagePage>(
                [&]() {
                    const auto status = fake_sane_api.start(handle);
                    if (status == SANE_STATUS_NO_DOCS) return false;
                    if (status != SANE_STATUS_GOOD) throw ScannerError("fake_start_failed");
                    return true;
                },
                [&](std::uint64_t remaining) {
                    return sane_detail::read_started_sane_page(
                        handle, std::nullopt, std::nullopt, fake_sane_api, remaining, true
                    );
                },
                [](const ImagePage& page) { return page.pixels.bytes.size(); },
                [&]() { fake_sane_api.cancel(handle); },
                10, 1024
            );
        } catch (const ScannerError&) {
            rejected = true;
        }
        assert(rejected);
        assert(state.cancel_calls == 1);
    }

    // A scanner I/O failure during frame read is not confused with feeder-empty.
    {
        FakeSaneState state;
        state.frames = {
            fake_frame(SANE_FRAME_GRAY, true, {42}, SANE_STATUS_IO_ERROR),
        };
        const auto handle = reinterpret_cast<SANE_Handle>(&state);
        bool rejected = false;
        try {
            (void)detail::collect_bounded_pages<ImagePage>(
                [&]() {
                    const auto status = fake_sane_api.start(handle);
                    if (status == SANE_STATUS_NO_DOCS) return false;
                    if (status != SANE_STATUS_GOOD) throw ScannerError("fake_start_failed");
                    return true;
                },
                [&](std::uint64_t remaining) {
                    return sane_detail::read_started_sane_page(
                        handle, std::nullopt, std::nullopt, fake_sane_api, remaining, true
                    );
                },
                [](const ImagePage& page) { return page.pixels.bytes.size(); },
                [&]() { fake_sane_api.cancel(handle); },
                10, 1024
            );
        } catch (const ScannerError&) {
            rejected = true;
        }
        assert(rejected);
        assert(state.cancel_calls == 1);
    }

    // Feeder-empty from sane_read before any bytes is a normal batch terminator.
    {
        FakeSaneState state;
        state.frames = {
            fake_frame(SANE_FRAME_GRAY, true, {}, SANE_STATUS_NO_DOCS),
        };
        const auto handle = reinterpret_cast<SANE_Handle>(&state);
        assert(fake_sane_api.start(handle) == SANE_STATUS_GOOD);
        bool feeder_empty = false;
        try {
            (void)sane_detail::read_started_sane_page(
                handle, std::nullopt, std::nullopt, fake_sane_api, 1024, true
            );
        } catch (const detail::ScanBatchEnd&) {
            feeder_empty = true;
        }
        fake_sane_api.cancel(handle);
        assert(feeder_empty);
        assert(state.cancel_calls == 1);
    }

    // NO_DOCS after partial bytes is not silently accepted as an empty feeder.
    {
        FakeSaneState state;
        state.frames = {
            fake_frame(SANE_FRAME_GRAY, true, {42}, SANE_STATUS_NO_DOCS),
        };
        const auto handle = reinterpret_cast<SANE_Handle>(&state);
        assert(fake_sane_api.start(handle) == SANE_STATUS_GOOD);
        bool rejected = false;
        try {
            (void)sane_detail::read_started_sane_page(
                handle, std::nullopt, std::nullopt, fake_sane_api, 1024, true
            );
        } catch (const ScannerError&) {
            rejected = true;
        }
        fake_sane_api.cancel(handle);
        assert(rejected);
        assert(state.cancel_calls == 1);
    }

    // An out-of-order planar channel fails the real reader and cancels the batch.
    {
        FakeSaneState state;
        state.frames = {
            fake_frame(SANE_FRAME_RED, false, {1, 2}),
            fake_frame(SANE_FRAME_BLUE, false, {3, 4}),
            fake_frame(SANE_FRAME_BLUE, true, {5, 6}),
        };
        const auto handle = reinterpret_cast<SANE_Handle>(&state);
        bool rejected = false;
        try {
            (void)detail::collect_bounded_pages<ImagePage>(
                [&]() {
                    const auto status = fake_sane_api.start(handle);
                    if (status == SANE_STATUS_NO_DOCS) return false;
                    if (status != SANE_STATUS_GOOD) throw ScannerError("fake_start_failed");
                    return true;
                },
                [&](std::uint64_t remaining) {
                    return sane_detail::read_started_sane_page(
                        handle, std::nullopt, std::nullopt, fake_sane_api, remaining, true
                    );
                },
                [](const ImagePage& page) { return page.pixels.bytes.size(); },
                [&]() { fake_sane_api.cancel(handle); },
                10, 1024
            );
        } catch (const ScannerError&) {
            rejected = true;
        }
        assert(rejected);
        assert(state.cancel_calls == 1);
    }

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

    // Exercise the ordered planar frame consumer with deterministic fake metadata.
    {
        struct FakeFrame {
            int format;
            int depth;
            int width;
            int lines;
            int stride;
            bool last;
        };
        const std::array<int, 3> formats{10, 11, 12};
        const std::array<FakeFrame, 3> frames{{
            {10, 8, 2, 1, 3, false},
            {11, 8, 2, 1, 3, false},
            {12, 8, 2, 1, 3, true},
        }};
        std::size_t next = 1;
        std::vector<std::size_t> consumed;
        detail::consume_planar_rgb_sequence<FakeFrame>(
            frames[0], formats,
            [&]() { return frames.at(next++); },
            [](const FakeFrame& frame, int expected_format, bool should_be_last) {
                if (!detail::planar_rgb_frame_matches(
                        frame.format, expected_format, frame.depth, 8,
                        frame.width, 2, frame.lines, 1, frame.stride,
                        frame.last, should_be_last
                    ))
                    throw std::runtime_error("invalid_fake_planar_frame");
            },
            [&](const FakeFrame&, std::size_t channel) { consumed.push_back(channel); }
        );
        assert((consumed == std::vector<std::size_t>{0, 1, 2}));
        assert(next == 3);
    }
    {
        struct FakeFrame { int format; bool last; };
        const std::array<int, 3> formats{10, 11, 12};
        const std::array<FakeFrame, 3> frames{{
            {10, false}, {12, false}, {12, true},
        }};
        std::size_t next = 1;
        std::vector<std::size_t> consumed;
        bool rejected = false;
        try {
            detail::consume_planar_rgb_sequence<FakeFrame>(
                frames[0], formats,
                [&]() { return frames.at(next++); },
                [](const FakeFrame& frame, int expected_format, bool should_be_last) {
                    if (frame.format != expected_format || frame.last != should_be_last)
                        throw std::runtime_error("invalid_fake_planar_frame");
                },
                [&](const FakeFrame&, std::size_t channel) { consumed.push_back(channel); }
            );
        } catch (const std::runtime_error& error) {
            rejected = std::string(error.what()) == "invalid_fake_planar_frame";
        }
        assert(rejected);
        assert((consumed == std::vector<std::size_t>{0}));
    }

    // Planar RGB page metadata must preserve exact RED/GREEN/BLUE order and flags.
    {
        constexpr int green = 3;
        constexpr int blue = 4;
        assert(detail::planar_rgb_frame_matches(
            green, green, 8, 8, 2, 2, 3, 3, 4, false, false
        ));
        assert(detail::planar_rgb_frame_matches(
            blue, blue, 8, 8, 2, 2, 3, 3, 4, true, true
        ));
        assert(!detail::planar_rgb_frame_matches(
            blue, green, 8, 8, 2, 2, 3, 3, 4, false, false
        ));
        assert(!detail::planar_rgb_frame_matches(
            green, green, 16, 8, 2, 2, 3, 3, 4, false, false
        ));
        assert(!detail::planar_rgb_frame_matches(
            green, green, 8, 8, 3, 2, 3, 3, 4, false, false
        ));
        assert(!detail::planar_rgb_frame_matches(
            green, green, 8, 8, 2, 2, 3, 3, 1, false, false
        ));
        assert(!detail::planar_rgb_frame_matches(
            green, green, 8, 8, 2, 2, 3, 3, 4, true, false
        ));
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
    assert(!detail::is_adf_source("ADF")); // ambiguous feeder mode is not assumed simplex
    assert(detail::is_adf_source("\tADF Front"));
    assert(!detail::is_adf_source("\t"));
    assert(detail::is_adf_source("ADF Front"));
    assert(detail::is_adf_source("ADF (Simplex)"));
    assert(detail::is_adf_source("ADF-Simplex"));
    assert(detail::is_adf_source("ADF: Front"));
    assert(!detail::is_adf_source("ADFree"));
    assert(!detail::is_adf_source("ADFScanner"));
    assert(!detail::is_adf_source("ADF Duplex"));
    assert(!detail::is_adf_source("Automatic Document Feeder (Duplex)"));
    assert(!detail::is_adf_source("Automatic Document Feeder"));
    assert(detail::is_adf_source("Automatic Document Feeder - Simplex"));
    assert(detail::is_adf_source("ADF one-sided"));
    assert(detail::is_adf_source("ADF single-sided"));
    assert(!detail::is_adf_source("ADF nonsimplex"));
    assert(!detail::is_adf_source("ADF frontline"));
    assert(!detail::is_adf_source("ADF one-sidedness"));
    assert(!detail::is_adf_source("Automatic Document FeederX"));
    assert(!detail::is_adf_source("automatic document feeder (duplex)"));
    assert(!detail::is_adf_source("Flatbed"));
    assert(!detail::is_adf_source("Not ADF"));
    assert(!detail::is_adf_source("Document Table"));
    assert(!detail::is_adf_source(""));
    assert(detail::is_duplex_source("ADF Duplex"));
    assert(detail::is_duplex_source("Automatic Document Feeder (Duplex)"));
    assert(detail::is_duplex_source("Double-Sided ADF"));
    assert(detail::is_duplex_source("two-sided feeder"));
    assert(!detail::is_duplex_source("ADF Front"));
    assert(!detail::is_duplex_source("Flatbed"));

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
