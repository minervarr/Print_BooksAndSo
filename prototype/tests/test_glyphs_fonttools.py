"""The real font, read from the real file.

These are backend tests: unlike tests/test_text.py they need fontTools and the
shipped OTF. They exist to prove the one assumption the no-embedded-font design
rests on -- that Latin Modern's outlines come back as CUBIC segments that map
straight onto PDF's `c`.
"""

import pytest

from backend.glyphs_fonttools import OpenTypeGlyphs, font_dir
from core.metrics import GlyphOutline, GlyphSource
from core.text import draw_text, text_width


@pytest.fixture(scope="module")
def roman() -> OpenTypeGlyphs:
    return OpenTypeGlyphs.regular()


def test_the_shipped_faces_exist():
    for name in ("lmroman10-regular.otf", "lmroman10-italic.otf"):
        assert (font_dir() / name).is_file(), font_dir() / name


def test_it_satisfies_the_glyphsource_protocol(roman):
    # The protocol is the seam core/ depends on; if this ever fails, core/ is
    # talking to something it was not designed against.
    assert isinstance(roman, GlyphSource)


def test_latin_modern_has_a_1000_unit_em(roman):
    assert roman.units_per_em == 1000


def test_a_capital_a_has_an_outline_and_an_advance(roman):
    glyph = roman.outline("A")
    assert isinstance(glyph, GlyphOutline)
    assert glyph.advance > 0
    assert glyph.commands


def test_every_operator_is_one_pdf_understands(roman):
    seen = set()
    for char in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,:;-":
        for operator, _ in roman.outline(char).commands:
            seen.add(operator)
    assert seen <= {"m", "l", "c", "h"}, seen


def test_the_outlines_are_cubic_which_is_the_whole_design(roman):
    # If Latin Modern were quadratic, every glyph would need converting and the
    # C++ port would need a converter too. It is not: it is CFF.
    operators = {op for op, _ in roman.outline("S").commands}
    assert "c" in operators


def test_curve_operands_come_in_sixes(roman):
    for operator, operands in roman.outline("O").commands:
        if operator == "c":
            assert len(operands) == 6, operands


def test_a_space_advances_without_drawing(roman):
    space = roman.outline(" ")
    assert space.advance > 0
    assert space.commands == ()


def test_an_unmapped_character_raises_keyerror(roman):
    with pytest.raises(KeyError):
        roman.outline("")   # a private-use codepoint


def test_outlines_are_cached_by_character(roman):
    assert roman.outline("A") is roman.outline("A")


def test_real_text_measures_plausibly(roman):
    # "Chapter One" at 24 pt should be a few inches, not a few points and not
    # a few feet. A units_per_em mix-up shows up here immediately.
    width = text_width(roman, "Chapter One", size=24.0)
    assert 100.0 < width < 220.0, width


def test_real_text_draws_a_fillable_path(roman):
    stream = draw_text(roman, "Chapter One", x=50.0, y=700.0, size=24.0, ink=1.0)
    assert stream.startswith("q")
    assert stream.endswith("Q")
    assert "\nf\n" in stream
    assert " c" in stream            # real curves survived
    assert len(stream) > 1000        # a real outline, not a stub


def test_the_italic_face_loads_too(roman):
    italic = OpenTypeGlyphs.italic()
    assert italic.units_per_em == 1000
    assert italic.outline("A").commands
    # Different face, different shape: a copy-paste path bug would make these
    # identical.
    assert italic.outline("A").commands != roman.outline("A").commands


def test_closed_contours_are_closed_explicitly(roman):
    # PDF's `f` closes open subpaths implicitly, so dropping `h` renders the
    # same and no other test notices. It is pinned anyway: `h` is part of the
    # PathCommand contract core/ is written against, and the C++ port must
    # produce the same command stream for the golden tests to diff clean.
    operators = [op for op, _ in roman.outline("O").commands]
    assert "h" in operators
