"""The page-slot model. These invariants ARE the specification.

Every assertion here is a fact about paper. Getting one wrong produces a PDF
that looks plausible on screen and is wrong in the hand -- notes on the wrong
side, a chapter opening on a left-hand page, a page with nowhere to write.

The layout of one chapter, N source pages:

    side 1  recto   portrait
    side 2  verso   mini-TOC
    side 3  recto   notes          <- faces the mini-TOC: plan the chapter
    side 4  verso   source page 1
    side 5  recto   notes
    ...
    side 2N+2  verso  source page N
    side 2N+3  recto  notes
    side 2N+4  verso  blank        <- parity, so the next portrait is a recto

4 + 2N sides. The mini-TOC costs a sheet, because landing on side 2 obliges
side 3 to be its facing page; that was measured wrong once and is the reason
test_every_content_page_faces_a_notes_page exists.
"""

import pytest

from core.plan import Chapter, NotesMode, SideKind, TocEntry, plan_sides


def chapter(number: int, first: int, last: int) -> Chapter:
    return Chapter(
        number=number,
        title=f"Chapter {number}",
        first_page=first,
        last_page=last,
        toc=(TocEntry("A section", first),),
    )


# --- the shape of one chapter ----------------------------------------------


def test_one_chapter_of_one_page_is_six_sides():
    sides = plan_sides([chapter(1, 1, 1)], notes=NotesMode.DOTS)
    assert [s.kind for s in sides] == [
        SideKind.PORTRAIT,
        SideKind.MINI_TOC,
        SideKind.NOTES,
        SideKind.CONTENT,
        SideKind.NOTES,
        SideKind.BLANK,
    ]


@pytest.mark.parametrize("page_count", [1, 2, 3, 7, 18])
def test_sides_per_chapter_is_four_plus_twice_the_page_count(page_count):
    sides = plan_sides([chapter(1, 1, page_count)], notes=NotesMode.DOTS)
    assert len(sides) == 4 + 2 * page_count


def test_the_parity_side_is_the_last_side_of_the_chapter():
    sides = plan_sides([chapter(1, 1, 3)], notes=NotesMode.DOTS)
    assert sides[-1].kind is SideKind.BLANK


# --- the four invariants ----------------------------------------------------


def test_every_portrait_is_on_a_recto():
    sides = plan_sides(
        [chapter(1, 1, 3), chapter(2, 4, 5), chapter(3, 6, 6)], notes=NotesMode.DOTS
    )
    portraits = [s for s in sides if s.kind is SideKind.PORTRAIT]
    assert len(portraits) == 3
    assert all(s.is_recto for s in portraits), [s.index for s in portraits]


def test_every_content_page_is_on_a_verso():
    sides = plan_sides([chapter(1, 1, 4), chapter(2, 5, 7)], notes=NotesMode.DOTS)
    content = [s for s in sides if s.kind is SideKind.CONTENT]
    assert content
    assert not any(s.is_recto for s in content), [s.index for s in content]


def test_every_content_page_faces_a_notes_page():
    # The invariant that caught the 2+2N arithmetic error: with the mini-TOC on
    # side 2 and no extra parity page, the LAST content page of every chapter
    # faced the next chapter's portrait instead of a notes page.
    sides = plan_sides([chapter(1, 1, 3), chapter(2, 4, 5)], notes=NotesMode.DOTS)
    by_index = {s.index: s for s in sides}

    for side in sides:
        if side.kind is not SideKind.CONTENT:
            continue
        facing = by_index.get(side.index + 1)
        assert facing is not None, f"content side {side.index} faces nothing"
        assert facing.kind is SideKind.NOTES, (
            f"content side {side.index} (source page {side.source_page}) faces "
            f"{facing.kind} instead of a notes page"
        )


def test_the_mini_toc_faces_a_notes_page():
    sides = plan_sides([chapter(1, 1, 2)], notes=NotesMode.DOTS)
    by_index = {s.index: s for s in sides}
    toc = next(s for s in sides if s.kind is SideKind.MINI_TOC)
    assert by_index[toc.index + 1].kind is SideKind.NOTES


def test_source_pages_appear_exactly_once_and_in_order():
    sides = plan_sides(
        [chapter(1, 1, 3), chapter(2, 4, 6), chapter(3, 7, 9)], notes=NotesMode.DOTS
    )
    pages = [s.source_page for s in sides if s.kind is SideKind.CONTENT]
    assert pages == list(range(1, 10))


def test_only_content_sides_carry_a_source_page():
    sides = plan_sides([chapter(1, 1, 2)], notes=NotesMode.DOTS)
    for side in sides:
        if side.kind is SideKind.CONTENT:
            assert side.source_page is not None
        else:
            assert side.source_page is None, f"{side.kind} carries a source page"


# --- indices, parity, gutter ------------------------------------------------


def test_side_indices_are_contiguous_from_one():
    sides = plan_sides([chapter(1, 1, 2), chapter(2, 3, 4)], notes=NotesMode.DOTS)
    assert [s.index for s in sides] == list(range(1, len(sides) + 1))


def test_recto_is_odd_and_verso_is_even():
    sides = plan_sides([chapter(1, 1, 2)], notes=NotesMode.DOTS)
    for side in sides:
        assert side.is_recto == (side.index % 2 == 1)


def test_the_gutter_is_on_the_left_of_a_recto_and_the_right_of_a_verso():
    # Flip a sheet bound on its left edge and the holes move to the other
    # side. Backwards, this puts the gutter in the outer margin: it looks fine
    # and reads wrong, because the binding then eats the text.
    sides = plan_sides([chapter(1, 1, 2)], notes=NotesMode.DOTS)
    for side in sides:
        assert side.gutter_edge == ("left" if side.is_recto else "right")


def test_every_side_knows_its_chapter():
    sides = plan_sides([chapter(1, 1, 2), chapter(2, 3, 3)], notes=NotesMode.DOTS)
    assert {s.chapter for s in sides} == {1, 2}
    assert all(s.chapter == 1 for s in sides[:6])


def test_a_second_chapter_starts_where_the_first_ended():
    first = plan_sides([chapter(1, 1, 3)], notes=NotesMode.DOTS)
    both = plan_sides([chapter(1, 1, 3), chapter(2, 4, 5)], notes=NotesMode.DOTS)
    assert len(first) == 10
    assert both[:10] == first
    assert both[10].kind is SideKind.PORTRAIT
    assert both[10].index == 11
    assert len(both) == 18


# --- notes = none: the plain chapter print ---------------------------------


def test_notes_none_emits_no_notes_pages():
    sides = plan_sides([chapter(1, 1, 4)], notes=NotesMode.NONE)
    assert not any(s.kind is SideKind.NOTES for s in sides)


def test_notes_none_still_opens_every_chapter_on_a_recto():
    sides = plan_sides(
        [chapter(1, 1, 3), chapter(2, 4, 4), chapter(3, 5, 8)], notes=NotesMode.NONE
    )
    portraits = [s for s in sides if s.kind is SideKind.PORTRAIT]
    assert len(portraits) == 3
    assert all(s.is_recto for s in portraits), [s.index for s in portraits]


def test_notes_none_prints_content_on_both_sides_of_the_sheet():
    # The point of the mode: no facing blanks, so content uses both sides.
    sides = plan_sides([chapter(1, 1, 4)], notes=NotesMode.NONE)
    content = [s for s in sides if s.kind is SideKind.CONTENT]
    assert any(s.is_recto for s in content)
    assert any(not s.is_recto for s in content)


def test_notes_none_keeps_every_source_page_exactly_once():
    sides = plan_sides([chapter(1, 1, 3), chapter(2, 4, 6)], notes=NotesMode.NONE)
    pages = [s.source_page for s in sides if s.kind is SideKind.CONTENT]
    assert pages == [1, 2, 3, 4, 5, 6]


# --- rejected input --------------------------------------------------------


def test_an_inverted_page_range_is_rejected():
    with pytest.raises(ValueError):
        plan_sides(
            [Chapter(number=1, title="x", first_page=9, last_page=4)],
            notes=NotesMode.DOTS,
        )


def test_a_page_range_below_one_is_rejected():
    # Source pages are 1-based everywhere, because that is what a reader types.
    with pytest.raises(ValueError):
        plan_sides(
            [Chapter(number=1, title="x", first_page=0, last_page=4)],
            notes=NotesMode.DOTS,
        )


def test_overlapping_chapters_are_rejected():
    # Two chapters claiming the same page means the outline was misread; it
    # would silently print that page twice.
    with pytest.raises(ValueError):
        plan_sides([chapter(1, 1, 5), chapter(2, 4, 8)], notes=NotesMode.DOTS)


def test_no_chapters_is_rejected():
    with pytest.raises(ValueError):
        plan_sides([], notes=NotesMode.DOTS)


def test_chapter_knows_its_page_count():
    assert chapter(1, 27, 44).page_count == 18
