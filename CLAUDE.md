# CLAUDE.md

Guidance for Claude Code (claude.ai/code) working in this repository.
The workspace-level `../CLAUDE.md` is authoritative for anything shared;
this file covers what is specific to Print_BooksAndSo.

## What this is

A tool that turns a PDF book into a **printable interleaved notebook**: every source
page lands on a left-hand page with a facing right-hand page for notes, each chapter
opens with a LaTeX-style portrait, and the output is shaped for the printer you
actually own — including cheap printers with no duplex unit. Input a PDF, output a
PDF. Fully offline: no network, no AI, no service.

It is **two implementations of one design** — a Python 3.13 prototype and a C++17
port. The design lives in `docs/superpowers/specs/`. Read that before changing
behaviour; read this before changing structure.

## Two implementations, and the names are mirrored on purpose

`prototype/core/plan.py` and `cpp/core/src/plan.cc` hold the same logic under the
same name, and `prototype/tests/test_plan.py` and `cpp/core/tests/plan_test.cc`
assert the same facts. That is not tidiness — it is what makes the port mechanical
instead of a redesign. **When you add a concept, add it to both sides under the same
name, or add it to neither.** A file that exists on one side only is a bug report
about this repo's structure.

The prototype is not throwaway. It stays as the reference implementation the golden
tests diff against.

## `core/` never imports a PDF library, and a test enforces it

`core/` is portable, pure, and has no I/O: it parses, plans and decides, and it
**never touches a PDF object**. `backend/` is the only place pikepdf, qpdf, freetype,
fontTools or a subprocess may appear — it is this repo's equivalent of the
`platform/<os>/` directory the rest of the workspace uses.

A test asserts `prototype/core/` imports nothing outside the standard library, so
the boundary cannot rot quietly. The C++ side enforces the same thing structurally:
**no `core/*_test` target may list a `backend/` source**, which is visible in one
CMake file. If a core test's link line ever needs `libqpdf`, something leaked in.

## Content streams are text, which is why the drawing code is pure

A PDF content stream is a string of operators. So `core/drawing.py` and
`core/src/drawing.cc` **emit text**, and their tests assert on the operators emitted.
The PDF library's entire job is object plumbing: import a page as a Form XObject,
attach a stream, write the file.

This is not a cute trick. Page drawing is normally the untestable part of a program
like this, and moving it into `core` as string generation is what buys real tests on
it. `QPDFPageObjectHelper::placeFormXObject()` returns a `std::string` for exactly
this reason — the design follows qpdf's grain, it does not fight it.

## Nothing is ever rendered, and that is the whole performance story

Source page content is **referenced by object, never decoded and never re-encoded**.
The dot grid is written **once** as a shared Form XObject and referenced N times, not
drawn per page. Output is written unlinearized. A 400-page book must build in well
under a second once the crop box is cached; if it does not, something is bypassing
the object-copy path and rendering instead.

The dot grid's own stream is one path: line width set to the dot diameter, `1 J`
round cap, every dot a degenerate subpath, **one `S` at the end**. An A4 content
area at a 5 mm pitch is 1890 dots: 73 KB of stream raw, 7.6 KB Flate-compressed,
one stroke operator -- and written **once** for the whole document, however many
pages reference it. (Measured, not estimated; the first draft of this file
guessed 2400 dots and 30 KB and was wrong about both.)

## One crop box for the whole book, and that is not laziness

Source pages are cropped to their ink and scaled up to use the sheet. That crop is
computed **once for the entire book** from a ~16-page sample, not per page.

Two reasons, and the second is the real one:

1. **Measured:** `gs -sDEVICE=bbox` over 499 pages takes **26 s** (~52 ms/page). Far
   too slow to sit in the hot path. The sample runs at `init` and the result is
   cached in the project TOML, so every rebuild after that is instant.
2. **Per-page cropping is worse typography.** A book is typographically uniform. Crop
   each page to its own ink and a short chapter-ending page gets blown up while the
   next is normal — text size would visibly jitter as you read. One crop box is not
   an approximation of the per-page answer; it is the better answer.

Blank pages return `0 0 0 0` from the bbox device. Discard them from the sample
rather than letting them collapse the union.

## The generated text is outlines, not an embedded font

Chapter portraits, chapter mini-TOCs and page footers are drawn by asking the font
for each glyph's outline and emitting PDF path operators — `m`, `c`, `h`, then `f`.
No font dictionary, no CID map, no subsetting, on either side of the port. The
backend's entire font duty is *"give me the outline of glyph G"*: a fontTools pen in
Python, `FT_Outline_Decompose` in C++.

Latin Modern is CFF-flavoured OTF, so its outlines are **already cubic** and map
straight onto PDF's `c` with no quadratic conversion. Fill with `f` (nonzero
winding), which is what CFF expects.

The consequence to know: **text we generate is not selectable or searchable.** The
original book pages are untouched and stay fully searchable. That trade was made
deliberately for a print-targeted artifact — it removes the fiddliest code in the
project from both implementations. Do not "fix" it without reading the spec.

## Portrait on a recto, content on a verso — the parity is the spec

The unit of imposition is a `Side`, not a page. A chapter is:

| Side | Content |
|---|---|
| 1 (recto) | chapter portrait |
| 2 (verso) | chapter mini-TOC |
| 3 (recto) | notes — faces the mini-TOC, for planning the chapter |
| 4 (verso) | source page 1 |
| 5 (recto) | notes |
| … | … |
| 2N+2 (verso) | source page N |
| 2N+3 (recto) | notes |
| 2N+4 (verso) | blank — parity, so the next portrait is a recto |

Open the book and you see the portrait alone, then `mini-TOC | notes`, then
`source page | notes` for every page of the chapter. **Five** invariants hold,
and they are the tests:

- every portrait is on a **recto**
- every content page is on a **verso**
- every content page **faces a notes page**
- sides per chapter == **`4 + 2N`**
- source pages appear **exactly once, in order**

**`4 + 2N`, and the fourth invariant is why.** This was first designed as
`2 + 2N`, on the belief that the mini-TOC rode along on the parity side for
free. It does not: landing on side 2 obliges side 3 to be its facing page, so
the mini-TOC costs **one sheet per chapter**, not nothing. The error was
invisible in every rule except one — the *last* content page of each chapter
faced the next chapter's portrait instead of a notes page — which is exactly
why `test_every_content_page_faces_a_notes_page` exists. At `2 + 2N` there is
room for only one page beyond portrait + content + notes, and it must sit on
the chapter's final verso. Paying the sheet was a deliberate choice; do not
"optimise" it back without re-reading that test.

`--notes none` is not a special case in the code. It is a different `Plan` through
the same engine.

## Python 3.13 in a venv, and both halves of that are deliberate

**3.13, not 3.14**, because pikepdf ships a `cp313` manylinux wheel and 3.13 needs no
compiler. **In a venv**, because this machine's system `python3` *is* 3.14 — there is
no other way to pin 3.13.

This repo is also the **first Python project in this workspace**. There is no
`pyproject.toml`, venv, pytest config or formatter config in any sibling repo; all
first-party Python elsewhere is one-off `tools/*.py` generators run against system
site-packages. So `prototype/pyproject.toml` *establishes* a convention rather than
following one. That is intentional — do not "correct" it into the `tools/` style.
What is kept from that style: a why-first module docstring and a `Usage:` line on
every entry point.

## Build

```bash
# Prototype
python3.13 -m venv prototype/.venv
prototype/.venv/bin/pip install -e prototype[dev]

# C++ — cpp/CMakeLists.txt is the project() root; the repo root has no CMake file,
# following archive_engine, whose core/CMakeLists.txt is its entry point.
scripts/linux/build.sh              # prompts on a TTY, Release otherwise
scripts/linux/build.sh debug        # + tests
```

## Tests

```bash
prototype/.venv/bin/pytest prototype/tests -q

cmake -S cpp -B cpp/build/linux_debug -G Ninja -DCMAKE_BUILD_TYPE=Debug
cmake --build cpp/build/linux_debug -j"$(nproc)"
ctest --test-dir cpp/build/linux_debug --output-on-failure
```

Assert-based, Debug-only, no framework. Each test **compiles the real sources it
exercises and links nothing else** — worth protecting more than the assertions,
because it is what keeps a test from quietly depending on a PDF library. Test
sources `#undef NDEBUG` so asserts survive Release.

Rendering has no automated tests. It is verified by **proof capture**:
`print-books proof` writes PNGs via `pdftoppm`, the same way the rest of this
workspace verifies drawing. Look at the sheets.

## Committing

Use `./git_wrapper commit "<message>"` — bare message, identity forced, **no
`Co-Authored-By`, no `Claude-Session`, no 🤖**. This overrides the default commit
convention. `git_wrapper` is a local tool and is gitignored, like in every sibling
repo; copy it from the workspace root. See the workspace `CLAUDE.md`.

## Known gaps

The repo is scaffolded and the design is settled; **the implementation has not
started**. Nothing below `prototype/` or `cpp/` is written yet.

Deferred deliberately, and not to be treated as oversights:

- **No TOC scraping.** Chapters come from the PDF outline, or you write the page
  ranges into the project TOML by hand. The dot-leader heuristic for books with no
  outline is a later phase.
- **No booklet imposition.** Sequential leaves only (punch/binder/spiral). The
  page-slot model is shaped so a saddle-stitch strategy drops in beside it, but it
  does not exist.
- **No GUI.** CLI plus a project TOML. `core/` never learns who called it, so a GUI
  can be added later without touching it.
- **Generated text is not searchable.** See above; this is a decision, not a gap.

Nothing more is claimed.
