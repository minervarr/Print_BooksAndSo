// plan_test.cc — the page-slot model. These invariants ARE the specification.
//
// Copyright (C) 2026 nava. AGPLv3 or later; see LICENSE.
#undef NDEBUG
#include <cassert>
#include <cstdio>
#include <stdexcept>
#include <vector>

#include "printbooks/plan.hh"

using namespace pb;

static Chapter chapter(int number, int first, int last) {
    Chapter c;
    c.number = number;
    c.title = "Chapter " + std::to_string(number);
    c.first_page = first;
    c.last_page = last;
    c.toc = {TocEntry{"A section", first, 0}};
    return c;
}

static std::vector<SideKind> kinds_of(const std::vector<Side>& sides) {
    std::vector<SideKind> out;
    for (const Side& s : sides)
        out.push_back(s.kind);
    return out;
}

// --- the shape of one chapter ----------------------------------------------

static void test_one_chapter_of_one_page_is_six_sides() {
    const std::vector<Side> sides = plan_sides({chapter(1, 1, 1)}, NotesMode::Dots);
    const std::vector<SideKind> expect = {SideKind::Portrait, SideKind::MiniToc, SideKind::Notes,
                                          SideKind::Content, SideKind::Notes, SideKind::Blank};
    assert(kinds_of(sides) == expect);
}

static void test_sides_per_chapter_is_four_plus_twice_the_page_count() {
    const int page_counts[] = {1, 2, 3, 7, 18};
    for (int n : page_counts) {
        const std::vector<Side> sides = plan_sides({chapter(1, 1, n)}, NotesMode::Dots);
        assert(static_cast<int>(sides.size()) == 4 + 2 * n);
    }
}

static void test_the_parity_side_is_the_last_side_of_the_chapter() {
    const std::vector<Side> sides = plan_sides({chapter(1, 1, 3)}, NotesMode::Dots);
    assert(sides.back().kind == SideKind::Blank);
}

// --- the four invariants ----------------------------------------------------

static void test_every_portrait_is_on_a_recto() {
    const std::vector<Side> sides =
        plan_sides({chapter(1, 1, 3), chapter(2, 4, 5), chapter(3, 6, 6)}, NotesMode::Dots);
    int portraits = 0;
    for (const Side& s : sides) {
        if (s.kind == SideKind::Portrait) {
            ++portraits;
            assert(s.is_recto());
        }
    }
    assert(portraits == 3);
}

static void test_every_content_page_is_on_a_verso() {
    const std::vector<Side> sides = plan_sides({chapter(1, 1, 4), chapter(2, 5, 7)}, NotesMode::Dots);
    bool any = false;
    for (const Side& s : sides) {
        if (s.kind == SideKind::Content) {
            any = true;
            assert(!s.is_recto());
        }
    }
    assert(any);
}

static void test_every_content_page_faces_a_notes_page() {
    const std::vector<Side> sides = plan_sides({chapter(1, 1, 3), chapter(2, 4, 5)}, NotesMode::Dots);
    for (std::size_t i = 0; i < sides.size(); ++i) {
        if (sides[i].kind != SideKind::Content)
            continue;
        assert(i + 1 < sides.size());
        assert(sides[i + 1].kind == SideKind::Notes);
    }
}

static void test_the_mini_toc_faces_a_notes_page() {
    const std::vector<Side> sides = plan_sides({chapter(1, 1, 2)}, NotesMode::Dots);
    for (std::size_t i = 0; i < sides.size(); ++i) {
        if (sides[i].kind == SideKind::MiniToc) {
            assert(i + 1 < sides.size());
            assert(sides[i + 1].kind == SideKind::Notes);
        }
    }
}

static void test_source_pages_appear_exactly_once_and_in_order() {
    const std::vector<Side> sides =
        plan_sides({chapter(1, 1, 3), chapter(2, 4, 6), chapter(3, 7, 9)}, NotesMode::Dots);
    std::vector<int> pages;
    for (const Side& s : sides)
        if (s.kind == SideKind::Content)
            pages.push_back(*s.source_page);
    std::vector<int> expect = {1, 2, 3, 4, 5, 6, 7, 8, 9};
    assert(pages == expect);
}

static void test_only_content_sides_carry_a_source_page() {
    const std::vector<Side> sides = plan_sides({chapter(1, 1, 2)}, NotesMode::Dots);
    for (const Side& s : sides) {
        if (s.kind == SideKind::Content)
            assert(s.source_page.has_value());
        else
            assert(!s.source_page.has_value());
    }
}

// --- indices, parity, gutter ------------------------------------------------

static void test_side_indices_are_contiguous_from_one() {
    const std::vector<Side> sides = plan_sides({chapter(1, 1, 2), chapter(2, 3, 4)}, NotesMode::Dots);
    for (std::size_t i = 0; i < sides.size(); ++i)
        assert(sides[i].index == static_cast<int>(i) + 1);
}

static void test_recto_is_odd_and_verso_is_even() {
    const std::vector<Side> sides = plan_sides({chapter(1, 1, 2)}, NotesMode::Dots);
    for (const Side& s : sides)
        assert(s.is_recto() == (s.index % 2 == 1));
}

static void test_the_gutter_is_on_the_left_of_a_recto_and_the_right_of_a_verso() {
    const std::vector<Side> sides = plan_sides({chapter(1, 1, 2)}, NotesMode::Dots);
    for (const Side& s : sides)
        assert(s.gutter_edge() == (s.is_recto() ? GutterEdge::Left : GutterEdge::Right));
}

static void test_every_side_knows_its_chapter() {
    const std::vector<Side> sides = plan_sides({chapter(1, 1, 2), chapter(2, 3, 3)}, NotesMode::Dots);
    for (std::size_t i = 0; i < 6; ++i)
        assert(sides[i].chapter == 1);
    bool has2 = false;
    for (const Side& s : sides)
        if (s.chapter == 2)
            has2 = true;
    assert(has2);
}

static void test_a_second_chapter_starts_where_the_first_ended() {
    const std::vector<Side> first = plan_sides({chapter(1, 1, 3)}, NotesMode::Dots);
    const std::vector<Side> both = plan_sides({chapter(1, 1, 3), chapter(2, 4, 5)}, NotesMode::Dots);
    assert(first.size() == 10);
    assert(both.size() == 18);
    assert(both[10].kind == SideKind::Portrait);
    assert(both[10].index == 11);
}

// --- notes = none: the plain chapter print ---------------------------------

static void test_notes_none_emits_no_notes_pages() {
    const std::vector<Side> sides = plan_sides({chapter(1, 1, 4)}, NotesMode::None);
    for (const Side& s : sides)
        assert(s.kind != SideKind::Notes);
}

static void test_notes_none_still_opens_every_chapter_on_a_recto() {
    const std::vector<Side> sides =
        plan_sides({chapter(1, 1, 3), chapter(2, 4, 4), chapter(3, 5, 8)}, NotesMode::None);
    int portraits = 0;
    for (const Side& s : sides)
        if (s.kind == SideKind::Portrait) {
            ++portraits;
            assert(s.is_recto());
        }
    assert(portraits == 3);
}

static void test_notes_none_prints_content_on_both_sides_of_the_sheet() {
    const std::vector<Side> sides = plan_sides({chapter(1, 1, 4)}, NotesMode::None);
    bool recto = false, verso = false;
    for (const Side& s : sides)
        if (s.kind == SideKind::Content)
            (s.is_recto() ? recto : verso) = true;
    assert(recto && verso);
}

static void test_notes_none_keeps_every_source_page_exactly_once() {
    const std::vector<Side> sides = plan_sides({chapter(1, 1, 3), chapter(2, 4, 6)}, NotesMode::None);
    std::vector<int> pages;
    for (const Side& s : sides)
        if (s.kind == SideKind::Content)
            pages.push_back(*s.source_page);
    std::vector<int> expect = {1, 2, 3, 4, 5, 6};
    assert(pages == expect);
}

// --- rejected input --------------------------------------------------------

static void expect_invalid(std::vector<Chapter> chapters) {
    bool threw = false;
    try {
        plan_sides(chapters, NotesMode::Dots);
    } catch (const std::invalid_argument&) {
        threw = true;
    }
    assert(threw);
}

static void test_an_inverted_page_range_is_rejected() {
    expect_invalid({chapter(1, 9, 4)});
}

static void test_a_page_range_below_one_is_rejected() {
    expect_invalid({chapter(1, 0, 4)});
}

static void test_overlapping_chapters_are_rejected() {
    expect_invalid({chapter(1, 1, 5), chapter(2, 4, 8)});
}

static void test_no_chapters_is_rejected() {
    expect_invalid({});
}

static void test_chapter_knows_its_page_count() {
    assert(chapter(1, 27, 44).page_count() == 18);
}

int main() {
    test_one_chapter_of_one_page_is_six_sides();
    test_sides_per_chapter_is_four_plus_twice_the_page_count();
    test_the_parity_side_is_the_last_side_of_the_chapter();
    test_every_portrait_is_on_a_recto();
    test_every_content_page_is_on_a_verso();
    test_every_content_page_faces_a_notes_page();
    test_the_mini_toc_faces_a_notes_page();
    test_source_pages_appear_exactly_once_and_in_order();
    test_only_content_sides_carry_a_source_page();
    test_side_indices_are_contiguous_from_one();
    test_recto_is_odd_and_verso_is_even();
    test_the_gutter_is_on_the_left_of_a_recto_and_the_right_of_a_verso();
    test_every_side_knows_its_chapter();
    test_a_second_chapter_starts_where_the_first_ended();
    test_notes_none_emits_no_notes_pages();
    test_notes_none_still_opens_every_chapter_on_a_recto();
    test_notes_none_prints_content_on_both_sides_of_the_sheet();
    test_notes_none_keeps_every_source_page_exactly_once();
    test_an_inverted_page_range_is_rejected();
    test_a_page_range_below_one_is_rejected();
    test_overlapping_chapters_are_rejected();
    test_no_chapters_is_rejected();
    test_chapter_knows_its_page_count();
    std::printf("plan_test: all assertions passed\n");
    return 0;
}
