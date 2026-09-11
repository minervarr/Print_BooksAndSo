"""The seam between core/ and a real font file.

core/ lays out Computer Modern without importing a font library: it talks to a
GlyphSource, and backend/ supplies one (fontTools in the prototype,
FT_Outline_Decompose in the C++ port). The whole interface is "give me the
outline of this character", which is what makes the port cheap -- there is no
font dictionary, no CID map and no subsetting on either side.

Coordinates are in FONT UNITS. Scaling to a point size is text.py's job,
because the same outline is drawn at four different sizes on one portrait.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

#: One PDF path segment in font units. The operator is a PDF operator name and
#: the tuple is its operands:
#:
#:   ("m", (x, y))                        moveto
#:   ("l", (x, y))                        lineto
#:   ("c", (x1, y1, x2, y2, x3, y3))      cubic bezier
#:   ("h", ())                            closepath
#:
#: Cubic only. Latin Modern is CFF-flavoured OpenType, so its outlines are
#: already cubic and map straight onto PDF's `c`; a quadratic conversion step
#: would be code waiting for a TrueType font this project never loads.
PathCommand = tuple[str, tuple[float, ...]]


@dataclass(frozen=True, slots=True)
class GlyphOutline:
    """One glyph: how far the pen moves, and the path to fill.

    `commands` may be empty -- a space is a real glyph with a real advance and
    nothing to draw. Emitting nothing for it *and* failing to advance would set
    the rest of the line solid.
    """

    advance: float
    commands: tuple[PathCommand, ...]


@runtime_checkable
class GlyphSource(Protocol):
    """A font, reduced to the one question core/ asks it."""

    units_per_em: int

    def outline(self, char: str) -> GlyphOutline:
        """The glyph for `char`, in font units.

        Raises KeyError if the font has no glyph for it. text.py collects those
        and reports them together, so a book title with a curly quote names the
        character to fix instead of raising from inside a page.
        """
        ...
