#!/usr/bin/env python3
"""
03_crosswalk.py - Build the gene-to-panel-target crosswalk.

PLAIN-LANGUAGE NOTE: AMRFinderPlus names genes very precisely (for example
blaKPC-3 or blaOXA-181). Rapid blood culture panels report broader targets
(KPC, OXA-48-like). This script uses NCBI's own gene family tree (the
Reference Gene Hierarchy) to decide which precise gene names belong to which
panel target, and flags any that need care. The result is
reference/gene_panel_crosswalk.csv, one row per gene name.

It also writes reference/gene_mechanism_map.csv, which says for every
AMRFinderPlus gene which drug class it affects. That second file is used to
explain disagreements (for example, a carbapenem-resistant isolate with no
panel carbapenemase but with a different carbapenemase the panel does not test).

Match flags:
  EXACT_TARGET       the gene is the panel target itself (mecA, mecC, vanA, vanB)
  FAMILY_MEMBER      an allele inside the target's family (blaKPC-3 -> KPC)
  FAMILY_UNTYPED     the family was found but the allele was not resolved (blaKPC)
  FAMILY_MEMBER_NONCARBA  OXA-48 family allele that NCBI's catalog does not list as
                     carbapenem-hydrolyzing (e.g. OXA-163, OXA-405); a panel may
                     detect it but carbapenem resistance is not expected
  VARIANT_SUBTYPE    a functional subtype of the target (mecA-ceftar)
Whether a specific allele is detected by a specific commercial panel depends on
the manufacturer's instructions for use and is NOT asserted here.
"""
import csv, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HIER = os.path.join(ROOT, "data", "raw", "ReferenceGeneHierarchy.txt")
OUTX = os.path.join(ROOT, "reference", "gene_panel_crosswalk.csv")
OUTM = os.path.join(ROOT, "reference", "gene_mechanism_map.csv")

# panel target -> AMRFinderPlus hierarchy node that defines it
TARGETS = {
    "mecA": "mecA", "mecC": "mecC", "vanA": "vanA", "vanB": "vanB",
    "KPC": "blaKPC", "NDM": "blaNDM", "OXA-48-like": "blaOXA-48_fam",
    "VIM": "blaVIM", "IMP": "blaIMP", "CTX-M": "blaCTX-M",
}
TARGET_CLASS = {"mecA": "methicillin", "mecC": "methicillin", "vanA": "vancomycin", "vanB": "vancomycin",
                "KPC": "carbapenem", "NDM": "carbapenem", "OXA-48-like": "carbapenem", "VIM": "carbapenem",
                "IMP": "carbapenem", "CTX-M": "extended-spectrum cephalosporin"}


def load():
    rows = {}
    with open(HIER, encoding="utf-8") as f:
        r = csv.DictReader(f, delimiter="\t")
        for d in r:
            rows[d["node_id"]] = d
    return rows


def ancestors(node, rows):
    seen = []
    while node and node in rows and node not in seen:
        seen.append(node)
        node = rows[node]["parent_node_id"]
    return seen


def main():
    rows = load()
    os.makedirs(os.path.dirname(OUTX), exist_ok=True)
    db = next(iter(rows.values()))["db_version"]
    xw = []
    for nid, d in rows.items():
        anc = ancestors(nid, rows)
        for tgt, fam in TARGETS.items():
            if fam not in anc:
                continue
            if nid == fam:
                flag = "EXACT_TARGET" if tgt in ("mecA", "mecC", "vanA", "vanB") else "FAMILY_UNTYPED"
            elif tgt == "OXA-48-like" and d["subclass"] != "CARBAPENEM":
                flag = "FAMILY_MEMBER_NONCARBA"
            elif tgt in ("mecA", "mecC", "vanA", "vanB"):
                flag = "VARIANT_SUBTYPE"
            else:
                flag = "FAMILY_MEMBER"
            xw.append({"amrfinder_symbol": nid, "panel_target": tgt, "target_drug_class": TARGET_CLASS[tgt],
                       "hierarchy_family_node": fam, "match_flag": flag,
                       "catalog_class": d["class"], "catalog_subclass": d["subclass"],
                       "product_name": d["name"], "refgene_db_version": db})
    xw.sort(key=lambda x: (list(TARGETS).index(x["panel_target"]), x["amrfinder_symbol"]))
    with open(OUTX, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(xw[0]))
        w.writeheader()
        w.writerows(xw)
    # mechanism map for every node (used to explain discordance)
    with open(OUTM, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["amrfinder_symbol", "type", "class", "subclass", "product_name", "family_path"])
        for nid, d in sorted(rows.items()):
            w.writerow([nid, d["type"], d["class"], d["subclass"], d["name"], ">".join(ancestors(nid, rows)[:6])])
    from collections import Counter
    print("crosswalk rows:", len(xw), Counter((x["panel_target"], x["match_flag"]) for x in xw))


if __name__ == "__main__":
    main()
