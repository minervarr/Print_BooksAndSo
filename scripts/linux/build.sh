#!/usr/bin/env bash
# Desktop Linux build.
#
# Usage: scripts/linux/build.sh [--debug|--release|--share|--packages|--asan]
#                               [--clean] [-h] [cmake args...]
# Passing a mode flag explicitly (scripts, CI) always skips straight to the
# build — same for non-interactive stdin (defaults to Release, Universal).
#
# Run with no mode flag on an interactive terminal and two prompts run in
# sequence — microarchitecture target, then build type — since they're
# orthogonal (e.g. Native+Debug is a legitimate combination, not just
# Universal+Release):
#   Scene 1 — microarch target:
#     1) Universal (default) -- portable generic x86-64 baseline
#     2) Native               -- tuned to this exact CPU (-march=native)
#     3) Custom                -- enter any -march value (v2/v3/v4/znver4/...)
#     4) All                   -- build universal/v3/v4/zen4 in one pass
#     5) Packages              -- the same four as Arch packages, for upload
#   Scene 2 — build type (skipped for Packages, which is Release by definition):
#     1) Release (default)
#     2) Debug
#
# Mode / directory map:
#   --release / release   the app as it ships. Optimised, asserts out, no tests.
#                         -> build/linux${ARCH_SUFFIX}
#   --debug / debug       symbols, live asserts, the test suite.
#                         -> build/linux${ARCH_SUFFIX}_debug
#   --asan                Debug + AddressSanitizer + UBSan -> build/linux_asan
#   --share               four variants (universal/v3/v4/zen4) under
#                         build/linux_share[_debug]/ Release tarballs in
#                         dist/linux/print-books-linux-$variant.tar.gz
#   --packages            makepkg -f in packaging/arch (Release only)
#   --clean               remove the build directory first
#   -h / --help           this header
#
# Each combination gets its OWN directory. Reconfiguring one config into
# another in place is how a stale binary outlives the source that made it.
#
# cmake root is cpp/ (repo root has no CMakeLists.txt). Build trees land at
# the repo root: cmake -S cpp -B build/linux…
#
# Prereqs: cmake >= 3.22, ninja, a C++17 compiler, zlib, libjpeg. core/ has no
# PDF library and no font library on its link line (qpdf needs zlib+libjpeg).
# --packages also needs makepkg (base-devel).
set -euo pipefail
cd "$(dirname "$0")/../.."

BUILD_TYPE=Release
SHARE=0
PACKAGES=0
CLEAN=0
ASAN=0
MODE_SET=0
ARCH_LEVEL=""
ARCH_SUFFIX=""
CMAKE_ARGS=()

for arg in "$@"; do
    case "$arg" in
        debug|--debug)     BUILD_TYPE=Debug;   MODE_SET=1 ;;
        release|--release) BUILD_TYPE=Release; MODE_SET=1 ;;
        --share)           SHARE=1; MODE_SET=1 ;;
        --packages)        PACKAGES=1; MODE_SET=1 ;;
        --asan)            BUILD_TYPE=Debug; ASAN=1; MODE_SET=1 ;;
        --clean)           CLEAN=1 ;;
        -h|--help)         sed -n '2,44p' "$0"; exit 0 ;;
        *)                 CMAKE_ARGS+=("$arg") ;;
    esac
done

# No mode flag given: ask, if there's actually someone at the keyboard to
# answer (stdin a tty) — a non-interactive caller (CI, a pipe) falls through
# to the Release/Universal default above instead of hanging on `read`.
if [[ "$MODE_SET" -eq 0 && -t 0 ]]; then
    echo "Select microarchitecture target:"
    echo "  1) Universal (default) -- portable generic x86-64 baseline"
    echo "  2) Native -- tuned to this exact CPU (-march=native)"
    echo "  3) Custom -- enter a specific -march value (v2/v3/v4/znver4/...)"
    echo "  4) All -- build universal/v3/v4/zen4 in one pass"
    echo "  5) Packages -- the same four as Arch packages, for upload"
    read -r -p "Enter choice [1-5, default 1]: " arch_choice
    case "$arch_choice" in
        ""|1) ;;
        2) ARCH_LEVEL="native"; ARCH_SUFFIX="_native" ;;
        3)
            read -r -p "Enter -march value (e.g. v3, v4, znver4): " custom_level
            if [[ -z "$custom_level" ]]; then
                echo "error: no value entered" >&2
                exit 2
            fi
            ARCH_LEVEL="$custom_level"
            ARCH_SUFFIX="_custom-${custom_level}"
            ;;
        4) SHARE=1 ;;
        5) PACKAGES=1 ;;
        *) echo "error: invalid choice '$arch_choice'" >&2; exit 2 ;;
    esac

    # Packages are Release by definition — the PKGBUILD hardcodes it. Skip
    # the question rather than ask one whose answer is ignored.
    if [[ "$PACKAGES" -eq 0 ]]; then
        echo "Select build type:"
        echo "  1) Release (default)"
        echo "  2) Debug"
        read -r -p "Enter choice [1-2, default 1]: " type_choice
        case "$type_choice" in
            ""|1) BUILD_TYPE=Release ;;
            2)    BUILD_TYPE=Debug ;;
            *)    echo "error: invalid choice '$type_choice'" >&2; exit 2 ;;
        esac
    fi
fi

if [[ "$PACKAGES" -eq 1 ]]; then
    # The Arch-package sibling of --share: same four microarch variants, but
    # built by makepkg into installable .pkg.tar.zst files instead of tarballs.
    #
    # This script does NOT rebuild anything itself here. Everything lives in
    # packaging/arch/PKGBUILD, because that is where a person reading the
    # package expects to find it, and because makepkg has to own $srcdir for
    # its checksums to mean anything.
    #
    # The PKGBUILD builds the last PUSHED commit, not this working tree.
    PKG_DIR=packaging/arch
    DIST_DIR=dist/linux

    # WHERE MAKEPKG PUTS ITS WORKING FILES — this is load-bearing, not tidiness.
    #
    # Left alone, all of these default to $startdir, i.e. packaging/arch/
    # itself (makepkg: `${!var:-$startdir}`). For a git source that means
    # makepkg drops a bare clone of this entire repository under
    # packaging/arch/. A .gitignore entry is a second line of defence; this
    # is the first, because build/ and dist/ are ignored wholesale at the
    # repo root rather than by a nested pattern that can be missed.
    #
    # Absolute paths: makepkg runs with its own $startdir, so relative ones
    # would resolve against packaging/arch/.
    export SRCDEST="$PWD/build/packaging/src"      # VCS clones + source tarballs
    export BUILDDIR="$PWD/build/packaging/build"   # src/ and pkg/ extraction
    export PKGDEST="$PWD/$DIST_DIR"                # finished packages, straight to dist/
    mkdir -p "$SRCDEST" "$BUILDDIR" "$PKGDEST"

    if ! command -v makepkg >/dev/null 2>&1; then
        echo "error: makepkg not found — this mode needs base-devel" >&2
        exit 2
    fi
    if [[ ! -f "$PKG_DIR/PKGBUILD" ]]; then
        echo "error: packaging/arch/PKGBUILD not found" >&2
        exit 2
    fi
    if [[ "$BUILD_TYPE" == "Debug" ]]; then
        echo "note: --packages is always Release; ignoring --debug." >&2
    fi
    if [[ ${#CMAKE_ARGS[@]} -gt 0 ]]; then
        echo "note: extra cmake args are not forwarded to makepkg;" >&2
        echo "      edit $PKG_DIR/PKGBUILD's build() instead: ${CMAKE_ARGS[*]}" >&2
    fi

    if [[ "$CLEAN" -eq 1 ]]; then
        echo "Cleaning build/packaging and previous packages..."
        rm -rf build/packaging
        rm -f "$DIST_DIR"/*.pkg.tar.zst
        mkdir -p "$SRCDEST" "$BUILDDIR"
    fi

    echo
    echo "==> makepkg: four variants, each a full build (this takes a while)"
    # -f so a re-run overwrites; no -i, since installing one of four on the
    # build machine is a separate decision from producing them.
    ( cd "$PKG_DIR" && makepkg -f )

    # PKGDEST already put them in $DIST_DIR, next to the --share tarballs, so
    # there is one place to upload from and nothing to move.
    shopt -s nullglob
    built=("$DIST_DIR"/*.pkg.tar.zst)
    shopt -u nullglob
    if [[ ${#built[@]} -eq 0 ]]; then
        echo "error: makepkg reported success but produced no packages" >&2
        exit 1
    fi

    echo
    echo "Packages in $DIST_DIR/:"
    for p in "${built[@]}"; do
        printf '  %6s  %s\n' "$(du -h "$p" | cut -f1)" "$p"
    done
    echo
    echo "Each is self-contained — a recipient downloads ONE and runs:"
    echo "  sudo pacman -U <file>"
    echo "They can check which variant their CPU supports with:"
    echo "  /lib/ld-linux-x86-64.so.2 --help | grep -A4 'Subdirectories of glibc-hwcaps'"
    echo "universal works everywhere; v3/v4/zen4 only where that line says 'supported'."
    exit 0
fi

if [[ "$SHARE" -eq 1 ]]; then
    # variant name -> PRINTBOOKS_ARCH_LEVEL value ("" = compiler default baseline)
    declare -A SHARE_VARIANTS=(
        [universal]=""
        [v3]="v3"
        [v4]="v4"
        [zen4]="znver4"
    )

    if [[ "$BUILD_TYPE" == "Debug" ]]; then
        SHARE_ROOT=build/linux_share_debug
    else
        SHARE_ROOT=build/linux_share
    fi
    DIST_DIR=dist/linux

    if [[ "$CLEAN" -eq 1 ]]; then
        echo "Cleaning $SHARE_ROOT and $DIST_DIR..."
        rm -rf "$SHARE_ROOT" "$DIST_DIR"
    fi
    [[ "$BUILD_TYPE" == "Release" ]] && mkdir -p "$DIST_DIR"

    for variant in universal v3 v4 zen4; do
        level="${SHARE_VARIANTS[$variant]}"
        variant_dir="$SHARE_ROOT/$variant"
        arch_arg=()
        [[ -n "$level" ]] && arch_arg=(-DPRINTBOOKS_ARCH_LEVEL="$level")

        echo
        echo "==> Configuring '$variant' ($BUILD_TYPE) -> $variant_dir..."
        cmake -S cpp -B "$variant_dir" -G Ninja \
            -DCMAKE_BUILD_TYPE="$BUILD_TYPE" \
            "${arch_arg[@]}" "${CMAKE_ARGS[@]}"
        cmake --build "$variant_dir" -j"$(nproc)"

        if [[ "$BUILD_TYPE" == "Release" ]]; then
            # Binary + fonts/ next to it: font_dir() looks at dirname(exe)/fonts
            # before the compile-time source-tree path, so a tarball extracted
            # on another machine works with no env vars.
            bin="$variant_dir/cli/print-books"
            if [[ ! -e "$bin" ]]; then
                echo "error: $bin not found after build" >&2
                exit 1
            fi
            pkg_name="print-books-linux-$variant"
            pkg_dir="$DIST_DIR/$pkg_name"
            rm -rf "$pkg_dir"
            mkdir -p "$pkg_dir/fonts"
            cp "$bin" "$pkg_dir/"
            cp assets/fonts/*.otf "$pkg_dir/fonts/"
            tar -C "$DIST_DIR" -czf "$DIST_DIR/$pkg_name.tar.gz" "$pkg_name"
            rm -rf "$pkg_dir"
            echo "==> Packaged $DIST_DIR/$pkg_name.tar.gz"
        else
            echo "==> Built $variant_dir (Debug, not packaged)"
        fi
    done

    echo
    if [[ "$BUILD_TYPE" == "Release" ]]; then
        echo "All-variant build done. Tarballs in $DIST_DIR/:"
        for variant in universal v3 v4 zen4; do
            tarball="$DIST_DIR/print-books-linux-$variant.tar.gz"
            printf '  %6s  %s\n' "$(du -h "$tarball" | cut -f1)" "$tarball"
        done
    else
        echo "All-variant build done (Debug, unpackaged). Trees:"
        for variant in universal v3 v4 zen4; do
            echo "  $SHARE_ROOT/$variant"
        done
    fi
    exit 0
fi

# The directory NAMES the configuration, so two configs can never share one.
if [[ "$ASAN" -eq 1 ]]; then
    BUILD_DIR="build/linux_asan"
elif [[ "$BUILD_TYPE" == "Debug" ]]; then
    BUILD_DIR="build/linux${ARCH_SUFFIX}_debug"
else
    BUILD_DIR="build/linux${ARCH_SUFFIX}"
fi

EXTRA=()
[[ "$ASAN" -eq 1 ]] && EXTRA+=(-DPRINTBOOKS_SANITIZE=ON)
ARCH_ARG=()
[[ -n "$ARCH_LEVEL" ]] && ARCH_ARG=(-DPRINTBOOKS_ARCH_LEVEL="$ARCH_LEVEL")

if [[ "$CLEAN" -eq 1 && -d "$BUILD_DIR" ]]; then
    echo "Cleaning $BUILD_DIR..."
    rm -rf "$BUILD_DIR"
fi

echo "Configuring CMake (Ninja, $BUILD_TYPE${ARCH_LEVEL:+, arch=$ARCH_LEVEL}) -> $BUILD_DIR..."
cmake -S cpp -B "$BUILD_DIR" -G Ninja \
    -DCMAKE_BUILD_TYPE="$BUILD_TYPE" \
    "${EXTRA[@]}" "${ARCH_ARG[@]}" "${CMAKE_ARGS[@]}"
cmake --build "$BUILD_DIR" -j"$(nproc)"

echo
echo "Binaries in $BUILD_DIR/:"
if [[ -x "$BUILD_DIR/cli/print-books" ]]; then
    echo "  cli/print-books -- init and build a printable notebook"
    echo
    echo "  ./print-books init BOOK.pdf"
    echo "  ./print-books build project.toml"
else
    echo "  (cli/print-books not built)"
fi
if [[ "$BUILD_TYPE" == "Debug" ]]; then
    echo
    echo "  ctest --test-dir $BUILD_DIR --output-on-failure"
fi
