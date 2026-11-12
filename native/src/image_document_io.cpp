#include "emwat/image_document_io.hpp"

#include <utility>

namespace emwat {

void load_into_document(ImageDocument& document, const std::filesystem::path& path) {
    auto decoded_pages = load_image_file(path);
    ImageDocument replacement;
    for (auto& page : decoded_pages) replacement.append_page(std::move(page));
    replacement.mark_saved();
    document = std::move(replacement);
}

void save_document(ImageDocument& document, const std::filesystem::path& path,
                   CodecOptions options) {
    std::vector<ImagePage> snapshot;
    snapshot.reserve(document.page_count());
    for (std::size_t i = 0; i < document.page_count(); ++i)
        snapshot.push_back(document.page(i));
    save_image_file(snapshot, path, options);
    document.mark_saved();
}

} // namespace emwat
