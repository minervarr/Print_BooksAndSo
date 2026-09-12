// pdf_qpdf_test.cc — qpdf probe, outline chapters, project TOML, emit.
//
// Copyright (C) 2026 nava. AGPLv3 or later; see LICENSE.
//
// Backend test: unlike core/tests this needs libqpdf and the fixture PDF.
// Pins the probe contract that is easy to get wrong — /Info vs XMP, 1-based
// outline pages, and chapter ends inferred from the next start. Emit is the
// other half: one output page per planned side, a real PDF qpdf can parse.
#undef NDEBUG
#include <cassert>
#include <cstdio>
#include <string>
#include <sys/stat.h>
#include <unistd.h>
#include <vector>

#include <qpdf/QPDF.hh>
#include <qpdf/QPDFPageDocumentHelper.hh>

#include "freetype/glyphs_freetype.hh"
#include "printbooks/geometry.hh"
#include "printbooks/plan.hh"
#include "printbooks/render.hh"
#include "printbooks/units.hh"
#include "project.hh"
#include "qpdf/pdf_qpdf.hh"

using namespace pb;

#ifndef PRINTBOOKS_FIXTURE_DIR
#define PRINTBOOKS_FIXTURE_DIR "fixtures"
#endif

static bool is_file(const std::string& path) {
    struct stat st;
    return stat(path.c_str(), &st) == 0 && S_ISREG(st.st_mode);
}

static std::string mini_book() {
    return std::string(PRINTBOOKS_FIXTURE_DIR) + "/mini_book.pdf";
}

static void test_probe_reads_title_and_author_from_the_info_dictionary() {
    const SourceBook book = probe(mini_book());
    assert(book.title == "The Test Book");
    assert(book.author == "Test Author");
}

static void test_probe_reads_the_outline_and_page_count() {
    const SourceBook book = probe(mini_book());
    assert(book.page_count() == 4);
    assert(book.outline.size() == 2);
    assert(book.outline[0].title == "Chapter One");
    assert(book.outline[0].page == 1);
    assert(book.outline[0].depth == 0);
    assert(book.outline[1].title == "Chapter Two");
    assert(book.outline[1].page == 3);
    assert(book.outline[1].depth == 0);
}

static void test_chapters_from_outline_infers_the_end_from_the_next_start() {
    const SourceBook book = probe(mini_book());
    const std::vector<Chapter> chapters = chapters_from_outline(book);
    assert(chapters.size() == 2);
    assert(chapters[0].first_page == 1);
    assert(chapters[0].last_page == 2);
    assert(chapters[1].first_page == 3);
    assert(chapters[1].last_page == 4);
    assert(chapters[0].title == "Chapter One");
    assert(chapters[1].title == "Chapter Two");
    assert(chapters[0].number == 1);
    assert(chapters[1].number == 2);
}

static void test_toml_round_trip_writes_then_reads_chapters() {
    std::vector<Chapter> in(2);
    in[0].number = 1;
    in[0].title = "Chapter One";
    in[0].first_page = 1;
    in[0].last_page = 2;
    in[1].number = 2;
    in[1].title = "Chapter Two";
    in[1].first_page = 3;
    in[1].last_page = 4;
    in[1].toc = {TocEntry{"A section", 3, 0}};

    const std::string path =
        "/tmp/printbooks_proj_" + std::to_string(getpid()) + ".toml";
    write_project(path, mini_book(), "The Test Book", "Test Author", in, "a4",
                  "dots");
    const Project proj = read_project(path);
    assert(proj.book == mini_book());
    assert(proj.title == "The Test Book");
    assert(proj.author == "Test Author");
    assert(proj.paper == "a4");
    assert(proj.notes == "dots");
    const std::vector<Chapter> out = read_chapters(path);
    assert(out.size() == 2);
    assert(proj.chapters.size() == 2);
    assert(out[0].number == 1);
    assert(out[0].title == "Chapter One");
    assert(out[0].first_page == 1);
    assert(out[0].last_page == 2);
    assert(out[0].toc.empty());
    assert(out[1].number == 2);
    assert(out[1].title == "Chapter Two");
    assert(out[1].first_page == 3);
    assert(out[1].last_page == 4);
    assert(out[1].toc.size() == 1);
    assert(out[1].toc[0].title == "A section");
    assert(out[1].toc[0].page == 3);
    assert(out[1].toc[0].depth == 0);
    std::remove(path.c_str());
}

static std::string read_prefix(const std::string& path, std::size_t n) {
    FILE* f = std::fopen(path.c_str(), "rb");
    assert(f != nullptr);
    std::string buf(n, '\0');
    const std::size_t got = std::fread(buf.data(), 1, n, f);
    std::fclose(f);
    buf.resize(got);
    return buf;
}

static void test_emit_produces_one_page_per_side() {
    const SourceBook book = probe(mini_book());
    const std::vector<Chapter> chapters = chapters_from_outline(book);
    const std::vector<Side> sides = plan_sides(chapters, NotesMode::Dots);

    const FreeTypeGlyphs roman = FreeTypeGlyphs::regular();
    const FreeTypeGlyphs italic = FreeTypeGlyphs::italic();
    const Renderer renderer(
        Layout{paper("a4"), mm(15.0), mm(10.0)}, GridSpec{}, Style{},
        BookInfo{book.title, book.author}, &roman, &italic, NotesMode::Dots);

    const std::string out_path =
        "/tmp/printbooks_emit_" + std::to_string(getpid()) + ".pdf";
    emit(book, chapters, sides, renderer, out_path);

    assert(read_prefix(out_path, 5) == "%PDF-");

    QPDF pdf;
    pdf.processFile(out_path.c_str());
    const std::vector<QPDFPageObjectHelper> pages =
        QPDFPageDocumentHelper::get(pdf).getAllPages();
    assert(pages.size() == sides.size());
    std::remove(out_path.c_str());
}

int main() {
    assert(is_file(mini_book()));
    test_probe_reads_title_and_author_from_the_info_dictionary();
    test_probe_reads_the_outline_and_page_count();
    test_chapters_from_outline_infers_the_end_from_the_next_start();
    test_toml_round_trip_writes_then_reads_chapters();
    test_emit_produces_one_page_per_side();
    std::printf("pdf_qpdf_test: all assertions passed\n");
    return 0;
}
