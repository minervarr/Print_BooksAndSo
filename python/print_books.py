#!/usr/bin/env python3
"""Locate the print-books C++ binary and replace this process with it.

The product CLI is C++ (`build/*/cli/print-books`). This script exists so you
can drive that binary from current CPython with no venv and no third-party
packages: it finds the executable and `os.execv`s it. It does not parse flags,
write TOML, or touch a PDF.

Usage:
    ./print-books init BOOK.pdf [-o project.toml]
    ./print-books build project.toml [-o out.pdf]
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve()
_REPO_ROOT = _SCRIPT.parent.parent

# Fixed well-known trees first (release, then debug, then asan, then native).
_WELL_KNOWN = (
    "build/linux/cli/print-books",
    "build/linux_debug/cli/print-books",
    "build/linux_asan/cli/print-books",
    "build/linux_native/cli/print-books",
    "build/linux_native_debug/cli/print-books",
)


def _is_executable(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)


def _is_launcher(path: Path) -> bool:
    """True if *path* is this Python locator (would recurse under execv).

    Both `python/print_books.py` and the repo-root `./print-books` front door
    count: putting `.` on PATH must not exec the wrapper again.
    """
    try:
        resolved = path.resolve()
    except OSError:
        return False
    try:
        if resolved.samefile(_SCRIPT):
            return True
    except OSError:
        pass
    front = _REPO_ROOT / "print-books"
    try:
        if front.exists() and resolved.samefile(front):
            return True
    except OSError:
        pass
    return resolved == front


def find_binary() -> str | None:
    """Return the path to the print-books binary, or None if not found.

    Search order (first hit wins):
      1. $PRINT_BOOKS_BIN when it names an executable file
      2. a PATH entry named print-books that is not this locator
         (`python/print_books.py` or repo-root `./print-books`)
      3. well-known build trees under the repo root (parent of python/)
    """
    env = os.environ.get("PRINT_BOOKS_BIN")
    if env:
        candidate = Path(env)
        if _is_executable(candidate) and not _is_launcher(candidate):
            return str(candidate.resolve())

    for directory in os.environ.get("PATH", "").split(os.pathsep):
        if not directory:
            continue
        candidate = Path(directory) / "print-books"
        if _is_executable(candidate) and not _is_launcher(candidate):
            return str(candidate.resolve())

    build_root = _REPO_ROOT / "build"
    ordered: list[Path] = [_REPO_ROOT / rel for rel in _WELL_KNOWN]
    if build_root.is_dir():
        ordered.extend(sorted(build_root.glob("linux_custom-*/cli/print-books")))

    for candidate in ordered:
        if _is_executable(candidate):
            return str(candidate.resolve())
    return None


def main() -> None:
    binary = find_binary()
    if binary is None:
        print(
            "error: print-books binary not found; run scripts/linux/build.sh",
            file=sys.stderr,
        )
        sys.exit(127)
    os.execv(binary, [binary, *sys.argv[1:]])


if __name__ == "__main__":
    main()
