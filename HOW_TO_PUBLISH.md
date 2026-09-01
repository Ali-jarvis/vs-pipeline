# How to publish this to your GitHub

Two ways — pick whichever you prefer.

## Option A — with the GitHub website (easiest)

1. Go to https://github.com/new
2. Repository name: `vs-pipeline` (or anything you like)
3. Description: "Structure-based virtual screening pipeline: SDF → PDBQT → Vina → ranked CSV → publication figures"
4. Choose Public (if you want it citable and open-source) or Private
5. **Don't** initialize with README, .gitignore, or license — this repo already has them
6. Click "Create repository"
7. On the empty repo page, click "uploading an existing file"
8. Drag the whole `vs-pipeline/` folder in
9. Commit message: `Initial commit: SBVS pipeline v1.0`
10. Click "Commit changes"

## Option B — from the command line (recommended for future updates)

On your server or laptop where you have this folder:

```bash
cd /path/to/vs-pipeline

# Initialize git
git init
git add .
git commit -m "Initial commit: SBVS pipeline v1.0"

# Create the empty repo on GitHub first (see step 1-6 in Option A)
# Then link it and push:
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/vs-pipeline.git
git push -u origin main
```

If you get a password prompt and it rejects your password: GitHub no
longer accepts passwords for git operations. Use a personal access token
instead: https://github.com/settings/tokens (generate a token with `repo`
scope, use it in place of your password).

## After it's on GitHub

1. **Add repository topics** for discoverability. On your repo page,
   click the gear icon next to "About" and add topics like:
   `virtual-screening`, `autodock-vina`, `drug-discovery`,
   `cheminformatics`, `computational-biology`, `structure-based-drug-design`

2. **Verify the Citation button appears.** GitHub auto-parses `CITATION.cff`
   and shows "Cite this repository" on the right sidebar. Edit
   `CITATION.cff` to add your real ORCID and confirm your name/affiliation.

3. **Enable Discussions** (Settings → Features → Discussions). Lets
   people ask questions without opening issues.

4. **Add a link back to it in your ORCID / Google Scholar / LinkedIn**.

## Updating later

```bash
cd /path/to/vs-pipeline
# make your changes
git add .
git commit -m "Add: consensus scoring module"
git push
```

## Getting a DOI (for citing in papers)

If you want the pipeline to have a proper DOI for methods sections:

1. Link your GitHub account to Zenodo: https://zenodo.org/account/settings/github/
2. Enable the repository in Zenodo
3. Cut a release on GitHub (Releases → Draft a new release → tag `v1.0.0`)
4. Zenodo automatically archives it and mints a DOI
5. Add the DOI badge to your README

This is the standard way of citing software in publications and takes
about 5 minutes total.
