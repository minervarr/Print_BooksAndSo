"""One side of one sheet: first as layout, then as a content stream.

Rendering is two steps on purpose.

`layout_side()` returns DATA -- strings, coordinates, sizes, flags. `emit()`
turns that into PDF operators. The split exists because text here is drawn as
glyph outlines: a finished stream is a few hundred path operators and cannot be
searched for the string "CHAPTER ONE". Layout can be asserted directly, and it
is also the natural thing for the C++ port's golden tests to diff -- a
disagreement names the run that moved instead of reporting that two PDFs
differ.

Pure: no PDF library, no font file, no I/O. The font arrives as a GlyphSource.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core import units
from core.drawing import center_ticks, dot_grid, registration_tick
from core.geometry import Placement, Rect, Size, content_area, fit
from core.metrics import GlyphSource
from core.numwords import ordinal_words
from core.pdfops import num
from core.plan import Chapter, NotesMode, Side, SideKind
from core.text import draw_text, text_width, wrap_text

#: The separator between book title and author on a portrait footer.
MIDDOT = "·"


@dataclass(frozen=True, slots=True)
class Layout:
    """The sheet and what is reserved around its edges."""

    paper: Size
    margin: float
    gutter: float


@dataclass(frozen=True, slots=True)
class GridSpec:
    """The notes-page dot grid.

    0.25 mm is a floor, not a preference: below about 0.2 mm most printers drop
    the dot entirely and the page comes out blank.
    """

    pitch: float = field(default_factory=lambda: units.mm(5.0))
    dot: float = field(default_factory=lambda: units.mm(0.25))
    ink: float = 0.25


@dataclass(frozen=True, slots=True)
class Style:
    """Type sizes and weights for the furniture. Points throughout."""

    kicker_size: float = 11.0
    kicker_tracking: float = 1.6
    kicker_ink: float = 1.0
    rule_width: float = 0.4
    rule_ink: float = 1.0
    title_size: float = 24.0
    title_leading: float = 1.18
    title_lines: int = 2
    footer_size: float = 8.5
    footer_ink: float = 0.6
    toc_size: float = 10.0
    toc_leading: float = 1.8
    toc_ink: float = 0.85
    toc_indent: float = 14.0
    tick_length: float = field(default_factory=lambda: units.mm(3.0))
    tick_width: float = 0.3
    tick_ink: float = 0.4
    reg_size: float = field(default_factory=lambda: units.mm(2.0))
    reg_width: float = 0.3
    reg_ink: float = 0.9


@dataclass(frozen=True, slots=True)
class BookInfo:
    """What the portrait footer can say. Either field may be empty."""

    title: str = ""
    author: str = ""


@dataclass(frozen=True, slots=True)
class TextRun:
    """One run of text on a baseline, already positioned."""

    text: str
    x: float
    y: float
    size: float
    ink: float = 1.0
    tracking: float = 0.0
    italic: bool = False


@dataclass(frozen=True, slots=True)
class Rule:
    """A horizontal hairline."""

    x0: float
    y: float
    x1: float
    width: float
    ink: float


@dataclass(frozen=True, slots=True)
class SideLayout:
    """Everything that goes on one side, as data."""

    side: Side
    box: Rect
    texts: tuple[TextRun, ...] = ()
    rules: tuple[Rule, ...] = ()
    grid: bool = False
    ticks: bool = False
    registration: str | None = None
    content: Placement | None = None


class Renderer:
    def __init__(
        self,
        *,
        layout: Layout,
        grid: GridSpec,
        style: Style,
        book: BookInfo,
        roman: GlyphSource,
        italic: GlyphSource,
        notes: NotesMode,
    ) -> None:
        self.layout = layout
        self.grid = grid
        self.style = style
        self.book = book
        self.roman = roman
        self.italic = italic
        self.notes = notes

    # --- geometry ----------------------------------------------------------

    def box_for(self, side: Side) -> Rect:
        """The drawable box for `side`, with the gutter on its binding edge."""
        return content_area(
            self.layout.paper,
            margin=self.layout.margin,
            gutter=self.layout.gutter,
            gutter_edge=side.gutter_edge,
        )

    def _outer_corner(self, side: Side) -> str:
        """The corner away from the binding, for the registration mark."""
        return "bottom-right" if side.is_recto else "bottom-left"

    # --- layout ------------------------------------------------------------

    def layout_side(
        self,
        side: Side,
        chapter: Chapter | None = None,
        *,
        page_box: Rect | None = None,
        facing_page: int | None = None,
    ) -> SideLayout:
        box = self.box_for(side)

        if side.kind is SideKind.PORTRAIT:
            return self._portrait(side, box, chapter)
        if side.kind is SideKind.MINI_TOC:
            return self._mini_toc(side, box, chapter)
        if side.kind is SideKind.NOTES:
            return self._notes(side, box, chapter, facing_page)
        if side.kind is SideKind.CONTENT:
            return self._content(side, box, page_box)
        if side.kind is SideKind.BLANK:
            return SideLayout(
                side=side, box=box, registration=self._outer_corner(side)
            )
        raise ValueError(f"no layout for side kind {side.kind}")

    def _portrait(self, side: Side, box: Rect, chapter: Chapter | None) -> SideLayout:
        if chapter is None:
            raise ValueError("a portrait needs its chapter")
        st = self.style
        texts: list[TextRun] = []

        kicker_y = box.y1 - 0.16 * box.height
        texts.append(
            TextRun(
                text=f"CHAPTER {ordinal_words(chapter.number).upper()}",
                x=box.x0,
                y=kicker_y,
                size=st.kicker_size,
                ink=st.kicker_ink,
                tracking=st.kicker_tracking,
            )
        )

        rule_y = kicker_y - st.kicker_size * 0.62
        rules = (Rule(box.x0, rule_y, box.x1, st.rule_width, st.rule_ink),)

        # Ragged right from the left margin: the LaTeX chapter head sets the
        # title flush left and lets the right edge fall where it will.
        lines = wrap_text(
            self.roman,
            chapter.title,
            size=st.title_size,
            max_width=box.width,
            max_lines=st.title_lines,
        )
        baseline = rule_y - st.title_size * 1.45
        for line in lines:
            texts.append(
                TextRun(text=line, x=box.x0, y=baseline, size=st.title_size)
            )
            baseline -= st.title_size * st.title_leading

        # Footer: identity, then the page range. Either may be absent, and an
        # absent one must not leave a dangling separator behind.
        identity = MIDDOT.join(
            part for part in (self.book.title.strip(), self.book.author.strip()) if part
        ).replace(MIDDOT, f" {MIDDOT} ")
        footer_y = box.y0 + st.footer_size * 3.2
        if identity:
            texts.append(
                self._centred(
                    identity, box, footer_y, st.footer_size, st.footer_ink, italic=True
                )
            )
        texts.append(
            self._centred(
                f"pp. {chapter.first_page}–{chapter.last_page}",
                box,
                footer_y - st.footer_size * 1.6,
                st.footer_size,
                st.footer_ink,
                italic=True,
            )
        )

        return SideLayout(side=side, box=box, texts=tuple(texts), rules=rules)

    def _mini_toc(self, side: Side, box: Rect, chapter: Chapter | None) -> SideLayout:
        if chapter is None:
            raise ValueError("a mini-TOC needs its chapter")
        st = self.style

        # Most PDFs have a flat outline with nothing below chapter level. An
        # empty page there is a wasted sheet, so it becomes notes paper.
        if not chapter.toc:
            return self._notes(side, box, chapter, facing_page=None)

        texts: list[TextRun] = [
            TextRun(
                text="IN THIS CHAPTER",
                x=box.x0,
                y=box.y1 - st.kicker_size,
                size=st.kicker_size,
                ink=st.kicker_ink,
                tracking=st.kicker_tracking,
            )
        ]
        rules = (
            Rule(
                box.x0,
                box.y1 - st.kicker_size * 1.62,
                box.x1,
                st.rule_width,
                st.rule_ink,
            ),
        )

        baseline = box.y1 - st.kicker_size * 1.62 - st.toc_size * 2.0
        for entry in chapter.toc:
            texts.append(
                TextRun(
                    text=entry.title,
                    x=box.x0 + entry.depth * st.toc_indent,
                    y=baseline,
                    size=st.toc_size,
                    ink=st.toc_ink,
                )
            )
            page = str(entry.page)
            width = text_width(self.roman, page, size=st.toc_size)
            texts.append(
                TextRun(
                    text=page,
                    x=box.x1 - width,
                    y=baseline,
                    size=st.toc_size,
                    ink=st.toc_ink,
                )
            )
            baseline -= st.toc_size * st.toc_leading

        return SideLayout(
            side=side,
            box=box,
            texts=tuple(texts),
            rules=rules,
            registration=self._outer_corner(side),
        )

    def _notes(
        self,
        side: Side,
        box: Rect,
        chapter: Chapter | None,
        facing_page: int | None,
    ) -> SideLayout:
        st = self.style
        texts: list[TextRun] = []

        if chapter is not None and facing_page is not None:
            label = f"Ch. {chapter.number} {MIDDOT} p. {facing_page}"
            width = text_width(self.italic, label, size=st.footer_size * 0.85)
            # The OUTER edge, away from the binding: a footer against the
            # gutter disappears into the spiral.
            x = box.x1 - width if side.is_recto else box.x0
            texts.append(
                TextRun(
                    text=label,
                    x=x,
                    y=box.y0 - st.footer_size * 0.9,
                    size=st.footer_size * 0.85,
                    ink=0.45,
                    italic=True,
                )
            )

        return SideLayout(
            side=side,
            box=box,
            texts=tuple(texts),
            grid=self.notes is NotesMode.DOTS,
            ticks=self.notes in (NotesMode.DOTS, NotesMode.LINES, NotesMode.BLANK),
            registration=self._outer_corner(side),
        )

    def _content(
        self, side: Side, box: Rect, page_box: Rect | None
    ) -> SideLayout:
        placement = fit(page_box, box) if page_box is not None else None
        return SideLayout(
            side=side,
            box=box,
            registration=self._outer_corner(side),
            content=placement,
        )

    def _centred(
        self,
        text: str,
        box: Rect,
        y: float,
        size: float,
        ink: float,
        *,
        italic: bool,
    ) -> TextRun:
        source = self.italic if italic else self.roman
        width = text_width(source, text, size=size)
        return TextRun(
            text=text,
            x=box.x0 + (box.width - width) / 2.0,
            y=y,
            size=size,
            ink=ink,
            italic=italic,
        )

    # --- emit --------------------------------------------------------------

    def emit(self, sl: SideLayout) -> str:
        """`sl` as PDF content-stream operators.

        Mechanical: every decision was already made in layout_side().
        """
        st = self.style
        parts: list[str] = []

        if sl.grid:
            parts.append(
                dot_grid(
                    sl.box, pitch=self.grid.pitch, dot=self.grid.dot, ink=self.grid.ink
                )
            )
        if sl.ticks:
            parts.append(
                center_ticks(
                    sl.box,
                    length=st.tick_length,
                    width=st.tick_width,
                    ink=st.tick_ink,
                )
            )
        if sl.registration is not None:
            parts.append(
                registration_tick(
                    sl.box,
                    corner=sl.registration,
                    size=st.reg_size,
                    width=st.reg_width,
                    ink=st.reg_ink,
                )
            )
        for rule in sl.rules:
            parts.append(self._rule_stream(rule))
        for run in sl.texts:
            source = self.italic if run.italic else self.roman
            parts.append(
                draw_text(
                    source,
                    run.text,
                    x=run.x,
                    y=run.y,
                    size=run.size,
                    ink=run.ink,
                    tracking=run.tracking,
                )
            )

        return "\n".join(part for part in parts if part)

    def _rule_stream(self, rule: Rule) -> str:
        return "\n".join(
            [
                "q",
                f"{num(1.0 - rule.ink)} G",
                f"{num(rule.width)} w",
                "0 J",
                f"{num(rule.x0)} {num(rule.y)} m {num(rule.x1)} {num(rule.y)} l",
                "S",
                "Q",
            ]
        )

    def place_form(self, name: str, placement: Placement | None) -> str:
        """Draw an imported source page at `placement`.

        The XObject NAME belongs to the backend -- core never learns what a
        PDF object is -- but the operators are text, so they are generated
        here with everything else.
        """
        if placement is None:
            raise ValueError("cannot place a form without a placement")
        return "\n".join(
            [
                "q",
                f"{num(placement.scale)} 0 0 {num(placement.scale)} "
                f"{num(placement.dx)} {num(placement.dy)} cm",
                f"{name} Do",
                "Q",
            ]
        )
