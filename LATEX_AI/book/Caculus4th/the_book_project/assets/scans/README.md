# scans/ — only real FIGURE crops

A file here is a **reference crop of a drawing the book labels FIGURE n**.
Not an equation, not a paragraph, not a full page, not a pdfimages dump.

## Name

```
chNN-figMM.png
```

- `NN` = chapter number, two digits (`ch02`, not `calcu5`)
- `MM` = the number printed next to FIGURE (`FIGURE 1` → `fig01`)

Example: chapter 2, FIGURE 1 → `ch02-fig01.png`

## How to add one

1. Confirm the scan says **FIGURE n** (or the prose says “Figure n”).
2. Preview that page at 72 dpi (1 pt = 1 px, origin top-left):

   `pdftoppm -png -r 72 -f PAGE -l PAGE "../../sources/Michael Spivak - Calculus, 4th Edition (2008).pdf" /tmp/p`

3. Crop:

   `python3 ../crop-scan.py --page PAGE --x X --y Y --width W --height H --name chNN-figMM`

`--page` is 1-based in the PDF you pass (default `sources/Michael Spivak - Calculus, 4th Edition (2008).pdf`).

4. In the chapter `.tex`, do **not** `\includegraphics` this PNG. Leave:

   `% TODO figure MM  assets/scans/chNN-figMM.png`

   until it is redrawn (TikZ / pgfplots / FreeCAD).
