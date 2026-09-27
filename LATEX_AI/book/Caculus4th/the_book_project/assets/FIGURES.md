# Reconstructed figures (chapters 1–8)

Do **not** ship scan PNGs in the PDF. Crops in `scans/` are the model only.

## Where the drawing lives

| Kind | Path | How the chapter includes it |
|---|---|---|
| TikZ geometry | `geometric/chNN-figMM.tex` | `\input{assets/geometric/chNN-figMM}` |
| pgfplots | `plots/chNN-figMM.tex` | `\input{assets/plots/chNN-figMM}` |
| FreeCAD 3-D | `generators/chNN-figMM.py` → `rendered/chNN-figMM.svg` | `\includesvg[width=0.95\textwidth,inkscapelatex=false]{assets/rendered/chNN-figMM}` |

The `.tex` snippet is **only** a `tikzpicture` (or a `tabular` of two of them). Caption and centering belong in the chapter:

```latex
\begin{center}
\input{assets/geometric/ch04-fig08}\\[0.6em]
\figlabel{8}
\end{center}
```

Appendix figures whose printed number restarts still use sequential files (`ch08-fig10`) but `\figlabel{1}`.

## Style

- Black line art, `reconstruction line` / `reconstruction plot` from `my_book.sty`.
- No colour fills except white (and light gray only if the scan is shaded disks).
- Labels in math: $(a,b)$, $\varepsilon$, not OCR junk.
- Ignore neighbouring problem text that leaked into a crop.
- Do not trace the PNG. Named $f$ → real `\addplot`. Generic wiggles → a smooth made-up curve with the same zeros/extrema idea.
- FreeCAD only for true solids (Hanoi, cylinder∩plane, Dandelin cones). Line-art, single stroke, like `generators/calcu5-fig1.py`.

## AI previews

`python3 preview-figures.py` writes 300 dpi JPEGs to `ai-preview/`. That
folder is not `\input` by the book. Attach those JPEGs in chat next to
the matching `scans/chNN-figMM.png`.
