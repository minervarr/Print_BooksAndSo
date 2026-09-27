#!/usr/bin/env python3
"""Crop one real FIGURE from a scan PDF into a scans/ folder.

Not for equations or full pages. Coordinates are on a 72 dpi preview
(1 pt = 1 px, origin top-left — same as `pdftoppm -r 72`).

    python3 crop-scan.py --pdf BOOK.pdf --scans path/to/scans \
        --page 55 --x 24 --y 618 --width 242 --height 228 --name ch02-fig01
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from pathlib import Path

NAME_RE = re.compile(r"^ch(\d{2})-fig(\d{2})$")
PREVIEW_DPI = 72


def to_px(n: float, dpi: int) -> int:
    return max(1, round(n * dpi / PREVIEW_DPI))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pdf", type=Path, required=True)
    ap.add_argument("--scans", type=Path, required=True, help="output directory")
    ap.add_argument("--page", type=int, required=True, help="1-based page in --pdf")
    ap.add_argument("--x", type=float, required=True, help="left, 72 dpi px")
    ap.add_argument("--y", type=float, required=True, help="top, 72 dpi px")
    ap.add_argument("--width", type=float, required=True)
    ap.add_argument("--height", type=float, required=True)
    ap.add_argument("--name", required=True, help="chNN-figMM")
    ap.add_argument("--dpi", type=int, default=150)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    m = NAME_RE.fullmatch(args.name)
    if not m:
        print("name must be chNN-figMM (e.g. ch02-fig01)", file=sys.stderr)
        return 2
    pdf = args.pdf.resolve()
    scans = args.scans.resolve()
    if not pdf.is_file():
        print("no such file:", pdf, file=sys.stderr)
        return 1
    if args.page < 1 or args.width <= 0 or args.height <= 0:
        print("page >= 1 and width/height > 0", file=sys.stderr)
        return 2

    scans.mkdir(parents=True, exist_ok=True)
    dest = scans / f"{args.name}.png"
    if dest.exists() and not args.force:
        print("exists (use --force):", dest, file=sys.stderr)
        return 1

    x = to_px(args.x, args.dpi)
    y = to_px(args.y, args.dpi)
    w = to_px(args.width, args.dpi)
    h = to_px(args.height, args.dpi)
    prefix = dest.with_suffix("")
    subprocess.run(
        [
            "pdftoppm", "-png",
            "-r", str(args.dpi),
            "-f", str(args.page), "-l", str(args.page),
            "-x", str(x), "-y", str(y), "-W", str(w), "-H", str(h),
            str(pdf), str(prefix),
        ],
        check=True,
    )
    produced = list(dest.parent.glob(prefix.name + "-*.png"))
    if len(produced) == 1 and produced[0] != dest:
        produced[0].replace(dest)
    if not dest.is_file():
        print("pdftoppm wrote nothing at", dest, file=sys.stderr)
        return 1

    manifest = scans / "manifest.csv"
    new_row = {
        "file": dest.name,
        "chapter": m.group(1),
        "figure": m.group(2),
        "pdf": str(pdf),
        "page": args.page,
        "x": args.x,
        "y": args.y,
        "width": args.width,
        "height": args.height,
        "dpi": args.dpi,
    }
    rows: list[dict] = []
    fields = list(new_row.keys())
    if manifest.is_file():
        with manifest.open(newline="") as fh:
            rows = [r for r in csv.DictReader(fh) if r.get("file") != dest.name]
    rows.append(new_row)
    rows.sort(key=lambda r: r.get("file", ""))
    with manifest.open("w", newline="") as fh:
        wri = csv.DictWriter(fh, fieldnames=fields)
        wri.writeheader()
        wri.writerows(rows)
    print(dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
