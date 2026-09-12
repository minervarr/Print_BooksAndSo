"""Laying out a line of text as filled outlines.

No font dictionary reaches the output: each glyph becomes PDF path operators
and the line is one filled path. The trade is that this text is not selectable
or searchable -- deliberate, for a print-targeted artifact, and it removes CID
font dictionaries and width arrays from both sides of the port.

Everything here is pure arithmetic over a GlyphSource (see metrics.py).
"""

from __future__ import annotations

from core.metrics import GlyphSource
from core.pdfops import gray, num


def text_width(
    source: GlyphSource, text: str, *, size: float, tracking: float = 0.0
) -> float:
    """Width of `text` in points.

    Tracking is added BETWEEN glyphs, never after the last one. A trailing gap
    would make every centred line sit visibly left of centre -- by half the
    tracking, which is small, consistent, and maddening to find.
    """
    if not text:
        return 0.0

    scale = size / source.units_per_em
    advances = sum(source.outline(ch).advance for ch in text)
    return advances * scale + tracking * (len(text) - 1)


def draw_text(
    source: GlyphSource,
    text: str,
    *,
    x: float,
    y: float,
    size: float,
    ink: float,
    tracking: float = 0.0,
) -> str:
    """`text` at (x, y) as one filled path, baseline-left origin.

    Filled with `f` (nonzero winding), which is what CFF outlines expect.
    Stroking them instead would draw hairline outlines of the letters:
    legible, and obviously wrong.
    """
    if size <= 0.0:
        raise ValueError(f"size must be positive, got {size}")
    fill = gray(ink)
    if not text:
        return ""

    # Collect every missing character before failing, so the error names all of
    # them at once rather than stopping at the first.
    missing: list[str] = []
    outlines = []
    for ch in text:
        try:
            outlines.append(source.outline(ch))
        except KeyError:
            if ch not in missing:
                missing.append(ch)
    if missing:
        shown = " ".join(f"{ch!r} (U+{ord(ch):04X})" for ch in missing)
        raise ValueError(f"font is missing {len(missing)} glyph(s): {shown}")

    scale = size / source.units_per_em
    out = ["q", f"{fill} g"]
    pen = x

    for outline in outlines:
        for operator, operands in outline.commands:
            if operands:
                coords = [
                    num(pen + operands[i] * scale)
                    if i % 2 == 0
                    else num(y + operands[i] * scale)
                    for i in range(len(operands))
                ]
                out.append(f"{' '.join(coords)} {operator}")
            else:
                out.append(operator)
        pen += outline.advance * scale + tracking

    out.append("f")
    out.append("Q")
    return "\n".join(out)


def wrap_text(
    source: GlyphSource,
    text: str,
    *,
    size: float,
    max_width: float,
    max_lines: int,
    tracking: float = 0.0,
) -> tuple[str, ...]:
    """Greedy word wrap, measured against real glyph advances.

    Two deliberate refusals:

    * A single word wider than the line is NOT dropped or hyphenated -- there
      is no hyphenation dictionary here, so it overflows and shows up on the
      proof, which is where you want to find out.
    * Running past `max_lines` truncates with an ellipsis rather than silently
      dropping the tail. A title missing its last four words reads as a
      different title, and nothing downstream would flag it.
    """
    if max_width <= 0.0:
        raise ValueError(f"max_width must be positive, got {max_width}")
    if max_lines < 1:
        raise ValueError(f"max_lines must be at least 1, got {max_lines}")

    words = text.split()
    if not words:
        return ()

    lines: list[str] = []
    current = ""

    for word in words:
        candidate = f"{current} {word}" if current else word
        if current and text_width(
            source, candidate, size=size, tracking=tracking
        ) > max_width:
            lines.append(current)
            current = word
            if len(lines) == max_lines:
                # Out of lines with words still to place.
                lines[-1] = f"{lines[-1]}\u2026"
                return tuple(lines)
        else:
            current = candidate

    lines.append(current)
    return tuple(lines)
