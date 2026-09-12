// geometry_test.cc — sheet geometry: the content box, and fitting a page into it.
//
// Copyright (C) 2026 nava. AGPLv3 or later; see LICENSE.
#undef NDEBUG
#include <cassert>
#include <cstdio>

#include "printbooks/geometry.hh"
#include "printbooks/units.hh"

#include "test_util.hh"

using namespace pb;
using pb_test::approx;

static void test_paper_a4_in_points() {
    const Size a4 = paper("a4");
    assert(approx(a4.width, 595.2755905511812));
    assert(approx(a4.height, 841.8897637795277));
}

static void test_paper_rejects_an_unknown_name() {
    bool threw = false;
    try {
        paper("a3");
    } catch (const std::invalid_argument&) {
        threw = true;
    }
    assert(threw);
}

static void test_rect_width_and_height() {
    const Rect r(10.0, 20.0, 110.0, 220.0);
    assert(r.width() == 100.0);
    assert(r.height() == 200.0);
}

static void test_rect_rejects_an_inverted_box() {
    bool threw = false;
    try {
        Rect(110.0, 20.0, 10.0, 220.0);
    } catch (const std::invalid_argument&) {
        threw = true;
    }
    assert(threw);
}

static void test_content_area_insets_the_margin_on_all_four_sides() {
    const Rect box = content_area(Size(1000.0, 2000.0), 100.0, 0.0, GutterEdge::Left);
    assert(box.x0 == 100.0 && box.y0 == 100.0 && box.x1 == 900.0 && box.y1 == 1900.0);
}

static void test_content_area_adds_the_gutter_to_the_left_edge_only() {
    const Rect box = content_area(Size(1000.0, 2000.0), 100.0, 50.0, GutterEdge::Left);
    assert(box.x0 == 150.0 && box.y0 == 100.0 && box.x1 == 900.0 && box.y1 == 1900.0);
}

static void test_content_area_adds_the_gutter_to_the_right_edge_only() {
    const Rect box = content_area(Size(1000.0, 2000.0), 100.0, 50.0, GutterEdge::Right);
    assert(box.x0 == 100.0 && box.y0 == 100.0 && box.x1 == 850.0 && box.y1 == 1900.0);
}

static void test_content_area_rejects_a_margin_that_eats_the_sheet() {
    bool threw = false;
    try {
        content_area(Size(200.0, 200.0), 100.0, 0.0, GutterEdge::Left);
    } catch (const std::invalid_argument&) {
        threw = true;
    }
    assert(threw);
}

static void test_fit_scales_up_and_centres_on_the_constrained_axis() {
    const Placement p = fit(Rect(0.0, 0.0, 100.0, 100.0), Rect(0.0, 0.0, 200.0, 400.0));
    assert(p.scale == 2.0);  // width-constrained
    assert(p.dx == 0.0);
    assert(p.dy == 100.0);   // (400 - 200) / 2
}

static void test_fit_accounts_for_a_source_box_that_does_not_start_at_the_origin() {
    const Placement p = fit(Rect(50.0, 50.0, 150.0, 150.0), Rect(0.0, 0.0, 200.0, 400.0));
    assert(p.scale == 2.0);
    assert(p.dx == -100.0);
    assert(p.dy == 0.0);
}

static void test_fit_places_the_source_corners_exactly_on_the_target() {
    const Rect source(50.0, 50.0, 150.0, 150.0);
    const Rect target(0.0, 0.0, 200.0, 400.0);
    const Placement p = fit(source, target);
    assert(approx(p.apply_x(source.x0), 0.0));
    assert(approx(p.apply_x(source.x1), 200.0));
    assert(approx(p.apply_y(source.y0), 100.0));
    assert(approx(p.apply_y(source.y1), 300.0));
}

static void test_fit_is_height_constrained_when_the_source_is_tall() {
    const Placement p = fit(Rect(0.0, 0.0, 100.0, 400.0), Rect(0.0, 0.0, 200.0, 400.0));
    assert(p.scale == 1.0);
    assert(p.dx == 50.0);
    assert(p.dy == 0.0);
}

static void test_fit_never_distorts() {
    const Rect source(0.0, 0.0, 300.0, 100.0);
    const Size target = paper("a4");
    const Placement p = fit(source, Rect::from_size(target));
    const double placed_w = p.scale * source.width();
    const double placed_h = p.scale * source.height();
    assert(approx(placed_w / placed_h, 3.0));
}

static void test_fit_rejects_a_degenerate_source() {
    bool threw = false;
    try {
        fit(Rect(0.0, 0.0, 0.0, 0.0), Rect(0.0, 0.0, 200.0, 400.0));
    } catch (const std::invalid_argument&) {
        threw = true;
    }
    assert(threw);
}

static void test_a4_content_area_with_realistic_millimetres() {
    const Rect box =
        content_area(paper("a4"), mm(15.0), mm(10.0), GutterEdge::Left);
    assert(approx(box.x0, mm(25.0)));
    assert(approx(box.y0, mm(15.0)));
    assert(approx(box.x1, mm(195.0)));
    assert(approx(box.y1, mm(282.0)));
}

int main() {
    test_paper_a4_in_points();
    test_paper_rejects_an_unknown_name();
    test_rect_width_and_height();
    test_rect_rejects_an_inverted_box();
    test_content_area_insets_the_margin_on_all_four_sides();
    test_content_area_adds_the_gutter_to_the_left_edge_only();
    test_content_area_adds_the_gutter_to_the_right_edge_only();
    test_content_area_rejects_a_margin_that_eats_the_sheet();
    test_fit_scales_up_and_centres_on_the_constrained_axis();
    test_fit_accounts_for_a_source_box_that_does_not_start_at_the_origin();
    test_fit_places_the_source_corners_exactly_on_the_target();
    test_fit_is_height_constrained_when_the_source_is_tall();
    test_fit_never_distorts();
    test_fit_rejects_a_degenerate_source();
    test_a4_content_area_with_realistic_millimetres();
    std::printf("geometry_test: all assertions passed\n");
    return 0;
}
