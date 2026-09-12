// paths.hh — CLI path helpers. Header-only so cli_main and its test share one
// definition. Default notebook output must NEVER be the source book: replacing
// the suffix of project.toml with .pdf lands on BOOK.pdf, which is what the
// TOML's `book =` line already names.
#pragma once

#include <string>
#include <sys/stat.h>

namespace pb {
namespace cli {

inline std::string with_suffix(const std::string& path, const std::string& suffix) {
    const auto slash = path.find_last_of("/\\");
    const auto start = (slash == std::string::npos) ? 0 : slash + 1;
    const auto dot = path.find_last_of('.');
    if (dot == std::string::npos || dot < start || dot == start)
        return path + suffix;
    return path.substr(0, dot) + suffix;
}

inline std::string default_notebook_pdf(const std::string& project_path) {
    return with_suffix(project_path, "_notebook.pdf");
}

inline std::string default_project_toml(const std::string& book_path) {
    return with_suffix(book_path, ".toml");
}

inline bool same_regular_file(const std::string& a, const std::string& b) {
    if (a == b)
        return true;
    struct stat sa {};
    struct stat sb {};
    if (::stat(a.c_str(), &sa) != 0 || ::stat(b.c_str(), &sb) != 0)
        return false;
    return sa.st_dev == sb.st_dev && sa.st_ino == sb.st_ino;
}

inline bool ends_with_ci(const std::string& s, const std::string& suf) {
    if (s.size() < suf.size())
        return false;
    for (std::size_t i = 0; i < suf.size(); ++i) {
        unsigned char a = static_cast<unsigned char>(s[s.size() - suf.size() + i]);
        unsigned char b = static_cast<unsigned char>(suf[i]);
        if (a >= 'A' && a <= 'Z')
            a = static_cast<unsigned char>(a - 'A' + 'a');
        if (b >= 'A' && b <= 'Z')
            b = static_cast<unsigned char>(b - 'A' + 'a');
        if (a != b)
            return false;
    }
    return true;
}

// "niu", "niu.pdf", "niu.PDF" → "niu1.pdf" for chapter 1.
inline std::string strip_pdf_suffix(const std::string& path) {
    if (ends_with_ci(path, ".pdf"))
        return path.substr(0, path.size() - 4);
    return path;
}

inline std::string chapter_pdf(const std::string& name, int chapter) {
    return strip_pdf_suffix(name) + std::to_string(chapter) + ".pdf";
}

}  // namespace cli
}  // namespace pb
