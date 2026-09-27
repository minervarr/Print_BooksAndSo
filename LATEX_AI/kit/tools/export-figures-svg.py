#!/usr/bin/env python3
"""Export TikZ/pgfplots figures to SVG for HTML (and any later reuse).

Print PDF still \\input the TeX snippets. HTML \\includegraphics these SVGs.
FreeCAD drawings already live in assets/rendered/*.svg and are left alone.

    python3 export-figures-svg.py --assets book/.../assets
    python3 export-figures-svg.py --assets book/.../assets ch04-fig07
    python3 export-figures-svg.py --assets book/.../assets --force

stdlib + lualatex + pdftocairo (or inkscape).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from figure_render import (  # noqa: E402
    export_tex_svg,
    map_jobs,
    nworkers,
    scratch_dir,
    tex_stems,
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("stem", nargs="?", help="e.g. ch04-fig07; omit for all TikZ")
    ap.add_argument("--assets", type=Path, required=True,
                    help="book assets/ (geometric, plots, rendered)")
    ap.add_argument("--force", action="store_true",
                    help="rebuild even if SVG is newer than the .tex")
    ap.add_argument("--jobs", type=int, default=0,
                    help="parallel lualatex workers (default: min(8, nproc))")
    ap.add_argument("--quiet", action="store_true",
                    help="only print summary and failures")
    args = ap.parse_args()
    assets = args.assets.resolve()
    project = assets.parent
    out = assets / "rendered"
    out.mkdir(parents=True, exist_ok=True)
    jobs_list = tex_stems(assets, args.stem)
    workers = nworkers(args.jobs)
    failures: list[str] = []
    wrote = 0
    skipped = 0

    def one(item: tuple[str, Path]) -> str:
        stem, src = item
        dest = out / f"{stem}.svg"
        # Unique tmp per worker so parallel lualatex jobs do not collide.
        with scratch_dir(f"fig-svg-{stem}-") as tmpname:
            return export_tex_svg(src, dest, project, Path(tmpname), args.force)

    results = map_jobs(one, jobs_list, workers)
    for item, status, err in sorted(results, key=lambda t: t[0][0]):
        stem, src = item
        if err is not None:
            print("FAIL", stem, file=sys.stderr)
            print(err, file=sys.stderr)
            failures.append(stem)
            continue
        dest = out / f"{stem}.svg"
        if status == "skip":
            skipped += 1
            if not args.quiet:
                print("skip", dest)
        else:
            wrote += 1
            if not args.quiet:
                print(dest)

    print(f"svg wrote {wrote}, skip {skipped}, fail {len(failures)} → {out}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
