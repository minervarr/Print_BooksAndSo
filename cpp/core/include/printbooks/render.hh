// render.hh — one side of one sheet: first as layout, then as a content stream.
//
// Copyright (C) 2026 nava. AGPLv3 or later; see LICENSE.
//
// Rendering is two steps on purpose. layout_side() returns DATA — strings,
// coordinates, sizes, flags. emit() turns that into PDF operators. The split
// exists because text is drawn as glyph outlines: a finished stream is a few
// hundred path operators and cannot be searched for "CHAPTER ONE". Layout can
// be asserted directly, and it is also the natural thing for the C++ port's
// golden tests to diff.
#pragma once

#include <optional>
#include <string>
#include <vector>

#include "printbooks/drawing.hh"
#include "printbooks/geometry.hh"
#include "printbooks/metrics.hh"
#include "printbooks/plan.hh"
#include "printbooks/units.hh"

namespace pb {

// The sheet and what is reserved around its edges.
struct Layout {
    Size paper;
    double margin;
    double gutter;
};

// The notes-page dot grid. 0.25 mm is a floor, not a preference: below about
// 0.2 mm most printers drop the dot entirely and the page comes out blank.
struct GridSpec {
    double pitch = mm(5.0);
    double dot = mm(0.25);
    double ink = 0.25;
};

// Type sizes and weights for the furniture. Points throughout.
struct Style {
    double kicker_size = 11.0;
    double kicker_tracking = 1.6;
    double kicker_ink = 1.0;
    double rule_width = 0.4;
    double rule_ink = 1.0;
    double title_size = 24.0;
    double title_leading = 1.18;
    int title_lines = 2;
    double footer_size = 8.5;
    double footer_ink = 0.6;
    double toc_size = 10.0;
    double toc_leading = 1.8;
    double toc_ink = 0.85;
    double toc_indent = 14.0;
    double tick_length = mm(3.0);
    double tick_width = 0.3;
    double tick_ink = 0.4;
    double reg_size = mm(2.0);
    double reg_width = 0.3;
    double reg_ink = 0.9;
};

// What the portrait footer can say. Either field may be empty.
struct BookInfo {
    std::string title;
    std::string author;
};

// One run of text on a baseline, already positioned.
struct TextRun {
    std::string text;
    double x;
    double y;
    double size;
    double ink = 1.0;
    double tracking = 0.0;
    bool italic = false;
};

// A horizontal hairline.
struct Rule {
    double x0;
    double y;
    double x1;
    double width;
    double ink;
};

// Everything that goes on one side, as data.
struct SideLayout {
    Side side;
    Rect box;
    std::vector<TextRun> texts;
    std::vector<Rule> rules;
    bool grid = false;
    bool ticks = false;
    std::optional<Corner> registration;
    std::optional<Placement> content;
};

class Renderer {
public:
    Renderer(Layout layout, GridSpec grid, Style style, BookInfo book,
             const GlyphSource* roman, const GlyphSource* italic, NotesMode notes);

    const Layout& layout() const { return layout_; }
    const GridSpec& grid() const { return grid_; }

    // The drawable box for `side`, with the gutter on its binding edge.
    Rect box_for(const Side& side) const;

    // Layout one side as data. `chapter` is required for a portrait or
    // mini-TOC; `page_box` is the source page's crop box for a content side;
    // `facing_page` names the content page a notes side faces.
    SideLayout layout_side(const Side& side, const Chapter* chapter = nullptr,
                           std::optional<Rect> page_box = std::nullopt,
                           std::optional<int> facing_page = std::nullopt) const;

    // `sl` as PDF content-stream operators. Mechanical: every decision was
    // already made in layout_side().
    std::string emit(const SideLayout& sl) const;

    // Draw an imported source page at `placement`. The XObject NAME belongs to
    // the backend — core never learns what a PDF object is — but the operators
    // are text, so they are generated here.
    std::string place_form(const std::string& name, const Placement& placement) const;

private:
    Corner outer_corner(const Side& side) const;
    SideLayout portrait(const Side& side, const Rect& box, const Chapter* chapter) const;
    SideLayout mini_toc(const Side& side, const Rect& box, const Chapter* chapter) const;
    SideLayout notes(const Side& side, const Rect& box, const Chapter* chapter,
                     std::optional<int> facing_page) const;
    SideLayout content(const Side& side, const Rect& box,
                       std::optional<Rect> page_box) const;
    TextRun centred(const std::string& text, const Rect& box, double y, double size,
                    double ink, bool italic) const;
    std::string rule_stream(const Rule& rule) const;

    Layout layout_;
    GridSpec grid_;
    Style style_;
    BookInfo book_;
    const GlyphSource* roman_;
    const GlyphSource* italic_;
    NotesMode notes_;
};

}  // namespace pb
