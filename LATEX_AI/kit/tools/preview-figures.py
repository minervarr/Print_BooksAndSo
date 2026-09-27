#!/usr/bin/env python3
"""Rasterize reconstructed figures for AI review. Not used by main.tex.

TikZ/pgfplots snippets and FreeCAD SVGs become 300 dpi JPEGs in
assets/ai-preview/. scans/ is the original crop; rendered/ is what the
book includes. This folder is only for looking.

    python3 preview-figures.py --assets book/.../assets
    python3 preview-figures.py --assets book/.../assets ch04-fig07
    python3 preview-figures.py --assets book/.../assets --dpi 300

For HTML-quality vectors use export-figures-svg.py instead.

stdlib + lualatex + pdftoppm. SVG via inkscape → PDF → JPEG.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from figure_render import (  # noqa: E402
    compile_tex_pdf,
    pdf_to_jpeg,
    scratch_dir,
    svg_sources,
    svg_to_pdf,
    tex_stems,
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("stem", nargs="?", help="e.g. ch04-fig07; omit for all")
    ap.add_argument("--assets", type=Path, required=True,
                    help="book assets/ (geometric, plots, rendered, ai-preview)")
    ap.add_argument("--dpi", type=int, default=300)
    args = ap.parse_args()
    assets = args.assets.resolve()
    project = assets.parent
    out = assets / "ai-preview"
    out.mkdir(parents=True, exist_ok=True)

    jobs: list[tuple[str, Path, str]] = [
        (s, p, "tex") for s, p in tex_stems(assets, None)
    ]
    jobs += [(s, p, "svg") for s, p in svg_sources(assets, None)]
    if args.stem:
        jobs = [t for t in jobs if t[0] == args.stem]
        if not jobs:
            raise SystemExit(f"no figure named {args.stem!r}")

    failures: list[str] = []
    rows: list[dict] = []
    with scratch_dir("ai-preview-") as tmpname:
        tmp = Path(tmpname)
        for stem, src, kind in jobs:
            dest = out / f"{stem}.jpg"
            try:
                if kind == "tex":
                    pdf = compile_tex_pdf(src, project, tmp, stem)
                    pdf_to_jpeg(pdf, dest, args.dpi)
                else:
                    pdf = tmp / f"{stem}.pdf"
                    svg_to_pdf(src, pdf)
                    pdf_to_jpeg(pdf, dest, args.dpi)
            except (Exception) as e:
                print("FAIL", stem, file=sys.stderr)
                print(e, file=sys.stderr)
                failures.append(stem)
                continue
            print(dest)
            rows.append(
                {
                    "file": dest.name,
                    "source": str(src.relative_to(assets)),
                    "kind": kind,
                    "dpi": args.dpi,
                }
            )
    man = out / "manifest.csv"
    existing: list[dict] = []
    if man.is_file() and args.stem:
        with man.open(newline="") as fh:
            existing = [r for r in csv.DictReader(fh) if r.get("file") != f"{args.stem}.jpg"]
    all_rows = existing + rows
    all_rows.sort(key=lambda r: r.get("file", ""))
    if all_rows:
        with man.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=("file", "source", "kind", "dpi"))
            w.writeheader()
            w.writerows(all_rows)
    if failures:
        print(f"failed {len(failures)}/{len(jobs)}", file=sys.stderr)
        return 1
    print(f"wrote {len(rows)} JPEG(s) → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
