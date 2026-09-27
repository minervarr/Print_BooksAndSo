# Dandelin spheres on a cone (ellipse) and a double cone (hyperbola). Line-art SVG.
import os
import sys
import FreeCAD as App
import Part

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
from ch04_lineart import (
    double_cone, circle, ellipse, parallelogram, line, path, text, sub,
    wrap, write_svg, ell_d, poly_d,
)

doc = App.newDocument("ch04_fig50")
H3, R3 = 50.0, 28.0
doc.addObject("Part::Feature", "Up").Shape = Part.makeCone(
    0, R3, H3, App.Vector(0, 0, 0), App.Vector(0, 0, 1))
doc.addObject("Part::Feature", "Dn").Shape = Part.makeCone(
    0, R3, H3, App.Vector(0, 0, 0), App.Vector(0, 0, -1))
doc.recompute()

body = []

# ---------- (a) single nappe, two spheres, cutting plane ----------
ax, ay = 30.0, 64.0
H, RX, RY = 46.0, 24.0, 6.0
top = ay - H
body.append(path(poly_d([
    (ax - RX, top), (ax, ay), (ax + RX, top)
]), fill="#ffffff"))
body.append(line((ax - RX, top), (ax, ay)))
body.append(line((ax + RX, top), (ax, ay)))
body.append(ellipse(ax, top, RX, RY, fill="#ffffff"))

body.append(parallelogram([
    (ax - 24.0, ay - 24.0),
    (ax + 10.0, ay - 36.0),
    (ax + 34.0, ay - 18.0),
    (ax, ay - 6.0),
]))
# cone over the plane near the apex
body.append(path(poly_d([
    (ax - 9.0, ay - 17.5), (ax, ay), (ax + 9.0, ay - 17.5)
]), fill="#ffffff"))
body.append(line((ax - RX, top), (ax, ay)))
body.append(line((ax + RX, top), (ax, ay)))

r1, c1y = 17.0, top + 12.0
body.append(circle(ax, c1y, r1, fill="#ffffff"))
eq1, rx1, ry1 = c1y + 4.2, 16.2, 4.2
body.append(path(ell_d(ax, eq1, rx1, ry1), fill="none", dashed=True))
body.append(path("M %.3f %.3f A %.3f %.3f 0 0 0 %.3f %.3f"
                 % (ax - rx1, eq1, rx1, ry1, ax + rx1, eq1)))

r2, c2y = 6.4, ay - 14.5
body.append(circle(ax + 0.3, c2y, r2, fill="#ffffff"))
eq2, rx2, ry2 = c2y - 1.1, 6.0, 1.7
body.append(path(ell_d(ax + 0.3, eq2, rx2, ry2), fill="none", dashed=True))
body.append(path("M %.3f %.3f A %.3f %.3f 0 0 0 %.3f %.3f"
                 % (ax + 0.3 - rx2, eq2, rx2, ry2, ax + 0.3 + rx2, eq2)))

body.append(circle(ax + 8.2, ay - 25.5, 0.5, fill="#000000"))
body.append(circle(ax - 1.2, c2y - r2 + 0.7, 0.5, fill="#000000"))
body.append(circle(ax + 6.0, ay - 19.0, 0.5, fill="#000000"))
body.append(text(ax, eq1 + 1.7, sub("C", "1"), size=3.4))
body.append(text(ax + r2 + 6.0, c2y + 2.2, sub("C", "2"), size=3.4, anchor="start"))
body.append(text(ax + 11.6, ay - 15.4, "z", size=3.6, anchor="start"))
body.append(text(ax, ay + 7.5, "(a)", size=3.6, italic=False))

# ---------- (b) double cone, one sphere in each nappe ----------
bx, by = 92.0, 42.0
Hb, RXb, RYb = 30.0, 17.0, 4.4
body += double_cone(bx, by, Hb, RXb, RYb)

rU, cUy = 15.5, by - Hb + 8.0
body.append(circle(bx, cUy, rU, fill="#ffffff"))
eqU, rxU, ryU = cUy + 5.8, 16.0, 4.0
body.append(path(ell_d(bx, eqU, rxU, ryU), fill="none", dashed=True))
body.append(path("M %.3f %.3f A %.3f %.3f 0 0 0 %.3f %.3f"
                 % (bx - rxU, eqU, rxU, ryU, bx + rxU, eqU)))
# redraw top rim over the sphere
body.append(ellipse(bx, by - Hb, RXb, RYb, fill="none"))

rL, cLy = 7.2, by + 15.5
body.append(circle(bx, cLy, rL, fill="#ffffff"))
eqL, rxL, ryL = cLy - 1.0, 6.8, 1.85
body.append(path(ell_d(bx, eqL, rxL, ryL), fill="none", dashed=True))
body.append(path("M %.3f %.3f A %.3f %.3f 0 0 0 %.3f %.3f"
                 % (bx - rxL, eqL, rxL, ryL, bx + rxL, eqL)))

body.append(circle(bx + 14.5, eqU + 0.8, 0.5, fill="#000000"))
body.append(circle(bx + 11.0, by - 13.0, 0.5, fill="#000000"))
body.append(circle(bx + 4.2, cLy + rL - 0.5, 0.5, fill="#000000"))
body.append(text(bx, eqU + 1.6, sub("C", "1"), size=3.4))
body.append(text(bx - rL - 7.0, cLy + 1.6, sub("C", "2"), size=3.4, anchor="end"))
body.append(text(bx + 17.2, eqU + 2.0, "z", size=3.6, anchor="start"))
body.append(text(bx, by + Hb + 10.5, "(b)", size=3.6, italic=False))

svg = wrap(body, 122.0, 90.0)
out = write_svg("ch04-fig50", svg)
App.Console.PrintMessage("SVG written: %s\n" % out)
