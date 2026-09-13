# LATEX_AI — reconstructing Spivak, *Calculus*, as LaTeX

Reverse-engineer a scanned book into clean LaTeX, unit by unit, preserving
the author's typographic essence while producing an artifact that reads
well on both a screen and paper.

The **kit** (`kit/`) is general: copy it next to another book. This **book**
(`book/`) is Spivak-specific. Source scans live in `sources/` and are
read-only.

Read `kit/README.md` before starting a new title. Read `book/style.tex`
and `book/chapters/notes.md` before working a unit of *this* title.

## The invariant input shape

```
sources/original.pdf     the whole book
sources/<name>N.pdf      one scan per unit, N = 0, 1, 2, ...
```

`<name>` is a short slug (`calcu` here). **No number = 0.** A unit is a
front/back-matter section or a Part, not necessarily a single chapter.

The unit PDFs are scans with an OCR text layer. The OCR is a *draft*:
subscripts and symbols are mangled. Every equation is re-typed.

## Layout

```
LATEX_AI/
  kit/                   GENERAL — tools, packages, figure style, Makefile
  book/                  SPECIFIC — this author's voice and content
    style.tex            living essence file (grows after every chapter)
    main.tex             front / main / back + \input units
    unit.tex             one-unit wrapper
    Makefile
    chapters/calcuN.tex
    chapters/notes.md
    figures/geometric/   hand TikZ
    figures/plots/       pgfplots
    figures/scans/       reference crops, not shipped
  sources/               read-only scans
  README.md              this file
```

## Book structure

| Matter | Units | Pages |
|---|---|---|
| Front | calcu1–4 (title, copyright, preface, contents) | roman |
| Main | calcu5–9 (Parts I–V), starting at Chapter 1 | arabic from 1 |
| Back | calcu10–13 (reading, answers, glossary, index) | arabic, continues |

We reproduce that *structure*, not the 2008 page numbers.

## The rules

1. **One unit at a time.** Work `calcu1`, then `calcu2`, … Never the whole book at once.
2. **Chapter separation must be visible.** `\spivakchapter` is the opener. If the source already has a title divider, do not duplicate it.
3. **Reproduce section weight faithfully.** A tiny dedication stays tiny.
4. **Digital *and* print.** `book` + `oneside` + moderate margins. Do not copy the source's huge print margins.
5. **`book/style.tex` is the living essence file.** Typographic identity lives there. After every chapter, grow it. Kit files grow only for capabilities the next book will need.
6. **Page fidelity at deliberate boundaries.** Title pages, part dividers, epigraphs, chapter openers, contents: if the source page is sparse, it stays sparse. Dense prose reflows. Every chapter begins on a fresh page.
7. **Figures are reconstructed, not photocopied.** Three kinds:

   | Kind | How | Fonts |
   |---|---|---|
   | Function graph | pgfplots (`reconstruction plot`), expression or table | TeX |
   | Geometric line art | hand TikZ (`reconstruction`), `\node` for numbers | TeX |
   | Unique ink | last resort: crop + `\includegraphics`, or `kit/tools/trace_figure.py` | will not follow the book font |

   Preserve dimensionality: a 3-D drawing stays 3-D. Captions (`FIGURE 1`) are TeX. Pictures are `\input`, never a pre-rendered PDF, so a font change in `style.tex` rebuilds the labels.
8. **Tables** are real `tabular`/`array`. **Equations** are re-typed.

## Build

Front door is `./build.sh`. On a TTY it asks what to compile; otherwise it
builds the full book. Non-interactive flags for scripts:

```
./build.sh                # asks, on a TTY; else the full book
./build.sh book           # book/build/book.pdf
./build.sh units          # book/build/units/calcuN.pdf
./build.sh unit calcu5
./build.sh figures
./build.sh all
./build.sh --clean book
```

Same targets via `make -C book book` (or `units` / `unit UNIT=…` / `figures`).
Unit PDFs restart at page 1 (roman in front matter). The combined book is
the only running sequence. Needs `pdflatex`.

## Per-chapter workflow

1. **Orient.** `pdftotext -layout sources/calcuN.pdf -`. Read the first two pages for the opener / divider.
2. **Log.** Append a `## calcuN` section to `book/chapters/notes.md`.
3. **Skeleton.** Prose and equations into `book/chapters/calcuN.tex` in reading order.
4. **Classify.** `\begin{theorem}` / `\begin{proof}` / `\prop` / `\pnum` + `romans`/`letters`. Re-type every equation.
5. **Figures.** Study the scan. Classify as plot / geometry / unique ink. Extract a reference crop with `kit/tools/extract_figure.py` if needed; draw in TikZ or pgfplots. `\input` the body-only `.tex`.
6. **Tables.** Real `tabular`/`array`.
7. **Grow `book/style.tex`.** New environments, macros, conventions — here, with a `% WHY` comment. Packages that every book will need go in `kit/tex/packages.tex`.
8. **Compile.** `make book` (twice via the Makefile) and `make unit UNIT=calcuN`. Check boundaries against the source.
9. **Vision check.** Note anything left for a vision-capable agent in `notes.md`.

## Status

calcu1–5 are reconstructed (Part I Prologue). calcu6–13 are not started.
The first figure (Hanoi, calcu5) is geometric TikZ; it is the template for later drawings.

## Fonts

Computer Modern. That is a deliberate identity choice, not a match of the
2008 Times re-typeset. Figures inherit it.
