#!/usr/bin/env bash
# Desktop Linux build.
#
#   --release   the app as it ships. Optimised, asserts compiled out, no tests.
#               -> build/linux
#   --debug     everything needed to find a problem: symbols, live asserts, the
#               test suite.                                          -> build/linux_debug
#
# Extra flags:
#   --asan      Debug + AddressSanitizer + UBSan                     -> build/linux_asan
#   --clean     remove the build directory first
#
# Each combination gets its OWN directory. Reconfiguring one config into
# another in place is how a stale binary outlives the source that made it.
#
# Prereqs: cmake >= 3.22, ninja, a C++17 compiler. Nothing else: core/ has no
# PDF library and no font library on its link line.
set -euo pipefail
cd "$(dirname "$0")/../.."

BUILD_TYPE=Release
CLEAN=0
ASAN=0
MODE_SET=0
CMAKE_ARGS=()

for arg in "$@"; do
    case "$arg" in
        debug|--debug)     BUILD_TYPE=Debug;   MODE_SET=1 ;;
        release|--release) BUILD_TYPE=Release; MODE_SET=1 ;;
        --asan)            BUILD_TYPE=Debug; ASAN=1; MODE_SET=1 ;;
        --clean)           CLEAN=1 ;;
        -h|--help)         sed -n '2,20p' "$0"; exit 0 ;;
        *)                 CMAKE_ARGS+=("$arg") ;;
    esac
done

# Ask, if there is someone at the keyboard to answer. A non-interactive caller
# (CI, a pipe) falls through to the Release default instead of hanging on read.
if [[ "$MODE_SET" -eq 0 && -t 0 ]]; then
    echo "Select build:"
    echo "  1) Release (default) -- the app as it ships"
    echo "  2) Debug             -- + tests + symbols"
    echo "  3) Debug + ASan/UBSan"
    read -r -p "Enter choice [1-3, default 1]: " choice
    case "$choice" in
        ""|1) BUILD_TYPE=Release ;;
        2)    BUILD_TYPE=Debug ;;
        3)    BUILD_TYPE=Debug; ASAN=1 ;;
        *)    echo "error: invalid choice '$choice'" >&2; exit 2 ;;
    esac
fi

# The directory NAMES the configuration, so two configs can never share one.
if [[ "$BUILD_TYPE" == "Debug" ]]; then BUILD_DIR="build/linux_debug"
else                                    BUILD_DIR="build/linux"; fi
[[ "$ASAN" -eq 1 ]] && BUILD_DIR="build/linux_asan"

EXTRA=()
[[ "$ASAN" -eq 1 ]] && EXTRA+=(-DPRINTBOOKS_SANITIZE=ON)

if [[ "$CLEAN" -eq 1 && -d "$BUILD_DIR" ]]; then
    echo "Cleaning $BUILD_DIR..."
    rm -rf "$BUILD_DIR"
fi

echo "Configuring CMake (Ninja, $BUILD_TYPE) -> $BUILD_DIR..."
cmake -S cpp -B "cpp/$BUILD_DIR" -G Ninja \
    -DCMAKE_BUILD_TYPE="$BUILD_TYPE" \
    "${EXTRA[@]}" "${CMAKE_ARGS[@]}"
cmake --build "cpp/$BUILD_DIR" -j"$(nproc)"

echo
echo "Done -> cpp/$BUILD_DIR/"
if [[ "$BUILD_TYPE" == "Debug" ]]; then
    echo
    echo "  ctest --test-dir cpp/$BUILD_DIR --output-on-failure"
fi
