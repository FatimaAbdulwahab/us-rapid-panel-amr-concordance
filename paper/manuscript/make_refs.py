#!/usr/bin/env python3
"""
make_refs.py - Build references.tex for the preprint.

PLAIN-LANGUAGE NOTE: Every journal reference is formatted from its Crossref
record (crossref_raw.json, fetched by DOI), so author names, titles, volumes and
pages come from the publisher's registration, not from memory. References are
numbered in the order they are first cited in preprint.tex.
"""
import json, os, re, html

HERE = os.path.dirname(os.path.abspath(__file__))
CR = json.load(open(os.path.join(HERE, "crossref_raw.json")))

MANUAL = {
    "cdc2019": r"Centers for Disease Control and Prevention. \textit{Antibiotic Resistance Threats in the United States, 2019}. "
               r"U.S. Department of Health and Human Services, CDC, Atlanta, GA, 2019. "
               r"\href{https://doi.org/10.15620/cdc:82532}{doi:10.15620/cdc:82532}.",
    "carb2020": r"Federal Task Force on Combating Antibiotic-Resistant Bacteria. \textit{National Action Plan for Combating "
                r"Antibiotic-Resistant Bacteria, 2020--2025}. U.S. Department of Health and Human Services, Washington, DC, 2020. "
                r"\url{https://aspe.hhs.gov/reports/national-action-plan-combating-antibiotic-resistant-bacteria-2020-2025}.",
    "clsi2025": r"Clinical and Laboratory Standards Institute. \textit{Performance Standards for Antimicrobial Susceptibility "
                r"Testing}. CLSI supplement M100, 35th edition. Clinical and Laboratory Standards Institute, Wayne, PA, 2025.",
    "fdastic": r"U.S. Food and Drug Administration. Antibacterial Susceptibility Test Interpretive Criteria. "
               r"\url{https://www.fda.gov/drugs/development-resources/antibacterial-susceptibility-test-interpretive-criteria}. "
               r"Accessed 24 October 2026.",
    "eutils": r"Eric Sayers. A General Introduction to the E-utilities. In \textit{Entrez Programming Utilities Help}. "
              r"National Center for Biotechnology Information, Bethesda, MD. \url{https://www.ncbi.nlm.nih.gov/books/NBK25499/}.",
    "ncbipd": r"National Center for Biotechnology Information. Pathogen Detection. "
              r"\url{https://www.ncbi.nlm.nih.gov/pathogens/}. Data accessed 24 October 2026.",
    "thiswork": r"Fatima Abdulwahab. U.S. Rapid Panel Resistance Marker Concordance Benchmark, version 1.0.0. "
                r"Code and data: \url{https://github.com/FatimaAbdulwahab/us-rapid-panel-amr-concordance}; "
                r"lookup page: \url{https://fatimaabdulwahab.github.io/us-rapid-panel-amr-concordance/}; "
                r"Zenodo archive DOI \nv{zenodo-doi}.",
}


def tex_escape(s):
    s = html.unescape(re.sub(r"<[^>]+>", "", s or ""))
    s = re.sub(r"\s+", " ", s).strip()
    for a, b in [("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("_", r"\_"), ("#", r"\#"), ("$", r"\$"),
                 ("β", r"$\beta$"), ("–", "--"), ("—", "---"), ("’", "'"), ("‘", "`")]:
        s = s.replace(a, b)
    return s


def authors(m):
    au = m.get("author", [])
    names = [tex_escape(f"{a.get('given', '')} {a.get('family', '')}".strip()) for a in au if a.get("family")]
    if not names:
        return ""
    if len(names) > 3:
        return names[0] + " et al."
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + ", and " + names[-1]


def year(m):
    for k in ["published-print", "journal-issue", "issued"]:
        v = m.get(k, {})
        if isinstance(v, dict) and "date-parts" in v:
            return v["date-parts"][0][0]
        if k == "journal-issue" and isinstance(v, dict) and "published-print" in v:
            return v["published-print"]["date-parts"][0][0]
    return ""


def fmt(key):
    if key in MANUAL:
        return MANUAL[key]
    m = CR[key]
    title = tex_escape((m.get("title") or [""])[0])
    title = re.sub(r"(Staphylococcus aureus|Escherichia coli|Klebsiella pneumoniae|Enterococcus faecium|vanA)",
                   r"\\textit{\1}", title)
    jr = tex_escape((m.get("short-container-title") or m.get("container-title") or [""])[0])
    vol = m.get("volume", "")
    iss = m.get("issue", "")
    pg = m.get("page") or m.get("article-number") or ""
    loc = (f"{vol}" + (f"({iss})" if iss else "") + (f":{pg.replace('-', '--')}" if pg else "")) if vol else (
        f"{pg}" if pg else "")
    doi = m["DOI"]
    au = authors(m)
    return (f"{au}{'' if au.endswith('.') else '.'} {title}. \\textit{{{jr}}}, {loc}, {year(m)}. "
            f"\\href{{https://doi.org/{doi}}}{{doi:{tex_escape(doi)}}}").replace(", , ", ", ")


if __name__ == "__main__":
    tex = open(os.path.join(HERE, "preprint.tex")).read()
    tex = re.sub(r"(?m)%.*$", "", tex)
    order = []
    for grp in re.findall(r"\\cite\{([^}]+)\}", tex):
        for k in grp.split(","):
            k = k.strip()
            if k and k not in order:
                order.append(k)
    missing = [k for k in order if k not in CR and k not in MANUAL]
    if missing:
        raise SystemExit(f"cited but not defined: {missing}")
    unused = [k for k in list(CR) + list(MANUAL) if k not in order]
    with open(os.path.join(HERE, "references.tex"), "w") as f:
        f.write("% Auto-generated by make_refs.py from Crossref records (crossref_raw.json). Do not edit.\n")
        f.write("\\begin{thebibliography}{%d}\n" % len(order))
        for k in order:
            f.write(f"\\bibitem{{{k}}} {fmt(k)}\n\n")
        f.write("\\end{thebibliography}\n")
    print(f"{len(order)} references written; unused entries: {unused}")
