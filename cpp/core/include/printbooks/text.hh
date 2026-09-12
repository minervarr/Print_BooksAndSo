// text.hh — laying out a line of text as filled outlines.
//
// Copyright (C) 2026 nava. AGPLv3 or later; see LICENSE.
//
// No font dictionary reaches the output: each glyph becomes PDF path operators
// and the line is one filled path. The trade is that this text is not
// selectable or searchable — deliberate, for a print-targeted artifact.
#pragma once

#include <string>
#include <vector>

#include "printbooks/metrics.hh"

namespace pb {

// Width of `text` in points. Tracking is added BETWEEN glyphs, never after the
// last one — a trailing gap would shift every centred line left by half the
// tracking.
double text_width(const GlyphSource& source, const std::string& text, double size,
                  double tracking = 0.0);

// `text` at (x, y) as one filled path, baseline-left origin. Filled with `f`
// (nonzero winding), which is what CFF outlines expect. Throws std::invalid_argument
// if the font is missing a glyph, naming every missing character at once.
std::string draw_text(const GlyphSource& source, const std::string& text, double x, double y,
                      double size, double ink, double tracking = 0.0);

// Greedy word wrap, measured against real glyph advances. A single word wider
// than the line is not dropped or hyphenated; running past max_lines truncates
// with an ellipsis rather than silently dropping the tail.
std::vector<std::string> wrap_text(const GlyphSource& source, const std::string& text,
                                   double size, double max_width, int max_lines,
                                   double tracking = 0.0);

}  // namespace pb
