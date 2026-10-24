# Publish guide

*Plain-language note: how to put this project on GitHub, turn on the public lookup page, and get three permanent DOIs from Zenodo. Do this only after you have finished `docs/VERIFY_CHECKLIST.md`. Total time: about 30 to 45 minutes. You can also skip Parts 1 to 3 by giving Claude two upload tokens (see Part 0).*

## Copy-ready text

**Repository name:** `us-rapid-panel-amr-concordance`

**Repository description:** Open benchmark: how well rapid blood culture panel resistance genes (mecA, vanA/B, KPC, NDM, OXA-48-like, VIM, IMP, CTX-M) predict lab susceptibility in U.S. clinical isolates.

**Author:** Abdulwahab, Fatima. ORCID 0009-0008-2298-8386. Independent Researcher, Dallas, Texas, USA.

**Keywords:** antimicrobial resistance; rapid diagnostics; blood culture identification panel; AMRFinderPlus; genotype-phenotype concordance; NCBI Pathogen Detection; carbapenemase; mecA; vanA; CTX-M

**License:** data and documents CC BY 4.0; code MIT

**Release notes (v1.0.0):** First public release. Isolate-level benchmark, gene to panel target crosswalk, discordance case collection, codebook, provenance log and lookup page. Data accessed from NCBI on the date in `data/raw/PROVENANCE.txt`; breakpoints CLSI M100-Ed35 (2025).

## Part 0 (optional): let Claude upload for you

1. **GitHub token** (5 min). Go to https://github.com/settings/tokens/new . Note: "rapid panel upload". Expiration: 7 days. Tick **repo** and **workflow**. Click **Generate token**. Copy it.
2. **Zenodo token** (3 min). Go to https://zenodo.org/account/settings/applications/tokens/new/ . Name: "rapid panel upload". Tick **deposit:write** and **deposit:actions**. Click **Create**. Copy it.
3. Paste both into the chat with Claude. A token is a temporary password that lets Claude upload on your behalf. Claude will not save it in any file.
4. After publishing, delete both: https://github.com/settings/tokens and https://zenodo.org/account/settings/applications/ .

## Part 1: GitHub (15 min)

1. Go to https://github.com/new . Owner: FatimaAbdulwahab. Repository name: paste from above. Description: paste from above. Choose **Public**. Leave "Add a README" **unticked**. Click **Create repository**.
2. Download the project zip Claude gave you and unzip it.
3. On the new empty repository page, click **uploading an existing file**. Drag in everything inside the unzipped folder (not the folder itself). GitHub accepts up to 100 files per upload; if it complains, upload the folders `code`, `data`, `docs`, `paper`, `reference`, `tools`, `zenodo` in two or three batches. Commit message: `v1.0.0 release`. Click **Commit changes**.
   *If you are comfortable with a terminal instead:* in the project folder run `git init -b main`, `git add -A`, `git commit -m "v1.0.0 release"`, `git remote add origin https://github.com/FatimaAbdulwahab/us-rapid-panel-amr-concordance.git`, `git push -u origin main`.
4. The repository page should now show the README with the title "U.S. Rapid Panel Resistance Marker Concordance Benchmark".

## Part 2: Turn on the lookup page (3 min)

1. In the repository, click **Settings**, then **Pages** in the left menu.
2. Under "Build and deployment", Source: **Deploy from a branch**. Branch: **main**, folder: **/docs**. Click **Save**.
3. Wait two minutes, refresh. The page shows "Your site is live at https://fatimaabdulwahab.github.io/us-rapid-panel-amr-concordance/". Open it: you should see the lookup page with mecA selected.

## Part 3: Zenodo, three records (20 min)

**Record A, the benchmark (linked to GitHub, so future releases get DOIs automatically):**
1. Log in at https://zenodo.org with ORCID.
2. Click your name (top right), **GitHub**. Find `us-rapid-panel-amr-concordance` and flip its switch **On**. (If it is not listed, click **Sync now**.)
3. Back on GitHub, open the repository, click **Releases** (right side), **Draft a new release**. Tag: `v1.0.0` (choose "Create new tag"). Title: `v1.0.0`. Paste the release notes. Click **Publish release**.
4. Within about five minutes Zenodo shows a new record with a DOI under Zenodo, **Uploads**. Open it, click **Edit**, and paste the description and keywords from `zenodo/benchmark.json` (the `description` text). Set license to CC BY 4.0. Click **Publish**.

**Record B, the crosswalk, and Record C, the discordance collection (manual uploads):**
1. Click **New upload** at https://zenodo.org/uploads/new .
2. Drag in the files listed in `zenodo/crosswalk.files.txt` (for B) or `zenodo/discordance.files.txt` (for C).
3. Resource type: **Dataset**. Title, description and keywords: copy from `zenodo/crosswalk.json` or `zenodo/discordance.json`. Creator: Abdulwahab, Fatima, ORCID 0009-0008-2298-8386, affiliation Independent Researcher, Dallas, Texas, USA. License: **Creative Commons Attribution 4.0**. Version: 1.0.0.
4. Under "Related works" add the GitHub repository URL, relation **Is supplemented by**, and the Record A DOI, relation **Is part of**.
5. Click **Publish**. Copy the DOI.

## Part 4: The same day (10 min)

1. Send the three DOIs to Claude. Claude will put them in `README.md`, `CITATION.cff`, `LICENSE-DATA.md` and the lookup page footer, and give you the updated files to upload.
2. Add three rows to `docs/evidence_log.csv` (one per DOI): date, artifact, "dataset", "Zenodo + GitHub", the DOI, "live". Save a PDF of each Zenodo record page (browser **Print**, **Save as PDF**).
3. Optional: add the DOIs to your ORCID record (https://orcid.org/my-orcid , **Works**, **Add**, **Search & link**, **DataCite**).
