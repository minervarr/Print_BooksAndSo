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

# Whole-program optimization (MSVC /GL+/LTCG, GCC/Clang LTO) for Release
# builds: lets the linker inline/dead-strip across translation units instead
# of stopping at each object's boundary. Must be set before
# add_subdirectory()/add_executable() calls below — CMake reads it at
# target-creation time, not build time. Costs link time; harmless for Debug
# (this only fires when CMAKE_BUILD_TYPE=Release).
if(CMAKE_BUILD_TYPE STREQUAL "Release")
    set(CMAKE_INTERPROCEDURAL_OPTIMIZATION TRUE)
endif()

# Optional x86-64 psABI microarchitecture level (v2/v3/v4, or "native").
# Empty (default) leaves the compiler's generic x86-64 baseline untouched —
# a binary compiled for v4 (AVX-512 etc.) SIGILLs on any CPU that lacks it,
# and GCC/Clang only recognize -march=x86-64-v2/v3/v4 from GCC 11 / Clang 12
# onward, so hardcoding this would break compiling *and* running on another
# machine or an older toolchain. Opt in explicitly per build:
#   cmake -B build/linux -DPRINTBOOKS_ARCH_LEVEL=v4 ...
# Appended to CMAKE_CXX_FLAGS/CMAKE_C_FLAGS (not add_compile_options) so any
# future ExternalProject sub-builds that forward those variables pick it up
# too — an add_compile_options() directory property would not cross that
# boundary.
set(PRINTBOOKS_ARCH_LEVEL "" CACHE STRING "x86-64 target to compile for: v2/v3/v4 (psABI level), native, or a specific -march name (e.g. znver4). Empty = compiler default (portable).")
if(PRINTBOOKS_ARCH_LEVEL AND NOT MSVC)
    if(PRINTBOOKS_ARCH_LEVEL MATCHES "^v[234]$" OR PRINTBOOKS_ARCH_LEVEL STREQUAL "v1")
        set(PRINTBOOKS_ARCH_FLAG "-march=x86-64-${PRINTBOOKS_ARCH_LEVEL}")
    else()
        # "native", or any other -march value GCC/Clang recognizes directly
        # (znver1..znver4 for AMD Zen-tuned builds, etc.)
        set(PRINTBOOKS_ARCH_FLAG "-march=${PRINTBOOKS_ARCH_LEVEL}")
    endif()
    include(CheckCXXCompilerFlag)
    check_cxx_compiler_flag("${PRINTBOOKS_ARCH_FLAG}" PRINTBOOKS_ARCH_FLAG_SUPPORTED)
    if(NOT PRINTBOOKS_ARCH_FLAG_SUPPORTED)
        message(FATAL_ERROR "Compiler does not support ${PRINTBOOKS_ARCH_FLAG} "
                             "(x86-64-v2/v3/v4 need GCC 11+ or Clang 12+). "
                             "Leave PRINTBOOKS_ARCH_LEVEL unset to build portably.")
    endif()
    string(APPEND CMAKE_CXX_FLAGS " ${PRINTBOOKS_ARCH_FLAG}")
    string(APPEND CMAKE_C_FLAGS " ${PRINTBOOKS_ARCH_FLAG}")
elseif(PRINTBOOKS_ARCH_LEVEL AND MSVC)
    message(WARNING "PRINTBOOKS_ARCH_LEVEL is a GCC/Clang psABI flag and has no "
                     "MSVC equivalent for v4 (MSVC tops out at /arch:AVX2) — ignored.")
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
