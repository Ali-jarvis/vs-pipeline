# Troubleshooting

## Ligand preparation

### `RDKit could not parse mol block`

The SDF record has an invalid V2000/V3000 block. Common causes:

- Unusual atom types (metals, radicals)
- Missing atom coordinates (2D-only SDFs from some databases work fine
  because we generate 3D coords anyway, but truly malformed records fail)
- Non-standard sd-file syntax

Fix: re-export the SDF from its source using OpenBabel: `obabel input.sdf -O clean.sdf`.

### `3D embedding failed`

Rare, usually for highly strained macrocycles or over-constrained
compounds. The script tries deterministic ETKDGv3 first, then
random-coords initialization. If both fail, the compound is skipped and
logged.

Fix: for a handful of failed compounds, embed manually in the RDKit
Python API with `useSmallRingTorsions=True` and a large max iterations,
then save the result as PDBQT with Meeko separately.

### `Meeko produced no molecule setups`

Meeko can't parameterize the atom types — usually metals or unusual
valences. Skip these compounds or use OpenBabel as a fallback prep tool.

## Screening

### `submit_screen.sh` says "worker died immediately"

Check `screen.run.log`:

```bash
cat screen.run.log
```

Most common causes and fixes:

| Error message | Cause | Fix |
| --- | --- | --- |
| `vina: command not found` | Wrong conda env | `conda activate vs_run` before submit |
| `receptor '...' not found` | Wrong path in `vina_config.txt` | Use absolute path |
| `no PDBQT ligands in pdbqt_out` | Wrong `LIGAND_DIR` | Pass `LIGAND_DIR=/path/to/pdbqt_out` |
| Various Python errors | Env wasn't activated inside the detached job | Verify `conda.sh` search paths in `submit_screen.sh` |

### Every ligand fails with a Vina parsing error

Your PDBQT ligands were prepared with the wrong tool. Legacy
`prepare_ligand4.py` PDBQTs often confuse Vina 1.2. Re-prep with Meeko
via this repo's `sdf_to_pdbqt.py`.

### Many compounds in `no_result.txt` after parsing

Vina ran but found no valid pose. Almost always: **box is in the wrong
place, or too small**.

1. Open the receptor in PyMOL, mark the box center as a pseudoatom.
2. Confirm the pseudoatom is inside the actual binding pocket.
3. Increase box size (edit `vina_config.txt`) — try 30 × 30 × 30 as a
   test. If everything docks then, your box is too small.
4. Delete `vina_out/` and re-submit.

### Screen is much slower than the estimate

Check:

- **Is the box huge?** Blind-docking boxes (60+ Å) can be 10× slower
  than pocket boxes (25 Å).
- **Are you swapping?** `free -h` — if swap is being used, reduce
  `NJOBS`.
- **Is disk I/O saturated?** `iostat -xz 5` — if `%util` > 80, drop
  `NJOBS` or use `IONICE_CLASS=3`.
- **Are other users on the machine?** `top` — competing jobs steal CPU.

### `monitor_screen.sh` says "No status file"

Either the worker hasn't started yet (wait 5s) or it died before writing
the first status update. Check `screen.run.log`.

### Job survives SSH but dies when I close my laptop lid

Almost never happens with `nohup setsid`, but on some corporate VPNs
the SSH server terminates its session hard. Belt-and-suspenders fix:
run inside `tmux` too.

```bash
tmux new -s screen
./submit_screen.sh
# Ctrl-B then D to detach
```

Reattach later with `tmux attach -t screen`.

## Parsing

### `no '*_out.pdbqt' files in vina_out`

Nothing docked yet. Either the screen hasn't run, or Vina output paths
were configured differently. Check what's in `vina_out/`:

```bash
ls vina_out/ | head
```

If files are named differently (e.g. `_docked.pdbqt`), pass
`--suffix _docked.pdbqt` to the parser.

### CSV has fewer rows than my library

Some compounds failed to dock — check `top_hits/no_result.txt` for the
list. See "Many compounds in `no_result.txt`" above.

## Figure rendering

### `pymol: command not found`

Activate the screening env: `conda activate vs_run`. It includes
`pymol-open-source`.

### `X connection failed` or `no DISPLAY`

You're on a headless server. That's fine — the `-cq` flags in
`batch_render.sh` tell PyMOL to run without a display. If you edited
the wrapper and removed `-cq`, add them back.

### Ray tracing is very slow

Each 300 DPI ray-traced image takes ~30 seconds. For 10 figures that's
5 minutes, which is normal. For draft-quality quick renders, edit
`render_top10.py` and set `RAY_TRACE = 0`.

### Ligand appears inside the cartoon

The receptor cartoon is drawn with 15% transparency by default. If your
ligand is buried and hard to see, either:

1. Increase transparency: `cmd.set("cartoon_transparency", 0.6, ...)`
2. Cut a slice: `cmd.set("ray_trace_disabled_shaders", 4)` and add a
   clipping plane.

### Labels overlap or are unreadable

See the labels section in [`FIGURE_GUIDE.md`](FIGURE_GUIDE.md).

### Interacting residues are missing

The default 4.0 Å cutoff misses some hydrophobic/van der Waals contacts.
Increase it: edit `CONTACT_CUTOFF = 5.0` in `render_top10.py`.
