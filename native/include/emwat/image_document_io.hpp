#pragma once

#include "emwat/image_codec.hpp"

namespace emwat {

// Decodes completely before replacing the current document. A failed load leaves it unchanged.
void load_into_document(ImageDocument& document, const std::filesystem::path& path);

// Saves a snapshot of every page. The document becomes clean only after a successful save.
void save_document(ImageDocument& document, const std::filesystem::path& path,
                   CodecOptions options = {});

} // namespace emwat
