# Codebook

*Plain-language note: this file explains every column in every output table, where it comes from, and how it was computed. Open it when you or a reader needs to know exactly what a column means.*

All tables are UTF-8. `.tsv` files are tab-separated; `.csv` files are comma-separated. Empty cell = not available or not applicable. Booleans are `True` / `False`.

## Shared definitions

| Term | Definition |
|---|---|
| Isolate | One NCBI BioSample. When a BioSample has more than one genome in Pathogen Detection, the most recently created analysis target is kept. |
| U.S. | `geo_loc_name` begins with `USA`. |
| Human clinical | NCBI `epi_type` = `clinical` AND (host contains "Homo sapiens", "human" or "patient"; OR host blank AND isolation source names a human specimen and no food, animal or environmental source). |
| Panel target | One of mecA, mecC, vanA, vanB, KPC, NDM, OXA-48-like, VIM, IMP, CTX-M, assigned through `reference/gene_panel_crosswalk.csv`. |
| Detected | AMRFinderPlus reported at least one gene in the target's family, complete or partial. |
| Resistant (R) | Final category R for the drug (see `final_category`). |
| Not resistant | Final category S, I or SDD (main analysis), or S only (sensitivity analysis). |
| Composite drug | "any carbapenem" = meropenem, imipenem, ertapenem, doripenem; "oxacillin or cefoxitin"; "any of ceftriaxone, cefotaxime, ceftazidime". Resistant if R to any tested member; not resistant if at least one member was tested and none was R. |

## `data/processed/benchmark_isolates.tsv` (one row per isolate)

| Column | Meaning | Source / transformation |
|---|---|---|
| biosample_acc | NCBI BioSample accession | NCBI |
| target_acc | Pathogen Detection analysis target (PDT) accession | NCBI Pathogen Detection |
| asm_acc | Genome assembly accession | NCBI Pathogen Detection |
| organism | Analysis group: *S. aureus*, *E. faecalis*, *E. faecium*, *E. coli* (includes *Shigella*), *K. pneumoniae* complex, *K. oxytoca* complex, *K. aerogenes*, *Enterobacter cloacae* complex, *Citrobacter freundii* complex, *Serratia* spp., Morganella / Providencia, *Salmonella enterica*, Klebsiella other, Other Enterobacterales | from `scientific_name` by `organism_category()` in `code/04_build.py` |
| scientific_name | Species as computed by NCBI | NCBI |
| ncbi_taxgroup | Pathogen Detection organism group the row came from | file name |
| us_state | State resolved from `geo_loc_name` (full names, postal codes, and a fixed city and misspelling table); blank when only "USA" is given | `us_state()` in `code/04_build.py` |
| location_note | Set when the location is the submitter's rather than the patient's (Walter Reed "District of Columbia" rows) | computed |
| strain | Strain name as submitted (used to remove laboratory reference strains such as JE2 and LAC) | NCBI |
| collection_year | First four digits of `collection_date` | NCBI |
| isolation_source | As submitted | NCBI |
| specimen_category | blood; other sterile site; urine; respiratory; wound/tissue; screening/colonization swab; stool; other/unspecified | keyword rules in `specimen_category()` |
| human_clinical_rule | Which branch of the human-clinical rule admitted the isolate | computed |
| bioproject_acc, bioproject_center | Submitting project and center | NCBI |
| amrfinder_version, refgene_db_version | AMRFinderPlus software and database used by NCBI for this isolate | NCBI |
| `<target>_detected` | Panel target found (complete or partial) | crosswalk applied to `AMR_genotypes` |
| `<target>_complete` | At least one call for the target is complete (no PARTIAL, MISTRANSLATION, INTERNAL_STOP, FRAMESHIFT suffix) | computed |
| `<target>_alleles` | Every AMRFinderPlus symbol matched to the target, with NCBI's suffix if any | NCBI symbols |
| `<target>_flags` | Crosswalk match flags of those symbols | crosswalk |
| other_carbapenem_gene | Non-panel genes whose catalog subclass includes CARBAPENEM (e.g. blaOXA-23, blaIMI, blaSME, blaGES carbapenemases) | AMRFinderPlus hierarchy |
| other_carbapenem_porin_or_point | Point mutations with subclass CARBAPENEM (porins ompK35, ompK36, ompC, ompF and similar), including frameshift and truncation calls not listed one by one in the mutation table, which are mapped by gene | AMRProt-mutation.tsv |
| other_cephalosporinase | All non-CTX-M genes with subclass including CEPHALOSPORIN | hierarchy |
| other_ceph_acquired | The subset that are acquired ESBL or AmpC genes (e.g. SHV-12, CMY-2 in *E. coli*, DHA in *K. pneumoniae*) | `ceph_kind()` |
| other_ceph_intrinsic | The subset intrinsic to the organism (e.g. *E. coli* blaEC, *Enterobacter* blaACT/blaMIR, *C. freundii* blaCMY, *Serratia* blaSRT, *K. oxytoca* blaOXY) | `ceph_kind()` |
| other_ceph_narrow | Narrow-spectrum OXA-1 and OXA-10 family enzymes | `ceph_kind()` |
| other_ampc_promoter_point | *E. coli* chromosomal ampC promoter mutations | AMRProt-mutation.tsv |
| other_methicillin, other_vancomycin | Non-panel methicillin (e.g. mecB) or glycopeptide genes (vanC, vanD, vanM, vanN, operon accessory genes) | hierarchy |
| `<drug>_category` | Final S, I, SDD, NS, R, NI (not interpretable) or NA (drug not applicable to this organism) | see long table |
| `<drug>_category_source` | reinterpreted MIC; reinterpreted DISK; submitter interpretation; not interpretable; drug not applicable to organism | computed |
| `<drug>_sign`, `<drug>_value` | Measurement sign and value as submitted | NCBI BioSample |
| AMR_genotypes | Full AMRFinderPlus genotype string | NCBI |
| AST_phenotypes | NCBI's summary of submitted S/I/R calls | NCBI |

## `data/processed/benchmark_isolate_drug_long.tsv` (one row per isolate and drug)

| Column | Meaning |
|---|---|
| biosample_acc, drug | Isolate and drug (lower case) |
| method | MIC or DISK (DISK when units are mm or the method names disk diffusion) |
| sign, value, units | As submitted (`value` is the original reading, before any rounding) |
| platform, vendor, testing_standard | As submitted (e.g. Vitek 2, Sensititre, Phoenix; CLSI) |
| submitted_phenotype | Submitter's S/I/R, or "not defined" |
| reinterpreted | Category from `reference/breakpoints.csv`: S, I, R, NI (censored value spans two categories, or MIC not on the dilution series) or NA |
| final_category | reinterpreted value when S/I/R; else submitter's call; else NI |
| category_source | Which of the two was used |
| near_R_breakpoint | Exact MIC within one two-fold dilution of the R breakpoint, or zone within 2 mm |
| mic_off_dilution_series | MIC value not on the two-fold or gradient-strip series (e.g. 23 mg/L); submitter call used |
| mic_rounded_up_from_gradient | Gradient-strip half-step (e.g. 1.5) rounded up to the next two-fold dilution before interpretation |

Censored values: `<=x` means the MIC is x or lower; `<x` is x/2 or lower; `>=x` is x or higher; `>x` is 2x or higher. A censored value is interpreted only when every possible value falls in one category. When an isolate has several results for one drug, the order of preference is reinterpreted MIC, reinterpreted disk, submitter call; ties keep the most resistant. Imipenem is not used for Morganella / Providencia (intrinsically elevated MICs).

## `data/processed/concordance_table.csv` (one row per analysis)

| Column | Meaning |
|---|---|
| analysis_version | `main` (I and SDD count as not resistant) or `sensitivity_excluding_intermediate` (isolates with I or SDD left out) |
| isolate_subset | all U.S. human clinical isolates; or blood and other sterile-site isolates only |
| level | `gene` (one target) or `class` (any target of the class: mecA or mecC; vanA or vanB; any panel carbapenemase) |
| panel_target, drug, organism | What was scored |
| n | Isolates with a usable result |
| gene_pos_R, gene_pos_notR, gene_neg_R, gene_neg_notR | The 2x2 table |
| ppv | gene_pos_R / (gene_pos_R + gene_pos_notR): when the gene is found, share resistant |
| npv | gene_neg_notR / (gene_neg_notR + gene_neg_R): when the gene is absent, share not resistant |
| sensitivity | gene_pos_R / all resistant |
| specificity | gene_neg_notR / all not resistant |
| `*_lo95`, `*_hi95` | Wilson score 95% interval |
| categorical_agreement | (gene_pos_R + gene_neg_notR) / n |

For a single carbapenemase at gene level, isolates carrying a different carbapenemase count as gene-negative. Use the class-level row to judge what a fully negative carbapenemase result means.

## `data/processed/discordance_cases.csv` (one row per discordant isolate and target)

Recorded from the main analysis, all clinical isolates, organism-level rows, using the composite drug where one exists (vancomycin for enterococci). Gene detected but not resistant is recorded per target; gene not detected but resistant is recorded per class (mecA or mecC; vanA or vanB; any panel carbapenemase; CTX-M).

| Column | Meaning |
|---|---|
| direction | "gene detected, not resistant" or "gene not detected, resistant" |
| us_state, location_note, specimen_category, collection_year, bioproject_acc | As in the isolate table |
| panel_target, drug_or_composite | What disagreed |
| target_alleles, target_flags | The panel-target calls and crosswalk flags |
| non_panel_mechanisms | Other genes or mutations of the same drug class found by AMRFinderPlus |
| phenotype_detail | Each drug: sign, value, units, final category and its source |
| primary_cause | First applicable cause in the fixed order below |
| all_applicable_causes | Every applicable cause, separated by " ; " |
| biosample_url | Link to check the record |

Cause order, gene detected but not resistant: partial or interrupted gene call; non-carbapenemase OXA-48 variant; value within one dilution of the R breakpoint; submitter interpretation differs from current breakpoints; submitter call only; unexplained.

Cause order, gene not detected but resistant: (carbapenems) non-panel carbapenemase, ESBL or AmpC (acquired, intrinsic or promoter-driven) with porin change, ESBL or AmpC without a called porin change, porin change only; (cephalosporins) panel carbapenemase present, acquired non-CTX-M ESBL or AmpC, chromosomal AmpC organism, ampC promoter mutation (an "only narrow-spectrum beta-lactamases" note is listed but never chosen as the primary cause); (glycopeptides) vanA operon genes without a ligase call, non-panel van gene; (methicillin) mec regulators without mecA, non-panel mec gene; then value near breakpoint; submitter interpretation differs; submitter call only; unexplained.

## `reference/gene_panel_crosswalk.csv` (one row per AMRFinderPlus symbol)

| Column | Meaning |
|---|---|
| amrfinder_symbol | Node in the AMRFinderPlus Reference Gene Hierarchy |
| panel_target | Panel target it maps to |
| target_drug_class | methicillin, vancomycin, carbapenem or extended-spectrum cephalosporin |
| hierarchy_family_node | Family node used to define the target (e.g. blaOXA-48_fam) |
| match_flag | EXACT_TARGET, FAMILY_MEMBER, FAMILY_UNTYPED, FAMILY_MEMBER_NONCARBA, VARIANT_SUBTYPE (defined in `code/03_crosswalk.py`) |
| catalog_class, catalog_subclass, product_name | From NCBI |
| refgene_db_version | Database version the crosswalk was built from |

Whether a commercial panel detects a specific allele is set by its manufacturer's instructions for use and is not asserted here.

## `reference/breakpoints.csv`

One row per organism group, drug and method, with the susceptible and resistant breakpoints, the name of the in-between category, and the source.

## `paper/stats.json`

Every number quoted in the README, talk track, checklist and lookup page. Written by `code/04_build.py`.
