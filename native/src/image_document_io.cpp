#include "emwat/image_document_io.hpp"

#include <cerrno>
#include <cstdlib>
#include <filesystem>
#include <system_error>
#include <unistd.h>
#include <fcntl.h>
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
        // Flush encoded bytes before the atomic name replacement.
        const int file_descriptor = ::open(path_.c_str(), O_RDONLY | O_CLOEXEC);
        if (file_descriptor < 0)
            throw std::system_error(errno, std::generic_category(), "cannot reopen temporary image file");
        if (::fsync(file_descriptor) != 0) {
            const int error = errno;
            (void)::close(file_descriptor);
            throw std::system_error(error, std::generic_category(), "cannot sync temporary image file");
        }
        if (::close(file_descriptor) != 0)
            throw std::system_error(errno, std::generic_category(), "cannot close synced image file");

        std::error_code error;
        std::filesystem::rename(path_, destination, error);
        if (error) throw std::system_error(error, "cannot atomically replace image file");
        committed_ = true;

        // Persist the directory entry update as well as the file contents.
        const auto parent = destination.has_parent_path()
            ? destination.parent_path() : std::filesystem::path(".");
        const int directory_descriptor = ::open(parent.c_str(), O_RDONLY | O_DIRECTORY | O_CLOEXEC);
        if (directory_descriptor < 0)
            throw std::system_error(errno, std::generic_category(), "cannot open image directory for sync");
        if (::fsync(directory_descriptor) != 0) {
            const int sync_error = errno;
            (void)::close(directory_descriptor);
            throw std::system_error(sync_error, std::generic_category(), "cannot sync image directory");
        }
        if (::close(directory_descriptor) != 0)
            throw std::system_error(errno, std::generic_category(), "cannot close synced image directory");
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
    const auto snapshot_generation = document.generation();
    std::vector<ImagePage> snapshot;
    snapshot.reserve(document.page_count());
    for (std::size_t i = 0; i < document.page_count(); ++i)
        snapshot.push_back(document.page(i));

    TemporaryFile temporary(path);
    save_image_file(snapshot, temporary.path(), options);
    temporary.commit_to(path);
    // A newer edit may have occurred while the snapshot was being encoded.
    // The file is valid, but the live document must remain dirty in that case.
    (void)document.mark_saved_if_generation(snapshot_generation);
}

} // namespace emwat
