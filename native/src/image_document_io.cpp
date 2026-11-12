#include "emwat/image_document_io.hpp"

#include <cerrno>
#include <cstdlib>
#include <filesystem>
#include <system_error>
#include <unistd.h>
#include <utility>
#include <vector>

namespace emwat {
namespace {

class TemporaryFile {
public:
    explicit TemporaryFile(const std::filesystem::path& destination) {
        const auto extension = destination.extension().string();
        const auto parent = destination.has_parent_path()
            ? destination.parent_path() : std::filesystem::path(".");
        auto pattern = (parent / (destination.stem().string() + ".tmp-XXXXXX" + extension)).string();
        std::vector<char> writable(pattern.begin(), pattern.end());
        writable.push_back('\0');
        const int descriptor = ::mkstemps(writable.data(), static_cast<int>(extension.size()));
        if (descriptor < 0)
            throw std::system_error(errno, std::generic_category(), "cannot create temporary image file");
        path_ = writable.data();
        if (::close(descriptor) != 0) {
            const int error = errno;
            std::error_code ignored;
            std::filesystem::remove(path_, ignored);
            throw std::system_error(error, std::generic_category(), "cannot close temporary image file");
        }
    }

    ~TemporaryFile() {
        if (!committed_) {
            std::error_code ignored;
            std::filesystem::remove(path_, ignored);
        }
    }

    const std::filesystem::path& path() const noexcept { return path_; }

    void commit_to(const std::filesystem::path& destination) {
        std::error_code error;
        std::filesystem::rename(path_, destination, error);
        if (error) throw std::system_error(error, "cannot atomically replace image file");
        committed_ = true;
    }

private:
    std::filesystem::path path_;
    bool committed_{false};
};

} // namespace

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

    TemporaryFile temporary(path);
    save_image_file(snapshot, temporary.path(), options);
    temporary.commit_to(path);
    document.mark_saved();
}

} // namespace emwat
