"""A GlyphSource backed by a real OpenType file, via fontTools.

This is the whole font implementation. There is no embedding, no subsetting and
no CID dictionary anywhere in this program: core/text.py asks for a glyph's
outline and fills it as a path. The C++ port replaces this one file with
FT_Outline_Decompose and changes nothing above it.

Latin Modern is CFF-flavoured OpenType, so fontTools hands back cubic
`curveTo` segments that map straight onto PDF's `c`. A quadratic `qCurveTo`
would mean a TrueType font got loaded, which this program never does on
purpose -- so it raises rather than silently approximating.
"""

from __future__ import annotations

import functools
import os
import pathlib

from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont

from core.metrics import GlyphOutline, PathCommand


def font_dir() -> pathlib.Path:
    """Where the shipped Latin Modern faces live.

    assets/fonts/ sits at the REPO root, shared by the prototype and the C++
    port, so neither owns the font and they cannot drift apart.
    """
    override = os.environ.get("PRINT_BOOKS_FONT_DIR")
    if override:
        return pathlib.Path(override)
    return pathlib.Path(__file__).resolve().parents[2] / "assets" / "fonts"


class OpenTypeGlyphs:
    """One face, loaded once, with its outlines cached.

    A chapter portrait draws the same few dozen characters repeatedly and a
    book has many chapters, so the cache is worth having -- but it is keyed by
    character, not by (character, size), because scaling is text.py's job.
    """

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self.path = pathlib.Path(path)
        self._font = TTFont(self.path, lazy=True)
        self.units_per_em: int = self._font["head"].unitsPerEm
        self._glyphs = self._font.getGlyphSet()
        self._cmap = self._font.getBestCmap()

    @classmethod
    def regular(cls) -> OpenTypeGlyphs:
        return cls(font_dir() / "lmroman10-regular.otf")

    @classmethod
    def italic(cls) -> OpenTypeGlyphs:
        return cls(font_dir() / "lmroman10-italic.otf")

    @functools.lru_cache(maxsize=512)  # noqa: B019 -- one instance per face, bounded
    def outline(self, char: str) -> GlyphOutline:
        name = self._cmap.get(ord(char))
        if name is None:
            raise KeyError(char)

        pen = RecordingPen()
        glyph = self._glyphs[name]
        glyph.draw(pen)

        commands: list[PathCommand] = []
        for operator, operands in pen.value:
            if operator == "moveTo":
                commands.append(("m", tuple(map(float, operands[0]))))
            elif operator == "lineTo":
                commands.append(("l", tuple(map(float, operands[0]))))
            elif operator == "curveTo":
                if len(operands) != 3:
                    # A "superbezier": TrueType-shaped, not CFF. Approximating
                    # it here would quietly change letter shapes.
                    raise ValueError(
                        f"glyph {name!r} has a {len(operands)}-point curve; "
                        "this reader expects cubic CFF outlines"
                    )
                flat: list[float] = []
                for point in operands:
                    flat.extend(float(v) for v in point)
                commands.append(("c", tuple(flat)))
            elif operator == "qCurveTo":
                raise ValueError(
                    f"glyph {name!r} is quadratic (TrueType). This program "
                    "loads CFF-flavoured OpenType so outlines stay cubic; "
                    f"check {self.path.name}"
                )
            elif operator == "closePath":
                commands.append(("h", ()))
            elif operator == "endPath":
                pass  # an open contour; nothing to emit
            else:  # pragma: no cover - fontTools would have to grow an operator
                raise ValueError(f"unexpected pen operator {operator!r}")

        return GlyphOutline(advance=float(glyph.width), commands=tuple(commands))
