# Dandelin spheres in a cylinder. Line-art SVG.
import os
import sys
import FreeCAD as App
import Part

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
from ch04_lineart import (
    cylinder, circle, ellipse, parallelogram, line, path, text, sub,
    wrap, write_svg, ell_d,
)

doc = App.newDocument("ch04_fig49")
R, H = 16.0, 70.0
doc.addObject("Part::Feature", "Cyl").Shape = Part.makeCylinder(
    R, H, App.Vector(0, 0, 0))
doc.addObject("Part::Feature", "S1").Shape = Part.makeSphere(
    R, App.Vector(0, 0, H - R - 2.0))
doc.addObject("Part::Feature", "S2").Shape = Part.makeSphere(
    R, App.Vector(0, 0, R + 2.0))
doc.recompute()

cx = 30.0
rx, ry = 14.0, 4.2
top, bot = 12.0, 86.0
r_sph = 14.0
c1y = top + r_sph - 0.6
c2y = bot - r_sph + 0.6
eq1, eq2 = c1y, c2y

body = []

# tilted cutting plane through the cylinder
body.append(parallelogram([
    (cx - 26.0, 44.0),
    (cx + 12.0, 26.0),
    (cx + 36.0, 40.0),
    (cx - 2.0, 58.0),
]))

body += cylinder(cx, top, bot, rx, ry)

# S1
body.append(circle(cx, c1y, r_sph, fill="#ffffff"))
body.append(path(ell_d(cx, eq1, rx, ry), fill="none", dashed=True))
body.append(path("M %.3f %.3f A %.3f %.3f 0 0 0 %.3f %.3f"
                 % (cx - rx, eq1, rx, ry, cx + rx, eq1)))
# S2
body.append(circle(cx, c2y, r_sph, fill="#ffffff"))
body.append(path(ell_d(cx, eq2, rx, ry), fill="none", dashed=True))
body.append(path("M %.3f %.3f A %.3f %.3f 0 0 0 %.3f %.3f"
                 % (cx - rx, eq2, rx, ry, cx + rx, eq2)))

# cylinder sides over the spheres
body.append(line((cx - rx, top + ry), (cx - rx, bot - ry)))
body.append(line((cx + rx, top + ry), (cx + rx, bot - ry)))
body.append(ellipse(cx, top, rx, ry, fill="none"))

F1 = (cx + 1.6, c1y + r_sph - 1.4)
F2 = (cx - 3.5, c2y - r_sph + 1.0)
z = (cx + 7.2, 43.5)
C1pt = (z[0], eq1 + 1.6)
body.append(line(z, C1pt))
body.append(line(z, F1))
for p in (F1, F2, z, C1pt):
    body.append(circle(p[0], p[1], 0.55, fill="#000000"))

body.append(text(cx + r_sph + 2.6, c1y - 7.5, sub("S", "1"), size=3.8, anchor="start"))
body.append(text(cx, eq1 + 1.4, sub("C", "1"), size=3.4))
body.append(text(cx + r_sph + 2.6, c2y + 9.0, sub("S", "2"), size=3.8, anchor="start"))
body.append(text(cx, eq2 + 1.6, sub("C", "2"), size=3.4))
body.append(text(F1[0] - 4.0, F1[1] - 2.6, sub("F", "1"), size=3.4, anchor="end"))
body.append(text(F2[0] - 3.4, F2[1] - 1.2, sub("F", "2"), size=3.4, anchor="end"))
body.append(text(z[0] + 2.8, z[1] + 3.4, "z", size=3.6, anchor="start"))
body.append(text(C1pt[0] + 3.8, 0.5 * (C1pt[1] + z[1]) + 2.2, "L", size=3.5, anchor="start"))
body.append(text(cx + 28.0, 32.5, "P", size=3.8, anchor="start"))

svg = wrap(body, 70.0, 100.0)
out = write_svg("ch04-fig49", svg)
App.Console.PrintMessage("SVG written: %s\n" % out)
