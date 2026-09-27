#!/usr/bin/env python3
"""Book shim: crop a FIGURE into this book's scans/. Implementation: kit/tools."""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

ASSETS = Path(__file__).resolve().parent
BOOK = ASSETS.parents[1]  # Caculus4th/
KIT = ASSETS.parents[3] / "kit" / "tools" / "crop-scan.py"
DEFAULT_PDF = BOOK / "sources" / "Michael Spivak - Calculus, 4th Edition (2008).pdf"

if "--pdf" not in sys.argv:
    sys.argv += ["--pdf", str(DEFAULT_PDF)]
if "--scans" not in sys.argv:
    sys.argv += ["--scans", str(ASSETS / "scans")]
sys.argv[0] = str(KIT)
runpy.run_path(str(KIT), run_name="__main__")
