"""Text as glyph outlines.

There is no font dictionary in the output. Text is drawn by asking the font for
each glyph's outline and emitting PDF path operators, which is why core/ can lay
out Computer Modern without importing a font library: it talks to a
GlyphSource, and the test supplies a hand-built one.

The stub below is a legitimate test double -- the font is an external
dependency with a real implementation in backend/ -- not a mock of the code
under test. Its glyphs are deliberately trivial so the arithmetic is checkable
by hand: a 1000-unit em, an 'A' that is a filled square from 0,0 to 1000,1000
advancing 500, and a 'B' that is a single cubic curve.
"""

import re

import pytest

from core.metrics import GlyphOutline
from core.text import draw_text, text_width


class StubFont:
    units_per_em = 1000

    _glyphs = {
        "A": GlyphOutline(
            advance=500.0,
            commands=(
                ("m", (0.0, 0.0)),
                ("l", (1000.0, 0.0)),
                ("l", (1000.0, 1000.0)),
                ("l", (0.0, 1000.0)),
                ("h", ()),
            ),
        ),
        "B": GlyphOutline(
            advance=250.0,
            commands=(
                ("m", (0.0, 0.0)),
                ("c", (100.0, 200.0, 300.0, 400.0, 500.0, 600.0)),
                ("h", ()),
            ),
        ),
        " ": GlyphOutline(advance=300.0, commands=()),
    }

    def outline(self, char: str) -> GlyphOutline:
        try:
            return self._glyphs[char]
        except KeyError:
            raise KeyError(char) from None


def ops(stream: str, operator: str) -> int:
    return len(re.findall(rf"(?:^|\s){re.escape(operator)}(?=\s|$)", stream))


def points(stream: str) -> list[tuple[float, float]]:
    return [
        (float(a), float(b))
        for a, b in re.findall(r"(-?[\d.]+) (-?[\d.]+) [ml]", stream)
    ]


# --- measuring --------------------------------------------------------------


def test_width_of_one_glyph_scales_from_font_units_to_points():
    # advance 500 of a 1000-unit em at 10 pt = 5 pt.
    assert text_width(StubFont(), "A", size=10.0) == pytest.approx(5.0)


def test_width_accumulates_advances():
    # A=500, B=250, space=300 -> 1050/1000 * 10 = 10.5
    assert text_width(StubFont(), "AB ", size=10.0) == pytest.approx(10.5)


def test_width_of_the_empty_string_is_zero():
    assert text_width(StubFont(), "", size=10.0) == 0.0


def test_tracking_is_added_between_glyphs_not_after_the_last():
    # Three glyphs means two gaps. Adding a gap after the last one would make
    # every centred line sit visibly left of centre.
    plain = text_width(StubFont(), "AAA", size=10.0)
    tracked = text_width(StubFont(), "AAA", size=10.0, tracking=2.0)
    assert tracked - plain == pytest.approx(4.0)


def test_tracking_does_not_apply_to_a_single_glyph():
    plain = text_width(StubFont(), "A", size=10.0)
    tracked = text_width(StubFont(), "A", size=10.0, tracking=2.0)
    assert tracked == pytest.approx(plain)


# --- drawing ----------------------------------------------------------------


def test_glyphs_are_filled_not_stroked():
    # CFF outlines are filled with nonzero winding. Stroking them would draw
    # hairline outlines of the letters: legible, and obviously wrong.
    stream = draw_text(StubFont(), "A", x=0.0, y=0.0, size=10.0, ink=1.0)
    assert ops(stream, "f") == 1
    assert ops(stream, "S") == 0


def test_drawing_saves_and_restores_graphics_state():
    stream = draw_text(StubFont(), "A", x=0.0, y=0.0, size=10.0, ink=1.0)
    assert ops(stream, "q") == 1
    assert ops(stream, "Q") == 1


def test_ink_becomes_a_fill_gray_not_a_stroke_gray():
    stream = draw_text(StubFont(), "A", x=0.0, y=0.0, size=10.0, ink=0.6)
    assert re.search(r"(?:^|\s)0\.4 g(?=\s|$)", stream)
    assert not re.search(r"(?:^|\s)0\.4 G(?=\s|$)", stream)


def test_an_outline_is_scaled_from_font_units_to_the_point_size():
    # The stub 'A' spans the full em, so at 10 pt it must span exactly 10 pt.
    stream = draw_text(StubFont(), "A", x=0.0, y=0.0, size=10.0, ink=1.0)
    xs = [x for x, _ in points(stream)]
    ys = [y for _, y in points(stream)]
    assert min(xs) == pytest.approx(0.0)
    assert max(xs) == pytest.approx(10.0)
    assert min(ys) == pytest.approx(0.0)
    assert max(ys) == pytest.approx(10.0)


def test_an_outline_is_translated_to_the_pen_position():
    stream = draw_text(StubFont(), "A", x=100.0, y=200.0, size=10.0, ink=1.0)
    xs = [x for x, _ in points(stream)]
    ys = [y for _, y in points(stream)]
    assert min(xs) == pytest.approx(100.0)
    assert max(xs) == pytest.approx(110.0)
    assert min(ys) == pytest.approx(200.0)
    assert max(ys) == pytest.approx(210.0)


def test_the_pen_advances_between_glyphs():
    # Two 'A's: the second starts one advance (500/1000 * 10 = 5 pt) along.
    # Forgetting this draws every glyph of a title on top of the first.
    stream = draw_text(StubFont(), "AA", x=0.0, y=0.0, size=10.0, ink=1.0)
    xs = sorted({x for x, _ in points(stream)})
    assert xs == pytest.approx([0.0, 5.0, 10.0, 15.0])


def test_tracking_moves_the_pen_too():
    stream = draw_text(StubFont(), "AA", x=0.0, y=0.0, size=10.0, ink=1.0, tracking=2.0)
    xs = sorted({x for x, _ in points(stream)})
    assert xs == pytest.approx([0.0, 7.0, 10.0, 17.0])


def test_cubic_curves_survive_as_curve_operators():
    # Latin Modern is CFF-flavoured, so its outlines are ALREADY cubic and map
    # straight onto PDF's c. A quadratic conversion step here would be a bug
    # looking for a TrueType font that this project never loads.
    stream = draw_text(StubFont(), "B", x=0.0, y=0.0, size=10.0, ink=1.0)
    assert ops(stream, "c") == 1
    curve = re.search(r"((?:-?[\d.]+ ){6})c", stream)
    assert curve
    values = [float(v) for v in curve.group(1).split()]
    assert values == pytest.approx([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])


def test_a_glyph_with_no_outline_still_advances():
    # A space. Emitting nothing for it but also not advancing would set the
    # rest of the line solid.
    stream = draw_text(StubFont(), "A A", x=0.0, y=0.0, size=10.0, ink=1.0)
    xs = sorted({x for x, _ in points(stream)})
    assert max(xs) == pytest.approx(18.0)   # (500 + 300)/1000*10 + 10


def test_the_empty_string_draws_nothing_at_all():
    # Not even a q/Q pair: an empty stream is easier to assert on downstream
    # than a stream that is technically non-empty.
    assert draw_text(StubFont(), "", x=0.0, y=0.0, size=10.0, ink=1.0) == ""


def test_missing_glyphs_are_reported_together_and_name_themselves():
    # One error naming every missing character, rather than a bare KeyError
    # from somewhere inside a page. A book title with a curly quote should tell
    # you which character to add, not where the traceback happened.
    with pytest.raises(ValueError, match="missing"):
        draw_text(StubFont(), "AZQ", x=0.0, y=0.0, size=10.0, ink=1.0)

    try:
        draw_text(StubFont(), "AZQ", x=0.0, y=0.0, size=10.0, ink=1.0)
    except ValueError as exc:
        assert "Z" in str(exc) and "Q" in str(exc)


def test_a_nonpositive_size_is_rejected():
    with pytest.raises(ValueError):
        draw_text(StubFont(), "A", x=0.0, y=0.0, size=0.0, ink=1.0)
