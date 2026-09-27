#!/usr/bin/env python3
"""Book shim: rasterize this book's figures into ai-preview/. Implementation: kit/tools."""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

ASSETS = Path(__file__).resolve().parent
KIT = ASSETS.parents[3] / "kit" / "tools" / "preview-figures.py"

if "--assets" not in sys.argv:
    sys.argv += ["--assets", str(ASSETS)]
sys.argv[0] = str(KIT)
runpy.run_path(str(KIT), run_name="__main__")
