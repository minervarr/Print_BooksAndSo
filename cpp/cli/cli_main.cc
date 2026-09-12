// cli_main.cc — print-books: turn a PDF book into a printable interleaved notebook.
//
// Copyright (C) 2026 nava. AGPLv3 or later; see LICENSE.
//
// Usage:
//     print-books init BOOK.pdf [-o project.toml] [--paper a4|letter] [--notes dots|lines|blank|none]
//     print-books build project.toml [-o out.pdf] [--chapters all|1|1,3-5]

#include <cctype>
#include <cstring>
#include <iostream>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <sys/stat.h>
#include <vector>

#include "freetype/glyphs_freetype.hh"
#include "printbooks/geometry.hh"
#include "printbooks/plan.hh"
#include "printbooks/render.hh"
#include "printbooks/units.hh"
#include "project.hh"
#include "qpdf/pdf_qpdf.hh"

namespace {

void usage(std::ostream& out) {
    out << "Turn a PDF book into a printable interleaved notebook.\n"
        << "\n"
        << "Usage:\n"
        << "    print-books init BOOK.pdf [-o project.toml] [--paper a4|letter] "
           "[--notes dots|lines|blank|none]\n"
        << "    print-books build project.toml [-o out.pdf] [--chapters all|1|1,3-5]\n";
}

bool is_regular_file(const std::string& path) {
    struct stat st;
    return ::stat(path.c_str(), &st) == 0 && S_ISREG(st.st_mode);
}

std::string trim(const std::string& s) {
    std::size_t i = 0;
    while (i < s.size() && std::isspace(static_cast<unsigned char>(s[i])))
        ++i;
    std::size_t j = s.size();
    while (j > i && std::isspace(static_cast<unsigned char>(s[j - 1])))
        --j;
    return s.substr(i, j - i);
}

// pathlib.Path.with_suffix: replace the last suffix of the filename, or
// append if the last component has none (a leading dot is not a suffix).
std::string with_suffix(const std::string& path, const std::string& suffix) {
    const auto slash = path.find_last_of("/\\");
    const auto start = (slash == std::string::npos) ? 0 : slash + 1;
    const auto dot = path.find_last_of('.');
    if (dot == std::string::npos || dot < start || dot == start)
        return path + suffix;
    return path.substr(0, dot) + suffix;
}

bool valid_paper(const std::string& name) {
    return name == "a4" || name == "letter";
}

bool valid_notes(const std::string& name) {
    return name == "dots" || name == "lines" || name == "blank" || name == "none";
}

pb::NotesMode notes_mode(const std::string& name) {
    if (name == "dots")
        return pb::NotesMode::Dots;
    if (name == "lines")
        return pb::NotesMode::Lines;
    if (name == "blank")
        return pb::NotesMode::Blank;
    if (name == "none")
        return pb::NotesMode::None;
    throw std::invalid_argument("unknown notes mode '" + name + "'");
}

std::vector<pb::Chapter> select_chapters(const std::vector<pb::Chapter>& chapters,
                                         const std::string& spec) {
    if (spec == "all")
        return chapters;
    std::set<int> wanted;
    std::istringstream ss(spec);
    std::string part;
    while (std::getline(ss, part, ',')) {
        part = trim(part);
        if (part.empty())
            continue;
        const auto dash = part.find('-');
        if (dash != std::string::npos) {
            const int lo = std::stoi(part.substr(0, dash));
            const int hi = std::stoi(part.substr(dash + 1));
            for (int n = lo; n <= hi; ++n)
                wanted.insert(n);
        } else {
            wanted.insert(std::stoi(part));
        }
    }
    std::vector<pb::Chapter> out;
    for (const pb::Chapter& ch : chapters) {
        if (wanted.count(ch.number))
            out.push_back(ch);
    }
    return out;
}

struct Args {
    std::string command;
    std::string positional;
    std::string output;
    std::string paper = "a4";
    std::string notes = "dots";
    std::string chapters = "all";
    bool saw_output = false;
    bool saw_paper = false;
    bool saw_notes = false;
    bool saw_chapters = false;
    bool help = false;
};

int fail_usage(const std::string& msg) {
    std::cerr << "error: " << msg << "\n";
    usage(std::cerr);
    return 2;
}

bool take_value(int& i, int argc, char** argv, std::string* out) {
    const char* eq = std::strchr(argv[i], '=');
    if (eq != nullptr && eq != argv[i]) {
        *out = eq + 1;
        return true;
    }
    if (i + 1 >= argc)
        return false;
    ++i;
    *out = argv[i];
    return true;
}

int parse_args(int argc, char** argv, Args* args) {
    if (argc < 2)
        return fail_usage("missing command");

    int i = 1;
    if (std::strcmp(argv[1], "-h") == 0 || std::strcmp(argv[1], "--help") == 0) {
        args->help = true;
        return 0;
    }
    args->command = argv[1];
    i = 2;

    for (; i < argc; ++i) {
        const char* a = argv[i];
        if (std::strcmp(a, "-h") == 0 || std::strcmp(a, "--help") == 0) {
            args->help = true;
            return 0;
        }
        std::string flag = a;
        const auto eq = flag.find('=');
        const std::string name = (eq == std::string::npos) ? flag : flag.substr(0, eq);

        if (name == "-o" || name == "--output") {
            if (!take_value(i, argc, argv, &args->output))
                return fail_usage(name + " needs a value");
            args->saw_output = true;
        } else if (name == "--paper") {
            if (!take_value(i, argc, argv, &args->paper))
                return fail_usage("--paper needs a value");
            args->saw_paper = true;
        } else if (name == "--notes") {
            if (!take_value(i, argc, argv, &args->notes))
                return fail_usage("--notes needs a value");
            args->saw_notes = true;
        } else if (name == "--chapters") {
            if (!take_value(i, argc, argv, &args->chapters))
                return fail_usage("--chapters needs a value");
            args->saw_chapters = true;
        } else if (a[0] == '-') {
            return fail_usage(std::string("unknown option '") + a + "'");
        } else if (args->positional.empty()) {
            args->positional = a;
        } else {
            return fail_usage(std::string("unexpected argument '") + a + "'");
        }
    }
    return 0;
}

int cmd_init(const Args& args) {
    if (args.positional.empty())
        return fail_usage("missing BOOK.pdf");
    if (args.saw_chapters)
        return fail_usage("init does not take --chapters");
    if (!valid_paper(args.paper))
        return fail_usage("paper must be a4 or letter");
    if (!valid_notes(args.notes))
        return fail_usage("notes must be dots, lines, blank, or none");
    if (!is_regular_file(args.positional)) {
        std::cerr << "error: " << args.positional << " not found\n";
        return 1;
    }

    const pb::SourceBook book = pb::probe(args.positional);
    std::vector<pb::Chapter> chapters = pb::chapters_from_outline(book);
    if (chapters.empty()) {
        pb::Chapter ch;
        ch.number = 1;
        ch.title = book.title.empty() ? std::string("Untitled") : book.title;
        ch.first_page = 1;
        ch.last_page = book.page_count();
        chapters.push_back(std::move(ch));
    }

    const std::string out =
        args.saw_output ? args.output : with_suffix(args.positional, ".toml");
    pb::write_project(out, args.positional, book.title, book.author, chapters,
                      args.paper, args.notes);
    std::cout << "  " << chapters.size() << " chapters from the PDF outline\n";
    std::cout << "  " << book.page_count() << " pages, " << book.outline.size()
              << " outline entries\n";
    std::cout << "  wrote " << out << "\n";
    return 0;
}

int cmd_build(const Args& args) {
    if (args.positional.empty())
        return fail_usage("missing project.toml");
    if (args.saw_paper || args.saw_notes)
        return fail_usage("build does not take --paper/--notes");
    if (!is_regular_file(args.positional)) {
        std::cerr << "error: " << args.positional << " not found\n";
        return 1;
    }

    const pb::Project project = pb::read_project(args.positional);
    if (project.chapters.empty()) {
        std::cerr << "error: " << args.positional << " declares no chapters\n";
        return 2;
    }
    if (project.book.empty()) {
        std::cerr << "error: missing book path\n";
        return 1;
    }
    if (!is_regular_file(project.book)) {
        std::cerr << "error: " << project.book << " not found\n";
        return 1;
    }

    std::vector<pb::Chapter> chapters;
    try {
        chapters = select_chapters(project.chapters, args.chapters);
    } catch (const std::exception&) {
        std::cerr << "error: invalid --chapters '" << args.chapters << "'\n";
        return 2;
    }
    if (chapters.empty()) {
        std::cerr << "error: --chapters selected nothing\n";
        return 2;
    }

    const pb::NotesMode notes = notes_mode(project.notes);
    const pb::SourceBook book = pb::probe(project.book);
    const std::vector<pb::Side> sides = pb::plan_sides(chapters, notes);

    const pb::FallbackGlyphs roman = pb::FallbackGlyphs::regular();
    const pb::FallbackGlyphs italic = pb::FallbackGlyphs::italic();
    const pb::Renderer renderer(
        pb::Layout{pb::paper(project.paper), pb::mm(15.0), pb::mm(10.0)},
        pb::GridSpec{}, pb::Style{}, pb::BookInfo{project.title, project.author},
        &roman, &italic, notes);

    const std::string out =
        args.saw_output ? args.output : with_suffix(args.positional, ".pdf");
    pb::emit(book, chapters, sides, renderer, out);

    const std::size_t sheets = (sides.size() + 1) / 2;
    std::cout << "  " << chapters.size() << " chapters, " << sides.size()
              << " sides -> " << sheets << " sheets\n";
    std::cout << "  wrote " << out << "\n";
    return 0;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc > 0)
        pb::set_program_path(argv[0]);
    try {
        Args args;
        const int parsed = parse_args(argc, argv, &args);
        if (parsed != 0)
            return parsed;
        if (args.help) {
            usage(std::cout);
            return 0;
        }
        if (args.command == "init")
            return cmd_init(args);
        if (args.command == "build")
            return cmd_build(args);
        std::cerr << "error: unknown command '" << args.command << "'\n";
        usage(std::cerr);
        return 2;
    } catch (const std::exception& e) {
        std::cerr << "error: " << e.what() << "\n";
        return 1;
    }
}
