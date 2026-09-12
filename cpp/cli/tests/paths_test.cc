// paths_test.cc — default notebook path must not be the source book.
#undef NDEBUG
#include <cassert>
#include <cstdio>
#include <fstream>
#include <string>
#include <unistd.h>

#include "paths.hh"

using pb::cli::default_notebook_pdf;
using pb::cli::default_project_toml;
using pb::cli::same_regular_file;
using pb::cli::with_suffix;

static void test_notebook_is_not_the_source_pdf() {
    // The bug: with_suffix(project.toml, ".pdf") == the book's filename.
    assert(with_suffix("book.toml", ".pdf") == "book.pdf");
    assert(default_notebook_pdf("book.toml") == "book_notebook.pdf");
    assert(default_notebook_pdf("Michael Spivak - Calculus, 4th Edition (2008).toml") ==
           "Michael Spivak - Calculus, 4th Edition (2008)_notebook.pdf");
    assert(default_notebook_pdf("/tmp/a.toml") == "/tmp/a_notebook.pdf");
}

static void test_project_toml_from_book() {
    assert(default_project_toml("book.pdf") == "book.toml");
}

static void test_same_regular_file() {
    char dir[] = "/tmp/pb_paths_XXXXXX";
    assert(mkdtemp(dir) != nullptr);
    const std::string a = std::string(dir) + "/x";
    const std::string b = std::string(dir) + "/y";
    {
        std::ofstream(a.c_str()) << "a";
        std::ofstream(b.c_str()) << "b";
    }
    assert(same_regular_file(a, a));
    assert(!same_regular_file(a, b));
    assert(!same_regular_file(a, std::string(dir) + "/missing"));
    ::unlink(a.c_str());
    ::unlink(b.c_str());
    ::rmdir(dir);
}

int main() {
    test_notebook_is_not_the_source_pdf();
    test_project_toml_from_book();
    test_same_regular_file();
    std::printf("cli_paths_test: all assertions passed\n");
    return 0;
}
