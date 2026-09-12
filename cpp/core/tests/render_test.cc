// render_test.cc — side layout: what goes where on one side of one sheet.
//
// Copyright (C) 2026 nava. AGPLv3 or later; see LICENSE.
#undef NDEBUG
#include <cassert>
#include <cstdio>
#include <string>
#include <vector>

#include "printbooks/geometry.hh"
#include "printbooks/metrics.hh"
#include "printbooks/plan.hh"
#include "printbooks/render.hh"
#include "printbooks/units.hh"

#include "test_util.hh"

using namespace pb;
using pb_test::approx;
using pb_test::ops;

namespace {

// Every glyph 500/1000 em, so at size 10 each character is exactly 5 pt. The
// outline is trivial: one moveto and a closepath, enough to be emitted.
struct FixedWidthFont : GlyphSource {
    int units_per_em() const override { return 1000; }
    GlyphOutline outline(char32_t) const override {
        return GlyphOutline{500.0, {PathCommand{'m', {0.0, 0.0}}, PathCommand{'h', {}}}};
    }
};

const FixedWidthFont kFont;

const Chapter CHAPTER{1, "The Mechanism of Habit Formation", 27, 44,
                      {{"Cues and cravings", 28, 0}, {"The two-minute rule", 35, 1}}};

Renderer renderer() {
    return Renderer(Layout{paper("a4"), mm(15.0), mm(10.0)}, GridSpec{}, Style{},
                    BookInfo{"Atomic Habits", "James Clear"}, &kFont, &kFont, NotesMode::Dots);
}

std::vector<Side> sides() { return plan_sides({CHAPTER}, NotesMode::Dots); }

Side side_of(const std::vector<Side>& ss, SideKind kind) {
    for (const Side& s : ss)
        if (s.kind == kind)
            return s;
    assert(false);
    return ss.front();
}

// --- the box ---------------------------------------------------------------

void test_a_recto_takes_its_gutter_from_the_left() {
    Renderer r = renderer();
    const Side portrait = side_of(sides(), SideKind::Portrait);
    assert(portrait.is_recto());
    const Rect box = r.box_for(portrait);
    assert(approx(box.x0, mm(25.0)));
    assert(approx(box.x1, mm(195.0)));
}

void test_a_verso_takes_its_gutter_from_the_right() {
    Renderer r = renderer();
    const Side content = side_of(sides(), SideKind::Content);
    assert(!content.is_recto());
    const Rect box = r.box_for(content);
    assert(approx(box.x0, mm(15.0)));
    assert(approx(box.x1, mm(185.0)));
}

// --- the portrait ----------------------------------------------------------

void test_the_portrait_kicker_spells_the_chapter_number() {
    Renderer r = renderer();
    const Side portrait = side_of(sides(), SideKind::Portrait);
    const SideLayout sl = r.layout_side(portrait, &CHAPTER);
    assert(sl.texts[0].text == "CHAPTER ONE");
}

void test_the_portrait_kicker_is_letterspaced() {
    Renderer r = renderer();
    const SideLayout sl = r.layout_side(side_of(sides(), SideKind::Portrait), &CHAPTER);
    assert(sl.texts[0].tracking > 0.0);
}

void test_the_portrait_has_exactly_one_hairline_rule() {
    Renderer r = renderer();
    const SideLayout sl = r.layout_side(side_of(sides(), SideKind::Portrait), &CHAPTER);
    assert(sl.rules.size() == 1);
    assert(approx(sl.rules[0].width, 0.4));
}

void test_the_rule_spans_the_content_width() {
    Renderer r = renderer();
    const Side portrait = side_of(sides(), SideKind::Portrait);
    const Rect box = r.box_for(portrait);
    const SideLayout sl = r.layout_side(portrait, &CHAPTER);
    assert(approx(sl.rules[0].x0, box.x0));
    assert(approx(sl.rules[0].x1, box.x1));
}

void test_the_rule_sits_below_the_kicker_and_above_the_title() {
    Renderer r = renderer();
    const SideLayout sl = r.layout_side(side_of(sides(), SideKind::Portrait), &CHAPTER);
    const TextRun& kicker = sl.texts[0];
    const TextRun* title = nullptr;
    for (const TextRun& t : sl.texts)
        if (t.size >= 24.0)
            title = &t;
    assert(title != nullptr);
    assert(title->y < sl.rules[0].y && sl.rules[0].y < kicker.y);
}

void test_the_portrait_title_is_ragged_right_from_the_left_margin() {
    Renderer r = renderer();
    const Side portrait = side_of(sides(), SideKind::Portrait);
    const Rect box = r.box_for(portrait);
    const SideLayout sl = r.layout_side(portrait, &CHAPTER);
    bool any = false;
    for (const TextRun& t : sl.texts)
        if (t.size >= 24.0) {
            any = true;
            assert(approx(t.x, box.x0));
        }
    assert(any);
}

void test_a_long_portrait_title_wraps_to_two_lines() {
    Renderer r = Renderer(Layout{paper("a4"), mm(60.0), mm(10.0)}, GridSpec{}, Style{},
                          BookInfo{"Atomic Habits", "James Clear"}, &kFont, &kFont, NotesMode::Dots);
    const SideLayout sl = r.layout_side(side_of(sides(), SideKind::Portrait), &CHAPTER);
    std::vector<const TextRun*> titles;
    for (const TextRun& t : sl.texts)
        if (t.size >= 24.0)
            titles.push_back(&t);
    assert(titles.size() == 2);
    assert(titles[1]->y < titles[0]->y);
}

void test_the_portrait_footer_names_the_book_and_the_author() {
    Renderer r = renderer();
    const SideLayout sl = r.layout_side(side_of(sides(), SideKind::Portrait), &CHAPTER);
    bool found = false;
    for (const TextRun& t : sl.texts)
        if (t.italic && t.text.find("Atomic Habits") != std::string::npos &&
            t.text.find("James Clear") != std::string::npos)
            found = true;
    assert(found);
}

void test_the_portrait_footer_states_the_page_range() {
    Renderer r = renderer();
    const SideLayout sl = r.layout_side(side_of(sides(), SideKind::Portrait), &CHAPTER);
    bool found = false;
    for (const TextRun& t : sl.texts)
        if (t.italic && t.text.find("27") != std::string::npos &&
            t.text.find("44") != std::string::npos)
            found = true;
    assert(found);
}

void test_an_unknown_author_leaves_no_dangling_separator() {
    Renderer r = Renderer(Layout{paper("a4"), mm(15.0), mm(10.0)}, GridSpec{}, Style{},
                          BookInfo{"Atomic Habits", ""}, &kFont, &kFont, NotesMode::Dots);
    const SideLayout sl = r.layout_side(side_of(sides(), SideKind::Portrait), &CHAPTER);
    for (const TextRun& t : sl.texts) {
        assert(t.text.find("\u00B7\u00B7") == std::string::npos);
        assert(t.text.size() < 2 ||
               t.text.compare(t.text.size() - 2, 2, "\u00B7") != 0);
    }
}

void test_an_unknown_title_and_author_drop_the_footer_line_entirely() {
    Renderer r = Renderer(Layout{paper("a4"), mm(15.0), mm(10.0)}, GridSpec{}, Style{},
                          BookInfo{"", ""}, &kFont, &kFont, NotesMode::Dots);
    const SideLayout sl = r.layout_side(side_of(sides(), SideKind::Portrait), &CHAPTER);
    bool range = false, identity = false;
    for (const TextRun& t : sl.texts) {
        if (t.text.find("27") != std::string::npos)
            range = true;
        if (t.text.find("Atomic") != std::string::npos)
            identity = true;
    }
    assert(range);
    assert(!identity);
}

void test_the_portrait_carries_no_dot_grid() {
    Renderer r = renderer();
    const SideLayout sl = r.layout_side(side_of(sides(), SideKind::Portrait), &CHAPTER);
    assert(!sl.grid && !sl.ticks);
}

// --- the mini-TOC ----------------------------------------------------------

void test_the_mini_toc_lists_its_entries_with_page_numbers() {
    Renderer r = renderer();
    const SideLayout sl = r.layout_side(side_of(sides(), SideKind::MiniToc), &CHAPTER);
    bool cues = false, page = false, two = false;
    for (const TextRun& t : sl.texts) {
        if (t.text.find("Cues and cravings") != std::string::npos)
            cues = true;
        if (t.text == "28")
            page = true;
        if (t.text.find("two-minute") != std::string::npos)
            two = true;
    }
    assert(cues && page && two);
}

void test_mini_toc_entries_descend_down_the_page() {
    Renderer r = renderer();
    const SideLayout sl = r.layout_side(side_of(sides(), SideKind::MiniToc), &CHAPTER);
    const TextRun* flat = nullptr;
    const TextRun* nested = nullptr;
    for (const TextRun& t : sl.texts) {
        if (t.text.find("Cues") != std::string::npos)
            flat = &t;
        if (t.text.find("two-minute") != std::string::npos)
            nested = &t;
    }
    assert(flat && nested);
    assert(flat->y > nested->y);
}

void test_a_nested_toc_entry_is_indented() {
    Renderer r = renderer();
    const SideLayout sl = r.layout_side(side_of(sides(), SideKind::MiniToc), &CHAPTER);
    const TextRun* flat = nullptr;
    const TextRun* nested = nullptr;
    for (const TextRun& t : sl.texts) {
        if (t.text.find("Cues") != std::string::npos)
            flat = &t;
        if (t.text.find("two-minute") != std::string::npos)
            nested = &t;
    }
    assert(flat && nested);
    assert(nested->x > flat->x);
}

void test_page_numbers_are_right_aligned_to_the_content_edge() {
    Renderer r = renderer();
    const Side toc_side = side_of(sides(), SideKind::MiniToc);
    const Rect box = r.box_for(toc_side);
    const SideLayout sl = r.layout_side(toc_side, &CHAPTER);
    bool any = false;
    for (const TextRun& t : sl.texts) {
        if (t.text == "28" || t.text == "35") {
            any = true;
            assert(t.x < box.x1);
            assert(t.x > box.x0 + box.width() / 2);
        }
    }
    assert(any);
}

void test_a_chapter_with_no_outline_entries_falls_back_to_a_dot_grid() {
    Chapter bare{1, "Untitled", 1, 3, {}};
    Renderer r = renderer();
    const std::vector<Side> ss = plan_sides({bare}, NotesMode::Dots);
    const SideLayout sl = r.layout_side(side_of(ss, SideKind::MiniToc), &bare);
    assert(sl.grid);
}

// --- notes and blanks ------------------------------------------------------

void test_a_notes_side_has_a_grid_ticks_and_a_registration_mark() {
    Renderer r = renderer();
    const SideLayout sl = r.layout_side(side_of(sides(), SideKind::Notes), &CHAPTER);
    assert(sl.grid && sl.ticks && sl.registration.has_value());
}

void test_the_notes_footer_names_the_chapter_and_the_source_page() {
    Renderer r = renderer();
    const std::vector<Side> ss = sides();
    const Side content = side_of(ss, SideKind::Content);
    // The notes page immediately after the first content page.
    const Side notes = ss[content.index];  // 1-based index -> next element
    assert(notes.kind == SideKind::Notes);
    const SideLayout sl = r.layout_side(notes, &CHAPTER, std::nullopt, content.source_page);
    bool found = false;
    for (const TextRun& t : sl.texts)
        if (t.text.find("Ch. 1") != std::string::npos &&
            t.text.find("27") != std::string::npos)
            found = true;
    assert(found);
}

void test_the_notes_footer_sits_on_the_outer_edge_not_the_binding_edge() {
    Renderer r = renderer();
    const Side notes = side_of(sides(), SideKind::Notes);
    assert(notes.is_recto());
    const Rect box = r.box_for(notes);
    const SideLayout sl = r.layout_side(notes, &CHAPTER, std::nullopt, 27);
    const TextRun* footer = nullptr;
    for (const TextRun& t : sl.texts)
        if (t.text.find("Ch.") != std::string::npos)
            footer = &t;
    assert(footer != nullptr);
    assert(footer->x > box.x0 + box.width() / 2);
}

void test_notes_mode_blank_still_keeps_the_ticks_but_drops_the_grid() {
    Renderer r = Renderer(Layout{paper("a4"), mm(15.0), mm(10.0)}, GridSpec{}, Style{},
                          BookInfo{"Atomic Habits", "James Clear"}, &kFont, &kFont, NotesMode::Blank);
    const SideLayout sl = r.layout_side(side_of(sides(), SideKind::Notes), &CHAPTER);
    assert(!sl.grid && sl.ticks);
}

void test_a_blank_parity_side_carries_only_a_registration_mark() {
    Renderer r = renderer();
    const SideLayout sl = r.layout_side(side_of(sides(), SideKind::Blank), &CHAPTER);
    assert(!sl.grid && !sl.ticks);
    assert(sl.texts.empty());
    assert(sl.registration.has_value());
}

// --- content ---------------------------------------------------------------

void test_a_content_side_places_the_source_page_scaled_into_the_box() {
    Renderer r = renderer();
    const Side content = side_of(sides(), SideKind::Content);
    const Rect page_box(0.0, 0.0, 396.0, 612.0);  // a trade paperback page
    const SideLayout sl = r.layout_side(content, &CHAPTER, page_box, std::nullopt);
    assert(sl.content.has_value());
    assert(sl.content->scale > 1.0);  // scaled up to use the sheet
    const Rect box = r.box_for(content);
    assert(sl.content->apply_x(page_box.x0) >= box.x0 - 1e-6);
    assert(sl.content->apply_x(page_box.x1) <= box.x1 + 1e-6);
}

void test_a_content_side_draws_no_furniture_over_the_page() {
    Renderer r = renderer();
    const Side content = side_of(sides(), SideKind::Content);
    const SideLayout sl =
        r.layout_side(content, &CHAPTER, Rect(0.0, 0.0, 396.0, 612.0), std::nullopt);
    assert(!sl.grid && !sl.ticks);
}

// --- emit ------------------------------------------------------------------

void test_emitting_a_notes_side_produces_a_grid_and_ticks_stream() {
    Renderer r = renderer();
    const Side notes = side_of(sides(), SideKind::Notes);
    const SideLayout sl = r.layout_side(notes, &CHAPTER, std::nullopt, 27);
    const std::string stream = r.emit(sl);
    assert(ops(stream, "m") > 0);
    assert(ops(stream, "S") > 0);
    assert(ops(stream, "q") == ops(stream, "Q"));
}

void test_emitting_a_blank_side_is_nearly_empty() {
    Renderer r = renderer();
    const SideLayout sl = r.layout_side(side_of(sides(), SideKind::Blank), &CHAPTER);
    const std::string stream = r.emit(sl);
    assert(stream.size() < 200);
}

void test_placing_a_form_xobject_emits_a_cm_and_a_do() {
    Renderer r = renderer();
    const Side content = side_of(sides(), SideKind::Content);
    const SideLayout sl =
        r.layout_side(content, &CHAPTER, Rect(0.0, 0.0, 396.0, 612.0), std::nullopt);
    const std::string stream = r.place_form("/Fx0", *sl.content);
    assert(stream.find("cm") != std::string::npos);
    assert(stream.find("/Fx0 Do") != std::string::npos);
    assert(stream.front() == 'q' && stream.back() == 'Q');
}

}  // namespace

int main() {
    test_a_recto_takes_its_gutter_from_the_left();
    test_a_verso_takes_its_gutter_from_the_right();
    test_the_portrait_kicker_spells_the_chapter_number();
    test_the_portrait_kicker_is_letterspaced();
    test_the_portrait_has_exactly_one_hairline_rule();
    test_the_rule_spans_the_content_width();
    test_the_rule_sits_below_the_kicker_and_above_the_title();
    test_the_portrait_title_is_ragged_right_from_the_left_margin();
    test_a_long_portrait_title_wraps_to_two_lines();
    test_the_portrait_footer_names_the_book_and_the_author();
    test_the_portrait_footer_states_the_page_range();
    test_an_unknown_author_leaves_no_dangling_separator();
    test_an_unknown_title_and_author_drop_the_footer_line_entirely();
    test_the_portrait_carries_no_dot_grid();
    test_the_mini_toc_lists_its_entries_with_page_numbers();
    test_mini_toc_entries_descend_down_the_page();
    test_a_nested_toc_entry_is_indented();
    test_page_numbers_are_right_aligned_to_the_content_edge();
    test_a_chapter_with_no_outline_entries_falls_back_to_a_dot_grid();
    test_a_notes_side_has_a_grid_ticks_and_a_registration_mark();
    test_the_notes_footer_names_the_chapter_and_the_source_page();
    test_the_notes_footer_sits_on_the_outer_edge_not_the_binding_edge();
    test_notes_mode_blank_still_keeps_the_ticks_but_drops_the_grid();
    test_a_blank_parity_side_carries_only_a_registration_mark();
    test_a_content_side_places_the_source_page_scaled_into_the_box();
    test_a_content_side_draws_no_furniture_over_the_page();
    test_emitting_a_notes_side_produces_a_grid_and_ticks_stream();
    test_emitting_a_blank_side_is_nearly_empty();
    test_placing_a_form_xobject_emits_a_cm_and_a_do();
    std::printf("render_test: all assertions passed\n");
    return 0;
}
