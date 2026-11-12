#include "emwat/image_document.hpp"

#include <cstdint>
#include <stdexcept>
#include <vector>

// Keep assertions active in Release builds so the test executable really tests.
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>

using namespace emwat;

static PixelBuffer sample() {
    // 2x3 Gray8 image: 1 2 / 3 4 / 5 6
    return PixelBuffer{2, 3, 2, PixelFormat::Gray8, {1, 2, 3, 4, 5, 6}};
}

int main() {
    {
        auto image = sample();
        image.rotate(QuarterTurn::Clockwise90);
        assert(image.width == 3 && image.height == 2 && image.stride == 3);
        assert((image.bytes == std::vector<std::uint8_t>{5, 3, 1, 6, 4, 2}));
    }
    {
        auto image = sample();
        image.rotate(QuarterTurn::Clockwise270);
        assert(image.width == 3 && image.height == 2);
        assert((image.bytes == std::vector<std::uint8_t>{2, 4, 6, 1, 3, 5}));
    }
    {
        auto image = sample();
        image.flip(FlipAxis::Horizontal);
        assert((image.bytes == std::vector<std::uint8_t>{2, 1, 4, 3, 6, 5}));
    }
    {
        auto image = sample();
        image.crop(CropRect{1, 1, 1, 2});
        assert(image.width == 1 && image.height == 2 && image.stride == 1);
        assert((image.bytes == std::vector<std::uint8_t>{4, 6}));
    }
    {
        auto image = sample();
        bool threw = false;
        try { image.crop(CropRect{1, 2, 2, 1}); }
        catch (const std::out_of_range&) { threw = true; }
        assert(threw && image.width == 2 && image.height == 3);
    }
    {
        // Padded RGB rows: crop must ignore padding and retain channel groups.
        PixelBuffer image{2, 2, 8, PixelFormat::RGB8,
                          {1, 2, 3, 4, 5, 6, 99, 99, 7, 8, 9, 10, 11, 12, 99, 99}};
        image.crop(CropRect{1, 0, 1, 2});
        assert(image.width == 1 && image.height == 2 && image.stride == 3);
        assert((image.bytes == std::vector<std::uint8_t>{4, 5, 6, 10, 11, 12}));
    }
    {
        ImageDocument doc;
        doc.append_page(ImagePage{sample(), 300.0, 200.0});
        assert(doc.page_count() == 1 && doc.active_page() == 0 && doc.dirty());
        doc.mark_saved();
        doc.rotate_active(QuarterTurn::Clockwise90);
        assert(doc.dirty() && doc.generation() == 2);
        assert(doc.page(0).pixels.width == 3 && doc.page(0).pixels.height == 2);
        assert(doc.page(0).dpi_x == 200.0 && doc.page(0).dpi_y == 300.0);
        doc.mark_saved();
        doc.crop_active(CropRect{0, 0, 2, 1});
        assert(doc.dirty() && doc.generation() == 3);
        assert(doc.page(0).pixels.width == 2 && doc.page(0).pixels.height == 1);
    }
    {
        bool threw = false;
        try { (void)sample().rotate(static_cast<QuarterTurn>(0)); }
        catch (const std::invalid_argument&) { threw = true; }
        assert(threw);
    }
    return 0;
}
