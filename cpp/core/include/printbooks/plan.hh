// plan.hh — the page-slot model: a book and a notes mode become an ordered list
// of sides.
//
// Copyright (C) 2026 nava. AGPLv3 or later; see LICENSE.
//
// The unit here is a SIDE of a sheet, not a page, because everything that can
// go wrong in this program is a parity error. A portrait on a left-hand page,
// notes on the wrong side of the spread, a content page with nowhere to write
// beside it — each looks plausible on screen and is wrong in the hand.
#pragma once

#include <optional>
#include <string>
#include <vector>

#include "printbooks/geometry.hh"

namespace pb {

// What occupies one side of one sheet.
enum class SideKind { Portrait, MiniToc, Content, Notes, Blank };

// What a notes page carries — or whether there are notes pages at all. None is
// the "just print the chapter" mode: no facing pages, content on both sides.
enum class NotesMode { Dots, Lines, Blank, None };

// One line of a chapter's mini-TOC.
struct TocEntry {
    std::string title;
    int page;
    int depth = 0;
};

// A run of source pages, 1-based and inclusive at both ends — 1-based because
// that is what a reader types into the project TOML.
struct Chapter {
    int number = 0;
    std::string title;
    int first_page = 0;
    int last_page = 0;
    std::vector<TocEntry> toc;

    int page_count() const { return last_page - first_page + 1; }
};

// One side of one sheet, at a 1-based physical position.
struct Side {
    int index;
    SideKind kind;
    int chapter;
    std::optional<int> source_page;

    // Odd sides are rectos — the right-hand page of an opened spread.
    bool is_recto() const { return index % 2 == 1; }

    // Which edge the binding is on. A recto's binding edge is its left; a
    // verso's is its right. Backwards, the gutter sits in the outer margin,
    // which looks fine and lets the binding eat the text.
    GutterEdge gutter_edge() const {
        return is_recto() ? GutterEdge::Left : GutterEdge::Right;
    }
};

// Lay the chapters out as an ordered list of sides. Every chapter occupies an
// even number of sides, which is what keeps the next chapter's portrait on a
// recto without the caller tracking parity. Throws on empty input, a page range
// below 1, an inverted range, or two chapters claiming the same page.
std::vector<Side> plan_sides(const std::vector<Chapter>& chapters, NotesMode notes);

}  // namespace pb
