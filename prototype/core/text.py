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
