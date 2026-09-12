// cli_main.cc — print-books: turn a PDF book into a printable interleaved notebook.
//
// Copyright (C) 2026 nava. AGPLv3 or later; see LICENSE.
//
// Usage:
//     print-books                         # questions, then init + build
//     print-books BOOK.pdf                # same, book path filled in
//     print-books init BOOK.pdf [-o project.toml] [--paper a4|letter] [--notes dots|lines|blank|none]
//     print-books build project.toml [-o out.pdf] [--chapters all|1|1,3-5]
//
// Default build output is <project>_notebook.pdf, never the source book.

#include <cctype>
#include <cstring>
#include <iostream>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unistd.h>
#include <vector>

#include "freetype/glyphs_freetype.hh"
#include "paths.hh"
#include "printbooks/geometry.hh"
#include "printbooks/plan.hh"
#include "printbooks/render.hh"
#include "printbooks/units.hh"
#include "project.hh"
#include "qpdf/pdf_qpdf.hh"

namespace {

using pb::cli::chapter_pdf;
using pb::cli::default_notebook_pdf;
using pb::cli::default_project_toml;
using pb::cli::ends_with_ci;
using pb::cli::same_regular_file;
using pb::cli::strip_pdf_suffix;
using pb::cli::with_suffix;

void usage(std::ostream& out) {
    out << "Turn a PDF book into a printable interleaved notebook.\n"
        << "\n"
        << "Usage:\n"
        << "    print-books                         ask, then init + build\n"
        << "    print-books BOOK.pdf                same, with the book filled in\n"
        << "    print-books init BOOK.pdf [-o project.toml] [--paper a4|letter]\n"
        << "                                [--notes dots|lines|blank|none]\n"
        << "    print-books build project.toml [-o out.pdf] [--chapters all|1,3-5]\n"
        << "                                [--split]   # -o niu  → niu1.pdf, niu2.pdf, …\n";
}

bool is_regular_file(const std::string& path) {
    struct stat st {};
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
    bool split = false;
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
    if (argc < 2) {
        args->command = "wizard";
        return 0;
    }

    int i = 1;
    if (std::strcmp(argv[1], "-h") == 0 || std::strcmp(argv[1], "--help") == 0) {
        args->help = true;
        return 0;
    }

    const std::string first = argv[1];
    if (first == "init" || first == "build" || first == "wizard") {
        args->command = first;
        i = 2;
    } else if (ends_with_ci(first, ".pdf")) {
        args->command = "wizard";
        args->positional = first;
        i = 2;
    } else if (ends_with_ci(first, ".toml")) {
        args->command = "build";
        args->positional = first;
        i = 2;
    } else {
        args->command = first;
        i = 2;
    }

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
        } else if (name == "--split") {
            args->split = true;
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

std::string ask_line(const std::string& prompt, const std::string& def) {
    std::cout << prompt;
    if (!def.empty())
        std::cout << " [" << def << "]";
    std::cout << ": " << std::flush;
    std::string line;
    if (!std::getline(std::cin, line))
        throw std::runtime_error("input closed");
    line = trim(line);
    return line.empty() ? def : line;
}

int ask_choice(const std::string& prompt, int n, int def) {
    std::cout << prompt << " [" << def << "]: " << std::flush;
    std::string line;
    if (!std::getline(std::cin, line))
        throw std::runtime_error("input closed");
    line = trim(line);
    if (line.empty())
        return def;
    const int v = std::stoi(line);
    if (v < 1 || v > n)
        throw std::invalid_argument("choice must be 1.." + std::to_string(n));
    return v;
}

int refuse_clobber(const std::string& out, const std::string& book) {
    if (!same_regular_file(out, book) && out != book)
        return 0;
    std::cerr << "error: refusing to write the notebook over the source book:\n"
              << "  " << book << "\n"
              << "  use -o some_other.pdf  (default is *_notebook.pdf)\n";
    return 1;
}

int cmd_init(const Args& args) {
    if (args.positional.empty())
        return fail_usage("missing BOOK.pdf");
    if (args.saw_chapters)
        return fail_usage("init does not take --chapters");
    if (args.split)
        return fail_usage("init does not take --split");
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
        args.saw_output ? args.output : default_project_toml(args.positional);
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
        return fail_usage("build does not take --paper/--notes (they live in the TOML)");
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

    const pb::FallbackGlyphs roman = pb::FallbackGlyphs::regular();
    const pb::FallbackGlyphs italic = pb::FallbackGlyphs::italic();
    const pb::Renderer renderer(
        pb::Layout{pb::paper(project.paper), pb::mm(15.0), pb::mm(10.0)},
        pb::GridSpec{}, pb::Style{}, pb::BookInfo{project.title, project.author},
        &roman, &italic, notes);

    auto write_one = [&](const std::vector<pb::Chapter>& chs, const std::string& out) -> int {
        if (const int r = refuse_clobber(out, project.book))
            return r;
        const std::vector<pb::Side> sides = pb::plan_sides(chs, notes);
        pb::emit(book, chs, sides, renderer, out);
        const std::size_t sheets = (sides.size() + 1) / 2;
        std::cout << "  " << chs.size() << " chapter" << (chs.size() == 1 ? "" : "s")
                  << ", " << sides.size() << " sides -> " << sheets << " sheets\n";
        std::cout << "  wrote " << out << "\n";
        return 0;
    };

    if (args.split) {
        const std::string stem = strip_pdf_suffix(
            args.saw_output ? args.output : with_suffix(args.positional, ""));
        for (const pb::Chapter& ch : chapters) {
            const std::string out = chapter_pdf(stem, ch.number);
            if (const int r = write_one({ch}, out))
                return r;
        }
        return 0;
    }

    const std::string out =
        args.saw_output ? args.output : default_notebook_pdf(args.positional);
    return write_one(chapters, out);
}

int cmd_wizard(Args args) {
    if (!::isatty(STDIN_FILENO) || !::isatty(STDOUT_FILENO))
        return fail_usage("missing command (not a terminal — pass init or build)");

    std::cout << "print-books — printable interleaved notebook\n\n";

    if (args.positional.empty()) {
        args.positional = ask_line("Path to the PDF book", "");
        if (args.positional.empty())
            return fail_usage("need a PDF path");
    }
    if (!is_regular_file(args.positional)) {
        std::cerr << "error: " << args.positional << " not found\n";
        return 1;
    }

    if (!args.saw_paper) {
        std::cout << "Paper size:\n"
                  << "  1) A4 (default)\n"
                  << "  2) US Letter\n";
        args.paper = (ask_choice("Enter choice", 2, 1) == 2) ? "letter" : "a4";
        args.saw_paper = true;
    }

    if (!args.saw_notes) {
        std::cout << "Notes pages facing each book page?\n"
                  << "  1) Yes — dot grid (default)\n"
                  << "  2) Yes — blank paper\n"
                  << "  3) No  — book on both sides of the sheet\n";
        switch (ask_choice("Enter choice", 3, 1)) {
            case 2: args.notes = "blank"; break;
            case 3: args.notes = "none"; break;
            default: args.notes = "dots"; break;
        }
        args.saw_notes = true;
    }

    std::cout << "Two-sided printing: this program writes a sequential PDF\n"
              << "(page 1, page 2, …). Duplex shuffle for a printer with no\n"
              << "duplex unit is not built yet — use the printer driver, or\n"
              << "print odd then even pages.\n";

    const std::string toml = default_project_toml(args.positional);
    Args init = args;
    init.positional = args.positional;
    init.saw_output = true;
    init.output = toml;
    const int ir = cmd_init(init);
    if (ir != 0)
        return ir;

    if (!args.saw_chapters) {
        std::cout << "Chapters to print (all, or e.g. 1,3-5)\n";
        args.chapters = ask_line("Chapters", "all");
        args.saw_chapters = true;
    }

    std::cout << "Output files:\n"
              << "  1) One PDF (default)\n"
              << "  2) One PDF per chapter  (niu1.pdf, niu2.pdf, …)\n";
    args.split = (ask_choice("Enter choice", 2, 1) == 2);

    const std::string toml_stem = with_suffix(toml, "");
    if (args.split) {
        const std::string name = ask_line(
            "Name for the files (.pdf is optional; chapter number is appended)", toml_stem);
        args.output = name;
        args.saw_output = true;
        std::cout << "  will write " << chapter_pdf(name, 1) << ", "
                  << chapter_pdf(name, 2) << ", …\n";
    } else if (!args.saw_output) {
        args.output = ask_line("Output PDF", default_notebook_pdf(toml));
        args.saw_output = true;
    }

    Args build;
    build.command = "build";
    build.positional = toml;
    build.output = args.output;
    build.saw_output = args.saw_output;
    build.chapters = args.chapters;
    build.saw_chapters = args.saw_chapters;
    build.split = args.split;
    return cmd_build(build);
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
        if (args.command == "wizard")
            return cmd_wizard(args);
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
