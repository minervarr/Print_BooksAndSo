// pdf_qpdf.hh — probe a source PDF into plain data (qpdf).
//
// Copyright (C) 2026 nava. AGPLv3 or later; see LICENSE.
//
// Two jobs, probe and emit, and between them core/ does all the deciding.
// This header is the probe half: page boxes, the outline tree, metadata.
// Nothing PDF-shaped crosses back into core/.
#pragma once

#include <string>
#include <vector>

#include "printbooks/geometry.hh"
#include "printbooks/plan.hh"

namespace pb {

// One page of the source book, 1-based.
struct SourcePage {
    int number;
    Rect media_box;
    Rect crop_box;
    int rotate;
};

// One entry of the source outline, flattened with its depth.
struct OutlineItem {
    std::string title;
    int page;
    int depth;
};

// A source PDF as plain data. No qpdf objects survive in here.
struct SourceBook {
    std::string path;
    std::vector<SourcePage> pages;
    std::vector<OutlineItem> outline;
    std::string title;
    std::string author;

    int page_count() const { return static_cast<int>(pages.size()); }
};

// Read `path` into plain data for core/ to plan against.
SourceBook probe(const std::string& path);

// Top-level outline entries as chapters, with their sub-entries as TOC.
// A chapter runs from its own first page to the page before the next
// chapter's — the outline states where things START, never where they end.
std::vector<Chapter> chapters_from_outline(const SourceBook& book, int min_gap = 1);

}  // namespace pb
