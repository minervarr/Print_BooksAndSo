"""Content-stream emitters.

A PDF content stream is text, which is the whole reason this code is in core/
and testable at all. These tests read the operators the emitters produce.

The recurring assertion is ONE stroke operator per grid. A dot grid drawn the
obvious way -- a circle per dot -- is thousands of path operators and a bloated
stream. Drawn as one path of degenerate subpaths with a round line cap, it is
one `S`, and as a Form XObject it appears once in the file rather than once per
page. That is the performance claim in CLAUDE.md, so it gets a test.
"""

import re

import pytest

from core import units
from core.drawing import center_ticks, dot_grid, registration_tick
from core.geometry import Rect


def ops(stream: str, operator: str) -> int:
    """How many times a bare operator appears as its own token."""
    return len(re.findall(rf"(?:^|\s){re.escape(operator)}(?=\s|$)", stream))


def numbers(stream: str) -> list[float]:
    return [float(t) for t in re.findall(r"-?\d+\.?\d*", stream)]


# --- the dot grid -----------------------------------------------------------


def test_dot_grid_is_one_path_with_one_stroke():
    box = Rect(0.0, 0.0, 100.0, 100.0)
    stream = dot_grid(box, pitch=10.0, dot=0.7, ink=0.25)
    assert ops(stream, "S") == 1, "the whole grid must be a single stroked path"
    assert ops(stream, "f") == 0, "dots are stroked with a round cap, not filled"


def test_dot_grid_emits_one_degenerate_subpath_per_dot():
    # 100 pt wide at a 10 pt pitch is 11 dots per row (0, 10, ... 100).
    box = Rect(0.0, 0.0, 100.0, 100.0)
    stream = dot_grid(box, pitch=10.0, dot=0.7, ink=0.25)
    assert ops(stream, "m") == 11 * 11
    assert ops(stream, "l") == 11 * 11


def test_dot_grid_sets_a_round_cap_so_a_degenerate_subpath_prints_as_a_dot():
    # Without `1 J` a zero-length subpath paints nothing at all: the page would
    # come out blank and the stream would look perfectly correct.
    stream = dot_grid(Rect(0.0, 0.0, 50.0, 50.0), pitch=10.0, dot=0.7, ink=0.25)
    assert re.search(r"(?:^|\s)1 J(?=\s|$)", stream)


def test_dot_grid_line_width_is_the_dot_diameter():
    stream = dot_grid(Rect(0.0, 0.0, 50.0, 50.0), pitch=10.0, dot=0.7087, ink=0.25)
    assert re.search(r"(?:^|\s)0\.7087 w(?=\s|$)", stream)


def test_dot_grid_ink_fraction_becomes_a_stroke_gray():
    # 25 % ink is a gray LEVEL of 0.75, and it is the stroke colour (capital
    # G), not the fill colour. Lowercase g here would leave the dots black.
    stream = dot_grid(Rect(0.0, 0.0, 50.0, 50.0), pitch=10.0, dot=0.7, ink=0.25)
    assert re.search(r"(?:^|\s)0\.75 G(?=\s|$)", stream)
    assert not re.search(r"(?:^|\s)0\.75 g(?=\s|$)", stream)


def test_dot_grid_saves_and_restores_graphics_state():
    # Unbalanced q/Q leaks the line width and colour into whatever draws next.
    stream = dot_grid(Rect(0.0, 0.0, 50.0, 50.0), pitch=10.0, dot=0.7, ink=0.25)
    assert ops(stream, "q") == 1
    assert ops(stream, "Q") == 1
    assert stream.index("q") < stream.index("Q")


def test_dot_grid_is_centred_in_its_box():
    # 105 wide at a 10 pt pitch fits 11 dots spanning 100, so there is 2.5 pt
    # of slack and it is split evenly rather than left-aligned.
    box = Rect(0.0, 0.0, 105.0, 105.0)
    stream = dot_grid(box, pitch=10.0, dot=0.7, ink=0.25)
    xs = sorted({float(m.group(1)) for m in re.finditer(r"(-?[\d.]+) [\d.-]+ m", stream)})
    assert xs[0] == pytest.approx(2.5)
    assert xs[-1] == pytest.approx(102.5)


def test_every_dot_is_inside_its_box():
    box = Rect(20.0, 30.0, 220.0, 330.0)
    stream = dot_grid(box, pitch=7.0, dot=0.7, ink=0.25)
    points = [
        (float(a), float(b))
        for a, b in re.findall(r"(-?[\d.]+) (-?[\d.]+) m", stream)
    ]
    assert points
    for x, y in points:
        assert box.x0 <= x <= box.x1
        assert box.y0 <= y <= box.y1


def test_dot_grid_at_the_real_default_spacing():
    # An A4 content area with 15 mm margins and a 10 mm gutter is 170 x 267 mm.
    # At a 5 mm pitch with dots on both ends that is (34+1) x (53+1) = 1890,
    # derived by hand. A pitch conversion that forgot 72/25.4 would be out by
    # a factor of ~2.8 and still look like a plausible grid.
    box = Rect(units.mm(25.0), units.mm(15.0), units.mm(195.0), units.mm(282.0))
    stream = dot_grid(box, pitch=units.mm(5.0), dot=units.mm(0.25), ink=0.25)
    assert ops(stream, "m") == 35 * 54
    assert ops(stream, "S") == 1


def test_dot_grid_rejects_a_nonpositive_pitch():
    with pytest.raises(ValueError):
        dot_grid(Rect(0.0, 0.0, 50.0, 50.0), pitch=0.0, dot=0.7, ink=0.25)


def test_dot_grid_rejects_a_nonpositive_dot():
    with pytest.raises(ValueError):
        dot_grid(Rect(0.0, 0.0, 50.0, 50.0), pitch=10.0, dot=0.0, ink=0.25)


def test_dot_grid_rejects_an_ink_fraction_outside_zero_to_one():
    with pytest.raises(ValueError):
        dot_grid(Rect(0.0, 0.0, 50.0, 50.0), pitch=10.0, dot=0.7, ink=1.5)


def test_dot_grid_rejects_a_pitch_larger_than_the_box():
    with pytest.raises(ValueError):
        dot_grid(Rect(0.0, 0.0, 5.0, 5.0), pitch=10.0, dot=0.7, ink=0.25)


# --- centre ticks -----------------------------------------------------------


def test_centre_ticks_are_four_ticks_in_one_path():
    box = Rect(0.0, 0.0, 200.0, 400.0)
    stream = center_ticks(box, length=10.0, width=0.3, ink=0.4)
    assert ops(stream, "m") == 4
    assert ops(stream, "l") == 4
    assert ops(stream, "S") == 1


def test_centre_ticks_sit_at_the_edge_midpoints_and_point_inward():
    box = Rect(0.0, 0.0, 200.0, 400.0)
    stream = center_ticks(box, length=10.0, width=0.3, ink=0.4)
    segments = re.findall(
        r"(-?[\d.]+) (-?[\d.]+) m (-?[\d.]+) (-?[\d.]+) l", stream
    )
    found = {tuple(float(v) for v in seg) for seg in segments}

    assert (100.0, 0.0, 100.0, 10.0) in found      # bottom edge, up
    assert (100.0, 400.0, 100.0, 390.0) in found   # top edge, down
    assert (0.0, 200.0, 10.0, 200.0) in found      # left edge, right
    assert (200.0, 200.0, 190.0, 200.0) in found   # right edge, left


def test_centre_ticks_never_cross_the_middle_of_the_page():
    # The point of ticks over crosshairs is that the writing area stays clear.
    box = Rect(0.0, 0.0, 200.0, 400.0)
    stream = center_ticks(box, length=10.0, width=0.3, ink=0.4)
    for x, y in re.findall(r"(-?[\d.]+) (-?[\d.]+) [ml]", stream):
        x, y = float(x), float(y)
        near_an_edge = (
            x <= 10.0 or x >= 190.0 or y <= 10.0 or y >= 390.0
        )
        assert near_an_edge, f"tick point ({x}, {y}) intrudes into the page"


def test_centre_ticks_reject_a_length_that_would_meet_in_the_middle():
    with pytest.raises(ValueError):
        center_ticks(Rect(0.0, 0.0, 20.0, 20.0), length=15.0, width=0.3, ink=0.4)


# --- registration -----------------------------------------------------------


def test_registration_tick_is_one_short_stroked_corner():
    box = Rect(0.0, 0.0, 200.0, 400.0)
    stream = registration_tick(box, corner="bottom-left", size=6.0, width=0.3, ink=1.0)
    assert ops(stream, "S") == 1
    assert ops(stream, "m") == 2   # an L: one horizontal, one vertical arm


def test_registration_tick_is_placed_at_the_named_corner():
    box = Rect(10.0, 20.0, 210.0, 420.0)
    stream = registration_tick(box, corner="top-right", size=6.0, width=0.3, ink=1.0)
    xs = [float(x) for x, _ in re.findall(r"(-?[\d.]+) (-?[\d.]+) [ml]", stream)]
    ys = [float(y) for _, y in re.findall(r"(-?[\d.]+) (-?[\d.]+) [ml]", stream)]
    assert max(xs) == pytest.approx(210.0)
    assert max(ys) == pytest.approx(420.0)


def test_registration_tick_rejects_an_unknown_corner():
    with pytest.raises(ValueError):
        registration_tick(
            Rect(0.0, 0.0, 100.0, 100.0), corner="middle", size=6.0, width=0.3, ink=1.0
        )
