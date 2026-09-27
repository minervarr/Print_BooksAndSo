# Reconstruction kit

Reusable tools. A book folder holds voice (`my_book.sty`), chapters, and
figures. Copy `kit/` next to a new title; do not fork the scripts inside
the book except as a thin shim.

## Tools (`kit/tools/`)

| Script | What |
|---|---|
| `crop-scan.py` | Crop one **FIGURE** from a scan PDF → `scans/chNN-figMM.png` |
| `figure_render.py` | Shared compile (TikZ → PDF) plus JPEG/SVG writers |
| `preview-figures.py` | TikZ + FreeCAD SVG → 300 dpi JPEG in `ai-preview/` (AI only, not the book) |
| `export-figures-svg.py` | TikZ → `assets/rendered/<stem>.svg` for HTML (skip if up to date) |
| `design-figures.sh` | Run every `assets/generators/*.py` through FreeCAD |

```
python3 kit/tools/crop-scan.py --pdf BOOK.pdf --scans book/.../scans \
  --page 55 --x 24 --y 618 --width 242 --height 228 --name ch02-fig01

python3 kit/tools/preview-figures.py --assets book/.../assets
python3 kit/tools/preview-figures.py --assets book/.../assets ch04-fig07
python3 kit/tools/export-figures-svg.py --assets book/.../assets
python3 kit/tools/export-figures-svg.py --assets book/.../assets ch04-fig07
```

Coordinates for `crop-scan` are 72 dpi, origin top-left (`pdftoppm -r 72`).

## TeX (`kit/tex/`)

`figure-style.tex` — `reconstruction` / `reconstruction plot` (black line art).
`fonts.tex` / `packages.tex` / `figure-standalone.tex` — starting point for a
new title; this Calculus book inlines the styles in `my_book.sty`.

No EPUB. No Makefile. The book’s `build.py` is the front door. HTML for
a title is `make4ht` + MathJax from that book’s `build.py html`, not a
kit ebook pipeline.
