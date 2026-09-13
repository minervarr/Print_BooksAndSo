# Reconstruction notes (per-chapter log)

Durable memory for agents. Read the relevant section before working a unit;
append after finishing. Format: one `## calcuN` block per unit.

---

## calcu1 — Title page

- Source: 4 scanned pages; only the first carries text ("CALCULUS / Fourth
  Edition / Michael Spivak"), the rest blank.
- Reproduced as one short page. No OCR issues.

## calcu2 — Copyright + dedication

- Reproduced the copyright block, publisher imprint, ISBN, and the closing
  dedication ("Dedicated to the Memory of Y. P.") as one page.
- OCR read "ofAmerica" as one word (missing space); fixed.

## calcu3 — Preface

- Four editions (first/second/third/fourth). Each opens with an all-caps
  heading, closes with a right-aligned signature.
- Bacon epigraph reproduced via `\epigraph` (kept short, right-aligned).
- OCR fixes: "math­ematical" (soft hyphen), "difficulty'" (stray quote),
  "Starring and double starring" -> "starring and double starring",
  "provided a good test" -> "provide a good test",
  "Needles to say" -> "Needless to say".

## calcu4 — Contents

- Reproduced as a static list (not `\tableofcontents`) with `\dotfill`
  leaders, matching the source's part/chapter/page layout.
- OCR fixes: "PARTI" -> "PART I", "PARTY" -> "PART V", "7T" -> "$\pi$".

## calcu5 — Part I: Prologue (Ch. 1 "Basic Properties of Numbers", Ch. 2 "Numbers of Various Sorts")

### Structure
- `\partdivider{I}{Prologue}` then Disraeli `\epigraph`, then two
  `\spivakchapter`s. Matches the source's divider -> quote -> chapter flow.

### Environment/style decisions (added to preface.tex)
- `\spivakchapter{n}{title}`: fresh page, big chapter number. The 2008 scan
  uses a plain run-in "CHAPTER ■ title" line with no number; we use the
  classic Computer Modern opener with a large number instead (owner chose
  "classic Spivak" identity). No number was lost — the scan has none.
- `\prop{n}` for the (P1)..(P12) property labels.
- `\pnum{...}` + `romans`/`letters` lists for the problem sets (starred
  problems written as `\pnum{*8.}` etc.).
- `theorem` (italic body) / `proof` (caps, $\blacksquare$) numbered per
  chapter with no chapter prefix (book prints "THEOREM 1").

### OCR corrections worth noting
- Subscripts/symbols were heavily mangled: "a\ + • • • + an" -> $a_1+\cdots+a_n$,
  "a\,... ,an" -> $a_1,\dots,a_n$, "4-" and "-I-" -> "$+$", "7T" -> $\pi$,
  "V2"/"f2" -> $\sqrt{2}$, "N"/"Z"/"Q"/"R" -> $\mathbb N/\mathbb Z/\mathbb Q/\mathbb R$,
  "n\" -> $n!$, "ÍÍÍ_tl2" -> $\frac{k(k+1)}2$.
- Absolute-value definition: source OCR shows "a>0"/"a<0"; restored the
  standard $\ge0$/$\le0$ definition (needed for $|0|=0$, and the text says
  "$|a|$ is always positive, except when $a=0$").
- Theorem 1 case split likewise restored to $\ge0$/$\le0$ cases.

### Reconstructed (OCR-lost) items — MUST verify against the source scan
A vision-capable agent should confirm these, marked `% [reconstructed]` in the
`.tex`:
- Ch.1 Problem 3(iv) `a/b · c/d = ac/bd`, 3(v) `(a/b)/(c/d) = ad/bc` (fraction
  rules the OCR dropped).
- Ch.1 Problem 4(xiv) `(x-1)/(x+1) > 0`.
- Ch.2 Problem 4(a) `\sum_{j=0}^k C(m,j)C(n,k-j) = C(m+n,k)`,
  4(b) `C(n,0)-C(n,1)+C(n,2)-... ± C(n,n) = 0`.
- Ch.2 Problem 7 the ten $\sum k^p$ closed forms (typed from the standard
  list; coefficients to double-check).
- Ch.2 Problem 20 the Fibonacci closed form (Binet formula).

### Figure
- Three-spindles diagram (Problem 2-26, "Figure 1") is **semantic TikZ**,
  not a pixel trace. Reference crop: `figures/scans/calcu5-fig1.png`.
  Drawing: `figures/geometric/calcu5-fig1.tex`. The old 850-polyline
  centre-line file is kept only as `figures/traces/calcu5-fig1.tex` and
  is not `\input`.
- Structure to match by eye: oblique board (front/back nearly horizontal,
  depth up-right, mild perspective); four stacked disks with shaded rims
  (light from the left); spindle cap; two empty pegs labelled `2` (on the
  back edge, taller) and `3` (right) as TeX `\node`s; caption `FIGURE 1`
  as TeX. The back edge is interrupted by peg 2, not drawn through it.
- Labels follow the document font (Computer Modern today). A pixel trace
  cannot do that; that is why the tracer was demoted to last-resort.

