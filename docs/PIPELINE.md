# Pipeline Protocol

Detailed documentation for each stage. If you just want to run it,
see [QUICKSTART.md](QUICKSTART.md).

## Stage 1 — Ligand preparation

**Input:** multi-compound `.sdf` file (Enamine REAL, ZINC, ChEMBL, in-house
library, etc.)
**Output:** one `.pdbqt` file per compound, named by catalog ID.

### What happens per compound

1. **Parse SDF record** with RDKit (`Chem.MolFromMolBlock`).
2. **Add explicit hydrogens** (`Chem.AddHs`).
3. **Generate 3D coordinates** with ETKDGv3, deterministic seed. Falls
   back to random-coords initialization if the primary method fails
   (rare, but happens on strained macrocycles).
4. **Energy-minimize** with MMFF94. UFF fallback for compounds MMFF can't
   parameterize.
5. **Prepare PDBQT** with Meeko's `MoleculePreparation` — assigns
   Gasteiger partial charges, detects rotatable bonds, merges non-polar
   hydrogens.

### Why Meeko, not `prepare_ligand4.py`?

Meeko is the current recommended tool from the AutoDock developers.
The legacy MGLTools script has known bugs with modern chemistry (metals,
unusual valences, macrocycles), depends on Python 2, and produces
subtly different rotatable-bond assignments than Vina expects.

### Command

```bash
python scripts/sdf_to_pdbqt.py library.sdf -o pdbqt_out -j 8
```

`-j` = parallel workers. Set to your CPU count minus a few.

### Naming

The script looks for these SDF properties in order, uses the first one
found: `Catalog ID`, `catalog_id`, `CatalogID`, `ID`, `Name`, `ZINC_ID`,
`zinc_id`. Falls back to the SDF `_Name` field, then to `mol_0000001`
etc. if nothing else is available.

### Recommended pre-processing

If your library isn't already filtered:

1. **PAINS filter** — RDKit's `rdkit.Chem.rdfiltercatalog.FilterCatalog`
   with PAINS_A/B/C catalogs.
2. **Aggregator filter** — Advisor (SwissDrugDesign) or the SI of
   Irwin & Shoichet.
3. **Lipinski/Veber rules** — if you want oral drugs.
4. **Tautomer/protonation enumeration at pH 7.4** — Dimorphite-DL or
   `obabel -p 7.4`. Docking at only one tautomer misses real hits.

These aren't in this pipeline yet — happy to add them as a separate
prep script.

## Stage 2 — Receptor preparation

Not automated here; needs case-by-case judgment.

1. Start from a high-resolution X-ray or a validated structural model.
2. Remove waters (unless a specific water is crystallographically
   confirmed to mediate binding — then keep it and reduce the box).
3. Remove co-crystallized ligands and buffer components.
4. Fix missing side chains (SwissModel, Modeller, ChimeraX).
5. Assign hydrogens and protonation states at pH 7.4 (Reduce, PDB2PQR).
6. Convert to PDBQT:

   ```bash
   mk_prepare_receptor.py -i receptor.pdb -o receptor.pdbqt -p
   ```

## Stage 3 — Docking box definition

The single biggest determinant of whether your results mean anything.

**If you have a co-crystallized ligand** (recommended): use its centroid
as the box center, and set box edges ~6 Å larger than the ligand's
extent in each direction.

```python
# In PyMOL
load holo_complex.pdb
select lig, resn LIG   # replace LIG with the ligand's residue name
get_extent lig
# Prints  minX minY minZ  and  maxX maxY maxZ
# center = midpoint; size = (max - min) + 12
```

**If you don't have a bound ligand**: use a cavity detector.

- **fpocket** — command-line, fast, gives pocket ranks and centroids
- **DoGSiteScorer** — web service, more detailed druggability metrics
- **CASTp** — web service, geometric analysis

**Always verify the box visually in PyMOL** before launching a screen:

```python
load receptor.pdb
pseudoatom box_center, pos=[x, y, z]
show spheres, box_center
```

## Stage 4 — Screening execution

See [QUICKSTART.md](QUICKSTART.md) section 5–6.

### CPU tuning

Total CPU usage = `NJOBS × CPU_PER_JOB`. Empirically for Vina:

- `NJOBS=nproc, CPU_PER_JOB=1` — fastest for large libraries
- `NJOBS=nproc/4, CPU_PER_JOB=4` — better for very complex ligands where
  Vina's internal threading helps

Default: 50 parallel Vina calls at 1 CPU each. Override with `NJOBS=N`.

### Resume behavior

`submit_screen.sh` writes a status file every 5 completed ligands. If
the job is killed or the server reboots, re-running `submit_screen.sh`
picks up where it left off — every ligand with a valid
`REMARK VINA RESULT` line in its output is skipped.

### Failure detection

The worker logs one line per compound to `screen.detail.log`:

```
14:32:11  OK   Z136273548
14:32:14  OK   Z254870174
14:32:16  FAIL Z999999999
14:32:18  SKIP Z123456789    (already had output)
```

Failures usually mean:
- Ligand couldn't be posed anywhere in the box (box too small or wrong location)
- PDBQT syntax problem (rare — check `vina_out/Z*.vina.log`)
- Vina timeout on a very flexible ligand (increase `--exhaustiveness`
  reduction or split flexible ligands out for slower runs)

## Stage 5 — Result parsing and ranking

```bash
python scripts/parse_results.py --in-dir vina_out --top-n 50
```

Extracts the best (mode 1) binding affinity from every `*_out.pdbqt`
file. Vina writes the affinity as:

```
REMARK VINA RESULT:     -8.5      0.000      0.000
```

The first number is affinity in kcal/mol. Lower (more negative) =
stronger predicted binding.

### CSV columns

| Column | Meaning |
| --- | --- |
| `rank` | 1 = best affinity |
| `catalog_id` | Compound ID from the SDF |
| `best_affinity_kcal_per_mol` | Mode 1 affinity (the rank key) |
| `n_modes` | How many poses Vina returned (up to `num_modes`) |
| `mode2_affinity` | Second-best pose affinity — for gap analysis |
| `delta_mode1_mode2` | Gap between best and second-best; larger = more decisive |
| `rmsd_lb_best` / `rmsd_ub_best` | RMSD of best pose relative to itself (should be 0.0) |
| `output_pdbqt` | Absolute path to the Vina output file |

## Stage 6 — Post-screening validation

**Every top hit should be:**

1. **Visually inspected** in PyMOL. Does the pose look chemically
   reasonable? Any clashes? Is it floating in solvent? Is the polar
   face pointing at the polar pocket?
2. **Re-docked at higher exhaustiveness** (`--exhaustiveness 32`) to
   confirm the affinity is stable.
3. **Consensus scored** with an orthogonal method: smina + Vinardo,
   GNINA (deep learning), or MM-GBSA if you have Amber.
4. **Chemotype-clustered** with the top few hundred hits (Tanimoto ≥ 0.4)
   so your top 50 isn't just one scaffold repeated.

## Stage 7 — Publication figures

See [FIGURE_GUIDE.md](FIGURE_GUIDE.md) for customizing the PyMOL output.

Quick version:

```bash
cd pymol
./batch_render.sh                # top 10 at 300 DPI
```

Each figure shows receptor cartoon, ligand as sticks, interacting
residues within 4 Å, and polar contacts as dashes. Residues are
labeled with one-letter code + number.

## References

- **AutoDock Vina 1.2**: Eberhardt et al. (2021) *J Chem Inf Model* 61(8):3891.
- **Meeko**: forlilab.github.io/Meeko
- **RDKit**: rdkit.org
- **fpocket**: Schmidtke et al. (2010) *Bioinformatics* 26:3073.
- **Vinardo**: Quiroga & Villarreal (2016) *PLoS One* 11(5):e0155183.
- **GNINA**: McNutt et al. (2021) *J Cheminform* 13:43.
