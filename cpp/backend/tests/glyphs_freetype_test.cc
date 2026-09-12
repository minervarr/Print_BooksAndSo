// glyphs_freetype_test.cc — Latin Modern outlines via FreeType.
//
// Copyright (C) 2026 nava. AGPLv3 or later; see LICENSE.
//
// Backend test: unlike core/tests/text_test.cc this needs FreeType and the
// shipped OTF. It exists to prove the no-embedded-font design's assumption —
// Latin Modern's outlines come back as cubic segments that map onto PDF's `c`.
#undef NDEBUG
#include <cassert>
#include <cstdio>
#include <stdexcept>
#include <string>
#include <sys/stat.h>

#include "freetype/glyphs_freetype.hh"

using namespace pb;

static bool is_file(const std::string& path) {
    struct stat st;
    return stat(path.c_str(), &st) == 0 && S_ISREG(st.st_mode);
}

static void test_the_shipped_faces_exist() {
    const std::string dir = font_dir();
    assert(is_file(dir + "/lmroman10-regular.otf"));
    assert(is_file(dir + "/lmroman10-italic.otf"));
}

static void test_regular_and_italic_load() {
    FreeTypeGlyphs roman = FreeTypeGlyphs::regular();
    FreeTypeGlyphs italic = FreeTypeGlyphs::italic();
    assert(roman.units_per_em() == 1000);
    assert(italic.units_per_em() == 1000);
    assert(!roman.outline(U'A').commands.empty());
    assert(!italic.outline(U'A').commands.empty());
    // Different face, different shape: a copy-paste path bug would make these
    // identical.
    assert(italic.outline(U'A').commands.front().operands !=
           roman.outline(U'A').commands.front().operands);
}

static void test_latin_modern_has_a_1000_unit_em() {
    assert(FreeTypeGlyphs::regular().units_per_em() == 1000);
}

static void test_capital_h_has_cubic_commands() {
    const GlyphOutline glyph = FreeTypeGlyphs::regular().outline(U'H');
    assert(glyph.advance > 0);
    assert(!glyph.commands.empty());
    bool has_cubic = false;
    for (const PathCommand& cmd : glyph.commands) {
        if (cmd.op == 'c') {
            has_cubic = true;
            assert(cmd.operands.size() == 6);
        }
    }
    assert(has_cubic);
}

static void test_every_operator_is_one_pdf_understands() {
    FreeTypeGlyphs roman = FreeTypeGlyphs::regular();
    const char* chars =
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,:;-";
    for (const char* p = chars; *p != '\0'; ++p) {
        const GlyphOutline glyph = roman.outline(static_cast<unsigned char>(*p));
        for (const PathCommand& cmd : glyph.commands) {
            assert(cmd.op == 'm' || cmd.op == 'l' || cmd.op == 'c' || cmd.op == 'h');
            if (cmd.op == 'm' || cmd.op == 'l')
                assert(cmd.operands.size() == 2);
            else if (cmd.op == 'c')
                assert(cmd.operands.size() == 6);
            else
                assert(cmd.operands.empty());
        }
    }
}

static void test_a_space_advances_without_drawing() {
    const GlyphOutline space = FreeTypeGlyphs::regular().outline(U' ');
    assert(space.advance > 0);
    assert(space.commands.empty());
}

static void test_unmapped_character_throws_out_of_range() {
    bool threw = false;
    try {
        (void)FreeTypeGlyphs::regular().outline(U'\uFFFD');
    } catch (const std::out_of_range&) {
        threw = true;
    }
    assert(threw);
}

static void test_closed_contours_are_closed_explicitly() {
    // PDF's `f` closes open subpaths implicitly, so dropping `h` renders the
    // same and no other test notices. It is pinned anyway: `h` is part of the
    // PathCommand contract, and golden tests will diff the command stream.
    bool has_close = false;
    for (const PathCommand& cmd : FreeTypeGlyphs::regular().outline(U'O').commands) {
        if (cmd.op == 'h')
            has_close = true;
    }
    assert(has_close);
}

// Latin Modern is CFF: FT_Outline_Decompose never calls conicTo on these
// faces. If it did, FreeTypeGlyphs throws std::invalid_argument naming the
// face path — the same refusal as Python's qCurveTo. There is no LM glyph
// that produces a quadratic, so this is documented rather than executed.

int main() {
    test_the_shipped_faces_exist();
    test_regular_and_italic_load();
    test_latin_modern_has_a_1000_unit_em();
    test_capital_h_has_cubic_commands();
    test_every_operator_is_one_pdf_understands();
    test_a_space_advances_without_drawing();
    test_unmapped_character_throws_out_of_range();
    test_closed_contours_are_closed_explicitly();
    std::printf("glyphs_freetype_test: all assertions passed\n");
    return 0;
}
