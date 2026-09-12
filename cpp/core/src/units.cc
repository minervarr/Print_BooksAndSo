// units.cc — millimetres in, PDF points out.
//
// Copyright (C) 2026 nava. AGPLv3 or later; see LICENSE.

#include "printbooks/units.hh"

namespace pb {

double mm(double value) {
    return value * 72.0 / 25.4;
}

double pt_to_mm(double value) {
    return value * 25.4 / 72.0;
}

double inch(double value) {
    return value * 72.0;
}

bool paper_size(std::string_view name, PaperSize* out) {
    if (name == "a4") {
        *out = {210.0, 297.0};
        return true;
    }
    if (name == "letter") {
        // 8.5 x 11 in, stored in millimetres like every other paper.
        *out = {215.9, 279.4};
        return true;
    }
    return false;
}

}  // namespace pb
