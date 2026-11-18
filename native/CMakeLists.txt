cmake_minimum_required(VERSION 3.20)
project(emwat_native_core VERSION 0.1.0 LANGUAGES CXX)

include(GNUInstallDirs)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(PNG REQUIRED)
find_package(JPEG REQUIRED)
find_package(TIFF REQUIRED)
find_path(SANE_INCLUDE_DIR NAMES sane/sane.h REQUIRED)
find_library(SANE_LIBRARY NAMES sane REQUIRED)

enable_testing()
add_library(emwat_image_core
    src/image_document.cpp
    src/image_codec.cpp
    src/image_document_io.cpp
    src/sane_scanner.cpp
)
target_include_directories(emwat_image_core PUBLIC include PRIVATE ${SANE_INCLUDE_DIR})
target_link_libraries(emwat_image_core PRIVATE PNG::PNG JPEG::JPEG TIFF::TIFF ${SANE_LIBRARY})
target_compile_options(emwat_image_core PRIVATE -Wall -Wextra -Wpedantic -Werror)

add_executable(emwat_image_document_tests tests/test_image_document.cpp)
target_link_libraries(emwat_image_document_tests PRIVATE emwat_image_core)
target_compile_options(emwat_image_document_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
add_test(NAME image_document_core COMMAND emwat_image_document_tests)

add_executable(emwat_image_codec_tests tests/test_image_codec.cpp)
target_link_libraries(emwat_image_codec_tests PRIVATE emwat_image_core)
target_compile_options(emwat_image_codec_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
add_test(NAME image_codec COMMAND emwat_image_codec_tests)

add_executable(emwat_scanner_tests tests/test_scanner.cpp)
target_link_libraries(emwat_scanner_tests PRIVATE emwat_image_core)
target_compile_options(emwat_scanner_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
add_test(NAME scanner_backend_contract COMMAND emwat_scanner_tests)

add_executable(emwat_image_document_io_tests tests/test_image_document_io.cpp)
target_link_libraries(emwat_image_document_io_tests PRIVATE emwat_image_core)
target_compile_options(emwat_image_document_io_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
add_test(NAME image_document_io COMMAND emwat_image_document_io_tests)

# Install the reusable native image/scanner core and its public headers.
# This is a library install rule, not yet a complete desktop application package.
install(TARGETS emwat_image_core
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)
install(DIRECTORY include/emwat
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
    FILES_MATCHING PATTERN "*.hpp"
)


# Debian development package for the reusable static native core.
# This deliberately does not claim to package the Python bridge, daemon, or GUI.
set(EMWAT_PACKAGE_VERSION "${PROJECT_VERSION}" CACHE STRING "EMWAT Debian package version")
set(CPACK_GENERATOR "DEB")
set(CPACK_PACKAGE_NAME "emwat-native-core-dev")
set(CPACK_PACKAGE_VERSION "${EMWAT_PACKAGE_VERSION}")
set(CPACK_PACKAGE_DESCRIPTION_SUMMARY "EMWAT native image and scanner development library")
set(CPACK_PACKAGE_VENDOR "EMWAT Linux")
set(CPACK_PACKAGE_CONTACT "EMWAT Linux contributors")
set(CPACK_PACKAGING_INSTALL_PREFIX "/usr")
set(CPACK_DEBIAN_PACKAGE_MAINTAINER "EMWAT Linux contributors")
set(CPACK_DEBIAN_PACKAGE_SECTION "libdevel")
set(CPACK_DEBIAN_PACKAGE_PRIORITY "optional")
set(CPACK_DEBIAN_PACKAGE_DEPENDS "libpng-dev, libjpeg-dev, libtiff-dev, libsane-dev")
set(CPACK_DEBIAN_PACKAGE_SHLIBDEPS OFF)
set(CPACK_DEBIAN_FILE_NAME "DEB-DEFAULT")
include(CPack)
