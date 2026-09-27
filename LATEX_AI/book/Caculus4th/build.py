#!/usr/bin/env python3
"""Build print PDFs and the HTML smoke of the reconstructed Calculus book.

Print: LuaLaTeX, aux in the_book_project/build/<variant>/, named files in pdf/.
HTML:  make4ht + MathJax → html/ (front + chapters 1–8; figures as SVG).

Usage: python3 build.py [all|print|print-v|print-h|html]
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

PRINT = ("print-v", "print-h")
PDF_NAME = {
    "print-v": "Calculus-4e-print-A4.pdf",
    "print-h": "Calculus-4e-print-A4-landscape.pdf",
}

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT / "the_book_project"
SHARE = ROOT / "pdf"
HTML_OUT = ROOT / "html"

ENGINE = (
    "lualatex",
    "-interaction=nonstopmode",
    "-halt-on-error",
    "-shell-escape",
)


def build_one(variant: str) -> Path:
    outdir = PROJECT / "build" / variant
    outdir.mkdir(parents=True, exist_ok=True)
    cmd = [
        *ENGINE,
        f"-output-directory={outdir}",
        "-jobname=main",
        f"\\def\\BookVariant{{{variant}}}\\input{{main.tex}}",
    ]
    for _ in range(2):
        result = subprocess.run(cmd, cwd=PROJECT)
        if result.returncode != 0:
            sys.exit(result.returncode)
    pdf = outdir / "main.pdf"
    SHARE.mkdir(parents=True, exist_ok=True)
    named = SHARE / PDF_NAME[variant]
    shutil.copy2(pdf, named)
    print(named)
    return named


def export_html_svg() -> None:
    """TikZ → assets/rendered/*.svg (skip up-to-date). Kit tool via book shim."""
    shim = PROJECT / "assets" / "export-figures-svg.py"
    result = subprocess.run(
        [sys.executable, str(shim), "--quiet"], cwd=PROJECT
    )
    if result.returncode != 0:
        sys.exit(result.returncode)


def build_html() -> Path:
    """HTML: html.tex (title through chapter 8), MathJax, SVG figures."""
    export_html_svg()
    out = HTML_OUT
    bdir = PROJECT / "build" / "html"
    out.mkdir(parents=True, exist_ok=True)
    bdir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "make4ht",
        "-l",
        "-s",
        "-d",
        str(out),
        "-B",
        str(bdir),
        "-j",
        "index",
        "-c",
        str(PROJECT / "html.cfg"),
        "html.tex",
        "xhtml,charset=utf-8,mathjax,fn-in",
    ]
    result = subprocess.run(cmd, cwd=PROJECT)
    if result.returncode != 0:
        sys.exit(result.returncode)
    index = out / "index.html"
    if index.is_file():
        html = index.read_text(encoding="utf-8")
        html = html.replace("<title></title>", "<title>Calculus, Fourth Edition</title>", 1)
        html = html.replace("<title></title>", "<title>Calculus, Fourth Edition</title>", 1)
        html = html.replace("alt='PIC'", "alt='Figure'")
        # Safety net: \Preamble can mangle #1 in html.cfg. Force the abs macro.
        needle = 'macros: { dom:'
        want = 'macros: { abs: ["\\\\left\\\\lvert#1\\\\right\\\\rvert", 1], dom:'
        if "abs: [" not in html and needle in html:
            html = html.replace(needle, want, 1)
        index.write_text(html, encoding="utf-8")
    print(index)
    # Same gate as `python3 chapter.py test-html`.
    sys.path.insert(0, str(ROOT))
    from chapter import html_mathjax_failures  # noqa: E402

    fails = html_mathjax_failures(out)
    if fails:
        print("FAIL html MathJax")
        for f in fails:
            print(" -", f)
        sys.exit(1)
    print("PASS html MathJax")
    return index


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build Calculus reconstruction (print PDF + HTML)."
    )
    parser.add_argument(
        "variant",
        nargs="?",
        choices=("all", "print", "html") + PRINT,
        help="print-v / print-h / html; omit or 'all' = both prints (not HTML)",
    )
    args = parser.parse_args()
    if args.variant == "html":
        build_html()
        return
    if args.variant in (None, "all", "print"):
        variants = PRINT
    else:
        variants = (args.variant,)
    for variant in variants:
        build_one(variant)


if __name__ == "__main__":
    main()
