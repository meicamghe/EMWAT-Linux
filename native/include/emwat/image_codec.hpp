#pragma once

#include "emwat/image_document.hpp"

#include <filesystem>
#include <stdexcept>
#include <vector>

namespace emwat {

enum class ImageFileFormat { Png, Jpeg, Tiff };

struct CodecOptions {
    int jpeg_quality{92};
};

class CodecError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

// Loads all pages transactionally. PNG/JPEG produce one page; TIFF may produce many.
[[nodiscard]] std::vector<ImagePage> load_image_file(const std::filesystem::path& path);
// TIFF writes every page; PNG/JPEG require exactly one page.
void save_image_file(const std::vector<ImagePage>& pages,
                     const std::filesystem::path& path,
                     CodecOptions options = {});
[[nodiscard]] ImageFileFormat image_format_from_extension(const std::filesystem::path& path);

} // namespace emwat
