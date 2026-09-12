// geometry.cc — sheet geometry: the content box, and fitting a page into it.
//
// Copyright (C) 2026 nava. AGPLv3 or later; see LICENSE.

#include "printbooks/geometry.hh"

#include <algorithm>
#include <stdexcept>

#include "printbooks/units.hh"

namespace pb {

Size::Size(double w, double h) : width(w), height(h) {
    if (width <= 0.0 || height <= 0.0)
        throw std::invalid_argument("degenerate size");
}

Rect::Rect(double x0_, double y0_, double x1_, double y1_)
    : x0(x0_), y0(y0_), x1(x1_), y1(y1_) {
    if (x1 < x0 || y1 < y0)
        throw std::invalid_argument("inverted rect");
}

Size paper(std::string_view name) {
    PaperSize p;
    if (!paper_size(name, &p)) {
        std::string msg = "unknown paper '";
        msg += name;
        msg += "'; known sizes: a4, letter";
        throw std::invalid_argument(msg);
    }
    return Size(mm(p.width_mm), mm(p.height_mm));
}

Rect content_area(const Size& sheet, double margin, double gutter, GutterEdge edge) {
    if (gutter < 0.0 || margin < 0.0)
        throw std::invalid_argument("negative margin/gutter");

    const double x0 = margin + (edge == GutterEdge::Left ? gutter : 0.0);
    const double x1 = sheet.width - margin - (edge == GutterEdge::Right ? gutter : 0.0);
    const double y0 = margin;
    const double y1 = sheet.height - margin;

    if (x1 <= x0 || y1 <= y0)
        throw std::invalid_argument("margin + gutter leaves no content area");

    return Rect(x0, y0, x1, y1);
}

Placement fit(const Rect& source, const Rect& target) {
    if (source.width() <= 0.0 || source.height() <= 0.0)
        throw std::invalid_argument("degenerate source box");

    // The - scale * source.x0 term is the one that is easy to forget: a cropped
    // page's box rarely starts at the origin, and dropping it shifts every page
    // on every sheet by the crop offset.
    const double scale =
        std::min(target.width() / source.width(), target.height() / source.height());
    const double dx =
        target.x0 + (target.width() - scale * source.width()) / 2.0 - scale * source.x0;
    const double dy =
        target.y0 + (target.height() - scale * source.height()) / 2.0 - scale * source.y0;
    return Placement{scale, dx, dy};
}

}  // namespace pb
