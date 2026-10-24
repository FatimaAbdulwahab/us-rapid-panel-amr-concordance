#!/usr/bin/env python3
"""
02_parse_antibiograms.py - Turn the downloaded BioSample XML into one flat table.

PLAIN-LANGUAGE NOTE: Each BioSample record holds descriptive fields (where and
when the sample was collected, the host) plus the antibiogram table. This script
writes one row per isolate per drug to data/processed/antibiogram_long.tsv.gz,
keeping the submitter's value, sign (<=, ==, >), units, method, platform and
testing standard exactly as submitted. Nothing is interpreted yet.
You do not need to open this file.
"""
import csv, gzip, os, re
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "raw", "biosample_antibiograms.xml.gz")
OUT = os.path.join(ROOT, "data", "processed", "antibiogram_long.tsv.gz")

ATTRS = ["geo_loc_name", "host", "isolation_source", "collection_date", "host_disease",
         "isolate", "strain", "collected_by", "lat_lon"]
COLS = ["biosample_acc", "bs_organism", "bs_taxid", "bs_package"] + ["bs_" + a for a in ATTRS] + [
    "antibiotic", "submitted_phenotype", "measurement_sign", "measurement", "measurement_units",
    "lab_typing_method", "lab_typing_platform", "vendor", "method_version", "testing_standard"]


def parse_chunk(text, w, stats):
    root = ET.fromstring(text)
    for bs in root.iter("BioSample"):
        stats["biosamples"] += 1
        acc = bs.get("accession")
        org = bs.find("Description/Organism")
        orgname = org.get("taxonomy_name") if org is not None else ""
        taxid = org.get("taxonomy_id") if org is not None else ""
        pkg = (bs.findtext("Package") or "").strip()
        attrs = {}
        for a in bs.iter("Attribute"):
            k = a.get("harmonized_name") or a.get("attribute_name")
            if k in ATTRS and k not in attrs:
                attrs[k] = (a.text or "").strip()
        base = [acc, orgname, taxid, pkg] + [attrs.get(a, "") for a in ATTRS]
        for tbl in bs.iter("Table"):
            if not (tbl.get("class") or "").startswith("Antibiogram"):
                continue
            hdr = [(c.text or "").strip().lower() for c in tbl.findall("Header/Cell")]
            idx = {h: i for i, h in enumerate(hdr)}
            want = ["antibiotic", "resistance phenotype", "measurement sign", "measurement",
                    "measurement units", "laboratory typing method", "laboratory typing platform",
                    "vendor", "laboratory typing method version or reagent", "testing standard"]
            for row in tbl.findall("Body/Row"):
                cells = [(c.text or "").strip() for c in row.findall("Cell")]
                vals = [cells[idx[k]] if k in idx and idx[k] < len(cells) else "" for k in want]
                w.writerow(base + vals)
                stats["rows"] += 1


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    stats = {"biosamples": 0, "rows": 0}
    with gzip.open(SRC, "rt", encoding="utf-8") as f:
        data = f.read()
    chunks = [c for c in re.split(r"(?=<\?xml )", data) if c.strip()]
    with gzip.open(OUT, "wt", newline="", encoding="utf-8") as fo:
        w = csv.writer(fo, delimiter="\t", lineterminator="\n")
        w.writerow(COLS)
        for c in chunks:
            parse_chunk(c.strip(), w, stats)
    print(stats)


if __name__ == "__main__":
    main()
