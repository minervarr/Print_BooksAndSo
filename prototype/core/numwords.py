"""Chapter numbers as English words, for the portrait kicker.

CHAPTER ONE rather than CHAPTER 1. LaTeX's book class prints the numeral, but
the approved portrait spells it, and spelling it is the part that needs code.

A table, not an algorithm: offline, deterministic, no locale database, and the
same twenty lines port to C++ unchanged. Past ninety-nine it returns the
numeral instead of guessing -- a hundred-chapter book is real, and "one hundred
thirty-seven" assembled badly looks worse than 137.
"""

from __future__ import annotations

_ONES = (
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
    "sixteen", "seventeen", "eighteen", "nineteen",
)

_TENS = (
    "", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy",
    "eighty", "ninety",
)


def ordinal_words(number: int) -> str:
    """`number` in lowercase English words, or the numeral past 99.

    Hyphenated, never spaced: "twenty one" would letterspace as two words on
    the portrait and read as a typesetting mistake.
    """
    if number < 1:
        raise ValueError(f"chapters are 1-based; got {number}")

    if number < 20:
        return _ONES[number]
    if number < 100:
        tens, ones = divmod(number, 10)
        return _TENS[tens] if ones == 0 else f"{_TENS[tens]}-{_ONES[ones]}"
    return str(number)
