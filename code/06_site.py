#!/usr/bin/env python3
"""
06_site.py - Build the public lookup page (docs/index.html) for GitHub Pages.

PLAIN-LANGUAGE NOTE: Fills the page template with the concordance table and the
version details from paper/stats.json. GitHub Pages serves docs/index.html as
the public website. Run with --final after verification to remove the DRAFT
banner, and pass --doi once Zenodo has issued one.
"""
import argparse, json, os
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = "https://github.com/FatimaAbdulwahab/us-rapid-panel-amr-concordance"

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--final", action="store_true")
    ap.add_argument("--doi", default="DOI to be assigned at release")
    ap.add_argument("--fragment-out", help="also write a body-only copy here (for preview)")
    a = ap.parse_args()
    st = json.load(open(os.path.join(ROOT, "paper", "stats.json")))
    prov = [json.loads(l) for l in open(os.path.join(ROOT, "data", "raw", "PROVENANCE.jsonl"))]
    t = pd.read_csv(os.path.join(ROOT, "data", "processed", "concordance_table.csv"))
    t = t.astype(object).where(pd.notna(t), None)
    tpl = open(os.path.join(ROOT, "code", "site_template.html")).read()
    banner = "" if a.final else ('<div class="draft">DRAFT. These numbers have not yet been checked by the author. '
                                 'Do not cite until the released version.</div>')
    body = (tpl.replace("<!--DRAFT_BANNER-->", banner)
            .replace("__VERSION__", st["release_tag"]).replace("__NBENCH__", f'{st["n_benchmark_isolates"]:,}')
            .replace("__DOI__", a.doi).replace("__REPO__", REPO)
            .replace("__AMRV__", ", ".join(st["amrfinder_versions"]))
            .replace("__DBV__", ", ".join(st["refgene_db_versions"]))
            .replace("__DATE__", max(p["access_date"] for p in prov))
            .replace("__DATA__", json.dumps(t.to_dict("records"), separators=(",", ":"))))
    full = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            + body.split("<style>")[0] + "<style>" + body.split("<style>", 1)[1].split("</style>", 1)[0] +
            "</style>\n</head>\n<body>\n" + body.split("</style>", 1)[1] + "\n</body>\n</html>\n")
    os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
    open(os.path.join(ROOT, "docs", "index.html"), "w").write(full)
    if a.fragment_out:
        open(a.fragment_out, "w").write(body)
    print("wrote docs/index.html", len(full), "bytes")
