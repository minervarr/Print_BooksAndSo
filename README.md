# Print_BooksAndSo

Turn a PDF book into a **printable notebook**. Every page of the book lands on a
left-hand sheet with a facing right-hand page for notes, every chapter opens with a
LaTeX-style portrait, and the output is shaped for the printer you actually own —
including cheap printers with no duplex unit.

Input a PDF. Output a PDF. No network, no AI, no service, no account.

> **Status:** the product is the C++17 `print-books` binary. `./print-books` at
> the repo root finds it and `exec`s it — no venv, no pikepdf. `prototype/` is a
> historical reference kept for later golden diffs.

```console
$ scripts/linux/build.sh
Binaries in build/linux/:
  cli/print-books -- init and build a printable notebook

  ./print-books init BOOK.pdf
  ./print-books build project.toml

$ ./print-books init ~/Books/atomic_habits.pdf -o habits.toml
  19 chapters from the PDF outline
  wrote habits.toml

$ ./print-books build habits.toml --chapters 1
  1 chapters, 38 sides -> 19 sheets
  wrote habits.toml.pdf
```

(`init` status about the crop box is the designed interface; sampled ink bbox is
not in this build yet — `build` uses each page's CropBox.)

## The decisions, and why

**The unit of imposition is a *side*, not a page.** A chapter is a portrait on a
recto, a mini-TOC on its verso, then one spread per source page: content on the
left, notes on the right. Five invariants fall out and they are the tests — portraits
on rectos, content on versos, every content page facing a notes page, `4 + 2N` sides
per chapter, every source page exactly once. Getting any of them wrong is invisible
until you have printed forty sheets.

**The mini-TOC costs a sheet, and that was a choice.** The back of each portrait
carries the chapter's own sub-sections and page numbers. It is not free: landing on
side 2 obliges side 3 to be its facing page, so a chapter runs `4 + 2N` sides rather
than `2 + 2N`. The design was briefly wrong about this, and the symptom was the last
content page of every chapter having no notes page beside it.

**Nothing is ever rendered.** Source pages are referenced as Form XObjects, never
decoded. The dot grid is one shared XObject referenced N times, not drawn per page.
That is the entire performance story, and it is why a 400-page book builds in well
under a second.

**One crop box for the whole book.** Pages are cropped to their ink and scaled up,
but from a 16-page sample, cached — not per page. Per-page cropping makes text size
jitter as you read, because a short chapter-ending page gets blown up while the next
is normal. It is also 26 s slower on a 500-page book, measured. (Sampled bbox is
not wired into this build yet; see Known gaps in `CLAUDE.md`.)

**Generated text is glyph outlines, not an embedded font.** Real Computer Modern with
no font dictionary, no CID map, no subsetting. The trade: the portraits and footers
are not searchable. The book's own pages are untouched and stay searchable.

**Ink is a cost.** The notes page is a 0.25 mm dot grid at 25 % gray, not lines — and
the page centre is marked by four small ticks at the edge midpoints instead of two
full crosshairs. You get both axes for about eight path operators.

**C++ is the engine; `./print-books` is the front door.** The CLI, probe, plan,
render and emit path live in C++17 (`cpp/`). The repo-root script only finds
`build/*/cli/print-books` (or `$PRINT_BOOKS_BIN` / `PATH`) and replaces itself with
it. The Python 3.13 `prototype/` tree remains on disk as the reference the golden
tests will diff against — it is not the product front door.

## Layout

```
print-books   front door (stdlib locator → exec the C++ binary).
python/       locator module + tests.
cpp/          C++17 product. cpp/CMakeLists.txt is the project() root.
  core/       PURE: no OS headers, no PDF library, no I/O. Plans and decides.
  backend/    qpdf, freetype, toml++ (submodules under third_party/).
  cli/        -> print-books  (init + build)
prototype/    historical Python 3.13 reference (pikepdf/fontTools); golden diffs.
assets/fonts/ Latin Modern Roman, regular and italic.
fixtures/     tiny synthetic PDFs for tests.
docs/         the design spec + port handoff.
scripts/linux/build.sh   Matrix-shaped: --debug/--release/--share/--packages/--asan
```

## Building

```bash
# C++ binary (prompts on a TTY; non-interactive → Release, Universal)
scripts/linux/build.sh              # -> build/linux/cli/print-books
scripts/linux/build.sh debug        # -> build/linux_debug/cli/print-books + tests
scripts/linux/build.sh --asan
scripts/linux/build.sh --share      # four microarch variants → dist/linux/*.tar.gz
scripts/linux/build.sh --packages   # Arch makepkg (needs packaging/arch/PKGBUILD)

ctest --test-dir build/linux_debug --output-on-failure

# Drive it (after a build; no venv)
./print-books init fixtures/mini_book.pdf -o /tmp/mini.toml
./print-books build /tmp/mini.toml -o /tmp/mini_nb.pdf
```

Optional: `PRINT_BOOKS_BIN=/path/to/print-books` overrides discovery. Prereqs for
the C++ build: cmake ≥ 3.22, ninja, a C++17 compiler, plus OS `zlib` and `libjpeg`
(qpdf's CMake `find_package`s them).

The prototype still builds under Python 3.13 in a venv if you need it for goldens;
that pin is prototype-only — the product launcher runs on current system Python.

## Licence

Copyright (C) 2026 nava. AGPLv3 or later; see `LICENSE`.
