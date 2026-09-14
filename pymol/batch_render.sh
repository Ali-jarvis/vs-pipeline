#!/bin/bash
# =====================================================================
# batch_render.sh — convenience wrapper for render_top10.py.
# Renders the top-10 interaction figures using default paths.
#
# Assumes you're running from the repo root with:
#   - receptor at scripts/receptor.pdbqt (or override via RECEPTOR=)
#   - top hits in scripts/top_hits/
#   - figures written to figures/
#
# Usage:
#   ./batch_render.sh                           # defaults: top 10
#   TOP_N=20 ./batch_render.sh                  # render top 20
#   RECEPTOR=my_target.pdb ./batch_render.sh    # different receptor
# =====================================================================

set -euo pipefail

# Resolve script directory so paths work no matter where you invoke from
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

RECEPTOR="${RECEPTOR:-$REPO_ROOT/scripts/receptor.pdbqt}"
POSE_DIR="${POSE_DIR:-$REPO_ROOT/scripts/top_hits}"
OUT_DIR="${OUT_DIR:-$REPO_ROOT/figures}"
TOP_N="${TOP_N:-10}"

# Sanity checks
[[ -f "$RECEPTOR" ]] || { echo "ERROR: receptor not found: $RECEPTOR"; exit 1; }
[[ -d "$POSE_DIR" ]] || { echo "ERROR: pose dir not found: $POSE_DIR"; exit 1; }

command -v pymol >/dev/null || {
    echo "ERROR: pymol not on PATH. Activate vs_run env first:"
    echo "  conda activate vs_run"
    exit 1
}

mkdir -p "$OUT_DIR"

echo "Rendering top-$TOP_N interaction figures"
echo "  Receptor : $RECEPTOR"
echo "  Poses    : $POSE_DIR"
echo "  Output   : $OUT_DIR"
echo ""

# -cq = no GUI, quiet startup. -- separates PyMOL args from script args.
pymol -cq "$SCRIPT_DIR/render_top10.py" -- \
    --receptor "$RECEPTOR" \
    --pose-dir "$POSE_DIR" \
    --out-dir  "$OUT_DIR" \
    --top-n    "$TOP_N"

echo ""
echo "Done. Preview a figure with:"
echo "  eog $OUT_DIR/rank01_*.png    # Linux"
echo "  open $OUT_DIR/rank01_*.png   # macOS"
