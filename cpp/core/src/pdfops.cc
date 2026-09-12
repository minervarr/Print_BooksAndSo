// pdfops.cc — formatting primitives shared by every content-stream emitter.
//
// Copyright (C) 2026 nava. AGPLv3 or later; see LICENSE.

#include "printbooks/pdfops.hh"

#include <cstdio>
#include <stdexcept>

namespace pb {

std::string num(double value) {
    char buf[64];
    std::snprintf(buf, sizeof buf, "%.4f", value);
    std::string s(buf);

    // Four decimals is ~0.4 micron — far finer than any printer resolves.
    // Short numbers matter because the dot grid is the largest stream written.
    while (!s.empty() && s.back() == '0')
        s.pop_back();
    if (!s.empty() && s.back() == '.')
        s.pop_back();
    if (s.empty() || s == "-" || s == "-0")
        return "0";
    return s;
}

std::string gray(double ink) {
    if (!(ink >= 0.0 && ink <= 1.0))
        throw std::invalid_argument("ink must be a fraction of black in 0..1");
    return num(1.0 - ink);
}

}  // namespace pb
