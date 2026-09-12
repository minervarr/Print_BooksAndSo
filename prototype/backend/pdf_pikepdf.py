"""The only file that knows what a PDF object is.

Two jobs, probe and emit, and between them core/ does all the deciding.

  probe()  reads a source book into plain data: page boxes, the outline tree,
           metadata. Nothing PDF-shaped crosses back into core/.
  emit()   assembles the output: one page per side, each source page imported
           as a Form XObject and PLACED rather than decoded.

Nothing is ever rendered. A source page's content is referenced by object, so
the cost of a 400-page book is qpdf's object copy -- the same C++ the port will
call directly. The dot grid is written once as a shared Form XObject and
referenced from every notes page; there are exactly two of them, one per gutter
edge, however many pages a book has.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
import pathlib

import pikepdf

from core.geometry import Rect
from core.plan import Chapter, NotesMode, Side, SideKind, TocEntry
from core.render import Renderer


@dataclass(frozen=True, slots=True)
class SourcePage:
    """One page of the source book, 1-based."""

    number: int
    media_box: Rect
    crop_box: Rect
    rotate: int


@dataclass(frozen=True, slots=True)
class OutlineItem:
    """One entry of the source outline, flattened with its depth."""

    title: str
    page: int
    depth: int


@dataclass(frozen=True, slots=True)
class SourceBook:
    """A source PDF as plain data. No pikepdf objects survive in here."""

    path: pathlib.Path
    pages: tuple[SourcePage, ...] = ()
    outline: tuple[OutlineItem, ...] = ()
    title: str = ""
    author: str = ""

    @property
    def page_count(self) -> int:
        return len(self.pages)


def _rect(obj, fallback: Rect) -> Rect:
    if obj is None:
        return fallback
    values = [float(v) for v in obj]
    # A /MediaBox is not guaranteed to be written lower-left first.
    x0, x1 = sorted((values[0], values[2]))
    y0, y1 = sorted((values[1], values[3]))
    return Rect(x0, y0, x1, y1)


def _metadata(pdf: pikepdf.Pdf) -> tuple[str, str]:
    """Title and author, XMP first, then the /Info dictionary.

    XMP is the modern one and wins where both exist. Either may be absent,
    which is the common case rather than an error -- the portrait footer
    degrades instead of printing a gap.

    /Info is snapshotted BEFORE open_metadata(): pikepdf's open_metadata()
    migrates /Info into XMP when the context closes, removing /Title from the
    /Info dictionary, so reading it after the fact always sees nothing.
    """
    info = pdf.docinfo
    info_title = str(info["/Title"]) if "/Title" in info else ""
    info_author = str(info["/Author"]) if "/Author" in info else ""

    title = author = ""
    try:
        with pdf.open_metadata() as meta:
            title = str(meta.get("dc:title", "") or "")
            creator = meta.get("dc:creator", "") or ""
            author = ", ".join(creator) if isinstance(creator, list) else str(creator)
    except Exception:  # noqa: BLE001 - malformed XMP is common and not fatal
        pass

    if not title:
        title = info_title
    if not author:
        author = info_author
    return title.strip(), author.strip()


def _outline(pdf: pikepdf.Pdf) -> tuple[OutlineItem, ...]:
    """The outline tree, flattened to (title, 1-based page, depth).

    An outline entry can point at a destination this reader cannot resolve --
    a named destination into a damaged file, most often. Those are skipped
    rather than fatal: a partial outline still beats typing page ranges by
    hand, and "no outline" is a supported case anyway.
    """
    page_index = {page.obj.objgen: n for n, page in enumerate(pdf.pages, start=1)}
    items: list[OutlineItem] = []

    def walk(entries, depth: int) -> None:
        for entry in entries:
            number = None
            try:
                target = entry.destination
                if isinstance(target, pikepdf.Array) and len(target) > 0:
                    number = page_index.get(target[0].objgen)
                elif entry.action is not None:
                    dest = entry.action.get("/D")
                    if isinstance(dest, pikepdf.Array) and len(dest) > 0:
                        number = page_index.get(dest[0].objgen)
            except Exception:  # noqa: BLE001 - unresolvable destination
                number = None

            if number is not None:
                items.append(OutlineItem(str(entry.title), number, depth))
            walk(entry.children, depth + 1)

    with pdf.open_outline() as outline:
        walk(outline.root, 0)
    return tuple(items)


def probe(path: str | pathlib.Path) -> SourceBook:
    """Read `path` into plain data for core/ to plan against."""
    path = pathlib.Path(path)
    with pikepdf.open(path) as pdf:
        pages: list[SourcePage] = []
        for number, page in enumerate(pdf.pages, start=1):
            media = _rect(page.obj.get("/MediaBox"), Rect(0.0, 0.0, 612.0, 792.0))
            crop = _rect(page.obj.get("/CropBox"), media)
            rotate = int(page.obj.get("/Rotate", 0) or 0) % 360
            pages.append(SourcePage(number, media, crop, rotate))

        title, author = _metadata(pdf)
        outline = _outline(pdf)

    return SourceBook(
        path=path,
        pages=tuple(pages),
        outline=outline,
        title=title,
        author=author,
    )


class _Emitter:
    """Builds the output document. One instance per output file."""

    def __init__(self, source: pikepdf.Pdf, renderer: Renderer) -> None:
        self.source = source
        self.renderer = renderer
        self.out = pikepdf.Pdf.new()
        self._grids: dict[tuple[float, float, float, float], pikepdf.Object] = {}
        self._forms: dict[int, pikepdf.Object] = {}

    def _grid_form(self, box: Rect, stream: str) -> pikepdf.Object:
        """The dot grid as a Form XObject, made once per distinct box.

        A recto and a verso have different boxes because the gutter swaps
        sides, so there are two -- not one per page, and not one per book.
        """
        key = (box.x0, box.y0, box.x1, box.y1)
        if key not in self._grids:
            form = pikepdf.Stream(self.out, stream.encode("ascii"))
            form.Type = pikepdf.Name.XObject
            form.Subtype = pikepdf.Name.Form
            form.BBox = pikepdf.Array([box.x0, box.y0, box.x1, box.y1])
            self._grids[key] = self.out.make_indirect(form)
        return self._grids[key]

    def _page_form(self, number: int) -> pikepdf.Object:
        """A source page imported as a Form XObject, made once per page."""
        if number not in self._forms:
            src = pikepdf.Page(self.source.pages[number - 1])
            self._forms[number] = self.out.copy_foreign(src.as_form_xobject())
        return self._forms[number]

    def add_side(self, side: Side, chapter: Chapter | None) -> None:
        paper = self.renderer.layout.paper
        page = self.out.add_blank_page(page_size=(paper.width, paper.height))

        facing = None
        page_box = None
        if side.kind is SideKind.NOTES:
            facing = self._facing_page
        elif side.kind is SideKind.CONTENT:
            assert side.source_page is not None
            page_box = self.renderer_page_box(side.source_page)

        sl = self.renderer.layout_side(
            side, chapter, page_box=page_box, facing_page=facing
        )

        parts: list[str] = []

        # The source page goes down FIRST, so furniture never hides under it.
        if side.kind is SideKind.CONTENT:
            assert side.source_page is not None
            form = self._page_form(side.source_page)
            name = page.add_resource(form, pikepdf.Name.XObject)
            parts.append(self.renderer.place_form(str(name), sl.content))

        # The grid is a shared XObject rather than inline operators: one copy
        # in the file, referenced from every notes page.
        if sl.grid:
            from core.drawing import dot_grid

            grid = self.renderer.grid
            stream = dot_grid(
                sl.box, pitch=grid.pitch, dot=grid.dot, ink=grid.ink
            )
            form = self._grid_form(sl.box, stream)
            name = page.add_resource(form, pikepdf.Name.XObject)
            parts.append(f"q\n{name} Do\nQ")

        furniture = self.renderer.emit(
            type(sl)(
                side=sl.side,
                box=sl.box,
                texts=sl.texts,
                rules=sl.rules,
                grid=False,          # already placed as an XObject above
                ticks=sl.ticks,
                registration=sl.registration,
                content=None,
            )
        )
        if furniture:
            parts.append(furniture)

        if parts:
            page.contents_add(
                pikepdf.Stream(self.out, "\n".join(parts).encode("ascii"))
            )

    # set by emit() before each notes side
    _facing_page: int | None = None
    _page_boxes: dict[int, Rect] = {}

    def renderer_page_box(self, number: int) -> Rect:
        return self._page_boxes[number]


def emit(
    book: SourceBook,
    chapters: Sequence[Chapter],
    sides: Sequence[Side],
    renderer: Renderer,
    output: str | pathlib.Path,
    *,
    crop: Rect | None = None,
) -> pathlib.Path:
    """Write the planned sides to `output`.

    `crop` is the box of each source page to show -- ONE box for the whole
    book (see CLAUDE.md on why it is not per page). None means use each page's
    own CropBox.
    """
    output = pathlib.Path(output)
    by_number = {ch.number: ch for ch in chapters}

    with pikepdf.open(book.path) as source:
        em = _Emitter(source, renderer)
        em._page_boxes = {
            page.number: (crop if crop is not None else page.crop_box)
            for page in book.pages
        }

        # A notes page belongs to the content page it faces, which is the side
        # immediately before it.
        for position, side in enumerate(sides):
            if side.kind is SideKind.NOTES and position > 0:
                previous = sides[position - 1]
                em._facing_page = (
                    previous.source_page
                    if previous.kind is SideKind.CONTENT
                    else None
                )
            else:
                em._facing_page = None
            em.add_side(side, by_number.get(side.chapter))

        em.out.save(output, linearize=False)

    return output


def chapters_from_outline(
    book: SourceBook, *, min_gap: int = 1
) -> tuple[Chapter, ...]:
    """Top-level outline entries as chapters, with their sub-entries as TOC.

    A chapter runs from its own first page to the page before the next
    chapter's -- the outline states where things START and never where they
    end, so the end is always inferred.
    """
    tops = [item for item in book.outline if item.depth == 0]
    if not tops:
        return ()

    chapters: list[Chapter] = []
    for position, top in enumerate(tops):
        first = top.page
        last = (
            tops[position + 1].page - 1
            if position + 1 < len(tops)
            else book.page_count
        )
        if last < first:
            continue
        if last - first + 1 < min_gap:
            continue

        toc = tuple(
            TocEntry(item.title, item.page, depth=item.depth - 1)
            for item in book.outline
            if item.depth > 0 and first <= item.page <= last
        )
        chapters.append(
            Chapter(
                number=len(chapters) + 1,
                title=top.title,
                first_page=first,
                last_page=last,
                toc=toc,
            )
        )
    return tuple(chapters)
