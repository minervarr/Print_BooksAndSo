# Reconstruction notes

One heading per file. Point at the matching `sources/calcuN.pdf`.
Leave bullets for the agent who transcribes that file.

## frontmatter/title.tex
- source: `sources/calcu1.pdf`

## frontmatter/copyright.tex
- source: `sources/calcu2.pdf`

## frontmatter/preface.tex
- source: `sources/calcu3.pdf`

## frontmatter/contents.tex
- source: `sources/calcu4.pdf`

## chapter01
- source: `sources/calcu5.pdf` — Basic Properties of Numbers (book pp.~3–20).
- PDF map: p.1–2 are the unit split cover / “in this chapter”; Part~I starts at p.3 (part page), p.4 Disraeli, p.5 ch.1 opener. PDF p.14 is book p.14 and PDF p.15 is book p.12 (leaves swapped in the split).
- Epigraph is in `main.tex` immediately after `\partdivider{I}{Prologue}`, not in this file.
- Scan-over-OLD corrections: Problem~4(x) is $(x-\sqrt[3]{2})(x-\sqrt{2})>0$ (OLD had $\sqrt{2}$ twice); Problem~3(iv) is $ac/db$ (not $bd$); Problem~16(d) hint starts $x^3+2x^2y+\cdots$ (OLD had $x^2$); Theorem~1 cases are $(1)$–$(4)$, not roman; abs definition and theorem cases use $\ge0$/$\le0$; “positive”/“negative”/“absolute value” are bold.
- OCR fixes (subscripts, $\neq$, $\sqrt{\phantom{x}}$, $\varepsilon$, $\lambda$): as in OLD notes for calcu5. Division-by-zero sentence italicizes *always*.
- Vision-checked against `pdftoppm` of calcu5 pp.~5–22. No remaining `% [reconstructed]` flags in this file.

## chapter02
- source: `sources/calcu5.pdf` — Numbers of Various Sorts (book pp.~21–35).
- PDF map: calcu5 p.23 = book p.21, then sequential through p.37 = book p.35
  (no swapped leaves in this half of the unit; ch.1’s p.14/p.12 swap is
  earlier).
- Scan-over-OLD corrections (OLD `calcu5.tex` from `\spivakchapter{2}`):
  - Number systems are bold $\mathbf{N},\mathbf{Z},\mathbf{Q},\mathbf{R}$,
    not blackboard bold.
  - Complete induction assumes $P(l)$ for $l \leq k$ (OLD had $<$).
  - $\sum i$ dummy-variable examples are three displayed identities
    ($\sum_{j=1}^{n} j$, $\sum_{j=1}^{i} j$, $\sum_{n=1}^{j} n$), not
    $\sum i = \sum j$.
  - Sum excluding $i=4$ writes $a_1+a_2+a_3+a_5+a_6+\cdots+a_n$ (OLD
    dropped $a_6$).
  - Problem~3(e) has four parts (total, alternating, odd, even); OLD had
    only the total in 3(e) and put the alternating sum in 4(b).
  - Problem~4(a) is $\sum_{k=0}^{l}\binom{n}{k}\binom{m}{l-k}=\binom{n+m}{l}$;
    4(b) is $\sum_{k=0}^{n}\binom{n}{k}^{2}=\binom{2n}{n}$.
  - Binomial theorem also equals $\sum_{j=0}^{n}\binom{n}{j}a^{n-j}b^{j}$.
  - Problem~7 Faulhaber list is a single column (not two).
- Figure~1 (Problem~26, Tower of Hanoi): scan crop
  `assets/scans/ch02-fig01.png` (from the 4th-edition scan p.55 via
  `crop-scan.py`). Generator `assets/generators/calcu5-fig1.py`
  → `assets/rendered/calcu5-fig1.svg`. Included with
  `\includesvg[width=0.95\textwidth,inkscapelatex=false]` so the native
  243.6 mm SVG scales to the 130 mm digital / print-h measure; digits 2/3
  are SVG paths (do not let Inkscape overlay TeX). Caption is `\figlabel{1}`.
- Vision-checked formulas against `pdftoppm` of calcu5 pp.~23–37. No
  remaining `% [reconstructed]` flags in this file.

## chapter03
- source: `sources/chapters/ch03-functions.pdf` (original scan pp.~57–76;
  book pp.~39–55). Slice p.1 = Part~II Foundations, p.2 blank, p.3 Dedekind
  epigraph — those live in `main.tex`, not this file. Body starts at slice
  p.4 = book p.39 (`\spivakchapter{3}{Functions}`).
- PDF map (attached slice → book): 4→39, 5→40, …, 18→53 problems, 19→54
  appendix, 20→55 end of proof. No swapped leaves.
- `crops: none`. Chapter~3 has no FIGURE~n drawings.
- Structure: opening prose is outside `spivakdefn`. Only the sentence
  “A function is a rule…” is `\begin{spivakdefn}[PROVISIONAL DEFINITION]`.
  Two later unnumbered DEFINITION boxes (function as pairs; domain / \(f(a)\))
  are `spivakdefn`. Appendix “Ordered Pairs” is in this file after the
  problems (`% Appendix. Ordered Pairs`).
- Problems 1–5 use `romans`; from 6 onward `letters`. Stars as in the scan:
  `*(c)(d)` on 10, `*(d)(e)` on 11, `*13`, `*16`–`*20`, `*24`–`*26`, and
  `*(c)` on 28.
- Scan facts (do not “correct”): Ex.~4 is \(-17\le x\le\pi/3\); Ex.~6 maps
  17 to \(36/\pi\) and \(\pi^2/17\) to 28, with blackboard \(\mathbb{Q}\);
  rewrite (8) is named \(y\); \(k(x)=1/x+1/(x-1)\); nested eval is
  \(f(r(s(\theta(\alpha_3(y(1/3))))))=1\); after \(s(x+y)\):
  \(\theta(\pi^2/17)=\theta(36/\pi)\), \(y(1/3)=0\), \(y(7/9)=-\pi\);
  (9)–(12) as on pp.~42–43; Problem~1(ii) is \(f(1/x)\); Problem~2 \(h\) is
  the 0/1 rational/irrational function with \(\le\); Problem~3(ii)
  \(\sqrt{1-\sqrt{1-x^2}}\); Problem~4 \(P(x)=2^x\) and “you answer”
  (as printed); Problem~5 (i) \(2^{\sin x}\), (ii) \(\sin 2^x\),
  (vi) \(\sin(2^u+2^{u^2})\); Problem~9 is only (a)(b)(c); Problem~10 is
  separate; Problem~11(c) is \(H(H(y))=H(y)\). \(\mathbf{R}\) elsewhere
  (bold, matching ch.~2). Book writes “simple” not “simply” in the two
  abbreviation sentences.
- Vision-checked against `pdftoppm` of `ch03-functions.pdf` pp.~4–20.
  No `% [reconstructed]` flags.

## chapter04
- source: `sources/chapters/ch04-graphs.pdf` (book pp.~56–89; original scan
  pp.~77–110). Unit `calcu6.pdf` is coarser.
- PDF map: slice p.1 = book p.56 (chapter opener). Slice pp.~3–4 are book
  59 then 58 (swapped leaves, as in ch.1’s p.14/p.12). Remaining pages
  sequential. Appendices stay in this file: 1 Vectors (book p.75 / slice
  p.20), 2 The Conic Sections (p.80 / p.25), 3 Polar Coordinates (p.84 /
  p.29).
- Type from `pdftoppm` of the chapter slice, not OCR. OCR drops $\varepsilon$,
  $\Lambda$, $\pm$, and swaps $<$ with $\leq$.
- Scan traps: Problem~1 uses (i)–(viii) not (a); 1(v) is
  $1/(1+x^2)\ge 1/2$; 1(vii) $x^2+1\ge 2$. Problem~5(ii) is
  $y^2/a^2-x^2/b^2=1$. Problem~13(b) is $\lvert\sin x\rvert$ and $\sin^2 x$.
  Problem~16 is $Ax^2+Bx+Cy^2+Dy+E=0$ (hint still says “$A$ and $B$”).
  Problem~17 is the floor $[x]$; 17(vi) is $1/[1/x]$. Problem~18 $\{x\}$ is
  distance to the nearest integer. Stars on *19, *20, *22, *23 only.
  Polar constant is $\Lambda=(1-\varepsilon^2)a$, not $A$. Book typo “Out
  last example”; Vectors “we've haven't”; slope of $M$ prints
  $(v_1+w_1)-v_2$ in the denominator.
- $\mathbf{R}$ (bold, matching ch.~1–2). Empty set $\emptyset$.
- Figures: book FIGURE 1–31 → `ch04-fig01`–`31` (main-text still TODO crops).
  Appendix figures restart in the scan; files stay sequential: App.~1
  FIGURE 1–10 → fig32–41; App.~2 FIGURE 1–9 → fig42–50; App.~3 FIGURE 1–8
  → fig51–58. Crops from the chapter PDF (`crop-scan.py --pdf …/ch04-graphs.pdf`).
- Appendix reconstructions (32–58): TikZ in `assets/geometric/ch04-figNN.tex`
  except solids 47–50, which are FreeCAD line-art
  `assets/generators/ch04-figNN.py` → `assets/rendered/ch04-figNN.svg`
  (`inkscapelatex=false`). Fig.~46 is the 2-D slope diagram, so TikZ.
  Printed `\figlabel` restarts per appendix.

## chapter05
- source: `sources/chapters/ch05-limits.pdf` (orig.\ pp.\ 111–135; book pp.\ 90–114)
- PDF map (attached → printed): 1→90, 2→91, …, 14→103, **16→104**, **15→105**, 17→106, …, 23→112, **25→113**, **24→114**. Leaves 104/105 and 113/114 are swapped in the slice; body is in book order.
- Typed from `pdftoppm` of the chapter PDF. Bitmap displays (ε-δ work, piecewise graphs) typed as TeX, not cropped.
- OCR traps: ε/δ vs e/s/5; `l` vs `1` vs `I`; `sin 1/x`; `\mathbf{R}` not blackboard; Thomae list omits non-lowest-terms; Problem 32 is `m\geq n`; Problem 15(xi) cube is on the parenthesis; Problem 42 cites “Figure 19” while the drawing is labelled FIGURE 20 (kept as printed). Page 92 prints `|f(x)-a|<ε` for `f(x)=3{,}000{,}000x`.
- Figures 1–20: `assets/scans/ch05-fig01.png`–`ch05-fig20.png` (crops from the chapter PDF). No `\includegraphics`.
- Problems 1–42, including `*5`, `*14`, `*20`, `**23`, `*24`, `*26`, `*28`, `*42`. Romans vs letters as in the scan. Unnumbered LEMMA via `\begin{spivakdefn}[LEMMA]`.

## chapter06
- source: `sources/chapters/ch06-continuous-functions.pdf` (original pp.~136–142;
  book pp.~115–121). Typed from `pdftoppm` of that slice, not OCR.
- PDF map (1-based in the chapter PDF): p.1 = book 115, p.2 = 116,
  p.3 = 117, **p.4 = 119, p.5 = 118** (leaves swapped), p.6 = 120,
  p.7 = 121. Body is in printed order.
- Scan wording kept: “(if fact, we must)” at $G(0)=0$; “There theorems
  are generally much harder…” (book p.~119).
- $\mathbf{R}$, not blackboard. $\varepsilon$/$\delta$. Problems 4-17
  and 4-19 as printed. Problem~8 uses $\alpha$. Problem~16 uses
  $0 \leq x-a < \delta$. 17(d)\*(e)\*\* are starred subparts.
- Figures 1–5 redrawn (scans remain the model only): geometric
  `ch06-fig01,02,03,05`; plot `ch06-fig04` is $x\sin(5/x)$ for $g$/$G$.

## chapter07
- source: `sources/chapters/ch07-three-hard-theorems.pdf` (original scan
  pp.~143–153 = book pp.~122–132). Not `sources/calcu7.pdf` (that is Part~III).
- PDF map: chapter-PDF p.1 = book p.122, then sequential except two swapped
  leaves (same class of split as ch.1): PDF p.6 = book p.128, PDF p.7 = book
  p.127; PDF p.10 = book p.132, PDF p.11 = book p.131. Transcribed in book
  order 122–132.
- Theorems 1–3 are IVT-seed / bounded-above / attains-maximum on $[a,b]$;
  proofs deferred to ch.8. Square-root theorem uses $\alpha$, not $a$.
- OCR traps: $\leq$ vs $<$ (Thm~2 is $\leq N$); $\alpha$ vs $a$; $N_1,N_2$;
  $x^{179}$ and $163/(1+x^2+\sin^2 x)=119$ in Problem~3; floor $[x]$ in 1(xii);
  $\mathbf{R}$ bold, not blackboard; P1--P12 in running text.
- Figures 1–16 redrawn (scans remain the model only): geometric cartoons
  except plots `ch07-fig05` ($1/x$) and `ch07-fig07` ($x^2$). Unnamed
  IVT/EVT wiggles are smooth stand-ins with the same extrema/zeros.
- Vision-typed from `pdftoppm` of the chapter scan. No `% [reconstructed]`.

## chapter08
- source: `sources/chapters/ch08-least-upper-bounds.pdf` (original pp.~154–167 = book pp.~133–146). Also in `sources/calcu6.pdf`.
- PDF map: slice p.1 = book 133 (opener). Slice pp.~2 and~4 are swapped: p.2 = book 135, p.4 = book 134, then p.3 = 136, p.5 = 137, \ldots, p.14 = 146. Typed in book order.
- Appendix. Uniform Continuity lives in this same file after the chapter problems (book pp.~144–146).
- Number systems are bold $\mathbf{N},\mathbf{Z},\mathbf{Q},\mathbf{R}$, not blackboard. Empty set is $\emptyset$. Least-upper-bound points are $\alpha$.
- THEOREM 7-1/7-2/7-3 are restated from Chapter~7 (unnumbered here, so the chapter’s THEOREM 1–3 and the appendix THEOREM 1 keep the book’s numbers). Appendix LEMMA is unnumbered. Appendix THEOREM 1 resets the theorem counter.
- OCR traps: $\geq$ vs $>$ in the bounded-above definition; mixed numbers $1\frac12$, $1\frac14$; $g(x)=1/(\alpha-f(x))$; Archimedes $\frac{223}{71}<\pi<\frac{22}{7}$; Problem~1(v) is $x^2+x+1\geq 0$; *9 is $\lvert\lvert\lvert f\rvert\rvert\rvert$; *11(d); $\varlimsup$/$\varliminf$ in *18–*19.
- Unlabeled number line in the Archimedean-property paragraph is TikZ (not a FIGURE). Cross-refs “Figure 18 on page 62” and “page 450” / “page 142” kept as printed.
- Figures: `ch08-fig01`–`fig09` = FIGURE 1–9; `ch08-fig10`/`fig11` = appendix FIGURE 1–2. Reconstructed as TikZ/pgfplots under `assets/plots/` and `assets/geometric/`. Scans remain the model only.

## chapter09
- source: `sources/calcu7.pdf` — Derivatives

## chapter10
- source: `sources/calcu7.pdf` — Differentiation

## chapter11
- source: `sources/calcu7.pdf` — Significance of the Derivative

## chapter12
- source: `sources/calcu7.pdf` — Inverse Functions

## chapter13
- source: `sources/calcu7.pdf` — Integrals

## chapter14
- source: `sources/calcu7.pdf` — The Fundamental Theorem of Calculus

## chapter15
- source: `sources/calcu7.pdf` — The Trigonometric Functions

## chapter16
- source: `sources/calcu7.pdf` — π is Irrational

## chapter17
- source: `sources/calcu7.pdf` — Planetary Motion

## chapter18
- source: `sources/calcu7.pdf` — The Logarithm and Exponential Functions

## chapter19
- source: `sources/calcu7.pdf` — Integration in Elementary Terms

## chapter20
- source: `sources/calcu8.pdf` — Approximation by Polynomial Functions

## chapter21
- source: `sources/calcu8.pdf` — e is Transcendental

## chapter22
- source: `sources/calcu8.pdf` — Infinite Sequences

## chapter23
- source: `sources/calcu8.pdf` — Infinite Series

## chapter24
- source: `sources/calcu8.pdf` — Uniform Convergence and Power Series

## chapter25
- source: `sources/calcu8.pdf` — Complex Numbers

## chapter26
- source: `sources/calcu8.pdf` — Complex Functions

## chapter27
- source: `sources/calcu8.pdf` — Complex Power Series

## chapter28
- source: `sources/calcu9.pdf` — Fields

## chapter29
- source: `sources/calcu9.pdf` — Construction of the Real Numbers

## chapter30
- source: `sources/calcu9.pdf` — Uniqueness of the Real Numbers

## backmatter/suggested-reading.tex
- source: `sources/calcu10.pdf`

## backmatter/answers.tex
- source: `sources/calcu11.pdf`

## backmatter/glossary.tex
- source: `sources/calcu12.pdf`

## backmatter/index.tex
- source: `sources/calcu13.pdf`
