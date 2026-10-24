#!/usr/bin/env python3
"""
04_build.py - Build the isolate-level benchmark, the concordance tables and the
discordance case collection.

PLAIN-LANGUAGE NOTE: This is the main analysis. It
  1. keeps U.S. human clinical isolates that have both a genome result and a
     susceptibility result for a drug that matches a panel target,
  2. re-reads every MIC or zone size against the breakpoint table in
     reference/breakpoints.csv (so all isolates are judged by the same rules),
  3. marks which panel targets AMRFinderPlus found in each genome,
  4. counts, for each gene, drug and organism, how often "gene found" went with
     "resistant" and "gene not found" went with "not resistant",
  5. lists every disagreement with its most likely cause.
Outputs land in data/processed/ and paper/stats.json. Every number in the
documents is read from those files. You do not need to open this file; the
codebook (docs/CODEBOOK.md) explains every output column.

Usage: python code/04_build.py [--release-tag v1.0]
"""
import argparse, csv, glob, gzip, json, math, os, re
from collections import Counter, defaultdict
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
PROC = os.path.join(ROOT, "data", "processed")
REF = os.path.join(ROOT, "reference")
PAPER = os.path.join(ROOT, "paper")

# ---------------------------------------------------------------- organism groups
AMPC_ORGS = {"Enterobacter cloacae complex", "Klebsiella aerogenes", "Citrobacter freundii complex",
             "Serratia spp.", "Morganella / Providencia"}


def organism_category(name):
    n = (name or "").lower()
    if n.startswith("staphylococcus aureus"):
        return "Staphylococcus aureus"
    if n.startswith("enterococcus faecalis"):
        return "Enterococcus faecalis"
    if n.startswith("enterococcus faecium"):
        return "Enterococcus faecium"
    if n.startswith("escherichia coli") or n.startswith("shigella"):
        return "Escherichia coli"
    if n.startswith(("klebsiella pneumoniae", "klebsiella quasipneumoniae", "klebsiella variicola",
                     "klebsiella quasivariicola", "klebsiella africana")):
        return "Klebsiella pneumoniae complex"
    if n.startswith(("klebsiella oxytoca", "klebsiella michiganensis", "klebsiella grimontii",
                     "klebsiella pasteurii", "klebsiella huaxiensis", "klebsiella spallanzanii")):
        return "Klebsiella oxytoca complex"
    if n.startswith("klebsiella aerogenes") or n.startswith("enterobacter aerogenes"):
        return "Klebsiella aerogenes"
    if n.startswith("enterobacter"):
        return "Enterobacter cloacae complex"
    if n.startswith("citrobacter"):
        return "Citrobacter freundii complex"
    if n.startswith("serratia"):
        return "Serratia spp."
    if n.startswith(("morganella", "providencia", "proteus")):
        return "Morganella / Providencia"
    if n.startswith("salmonella"):
        return "Salmonella enterica"
    if n.startswith("klebsiella"):
        return "Klebsiella, other"
    return "Other Enterobacterales"


def bp_group(org):
    if org == "Staphylococcus aureus":
        return "Staphylococcus_aureus"
    if org.startswith("Enterococcus"):
        return "Enterococcus"
    return "Enterobacterales"


# ---------------------------------------------------------------- analysis plan
CARBA = ["meropenem", "imipenem", "ertapenem", "doripenem"]
CEPH3 = ["ceftriaxone", "cefotaxime", "ceftazidime"]
PLAN = {  # target set -> (organism family, drugs, composite name, class-level target set)
    "mecA": ("Staphylococcus aureus", ["oxacillin", "cefoxitin"], "oxacillin or cefoxitin", "methicillin"),
    "mecC": ("Staphylococcus aureus", ["oxacillin", "cefoxitin"], "oxacillin or cefoxitin", "methicillin"),
    "vanA": ("Enterococcus", ["vancomycin"], None, "vancomycin"),
    "vanB": ("Enterococcus", ["vancomycin"], None, "vancomycin"),
    "KPC": ("Enterobacterales", CARBA, "any carbapenem", "carbapenem"),
    "NDM": ("Enterobacterales", CARBA, "any carbapenem", "carbapenem"),
    "OXA-48-like": ("Enterobacterales", CARBA, "any carbapenem", "carbapenem"),
    "VIM": ("Enterobacterales", CARBA, "any carbapenem", "carbapenem"),
    "IMP": ("Enterobacterales", CARBA, "any carbapenem", "carbapenem"),
    "CTX-M": ("Enterobacterales", CEPH3, "any of ceftriaxone, cefotaxime, ceftazidime", "extended-spectrum cephalosporin"),
}
CLASS_SETS = {  # class-level "any panel target" sets
    "methicillin": ("mecA or mecC", ["mecA", "mecC"]),
    "vancomycin": ("vanA or vanB", ["vanA", "vanB"]),
    "carbapenem": ("any panel carbapenemase (KPC, NDM, OXA-48-like, VIM, IMP)", ["KPC", "NDM", "OXA-48-like", "VIM", "IMP"]),
    "extended-spectrum cephalosporin": ("CTX-M", ["CTX-M"]),
}
DRUGS_IN_SCOPE = set(["oxacillin", "cefoxitin", "vancomycin"] + CARBA + CEPH3)
INCOMPLETE = ("PARTIAL", "PARTIAL_END_OF_CONTIG", "MISTRANSLATION", "INTERNAL_STOP", "FRAMESHIFT", "NONFUNCTIONAL")

HUMAN_SPECIMEN = re.compile(r"urin|blood|sputum|wound|swab|abscess|tissue|stool|rectal|perirectal|nasal|"
                            r"aspirate|lavage|fluid|bile|drainage|lesion|catheter|csf|clinical|sepsis|"
                            r"respiratory|bronch|tracheal|feces|faeces|throat|groin|axill|skin|bone|joint", re.I)
NONHUMAN_SOURCE = re.compile(r"calf|cattle|bovine|chicken|turkey|pork|swine|beef|retail|meat|food|"
                             r"canine|feline|dog|cat |poultry|equine|horse|deer|environment|water|soil", re.I)


def specimen_category(src):
    s = (src or "").lower()
    if re.search(r"blood|bacteremia|sepsis|bloodstream", s):
        return "blood"
    if re.search(r"csf|cerebrospinal|pleural|peritoneal|synovial|joint|bone|sterile", s):
        return "other sterile site"
    if re.search(r"urin|uti|urinary|bladder|nephrostomy", s):
        return "urine"
    # wound and respiratory come before screening swabs so that "perirectal abscess",
    # "groin wound" and "post-colorectal surgical infection" are not filed as screening swabs
    if re.search(r"sputum|tracheal|bronch|lavage|respiratory|lung|bal\b|pneumon", s):
        return "respiratory"
    if re.search(r"wound|abscess|tissue|skin|lesion|drainage|ulcer|surgical|infection|cellulitis", s):
        return "wound/tissue"
    if re.search(r"rectal|perirectal|nares|nasal|axill|groin|surveillance|screen|colonization", s):
        return "screening/colonization swab"
    if re.search(r"stool|feces|faeces|fecal|diarr|gastro|intestin", s):
        return "stool"
    return "other/unspecified"


# ---------------------------------------------------------------- beta-lactamase classes
# Chromosomal (intrinsic) cephalosporinases by organism; they are not acquired ESBL or AmpC genes.
INTRINSIC_CEPH = {"Escherichia coli": ("blaEC",), "Enterobacter cloacae complex": ("blaACT", "blaMIR"),
                  "Klebsiella aerogenes": ("ampC_Kaer", "blaCMY"), "Citrobacter freundii complex": ("blaCMY", "blaCFE"),
                  "Serratia spp.": ("blaSRT", "blaSST"), "Morganella / Providencia": ("blaDHA", "blaPRC"),
                  "Klebsiella oxytoca complex": ("blaOXY",), "Klebsiella pneumoniae complex": ("blaSHV-1", "blaLEN", "blaOKP")}
# Narrow-spectrum class D enzymes AMRFinderPlus lists under CEPHALOSPORIN; not ESBLs.
NARROW = re.compile(r"^blaOXA-(1|4|30|31|47|10|101|129|240|256)$|^blaOXA-1_fam$|^blaOXA-10_fam$")


def ceph_kind(tok, org):
    sym = tok.split("=")[0]
    if NARROW.match(sym):
        return "narrow"
    for pre in INTRINSIC_CEPH.get(org, ()):
        if sym == pre or sym.startswith(pre + "-") or sym.startswith(pre + "_") or sym.startswith(pre + "="):
            return "intrinsic"
    return "acquired"


# ---------------------------------------------------------------- U.S. location
STATES = {"AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California", "CO": "Colorado",
          "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
          "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
          "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
          "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
          "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
          "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
          "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas",
          "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
          "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia"}
# cities and misspellings seen in submitted geo_loc_name values, resolved to the state named
# elsewhere in the same record or in the submitter's own coordinates
CITY_OR_TYPO = {"boston": "Massachusetts", "houston": "Texas", "detroit": "Michigan", "rochester": "New York",
                "irvine": "California", "cincinnati": "Ohio", "madison": "Wisconsin", "scotsdale": "Arizona",
                "scottsdale": "Arizona", "temple": "Texas", "cleveland": "Ohio", "ann arbor": "Michigan",
                "omaha": "Nebraska", "conneticut": "Connecticut", "bethesa": "Maryland", "bethesda": "Maryland"}


def us_state(geo):
    """Resolve 'USA: <place>' to a state name ('' when no place is given)."""
    rest = re.sub(r"^USA:?\s*", "", geo or "").strip()
    if not rest:
        return ""
    parts = [p.strip() for p in rest.split(",") if p.strip()]
    full = {v.lower(): v for v in STATES.values()}
    for p in reversed(parts):  # the state is usually last ("Detroit, MI", "Ann Arbor, Michigan")
        q = p.lower().strip(". ")
        if q in full:
            return full[q]
        if p.upper() in STATES:
            return STATES[p.upper()]
        if q in CITY_OR_TYPO:
            return CITY_OR_TYPO[q]
    return "unresolved: " + rest


# ---------------------------------------------------------------- reference strains
REFERENCE_STRAINS = re.compile(r"^(JE2|LAC|USA300[ _-]?FPR3757|FPR3757|NCTC[ _-]?8325(-4)?|RN4220|Newman|COL|Mu50|"
                               r"Mu3|N315|MW2|NRS\d+|ATCC[ _-]?\d+|BAA-?\d+|MG1655|K-?12)$", re.I)


# ---------------------------------------------------------------- breakpoints
def load_breakpoints():
    bps = {}
    with open(os.path.join(REF, "breakpoints.csv")) as f:
        for d in csv.DictReader(f):
            s = float(d["susceptible"].lstrip("<=>"))
            r = float(d["resistant"].lstrip("<=>"))
            bps[(d["bp_group"], d["drug"], d["method"])] = (s, r, d["non_resistant_category_between"])
    return bps


def parse_num(x):
    x = (x or "").strip().lstrip(".")  # ".25" handled below
    m = re.match(r"^\s*(\d*\.?\d+)", (x if not x.startswith(".") else "0" + x))
    return float(m.group(1)) if m else None


def num_from(raw):
    raw = (raw or "").strip()
    if raw.startswith("."):
        raw = "0" + raw
    m = re.match(r"^(\d*\.?\d+)", raw)
    return float(m.group(1)) if m else None


def interpret_mic(sign, val, s_bp, r_bp, between):
    """Return S, I, R, or NI (not interpretable) for an MIC with a censoring sign."""
    if val is None:
        return "NI"
    sign = {"=": "==", "": "=="}.get(sign, sign)
    if sign == "==":
        lo = hi = val
    elif sign == "<=":
        lo, hi = 0.0, val
    elif sign == "<":
        lo, hi = 0.0, val / 2.0
    elif sign == ">=":
        lo, hi = val, math.inf
    elif sign == ">":
        lo, hi = val * 2.0, math.inf
    else:
        return "NI"

    def cat(m):
        if m <= s_bp + 1e-9:
            return "S"
        if m >= r_bp - 1e-9:
            return "R"
        return "I" if between == "I" else "NI"
    a, b = cat(lo), cat(hi if hi != math.inf else 1e9)
    return a if a == b else "NI"


def interpret_disk(sign, val, s_bp, r_bp, between):
    if val is None:
        return "NI"
    sign = {"=": "==", "": "=="}.get(sign, sign)
    if sign == "==":
        lo = hi = val
    elif sign in (">=", ">"):
        lo, hi = val, 1e9
    elif sign in ("<=", "<"):
        lo, hi = 0.0, val
    else:
        return "NI"

    def cat(z):
        if z >= s_bp - 1e-9:
            return "S"
        if z <= r_bp + 1e-9:
            return "R"
        return "I" if between == "I" else "NI"
    a, b = cat(lo), cat(hi)
    return a if a == b else "NI"


SUBMITTED = {"resistant": "R", "susceptible": "S", "intermediate": "I", "nonsusceptible": "NS",
             "susceptible-dose dependent": "SDD", "susceptible dose dependent": "SDD"}


STD_DILUTIONS = {0.002, 0.004, 0.008, 0.015, 0.016, 0.03, 0.03125, 0.06, 0.0625, 0.12, 0.125, 0.25, 0.5}


def on_dilution_series(val):
    """True when an MIC value sits on the standard two-fold dilution series.
    Values like 23 or 25 mg/L are not MICs (most likely zone diameters filed with MIC units)."""
    if val is None or val <= 0:
        return False
    if any(abs(val - d) < 1e-6 for d in STD_DILUTIONS):
        return True
    k = math.log2(val)
    return abs(k - round(k)) < 1e-6


GRADIENT_HALF_STEPS = {0.023, 0.047, 0.064, 0.094, 0.19, 0.38, 0.75, 1.5, 3, 6, 12, 24, 48, 96, 192}


def round_up_gradient(val):
    """Gradient-strip (Etest-type) readings fall between two-fold dilutions; CLSI directs rounding
    up to the next two-fold dilution before interpretation. Returns the rounded value or None."""
    if val is None or not any(abs(val - g) < 1e-6 for g in GRADIENT_HALF_STEPS):
        return None
    return 2.0 ** math.ceil(math.log2(val))


def one_dilution_from_R(sign, val, r_bp, method):
    """True when an exactly measured value sits at the resistant breakpoint or one step away."""
    if val is None or sign not in ("==", "=", ""):
        return False
    if method == "MIC":
        return abs(math.log2(val) - math.log2(r_bp)) <= 1.0 + 1e-9
    return abs(val - r_bp) <= 2  # disk: within 2 mm of the resistant breakpoint


# ---------------------------------------------------------------- genes
def load_crosswalk():
    xw = {}
    with open(os.path.join(REF, "gene_panel_crosswalk.csv")) as f:
        for d in csv.DictReader(f):
            xw[d["amrfinder_symbol"]] = (d["panel_target"], d["match_flag"])
    return xw


def load_mechanisms():
    mech = {}
    with open(os.path.join(REF, "gene_mechanism_map.csv")) as f:
        for d in csv.DictReader(f):
            mech[d["amrfinder_symbol"]] = (d["class"], d["subclass"])
    with open(os.path.join(RAW, "AMRProt-mutation.tsv")) as f:
        for d in csv.DictReader(f, delimiter="\t"):
            mech[d["reported_mutation_symbol"]] = (d["class"], d["subclass"])
            mech.setdefault(d["standard_mutation_symbol"], (d["class"], d["subclass"]))
            # gene-level fallback so frameshift and truncation calls not listed one by one
            # (e.g. ompK35_E42RfsTer47) still map to their gene's drug class
            g = d["reported_mutation_symbol"].split("_")[0]
            cls0, sub0 = mech.get("__gene__" + g, ("", ""))
            mech["__gene__" + g] = (d["class"] if not cls0 or cls0 == d["class"] else cls0,
                                    "/".join(sorted(set(filter(None, (sub0 + "/" + d["subclass"]).split("/"))))))
    return mech


def parse_genotypes(s):
    s = (s or "").strip().strip('"')
    if s in ("", "NULL"):
        return []
    out = []
    for tok in s.split(","):
        tok = tok.strip().strip('"')
        if not tok:
            continue
        sym, _, suf = tok.partition("=")
        out.append((sym, suf))
    return out


def mech_of(sym, mech):
    if sym in mech:
        return mech[sym]
    base = sym.split("_")[0]
    return mech.get("__gene__" + base, mech.get(base, ("", "")))


# ---------------------------------------------------------------- statistics
def wilson(k, n, z=1.959964):
    if n == 0:
        return (None, None, None)
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (round(p, 4), round(max(0, c - h), 6), round(min(1, c + h), 6))


def two_by_two(rows):
    tp = sum(1 for g, p in rows if g and p)
    fp = sum(1 for g, p in rows if g and not p)
    fn = sum(1 for g, p in rows if not g and p)
    tn = sum(1 for g, p in rows if not g and not p)
    out = {"n": len(rows), "gene_pos_R": tp, "gene_pos_notR": fp, "gene_neg_R": fn, "gene_neg_notR": tn}
    for name, k, n in [("ppv", tp, tp + fp), ("npv", tn, tn + fn), ("sensitivity", tp, tp + fn),
                       ("specificity", tn, tn + fp)]:
        p, lo, hi = wilson(k, n)
        out[name], out[name + "_lo95"], out[name + "_hi95"] = p, lo, hi
    out["categorical_agreement"] = round((tp + tn) / len(rows), 4) if rows else None
    return out


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--release-tag", default="v1.0")
    args = ap.parse_args()
    os.makedirs(PROC, exist_ok=True)
    os.makedirs(PAPER, exist_ok=True)
    qa = []
    stats = {"release_tag": args.release_tag}

    def note(k, v, text=None):
        stats[k] = v
        qa.append(f"{text or k}: {v}")

    # ---------- AMRFinderPlus isolate rows
    keep_cols = ["target_acc", "biosample_acc", "asm_acc", "scientific_name", "geo_loc_name", "host", "epi_type",
                 "isolation_source", "collection_date", "bioproject_acc", "bioproject_center", "collected_by",
                 "AMR_genotypes", "AST_phenotypes", "amrfinder_version", "refgene_db_version",
                 "amrfinder_analysis_type", "target_creation_date", "attribute_package", "strain"]
    frames = []
    for f in sorted(glob.glob(os.path.join(RAW, "*.ast_subset.tsv.gz"))):
        d = pd.read_csv(f, sep="\t", dtype=str, keep_default_na=False, usecols=lambda c: c in keep_cols)
        d["ncbi_taxgroup"] = os.path.basename(f).split(".")[0]
        frames.append(d)
    iso = pd.concat(frames, ignore_index=True)
    ab = pd.read_csv(os.path.join(PROC, "antibiogram_long.tsv.gz"), sep="\t", dtype=str, keep_default_na=False)
    note("n_biosamples_with_antibiogram_in_scope_organisms", int(ab.biosample_acc.nunique()),
         "BioSamples with an antibiogram (S. aureus, E. faecalis, E. faecium, Enterobacterales), worldwide")
    iso = iso[iso.biosample_acc.isin(set(ab.biosample_acc))]
    note("n_with_amrfinder_result", int(iso.biosample_acc.nunique()),
         "...of which have an AMRFinderPlus result in Pathogen Detection")
    # one genome per BioSample: keep the most recently created analysis target
    dup = iso.biosample_acc.duplicated(keep=False).sum()
    iso = iso.sort_values("target_creation_date").drop_duplicates("biosample_acc", keep="last")
    note("n_duplicate_genome_rows_collapsed", int(dup), "rows sharing a BioSample (collapsed to latest genome)")

    iso["is_us"] = iso.geo_loc_name.str.startswith("USA")
    note("n_us", int(iso.is_us.sum()), "...collected in the USA (geo_loc_name starts with 'USA')")
    iso = iso[iso.is_us].copy()
    host = iso.host.str.lower()
    human_host = host.str.contains("homo sapiens|human|patient", regex=True)
    missing_host = host.isin(["", "null", "missing", "not collected", "not applicable", "unknown", "not provided"])
    src_ok = iso.isolation_source.str.contains(HUMAN_SPECIMEN) & ~iso.isolation_source.str.contains(NONHUMAN_SOURCE)
    iso["human_clinical_rule"] = ""
    iso.loc[(iso.epi_type == "clinical") & human_host, "human_clinical_rule"] = "clinical package, human host"
    iso.loc[(iso.epi_type == "clinical") & missing_host & src_ok, "human_clinical_rule"] = \
        "clinical package, host blank, human specimen source"
    excluded = iso[iso.human_clinical_rule == ""]
    note("n_us_excluded_not_human_clinical", int(len(excluded)),
         "...U.S. isolates excluded as non-clinical or non-human (food, animal, environment)")
    iso = iso[iso.human_clinical_rule != ""].copy()
    note("n_us_human_clinical", int(len(iso)), "...U.S. human clinical isolates")
    iso["organism"] = iso.scientific_name.map(organism_category)
    iso["specimen_category"] = iso.isolation_source.map(specimen_category)
    iso["us_state"] = iso.geo_loc_name.map(us_state)
    iso["location_note"] = ""
    iso.loc[(iso.us_state == "District of Columbia") &
            iso.bioproject_center.str.contains("Walter Reed", case=False), "location_note"] = \
        "submitter location (Walter Reed Army Institute of Research); patient location not given"
    # laboratory reference strains are not clinical isolates
    strain_names = iso.strain.fillna("").str.strip()
    bs_strain = ab.drop_duplicates("biosample_acc").set_index("biosample_acc").bs_strain
    strain_names = strain_names.where(strain_names.ne("") & strain_names.ne("NULL"),
                                      iso.biosample_acc.map(bs_strain).fillna(""))
    ref = strain_names.str.match(REFERENCE_STRAINS)
    stats["excluded_reference_strains"] = {b: n for b, n in zip(iso.biosample_acc[ref], strain_names[ref])}
    note("n_excluded_reference_strains", int(ref.sum()),
         "...laboratory reference strains removed (e.g. JE2, LAC): " +
         ", ".join(f"{b} ({n})" for b, n in stats["excluded_reference_strains"].items()))
    iso = iso[~ref].copy()
    iso["collection_year"] = iso.collection_date.str.extract(r"^(\d{4})")[0]

    # ---------- interpret antibiograms
    bps = load_breakpoints()
    ab = ab[ab.biosample_acc.isin(set(iso.biosample_acc))].copy()
    ab["drug"] = ab.antibiotic.str.lower().str.strip()
    ab = ab[ab.drug.isin(DRUGS_IN_SCOPE)].copy()
    org_of = dict(zip(iso.biosample_acc, iso.organism))
    recs = []
    for r in ab.itertuples(index=False):
        org = org_of[r.biosample_acc]
        g = bp_group(org)
        units = (r.measurement_units or "").lower()
        method = "DISK" if (units == "mm" or "disk" in (r.lab_typing_method or "").lower()) else "MIC"
        val = num_from(r.measurement)
        sign = (r.measurement_sign or "").strip()
        bp = bps.get((g, r.drug, method))
        applicable = bp is not None
        # CLSI: imipenem MICs are intrinsically elevated in Morganellaceae; do not use.
        if r.drug == "imipenem" and org == "Morganella / Providencia":
            applicable = False
        reint = "NA"
        rounded = round_up_gradient(val) if method == "MIC" and not on_dilution_series(val) else None
        if rounded is not None:
            val = rounded
        off_series = method == "MIC" and val is not None and not on_dilution_series(val)
        if applicable:
            fn = interpret_mic if method == "MIC" else interpret_disk
            reint = "NI" if off_series else fn(sign, val, *bp)
        sub = SUBMITTED.get((r.submitted_phenotype or "").lower().strip(), "ND")
        if not applicable:
            final, src = "NA", "drug not applicable to organism"
        elif reint in ("S", "I", "R"):
            final, src = reint, f"reinterpreted {method}"
        elif sub in ("S", "I", "R", "SDD", "NS"):
            final, src = sub, "submitter interpretation"
        else:
            final, src = "NI", "not interpretable"
        borderline = applicable and one_dilution_from_R(sign, val, bp[1], method)
        recs.append({"biosample_acc": r.biosample_acc, "drug": r.drug, "method": method, "sign": sign,
                     "value": r.measurement, "units": r.measurement_units, "platform": r.lab_typing_platform,
                     "vendor": r.vendor, "testing_standard": r.testing_standard,
                     "submitted_phenotype": r.submitted_phenotype, "reinterpreted": reint,
                     "final_category": final, "category_source": src, "near_R_breakpoint": borderline,
                     "mic_off_dilution_series": off_series, "mic_rounded_up_from_gradient": rounded is not None})
    ld = pd.DataFrame(recs)
    # one call per isolate x drug: prefer reinterpreted MIC, then disk, then submitter; flag conflicts
    rank = {"reinterpreted MIC": 0, "reinterpreted DISK": 1, "submitter interpretation": 2,
            "not interpretable": 3, "drug not applicable to organism": 4}
    ld["rank"] = ld.category_source.map(rank)
    sev = {"R": 3, "NS": 2, "I": 1, "SDD": 1, "S": 0}
    conflicts = ld[ld["rank"] <= 1].groupby(["biosample_acc", "drug"]).final_category.nunique()
    note("n_isolate_drug_pairs_with_conflicting_repeat_tests", int((conflicts > 1).sum()),
         "isolate-drug pairs tested twice with different categories (most resistant kept)")
    ld["sev"] = ld.final_category.map(sev).fillna(-1)
    ld = ld.sort_values(["biosample_acc", "drug", "rank", "sev"], ascending=[True, True, True, False])
    best = ld.drop_duplicates(["biosample_acc", "drug"], keep="first").drop(columns=["rank", "sev"])
    # agreement between submitter call and reinterpretation (QA)
    both = best[best.reinterpreted.isin(["S", "I", "R"]) &
                best.submitted_phenotype.str.lower().isin(["susceptible", "intermediate", "resistant"])]
    agree = (both.reinterpreted == both.submitted_phenotype.str.lower().map(SUBMITTED)).mean() if len(both) else None
    note("submitter_vs_reinterpreted_agreement", round(float(agree), 4) if agree is not None else None,
         "share of isolate-drug results where the submitter's S/I/R matches reinterpretation")
    note("n_isolate_drug_mic_off_dilution_series", int(best.mic_off_dilution_series.sum()),
         "isolate-drug MICs not on the two-fold dilution series (likely unit errors; submitter call used)")
    note("n_isolate_drug_mic_rounded_up_from_gradient", int(best.mic_rounded_up_from_gradient.sum()),
         "isolate-drug MICs read from gradient strips (half-steps) rounded up to the next two-fold dilution")
    note("n_isolate_drug_reinterpreted", int(best.category_source.str.startswith("reinterpreted").sum()))
    note("n_isolate_drug_submitter_only", int((best.category_source == "submitter interpretation").sum()))
    note("n_isolate_drug_not_interpretable", int((best.category_source == "not interpretable").sum()))

    # ---------- genes
    xw = load_crosswalk()
    mech = load_mechanisms()
    targets = list(PLAN)
    gene_rows = []
    for r in iso.itertuples(index=False):
        calls = parse_genotypes(r.AMR_genotypes)
        org = r.organism
        d = {"biosample_acc": r.biosample_acc}
        for t in targets:
            hits = [(s, suf) for s, suf in calls if xw.get(s, ("", ""))[0] == t]
            d[f"{t}_detected"] = bool(hits)
            d[f"{t}_complete"] = any(suf.split("_")[0] not in INCOMPLETE and suf not in INCOMPLETE for s, suf in hits)
            d[f"{t}_alleles"] = ";".join(s + ("=" + suf if suf else "") for s, suf in hits)
            d[f"{t}_flags"] = ";".join(sorted({xw[s][1] for s, _ in hits}))
        # non-panel mechanisms by drug class
        other = defaultdict(list)
        panel_syms = set(xw)
        for s, suf in calls:
            if s in panel_syms:
                continue
            cls, sub = mech_of(s, mech)
            tok = s + ("=" + suf if suf else "")
            if "CARBAPENEM" in sub:
                (other["carbapenem_porin_or_point"] if suf == "POINT" else other["carbapenem_gene"]).append(tok)
            if "CEPHALOSPORIN" in sub and suf != "POINT":
                other["cephalosporinase"].append(tok)
                other["ceph_" + ceph_kind(tok, org)].append(tok)
            if "CEPHALOSPORIN" in sub and suf == "POINT" and s.startswith("ampC"):
                other["ampc_promoter_point"].append(tok)
            if "METHICILLIN" in sub:
                other["methicillin"].append(tok)
            if "VANCOMYCIN" in sub or "GLYCOPEPTIDE" in cls:
                other["vancomycin"].append(tok)
        for k in ["carbapenem_gene", "carbapenem_porin_or_point", "cephalosporinase", "ceph_acquired",
                  "ceph_intrinsic", "ceph_narrow", "ampc_promoter_point", "methicillin", "vancomycin"]:
            d[f"other_{k}"] = ";".join(other[k])
        gene_rows.append(d)
    genes = pd.DataFrame(gene_rows)
    iso = iso.merge(genes, on="biosample_acc", how="left")

    # ---------- analysis rows
    pheno = {(b, dr): row for b, dr, row in zip(best.biosample_acc, best.drug, best.to_dict("records"))}

    def is_R(cat):
        return cat in ("R",)

    def usable(cat, exclude_i):
        if cat in ("NA", "NI"):
            return False
        if exclude_i and cat in ("I", "SDD", "NS"):
            return False
        return True

    def org_rows(fam):
        if fam == "Staphylococcus aureus":
            return [("Staphylococcus aureus", iso.organism == "Staphylococcus aureus")]
        if fam == "Enterococcus":
            return [("Enterococcus faecalis", iso.organism == "Enterococcus faecalis"),
                    ("Enterococcus faecium", iso.organism == "Enterococcus faecium"),
                    ("Enterococcus faecalis + faecium", iso.organism.str.startswith("Enterococcus"))]
        ent = ~iso.organism.isin(["Staphylococcus aureus", "Enterococcus faecalis", "Enterococcus faecium"])
        out = [(o, iso.organism == o) for o in sorted(iso[ent].organism.unique())]
        out.append(("Enterobacterales (excluding Salmonella)", ent & (iso.organism != "Salmonella enterica")))
        return out

    def phenotype_for(b, drugs, composite, exclude_i):
        if not composite:
            p = pheno.get((b, drugs[0]))
            if p is None or not usable(p["final_category"], exclude_i):
                return None
            return is_R(p["final_category"])
        cats = [pheno[(b, dr)]["final_category"] for dr in drugs if (b, dr) in pheno]
        cats = [c for c in cats if c not in ("NA", "NI")]
        if not cats:
            return None
        if any(is_R(c) for c in cats):
            return True
        if exclude_i and any(c in ("I", "SDD", "NS") for c in cats):
            return None
        return False

    results, disc = [], []
    subsets = [("all U.S. human clinical isolates", None), ("blood and other sterile-site isolates only",
                                                              iso.specimen_category.isin(["blood", "other sterile site"]))]
    for exclude_i, ver in [(False, "main"), (True, "sensitivity_excluding_intermediate")]:
        for sname, smask in subsets:
            if ver != "main" and smask is not None:
                continue
            analyses = []
            for t, (fam, drugs, comp, cls) in PLAN.items():
                for dr in drugs:
                    analyses.append((t, [t], fam, [dr], dr, False, cls, "gene"))
                if comp:
                    analyses.append((t, [t], fam, drugs, comp, True, cls, "gene"))
            for cls, (label, tset) in CLASS_SETS.items():
                fam, drugs, comp, _ = PLAN[tset[0]]
                for dr in drugs:
                    analyses.append((label, tset, fam, [dr], dr, False, cls, "class"))
                if comp:
                    analyses.append((label, tset, fam, drugs, comp, True, cls, "class"))
            for tlabel, tset, fam, drugs, dlabel, comp, cls, level in analyses:
                if level == "class" and len(tset) == 1:  # CTX-M class row duplicates the gene row
                    continue
                for oname, omask in org_rows(fam):
                    m = omask if smask is None else (omask & smask)
                    sub = iso[m]
                    rows, members = [], []
                    for r in sub.to_dict("records"):
                        p = phenotype_for(r["biosample_acc"], drugs, comp, exclude_i)
                        if p is None:
                            continue
                        g = any(r[f"{x}_detected"] for x in tset)
                        rows.append((g, p))
                        members.append((r, g, p))
                    if not rows:
                        continue
                    res = {"analysis_version": ver, "isolate_subset": sname, "level": level,
                           "panel_target": tlabel, "drug": dlabel, "organism": oname}
                    res.update(two_by_two(rows))
                    results.append(res)
                    # discordance collection: main version, all-isolate subset, per-organism rows only
                    # one record per isolate: use the composite drug row (or the only drug when there is one)
                    if ver != "main" or smask is not None or oname.startswith("Enterobacterales (") \
                            or oname == "Enterococcus faecalis + faecium" or (len(drugs) > 1 and not comp) \
                            or (len(PLAN[tset[0]][1]) > 1 and not comp):
                        continue
                    for r, g, p in members:
                        if level == "gene" and g and not p:
                            disc.append(discord_row(r, "gene detected, not resistant", tlabel, tset, drugs,
                                                    dlabel, comp, pheno, cls))
                        if level == "class" or (level == "gene" and tlabel == "CTX-M"):
                            if (not g) and p:
                                disc.append(discord_row(r, "gene not detected, resistant", tlabel, tset, drugs,
                                                        dlabel, comp, pheno, cls))
    res = pd.DataFrame(results)
    res.to_csv(os.path.join(PROC, "concordance_table.csv"), index=False)
    dd = pd.DataFrame(disc)
    dd.to_csv(os.path.join(PROC, "discordance_cases.csv"), index=False)

    # ---------- isolate-level benchmark table
    wide = best.pivot_table(index="biosample_acc", columns="drug",
                            values=["final_category", "value", "sign", "category_source"], aggfunc="first")
    wide.columns = [f"{d}_{v}".replace("final_category", "category") for v, d in wide.columns]
    out = iso.merge(wide, left_on="biosample_acc", right_index=True, how="left")
    order = (["biosample_acc", "target_acc", "asm_acc", "organism", "scientific_name", "ncbi_taxgroup",
              "us_state", "location_note", "collection_year", "isolation_source", "specimen_category",
              "human_clinical_rule", "strain",
              "bioproject_acc", "bioproject_center", "amrfinder_version", "refgene_db_version"]
             + [c for t in targets for c in (f"{t}_detected", f"{t}_complete", f"{t}_alleles", f"{t}_flags")]
             + [c for c in out.columns if c.startswith("other_")]
             + sorted([c for c in out.columns if any(c.startswith(dr + "_") for dr in DRUGS_IN_SCOPE)])
             + ["AMR_genotypes", "AST_phenotypes"])
    out = out[[c for c in order if c in out.columns]].sort_values(["organism", "biosample_acc"])
    # an isolate is in the benchmark if it has >=1 usable result for a drug paired to its organism's targets
    fam_drugs = {"Staphylococcus aureus": ["oxacillin", "cefoxitin"], "Enterococcus": ["vancomycin"],
                 "Enterobacterales": CARBA + CEPH3}

    def in_bench(r):
        fam = "Staphylococcus aureus" if r.organism == "Staphylococcus aureus" else (
            "Enterococcus" if r.organism.startswith("Enterococcus") else "Enterobacterales")
        return any(pheno.get((r.biosample_acc, dr), {}).get("final_category", "NA") not in ("NA", "NI")
                   for dr in fam_drugs[fam])
    out = out[[in_bench(r) for r in out.itertuples(index=False)]]
    out.to_csv(os.path.join(PROC, "benchmark_isolates.tsv"), sep="\t", index=False)
    best[best.biosample_acc.isin(set(out.biosample_acc))].to_csv(
        os.path.join(PROC, "benchmark_isolate_drug_long.tsv"), sep="\t", index=False)
    note("n_benchmark_isolates", int(len(out)), "isolates in the benchmark (>=1 usable paired drug result)")
    for o, n in out.organism.value_counts().items():
        stats.setdefault("n_by_organism", {})[o] = int(n)
    for s, n in out.specimen_category.value_counts().items():
        stats.setdefault("n_by_specimen", {})[s] = int(n)
    st_vals = out.us_state.fillna("")
    named = st_vals[(st_vals != "") & ~st_vals.str.startswith("unresolved")]
    stats["n_states"] = int(named[named != "District of Columbia"].nunique())
    stats["n_dc"] = int((named == "District of Columbia").sum())
    stats["n_no_state"] = int((st_vals == "").sum())
    stats["n_state_unresolved"] = int(st_vals.str.startswith("unresolved").sum())
    stats["n_location_is_submitter_not_patient"] = int((out.location_note != "").sum())
    stats["n_by_state"] = {k: int(v) for k, v in named.value_counts().items()}
    # Author decision point: mecA-positive S. aureus with a low oxacillin MIC that the submitting lab
    # called resistant (labs may call MRSA from cefoxitin, PBP2a or mecA results). Main rule: MIC only.
    sa = out[out.organism == "Staphylococcus aureus"]
    flip = []
    for b in sa[sa["mecA_detected"]].biosample_acc:
        p = pheno.get((b, "oxacillin"))
        if p and p["final_category"] != "R" and str(p["submitted_phenotype"]).lower() == "resistant":
            flip.append(b)
    h = res[(res.analysis_version == "main") & (res.isolate_subset == "all U.S. human clinical isolates") &
            (res.panel_target == "mecA") & (res.drug == "oxacillin or cefoxitin") &
            (res.organism == "Staphylococcus aureus")].iloc[0]
    k, n = int(h.gene_pos_R) + len(flip), int(h.gene_pos_R + h.gene_pos_notR)
    stats["mecA_alt_trust_submitter_oxacillin_R"] = {
        "isolates_affected": sorted(flip), "ppv": round(k / n, 4), "gene_pos_R": k, "gene_pos": n,
        "rule": "use the submitting lab's 'resistant' call for oxacillin when it disagrees with the MIC"}
    yrs = pd.to_numeric(out.collection_year, errors="coerce").dropna()
    stats["collection_year_min"], stats["collection_year_max"] = int(yrs.min()), int(yrs.max())
    stats["n_missing_year"] = int(out.collection_year.isna().sum() + (out.collection_year == "").sum())
    top = out.bioproject_acc.value_counts().head(5)
    stats["top_bioprojects"] = {k: int(v) for k, v in top.items()}
    stats["top_bioproject_share"] = round(float(top.iloc[0] / len(out)), 4)
    stats["n_blood_or_sterile"] = int(out.specimen_category.isin(["blood", "other sterile site"]).sum())
    stats["amrfinder_versions"] = sorted(out.amrfinder_version.unique().tolist())
    stats["refgene_db_versions"] = sorted(out.refgene_db_version.unique().tolist())
    for t in targets:
        stats.setdefault("n_detected", {})[t] = int(out[f"{t}_detected"].sum())
    stats["n_discordance_cases"] = int(len(dd))
    if len(dd):
        stats["discordance_by_direction"] = {k: int(v) for k, v in dd.direction.value_counts().items()}
        stats["discordance_by_cause"] = {k: int(v) for k, v in dd.primary_cause.value_counts().items()}
        stats["n_discordant_isolates"] = int(dd.biosample_acc.nunique())
    # headline rows for documents
    head = res[(res.analysis_version == "main") & (res.isolate_subset == "all U.S. human clinical isolates")]
    hl = {}
    for (t, dr, o) in [("mecA", "oxacillin or cefoxitin", "Staphylococcus aureus"),
                       ("vanA or vanB", "vancomycin", "Enterococcus faecalis + faecium"),
                       ("vanA", "vancomycin", "Enterococcus faecium"),
                       ("KPC", "meropenem", "Enterobacterales (excluding Salmonella)"),
                       ("KPC", "any carbapenem", "Enterobacterales (excluding Salmonella)"),
                       ("NDM", "any carbapenem", "Enterobacterales (excluding Salmonella)"),
                       ("OXA-48-like", "any carbapenem", "Enterobacterales (excluding Salmonella)"),
                       ("any panel carbapenemase (KPC, NDM, OXA-48-like, VIM, IMP)", "meropenem",
                        "Enterobacterales (excluding Salmonella)"),
                       ("any panel carbapenemase (KPC, NDM, OXA-48-like, VIM, IMP)", "any carbapenem",
                        "Enterobacterales (excluding Salmonella)"),
                       ("CTX-M", "ceftriaxone", "Enterobacterales (excluding Salmonella)"),
                       ("CTX-M", "ceftriaxone", "Escherichia coli"),
                       ("CTX-M", "ceftriaxone", "Klebsiella pneumoniae complex"),
                       ("CTX-M", "ceftriaxone", "Salmonella enterica")]:
        x = head[(head.panel_target == t) & (head.drug == dr) & (head.organism == o)]
        if len(x):
            hl[f"{t} | {dr} | {o}"] = {k: (None if pd.isna(v) else (int(v) if isinstance(v, (int,)) or
                                                                       (hasattr(v, "is_integer") and k in
                                                                        ("n", "gene_pos_R", "gene_pos_notR", "gene_neg_R", "gene_neg_notR"))
                                                                       else v))
                                       for k, v in x.iloc[0].items()}
    stats["headline"] = hl
    stats["n_concordance_rows"] = int(len(res))

    # ---------- QA: spot checks (deterministic picks the author verifies by hand)
    spot = []
    for t, drug in [("mecA", "oxacillin"), ("vanA", "vancomycin"), ("KPC", "meropenem"), ("NDM", "meropenem"),
                    ("CTX-M", "ceftriaxone")]:
        cand = out[out[f"{t}_detected"] & out.get(f"{drug}_category", pd.Series(dtype=str)).notna()]
        if len(cand):
            r = cand.sort_values("biosample_acc").iloc[0]
            spot.append({"biosample_acc": r.biosample_acc, "organism": r.organism, "check_gene": t,
                         "alleles": r[f"{t}_alleles"], "drug": drug, "sign": r.get(f"{drug}_sign"),
                         "value": r.get(f"{drug}_value"), "category": r.get(f"{drug}_category"),
                         "biosample_url": f"https://www.ncbi.nlm.nih.gov/biosample/{r.biosample_acc}",
                         "isolates_browser_url": f"https://www.ncbi.nlm.nih.gov/pathogens/isolates/#{r.biosample_acc}"})
    neg = out[(out.organism == "Escherichia coli") & ~out["CTX-M_detected"] & (out.get("ceftriaxone_category") == "S")]
    if len(neg):
        r = neg.sort_values("biosample_acc").iloc[0]
        spot.append({"biosample_acc": r.biosample_acc, "organism": r.organism, "check_gene": "CTX-M (absent)",
                     "alleles": "", "drug": "ceftriaxone", "sign": r.get("ceftriaxone_sign"),
                     "value": r.get("ceftriaxone_value"), "category": r.get("ceftriaxone_category"),
                     "biosample_url": f"https://www.ncbi.nlm.nih.gov/biosample/{r.biosample_acc}",
                     "isolates_browser_url": f"https://www.ncbi.nlm.nih.gov/pathogens/isolates/#{r.biosample_acc}"})
    stats["spot_checks"] = spot

    # interpretation unit tests (QA): fixed cases with known answers
    assert round_up_gradient(1.5) == 2 and round_up_gradient(0.75) == 1 and round_up_gradient(2) is None
    assert on_dilution_series(0.12) and not on_dilution_series(23)
    tests = [("<=", 0.25, 1, 4, "I", "S"), ("==", 2, 1, 4, "I", "I"), (">", 2, 1, 4, "I", "R"),
             (">", 1, 1, 4, "I", "NI"), ("<=", 2, 1, 4, "I", "NI"), ("==", 4, 2, 4, "none", "R"),
             (">=", 16, 4, 16, "I", "R"), ("<", 0.5, 0.5, 2, "I", "S")]
    unit_ok = all(interpret_mic(s, v, sb, rb, b) == want for s, v, sb, rb, b, want in tests) \
        and interpret_disk("==", 18, 23, 19, "I") == "R" and interpret_disk("==", 25, 23, 19, "I") == "S"
    note("interpretation_unit_tests_pass", bool(unit_ok))

    with open(os.path.join(PAPER, "stats.json"), "w") as f:
        json.dump(stats, f, indent=1, default=str)
    write_qa(qa, stats, res, dd, out, best)
    print("\n".join(qa))


def discord_row(r, direction, tlabel, tset, drugs, dlabel, comp, pheno, cls):
    rd = r
    drug_detail = []
    near = False
    sub_vs_re = False
    submitter_only = True
    for dr in drugs:
        p = pheno.get((r["biosample_acc"], dr))
        if not p or p["final_category"] in ("NA",):
            continue
        drug_detail.append(f"{dr} {p['sign']}{p['value']} {p['units']} -> {p['final_category']} ({p['category_source']})")
        near = near or bool(p["near_R_breakpoint"])
        if p["category_source"].startswith("reinterpreted"):
            submitter_only = False
        sp = SUBMITTED.get((p["submitted_phenotype"] or "").lower(), "ND")
        if p["reinterpreted"] in ("S", "I", "R") and sp in ("S", "I", "R") and sp != p["reinterpreted"]:
            sub_vs_re = True
    causes = []
    if direction == "gene detected, not resistant":
        alle = ";".join(rd[f"{t}_alleles"] for t in tset if rd[f"{t}_alleles"])
        flags = ";".join(rd[f"{t}_flags"] for t in tset if rd[f"{t}_flags"])
        if not any(rd[f"{t}_complete"] for t in tset):
            causes.append("gene call partial or interrupted in the assembly")
        if "FAMILY_MEMBER_NONCARBA" in flags and cls == "carbapenem" and \
                not any("FAMILY_MEMBER_NONCARBA" not in rd[f"{t}_flags"] and rd[f"{t}_detected"] for t in tset):
            causes.append("allele not catalogued as carbapenem-hydrolyzing (OXA-48 family variant)")
        if near:
            causes.append("measured value at or within one dilution of the resistant breakpoint")
        if sub_vs_re:
            causes.append("submitter's interpretation differs from current breakpoints")
        if submitter_only:
            causes.append("phenotype available only as submitter S/I/R call")
        causes.append("unexplained by available data (candidates: low expression, heteroresistance, "
                      "mixed culture, testing or assembly error)")
        other = ""
    else:
        alle, flags = "", ""
        key = {"carbapenem": ["other_carbapenem_gene"], "extended-spectrum cephalosporin": ["other_cephalosporinase"],
               "methicillin": ["other_methicillin"], "vancomycin": ["other_vancomycin"]}[cls]
        other = ";".join(rd[k] for k in key if rd[k])
        if cls == "carbapenem":
            if rd["other_carbapenem_gene"]:
                causes.append("non-panel carbapenemase detected")
            ampc_or_esbl = rd["other_ceph_acquired"] or rd["other_ceph_intrinsic"] or rd["other_ampc_promoter_point"]
            if ampc_or_esbl and rd["other_carbapenem_porin_or_point"]:
                causes.append("ESBL or AmpC plus porin change (non-carbapenemase mechanism)")
            elif ampc_or_esbl:
                causes.append("ESBL or AmpC detected without a called porin change (likely non-carbapenemase mechanism)")
            elif rd["other_carbapenem_porin_or_point"]:
                causes.append("porin change without ESBL or AmpC (non-carbapenemase mechanism)")
            other = ";".join(x for x in [rd["other_carbapenem_gene"], rd["other_carbapenem_porin_or_point"],
                                         rd["other_cephalosporinase"], rd["other_ampc_promoter_point"]] if x)
        elif cls == "extended-spectrum cephalosporin":
            other = ";".join(x for x in [rd["other_cephalosporinase"], rd["other_ampc_promoter_point"]] if x)
            if rd["other_ceph_acquired"]:
                causes.append("acquired non-CTX-M ESBL or AmpC detected")
            if r["organism"] in AMPC_ORGS:
                causes.append("organism with chromosomal AmpC (possible derepression)")
            if rd["other_ampc_promoter_point"]:
                causes.append("chromosomal ampC promoter mutation (AmpC overproduction)")
            if rd["other_ceph_narrow"] and not (rd["other_ceph_acquired"] or rd["other_ampc_promoter_point"]):
                causes.append("only narrow-spectrum beta-lactamases found (OXA-1 or OXA-10 family; not ESBLs)")
            if any(rd[f"{t}_detected"] for t in ["KPC", "NDM", "OXA-48-like", "VIM", "IMP"]):
                causes.append("panel carbapenemase present (explains cephalosporin resistance)")
        else:
            if cls == "vancomycin" and re.search(r"van[A-Z]-A", other or ""):
                causes.append("vanA operon genes found without a vanA ligase call (possible assembly break)")
            elif cls == "methicillin" and re.search(r"mec[IR]", rd.get("AMR_genotypes", "") or ""):
                causes.append("mec regulator genes found without a mecA call (possible assembly break)")
            elif other:
                causes.append(f"non-panel {cls} resistance gene detected")
        if near:
            causes.append("measured value at or within one dilution of the resistant breakpoint")
        if sub_vs_re:
            causes.append("submitter's interpretation differs from current breakpoints")
        if submitter_only:
            causes.append("phenotype available only as submitter S/I/R call")
        causes.append("unexplained by available data (candidates: mechanism not in AMRFinderPlus, "
                      "expression change, testing or assembly error)")
    # carbapenemase present explains ceph R; order matters for primary cause
    if direction == "gene not detected, resistant" and cls == "extended-spectrum cephalosporin":
        pri = [c for c in causes if c.startswith("panel carbapenemase")] or \
              [c for c in causes if not c.startswith("only narrow-spectrum")]
    else:
        pri = causes
    return {"biosample_acc": r["biosample_acc"], "organism": r["organism"], "specimen_category": r["specimen_category"],
            "us_state": r["us_state"], "location_note": r["location_note"], "collection_year": r["collection_year"], "bioproject_acc": r["bioproject_acc"],
            "direction": direction, "panel_target": tlabel, "drug_or_composite": dlabel,
            "target_alleles": alle, "target_flags": flags, "non_panel_mechanisms": other,
            "phenotype_detail": " | ".join(drug_detail), "primary_cause": pri[0],
            "all_applicable_causes": " ; ".join(causes),
            "biosample_url": f"https://www.ncbi.nlm.nih.gov/biosample/{r['biosample_acc']}"}


def write_qa(qa, stats, res, dd, out, best):
    p = os.path.join(PROC, "qa_report.txt")
    with open(p, "w") as f:
        f.write("QA REPORT - U.S. Rapid Panel Resistance Marker Concordance Benchmark\n")
        f.write("PLAIN-LANGUAGE NOTE: Written automatically by code/04_build.py. It shows how many isolates\n"
                "were kept at each step, how results were interpreted, and five isolates to check by hand.\n\n")
        f.write("== Funnel ==\n" + "\n".join(qa) + "\n\n")
        f.write("== Isolates by organism ==\n" + out.organism.value_counts().to_string() + "\n\n")
        f.write("== Isolates by specimen category ==\n" + out.specimen_category.value_counts().to_string() + "\n\n")
        f.write("== Isolates by human-clinical rule ==\n" + out.human_clinical_rule.value_counts().to_string() + "\n\n")
        f.write("== Top BioProjects (concentration check) ==\n" + out.bioproject_acc.value_counts().head(10).to_string() + "\n\n")
        f.write("== Isolate-drug results by interpretation source ==\n" +
                best.groupby(["drug", "category_source"]).size().to_string() + "\n\n")
        f.write("== Panel target detections in benchmark ==\n" +
                "\n".join(f"{k}: {v}" for k, v in stats["n_detected"].items()) + "\n\n")
        f.write("== Sanity checks ==\n")
        ok_rng = all(((res[c].dropna() >= 0) & (res[c].dropna() <= 1)).all() for c in ["ppv", "npv", "sensitivity", "specificity"])
        f.write(f"all proportions within [0,1]: {ok_rng}\n")
        sums = (res.gene_pos_R + res.gene_pos_notR + res.gene_neg_R + res.gene_neg_notR == res.n).all()
        f.write(f"2x2 cells sum to n in every row: {bool(sums)}\n")
        f.write(f"no duplicate BioSamples in benchmark: {not out.biosample_acc.duplicated().any()}\n")
        f.write(f"all benchmark isolates U.S.: {bool(out.us_state.notna().all())}\n\n")
        f.write("== Spot checks (verify each against NCBI by hand) ==\n")
        for s in stats["spot_checks"]:
            f.write(json.dumps(s) + "\n")
        f.write("\n== Discordance cases by primary cause ==\n")
        if len(dd):
            f.write(dd.groupby(["direction", "primary_cause"]).size().to_string() + "\n")


if __name__ == "__main__":
    main()
