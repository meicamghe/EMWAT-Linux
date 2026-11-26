#include "emwat/scan_result.hpp"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <stdexcept>

using namespace emwat;

template <typename Fn>
static bool throws_invalid(Fn&& fn) {
    try { fn(); } catch (const std::invalid_argument&) { return true; }
    return false;
}

int main() {
    ScanResult files{
        SinglePageFileSet{{"page-001.tif", "page-002.tif"}},
        std::string("scan/session-7"),
        std::string("response.tif")
    };
    files.validate();
    assert(files.is_single_page_file_set());
    assert(!files.is_multipage_file());
    assert(files.output_file_count() == 2);

    ScanResult multipage{
        MultiPageFile{"document.tif"},
        std::nullopt,
        std::string("document-response.tif")
    };
    multipage.validate();
    assert(!multipage.is_single_page_file_set());
    assert(multipage.is_multipage_file());
    assert(multipage.output_file_count() == 1);

    // Preserve the response XML's independent status/error/image fields.
    // ImageName is not the same field as the response filename or scan path.
    ScanResponseMetadata response{
        std::string("success"),
        std::string("0"),
        ScanResponseImageMetadata{
            std::string("returned-image-name"),
            std::string("base64")
        }
    };
    ScanResult with_response{
        MultiPageFile{"physical-output.tif"},
        std::string("physical-scan-path"),
        std::string("outer-response-filename"),
        response
    };
    with_response.validate();
    assert(with_response.scan_path == std::optional<std::string>("physical-scan-path"));
    assert(with_response.response_filename ==
           std::optional<std::string>("outer-response-filename"));
    assert(with_response.response_metadata.has_value());
    assert(with_response.response_metadata->status ==
           std::optional<std::string>("success"));
    assert(with_response.response_metadata->error_code ==
           std::optional<std::string>("0"));
    assert(with_response.response_metadata->scanned_image.has_value());
    assert(with_response.response_metadata->scanned_image->image_name ==
           std::optional<std::string>("returned-image-name"));
    assert(with_response.response_metadata->scanned_image->encoding ==
           std::optional<std::string>("base64"));

    ScanResult empty_set{SinglePageFileSet{{}}, {}, {}};
    assert(throws_invalid([&] { empty_set.validate(); }));

    ScanResult empty_entry{SinglePageFileSet{{"page-1.tif", ""}}, {}, {}};
    assert(throws_invalid([&] { empty_entry.validate(); }));

    ScanResult empty_multipage{MultiPageFile{""}, {}, {}};
    assert(throws_invalid([&] { empty_multipage.validate(); }));

    ScanResult empty_metadata{
        MultiPageFile{"document.tif"}, std::string(""), {}
    };
    assert(throws_invalid([&] { empty_metadata.validate(); }));

    return 0;
}
