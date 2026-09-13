#!/usr/bin/env bash
# Compile the reconstructed book.
#
# Usage: ./build.sh [book|units|unit <name>|figures|all|clean] [--clean] [-h]
#
# No argument on a TTY: asks what to build.
# No argument otherwise (CI, a pipe): builds the full book.
#
# Targets:
#   book       one PDF, front/main/back matter          -> book/build/book.pdf
#   units      one PDF per reconstructed unit           -> book/build/units/
#   unit NAME  that unit only (NAME = calcu5, …)
#   figures    standalone TikZ/pgfplots                 -> book/build/figures/
#   all        book + units + figures
#   clean      delete book/build/
set -euo pipefail
cd "$(dirname "$0")"

TARGET=""
UNIT_NAME=""
CLEAN=0

usage() { sed -n '2,15p' ./build.sh; }

list_units() {
    find book/chapters -maxdepth 1 -name '*.tex' -printf '%f\n' \
        | sed 's/\.tex$//' | sort
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        book|units|figures|all|clean) TARGET=$1 ;;
        unit)
            TARGET=unit
            shift
            UNIT_NAME=${1:-}
            [[ -n "$UNIT_NAME" ]] || { echo "usage: $0 unit <name>" >&2; exit 1; }
            ;;
        --clean) CLEAN=1 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "unknown argument: $1" >&2; usage; exit 1 ;;
    esac
    shift
done

# Interactive only when someone is actually at the keyboard.
if [[ -z "$TARGET" && -t 0 ]]; then
    echo "What should I compile?"
    echo "  1) Full book (default)  — one PDF, front / main / back matter"
    echo "  2) All units            — one PDF per reconstructed chapter"
    echo "  3) One unit             — you pick the name next"
    echo "  4) Standalone figures   — TikZ / pgfplots only, for review"
    echo "  5) Everything           — book + units + figures"
    echo "  6) Clean                — delete book/build/"
    read -r -p "Choice [1]: " choice
    case "${choice:-1}" in
        1|"") TARGET=book ;;
        2)    TARGET=units ;;
        3)
            TARGET=unit
            echo "Reconstructed units:"
            list_units | sed 's/^/  /'
            read -r -p "Unit name: " UNIT_NAME
            ;;
        4)    TARGET=figures ;;
        5)    TARGET=all ;;
        6)    TARGET=clean ;;
        *)    echo "not a choice: $choice" >&2; exit 1 ;;
    esac
fi
TARGET=${TARGET:-book}

command -v pdflatex >/dev/null || {
    echo "pdflatex not found. Install a TeX Live (or MiKTeX) that provides it." >&2
    exit 1
}

if [[ "$CLEAN" -eq 1 || "$TARGET" == clean ]]; then
    echo "-> make -C book clean"
    make -C book clean
    [[ "$TARGET" == clean ]] && exit 0
fi

case "$TARGET" in
    book)
        echo "-> make -C book book"
        make -C book book
        echo "wrote book/build/book.pdf"
        ;;
    units)
        echo "-> make -C book units"
        make -C book units
        echo "wrote book/build/units/"
        ;;
    unit)
        [[ -n "$UNIT_NAME" ]] || { echo "unit name is empty" >&2; exit 1; }
        [[ -f "book/chapters/${UNIT_NAME}.tex" ]] || {
            echo "no such unit: book/chapters/${UNIT_NAME}.tex" >&2
            echo "have:" >&2
            list_units | sed 's/^/  /' >&2
            exit 1
        }
        echo "-> make -C book unit UNIT=$UNIT_NAME"
        make -C book unit UNIT="$UNIT_NAME"
        echo "wrote book/build/units/${UNIT_NAME}.pdf"
        ;;
    figures)
        echo "-> make -C book figures"
        make -C book figures
        echo "wrote book/build/figures/"
        ;;
    all)
        echo "-> make -C book book units figures"
        make -C book book units figures
        echo "wrote book/build/book.pdf, book/build/units/, book/build/figures/"
        ;;
    *) echo "unknown target: $TARGET" >&2; exit 1 ;;
esac
