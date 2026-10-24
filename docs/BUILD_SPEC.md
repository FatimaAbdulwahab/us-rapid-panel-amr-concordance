# Build spec

*Plain-language note: the one-page plan the build followed. Each line has a plain meaning in italics.*

```
PROJECT:        U.S. Rapid Panel Resistance Marker Concordance Benchmark. Archetypes: benchmark + validation study + dataset.
QUESTION:       When a rapid blood culture panel target gene is present (or absent) in a U.S. clinical isolate,
                how often is the laboratory susceptibility result resistant (or not)?
SOURCES:        NCBI BioSample antibiograms (E-utilities, antibiogram[filter]); NCBI Pathogen Detection
                latest_snps/AMR/*.amr.metadata.tsv; AMRFinderPlus Reference Gene Hierarchy, Catalog and
                AMRProt-mutation (database 2026-08-07.1); CLSI M100-Ed35 (2025) breakpoints. All accessed 2026-10-24.
                NCBI data: no restrictions on use.
UNIT:           One isolate (BioSample). Analysis unit: isolate x panel target x drug.
MEASURES:       PPV, NPV, sensitivity, specificity, categorical agreement, Wilson 95% CI; by gene, drug, organism;
                all specimens and blood/sterile-site; I/SDD as not resistant (main) or excluded (sensitivity).
OUTPUTS:        data/processed/benchmark_isolates.tsv, benchmark_isolate_drug_long.tsv, concordance_table.csv,
                discordance_cases.csv; reference/gene_panel_crosswalk.csv; docs/index.html (lookup page);
                docs/CODEBOOK.md; data/raw/PROVENANCE.txt; paper/figures/fig1, fig2; paper/stats.json.
VENUES:         GitHub (code, data, Pages lookup) -> Zenodo: benchmark DOI, crosswalk DOI, discordance DOI.
VERIFY POINTS:  Breakpoint table vs. CLSI M100 and FDA STIC; spot checks vs. NCBI; Salmonella handling; I/SDD handling;
                human-clinical rule; off-series MIC handling; gradient rounding; OXA-48 non-carbapenemase variants.
LICENSE:        Code MIT; data and documents CC BY 4.0.
ASSUMPTIONS:    Proceeding on the defaults offered to the author on 2026-10-24 (author block as given; Salmonella
                as its own row; reinterpret MICs with CLSI M100-Ed35; I/SDD as not resistant; CC BY 4.0 + MIT).
```

*Question: the one thing this project answers. Unit: every row in the main table is one isolate. Measures: the four "report card" numbers, each with a range of uncertainty. Venues: GitHub first, then three Zenodo DOIs. Verify points: the decisions you rule on in the checklist.*
