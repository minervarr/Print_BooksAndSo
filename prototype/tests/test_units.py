"""Millimetres, points, and paper.

Every number in this program is eventually a PDF user-space unit (1/72 inch),
but every number a human states about paper is a millimetre. This is the one
place that conversion happens, so it is the one place it can be wrong.
"""

import math

import pytest

from core import units


def test_one_inch_is_seventy_two_points_exactly():
    # Multiply-then-divide, so this is exact rather than 72.00000000000001.
    # Asserted with == on purpose: if it ever becomes approximate, the rest of
    # the geometry starts accumulating error and nothing else will notice.
    assert units.mm(25.4) == 72.0


def test_five_millimetre_dot_pitch():
    # The notes-page grid pitch. Quoted in the spec as 14.1732 pt.
    assert math.isclose(units.mm(5.0), 14.173228346456693, rel_tol=1e-12)


def test_millimetres_round_trip_through_points():
    for value in (0.0, 0.25, 5.0, 210.0, 297.0):
        assert math.isclose(units.pt_to_mm(units.mm(value)), value, rel_tol=1e-12)


def test_a4_is_210_by_297_millimetres():
    assert units.PAPER_MM["a4"] == (210.0, 297.0)


def test_a4_in_points():
    width_mm, height_mm = units.PAPER_MM["a4"]
    assert math.isclose(units.mm(width_mm), 595.2755905511812, rel_tol=1e-12)
    assert math.isclose(units.mm(height_mm), 841.8897637795277, rel_tol=1e-12)


def test_letter_is_us_letter_in_millimetres():
    # 8.5 x 11 inches. Stored in mm like every other paper so there is exactly
    # one code path, even though inches are where it came from.
    width_mm, height_mm = units.PAPER_MM["letter"]
    assert math.isclose(units.mm(width_mm), 612.0, abs_tol=1e-9)
    assert math.isclose(units.mm(height_mm), 792.0, abs_tol=1e-9)


def test_paper_names_are_lowercase_only():
    # The CLI takes --paper a4; there is no aliasing layer, so the table must
    # not grow capitalised duplicates.
    assert all(name == name.lower() for name in units.PAPER_MM)


def test_unknown_paper_is_a_keyerror_not_a_silent_default():
    with pytest.raises(KeyError):
        units.PAPER_MM["a3"]
