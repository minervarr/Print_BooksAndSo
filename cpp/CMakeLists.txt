# ---------------------------------------------------------------------------
# Print_BooksAndSo — turn a PDF book into a printable interleaved notebook.
#
#   core/   portable C++17. No OS headers, no PDF library, no I/O. Testable on
#           a desktop with no printer and no font file. The C++ port of the
#           Python prototype; names are mirrored so the port is mechanical.
# ---------------------------------------------------------------------------
cmake_minimum_required(VERSION 3.22)
# C is required by the freetype and qpdf submodules (their project() enables it
# too; declaring it here keeps the top-level language set honest).
project(printbooks LANGUAGES C CXX)

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

# ── Third-party (submodules under cpp/third_party/) ─────────────────────────
# Vendored so the backend can link qpdf / freetype / toml++ without depending
# on distro package versions. core/ must never link these — that boundary is
# enforced by cpp/core/CMakeLists.txt listing only its own sources on every
# test executable. Set every CACHE option BEFORE add_subdirectory so the
# subprojects' option() calls see the values we want.
#
# Pins (release tags, not main):
#   qpdf          v12.4.1
#   freetype      VER-2-14-3
#   tomlplusplus  v3.4.0
#
# qpdf is ExternalProject, not add_subdirectory: its qpdf/ and libtests/
# CMakeLists use ${CMAKE_SOURCE_DIR}/libqpdf for private headers, which
# points at *our* source root when nested and breaks the build (same class
# of "not a subproject" problem as Matrix's libjpeg-turbo). Building it
# out-of-tree also keeps its enable_testing()/add_test() out of our ctest.

find_package(ZLIB QUIET)
if(NOT ZLIB_FOUND)
    message(FATAL_ERROR "ZLIB not found (required by qpdf). "
                        "Install the Arch package: zlib")
endif()
find_package(JPEG QUIET)
if(NOT JPEG_FOUND)
    message(FATAL_ERROR "JPEG not found (required by qpdf). "
                        "Install the Arch package: libjpeg")
endif()
# Re-find as REQUIRED so ZLIB::ZLIB / JPEG::JPEG imported targets exist for
# dependents; the QUIET probes above only exist to name the Arch packages.
find_package(ZLIB REQUIRED)
find_package(JPEG REQUIRED)

set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)

# FreeType: outlines only — no raster deps.
set(FT_DISABLE_HARFBUZZ ON CACHE BOOL "" FORCE)
set(FT_DISABLE_PNG      ON CACHE BOOL "" FORCE)
set(FT_DISABLE_BZIP2    ON CACHE BOOL "" FORCE)
set(FT_DISABLE_BROTLI   ON CACHE BOOL "" FORCE)
set(FT_DISABLE_ZLIB     ON CACHE BOOL "" FORCE)

add_subdirectory(third_party/freetype)
add_subdirectory(third_party/tomlplusplus)

include(ExternalProject)
set(QPDF_INSTALL_DIR "${CMAKE_BINARY_DIR}/qpdf-install")
set(QPDF_LIBRARY "${QPDF_INSTALL_DIR}/lib/libqpdf.a")
# CMAKE_CXX_FLAGS/CMAKE_C_FLAGS forwarded explicitly: ExternalProject runs a
# separate configure, so PRINTBOOKS_ARCH_LEVEL would otherwise not reach qpdf.
ExternalProject_Add(qpdf_ext
    SOURCE_DIR "${CMAKE_SOURCE_DIR}/third_party/qpdf"
    CMAKE_ARGS
        -G${CMAKE_GENERATOR}
        -DCMAKE_BUILD_TYPE=${CMAKE_BUILD_TYPE}
        -DCMAKE_C_COMPILER=${CMAKE_C_COMPILER}
        -DCMAKE_CXX_COMPILER=${CMAKE_CXX_COMPILER}
        -DCMAKE_CXX_FLAGS=${CMAKE_CXX_FLAGS}
        -DCMAKE_C_FLAGS=${CMAKE_C_FLAGS}
        -DCMAKE_INSTALL_PREFIX=${QPDF_INSTALL_DIR}
        -DCMAKE_INSTALL_LIBDIR=lib
        -DBUILD_SHARED_LIBS=OFF
        -DBUILD_STATIC_LIBS=ON
        -DBUILD_DOC=OFF
        -DINSTALL_MANUAL=OFF
        -DINSTALL_EXAMPLES=OFF
        -DINSTALL_CMAKE_PACKAGE=OFF
        -DINSTALL_PKGCONFIG=OFF
        -DOSS_FUZZ=OFF
        -DUSE_IMPLICIT_CRYPTO=OFF
        -DREQUIRE_CRYPTO_NATIVE=ON
        -DREQUIRE_CRYPTO_OPENSSL=OFF
        -DREQUIRE_CRYPTO_GNUTLS=OFF
    # Only the static library — skip CLI / libtests / examples / fuzz.
    BUILD_COMMAND ${CMAKE_COMMAND} --build <BINARY_DIR> --target libqpdf
    INSTALL_COMMAND ${CMAKE_COMMAND} -E make_directory
                        "${QPDF_INSTALL_DIR}/lib"
                        "${QPDF_INSTALL_DIR}/include"
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
                        <BINARY_DIR>/libqpdf/libqpdf.a "${QPDF_LIBRARY}"
        COMMAND ${CMAKE_COMMAND} -E copy_directory
                        "${CMAKE_SOURCE_DIR}/third_party/qpdf/include/qpdf"
                        "${QPDF_INSTALL_DIR}/include/qpdf"
    BUILD_BYPRODUCTS "${QPDF_LIBRARY}")

add_library(libqpdf STATIC IMPORTED GLOBAL)
file(MAKE_DIRECTORY "${QPDF_INSTALL_DIR}/include") # must exist at configure time
set_target_properties(libqpdf PROPERTIES
    IMPORTED_LOCATION "${QPDF_LIBRARY}"
    INTERFACE_INCLUDE_DIRECTORIES "${QPDF_INSTALL_DIR}/include")
target_link_libraries(libqpdf INTERFACE ZLIB::ZLIB JPEG::JPEG)
add_dependencies(libqpdf qpdf_ext)

# Ensure Debug/Release `ninja` actually compiles the vendored libs even though
# nothing in-tree links them yet (backends land in later tasks).
add_custom_target(printbooks_third_party ALL DEPENDS libqpdf freetype)

add_subdirectory(core)
