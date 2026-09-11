"""Sheet geometry: the content box, and fitting a source page into it.

All expectations here are computed by hand. This is the arithmetic that decides
whether text lands under a spiral binding or not, and it is invisible when
wrong until forty sheets have been printed.
"""

import math

import pytest

from core import units
from core.geometry import Rect, Size, content_area, fit, paper


def test_paper_a4_in_points():
    a4 = paper("a4")
    assert math.isclose(a4.width, 595.2755905511812, rel_tol=1e-12)
    assert math.isclose(a4.height, 841.8897637795277, rel_tol=1e-12)


def test_paper_rejects_an_unknown_name_by_naming_what_it_knows():
    # A silent fallback to A4 here would print a whole book at the wrong size.
    with pytest.raises(ValueError, match="a4"):
        paper("a3")


def test_rect_width_and_height():
    r = Rect(10.0, 20.0, 110.0, 220.0)
    assert r.width == 100.0
    assert r.height == 200.0


def test_rect_rejects_an_inverted_box():
    # PDF boxes are written lower-left to upper-right. An inverted one is
    # always a bug upstream, and silently normalising it hides that bug.
    with pytest.raises(ValueError):
        Rect(110.0, 20.0, 10.0, 220.0)


def test_content_area_insets_the_margin_on_all_four_sides():
    sheet = Size(1000.0, 2000.0)
    box = content_area(sheet, margin=100.0, gutter=0.0, gutter_edge="left")
    assert (box.x0, box.y0, box.x1, box.y1) == (100.0, 100.0, 900.0, 1900.0)


def test_content_area_adds_the_gutter_to_the_left_edge_only():
    sheet = Size(1000.0, 2000.0)
    box = content_area(sheet, margin=100.0, gutter=50.0, gutter_edge="left")
    assert (box.x0, box.y0, box.x1, box.y1) == (150.0, 100.0, 900.0, 1900.0)


def test_content_area_adds_the_gutter_to_the_right_edge_only():
    # A verso's binding edge is its RIGHT edge -- flip a sheet bound on the
    # left and the holes move to the other side. Getting this backwards puts
    # the gutter in the outer margin, which looks fine and reads wrong.
    sheet = Size(1000.0, 2000.0)
    box = content_area(sheet, margin=100.0, gutter=50.0, gutter_edge="right")
    assert (box.x0, box.y0, box.x1, box.y1) == (100.0, 100.0, 850.0, 1900.0)


def test_content_area_rejects_a_margin_that_eats_the_sheet():
    with pytest.raises(ValueError):
        content_area(Size(200.0, 200.0), margin=100.0, gutter=0.0, gutter_edge="left")


def test_fit_scales_up_and_centres_on_the_constrained_axis():
    source = Rect(0.0, 0.0, 100.0, 100.0)
    target = Rect(0.0, 0.0, 200.0, 400.0)
    p = fit(source, target)
    assert p.scale == 2.0          # width-constrained
    assert p.dx == 0.0
    assert p.dy == 100.0           # (400 - 200) / 2


def test_fit_accounts_for_a_source_box_that_does_not_start_at_the_origin():
    # A cropped page's box rarely starts at 0,0 -- this is the term that is
    # easiest to forget, and forgetting it shifts every page by the crop offset.
    source = Rect(50.0, 50.0, 150.0, 150.0)
    target = Rect(0.0, 0.0, 200.0, 400.0)
    p = fit(source, target)
    assert p.scale == 2.0
    assert p.dx == -100.0
    assert p.dy == 0.0


def test_fit_places_the_source_corners_exactly_on_the_target():
    # The property the two tests above are really about, asserted directly:
    # apply the placement to the source corners and they must bracket the
    # target box, centred.
    source = Rect(50.0, 50.0, 150.0, 150.0)
    target = Rect(0.0, 0.0, 200.0, 400.0)
    p = fit(source, target)

    assert math.isclose(p.apply_x(source.x0), 0.0, abs_tol=1e-9)
    assert math.isclose(p.apply_x(source.x1), 200.0, abs_tol=1e-9)
    assert math.isclose(p.apply_y(source.y0), 100.0, abs_tol=1e-9)
    assert math.isclose(p.apply_y(source.y1), 300.0, abs_tol=1e-9)


def test_fit_is_height_constrained_when_the_source_is_tall():
    source = Rect(0.0, 0.0, 100.0, 400.0)
    target = Rect(0.0, 0.0, 200.0, 400.0)
    p = fit(source, target)
    assert p.scale == 1.0
    assert p.dx == 50.0            # (200 - 100) / 2
    assert p.dy == 0.0


def test_fit_never_distorts():
    # One scale for both axes, always. A book page stretched to fill A4 is
    # the single most obvious way for this program to look broken.
    source = Rect(0.0, 0.0, 300.0, 100.0)
    target = paper("a4")
    p = fit(source, Rect.from_size(target))
    placed_w = p.scale * source.width
    placed_h = p.scale * source.height
    assert math.isclose(placed_w / placed_h, 3.0, rel_tol=1e-12)


def test_fit_rejects_a_degenerate_source():
    # A blank page's ink bbox comes back as 0 0 0 0 from ghostscript. It must
    # not reach fit() -- a zero-width source would divide by zero or, worse,
    # scale by infinity.
    with pytest.raises(ValueError):
        fit(Rect(0.0, 0.0, 0.0, 0.0), Rect(0.0, 0.0, 200.0, 400.0))


def test_a4_content_area_with_realistic_millimetres():
    # 15 mm margins, 10 mm gutter on the binding edge: the defaults a reader
    # would actually use, checked end to end through the unit conversion.
    box = content_area(
        paper("a4"), margin=units.mm(15.0), gutter=units.mm(10.0), gutter_edge="left"
    )
    assert math.isclose(box.x0, units.mm(25.0), rel_tol=1e-12)
    assert math.isclose(box.y0, units.mm(15.0), rel_tol=1e-12)
    assert math.isclose(box.x1, units.mm(195.0), rel_tol=1e-12)
    assert math.isclose(box.y1, units.mm(282.0), rel_tol=1e-12)
