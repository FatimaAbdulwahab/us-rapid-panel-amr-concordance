# Your verification checklist

*Plain-language version: before anything goes public under your name, you check it. Total time: about 1.5 to 2 hours. Tick each box and write the date. The publish gate (`python tools/publish_gate.py .`) checks the mechanical items automatically. These are yours.*

## Part 1: Make sure the results can be rebuilt (15 to 30 min)

Pick one:
- [ ] **Option A, run it yourself.** In a terminal in the project folder: `pip install -r requirements.txt` then `./run_all.sh --no-download`. The last lines should include `isolates in the benchmark (>=1 usable paired drug result): 5168` and `Done.`
- [ ] **Option B, ask Claude.** In a new chat with Opus 5.5 or Fable 5, upload the project zip and say: "Re-run this pipeline from scratch with --no-download and give me the headline numbers." Compare: 5,168 isolates; mecA PPV 97.7%; any-carbapenemase PPV 97.8%; CTX-M NPV in *K. pneumoniae* 37.3%; 970 discordance rows.

Then:
- [ ] Every number in `README.md` and `docs/TALK_TRACK.md` matches `paper/stats.json` (they are written from it by `code/07_docs.py`; spot-read three).

## Part 2: Check the sources and the rules (20 min)

- [ ] Open each source link in the README. Each page loads and is free to access.
- [ ] NCBI terms allow reuse: https://www.ncbi.nlm.nih.gov/home/about/policies/ (no restrictions on use of the data).
- [ ] **Breakpoints.** Open `reference/breakpoints.csv` beside your own copy of CLSI M100 (35th ed., 2025). Confirm each of the 19 rows, especially ertapenem (S <=0.5, R >=2), ceftazidime (S <=4, R >=16), cefotaxime disk (S >=26, R <=22), *S. aureus* oxacillin (S <=2, R >=4) and cefoxitin screen (<=4 / >=8), enterococcal vancomycin (S <=4, R >=32).
- [ ] **FDA recognition.** For each drug, open its page from https://www.fda.gov/drugs/development-resources/antibacterial-susceptibility-test-interpretive-criteria and confirm FDA recognizes CLSI M100 for that organism with no exception that changes these values. Then delete the word "[VERIFY]" in `reference/breakpoints.csv` for each row you confirmed.

## Part 3: Check rows by hand (40 to 60 min)

**Five gene and phenotype spot checks** (one per major target, chosen by the pipeline):
- [ ] `SAMN08391007` (Staphylococcus aureus): file says mecA = mecA, oxacillin >2 -> R. Open https://www.ncbi.nlm.nih.gov/pathogens/isolates/#SAMN08391007 and confirm the AMR genotypes column; open https://www.ncbi.nlm.nih.gov/biosample/SAMN08391007 and confirm the oxacillin value. ___
- [ ] `SAMN09728854` (Enterococcus faecium): file says vanA = vanA, vancomycin <=2 -> S. Open https://www.ncbi.nlm.nih.gov/pathogens/isolates/#SAMN09728854 and confirm the AMR genotypes column; open https://www.ncbi.nlm.nih.gov/biosample/SAMN09728854 and confirm the vancomycin value. ___
- [ ] `SAMN02141983` (Klebsiella pneumoniae complex): file says KPC = blaKPC-3, meropenem ==4 -> R. Open https://www.ncbi.nlm.nih.gov/pathogens/isolates/#SAMN02141983 and confirm the AMR genotypes column; open https://www.ncbi.nlm.nih.gov/biosample/SAMN02141983 and confirm the meropenem value. ___
- [ ] `SAMN02581242` (Klebsiella pneumoniae complex): file says NDM = blaNDM-1, meropenem >=16 -> R. Open https://www.ncbi.nlm.nih.gov/pathogens/isolates/#SAMN02581242 and confirm the AMR genotypes column; open https://www.ncbi.nlm.nih.gov/biosample/SAMN02581242 and confirm the meropenem value. ___
- [ ] `SAMN02581298` (Escherichia coli): file says CTX-M = blaCTX-M-15, ceftriaxone >32 -> R. Open https://www.ncbi.nlm.nih.gov/pathogens/isolates/#SAMN02581298 and confirm the AMR genotypes column; open https://www.ncbi.nlm.nih.gov/biosample/SAMN02581298 and confirm the ceftriaxone value. ___
- [ ] `SAMN02356588` (Escherichia coli): file says CTX-M (absent) not found, ceftriaxone <=1 -> S. Open https://www.ncbi.nlm.nih.gov/pathogens/isolates/#SAMN02356588 and confirm the AMR genotypes column; open https://www.ncbi.nlm.nih.gov/biosample/SAMN02356588 and confirm the ceftriaxone value. ___

**Five extreme values** (most likely to be errors):
- [ ] `SAMN02356595`, meropenem: file shows **>=32 mg/L**, category **R**. Open https://www.ncbi.nlm.nih.gov/biosample/SAMN02356595 , scroll to the Antibiogram table, find meropenem. Same value? ___
- [ ] `SAMN02581389`, meropenem: file shows **==32 mg/L**, category **R**. Open https://www.ncbi.nlm.nih.gov/biosample/SAMN02581389 , scroll to the Antibiogram table, find meropenem. Same value? ___
- [ ] `SAMN34488840`, vancomycin: file shows **>=32 mg/L**, category **R**. Open https://www.ncbi.nlm.nih.gov/biosample/SAMN34488840 , scroll to the Antibiogram table, find vancomycin. Same value? ___
- [ ] `SAMN36727281`, oxacillin: file shows **>=4 mg/L**, category **R**. Open https://www.ncbi.nlm.nih.gov/biosample/SAMN36727281 , scroll to the Antibiogram table, find oxacillin. Same value? ___
- [ ] `SAMN03287454`, ceftriaxone: file shows **<=0.25 mg/L**, category **S**. Open https://www.ncbi.nlm.nih.gov/biosample/SAMN03287454 , scroll to the Antibiogram table, find ceftriaxone. Same value? ___

**Five random rows** (chosen by computer, seed 42):
- [ ] `SAMN36726652`, ceftriaxone: file shows **<=1 mg/L**, category **S**. Open https://www.ncbi.nlm.nih.gov/biosample/SAMN36726652 , scroll to the Antibiogram table, find ceftriaxone. Same value? ___
- [ ] `SAMN19670090`, ceftriaxone: file shows **<=1 mg/L**, category **S**. Open https://www.ncbi.nlm.nih.gov/biosample/SAMN19670090 , scroll to the Antibiogram table, find ceftriaxone. Same value? ___
- [ ] `SAMN36728923`, ertapenem: file shows **<=0.5 mg/L**, category **S**. Open https://www.ncbi.nlm.nih.gov/biosample/SAMN36728923 , scroll to the Antibiogram table, find ertapenem. Same value? ___
- [ ] `SAMN26309010`, ceftazidime: file shows **<=2 mg/L**, category **S**. Open https://www.ncbi.nlm.nih.gov/biosample/SAMN26309010 , scroll to the Antibiogram table, find ceftazidime. Same value? ___
- [ ] `SAMN26304681`, ceftazidime: file shows **<=2 mg/L**, category **S**. Open https://www.ncbi.nlm.nih.gov/biosample/SAMN26304681 , scroll to the Antibiogram table, find ceftazidime. Same value? ___

**Three discordant cases you judge as a microbiologist** (open `data/processed/discordance_cases.csv`, filter `organism`):
- [ ] The five mecA-positive, oxacillin-susceptible *S. aureus* rows. Does the cause label fit? ___
- [ ] The vanA-positive, vancomycin-susceptible *E. faecium* (for example SAMN09728854). Would you call this vancomycin-variable *Enterococcus*? Should the label say so? ___
- [ ] Five CTX-M-negative, ceftriaxone-resistant *K. pneumoniae* rows. Does "panel carbapenemase present" or "non-panel ESBL or AmpC" match the genes listed? ___

## Part 4: Your decisions (15 min)

The build made these choices provisionally. Agree or change each one.
- [ ] **Salmonella.** Included as its own organism row and left out of the "Enterobacterales" summary row. Alternative: drop it entirely. Recommended: keep as is. Your choice: ___
- [ ] **Intermediate and SDD.** Counted as "not resistant" in the main tables; a second set of tables leaves them out. Alternative: count them as resistant ("non-susceptible"). That would lower PPV slightly and raise NPV for CTX-M. Recommended: keep as is. Your choice: ___
- [ ] **Which isolates count as human clinical.** NCBI "clinical" package plus a human host, or a blank host with a human specimen source (5,533 U.S. isolates before the drug filter). Screening swabs (191) and urine (3,426) are included in the main table. Alternative: limit the main table to blood and sterile sites (731 isolates), which panels actually test. Recommended: keep all clinical isolates in the main table and the blood table as a second view, as now. Your choice: ___
- [ ] **MICs that are not real MIC values.** 170 results such as "oxacillin 23 mg/L" are not on the dilution series and look like zone sizes filed as MICs. The build uses the submitter's S/I/R call for these. Alternative: drop them. Recommended: keep as is. Your choice: ___
- [ ] **Gradient-strip readings** (63 results such as 1.5 mg/L) are rounded up to the next two-fold dilution before interpretation, as CLSI directs. Agree? ___
- [ ] **OXA-48 family variants** that NCBI's catalog does not list as carbapenem-hydrolyzing (for example OXA-163, OXA-405) still count as "OXA-48-like detected" and carry the flag `FAMILY_MEMBER_NONCARBA`. Agree? ___

## Part 5: Before it goes public (20 to 30 min)

- [ ] The "In plain terms" paragraph of `README.md` is rewritten in your own words. Nothing remains that you could not explain or defend. (Claude can do this with you line by line.)
- [ ] Your name, ORCID, affiliation and email are correct in `AUTHORS.json`.
- [ ] You have read `docs/LIMITATIONS.md` and agree with it.
- [ ] Draft stamps removed: `FINAL=1 ./run_all.sh --no-download` and `python3 tools/publish_gate.py . --allow-draft-in code/ tools/ docs/GLOSSARY.md docs/START_HERE.md docs/VERIFY_CHECKLIST.md docs/PUBLISH_GUIDE.md` passes (the allowed paths are code and instructions that mention the words DRAFT and VERIFY on purpose).
- [ ] Evidence log row written in `docs/evidence_log.csv` on release day.

**When every box is ticked, reply to Claude in your own words that you have checked the package and approve publishing.**
