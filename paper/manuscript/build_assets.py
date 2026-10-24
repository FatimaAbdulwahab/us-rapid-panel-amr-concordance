#!/usr/bin/env python3
"""
build_assets.py - Write every number, table and figure the preprint uses.

PLAIN-LANGUAGE NOTE: The manuscript (preprint.tex) never contains a typed-in
result. It reads numbers.tex (one macro per number) and the tables/ and figures/
folders, all written here from the verified pipeline outputs in
data/processed/ and paper/stats.json. Re-run this, then compile, after any rebuild.

Usage: python3 paper/manuscript/build_assets.py
"""
import json, math, os, re
from collections import Counter

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PROC = os.path.join(ROOT, "data", "processed")
FIG = os.path.join(HERE, "figures")
TAB = os.path.join(HERE, "tables")
os.makedirs(FIG, exist_ok=True)
os.makedirs(TAB, exist_ok=True)

S = json.load(open(os.path.join(ROOT, "paper", "stats.json")))
T = pd.read_csv(os.path.join(PROC, "concordance_table.csv"))
O = pd.read_csv(os.path.join(PROC, "benchmark_isolates.tsv"), sep="\t", dtype=str, keep_default_na=False)
L = pd.read_csv(os.path.join(PROC, "benchmark_isolate_drug_long.tsv"), sep="\t", dtype=str, keep_default_na=False)
D = pd.read_csv(os.path.join(PROC, "discordance_cases.csv"), dtype=str, keep_default_na=False)
X = pd.read_csv(os.path.join(ROOT, "reference", "gene_panel_crosswalk.csv"), dtype=str)
BP = pd.read_csv(os.path.join(ROOT, "reference", "breakpoints.csv"), dtype=str)
DOIS = json.load(open(os.path.join(ROOT, "zenodo", "dois.json"))) if os.path.exists(
    os.path.join(ROOT, "zenodo", "dois.json")) else {}

ALL = "all U.S. human clinical isolates"
BLOOD = "blood and other sterile-site isolates only"
ENT = "Enterobacterales (excluding Salmonella)"
CARB = "any panel carbapenemase (KPC, NDM, OXA-48-like, VIM, IMP)"
CEPH_ANY = "any of ceftriaxone, cefotaxime, ceftazidime"
TARGETS = ["mecA", "mecC", "vanA", "vanB", "KPC", "NDM", "OXA-48-like", "VIM", "IMP", "CTX-M"]
N = {}  # macro key -> LaTeX string


# ------------------------------------------------------------------ helpers
def fmt_int(n):
    return f"{int(n):,}".replace(",", "{,}")


def pc(x, d=1):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "--"
    v = 100 * float(x)
    s = f"{v:.{d}f}"
    if float(x) < 1 and s == f"{100:.{d}f}":  # never show a bound below 100% as 100.0
        s = f"{math.floor(v * 10 ** (d + 1)) / 10 ** (d + 1):.{d + 1}f}"
    return s + r"\%"


def row(t, d, o, ver="main", sub=ALL):
    x = T[(T.analysis_version == ver) & (T.isolate_subset == sub) & (T.panel_target == t) & (T.drug == d) &
          (T.organism == o)]
    return None if x.empty else x.iloc[0]


def ci(r, m):
    if r is None or pd.isna(r[m]):
        return "--"
    return f"{pc(r[m])} ({pc(r[m + '_lo95'])}--{pc(r[m + '_hi95'])})"


def kfrac(r, m):
    if r is None:
        return "--"
    if m == "ppv":
        return f"{int(r.gene_pos_R)}/{int(r.gene_pos_R + r.gene_pos_notR)}"
    if m == "npv":
        return f"{int(r.gene_neg_notR)}/{int(r.gene_neg_notR + r.gene_neg_R)}"
    if m == "sensitivity":
        return f"{int(r.gene_pos_R)}/{int(r.gene_pos_R + r.gene_neg_R)}"
    return f"{int(r.gene_neg_notR)}/{int(r.gene_neg_notR + r.gene_pos_notR)}"


def put(key, val):
    N[key] = val if isinstance(val, str) else fmt_int(val) if isinstance(val, (int, np.integer)) else str(val)


def put_row(prefix, r):
    """Store n, cells, and each metric with CI for one analysis row."""
    if r is None:
        raise SystemExit(f"missing analysis row for {prefix}")
    put(prefix + "-n", int(r.n))
    for c in ["gene_pos_R", "gene_pos_notR", "gene_neg_R", "gene_neg_notR"]:
        put(prefix + "-" + c.replace("_", ""), int(r[c]))
    put(prefix + "-genepos", int(r.gene_pos_R + r.gene_pos_notR))
    put(prefix + "-geneneg", int(r.gene_neg_R + r.gene_neg_notR))
    for m in ["ppv", "npv", "sensitivity", "specificity"]:
        put(f"{prefix}-{m}", pc(r[m]))
        put(f"{prefix}-{m}-ci", f"{pc(r[m + '_lo95'])}--{pc(r[m + '_hi95'])}")
        put(f"{prefix}-{m}-frac", kfrac(r, m))
    put(prefix + "-agree", pc(r.categorical_agreement))


ORG_SHORT = {"Staphylococcus aureus": r"\textit{S.~aureus}", "Enterococcus faecalis": r"\textit{E.~faecalis}",
             "Enterococcus faecium": r"\textit{E.~faecium}",
             "Enterococcus faecalis + faecium": r"\textit{E.~faecalis} + \textit{E.~faecium}",
             "Escherichia coli": r"\textit{E.~coli}", "Klebsiella pneumoniae complex": r"\textit{K.~pneumoniae} cplx.",
             "Klebsiella oxytoca complex": r"\textit{K.~oxytoca} cplx.", "Klebsiella aerogenes": r"\textit{K.~aerogenes}",
             "Enterobacter cloacae complex": r"\textit{E.~cloacae} cplx.",
             "Citrobacter freundii complex": r"\textit{C.~freundii} cplx.", "Serratia spp.": r"\textit{Serratia} spp.",
             "Morganella / Providencia": r"\textit{Morganella}/\textit{Providencia}",
             "Salmonella enterica": r"\textit{Salmonella enterica}", "Other Enterobacterales": "Other Enterobacterales",
             "Klebsiella, other": r"\textit{Klebsiella}, other", ENT: r"Enterobacterales$^{a}$"}


def tex_table(name, colspec, header, rows, notes=None):
    """APS-style table body: double rules top and bottom, single rule under the header."""
    lines = [r"\begin{tabular}{" + colspec + "}", r"\hline\hline", header + r" \\", r"\hline"]
    for r in rows:
        lines.append(r"\hline" if r == "---" else r + r" \\")
    lines += [r"\hline\hline", r"\end{tabular}"]
    if notes:
        lines.append(r"\par\vspace{2pt}\begin{minipage}{0.97\linewidth}\footnotesize " + notes + r"\end{minipage}")
    open(os.path.join(TAB, name + ".tex"), "w").write("\n".join(lines) + "\n")


# ------------------------------------------------------------------ cohort numbers
for k in ["n_biosamples_with_antibiogram_in_scope_organisms", "n_with_amrfinder_result", "n_us",
          "n_us_excluded_not_human_clinical", "n_us_human_clinical", "n_excluded_reference_strains",
          "n_benchmark_isolates", "n_states", "n_dc", "n_no_state", "n_blood_or_sterile",
          "n_isolate_drug_reinterpreted", "n_isolate_drug_submitter_only", "n_isolate_drug_not_interpretable",
          "n_isolate_drug_mic_off_dilution_series", "n_isolate_drug_mic_rounded_up_from_gradient",
          "n_duplicate_genome_rows_collapsed", "n_isolate_drug_pairs_with_conflicting_repeat_tests",
          "n_discordance_cases", "n_discordant_isolates", "collection_year_min", "collection_year_max",
          "n_missing_year", "n_concordance_rows"]:
    v = S[k]
    put(k.replace("_", "-"), str(v) if k.startswith("collection_year") else int(v))
put("n-nonus", S["n_with_amrfinder_result"] - S["n_us"])
put("n-no-pd", S["n_biosamples_with_antibiogram_in_scope_organisms"] - S["n_with_amrfinder_result"])
put("n-no-paired-drug", S["n_us_human_clinical"] - S["n_excluded_reference_strains"] - S["n_benchmark_isolates"])
put("submitter-agreement", pc(S["submitter_vs_reinterpreted_agreement"]))
put("top-bioproject-share", pc(S["top_bioproject_share"], 0))
tb = list(S["top_bioprojects"].items())
put("top-bioproject-acc", tb[0][0])
put("top-bioproject-n", tb[0][1])
put("n-isolate-drug-total", int(len(L)))
put("n-isolate-drug-mic", int((L.method == "MIC").sum()))
put("n-isolate-drug-disk", int((L.method == "DISK").sum()))
plat = L.platform.replace({"": "not stated", "missing": "not stated"}).value_counts()
for p, n in plat.items():
    put("platform-" + re.sub(r"[^A-Za-z]", "", p).lower(), int(n))
put("pct-phoenix", pc(plat.get("Phoenix", 0) / len(L), 0))
put("pct-vitek", pc(plat.get("Vitek", 0) / len(L), 0))
put("pct-clsi", pc((L.testing_standard == "CLSI").mean(), 1))
for org, n in S["n_by_organism"].items():
    put("org-" + re.sub(r"[^A-Za-z]", "", org).lower(), int(n))
for sp, n in S["n_by_specimen"].items():
    put("spec-" + re.sub(r"[^A-Za-z]", "", sp).lower(), int(n))
put("pct-urine", pc(S["n_by_specimen"]["urine"] / S["n_benchmark_isolates"], 0))
for t in TARGETS:
    put("det-" + t.replace("-", "").lower(), int(S["n_detected"][t]))
put("n-states-total", S["n_states"])
mw = S["mecA_alt_trust_submitter_oxacillin_R"]
put("mecaalt-ppv", pc(mw["ppv"]))
put("mecaalt-frac", f"{mw['gene_pos_R']}/{mw['gene_pos']}")
put("mecaalt-n", len(mw["isolates_affected"]))
put("refstrains", ", ".join(f"{n} ({b})" for b, n in S["excluded_reference_strains"].items()))
put("amrfinder-versions", ", ".join(S["amrfinder_versions"]))
put("refgene-versions", ", ".join(S["refgene_db_versions"]))
put("n-refgene-versions", len(S["refgene_db_versions"]))
put("xw-rows", int(len(X)))
put("xw-oxa-noncarba", int((X.match_flag == "FAMILY_MEMBER_NONCARBA").sum()))
put("xw-oxa-carba", int(((X.panel_target == "OXA-48-like") & (X.match_flag == "FAMILY_MEMBER")).sum()))
put("refgene-db", X.refgene_db_version.iloc[0])
cpn = O[[f"{g}_detected" for g in ["KPC", "NDM", "OXA-48-like", "VIM", "IMP"]]].eq("True").sum(axis=1)
put("n-any-carba", int((cpn >= 1).sum()))
put("n-multi-carba", int((cpn >= 2).sum()))
put("n-carba-kp", int(((cpn >= 1) & (O.organism == "Klebsiella pneumoniae complex")).sum()))
prov = [json.loads(l) for l in open(os.path.join(ROOT, "data", "raw", "PROVENANCE.jsonl"))]
put("access-date", max(p["access_date"] for p in prov))
put("zenodo-doi", (r"\href{https://doi.org/" + DOIS["benchmark"] + "}{" + DOIS["benchmark"] + "}")
    if DOIS.get("benchmark") else "to be assigned on deposit")
put("zenodo-doi-xw", (r"\href{https://doi.org/" + DOIS["crosswalk"] + "}{" + DOIS["crosswalk"] + "}")
    if DOIS.get("crosswalk") else "to be assigned on deposit")
put("zenodo-doi-disc", (r"\href{https://doi.org/" + DOIS["discordance"] + "}{" + DOIS["discordance"] + "}")
    if DOIS.get("discordance") else "to be assigned on deposit")

# ------------------------------------------------------------------ headline analysis rows
HEAD = {
    "meca": ("mecA", "oxacillin or cefoxitin", "Staphylococcus aureus"),
    "meca-ox": ("mecA", "oxacillin", "Staphylococcus aureus"),
    "mecamecc": ("mecA or mecC", "oxacillin or cefoxitin", "Staphylococcus aureus"),
    "van": ("vanA or vanB", "vancomycin", "Enterococcus faecalis + faecium"),
    "vana-fm": ("vanA", "vancomycin", "Enterococcus faecium"),
    "vana-fs": ("vanA", "vancomycin", "Enterococcus faecalis"),
    "kpc-any": ("KPC", "any carbapenem", ENT), "kpc-mero": ("KPC", "meropenem", ENT),
    "ndm-any": ("NDM", "any carbapenem", ENT), "ndm-mero": ("NDM", "meropenem", ENT),
    "oxa-any": ("OXA-48-like", "any carbapenem", ENT), "oxa-mero": ("OXA-48-like", "meropenem", ENT),
    "vim-any": ("VIM", "any carbapenem", ENT), "imp-any": ("IMP", "any carbapenem", ENT),
    "carb-any": (CARB, "any carbapenem", ENT), "carb-mero": (CARB, "meropenem", ENT),
    "carb-erta": (CARB, "ertapenem", ENT), "carb-imi": (CARB, "imipenem", ENT), "carb-dori": (CARB, "doripenem", ENT),
    "carb-any-ec": (CARB, "any carbapenem", "Escherichia coli"),
    "carb-any-kp": (CARB, "any carbapenem", "Klebsiella pneumoniae complex"),
    "carb-any-ecl": (CARB, "any carbapenem", "Enterobacter cloacae complex"),
    "carb-any-kae": (CARB, "any carbapenem", "Klebsiella aerogenes"),
    "carb-mero-ec": (CARB, "meropenem", "Escherichia coli"),
    "carb-mero-kp": (CARB, "meropenem", "Klebsiella pneumoniae complex"),
    "ctx-cro": ("CTX-M", "ceftriaxone", ENT), "ctx-cro-ec": ("CTX-M", "ceftriaxone", "Escherichia coli"),
    "ctx-cro-kp": ("CTX-M", "ceftriaxone", "Klebsiella pneumoniae complex"),
    "ctx-cro-ecl": ("CTX-M", "ceftriaxone", "Enterobacter cloacae complex"),
    "ctx-cro-kae": ("CTX-M", "ceftriaxone", "Klebsiella aerogenes"),
    "ctx-cro-cf": ("CTX-M", "ceftriaxone", "Citrobacter freundii complex"),
    "ctx-cro-sal": ("CTX-M", "ceftriaxone", "Salmonella enterica"),
    "ctx-caz-ec": ("CTX-M", "ceftazidime", "Escherichia coli"),
    "ctx-caz-kp": ("CTX-M", "ceftazidime", "Klebsiella pneumoniae complex"),
    "ctx-caz": ("CTX-M", "ceftazidime", ENT),
    "ctx-ctx": ("CTX-M", "cefotaxime", ENT),
    "ctx-any3": ("CTX-M", CEPH_ANY, ENT),
}
for k, (t, d, o) in HEAD.items():
    put_row(k, row(t, d, o))
# blood-only and excluding-intermediate versions of selected rows
for k in ["meca", "van", "kpc-any", "carb-any", "carb-mero", "ctx-cro", "ctx-cro-ec", "ctx-cro-kp"]:
    t, d, o = HEAD[k]
    r = row(t, d, o, sub=BLOOD)
    if r is not None:
        put_row(k + "-blood", r)
    r = row(t, d, o, ver="sensitivity_excluding_intermediate")
    if r is not None:
        put_row(k + "-exI", r)

# ------------------------------------------------------------------ alleles
ALLELES = {}
for t in TARGETS:
    c = Counter()
    for a in O[f"{t}_alleles"]:  # isolates carrying each allele (an isolate counts once per allele)
        for x in {y.split("=")[0] for y in a.split(";") if y}:
            c[x] += 1
    ALLELES[t] = c
put("ctxm15", ALLELES["CTX-M"]["blaCTX-M-15"])
put("ctxm27", ALLELES["CTX-M"]["blaCTX-M-27"])
put("ctxm14", ALLELES["CTX-M"]["blaCTX-M-14"])
put("kpc3", ALLELES["KPC"]["blaKPC-3"])
put("kpc2", ALLELES["KPC"]["blaKPC-2"])
put("kpc4", ALLELES["KPC"]["blaKPC-4"])
put("ndm1", ALLELES["NDM"]["blaNDM-1"])
put("ndm5", ALLELES["NDM"]["blaNDM-5"])
put("oxa181", ALLELES["OXA-48-like"]["blaOXA-181"])
put("oxa232", ALLELES["OXA-48-like"]["blaOXA-232"])
put("oxa48", ALLELES["OXA-48-like"]["blaOXA-48"])
for t in TARGETS:
    put("partial-" + t.replace("-", "").lower(),
        int(((O[f"{t}_detected"] == "True") & (O[f"{t}_complete"] != "True")).sum()))

# ------------------------------------------------------------------ CTX-M subgroup (secondary analysis)
G1 = {"blaCTX-M-1", "blaCTX-M-3", "blaCTX-M-15", "blaCTX-M-28", "blaCTX-M-32", "blaCTX-M-55", "blaCTX-M-61",
      "blaCTX-M-79", "blaCTX-M-101", "blaCTX-M-174", "blaCTX-M-199"}
G9 = {"blaCTX-M-9", "blaCTX-M-14", "blaCTX-M-24", "blaCTX-M-27", "blaCTX-M-65", "blaCTX-M-102", "blaCTX-M-104",
      "blaCTX-M-174b"}


def ctx_group(a):
    s = {x.split("=")[0] for x in a.split(";") if x}
    a1, a9 = bool(s & G1), bool(s & G9)
    if a1 and a9:
        return "both"
    return "CTX-M-1 group" if a1 else ("CTX-M-9 group" if a9 else "other or untyped")


ctxi = O[O["CTX-M_detected"] == "True"].copy()
ctxi["grp"] = ctxi["CTX-M_alleles"].map(ctx_group)
SUB = []
for org in ["Escherichia coli", "Klebsiella pneumoniae complex"]:
    for g in ["CTX-M-1 group", "CTX-M-9 group"]:
        y = ctxi[(ctxi.organism == org) & (ctxi.grp == g)]
        rec = {"organism": org, "group": g}
        for d in ["ceftriaxone", "cefotaxime", "ceftazidime"]:
            z = y[y[f"{d}_category"].isin(["S", "I", "R", "SDD", "NS"])]
            rec[d] = (int((z[f"{d}_category"] == "R").sum()), int(len(z)))
        SUB.append(rec)
        tag = ("ec" if org.startswith("Esch") else "kp") + ("g1" if "1" in g.split()[0].split("-")[-1] else "g9")
        for d in ["ceftriaxone", "ceftazidime"]:
            k, n = rec[d]
            put(f"sub-{tag}-{d[:6]}", f"{k}/{n}")
            put(f"sub-{tag}-{d[:6]}-pct", pc(k / n) if n else "--")


def fisher_p(a, b, c, d):
    """Two-sided Fisher exact p for [[a,b],[c,d]] (sum of tables at most as likely)."""
    from math import comb
    r1, r2, c1 = a + b, c + d, a + c
    n = r1 + r2

    def p(x):
        return comb(r1, x) * comb(r2, c1 - x) / comb(n, c1)
    p0 = p(a)
    lo, hi = max(0, c1 - r2), min(r1, c1)
    return sum(p(x) for x in range(lo, hi + 1) if p(x) <= p0 * (1 + 1e-9))


e1 = SUB[0]["ceftazidime"]
e9 = SUB[1]["ceftazidime"]
pv = fisher_p(e1[0], e1[1] - e1[0], e9[0], e9[1] - e9[0])
put("sub-ec-fisher", r"$p<10^{-%d}$" % int(-math.floor(math.log10(pv))) if pv < 1e-4 else f"$p={pv:.3f}$")

# ------------------------------------------------------------------ per-enzyme x drug (pooled Enterobacterales)
ENZ = ["KPC", "NDM", "OXA-48-like", "VIM", "IMP"]
DR = ["meropenem", "imipenem", "ertapenem", "doripenem", "any carbapenem"]
for g in ENZ:
    for d in DR:
        r = row(g, d, ENT)
        key = f"enz-{g.replace('-', '').lower()}-{d.split()[0][:4]}"
        put(key, kfrac(r, "ppv") if r is not None and (r.gene_pos_R + r.gene_pos_notR) > 0 else "--")
        put(key + "-pct", pc(r.ppv) if r is not None and not pd.isna(r.ppv) else "--")

# ------------------------------------------------------------------ discordance numbers
dc = D.copy()
dc["cls"] = dc.drug_or_composite.map(lambda d: "methicillin" if "oxacillin" in d else "vancomycin" if d == "vancomycin"
                                       else "carbapenem" if "carbapenem" in d else "cephalosporin")
dc["cause"] = dc.primary_cause.str.replace(r" \(candidates.*", "", regex=True)
put("disc-gp", int((dc.direction == "gene detected, not resistant").sum()))
put("disc-gn", int((dc.direction == "gene not detected, resistant").sum()))
for (cls, dirn), n in dc.groupby(["cls", "direction"]).size().items():
    put(f"disc-{cls[:4]}-{'gp' if dirn.startswith('gene detected') else 'gn'}", int(n))
CAUSE_KEYS = {
    "unexplained by available data": "unexpl",
    "measured value at or within one dilution of the resistant breakpoint": "near",
    "submitter's interpretation differs from current breakpoints": "subdiff",
    "acquired non-CTX-M ESBL or AmpC detected": "acqesbl",
    "organism with chromosomal AmpC (possible derepression)": "ampcorg",
    "panel carbapenemase present (explains cephalosporin resistance)": "carbpres",
    "ESBL or AmpC detected without a called porin change (likely non-carbapenemase mechanism)": "esblnoporin",
    "porin change without ESBL or AmpC (non-carbapenemase mechanism)": "poriononly",
    "ESBL or AmpC plus porin change (non-carbapenemase mechanism)": "esblporin",
    "non-panel carbapenemase detected": "npcarb",
    "vanA operon genes found without a vanA ligase call (possible assembly break)": "vanoperon",
    "chromosomal ampC promoter mutation (AmpC overproduction)": "promoter",
    "phenotype available only as submitter S/I/R call": "subonly",
    "gene call partial or interrupted in the assembly": "partial",
}
for (cls, dirn, cause), n in dc.groupby(["cls", "direction", "cause"]).size().items():
    k = CAUSE_KEYS.get(cause)
    if k:
        put(f"dc-{cls[:4]}-{'gp' if dirn.startswith('gene detected') else 'gn'}-{k}", int(n))
for cause, k in CAUSE_KEYS.items():
    put(f"dctot-{k}", int((dc.cause == cause).sum()))
npc = Counter()
for m in dc[dc.cause == "non-panel carbapenemase detected"].non_panel_mechanisms:
    for x in m.split(";"):
        s = x.split("=")[0]
        if re.match(r"bla(OXA-23|OXA-24|OXA-58|GES|IMI|NMC|SME|FRI|OXA)", s) and "OXA-1" not in s:
            npc[s] += 1
put("npc-genes", ", ".join(f"\\textit{{{k}}}" for k in sorted(npc)) if npc else "none")
gp = dc[dc.direction == "gene detected, not resistant"]
put("gp-meca", int((gp.panel_target == "mecA").sum()))
put("gp-vana", int((gp.panel_target == "vanA").sum()))
put("gp-kpc", int((gp.panel_target == "KPC").sum()))
put("gp-oxa", int((gp.panel_target == "OXA-48-like").sum()))
put("gp-ctxm", int((gp.panel_target == "CTX-M").sum()))
put("vana-s-ids", ", ".join(gp[gp.panel_target == "vanA"].biosample_acc))
put("meca-s-ids", ", ".join(gp[gp.panel_target == "mecA"].biosample_acc))
put("meca-alt-ids", ", ".join(mw["isolates_affected"]))
for cause, k in CAUSE_KEYS.items():
    put(f"gp-{k}", int((gp.cause == cause).sum()))
kpg = dc[(dc.organism == "Klebsiella pneumoniae complex") & (dc.panel_target == "CTX-M") &
         (dc.direction == "gene not detected, resistant") & dc.drug_or_composite.str.startswith("any of")]
put("kp-ctx-gn", int(len(kpg)))
put("kp-ctx-gn-acq", int((kpg.cause == "acquired non-CTX-M ESBL or AmpC detected").sum()))
put("kp-ctx-gn-carb", int((kpg.cause == "panel carbapenemase present (explains cephalosporin resistance)").sum()))
dor = O[O.biosample_acc.isin(L[L.drug == "doripenem"].biosample_acc)]
put("dori-n", int(len(dor)))
put("dori-median-year", str(int(pd.to_numeric(dor.collection_year, errors="coerce").median())))
gnv = dc[(dc.direction == "gene not detected, resistant") & (dc.cls == "vancomycin")]
put("gn-van", int(len(gnv)))
gnm = dc[(dc.direction == "gene not detected, resistant") & (dc.cls == "methicillin")]
put("gn-meca", int(len(gnm)))
put("gn-meca-ids", ", ".join(gnm.biosample_acc))

# ------------------------------------------------------------------ TABLES
# Table: breakpoints
rows = []
for r in BP.itertuples():
    grp = {"Enterobacterales": "Enterobacterales", "Staphylococcus_aureus": r"\textit{S.~aureus}",
           "Enterococcus": r"\textit{Enterococcus} spp."}[r.bp_group]
    s = r.susceptible.replace("<=", r"$\le$").replace(">=", r"$\ge$")
    rr = r.resistant.replace("<=", r"$\le$").replace(">=", r"$\ge$")
    rows.append(f"{grp} & {r.drug} & {'MIC (mg/L)' if r.method == 'MIC' else 'Disk (mm)'} & {s} & {rr} & "
                f"{'I' if r.non_resistant_category_between == 'I' else '--'}")
tex_table("tab_breakpoints", "lllccc", r"Organism group & Agent & Method & S & R & Between", rows)

# Table: crosswalk summary
rows = []
for t in TARGETS:
    x = X[X.panel_target == t]
    fam = x.hierarchy_family_node.iloc[0]
    flags = Counter(x.match_flag)
    obs = ALLELES[t]
    obs_s = ", ".join(f"{a.replace('bla', '')} ({n})" for a, n in obs.most_common(4)) if obs else "none"
    rows.append(f"{t} & \\texttt{{{fam.replace('_', chr(92) + '_')}}} & {len(x)} & "
                f"{flags.get('FAMILY_MEMBER_NONCARBA', 0) or '--'} & {int((O[t + '_detected'] == 'True').sum())} & {obs_s}")
tex_table("tab_crosswalk", "llrrrp{0.36\\linewidth}",
          r"Target & Hierarchy node & Symbols & Non-carba.$^{a}$ & Isolates & Most frequent observed alleles (isolates)", rows)

# Table: cohort characteristics by organism
rows = []
orgs = list(S["n_by_organism"].keys())
for org in orgs:
    y = O[O.organism == org]
    n = len(y)
    bl = int(y.specimen_category.isin(["blood", "other sterile site"]).sum())
    ur = int((y.specimen_category == "urine").sum())
    yrs = pd.to_numeric(y.collection_year, errors="coerce").dropna()
    yr = f"{int(yrs.min())}--{int(yrs.max())}" if len(yrs) else "--"
    st = y.us_state.replace("", np.nan).dropna()
    rows.append(f"{ORG_SHORT.get(org, org)} & {fmt_int(n)} & {fmt_int(bl)} & {fmt_int(ur)} & {yr} & "
                f"{st.nunique()} & {y.bioproject_acc.nunique()}")
rows.append("---")
yrs = pd.to_numeric(O.collection_year, errors="coerce").dropna()
rows.append(f"Total & {fmt_int(len(O))} & {fmt_int(int(O.specimen_category.isin(['blood', 'other sterile site']).sum()))} & "
            f"{fmt_int(int((O.specimen_category == 'urine').sum()))} & {int(yrs.min())}--{int(yrs.max())} & "
            f"{O.us_state.replace('', np.nan).dropna().nunique()} & {O.bioproject_acc.nunique()}")
tex_table("tab_cohort", "lrrrcrr", r"Organism & Isolates & Blood/sterile & Urine & Years & States$^{a}$ & BioProjects",
          rows)

# Table: main concordance
MAIN_ROWS = [
    ("mecA", r"\textit{mecA}", "oxacillin or cefoxitin", "Staphylococcus aureus", "OXA or FOX"),
    ("mecA", r"\textit{mecA}", "oxacillin", "Staphylococcus aureus", "OXA"),
    ("vanA", r"\textit{vanA}", "vancomycin", "Enterococcus faecium", "VAN"),
    ("vanA", r"\textit{vanA}", "vancomycin", "Enterococcus faecalis", "VAN"),
    ("vanA or vanB", r"\textit{vanA}/\textit{vanB}", "vancomycin", "Enterococcus faecalis + faecium", "VAN"),
    ("KPC", "KPC", "any carbapenem", ENT, "Any CBP"),
    ("NDM", "NDM", "any carbapenem", ENT, "Any CBP"),
    ("OXA-48-like", "OXA-48-like", "any carbapenem", ENT, "Any CBP"),
    ("VIM", "VIM", "any carbapenem", ENT, "Any CBP"),
    ("IMP", "IMP", "any carbapenem", ENT, "Any CBP"),
    (CARB, "Any carbapenemase$^{b}$", "any carbapenem", ENT, "Any CBP"),
    (CARB, "Any carbapenemase$^{b}$", "meropenem", ENT, "MEM"),
    ("CTX-M", "CTX-M", "ceftriaxone", "Escherichia coli", "CRO"),
    ("CTX-M", "CTX-M", "ceftriaxone", "Klebsiella pneumoniae complex", "CRO"),
    ("CTX-M", "CTX-M", "ceftriaxone", ENT, "CRO"),
    ("CTX-M", "CTX-M", "ceftriaxone", "Salmonella enterica", "CRO"),
]
rows = []
for t, tl, d, o, dl in MAIN_ROWS:
    r = row(t, d, o)
    rows.append(f"{tl} & {ORG_SHORT.get(o, o)} & {dl} & {fmt_int(r.n)} & {int(r.gene_pos_R)} & {int(r.gene_pos_notR)} & "
                f"{int(r.gene_neg_R)} & {fmt_int(r.gene_neg_notR)} & {ci(r, 'ppv')} & {ci(r, 'npv')} & "
                f"{pc(r.sensitivity)} & {pc(r.specificity)}")
tex_table("tab_main", "lllrrrrrllrr",
          r"Target & Organism & Drug & $n$ & G+R & G+S & G$-$R & G$-$S & PPV (95\% CI) & NPV (95\% CI) & Sens. & Spec.",
          rows)

# Table: carbapenem enzyme x drug PPV
rows = []
for g in ENZ + [CARB]:
    cells = []
    for d in DR:
        r = row(g, d, ENT)
        cells.append("--" if r is None or (r.gene_pos_R + r.gene_pos_notR) == 0 else
                     f"{kfrac(r, 'ppv')} ({pc(r.ppv, 0)})")
    lab = "Any panel enzyme" if g == CARB else g
    rows.append(lab + " & " + " & ".join(cells))
tex_table("tab_carb_drug", "lccccc", r"Target & Meropenem & Imipenem & Ertapenem & Doripenem & Any carbapenem", rows)

# Table: carbapenemase class by organism
rows = []
for o in ["Escherichia coli", "Klebsiella pneumoniae complex", "Enterobacter cloacae complex", "Klebsiella aerogenes",
          "Citrobacter freundii complex", "Serratia spp.", "Morganella / Providencia", ENT]:
    a = row(CARB, "any carbapenem", o)
    m = row(CARB, "meropenem", o)
    rows.append(f"{ORG_SHORT.get(o, o)} & {fmt_int(a.n)} & {int(a.gene_pos_R + a.gene_pos_notR)} & "
                f"{kfrac(a, 'ppv')} & {kfrac(a, 'npv')} & {pc(a.sensitivity)} & "
                f"{kfrac(m, 'ppv') if m is not None else '--'} & {kfrac(m, 'npv') if m is not None else '--'}")
tex_table("tab_carb_org", "lrrllrll",
          r" & \multicolumn{5}{c}{Any carbapenem} & \multicolumn{2}{c}{Meropenem} \\ "
          r"\cline{2-6}\cline{7-8} Organism & $n$ & G+ & PPV & NPV & Sens. & PPV & NPV", rows)

# Table: CTX-M by organism (ceftriaxone) + chromosomal AmpC note
rows = []
for o in ["Escherichia coli", "Klebsiella pneumoniae complex", "Klebsiella oxytoca complex", "Enterobacter cloacae complex",
          "Klebsiella aerogenes", "Citrobacter freundii complex", "Serratia spp.", "Morganella / Providencia",
          "Salmonella enterica", ENT]:
    r = row("CTX-M", "ceftriaxone", o)
    rows.append(f"{ORG_SHORT.get(o, o)} & {fmt_int(r.n)} & {int(r.gene_pos_R + r.gene_pos_notR)} & {ci(r, 'ppv')} & "
                f"{ci(r, 'npv')} & {pc(r.sensitivity)} & {pc(r.specificity)}")
tex_table("tab_ctxm_org", "lrrllrr", r"Organism & $n$ & CTX-M+ & PPV (95\% CI) & NPV (95\% CI) & Sens. & Spec.", rows)

# Table: CTX-M subgroup
rows = []
for rec in SUB:
    cells = [f"{k}/{n} ({pc(k / n, 0)})" if n else "--" for k, n in (rec["ceftriaxone"], rec["cefotaxime"],
                                                                         rec["ceftazidime"])]
    rows.append(f"{ORG_SHORT[rec['organism']]} & {rec['group']} & " + " & ".join(cells))
tex_table("tab_ctxm_sub", "llccc", r"Organism & CTX-M subgroup & Ceftriaxone R & Cefotaxime R & Ceftazidime R", rows)

# Table: sensitivity analyses
rows = []
for k, lab in [("meca", r"\textit{mecA}, \textit{S.~aureus}, OXA/FOX"), ("van", r"\textit{vanA}/\textit{B}, enterococci, VAN"),
               ("kpc-any", "KPC, Enterobacterales, any CBP"), ("carb-any", "Any carbapenemase, any CBP"),
               ("carb-mero", "Any carbapenemase, MEM"), ("ctx-cro-ec", r"CTX-M, \textit{E.~coli}, CRO"),
               ("ctx-cro-kp", r"CTX-M, \textit{K.~pneumoniae} cplx., CRO")]:
    t, d, o = HEAD[k]
    cells = []
    for ver, sub in [("main", ALL), ("sensitivity_excluding_intermediate", ALL), ("main", BLOOD)]:
        r = row(t, d, o, ver=ver, sub=sub)
        cells += ["--", "--", "--"] if r is None else [fmt_int(r.n), pc(r.ppv), pc(r.npv)]
    rows.append(lab + " & " + " & ".join(cells))
tex_table("tab_sensitivity", "lrrrrrrrrr",
          r" & \multicolumn{3}{c}{Main analysis} & \multicolumn{3}{c}{I/SDD excluded} & \multicolumn{3}{c}{Blood/sterile site} \\ "
          r"\cline{2-4}\cline{5-7}\cline{8-10} Analysis & $n$ & PPV & NPV & $n$ & PPV & NPV & $n$ & PPV & NPV", rows)

# Table: discordance causes
CAUSE_LABEL = {
    "unexplained by available data": "Unexplained by available data",
    "measured value at or within one dilution of the resistant breakpoint": "MIC within one dilution of R breakpoint",
    "submitter's interpretation differs from current breakpoints": "Submitter call differs from M100-Ed35",
    "acquired non-CTX-M ESBL or AmpC detected": "Acquired non-CTX-M ESBL or AmpC",
    "organism with chromosomal AmpC (possible derepression)": "Chromosomal AmpC organism",
    "panel carbapenemase present (explains cephalosporin resistance)": "Panel carbapenemase present",
    "ESBL or AmpC detected without a called porin change (likely non-carbapenemase mechanism)": "ESBL/AmpC, no porin call",
    "porin change without ESBL or AmpC (non-carbapenemase mechanism)": "Porin change only",
    "ESBL or AmpC plus porin change (non-carbapenemase mechanism)": "ESBL/AmpC plus porin change",
    "non-panel carbapenemase detected": "Non-panel carbapenemase",
    "vanA operon genes found without a vanA ligase call (possible assembly break)": r"\textit{vanA} operon, no ligase call",
    "chromosomal ampC promoter mutation (AmpC overproduction)": r"\textit{ampC} promoter mutation",
    "phenotype available only as submitter S/I/R call": "Submitter S/I/R call only",
    "gene call partial or interrupted in the assembly": "Partial gene call",
}
CLS = ["methicillin", "vancomycin", "carbapenem", "cephalosporin"]
rows = []
for dirn, lab in [("gene detected, not resistant", "Gene detected, not resistant"),
                  ("gene not detected, resistant", "Gene not detected, resistant")]:
    y = dc[dc.direction == dirn]
    rows.append(r"\multicolumn{6}{l}{\textit{" + lab + "}}")
    order = y.cause.value_counts().index
    for c in order:
        cnt = [int(((y.cause == c) & (y.cls == k)).sum()) for k in CLS]
        rows.append(r"\quad " + CAUSE_LABEL.get(c, c) + " & " + " & ".join(str(v) if v else "--" for v in cnt) +
                    f" & {sum(cnt)}")
    tot = [int((y.cls == k).sum()) for k in CLS]
    rows.append(r"\quad \textit{Subtotal} & " + " & ".join(str(v) for v in tot) + f" & {sum(tot)}")
    rows.append("---")
rows = rows[:-1]
tex_table("tab_discordance", "lrrrrr", r"Primary cause & Methicillin & Vancomycin & Carbapenem & 3GC$^{a}$ & Total", rows)

# Appendix table: every gene-detected, not-resistant case except CTX-M
rows = []
for r in gp[gp.panel_target != "CTX-M"].sort_values(["panel_target", "biosample_acc"]).itertuples():
    det = r.phenotype_detail.replace(" -> ", r" $\rightarrow$ ").replace("<=", r"$\le$").replace(">=", r"$\ge$") \
        .replace("==", "").replace(" mg/L", "").replace("(reinterpreted MIC)", "").replace(
        "(submitter interpretation)", "(sub.)").replace("(reinterpreted DISK)", "(disk)").replace(" | ", "; ")
    det = re.sub(r"(\d)\.0\b", r"\1", det)
    cause = CAUSE_LABEL.get(r.primary_cause.split(" (candidates")[0], r.primary_cause)
    rows.append(f"\\texttt{{{r.biosample_acc}}} & {ORG_SHORT.get(r.organism, r.organism)} & "
                f"{r.target_alleles.replace('bla', '')} & {det} & {cause}")
tex_table("tab_appendix_gp", "lllp{0.30\\linewidth}p{0.20\\linewidth}",
          r"BioSample & Organism & Allele & Phenotype (MIC mg/L or zone mm $\rightarrow$ category) & Primary cause", rows)

# ------------------------------------------------------------------ FIGURES (seaborn, matplotlib)
sns.set_theme(context="paper", style="ticks", font="DejaVu Sans", font_scale=0.95,
              rc={"axes.linewidth": 0.8, "xtick.direction": "in", "ytick.direction": "in", "xtick.top": True,
                  "ytick.right": True, "axes.spines.top": True, "axes.spines.right": True, "legend.frameon": False,
                  "savefig.dpi": 300, "figure.dpi": 150, "pdf.fonttype": 42})
PAL = sns.color_palette("colorblind")
C_PPV, C_NPV, C_POS, C_NEG = PAL[0], PAL[1], PAL[3], PAL[7]
ONE, TWO = 3.4, 7.0


def save(fig, name):
    fig.savefig(os.path.join(FIG, name + ".pdf"), bbox_inches="tight")
    fig.savefig(os.path.join(FIG, name + ".png"), bbox_inches="tight", dpi=200)
    plt.close(fig)


# Fig 1: cohort flow
fig, ax = plt.subplots(figsize=(TWO, 3.1))
ax.set_axis_off()
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
main = [
    (9.2, f"BioSamples with an antibiogram, in-scope organisms\n(NCBI BioSample, worldwide): n = {S['n_biosamples_with_antibiogram_in_scope_organisms']:,}"),
    (7.15, f"With an AMRFinderPlus result in Pathogen Detection\n(one genome per BioSample): n = {S['n_with_amrfinder_result']:,}"),
    (5.1, f"Collected in the United States: n = {S['n_us']:,}"),
    (3.05, f"U.S. human clinical isolates, reference strains removed:\nn = {S['n_us_human_clinical'] - S['n_excluded_reference_strains']:,}"),
    (1.0, f"Benchmark: at least one interpretable result for a panel-paired drug\nn = {S['n_benchmark_isolates']:,}"),
]
side = [
    (8.17, f"No Pathogen Detection result: {S['n_biosamples_with_antibiogram_in_scope_organisms'] - S['n_with_amrfinder_result']:,}"),
    (6.12, f"Outside the United States: {S['n_with_amrfinder_result'] - S['n_us']:,}"),
    (4.07, f"Food, animal, environmental or non-clinical: {S['n_us_excluded_not_human_clinical']:,}\n"
           f"Laboratory reference strains (JE2, LAC): {S['n_excluded_reference_strains']}"),
    (2.02, f"No interpretable panel-paired drug result: "
           f"{S['n_us_human_clinical'] - S['n_excluded_reference_strains'] - S['n_benchmark_isolates']:,}"),
]
for y, txt in main:
    ax.text(3.2, y, txt, ha="center", va="center", fontsize=7.6,
            bbox=dict(boxstyle="round,pad=0.45", fc="white", ec="0.25", lw=0.8))
for (y1, _), (y2, _) in zip(main[:-1], main[1:]):
    ax.annotate("", xy=(3.2, y2 + 0.62), xytext=(3.2, y1 - 0.62),
                arrowprops=dict(arrowstyle="-|>", lw=0.8, color="0.25"))
for y, txt in side:
    ax.annotate("", xy=(6.55, y), xytext=(3.2, y), arrowprops=dict(arrowstyle="-|>", lw=0.8, color="0.25"))
    ax.text(6.65, y, txt, ha="left", va="center", fontsize=7.2,
            bbox=dict(boxstyle="round,pad=0.35", fc="0.95", ec="0.6", lw=0.6))
save(fig, "fig1_flow")

# Fig 2: cohort composition
fig = plt.figure(figsize=(TWO, 2.9))
gsp = fig.add_gridspec(1, 3, width_ratios=[1.55, 0.95, 1], wspace=0.75)
ax = fig.add_subplot(gsp[0])
SPEC = ["blood", "other sterile site", "urine", "respiratory", "wound/tissue", "screening/colonization swab", "stool",
        "other/unspecified"]
orgs_plot = [o for o in S["n_by_organism"] if S["n_by_organism"][o] >= 10]
ct = pd.crosstab(O.organism, O.specimen_category).reindex(index=orgs_plot[::-1], columns=SPEC, fill_value=0)
tot = ct.sum(axis=1)
sh = ct.div(tot, axis=0)
left = np.zeros(len(ct))
spec_pal = sns.color_palette("colorblind", len(SPEC))
for i, sp in enumerate(SPEC):
    ax.barh(range(len(ct)), sh[sp], left=left, color=spec_pal[i], label=sp, height=0.72, edgecolor="white", lw=0.3)
    left += sh[sp].values
for i, n in enumerate(tot):
    ax.text(1.02, i, f"{n:,}", va="center", fontsize=6, color="0.25", transform=ax.get_yaxis_transform())
ax.set_xlim(0, 1)
ax.set_xticks([0, .5, 1])
ax.set_xticklabels(["0", "50", "100"])
ax.tick_params(axis="y", right=False)
ax.set_yticks(range(len(ct)))
ax.set_yticklabels([re.sub(r"\\textit\{(.*?)\}", r"\1", ORG_SHORT.get(o, o)).replace("~", " ").replace("cplx.", "complex")
                    for o in ct.index], fontsize=6.6, style="italic")
ax.set_xlabel("Share of isolates (%); n at right")
ax.set_title("(a) Organism and specimen", fontsize=8, loc="left")
ax.legend(fontsize=5.6, ncol=2, loc="upper center", bbox_to_anchor=(0.45, -0.22), handlelength=1, columnspacing=0.8)
ax = fig.add_subplot(gsp[1])
yy = pd.to_numeric(O.collection_year, errors="coerce").dropna().astype(int)
sns.histplot(yy, discrete=True, color=PAL[0], ax=ax, edgecolor="white", lw=0.3)
ax.set_xlabel("Collection year")
ax.set_ylabel("Isolates")
ax.set_title("(b) Collection year", fontsize=8, loc="left")
ax = fig.add_subplot(gsp[2])
st = O.us_state.replace("", "Not stated").value_counts().head(8)[::-1]
ax.barh(range(len(st)), st.values, color=[PAL[7] if s == "Not stated" else PAL[2] for s in st.index], height=0.7)
ax.set_yticks(range(len(st)))
ax.set_yticklabels([s.replace("District of Columbia", "D.C.$^{*}$") for s in st.index], fontsize=6.6)
ax.tick_params(axis="y", right=False)
ax.set_xlabel("Isolates")
ax.set_title("(c) Submitting state", fontsize=8, loc="left")
save(fig, "fig2_cohort")

# Fig 3: forest plot PPV and NPV
FR = [("mecA", "oxacillin or cefoxitin", "Staphylococcus aureus", "mecA | S. aureus | OXA/FOX"),
      ("vanA", "vancomycin", "Enterococcus faecium", "vanA | E. faecium | VAN"),
      ("vanA", "vancomycin", "Enterococcus faecalis", "vanA | E. faecalis | VAN"),
      ("KPC", "any carbapenem", ENT, "KPC | Enterobacterales | any CBP"),
      ("NDM", "any carbapenem", ENT, "NDM | Enterobacterales | any CBP"),
      ("OXA-48-like", "any carbapenem", ENT, "OXA-48-like | Enterobacterales | any CBP"),
      ("VIM", "any carbapenem", ENT, "VIM | Enterobacterales | any CBP"),
      ("IMP", "any carbapenem", ENT, "IMP | Enterobacterales | any CBP"),
      (CARB, "any carbapenem", ENT, "Any carbapenemase | Enterobacterales | any CBP"),
      (CARB, "meropenem", ENT, "Any carbapenemase | Enterobacterales | MEM"),
      ("CTX-M", "ceftriaxone", "Escherichia coli", "CTX-M | E. coli | CRO"),
      ("CTX-M", "ceftriaxone", "Klebsiella pneumoniae complex", "CTX-M | K. pneumoniae cplx. | CRO"),
      ("CTX-M", "ceftriaxone", ENT, "CTX-M | Enterobacterales | CRO")]
fig, axes = plt.subplots(1, 2, figsize=(TWO, 3.9), sharey=True, gridspec_kw={"wspace": 0.42})
for ax, m, col, title in [(axes[0], "ppv", C_PPV, "(a) Gene detected: share resistant (PPV)"),
                          (axes[1], "npv", C_NPV, "(b) Gene not detected: share not resistant (NPV)")]:
    for i, (t, d, o, lab) in enumerate(FR):
        r = row(t, d, o)
        y = len(FR) - 1 - i
        ax.hlines(y, r[m + "_lo95"], r[m + "_hi95"], color=col, lw=1.6)
        ax.plot(r[m], y, "o", ms=4.8, color=col, mec="white", mew=0.7)
        ax.text(1.02, y, kfrac(r, m), transform=ax.get_yaxis_transform(), va="center", fontsize=6.3, color="0.25")
    ax.set_xlim(0, 1.0)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1])
    ax.set_xticklabels(["0", "25", "50", "75", "100"])
    ax.set_xlabel("Percent (Wilson 95% CI)")
    ax.set_title(title, fontsize=7.8, loc="left")
    ax.grid(axis="x", color="0.9", lw=0.6)
axes[0].set_yticks(range(len(FR)))
axes[0].set_yticklabels([f[3] for f in FR][::-1], fontsize=6.6)
axes[0].set_ylim(-0.6, len(FR) - 0.4)
save(fig, "fig3_forest")

# Fig 4: carbapenemase PPV by drug
fig, ax = plt.subplots(figsize=(ONE, 2.6))
drugs4 = ["meropenem", "imipenem", "ertapenem", "any carbapenem"]
marks = ["o", "s", "D", "^"]
enz4 = ["KPC", "NDM", "OXA-48-like", "VIM", "IMP", CARB]
for j, d in enumerate(drugs4):
    for i, g in enumerate(enz4):
        r = row(g, d, ENT)
        if r is None or (r.gene_pos_R + r.gene_pos_notR) == 0:
            continue
        x = i + (j - 1.5) * 0.17
        ax.vlines(x, r.ppv_lo95, r.ppv_hi95, color=PAL[j], lw=1.1)
        ax.plot(x, r.ppv, marks[j], color=PAL[j], ms=3.8, mec="white", mew=0.5, label=d if i == 0 else None)
ax.set_xticks(range(len(enz4)))
ax.set_xticklabels(["KPC", "NDM", "OXA-48\n-like", "VIM", "IMP", "Any"], fontsize=6.8)
ax.set_ylabel("PPV for resistance (%)")
ax.set_yticks([0, .25, .5, .75, 1])
ax.set_yticklabels(["0", "25", "50", "75", "100"])
ax.set_ylim(0, 1.04)
ax.legend(fontsize=6, ncol=2, loc="lower left")
ax.grid(axis="y", color="0.9", lw=0.6)
save(fig, "fig4_carb_drug")

# Fig 5: CTX-M NPV by organism and CTX-M subgroup ceftazidime
fig, axes = plt.subplots(1, 2, figsize=(TWO, 2.7), gridspec_kw={"width_ratios": [1.35, 1], "wspace": 0.45})
ax = axes[0]
orgs5 = ["Escherichia coli", "Salmonella enterica", "Serratia spp.", "Klebsiella pneumoniae complex",
         "Morganella / Providencia", "Klebsiella oxytoca complex", "Citrobacter freundii complex", "Klebsiella aerogenes",
         "Enterobacter cloacae complex"]
for i, o in enumerate(orgs5):
    r = row("CTX-M", "ceftriaxone", o)
    y = len(orgs5) - 1 - i
    col = PAL[2] if o in ("Escherichia coli", "Salmonella enterica") else (
        PAL[4] if o == "Klebsiella pneumoniae complex" else PAL[7])
    ax.hlines(y, r.npv_lo95, r.npv_hi95, color=col, lw=1.6)
    ax.plot(r.npv, y, "o", color=col, ms=4.8, mec="white", mew=0.6)
    ax.text(1.02, y, kfrac(r, "npv"), transform=ax.get_yaxis_transform(), va="center", fontsize=6.3, color="0.25")
ax.set_yticks(range(len(orgs5)))
ax.set_yticklabels([re.sub(r"\\textit\{(.*?)\}", r"\1", ORG_SHORT[o]).replace("~", " ") for o in orgs5][::-1],
                   fontsize=6.6, style="italic")
ax.set_xlim(0, 1)
ax.set_xticks([0, .25, .5, .75, 1])
ax.set_xticklabels(["0", "25", "50", "75", "100"])
ax.set_xlabel("NPV for ceftriaxone, CTX-M not detected (%)")
ax.set_title("(a) CTX-M-negative isolates", fontsize=7.8, loc="left")
ax.grid(axis="x", color="0.9", lw=0.6)
ax = axes[1]
labs, vals, los, his, cols = [], [], [], [], []
for rec in SUB:
    for d, c in [("ceftriaxone", PAL[0]), ("ceftazidime", PAL[1])]:
        k, n = rec[d]
        if n == 0:
            continue
        z = 1.959964
        p = k / n
        den = 1 + z * z / n
        cc = (p + z * z / (2 * n)) / den
        h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
        labs.append((rec["organism"], rec["group"], d))
        vals.append(p)
        los.append(max(0, cc - h))
        his.append(min(1, cc + h))
        cols.append(c)
xpos = []
x = 0
prev = None
for lab in labs:
    key = lab[:2]
    if prev is not None and key != prev:
        x += 0.6
    xpos.append(x)
    x += 1
    prev = key
ax.bar(xpos, vals, color=cols, width=0.85)
ax.vlines(xpos, los, his, color="0.2", lw=0.8)
groups = {}
for xp, lab in zip(xpos, labs):
    groups.setdefault(lab[:2], []).append(xp)
ax.set_xticks([np.mean(v) for v in groups.values()])
ax.set_xticklabels([("E. coli" if o.startswith("Esch") else "K. pneu.") + "\n" + g.replace(" group", "")
                    for o, g in groups], fontsize=6.4)
ax.set_ylim(0, 1.05)
ax.set_yticks([0, .25, .5, .75, 1])
ax.set_yticklabels(["0", "25", "50", "75", "100"])
ax.set_ylabel("Resistant among CTX-M+ (%)")
ax.set_title("(b) By CTX-M subgroup", fontsize=7.8, loc="left")
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=PAL[0], label="ceftriaxone"), Patch(color=PAL[1], label="ceftazidime")], fontsize=6,
          loc="upper center", bbox_to_anchor=(0.5, -0.24), ncol=2)
ax.set_title("(b) By CTX-M subgroup", fontsize=7.8, loc="left")
save(fig, "fig5_ctxm")


# Fig 6: MIC distributions by gene status
def mic_panel(ax, org_mask, gene_col, drug, title, bp_r, bp_s):
    """Share of isolates per MIC bin on the two-fold scale. Censored readings sit at their bound:
    <=x and >=x at x, <x at x/2, >x at 2x. Gradient half-steps are rounded up first."""
    y = O[org_mask][["biosample_acc", gene_col]]
    z = L[(L.drug == drug) & (L.method == "MIC") & L.biosample_acc.isin(y.biosample_acc)].merge(y, on="biosample_acc")
    z = z[~z.mic_off_dilution_series.eq("True")].copy()
    z["v"] = pd.to_numeric(z.value.str.split("/").str[0], errors="coerce")
    z = z.dropna(subset=["v"])
    z.loc[z.mic_rounded_up_from_gradient.eq("True"), "v"] = 2.0 ** np.ceil(np.log2(z["v"]))
    sign = z.sign.replace({"=": "==", "": "=="})
    k = np.round(np.log2(z.v)).astype(int) + sign.map({"<": -1, ">": 1}).fillna(0).astype(int)
    z["k"] = k
    z["grp"] = np.where(z[gene_col] == "True", "Gene detected", "Gene not detected")
    ks = np.arange(z.k.min(), z.k.max() + 1)
    tab = z.groupby(["grp", "k"]).size().unstack(fill_value=0).reindex(columns=ks, fill_value=0)
    share = tab.div(tab.sum(axis=1), axis=0)
    w = 0.4
    for j, (g, c) in enumerate([("Gene not detected", C_NEG), ("Gene detected", C_POS)]):
        if g in share.index:
            ax.bar(np.arange(len(ks)) + (j - 0.5) * w, share.loc[g].values, width=w, color=c,
                   label=f"{g} (n={int(tab.loc[g].sum()):,})")
    for bpv, ls in [(bp_s, ":"), (bp_r, "--")]:
        xb = list(ks).index(int(round(math.log2(bpv)))) if int(round(math.log2(bpv))) in ks else None
        if xb is not None:
            xline = xb + 0.5 if ls == ":" else xb - 0.5
            ax.axvline(xline, color="0.3", ls=ls, lw=0.8)
    ax.set_xticks(range(len(ks)))
    lab = {0.0625: "0.06", 0.125: "0.12", 0.03125: "0.03", 0.015625: "0.015", 0.0078125: "0.008"}
    ax.set_xticklabels([lab.get(2.0 ** kk, f"{2.0 ** kk:g}") for kk in ks], fontsize=6)
    ax.set_ylim(0, 1.0)
    ax.set_yticks([0, .25, .5, .75, 1])
    ax.set_yticklabels(["0", "25", "50", "75", "100"])
    ax.set_ylabel("Isolates in group (%)")
    ax.set_xlabel(f"{drug.capitalize()} MIC (mg/L)")
    ax.set_title(title, fontsize=7.6, loc="left")
    ax.tick_params(axis="x", top=False)
    ax.legend(fontsize=5.8, loc="upper center" if gene_col == "mecA_detected" else "center", handlelength=1)


fig, axes = plt.subplots(2, 2, figsize=(TWO, 4.4), gridspec_kw={"hspace": 0.55, "wspace": 0.25})
O["any_carb"] = O[[f"{g}_detected" for g in ["KPC", "NDM", "OXA-48-like", "VIM", "IMP"]]].eq("True").any(
    axis=1).map({True: "True", False: "False"})
ent_mask = ~O.organism.isin(["Staphylococcus aureus", "Enterococcus faecalis", "Enterococcus faecium",
                             "Salmonella enterica"])
mic_panel(axes[0, 0], O.organism == "Staphylococcus aureus", "mecA_detected", "oxacillin",
          "(a) S. aureus, oxacillin, by mecA", 4, 2)
mic_panel(axes[0, 1], O.organism.str.startswith("Enterococcus"), "vanA_detected", "vancomycin",
          "(b) Enterococci, vancomycin, by vanA", 32, 4)
mic_panel(axes[1, 0], ent_mask, "any_carb", "meropenem", "(c) Enterobacterales$^{a}$, meropenem", 4, 1)
mic_panel(axes[1, 1], O.organism == "Escherichia coli", "CTX-M_detected", "ceftriaxone",
          "(d) E. coli, ceftriaxone, by CTX-M", 4, 1)
save(fig, "fig6_mic")

# Fig 7: discordance causes by class
fig, axes = plt.subplots(1, 2, figsize=(TWO, 3.0), gridspec_kw={"width_ratios": [0.8, 1.5], "wspace": 0.95})
for ax, dirn, title in [(axes[0], "gene detected, not resistant", "(a) Gene detected, not resistant"),
                        (axes[1], "gene not detected, resistant", "(b) Gene not detected, resistant")]:
    y = dc[dc.direction == dirn]
    ct = pd.crosstab(y.cause.map(lambda c: re.sub(r"\\textit\{(.*?)\}", r"\1", CAUSE_LABEL.get(c, c))), y.cls)
    ct = ct.reindex(columns=[c for c in CLS if c in ct.columns])
    ct = ct.loc[ct.sum(axis=1).sort_values().index]
    left = np.zeros(len(ct))
    for c in ct.columns:
        ax.barh(range(len(ct)), ct[c], left=left, color=PAL[CLS.index(c)], height=0.68,
                label={"cephalosporin": "3rd-gen. cephalosporin"}.get(c, c), edgecolor="white", lw=0.3)
        left += ct[c].values
    for i, v in enumerate(left):
        ax.text(v + max(left) * 0.015, i, str(int(v)), va="center", fontsize=6)
    ax.set_yticks(range(len(ct)))
    ax.set_yticklabels(ct.index, fontsize=6.4)
    ax.tick_params(axis="y", right=False)
    ax.set_xlabel("Discordant isolate-target pairs")
    ax.set_title(title + f" (n={int(left.sum())})", fontsize=7.8, loc="left")
    ax.set_xlim(0, max(left) * 1.15)
h1, l1 = axes[1].get_legend_handles_labels()
h0, l0 = axes[0].get_legend_handles_labels()
hl = dict(zip(l0 + l1, h0 + h1))
fig.legend(hl.values(), hl.keys(), fontsize=6.4, ncol=4, loc="lower center", bbox_to_anchor=(0.5, -0.08))
save(fig, "fig7_discordance")

# Fig 8: robustness (main vs excluding I vs blood)
RB = [("meca", "mecA | S. aureus"), ("van", "vanA/B | enterococci"), ("kpc-any", "KPC | any CBP"),
      ("carb-any", "Any carbapenemase | any CBP"), ("carb-mero", "Any carbapenemase | MEM"),
      ("ctx-cro-ec", "CTX-M | E. coli | CRO"), ("ctx-cro-kp", "CTX-M | K. pneu. | CRO")]
fig, axes = plt.subplots(1, 2, figsize=(TWO, 2.7), sharey=True, gridspec_kw={"wspace": 0.15})
VERS = [("main", ALL, "Main analysis", "o"), ("sensitivity_excluding_intermediate", ALL, "I/SDD excluded", "s"),
        ("main", BLOOD, "Blood/sterile site only", "D")]
for ax, m, title in [(axes[0], "ppv", "(a) PPV"), (axes[1], "npv", "(b) NPV")]:
    for i, (k, lab) in enumerate(RB):
        t, d, o = HEAD[k]
        for j, (ver, sub, vl, mk) in enumerate(VERS):
            r = row(t, d, o, ver=ver, sub=sub)
            if r is None or pd.isna(r[m]):
                continue
            yv = len(RB) - 1 - i + (1 - j) * 0.22
            ax.hlines(yv, r[m + "_lo95"], r[m + "_hi95"], color=PAL[j], lw=1.1)
            ax.plot(r[m], yv, mk, color=PAL[j], ms=3.6, mec="white", mew=0.5, label=vl if i == 0 else None)
    ax.set_xlim(0, 1)
    ax.set_xticks([0, .25, .5, .75, 1])
    ax.set_xticklabels(["0", "25", "50", "75", "100"])
    ax.set_xlabel("Percent (Wilson 95% CI)")
    ax.set_title(title, fontsize=7.8, loc="left")
    ax.grid(axis="x", color="0.9", lw=0.6)
axes[0].set_yticks(range(len(RB)))
axes[0].set_yticklabels([r[1] for r in RB][::-1], fontsize=6.6)
h, l = axes[0].get_legend_handles_labels()
axes[1].legend(h, l, fontsize=6, loc="center left")
save(fig, "fig8_robustness")

# ------------------------------------------------------------------ write numbers.tex
with open(os.path.join(HERE, "numbers.tex"), "w") as f:
    f.write("% Auto-generated by build_assets.py from paper/stats.json and data/processed. Do not edit.\n")
    f.write(r"\makeatletter" + "\n")
    for k, v in sorted(N.items()):
        f.write("\\expandafter\\def\\csname nv@" + k + "\\endcsname{" + str(v) + "}\n")
    f.write(r"\makeatother" + "\n")
json.dump(N, open(os.path.join(HERE, "numbers.json"), "w"), indent=1, sort_keys=True)
print(f"{len(N)} numbers, tables: {len(os.listdir(TAB))}, figures: {len([f for f in os.listdir(FIG) if f.endswith('.pdf')])}")
