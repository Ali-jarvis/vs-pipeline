#!/usr/bin/env python3
"""
parse_results.py — parse AutoDock Vina outputs, write a full ranked CSV,
and isolate the top-N compounds.

Vina writes one or more docking modes per output PDBQT. Each mode is
prefixed by:

    REMARK VINA RESULT:     -8.5      0.000      0.000

The three numbers are affinity (kcal/mol), RMSD lower bound, and RMSD
upper bound relative to the best mode. Mode 1 is always the best pose;
we rank compounds by mode-1 affinity.

Usage
-----
    python parse_results.py --in-dir vina_out --top-n 50

Outputs
-------
    screening_results.csv        every compound, ranked
    top_hits/top50.csv           top-N summary
    top_hits/rank01_Z*.pdbqt     top-N pose files renamed by rank
    top_hits/no_result.txt       any compounds with no VINA RESULT

Author : Shahid Ali
License: MIT
"""

import argparse
import csv
import re
import shutil
import sys
from pathlib import Path

VINA_LINE = re.compile(
    r"^REMARK VINA RESULT:\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)"
)


def parse_vina_output(pdbqt_path: Path):
    """Return list of (affinity, rmsd_lb, rmsd_ub) tuples, one per mode."""
    modes = []
    with pdbqt_path.open() as fh:
        for line in fh:
            m = VINA_LINE.match(line)
            if m:
                modes.append(tuple(float(x) for x in m.groups()))
    return modes


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--in-dir", type=Path, default=Path("vina_out"),
                    help="Directory containing Vina output PDBQT files")
    ap.add_argument("--suffix", default="_out.pdbqt",
                    help="Filename suffix Vina wrote (default: _out.pdbqt)")
    ap.add_argument("--csv", type=Path, default=Path("screening_results.csv"),
                    help="Output CSV path (full ranking, all compounds)")
    ap.add_argument("--top-n", type=int, default=50,
                    help="How many top compounds to isolate")
    ap.add_argument("--top-dir", type=Path, default=Path("top_hits"),
                    help="Directory for top-N pose files and summary CSV")
    args = ap.parse_args()

    if not args.in_dir.is_dir():
        sys.exit(f"ERROR: input directory not found: {args.in_dir}")

    rows = []
    empty = []
    files = sorted(args.in_dir.glob(f"*{args.suffix}"))
    if not files:
        sys.exit(f"ERROR: no '*{args.suffix}' files in {args.in_dir}")

    for fp in files:
        cid = fp.name[: -len(args.suffix)]
        modes = parse_vina_output(fp)
        if not modes:
            empty.append(cid)
            continue
        best_aff, best_lb, best_ub = modes[0]
        rows.append({
            "rank": None,  # filled after sort
            "catalog_id": cid,
            "best_affinity_kcal_per_mol": best_aff,
            "n_modes": len(modes),
            "mode2_affinity": modes[1][0] if len(modes) > 1 else "",
            "delta_mode1_mode2": round(modes[1][0] - best_aff, 3) if len(modes) > 1 else "",
            "rmsd_lb_best": best_lb,
            "rmsd_ub_best": best_ub,
            "output_pdbqt": str(fp.resolve()),
        })

    # Lower (more negative) affinity = stronger predicted binding
    rows.sort(key=lambda r: r["best_affinity_kcal_per_mol"])
    for i, r in enumerate(rows, 1):
        r["rank"] = i

    # ---- full ranking CSV ----
    fieldnames = list(rows[0].keys())
    with args.csv.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    # ---- top N: pose files + summary CSV ----
    args.top_dir.mkdir(parents=True, exist_ok=True)
    top = rows[: args.top_n]
    top_csv = args.top_dir / f"top{args.top_n}.csv"
    with top_csv.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(top)

    width = len(str(args.top_n))
    for r in top:
        src = Path(r["output_pdbqt"])
        dst = args.top_dir / f"rank{r['rank']:0{width}d}_{r['catalog_id']}.pdbqt"
        shutil.copy2(src, dst)

    print(f"Parsed   : {len(rows)} compounds")
    print(f"Empty    : {len(empty)}  (no VINA RESULT line — likely a docking failure)")
    print(f"Full CSV : {args.csv.resolve()}")
    print(f"Top-{args.top_n}   : {args.top_dir.resolve()}")
    print()
    n_preview = min(20, len(top))
    print(f"Top {n_preview} preview:")
    print(f"{'rank':>4}  {'catalog_id':<14}  affinity (kcal/mol)")
    for r in top[:n_preview]:
        print(f"{r['rank']:>4}  {r['catalog_id']:<14}  {r['best_affinity_kcal_per_mol']:>6.2f}")

    if empty:
        (args.top_dir / "no_result.txt").write_text("\n".join(empty) + "\n")


if __name__ == "__main__":
    main()
