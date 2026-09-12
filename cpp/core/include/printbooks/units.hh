// units.hh — millimetres in, PDF points out.
//
// Copyright (C) 2026 nava. AGPLv3 or later; see LICENSE.
//
// A PDF user-space unit is 1/72 inch. Every measurement a human states about
// paper — sheet size, dot pitch, gutter, margin — is a millimetre. This module
// is the only place that conversion happens.
#pragma once

#include <string_view>

namespace pb {

// PDF user-space units per millimetre. Exposed for documentation; prefer mm().
inline constexpr double kMmToPt = 72.0 / 25.4;

// The conversion multiplies before it divides (v * 72.0 / 25.4, never
// v * (72.0 / 25.4)) so that whole inches land exactly: 25.4 mm comes back as
// 72.0 and not 72.00000000000001.
double mm(double value);

double pt_to_mm(double value);

// Inches to PDF points, because paper hardware is still imperial.
double inch(double value);

// A sheet size in millimetres, keyed by the name the CLI accepts (--paper a4).
// Lowercase only: there is no aliasing layer, so a capitalised duplicate would
// be a second code path that behaves the same until it does not.
struct PaperSize {
    double width_mm;
    double height_mm;
};

// Looks up `name` ("a4", "letter"). Returns false for an unknown name; the
// caller turns that into an error rather than silently defaulting.
bool paper_size(std::string_view name, PaperSize* out);

}  // namespace pb
