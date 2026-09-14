#!/usr/bin/env python3
"""
sdf_to_pdbqt.py — batch conversion of an SDF library to individual PDBQT
files for docking.

Each output is named after the compound's `Catalog ID` SDF property
(e.g. Z136273548.pdbqt), with fallback to other ID-like fields, the
internal _Name, or a running index if no identifier is present.

Pipeline per molecule:
    SDF record → RDKit parse → AddHs → ETKDGv3 3D embed → MMFF94 minimize
                             → Meeko MoleculePreparation → PDBQT file

Usage
-----
    conda activate vs_prep
    python sdf_to_pdbqt.py library.sdf -o pdbqt_out -j 8

For very large libraries increase -j to your core count.

Author : Shahid Ali
License: MIT
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

from rdkit import Chem, RDLogger
from rdkit.Chem import AllChem
from meeko import MoleculePreparation, PDBQTWriterLegacy
from tqdm import tqdm

RDLogger.DisableLog("rdApp.*")


# ---------- per-molecule worker ---------------------------------------------

def prep_one(mol_block: str, name: str, out_dir: str) -> tuple[str, bool, str]:
    """Embed, minimize, and write one molecule as PDBQT."""
    try:
        mol = Chem.MolFromMolBlock(mol_block, removeHs=False)
        if mol is None:
            return name, False, "RDKit could not parse mol block"

        mol = Chem.AddHs(mol)

        # 3D embedding — deterministic first, random-coords fallback
        params = AllChem.ETKDGv3()
        params.randomSeed = 0xF00D
        if AllChem.EmbedMolecule(mol, params) != 0:
            params.useRandomCoords = True
            if AllChem.EmbedMolecule(mol, params) != 0:
                return name, False, "3D embedding failed"

        # MMFF94 minimize — UFF fallback for unusual chemistry
        try:
            if AllChem.MMFFOptimizeMolecule(mol, maxIters=500) != 0:
                AllChem.UFFOptimizeMolecule(mol, maxIters=500)
        except Exception:
            try:
                AllChem.UFFOptimizeMolecule(mol, maxIters=500)
            except Exception as e:
                return name, False, f"FF minimization failed: {e!r}"

        # Meeko PDBQT prep (Gasteiger charges, rotatable-bond detection)
        prep = MoleculePreparation()
        setups = prep.prepare(mol)
        if not setups:
            return name, False, "Meeko produced no molecule setups"

        pdbqt_str, ok, err = PDBQTWriterLegacy.write_string(setups[0])
        if not ok:
            return name, False, f"PDBQT writer error: {err}"

        out_path = Path(out_dir) / f"{name}.pdbqt"
        out_path.write_text(pdbqt_str)
        return name, True, str(out_path)

    except Exception as e:
        return name, False, repr(e)


# ---------- SDF iteration ----------------------------------------------------

_ID_FIELDS = ("Catalog ID", "catalog_id", "CatalogID", "ID", "Name",
              "ZINC_ID", "zinc_id")


def _safe_filename(s: str) -> str:
    bad = '/\\:*?"<>| \t\n\r'
    return "".join("_" if c in bad else c for c in s).strip("._") or "unnamed"


def iter_sdf_blocks(sdf_path: Path, id_field: str | None):
    """Yield (mol_block_text, sanitized_name) for every parseable record."""
    supplier = Chem.SDMolSupplier(str(sdf_path), removeHs=False, sanitize=True)
    for idx, mol in enumerate(supplier):
        if mol is None:
            logging.warning("Record #%d unreadable; skipped", idx + 1)
            continue

        name = None
        if id_field and mol.HasProp(id_field):
            name = mol.GetProp(id_field)
        else:
            for f in _ID_FIELDS:
                if mol.HasProp(f):
                    name = mol.GetProp(f)
                    break
        if not name:
            try:
                name = mol.GetProp("_Name")
            except KeyError:
                name = ""
        if not name.strip():
            name = f"mol_{idx + 1:07d}"

        yield Chem.MolToMolBlock(mol), _safe_filename(name)


# ---------- CLI --------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Convert a multi-compound SDF to individual PDBQT files.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("sdf", type=Path, help="Input multi-compound SDF file")
    ap.add_argument("-o", "--out-dir", type=Path, default=Path("pdbqt_out"),
                    help="Directory for PDBQT files")
    ap.add_argument("-j", "--jobs", type=int,
                    default=max(1, (os.cpu_count() or 4) - 1),
                    help="Parallel worker processes")
    ap.add_argument("--id-field", default="Catalog ID",
                    help="SDF property to use as filename")
    ap.add_argument("--log", type=Path, default=Path("conversion.log"),
                    help="Log file path")
    ap.add_argument("--overwrite", action="store_true",
                    help="Re-process molecules even if their PDBQT exists")
    args = ap.parse_args()

    if not args.sdf.exists():
        sys.exit(f"ERROR: input SDF not found: {args.sdf}")

    args.out_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        filename=args.log, filemode="w", level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    logging.info("Input:  %s", args.sdf.resolve())
    logging.info("Output: %s", args.out_dir.resolve())
    logging.info("Jobs:   %d", args.jobs)

    print(f"Reading {args.sdf} ...", flush=True)
    tasks = []
    for block, name in iter_sdf_blocks(args.sdf, args.id_field):
        if not args.overwrite and (args.out_dir / f"{name}.pdbqt").exists():
            logging.info("SKIP %s (already exists)", name)
            continue
        tasks.append((block, name))
    print(f"Queued {len(tasks)} molecules for conversion.", flush=True)

    success = failed = 0
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        futures = [pool.submit(prep_one, b, n, str(args.out_dir))
                   for b, n in tasks]
        for fut in tqdm(as_completed(futures), total=len(futures), desc="PDBQT"):
            name, ok, msg = fut.result()
            if ok:
                success += 1
                logging.info("OK   %s -> %s", name, msg)
            else:
                failed += 1
                logging.error("FAIL %s : %s", name, msg)

    print(f"\nFinished. success={success}  failed={failed}")
    print(f"  PDBQT dir : {args.out_dir.resolve()}")
    print(f"  Log file  : {args.log.resolve()}")
    if failed:
        print(f"  Check the log for the {failed} failures.")


if __name__ == "__main__":
    main()
