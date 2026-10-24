#!/usr/bin/env python3
"""
01a_fetch_antibiograms.py - Download every NCBI BioSample record that carries a
laboratory antibiogram (susceptibility table) for the organisms in scope.

PLAIN-LANGUAGE NOTE: When a laboratory submits a genome to NCBI it can attach a
table of susceptibility results (drug, MIC or zone, method, standard). That table
lives in the "BioSample" record. This script asks NCBI for every BioSample with
such a table for S. aureus, E. faecalis, E. faecium and the Enterobacterales,
downloads them, and logs the query, date and file fingerprint in
data/raw/PROVENANCE.jsonl. You do not need to open this file.

Source: NCBI E-utilities, database "biosample", filter antibiogram[filter].
https://www.ncbi.nlm.nih.gov/books/NBK25499/
"""
import datetime, gzip, hashlib, json, os, re, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
EU = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
QUERY = ('antibiogram[filter] AND ("Staphylococcus aureus"[Organism] OR '
         '"Enterococcus faecalis"[Organism] OR "Enterococcus faecium"[Organism] OR '
         '"Enterobacterales"[Organism])')
BATCH = 200
TOOL = "us-rapid-panel-amr-concordance"


def get(url, data=None, tries=6):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=data)
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.read()
        except Exception as e:  # transient NCBI errors are common; back off
            if i == tries - 1:
                raise
            time.sleep(3 * (i + 1))


def main():
    os.makedirs(RAW, exist_ok=True)
    params = urllib.parse.urlencode({"db": "biosample", "term": QUERY, "usehistory": "y",
                                     "retmax": 0, "tool": TOOL})
    x = get(EU + "esearch.fcgi?" + params).decode()
    count = int(re.search(r"<Count>(\d+)</Count>", x).group(1))
    webenv = re.search(r"<WebEnv>(.*?)</WebEnv>", x).group(1)
    qk = re.search(r"<QueryKey>(\d+)</QueryKey>", x).group(1)
    print("records:", count, flush=True)
    out = os.path.join(RAW, "biosample_antibiograms.xml.gz")
    h = hashlib.sha256()
    n = 0
    with gzip.open(out, "wb") as fo:
        for start in range(0, count, BATCH):
            p = urllib.parse.urlencode({"db": "biosample", "query_key": qk, "WebEnv": webenv,
                                        "retstart": start, "retmax": BATCH, "retmode": "xml",
                                        "tool": TOOL})
            b = get(EU + "efetch.fcgi?" + p)
            h.update(b)
            fo.write(b + b"\n")
            n += b.count(b"<BioSample ")
            print(start, n, flush=True)
            time.sleep(0.4)  # stay under NCBI's 3 requests/second limit
    rec = {"access_date": datetime.date.today().isoformat(), "source": "NCBI BioSample via E-utilities",
           "query": QUERY, "esearch_count": count, "records_downloaded": n,
           "saved_as": os.path.relpath(out, ROOT), "content_sha256": h.hexdigest(),
           "terms": "NCBI public data; https://www.ncbi.nlm.nih.gov/home/about/policies/"}
    with open(os.path.join(RAW, "PROVENANCE.jsonl"), "a") as log:
        log.write(json.dumps(rec) + "\n")
    print(json.dumps(rec))


if __name__ == "__main__":
    main()
