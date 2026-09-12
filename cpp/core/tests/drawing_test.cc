// drawing_test.cc — content-stream emitters.
//
// Copyright (C) 2026 nava. AGPLv3 or later; see LICENSE.
#undef NDEBUG
#include <algorithm>
#include <cassert>
#include <cstdio>
#include <string>
#include <vector>

#include "printbooks/drawing.hh"
#include "printbooks/geometry.hh"
#include "printbooks/units.hh"

#include "test_util.hh"

using namespace pb;
using pb_test::approx;
using pb_test::ml_points;
using pb_test::ops;

static double max_x(const std::vector<std::pair<double, double>>& pts) {
    double m = pts.front().first;
    for (const auto& p : pts)
        m = std::max(m, p.first);
    return m;
}
static double max_y(const std::vector<std::pair<double, double>>& pts) {
    double m = pts.front().second;
    for (const auto& p : pts)
        m = std::max(m, p.second);
    return m;
}
static double min_x(const std::vector<std::pair<double, double>>& pts) {
    double m = pts.front().first;
    for (const auto& p : pts)
        m = std::min(m, p.first);
    return m;
}

static bool expect_throw(void (*f)()) {
    try {
        f();
    } catch (const std::invalid_argument&) {
        return true;
    }
    return false;
}

// --- the dot grid -----------------------------------------------------------

static void test_dot_grid_is_one_path_with_one_stroke() {
    const std::string stream = dot_grid(Rect(0.0, 0.0, 100.0, 100.0), 10.0, 0.7, 0.25);
    assert(ops(stream, "S") == 1);
    assert(ops(stream, "f") == 0);
}

static void test_dot_grid_emits_one_degenerate_subpath_per_dot() {
    const std::string stream = dot_grid(Rect(0.0, 0.0, 100.0, 100.0), 10.0, 0.7, 0.25);
    assert(ops(stream, "m") == 11 * 11);
    assert(ops(stream, "l") == 11 * 11);
}

static void test_dot_grid_sets_a_round_cap() {
    const std::string stream = dot_grid(Rect(0.0, 0.0, 50.0, 50.0), 10.0, 0.7, 0.25);
    assert(stream.find("1 J") != std::string::npos);
}

static void test_dot_grid_line_width_is_the_dot_diameter() {
    const std::string stream = dot_grid(Rect(0.0, 0.0, 50.0, 50.0), 10.0, 0.7087, 0.25);
    assert(stream.find("0.7087 w") != std::string::npos);
}

static void test_dot_grid_ink_fraction_becomes_a_stroke_gray() {
    const std::string stream = dot_grid(Rect(0.0, 0.0, 50.0, 50.0), 10.0, 0.7, 0.25);
    assert(stream.find("0.75 G") != std::string::npos);
    assert(stream.find("0.75 g") == std::string::npos);
}

static void test_dot_grid_saves_and_restores_graphics_state() {
    const std::string stream = dot_grid(Rect(0.0, 0.0, 50.0, 50.0), 10.0, 0.7, 0.25);
    assert(ops(stream, "q") == 1);
    assert(ops(stream, "Q") == 1);
    assert(stream.find("q") < stream.find("Q"));
}

static void test_dot_grid_is_centred_in_its_box() {
    const std::string stream = dot_grid(Rect(0.0, 0.0, 105.0, 105.0), 10.0, 0.7, 0.25);
    const auto pts = ml_points(stream);
    assert(approx(min_x(pts), 2.5));
    assert(approx(max_x(pts), 102.5));
}

static void test_every_dot_is_inside_its_box() {
    const Rect box(20.0, 30.0, 220.0, 330.0);
    const std::string stream = dot_grid(box, 7.0, 0.7, 0.25);
    const auto pts = ml_points(stream);
    assert(!pts.empty());
    for (const auto& p : pts) {
        assert(box.x0 <= p.first && p.first <= box.x1);
        assert(box.y0 <= p.second && p.second <= box.y1);
    }
}

static void test_dot_grid_at_the_real_default_spacing() {
    const Rect box(mm(25.0), mm(15.0), mm(195.0), mm(282.0));
    const std::string stream = dot_grid(box, mm(5.0), mm(0.25), 0.25);
    assert(ops(stream, "m") == 35 * 54);
    assert(ops(stream, "S") == 1);
}

static void test_dot_grid_rejects_a_nonpositive_pitch() {
    assert(expect_throw([] { dot_grid(Rect(0.0, 0.0, 50.0, 50.0), 0.0, 0.7, 0.25); }));
}

static void test_dot_grid_rejects_a_nonpositive_dot() {
    assert(expect_throw([] { dot_grid(Rect(0.0, 0.0, 50.0, 50.0), 10.0, 0.0, 0.25); }));
}

static void test_dot_grid_rejects_an_ink_fraction_outside_zero_to_one() {
    assert(expect_throw([] { dot_grid(Rect(0.0, 0.0, 50.0, 50.0), 10.0, 0.7, 1.5); }));
}

static void test_dot_grid_rejects_a_pitch_larger_than_the_box() {
    assert(expect_throw([] { dot_grid(Rect(0.0, 0.0, 5.0, 5.0), 10.0, 0.7, 0.25); }));
}

// --- centre ticks -----------------------------------------------------------

static void test_centre_ticks_are_four_ticks_in_one_path() {
    const std::string stream = center_ticks(Rect(0.0, 0.0, 200.0, 400.0), 10.0, 0.3, 0.4);
    assert(ops(stream, "m") == 4);
    assert(ops(stream, "l") == 4);
    assert(ops(stream, "S") == 1);
}

static void test_centre_ticks_sit_at_the_edge_midpoints_and_point_inward() {
    const std::string stream = center_ticks(Rect(0.0, 0.0, 200.0, 400.0), 10.0, 0.3, 0.4);
    assert(stream.find("100 0 m 100 10 l") != std::string::npos);      // bottom, up
    assert(stream.find("100 400 m 100 390 l") != std::string::npos);   // top, down
    assert(stream.find("0 200 m 10 200 l") != std::string::npos);      // left, right
    assert(stream.find("200 200 m 190 200 l") != std::string::npos);   // right, left
}

static void test_centre_ticks_never_cross_the_middle_of_the_page() {
    const std::string stream = center_ticks(Rect(0.0, 0.0, 200.0, 400.0), 10.0, 0.3, 0.4);
    for (const auto& p : ml_points(stream)) {
        const bool near_edge = p.first <= 10.0 || p.first >= 190.0 ||
                               p.second <= 10.0 || p.second >= 390.0;
        assert(near_edge);
    }
}

static void test_centre_ticks_reject_a_length_that_would_meet_in_the_middle() {
    assert(expect_throw(
        [] { center_ticks(Rect(0.0, 0.0, 20.0, 20.0), 15.0, 0.3, 0.4); }));
}

// --- registration -----------------------------------------------------------

static void test_registration_tick_is_one_short_stroked_corner() {
    const std::string stream =
        registration_tick(Rect(0.0, 0.0, 200.0, 400.0), Corner::BottomLeft, 6.0, 0.3, 1.0);
    assert(ops(stream, "S") == 1);
    assert(ops(stream, "m") == 2);  // an L: one horizontal, one vertical arm
}

static void test_registration_tick_is_placed_at_the_named_corner() {
    const std::string stream =
        registration_tick(Rect(10.0, 20.0, 210.0, 420.0), Corner::TopRight, 6.0, 0.3, 1.0);
    const auto pts = ml_points(stream);
    assert(approx(max_x(pts), 210.0));
    assert(approx(max_y(pts), 420.0));
}

int main() {
    test_dot_grid_is_one_path_with_one_stroke();
    test_dot_grid_emits_one_degenerate_subpath_per_dot();
    test_dot_grid_sets_a_round_cap();
    test_dot_grid_line_width_is_the_dot_diameter();
    test_dot_grid_ink_fraction_becomes_a_stroke_gray();
    test_dot_grid_saves_and_restores_graphics_state();
    test_dot_grid_is_centred_in_its_box();
    test_every_dot_is_inside_its_box();
    test_dot_grid_at_the_real_default_spacing();
    test_dot_grid_rejects_a_nonpositive_pitch();
    test_dot_grid_rejects_a_nonpositive_dot();
    test_dot_grid_rejects_an_ink_fraction_outside_zero_to_one();
    test_dot_grid_rejects_a_pitch_larger_than_the_box();
    test_centre_ticks_are_four_ticks_in_one_path();
    test_centre_ticks_sit_at_the_edge_midpoints_and_point_inward();
    test_centre_ticks_never_cross_the_middle_of_the_page();
    test_centre_ticks_reject_a_length_that_would_meet_in_the_middle();
    test_registration_tick_is_one_short_stroked_corner();
    test_registration_tick_is_placed_at_the_named_corner();
    std::printf("drawing_test: all assertions passed\n");
    return 0;
}
