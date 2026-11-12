#include "emwat/image_document.hpp"

#include <limits>
#include <utility>

namespace emwat {
namespace {
std::uint32_t bytes_per_pixel(PixelFormat format) {
    switch (format) {
    case PixelFormat::Gray8: return 1;
    case PixelFormat::RGB8: return 3;
    case PixelFormat::RGBA8: return 4;
    }
    throw std::invalid_argument("unsupported pixel format");
}

std::size_t checked_size(std::uint32_t width, std::uint32_t height, std::size_t channels) {
    if (width == 0 || height == 0) throw std::invalid_argument("pixel dimensions must be non-zero");
    const auto row = static_cast<std::size_t>(width) * channels;
    if (row > std::numeric_limits<std::size_t>::max() / height)
        throw std::overflow_error("pixel buffer size overflow");
    return row * height;
}
} // namespace

std::size_t PixelBuffer::channels() const { return bytes_per_pixel(format); }

bool PixelBuffer::valid() const noexcept {
    try {
        const auto channel_count = bytes_per_pixel(format);
        if (width == 0 || height == 0) return false;
        const auto min_stride = static_cast<std::size_t>(width) * channel_count;
        if (stride < min_stride || stride > std::numeric_limits<std::size_t>::max() / height) return false;
        return bytes.size() >= stride * height;
    } catch (...) { return false; }
}

void PixelBuffer::rotate(QuarterTurn turn) {
    if (!valid()) throw std::invalid_argument("invalid pixel buffer");
    const auto turns = static_cast<unsigned>(turn);
    if (turns < 1 || turns > 3) throw std::invalid_argument("invalid quarter turn");
    if (turns == 2) {
        const auto bpp = channels();
        std::vector<std::uint8_t> output(bytes.size());
        for (std::uint32_t y = 0; y < height; ++y)
            for (std::uint32_t x = 0; x < width; ++x) {
                const auto src = static_cast<std::size_t>(y) * stride + static_cast<std::size_t>(x) * bpp;
                const auto dst = static_cast<std::size_t>(height - 1 - y) * stride + static_cast<std::size_t>(width - 1 - x) * bpp;
                for (std::size_t c = 0; c < bpp; ++c) output[dst + c] = bytes[src + c];
            }
        bytes.swap(output);
        return;
    }
    const auto bpp = channels();
    const auto new_width = height;
    const auto new_height = width;
    const auto new_stride = static_cast<std::size_t>(new_width) * bpp;
    std::vector<std::uint8_t> output(checked_size(new_width, new_height, bpp));
    for (std::uint32_t y = 0; y < height; ++y)
        for (std::uint32_t x = 0; x < width; ++x) {
            const auto src = static_cast<std::size_t>(y) * stride + static_cast<std::size_t>(x) * bpp;
            const auto nx = turns == 1 ? height - 1 - y : y;
            const auto ny = turns == 1 ? x : width - 1 - x;
            const auto dst = static_cast<std::size_t>(ny) * new_stride + static_cast<std::size_t>(nx) * bpp;
            for (std::size_t c = 0; c < bpp; ++c) output[dst + c] = bytes[src + c];
        }
    width = new_width;
    height = new_height;
    stride = new_stride;
    bytes.swap(output);
}

void PixelBuffer::flip(FlipAxis axis) {
    if (!valid()) throw std::invalid_argument("invalid pixel buffer");
    if (axis != FlipAxis::Horizontal && axis != FlipAxis::Vertical)
        throw std::invalid_argument("invalid flip axis");
    const auto bpp = channels();
    std::vector<std::uint8_t> output(bytes.size());
    for (std::uint32_t y = 0; y < height; ++y)
        for (std::uint32_t x = 0; x < width; ++x) {
            const auto nx = axis == FlipAxis::Horizontal ? width - 1 - x : x;
            const auto ny = axis == FlipAxis::Vertical ? height - 1 - y : y;
            const auto src = static_cast<std::size_t>(y) * stride + static_cast<std::size_t>(x) * bpp;
            const auto dst = static_cast<std::size_t>(ny) * stride + static_cast<std::size_t>(nx) * bpp;
            for (std::size_t c = 0; c < bpp; ++c) output[dst + c] = bytes[src + c];
        }
    bytes.swap(output);
}

void PixelBuffer::crop(CropRect region) {
    if (!valid()) throw std::invalid_argument("invalid pixel buffer");
    if (region.width == 0 || region.height == 0 || region.x >= width || region.y >= height ||
        region.width > width - region.x || region.height > height - region.y)
        throw std::out_of_range("crop rectangle is outside the image");
    const auto bpp = channels();
    const auto new_stride = static_cast<std::size_t>(region.width) * bpp;
    std::vector<std::uint8_t> output(checked_size(region.width, region.height, bpp));
    for (std::uint32_t y = 0; y < region.height; ++y) {
        const auto src = static_cast<std::size_t>(region.y + y) * stride +
                         static_cast<std::size_t>(region.x) * bpp;
        const auto dst = static_cast<std::size_t>(y) * new_stride;
        std::copy_n(bytes.begin() + static_cast<std::ptrdiff_t>(src),
                    static_cast<std::size_t>(region.width) * bpp,
                    output.begin() + static_cast<std::ptrdiff_t>(dst));
    }
    width = region.width;
    height = region.height;
    stride = new_stride;
    bytes.swap(output);
}

const ImagePage& ImageDocument::page(std::size_t index) const {
    if (index >= pages_.size()) throw std::out_of_range("page index out of range");
    return pages_[index];
}
ImagePage& ImageDocument::page(std::size_t index) {
    if (index >= pages_.size()) throw std::out_of_range("page index out of range");
    return pages_[index];
}
void ImageDocument::append_page(ImagePage value) {
    if (!value.pixels.valid()) throw std::invalid_argument("cannot append invalid image page");
    pages_.push_back(std::move(value));
    if (pages_.size() == 1) active_page_ = 0;
    dirty_ = true;
    ++generation_;
}
void ImageDocument::select_page(std::size_t index) {
    if (index >= pages_.size()) throw std::out_of_range("page index out of range");
    if (active_page_ != index) { active_page_ = index; ++generation_; }
}
void ImageDocument::rotate_active(QuarterTurn turn) {
    if (pages_.empty()) throw std::logic_error("document has no pages");
    auto& image = pages_.at(active_page_);
    image.pixels.rotate(turn);
    if (turn == QuarterTurn::Clockwise90 || turn == QuarterTurn::Clockwise270)
        std::swap(image.dpi_x, image.dpi_y);
    dirty_ = true;
    ++generation_;
}
void ImageDocument::flip_active(FlipAxis axis) {
    if (pages_.empty()) throw std::logic_error("document has no pages");
    pages_.at(active_page_).pixels.flip(axis);
    dirty_ = true;
    ++generation_;
}
void ImageDocument::crop_active(CropRect region) {
    if (pages_.empty()) throw std::logic_error("document has no pages");
    pages_.at(active_page_).pixels.crop(region);
    dirty_ = true;
    ++generation_;
}

} // namespace emwat
