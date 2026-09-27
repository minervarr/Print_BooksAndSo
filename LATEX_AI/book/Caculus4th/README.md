# Calculus, 4th Edition — reconstruction

Michael Spivak, Publish or Perish, 2008. ISBN 978-0-914098-91-1.

Source (read-only): `sources/Michael Spivak - Calculus, 4th Edition (2008).pdf`
(701 pages). Chapter slices: `python3 chapter.py split` → `sources/chapters/`.

One LuaLaTeX source. **Two print PDFs** in `pdf/`. **HTML** (MathJax) in
`html/` — smoke: front matter + chapters 1–8; graphs are SVG. EPUB is out of scope.
Status: `the_book_project/PROGRESS.md`.

## Layout

```
Caculus4th/
├── README.md                 this file (the only project doc)
├── build.py                  print PDFs + HTML
├── chapter.py                slice / test / chat prompt
├── pdf/                      share folder — print PDFs only, named
├── html/                     make4ht + MathJax (smoke: through ch. 8, SVG)
├── packages_manuals/         CTAN manuals for packages we load
├── sources/                  original scan + chapters/*.pdf
└── the_book_project/
    ├── main.tex
    ├── my_book.sty
    ├── PROGRESS.md           glance table
    ├── notes.md              OCR / figure log
    ├── frontmatter/ chapters/ backmatter/
    ├── build/<variant>/      LaTeX aux + a working main.pdf
    └── assets/
        ├── crop-scan.py      shim → kit/tools
        ├── preview-figures.py shim → kit/tools
        ├── export-figures-svg.py shim → kit/tools
        ├── generators/ geometric/ plots/ rendered/
        ├── scans/            original FIGURE crops (not shipped)
        └── ai-preview/       300 dpi JPEGs of reconstructions (AI only)
```

Reusable code lives in `../../kit/`.

## Engine and page

LuaLaTeX + New Computer Modern for **print**. HTML is `make4ht` + MathJax
(needs JavaScript in the browser). Class `book`, 11 pt, `oneside`, `openany`.

| Command | Output |
|---|---|
| `print-v` | `pdf/Calculus-4e-print-A4.pdf` |
| `print-h` | `pdf/Calculus-4e-print-A4-landscape.pdf` |
| `html` | `html/index.html` (front + ch. 1–8; SVG figures; MathJax gate) |

Print: A4, 2.2 cm, running head. Landscape uses the sheet. PDF math uses
`axessibility` (copy/paste ActualText) and `bookmark` after `hyperref`.

## Commands

```
python3 build.py              # both print PDFs → pdf/
python3 build.py print-v
python3 build.py html         # MathJax smoke → html/index.html

python3 chapter.py list
python3 chapter.py pdf 9      # attach this slice in chat
python3 chapter.py test 8     # PASS / FAIL (PDF)
python3 chapter.py test-html  # MathJax gate on html/ (no rebuild)
python3 chapter.py prompt 9

python3 the_book_project/assets/preview-figures.py
python3 the_book_project/assets/export-figures-svg.py   # TikZ → rendered/*.svg
python3 the_book_project/assets/crop-scan.py \
  --page 55 --x 24 --y 618 --width 242 --height 228 --name ch02-fig01
```

## Voice (`my_book.sty`)

`\partdivider` `\spivakchapter` `\epigraph` THEOREM / PROOF `\begin{spivakdefn}`
`\prop{n}` `\pnum{1.}` / `\pnum{*8.}` `romans` `letters` `steps` `\abs`
`\figlabel{1}` `\figtex{assets/plots/...}`. The book writes **domain**, not “dom”. Bold systems
`\mathbf{N}` unless the scan is blackboard.

Figures: pgfplots, TikZ, or FreeCAD → SVG. Captions are TeX. Never
`\includegraphics` a scan. `scans/` is the model; `ai-preview/` is for a
chat model to look at.

## One chapter (chat)

Attach `python3 chapter.py pdf N` (or `chapter.py prompt N`). The model
has no repo. Paste:

```
You have no access to any project file except this message and the attached PDF.
Copy-typist. One chapter. Then stop.

THIS JOB: chapter N, title from the PDF filename. Write chapterNN.tex
starting with \spivakchapter{N}{Title}. No \documentclass. Appendix in
the same file if it is in the slice.

Type from the pictures. OCR lies. Reflow prose. No \chapter, no
\partdivider, no \epigraph.

Macros: \prop \pnum theorem/proof spivakdefn \abs \figlabel romans
letters steps. Stars: \pnum{*8.}

FIGURE n only: give a crop-scan line
  --page P --x X --y Y --width W --height H --name chNN-figMM
(P is 1-based in the attached PDF, 72 dpi, top-left). In the tex:
  % TODO figure MM  assets/scans/chNN-figMM.png
Do not include the PNG. Equations stay TeX even if they are bitmaps.

Return: (1) tex (2) crops or "crops: none" (3) short notes.
Human runs crop-scan and: python3 chapter.py test N
It must print PASS. Do not start the next chapter.
```

Foundations (ch. 1–8) are drafted. Next: Part III, chapter 9.

## Outline

Part I 1–2 · Part II 3–8 (stop here for a solid base) · Part III 9–19 ·
Part IV 20–27 · Part V 28–30 · back matter.
