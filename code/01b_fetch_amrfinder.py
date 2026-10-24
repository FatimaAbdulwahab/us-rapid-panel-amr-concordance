#!/usr/bin/env python3
"""
01b_fetch_amrfinder.py - Download the NCBI Pathogen Detection AMRFinderPlus result tables.

PLAIN-LANGUAGE NOTE: This script downloads the public NCBI tables that list,
for every bacterial genome, which resistance genes AMRFinderPlus found and
(when the submitter provided them) the lab susceptibility results. It keeps
only isolates that have susceptibility results, saves them in data/raw/, and
writes where each file came from into data/raw/PROVENANCE.jsonl.
Run 01a first: this script keeps an isolate if its BioSample has an antibiogram
(from 01a) or if NCBI lists submitter S/I/R calls for it.
You do not need to open this file.

Source: https://ftp.ncbi.nlm.nih.gov/pathogen/Results/<organism group>/latest_snps/AMR/
Each group has one file named PDGxxxxxxxxx.NNNN.amr.metadata.tsv. "latest_snps"
always points to the newest analysis run, so the PDG accession (the run number)
is recorded in the provenance log; that accession pins the exact version used.
"""
import datetime, gzip, hashlib, json, os, re, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
BASE = "https://ftp.ncbi.nlm.nih.gov/pathogen/Results"

# Organism groups in scope. Enterobacterales = every NCBI group in that order
# that is a human pathogen of clinical relevance; non-human hosts are removed in 02.
GROUPS = [
    "Staphylococcus_aureus", "Enterococcus_faecalis", "Enterococcus_faecium",
    "Escherichia_coli_Shigella", "Klebsiella", "Klebsiella_oxytoca",
    "Citrobacter_freundii", "Citrobacter_portucalensis", "Cronobacter",
    "Enterobacter_asburiae", "Enterobacter_bugandensis", "Enterobacter_cancerogenus",
    "Enterobacter_chengduensis", "Enterobacter_chuandaensis", "Enterobacter_cloacae",
    "Enterobacter_hormaechei", "Enterobacter_intestinihominis", "Enterobacter_kobei",
    "Enterobacter_ludwigii", "Enterobacter_mori", "Enterobacter_oligotrophicus",
    "Enterobacter_quasiroggenkampii", "Enterobacter_roggenkampii",
    "Enterobacter_sichuanensis", "Enterobacter_soli",
    "Kluyvera_intermedia", "Morganella", "Providencia", "Serratia",
    "Pluralibacter_gergoviae", "Salmonella",
]


def find_file(group):
    url = f"{BASE}/{group}/latest_snps/AMR/"
    html = urllib.request.urlopen(url, timeout=120).read().decode()
    m = re.search(r'href="(PDG\d+\.\d+\.amr\.metadata\.tsv)"', html)
    if not m:
        raise RuntimeError(f"no amr.metadata.tsv under {url}")
    return url + m.group(1), m.group(1)


def antibiogram_accessions():
    path = os.path.join(RAW, "biosample_antibiograms.xml.gz")
    acc = set()
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            acc.update(re.findall(r'<BioSample [^>]*accession="([^"]+)"', line))
    return acc


def fetch(group, log, keep):
    url, name = find_file(group)
    out = os.path.join(RAW, f"{group}.ast_subset.tsv.gz")
    h = hashlib.sha256()
    nbytes = nrows = nkept = 0
    with urllib.request.urlopen(url, timeout=600) as r, gzip.open(out, "wt", encoding="utf-8") as fo:
        buf = b""
        header = None
        ast_col = None
        while True:
            chunk = r.read(1 << 22)
            if not chunk:
                break
            h.update(chunk)
            nbytes += len(chunk)
            buf += chunk
            lines = buf.split(b"\n")
            buf = lines.pop()
            for ln in lines:
                s = ln.decode("utf-8", "replace")
                if header is None:
                    header = s.split("\t")
                    ast_col = header.index("AST_phenotypes")
                    bs_col = header.index("biosample_acc")
                    fo.write(s + "\n")
                    continue
                nrows += 1
                f = s.split("\t")
                if len(f) > ast_col and (f[ast_col] not in ("NULL", "") or f[bs_col] in keep):
                    fo.write(s + "\n")
                    nkept += 1
        if buf.strip():
            nrows += 1
            f = buf.decode().split("\t")
            if len(f) > ast_col and (f[ast_col] not in ("NULL", "") or f[bs_col] in keep):
                fo.write(buf.decode() + "\n")
                nkept += 1
    rec = {
        "access_date": datetime.date.today().isoformat(),
        "group": group, "source_file": name, "source_url": url,
        "source_bytes": nbytes, "source_sha256": h.hexdigest(),
        "source_rows": nrows, "rows_kept_with_AST_or_antibiogram": nkept,
        "saved_as": os.path.relpath(out, ROOT),
        "terms": "NCBI public data; no restrictions on use (https://www.ncbi.nlm.nih.gov/home/about/policies/)",
    }
    log.write(json.dumps(rec) + "\n")
    log.flush()
    print(group, nrows, nkept, flush=True)
    return rec


if __name__ == "__main__":
    os.makedirs(RAW, exist_ok=True)
    groups = sys.argv[1:] or GROUPS
    keep = antibiogram_accessions()
    print("antibiogram BioSamples:", len(keep), flush=True)
    with open(os.path.join(RAW, "PROVENANCE.jsonl"), "a") as log:
        for g in groups:
            fetch(g, log, keep)
