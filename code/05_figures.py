#!/usr/bin/env python3
"""
05_figures.py - Draw the two summary figures from the processed tables.

PLAIN-LANGUAGE NOTE: Figure 1 shows, for each panel target, how often a detected
gene meant "resistant" (left) and how often an absent gene meant "not resistant"
(right), with 95% confidence intervals. Figure 2 counts the disagreements by
likely cause. Figures carry a DRAFT stamp until you have checked the numbers;
run with --final after verification to remove it.
"""
import argparse, os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(ROOT, "data", "processed")
FIG = os.path.join(ROOT, "paper", "figures")
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
BLUE, ORANGE = "#2a78d6", "#eb6834"
ENT = "Enterobacterales (excluding Salmonella)"
ROWS = [  # (label, panel_target, drug, organism)
    ("mecA  |  S. aureus  |  oxacillin or cefoxitin", "mecA", "oxacillin or cefoxitin", "Staphylococcus aureus"),
    ("vanA  |  E. faecium  |  vancomycin", "vanA", "vancomycin", "Enterococcus faecium"),
    ("vanA  |  E. faecalis  |  vancomycin", "vanA", "vancomycin", "Enterococcus faecalis"),
    ("KPC  |  Enterobacterales  |  any carbapenem", "KPC", "any carbapenem", ENT),
    ("NDM  |  Enterobacterales  |  any carbapenem", "NDM", "any carbapenem", ENT),
    ("OXA-48-like  |  Enterobacterales  |  any carbapenem", "OXA-48-like", "any carbapenem", ENT),
    ("VIM  |  Enterobacterales  |  any carbapenem", "VIM", "any carbapenem", ENT),
    ("IMP  |  Enterobacterales  |  any carbapenem", "IMP", "any carbapenem", ENT),
    ("Any panel carbapenemase  |  Enterobacterales  |  any carbapenem",
     "any panel carbapenemase (KPC, NDM, OXA-48-like, VIM, IMP)", "any carbapenem", ENT),
    ("CTX-M  |  E. coli  |  ceftriaxone", "CTX-M", "ceftriaxone", "Escherichia coli"),
    ("CTX-M  |  K. pneumoniae complex  |  ceftriaxone", "CTX-M", "ceftriaxone", "Klebsiella pneumoniae complex"),
    ("CTX-M  |  Enterobacterales  |  ceftriaxone", "CTX-M", "ceftriaxone", ENT),
]


def style(ax):
    ax.set_facecolor(SURF)
    for s in ["top", "right", "left"]:
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK2, length=0, labelsize=8.5)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def stamp(fig, final):
    if not final:
        fig.text(0.99, 0.01, "DRAFT - not yet verified", ha="right", va="bottom", fontsize=9, color="#b00020")


def fig1(final):
    t = pd.read_csv(os.path.join(PROC, "concordance_table.csv"))
    t = t[(t.analysis_version == "main") & (t.isolate_subset == "all U.S. human clinical isolates")]
    data = []
    for lab, tg, dr, org in ROWS:
        x = t[(t.panel_target == tg) & (t.drug == dr) & (t.organism == org)]
        if len(x):
            data.append((lab, x.iloc[0]))
    fig, axes = plt.subplots(1, 2, figsize=(11, 0.42 * len(data) + 1.6), sharey=True, facecolor=SURF)
    for ax, (m, title, col) in zip(axes, [("ppv", "Gene detected: share resistant (PPV)", BLUE),
                                          ("npv", "Gene not detected: share not resistant (NPV)", ORANGE)]):
        style(ax)
        for i, (lab, r) in enumerate(data):
            y = len(data) - 1 - i
            if pd.isna(r[m]):
                ax.text(0.02, y, "no gene-positive isolates", va="center", fontsize=8, color=INK2)
                continue
            ax.plot([r[m + "_lo95"], r[m + "_hi95"]], [y, y], color=col, linewidth=2, solid_capstyle="round")
            ax.plot(r[m], y, "o", color=col, markersize=7, markeredgecolor=SURF, markeredgewidth=1.5)
            k = int(r.gene_pos_R) if m == "ppv" else int(r.gene_neg_notR)
            n = int(r.gene_pos_R + r.gene_pos_notR) if m == "ppv" else int(r.gene_neg_notR + r.gene_neg_R)
            ax.text(1.03, y, f"{k}/{n}", va="center", fontsize=8, color=INK2, transform=ax.get_yaxis_transform())
        ax.set_xlim(0, 1.0)
        ax.set_xticks([0, .25, .5, .75, 1])
        ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
        ax.set_title(title, fontsize=10, color=INK, loc="left", pad=8)
    axes[0].set_yticks(range(len(data)))
    axes[0].set_yticklabels([d[0] for d in data][::-1], fontsize=8.5, color=INK)
    fig.suptitle("Figure 1. Panel target result vs. laboratory susceptibility, U.S. human clinical isolates "
                 "(NCBI Pathogen Detection)", fontsize=10.5, color=INK, x=0.01, ha="left")
    fig.text(0.01, 0.005, "Dots: point estimate; lines: Wilson 95% CI; numbers: isolates. "
             "Phenotype: MICs reinterpreted with CLSI M100-Ed35 breakpoints; I/SDD counted as not resistant.",
             fontsize=7.5, color=INK2)
    stamp(fig, final)
    fig.tight_layout(rect=(0, 0.03, 0.97, 0.95))
    for ext in ("png", "svg"):
        fig.savefig(os.path.join(FIG, f"fig1_concordance.{ext}"), dpi=200, facecolor=SURF)


SHORT = {
    "unexplained by available data": "Unexplained by available data",
    "measured value at or within one dilution of the resistant breakpoint": "MIC within 1 dilution of R breakpoint",
    "submitter's interpretation differs from current breakpoints": "Submitter call differs from current breakpoints",
    "gene call partial or interrupted in the assembly": "Partial or interrupted gene call",
    "allele not catalogued as carbapenem-hydrolyzing (OXA-48 family variant)": "Non-carbapenemase OXA-48 variant",
    "phenotype available only as submitter S/I/R call": "Submitter S/I/R call only",
    "organism with chromosomal AmpC (possible derepression)": "Chromosomal AmpC organism",
    "non-panel ESBL or AmpC detected": "Non-panel ESBL or AmpC gene",
    "acquired non-CTX-M ESBL or AmpC detected": "Acquired non-CTX-M ESBL or AmpC",
    "chromosomal ampC promoter mutation (AmpC overproduction)": "ampC promoter mutation",
    "porin change without ESBL or AmpC (non-carbapenemase mechanism)": "Porin change only",
    "panel carbapenemase present (explains cephalosporin resistance)": "Panel carbapenemase present",
    "ESBL or AmpC detected without a called porin change (likely non-carbapenemase mechanism)": "ESBL/AmpC, no porin call",
    "ESBL or AmpC plus porin change (non-carbapenemase mechanism)": "ESBL/AmpC plus porin change",
    "non-panel carbapenemase detected": "Non-panel carbapenemase gene",
    "non-panel vancomycin resistance gene detected": "Non-panel van gene",
    "non-panel methicillin resistance gene detected": "Non-panel mec gene",
    "vanA operon genes found without a vanA ligase call (possible assembly break)": "vanA operon without ligase call",
    "mec regulator genes found without a mecA call (possible assembly break)": "mec regulators without mecA call",
}


def fig2(final):
    d = pd.read_csv(os.path.join(PROC, "discordance_cases.csv"))
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), facecolor=SURF)
    for ax, (dirn, col) in zip(axes, [("gene detected, not resistant", BLUE), ("gene not detected, resistant", ORANGE)]):
        style(ax)
        c = d[d.direction == dirn].primary_cause.map(lambda x: SHORT.get(x.split(" (candidates")[0], x)).value_counts()
        c = c.sort_values()
        ax.barh(range(len(c)), c.values, color=col, height=0.6)
        ax.set_yticks(range(len(c)))
        ax.set_yticklabels(list(c.index), fontsize=8, color=INK)
        for i, v in enumerate(c.values):
            ax.text(v, i, f" {v}", va="center", fontsize=7.5, color=INK2)
        ax.set_title(f"{dirn.capitalize()} (n={int(c.sum())})", fontsize=9.5, color=INK, loc="left")
    fig.suptitle("Figure 2. Discordant isolate-target pairs by most likely cause", fontsize=10.5, color=INK,
                 x=0.01, ha="left")
    stamp(fig, final)
    fig.tight_layout(rect=(0, 0.03, 1, 0.94))
    for ext in ("png", "svg"):
        fig.savefig(os.path.join(FIG, f"fig2_discordance_causes.{ext}"), dpi=200, facecolor=SURF)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--final", action="store_true")
    a = ap.parse_args()
    os.makedirs(FIG, exist_ok=True)
    fig1(a.final)
    fig2(a.final)
    print("figures written to", FIG)
