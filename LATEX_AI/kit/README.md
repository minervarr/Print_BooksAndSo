# Reconstruction kit

Copy this `kit/` directory next to a new book. It does not know the author.
The book folder holds the author's voice (`style.tex`), the chapters, and
the figures.

## Layout of a new book

```
<project>/
  kit/                 this directory
  book/
    style.tex          author identity (theorems, openers, lists)
    main.tex           \frontmatter / \mainmatter / \backmatter + \input units
    unit.tex           one-unit wrapper (copy kit/templates/unit.tex)
    Makefile           include ../kit/make/latex.mk; set FRONT MAIN BACK
    chapters/<slug>N.tex
    figures/geometric/ semantic TikZ
    figures/plots/     pgfplots (expression or .dat)
    figures/scans/     reference crops, not shipped
  sources/
    original.pdf
    <slug>N.pdf        one scan per unit; no number = 0
```

Start from `kit/templates/`.

## Figures (three kinds)

| Kind | How | Fonts |
|---|---|---|
| Function graph | pgfplots, `reconstruction plot` style, expression or table | ticks/labels are TeX |
| Geometric line art | hand TikZ, `reconstruction` style, `\node` for numbers | nodes are TeX |
| Unique ink | last resort: `\includegraphics` of a crop, or `tools/trace_figure.py` | will **not** follow the book font |

Do not trace lettering. Captions (`FIGURE 1`) are TeX. A picture is
`\input` into the chapter, never a pre-rendered PDF, so a preface/style
font change rebuilds the labels.

Standalone review (same packages, same style):

```
make figures          # from the book directory
```

## Tools

```
tools/extract_figure.py SOURCE.pdf PAGE OUT.png     # look at a page
tools/extract_figure.py SOURCE.pdf PAGE prefix --pdfimages
tools/trace_figure.py IN.png OUT.tex --method centerline   # last-resort line art
tools/validate_figure.py ORIG.png PAGE.pdf [PAGE]          # structural IoU
```

Pixel IoU is a check, not the ship criterion. Beauty and font inheritance
beat a photocopy of the scan.

## Build

From the book directory:

```
make book                 # build/book.pdf
make units                # build/units/<name>.pdf for every listed unit
make unit UNIT=<name>
make figures
```

Unit PDFs restart at page 1 (roman in front matter, arabic otherwise).
The combined book is the only running sequence.
