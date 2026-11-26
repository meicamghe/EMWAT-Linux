#pragma once

#include <filesystem>
#include <optional>
#include <stdexcept>
#include <string>
#include <variant>
#include <vector>

namespace emwat {

// EMWAT distinguishes a collection of page files from one multipage result.
// Keep this output ownership model separate from ImageDocument and scanner
// hardware/session state; exact Windows naming rules remain under investigation.
struct SinglePageFileSet {
    std::vector<std::filesystem::path> files;
};

struct MultiPageFile {
    std::filesystem::path file;
};

using ScanOutput = std::variant<SinglePageFileSet, MultiPageFile>;

// Raw response XML metadata recovered from TXMLResponseScanType and its
// nested TXMLScanedImageType. Keep each field independent: no status enum,
// encoding-to-extension mapping, or path inference is assumed here.
struct ScanResponseImageMetadata {
    std::optional<std::string> image_name;
    std::optional<std::string> encoding;
};

struct ScanResponseMetadata {
    std::optional<std::string> status;
    std::optional<std::string> error_code;
    std::optional<ScanResponseImageMetadata> scanned_image;
};

struct ScanResult {
    ScanOutput output;
    std::optional<std::string> scan_path;
    std::optional<std::string> response_filename;
    std::optional<ScanResponseMetadata> response_metadata{};

    [[nodiscard]] bool is_single_page_file_set() const noexcept {
        return std::holds_alternative<SinglePageFileSet>(output);
    }

    [[nodiscard]] bool is_multipage_file() const noexcept {
        return std::holds_alternative<MultiPageFile>(output);
    }

    // Counts physical output files, not image pages. A multipage file may hold
    // several pages; its internal page count is intentionally not inferred here.
    [[nodiscard]] std::size_t output_file_count() const noexcept {
        if (const auto* set = std::get_if<SinglePageFileSet>(&output))
            return set->files.size();
        return 1;
    }

    // Validate structural invariants only. This does not touch the filesystem
    // or assert undocumented EMWAT path/filename/response semantics.
    void validate() const {
        if (scan_path && scan_path->empty())
            throw std::invalid_argument("scan_path_must_not_be_empty");
        if (response_filename && response_filename->empty())
            throw std::invalid_argument("response_filename_must_not_be_empty");

        if (const auto* set = std::get_if<SinglePageFileSet>(&output)) {
            if (set->files.empty())
                throw std::invalid_argument("single_page_file_set_must_not_be_empty");
            for (const auto& path : set->files) {
                if (path.empty())
                    throw std::invalid_argument("scan_result_file_path_must_not_be_empty");
            }
            return;
        }

        if (std::get<MultiPageFile>(output).file.empty())
            throw std::invalid_argument("multipage_file_path_must_not_be_empty");
    }
};

} // namespace emwat
