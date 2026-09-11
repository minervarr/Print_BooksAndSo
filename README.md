# Print_BooksAndSo

Turn a PDF book into a **printable notebook**. Every page of the book lands on a
left-hand sheet with a facing right-hand page for notes, every chapter opens with a
LaTeX-style portrait, and the output is shaped for the printer you actually own —
including cheap printers with no duplex unit.

Input a PDF. Output a PDF. No network, no AI, no service, no account.

> **Status:** scaffolded. The design is settled (`docs/superpowers/specs/`) and the
> implementation has not started. The transcript below is the designed interface,
> not a recording.

```console
$ print-books init ~/Books/atomic_habits.pdf -o habits.toml
  19 chapters from the PDF outline
  crop box from a 16-page sample: 71.99 42.12 540.01 716.94
  wrote habits.toml

$ print-books build habits.toml --chapters 1 --duplex manual
  chapter 1 "The Mechanism of Habit Formation", pages 27-44
  38 sides -> 19 sheets
  habits_ch01_fronts.pdf   19 pages
  habits_ch01_backs.pdf    19 pages  (reversed, rotated 180 for printer "hp_1020")

  Print habits_ch01_fronts.pdf first. Reload the stack as printed, then print
  habits_ch01_backs.pdf. Check the corner ticks align before printing the rest.
```

## The decisions, and why

**The unit of imposition is a *side*, not a page.** A chapter is a portrait on a
recto, a mini-TOC on its verso, then one spread per source page: content on the
left, notes on the right. Four invariants fall out and they are the tests — portraits
on rectos, content on versos, `2 + 2N` sides per chapter, every source page exactly
once. Getting this wrong is invisible until you have printed forty sheets.

**The mini-TOC pays for itself.** `2 + 2N` is even, so the next chapter's portrait
lands on a recto with no filler page. Without it you need a blank to restore parity —
the same paper, less use. So the back of each portrait carries the chapter's own
sub-sections and page numbers.

**Nothing is ever rendered.** Source pages are referenced as Form XObjects, never
decoded. The dot grid is one shared XObject referenced N times, not drawn per page.
That is the entire performance story, and it is why a 400-page book builds in well
under a second.

**One crop box for the whole book.** Pages are cropped to their ink and scaled up,
but from a 16-page sample, cached — not per page. Per-page cropping makes text size
jitter as you read, because a short chapter-ending page gets blown up while the next
is normal. It is also 26 s slower on a 500-page book, measured.

**Generated text is glyph outlines, not an embedded font.** Real Computer Modern with
no font dictionary, no CID map, no subsetting, on either side of the port. The
trade: the portraits and footers are not searchable. The book's own pages are
untouched and stay searchable.

**Ink is a cost.** The notes page is a 0.25 mm dot grid at 25 % gray, not lines — and
the page centre is marked by four small ticks at the edge midpoints instead of two
full crosshairs. You get both axes for about eight path operators.

**Two implementations, one design.** A Python 3.13 prototype and a C++17 port, with
mirrored file names so the port is mechanical. Both drive the same engine underneath:
pikepdf is qpdf, so `Page.as_form_xobject()` and
`QPDFPageObjectHelper::getFormXObjectForPage()` are the same call.

## Layout

```
prototype/    Python 3.13. The reference implementation, and not throwaway —
              the golden tests diff the C++ port against it.
  core/       PURE: stdlib only, no PDF library, no I/O. Plans and decides.
  backend/    the only place pikepdf, fontTools or a subprocess appears.
  cli/        argparse front door.
cpp/          C++17. cpp/CMakeLists.txt is the project() root.
  core/       the same promise: no OS headers, no PDF library, no I/O.
  backend/    qpdf, freetype, ghostscript.
  cli/        -> print-books
assets/fonts/ Latin Modern Roman, regular and italic. Shared by both.
fixtures/     tiny synthetic PDFs + golden JSON plans for the cross-language tests.
docs/         the design spec.
```

## Building

```bash
python3.13 -m venv prototype/.venv
prototype/.venv/bin/pip install -e prototype[dev]

scripts/linux/build.sh debug        # C++, + tests
ctest --test-dir cpp/build/linux_debug --output-on-failure
```

Python **3.13, not 3.14**: pikepdf ships a `cp313` wheel, so nothing needs a
compiler. In a venv, because this machine's system `python3` is 3.14.

## Licence

Copyright (C) 2026 nava. AGPLv3 or later; see `LICENSE`.
