#include "emwat/scanner.hpp"

#include <sane/sane.h>

#include <mutex>
#include <string>

namespace emwat {
namespace {
std::mutex& sane_mutex() {
    static std::mutex value;
    return value;
}

class SaneSession {
public:
    SaneSession() {
        SANE_Int version = 0;
        const auto status = sane_init(&version, nullptr);
        if (status != SANE_STATUS_GOOD)
            throw ScannerError(std::string("SANE initialization failed: ") + sane_strstatus(status));
        active_ = true;
    }

    ~SaneSession() {
        if (active_) sane_exit();
    }

    SaneSession(const SaneSession&) = delete;
    SaneSession& operator=(const SaneSession&) = delete;

private:
    bool active_{};
};

std::string safe_string(const SANE_Char* value) {
    return value ? reinterpret_cast<const char*>(value) : std::string{};
}
} // namespace

std::vector<ScannerDevice> SaneScannerBackend::list_devices() {
    std::lock_guard<std::mutex> lock(sane_mutex());
    SaneSession session;

    const SANE_Device** devices = nullptr;
    const auto status = sane_get_devices(&devices, SANE_FALSE);
    if (status != SANE_STATUS_GOOD)
        throw ScannerError(std::string("SANE device discovery failed: ") + sane_strstatus(status));

    std::vector<ScannerDevice> result;
    if (!devices) return result;

    for (auto current = devices; *current != nullptr; ++current) {
        result.push_back(ScannerDevice{
            safe_string((*current)->name),
            safe_string((*current)->vendor),
            safe_string((*current)->model),
            safe_string((*current)->type)
        });
    }
    return result;
}

} // namespace emwat
