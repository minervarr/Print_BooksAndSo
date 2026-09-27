#!/usr/bin/env python3
"""Chapter PDFs, chat prompt, and a compile test.

One original scan → one descriptively named PDF per chapter (appendices
stay with their chapter). Names are automatic: ch03-functions.pdf.

    python3 chapter.py list
    python3 chapter.py split              # write sources/chapters/*.pdf
    python3 chapter.py pdf 3              # print path (splits if missing)
    python3 chapter.py test 3             # compile + checks; no human “is it ok?”
    python3 chapter.py test-html          # MathJax gate on html/ (no rebuild)
    python3 chapter.py prompt 3           # prompt to paste in a chat, with PDF path

stdlib + qpdf + lualatex.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ORIGINAL = ROOT / "sources" / "Michael Spivak - Calculus, 4th Edition (2008).pdf"
OUT_DIR = ROOT / "sources" / "chapters"
PROJECT = ROOT / "the_book_project"
HTML_DIR = ROOT / "html"
MATHJAX_ALLOW = PROJECT / "mathjax-allow.txt"
MATHJAX_DENY = frozenset({"cline", "multicolumn", "arraystretch"})
MATHJAX_SPAN = re.compile(
    r"<(?:span|div) class='mathjax[^']*'[^>]*>(.*?)</(?:span|div)>",
    re.S,
)
ENGINE = (
    "lualatex",
    "-interaction=nonstopmode",
    "-halt-on-error",
    "-shell-escape",
)


def slug(title: str) -> str:
    s = title.lower()
    s = s.replace("π", "pi")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


# start/end are 1-based inclusive pages in the source scan (outline).
# Appendices are folded into the parent chapter. Part pages go with the
# first chapter of that part.
CATALOG: list[dict] = [
    {"kind": "front", "key": "title", "title": "Title page", "start": 8, "end": 8,
     "tex": "frontmatter/title.tex"},
    {"kind": "front", "key": "copyright", "title": "Copyright", "start": 9, "end": 10,
     "tex": "frontmatter/copyright.tex"},
    {"kind": "front", "key": "preface", "title": "Preface", "start": 11, "end": 17,
     "tex": "frontmatter/preface.tex"},
    {"kind": "front", "key": "contents", "title": "Contents", "start": 18, "end": 21,
     "tex": "frontmatter/contents.tex"},
    {"kind": "chapter", "num": 1, "title": "Basic Properties of Numbers", "start": 22, "end": 41},
    {"kind": "chapter", "num": 2, "title": "Numbers of Various Sorts", "start": 42, "end": 56},
    {"kind": "chapter", "num": 3, "title": "Functions", "start": 57, "end": 76},
    {"kind": "chapter", "num": 4, "title": "Graphs", "start": 77, "end": 110},
    {"kind": "chapter", "num": 5, "title": "Limits", "start": 111, "end": 135},
    {"kind": "chapter", "num": 6, "title": "Continuous Functions", "start": 136, "end": 142},
    {"kind": "chapter", "num": 7, "title": "Three Hard Theorems", "start": 143, "end": 153},
    {"kind": "chapter", "num": 8, "title": "Least Upper Bounds", "start": 154, "end": 167},
    {"kind": "chapter", "num": 9, "title": "Derivatives", "start": 168, "end": 188},
    {"kind": "chapter", "num": 10, "title": "Differentiation", "start": 189, "end": 208},
    {"kind": "chapter", "num": 11, "title": "Significance of the Derivative", "start": 209, "end": 250},
    {"kind": "chapter", "num": 12, "title": "Inverse Functions", "start": 251, "end": 273},
    {"kind": "chapter", "num": 13, "title": "Integrals", "start": 274, "end": 305},
    {"kind": "chapter", "num": 14, "title": "The Fundamental Theorem of Calculus", "start": 306, "end": 322},
    {"kind": "chapter", "num": 15, "title": "The Trigonometric Functions", "start": 323, "end": 344},
    {"kind": "chapter", "num": 16, "title": "Pi is Irrational", "start": 345, "end": 350},
    {"kind": "chapter", "num": 17, "title": "Planetary Motion", "start": 351, "end": 359},
    {"kind": "chapter", "num": 18, "title": "The Logarithm and Exponential Functions", "start": 360, "end": 383},
    {"kind": "chapter", "num": 19, "title": "Integration in Elementary Terms", "start": 384, "end": 428},
    {"kind": "chapter", "num": 20, "title": "Approximation by Polynomial Functions", "start": 429, "end": 462},
    {"kind": "chapter", "num": 21, "title": "e is Transcendental", "start": 463, "end": 472},
    {"kind": "chapter", "num": 22, "title": "Infinite Sequences", "start": 473, "end": 491},
    {"kind": "chapter", "num": 23, "title": "Infinite Series", "start": 492, "end": 519},
    {"kind": "chapter", "num": 24, "title": "Uniform Convergence and Power Series", "start": 520, "end": 546},
    {"kind": "chapter", "num": 25, "title": "Complex Numbers", "start": 547, "end": 561},
    {"kind": "chapter", "num": 26, "title": "Complex Functions", "start": 562, "end": 575},
    {"kind": "chapter", "num": 27, "title": "Complex Power Series", "start": 576, "end": 599},
    {"kind": "chapter", "num": 28, "title": "Fields", "start": 600, "end": 609},
    {"kind": "chapter", "num": 29, "title": "Construction of the Real Numbers", "start": 610, "end": 621},
    {"kind": "chapter", "num": 30, "title": "Uniqueness of the Real Numbers", "start": 622, "end": 628},
    {"kind": "back", "key": "suggested-reading", "title": "Suggested Reading", "start": 629, "end": 639,
     "tex": "backmatter/suggested-reading.tex"},
    {"kind": "back", "key": "answers", "title": "Answers", "start": 640, "end": 685,
     "tex": "backmatter/answers.tex"},
    {"kind": "back", "key": "glossary", "title": "Glossary of Symbols", "start": 686, "end": 689,
     "tex": "backmatter/glossary.tex"},
    {"kind": "back", "key": "index", "title": "Index", "start": 690, "end": 701,
     "tex": "backmatter/index.tex"},
]


def stem(entry: dict) -> str:
    if entry["kind"] == "chapter":
        return f"ch{entry['num']:02d}-{slug(entry['title'])}"
    prefix = "front" if entry["kind"] == "front" else "back"
    return f"{prefix}-{slug(entry['title'])}"


def tex_path(entry: dict) -> Path:
    if entry["kind"] == "chapter":
        return PROJECT / "chapters" / f"chapter{entry['num']:02d}.tex"
    return PROJECT / entry["tex"]


def pdf_path(entry: dict) -> Path:
    return OUT_DIR / f"{stem(entry)}.pdf"


def find_entry(token: str) -> dict:
    token = token.strip().lower()
    token = token.removeprefix("chapter").removeprefix("ch")
    for e in CATALOG:
        if e.get("num") is not None and token == str(e["num"]):
            return e
        if token in (e.get("key") or "", stem(e), slug(e["title"])):
            return e
        if e.get("num") is not None and token == f"{e['num']:02d}":
            return e
    raise SystemExit(f"unknown chapter {token!r} (try: python3 chapter.py list)")


def cmd_list(_: argparse.Namespace) -> int:
    for e in CATALOG:
        print(f"{stem(e):55}  pp.{e['start']}-{e['end']:3}  {tex_path(e).relative_to(PROJECT)}")
    return 0


def split_one(entry: dict) -> Path:
    if not ORIGINAL.is_file():
        raise SystemExit(f"missing {ORIGINAL}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dest = pdf_path(entry)
    subprocess.run(
        [
            "qpdf",
            str(ORIGINAL),
            "--pages", ".",
            f"{entry['start']}-{entry['end']}",
            "--",
            str(dest),
        ],
        check=True,
    )
    return dest


def cmd_split(_: argparse.Namespace) -> int:
    for e in CATALOG:
        p = split_one(e)
        print(p)
    return 0


def cmd_pdf(args: argparse.Namespace) -> int:
    e = find_entry(args.which)
    dest = pdf_path(e)
    if not dest.is_file():
        dest = split_one(e)
    print(dest)
    return 0


def is_stub(text: str) -> bool:
    if "Not yet written" in text:
        return True
    code = [
        ln
        for ln in text.splitlines()
        if ln.strip() and not ln.strip().startswith("%")
    ]
    return len(code) < 4


def compile_unit(entry: dict, outdir: Path) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    rel = tex_path(entry).relative_to(PROJECT).as_posix()
    job = "unit"
    unit = outdir / f"{job}.tex"
    if entry["kind"] == "chapter":
        body = (
            r"\documentclass[11pt,oneside,openany]{book}" "\n"
            r"\usepackage{my_book}" "\n"
            r"\begin{document}" "\n"
            r"\mainmatter" "\n"
            f"\\input{{{rel}}}" "\n"
            r"\end{document}" "\n"
        )
    elif entry["kind"] == "front":
        body = (
            r"\documentclass[11pt,oneside,openany]{book}" "\n"
            r"\usepackage{my_book}" "\n"
            r"\begin{document}" "\n"
            r"\frontmatter" "\n"
            f"\\input{{{rel}}}" "\n"
            r"\end{document}" "\n"
        )
    else:
        body = (
            r"\documentclass[11pt,oneside,openany]{book}" "\n"
            r"\usepackage{my_book}" "\n"
            r"\begin{document}" "\n"
            r"\backmatter" "\n"
            f"\\input{{{rel}}}" "\n"
            r"\end{document}" "\n"
        )
    unit.write_text(body)
    cmd = [
        *ENGINE,
        f"-output-directory={outdir}",
        f"-jobname={job}",
        unit.name,
    ]
    result = subprocess.run(cmd, cwd=PROJECT, capture_output=True, text=True)
    log = outdir / f"{job}.log"
    pdf = outdir / f"{job}.pdf"
    if result.returncode != 0 or not pdf.is_file():
        tail = log.read_text(errors="replace")[-4000:] if log.is_file() else result.stderr
        raise SystemExit(f"FAIL compile\n{tail}")
    return pdf


def cmd_test(args: argparse.Namespace) -> int:
    e = find_entry(args.which)
    tex = tex_path(e)
    if not tex.is_file():
        raise SystemExit(f"FAIL missing {tex}")
    text = tex.read_text()
    failures: list[str] = []
    if is_stub(text):
        failures.append("still a stub (Not yet written / almost empty)")

    for m in re.finditer(
        r"TODO figure\s+(\d+)\s+(assets/scans/ch\d{2}-fig\d{2}\.png)",
        text,
    ):
        png = PROJECT / m.group(2)
        if not png.is_file():
            failures.append(f"TODO figure {m.group(1)} missing {png.name}")

    bad_scan = re.findall(r"assets/scans/(?!ch\d{2}-fig\d{2}\.png)[\w./-]+", text)
    for b in bad_scan:
        failures.append(f"scan name not chNN-figMM: {b}")

    if r"\includegraphics" in text and "scans/" in text:
        failures.append("do not \\includegraphics a scan crop into the book")

    outdir = PROJECT / "build" / "test" / stem(e)
    if not is_stub(text) or args.force_compile:
        pdf = compile_unit(e, outdir)
        log = (outdir / "unit.log").read_text(errors="replace")
        if re.search(r"^!", log, re.M):
            failures.append("TeX error in log")
        over = re.findall(r"Overfull \\hbox \(([\d.]+)pt", log)
        fat = [o for o in over if float(o) > 20]
        if fat:
            failures.append(f"overfull > 20pt ({len(fat)} boxes)")
        extracted = subprocess.check_output(["pdftotext", str(pdf), "-"], text=True, errors="replace")
        needle = e["title"].split()[0]
        if needle.lower() not in extracted.lower() and e["kind"] == "chapter":
            failures.append(f"PDF text missing title word {needle!r}")
        print(f"compiled {pdf}")
    else:
        print("skip compile (stub)")

    if failures:
        print("FAIL")
        for f in failures:
            print(" -", f)
        return 1
    print("PASS", tex.relative_to(PROJECT))
    return 0


def load_mathjax_allow() -> set[str]:
    names: set[str] = set()
    if not MATHJAX_ALLOW.is_file():
        raise SystemExit(f"FAIL missing {MATHJAX_ALLOW}")
    for line in MATHJAX_ALLOW.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            names.add(line)
    return names


def html_mathjax_failures(html_dir: Path | None = None) -> list[str]:
    """Unknown / forbidden TeX in MathJax spans. Empty = pass."""
    html_dir = html_dir or HTML_DIR
    allow = load_mathjax_allow()
    failures: list[str] = []
    pages = sorted(html_dir.glob("index*.html"))
    if not pages:
        return [f"no index*.html in {html_dir}"]

    cmd_re = re.compile(r"\\([a-zA-Z]+)")
    array_at = re.compile(r"\\begin\s*\{array\}\s*\{[^}]*@")
    found_abs_macro = False

    for path in pages:
        text = path.read_text(encoding="utf-8", errors="replace")
        if "macros:" in text and re.search(r"\babs\s*:", text):
            found_abs_macro = True

        for m in MATHJAX_SPAN.finditer(text):
            chunk = m.group(1)
            if array_at.search(chunk):
                snippet = re.sub(r"\s+", " ", chunk)[:80]
                failures.append(f"{path.name}: array preamble with @ (MathJax): {snippet}")
            for name in cmd_re.findall(chunk):
                if name in MATHJAX_DENY:
                    snippet = re.sub(r"\s+", " ", chunk)[:80]
                    failures.append(f"{path.name}: forbidden \\{name}: {snippet}")
                elif name not in allow:
                    snippet = re.sub(r"\s+", " ", chunk)[:80]
                    failures.append(f"{path.name}: unknown \\{name}: {snippet}")

        stripped = re.sub(r"<(script|style)[\s\S]*?</\1>", "", text, flags=re.I)
        stripped = MATHJAX_SPAN.sub("", stripped)
        leaked = cmd_re.findall(stripped)
        if leaked:
            extra = sorted(set(leaked))[:8]
            failures.append(f"{path.name}: TeX leak outside math: {', '.join(extra)}")

        for src in re.findall(r"<img[^>]+src='([^']+)'", text):
            if src.startswith("http"):
                continue
            img = path.parent / src
            if not img.is_file():
                failures.append(f"{path.name}: missing image {src}")

    # Dedup while keeping order
    seen: set[str] = set()
    uniq: list[str] = []
    for f in failures:
        if f not in seen:
            seen.add(f)
            uniq.append(f)

    index = html_dir / "index.html"
    if index.is_file() and not found_abs_macro:
        uniq.append("index.html: MathJax config missing macros.abs")
    return uniq


def cmd_test_html(_args: argparse.Namespace) -> int:
    failures = html_mathjax_failures()
    if failures:
        print("FAIL html MathJax")
        for f in failures:
            print(" -", f)
        return 1
    print("PASS html MathJax", HTML_DIR / "index.html")
    return 0


PROMPT = """You are transcribing one piece of Spivak, Calculus 4e, into an existing LuaLaTeX tree. Copy-typist, not architect. One file. Then stop.

Repo: {repo}
Work only under book/Caculus4th/

READ FIRST:
- book/Caculus4th/README.md (Chat / one chapter)
- book/Caculus4th/the_book_project/PROGRESS.md
- book/Caculus4th/the_book_project/assets/scans/README.md

THIS JOB:
- Scan PDF (attach this file): {pdf}
- Write: {tex}
- Title: {title}
- Source-scan pages {start}–{end} (already sliced).

RULES:
- Type from the attached PDF pages (pictures), not from OCR guesses.
- Keep existing \\spivakchapter. No \\chapter. No \\partdivider / \\epigraph in the chapter file.
- Macros: \\prop \\pnum theorem/proof spivakdefn \\abs \\figlabel romans/letters/steps. “domain” not dom. Bold systems \\mathbf{{N}} unless the scan is blackboard. Stars: \\pnum{{*8.}}
- FIGURE n only: crop with
  python3 book/Caculus4th/the_book_project/assets/crop-scan.py --pdf {pdf} --page P --x X --y Y --width W --height H --name ch{num:02d}-figMM
  P is 1-based in the ATTACHED chapter PDF. Name ch{num:02d}-figMM.
  Do not \\includegraphics the PNG. Leave: % TODO figure MM  assets/scans/ch{num:02d}-figMM.png
  Equations (even if they are bitmaps) are TeX, not scans/.
- Do not edit other chapters, OLD/, kit/, geometry, build.py.
- No HTML/EPUB.

VERIFY YOURSELF (do not ask me if it is good):
  python3 book/Caculus4th/chapter.py test {token}
It must print PASS. If FAIL, fix and run again until PASS. Then stop.
Update notes.md (## this file) and PROGRESS.md → drafted.

Do not start the next chapter.
"""


def cmd_prompt(args: argparse.Namespace) -> int:
    e = find_entry(args.which)
    dest = pdf_path(e)
    if not dest.is_file():
        dest = split_one(e)
    latex_ai = ROOT.parent.parent  # LATEX_AI/  (ROOT is Caculus4th)
    num = e.get("num") or 0
    token = str(e["num"]) if e.get("num") is not None else e.get("key") or stem(e)
    print(
        PROMPT.format(
            repo=str(latex_ai),
            pdf=str(dest),
            tex=str(tex_path(e).relative_to(latex_ai)),
            title=e["title"],
            start=e["start"],
            end=e["end"],
            num=num if num else 0,
            token=token,
        )
    )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="stems, page ranges, tex files")
    sub.add_parser("split", help="write all sources/chapters/*.pdf")
    p = sub.add_parser("pdf", help="path to one chapter PDF (split if needed)")
    p.add_argument("which")
    t = sub.add_parser("test", help="compile + checks; exit 1 if not done")
    t.add_argument("which")
    t.add_argument("--force-compile", action="store_true")
    sub.add_parser("test-html", help="MathJax gate on html/; no rebuild")
    pr = sub.add_parser("prompt", help="print the chat prompt for one chapter")
    pr.add_argument("which")
    args = ap.parse_args()
    if args.cmd == "list":
        return cmd_list(args)
    if args.cmd == "split":
        return cmd_split(args)
    if args.cmd == "pdf":
        return cmd_pdf(args)
    if args.cmd == "test":
        return cmd_test(args)
    if args.cmd == "test-html":
        return cmd_test_html(args)
    if args.cmd == "prompt":
        return cmd_prompt(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
