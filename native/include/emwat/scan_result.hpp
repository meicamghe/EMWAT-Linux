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

struct ScanResult {
    ScanOutput output;
    std::optional<std::string> scan_path;
    std::optional<std::string> response_filename;

    [[nodiscard]] bool is_single_page_file_set() const noexcept {
        return std::holds_alternative<SinglePageFileSet>(output);
    }

    [[nodiscard]] bool is_multipage_file() const noexcept {
        return std::holds_alternative<MultiPageFile>(output);
    }

    [[nodiscard]] std::size_t output_file_count() const noexcept {
        if (const auto* set = std::get_if<SinglePageFileSet>(&output))
            return set->files.size();
        return 1;
    }

    // Validate structural invariants only. This does not touch the filesystem
    // or assert undocumented EMWAT path/filename semantics.
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
