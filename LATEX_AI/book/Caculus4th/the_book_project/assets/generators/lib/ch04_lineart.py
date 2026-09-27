# Shared SVG line-art helpers for ch04 solids (white fill, one black stroke).
import os
import math

SW = 0.50  # mm


def _fmt(p):
    return "%.3f %.3f" % p


def ell_d(cx, cy, rx, ry):
    return ("M %.3f %.3f A %.3f %.3f 0 1 1 %.3f %.3f "
            "A %.3f %.3f 0 1 1 %.3f %.3f Z"
            % (cx - rx, cy, rx, ry, cx + rx, cy, rx, ry, cx - rx, cy))


def poly_d(pts, close=True):
    d = "M " + " L ".join(_fmt(p) for p in pts)
    if close:
        d += " Z"
    return d


def path(d, fill="none", dashed=False, sw=SW):
    dash = ' stroke-dasharray="1.7 1.15"' if dashed else ""
    return ('<path d="%s" fill="%s" stroke="#000000" stroke-width="%.3f" '
            'stroke-linecap="round" stroke-linejoin="round"%s/>'
            % (d, fill, sw, dash))


def line(a, b, dashed=False, sw=SW):
    return path("M %s L %s" % (_fmt(a), _fmt(b)), dashed=dashed, sw=sw)


def circle(cx, cy, r, fill="#ffffff", dashed=False, sw=SW):
    dash = ' stroke-dasharray="1.7 1.15"' if dashed else ""
    return ('<circle cx="%.3f" cy="%.3f" r="%.3f" fill="%s" stroke="#000000" '
            'stroke-width="%.3f"%s/>' % (cx, cy, r, fill, sw, dash))


def ellipse(cx, cy, rx, ry, fill="#ffffff", dashed=False, sw=SW):
    return path(ell_d(cx, cy, rx, ry), fill=fill, dashed=dashed, sw=sw)


def text(x, y, s, size=3.6, anchor="middle", italic=True):
    st = ' font-style="italic"' if italic else ""
    return ('<text x="%.3f" y="%.3f" font-family="Times New Roman, Times, serif" '
            'font-size="%.2f" text-anchor="%s" fill="#000000"%s>%s</text>'
            % (x, y, size, anchor, st, s))


def sub(base, n):
    return ('%s<tspan baseline-shift="sub" font-size="2.5">%s</tspan>'
            % (base, n))


def wrap(body, w, h):
    bg = '<rect x="0" y="0" width="%.3f" height="%.3f" fill="#ffffff" stroke="none"/>' % (w, h)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'shape-rendering="geometricPrecision" '
            'width="%.3fmm" height="%.3fmm" viewBox="0 0 %.3f %.3f">\n'
            '%s\n%s\n</svg>\n' % (w, h, w, h, bg, "\n".join(body)))


def write_svg(name, svg):
    out = os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "rendered",
        name + ".svg"))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as fh:
        fh.write(svg)
    return out


def double_cone(cx, cy, H, rx, ry, fill=True):
    """Double nappe: apex at (cx, cy), rims at cy±H. SVG y down, so +H is down."""
    parts = []
    top, bot = cy - H, cy + H
    if fill:
        parts.append(path(poly_d([
            (cx - rx, top), (cx + rx, top), (cx, cy)
        ]), fill="#ffffff"))
        parts.append(path(poly_d([
            (cx - rx, bot), (cx + rx, bot), (cx, cy)
        ]), fill="#ffffff"))
    parts.append(line((cx - rx, top), (cx + rx, bot)))
    parts.append(line((cx + rx, top), (cx - rx, bot)))
    parts.append(ellipse(cx, top, rx, ry, fill="#ffffff"))
    parts.append(ellipse(cx, bot, rx, ry, fill="#ffffff"))
    return parts


def cylinder(cx, top, bot, rx, ry, fill=True):
    parts = []
    if fill:
        parts.append(path(
            "M %.3f %.3f L %.3f %.3f A %.3f %.3f 0 0 0 %.3f %.3f "
            "L %.3f %.3f A %.3f %.3f 0 0 1 %.3f %.3f Z"
            % (cx - rx, top, cx - rx, bot, rx, ry, cx + rx, bot,
               cx + rx, top, rx, ry, cx - rx, top),
            fill="#ffffff"))
    parts.append(line((cx - rx, top), (cx - rx, bot)))
    parts.append(line((cx + rx, top), (cx + rx, bot)))
    parts.append(ellipse(cx, top, rx, ry, fill="#ffffff"))
    parts.append(ellipse(cx, bot, rx, ry, fill="#ffffff"))
    return parts


def parallelogram(pts, fill="#ffffff"):
    return path(poly_d(pts), fill=fill)


def tilted_ell_pts(cx, cy, rx, ry, rot, n=64):
    cr, sr = math.cos(rot), math.sin(rot)
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x, y = rx * math.cos(t), ry * math.sin(t)
        pts.append((cx + cr * x - sr * y, cy + sr * x + cr * y))
    return pts


def split_front_back(pts, pred):
    """Split a closed polyline into front/back chains using pred(pt)->bool front."""
    n = len(pts)
    front, back = [], []
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        fa, fb = pred(a), pred(b)
        if fa and fb:
            front.append((a, b))
        elif (not fa) and (not fb):
            back.append((a, b))
        else:
            # cut at midpoint
            m = ((a[0] + b[0]) * 0.5, (a[1] + b[1]) * 0.5)
            if fa:
                front.append((a, m))
                back.append((m, b))
            else:
                back.append((a, m))
                front.append((m, b))
    def segs_to_d(segs):
        if not segs:
            return []
        ds = []
        d = "M %s" % _fmt(segs[0][0])
        d += " L %s" % _fmt(segs[0][1])
        for a, b in segs[1:]:
            if abs(a[0] - (float(d.rsplit(" ", 2)[-2]))) > 1e-2:
                ds.append(d)
                d = "M %s L %s" % (_fmt(a), _fmt(b))
            else:
                d += " L %s" % _fmt(b)
        ds.append(d)
        return ds
    return segs_to_d(front), segs_to_d(back)
