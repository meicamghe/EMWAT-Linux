cmake_minimum_required(VERSION 3.20)
project(emwat_native_core LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(PNG REQUIRED)
find_package(JPEG REQUIRED)
find_package(TIFF REQUIRED)

enable_testing()
add_library(emwat_image_core
    src/image_document.cpp
    src/image_codec.cpp
    src/image_document_io.cpp
)
target_include_directories(emwat_image_core PUBLIC include)
target_link_libraries(emwat_image_core PRIVATE PNG::PNG JPEG::JPEG TIFF::TIFF)
target_compile_options(emwat_image_core PRIVATE -Wall -Wextra -Wpedantic -Werror)

add_executable(emwat_image_document_tests tests/test_image_document.cpp)
target_link_libraries(emwat_image_document_tests PRIVATE emwat_image_core)
target_compile_options(emwat_image_document_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
add_test(NAME image_document_core COMMAND emwat_image_document_tests)

add_executable(emwat_image_codec_tests tests/test_image_codec.cpp)
target_link_libraries(emwat_image_codec_tests PRIVATE emwat_image_core)
target_compile_options(emwat_image_codec_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
add_test(NAME image_codec COMMAND emwat_image_codec_tests)

add_executable(emwat_image_document_io_tests tests/test_image_document_io.cpp)
target_link_libraries(emwat_image_document_io_tests PRIVATE emwat_image_core)
target_compile_options(emwat_image_document_io_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
add_test(NAME image_document_io COMMAND emwat_image_document_io_tests)
