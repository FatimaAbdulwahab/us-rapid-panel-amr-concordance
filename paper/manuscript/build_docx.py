#!/usr/bin/env python3
"""
build_docx.py - Build the Word (.docx) version of the preprint, laid out like preprint.pdf.

PLAIN-LANGUAGE NOTE: Uses the same converted manuscript text as the editable doc
(tex2md.py output, which reads numbers.json, preprint.aux, tables/ and
references.tex), so the Word file says exactly what the PDF says. Figures are the
same PNGs. Equations become native Word equations.

Layout copied from preprint.tex: US Letter, 0.85/0.90 in top/bottom and 0.72 in side
margins, two columns 0.26 in apart; single-column title block and abstract; Palatino
10 pt; APS-style headings (I. INTRODUCTION / A. Subsection / 1. Run-in.); "FIG. n:" and
"TABLE n:" captions; double-rule tables; full-width figures and tables where the PDF
uses figure*/table*; numbered equations; [n] references; blue citations and URLs,
red cross-references. Output: preprint.docx
"""
import os, re, subprocess, copy
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor, Emu

HERE = os.path.dirname(os.path.abspath(__file__))
SEC = os.path.join(HERE, "docsec")
FIG = os.path.join(HERE, "figures")
FIGS = ["fig1_flow", "fig2_cohort", "fig3_forest", "fig4_carb_drug", "fig5_ctxm", "fig6_mic", "fig7_discordance",
        "fig8_robustness"]
FONT = "Palatino Linotype"
ORCID = "0009-0008-2298-8386"
EMAIL = "abdulwahabfatima43@gmail.com"

# Geometry (twentieths of a point) from the geometry package options in preprint.tex
PAGE_W, PAGE_H = 12240, 15840
M_TOP, M_BOT, M_SIDE = 1224, 1296, 1037
COL_SEP = 374
TEXT_W = PAGE_W - 2 * M_SIDE                 # 10166
COL_W = (TEXT_W - COL_SEP) // 2              # 4896

# Floats set across both columns in the PDF (figure* / table*); everything else sits in one column.
WIDE_FIGS = {1, 2, 3, 5, 6, 7, 8}
WIDE_TABS = {"II", "IV", "V", "X", "AI"}
FIG_WIDTH_IN = {1: 0.86 * TEXT_W / 1440}     # fig 1 is 0.86\textwidth; other wide figures \textwidth
TAB_PT = {"V": 7}                            # Table V is \scriptsize; the rest \footnotesize

BLUE = RGBColor(0x00, 0x00, 0xB3)            # blue!70!black (citations, URLs)
RED = RGBColor(0xBF, 0x00, 0x00)             # red!75!black (cross-references)

# ---------------------------------------------------------------------------
# 1. Markdown in, marked up for pandoc custom styles
# ---------------------------------------------------------------------------
subprocess.run(["python3", os.path.join(HERE, "tex2md.py"),
                "{" + ",".join(f'"{k}":"{os.path.join(FIG, k + ".png")}"' for k in FIGS) + "}"],
               check=True, stdout=subprocess.DEVNULL)


def div(style, body):
    return f'::: {{custom-style="{style}"}}\n{body}\n:::\n'


front = open(os.path.join(SEC, "00_front.md")).read()
m = re.match(r"\*\*(.*?)\*\*\n\n.*?\n\n## Abstract\n\n(.*?)\n\n(\*\*Keywords:\*\*.*)", front, re.S)
title, abstract, keywords = m.group(1), m.group(2).strip(), m.group(3).strip()
t1, t2 = title.split("? ", 1)
parts = [
    div("Title", f"{t1}?\\\n{t2}"),
    div("Author", "Fatima Abdulwahab ORCIDICON^1,^[^corr]"),
    div("Affiliation", "^1^Independent Researcher, Dallas, Texas, USA"),
    div("Abstract", abstract),
    div("Keywords", keywords),
    f"[^corr]: [{EMAIL}](mailto:{EMAIL})\n",
]

body = "\n\n".join(open(os.path.join(SEC, f)).read() for f in ["01.md", "02.md", "03.md", "04.md", "05.md"])
appendix = open(os.path.join(SEC, "07_appendix.md")).read()
refs = open(os.path.join(SEC, "06_refs.md")).read()


def link_citations(s):
    def one(mm):
        if any(int(x) == 0 for x in re.findall(r"\d+", mm.group(1))):
            return mm.group(0)  # an interval such as [0,1], not a citation
        inner = re.sub(r"\d+", lambda n: f"[{n.group(0)}](#ref-{n.group(0)})", mm.group(1))
        return "\\[" + inner + "\\]"
    return re.sub(r"\[(\d+(?:(?:, ?|–)\d+)*)\](?!\()", one, s)


def link_crossrefs(s):
    # "Table V", "Tables VI and VII", "Fig. 6c", "Figs. 3 and 4", "Sec. IV" -> internal links (red in the PDF)
    def one(mm):
        word, rest = mm.group(1), mm.group(2)
        kind = "tab" if word.startswith("Table") else ("fig" if word.startswith("Fig") else "sec")
        rest = re.sub(r"\b([IVX]+|\d+)\b", lambda n: f"[{n.group(1)}](#{kind}-{n.group(1)})", rest)
        return word + " " + rest
    return re.sub(r"\b(Tables?|Figs?\.|Sec\.)\s((?:[IVX]+|\d+)[a-d]?(?:(?:,\s|\sand\s|–)(?:[IVX]+|\d+)[a-d]?)*)\b",
                  one, s)


def mark_floats(s):
    s = re.sub(r"(?m)^\*\*Fig\. (\d+)\.\*\* ?(.*)$",
               lambda mm: "\n" + div("FigCaption", f"[]{{#fig-{mm.group(1)}}}FIG. {mm.group(1)}: {mm.group(2)}"), s)
    s = re.sub(r"(?m)^\*\*Table (A?[IVX]+)\.\*\* ?(.*)$",
               lambda mm: "\n" + div("TabCaption", f"[]{{#tab-{mm.group(1)}}}TABLE {mm.group(1)}: {mm.group(2)}"), s)
    s = re.sub(r"(?m)^(Note: .*)$", lambda mm: "\n" + div("TableNote", mm.group(1)), s)

    def img(mm):
        n = int(mm.group(1))
        w = FIG_WIDTH_IN.get(n, TEXT_W / 1440) if n in WIDE_FIGS else COL_W / 1440
        return f"![]({mm.group(2)}){{width={w:.2f}in}}"
    return re.sub(r"!\[Fig\. (\d+)\]\(([^)]+)\)", img, s)


def headings(s):
    # Roman-numbered sections get anchors; unnumbered back matter under "V. Conclusions" becomes section level.
    s = re.sub(r"(?m)^## ([IVX]+)\. (.*)$", r"## \1. \2 {#sec-\1}", s)
    head, _, tail = s.partition("## V. Conclusions")
    if tail:
        first, _, back = tail.partition("\n### ")
        tail = first + ("\n## " + back.replace("\n### ", "\n## ") if back else "")
    return head + ("## V. Conclusions" + tail if tail else "")


def equations(s):
    def aligned(mm):
        rows = [r.strip() for r in mm.group(1).split("\\\\") if r.strip()]
        return "\n\n".join("$$" + r.replace(", &", ",\\qquad ").replace("&", "") + "$$" for r in rows)
    s = re.sub(r"```latex\n\\begin\{aligned\}\n(.*?)\\end\{aligned\}\n```", aligned, s, flags=re.S)
    return re.sub(r"```latex\n(.*?)\n```", lambda mm: "$$" + mm.group(1).strip() + "$$", s, flags=re.S)


body = equations(link_crossrefs(link_citations(mark_floats(headings(body)))))
appendix = mark_floats(appendix)
ref_lines = []
for line in refs.splitlines():
    mm = re.match(r"^(\d+)\. (.*)$", line)
    if mm:
        ref_lines.append(div("Reference", f"[]{{#ref-{mm.group(1)}}}\\[{mm.group(1)}\\] {mm.group(2)}"))
refs_md = "## References\n\n" + "\n".join(ref_lines)

md = "\n\n".join(parts + [body, refs_md, appendix])
src = os.path.join(HERE, "preprint_docx.md")
open(src, "w").write(md)
out = os.path.join(HERE, "preprint.docx")
subprocess.run(["pandoc", src, "-f", "markdown+pipe_tables+tex_math_dollars+superscript", "-o", out,
                "--resource-path", HERE], check=True)
os.remove(src)

# ---------------------------------------------------------------------------
# 2. Styling and layout
# ---------------------------------------------------------------------------
d = Document(out)
styles = {s.name.lower(): s for s in d.styles}


def S(name):
    return styles.get(name.lower())


def set_font(style_or_rpr_owner):
    rpr = style_or_rpr_owner.element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.insert(0, rf)
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(a), FONT)
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme"):
        rf.attrib.pop(qn(a), None)


# document defaults
dd = d.styles.element.find(qn("w:docDefaults"))
rpd = dd.find(qn("w:rPrDefault")).find(qn("w:rPr"))
rf = rpd.find(qn("w:rFonts"))
if rf is None:
    rf = OxmlElement("w:rFonts")
    rpd.insert(0, rf)
for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
    rf.set(qn(a), FONT)
for a in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme"):
    rf.attrib.pop(qn(a), None)

BLACK = RGBColor(0, 0, 0)
for s in d.styles:
    if s.type in (1, 2) and s.name.lower() not in ("hyperlink",):  # paragraph / character styles
        try:
            set_font(s)
            if s.type == 1:
                s.font.color.rgb = BLACK
        except Exception:
            pass


def pstyle(name, size=10, bold=None, italic=None, align=None, before=0, after=0, first=None, left=None,
           right=None, hanging=None, caps=None, keep=None, line=0.95):
    s = S(name)
    if s is None:
        s = d.styles.add_style(name, 1)
        s.base_style = S("Normal")
        styles[name.lower()] = s
    f = s.font
    f.size = Pt(size)
    f.bold = bold
    f.italic = italic
    f.all_caps = caps
    f.color.rgb = BLACK
    pf = s.paragraph_format
    pf.space_before, pf.space_after = Pt(before), Pt(after)
    pf.line_spacing = line
    if align is not None:
        pf.alignment = align
    if first is not None:
        pf.first_line_indent = Pt(first)
    if left is not None:
        pf.left_indent = Emu(left * 635)
    if right is not None:
        pf.right_indent = Emu(right * 635)
    if hanging is not None:
        pf.left_indent = Emu(hanging * 635)
        pf.first_line_indent = Emu(-hanging * 635)
    if keep is not None:
        pf.keep_with_next = keep
    pf.widow_control = True
    return s


J, C = WD_ALIGN_PARAGRAPH.JUSTIFY, WD_ALIGN_PARAGRAPH.CENTER
pstyle("Normal", 10, align=J)
pstyle("Body Text", 10, align=J, first=12)
pstyle("First Paragraph", 10, align=J, first=0)
pstyle("Compact", 10, align=J)
pstyle("Title", 12, bold=True, align=C, after=10, line=1.0)
pstyle("Author", 10, align=C, after=3)
pstyle("Affiliation", 9, italic=True, align=C, after=12)
ABS_IND = int(TEXT_W * 0.09)
pstyle("Abstract", 9, align=J, left=ABS_IND, right=ABS_IND)
pstyle("Keywords", 9, align=J, left=ABS_IND, right=ABS_IND, before=4, after=16)
pstyle("Heading 2", 9, bold=True, align=C, caps=True, before=9, after=5, keep=True)
pstyle("Heading 3", 9, bold=True, align=C, before=7, after=4, keep=True)
pstyle("FigCaption", 9, align=J, before=4, after=10)
pstyle("TabCaption", 9, align=J, after=4, keep=True)
pstyle("TableNote", 8, align=WD_ALIGN_PARAGRAPH.LEFT, before=2, after=10)
pstyle("Reference", 9, align=J, hanging=400, after=1)
pstyle("Footnote Text", 8, align=J)
for name in ("Heading 2", "Heading 3"):
    S(name).font.italic = False
for name in ("Heading 1", "Heading 4"):
    if S(name):
        S(name).font.color.rgb = BLACK
if S("Verbatim Char"):
    S("Verbatim Char").font.size = None  # code takes the size of the text around it, as \texttt does
if S("Hyperlink"):
    S("Hyperlink").font.color.rgb = BLUE
    S("Hyperlink").font.underline = False

body_el = d.element.body
W_P, W_TBL = qn("w:p"), qn("w:tbl")


def text(el):
    return "".join(t.text or "" for t in el.iter(qn("w:t"))) if el.tag == W_P else ""


def style_of(el):
    if el.tag != W_P:
        return None
    ps = el.find(qn("w:pPr") + "/" + qn("w:pStyle"))
    return ps.get(qn("w:val")) if ps is not None else None


style_ids = {s.style_id: s.name for s in d.styles}


def sname(el):
    return style_ids.get(style_of(el), "")


def new_p(after_el, size=1):
    p = OxmlElement("w:p")
    pPr = OxmlElement("w:pPr")
    sp = OxmlElement("w:spacing")
    sp.set(qn("w:before"), "0"); sp.set(qn("w:after"), "0"); sp.set(qn("w:line"), "20"); sp.set(qn("w:lineRule"), "exact")
    pPr.append(sp)
    rpr = OxmlElement("w:rPr")
    sz = OxmlElement("w:sz"); sz.set(qn("w:val"), str(size * 2)); rpr.append(sz)
    pPr.append(rpr)
    p.append(pPr)
    after_el.addnext(p)
    return p


# --- headings: A. lettered subsections, run-in numbered sub-subsections --------
letter, num = 0, 0
for el in list(body_el):
    n = sname(el)
    if n == "Heading 2":
        letter, num = 0, 0
    elif n == "Heading 3":
        letter += 1
        num = 0
        r = OxmlElement("w:r"); t = OxmlElement("w:t"); t.text = f"{chr(64 + letter)}.\u2002"
        t.set(qn("xml:space"), "preserve"); r.append(t)
        el.find(qn("w:pPr")).addnext(r)
    elif n == "Heading 4":
        num += 1
        nxt = el.getnext()
        runs = [copy.deepcopy(r) for r in el.iter(qn("w:r"))]
        lead = OxmlElement("w:r"); t = OxmlElement("w:t"); t.text = f"{num}. "; t.set(qn("xml:space"), "preserve")
        lead.append(t)
        tailr = OxmlElement("w:r"); t = OxmlElement("w:t"); t.text = ".\u2002"; t.set(qn("xml:space"), "preserve")
        tailr.append(t)
        anchor = nxt.find(qn("w:pPr"))
        seq = [lead] + runs + [tailr]
        for r in seq:
            rpr = r.find(qn("w:rPr"))
            if rpr is None:
                rpr = OxmlElement("w:rPr"); r.insert(0, rpr)
            for tag in ("w:i", "w:sz"):
                for x in rpr.findall(qn(tag)):
                    rpr.remove(x)
            i = OxmlElement("w:i"); rpr.append(i)
            sz = OxmlElement("w:sz"); sz.set(qn("w:val"), "18"); rpr.append(sz)
        for r in reversed(seq):
            if anchor is not None:
                anchor.addnext(r)
            else:
                nxt.insert(0, r)
        body_el.remove(el)

# --- paragraphs that continue after a display equation are not indented ---------
for p in d.paragraphs:
    if p.style.name == "Body Text" and re.match(r"^[a-z]", p.text):
        p.paragraph_format.first_line_indent = Pt(0)

# --- reference labels: "[n]" + tab, hanging indent --------------------------------
for p in d.paragraphs:
    if p.style.name == "Reference":
        for r in p.runs:
            if re.match(r"^\[\d+\] ", r.text):
                r.text = re.sub(r"^(\[\d+\]) ", "\\1\t", r.text)
                break
        tabs = p.paragraph_format.tab_stops
        tabs.add_tab_stop(Emu(400 * 635))

# --- hyperlink colours: citations/URLs blue, internal cross-references red ------
for h in body_el.iter(qn("w:hyperlink")):
    anchor = h.get(qn("w:anchor")) or ""
    color = RED if re.match(r"^(tab|fig|sec)-", anchor) else BLUE
    for r in h.iter(qn("w:r")):
        rpr = r.find(qn("w:rPr"))
        if rpr is None:
            rpr = OxmlElement("w:rPr"); r.insert(0, rpr)
        for x in rpr.findall(qn("w:color")) + rpr.findall(qn("w:u")):
            rpr.remove(x)
        c = OxmlElement("w:color"); c.set(qn("w:val"), str(color)); rpr.append(c)
        u = OxmlElement("w:u"); u.set(qn("w:val"), "none"); rpr.append(u)


# --- tables ------------------------------------------------------------------------
def set_borders(cell, **kw):
    tcPr = cell._tc.get_or_add_tcPr()
    b = tcPr.find(qn("w:tcBorders"))
    if b is None:
        b = OxmlElement("w:tcBorders"); tcPr.append(b)
    for edge in ("top", "left", "bottom", "right"):
        if edge in kw:
            for x in b.findall(qn(f"w:{edge}")):
                b.remove(x)
    for edge in ("top", "left", "bottom", "right"):
        if edge in kw:
            el = OxmlElement(f"w:{edge}")
            for k, v in kw[edge].items():
                el.set(qn(f"w:{k}"), str(v))
            b.append(el)


TBL_ORDER = ["tblStyle", "tblpPr", "tblOverlap", "bidiVisual", "tblStyleRowBandSize", "tblStyleColBandSize", "tblW",
             "jc", "tblCellSpacing", "tblInd", "tblBorders", "shd", "tblLayout", "tblCellMar", "tblLook",
             "tblCaption", "tblDescription"]
NUMERIC = re.compile(r"^[\s\d.,%/()≤≥<>=+\-–—−±~*ᵃᵇ]*$")


def format_table(t, width, size):
    ncols = len(t.columns)
    need = []
    for ci in range(ncols):
        longest = 3
        for row in t.rows:
            txt = row.cells[ci].text.strip()
            words = max((len(w) for w in txt.split()), default=0)
            mono = 1.3 if re.match(r"^(SAMN|bla|mec|van)", txt) else 1.0
            longest = max(longest, min(len(txt), 26), int((words + 1.5) * mono))
        need.append(longest)
    pad = 120  # left+right cell margins, which every column needs whatever its text
    floor = (380 if width < 6000 else 520) - pad
    inner = width - pad * ncols
    fixed = set()
    while True:
        free = [i for i in range(ncols) if i not in fixed]
        room = inner - floor * len(fixed)
        ftot = sum(need[i] for i in free) or 1
        widths = [floor if i in fixed else int(room * need[i] / ftot) for i in range(ncols)]
        newly = {i for i in free if widths[i] < floor}
        if not newly:
            break
        fixed |= newly
    widths = [w + pad for w in widths]
    widths[max(range(ncols), key=lambda i: widths[i])] += width - sum(widths)
    tblPr = t._tbl.tblPr
    for tag in ("tblW", "tblLayout", "tblCellMar", "jc", "tblInd"):
        for el in tblPr.findall(qn(f"w:{tag}")):
            tblPr.remove(el)
    tw = OxmlElement("w:tblW"); tw.set(qn("w:w"), str(width)); tw.set(qn("w:type"), "dxa"); tblPr.append(tw)
    jc = OxmlElement("w:jc"); jc.set(qn("w:val"), "center"); tblPr.append(jc)
    lay = OxmlElement("w:tblLayout"); lay.set(qn("w:type"), "fixed"); tblPr.append(lay)
    mar = OxmlElement("w:tblCellMar")
    for side, v in (("top", 0), ("left", 60), ("bottom", 0), ("right", 60)):
        e = OxmlElement(f"w:{side}"); e.set(qn("w:w"), str(v)); e.set(qn("w:type"), "dxa"); mar.append(e)
    tblPr.append(mar)
    kids = list(tblPr)
    for k in kids:
        tblPr.remove(k)
    kids.sort(key=lambda e: TBL_ORDER.index(e.tag.split("}")[1]) if e.tag.split("}")[1] in TBL_ORDER else 99)
    for k in kids:
        tblPr.append(k)
    for gc, w in zip(t._tbl.tblGrid.findall(qn("w:gridCol")), widths):
        gc.set(qn("w:w"), str(w))
    # numeric columns centred, as in the LaTeX tables
    centre = []
    for ci in range(ncols):
        vals = [r.cells[ci].text.strip() for r in t.rows[1:] if r.cells[ci].text.strip()]
        centre.append(ci > 0 and vals and sum(bool(NUMERIC.match(v)) for v in vals) >= 0.8 * len(vals))
    last = len(t.rows) - 1
    for ri, row in enumerate(t.rows):
        for ci, cell in enumerate(row.cells):
            tcPr = cell._tc.get_or_add_tcPr()
            for el in tcPr.findall(qn("w:tcW")):
                tcPr.remove(el)
            cw = OxmlElement("w:tcW"); cw.set(qn("w:w"), str(widths[ci])); cw.set(qn("w:type"), "dxa")
            tcPr.insert(0, cw)
            for p in cell.paragraphs:
                pf = p.paragraph_format
                pf.space_after = pf.space_before = Pt(0)
                pf.first_line_indent = Pt(0)
                pf.line_spacing = 1.0
                p.alignment = C if centre[ci] else WD_ALIGN_PARAGRAPH.LEFT
                for r in p.runs:
                    r.font.size = Pt(size)
                    r.font.bold = None
            dbl = {"val": "double", "sz": 4, "space": 0, "color": "000000"}
            sgl = {"val": "single", "sz": 4, "space": 0, "color": "000000"}
            kw = {}
            if ri == 0:
                kw.update(top=dbl, bottom=sgl)
            if ri == last:
                kw["bottom"] = dbl
            if kw:
                set_borders(cell, **kw)


# --- find float groups -------------------------------------------------------------
groups = []  # (first element, last element, wide)
els = list(body_el)
i = 0
while i < len(els):
    e = els[i]
    n = sname(e)
    if n == "TabCaption" and i + 1 < len(els) and els[i + 1].tag == W_TBL:
        lab = re.match(r"TABLE (A?[IVX]+):", text(e)).group(1)
        tbl = els[i + 1]
        j = i + 2
        while j < len(els) and sname(els[j]) == "TableNote":
            j += 1
        wide = lab in WIDE_TABS
        t = [x for x in d.tables if x._tbl is tbl][0]
        format_table(t, TEXT_W if wide else COL_W, TAB_PT.get(lab, 8 if wide or len(t.columns) < 6 else 7))
        if len(text(e)) < (150 if wide else 70):
            e.find(qn("w:pPr")).append(OxmlElement("w:jc"))
            e.find(qn("w:pPr")).find(qn("w:jc")).set(qn("w:val"), "center")
        if not wide:  # a column-width table stays in one piece, like a LaTeX float
            for row in t.rows[:-1]:
                for cell in row.cells:
                    for cp in cell.paragraphs:
                        cp.paragraph_format.keep_with_next = True
            for row in t.rows:
                trPr = row._tr.get_or_add_trPr()
                cs = OxmlElement("w:cantSplit"); trPr.insert(0, cs)
        groups.append((e, els[j - 1], wide, lab))
        i = j
        continue
    if e.tag == W_P and e.xpath(".//pic:pic") and i + 1 < len(els) and sname(els[i + 1]) == "FigCaption":
        num = int(re.match(r"FIG\. (\d+):", text(els[i + 1])).group(1))
        pp = e.find(qn("w:pPr"))
        jc = OxmlElement("w:jc"); jc.set(qn("w:val"), "center")
        sp_ = OxmlElement("w:spacing"); sp_.set(qn("w:before"), "60"); sp_.set(qn("w:after"), "0")
        sp_.set(qn("w:line"), "240"); sp_.set(qn("w:lineRule"), "auto")
        for x in pp.findall(qn("w:spacing")) + pp.findall(qn("w:ind")):
            pp.remove(x)
        ind_ = OxmlElement("w:ind"); ind_.set(qn("w:firstLine"), "0")
        pp.append(sp_); pp.append(ind_); pp.append(jc)
        groups.append((e, els[i + 1], num in WIDE_FIGS, num))
        i += 2
        continue
    i += 1

# --- full-width floats travel as one unsplittable block (borderless one-cell table) --------
def wrap_block(first, last, width=TEXT_W):
    seq, el = [], first
    while True:
        seq.append(el)
        if el is last:
            break
        el = el.getnext()
    t = d.add_table(rows=1, cols=1)
    tbl = t._tbl
    tblPr = tbl.tblPr
    for x in list(tblPr):
        tblPr.remove(x)
    tw = OxmlElement("w:tblW"); tw.set(qn("w:w"), str(width)); tw.set(qn("w:type"), "dxa"); tblPr.append(tw)
    jc = OxmlElement("w:jc"); jc.set(qn("w:val"), "center"); tblPr.append(jc)
    bd = OxmlElement("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{side}"); e.set(qn("w:val"), "nil"); bd.append(e)
    tblPr.append(bd)
    lay = OxmlElement("w:tblLayout"); lay.set(qn("w:type"), "fixed"); tblPr.append(lay)
    mar = OxmlElement("w:tblCellMar")
    for side in ("top", "left", "bottom", "right"):
        e = OxmlElement(f"w:{side}"); e.set(qn("w:w"), "0"); e.set(qn("w:type"), "dxa"); mar.append(e)
    tblPr.append(mar)
    tbl.tblGrid.findall(qn("w:gridCol"))[0].set(qn("w:w"), str(width))
    tc = t.rows[0].cells[0]._tc
    tcPr = tc.get_or_add_tcPr()
    for x in tcPr.findall(qn("w:tcW")):
        tcPr.remove(x)
    cw = OxmlElement("w:tcW"); cw.set(qn("w:w"), str(width)); cw.set(qn("w:type"), "dxa"); tcPr.insert(0, cw)
    tc.remove(tc.find(W_P))
    first.addprevious(tbl)
    for el in seq:
        tc.append(el)
    if seq[-1].tag == W_TBL:
        tc.append(OxmlElement("w:p"))
    trPr = t.rows[0]._tr.get_or_add_trPr()
    trPr.append(OxmlElement("w:cantSplit"))
    return tbl


groups = [(wrap_block(f, l), None, w, lab) if (w and lab != "AI")
          else ((wrap_block(f, l, COL_W), None, w, lab) if isinstance(lab, str) and lab != "AI" else (f, l, w, lab))
          for f, l, w, lab in groups]
groups = [(f, f if l is None else l, w, lab) for f, l, w, lab in groups]

# --- display equations -> centred equation with right-aligned number (1), (2), (3) ----
eq_n = 0
for p in list(body_el.iter(W_P)):
    if p.find(qn("m:oMathPara")) is None or p.getparent() is not body_el:
        continue
    eq_n += 1
    t = d.add_table(rows=1, cols=3)
    tbl = t._tbl
    ws = [700, COL_W - 1400, 700]
    tblPr = tbl.tblPr
    for x in tblPr.findall(qn("w:tblW")) + tblPr.findall(qn("w:tblLayout")):
        tblPr.remove(x)
    tw = OxmlElement("w:tblW"); tw.set(qn("w:w"), str(COL_W)); tw.set(qn("w:type"), "dxa"); tblPr.append(tw)
    lay = OxmlElement("w:tblLayout"); lay.set(qn("w:type"), "fixed"); tblPr.append(lay)
    mar = OxmlElement("w:tblCellMar")
    for side in ("left", "right"):
        e = OxmlElement(f"w:{side}"); e.set(qn("w:w"), "0"); e.set(qn("w:type"), "dxa"); mar.append(e)
    tblPr.append(mar)
    kids = sorted(list(tblPr), key=lambda e: TBL_ORDER.index(e.tag.split("}")[1]) if e.tag.split("}")[1] in TBL_ORDER else 99)
    for k in list(tblPr):
        tblPr.remove(k)
    for k in kids:
        if k.tag == qn("w:tblStyle"):
            continue
        tblPr.append(k)
    for gc, w in zip(tbl.tblGrid.findall(qn("w:gridCol")), ws):
        gc.set(qn("w:w"), str(w))
    cells = t.rows[0].cells
    for c, w in zip(cells, ws):
        c.width = Emu(w * 635)
        c.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    mid = cells[1]._tc
    mid.remove(mid.find(W_P))
    p.addprevious(tbl)
    mid.append(p)
    pf = cells[1].paragraphs[0].paragraph_format
    pf.space_before = pf.space_after = Pt(3)
    pf.first_line_indent = Pt(0)
    pf.line_spacing = 1.0
    rp = cells[2].paragraphs[0]
    rp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    rp.paragraph_format.first_line_indent = Pt(0)
    rp.add_run(f"({eq_n})").font.size = Pt(10)
    cells[0].paragraphs[0].paragraph_format.first_line_indent = Pt(0)

# --- page footer with the page number --------------------------------------------
sec = d.sections[0]
fp = sec.footer.paragraphs[0]
fp.alignment = C
fp.paragraph_format.first_line_indent = Pt(0)
run = fp.add_run()
run.font.size = Pt(10)
for tag, txt in [("begin", None), (None, "PAGE"), ("end", None)]:
    if tag:
        fc = OxmlElement("w:fldChar"); fc.set(qn("w:fldCharType"), tag); run._r.append(fc)
    else:
        it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = txt; run._r.append(it)
final_sp = body_el.find(qn("w:sectPr"))
footer_ref = copy.deepcopy(final_sp.find(qn("w:footerReference")))


def make_sectpr(cols, start="continuous"):
    sp = OxmlElement("w:sectPr")
    if footer_ref is not None:
        sp.append(copy.deepcopy(footer_ref))
    if start:
        ty = OxmlElement("w:type"); ty.set(qn("w:val"), start); sp.append(ty)
    pg = OxmlElement("w:pgSz"); pg.set(qn("w:w"), str(PAGE_W)); pg.set(qn("w:h"), str(PAGE_H)); sp.append(pg)
    mar = OxmlElement("w:pgMar")
    for k, v in (("top", M_TOP), ("right", M_SIDE), ("bottom", M_BOT), ("left", M_SIDE), ("header", 720),
                 ("footer", 560), ("gutter", 0)):
        mar.set(qn(f"w:{k}"), str(v))
    sp.append(mar)
    c = OxmlElement("w:cols"); c.set(qn("w:num"), str(cols)); c.set(qn("w:space"), str(COL_SEP)); sp.append(c)
    return sp


def put_sectpr(p, sp):
    pPr = p.find(qn("w:pPr"))
    if pPr is None:
        pPr = OxmlElement("w:pPr"); p.insert(0, pPr)
    old = pPr.find(qn("w:sectPr"))
    if old is not None:
        pPr.remove(old)
    pPr.append(sp)


def has_sectpr(p):
    return p is not None and p.tag == W_P and p.find(qn("w:pPr") + "/" + qn("w:sectPr")) is not None


# section 1: title block and abstract (one column)
kw_p = [el for el in body_el if sname(el) == "Keywords"][-1]
put_sectpr(kw_p, make_sectpr(1, start=None))

# full-width floats: close the two-column run before, open it again after
appendix_start = [el for el in body_el if sname(el) == "Heading 2" and text(el).startswith("Appendix")][0]
for first, last, wide, lab in groups:
    if not wide or lab == "AI":
        continue
    prev = first.getprevious()
    # adjacent wide floats each keep their own one-column section (an empty two-column section between
    # them), so no one-column section has to break across a page
    if prev.tag != W_P or has_sectpr(prev):
        prev = new_p(prev)
    put_sectpr(prev, make_sectpr(2))
    end = last if last.tag == W_P else new_p(last)
    put_sectpr(end, make_sectpr(1))

# The paragraph that resumes two-column text after a full-width float must not be held to the next
# paragraph (LibreOffice otherwise lays the float and that text on top of each other when the float moves
# to the next page). Word ignores the difference.
for sp_el in list(body_el.iter(qn("w:sectPr"))):
    cols = sp_el.find(qn("w:cols"))
    holder = sp_el.getparent().getparent()
    if cols is None or cols.get(qn("w:num")) != "1" or holder is kw_p:
        continue
    nxt = holder.getnext()
    if nxt is not None and nxt.tag == W_P:
        ppr = nxt.find(qn("w:pPr"))
        if ppr is None:
            ppr = OxmlElement("w:pPr"); nxt.insert(0, ppr)
        kn = OxmlElement("w:keepNext"); kn.set(qn("w:val"), "0")
        ppr.append(kn)

# references close the last two-column run; the appendix starts a new page in one column
last_ref = [el for el in body_el if sname(el) == "Reference"][-1]
put_sectpr(last_ref, make_sectpr(2))
for k in list(final_sp):
    if k.tag != qn("w:footerReference") and k.tag != qn("w:headerReference"):
        final_sp.remove(k)
for k in list(make_sectpr(1, start="nextPage")):
    if k.tag != qn("w:footerReference"):
        final_sp.append(k)

# --- ORCID icon after the author name, linked to the ORCID record ------------------
icon = os.path.join(HERE, "figures", "orcid_icon.png")
if not os.path.exists(icon):
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    dr.ellipse((0, 0, 127, 127), fill=(166, 206, 57, 255))
    try:
        fnt = ImageFont.truetype("DejaVuSans-Bold.ttf", 62)
    except Exception:
        fnt = ImageFont.load_default()
    dr.text((64, 66), "iD", fill="white", font=fnt, anchor="mm")
    im.save(icon)
for p in d.paragraphs:
    if p.style.name == "Author":
        for r in p.runs:
            if "ORCIDICON" in r.text:
                r.text = r.text.replace(" ORCIDICON", "\u2009")
                pic = p.add_run()
                pic.add_picture(icon, height=Pt(8))
                rid = d.part.relate_to(f"https://orcid.org/{ORCID}", RT.HYPERLINK, is_external=True)
                h = OxmlElement("w:hyperlink"); h.set(qn("r:id"), rid)
                r._r.addnext(h)
                h.append(pic._r)
                sp = OxmlElement("w:r"); t = OxmlElement("w:t"); t.text = "\u2009"; t.set(qn("xml:space"), "preserve")
                sp.append(t)
                h.addnext(sp)
                break
        break

d.core_properties.title = title
d.core_properties.author = "Fatima Abdulwahab"
d.save(out)
print("wrote", out, f"({len(groups)} floats, {eq_n} equations)")

# ---------------------------------------------------------------------------
# 3. Schema clean-up pass: element order, footnote "*" mark, ids
# ---------------------------------------------------------------------------
import zipfile, shutil
from lxml import etree

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
M = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"
PPR = ["pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr", "widowControl", "numPr", "suppressLineNumbers",
       "pBdr", "shd", "tabs", "suppressAutoHyphens", "kinsoku", "wordWrap", "overflowPunct", "topLinePunct",
       "autoSpaceDE", "autoSpaceDN", "bidi", "adjustRightInd", "snapToGrid", "spacing", "ind", "contextualSpacing",
       "mirrorIndents", "suppressOverlap", "jc", "textDirection", "textAlignment", "textboxTightWrap", "outlineLvl",
       "divId", "cnfStyle", "rPr", "sectPr", "pPrChange"]
STY = ["name", "aliases", "basedOn", "next", "link", "autoRedefine", "hidden", "uiPriority", "semiHidden",
       "unhideWhenUsed", "qFormat", "locked", "personal", "personalCompose", "personalReply", "rsid", "pPr", "rPr",
       "tblPr", "trPr", "tcPr", "tblStylePr"]
RPR = ["rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps", "smallCaps", "strike", "dstrike", "outline", "shadow",
       "emboss", "imprint", "noProof", "snapToGrid", "vanish", "webHidden", "color", "spacing", "w", "kern", "position",
       "sz", "szCs", "highlight", "u", "effect", "bdr", "shd", "fitText", "vertAlign", "rtl", "cs", "em", "lang",
       "eastAsianLayout", "specVanish", "oMath"]
TCPR = ["cnfStyle", "tcW", "gridSpan", "hMerge", "vMerge", "tcBorders", "shd", "noWrap", "tcMar", "textDirection",
        "tcFitText", "vAlign", "hideMark"]
SECT = ["headerReference", "footerReference", "footnotePr", "endnotePr", "type", "pgSz", "pgMar", "paperSrc",
        "pgBorders", "lnNumType", "pgNumType", "cols", "formProt", "vAlign", "noEndnote", "titlePg", "textDirection",
        "bidi", "rtlGutter", "docGrid", "printerSettings", "sectPrChange"]
SETTINGS = ["writeProtection", "view", "zoom", "removePersonalInformation", "removeDateAndTime",
            "doNotDisplayPageBoundaries", "displayBackgroundShape", "printPostScriptOverText",
            "printFractionalCharacterWidth", "printFormsData", "embedTrueTypeFonts", "embedSystemFonts",
            "saveSubsetFonts", "saveFormsData", "mirrorMargins", "alignBordersAndEdges", "bordersDoNotSurroundHeader",
            "bordersDoNotSurroundFooter", "gutterAtTop", "hideSpellingErrors", "hideGrammaticalErrors",
            "activeWritingStyle", "proofState", "formsDesign", "attachedTemplate", "linkStyles",
            "stylePaneFormatFilter", "stylePaneSortMethod", "documentType", "mailMerge", "revisionView",
            "trackRevisions", "doNotTrackMoves", "doNotTrackFormatting", "documentProtection", "autoFormatOverride",
            "styleLockTheme", "styleLockQFSet", "defaultTabStop", "autoHyphenation", "consecutiveHyphenLimit",
            "hyphenationZone", "doNotHyphenateCaps", "showEnvelope", "summaryLength", "clickAndTypeStyle",
            "defaultTableStyle", "evenAndOddHeaders", "bookFoldRevPrinting", "bookFoldPrinting",
            "bookFoldPrintingSheets", "drawingGridHorizontalSpacing", "drawingGridVerticalSpacing",
            "displayHorizontalDrawingGridEvery", "displayVerticalDrawingGridEvery",
            "doNotUseMarginsForDrawingGridOrigin", "drawingGridHorizontalOrigin", "drawingGridVerticalOrigin",
            "doNotShadeFormData", "noPunctuationKerning", "characterSpacingControl", "printTwoOnOne",
            "strictFirstAndLastChars", "noLineBreaksAfter", "noLineBreaksBefore", "savePreviewPicture",
            "doNotValidateAgainstSchema", "saveInvalidXml", "ignoreMixedContent", "alwaysShowPlaceholderText",
            "doNotDemarcateInvalidXml", "saveXmlDataOnly", "useXSLTransform", "saveThroughXslt", "showXMLTags",
            "alwaysMergeEmptyNamespace", "updateFields", "hdrShapeDefaults", "footnotePr", "endnotePr", "compat",
            "docVars", "rsids", "mathPr", "attachedSchema", "themeFontLang", "clrSchemeMapping",
            "doNotIncludeSubdocsInStats", "doNotAutoCompressPictures", "forceUpgrade", "captions",
            "readModeInkLockDown", "smartTagType", "schemaLibrary", "shapeDefaults", "doNotEmbedSmartTags",
            "decimalSymbol", "listSeparator"]


def reorder(parent, order, ns=W):
    kids = list(parent)
    known = [k for k in kids if isinstance(k.tag, str) and k.tag.startswith(ns) and k.tag[len(ns):] in order]
    if not known:
        return
    for k in kids:
        parent.remove(k)
    known.sort(key=lambda e: order.index(e.tag[len(ns):]))
    for k in known + [k for k in kids if k not in known]:
        parent.append(k)


def star_mark(run_el, ref_tag):
    """Turn an auto-numbered footnote mark into the '*' used in the PDF."""
    ref = run_el.find(W + ref_tag)
    if ref_tag == "footnoteReference":
        ref.set(W + "customMarkFollows", "1")
        t = etree.SubElement(run_el, W + "t")
        t.text = "*"
    else:
        run_el.remove(ref)
        t = etree.SubElement(run_el, W + "t")
        t.text = "*"


tmp = out + ".tmp"
with zipfile.ZipFile(out) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
    for item in zin.infolist():
        data = zin.read(item.filename)
        if item.filename in ("word/document.xml", "word/styles.xml", "word/numbering.xml", "word/settings.xml",
                             "word/footnotes.xml"):
            root = etree.fromstring(data)
            if item.filename == "word/document.xml":
                for r in root.iter(W + "r"):
                    if r.find(W + "footnoteReference") is not None:
                        star_mark(r, "footnoteReference")
            if item.filename == "word/footnotes.xml":
                for fn in root.findall(W + "footnote"):
                    if fn.get(W + "type") in ("separator", "continuationSeparator"):
                        continue
                    for r in fn.iter(W + "r"):
                        if r.find(W + "footnoteRef") is not None:
                            star_mark(r, "footnoteRef")
            for p in root.iter(W + "pPr"):
                reorder(p, PPR)
            for r in root.iter(W + "rPr"):
                if r.text and r.text.strip():
                    r.text = None
                for ch in r:
                    if ch.tail and ch.tail.strip():
                        ch.tail = None
                reorder(r, RPR)
            for tc in root.iter(W + "tcPr"):
                reorder(tc, TCPR)
            for sp in root.iter(W + "sectPr"):
                reorder(sp, SECT)
            for sc in list(root.iter(M + "sepChr")):
                if not sc.get(M + "val"):
                    sc.getparent().remove(sc)  # empty separator: same as none for a single-element delimiter
            # merge runs of upright letters that pandoc writes one character at a time (\mathrm{PPV})
            for par in list(root.iter()):
                kids = list(par)
                prev = None
                for k in kids:
                    if k.tag == M + "r" and prev is not None and prev.tag == M + "r":
                        a, b = prev.find(M + "rPr"), k.find(M + "rPr")
                        sa = etree.tostring(a) if a is not None else b""
                        sb = etree.tostring(b) if b is not None else b""
                        ta, tb = prev.find(M + "t"), k.find(M + "t")
                        if sa == sb and sa and ta is not None and tb is not None and \
                                re.fullmatch(r"[A-Za-z]+", ta.text or "") and re.fullmatch(r"[A-Za-z]+", tb.text or ""):
                            ta.text = (ta.text or "") + (tb.text or "")
                            par.remove(k)
                            continue
                    prev = k
            for mr in root.iter(M + "r"):
                mt = mr.find(M + "t")
                if mt is not None and (mt.text or "").strip() == "+" and mr.getparent().tag == M + "sup":
                    rp = mr.find(M + "rPr")
                    if rp is None:
                        rp = etree.Element(M + "rPr"); mr.insert(0, rp)
                    for x in rp.findall(M + "sty"):
                        rp.remove(x)
                    if rp.find(M + "nor") is None:
                        etree.SubElement(rp, M + "nor")  # lone superscript "+" as normal text (renders in all readers)
            for dp in root.iter(M + "dPr"):
                reorder(dp, ["begChr", "sepChr", "endChr", "grow", "shp", "ctrlPr"], ns=M)
            for mc in root.iter(M + "mcPr"):
                reorder(mc, ["count", "mcJc"], ns=M)
            if root.tag == W + "settings":
                kids = list(root)
                for k in kids:
                    root.remove(k)
                loc = lambda e: etree.QName(e).localname
                kids.sort(key=lambda e: SETTINGS.index(loc(e)) if loc(e) in SETTINGS else len(SETTINGS))
                for k in kids:
                    root.append(k)
            for st_el in root.iter(W + "style"):
                reorder(st_el, STY)
            for pm in root.iter(W + "pgMar"):
                for k, v in (("header", "720"), ("footer", "560"), ("gutter", "0")):
                    if pm.get(W + k) is None:
                        pm.set(W + k, v)
            for ns_el in root.iter(W + "nsid"):
                v = ns_el.get(W + "val")
                if v and len(v) != 8:
                    ns_el.set(W + "val", v.rjust(8, "0")[-8:])
            data = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
        zout.writestr(item, data)
shutil.move(tmp, out)
print("schema pass done")
