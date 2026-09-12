// project.hh — generated, hand-editable project TOML.
//
// Copyright (C) 2026 nava. AGPLv3 or later; see LICENSE.
//
// Writer is ours (quote-escape like the Python prototype). Reader uses toml++
// and fills std::vector<Chapter>. core/ never sees the file format.
#pragma once

#include <string>
#include <vector>

#include "printbooks/plan.hh"

namespace pb {

void write_project(const std::string& out_path,
                   const std::string& book_path,
                   const std::string& title,
                   const std::string& author,
                   const std::vector<Chapter>& chapters,
                   const std::string& paper,
                   const std::string& notes);

// Everything `build` needs from the generated TOML. `read_chapters` is the
// chapters field of the same parse.
struct Project {
    std::string book;
    std::string title;
    std::string author;
    std::string paper = "a4";
    std::string notes = "dots";
    std::vector<Chapter> chapters;
};

Project read_project(const std::string& path);
std::vector<Chapter> read_chapters(const std::string& path);

}  // namespace pb
