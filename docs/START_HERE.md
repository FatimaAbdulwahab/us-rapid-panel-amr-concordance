# Start Here: U.S. Rapid Panel Resistance Marker Concordance Benchmark

*Read this first. It explains your project in plain language. Words in bold are explained in [GLOSSARY.md](GLOSSARY.md).*

## What you are building

A free, permanent public table that shows, gene by gene, how often a resistance gene reported by a rapid blood culture panel matches the laboratory's growth-based susceptibility result, for U.S. clinical isolates.

## Why it matters

When a blood culture turns positive, panels such as BioFire FilmArray BCID2 report resistance genes like mecA, KPC or CTX-M within about an hour. The **antimicrobial susceptibility test** from BD Phoenix or a similar system takes another day or two. Labs and prescribers act on the gene result in between. They need to know two things: when the gene is found, how often is the organism really resistant? And when it is not found, how safe is it to assume susceptibility?

Published studies answer this one hospital at a time. We are not aware of an openly maintained, U.S.-focused table that gives the figure gene by gene. This project builds that table from public data, and updates it as NCBI grows.

Think of it as a report card for each gene target: how often its early "yes" or "no" was right once the full lab result came in.

## Where the information comes from

All sources are free and public. Nothing here needs special permission.

| Source | In plain terms | What one row looks like | Link |
|---|---|---|---|
| NCBI BioSample antibiograms | Susceptibility results that labs attach when they submit a bacterial genome to the U.S. National Library of Medicine | One isolate, one drug: "meropenem, MIC >=16 mg/L, Vitek 2, CLSI, resistant" | https://www.ncbi.nlm.nih.gov/biosample |
| NCBI Pathogen Detection | NCBI runs its own gene-finding program, **AMRFinderPlus**, on every submitted genome | One isolate: "blaKPC-3, blaSHV-11, oqxA..." | https://www.ncbi.nlm.nih.gov/pathogens/ |
| AMRFinderPlus gene family tree | NCBI's official list of which gene names belong to which family | "blaOXA-181 belongs to the OXA-48 family" | https://ftp.ncbi.nlm.nih.gov/pathogen/Antimicrobial_resistance/ |
| CLSI M100, 35th edition (2025) | The breakpoints FDA recognizes for reading MICs as S, I or R | "Enterobacterales, meropenem: S <=1, R >=4" | your own copy |

## What you will have at the end

- [ ] **A public project page** on GitHub where anyone can see and reuse your work: https://github.com/FatimaAbdulwahab/us-rapid-panel-amr-concordance
- [ ] **Three permanent citation numbers (DOIs)** from Zenodo: the benchmark dataset, the gene-to-panel crosswalk, and the discordance case collection
- [ ] **A free lookup page** where anyone picks a gene, drug and organism and sees the answer: https://fatimaabdulwahab.github.io/us-rapid-panel-amr-concordance/
- [ ] **A codebook and provenance log** with every release, so others can trust and reuse it

## How it connects to your work

You have performed organism identification and susceptibility testing on BioFire FilmArray, BD Phoenix and MALDI-TOF in high-complexity microbiology, and both of your review manuscripts look at where gene results and growth results disagree. This project turns that question into an open, national-scale measurement that labs can use.

## What you need to do

| Your task | When | Time |
|---|---|---|
| Create a Zenodo account (log in with ORCID) | Now | 3 min |
| Answer the five setup questions (or say "go with your defaults") | Now | 5 min |
| Check the results using `docs/VERIFY_CHECKLIST.md` | Now that the draft is ready | 1.5 to 2 hours |
| Rewrite the README summary in your own words | During checking | 15 min |
| Approve publishing | After checking | 5 min |
| Push to GitHub and publish on Zenodo, using `docs/PUBLISH_GUIDE.md` (or give Claude upload tokens) | After approval | 30 min |

Everything else is built for you.

## The steps ahead

1. **Data collected.** Done. Downloaded from NCBI with every source logged.
2. **Data cleaned and combined.** Done. Genes matched to lab results, U.S. human clinical isolates kept.
3. **Quality checks.** Done. Counts, interpretation tests and spot checks in `data/processed/qa_report.txt`.
4. **Figures and lookup page.** Done, stamped DRAFT.
5. **Documents.** Done. README, codebook, limitations, talk track.
6. **Ready for your check.** You verify, then we publish.

*You are here: step 6.*
