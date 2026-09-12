"""Chapter numbers as English words.

The portrait kicker reads CHAPTER ONE. LaTeX's book class actually prints the
arabic numeral, but the approved mockup spells it, and spelling it is the part
that needs code. Offline, deterministic, no locale database: a table.
"""

import pytest

from core.numwords import ordinal_words


@pytest.mark.parametrize(
    "number,expected",
    [
        (1, "one"),
        (2, "two"),
        (9, "nine"),
        (10, "ten"),
        (11, "eleven"),
        (12, "twelve"),
        (13, "thirteen"),
        (15, "fifteen"),
        (19, "nineteen"),
        (20, "twenty"),
        (21, "twenty-one"),
        (30, "thirty"),
        (42, "forty-two"),
        (50, "fifty"),
        (99, "ninety-nine"),
    ],
)
def test_numbers_become_words(number, expected):
    assert ordinal_words(number) == expected


def test_the_hyphen_is_a_hyphen_not_a_space():
    # "twenty one" would letterspace as two words on the portrait and look
    # like a typesetting mistake.
    assert "-" in ordinal_words(21)
    assert " " not in ordinal_words(21)


def test_zero_and_negatives_are_rejected():
    # Chapters are 1-based. A zero here means an off-by-one upstream.
    with pytest.raises(ValueError):
        ordinal_words(0)
    with pytest.raises(ValueError):
        ordinal_words(-3)


def test_beyond_the_table_it_says_so_rather_than_guessing():
    # A hundred-chapter book is real (a Bible, a serialized novel). Falling
    # back to the numeral is right; inventing "one hundred" badly is not.
    assert ordinal_words(100) == "100"
    assert ordinal_words(137) == "137"
