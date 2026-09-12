# ---------------------------------------------------------------------------
# Print_BooksAndSo — turn a PDF book into a printable interleaved notebook.
#
#   core/   portable C++17. No OS headers, no PDF library, no I/O. Testable on
#           a desktop with no printer and no font file. The C++ port of the
#           Python prototype; names are mirrored so the port is mechanical.
# ---------------------------------------------------------------------------
cmake_minimum_required(VERSION 3.22)
project(printbooks LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

get_property(_multi_config GLOBAL PROPERTY GENERATOR_IS_MULTI_CONFIG)
if(NOT CMAKE_BUILD_TYPE AND NOT _multi_config)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
    set_property(CACHE CMAKE_BUILD_TYPE PROPERTY STRINGS Debug Release RelWithDebInfo MinSizeRel)
endif()

# ── The two configurations ──────────────────────────────────────────────────
#   Release   the app as it ships: optimised, asserts compiled out, no tests.
#   Debug     everything needed to find a problem: symbols, live asserts, tests.
# Each is a SEPARATE build directory; they are not interchangeable.
if(CMAKE_BUILD_TYPE STREQUAL "Debug")
    set(_dev_default ON)
else()
    set(_dev_default OFF)
endif()

option(PRINTBOOKS_TESTS     "Build the assert-based test suite" ${_dev_default})
option(PRINTBOOKS_SANITIZE  "Build with ASan + UBSan (Debug only)" OFF)

if(PRINTBOOKS_SANITIZE)
    if(CMAKE_BUILD_TYPE STREQUAL "Release")
        message(FATAL_ERROR "PRINTBOOKS_SANITIZE is for Debug: a sanitised Release "
                            "is neither fast nor especially informative.")
    endif()
    add_compile_options(-fsanitize=address,undefined -fno-omit-frame-pointer)
    add_link_options(-fsanitize=address,undefined)
    message(STATUS "printbooks: ASan + UBSan enabled")
endif()

if(PRINTBOOKS_TESTS)
    enable_testing()
endif()

add_subdirectory(core)
