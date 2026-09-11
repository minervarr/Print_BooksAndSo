"""Millimetres in, PDF points out.

A PDF user-space unit is 1/72 inch. Every measurement a human states about
paper -- sheet size, dot pitch, gutter, margin -- is a millimetre. This module
is the only place that conversion happens.

The conversion multiplies before it divides (`v * 72.0 / 25.4`, never
`v * (72.0 / 25.4)`) so that whole inches land exactly: 25.4 mm comes back as
72.0 and not 72.00000000000001. That matters because these values are summed
across a page layout, and an error that starts in the sixteenth decimal place
is still an error that grows.

Paper is stored in MILLIMETRES, not points, because that is how paper is
specified -- A4 is 210x297 mm, and US Letter's 215.9x279.4 is exactly 8.5x11
inches restated. Converting at the point of use keeps one code path.
"""

#: PDF user-space units per millimetre. Exposed for documentation; prefer mm().
MM_TO_PT = 72.0 / 25.4

#: Sheet sizes in millimetres, keyed by the name the CLI accepts (--paper a4).
#: Lowercase only: there is no aliasing layer, so a capitalised duplicate here
#: would be a second code path that behaves the same until it does not.
PAPER_MM: dict[str, tuple[float, float]] = {
    "a4": (210.0, 297.0),
    "letter": (215.9, 279.4),  # 8.5 x 11 in
}


def mm(value: float) -> float:
    """Millimetres to PDF points."""
    return value * 72.0 / 25.4


def pt_to_mm(value: float) -> float:
    """PDF points to millimetres."""
    return value * 25.4 / 72.0


def inch(value: float) -> float:
    """Inches to PDF points. Here because paper hardware is still imperial."""
    return value * 72.0
