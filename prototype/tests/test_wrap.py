"""Greedy word wrapping against real glyph advances.

The portrait title gets at most two lines. Wrapping needs the font, so it lives
beside text_width and takes the same GlyphSource.
"""

import pytest

from core.metrics import GlyphOutline
from core.text import wrap_text


class FixedWidthFont:
    """Every glyph 500/1000 em, so at size 10 each character is exactly 5 pt."""

    units_per_em = 1000

    def outline(self, char: str) -> GlyphOutline:
        return GlyphOutline(advance=500.0, commands=())


FONT = FixedWidthFont()


def test_a_short_title_stays_on_one_line():
    assert wrap_text(FONT, "Short", size=10.0, max_width=100.0, max_lines=2) == ("Short",)


def test_a_long_title_breaks_at_a_space():
    # 5 pt per character. "Habit Formation" is 15 chars = 75 pt; a 40 pt limit
    # fits "Habit" (25) but not "Habit Formation".
    lines = wrap_text(FONT, "Habit Formation", size=10.0, max_width=40.0, max_lines=2)
    assert lines == ("Habit", "Formation")


def test_wrapping_is_greedy():
    lines = wrap_text(FONT, "a b c d", size=10.0, max_width=30.0, max_lines=3)
    # 30 pt holds 6 characters: "a b c" is 5, "a b c d" is 7. So the first line
    # takes as much as fits.
    assert lines[0] == "a b c"


def test_beyond_max_lines_the_last_line_is_truncated_with_an_ellipsis():
    # A 40-word chapter title exists. Silently dropping the tail would print a
    # title that reads as a different title.
    lines = wrap_text(
        FONT, "one two three four five six", size=10.0, max_width=40.0, max_lines=2
    )
    assert len(lines) == 2
    assert lines[-1].endswith("…")


def test_a_single_word_too_long_for_the_line_is_not_dropped():
    # No hyphenation dictionary here, so it overflows rather than vanishes --
    # visible on the proof, which is the point.
    lines = wrap_text(FONT, "Unsplittable", size=10.0, max_width=10.0, max_lines=2)
    assert lines == ("Unsplittable",)


def test_the_empty_string_wraps_to_nothing():
    assert wrap_text(FONT, "", size=10.0, max_width=100.0, max_lines=2) == ()


def test_runs_of_whitespace_collapse():
    assert wrap_text(
        FONT, "  Habit   Formation  ", size=10.0, max_width=200.0, max_lines=2
    ) == ("Habit Formation",)


def test_a_nonpositive_width_is_rejected():
    with pytest.raises(ValueError):
        wrap_text(FONT, "x", size=10.0, max_width=0.0, max_lines=2)
