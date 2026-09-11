"""The page-slot model: a book and a notes mode become an ordered list of sides.

The unit here is a SIDE of a sheet, not a page, because everything that can go
wrong in this program is a parity error. A portrait on a left-hand page, notes
on the wrong side of the spread, a content page with nowhere to write beside
it -- each looks plausible on screen and is wrong in the hand.

One chapter of N source pages, interleaved:

    side 1     recto   portrait
    side 2     verso   mini-TOC
    side 3     recto   notes            faces the mini-TOC: plan the chapter
    side 4     verso   source page 1
    side 5     recto   notes
    ...
    side 2N+2  verso   source page N
    side 2N+3  recto   notes
    side 2N+4  verso   blank            parity: the next portrait is a recto

4 + 2N sides. This was first designed as 2 + 2N on the belief that the mini-TOC
rode along on the parity side for free. It does not: landing on side 2 obliges
side 3 to be its facing page, so the mini-TOC costs a sheet per chapter rather
than nothing. The error was invisible in every rule except one -- the LAST
content page of each chapter faced the next chapter's portrait instead of a
notes page -- which is now asserted directly in
test_every_content_page_faces_a_notes_page.

Pure: no PDF library, no I/O, no drawing. It decides what goes where.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal

GutterEdge = Literal["left", "right"]


class SideKind(StrEnum):
    """What occupies one side of one sheet."""

    PORTRAIT = "portrait"
    MINI_TOC = "mini_toc"
    CONTENT = "content"
    NOTES = "notes"
    BLANK = "blank"


class NotesMode(StrEnum):
    """What a notes page carries -- or whether there are notes pages at all.

    NONE is the "just print the chapter" mode: no facing pages, content on both
    sides of every sheet. It is not a special case in the code, only a
    different plan through the same engine.
    """

    DOTS = "dots"
    LINES = "lines"
    BLANK = "blank"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class TocEntry:
    """One line of a chapter's mini-TOC."""

    title: str
    page: int
    depth: int = 0


@dataclass(frozen=True, slots=True)
class Chapter:
    """A run of source pages, 1-based and inclusive at both ends.

    1-based because that is what a reader types into the project TOML, and
    converting at the boundary is cheaper than remembering which convention
    applies where.
    """

    number: int
    title: str
    first_page: int
    last_page: int
    toc: tuple[TocEntry, ...] = field(default_factory=tuple)

    @property
    def page_count(self) -> int:
        return self.last_page - self.first_page + 1

    def pages(self) -> range:
        return range(self.first_page, self.last_page + 1)


@dataclass(frozen=True, slots=True)
class Side:
    """One side of one sheet, at a 1-based physical position."""

    index: int
    kind: SideKind
    chapter: int
    source_page: int | None = None

    @property
    def is_recto(self) -> bool:
        """Odd sides are rectos -- the right-hand page of an opened spread."""
        return self.index % 2 == 1

    @property
    def gutter_edge(self) -> GutterEdge:
        """Which edge the binding is on for this side.

        A recto's binding edge is its left; a verso's is its right. Flip a
        sheet bound on the left and the holes move to the other side. Backwards
        this puts the gutter in the outer margin, which looks fine and lets the
        binding eat the text.
        """
        return "left" if self.is_recto else "right"


def _validate(chapters: Sequence[Chapter]) -> None:
    if not chapters:
        raise ValueError("no chapters to plan")

    for ch in chapters:
        if ch.first_page < 1:
            raise ValueError(
                f"chapter {ch.number} starts at page {ch.first_page}; source "
                "pages are 1-based"
            )
        if ch.last_page < ch.first_page:
            raise ValueError(
                f"chapter {ch.number} runs {ch.first_page}..{ch.last_page}, "
                "which is backwards"
            )

    # Overlap means the outline was misread, and the symptom would be a page
    # silently printed twice rather than an error.
    seen: dict[int, int] = {}
    for ch in chapters:
        for page in ch.pages():
            if page in seen:
                raise ValueError(
                    f"source page {page} is claimed by chapter {seen[page]} "
                    f"and chapter {ch.number}"
                )
            seen[page] = ch.number


def plan_sides(
    chapters: Sequence[Chapter], *, notes: NotesMode
) -> tuple[Side, ...]:
    """Lay the chapters out as an ordered list of sides.

    Every chapter occupies an even number of sides, which is what keeps the
    next chapter's portrait on a recto without the caller tracking parity.
    """
    _validate(chapters)

    sides: list[Side] = []
    index = 1

    def emit(kind: SideKind, chapter: int, source_page: int | None = None) -> None:
        nonlocal index
        sides.append(Side(index, kind, chapter, source_page))
        index += 1

    for ch in chapters:
        emit(SideKind.PORTRAIT, ch.number)
        emit(SideKind.MINI_TOC, ch.number)

        if notes is NotesMode.NONE:
            for page in ch.pages():
                emit(SideKind.CONTENT, ch.number, page)
        else:
            # The mini-TOC's facing page: a notes page to plan the chapter on.
            emit(SideKind.NOTES, ch.number)
            for page in ch.pages():
                emit(SideKind.CONTENT, ch.number, page)
                emit(SideKind.NOTES, ch.number)

        # Parity. An odd run so far would put the next portrait on a verso.
        if len(sides) % 2 == 1:
            emit(SideKind.BLANK, ch.number)

    return tuple(sides)
