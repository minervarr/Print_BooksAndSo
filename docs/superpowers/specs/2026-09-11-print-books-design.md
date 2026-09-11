# Print_BooksAndSo — design & implementation plan

## Context

There is no tool that turns a PDF book into something you can *work in*. Reading a
book and taking notes means either writing in the margins of a bought copy or
keeping notes in a separate place where they lose their anchor to the page that
provoked them.

This project takes a PDF and emits a **printable interleaved notebook**: every
source page lands on a left-hand page with a facing right-hand page for notes, each
chapter opens with a LaTeX-style portrait, and the output is shaped for the printer
you actually own — including cheap printers with no duplex unit. It must work fully
offline, with no AI and no network, and it must be fast enough that regenerating a
400-page book is not something you wait for.

The repo is `https://github.com/minervarr/Print_BooksAndSo.git` — created, empty,
no commits yet (`git ls-remote` returns nothing).

Two deliverables, deliberately: a **Python 3.13 prototype** to get the paper right
quickly, and a **C++17 port** for speed and for consistency with the rest of the
workspace. The directory and module names are mirrored so the port is mechanical
rather than a redesign.

---

## Decisions settled during brainstorming

| Question | Decision |
|---|---|
| Front door | CLI + a generated, hand-editable TOML project file. No GUI in v1; `core/` never learns who called it, so a GUI can be added later with zero rework. |
| Binding | Sequential leaves (punch/binder/spiral), left-edge gutter. The page-slot model is shaped so saddle-stitch booklet imposition drops in later as a second strategy. |
| Chapter portrait | LaTeX `\chapter` head: letterspaced small-caps kicker, 0.4 pt hairline rule, 24 pt ragged-right title on the upper third, book identity + page range in 8.5 pt italic at the foot. |
| The parity side | Back of the portrait becomes the chapter's **mini-TOC** (sub-sections + page numbers from the outline tree), falling back to a dot page. Costs zero extra paper. |
| Generated text | **Glyph outlines as vector paths.** No font embedding, no CID dictionaries, no subsetting. Generated furniture is not searchable; original book pages are untouched and stay searchable. |
| Content fit | One crop box for the whole book from a sampled ink bbox, cached in the project file. Not per-page. |

### Assumptions (stated, not asked)

A4 default and configurable; left-edge gutter; LTR; `git_wrapper_exe` copied to the
repo root as `./git_wrapper`, matching every sibling repo in the workspace.

---

## Verified facts this plan rests on

Checked on this machine, not assumed:

- `python3.13` present at `/usr/bin/python3.13` alongside 3.14.
- **pikepdf 10.13.0.post1 ships `cp313-cp313-manylinux…x86_64.whl`** — installs on
  3.13 with no compiler. (This is why 3.13, not 3.14.)
- **`libqpdf` 12.4.1 with headers** at `/usr/include/qpdf`, `pkg-config libqpdf` works.
- The port's linchpin exists in those headers:
  `QPDFPageObjectHelper::getFormXObjectForPage()` (line 319) and
  `placeFormXObject()` (line 336) — **and `placeFormXObject` returns a
  `std::string` content-stream fragment**, which is exactly the shape the pure-core
  design needs. pikepdf's `Page.as_form_xobject()`/`add_overlay()` wrap the same
  qpdf calls, so prototype and port drive one engine.
- `freetype2` 26.6.20 system-wide; also already the workspace's vendored submodule pattern.
- `tomlplusplus` 3.4.0 at `/usr/include/toml++` (header-only).
- Latin Modern OTF at `/usr/share/texmf-dist/fonts/opentype/public/lm/` **and already
  vendored in the workspace** at `vulkan_font_engine/tools/atlas_gen/fonts/lmroman10-regular.otf`.
  111–119 KB per face. CFF-flavoured, so outlines are already cubic → straight to PDF `c`.
- `pdftoppm` 26.08 for proof rendering; `gs` for the bbox sample.
- Toolchain: g++ 16.2.1, CMake 4.4.3, Ninja 1.13.2.
- `fontTools` is **not** installed → goes in the prototype venv (pure-Python wheel).

**Measured risk that shaped the design:** `gs -sDEVICE=bbox` over 499 pages took
**26 s** (~52 ms/page). Far too slow for the hot path. Hence sampling + caching, which
is also better typography — see "Fit" below.

---

## Repo layout

Module names mirrored across both implementations so the port is mechanical:
`plan.py` ↔ `plan.cpp`, `test_plan.py` ↔ `plan_test.cc`.

```
Print_BooksAndSo/
  CLAUDE.md  README.md  LICENSE  .gitignore  git_wrapper
  assets/fonts/               lmroman10-{regular,italic}.otf   (shared by both)
  fixtures/                   tiny synthetic PDFs + golden JSON plans
  docs/superpowers/specs/

  prototype/                  Python 3.13
    pyproject.toml            requires-python = "==3.13.*"; console script "print-books"
    .venv/                    gitignored; python3.13 -m venv (see "New territory" below)
    core/                     PURE: stdlib only. Never imports pikepdf. Enforced by a test.
      units.py                mm/pt conversion, A4/Letter constants
      geometry.py             Rect, Size, fit-into, gutter shift, crop resolution
      project.py              the TOML project model + a small TOML writer
      outline.py              outline tree → chapters + mini-TOC entries
      plan.py                 page-slot model + imposition strategies
      drawing.py              PDF content-stream emitters (grid, ticks, portrait, TOC, footer)
      text.py                 outline-path text layout; consumes the GlyphSource protocol
      metrics.py              GlyphSource + FontMetrics protocols (no implementation)
      printer.py              printer profiles + the manual-duplex backs transform
    backend/                  the ONLY place a PDF library or subprocess appears
      pdf_pikepdf.py          probe + emit
      glyphs_fonttools.py     GlyphSource via fontTools pens
      bbox_gs.py              sampled ink bbox via ghostscript
      proof.py                pdftoppm proof renderer
    cli/main.py               argparse front door
    tests/                    pytest against core/ only — passes with no PDF lib installed

  cpp/
    CMakeLists.txt            THE project() root — the repo root has none, following
                              archive_engine, whose core/CMakeLists.txt is its entry point
    core/CMakeLists.txt       printbooks_core (STATIC)
    core/include/printbooks/  units.hh geometry.hh project.hh outline.hh plan.hh
                              drawing.hh text.hh metrics.hh printer.hh
    core/src/                 same names .cc
    core/tests/               *_test.cc — plain assert(), #undef NDEBUG line 1
    backend/qpdf/             pdf_qpdf.{hh,cc}
    backend/freetype/         glyphs_freetype.{hh,cc}
    backend/gs/               bbox_gs.{hh,cc}
    cli/CMakeLists.txt        printbooks_cli, OUTPUT_NAME print-books
    cli/cli_main.cc
    third_party/              toml++ single header (vendored for reproducibility)
  scripts/linux/build.sh      cmake -S cpp -B cpp/build/linux…
```

`core/` carries the same promise it carries in Matrix_Player and Economycs: no OS
headers, no PDF library, no I/O. `backend/` is this repo's `platform/<os>/` — the one
place the outside world exists. Header extension `.hh` and source `.cc` to match
Economycs and archive_engine; include prefix `printbooks/` so `#include
<printbooks/plan.hh>` reads the way `<economycs/money.hh>` and `<arc/fs/paths.hh>` do.

---

## The core model

Four stages. Exactly one is impure.

**1. Probe** *(backend)* → a `SourceBook` data record: page count, each page's
MediaBox/CropBox/Rotate, the outline tree, `/Info` + XMP metadata. Handed to core as
plain data; core never touches a PDF object.

**2. Plan** *(pure)* → an ordered list of `Side` values, each one of:

- `Portrait{chapter}`
- `MiniToc{chapter, entries}`
- `Content{src_page, placement}`
- `Notes{grid, footer}`
- `Blank`

Each `Side` carries its index, its recto/verso parity, and the gutter edge. This is
the load-bearing abstraction, because it makes the rules *assertable*:

- every `Portrait` is on a recto
- every `Content` is on a verso
- sides per chapter == `2 + 2N`
- source pages appear exactly once, in order

**3. Render** *(pure)* → each `Side` becomes a PDF **content-stream string** plus the
resource names it references. PDF content streams are text, so the drawing code is
pure and unit-testable — the part that is normally untestable.

**4. Emit** *(backend)* → pikepdf/qpdf assembles the document: each source page
imported as a Form XObject, our content stream attached, the dot grid written **once**
as a shared XObject.

### Why this is fast

Nothing is ever rendered or re-encoded. Source page content is referenced by object,
never decoded. The dot grid is one XObject referenced N times. Output is written
unlinearized. The cost is qpdf's object copy, which is the same C++ in both
implementations.

### Fit

A book is typographically uniform, so **one crop box for the whole book**, not
per-page: per-page cropping would blow up a short chapter-ending page while the next
is normal, making text size jitter as you read. `init` samples ~16 pages via
`gs -sDEVICE=bbox`, takes a robust union (discarding blank pages, which return
`0 0 0 0`), and **caches the result in the project TOML** — so the one slow step runs
once and every rebuild is instant. `--fit page` skips it entirely.

### Drawing specifics

- **Dot grid**: line width = dot diameter, `1 J` round cap, all dots as degenerate
  subpaths in **one path with a single `S`**. ~2400 dots on A4 at 5 mm pitch, one
  stroke operator, ~30 KB — and as a Form XObject it appears once in the file, not
  once per page.
- Defaults: 5 mm pitch, 0.25 mm dot, 25 % K. Below ~0.2 mm most printers drop the dot.
- **Center ticks**: 4 inward ticks at the edge midpoints, 3 mm, 0.3 pt, 40 % K —
  both axes, outside the writing area, ~8 path ops. Quarter ticks optional.
- **Registration**: 2 mm outer-corner tick on both sides, so front/back misalignment
  is visible immediately instead of 40 sheets later.
- **Footer**: `Ch. 3 · p. 47`, 7 pt italic outlines, 40 % gray, outer edge — a sheet
  that falls out of the binder goes back where it belongs.
- **Text**: CFF outlines → `m`/`c`/`h` + `f` (nonzero winding, which is what CFF wants).

### Metadata resolution

CLI flag → project TOML → XMP `dc:title`/`dc:creator` → `/Info /Title /Author` →
filename heuristic → empty. A missing author degrades the footer gracefully rather
than printing a gap; you fill it in the TOML and re-run.

### Manual duplex

`--calibrate` prints two sheets marked `FRONT · this edge entered first ↑` with a
corner tick. You flip them the way you naturally would, print side two, and read off
which of four cases you got — *reverse order?* × *rotate 180°?*. Saved as a profile:

```toml
[printers.hp_1020]
backs_order  = "reverse"
backs_rotate = 180
```

From then on `_backs.pdf` is emitted already correct for that printer. `--instructions`
puts the reload procedure on page 1 of the backs PDF.

### CLI surface

```
print-books init BOOK.pdf [-o project.toml]    probe, detect chapters, sample bbox, write TOML
print-books build project.toml [options]
print-books calibrate [--printer NAME]
print-books proof project.toml [-n 6]

  --duplex auto|manual           auto = one PDF; manual = _fronts.pdf + _backs.pdf
  --single-file                  manual as one PDF: all fronts, then all backs
  --chapters 1 | 1,3-5 | all
  --split-per-chapter            one PDF per chapter
  --notes dots|lines|blank|none  none = plain chapter print, no facing pages
  --fit content|page
  --paper a4|letter
```

`--notes none` is not a special case in the code — it is a different `Plan` through
the same engine.

---

## Phases

### Phase 0 — the repo exists

0. `git init -b main` at `/home/nava/Files/code/active/Print_BooksAndSo`, remote
   `https://github.com/minervarr/Print_BooksAndSo.git`. Copy
   `/home/nava/Files/code/active/git_wrapper_exe` → `./git_wrapper`.
   `.gitignore`, `LICENSE` (AGPLv3-or-later, as the siblings), `README.md`,
   `CLAUDE.md`. Copy `lmroman10-{regular,italic}.otf` into `assets/fonts/` from
   `/usr/share/texmf-dist/fonts/opentype/public/lm/`. First commit + push with
   `./git_wrapper save`, which establishes `main` on the empty remote.

### Phase 1 — prototype, end to end

Deliverable: a real printable PDF from a real book, duplex-auto only.

1. `prototype/` scaffold: `pyproject.toml` pinned to `requires-python = "==3.13.*"`,
   venv via `python3.13 -m venv prototype/.venv`, deps `pikepdf` (cp313 wheel) +
   `fontTools`. A why-first module docstring with a `Usage:` line on each entry point,
   per the workspace's `tools/*.py` voice.
2. `core/units.py`, `core/geometry.py` + tests. A4 = 595.276 × 841.890 pt;
   5 mm = 14.1732 pt. Fit-into and gutter-shift are pure arithmetic, asserted exactly.
3. `core/project.py` + TOML writer + tests.
4. `core/outline.py` — outline tree → chapters + mini-TOC entries + tests.
5. `core/plan.py` — page-slot model, `SequentialImposer`, and the four invariants
   above as tests. **Write the tests first**; the invariants are the spec.
6. `core/metrics.py` + `core/text.py` — `GlyphSource` protocol, outline-path layout.
7. `core/drawing.py` — grid XObject, ticks, registration, portrait, mini-TOC, footer.
   Tests assert on emitted operators.
8. `backend/glyphs_fonttools.py`, `backend/pdf_pikepdf.py`.
9. `cli/main.py` — `init` and `build`.
10. Test against a real book; inspect with `pdftoppm`.

### Phase 2 — the printer

11. `core/printer.py` + profiles + the backs transform (order × rotation) + tests.
12. Calibration PDF generator; `--instructions` sheet.
13. `backend/bbox_gs.py` sampled bbox + caching into the project TOML.
14. `backend/proof.py` + `proof` command.

### Phase 3 — the C++ port

15. `cpp/` scaffold: `cpp/CMakeLists.txt` as project root (Economycs preamble),
    `core/CMakeLists.txt` + `cli/CMakeLists.txt`, `scripts/linux/build.sh` from the
    Economycs template, vendored toml++ single header.
16. Port `core/` file by file, each against its ported test — units → geometry →
    project → outline → plan → text → drawing → printer. Each port lands with its
    `*_test.cc` green before the next starts.
17. `backend/qpdf`, `backend/freetype`, `backend/gs`.
18. **Cross-language golden tests** — the port's real safety net. Both
    implementations dump the `Plan` and every content stream as JSON for the fixture
    books; C++ output must diff clean against Python output. When the port breaks it
    names the side of the chapter that disagrees, instead of "the PDF looks wrong."

### Phase 4 — later, not now

TOC-scrape tier (dot-leader heuristic, deterministic, no AI) for books with no
outline; `SaddleStitchImposer` as the second imposition strategy; Type0 font
embedding behind a flag if searchable furniture ever matters.

---

## Verification

**Pure-core tests, both languages** — the real safety net, mirroring the workspace's
"core tests run on the desktop with no NDK and no GPU":

```bash
# Python — deliberately run with NO pdf library importable
cd prototype && python3.13 -m pytest tests/ -q

# C++ — or just: scripts/linux/build.sh debug
cmake -S cpp -B cpp/build/linux_debug -G Ninja -DCMAKE_BUILD_TYPE=Debug
cmake --build cpp/build/linux_debug -j"$(nproc)"
ctest --test-dir cpp/build/linux_debug --output-on-failure
```

A test asserts `core/` imports nothing outside the stdlib, so the purity boundary
cannot rot silently. Its C++ counterpart is structural rather than a test: no
`core/*_test` target may list a `backend/` source, which is visible in one CMake file.

**End-to-end, on a real book:**

```bash
print-books init ~/Books/some_book.pdf -o /tmp/book.toml
print-books build /tmp/book.toml --chapters 1 --duplex auto -o /tmp/out.pdf
print-books proof /tmp/book.toml -n 6        # PNGs of the first 6 sheets
```

Then check by eye, the way rendering is verified everywhere else in this workspace:
portrait on a recto, content always on the left, notes facing it, mini-TOC behind the
portrait, dots faint but present, center ticks findable.

**Manual duplex:** `print-books calibrate`, print, flip, print, record the profile;
then a 4-sheet build and confirm fronts and backs align via the registration ticks.

**Performance gate:** a 400-page book must build in well under a second once the
bbox is cached. If it does not, the object-copy path is being bypassed.

---

## Conventions — copied from the siblings, not invented

Swept from Economycs, archive_engine, Matrix_Player and VideoPlayer. **Economycs is
the closest model** (CLI + core, no GUI needed) and its shapes should be copied.

**CMake.** Economycs' exact shape: a `_dev_default` computed from
`CMAKE_BUILD_TYPE STREQUAL "Debug"`, then `option(PRINTBOOKS_TESTS … ${_dev_default})`;
`enable_testing()` in the root *guarded by that option*, so a Release build can still
be told to run the suite. Tests gated on the **option**, not the build type. Root
preamble copied verbatim: `CMAKE_CXX_STANDARD 17`, `CXX_EXTENSIONS OFF`,
`CMAKE_EXPORT_COMPILE_COMMANDS ON`, and the `GENERATOR_IS_MULTI_CONFIG` /
default-to-Release block. Economycs' `PRINTBOOKS_SANITIZE` block is reusable verbatim.

**Tests.** Each `add_executable` **lists the real `.cc` TUs it exercises and links
nothing else** — the house convention says that property is worth protecting more
than the assertions are, because it is what stops a test from quietly acquiring a
dependency. So `geometry_test` links `src/geometry.cc src/units.cc` and no PDF
backend; `plan_test` links plan + geometry + units. Each test source opens with
`#undef NDEBUG` on line 1 before `<cassert>`, and each ends:

```cpp
    std::printf("plan_test: all assertions passed\n");
    return 0;
```

Registration via the `foreach` idiom with `-Wall -Wextra` and
`add_test(NAME ${_t} COMMAND ${_t})`.

**`cli/`.** A separate executable linking only the core library, with
`set_target_properties(printbooks_cli PROPERTIES OUTPUT_NAME print-books)` — exactly
how Economycs renames `economycs_cli` → `economycs`.

**`scripts/linux/build.sh`.** Economycs' 119-line template, not Matrix_Player's
325-line one (no microarch matrix needed for a tool that builds in seconds). Keep its
three habits: `-t 0` TTY guard around the `read` so a non-interactive caller falls
through to Release instead of hanging; `-h` re-printing the script's own header via
`sed -n '2,20p' "$0"` rather than a duplicated usage string; a build directory that
**names its configuration** (`build/linux`, `build/linux_debug`, `build/linux_asan`);
and an epilogue listing what was produced plus the `ctest` line in Debug.

**`CLAUDE.md`.** The sibling shape: `# CLAUDE.md` → "Guidance for Claude Code
(claude.ai/code) working in this repository." → a line pointing at the authoritative
workspace `../CLAUDE.md` → `## What this is` → a run of **assertion-shaped invariant
sections titled as claims, not nouns** (the house voice: "The namespace is `arc`, and
that is not cosmetic", "Parentheses mean something"). Ours: *"`core/` never imports a
PDF library, and a test enforces it"*, *"One crop box for the whole book, and that is
not laziness"*, *"The generated text is outlines, not a font"*, *"The dot grid is one
XObject"*. Then `## Build`, `## Tests`, `## Committing` last. Every rule carries its
why, and where there is a measurement it gets cited — the 26 s bbox figure belongs in
the file.

**`.gitignore`.** Economycs' sectioned file as the base (it is the most complete),
plus `camera_without_blood`'s Python block verbatim — the only complete one in the
workspace. Note `git_wrapper` is itself gitignored in Economycs and Matrix_Player as
"a local tool, not project source"; follow that. Add `.venv/`, `.pytest_cache/`,
`*.egg-info/`, proof PNGs and generated PDFs.

**New territory, deliberately.** There is **no Python convention in this workspace** —
no `pyproject.toml`, no venv, no pytest config, no formatter config in any
first-party repo. All existing first-party Python is one-off `tools/*.py` generators
run against system site-packages with a `try/except ImportError → sys.exit("… pip
install …")` guard. A prototype with its own `pyproject.toml` and venv therefore
*establishes* a convention. It is also forced: system `python3` is **3.14**, so
pinning 3.13 requires a venv. The new `CLAUDE.md` must say this is deliberate, so a
future reader does not "fix" it into the `tools/` style. What we do keep from that
style: the why-first module docstring and the `Usage:` line on every entry point.

**Committing.** `./git_wrapper commit "<message>"` / `./git_wrapper save "<message>"`
— never plain `git commit`. Identity is forced to `nava <nava@noreply.com>` and the
message is scrubbed. **No `Co-Authored-By:`, no `Claude-Session:`, no 🤖 lines** — the
workspace `CLAUDE.md` explicitly overrides the default attribution convention, and
the sibling repos each restate the prohibition. Branch `main`; the remote is empty, so
the first push establishes it. `git_wrapper_exe` is copied from the workspace root to
`./git_wrapper`.
