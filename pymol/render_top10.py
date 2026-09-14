#!/usr/bin/env python3
"""
render_top10.py — publication-quality PyMOL figures for the top-N docking hits.

For each pose PDBQT in top_hits/, produces a 300 DPI PNG showing:
  - Receptor as cartoon (light grey), transparent
  - Ligand as sticks (green carbons)
  - Interacting residues within 4.0 A as sticks (grey carbons)
  - H-bond distances as yellow dashes
  - Residue labels for the binding pocket
  - Clean white background, ray-traced

Run inside PyMOL — NOT as a regular python script. Use one of:

    pymol -cq render_top10.py -- \\
        --receptor receptor.pdbqt \\
        --pose-dir top_hits/ \\
        --out-dir figures/ \\
        --top-n 10

Or via the convenience wrapper: ./batch_render.sh

Requirements
------------
    pymol-open-source (from conda-forge) — installed by vs_run.yml.
    Standard system fonts (DejaVu Sans preferred).

Author : Shahid Ali
License: MIT
"""

import argparse
import os
import sys
from pathlib import Path

# PyMOL API — only available when run via `pymol` interpreter
try:
    from pymol import cmd, util
except ImportError:
    sys.exit(
        "This script must be run under PyMOL, e.g.\n"
        "    pymol -cq render_top10.py -- --receptor rec.pdbqt --pose-dir top_hits/\n"
        "Install PyMOL:  conda install -c conda-forge pymol-open-source"
    )


# ---------- rendering settings (edit for taste) ------------------------------

RENDER_WIDTH   = 2400          # px — 300 DPI × 8 inches
RENDER_HEIGHT  = 1800          # px — 300 DPI × 6 inches
RAY_TRACE      = 1             # 1 = raytrace (slower, publication quality)
CONTACT_CUTOFF = 4.0           # Angstroms — residues within this of ligand
HBOND_CUTOFF   = 3.5           # Angstroms — polar-contact distance ceiling
BG_COLOR       = "white"
CARTOON_COLOR  = "grey80"
LIGAND_CARBON  = "green"
POCKET_CARBON  = "grey60"
HBOND_COLOR    = "yellow"

# ---------------------------------------------------------------------------


def parse_args():
    ap = argparse.ArgumentParser(
        description="Render publication-quality interaction figures.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # PyMOL's -- passthrough gives us extra args after the script name
    argv = sys.argv[1:]
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    ap.add_argument("--receptor", required=True, type=Path,
                    help="Receptor structure (.pdbqt or .pdb)")
    ap.add_argument("--pose-dir", type=Path, default=Path("top_hits"),
                    help="Directory of ranked pose PDBQTs (rank01_*, rank02_*, ...)")
    ap.add_argument("--out-dir", type=Path, default=Path("figures"),
                    help="Where to save the PNG figures")
    ap.add_argument("--top-n", type=int, default=10,
                    help="Render this many top hits")
    ap.add_argument("--pattern", default="rank*.pdbqt",
                    help="Glob pattern for pose files")
    ap.add_argument("--save-session", action="store_true",
                    help="Also save a .pse PyMOL session per compound for later editing")
    return ap.parse_args(argv)


def setup_scene():
    """Global PyMOL settings that apply to every figure."""
    cmd.reinitialize()
    cmd.bg_color(BG_COLOR)
    cmd.set("ray_opaque_background", 0)   # transparent bg if needed
    cmd.set("antialias", 2)
    cmd.set("ray_trace_mode", 1)           # black outlines — publication style
    cmd.set("ray_trace_color", "black")
    cmd.set("cartoon_fancy_helices", 1)
    cmd.set("cartoon_smooth_loops", 1)
    cmd.set("cartoon_transparency", 0.15)
    cmd.set("stick_radius", 0.18)
    cmd.set("dash_radius", 0.06)
    cmd.set("dash_gap", 0.3)
    cmd.set("dash_length", 0.35)
    cmd.set("label_size", 20)
    cmd.set("label_font_id", 7)            # DejaVu Sans Bold
    cmd.set("label_color", "black")
    cmd.set("label_outline_color", "white")
    cmd.set("label_position", (0, 1.5, 3))


def render_one(receptor: Path, pose: Path, out_png: Path,
               save_session: bool = False) -> bool:
    """Render a single receptor+pose figure. Returns True on success."""
    try:
        cmd.reinitialize()
        setup_scene()

        # Load receptor and ligand
        cmd.load(str(receptor), "receptor")
        cmd.load(str(pose), "ligand")

        # Remove waters, keep only chain A if multi-chain (edit if inappropriate)
        cmd.remove("resn HOH+WAT")

        # Represent receptor as cartoon
        cmd.hide("everything", "receptor")
        cmd.show("cartoon", "receptor")
        cmd.color(CARTOON_COLOR, "receptor")

        # Ligand as sticks with green carbons
        cmd.hide("everything", "ligand")
        cmd.show("sticks", "ligand")
        util.cbag("ligand")   # colour by element, carbons green

        # Find residues within cutoff of ligand
        cmd.select("pocket",
                   f"byres (receptor within {CONTACT_CUTOFF} of ligand)")
        cmd.show("sticks", "pocket")
        cmd.hide("sticks", "pocket and (name C+N+O)")   # hide backbone sticks
        util.cbaw("pocket")   # colour by element, carbons grey/white
        cmd.color(POCKET_CARBON, "pocket and elem C")

        # Compute H-bonds / polar contacts between ligand and pocket
        cmd.distance("hbonds", "ligand", "pocket",
                     cutoff=HBOND_CUTOFF, mode=2)   # mode 2 = polar contacts
        cmd.color(HBOND_COLOR, "hbonds")
        cmd.hide("labels", "hbonds")    # hide distance numbers (uncomment to show)

        # Label interacting residues (one label per residue, at CA position)
        cmd.label("pocket and name CA",
                  '"%s%s" % (oneletter, resi)')

        # Orient view: zoom on the ligand + pocket with padding
        cmd.zoom("ligand", buffer=6.0)
        cmd.orient("ligand")

        # Render
        cmd.set("ray_shadows", 0)   # cleaner look for figures
        cmd.png(str(out_png), width=RENDER_WIDTH, height=RENDER_HEIGHT,
                dpi=300, ray=RAY_TRACE)

        if save_session:
            cmd.save(str(out_png.with_suffix(".pse")))

        return True
    except Exception as e:
        print(f"  ERROR rendering {pose.name}: {e}", file=sys.stderr)
        return False


def main():
    args = parse_args()

    if not args.receptor.exists():
        sys.exit(f"ERROR: receptor not found: {args.receptor}")
    if not args.pose_dir.is_dir():
        sys.exit(f"ERROR: pose directory not found: {args.pose_dir}")
    args.out_dir.mkdir(parents=True, exist_ok=True)

    poses = sorted(args.pose_dir.glob(args.pattern))[: args.top_n]
    if not poses:
        sys.exit(f"ERROR: no files matching {args.pattern} in {args.pose_dir}")

    print(f"Rendering {len(poses)} figures at {RENDER_WIDTH}x{RENDER_HEIGHT}, "
          f"ray-traced. This may take a few minutes per image.\n")

    ok = fail = 0
    for i, pose in enumerate(poses, 1):
        out_png = args.out_dir / (pose.stem + ".png")
        print(f"[{i:2d}/{len(poses)}] {pose.name} -> {out_png.name}")
        if render_one(args.receptor, pose, out_png, args.save_session):
            ok += 1
        else:
            fail += 1

    print(f"\nDone. success={ok}  failed={fail}")
    print(f"Figures in: {args.out_dir.resolve()}")


if __name__ == "__main__":
    main()
