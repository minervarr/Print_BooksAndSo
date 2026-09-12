"""Side layout: what goes where on one side of one sheet.

Rendering happens in two steps and this file tests the first one. Text is drawn
as glyph outlines, so a finished content stream cannot be searched for the
string "CHAPTER ONE" -- it is a few hundred path operators. Layout is therefore
pure data: strings and coordinates, assertable, and exactly what the C++
golden tests will diff against.
"""

import pytest

from core import units
from core.geometry import Rect, paper
from core.metrics import GlyphOutline
from core.plan import Chapter, NotesMode, SideKind, TocEntry, plan_sides
from core.render import BookInfo, GridSpec, Layout, Renderer, Style


class FixedWidthFont:
    units_per_em = 1000

    def outline(self, char: str) -> GlyphOutline:
        return GlyphOutline(advance=500.0, commands=(("m", (0.0, 0.0)), ("h", ())))


CHAPTER = Chapter(
    number=1,
    title="The Mechanism of Habit Formation",
    first_page=27,
    last_page=44,
    toc=(
        TocEntry("Cues and cravings", 28),
        TocEntry("The two-minute rule", 35, depth=1),
    ),
)


def renderer(**overrides) -> Renderer:
    font = FixedWidthFont()
    kwargs = dict(
        layout=Layout(
            paper=paper("a4"), margin=units.mm(15.0), gutter=units.mm(10.0)
        ),
        grid=GridSpec(),
        style=Style(),
        book=BookInfo(title="Atomic Habits", author="James Clear"),
        roman=font,
        italic=font,
        notes=NotesMode.DOTS,
    )
    kwargs.update(overrides)
    return Renderer(**kwargs)


def sides():
    return plan_sides([CHAPTER], notes=NotesMode.DOTS)


def layout_of(kind: SideKind):
    r = renderer()
    side = next(s for s in sides() if s.kind is kind)
    return r, side, r.layout_side(side, CHAPTER)


# --- the box ---------------------------------------------------------------


def test_a_recto_takes_its_gutter_from_the_left():
    r = renderer()
    portrait = next(s for s in sides() if s.kind is SideKind.PORTRAIT)
    assert portrait.is_recto
    box = r.box_for(portrait)
    assert box.x0 == pytest.approx(units.mm(25.0))
    assert box.x1 == pytest.approx(units.mm(195.0))


def test_a_verso_takes_its_gutter_from_the_right():
    r = renderer()
    content = next(s for s in sides() if s.kind is SideKind.CONTENT)
    assert not content.is_recto
    box = r.box_for(content)
    assert box.x0 == pytest.approx(units.mm(15.0))
    assert box.x1 == pytest.approx(units.mm(185.0))


# --- the portrait ----------------------------------------------------------


def test_the_portrait_kicker_spells_the_chapter_number():
    _, _, sl = layout_of(SideKind.PORTRAIT)
    assert sl.texts[0].text == "CHAPTER ONE"


def test_the_portrait_kicker_is_letterspaced():
    _, _, sl = layout_of(SideKind.PORTRAIT)
    assert sl.texts[0].tracking > 0.0


def test_the_portrait_has_exactly_one_hairline_rule():
    _, _, sl = layout_of(SideKind.PORTRAIT)
    assert len(sl.rules) == 1
    assert sl.rules[0].width == pytest.approx(0.4)


def test_the_rule_spans_the_content_width():
    r, side, sl = layout_of(SideKind.PORTRAIT)
    box = r.box_for(side)
    assert sl.rules[0].x0 == pytest.approx(box.x0)
    assert sl.rules[0].x1 == pytest.approx(box.x1)


def test_the_rule_sits_below_the_kicker_and_above_the_title():
    _, _, sl = layout_of(SideKind.PORTRAIT)
    kicker = sl.texts[0]
    title = next(t for t in sl.texts if t.size >= 24.0)
    assert title.y < sl.rules[0].y < kicker.y


def test_the_portrait_title_is_ragged_right_from_the_left_margin():
    r, side, sl = layout_of(SideKind.PORTRAIT)
    box = r.box_for(side)
    titles = [t for t in sl.texts if t.size >= 24.0]
    assert titles
    assert all(t.x == pytest.approx(box.x0) for t in titles)


def test_a_long_portrait_title_wraps_to_two_lines():
    # 31 characters at 500/1000 em and 24 pt is 372 pt; the A4 content width
    # is ~482 pt, so this title fits on one line with the stub font. Force the
    # wrap with a narrower sheet instead of a contrived font.
    r = renderer(
        layout=Layout(paper=paper("a4"), margin=units.mm(60.0), gutter=units.mm(10.0))
    )
    side = next(s for s in sides() if s.kind is SideKind.PORTRAIT)
    sl = r.layout_side(side, CHAPTER)
    titles = [t for t in sl.texts if t.size >= 24.0]
    assert len(titles) == 2
    assert titles[1].y < titles[0].y


def test_the_portrait_footer_names_the_book_and_the_author():
    _, _, sl = layout_of(SideKind.PORTRAIT)
    footers = [t.text for t in sl.texts if t.italic]
    assert any("Atomic Habits" in f and "James Clear" in f for f in footers)


def test_the_portrait_footer_states_the_page_range():
    _, _, sl = layout_of(SideKind.PORTRAIT)
    assert any("27" in t.text and "44" in t.text for t in sl.texts if t.italic)


def test_an_unknown_author_leaves_no_dangling_separator():
    # Metadata is often half-missing. "Atomic Habits ·" with nothing after it
    # looks like a bug, which is what it would be.
    r = renderer(book=BookInfo(title="Atomic Habits", author=""))
    side = next(s for s in sides() if s.kind is SideKind.PORTRAIT)
    sl = r.layout_side(side, CHAPTER)
    for run in sl.texts:
        assert not run.text.strip().endswith("·")
        assert "··" not in run.text


def test_an_unknown_title_and_author_drop_the_footer_line_entirely():
    r = renderer(book=BookInfo(title="", author=""))
    side = next(s for s in sides() if s.kind is SideKind.PORTRAIT)
    sl = r.layout_side(side, CHAPTER)
    # The page range survives; the identity line does not.
    assert any("27" in t.text for t in sl.texts)
    assert not any("Atomic" in t.text for t in sl.texts)


def test_the_portrait_carries_no_dot_grid():
    _, _, sl = layout_of(SideKind.PORTRAIT)
    assert sl.grid is False
    assert sl.ticks is False


# --- the mini-TOC ----------------------------------------------------------


def test_the_mini_toc_lists_its_entries_with_page_numbers():
    _, _, sl = layout_of(SideKind.MINI_TOC)
    texts = [t.text for t in sl.texts]
    assert any("Cues and cravings" in t for t in texts)
    assert any(t.strip() == "28" for t in texts)
    assert any("two-minute" in t for t in texts)


def test_mini_toc_entries_descend_down_the_page():
    _, _, sl = layout_of(SideKind.MINI_TOC)
    entries = [t for t in sl.texts if "Cues" in t.text or "two-minute" in t.text]
    assert len(entries) == 2
    assert entries[0].y > entries[1].y


def test_a_nested_toc_entry_is_indented():
    _, _, sl = layout_of(SideKind.MINI_TOC)
    flat = next(t for t in sl.texts if "Cues" in t.text)
    nested = next(t for t in sl.texts if "two-minute" in t.text)
    assert nested.x > flat.x


def test_page_numbers_are_right_aligned_to_the_content_edge():
    r, side, sl = layout_of(SideKind.MINI_TOC)
    box = r.box_for(side)
    numbers = [t for t in sl.texts if t.text.strip().isdigit()]
    assert numbers
    for run in numbers:
        assert run.x < box.x1
        assert run.x > box.x0 + box.width / 2


def test_a_chapter_with_no_outline_entries_falls_back_to_a_dot_grid():
    # Most PDFs have a flat outline. An empty page here would be a wasted
    # sheet, so the mini-TOC side becomes notes paper instead.
    bare = Chapter(number=1, title="Untitled", first_page=1, last_page=3, toc=())
    r = renderer()
    side = next(s for s in plan_sides([bare], notes=NotesMode.DOTS)
                if s.kind is SideKind.MINI_TOC)
    sl = r.layout_side(side, bare)
    assert sl.grid is True


# --- notes and blanks ------------------------------------------------------


def test_a_notes_side_has_a_grid_ticks_and_a_registration_mark():
    _, _, sl = layout_of(SideKind.NOTES)
    assert sl.grid is True
    assert sl.ticks is True
    assert sl.registration is not None


def test_the_notes_footer_names_the_chapter_and_the_source_page():
    r = renderer()
    side_list = sides()
    # the notes page immediately after the first content page
    content = next(s for s in side_list if s.kind is SideKind.CONTENT)
    notes = side_list[content.index]      # 1-based index -> next element
    assert notes.kind is SideKind.NOTES
    sl = r.layout_side(notes, CHAPTER, facing_page=content.source_page)
    assert any("Ch. 1" in t.text and "27" in t.text for t in sl.texts)


def test_the_notes_footer_sits_on_the_outer_edge_not_the_binding_edge():
    # On a recto the outer edge is the right. A footer against the gutter
    # disappears into the binding.
    r = renderer()
    notes = next(s for s in sides() if s.kind is SideKind.NOTES)
    assert notes.is_recto
    box = r.box_for(notes)
    sl = r.layout_side(notes, CHAPTER, facing_page=27)
    footer = next(t for t in sl.texts if "Ch." in t.text)
    assert footer.x > box.x0 + box.width / 2


def test_notes_mode_blank_still_keeps_the_ticks_but_drops_the_grid():
    r = renderer(notes=NotesMode.BLANK)
    side = next(s for s in sides() if s.kind is SideKind.NOTES)
    sl = r.layout_side(side, CHAPTER)
    assert sl.grid is False
    assert sl.ticks is True


def test_a_blank_parity_side_carries_only_a_registration_mark():
    _, _, sl = layout_of(SideKind.BLANK)
    assert sl.grid is False
    assert sl.ticks is False
    assert sl.texts == ()
    assert sl.registration is not None


# --- content ---------------------------------------------------------------


def test_a_content_side_places_the_source_page_scaled_into_the_box():
    r = renderer()
    side = next(s for s in sides() if s.kind is SideKind.CONTENT)
    page_box = Rect(0.0, 0.0, 396.0, 612.0)      # a trade paperback page
    sl = r.layout_side(side, CHAPTER, page_box=page_box)
    assert sl.content is not None
    assert sl.content.scale > 1.0                # scaled up to use the sheet
    box = r.box_for(side)
    assert sl.content.apply_x(page_box.x0) >= box.x0 - 1e-6
    assert sl.content.apply_x(page_box.x1) <= box.x1 + 1e-6


def test_a_content_side_draws_no_furniture_over_the_page():
    r = renderer()
    side = next(s for s in sides() if s.kind is SideKind.CONTENT)
    sl = r.layout_side(side, CHAPTER, page_box=Rect(0.0, 0.0, 396.0, 612.0))
    assert sl.grid is False
    assert sl.ticks is False


# --- emit ------------------------------------------------------------------


def test_emitting_a_notes_side_produces_a_grid_and_ticks_stream():
    r, side, sl = layout_of(SideKind.NOTES)
    sl = r.layout_side(side, CHAPTER, facing_page=27)
    stream = r.emit(sl)
    assert " m " in stream and "S" in stream
    assert stream.count("q") == stream.count("Q")


def test_emitting_a_blank_side_is_nearly_empty():
    r, side, sl = layout_of(SideKind.BLANK)
    stream = r.emit(sl)
    assert len(stream) < 200, stream


def test_placing_a_form_xobject_emits_a_cm_and_a_do():
    r = renderer()
    side = next(s for s in sides() if s.kind is SideKind.CONTENT)
    sl = r.layout_side(side, CHAPTER, page_box=Rect(0.0, 0.0, 396.0, 612.0))
    stream = r.place_form("/Fx0", sl.content)
    assert "cm" in stream
    assert "/Fx0 Do" in stream
    assert stream.startswith("q") and stream.endswith("Q")
