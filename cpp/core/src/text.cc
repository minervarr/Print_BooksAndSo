// text.cc — laying out text as filled outlines, measured against a GlyphSource.
//
// Copyright (C) 2026 nava. AGPLv3 or later; see LICENSE.

#include "printbooks/text.hh"

#include <algorithm>
#include <cstdio>
#include <sstream>
#include <stdexcept>

#include "printbooks/pdfops.hh"

namespace pb {

namespace {

// Decode one UTF-8 code point starting at s[i]; advances i past it. Malformed
// input yields U+FFFD so a bad byte can never abort a whole line of text.
char32_t next_codepoint(const std::string& s, std::size_t& i) {
    const unsigned char c = static_cast<unsigned char>(s[i]);
    if (c < 0x80) {
        i += 1;
        return c;
    }
    int n;
    char32_t cp;
    if ((c & 0xE0) == 0xC0) {
        n = 1; cp = c & 0x1F;
    } else if ((c & 0xF0) == 0xE0) {
        n = 2; cp = c & 0x0F;
    } else if ((c & 0xF8) == 0xF0) {
        n = 3; cp = c & 0x07;
    } else {
        i += 1;
        return 0xFFFD;
    }
    if (i + static_cast<std::size_t>(n) >= s.size()) {
        i += 1;
        return 0xFFFD;
    }
    for (int k = 0; k < n; ++k) {
        const unsigned char b = static_cast<unsigned char>(s[i + 1 + k]);
        if ((b & 0xC0) != 0x80) {
            i += 1;
            return 0xFFFD;
        }
        cp = (cp << 6) | (b & 0x3F);
    }
    i += 1 + n;
    return cp;
}

std::string encode_utf8(char32_t cp) {
    std::string s;
    if (cp < 0x80) {
        s += static_cast<char>(cp);
    } else if (cp < 0x800) {
        s += static_cast<char>(0xC0 | (cp >> 6));
        s += static_cast<char>(0x80 | (cp & 0x3F));
    } else if (cp < 0x10000) {
        s += static_cast<char>(0xE0 | (cp >> 12));
        s += static_cast<char>(0x80 | ((cp >> 6) & 0x3F));
        s += static_cast<char>(0x80 | (cp & 0x3F));
    } else {
        s += static_cast<char>(0xF0 | (cp >> 18));
        s += static_cast<char>(0x80 | ((cp >> 12) & 0x3F));
        s += static_cast<char>(0x80 | ((cp >> 6) & 0x3F));
        s += static_cast<char>(0x80 | (cp & 0x3F));
    }
    return s;
}

}  // namespace

double text_width(const GlyphSource& source, const std::string& text, double size,
                  double tracking) {
    if (text.empty())
        return 0.0;

    const double scale = size / source.units_per_em();
    double advances = 0.0;
    int count = 0;
    for (std::size_t i = 0; i < text.size();) {
        const char32_t cp = next_codepoint(text, i);
        advances += source.outline(cp).advance;
        ++count;
    }
    return advances * scale + tracking * (count - 1);
}

std::string draw_text(const GlyphSource& source, const std::string& text, double x, double y,
                      double size, double ink, double tracking) {
    if (size <= 0.0)
        throw std::invalid_argument("size must be positive");
    const std::string fill = gray(ink);
    if (text.empty())
        return "";

    // Collect every missing character before failing, so the error names all of
    // them at once rather than stopping at the first.
    std::vector<GlyphOutline> outlines;
    std::vector<char32_t> missing;
    for (std::size_t i = 0; i < text.size();) {
        const char32_t cp = next_codepoint(text, i);
        try {
            outlines.push_back(source.outline(cp));
        } catch (const std::out_of_range&) {
            if (std::find(missing.begin(), missing.end(), cp) == missing.end())
                missing.push_back(cp);
            outlines.push_back(GlyphOutline{});
        }
    }

    if (!missing.empty()) {
        std::string msg = "font is missing " + std::to_string(missing.size()) + " glyph(s):";
        for (char32_t cp : missing) {
            char hex[8];
            std::snprintf(hex, sizeof hex, "%04X", static_cast<unsigned>(cp));
            msg += " '";
            msg += encode_utf8(cp);
            msg += "' (U+" + std::string(hex) + ")";
        }
        throw std::invalid_argument(msg);
    }

    const double scale = size / source.units_per_em();
    std::string out = "q\n" + fill + " g";
    double pen = x;
    for (const GlyphOutline& outline : outlines) {
        for (const PathCommand& cmd : outline.commands) {
            if (cmd.operands.empty()) {
                out += "\n";
                out += cmd.op;
            } else {
                std::string line;
                for (std::size_t k = 0; k < cmd.operands.size(); ++k) {
                    if (k)
                        line += " ";
                    const double v = cmd.operands[k];
                    line += num((k % 2 == 0) ? pen + v * scale : y + v * scale);
                }
                out += "\n" + line + " " + cmd.op;
            }
        }
        pen += outline.advance * scale + tracking;
    }
    out += "\nf\nQ";
    return out;
}

std::vector<std::string> wrap_text(const GlyphSource& source, const std::string& text,
                                   double size, double max_width, int max_lines,
                                   double tracking) {
    if (max_width <= 0.0)
        throw std::invalid_argument("max_width must be positive");
    if (max_lines < 1)
        throw std::invalid_argument("max_lines must be at least 1");

    std::vector<std::string> words;
    std::istringstream in(text);
    std::string w;
    while (in >> w)
        words.push_back(w);
    if (words.empty())
        return {};

    std::vector<std::string> lines;
    std::string current;
    for (const std::string& word : words) {
        const std::string candidate = current.empty() ? word : current + " " + word;
        if (!current.empty() && text_width(source, candidate, size, tracking) > max_width) {
            lines.push_back(current);
            current = word;
            if (static_cast<int>(lines.size()) == max_lines) {
                lines.back() += "\u2026";
                return lines;
            }
        } else {
            current = candidate;
        }
    }
    lines.push_back(current);
    return lines;
}

}  // namespace pb
