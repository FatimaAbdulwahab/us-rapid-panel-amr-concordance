#!/usr/bin/env bash
# Rebuild everything from scratch. Steps 01a-01c download fresh data from NCBI
# (about 2 GB streamed, 20-40 minutes). To rebuild from the committed raw files
# only, run: ./run_all.sh --no-download
set -euo pipefail
cd "$(dirname "$0")"
if [ "${1:-}" != "--no-download" ]; then
  rm -f data/raw/PROVENANCE.jsonl
  python3 code/01a_fetch_antibiograms.py
  python3 code/01c_fetch_reference.py
  python3 code/01b_fetch_amrfinder.py
fi
python3 code/02_parse_antibiograms.py
python3 code/03_crosswalk.py
python3 code/04_build.py
python3 code/05_figures.py ${FINAL:+--final}
DOI_ARG=$(python3 -c "import json,os;p='zenodo/dois.json';print(json.load(open(p)).get('benchmark','') if os.path.exists(p) else '')")
python3 code/06_site.py ${FINAL:+--final} ${DOI_ARG:+--doi "https://doi.org/$DOI_ARG"}
python3 code/07_docs.py ${FINAL:+--final}
echo "Gate: python3 tools/publish_gate.py . --allow-draft-in code/ tools/ docs/GLOSSARY.md docs/START_HERE.md docs/VERIFY_CHECKLIST.md docs/PUBLISH_GUIDE.md"
echo "Done. Headline numbers are in paper/stats.json; checks in data/processed/qa_report.txt"
