# Cylinder with a cutting plane (edge-on). Line-art SVG.
import os
import sys
import FreeCAD as App
import Part

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
from ch04_lineart import cylinder, line, wrap, write_svg, ellipse

doc = App.newDocument("ch04_fig48")
cyl = Part.makeCylinder(18.0, 50.0, App.Vector(0, 0, -25.0))
doc.addObject("Part::Feature", "Cyl").Shape = cyl
doc.recompute()

cx, top, bot, rx, ry = 22.0, 8.0, 52.0, 12.0, 3.6
body = []
body += cylinder(cx, top, bot, rx, ry)
# axes through the mid-height
mid = 0.5 * (top + bot)
body.append(line((cx - 18.0, mid), (cx + 18.0, mid)))
body.append(line((cx, top - 6.0), (cx, bot + 6.0)))
# cutting plane, viewed nearly edge-on: a diagonal across the cylinder
body.append(line((cx - 8.5, mid + 10.5), (cx + 8.5, mid - 10.5)))

svg = wrap(body, 44.0, 66.0)
out = write_svg("ch04-fig48", svg)
App.Console.PrintMessage("SVG written: %s\n" % out)
