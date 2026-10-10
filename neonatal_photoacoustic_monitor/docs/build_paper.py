"""Number [@key] citations in order of first appearance, append the reference list,
export DOCX (pandoc) and PDF (LibreOffice)."""
import re, os, sys, subprocess, shutil
sys.path.insert(0, os.path.dirname(__file__))
from references import REFS
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "PAPER_DRAFT.md"), encoding="utf-8").read()
order = []
def repl(m):
    keys = [k.strip().lstrip("@") for k in re.split(r"[;,]", m.group(1)) if k.strip()]
    nums = []
    for k in keys:
        if k not in REFS:
            raise SystemExit(f"unknown reference key {k}")
        if k not in order:
            order.append(k)
        nums.append(order.index(k) + 1)
    nums = sorted(nums)
    # compress runs
    out, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        out.append(f"{nums[i]}" if j == i else (f"{nums[i]}, {nums[j]}" if j == i + 1 else f"{nums[i]}–{nums[j]}"))
        i = j + 1
    return "[" + ", ".join(out) + "]"
body = re.sub(r"\[@([^\]]+)\]", repl, src)
refs = "\n\n".join(f"[{i+1}] {REFS[k]}" for i, k in enumerate(order))
body = body.replace("<<REFERENCES>>", refs)
out_md = os.path.join(HERE, "PAPER_photon_to_phonon_neonatal_monitor.md")
open(out_md, "w", encoding="utf-8").write(body)
print("markdown written:", out_md, f"({len(order)} references, {len(body.split())} words)")
docx = out_md.replace(".md", ".docx")
subprocess.run(["pandoc", os.path.basename(out_md), "-o", os.path.basename(docx), f"--resource-path=.:..:{os.path.join(HERE, '..', 'figures')}"], check=True, cwd=HERE)
print("docx written:", docx)
r = subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", HERE, docx], capture_output=True, text=True)
print(r.stdout[-300:], r.stderr[-300:])
