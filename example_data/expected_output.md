# Expected Output

This directory shows what a successful pipeline run produces. Use it
to verify your installation is working correctly.

## After `sdf_to_pdbqt.py`

For `example_data/sample_library.sdf`, you should get:

```
pdbqt_out/
├── Z136273548.pdbqt
└── Z254870174.pdbqt
```

Each ~2–3 KB text file, starting with a `REMARK` header and containing
`ATOM` lines with Gasteiger charges in the last column.

## After Vina screening (with a real receptor + config)

```
vina_out/
├── Z136273548_out.pdbqt      # docked poses
├── Z136273548.vina.log        # Vina's stdout for this compound
├── Z254870174_out.pdbqt
└── Z254870174.vina.log
```

Each `*_out.pdbqt` contains 1–9 poses (depending on `num_modes`), each
prefixed by `REMARK VINA RESULT`.

## After `parse_results.py`

```
screening_results.csv    # every compound, ranked
top_hits/
├── top50.csv            # top-N summary
├── rank01_Z*.pdbqt      # top pose files, renamed by rank
├── rank02_Z*.pdbqt
└── ...
```

Sample `screening_results.csv`:

```csv
rank,catalog_id,best_affinity_kcal_per_mol,n_modes,mode2_affinity,delta_mode1_mode2,rmsd_lb_best,rmsd_ub_best,output_pdbqt
1,Z254870174,-9.7,9,-9.2,0.5,0.0,0.0,/path/to/vina_out/Z254870174_out.pdbqt
2,Z136273548,-8.5,9,-8.1,0.4,0.0,0.0,/path/to/vina_out/Z136273548_out.pdbqt
```

## After `batch_render.sh`

```
figures/
├── rank01_Z254870174.png    # ~2 MB PNG at 300 DPI
├── rank02_Z136273548.png
└── ...
```

Each figure shows the receptor cartoon, ligand as green sticks,
interacting residues as grey sticks, and polar contacts as yellow
dashes.
