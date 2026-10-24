# Talking about the U.S. Rapid Panel Resistance Marker Concordance Benchmark

*Every number here comes from `paper/stats.json`. Status: Released v1.0.0, 2026-10-24.*

## 60-second version

**The problem.** When a patient has a bloodstream infection, rapid panels can report a resistance gene within hours, long before the growth-based susceptibility result. Labs and doctors act on that early gene result. I am not aware of an openly maintained, U.S.-focused table that shows, gene by gene, how often that gene result matches the susceptibility result.

**What I built.** A free benchmark of 5,168 U.S. clinical isolates from NCBI whose genomes and lab susceptibility results are both public. For each panel target (mecA, vanA and vanB, KPC, NDM, OXA-48-like, VIM, IMP, CTX-M) it shows how often a detected gene meant resistance and how often an absent gene meant no resistance, by drug and organism. Every disagreement is listed with its likely cause.

**What it shows.** Detected genes are strong signals: mecA meant methicillin resistance in 97.7% of *S. aureus*, and any panel carbapenemase meant resistance to at least one carbapenem in 97.8% of Enterobacterales (87.6% for meropenem alone). Absent genes are weaker signals for some organisms. In *Klebsiella pneumoniae*, only 37.3% of CTX-M-negative isolates were ceftriaxone-susceptible, because other enzymes cause the same resistance.

**Who can use it.** Clinical microbiology labs writing reporting rules, antimicrobial stewardship teams, test developers and researchers.

**Where it is.** GitHub: https://github.com/FatimaAbdulwahab/us-rapid-panel-amr-concordance. Lookup page: https://fatimaabdulwahab.github.io/us-rapid-panel-amr-concordance/. DOI: assigned when the Zenodo record is published.

## Two-sentence version

I built an open benchmark of 5,168 U.S. clinical bacterial isolates that measures, gene by gene, how well the resistance genes reported by rapid blood culture panels predict the laboratory susceptibility result. It is versioned on Zenodo with a free lookup page, and every disagreement is classified by its likely cause.

## Questions you may be asked

1. **Where does the data come from?** From NCBI, the U.S. National Library of Medicine's public database. Labs that sequence a bacterial genome can attach their susceptibility results. NCBI runs its own gene-finding tool, AMRFinderPlus, on every genome. I joined the two and kept U.S. human clinical isolates.
2. **What are its limits?** It uses genes found in the whole genome, not the panel's own result. The isolates are the ones labs chose to sequence, often resistant ones, so the numbers are not national rates. About 40.2% come from a single submitter project, and for those the recorded location is the submitting lab's. Enterococci are few (119 isolates) and no vanB or mecC was found.
3. **Why does this matter for the United States?** CDC estimates more than 2.8 million antimicrobial-resistant infections and more than 35,000 deaths each year in the U.S. Rapid diagnostics are a named goal of the National Action Plan for Combating Antibiotic-Resistant Bacteria. Labs need to know how far an early gene result can be trusted.
