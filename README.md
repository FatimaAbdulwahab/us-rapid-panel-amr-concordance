# U.S. Rapid Panel Resistance Marker Concordance Benchmark

**Status:** Released v1.0.0, 2026-10-24 | **Maintainer:** Fatima Abdulwahab, ORCID [0009-0008-2298-8386](https://orcid.org/0009-0008-2298-8386) | **License:** code MIT, data and documents CC BY 4.0 | **DOI:** assigned when the Zenodo record is published

**In plain terms:** Rapid blood culture panels tell a laboratory within hours whether a resistance gene such as mecA, KPC or CTX-M is present. The growth-based susceptibility result arrives a day or two later. This project measures, gene by gene, how often the gene result agreed with the susceptibility result in 5,168 U.S. clinical isolates whose genomes and laboratory results are public at NCBI. Every disagreement is listed with its most likely cause. A free lookup page shows the numbers by gene, drug and organism: https://fatimaabdulwahab.github.io/us-rapid-panel-amr-concordance/

New here? Read [docs/START_HERE.md](docs/START_HERE.md) first. Unfamiliar terms are explained in [docs/GLOSSARY.md](docs/GLOSSARY.md).

## What this is

An open, versioned, isolate-level benchmark that pairs NCBI AMRFinderPlus gene calls with submitted antibiograms for U.S. human clinical isolates of *Staphylococcus aureus*, *Enterococcus faecalis*, *Enterococcus faecium* and the Enterobacterales. Genes are mapped to the targets that rapid blood culture panels report (mecA, mecC, vanA, vanB, KPC, NDM, OXA-48-like, VIM, IMP, CTX-M) through NCBI's own gene hierarchy. MICs and zone diameters are reinterpreted against CLSI M100 (35th ed., 2025) breakpoints. Positive predictive value, negative predictive value, sensitivity and specificity are reported with Wilson 95% intervals for every gene, drug and organism, for all specimens and for blood and sterile-site isolates alone.

AMRFinderPlus calls from assembled genomes stand in for the panel result. The benchmark answers "when the gene is there, does the phenotype follow?" It does not measure any commercial panel's analytical performance. See [docs/LIMITATIONS.md](docs/LIMITATIONS.md).

## Headline numbers (from `paper/stats.json`)

- **5,168 isolates** from 23 states and the District of Columbia (397 give no state), collected 2003 to 2024: *E. coli* 3,176, *K. pneumoniae* complex 790, *S. aureus* 550, *E. faecalis* 83, *E. faecium* 36, other Enterobacterales 533 (including 109 *Salmonella*). 731 are blood or other sterile-site isolates. The 2,099 District of Columbia isolates come from Walter Reed Army Institute of Research projects; that is the submitter's location, not necessarily the patient's.
- **mecA in *S. aureus*:** 215 of 220 mecA-positive isolates were oxacillin- or cefoxitin-resistant by MIC (PPV 97.7%); 329 of 330 mecA/mecC-negative isolates were not (NPV 99.7%). No mecC was found. For 3 mecA-positive isolates the submitting lab reported oxacillin resistant despite a low MIC; counting the lab's call instead gives PPV 99.1% (218 of 220). The main tables use the MIC.
- **vanA or vanB in enterococci:** PPV 89.7% (26 of 29), NPV 96.7% (87 of 90). No vanB was found. These estimates rest on few isolates.
- **Carbapenemases in Enterobacterales:** any panel carbapenemase predicted resistance to at least one carbapenem in 272 of 278 isolates (PPV 97.8%); its absence predicted no carbapenem resistance in 3,718 of 3,869 (NPV 96.1%). "Any carbapenem" includes ertapenem. **For meropenem alone, PPV is 87.6%** (241 of 275) and NPV 97.5%. KPC alone: PPV 98.0% for any carbapenem, 90.5% for meropenem.
- **CTX-M and ceftriaxone:** PPV 97.2% in *E. coli* and 99.1% in *K. pneumoniae* complex. A CTX-M-negative result was a much weaker signal in *K. pneumoniae* complex (NPV 37.3%) than in *E. coli* (NPV 94.2%).
- **970 discordant isolate-target pairs** (872 isolates), each with a likely cause, in `data/processed/discordance_cases.csv`.

## The four releases

| Output | File(s) | Zenodo record |
|---|---|---|
| Benchmark dataset | `data/processed/benchmark_isolates.tsv`, `benchmark_isolate_drug_long.tsv`, `concordance_table.csv` | assigned when the Zenodo record is published |
| Gene to panel target crosswalk | `reference/gene_panel_crosswalk.csv` | assigned when the Zenodo record is published |
| Discordance case collection | `data/processed/discordance_cases.csv` | assigned when the Zenodo record is published |
| Concordance lookup page | `docs/index.html`, served at https://fatimaabdulwahab.github.io/us-rapid-panel-amr-concordance/ | (part of the benchmark record) |

Each release ships with `docs/CODEBOOK.md` and the provenance log `data/raw/PROVENANCE.txt`.

## What is here

```
code/            numbered scripts in run order (01a, 01b, 01c fetch; 02 to 07 build)
reference/       breakpoints, gene-to-panel crosswalk, gene mechanism map
data/raw/        inputs as fetched (filtered to isolates with antibiograms), PROVENANCE.jsonl and PROVENANCE.txt
data/processed/  benchmark tables, concordance table, discordance cases, qa_report.txt
paper/           stats.json (every number the documents quote) and figures/
docs/            index.html (lookup page), START_HERE, GLOSSARY, CODEBOOK, LIMITATIONS,
                 VERIFY_CHECKLIST, NEXT_STEPS, TALK_TRACK, PUBLISH_GUIDE
tools/           publish gate, GitHub and Zenodo upload helpers
zenodo/          metadata for the three Zenodo records
```

## Run it

Python 3.10 or newer.

```
pip install -r requirements.txt
./run_all.sh                 # full rebuild with fresh NCBI downloads (20 to 40 minutes)
./run_all.sh --no-download   # rebuild from the committed raw files (about 1 minute)
```

`--no-download` reproduces the committed outputs exactly. A fresh download picks up isolates added to NCBI since 2026-10-24; that is how v1.1 is built.

## Sources

| Source | What it gives | Version | Terms | Accessed |
|---|---|---|---|---|
| NCBI BioSample antibiograms, via E-utilities ([docs](https://www.ncbi.nlm.nih.gov/books/NBK25499/)) | Submitted MIC, zone, method and S/I/R per drug | live database | NCBI policies: no restrictions on use | 2026-10-24 |
| NCBI Pathogen Detection AMR results ([FTP](https://ftp.ncbi.nlm.nih.gov/pathogen/Results/)) | AMRFinderPlus gene calls per isolate | analysis runs recorded in PROVENANCE.txt; AMRFinderPlus 4.2.5, 4.2.7 | same | 2026-10-24 |
| AMRFinderPlus Reference Gene Hierarchy and Catalog ([FTP](https://ftp.ncbi.nlm.nih.gov/pathogen/Antimicrobial_resistance/AMRFinderPlus/database/latest/)) | Gene families and drug classes for the crosswalk | database 2026-08-07.1 | same | 2026-10-24 |
| CLSI M100, 35th ed. (2025) | Breakpoints, cited in `reference/breakpoints.csv` | 2025 | values cited for reference | n/a |

## Limitations

See [docs/LIMITATIONS.md](docs/LIMITATIONS.md). The short version: genome calls are not panel calls; isolates are those labs chose to sequence and submit, so prevalence is not national prevalence; 40.2% of isolates come from one submitter project; enterococci are few.

## How to cite

Abdulwahab, F. *U.S. Rapid Panel Resistance Marker Concordance Benchmark*, v1.0. Zenodo. assigned when the Zenodo record is published. See `CITATION.cff`.

## AI assistance

Code, data wrangling and first drafts of documentation were prepared with the assistance of Claude (Anthropic). The author made the analytic decisions, checked the outputs against NCBI records using `docs/VERIFY_CHECKLIST.md`, and is responsible for the content.

## Maintainer

Fatima Abdulwahab, Independent Researcher, Dallas, Texas, USA. abdulwahabfatima43@gmail.com. Issues and corrections: https://github.com/FatimaAbdulwahab/us-rapid-panel-amr-concordance/issues
