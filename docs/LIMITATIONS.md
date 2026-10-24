# Limitations

*Plain-language note: what this benchmark can and cannot tell you. Read before citing any number. Counts quoted here are in `paper/stats.json`.*

1. **Genome calls stand in for panel calls.** The "panel result" is AMRFinderPlus run on an assembled whole genome, mapped to panel targets. A real panel uses PCR primers on a positive blood culture. Allele coverage, limits of detection, mixed cultures and specimen effects are not measured. Results describe how well the presence of the gene predicts the phenotype, not how any commercial panel performs.

2. **Panel allele coverage is not asserted.** The crosswalk assigns every allele in a family to its target. A given panel may miss some rare alleles. OXA-48 family alleles that NCBI does not list as carbapenem-hydrolyzing are flagged `FAMILY_MEMBER_NONCARBA`.

3. **The isolates are not a random sample.** They are the isolates that laboratories and surveillance programs chose to sequence and submit with susceptibility results. Resistant organisms and outbreak investigations are over-represented. PPV and NPV depend on how common resistance is, so the values here may differ from a single hospital's. Treat prevalence in this set as a property of the set, not of the United States.

4. **A few submitters dominate, and location often means the lab.** The largest single BioProject (Walter Reed Army Institute of Research, PRJNA809394) contributes about 40% of isolates (`top_bioproject_share` in stats.json). Their testing platform, panel of drugs and selection rules shape the results. All "District of Columbia" isolates come from Walter Reed projects, so that location is the submitter's, not necessarily the patient's; these rows carry a `location_note`. Submitted locations mix states, cities and misspellings; cities were resolved to their state by a fixed table in `code/04_build.py` (Rochester was resolved to New York from the submitter's coordinates). Counts by state are in `n_by_state` in stats.json, and some isolates give no state at all (`n_no_state`). State counts describe where isolates were submitted from, not national coverage.

5. **Enterococci and some targets are sparse.** Few enterococci have public antibiograms, and no vanB or mecC was found. VIM and IMP each have fewer than ten isolates. Confidence intervals are wide; the lookup page warns when a PPV rests on fewer than ten gene-positive isolates.

6. **Phenotypes come from many laboratories and methods.** Vitek, Sensititre, Phoenix, broth microdilution, disk and gradient strip are mixed. No central re-testing was done. Results were re-interpreted with CLSI M100-Ed35 breakpoints when a value was available; otherwise the submitter's call was used and flagged. Some submitted values are clearly not MICs (for example 23 mg/L) and were not reinterpreted.

7. **Cause labels are likely causes, not proven ones.** They are assigned by rules from the genome content and the MIC. Expression changes, porin loss not called by AMRFinderPlus, heteroresistance, mixed cultures, mislabeled samples and assembly errors cannot be told apart with public data, so they share the "unexplained by available data" label.

8. **Chromosomal AmpC organisms.** For *Enterobacter*, *K. aerogenes*, *Citrobacter freundii*, *Serratia* and Morganellaceae, cephalosporin resistance without CTX-M is expected. These rows lower the pooled CTX-M NPV and are labeled, not removed.

9. **Mixed AMRFinderPlus versions.** NCBI ran isolates with different software and database versions (listed in stats.json). Newer databases may call genes older runs missed. v1.1 will report whether re-runs change any calls.

10. **Specimen categories are inferred** from free-text isolation sources by keyword rules. Some isolates fall into "other/unspecified".

11. **Proteus is absent.** NCBI Pathogen Detection has no *Proteus* organism group, so *Proteus* isolates are not in this release.

12. **mecA phenotype rule.** For *S. aureus*, oxacillin resistance is judged from the MIC alone, so the phenotype stays independent of the gene result. Some submitting labs call oxacillin resistant from a cefoxitin screen, PBP2a or mecA test even when the oxacillin MIC is low. Three mecA-positive isolates are in that situation; counting the lab's call instead would raise the mecA PPV (the alternative value is `mecA_alt_trust_submitter_oxacillin_R` in stats.json and is quoted in the README).

13. **Laboratory reference strains removed.** *S. aureus* JE2 and LAC were submitted with clinical metadata but are laboratory strains; they are excluded by name (`excluded_reference_strains` in stats.json). Other reference strains may remain where the strain field does not name them.

14. **Beta-lactamase classes for cause labels.** Non-CTX-M cephalosporinases are split into acquired ESBL or AmpC genes, chromosomal enzymes intrinsic to the organism (for example *E. coli* blaEC, *Enterobacter* blaACT and blaMIR) and narrow-spectrum OXA-1 and OXA-10 family enzymes. Only acquired genes are labeled "acquired non-CTX-M ESBL or AmpC". *E. coli* ampC promoter mutations are labeled separately. The split uses fixed lists in `code/04_build.py` and may misplace rare enzymes.

15. **Breakpoints are fixed at one edition.** All results use CLSI M100-Ed35 (2025). Older submitter interpretations under earlier breakpoints were overridden where values allowed. The author confirmed every breakpoint value against CLSI M100-Ed35 and the FDA STIC pages on 2026-10-24.
