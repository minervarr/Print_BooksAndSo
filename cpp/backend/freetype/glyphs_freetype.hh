// glyphs_freetype.hh — GlyphSource via FT_Outline_Decompose.
//
// Copyright (C) 2026 nava. AGPLv3 or later; see LICENSE.
//
// The one-file swap the design promises: core/ asks for a glyph outline, this
// answers with PDF path operators. No font dictionary, no subsetting.
#pragma once

#include <memory>
#include <string>

#include "printbooks/metrics.hh"

namespace pb {

// Where the shipped Latin Modern faces live. Lookup, first hit wins:
//   1. $PRINT_BOOKS_FONT_DIR
//   2. dirname(executable)/fonts  if lmroman10-regular.otf is there
//      (Linux: /proc/self/exe; else argv0 from set_program_path)
//   3. /usr/share/print-books/fonts  if the regular face is there (pacman)
//   4. compile-time PRINTBOOKS_FONT_DIR (assets/fonts at the repo root)
std::string font_dir();

// argv[0] fallback for step 2 when /proc/self/exe is unavailable.
void set_program_path(const char* argv0);

class FreeTypeGlyphs : public GlyphSource {
public:
    explicit FreeTypeGlyphs(const std::string& path);
    ~FreeTypeGlyphs() override;
    FreeTypeGlyphs(FreeTypeGlyphs&&) noexcept;
    FreeTypeGlyphs& operator=(FreeTypeGlyphs&&) noexcept;
    FreeTypeGlyphs(const FreeTypeGlyphs&) = delete;
    FreeTypeGlyphs& operator=(const FreeTypeGlyphs&) = delete;

    static FreeTypeGlyphs regular();  // font_dir()/lmroman10-regular.otf
    static FreeTypeGlyphs italic();

    int units_per_em() const override;
    GlyphOutline outline(char32_t codepoint) const override;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

}  // namespace pb
