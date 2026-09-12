// units_test.cc — millimetres, points, and paper.
//
// Copyright (C) 2026 nava. AGPLv3 or later; see LICENSE.
//
// Plain assert(), no framework. NDEBUG is undefined first so the asserts
// survive a Release build.
#undef NDEBUG
#include <cassert>
#include <cstdio>

#include "printbooks/units.hh"

#include "test_util.hh"

using namespace pb;
using pb_test::approx;

static void test_one_inch_is_seventy_two_points_exactly() {
    // Multiply-then-divide, so this is exact rather than 72.00000000000001.
    assert(mm(25.4) == 72.0);
}

static void test_five_millimetre_dot_pitch() {
    assert(approx(mm(5.0), 14.173228346456693));
}

static void test_millimetres_round_trip_through_points() {
    const double values[] = {0.0, 0.25, 5.0, 210.0, 297.0};
    for (double v : values)
        assert(approx(pt_to_mm(mm(v)), v));
}

static void test_a4_is_210_by_297_millimetres() {
    PaperSize a4;
    assert(paper_size("a4", &a4));
    assert(a4.width_mm == 210.0 && a4.height_mm == 297.0);
}

static void test_a4_in_points() {
    PaperSize a4;
    assert(paper_size("a4", &a4));
    assert(approx(mm(a4.width_mm), 595.2755905511812));
    assert(approx(mm(a4.height_mm), 841.8897637795277));
}

static void test_letter_is_us_letter_in_millimetres() {
    PaperSize letter;
    assert(paper_size("letter", &letter));
    assert(approx(mm(letter.width_mm), 612.0, 1e-9, 1e-9));
    assert(approx(mm(letter.height_mm), 792.0, 1e-9, 1e-9));
}

static void test_unknown_paper_is_reported_not_defaulted() {
    PaperSize out;
    assert(!paper_size("a3", &out));
}

int main() {
    test_one_inch_is_seventy_two_points_exactly();
    test_five_millimetre_dot_pitch();
    test_millimetres_round_trip_through_points();
    test_a4_is_210_by_297_millimetres();
    test_a4_in_points();
    test_letter_is_us_letter_in_millimetres();
    test_unknown_paper_is_reported_not_defaulted();
    std::printf("units_test: all assertions passed\n");
    return 0;
}
