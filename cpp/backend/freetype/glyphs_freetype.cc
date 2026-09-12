// glyphs_freetype.cc — a GlyphSource backed by a real OpenType file.
//
// Copyright (C) 2026 nava. AGPLv3 or later; see LICENSE.
//
// Latin Modern is CFF-flavoured OpenType, so FT_Outline_Decompose hands back
// cubic segments that map straight onto PDF's `c`. A quadratic conicTo would
// mean a TrueType font got loaded, which this program never does on purpose —
// so it throws rather than silently approximating.

#include "freetype/glyphs_freetype.hh"

#include <cstdlib>
#include <stdexcept>
#include <unordered_map>
#include <utility>

#include <ft2build.h>
#include FT_FREETYPE_H
#include FT_OUTLINE_H

namespace pb {
namespace {

struct FtLibraryDeleter {
    void operator()(FT_Library lib) const noexcept {
        if (lib)
            FT_Done_FreeType(lib);
    }
};

struct FtFaceDeleter {
    void operator()(FT_Face face) const noexcept {
        if (face)
            FT_Done_Face(face);
    }
};

std::string join_font(const std::string& dir, const char* name) {
    if (dir.empty())
        return name;
    if (dir.back() == '/' || dir.back() == '\\')
        return dir + name;
    return dir + "/" + name;
}

struct Decompose {
    std::vector<PathCommand> commands;
    double start_x = 0.0;
    double start_y = 0.0;
    bool in_contour = false;
    std::string error;
};

void close_contour(Decompose* d) {
    if (!d->in_contour)
        return;
    // FT_Outline_Decompose closes with line_to(start). PDF's `h` does that
    // and marks the subpath closed; drop the redundant line so the command
    // stream matches fontTools' closePath.
    if (!d->commands.empty()) {
        const PathCommand& last = d->commands.back();
        if (last.op == 'l' && last.operands.size() == 2 &&
            last.operands[0] == d->start_x && last.operands[1] == d->start_y) {
            d->commands.pop_back();
        }
    }
    d->commands.push_back(PathCommand{'h', {}});
    d->in_contour = false;
}

int on_move_to(const FT_Vector* to, void* user) {
    auto* d = static_cast<Decompose*>(user);
    close_contour(d);
    d->start_x = static_cast<double>(to->x);
    d->start_y = static_cast<double>(to->y);
    d->commands.push_back(PathCommand{'m', {d->start_x, d->start_y}});
    d->in_contour = true;
    return 0;
}

int on_line_to(const FT_Vector* to, void* user) {
    auto* d = static_cast<Decompose*>(user);
    d->commands.push_back(
        PathCommand{'l', {static_cast<double>(to->x), static_cast<double>(to->y)}});
    return 0;
}

int on_conic_to(const FT_Vector* /*control*/, const FT_Vector* /*to*/, void* user) {
    auto* d = static_cast<Decompose*>(user);
    d->error = "quadratic (TrueType)";
    return 1;
}

int on_cubic_to(const FT_Vector* control1, const FT_Vector* control2, const FT_Vector* to,
                void* user) {
    auto* d = static_cast<Decompose*>(user);
    d->commands.push_back(PathCommand{'c',
                                      {static_cast<double>(control1->x),
                                       static_cast<double>(control1->y),
                                       static_cast<double>(control2->x),
                                       static_cast<double>(control2->y),
                                       static_cast<double>(to->x),
                                       static_cast<double>(to->y)}});
    return 0;
}

const FT_Outline_Funcs kOutlineFuncs = {
    on_move_to,
    on_line_to,
    on_conic_to,
    on_cubic_to,
    0,  // shift: font units stay font units
    0,  // delta
};

}  // namespace

struct FreeTypeGlyphs::Impl {
    std::string path;
    std::unique_ptr<FT_LibraryRec_, FtLibraryDeleter> library;
    std::unique_ptr<FT_FaceRec_, FtFaceDeleter> face;
    mutable std::unordered_map<char32_t, GlyphOutline> cache;

    GlyphOutline load(char32_t codepoint) const;
};

std::string font_dir() {
    if (const char* env = std::getenv("PRINT_BOOKS_FONT_DIR")) {
        if (env[0] != '\0')
            return env;
    }
#ifdef PRINTBOOKS_FONT_DIR
    return PRINTBOOKS_FONT_DIR;
#else
    throw std::runtime_error("PRINTBOOKS_FONT_DIR is not set");
#endif
}

FreeTypeGlyphs::FreeTypeGlyphs(const std::string& path) : impl_(std::make_unique<Impl>()) {
    impl_->path = path;
    FT_Library lib = nullptr;
    if (FT_Init_FreeType(&lib) != 0)
        throw std::runtime_error("FT_Init_FreeType failed");
    impl_->library.reset(lib);

    FT_Face face = nullptr;
    if (FT_New_Face(lib, path.c_str(), 0, &face) != 0)
        throw std::runtime_error("failed to open font: " + path);
    impl_->face.reset(face);

    if (FT_Select_Charmap(face, FT_ENCODING_UNICODE) != 0)
        throw std::runtime_error("font has no Unicode cmap: " + path);
}

FreeTypeGlyphs::~FreeTypeGlyphs() = default;
FreeTypeGlyphs::FreeTypeGlyphs(FreeTypeGlyphs&&) noexcept = default;
FreeTypeGlyphs& FreeTypeGlyphs::operator=(FreeTypeGlyphs&&) noexcept = default;

FreeTypeGlyphs FreeTypeGlyphs::regular() {
    return FreeTypeGlyphs(join_font(font_dir(), "lmroman10-regular.otf"));
}

FreeTypeGlyphs FreeTypeGlyphs::italic() {
    return FreeTypeGlyphs(join_font(font_dir(), "lmroman10-italic.otf"));
}

int FreeTypeGlyphs::units_per_em() const {
    return static_cast<int>(impl_->face->units_per_EM);
}

GlyphOutline FreeTypeGlyphs::Impl::load(char32_t codepoint) const {
    const FT_UInt index = FT_Get_Char_Index(face.get(), static_cast<FT_ULong>(codepoint));
    if (index == 0)
        throw std::out_of_range("font has no glyph for codepoint");

    if (FT_Load_Glyph(face.get(), index, FT_LOAD_NO_SCALE | FT_LOAD_NO_BITMAP) != 0)
        throw std::runtime_error("FT_Load_Glyph failed");

    GlyphOutline glyph;
    glyph.advance = static_cast<double>(face->glyph->metrics.horiAdvance);

    if (face->glyph->format != FT_GLYPH_FORMAT_OUTLINE ||
        face->glyph->outline.n_contours <= 0)
        return glyph;

    Decompose state;
    const FT_Error err =
        FT_Outline_Decompose(&face->glyph->outline, &kOutlineFuncs, &state);
    if (!state.error.empty()) {
        throw std::invalid_argument("glyph is quadratic (TrueType). This program "
                                    "loads CFF-flavoured OpenType so outlines stay "
                                    "cubic; check " +
                                    path);
    }
    if (err != 0)
        throw std::runtime_error("FT_Outline_Decompose failed");
    close_contour(&state);
    glyph.commands = std::move(state.commands);
    return glyph;
}

GlyphOutline FreeTypeGlyphs::outline(char32_t codepoint) const {
    auto it = impl_->cache.find(codepoint);
    if (it != impl_->cache.end())
        return it->second;
    GlyphOutline glyph = impl_->load(codepoint);
    impl_->cache.emplace(codepoint, glyph);
    return glyph;
}

}  // namespace pb
