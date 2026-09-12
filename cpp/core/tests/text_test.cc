// text_test.cc — text as glyph outlines.
//
// Copyright (C) 2026 nava. AGPLv3 or later; see LICENSE.
#undef NDEBUG
#include <algorithm>
#include <cassert>
#include <cstdio>
#include <string>
#include <vector>

#include "printbooks/metrics.hh"
#include "printbooks/text.hh"

#include "test_util.hh"

using namespace pb;
using pb_test::approx;
using pb_test::ml_points;
using pb_test::ops;

// A legitimate test double: the font is an external dependency with a real
// implementation in backend/, so core/ tests supply a hand-built one. Its
// glyphs are deliberately trivial so the arithmetic is checkable by hand.
struct StubFont : GlyphSource {
    int units_per_em() const override { return 1000; }

    GlyphOutline outline(char32_t cp) const override {
        if (cp == 'A')
            return GlyphOutline{500.0,
                                {PathCommand{'m', {0.0, 0.0}},
                                 PathCommand{'l', {1000.0, 0.0}},
                                 PathCommand{'l', {1000.0, 1000.0}},
                                 PathCommand{'l', {0.0, 1000.0}},
                                 PathCommand{'h', {}}}};
        if (cp == 'B')
            return GlyphOutline{250.0,
                                {PathCommand{'m', {0.0, 0.0}},
                                 PathCommand{'c', {100.0, 200.0, 300.0, 400.0, 500.0, 600.0}},
                                 PathCommand{'h', {}}}};
        if (cp == ' ')
            return GlyphOutline{300.0, {}};
        throw std::out_of_range("missing glyph");
    }
};

static StubFont font() { return StubFont{}; }

static std::vector<double> xs_of(const std::vector<std::pair<double, double>>& pts) {
    std::vector<double> xs;
    for (const auto& p : pts)
        xs.push_back(p.first);
    return xs;
}

// --- measuring --------------------------------------------------------------

static void test_width_of_one_glyph_scales_from_font_units_to_points() {
    assert(approx(text_width(font(), "A", 10.0), 5.0));
}

static void test_width_accumulates_advances() {
    assert(approx(text_width(font(), "AB ", 10.0), 10.5));
}

static void test_width_of_the_empty_string_is_zero() {
    assert(text_width(font(), "", 10.0) == 0.0);
}

static void test_tracking_is_added_between_glyphs_not_after_the_last() {
    const double plain = text_width(font(), "AAA", 10.0);
    const double tracked = text_width(font(), "AAA", 10.0, 2.0);
    assert(approx(tracked - plain, 4.0));
}

static void test_tracking_does_not_apply_to_a_single_glyph() {
    assert(approx(text_width(font(), "A", 10.0, 2.0), text_width(font(), "A", 10.0)));
}

// --- drawing ----------------------------------------------------------------

static void test_glyphs_are_filled_not_stroked() {
    const std::string stream = draw_text(font(), "A", 0.0, 0.0, 10.0, 1.0);
    assert(ops(stream, "f") == 1);
    assert(ops(stream, "S") == 0);
}

static void test_drawing_saves_and_restores_graphics_state() {
    const std::string stream = draw_text(font(), "A", 0.0, 0.0, 10.0, 1.0);
    assert(ops(stream, "q") == 1);
    assert(ops(stream, "Q") == 1);
}

static void test_ink_becomes_a_fill_gray_not_a_stroke_gray() {
    const std::string stream = draw_text(font(), "A", 0.0, 0.0, 10.0, 0.6);
    assert(stream.find("0.4 g") != std::string::npos);
    assert(stream.find("0.4 G") == std::string::npos);
}

static void test_an_outline_is_scaled_from_font_units_to_the_point_size() {
    const std::string stream = draw_text(font(), "A", 0.0, 0.0, 10.0, 1.0);
    const auto pts = ml_points(stream);
    double minx = pts.front().first, maxx = pts.front().first;
    double miny = pts.front().second, maxy = pts.front().second;
    for (const auto& p : pts) {
        minx = std::min(minx, p.first);
        maxx = std::max(maxx, p.first);
        miny = std::min(miny, p.second);
        maxy = std::max(maxy, p.second);
    }
    assert(approx(minx, 0.0) && approx(maxx, 10.0));
    assert(approx(miny, 0.0) && approx(maxy, 10.0));
}

static void test_an_outline_is_translated_to_the_pen_position() {
    const std::string stream = draw_text(font(), "A", 100.0, 200.0, 10.0, 1.0);
    const auto pts = ml_points(stream);
    double minx = pts.front().first, maxx = pts.front().first;
    double miny = pts.front().second, maxy = pts.front().second;
    for (const auto& p : pts) {
        minx = std::min(minx, p.first);
        maxx = std::max(maxx, p.first);
        miny = std::min(miny, p.second);
        maxy = std::max(maxy, p.second);
    }
    assert(approx(minx, 100.0) && approx(maxx, 110.0));
    assert(approx(miny, 200.0) && approx(maxy, 210.0));
}

static void test_the_pen_advances_between_glyphs() {
    const std::string stream = draw_text(font(), "AA", 0.0, 0.0, 10.0, 1.0);
    auto xs = xs_of(ml_points(stream));
    std::sort(xs.begin(), xs.end());
    xs.erase(std::unique(xs.begin(), xs.end()), xs.end());
    const double expect[] = {0.0, 5.0, 10.0, 15.0};
    assert(xs.size() == 4);
    for (std::size_t i = 0; i < xs.size(); ++i)
        assert(approx(xs[i], expect[i]));
}

static void test_tracking_moves_the_pen_too() {
    const std::string stream = draw_text(font(), "AA", 0.0, 0.0, 10.0, 1.0, 2.0);
    auto xs = xs_of(ml_points(stream));
    std::sort(xs.begin(), xs.end());
    xs.erase(std::unique(xs.begin(), xs.end()), xs.end());
    const double expect[] = {0.0, 7.0, 10.0, 17.0};
    assert(xs.size() == 4);
    for (std::size_t i = 0; i < xs.size(); ++i)
        assert(approx(xs[i], expect[i]));
}

static void test_cubic_curves_survive_as_curve_operators() {
    const std::string stream = draw_text(font(), "B", 0.0, 0.0, 10.0, 1.0);
    assert(ops(stream, "c") == 1);
    assert(stream.find("1 2 3 4 5 6 c") != std::string::npos);
}

static void test_a_glyph_with_no_outline_still_advances() {
    const std::string stream = draw_text(font(), "A A", 0.0, 0.0, 10.0, 1.0);
    const auto pts = ml_points(stream);
    double maxx = pts.front().first;
    for (const auto& p : pts)
        maxx = std::max(maxx, p.first);
    assert(approx(maxx, 18.0));
}

static void test_the_empty_string_draws_nothing_at_all() {
    assert(draw_text(font(), "", 0.0, 0.0, 10.0, 1.0).empty());
}

static void test_missing_glyphs_are_reported_together_and_name_themselves() {
    bool threw = false;
    std::string msg;
    try {
        draw_text(font(), "AZQ", 0.0, 0.0, 10.0, 1.0);
    } catch (const std::invalid_argument& e) {
        threw = true;
        msg = e.what();
    }
    assert(threw);
    assert(msg.find("missing") != std::string::npos);
    assert(msg.find("Z") != std::string::npos);
    assert(msg.find("Q") != std::string::npos);
}

static void test_a_nonpositive_size_is_rejected() {
    bool threw = false;
    try {
        draw_text(font(), "A", 0.0, 0.0, 0.0, 1.0);
    } catch (const std::invalid_argument&) {
        threw = true;
    }
    assert(threw);
}

int main() {
    test_width_of_one_glyph_scales_from_font_units_to_points();
    test_width_accumulates_advances();
    test_width_of_the_empty_string_is_zero();
    test_tracking_is_added_between_glyphs_not_after_the_last();
    test_tracking_does_not_apply_to_a_single_glyph();
    test_glyphs_are_filled_not_stroked();
    test_drawing_saves_and_restores_graphics_state();
    test_ink_becomes_a_fill_gray_not_a_stroke_gray();
    test_an_outline_is_scaled_from_font_units_to_the_point_size();
    test_an_outline_is_translated_to_the_pen_position();
    test_the_pen_advances_between_glyphs();
    test_tracking_moves_the_pen_too();
    test_cubic_curves_survive_as_curve_operators();
    test_a_glyph_with_no_outline_still_advances();
    test_the_empty_string_draws_nothing_at_all();
    test_missing_glyphs_are_reported_together_and_name_themselves();
    test_a_nonpositive_size_is_rejected();
    std::printf("text_test: all assertions passed\n");
    return 0;
}
