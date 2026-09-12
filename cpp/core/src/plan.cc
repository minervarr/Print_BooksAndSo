// plan.cc — the page-slot model.
//
// Copyright (C) 2026 nava. AGPLv3 or later; see LICENSE.

#include "printbooks/plan.hh"

#include <map>
#include <stdexcept>

namespace pb {

namespace {

void validate(const std::vector<Chapter>& chapters) {
    if (chapters.empty())
        throw std::invalid_argument("no chapters to plan");

    for (const Chapter& ch : chapters) {
        if (ch.first_page < 1)
            throw std::invalid_argument("chapter starts below page 1");
        if (ch.last_page < ch.first_page)
            throw std::invalid_argument("chapter runs backwards");
    }

    // Overlap means the outline was misread, and the symptom would be a page
    // silently printed twice rather than an error.
    std::map<int, int> owner;
    for (const Chapter& ch : chapters) {
        for (int page = ch.first_page; page <= ch.last_page; ++page) {
            auto it = owner.find(page);
            if (it != owner.end())
                throw std::invalid_argument("source page claimed by two chapters");
            owner[page] = ch.number;
        }
    }
}

}  // namespace

std::vector<Side> plan_sides(const std::vector<Chapter>& chapters, NotesMode notes) {
    validate(chapters);

    std::vector<Side> sides;
    int index = 1;
    auto emit = [&](SideKind kind, int chapter, std::optional<int> source_page = std::nullopt) {
        sides.push_back(Side{index, kind, chapter, source_page});
        ++index;
    };

    for (const Chapter& ch : chapters) {
        emit(SideKind::Portrait, ch.number);
        emit(SideKind::MiniToc, ch.number);

        if (notes == NotesMode::None) {
            for (int page = ch.first_page; page <= ch.last_page; ++page)
                emit(SideKind::Content, ch.number, page);
        } else {
            // The mini-TOC's facing page: a notes page to plan the chapter on.
            emit(SideKind::Notes, ch.number);
            for (int page = ch.first_page; page <= ch.last_page; ++page) {
                emit(SideKind::Content, ch.number, page);
                emit(SideKind::Notes, ch.number);
            }
        }

        // Parity: an odd run so far would put the next portrait on a verso.
        if (sides.size() % 2 == 1)
            emit(SideKind::Blank, ch.number);
    }

    return sides;
}

}  // namespace pb
