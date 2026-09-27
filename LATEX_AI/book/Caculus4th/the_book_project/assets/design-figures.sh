#!/usr/bin/env bash
# Design every reconstructed figure whose source is a FreeCAD generator.
# Each generators/*.py writes its canonical output itself — an SVG under
# rendered/ named after the generator — so a new figure is just a new .py
# beside the old ones; nothing else has to change.
#
# Usage:
#   ./design-figures.sh                # regenerate every generator
#   ./design-figures.sh calcu5-fig1    # regenerate one figure
#
# Headless (no GL):  xvfb-run -a ./design-figures.sh
set -euo pipefail

figure_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
gen_dir="$figure_dir/generators"

fig="${1:-}"
if [[ -n "$fig" ]]; then
  sources=("$gen_dir/$fig.py")
else
  sources=("$gen_dir"/*.py)
fi

for src in "${sources[@]}"; do
  [[ -f "$src" ]] || { echo "no generator: $src" >&2; exit 1; }
  name="$(basename "$src" .py)"
  out="$figure_dir/rendered/$name.svg"
  freecadcmd "$src"
  [[ -f "$out" ]] || { echo "generator $name produced no $out" >&2; exit 1; }
done