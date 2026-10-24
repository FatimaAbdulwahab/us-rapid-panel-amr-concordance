#!/usr/bin/env python3
"""
01c_fetch_reference.py - Download the AMRFinderPlus reference gene database files.

PLAIN-LANGUAGE NOTE: These are NCBI's official lists of resistance genes, their
families, and the drug classes they affect. The crosswalk (03) is built from
them. The database version is recorded so results can be tied to it.
You do not need to open this file.
"""
import datetime, hashlib, json, os, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
BASE = "https://ftp.ncbi.nlm.nih.gov/pathogen/Antimicrobial_resistance/AMRFinderPlus/database/latest/"
FILES = ["version.txt", "ReferenceGeneCatalog.txt", "ReferenceGeneHierarchy.txt", "AMRProt-mutation.tsv"]

if __name__ == "__main__":
    os.makedirs(RAW, exist_ok=True)
    ver = urllib.request.urlopen(BASE + "version.txt", timeout=120).read().decode().strip()
    with open(os.path.join(RAW, "PROVENANCE.jsonl"), "a") as log:
        for fn in FILES:
            b = urllib.request.urlopen(BASE + fn, timeout=300).read()
            out = os.path.join(RAW, "amrfinder_db_version.txt" if fn == "version.txt" else fn)
            open(out, "wb").write(b)
            rec = {"access_date": datetime.date.today().isoformat(), "source_url": BASE + fn,
                   "refgene_db_version": ver, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest(),
                   "saved_as": os.path.relpath(out, ROOT),
                   "terms": "NCBI public data; https://www.ncbi.nlm.nih.gov/home/about/policies/"}
            log.write(json.dumps(rec) + "\n")
            print(rec)
