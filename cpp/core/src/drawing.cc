// drawing.cc — content-stream emitters.
//
// Copyright (C) 2026 nava. AGPLv3 or later; see LICENSE.

#include "printbooks/drawing.hh"

#include <stdexcept>
#include <string>

#include "printbooks/pdfops.hh"

namespace pb {

namespace {

// Slack allowed when counting how many pitches span a box. 170 mm / 5 mm is
// exactly 34, but in binary it can land a hair under and lose a whole column.
constexpr double kEps = 1e-9;

int count(double span, double pitch) {
    return static_cast<int>(span / pitch + kEps) + 1;
}

}  // namespace

std::string dot_grid(const Rect& box, double pitch, double dot, double ink) {
    if (pitch <= 0.0)
        throw std::invalid_argument("pitch must be positive");
    if (dot <= 0.0)
        throw std::invalid_argument("dot diameter must be positive");
    const std::string g = gray(ink);  // throws if ink is outside 0..1
    if (pitch > box.width() || pitch > box.height())
        throw std::invalid_argument("pitch does not fit in the box");

    const int nx = count(box.width(), pitch);
    const int ny = count(box.height(), pitch);

    // Centre the grid: the slack left over after whole pitches is split, so the
    // margins look deliberate instead of the grid hugging one corner.
    const double x0 = box.x0 + (box.width() - (nx - 1) * pitch) / 2.0;
    const double y0 = box.y0 + (box.height() - (ny - 1) * pitch) / 2.0;

    std::string out = "q\n" + g + " G\n" + num(dot) + " w\n1 J";
    for (int iy = 0; iy < ny; ++iy) {
        const std::string y = num(y0 + iy * pitch);
        for (int ix = 0; ix < nx; ++ix) {
            const std::string x = num(x0 + ix * pitch);
            out += "\n" + x + " " + y + " m " + x + " " + y + " l";
        }
    }
    out += "\nS\nQ";
    return out;
}

std::string center_ticks(const Rect& box, double length, double width, double ink) {
    if (length <= 0.0 || width <= 0.0)
        throw std::invalid_argument("length and width must be positive");
    const std::string g = gray(ink);
    if (2.0 * length >= std::min(box.width(), box.height()))
        throw std::invalid_argument("ticks would meet in the middle");

    const double mid_x = (box.x0 + box.x1) / 2.0;
    const double mid_y = (box.y0 + box.y1) / 2.0;

    // bottom (up), top (down), left (right), right (left)
    const double segments[4][4] = {
        {mid_x, box.y0, mid_x, box.y0 + length},
        {mid_x, box.y1, mid_x, box.y1 - length},
        {box.x0, mid_y, box.x0 + length, mid_y},
        {box.x1, mid_y, box.x1 - length, mid_y},
    };

    std::string out = "q\n" + g + " G\n" + num(width) + " w\n0 J";
    for (const auto& s : segments)
        out += "\n" + num(s[0]) + " " + num(s[1]) + " m " + num(s[2]) + " " + num(s[3]) + " l";
    out += "\nS\nQ";
    return out;
}

std::string registration_tick(const Rect& box, Corner corner, double size, double width,
                              double ink) {
    if (size <= 0.0 || width <= 0.0)
        throw std::invalid_argument("size and width must be positive");
    const std::string g = gray(ink);

    double cx, cy, dx, dy;
    switch (corner) {
        case Corner::BottomLeft:  cx = box.x0; cy = box.y0; dx = size;  dy = size;  break;
        case Corner::BottomRight: cx = box.x1; cy = box.y0; dx = -size; dy = size;  break;
        case Corner::TopLeft:     cx = box.x0; cy = box.y1; dx = size;  dy = -size; break;
        case Corner::TopRight:    cx = box.x1; cy = box.y1; dx = -size; dy = -size; break;
        default: throw std::invalid_argument("unknown corner");
    }

    return "q\n" + g + " G\n" + num(width) + " w\n0 J\n" +
           num(cx) + " " + num(cy) + " m " + num(cx + dx) + " " + num(cy) + " l\n" +
           num(cx) + " " + num(cy) + " m " + num(cx) + " " + num(cy + dy) + " l\nS\nQ";
}

}  // namespace pb
