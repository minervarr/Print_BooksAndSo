// metrics.hh — the seam between core/ and a real font file.
//
// Copyright (C) 2026 nava. AGPLv3 or later; see LICENSE.
//
// core/ lays out Computer Modern without importing a font library: it talks to
// a GlyphSource, and backend/ supplies one (FT_Outline_Decompose in the port).
// The whole interface is "give me the outline of this character".
//
// Coordinates are in FONT UNITS. Scaling to a point size is text.hh's job,
// because the same outline is drawn at several different sizes on one portrait.
#pragma once

#include <cstdint>
#include <vector>

namespace pb {

// One PDF path segment in font units. The operator is a PDF operator name and
// the operands are its arguments:
//   'm' (x, y)                        moveto
//   'l' (x, y)                        lineto
//   'c' (x1, y1, x2, y2, x3, y3)      cubic bezier
//   'h' ()                            closepath
// Cubic only: Latin Modern is CFF-flavoured OpenType, so its outlines are
// already cubic and map straight onto PDF's `c`.
struct PathCommand {
    char op;
    std::vector<double> operands;
};

// One glyph: how far the pen moves, and the path to fill. `commands` may be
// empty — a space is a real glyph with a real advance and nothing to draw.
struct GlyphOutline {
    double advance = 0.0;
    std::vector<PathCommand> commands;
};

// A font, reduced to the one question core/ asks it. The interface takes a
// code point so a UTF-8 title can carry a curly quote or an accented letter.
struct GlyphSource {
    virtual ~GlyphSource() = default;

    virtual int units_per_em() const = 0;

    // The glyph for `codepoint`, in font units. Throws std::out_of_range if the
    // font has no glyph for it; text.cc collects those and reports them
    // together rather than failing from inside a page.
    virtual GlyphOutline outline(char32_t codepoint) const = 0;
};

}  // namespace pb
