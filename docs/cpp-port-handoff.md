# C++ port — handoff

State of the C++ port as of this commit, for whoever picks it up next. Read the
repo `CLAUDE.md` first (authoritative for structure); this documents the port
specifically.

## What is done

`core/` is ported file-by-file from the Python prototype, under mirrored names,
and every module has a mirrored test. The whole thing builds with nothing but a
C++17 compiler — no PDF library, no font library, no I/O on any core link line.

| Python (`prototype/core/`) | C++ header | C++ source | C++ test |
|---|---|---|---|
| `units.py` | `units.hh` | `units.cc` | `units_test.cc` |
| `geometry.py` | `geometry.hh` | `geometry.cc` | `geometry_test.cc` |
| `metrics.py` | `metrics.hh` | (header-only) | exercised by `text_test`, `render_test` |
| `pdfops.py` | `pdfops.hh` | `pdfops.cc` | exercised by `drawing_test`, `text_test` |
| `plan.py` | `plan.hh` | `plan.cc` | `plan_test.cc` |
| `drawing.py` | `drawing.hh` | `drawing.cc` | `drawing_test.cc` |
| `text.py` | `text.hh` | `text.cc` | `text_test.cc` |
| `numwords.py` | `numwords.hh` | `numwords.cc` | `numwords_test.cc` |
| `render.py` | `render.hh` | `render.cc` | `render_test.cc` |

`metrics.hh` and `pdfops.hh` have no dedicated test target because the Python
side has no `test_metrics.py` / `test_pdfops.py` either — they are covered by the
tests that use them, and the mirroring rule ("a file on one side only is a bug
report") applies to tests too.

Namespace is `pb`, include prefix is `printbooks/`, so `#include
<printbooks/plan.hh>` reads the way `<economycs/money.hh>` does. Header
extension `.hh`, source `.cc`, matching Economycs and archive_engine.

## Build and test

```bash
# Debug, tests included (also what scripts/linux/build.sh debug does):
cmake -S cpp -B cpp/build/linux_debug -G Ninja -DCMAKE_BUILD_TYPE=Debug
cmake --build cpp/build/linux_debug -j"$(nproc)"
ctest --test-dir cpp/build/linux_debug --output-on-failure   # 7/7 pass

# Release, no tests:
scripts/linux/build.sh release     # -> cpp/build/linux
scripts/linux/build.sh --clean debug
scripts/linux/build.sh --asan
```

The CMake shape is Economycs': `cpp/CMakeLists.txt` is the `project()` root (the
repo root has none), `PRINTBOOKS_TESTS` defaults ON in Debug and OFF in Release,
tests are gated on the **option** not the build type, and each test executable
lists the real `.cc` TUs it exercises and links nothing else. `PRINTBOOKS_SANITIZE`
adds ASan+UBSan and refuses Release, copied verbatim from Economycs.

## Deviations from the Python that a future diff should know about

These are where the port is deliberately not byte-for-byte the same shape as the
prototype. None change behaviour.

- **`GutterEdge` is one enum, not two aliases.** `geometry.py` and `plan.py` each
  declare their own `Literal["left", "right"]`; in C++ `enum class GutterEdge`
  lives in `geometry.hh` and `plan.hh` uses it. Same concept, one definition.
- **`Corner` is an enum, not a string.** `drawing.py` takes a `Corner =
  Literal[...]` string and `render.py` stores `registration: str | None`. The C++
  `enum class Corner` (in `drawing.hh`) makes an invalid corner unrepresentable,
  which is why `test_registration_tick_rejects_an_unknown_corner` has **no C++
  counterpart** — there is no way to pass one.
- **`GlyphSource::outline` takes a code point, not a single-char string.**
  Python iterates `str` as code points; C++ strings are UTF-8. `text.cc` owns a
  tiny UTF-8 decoder (`next_codepoint` / `encode_utf8`) so a curly quote or an
  accented title survives the port. Missing glyphs are `std::out_of_range`, and
  `draw_text` collects them all before throwing `std::invalid_argument`, matching
  the Python "name every missing character at once" behaviour.
- **`Size`/`Rect` reject in their constructors** rather than in `__post_init__`;
  both throw `std::invalid_argument`, mirroring `ValueError`.
- **`notes`/`page_box`/`facing_page` are `std::optional`** rather than Python's
  `None` defaults; `Renderer::layout_side` takes `const Chapter*` for the optional
  chapter.
- **`cpp/core/tests/test_util.hh`** supplies `approx()` (pytest.approx), `ops()`
  and `ml_points()` (the regex helpers). Test-only, not part of `printbooks_core`.

## What is NOT done (next)

In spec order, these are the remaining Phase 3 steps:

1. **Backends** — `cpp/backend/freetype/` (an `FT_Outline_Decompose` GlyphSource,
   the one-file swap the whole design promises) and `cpp/backend/qpdf/`
   (`probe` + `emit`, calling `QPDFPageObjectHelper::getFormXObjectForPage()` and
   `placeFormXObject()`, whose `std::string` return is why `render.hh` emits text).
   `cpp/backend/gs/` for the sampled ink bbox. These need the shipped
   `assets/fonts/lmroman10-*.otf` and real fixture PDFs, so they cannot be
   unit-tested the way core is.
2. **CLI** — write `prototype/cli/main.py` (`init`/`build`) first, then
   `cpp/cli/cli_main.cc` + `cpp/cli/CMakeLists.txt` (`OUTPUT_NAME print-books`).
   The mirroring rule means the C++ cli follows the Python cli.
3. **Golden tests** — the cross-language diff that names the disagreeing side.
   Blocked on (1), since both sides must be able to dump a real `Plan` and
   content streams for the fixture books.
4. **`core/project.py`/`outline.py`/`printer.py`** — still unwritten on *both*
   sides (see CLAUDE.md "Known gaps"). `backend/pdf_pikepdf.py::
   chapters_from_outline` currently does outline → chapters.

## Hygiene notes for the next session

- Commit with `./git_wrapper`, never plain `git commit`; bare message, no
  `Co-Authored-By` / `Claude-Session` / 🤖.
- `cpp/build/` is gitignored; `compile_commands.json` and `CMakeCache.txt` too.
- The LSP in this workspace reports "`printbooks/*.hh` file not found" until
  CMake has configured a build directory — it does not know the `include/` path.
  Configure first, then trust the compiler, not the editor.
