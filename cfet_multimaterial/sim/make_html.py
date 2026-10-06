"""Render paper/main.tex (the constrained subset of LaTeX used in this manuscript) as a
single self-contained HTML page (paper/manuscript.html) with embedded figures, numbered
references from refs.bib, and MathJax (SVG, no external fonts) for the equations.
Run: python3 -m sim.make_html
"""
import os, re, base64, html

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAP = os.path.join(HERE, "paper"); FIG = os.path.join(HERE, "figures")
SEARCH = [FIG, os.path.join(HERE, "schematics"), os.path.join(HERE, "layout", "png")]


def load_bib():
    txt = open(os.path.join(PAP, "refs.bib")).read()
    entries = {}
    for m in re.finditer(r"@(\w+)\{([^,]+),(.*?)\n\}", txt, re.S):
        body = m.group(3); d = {}
        for f in re.finditer(r"(\w+)\s*=\s*(\{(?:[^{}]|\{[^{}]*\})*\}|\"[^\"]*\"|\d+)", body):
            v = f.group(2).strip()
            if v[0] in "{\"": v = v[1:-1]
            d[f.group(1).lower()] = re.sub(r"[{}]", "", v)
        entries[m.group(2).strip()] = d
    return entries


def fmt_ref(d):
    au = d.get("author", "")
    au = " and ".join(a.strip() for a in au.split(" and ")[:3]) + (" et al." if au.count(" and ") >= 3 else "")
    au = au.replace(" and others", " et al.")
    title = re.sub(r"\$_\{?(\w+)\}?\$", r"<sub>\1</sub>", html.escape(d.get("title", "")))
    title = re.sub(r"\$\^\{?(\w+)\}?\$", r"<sup>\1</sup>", title)
    parts = [html.escape(au), "“" + title + ",”"]
    ven = d.get("journal") or d.get("booktitle") or d.get("howpublished") or d.get("publisher") or ""
    if ven: parts.append("<i>" + html.escape(ven) + "</i>")
    if d.get("volume"): parts.append("vol. " + html.escape(d["volume"]))
    if d.get("number"): parts.append("no. " + html.escape(d["number"]))
    if d.get("pages"): parts.append("pp. " + html.escape(d["pages"]).replace("--", "–"))
    if d.get("year"): parts.append(html.escape(d["year"]))
    s = ", ".join(parts) + "."
    if d.get("doi"): s += f' doi: <a href="https://doi.org/{html.escape(d["doi"])}">{html.escape(d["doi"])}</a>'
    elif d.get("url"): s += f' <a href="{html.escape(d["url"])}">{html.escape(d["url"])}</a>'
    return s


def img_uri(name):
    for d in SEARCH:
        p = os.path.join(d, name)
        if os.path.exists(p):
            return "data:image/png;base64," + base64.b64encode(open(p, "rb").read()).decode()
    return ""


def tex_table_to_html(tex):
    tex = re.sub(r"\\(hline|toprule|midrule|bottomrule)", "", tex)
    m = re.search(r"\\begin\{tabular\}\{[^}]*\}(.*)\\end\{tabular\}", tex, re.S)
    body = m.group(1) if m else tex
    rows = [r.strip() for r in re.split(r"\\\\", body) if r.strip()]
    out = ["<div class='tablewrap'><table>"]
    for i, r in enumerate(rows):
        cells = [inline(c.strip()) for c in r.split("&")]
        tag = "th" if i == 0 else "td"
        out.append("<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>")
    out.append("</table></div>")
    return "\n".join(out)


MACROS = {}
CITES = []


def cite(keys):
    nums = []
    for k in keys.split(","):
        k = k.strip()
        if k not in CITES: CITES.append(k)
        nums.append(str(CITES.index(k) + 1))
    return "[" + ", ".join(nums) + "]"


def inline(s):
    # macros from numbers.tex
    def mrep(m):
        return MACROS.get(m.group(1), m.group(0))
    s = re.sub(r"\\([A-Za-z]+)(?=[^A-Za-z]|$)", lambda m: MACROS[m.group(1)] if m.group(1) in MACROS else m.group(0), s)
    s = s.replace("\\ucm", "UCM-CFET").replace("\\ ", " ").replace("~", "&nbsp;")
    s = re.sub(r"\\cite\{([^}]*)\}", lambda m: cite(m.group(1)), s)
    s = re.sub(r"\\ref\{fig:(\w+)\}", lambda m: f"<a href='#fig-{m.group(1)}'>{FIGNUM.get(m.group(1), '?')}</a>", s)
    s = re.sub(r"\\ref\{tab:(\w+)\}", lambda m: f"<a href='#tab-{m.group(1)}'>{TABNUM.get(m.group(1), '?')}</a>", s)
    s = re.sub(r"\\ref\{eq:(\w+)\}", lambda m: EQNUM.get(m.group(1), "?"), s)
    s = re.sub(r"\\emph\{([^}]*)\}", r"<em>\1</em>", s)
    s = re.sub(r"\\textbf\{([^}]*)\}", r"<strong>\1</strong>", s)
    s = re.sub(r"\\texttt\{([^}]*)\}", lambda m: "<code>" + m.group(1).replace("\\_", "_") + "</code>", s)
    s = re.sub(r"\\IEEEPARstart\{(\w)\}\{(\w+)\}", r"\1\2", s)
    s = s.replace("\\%", "%").replace("\\_", "_").replace("\\&", "&amp;").replace("``", "“").replace("''", "”").replace("---", "—").replace("--", "–")
    s = s.replace("$^\\circ$", "°").replace("^\\circ", "°")
    s = re.sub(r"\\footnotesize|\\scriptsize|\\centering|\\balance", "", s)
    return s


FIGNUM, TABNUM, EQNUM = {}, {}, {}


def main():
    global MACROS
    tex = open(os.path.join(PAP, "main.tex")).read()
    for m in re.finditer(r"\\newcommand\{\\(\w+)\}\{([^}]*)\}", open(os.path.join(PAP, "numbers.tex")).read()):
        MACROS[m.group(1)] = m.group(2)
    bib = load_bib()
    body = tex[tex.index("\\maketitle"):tex.index("\\bibliographystyle")]
    title = re.search(r"\\title\{(.*?)\}\n", tex, re.S).group(1)
    # number figures/tables/equations in order of appearance
    for i, m in enumerate(re.finditer(r"\\label\{fig:(\w+)\}", body)): FIGNUM[m.group(1)] = str(i + 1)
    for i, m in enumerate(re.finditer(r"\\label\{tab:(\w+)\}", body)): TABNUM[m.group(1)] = str(i + 1)
    for i, m in enumerate(re.finditer(r"\\label\{eq:(\w+)\}", body)): EQNUM[m.group(1)] = f"({i + 1})"
    out = []
    # abstract & keywords
    ab = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", body, re.S).group(1)
    kw = re.search(r"\\begin\{IEEEkeywords\}(.*?)\\end\{IEEEkeywords\}", body, re.S).group(1)
    out.append(f"<section class='abstract'><h2>Abstract</h2><p>{inline(ab.strip())}</p><p class='kw'><b>Index terms</b> — {inline(kw.strip())}</p></section>")
    body = body[body.index("\\end{IEEEkeywords}") + len("\\end{IEEEkeywords}"):]
    # floats: pull out figures and tables, render where they appear
    def render_figure(m):
        inner = m.group(1)
        imgs = re.findall(r"\\includegraphics\[[^\]]*\]\{([^}]*)\}", inner)
        cap = re.search(r"\\caption\{(.*)\}\s*\\label\{fig:(\w+)\}", inner, re.S)
        caption, lab = (cap.group(1), cap.group(2)) if cap else ("", "x")
        ims = "".join(f"<img src='{img_uri(i)}' alt='{html.escape(i)}'>" for i in imgs)
        return f"<figure id='fig-{lab}'>{ims}<figcaption><b>Fig. {FIGNUM.get(lab,'?')}.</b> {inline(caption)}</figcaption></figure>"
    def render_table(m):
        inner = m.group(1)
        cap = re.search(r"\\caption\{(.*?)\}\s*\\label\{tab:(\w+)\}", inner, re.S)
        caption, lab = (cap.group(1), cap.group(2)) if cap else ("", "x")
        inp = re.search(r"\\input\{([^}]*)\}", inner)
        ttex = open(os.path.join(PAP, inp.group(1))).read() if inp else inner
        return f"<figure class='table' id='tab-{lab}'><figcaption><b>Table {TABNUM.get(lab,'?')}.</b> {inline(caption)}</figcaption>{tex_table_to_html(ttex)}</figure>"
    body = re.sub(r"\\begin\{figure\*?\}\[!t\](.*?)\\end\{figure\*?\}", render_figure, body, flags=re.S)
    body = re.sub(r"\\begin\{table\*?\}\[!t\](.*?)\\end\{table\*?\}", render_table, body, flags=re.S)
    # equations: keep LaTeX for MathJax, add numbers
    def render_eq(m):
        inner = m.group(2)
        lab = re.search(r"\\label\{eq:(\w+)\}", inner); inner = re.sub(r"\\label\{eq:\w+\}", "", inner)
        num = EQNUM.get(lab.group(1), "") if lab else ""
        env = m.group(1)
        return f"<div class='eq'>\\begin{{{env}}}{inner}\\end{{{env}}}<span class='eqnum'>{num}</span></div>"
    body = re.sub(r"\\begin\{(equation|align)\}(.*?)\\end\{\1\}", render_eq, body, flags=re.S)
    # sections
    body = re.sub(r"\\section\{([^}]*)\}", lambda m: f"\n\n<h2>{inline(m.group(1))}</h2>\n\n", body)
    body = re.sub(r"\\subsection\{([^}]*)\}", lambda m: f"\n\n<h3>{inline(m.group(1))}</h3>\n\n", body)
    body = re.sub(r"\\subsubsection\{([^}]*)\}", lambda m: f"\n\n<h4>{inline(m.group(1))}</h4>\n\n", body)
    body = re.sub(r"%%\w+", "", body)
    # paragraphs
    chunks = re.split(r"\n\s*\n", body)
    for c in chunks:
        c = c.strip()
        if not c: continue
        if c.startswith("<"):
            out.append(c if c.startswith(("<h", "<figure", "<div class='eq'")) else inline(c))
        else:
            out.append("<p>" + inline(c) + "</p>")
    refs = "".join(f"<li id='ref{i+1}'>{fmt_ref(bib.get(k, {'title': k}))}</li>" for i, k in enumerate(CITES))
    page = f"""<title>Multi-Material CFET Compact Model</title>
<style>
/* layout: single reading column (manuscript), figures full width of column, tables scroll */
:root {{ --bg:#fbfaf7; --fg:#1b1a17; --muted:#5e5b55; --rule:#d9d5cc; --accent:#0b4f8a; --accent2:#b84a12; --code:#f0ede6;
  --display:"Source Serif 4", Georgia, "Times New Roman", serif; --body:"Source Serif 4", Georgia, serif; --ui:"IBM Plex Sans", "Helvetica Neue", Arial, sans-serif; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#15171a; --fg:#e8e6e1; --muted:#a8a49c; --rule:#3a3d42; --accent:#7fb4e6; --accent2:#f0925c; --code:#22252a; color-scheme: dark }} }}
:root[data-theme="dark"] {{ --bg:#15171a; --fg:#e8e6e1; --muted:#a8a49c; --rule:#3a3d42; --accent:#7fb4e6; --accent2:#f0925c; --code:#22252a; color-scheme: dark }}
body {{ background:var(--bg); color:var(--fg); font-family:var(--body); font-size:16px; line-height:1.55; margin:0; padding-block:32px; padding-inline:16px; }}
main {{ max-width: 860px; margin: 0 auto; }}
header h1 {{ font-family:var(--display); font-weight:600; font-size:clamp(1.5rem, 3.2vw, 2.1rem); line-height:1.2; text-wrap:balance; margin:0 0 .4rem; }}
header .authors {{ font-family:var(--ui); color:var(--muted); font-size:.95rem; }}
header .note {{ font-family:var(--ui); font-size:.85rem; color:var(--muted); border:1px solid var(--rule); padding:.6rem .8rem; margin-top:1rem; }}
h2 {{ font-family:var(--ui); font-size:1.05rem; letter-spacing:.04em; text-transform:uppercase; color:var(--accent); margin:2.2rem 0 .6rem; border-bottom:1px solid var(--rule); padding-bottom:.25rem; }}
h3 {{ font-family:var(--ui); font-size:1rem; margin:1.4rem 0 .4rem; }}
h4 {{ font-family:var(--ui); font-size:.95rem; margin:1rem 0 .3rem; font-style:italic; font-weight:600; }}
p {{ margin:0 0 .9rem; }}
.abstract {{ border-left:3px solid var(--accent2); padding-left:1rem; margin:1.5rem 0; }}
.abstract h2 {{ border:0; margin-top:0; }}
.kw {{ font-family:var(--ui); font-size:.9rem; color:var(--muted); }}
figure {{ margin:1.4rem 0; }}
figure img {{ max-width:100%; display:block; margin:0 auto .5rem; }}
figcaption {{ font-family:var(--ui); font-size:.85rem; color:var(--muted); line-height:1.4; }}
.tablewrap {{ overflow-x:auto; margin-top:.5rem; }}
table {{ border-collapse:collapse; font-family:var(--ui); font-size:.8rem; font-variant-numeric:tabular-nums; min-width:100%; }}
th, td {{ padding:.3rem .5rem; border-bottom:1px solid var(--rule); text-align:right; white-space:nowrap; }}
th:first-child, td:first-child {{ text-align:left; }}
th {{ border-bottom:2px solid var(--fg); font-weight:600; }}
code {{ font-family:"IBM Plex Mono", Menlo, monospace; font-size:.85em; background:var(--code); padding:.05em .3em; border-radius:3px; }}
.eq {{ display:flex; align-items:center; gap:1rem; overflow-x:auto; margin:.6rem 0 1rem; }}
.eq > :first-child {{ flex:1; min-width:0; }}
.eqnum {{ font-family:var(--ui); color:var(--muted); }}
a {{ color:var(--accent); }}
ol.refs {{ font-family:var(--ui); font-size:.85rem; padding-left:1.4rem; }}
ol.refs li {{ margin-bottom:.4rem; }}
mjx-container {{ overflow-x:auto; overflow-y:hidden; }}
</style>
<script>window.MathJax = {{ tex: {{ inlineMath: [['$','$']], displayMath: [['\\\\[','\\\\]']] }}, svg: {{ fontCache: 'global' }} }};</script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/3.2.2/es5/tex-svg.js"></script>
<main>
<header>
<p class='authors' style='margin:0 0 .3rem'>Manuscript draft prepared for IEEE Transactions on Electron Devices</p>
<h1>{inline(title)}</h1>
<p class='authors'>M. Nisha Angeline — Department of ECE, Velalar College of Engineering and Technology, Thindal, Erode, India</p>
<p class='note'>All results in this draft were generated with the open-source mirror (ngspice 42 + NumPy) of the Verilog-A models; the Cadence Virtuoso/Spectre/ADE scripts for the identical flow are supplied in the companion repository and have not been executed here. Calibration targets are literature-anchored reference curves, not measurements.</p>
</header>
{chr(10).join(out)}
<h2>References</h2>
<ol class='refs'>{refs}</ol>
</main>
"""
    open(os.path.join(PAP, "manuscript.html"), "w").write(page)
    print("wrote paper/manuscript.html (%.1f MB)" % (len(page) / 1e6))


if __name__ == "__main__":
    main()
