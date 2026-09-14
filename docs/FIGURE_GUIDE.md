# Figure Customization Guide

The default `render_top10.py` produces good publication-quality figures,
but you'll often want to tweak colors, orientations, or add specific
labels. This guide covers the common customizations.

## Default figure style

Each figure includes:

- **Receptor**: light-grey cartoon, slightly transparent (85% opacity)
- **Ligand**: sticks, green carbons, colored heteroatoms
- **Interacting residues** (within 4.0 Å of ligand): sticks, grey carbons
- **H-bonds / polar contacts** (within 3.5 Å): yellow dashes
- **Residue labels**: one-letter code + residue number, at Cα
- **Background**: white, black outlines (ray-traced)
- **Resolution**: 2400 × 1800 px = 8 × 6 inches at 300 DPI

## Editing the defaults

Open `pymol/render_top10.py` and edit the constants near the top:

```python
RENDER_WIDTH   = 2400
RENDER_HEIGHT  = 1800
RAY_TRACE      = 1
CONTACT_CUTOFF = 4.0
HBOND_CUTOFF   = 3.5
BG_COLOR       = "white"
CARTOON_COLOR  = "grey80"
LIGAND_CARBON  = "green"
POCKET_CARBON  = "grey60"
HBOND_COLOR    = "yellow"
```

Change any of these and re-run `./batch_render.sh`.

## Common tweaks

### Different color scheme (colorblind-friendly)

Edit the constants:

```python
LIGAND_CARBON  = "0x0072B2"      # blue
POCKET_CARBON  = "0xE69F00"      # orange
HBOND_COLOR    = "0xCC79A7"      # magenta
```

These are Wong's colorblind-friendly palette (Nature Methods, 2011).

### Journal-specific figure dimensions

Most journals want figures at a fixed column width. Set the render size
to match:

```python
# Nature single column: 89 mm wide (3.5 in) at 300 DPI
RENDER_WIDTH  = 1050
RENDER_HEIGHT = 800

# Nature double column: 183 mm wide (7.2 in)
RENDER_WIDTH  = 2160
RENDER_HEIGHT = 1620
```

### Larger contact zone

If your compound spans a large pocket, 4 Å might miss important residues:

```python
CONTACT_CUTOFF = 5.0             # more residues shown
```

### Show H-bond distances as numbers

By default the distances are hidden for a cleaner look. To show them:

```python
# In render_one(), remove or comment out this line:
cmd.hide("labels", "hbonds")
```

### Only show hydrophobic pocket, no cartoon

```python
# In render_one(), replace the cartoon block with:
cmd.hide("everything", "receptor")
cmd.show("surface", "pocket")
cmd.set("transparency", 0.5, "pocket")
```

### Save an editable PyMOL session per figure

```bash
./batch_render.sh --save-session
```

Wait — the wrapper doesn't take that flag directly. Use the underlying
script:

```bash
pymol -cq pymol/render_top10.py -- \
    --receptor scripts/receptor.pdbqt \
    --pose-dir scripts/top_hits \
    --out-dir figures \
    --top-n 10 \
    --save-session
```

You'll get `figures/rank01_Z*.pse` files that open in PyMOL GUI for
manual tweaking (adjusting orientation, adding annotations, moving
labels).

## Manual figure polishing in PyMOL GUI

For a hero figure that goes in the main text of your paper, batch
rendering is a starting point — you'll want to hand-tune orientation
and residue selection.

```bash
pymol figures/rank01_Z136273548.pse
```

Then in the PyMOL GUI:

```python
# Rotate to a better view
rotate y, 30
rotate x, -15

# Hide a residue that's cluttering the view
hide sticks, resi 145 and pocket

# Manually label a specific residue with three-letter code
label pocket and resi 178 and name CA, "%s%s" % (resn, resi)

# Re-render at higher quality
png my_final_figure.png, width=3000, height=2400, dpi=600, ray=1
```

Then save the session again: `save figures/rank01_final.pse`.

## Multi-panel composite figures

For "Figure 3: interaction profiles of top hits", you'll typically want
a 3×3 grid of 9 compounds. Two options:

1. **In Inkscape / Illustrator**: import the 10 PNGs, arrange manually.
   Best for asymmetric layouts.

2. **In Python with matplotlib**: script the grid.

   ```python
   import matplotlib.pyplot as plt
   from pathlib import Path

   figs = sorted(Path("figures").glob("rank*.png"))[:9]
   fig, axes = plt.subplots(3, 3, figsize=(15, 12))
   for ax, f in zip(axes.flatten(), figs):
       ax.imshow(plt.imread(f))
       ax.set_title(f.stem, fontsize=10)
       ax.axis("off")
   plt.tight_layout()
   plt.savefig("figures/composite.png", dpi=300, bbox_inches="tight")
   ```

3. **In PyMOL with `set grid_mode, 1`**: load all 9 into one session
   and PyMOL tiles them. Less flexible but keeps everything vectorized.

## Common problems

### The ligand is in a weird orientation

PyMOL's `cmd.orient()` picks the principal axes of the ligand. For
odd-shaped ligands this can look strange. Manually orient in the GUI
and save as a session:

```python
# In GUI
orient ligand
rotate y, 45   # tweak until it looks right
get_view       # copies view to clipboard
```

Then paste the view matrix into `render_one()` before the `cmd.png()`
call:

```python
cmd.set_view("""\
    -0.798,  0.412,  0.439,  ...
""")
```

### Labels overlap the ligand

Increase label position offset in `setup_scene()`:

```python
cmd.set("label_position", (0, 2.5, 5))    # farther out
```

### Ray tracing takes too long

For quick draft figures, disable it:

```python
RAY_TRACE = 0
```

Rendering drops from ~30s per figure to ~1s. Re-enable for final versions.

### Fonts look wrong

The default `label_font_id = 7` is DejaVu Sans Bold, present on all
conda-forge PyMOL builds. Alternatives:

- `13` — Helvetica
- `9` — Times New Roman
- `16` — Arial

Full list in PyMOL: `help set_font_id`.
