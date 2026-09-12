// pdfops.hh — formatting primitives shared by every content-stream emitter.
//
// Copyright (C) 2026 nava. AGPLv3 or later; see LICENSE.
//
// Small on purpose. These two conversions were duplicated in the drawing and
// text emitters, which is exactly the kind of duplication that drifts: one of
// the two starts rounding to five decimals, or stops inverting ink, and the
// difference only shows up as a faint smudge on paper.
#pragma once

#include <string>

namespace pb {

// A PDF number: four decimals, no trailing zeros, no trailing point.
std::string num(double value);

// A fraction of black (0.25 = "25 % K") as a PDF gray level. PDF gray runs the
// other way — 0 is black, 1 is white — so the inversion happens here, once.
std::string gray(double ink);

}  // namespace pb
