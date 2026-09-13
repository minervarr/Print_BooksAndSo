#!/usr/bin/env python3
"""Score a rendered figure against its source scan, pixel-wise.

The engineering claim behind tools/trace_figure.py is that the vectorised
figure's silhouette *is* the scan's silhouette. This tool verifies that:
it renders a PDF page to PNG, finds the figure's ink, resizes it to the
source frame, and reports IoU / precision / recall against the scan's own
ink at the same binarisation.

Why IoU and not a diff: the two images live at different resolutions
(300 dpi render vs 944 dpi scan) and different rasterisations, so a
pixel-exact match is neither expected nor meaningful. IoU on binarised
ink, with recall on the scan side, tells you whether every stroke of the
original is present and where the reproduction adds or loses ink.

Compare against hand-coded figures (scores ~0.2), where IoU was low
because the geometry was only measured, never aligned.

Usage:
    python3 tools/validate_figure.py ORIG.png PAGE.pdf [PAGE] [--threshold 150]
        e.g. python3 tools/validate_figure.py assets/figures/calcu5-fig1.png \
                 build/main.pdf 39
"""

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image


def frame_ink(path, page):
    """Render page `page` (1-based) of `path` and binarise ink."""
    with tempfile.TemporaryDirectory() as td:
        png = Path(td) / "page.png"
        subprocess.run(["pdftoppm", "-png", "-f", str(page), "-l", str(page),
                        "-r", "300", str(path), str(png.with_suffix(""))],
                       check=True)
        img = sorted(Path(td).glob("page-*.png"))[0]
        a = np.asarray(Image.open(img).convert("L"))
    return a < 128


def bbox(ink):
    ys, xs = np.where(ink)
    if not len(ys):
        return None
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("orig", help="source scan PNG (944 dpi figure)")
    ap.add_argument("pdf", help="PDF to render the figure from")
    ap.add_argument("page", type=int, default=1, nargs="?",
                    help="page number holding the figure (default 1)")
    ap.add_argument("--threshold", type=int, default=150,
                    help="ink threshold on both images (default 150)")
    ap.add_argument("--cols", nargs=2, type=int, default=None,
                    help="page-column band [x0 x1] holding the figure, in 300-dpi "
                         "px; required if the PDF page carries text around it")
    ap.add_argument("--rows", nargs=2, type=int, default=None,
                    help="page-row band [y0 y1] holding the figure (300-dpi px); "
                         "combine with --cols on a text page")
    args = ap.parse_args()

    orig = np.asarray(Image.open(args.orig).convert("L")) < args.threshold
    render = frame_ink(args.pdf, args.page)
    if args.cols is not None:
        x0, x1 = args.cols
        render[:, :x0] = False
        render[:, x1:] = False
    if args.rows is not None:
        y0, y1 = args.rows
        render[:y0, :] = False
        render[y1:, :] = False

    ob = bbox(orig)
    rb = bbox(render)
    if not ob or not rb:
        raise SystemExit("no ink found in one of the images")
    oc = orig[ob[1]:ob[3], ob[0]:ob[2]]
    rc = render[rb[1]:rb[3], rb[0]:rb[2]]

    im = Image.fromarray(rc.astype(np.uint8) * 255).resize(
        (oc.shape[1], oc.shape[0]), Image.LANCZOS)
    rc2 = np.asarray(im) > 127

    tol = max(2, min(oc.shape) // 100)
    best = (0.0, 0, 0)
    for dy in range(-tol, tol + 1):
        for dx in range(-tol, tol + 1):
            y0 = max(0, dy); y1 = min(oc.shape[0], rc2.shape[0] + dy)
            x0 = max(0, dx); x1 = min(oc.shape[1], rc2.shape[1] + dx)
            a = oc[y0:y1, x0:x1]
            b = rc2[y0 - dy:y1 - dy, x0 - dx:x1 - dx]
            i = (a & b).sum(); u = (a | b).sum()
            if u and i / u > best[0]:
                best = (i / u, dy, dx)
    iou, dy, dx = best
    if dy or dx:
        y0 = max(0, dy); y1 = min(oc.shape[0], rc2.shape[0] + dy)
        x0 = max(0, dx); x1 = min(oc.shape[1], rc2.shape[1] + dx)
        oc2 = oc[y0:y1, x0:x1]
        rc3 = rc2[y0 - dy:y1 - dy, x0 - dx:x1 - dx]
        inter = (oc2 & rc3).sum()
        prec = inter / max(rc3.sum(), 1)
        rec = inter / max(oc2.sum(), 1)
    else:
        inter = (oc & rc2).sum()
        prec = inter / max(rc2.sum(), 1)
        rec = inter / max(oc.sum(), 1)

    iou, prec, rec = best[0], 0, 0
    if dy or dx:
        y0 = max(0, dy); y1 = min(oc.shape[0], rc2.shape[0] + dy)
        x0 = max(0, dx); x1 = min(oc.shape[1], rc2.shape[1] + dx)
        oc2 = oc[y0:y1, x0:x1]
        rc3 = rc2[y0 - dy:y1 - dy, x0 - dx:x1 - dx]
        inter = (oc2 & rc3).sum()
        prec = inter / max(rc3.sum(), 1)
        rec = inter / max(oc2.sum(), 1)
    else:
        inter = (oc & rc2).sum()
        prec = inter / max(rc2.sum(), 1)
        rec = inter / max(oc.sum(), 1)
    iou = best[0]

    print("frame %dx%d (orig bbox %dx%d, render bbox %dx%d)" %
          (oc.shape[1], oc.shape[0], oc.shape[1], oc.shape[0], rc.shape[1], rc.shape[0]))
    print("IoU %.3f   precision %.3f   recall %.3f   (shift %+d,%+d)" %
          (iou, prec, rec, dy, dx))
    print("ink: mine %.3f  orig %.3f  (mine %d px, orig %d px)" %
          (rc2.mean(), oc.mean(), rc2.sum(), oc.sum()))


if __name__ == "__main__":
    main()