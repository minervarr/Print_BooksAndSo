#!/usr/bin/env python3
"""Compile one reconstructed figure (TikZ/pgfplots) to PDF, then JPEG or SVG.

Used by preview-figures.py (AI JPEG) and export-figures-svg.py (HTML SVG).
Not imported by the book TeX.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

WRAPPER = r"""\documentclass[border=3mm]{standalone}
\usepackage{fontspec}
\usepackage{unicode-math}
\usepackage{amsmath,mathtools}
\DeclarePairedDelimiter{\abs}{\lvert}{\rvert}
\usepackage{tikz}
\usepackage{pgfplots}
\pgfplotsset{compat=1.17}
\usetikzlibrary{calc,arrows.meta,patterns,positioning,decorations.pathreplacing,angles,quotes}
\setmainfont{NewCM10-Regular}
\setmathfont{NewCMMath-Regular.otf}
\tikzset{
  reconstruction/.style={
    line cap=round,
    line join=round,
    >=Stealth,
    every node/.style={font=\normalsize},
  },
  reconstruction line/.style={line width=0.5pt, color=black},
}
\pgfplotsset{
  reconstruction plot/.style={
    axis lines=middle,
    axis line style={-Stealth, black},
    xlabel style={font=\normalsize},
    ylabel style={font=\normalsize},
    tick label style={font=\normalsize},
    legend style={font=\normalsize},
    every axis plot/.style={thick, black, mark=none},
    cycle list={{black, mark=none, thick}},
    scaled ticks=false,
    clip=false,
  },
}
\setlength{\textwidth}{140mm}
\pagestyle{empty}
\begin{document}
\input{\detokenize{@PATH@}}
\end{document}
"""


def tex_stems(assets: Path, only: str | None = None) -> list[tuple[str, Path]]:
    """TikZ/pgfplots snippets only: (stem, path)."""
    found: list[tuple[str, Path]] = []
    for folder in ("geometric", "plots"):
        for p in sorted((assets / folder).glob("ch*.tex")):
            found.append((p.stem, p))
    if only:
        found = [t for t in found if t[0] == only]
        if not found:
            raise FileNotFoundError(f"no TikZ figure named {only!r}")
    return found


def svg_sources(assets: Path, only: str | None = None) -> list[tuple[str, Path]]:
    found: list[tuple[str, Path]] = []
    for p in sorted((assets / "rendered").glob("*.svg")):
        found.append((p.stem, p))
    if only:
        found = [t for t in found if t[0] == only]
    return found


def compile_tex_pdf(src: Path, project: Path, tmp: Path, job: str) -> Path:
    rel = src.relative_to(project).as_posix()
    tex = tmp / f"{job}.tex"
    tex.write_text(WRAPPER.replace("@PATH@", rel), encoding="utf-8")
    result = subprocess.run(
        [
            "lualatex",
            "-interaction=nonstopmode",
            "-halt-on-error",
            f"-output-directory={tmp}",
            f"-jobname={job}",
            tex.name,
        ],
        cwd=project,
        capture_output=True,
        text=True,
    )
    pdf = tmp / f"{job}.pdf"
    if result.returncode != 0 or not pdf.is_file():
        log = tmp / f"{job}.log"
        tail = log.read_text(errors="replace")[-2500:] if log.is_file() else result.stderr
        raise RuntimeError(f"lualatex failed for {src.name}\n{tail}")
    return pdf


def pdf_to_jpeg(pdf: Path, dest: Path, dpi: int) -> None:
    prefix = dest.with_suffix("")
    subprocess.run(
        ["pdftoppm", "-jpeg", "-r", str(dpi), "-singlefile", str(pdf), str(prefix)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    jpg = prefix.with_suffix(".jpg")
    if jpg != dest:
        jpg.replace(dest)
    if not dest.is_file():
        raise RuntimeError(f"pdftoppm wrote nothing for {pdf}")


def pdf_to_svg(pdf: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    cairo = shutil.which("pdftocairo")
    if cairo:
        subprocess.run(
            [cairo, "-svg", str(pdf), str(dest)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
    else:
        ink = shutil.which("inkscape")
        if not ink:
            raise RuntimeError("need pdftocairo or inkscape to write SVG")
        subprocess.run(
            [ink, str(pdf), "--export-type=svg", f"--export-filename={dest}"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    if not dest.is_file():
        raise RuntimeError(f"no SVG written for {pdf}")


def svg_to_pdf(src: Path, dest: Path) -> None:
    ink = shutil.which("inkscape")
    if ink:
        subprocess.run(
            [ink, str(src), "--export-type=pdf", f"--export-filename={dest}"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return
    subprocess.run(
        ["rsvg-convert", "-f", "pdf", "-o", str(dest), str(src)],
        check=True,
    )


def up_to_date(dest: Path, src: Path) -> bool:
    return dest.is_file() and dest.stat().st_mtime >= src.stat().st_mtime


def export_tex_svg(
    src: Path,
    dest: Path,
    project: Path,
    tmp: Path,
    force: bool = False,
) -> str:
    """Write dest SVG from a TikZ snippet. Returns 'wrote' | 'skip'."""
    if not force and up_to_date(dest, src):
        return "skip"
    job = dest.stem
    pdf = compile_tex_pdf(src, project, tmp, job)
    pdf_to_svg(pdf, dest)
    return "wrote"


def nworkers(requested: int | None) -> int:
    cpu = os.cpu_count() or 2
    if requested is None or requested <= 0:
        return max(1, min(cpu, 8))
    return max(1, requested)


def map_jobs(fn, items: list, jobs: int) -> list[tuple]:
    """Run fn(item) in a pool. Returns list of (item, result|None, error|None)."""
    out: list[tuple] = []
    if jobs == 1 or len(items) <= 1:
        for item in items:
            try:
                out.append((item, fn(item), None))
            except Exception as e:  # noqa: BLE001 — report per figure
                out.append((item, None, e))
        return out
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        futs = {pool.submit(fn, item): item for item in items}
        for fut in as_completed(futs):
            item = futs[fut]
            try:
                out.append((item, fut.result(), None))
            except Exception as e:  # noqa: BLE001
                out.append((item, None, e))
    return out


def scratch_dir(prefix: str) -> tempfile.TemporaryDirectory:
    return tempfile.TemporaryDirectory(prefix=prefix)
