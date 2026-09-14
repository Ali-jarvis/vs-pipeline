# Quick Start — 5-minute walkthrough

This walks through the full pipeline with a small example. Total time
on a laptop: about 15 minutes (dominated by conda env creation).

## 1. Clone and set up environments

```bash
git clone https://github.com/Ali-jarvis/vs-pipeline.git
cd vs-pipeline

conda env create -f environments/vs_prep.yml    # ~5 min
conda env create -f environments/vs_run.yml     # ~5 min
```

`mamba env create -f ...` if conda's solver is slow.

## 2. Try it on the example data

The `example_data/sample_library.sdf` contains 2 compounds from Enamine
REAL. Convert them to PDBQT:

```bash
conda activate vs_prep
mkdir -p test_run && cd test_run
python ../scripts/sdf_to_pdbqt.py ../example_data/sample_library.sdf \
    -o pdbqt_out -j 4

ls pdbqt_out/
# Z136273548.pdbqt  Z254870174.pdbqt  Z423051088.pdbqt
```

Copy in a real receptor and edit the config, or skip to step 5 with
your own data.

## 3. Prepare your receptor

```bash
# Clean your PDB first: remove waters, ions, alternate conformations,
# and any co-crystallized ligands. Add hydrogens. Then:
mk_prepare_receptor.py -i receptor.pdb -o receptor.pdbqt -p
```

## 4. Configure the docking box

Edit `scripts/vina_config.txt`:

```
receptor = /full/path/to/receptor.pdbqt
center_x = 12.345          # coordinates of your binding site
center_y = 45.678
center_z = 78.901
size_x   = 25              # 22–25 A for a defined pocket
size_y   = 25
size_z   = 25
```

Get the center from your co-crystallized ligand centroid (in PyMOL:
`get_extent selection`) or from fpocket / DoGSiteScorer output.

**Verify the box in PyMOL before running:**

```python
# In PyMOL command line
load receptor.pdb
pseudoatom center, pos=[12.345, 45.678, 78.901]
show spheres, center
```

## 5. Launch the screen

```bash
conda activate vs_run
cd scripts/
chmod +x *.sh

./submit_screen.sh --check      # preview CPU plan
./submit_screen.sh              # go
```

For the 3-compound example this finishes in seconds. For a real 100k
library, disconnect after this — the job survives your logout.

## 6. Monitor progress

```bash
./monitor_screen.sh             # snapshot
./monitor_screen.sh -w          # live, refreshes every 30s
```

You'll see:

```
================ Virtual Screening Status ================
  Total ligands  : 100000
  Done           : 12488
  Failed         : 3
  Remaining      : 87509

  Progress       : [#####-----------------------------------] 12.5%
  Rate           : 42.3 ligands/min
  ETA finish     : 2026-05-15 14:23:11
===========================================================
```

## 7. Rank and extract top 50

```bash
python parse_results.py --in-dir vina_out --top-n 50
```

Produces:

- `screening_results.csv` — every compound ranked
- `top_hits/top50.csv` — top-50 summary
- `top_hits/rank01_Z*.pdbqt` through `rank50_Z*.pdbqt` — pose files

Console preview shows the top 20 with affinities.

## 8. Render publication figures

```bash
conda activate vs_run                     # PyMOL lives here
cd ../pymol
./batch_render.sh                         # top 10 by default
```

Produces PNG figures in `figures/`:

- `rank01_Z136273548.png` — the #1 hit
- `rank02_Z254870174.png`
- ... etc

Each figure: receptor cartoon, ligand sticks, interacting residues,
H-bonds, at 300 DPI, ready for a manuscript.

## What's next

- [`PIPELINE.md`](PIPELINE.md) — detailed protocol, tuning, and
  parameter recommendations
- [`FIGURE_GUIDE.md`](FIGURE_GUIDE.md) — customizing the PyMOL figures
- [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md) — common problems and fixes
