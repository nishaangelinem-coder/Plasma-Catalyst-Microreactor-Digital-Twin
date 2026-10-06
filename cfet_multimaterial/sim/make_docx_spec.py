"""Parse paper/main.tex (+ numbers.tex, tables, refs.bib) into a JSON block spec for the
Word builder (sim/build_docx.js), and render every display equation to PNG with LaTeX.
Run: python3 -m sim.make_docx_spec   -> paper/docx_build/spec.json, paper/docx_build/eq_*.png
"""
import os, re, json, subprocess, html
from .make_html import load_bib, fmt_ref

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAP = os.path.join(HERE, "paper"); OUT = os.path.join(PAP, "docx_build")
SEARCH = [os.path.join(HERE, "figures"), os.path.join(HERE, "schematics"), os.path.join(HERE, "layout", "png")]
MACROS, CITES, FIGNUM, TABNUM, EQNUM = {}, [], {}, {}, {}
GREEK = {"mu": "µ", "Omega": "Ω", "sigma": "σ", "lambda": "λ", "eta": "η", "beta": "β", "alpha": "α", "Delta": "Δ",
         "delta": "δ", "tau": "τ", "pi": "π", "theta": "θ", "epsilon": "ε", "rho": "ρ", "gamma": "γ", "phi": "φ", "omega": "ω"}
SYM = {"cdot": "·", "times": "×", "pm": "±", "geq": "≥", "leq": "≤", "approx": "≈", "to": "→", "rightarrow": "→", "infty": "∞",
       "propto": "∝", "ll": "≪", "gg": "≫", "neq": "≠", "circ": "°", "mathrm": "", "text": "", "emph": "", "quad": "  ", "ln": "ln", "exp": "exp", "tanh": "tanh", "max": "max"}

SYM.update({"int": "∫", "sum": "Σ", "log": "log", "partial": "∂", "langle": "⟨", "rangle": "⟩", "mid": "|", "sim": "~", "ldots": "…", "dots": "…"})


def braced(s, start):
    """Return (content, end_index) of the {...} group starting at s[start] == '{'."""
    depth = 0
    for j in range(start, len(s)):
        if s[j] == "{": depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0: return s[start + 1:j], j + 1
    return s[start + 1:], len(s)


def expand_cmd(s, name, fn):
    """Replace every \name{a}{b}... occurrence (n braced args, n = fn arity) using fn."""
    import inspect
    n = len(inspect.signature(fn).parameters)
    out = ""; i = 0
    while True:
        k = s.find("\\" + name + "{", i)
        if k < 0: out += s[i:]; return out
        out += s[i:k]; j = k + len(name) + 1; args = []
        for _ in range(n):
            while j < len(s) and s[j] in " \n": j += 1
            if j < len(s) and s[j] == "{":
                a, j = braced(s, j); args.append(a)
            else: args.append("")
        out += fn(*args); i = j


def cite(keys):
    nums = []
    for k in keys.split(","):
        k = k.strip()
        if k not in CITES: CITES.append(k)
        nums.append(str(CITES.index(k) + 1))
    return "[" + ", ".join(nums) + "]"


def math_runs(m, base):
    """Convert a LaTeX math fragment to runs with sub/superscripts (italic by default)."""
    runs = []
    s = m
    for _ in range(3):   # nested fractions / roots
        s = expand_cmd(s, "frac", lambda a, b: "(" + a + ")/(" + b + ")")
        s = expand_cmd(s, "tfrac", lambda a, b: "(" + a + ")/(" + b + ")")
        s = expand_cmd(s, "dfrac", lambda a, b: "(" + a + ")/(" + b + ")")
        s = expand_cmd(s, "sqrt", lambda a: "√(" + a + ")")
        s = expand_cmd(s, "mathrm", lambda a: a)
        s = expand_cmd(s, "text", lambda a: a)
    s = re.sub(r"\\bar\s*([A-Za-z])", lambda x: x.group(1) + "\u0304", s)
    s = re.sub(r"\\(left|right)\s*", "", s)
    s = re.sub(r"\\([A-Za-z]+)", lambda x: GREEK.get(x.group(1), SYM.get(x.group(1), x.group(0))), s)
    s = s.replace("\\,", " ").replace("\\!", "").replace("\;", " ").replace("~", " ").replace("\\{", "{").replace("\\}", "}")
    i = 0
    while i < len(s):
        c = s[i]
        if c in "_^":
            i += 1
            if i < len(s) and s[i] == "{":
                depth = 1; j = i + 1
                while j < len(s) and depth:
                    depth += {"{": 1, "}": -1}.get(s[j], 0); j += 1
                frag = s[i + 1:j - 1]; i = j
            else:
                frag = s[i]; i += 1
            frag = re.sub(r"[{}]", "", frag)
            runs.append(dict(base, text=frag, i=not frag.replace(".", "").replace(",", "").isdigit(), sub=(c == "_"), sup=(c == "^")))
        elif c in "{}":
            i += 1
        else:
            j = i
            while j < len(s) and s[j] not in "_^{}": j += 1
            frag = s[i:j]; i = j
            # letters italic, digits/operators upright
            for part in re.findall(r"[A-Za-z]+|[^A-Za-z]+", frag):
                runs.append(dict(base, text=part, i=bool(re.match(r"[A-Za-z]+$", part)) and part not in ("ln", "exp", "tanh", "max", "log")))
    return runs


def inline(s, base=None):
    """LaTeX inline text -> list of runs."""
    base = base or {}
    s = re.sub(r"\\([A-Za-z]+)(?=[^A-Za-z]|$)", lambda m: MACROS[m.group(1)] if m.group(1) in MACROS else m.group(0), s)
    s = s.replace("\\ucm", "UCM-CFET")
    s = re.sub(r"\\cite\{([^}]*)\}", lambda m: cite(m.group(1)), s)
    s = re.sub(r"\\ref\{fig:(\w+)\}", lambda m: FIGNUM.get(m.group(1), "?"), s)
    s = re.sub(r"\\ref\{tab:(\w+)\}", lambda m: TABNUM.get(m.group(1), "?"), s)
    s = re.sub(r"\\ref\{eq:(\w+)\}", lambda m: EQNUM.get(m.group(1), "?"), s)
    s = re.sub(r"\\IEEEPARstart\{(\w)\}\{(\w+)\}", r"\1\2", s)
    s = re.sub(r"\\(footnotesize|scriptsize|centering|balance|noindent)", "", s)
    s = s.replace("\\%", "%").replace("\\_", "_").replace("\\&", "&").replace("``", "“").replace("''", "”").replace("---", "—").replace("--", "–")
    s = s.replace("\\ ", " ").replace("~", "\u00a0").replace("\\\\", " ")
    runs = []
    pos = 0
    for m in re.finditer(r"\$([^$]+)\$|\\emph\{([^}]*)\}|\\textbf\{([^}]*)\}|\\texttt\{([^}]*)\}", s):
        if m.start() > pos:
            runs.append(dict(base, text=s[pos:m.start()]))
        if m.group(1) is not None:
            runs += math_runs(m.group(1), base)
        elif m.group(2) is not None:
            runs += inline(m.group(2), dict(base, i=True))
        elif m.group(3) is not None:
            runs += inline(m.group(3), dict(base, b=True))
        else:
            runs.append(dict(base, text=m.group(4).replace("\\_", "_"), mono=True))
        pos = m.end()
    if pos < len(s):
        runs.append(dict(base, text=s[pos:]))
    return [r for r in runs if r.get("text")]


def find_img(name):
    for d in SEARCH:
        p = os.path.join(d, name)
        if os.path.exists(p): return p
    return ""


def render_eq(latex, idx):
    """Render a display equation to a tight PNG via pdflatex standalone + pdftoppm."""
    tex = ("\\documentclass[preview,border=2pt]{standalone}\\usepackage{amsmath,amssymb}\\begin{document}"
           "\\begin{minipage}{3.3in}" + latex + "\\end{minipage}\\end{document}")
    base = os.path.join(OUT, f"eq_{idx}")
    open(base + ".tex", "w").write(tex)
    subprocess.run(["pdflatex", "-interaction=nonstopmode", "-output-directory", OUT, base + ".tex"], capture_output=True)
    subprocess.run(["pdftoppm", "-png", "-r", "400", "-singlefile", base + ".pdf", base], capture_output=True)
    for ext in (".tex", ".aux", ".log", ".pdf"):
        try: os.remove(base + ext)
        except OSError: pass
    return base + ".png"


def table_rows(tex):
    tex = re.sub(r"\\setlength\{[^}]*\}\{[^}]*\}", "", tex)
    tex = re.sub(r"\\(hline|toprule|midrule|bottomrule)", "", tex)
    k = tex.find("\\begin{tabular}")
    if k >= 0:
        _, j = braced(tex, tex.index("{", k + len("\\begin{tabular}")))   # skip the column spec (may nest braces)
        body = tex[j:tex.index("\\end{tabular}")]
    else:
        body = tex
    rows = [r.strip() for r in re.split(r"\\\\", body) if r.strip()]
    return [[inline(c.strip()) for c in r.split("&")] for r in rows]


def main():
    os.makedirs(OUT, exist_ok=True)
    tex = open(os.path.join(PAP, "main.tex")).read()
    for m in re.finditer(r"\\newcommand\{\\(\w+)\}\{([^}]*)\}", open(os.path.join(PAP, "numbers.tex")).read()):
        MACROS[m.group(1)] = m.group(2)
    bib = load_bib()
    title = re.search(r"\\title\{(.*?)\}\n", tex, re.S).group(1)
    body = tex[tex.index("\\maketitle"):tex.index("\\bibliographystyle")]
    for i, m in enumerate(re.finditer(r"\\label\{fig:(\w+)\}", body)): FIGNUM[m.group(1)] = str(i + 1)
    for i, m in enumerate(re.finditer(r"\\label\{tab:(\w+)\}", body)): TABNUM[m.group(1)] = "I II III IV V VI VII VIII".split()[i]
    for i, m in enumerate(re.finditer(r"\\label\{eq:(\w+)\}", body)): EQNUM[m.group(1)] = f"({i + 1})"
    blocks = []
    ab = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", body, re.S).group(1).strip()
    kw = re.search(r"\\begin\{IEEEkeywords\}(.*?)\\end\{IEEEkeywords\}", body, re.S).group(1).strip()
    blocks.append(dict(type="abstract", runs=inline(ab)))
    blocks.append(dict(type="keywords", runs=inline(kw)))
    body = body[body.index("\\end{IEEEkeywords}") + len("\\end{IEEEkeywords}"):]
    # tokenise floats / equations / headings / paragraphs in document order
    pattern = re.compile(r"(\\begin\{figure(\*?)\}\[!t\].*?\\end\{figure\*?\})|(\\begin\{table(\*?)\}\[!t\].*?\\end\{table\*?\})|"
                         r"(\\begin\{(equation|align)\}.*?\\end\{\6\})|(\\(sub)*section\{(?:[^{}]|\{[^{}]*\})*\})", re.S)
    pos = 0; eqi = 0; eqn = 0
    def flush(text):
        for c in re.split(r"\n\s*\n", text):
            c = c.strip()
            if c and not c.startswith("%"):
                blocks.append(dict(type="p", runs=inline(c)))
    for m in pattern.finditer(body):
        flush(body[pos:m.start()]); pos = m.end()
        tok = m.group(0)
        if tok.startswith("\\begin{figure"):
            wide = tok.startswith("\\begin{figure*}")
            imgs = [find_img(i) for i in re.findall(r"\\includegraphics\[[^\]]*\]\{([^}]*)\}", tok)]
            cap = re.search(r"\\caption\{(.*)\}\s*\\label\{fig:(\w+)\}", tok, re.S)
            blocks.append(dict(type="fig", wide=wide, imgs=imgs, num=FIGNUM.get(cap.group(2), "?"), caption=inline(cap.group(1))))
        elif tok.startswith("\\begin{table"):
            wide = tok.startswith("\\begin{table*}")
            cap = re.search(r"\\caption\{(.*?)\}\s*\\label\{tab:(\w+)\}", tok, re.S)
            inp = re.search(r"\\input\{([^}]*)\}", tok)
            ttex = open(os.path.join(PAP, inp.group(1))).read() if inp else tok
            blocks.append(dict(type="tab", wide=wide, num=TABNUM.get(cap.group(2), "?"), caption=inline(cap.group(1)), rows=table_rows(ttex)))
        elif tok.startswith("\\begin{equation") or tok.startswith("\\begin{align"):
            lab = re.search(r"\\label\{eq:(\w+)\}", tok)
            latex = re.sub(r"\n\s*\n", "\n", re.sub(r"\\label\{eq:\w+\}", "", tok))   # no blank lines inside align
            num = EQNUM.get(lab.group(1), "") if lab else ""
            if not num:
                eqn += 1; num = f"({len(EQNUM) + eqn})"
            eqi += 1
            # strip our own numbering: use equation* / align* and add the number as text
            latex = latex.replace("\\begin{equation}", "\\begin{equation*}").replace("\\end{equation}", "\\end{equation*}")
            latex = latex.replace("\\begin{align}", "\\begin{align*}").replace("\\end{align}", "\\end{align*}").replace("\\nonumber", "")
            blocks.append(dict(type="eq", png=render_eq(latex, eqi), num=num))
        else:
            level = tok.count("sub") + 1
            text, _ = braced(tok, tok.index("{"))
            blocks.append(dict(type=f"h{level}", runs=inline(text)))
    flush(body[pos:])
    # equation numbers: renumber sequentially in order of appearance (unlabelled ones included)
    k = 0
    for b in blocks:
        if b["type"] == "eq":
            k += 1; b["num"] = f"({k})"
    refs = [re.sub(r"<[^>]+>", "", html.unescape(fmt_ref(bib.get(key, {"title": key})))) for key in CITES]
    spec = dict(title=inline(title), author="M. Nisha Angeline", affiliation="Department of Electronics and Communication Engineering, Velalar College of Engineering and Technology, Thindal, Erode, Tamil Nadu, India (e-mail: nishavlsidesign@gmail.com)",
                journal="IEEE Transactions on Electron Devices", blocks=blocks, references=refs)
    json.dump(spec, open(os.path.join(OUT, "spec.json"), "w"), indent=0)
    print("blocks:", len(blocks), "equations:", eqi, "refs:", len(refs))


if __name__ == "__main__":
    main()
