#!/usr/bin/env python3
"""
tex2md.py - Convert preprint.tex into Markdown sections for the editable doc version.

PLAIN-LANGUAGE NOTE: The doc version of the preprint is produced from the same
source as the PDF: numbers come from numbers.json, figure/table/citation numbers
from the compiled preprint.aux, tables from tables/*.tex. Nothing is retyped.
Writes docsec/NN_<name>.md, one file per doc section.
Usage: python3 tex2md.py '<json map of figure label -> blob ref>'
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
N = json.load(open(os.path.join(HERE, "numbers.json")))
AUX = open(os.path.join(HERE, "preprint.aux")).read()
BLOBS = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
CITE = dict(re.findall(r"\\bibcite\{([^}]+)\}\{(\d+)\}", AUX))
LABEL = {k: v for k, v in re.findall(r"\\newlabel\{([^}]+)\}\{\{([^}]*)\}", AUX)}
OUT = os.path.join(HERE, "docsec")
os.makedirs(OUT, exist_ok=True)

MACROS = {r"\sau{}": "*S. aureus*", r"\eco{}": "*E. coli*", r"\kpn{}": "*K. pneumoniae*"}


def inline(s):
    s = re.sub(r"\\nv\{([^}]+)\}", lambda m: N[m.group(1)], s)
    for a, b in MACROS.items():
        s = s.replace(a, b)
    s = re.sub(r"\\cite\{([^}]+)\}", lambda m: "[" + ", ".join(CITE[k.strip()] for k in m.group(1).split(",")) + "]", s)
    s = re.sub(r"(Sec|Secs)\.~\\ref\{([^}]+)\}", lambda m: "Sec. " + LABEL.get(m.group(2), "?"), s)
    s = re.sub(r"Fig\.~\\ref\{([^}]+)\}", lambda m: "Fig. " + LABEL.get(m.group(1), "?"), s)
    s = re.sub(r"Figs\.~\\ref\{([^}]+)\}", lambda m: "Figs. " + LABEL.get(m.group(1), "?"), s)
    s = re.sub(r"Table~\\ref\{([^}]+)\}", lambda m: "Table " + LABEL.get(m.group(1), "?"), s)
    s = re.sub(r"\\ref\{([^}]+)\}", lambda m: LABEL.get(m.group(1), "?"), s)
    s = re.sub(r"\\(?:g|textit|emph)\{([^{}]*)\}", r"*\1*", s)
    s = re.sub(r"\\textbf\{([^{}]*)\}", r"**\1**", s)
    s = re.sub(r"\\texttt\{([^{}]*)\}", r"`\1`", s)
    s = re.sub(r"\\url\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\href\{([^}]*)\}\{([^}]*)\}", r"[\2](\1)", s)
    s = re.sub(r"\\textsuperscript\{([^}]*)\}", r"^\1", s)
    s = s.replace(r"$[n(G^{+}R)+n(G^{-}\bar R)]/n$", "[n(G⁺R) + n(G⁻R̄)]/n")
    s = s.replace(r"$\le x$ allows $(0,x]$, $<x$ allows $(0,x/2]$, $\ge x$ allows $[x,\infty)$ and $>x$ allows $[2x,\infty)$",
                  "≤x allows (0, x], <x allows (0, x/2], ≥x allows [x, ∞) and >x allows [2x, ∞)")
    s = s.replace(r"($\le x$ and $\ge x$ at $x$, $<x$ at $x/2$, $>x$ at $2x$)", "(≤x and ≥x at x, <x at x/2, >x at 2x)")
    rep = [(r"$\le$", "≤"), (r"$\ge$", "≥"), (r"$<$", "<"), (r"$>$", ">"), (r"$\beta$", "β"), (r"$\times$", "×"),
           (r"$\rightarrow$", "→"), (r"$2\times 2$", "2×2"), (r"$p<10^{-29}$", "p < 10⁻²⁹"), ("$n$", "n"),
           (r"$-$", "−"), (r"$^{a}$", "ᵃ"), (r"$^{b}$", "ᵇ"), (r"$^{*}$", "†"), (r"\%", "%"), ("~", " "),
           ("``", "“"), ("''", "”"), ("---", "—"), ("--", "–"), (r"\&", "&"), (r"\_", "_"), (r"\,", " "),
           (r"\ ", " "), (r"\quad ", "  "), (r"{,}", ","), ("\\\\", "")]
    for a, b in rep:
        s = s.replace(a, b)
    s = re.sub(r"\$G\^\{\+\}\$", "G⁺", s)
    s = re.sub(r"\$G\^\{-\}\$", "G⁻", s)
    s = re.sub(r"\$\(G\^\{\+\}, G\^\{-\}\)\$", "(G⁺, G⁻)", s)
    s = s.replace("($G^{+}$, $G^{-}$)", "(G⁺, G⁻)").replace("($R$, $\\bar R$)", "(R, R̄)")
    s = s.replace("($R$)", "(R)").replace("($\\bar R$)", "(R̄)")
    s = re.sub(r"\$([^$]*)\$", lambda m: m.group(1).replace("\\", ""), s)
    s = re.sub(r"\\[a-zA-Z]+\*?", "", s) if False else s
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()


def table_md(path):
    t = open(os.path.join(HERE, path)).read()
    body = t[t.index("\\hline", t.index("\\hline\\hline") + 12):t.rindex("\\hline\\hline")]
    head = t[t.index("\\hline\\hline") + 12:t.index("\\hline", t.index("\\hline\\hline") + 12)]
    head = head.strip().rstrip("\\").strip()
    if "\\multicolumn" in head:  # two-row header: keep the second row, prefix group names
        parts = head.split("\\\\")
        groups = re.findall(r"\\multicolumn\{(\d+)\}\{[^}]*\}\{([^}]*)\}", parts[0])
        second = re.sub(r"\\cline\{[^}]*\}", "", parts[1]).split("&")
        cols = [inline(c) for c in second]
        i = 1
        for span, name in groups:
            for j in range(int(span)):
                if i < len(cols):
                    cols[i] = f"{inline(name)}: {cols[i]}"
                    i += 1
    else:
        cols = [inline(c) for c in head.split("&")]
    rows = []
    for line in body.split("\n"):
        line = line.strip()
        if not line or line == "\\hline":
            continue
        line = line.rstrip("\\").strip()
        m = re.match(r"\\multicolumn\{\d+\}\{l\}\{(.*)\}$", line)
        if m:
            rows.append(["**" + inline(m.group(1)) + "**"] + [""] * (len(cols) - 1))
            continue
        cells = [inline(c) for c in line.split("&")]
        rows.append(cells + [""] * (len(cols) - len(cells)))
    md = "| " + " | ".join(cols) + " |\n| " + " | ".join(["---"] * len(cols)) + " |\n"
    for r in rows:
        md += "| " + " | ".join(c.replace("|", "/") for c in r[:len(cols)]) + " |\n"
    return md


def env_block(m):
    kind, inner = m.group(1), m.group(2)
    cap = re.search(r"\\caption\{(.*?)\}\s*\n\\label", inner, re.S)
    lab = re.search(r"\\label\{([^}]+)\}", inner).group(1)
    caption = inline(cap.group(1).replace("\n", " ")) if cap else ""
    num = LABEL.get(lab, "?")
    note = re.search(r"\\parbox\{[^}]*\}\{\\footnotesize (.*?)\}\s*$", inner.strip(), re.S)
    notes = "\n\nNote: " + inline(note.group(1).replace("\n", " ")) if note else ""
    if kind.startswith("figure"):
        f = re.search(r"figures/([a-z0-9_]+)\.pdf", inner).group(1)
        return f"\n\n![Fig. {num}]({BLOBS[f]})\n\n**Fig. {num}.** {caption}\n\n"
    tab = re.search(r"\\input\{(tables/[a-z_]+)\.tex\}", inner)
    if tab:
        return f"\n\n**Table {num}.** {caption}\n\n{table_md(tab.group(1) + '.tex')}{notes}\n\n"
    # inline tabular (Table of panel pairs)
    tb = inner[inner.index("\\begin{tabular}"):inner.index("\\end{tabular}")]
    tb = tb.split("\n", 1)[1].replace("\\hline", "")
    lines = [re.sub(r"\s+", " ", l).strip() for l in tb.split("\\\\") if l.strip()]
    hdr = [inline(c) for c in lines[0].split("&")]
    md = "| " + " | ".join(hdr) + " |\n| " + " | ".join(["---"] * len(hdr)) + " |\n"
    foot = []
    for l in lines[1:]:
        if l.startswith("\\multicolumn"):
            foot.append(inline(re.sub(r"\\multicolumn\{\d+\}\{l\}\{", "", l)[:-1]))
            continue
        cs = [inline(c) for c in l.split("&")]
        md += "| " + " | ".join(cs) + " |\n"
    return f"\n\n**Table {num}.** {caption}\n\n{md}\n" + ("\n\n".join(f"Note: {x}" for x in foot)) + "\n\n"


def convert(body):
    body = re.sub(r"(?m)^%.*\n", "", body)
    body = re.sub(r"\\begin\{(figure\*?|table\*?)\}(?:\[[^\]]*\])?(.*?)\\end\{\1\}", env_block, body, flags=re.S)
    body = re.sub(r"\\begin\{align\}(.*?)\\end\{align\}", lambda m: "\n\n```latex\n\\begin{aligned}\n" + re.sub(
        r"\\label\{[^}]*\}", "", m.group(1)).strip() + "\n\\end{aligned}\n```\n\n", body, flags=re.S)
    body = re.sub(r"\\begin\{equation\}(.*?)\\end\{equation\}", lambda m: "\n\n```latex\n" + re.sub(
        r"\\label\{[^}]*\}", "", m.group(1)).strip() + "\n```\n\n", body, flags=re.S)
    body = re.sub(r"\\begin\{enumerate\}\[[^\]]*\]", "", body).replace("\\end{enumerate}", "")
    body = re.sub(r"\\item\s*", "\n1. ", body)
    body = re.sub(r"\\subsection\{([^}]*)\}(\\label\{[^}]*\})?", lambda m: "\n\n### " + inline(m.group(1)) + "\n\n", body)
    body = re.sub(r"\\subsubsection\{((?:[^{}]|\{[^{}]*\})*)\}", lambda m: "\n\n#### " + inline(m.group(1)) + "\n\n", body)
    body = re.sub(r"\\addcontentsline\{[^}]*\}\{[^}]*\}\{[^}]*\}", "", body)
    # protect code blocks and pre-built blocks from inline()
    keep = []

    def stash(m):
        keep.append(m.group(0))
        return f"@@K{len(keep) - 1}@@"
    body = re.sub(r"```latex.*?```", stash, body, flags=re.S)
    body = re.sub(r"\n\n(?:!\[|\*\*(?:Fig|Table) ).*?(?=\n\n(?![|*!])|\Z)", stash, body, flags=re.S)
    paras = [p for p in re.split(r"\n\s*\n", body)]
    out = []
    for p in paras:
        p = p.strip()
        if not p:
            continue
        if p.startswith("@@K") or p.startswith("#"):
            out.append(p if p.startswith("@@K") else p)
        else:
            out.append(inline(p.replace("\n", " ")))
    md = "\n\n".join(out)
    for i, k in enumerate(keep):
        md = md.replace(f"@@K{i}@@", k.strip())
    return re.sub(r"\n{3,}", "\n\n", md).strip() + "\n"


if __name__ == "__main__":
    tex = open(os.path.join(HERE, "preprint.tex")).read()
    doc = tex[tex.index("\\begin{document}"):]
    # title block + abstract
    ab = doc[doc.index("\\small\nRapid"):doc.index("\\textbf{Keywords:}")]
    kw = doc[doc.index("\\textbf{Keywords:}") + 18:doc.index("\\end{minipage}", doc.index("\\textbf{Keywords:}"))]
    title1 = "How well do rapid blood culture panel resistance targets predict laboratory susceptibility?"
    title2 = "An open, gene-by-gene concordance benchmark of U.S. clinical isolates in NCBI Pathogen Detection"
    front = (f"**{title1} {title2}**\n\n"
             f"Fatima Abdulwahab ([ORCID 0009-0008-2298-8386](https://orcid.org/0009-0008-2298-8386)), Independent Researcher, "
             f"Dallas, Texas, USA. Correspondence: abdulwahabfatima43@gmail.com\n\n## Abstract\n\n"
             + inline(ab.replace("\\small", "").replace("\\par\\vspace{4pt}\\noindent", "").replace("\n", " "))
             + "\n\n**Keywords:** " + inline(kw.replace("\n", " ")) + "\n")
    open(os.path.join(OUT, "00_front.md"), "w").write(front)
    body = doc[doc.index("\\section{Introduction}"):doc.index("\\small\n\\input{references.tex}")]
    secs = re.split(r"\\section\*?\{([^}]*)\}(?:\\label\{[^}]*\})?", body)[1:]
    roman = {"Introduction": "I", "Materials and methods": "II", "Results": "III", "Discussion": "IV", "Conclusions": "V"}
    groups = {"01": [], "02": [], "03": [], "04": [], "05": []}
    for name, content in zip(secs[0::2], secs[1::2]):
        key = {"Introduction": "01", "Materials and methods": "02", "Results": "03", "Discussion": "04"}.get(name, "05")
        heading = f"## {roman[name]}. {name}" if name in roman else f"### {name}"
        groups[key].append(heading + "\n\n" + convert(content))
    for k, v in groups.items():
        open(os.path.join(OUT, f"{k}.md"), "w").write("\n\n".join(v))
    # references
    refs = open(os.path.join(HERE, "references.tex")).read()
    items = re.findall(r"\\bibitem\{([^}]+)\}\s*(.*?)(?=\\bibitem|\\end\{thebibliography\})", refs, re.S)
    lines = ["## References", ""]
    for i, (k, t) in enumerate(items, 1):
        lines.append(f"{i}. " + inline(t.replace("\n", " ")))
    open(os.path.join(OUT, "06_refs.md"), "w").write("\n".join(lines) + "\n")
    # appendix
    app = tex[tex.index("\\section*{Appendix"):tex.index("\\end{document}")]
    app_md = "## Appendix: gene-detected, not-resistant isolates (excluding CTX-M)\n\n" + convert(
        app[app.index("\\begin{table}"):])
    open(os.path.join(OUT, "07_appendix.md"), "w").write(app_md)
    for f in sorted(os.listdir(OUT)):
        print(f, len(open(os.path.join(OUT, f)).read()))
