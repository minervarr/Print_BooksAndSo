"""Content-stream emitters: the furniture this program draws on a sheet.

A PDF content stream is a string of postfix operators. So these functions
return strings, they take no PDF library, and their tests read the operators
back. That is the only reason page drawing -- normally the untestable part of a
program like this -- has real tests here.

Two conventions hold throughout:

  * Every emitter wraps itself in `q ... Q`. Without that, a line width or a
    colour leaks into whatever draws next, and the symptom appears on a
    different page than the cause.
  * `ink` is the fraction of black a human would name (0.25 = "25 % K"), not a
    PDF gray level. PDF gray runs the other way -- 0 is black -- so the
    conversion happens here, once, instead of at every call site.
"""

from __future__ import annotations

from typing import Literal

from core.geometry import Rect
from core.pdfops import gray as _gray
from core.pdfops import num as _num

Corner = Literal["bottom-left", "bottom-right", "top-left", "top-right"]

#: Slack allowed when counting how many pitches span a box. 170 mm / 5 mm is
#: exactly 34, but in binary it can land a hair under and lose a whole column.
_EPS = 1e-9


def _count(span: float, pitch: float) -> int:
    """How many points at `pitch` fit across `span`, inclusive of both ends."""
    return int(span / pitch + _EPS) + 1


def dot_grid(box: Rect, *, pitch: float, dot: float, ink: float) -> str:
    """A dot grid filling `box`, centred, as ONE stroked path.

    Every dot is a degenerate subpath -- `x y m x y l` -- and the round line
    cap (`1 J`) is what turns a zero-length segment into a round dot. Without
    `1 J` a zero-length subpath paints nothing at all: the page comes out blank
    while the stream looks perfectly correct.

    The alternative, a bezier circle per dot, is four curve operators each and
    a stream two orders of magnitude larger. This way the whole grid is one
    path with one `S`, and as a Form XObject it appears once in the document
    rather than once per page.
    """
    if pitch <= 0.0:
        raise ValueError(f"pitch must be positive, got {pitch}")
    if dot <= 0.0:
        raise ValueError(f"dot diameter must be positive, got {dot}")
    gray = _gray(ink)
    if pitch > box.width or pitch > box.height:
        raise ValueError(
            f"pitch {pitch} does not fit in a {box.width} x {box.height} box"
        )

    nx = _count(box.width, pitch)
    ny = _count(box.height, pitch)

    # Centre the grid: the slack left over after whole pitches is split, so the
    # margins look deliberate instead of the grid hugging one corner.
    x0 = box.x0 + (box.width - (nx - 1) * pitch) / 2.0
    y0 = box.y0 + (box.height - (ny - 1) * pitch) / 2.0

    out = ["q", f"{gray} G", f"{_num(dot)} w", "1 J"]
    for iy in range(ny):
        y = _num(y0 + iy * pitch)
        for ix in range(nx):
            x = _num(x0 + ix * pitch)
            out.append(f"{x} {y} m {x} {y} l")
    out.append("S")
    out.append("Q")
    return "\n".join(out)


def center_ticks(box: Rect, *, length: float, width: float, ink: float) -> str:
    """Four inward ticks at the edge midpoints of `box`.

    Both axes for about eight path operators, and -- the point -- the writing
    area stays clear. Full crosshairs would cost the same ink but cross the
    middle of the page, which is where you actually write.
    """
    if length <= 0.0 or width <= 0.0:
        raise ValueError(f"length and width must be positive, got {length}, {width}")
    gray = _gray(ink)
    if 2.0 * length >= min(box.width, box.height):
        raise ValueError(
            f"ticks of {length} would meet in the middle of a "
            f"{box.width} x {box.height} box"
        )

    mid_x = (box.x0 + box.x1) / 2.0
    mid_y = (box.y0 + box.y1) / 2.0

    segments = [
        (mid_x, box.y0, mid_x, box.y0 + length),   # bottom, pointing up
        (mid_x, box.y1, mid_x, box.y1 - length),   # top, pointing down
        (box.x0, mid_y, box.x0 + length, mid_y),   # left, pointing right
        (box.x1, mid_y, box.x1 - length, mid_y),   # right, pointing left
    ]

    out = ["q", f"{gray} G", f"{_num(width)} w", "0 J"]
    for ax, ay, bx, by in segments:
        out.append(f"{_num(ax)} {_num(ay)} m {_num(bx)} {_num(by)} l")
    out.append("S")
    out.append("Q")
    return "\n".join(out)


def registration_tick(
    box: Rect, *, corner: Corner, size: float, width: float, ink: float
) -> str:
    """A small L at one corner of `box`, drawn on both sides of a sheet.

    This is the manual-duplex check: print the fronts, print the backs, hold a
    sheet to the light. If the two Ls do not sit on top of each other the flip
    was wrong, and you know it on sheet one rather than sheet forty.
    """
    if size <= 0.0 or width <= 0.0:
        raise ValueError(f"size and width must be positive, got {size}, {width}")
    gray = _gray(ink)

    if corner == "bottom-left":
        cx, cy, dx, dy = box.x0, box.y0, size, size
    elif corner == "bottom-right":
        cx, cy, dx, dy = box.x1, box.y0, -size, size
    elif corner == "top-left":
        cx, cy, dx, dy = box.x0, box.y1, size, -size
    elif corner == "top-right":
        cx, cy, dx, dy = box.x1, box.y1, -size, -size
    else:
        raise ValueError(
            f"unknown corner {corner!r}; expected one of bottom-left, "
            "bottom-right, top-left, top-right"
        )

    out = [
        "q",
        f"{gray} G",
        f"{_num(width)} w",
        "0 J",
        f"{_num(cx)} {_num(cy)} m {_num(cx + dx)} {_num(cy)} l",
        f"{_num(cx)} {_num(cy)} m {_num(cx)} {_num(cy + dy)} l",
        "S",
        "Q",
    ]
    return "\n".join(out)
