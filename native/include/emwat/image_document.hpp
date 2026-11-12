#pragma once

#include <cstddef>
#include <cstdint>
#include <optional>
#include <stdexcept>
#include <vector>

namespace emwat {

enum class PixelFormat { Gray8, RGB8, RGBA8 };
enum class QuarterTurn : unsigned { Clockwise90 = 1, HalfTurn = 2, Clockwise270 = 3 };
enum class FlipAxis { Horizontal, Vertical };

struct CropRect {
    std::uint32_t x{};
    std::uint32_t y{};
    std::uint32_t width{};
    std::uint32_t height{};
};

struct PixelBuffer {
    std::uint32_t width{};
    std::uint32_t height{};
    std::size_t stride{};
    PixelFormat format{PixelFormat::RGB8};
    std::vector<std::uint8_t> bytes;

    [[nodiscard]] std::size_t channels() const;
    [[nodiscard]] bool valid() const noexcept;
    void rotate(QuarterTurn turn);
    void flip(FlipAxis axis);
    void crop(CropRect region);
};

struct ImagePage {
    PixelBuffer pixels;
    std::optional<double> dpi_x;
    std::optional<double> dpi_y;
};

class ImageDocument {
public:
    [[nodiscard]] std::size_t page_count() const noexcept { return pages_.size(); }
    [[nodiscard]] std::size_t active_page() const noexcept { return active_page_; }
    [[nodiscard]] bool dirty() const noexcept { return dirty_; }
    [[nodiscard]] std::uint64_t generation() const noexcept { return generation_; }
    [[nodiscard]] const ImagePage& page(std::size_t index) const;

    void append_page(ImagePage page);
    void select_page(std::size_t index);
    void rotate_active(QuarterTurn turn);
    void flip_active(FlipAxis axis);
    void crop_active(CropRect region);
    void mark_saved() noexcept { dirty_ = false; }

private:
    std::vector<ImagePage> pages_;
    std::size_t active_page_{};
    bool dirty_{};
    std::uint64_t generation_{};
};

} // namespace emwat
