// render.cc — one side of one sheet: layout, then a content stream.
//
// Copyright (C) 2026 nava. AGPLv3 or later; see LICENSE.

#include "printbooks/render.hh"

#include <stdexcept>
#include <string>
#include <vector>

#include "printbooks/numwords.hh"
#include "printbooks/pdfops.hh"
#include "printbooks/text.hh"

namespace pb {

namespace {

// The separator between book title and author on a portrait footer.
constexpr const char* kMiddot = "\u00B7";

std::string trim(const std::string& s) {
    const std::size_t b = s.find_first_not_of(" \t\r\n\f\v");
    if (b == std::string::npos)
        return "";
    const std::size_t e = s.find_last_not_of(" \t\r\n\f\v");
    return s.substr(b, e - b + 1);
}

void replace_all(std::string& s, const std::string& from, const std::string& to) {
    std::size_t pos = 0;
    while ((pos = s.find(from, pos)) != std::string::npos) {
        s.replace(pos, from.size(), to);
        pos += to.size();
    }
}

std::string to_upper(std::string s) {
    for (char& c : s)
        if (c >= 'a' && c <= 'z')
            c = static_cast<char>(c - 'a' + 'A');
    return s;
}

}  // namespace

Renderer::Renderer(Layout layout, GridSpec grid, Style style, BookInfo book,
                   const GlyphSource* roman, const GlyphSource* italic, NotesMode notes)
    : layout_(layout),
      grid_(grid),
      style_(style),
      book_(book),
      roman_(roman),
      italic_(italic),
      notes_(notes) {}

Rect Renderer::box_for(const Side& side) const {
    return content_area(layout_.paper, layout_.margin, layout_.gutter, side.gutter_edge());
}

Corner Renderer::outer_corner(const Side& side) const {
    return side.is_recto() ? Corner::BottomRight : Corner::BottomLeft;
}

SideLayout Renderer::layout_side(const Side& side, const Chapter* chapter,
                                 std::optional<Rect> page_box,
                                 std::optional<int> facing_page) const {
    const Rect box = box_for(side);

    switch (side.kind) {
        case SideKind::Portrait: return portrait(side, box, chapter);
        case SideKind::MiniToc:  return mini_toc(side, box, chapter);
        case SideKind::Notes:    return notes(side, box, chapter, facing_page);
        case SideKind::Content:  return content(side, box, page_box);
        case SideKind::Blank:
            return SideLayout{side, box, {}, {}, false, false, outer_corner(side),
                              std::nullopt};
    }
    throw std::invalid_argument("no layout for side kind");
}

SideLayout Renderer::portrait(const Side& side, const Rect& box,
                              const Chapter* chapter) const {
    if (chapter == nullptr)
        throw std::invalid_argument("a portrait needs its chapter");
    const Style& st = style_;
    std::vector<TextRun> texts;

    const double kicker_y = box.y1 - 0.16 * box.height();
    texts.push_back(TextRun{"CHAPTER " + to_upper(ordinal_words(chapter->number)),
                            box.x0, kicker_y, st.kicker_size, st.kicker_ink,
                            st.kicker_tracking, false});

    const double rule_y = kicker_y - st.kicker_size * 0.62;
    std::vector<Rule> rules = {Rule{box.x0, rule_y, box.x1, st.rule_width, st.rule_ink}};

    // Ragged right from the left margin: the LaTeX chapter head sets the title
    // flush left and lets the right edge fall where it will.
    const std::vector<std::string> lines =
        wrap_text(*roman_, chapter->title, st.title_size, box.width(), st.title_lines, 0.0);
    double baseline = rule_y - st.title_size * 1.45;
    for (const std::string& line : lines) {
        texts.push_back(TextRun{line, box.x0, baseline, st.title_size, 1.0, 0.0, false});
        baseline -= st.title_size * st.title_leading;
    }

    // Footer: identity, then the page range. Either may be absent, and an
    // absent one must not leave a dangling separator behind.
    std::string identity;
    {
        std::vector<std::string> parts;
        const std::string t = trim(book_.title);
        const std::string a = trim(book_.author);
        if (!t.empty())
            parts.push_back(t);
        if (!a.empty())
            parts.push_back(a);
        for (std::size_t i = 0; i < parts.size(); ++i) {
            if (i)
                identity += kMiddot;
            identity += parts[i];
        }
        replace_all(identity, kMiddot, std::string(" ") + kMiddot + " ");
    }

    const double footer_y = box.y0 + st.footer_size * 3.2;
    if (!identity.empty())
        texts.push_back(centred(identity, box, footer_y, st.footer_size, st.footer_ink, true));
    texts.push_back(centred("pp. " + std::to_string(chapter->first_page) + "\u2013" +
                                std::to_string(chapter->last_page),
                            box, footer_y - st.footer_size * 1.6, st.footer_size,
                            st.footer_ink, true));

    return SideLayout{side, box, std::move(texts), std::move(rules), false, false,
                      std::nullopt, std::nullopt};
}

SideLayout Renderer::mini_toc(const Side& side, const Rect& box,
                              const Chapter* chapter) const {
    if (chapter == nullptr)
        throw std::invalid_argument("a mini-TOC needs its chapter");
    const Style& st = style_;

    // Most PDFs have a flat outline with nothing below chapter level. An empty
    // page there is a wasted sheet, so it becomes notes paper.
    if (chapter->toc.empty())
        return notes(side, box, chapter, std::nullopt);

    std::vector<TextRun> texts = {TextRun{"IN THIS CHAPTER", box.x0, box.y1 - st.kicker_size,
                                          st.kicker_size, st.kicker_ink, st.kicker_tracking,
                                          false}};
    std::vector<Rule> rules = {Rule{box.x0, box.y1 - st.kicker_size * 1.62, box.x1,
                                    st.rule_width, st.rule_ink}};

    double baseline = box.y1 - st.kicker_size * 1.62 - st.toc_size * 2.0;
    for (const TocEntry& entry : chapter->toc) {
        texts.push_back(TextRun{entry.title, box.x0 + entry.depth * st.toc_indent, baseline,
                                st.toc_size, st.toc_ink, 0.0, false});
        const std::string page = std::to_string(entry.page);
        const double width = text_width(*roman_, page, st.toc_size, 0.0);
        texts.push_back(TextRun{page, box.x1 - width, baseline, st.toc_size, st.toc_ink, 0.0,
                                false});
        baseline -= st.toc_size * st.toc_leading;
    }

    return SideLayout{side, box, std::move(texts), std::move(rules), false, false,
                      outer_corner(side), std::nullopt};
}

SideLayout Renderer::notes(const Side& side, const Rect& box, const Chapter* chapter,
                           std::optional<int> facing_page) const {
    const Style& st = style_;
    std::vector<TextRun> texts;

    if (chapter != nullptr && facing_page.has_value()) {
        const std::string label = "Ch. " + std::to_string(chapter->number) + " " + kMiddot +
                                  " p. " + std::to_string(*facing_page);
        const double width = text_width(*italic_, label, st.footer_size * 0.85, 0.0);
        // The OUTER edge, away from the binding: a footer against the gutter
        // disappears into the spiral.
        const double x = side.is_recto() ? box.x1 - width : box.x0;
        texts.push_back(TextRun{label, x, box.y0 - st.footer_size * 0.9, st.footer_size * 0.85,
                                0.45, 0.0, true});
    }

    const bool grid = notes_ == NotesMode::Dots;
    const bool ticks =
        notes_ == NotesMode::Dots || notes_ == NotesMode::Lines || notes_ == NotesMode::Blank;
    return SideLayout{side, box, std::move(texts), {}, grid, ticks, outer_corner(side),
                      std::nullopt};
}

SideLayout Renderer::content(const Side& side, const Rect& box,
                             std::optional<Rect> page_box) const {
    std::optional<Placement> placement;
    if (page_box.has_value())
        placement = fit(*page_box, box);
    return SideLayout{side, box, {}, {}, false, false, outer_corner(side), placement};
}

TextRun Renderer::centred(const std::string& text, const Rect& box, double y, double size,
                          double ink, bool italic) const {
    const GlyphSource* source = italic ? italic_ : roman_;
    const double width = text_width(*source, text, size, 0.0);
    return TextRun{text, box.x0 + (box.width() - width) / 2.0, y, size, ink, 0.0, italic};
}

std::string Renderer::emit(const SideLayout& sl) const {
    const Style& st = style_;
    std::vector<std::string> parts;

    if (sl.grid)
        parts.push_back(dot_grid(sl.box, grid_.pitch, grid_.dot, grid_.ink));
    if (sl.ticks)
        parts.push_back(center_ticks(sl.box, st.tick_length, st.tick_width, st.tick_ink));
    if (sl.registration.has_value())
        parts.push_back(registration_tick(sl.box, *sl.registration, st.reg_size, st.reg_width,
                                          st.reg_ink));
    for (const Rule& rule : sl.rules)
        parts.push_back(rule_stream(rule));
    for (const TextRun& run : sl.texts) {
        const GlyphSource* source = run.italic ? italic_ : roman_;
        parts.push_back(draw_text(*source, run.text, run.x, run.y, run.size, run.ink,
                                  run.tracking));
    }

    std::string out;
    for (const std::string& part : parts) {
        if (part.empty())
            continue;
        if (!out.empty())
            out += "\n";
        out += part;
    }
    return out;
}

std::string Renderer::rule_stream(const Rule& rule) const {
    return "q\n" + num(1.0 - rule.ink) + " G\n" + num(rule.width) + " w\n0 J\n" +
           num(rule.x0) + " " + num(rule.y) + " m " + num(rule.x1) + " " + num(rule.y) +
           " l\nS\nQ";
}

std::string Renderer::place_form(const std::string& name, const Placement& placement) const {
    return "q\n" + num(placement.scale) + " 0 0 " + num(placement.scale) + " " +
           num(placement.dx) + " " + num(placement.dy) + " cm\n" + name + " Do\nQ";
}

}  // namespace pb
