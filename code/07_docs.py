#!/usr/bin/env python3
"""
07_docs.py - Write every document that quotes a number, straight from paper/stats.json.

PLAIN-LANGUAGE NOTE: You never type a number into the README or talk track by
hand. This script reads the numbers the analysis wrote and fills them in, so the
text and the data cannot disagree. Re-run it after any rebuild.
Writes: README.md, docs/TALK_TRACK.md, docs/VERIFY_CHECKLIST.md, data/raw/PROVENANCE.txt
"""
import datetime, json, os, sys
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = json.load(open(os.path.join(ROOT, "paper", "stats.json")))
PROV = [json.loads(l) for l in open(os.path.join(ROOT, "data", "raw", "PROVENANCE.jsonl"))]
AUTH = json.load(open(os.path.join(ROOT, "AUTHORS.json")))["authors"][0]
REPO = "https://github.com/FatimaAbdulwahab/us-rapid-panel-amr-concordance"
PAGES = "https://fatimaabdulwahab.github.io/us-rapid-panel-amr-concordance/"
ENT = "Enterobacterales (excluding Salmonella)"
CARB = "any panel carbapenemase (KPC, NDM, OXA-48-like, VIM, IMP)"
ACCESS = max(p["access_date"] for p in PROV)


def H(t, d, o):
    return S["headline"][f"{t} | {d} | {o}"]


def pc(x):
    return f"{100 * x:.1f}%"


def frac_ppv(h):
    return f"{h['gene_pos_R']:,} of {h['gene_pos_R'] + h['gene_pos_notR']:,}"


def frac_npv(h):
    return f"{h['gene_neg_notR']:,} of {h['gene_neg_notR'] + h['gene_neg_R']:,}"


mec = H("mecA", "oxacillin or cefoxitin", "Staphylococcus aureus")
van = H("vanA or vanB", "vancomycin", "Enterococcus faecalis + faecium")
kpc = H("KPC", "any carbapenem", ENT)
kpc_mero = H("KPC", "meropenem", ENT)
carb_mero = H(CARB, "meropenem", ENT)
alt = S["mecA_alt_trust_submitter_oxacillin_R"]
carb = H(CARB, "any carbapenem", ENT)
ctx_ec = H("CTX-M", "ceftriaxone", "Escherichia coli")
ctx_kp = H("CTX-M", "ceftriaxone", "Klebsiella pneumoniae complex")
nb = S["n_benchmark_isolates"]
org = S["n_by_organism"]
FINAL = "--final" in sys.argv
_dp = os.path.join(ROOT, "zenodo", "dois.json")
DOIS = json.load(open(_dp)) if os.path.exists(_dp) else {}
def doi_link(k):
    d = DOIS.get(k)
    if d:
        return f"[{d}](https://doi.org/{d})"
    return "assigned when the Zenodo record is published" if FINAL else "[DOI PENDING]"
draft = (f"Released v1.0.0, {datetime.date.today().isoformat()}" if FINAL
         else "DRAFT v1.0 (not yet verified by the author)")

readme = f"""# U.S. Rapid Panel Resistance Marker Concordance Benchmark

**Status:** {draft} | **Maintainer:** {AUTH['name']}, ORCID [{AUTH['orcid']}](https://orcid.org/{AUTH['orcid']}) | **License:** code MIT, data and documents CC BY 4.0 | **DOI:** {doi_link('benchmark')}

**In plain terms:** Rapid blood culture panels tell a laboratory within hours whether a resistance gene such as mecA, KPC or CTX-M is present. The growth-based susceptibility result arrives a day or two later. This project measures, gene by gene, how often the gene result agreed with the susceptibility result in {nb:,} U.S. clinical isolates whose genomes and laboratory results are public at NCBI. Every disagreement is listed with its most likely cause. A free lookup page shows the numbers by gene, drug and organism: {PAGES}

New here? Read [docs/START_HERE.md](docs/START_HERE.md) first. Unfamiliar terms are explained in [docs/GLOSSARY.md](docs/GLOSSARY.md).

## What this is

An open, versioned, isolate-level benchmark that pairs NCBI AMRFinderPlus gene calls with submitted antibiograms for U.S. human clinical isolates of *Staphylococcus aureus*, *Enterococcus faecalis*, *Enterococcus faecium* and the Enterobacterales. Genes are mapped to the targets that rapid blood culture panels report (mecA, mecC, vanA, vanB, KPC, NDM, OXA-48-like, VIM, IMP, CTX-M) through NCBI's own gene hierarchy. MICs and zone diameters are reinterpreted against CLSI M100 (35th ed., 2025) breakpoints. Positive predictive value, negative predictive value, sensitivity and specificity are reported with Wilson 95% intervals for every gene, drug and organism, for all specimens and for blood and sterile-site isolates alone.

AMRFinderPlus calls from assembled genomes stand in for the panel result. The benchmark answers "when the gene is there, does the phenotype follow?" It does not measure any commercial panel's analytical performance. See [docs/LIMITATIONS.md](docs/LIMITATIONS.md).

## Headline numbers (from `paper/stats.json`{'' if FINAL else '; do not cite until released'})

- **{nb:,} isolates** from {S['n_states']} states and the District of Columbia ({S['n_no_state']:,} give no state), collected {S['collection_year_min']} to {S['collection_year_max']}: *E. coli* {org['Escherichia coli']:,}, *K. pneumoniae* complex {org['Klebsiella pneumoniae complex']:,}, *S. aureus* {org['Staphylococcus aureus']:,}, *E. faecalis* {org['Enterococcus faecalis']:,}, *E. faecium* {org['Enterococcus faecium']:,}, other Enterobacterales {nb - org['Escherichia coli'] - org['Klebsiella pneumoniae complex'] - org['Staphylococcus aureus'] - org['Enterococcus faecalis'] - org['Enterococcus faecium']:,} (including {org['Salmonella enterica']:,} *Salmonella*). {S['n_blood_or_sterile']:,} are blood or other sterile-site isolates. The {S['n_dc']:,} District of Columbia isolates come from Walter Reed Army Institute of Research projects; that is the submitter's location, not necessarily the patient's.
- **mecA in *S. aureus*:** {frac_ppv(mec)} mecA-positive isolates were oxacillin- or cefoxitin-resistant by MIC (PPV {pc(mec['ppv'])}); {frac_npv(mec)} mecA/mecC-negative isolates were not (NPV {pc(mec['npv'])}). No mecC was found. For {len(alt['isolates_affected'])} mecA-positive isolates the submitting lab reported oxacillin resistant despite a low MIC; counting the lab's call instead gives PPV {pc(alt['ppv'])} ({alt['gene_pos_R']} of {alt['gene_pos']}). The main tables use the MIC.
- **vanA or vanB in enterococci:** PPV {pc(van['ppv'])} ({frac_ppv(van)}), NPV {pc(van['npv'])} ({frac_npv(van)}). No vanB was found. These estimates rest on few isolates.
- **Carbapenemases in Enterobacterales:** any panel carbapenemase predicted resistance to at least one carbapenem in {frac_ppv(carb)} isolates (PPV {pc(carb['ppv'])}); its absence predicted no carbapenem resistance in {frac_npv(carb)} (NPV {pc(carb['npv'])}). "Any carbapenem" includes ertapenem. **For meropenem alone, PPV is {pc(carb_mero['ppv'])}** ({frac_ppv(carb_mero)}) and NPV {pc(carb_mero['npv'])}. KPC alone: PPV {pc(kpc['ppv'])} for any carbapenem, {pc(kpc_mero['ppv'])} for meropenem.
- **CTX-M and ceftriaxone:** PPV {pc(ctx_ec['ppv'])} in *E. coli* and {pc(ctx_kp['ppv'])} in *K. pneumoniae* complex. A CTX-M-negative result was a much weaker signal in *K. pneumoniae* complex (NPV {pc(ctx_kp['npv'])}) than in *E. coli* (NPV {pc(ctx_ec['npv'])}).
- **{S['n_discordance_cases']:,} discordant isolate-target pairs** ({S['n_discordant_isolates']:,} isolates), each with a likely cause, in `data/processed/discordance_cases.csv`.

## The four releases

| Output | File(s) | Zenodo record |
|---|---|---|
| Benchmark dataset | `data/processed/benchmark_isolates.tsv`, `benchmark_isolate_drug_long.tsv`, `concordance_table.csv` | {doi_link('benchmark')} |
| Gene to panel target crosswalk | `reference/gene_panel_crosswalk.csv` | {doi_link('crosswalk')} |
| Discordance case collection | `data/processed/discordance_cases.csv` | {doi_link('discordance')} |
| Concordance lookup page | `docs/index.html`, served at {PAGES} | (part of the benchmark record) |

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

`--no-download` reproduces the committed outputs exactly. A fresh download picks up isolates added to NCBI since {ACCESS}; that is how v1.1 is built.

## Sources

| Source | What it gives | Version | Terms | Accessed |
|---|---|---|---|---|
| NCBI BioSample antibiograms, via E-utilities ([docs](https://www.ncbi.nlm.nih.gov/books/NBK25499/)) | Submitted MIC, zone, method and S/I/R per drug | live database | NCBI policies: no restrictions on use | {ACCESS} |
| NCBI Pathogen Detection AMR results ([FTP](https://ftp.ncbi.nlm.nih.gov/pathogen/Results/)) | AMRFinderPlus gene calls per isolate | analysis runs recorded in PROVENANCE.txt; AMRFinderPlus {', '.join(S['amrfinder_versions'])} | same | {ACCESS} |
| AMRFinderPlus Reference Gene Hierarchy and Catalog ([FTP](https://ftp.ncbi.nlm.nih.gov/pathogen/Antimicrobial_resistance/AMRFinderPlus/database/latest/)) | Gene families and drug classes for the crosswalk | database 2026-08-07.1 | same | {ACCESS} |
| CLSI M100, 35th ed. (2025) | Breakpoints, cited in `reference/breakpoints.csv` | 2025 | values cited for reference | n/a |

## Limitations

See [docs/LIMITATIONS.md](docs/LIMITATIONS.md). The short version: genome calls are not panel calls; isolates are those labs chose to sequence and submit, so prevalence is not national prevalence; {pc(S['top_bioproject_share'])} of isolates come from one submitter project; enterococci are few.

## How to cite

{AUTH['family']}, {AUTH['given'][0]}. *U.S. Rapid Panel Resistance Marker Concordance Benchmark*, v1.0. Zenodo. {doi_link('benchmark')}. See `CITATION.cff`.

## AI assistance

Code, data wrangling and first drafts of documentation were prepared with the assistance of Claude (Anthropic). The author made the analytic decisions, checked the outputs against NCBI records using `docs/VERIFY_CHECKLIST.md`, and is responsible for the content.

## Maintainer

{AUTH['name']}, {AUTH['affiliation']}. {AUTH['email']}. Issues and corrections: {REPO}/issues
"""
open(os.path.join(ROOT, "README.md"), "w").write(readme)

talk = f"""# Talking about the U.S. Rapid Panel Resistance Marker Concordance Benchmark

*Every number here comes from `paper/stats.json`. Status: {draft}.*

## 60-second version

**The problem.** When a patient has a bloodstream infection, rapid panels can report a resistance gene within hours, long before the growth-based susceptibility result. Labs and doctors act on that early gene result. I am not aware of an openly maintained, U.S.-focused table that shows, gene by gene, how often that gene result matches the susceptibility result.

**What I built.** A free benchmark of {nb:,} U.S. clinical isolates from NCBI whose genomes and lab susceptibility results are both public. For each panel target (mecA, vanA and vanB, KPC, NDM, OXA-48-like, VIM, IMP, CTX-M) it shows how often a detected gene meant resistance and how often an absent gene meant no resistance, by drug and organism. Every disagreement is listed with its likely cause.

**What it shows.** Detected genes are strong signals: mecA meant methicillin resistance in {pc(mec['ppv'])} of *S. aureus*, and any panel carbapenemase meant resistance to at least one carbapenem in {pc(carb['ppv'])} of Enterobacterales ({pc(carb_mero['ppv'])} for meropenem alone). Absent genes are weaker signals for some organisms. In *Klebsiella pneumoniae*, only {pc(ctx_kp['npv'])} of CTX-M-negative isolates were ceftriaxone-susceptible, because other enzymes cause the same resistance.

**Who can use it.** Clinical microbiology labs writing reporting rules, antimicrobial stewardship teams, test developers and researchers.

**Where it is.** GitHub: {REPO}. Lookup page: {PAGES}. DOI: {doi_link('benchmark')}.

## Two-sentence version

I built an open benchmark of {nb:,} U.S. clinical bacterial isolates that measures, gene by gene, how well the resistance genes reported by rapid blood culture panels predict the laboratory susceptibility result. It is versioned on Zenodo with a free lookup page, and every disagreement is classified by its likely cause.

## Questions you may be asked

1. **Where does the data come from?** From NCBI, the U.S. National Library of Medicine's public database. Labs that sequence a bacterial genome can attach their susceptibility results. NCBI runs its own gene-finding tool, AMRFinderPlus, on every genome. I joined the two and kept U.S. human clinical isolates.
2. **What are its limits?** It uses genes found in the whole genome, not the panel's own result. The isolates are the ones labs chose to sequence, often resistant ones, so the numbers are not national rates. About {pc(S['top_bioproject_share'])} come from a single submitter project, and for those the recorded location is the submitting lab's. Enterococci are few ({org['Enterococcus faecalis'] + org['Enterococcus faecium']} isolates) and no vanB or mecC was found.
3. **Why does this matter for the United States?** CDC estimates more than 2.8 million antimicrobial-resistant infections and more than 35,000 deaths each year in the U.S. Rapid diagnostics are a named goal of the National Action Plan for Combating Antibiotic-Resistant Bacteria. Labs need to know how far an early gene result can be trusted.
"""
open(os.path.join(ROOT, "docs", "TALK_TRACK.md"), "w").write(talk)

# provenance, human-readable
import hashlib


def file_sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


lines = ["PROVENANCE LOG - U.S. Rapid Panel Resistance Marker Concordance Benchmark",
         "PLAIN-LANGUAGE NOTE: one line per downloaded file. Two fingerprints are given:",
         "  COMMITTED = size and SHA-256 of the file exactly as it ships in data/raw/ (check these with sha256sum).",
         "  SOURCE    = size and SHA-256 of the full stream downloaded from NCBI before filtering to isolates with",
         "              antibiograms (identical to COMMITTED for files saved unfiltered). Kept to identify the NCBI version.",
         "The full record (including row counts) is in PROVENANCE.jsonl.", ""]
for p in PROV:
    src = p.get("source_url") or (p.get("source", "") + " query: " + p.get("query", ""))
    sha = p.get("source_sha256") or p.get("sha256") or p.get("content_sha256")
    size = p.get("source_bytes") or p.get("bytes") or ""
    extra = ""
    if "source_rows" in p:
        extra = f" | {p['source_rows']} source rows, {p['rows_kept_with_AST_or_antibiogram']} kept"
    if "records_downloaded" in p:
        extra = f" | {p['records_downloaded']} records"
    fp = os.path.join(ROOT, p.get("saved_as", ""))
    csize, csha = (os.path.getsize(fp), file_sha(fp)) if os.path.isfile(fp) else ("missing", "missing")
    src_fp = f"SOURCE {size} bytes sha256:{sha}" if size else f"SOURCE sha256:{sha} (of the concatenated E-utilities responses)"
    lines.append(f"{p['access_date']} | {p.get('saved_as')} | COMMITTED {csize} bytes sha256:{csha} | {src_fp} | "
                 f"{src}{extra} | {p.get('terms','')}")
open(os.path.join(ROOT, "data", "raw", "PROVENANCE.txt"), "w").write("\n".join(lines) + "\n")

# verification checklist
ld = pd.read_csv(os.path.join(ROOT, "data", "processed", "benchmark_isolate_drug_long.tsv"), sep="\t", dtype=str)
mic = ld[ld.category_source == "reinterpreted MIC"].copy()
rnd = mic.sample(5, random_state=42)
mic["v"] = pd.to_numeric(mic.value, errors="coerce")
ext = pd.concat([mic[mic.drug == "meropenem"].nlargest(2, "v"), mic[mic.drug == "vancomycin"].nlargest(1, "v"),
                 mic[mic.drug == "oxacillin"].nlargest(1, "v"), mic[mic.drug == "ceftriaxone"].nsmallest(1, "v")])


def row_item(r):
    return (f"- [ ] `{r.biosample_acc}`, {r.drug}: file shows **{r.sign}{r.value} {r.units}**, category **{r.final_category}**. "
            f"Open https://www.ncbi.nlm.nih.gov/biosample/{r.biosample_acc} , scroll to the Antibiogram table, find {r.drug}. "
            f"Same value? ___")


spot = "\n".join(
    f"- [ ] `{s['biosample_acc']}` ({s['organism']}): file says {s['check_gene']} "
    f"{'= ' + s['alleles'] if s['alleles'] else 'not found'}, {s['drug']} {s['sign']}{s['value']} -> {s['category']}. "
    f"Open {s['isolates_browser_url']} and confirm the AMR genotypes column; open {s['biosample_url']} and confirm the {s['drug']} value. ___"
    for s in S["spot_checks"])
checklist = f"""# Your verification checklist

*Plain-language version: before anything goes public under your name, you check it. Total time: about 1.5 to 2 hours. Tick each box and write the date. The publish gate (`python tools/publish_gate.py .`) checks the mechanical items automatically. These are yours.*

## Part 1: Make sure the results can be rebuilt (15 to 30 min)

Pick one:
- [ ] **Option A, run it yourself.** In a terminal in the project folder: `pip install -r requirements.txt` then `./run_all.sh --no-download`. The last lines should include `isolates in the benchmark (>=1 usable paired drug result): {nb}` and `Done.`
- [ ] **Option B, ask Claude.** In a new chat with Opus 5.5 or Fable 5, upload the project zip and say: "Re-run this pipeline from scratch with --no-download and give me the headline numbers." Compare: {nb:,} isolates; mecA PPV {pc(mec['ppv'])}; any-carbapenemase PPV {pc(carb['ppv'])}; CTX-M NPV in *K. pneumoniae* {pc(ctx_kp['npv'])}; {S['n_discordance_cases']:,} discordance rows.

Then:
- [ ] Every number in `README.md` and `docs/TALK_TRACK.md` matches `paper/stats.json` (they are written from it by `code/07_docs.py`; spot-read three).

## Part 2: Check the sources and the rules (20 min)

- [ ] Open each source link in the README. Each page loads and is free to access.
- [ ] NCBI terms allow reuse: https://www.ncbi.nlm.nih.gov/home/about/policies/ (no restrictions on use of the data).
- [ ] **Breakpoints.** Open `reference/breakpoints.csv` beside your own copy of CLSI M100 (35th ed., 2025). Confirm each of the 19 rows, especially ertapenem (S <=0.5, R >=2), ceftazidime (S <=4, R >=16), cefotaxime disk (S >=26, R <=22), *S. aureus* oxacillin (S <=2, R >=4) and cefoxitin screen (<=4 / >=8), enterococcal vancomycin (S <=4, R >=32).
- [ ] **FDA recognition.** For each drug, open its page from https://www.fda.gov/drugs/development-resources/antibacterial-susceptibility-test-interpretive-criteria and confirm FDA recognizes CLSI M100 for that organism with no exception that changes these values. Then delete the word "[VERIFY]" in `reference/breakpoints.csv` for each row you confirmed.

## Part 3: Check rows by hand (40 to 60 min)

**Five gene and phenotype spot checks** (one per major target, chosen by the pipeline):
{spot}

**Five extreme values** (most likely to be errors):
{chr(10).join(row_item(r) for r in ext.itertuples())}

**Five random rows** (chosen by computer, seed 42):
{chr(10).join(row_item(r) for r in rnd.itertuples())}

**Three discordant cases you judge as a microbiologist** (open `data/processed/discordance_cases.csv`, filter `organism`):
- [ ] The five mecA-positive, oxacillin-susceptible *S. aureus* rows. Does the cause label fit? ___
- [ ] The vanA-positive, vancomycin-susceptible *E. faecium* (for example SAMN09728854). Would you call this vancomycin-variable *Enterococcus*? Should the label say so? ___
- [ ] Five CTX-M-negative, ceftriaxone-resistant *K. pneumoniae* rows. Does "panel carbapenemase present" or "non-panel ESBL or AmpC" match the genes listed? ___

## Part 4: Your decisions (15 min)

The build made these choices provisionally. Agree or change each one.
- [ ] **Salmonella.** Included as its own organism row and left out of the "Enterobacterales" summary row. Alternative: drop it entirely. Recommended: keep as is. Your choice: ___
- [ ] **Intermediate and SDD.** Counted as "not resistant" in the main tables; a second set of tables leaves them out. Alternative: count them as resistant ("non-susceptible"). That would lower PPV slightly and raise NPV for CTX-M. Recommended: keep as is. Your choice: ___
- [ ] **Which isolates count as human clinical.** NCBI "clinical" package plus a human host, or a blank host with a human specimen source ({S['n_us_human_clinical']:,} U.S. isolates before the drug filter). Screening swabs ({S['n_by_specimen'].get('screening/colonization swab', 0)}) and urine ({S['n_by_specimen'].get('urine', 0):,}) are included in the main table. Alternative: limit the main table to blood and sterile sites ({S['n_blood_or_sterile']:,} isolates), which panels actually test. Recommended: keep all clinical isolates in the main table and the blood table as a second view, as now. Your choice: ___
- [ ] **MICs that are not real MIC values.** {S['n_isolate_drug_mic_off_dilution_series']} results such as "oxacillin 23 mg/L" are not on the dilution series and look like zone sizes filed as MICs. The build uses the submitter's S/I/R call for these. Alternative: drop them. Recommended: keep as is. Your choice: ___
- [ ] **Gradient-strip readings** ({S['n_isolate_drug_mic_rounded_up_from_gradient']} results such as 1.5 mg/L) are rounded up to the next two-fold dilution before interpretation, as CLSI directs. Agree? ___
- [ ] **OXA-48 family variants** that NCBI's catalog does not list as carbapenem-hydrolyzing (for example OXA-163, OXA-405) still count as "OXA-48-like detected" and carry the flag `FAMILY_MEMBER_NONCARBA`. Agree? ___

## Part 5: Before it goes public (20 to 30 min)

- [ ] The "In plain terms" paragraph of `README.md` is rewritten in your own words. Nothing remains that you could not explain or defend. (Claude can do this with you line by line.)
- [ ] Your name, ORCID, affiliation and email are correct in `AUTHORS.json`.
- [ ] You have read `docs/LIMITATIONS.md` and agree with it.
- [ ] Draft stamps removed: `FINAL=1 ./run_all.sh --no-download` and `python3 tools/publish_gate.py . --allow-draft-in code/ tools/ docs/GLOSSARY.md docs/START_HERE.md docs/VERIFY_CHECKLIST.md docs/PUBLISH_GUIDE.md` passes (the allowed paths are code and instructions that mention the words DRAFT and VERIFY on purpose).
- [ ] Evidence log row written in `docs/evidence_log.csv` on release day.

**When every box is ticked, reply to Claude in your own words that you have checked the package and approve publishing.**
"""
open(os.path.join(ROOT, "docs", "VERIFY_CHECKLIST.md"), "w").write(checklist)
# citation file and data license carry the DOI too
cff = open(os.path.join(ROOT, "CITATION.cff")).read().splitlines()
cff = [(f'date-released: "{datetime.date.today().isoformat()}"' if l.startswith("date-released") and FINAL else
        (f'doi: "{DOIS["benchmark"]}"' if l.startswith("doi:") and DOIS.get("benchmark") else l)) for l in cff
       if not (FINAL and l.startswith("doi:") and not DOIS.get("benchmark"))]
if DOIS.get("benchmark") and not any(l.startswith("doi:") for l in cff):
    i = next(i for i, l in enumerate(cff) if l.startswith("url:"))
    cff.insert(i + 1, f'doi: "{DOIS["benchmark"]}"')
open(os.path.join(ROOT, "CITATION.cff"), "w").write("\n".join(cff) + "\n")
lic = open(os.path.join(ROOT, "LICENSE-DATA.md")).read()
if DOIS.get("benchmark"):
    lic = lic.replace("[DOI PENDING]", f"https://doi.org/{DOIS['benchmark']}").replace(
        "DOI assigned when the Zenodo record is published", f"https://doi.org/{DOIS['benchmark']}")
elif FINAL:
    lic = lic.replace("[DOI PENDING]", "DOI assigned when the Zenodo record is published")
open(os.path.join(ROOT, "LICENSE-DATA.md"), "w").write(lic)
print("docs written", "(final)" if FINAL else "(draft)")
