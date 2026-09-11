"""Formatting primitives shared by every content-stream emitter.

Small on purpose. These two conversions were duplicated in drawing.py and
text.py, which is exactly the kind of duplication that drifts: one of the two
starts rounding to five decimals, or stops inverting ink, and the difference
only shows up as a faint smudge on paper.
"""

from __future__ import annotations


def num(value: float) -> str:
    """A PDF number: four decimals, no trailing zeros, no trailing point.

    PDF points are 1/72 inch, so four decimals is ~0.4 micron -- far finer than
    any printer resolves. Short numbers matter because the dot grid is the
    largest stream this program writes.
    """
    text = f"{value:.4f}".rstrip("0").rstrip(".")
    return "0" if text in ("", "-", "-0") else text


def gray(ink: float) -> str:
    """A fraction of black (0.25 = "25 % K") as a PDF gray level.

    PDF gray runs the other way -- 0 is black, 1 is white -- so the inversion
    happens here, once, rather than at every call site.
    """
    if not 0.0 <= ink <= 1.0:
        raise ValueError(f"ink must be a fraction of black in 0..1, got {ink}")
    return num(1.0 - ink)
