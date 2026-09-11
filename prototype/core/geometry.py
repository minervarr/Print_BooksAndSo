"""Sheet geometry: the box content may occupy, and how a page fits into it.

Pure arithmetic over PDF user-space points. No PDF library, no I/O.

Two things live here and nothing else does:

  content_area()  what part of a sheet may be drawn on, once the margin and
                  the binding gutter are taken out
  fit()           the uniform scale and offset that centres a source box in a
                  target box

`fit` returns a Placement rather than a matrix because the caller needs the
scale on its own (to reason about legibility) as well as the translation. The
PDF it becomes is `q <s> 0 0 <s> <dx> <dy> cm ... Q` -- uniform, never a
separate sx/sy, because a book page stretched to fill the sheet is the most
obvious way for this program to look broken.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from core import units

GutterEdge = Literal["left", "right"]


@dataclass(frozen=True, slots=True)
class Size:
    """A sheet, in points."""

    width: float
    height: float

    def __post_init__(self) -> None:
        if self.width <= 0.0 or self.height <= 0.0:
            raise ValueError(f"degenerate size: {self.width} x {self.height}")


@dataclass(frozen=True, slots=True)
class Rect:
    """A PDF box, lower-left to upper-right.

    Construction REJECTS an inverted box instead of normalising it. A box with
    x1 < x0 always means the caller read a /MediaBox wrong or subtracted in the
    wrong order, and quietly swapping the corners would hide that bug behind
    output that is merely slightly off.
    """

    x0: float
    y0: float
    x1: float
    y1: float

    def __post_init__(self) -> None:
        if self.x1 < self.x0 or self.y1 < self.y0:
            raise ValueError(
                f"inverted rect: ({self.x0}, {self.y0}) .. ({self.x1}, {self.y1})"
            )

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    @classmethod
    def from_size(cls, size: Size) -> Rect:
        return cls(0.0, 0.0, size.width, size.height)


@dataclass(frozen=True, slots=True)
class Placement:
    """A uniform scale plus a translation: `s 0 0 s dx dy cm`."""

    scale: float
    dx: float
    dy: float

    def apply_x(self, x: float) -> float:
        return self.scale * x + self.dx

    def apply_y(self, y: float) -> float:
        return self.scale * y + self.dy


def paper(name: str) -> Size:
    """Sheet size in points, by the name the CLI accepts."""
    try:
        width_mm, height_mm = units.PAPER_MM[name]
    except KeyError:
        known = ", ".join(sorted(units.PAPER_MM))
        raise ValueError(f"unknown paper {name!r}; known sizes: {known}") from None
    return Size(units.mm(width_mm), units.mm(height_mm))


def content_area(
    sheet: Size, *, margin: float, gutter: float, gutter_edge: GutterEdge
) -> Rect:
    """The drawable box of one side of one sheet.

    The margin comes off all four edges; the gutter comes off ONE edge, the one
    the binding is on. Which edge that is depends on the side: a recto's
    binding edge is its left, a verso's is its right -- flip a sheet bound on
    the left and the holes move to the other side. The caller decides (see
    plan.py); this function only obeys.
    """
    if gutter < 0.0 or margin < 0.0:
        raise ValueError(f"negative margin/gutter: {margin}, {gutter}")

    x0 = margin + (gutter if gutter_edge == "left" else 0.0)
    x1 = sheet.width - margin - (gutter if gutter_edge == "right" else 0.0)
    y0 = margin
    y1 = sheet.height - margin

    if x1 <= x0 or y1 <= y0:
        raise ValueError(
            f"margin {margin} + gutter {gutter} leaves no content area on a "
            f"{sheet.width} x {sheet.height} sheet"
        )
    return Rect(x0, y0, x1, y1)


def fit(source: Rect, target: Rect) -> Placement:
    """Uniform scale + offset placing `source` centred inside `target`.

    The `- scale * source.x0` term is the one that is easy to forget: a cropped
    page's box rarely starts at the origin, and dropping it shifts every page
    on every sheet by the crop offset.
    """
    if source.width <= 0.0 or source.height <= 0.0:
        raise ValueError(
            f"degenerate source box {source}; a blank page's ink bbox comes "
            "back as 0 0 0 0 and must be filtered out before it reaches fit()"
        )

    scale = min(target.width / source.width, target.height / source.height)
    dx = target.x0 + (target.width - scale * source.width) / 2.0 - scale * source.x0
    dy = target.y0 + (target.height - scale * source.height) / 2.0 - scale * source.y0
    return Placement(scale, dx, dy)
