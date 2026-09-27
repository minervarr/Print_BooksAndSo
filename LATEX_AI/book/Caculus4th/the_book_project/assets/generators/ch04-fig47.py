# Double cone cut by a plane: parabola / ellipse / hyperbola. Line-art SVG.
import os
import sys
import math
import FreeCAD as App
import Part

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
from ch04_lineart import (
    double_cone, parallelogram, path, line, wrap, write_svg,
)

doc = App.newDocument("ch04_fig47")
H3, R3 = 40.0, 22.0
doc.addObject("Part::Feature", "Up").Shape = Part.makeCone(
    0, R3, H3, App.Vector(0, 0, 0), App.Vector(0, 0, 1))
doc.addObject("Part::Feature", "Dn").Shape = Part.makeCone(
    0, R3, H3, App.Vector(0, 0, 0), App.Vector(0, 0, -1))
doc.recompute()

H, RX, RY = 22.0, 11.5, 3.3
GAP = 50.0
Y0 = 34.0
body = []


def parabola(cx, cy, a, b, t0, t1, n=28):
    pts = []
    for i in range(n):
        t = t0 + (t1 - t0) * i / (n - 1)
        # t along the plane; a*t^2 is transverse
        pts.append((cx + b[0] * t + a[0] * t * t,
                    cy + b[1] * t + a[1] * t * t))
    return path("M " + " L ".join("%.3f %.3f" % p for p in pts))


def rot_ell_arcs(cx, cy, rx, ry, rot, dashed_upper=True):
    """Tilted ellipse: back (smaller y) dashed, front solid."""
    cr, sr = math.cos(rot), math.sin(rot)
    def pt(t):
        x, y = rx * math.cos(t), ry * math.sin(t)
        return (cx + cr * x - sr * y, cy + sr * x + cr * y)
    back, front = [], []
    n = 64
    for i in range(n):
        t0 = 2 * math.pi * i / n
        t1 = 2 * math.pi * (i + 1) / n
        a, b = pt(t0), pt(t1)
        mid = pt(0.5 * (t0 + t1))
        # local 'up' is toward decreasing y in the unrotated frame
        loc_y = -math.sin(rot) * (mid[0] - cx) + math.cos(rot) * (mid[1] - cy)
        (back if loc_y < 0 else front).append((a, b))
    def chain(segs):
        if not segs:
            return ""
        d = "M %.3f %.3f" % segs[0][0]
        for a, b in segs:
            d += " L %.3f %.3f" % b
        return d
    return [
        path(chain(back), dashed=True),
        path(chain(front)),
    ]


# --- (1) parabola: plane // right generator ---
cx = 20.0
body.append(parallelogram([
    (cx - 9.0, Y0 - 27.0),
    (cx + 8.5, Y0 - 29.5),
    (cx + 18.0, Y0 + 20.0),
    (cx + 0.5, Y0 + 22.5),
]))
body += double_cone(cx, Y0, H, RX, RY)
body.append(parabola(cx - 0.8, Y0 - 12.5, (0.15, 8.8), (4.6, 0.4), -1.05, 1.05))
body.append(line((cx + RX - 0.6, Y0 - H + 7), (cx + 5.0, Y0 - 3), dashed=True))

# --- (2) ellipse: shallower plane ---
cx = 20.0 + GAP
body.append(parallelogram([
    (cx - 18.0, Y0 - 3.5),
    (cx + 1.5, Y0 - 17.5),
    (cx + 19.0, Y0 - 4.5),
    (cx - 0.5, Y0 + 9.5),
]))
body += double_cone(cx, Y0, H, RX, RY)
body += rot_ell_arcs(cx + 0.3, Y0 - 6.0, 8.6, 2.35, math.radians(24))

# --- (3) hyperbola: steep plane through both nappes ---
cx = 20.0 + 2 * GAP
body.append(parallelogram([
    (cx - 6.5, Y0 - 31.0),
    (cx + 11.5, Y0 - 32.5),
    (cx + 20.0, Y0 + 29.0),
    (cx + 2.0, Y0 + 30.5),
]))
body += double_cone(cx, Y0, H, RX, RY)
body.append(parabola(cx + 1.4, Y0 - 15.5, (0.1, 7.4), (4.0, 0.2), -1.0, 1.0))
body.append(parabola(cx + 5.2, Y0 + 16.0, (0.1, -6.6), (4.2, 0.15), -1.0, 1.0))
body.append(line((cx + RX - 1.0, Y0 - H + 8), (cx + 6.0, Y0 - 1), dashed=True))
body.append(line((cx + 8.0, Y0 + 7), (cx + RX, Y0 + H - 4), dashed=True))

svg = wrap(body, 20.0 + 2 * GAP + 24.0, 70.0)
out = write_svg("ch04-fig47", svg)
App.Console.PrintMessage("SVG written: %s\n" % out)
