#!/usr/bin/env python3
"""Trace a scanned figure's pixels into vector paths that TikZ can render.

Last-resort tracer for unique ink that cannot be reconstructed as
geometry or as a pgfplots graph. Prefer hand TikZ / pgfplots: traced
paths are photocopies of the scan and do not inherit the document font.

It thresholds the raster to bilevel (dark = ink) and turns the bitmap
into vector paths. Coordinates are scan pixels, y' = height - y_scan,
drawn with [x=0.0269mm, y=0.0269mm].

Two strategies, pick per figure:

- ``--method potrace`` (default): trace region contours, emit one TikZ
  ``\\fill`` per closed subpath. Good for scanned *shaded* art and solid
  blocks. Wrong tool for line art: anti-aliasing bridges strokes into one
  connected mass, and potrace fills the area it encloses, producing a
  solid blob instead of line work.
- ``--method centerline``: skeletonise (Zhang-Suen thinning) and emit the
  stroke centre-lines as stroked polylines, with ``line width`` set from
  the bitmap's measured mean stroke thickness. This is the strategy for
  line art: no enclosed-area fill, topology preserved, stroke widths match
  the scan.

What you get is a vector drawing whose silhouette *is* the scan's
silhouette — the geometry no longer has to be re-measured by hand.

Usage:
    python3 tools/trace_figure.py INPUT.png OUTPUT.tex [--threshold 160]
    python3 tools/trace_figure.py INPUT.png OUTPUT.tex --method centerline [--line-width 0.19]
"""

import argparse
import re
import subprocess
import sys
import warnings
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image


def to_pbm(bitmap, path):
    h, w = bitmap.shape
    out = bytearray(b"P4\n%d %d\n" % (w, h))
    for row in bitmap:
        bits = bytearray((w + 7) // 8)
        for x in range(w):
            if row[x]:
                bits[x // 8] |= 0x80 >> (x % 8)
        out += bits
    with open(path, "wb") as fh:
        fh.write(out)


_TOK = re.compile(r"([MLCZmlczhvHV]|[-\d.eE+]+)")


def iter_tokens(d):
    for m in _TOK.finditer(d):
        v = m.group(1)
        if v and v[0] in "MLCZmlczhvHV":
            yield v
        else:
            yield float(v)


def svg_curves_to_tikz(d, scale):
    """Convert an SVG path `d` string into TikZ \fill statements, one per
    closed subpath.

    potrace emits absolute M/L/C/Z; the tokeniser also copes with
    m/l/h/v/c relaxed forms should another tracer be used later. Each
    subpath is an independent closed region, so each becomes its own
    \fill — chaining them inside a single path would make PGF fill the
    wedges between the connector lines. Coordinates come out in potrace's
    user space (10 px per unit, y up, origin at the bottom) and are mapped
    to scan-px: x*scale, y*scale.
    """
    it = iter_tokens(d)
    out = []
    x = y = cx = cy = None
    cmd = None

    def emit_point(px, py):
        nonlocal x, y
        x, y = px, py
        out[-1].append("(%.2f, %.2f)" % (px * scale, py * scale))

    while True:
        try:
            t = next(it)
        except StopIteration:
            break
        if isinstance(t, str):
            cmd = t
            continue
        if cmd == "H":
            emit_point(t, y)
        elif cmd == "V":
            emit_point(x, t)
        elif cmd == "M":
            yy = next(it)
            if not out or out[-1]:
                out.append([])  # a new closed subpath
            emit_point(t, yy)
            cmd = "L"
        elif cmd == "L":
            yy = next(it)
            out[-1].append(" -- ")
            emit_point(t, yy)
            cmd = "L"
        elif cmd == "C":
            x1, y1 = t, next(it)
            x2, y2 = next(it), next(it)
            xx, y3 = next(it), next(it)
            out[-1].append(" .. controls (%.2f, %.2f) and (%.2f, %.2f) .. (%.2f, %.2f)"
                           % (x1 * scale, y1 * scale, x2 * scale, y2 * scale,
                              xx * scale, y3 * scale))
            x, y = xx, y3
        elif cmd in ("m", "l"):
            yy = next(it)
            xx, y3 = t + (x or 0), yy + (y or 0)
            if not out or out[-1]:
                out.append([])
            emit_point(xx, y3)
            cmd = "l"
        elif cmd == "c":
            ox, oy = x or 0, y or 0
            x1, y1 = t + ox, next(it) + oy
            x2, y2 = next(it) + ox, next(it) + oy
            xx, y3 = next(it) + ox, next(it) + oy
            out[-1].append(" .. controls (%.2f, %.2f) and (%.2f, %.2f) .. (%.2f, %.2f)"
                           % (x1 * scale, y1 * scale, x2 * scale, y2 * scale,
                              xx * scale, y3 * scale))
            x, y = xx, y3
        elif cmd == "h":
            emit_point(t + (x or 0), y)
        elif cmd == "v":
            emit_point(x, t + (y or 0))
        else:
            warnings.warn("unhandled command %r" % cmd)
    parts = ["\\fill " + " ".join(sub) + " -- cycle;" for sub in out if sub]
    if not parts:
        raise ValueError("no path data")
    return parts


import numpy as _np


def _neighbours(p):
    n2 = _np.roll(p, 1, axis=0); n2[0, :] = 0
    n6 = _np.roll(p, -1, axis=0); n6[-1, :] = 0
    n4 = _np.roll(p, 1, axis=1); n4[:, 0] = 0
    n8 = _np.roll(p, -1, axis=1); n8[:, -1] = 0
    n3 = _np.roll(n2, 1, axis=1); n3[:, 0] = 0
    n9 = _np.roll(n2, -1, axis=1); n9[:, -1] = 0
    n5 = _np.roll(n6, 1, axis=1); n5[:, 0] = 0
    n7 = _np.roll(n6, -1, axis=1); n7[:, -1] = 0
    return n2, n3, n4, n5, n6, n7, n8, n9


def zhang_suen(bitmap):
    """Thin a bilevel bitmap to 1-px centre-lines (Zhang-Suen)."""
    p = bitmap.astype(np.uint8)
    while True:
        changed = False
        n2, n3, n4, n5, n6, n7, n8, n9 = _neighbours(p)
        B = n2 + n3 + n4 + n5 + n6 + n7 + n8 + n9
        order = [n9, n2, n3, n4, n5, n6, n7, n8, n9]
        A = np.zeros_like(p)
        for i in range(8):
            A += ((order[i] == 0) & (order[i + 1] == 1)).astype(np.uint8)
        for step in (1, 2):
            c = (B >= 2) & (B <= 6) & (A == 1) & (p == 1)
            if step == 1:
                c &= (n2 * n4 * n6 == 0) & (n4 * n6 * n8 == 0)
            else:
                c &= (n2 * n4 * n8 == 0) & (n2 * n6 * n8 == 0)
            y, x = np.where(c)
            if len(y):
                p[y, x] = 0
                changed = True
        if not changed:
            return p == 1


def extract_chains(thin):
    """Decompose a skeleton into 8-connected polylines, split at junctions.

    Returns list of chains; each chain is [(x, y), ...] in image (col,row)
    space. Junction pixels end their chain so branches reconnect later at
    the same pixel. Loops with no endpoints are also extracted.
    """
    H, W = thin.shape
    n2, n3, n4, n5, n6, n7, n8, n9 = _neighbours(thin.astype(np.uint8))
    B = (n2 + n3 + n4 + n5 + n6 + n7 + n8 + n9).astype(np.uint8)
    visited = _np.zeros_like(thin, dtype=bool)
    chains = []

    def walk(sx, sy):
        chain = [(sx, sy)]
        visited[sy, sx] = True
        px, py, prv = sx, sy, None
        while True:
            if B[py, px] >= 3:
                break
            nxt = None
            for dx, dy in ((1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0),
                           (-1, 1), (0, 1), (1, 1)):
                qx, qy = px + dx, py + dy
                if 0 <= qx < W and 0 <= qy < H and thin[qy, qx] and not visited[qy, qx] \
                        and (qx, qy) != prv:
                    nxt = (qx, qy)
                    break
            if nxt is None:
                break
            px, py, prv = nxt[0], nxt[1], (px, py)
            chain.append((px, py))
            visited[py, px] = True
        return chain

    for y, x in _np.argwhere(thin & (B == 1)):
        c = walk(int(x), int(y))
        if len(c) >= 3:
            chains.append(c)
    for y, x in _np.argwhere(thin & ~visited):
        c = walk(int(x), int(y))
        if len(c) >= 3:
            chains.append(c)
    return chains


def simplify_chain(chain, tol=0.6):
    """Drop collinear midpoints from a pixel chain within `tol` px."""
    if len(chain) < 3:
        return chain
    out = [chain[0]]
    i = 0
    while i < len(chain) - 1:
        ax, ay = out[-1]
        j = i + 1
        bx, by = chain[i]
        cx, cy = chain[j]
        while True:
            dx, dy = cx - ax, cy - ay
            nrm = (dx * dx + dy * dy) ** 0.5
            bx2, by2 = bx - ax, by - ay
            off = abs(dx * by2 - dy * bx2) / nrm if nrm else 0
            if off > tol or j >= len(chain) - 1:
                break
            bx, by = cx, cy
            j += 1
            if j >= len(chain):
                break
            cx, cy = chain[j]
        out.append(chain[min(j, len(chain) - 1)])
        i = min(j, len(chain) - 1)
    return out


def measure_width(bitmap, thin):
    n = int(thin.sum())
    if n == 0:
        return None
    return max(1.0, bitmap.astype(int).sum() / n)


def emit_centerline(thin, height, line_width_mm):
    chains = extract_chains(thin)
    chains = [simplify_chain(c) for c in chains]
    draws = []
    for c in chains:
        pts = " -- ".join("(%.1f, %.0f)" % (x, height - y) for x, y in c)
        draws.append("\\draw[line width=%.2fmm] %s;" % (line_width_mm, pts))
    return draws


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="grayscale PNG of the figure (or other raster)")
    ap.add_argument("output", help="generated .tex to write the tikzpicture to")
    ap.add_argument("--threshold", type=int, default=190,
                    help="bilevel threshold; darker pixels are ink (default 190)")
    ap.add_argument("--height", type=int, default=None,
                    help="scan height in px; y is flipped so y' = height - y "
                         "(default: the image's own height)")
    ap.add_argument("--method", choices=("potrace", "centerline"), default="potrace",
                    help="trace strategy: potrace fills regions, centerline strokes (default potrace)")
    ap.add_argument("--line-width", type=float, default=None,
                    help="centerline stroke width in mm (default: measured from the bitmap)")
    ap.add_argument("--potrace", default="potrace")
    args = ap.parse_args()

    im = Image.open(args.input).convert("L")
    a = np.asarray(im, dtype=np.uint8)
    h, w = a.shape
    if args.height is None:
        args.height = h
    elif args.height != h:
        raise SystemExit("--height %d does not match image height %d" % (args.height, h))

    bitmap = a < args.threshold

    if args.method == "potrace":
        pbm = args.output + ".pbm"
        svg = args.output + ".svg"
        to_pbm(bitmap, pbm)
        subprocess.run([args.potrace, "-b", "svg", "-o", svg, pbm], check=True)
        tree = ET.parse(svg)
        ns = "{http://www.w3.org/2000/svg}"
        scale = 0.1  # potrace's user space is 10 px per unit (match SVG scale(0.1,-0.1))
        paths = []
        for path in tree.getroot().iter(ns + "path"):
            d = path.get("d")
            if d and path.get("fill", "#000000") not in ("none",):
                try:
                    paths.extend(svg_curves_to_tikz(d, scale))
                except ValueError:
                    warnings.warn("skipping a trivially empty path")
        if not paths:
            raise SystemExit("no usable paths traced from %s" % args.input)
        body = "\n".join(paths)
        count = len(paths)
        note = "traced vector fill paths (potrace)"
    else:
        thin = zhang_suen(bitmap)
        if args.line_width is None:
            wpx = measure_width(bitmap, thin)
            args.line_width = max(wpx * 0.0269, 0.05)
        draws = emit_centerline(thin, h, args.line_width)
        if not draws:
            raise SystemExit("no usable centre-lines traced from %s" % args.input)
        body = "\n".join(draws)
        count = len(draws)
        note = "centre-line polylines, line width %.2fmm" % args.line_width

    head = (
        "%% This file was generated by tools/trace_figure.py from %r — do not\n"
        "%% hand-edit; re-run the tool instead. It redraws a scanned figure as\n"
        "%% %s.\n"
        "%% Coordinates are scan pixels,\n"
        "%% y' = %d - y_scan; draw it with [x=0.0269mm, y=0.0269mm].\n"
        "%% Generated by tools/trace_figure.py --method %s.\n"
        "\\begin{tikzpicture}[x=0.0269mm, y=0.0269mm, line cap=round, line join=round]\n"
        % (args.input, note, args.height, args.method)
    )
    tail = "\n\\end{tikzpicture}\n"
    with open(args.output, "w") as fh:
        fh.write(head + body + tail)

    print("wrote %s: %d traced %s (%.0f KB)" % (args.output, count, args.method, len(body) / 1024))


if __name__ == "__main__":
    main()