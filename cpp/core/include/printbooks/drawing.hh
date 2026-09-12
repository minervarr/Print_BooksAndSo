// drawing.hh — content-stream emitters: the furniture drawn on a sheet.
//
// Copyright (C) 2026 nava. AGPLv3 or later; see LICENSE.
//
// A PDF content stream is a string of postfix operators, so these functions
// return strings, take no PDF library, and their tests read the operators back.
#pragma once

#include <string>

#include "printbooks/geometry.hh"

namespace pb {

enum class Corner { BottomLeft, BottomRight, TopLeft, TopRight };

// A dot grid filling `box`, centred, as ONE stroked path: every dot is a
// degenerate subpath and the round line cap turns it into a dot.
std::string dot_grid(const Rect& box, double pitch, double dot, double ink);

// Four inward ticks at the edge midpoints of `box`.
std::string center_ticks(const Rect& box, double length, double width, double ink);

// A small L at one corner of `box`, drawn on both sides of a sheet — the
// manual-duplex check.
std::string registration_tick(const Rect& box, Corner corner, double size, double width,
                              double ink);

}  // namespace pb
