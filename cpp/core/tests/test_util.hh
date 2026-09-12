// test_util.hh — shared helpers for the assert-based core tests.
//
// Copyright (C) 2026 nava. AGPLv3 or later; see LICENSE.
//
// These mirror what the Python side gets for free from pytest: `pytest.approx`
// and regex-based operator counting over content streams. Test-only, so it is
// not part of the core library.
#pragma once

#include <cmath>
#include <cstddef>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

namespace pb_test {

// pytest.approx with a relative and an absolute floor, so a value near zero
// and a value near a thousand are both compared sanely.
inline bool approx(double a, double b, double rel = 1e-9, double abs = 1e-9) {
    const double tol = std::max(abs, rel * std::max(std::fabs(a), std::fabs(b)));
    return std::fabs(a - b) <= tol;
}

// How many times `op` appears as its own whitespace-delimited token.
inline int ops(const std::string& stream, const std::string& op) {
    int n = 0;
    std::istringstream in(stream);
    std::string tok;
    while (in >> tok)
        if (tok == op)
            ++n;
    return n;
}

// Every (x, y) that immediately precedes a moveto or lineto, i.e. the geometry
// of a path. Mirrors the Python regex `(-?[\d.]+) (-?[\d.]+) [ml]`.
inline std::vector<std::pair<double, double>> ml_points(const std::string& stream) {
    std::vector<std::string> tok;
    std::istringstream in(stream);
    std::string t;
    while (in >> t)
        tok.push_back(t);

    std::vector<std::pair<double, double>> pts;
    for (std::size_t i = 0; i + 2 < tok.size(); ++i) {
        if (tok[i + 2] == "m" || tok[i + 2] == "l")
            pts.emplace_back(std::stod(tok[i]), std::stod(tok[i + 1]));
    }
    return pts;
}

}  // namespace pb_test
