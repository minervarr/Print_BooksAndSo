// pdf_qpdf.cc — probe a source PDF into plain data.
//
// Copyright (C) 2026 nava. AGPLv3 or later; see LICENSE.
//
// MediaBox fallback 612×792; CropBox falls back to MediaBox; corners sorted.
// /Info is snapshotted before XMP; XMP dc:title / dc:creator wins when present;
// malformed XMP is not fatal. Outline destinations that will not resolve are
// skipped rather than fatal.

#include "qpdf/pdf_qpdf.hh"

#include <algorithm>
#include <cctype>
#include <cstring>
#include <map>
#include <stdexcept>
#include <utility>

#include <qpdf/Buffer.hh>
#include <qpdf/QPDF.hh>
#include <qpdf/QPDFObjGen.hh>
#include <qpdf/QPDFObjectHandle.hh>
#include <qpdf/QPDFOutlineDocumentHelper.hh>
#include <qpdf/QPDFOutlineObjectHelper.hh>
#include <qpdf/QPDFPageDocumentHelper.hh>
#include <qpdf/QPDFPageObjectHelper.hh>

namespace pb {
namespace {

std::string trim(std::string s) {
    auto is_sp = [](unsigned char c) { return std::isspace(c) != 0; };
    while (!s.empty() && is_sp(static_cast<unsigned char>(s.front())))
        s.erase(s.begin());
    while (!s.empty() && is_sp(static_cast<unsigned char>(s.back())))
        s.pop_back();
    return s;
}

void replace_all(std::string& s, const char* from, const char* to) {
    const size_t n = std::strlen(from);
    const size_t m = std::strlen(to);
    size_t pos = 0;
    while ((pos = s.find(from, pos)) != std::string::npos) {
        s.replace(pos, n, to);
        pos += m;
    }
}

std::string xml_unescape(std::string s) {
    replace_all(s, "&amp;", "&");
    replace_all(s, "&lt;", "<");
    replace_all(s, "&gt;", ">");
    replace_all(s, "&quot;", "\"");
    replace_all(s, "&apos;", "'");
    return s;
}

std::string strip_tags(const std::string& s) {
    std::string out;
    bool in_tag = false;
    for (char c : s) {
        if (c == '<')
            in_tag = true;
        else if (c == '>')
            in_tag = false;
        else if (!in_tag)
            out += c;
    }
    return xml_unescape(trim(out));
}

struct Li {
    std::string lang;
    std::string text;
};

std::vector<Li> rdf_li(const std::string& inner) {
    std::vector<Li> items;
    const std::string open = "<rdf:li";
    size_t pos = 0;
    while ((pos = inner.find(open, pos)) != std::string::npos) {
        const size_t gt = inner.find('>', pos);
        if (gt == std::string::npos)
            break;
        const std::string tag = inner.substr(pos, gt - pos);
        std::string lang;
        const size_t lang_at = tag.find("xml:lang=\"");
        if (lang_at != std::string::npos) {
            const size_t q = tag.find('"', lang_at + 10);
            if (q != std::string::npos)
                lang = tag.substr(lang_at + 10, q - (lang_at + 10));
        }
        if (gt > pos && inner[gt - 1] == '/') {
            pos = gt + 1;
            continue;
        }
        const size_t close = inner.find("</rdf:li>", gt);
        if (close == std::string::npos)
            break;
        items.push_back(Li{lang, strip_tags(inner.substr(gt + 1, close - (gt + 1)))});
        pos = close + 9;
    }
    return items;
}

std::string xmp_dc(const std::string& xmp, const char* name, bool join_all) {
    const std::string open = std::string("<dc:") + name;
    const size_t pos = xmp.find(open);
    if (pos == std::string::npos)
        return {};
    const size_t gt = xmp.find('>', pos);
    if (gt == std::string::npos)
        return {};
    if (gt > pos && xmp[gt - 1] == '/')
        return {};
    const std::string close = std::string("</dc:") + name + ">";
    const size_t end = xmp.find(close, gt);
    if (end == std::string::npos)
        return {};
    const std::string inner = xmp.substr(gt + 1, end - (gt + 1));
    const std::vector<Li> items = rdf_li(inner);
    if (!items.empty()) {
        if (join_all) {
            std::string joined;
            for (size_t i = 0; i < items.size(); ++i) {
                if (i)
                    joined += ", ";
                joined += items[i].text;
            }
            return joined;
        }
        for (const Li& item : items) {
            if (item.lang == "x-default")
                return item.text;
        }
        return items.front().text;
    }
    return strip_tags(inner);
}

Rect rect_from(QPDFObjectHandle obj, const Rect& fallback) {
    if (!obj.isArray() || obj.getArrayNItems() < 4)
        return fallback;
    double v[4];
    for (int i = 0; i < 4; ++i) {
        QPDFObjectHandle item = obj.getArrayItem(i);
        if (!item.isNumber())
            return fallback;
        v[i] = item.getNumericValue();
    }
    const double x0 = std::min(v[0], v[2]);
    const double x1 = std::max(v[0], v[2]);
    const double y0 = std::min(v[1], v[3]);
    const double y1 = std::max(v[1], v[3]);
    return Rect(x0, y0, x1, y1);
}

std::string info_string(QPDFObjectHandle info, const char* key) {
    if (!info.isDictionary() || !info.hasKey(key))
        return {};
    QPDFObjectHandle v = info.getKey(key);
    if (!v.isString())
        return {};
    return trim(v.getUTF8Value());
}

std::pair<std::string, std::string> metadata(QPDF& qpdf) {
    // Snapshot /Info BEFORE reading XMP. pikepdf's open_metadata() migrates
    // /Info into XMP; qpdf does not, but the order is still the contract.
    const QPDFObjectHandle info = qpdf.getTrailer().getKey("/Info");
    const std::string info_title = info_string(info, "/Title");
    const std::string info_author = info_string(info, "/Author");

    std::string title;
    std::string author;
    try {
        QPDFObjectHandle meta = qpdf.getRoot().getKey("/Metadata");
        if (meta.isStream()) {
            std::shared_ptr<Buffer> buf = meta.getStreamData();
            const std::string xmp(reinterpret_cast<const char*>(buf->getBuffer()),
                                  buf->getSize());
            title = trim(xmp_dc(xmp, "title", false));
            author = trim(xmp_dc(xmp, "creator", true));
        }
    } catch (const std::exception&) {
        // Malformed XMP is common and not fatal.
    }

    if (title.empty())
        title = info_title;
    if (author.empty())
        author = info_author;
    return {title, author};
}

void walk_outlines(std::vector<QPDFOutlineObjectHelper> items,
                   int depth,
                   const std::map<QPDFObjGen, int>& page_index,
                   std::vector<OutlineItem>& out) {
    for (QPDFOutlineObjectHelper& item : items) {
        try {
            QPDFObjectHandle dest_page = item.getDestPage();
            if (!dest_page.isNull()) {
                auto it = page_index.find(dest_page.getObjGen());
                if (it != page_index.end())
                    out.push_back(OutlineItem{item.getTitle(), it->second, depth});
            }
        } catch (const std::exception&) {
            // Unresolvable destination: skip, keep walking children.
        }
        walk_outlines(item.getKids(), depth + 1, page_index, out);
    }
}

}  // namespace

SourceBook probe(const std::string& path) {
    QPDF qpdf;
    qpdf.setSuppressWarnings(true);
    qpdf.processFile(path.c_str());

    std::vector<SourcePage> pages;
    std::map<QPDFObjGen, int> page_index;
    const Rect letter(0.0, 0.0, 612.0, 792.0);

    int number = 0;
    for (QPDFPageObjectHelper page : QPDFPageDocumentHelper::get(qpdf).getAllPages()) {
        ++number;
        page_index[page.getObjectHandle().getObjGen()] = number;

        const Rect media = rect_from(page.getMediaBox(), letter);
        const Rect crop = rect_from(page.getCropBox(), media);

        int rotate = 0;
        QPDFObjectHandle rot = page.getAttribute("/Rotate", false);
        if (rot.isInteger())
            rotate = rot.getIntValueAsInt();
        rotate %= 360;
        if (rotate < 0)
            rotate += 360;

        pages.push_back(SourcePage{number, media, crop, rotate});
    }

    const auto meta = metadata(qpdf);

    std::vector<OutlineItem> outline;
    QPDFOutlineDocumentHelper& odh = QPDFOutlineDocumentHelper::get(qpdf);
    if (odh.hasOutlines())
        walk_outlines(odh.getTopLevelOutlines(), 0, page_index, outline);

    return SourceBook{path, std::move(pages), std::move(outline), meta.first, meta.second};
}

std::vector<Chapter> chapters_from_outline(const SourceBook& book, int min_gap) {
    std::vector<const OutlineItem*> tops;
    for (const OutlineItem& item : book.outline) {
        if (item.depth == 0)
            tops.push_back(&item);
    }
    if (tops.empty())
        return {};

    std::vector<Chapter> chapters;
    for (size_t position = 0; position < tops.size(); ++position) {
        const int first = tops[position]->page;
        const int last = (position + 1 < tops.size()) ? tops[position + 1]->page - 1
                                                      : book.page_count();
        if (last < first)
            continue;
        if (last - first + 1 < min_gap)
            continue;

        Chapter ch;
        ch.number = static_cast<int>(chapters.size()) + 1;
        ch.title = tops[position]->title;
        ch.first_page = first;
        ch.last_page = last;
        for (const OutlineItem& item : book.outline) {
            if (item.depth > 0 && first <= item.page && item.page <= last)
                ch.toc.push_back(TocEntry{item.title, item.page, item.depth - 1});
        }
        chapters.push_back(std::move(ch));
    }
    return chapters;
}

}  // namespace pb
