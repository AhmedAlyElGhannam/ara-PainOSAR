cmake_minimum_required(VERSION 3.28)

project(telemetry
    VERSION 0.1.0
    DESCRIPTION "Telemetry parsing and log formatting"
    LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# --------------------------------------------------------------------------
# Toolchain
#
# The project is specified to build with GCC. Refuse anything else rather than
# silently producing a binary nobody tested, and warn when the major version
# drifts from the one the CI image pins.
# --------------------------------------------------------------------------
set(TELEMETRY_EXPECTED_GCC_MAJOR 16 CACHE STRING "GCC major version the CI image ships")

if(NOT CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    message(FATAL_ERROR
        "This project builds with GCC. Found ${CMAKE_CXX_COMPILER_ID} "
        "${CMAKE_CXX_COMPILER_VERSION}. Set CXX=g++-${TELEMETRY_EXPECTED_GCC_MAJOR}.")
endif()

if(CMAKE_CXX_COMPILER_VERSION VERSION_LESS ${TELEMETRY_EXPECTED_GCC_MAJOR})
    message(WARNING
        "Building with GCC ${CMAKE_CXX_COMPILER_VERSION}; CI pins "
        "GCC ${TELEMETRY_EXPECTED_GCC_MAJOR}. Results may differ from CI.")
endif()

# --------------------------------------------------------------------------
# The mandated flag set
#
# -O0 and -g keep the sanitizer's stack traces exact.
# -fno-omit-frame-pointer is what makes those traces unwind at all.
# AddressSanitizer must appear at BOTH compile and link time; passing it only
# to the compiler produces confusing undefined-symbol errors at link.
# --------------------------------------------------------------------------
set(TELEMETRY_REQUIRED_FLAGS
    -g
    -O0
    -fsanitize=address
    -fno-omit-frame-pointer)

# Kept separate so the required set above stays exactly as specified.
set(TELEMETRY_WARNING_FLAGS
    -Wall
    -Wextra
    -Wpedantic
    -Wshadow
    -Wconversion)

option(TELEMETRY_WARNINGS_AS_ERRORS "Promote warnings to errors" ON)

add_library(telemetry_flags INTERFACE)
target_compile_options(telemetry_flags INTERFACE
    ${TELEMETRY_REQUIRED_FLAGS}
    ${TELEMETRY_WARNING_FLAGS}
    $<$<BOOL:${TELEMETRY_WARNINGS_AS_ERRORS}>:-Werror>)
target_link_options(telemetry_flags INTERFACE
    -fsanitize=address
    -fno-omit-frame-pointer)

# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------
include(CTest)

option(TELEMETRY_BUILD_TESTS "Build the unit test suite" ON)

if(TELEMETRY_BUILD_TESTS AND BUILD_TESTING)
    include(FetchContent)

    # The CI image vendors GoogleTest at /opt/googletest so builds need no
    # network. FetchContent falls back to a download when it is absent, which
    # is what happens on a developer laptop.
    if(EXISTS /opt/googletest/CMakeLists.txt)
        set(FETCHCONTENT_SOURCE_DIR_GOOGLETEST /opt/googletest
            CACHE PATH "Vendored GoogleTest supplied by the CI image")
    endif()

    FetchContent_Declare(googletest
        GIT_REPOSITORY https://github.com/google/googletest.git
        GIT_TAG        v1.17.0
        GIT_SHALLOW    TRUE)

    # GoogleTest is built from source inside this project so it inherits the
    # sanitizer flags. Linking a non-instrumented GoogleTest against
    # instrumented code produces container-overflow false positives.
    set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
    set(INSTALL_GTEST OFF CACHE BOOL "" FORCE)
    FetchContent_MakeAvailable(googletest)
    include(GoogleTest)

endif()

# --------------------------------------------------------------------------
# The platform tree
#
# Declared last so telemetry_flags and GoogleTest exist before any module
# tries to link them.
# --------------------------------------------------------------------------
add_subdirectory(platform)
