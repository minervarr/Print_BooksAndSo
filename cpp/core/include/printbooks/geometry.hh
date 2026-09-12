// geometry.hh — sheet geometry: the box content may occupy, and how a page fits.
//
// Copyright (C) 2026 nava. AGPLv3 or later; see LICENSE.
//
// Pure arithmetic over PDF user-space points. No PDF library, no I/O.
//
// content_area()  what part of a sheet may be drawn on, once the margin and the
//                 binding gutter are taken out.
// fit()           the uniform scale and offset that centres a source box in a
//                 target box.
#pragma once

#include <string>
#include <string_view>

namespace pb {

// Which edge of a sheet the binding is on.
enum class GutterEdge { Left, Right };

// A sheet, in points. Construction rejects a degenerate size rather than
// letting a zero dimension poison every layout downstream.
struct Size {
    double width;
    double height;

    Size(double w, double h);
};

// A PDF box, lower-left to upper-right. Construction REJECTS an inverted box
// instead of normalising it: x1 < x0 always means a /MediaBox was read wrong,
// and quietly swapping the corners would hide that bug behind slightly-off
// output.
struct Rect {
    double x0;
    double y0;
    double x1;
    double y1;

    Rect(double x0, double y0, double x1, double y1);

    double width() const { return x1 - x0; }
    double height() const { return y1 - y0; }

    static Rect from_size(const Size& s) { return Rect(0.0, 0.0, s.width, s.height); }
};

// A uniform scale plus a translation: `s 0 0 s dx dy cm`.
struct Placement {
    double scale;
    double dx;
    double dy;

    double apply_x(double x) const { return scale * x + dx; }
    double apply_y(double y) const { return scale * y + dy; }
};

// Sheet size in points, by the name the CLI accepts. Throws for an unknown
// name — a silent fallback to A4 would print a whole book at the wrong size.
Size paper(std::string_view name);

// The drawable box of one side of one sheet. The margin comes off all four
// edges; the gutter comes off ONE edge, the binding edge, which the caller
// decides (see plan.hh). Throws if the margin/gutter leaves no content area.
Rect content_area(const Size& sheet, double margin, double gutter, GutterEdge edge);

// Uniform scale + offset placing `source` centred inside `target`. Throws on a
// degenerate source: a blank page's ink bbox comes back 0 0 0 0 and must be
// filtered out before it reaches fit().
Placement fit(const Rect& source, const Rect& target);

}  // namespace pb
