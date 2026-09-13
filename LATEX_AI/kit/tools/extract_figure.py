#!/usr/bin/env python3
"""Pull a figure out of a scanned unit PDF.

Two modes, pick the one that matches the scan:

- default: rasterise page PAGE at DPI (pdftoppm). Use this to *look* at a
  page, then crop the figure by eye. A rendered page is not the original
  image object.
- ``--pdfimages``: dump the embedded image objects on that page
  (pdfimages). Use this when the figure is its own object, often at a
  higher ppi than the page render.

This kit does not redraw from the crop. The crop is a reference for a
semantic TikZ / pgfplots reconstruction (see kit/README.md).

Usage:
    extract_figure.py SOURCE.pdf PAGE OUT.png
    extract_figure.py SOURCE.pdf PAGE OUT.png --dpi 300
    extract_figure.py SOURCE.pdf PAGE prefix --pdfimages
"""

import argparse
import subprocess
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="unit PDF (a scan)")
    ap.add_argument("page", type=int, help="1-based page number")
    ap.add_argument("out", help="output PNG path, or prefix with --pdfimages")
    ap.add_argument("--dpi", type=int, default=300,
                    help="rasterisation resolution (default 300)")
    ap.add_argument("--pdfimages", action="store_true",
                    help="dump embedded image objects instead of a page render")
    args = ap.parse_args()

    src = Path(args.source)
    if not src.is_file():
        raise SystemExit("no such file: %s" % src)

    if args.pdfimages:
        prefix = args.out
        subprocess.run(
            ["pdfimages", "-png", "-f", str(args.page), "-l", str(args.page),
             str(src), prefix],
            check=True,
        )
        print("wrote pdfimages prefix %s (page %d)" % (prefix, args.page))
        return

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    stem = out.with_suffix("")
    subprocess.run(
        ["pdftoppm", "-png", "-f", str(args.page), "-l", str(args.page),
         "-r", str(args.dpi), str(src), str(stem)],
        check=True,
    )
    produced = list(out.parent.glob(stem.name + "-*.png"))
    if len(produced) == 1 and produced[0] != out:
        produced[0].replace(out)
    print("wrote %s (page %d @ %d dpi)" % (out, args.page, args.dpi))


if __name__ == "__main__":
    sys.exit(main())
