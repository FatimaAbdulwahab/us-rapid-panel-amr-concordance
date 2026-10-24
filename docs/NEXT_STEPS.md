# Next steps

*Plain-language note: what later versions add, so v1.0 is understood as the first step of a maintained resource.*

## v1.1 (target October 2027)

- Re-run `./run_all.sh` (full download) to add isolates deposited during 2027. Report how many were added per organism and whether any v1.0 numbers moved outside their confidence intervals.
- Add a year-over-year difference table (`data/processed/changes_since_v1.0.csv`).
- Report whether NCBI re-runs with newer AMRFinderPlus databases changed any gene calls.

## Candidate additions

- **mcr-1 and colistin**, the remaining BCID2 resistance target, if enough U.S. isolates have colistin MICs.
- **Enterococci from other public sources** (for example, the Bacterial and Viral Bioinformatics Resource Center) to strengthen vanA and vanB estimates.
- **Panel-specific allele coverage columns**, filled only from manufacturers' published instructions for use.
- **A short data descriptor paper** (for example in *Scientific Data* or *Microbiology Resource Announcements*) citing the Zenodo DOIs.
- **Per-submitter sensitivity analysis**, leaving out the largest BioProject, to show how much one source drives each estimate.
