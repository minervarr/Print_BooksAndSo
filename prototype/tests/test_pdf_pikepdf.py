"""The probe/emit backend, against a synthetic book.

These are backend tests: unlike tests/test_core_purity.py they need pikepdf.
They pin the one behaviour that is easy to get wrong — pikepdf's open_metadata()
migrates /Info into XMP on save, so a probe that reads XMP first and /Info
second silently returns an empty title. That is exactly what this file's first
test guards against.
"""

import pikepdf
import pytest

from backend.pdf_pikepdf import chapters_from_outline, emit, probe
from core.geometry import paper
from core.plan import NotesMode, plan_sides
from core.render import BookInfo, GridSpec, Layout, Renderer, Style
from core import units


def _make_book(path, page_count=4, title="", author=""):
    pdf = pikepdf.new()
    for _ in range(page_count):
        pdf.add_blank_page(page_size=(612.0, 792.0))
    if title:
        pdf.docinfo["/Title"] = title
    if author:
        pdf.docinfo["/Author"] = author
    with pdf.open_outline() as outline:
        outline.root.extend(
            [
                pikepdf.OutlineItem("Chapter One", 0),
                pikepdf.OutlineItem("Chapter Two", 2),
            ]
        )
    pdf.save(path)


def test_probe_reads_title_and_author_from_the_info_dictionary(tmp_path):
    # /Info only, no XMP. Before the fix, open_metadata() migrated /Info into
    # XMP on close and the fallback read an already-emptied /Info, so both
    # fields came back empty.
    book_path = tmp_path / "book.pdf"
    _make_book(book_path, title="The Test Book", author="Test Author")
    book = probe(book_path)
    assert book.title == "The Test Book"
    assert book.author == "Test Author"


def test_probe_reads_the_outline_and_page_count(tmp_path):
    book_path = tmp_path / "book.pdf"
    _make_book(book_path, page_count=4)
    book = probe(book_path)
    assert book.page_count == 4
    assert [(o.title, o.page, o.depth) for o in book.outline] == [
        ("Chapter One", 1, 0),
        ("Chapter Two", 3, 0),
    ]


def test_chapters_from_outline_infers_the_end_from_the_next_start(tmp_path):
    book_path = tmp_path / "book.pdf"
    _make_book(book_path, page_count=5)
    book = probe(book_path)
    chapters = chapters_from_outline(book)
    assert [(c.first_page, c.last_page) for c in chapters] == [(1, 2), (3, 5)]


def test_emit_produces_one_page_per_side(tmp_path):
    book_path = tmp_path / "book.pdf"
    _make_book(book_path, page_count=4)
    book = probe(book_path)
    chapters = chapters_from_outline(book)
    sides = plan_sides(chapters, notes=NotesMode.DOTS)

    from backend.glyphs_fonttools import OpenTypeGlyphs

    renderer = Renderer(
        layout=Layout(paper=paper("a4"), margin=units.mm(15.0), gutter=units.mm(10.0)),
        grid=GridSpec(),
        style=Style(),
        book=BookInfo(title=book.title, author=book.author),
        roman=OpenTypeGlyphs.regular(),
        italic=OpenTypeGlyphs.italic(),
        notes=NotesMode.DOTS,
    )
    out = emit(book, chapters, sides, renderer, tmp_path / "out.pdf")

    with pikepdf.open(out) as pdf:
        assert len(pdf.pages) == len(sides)
