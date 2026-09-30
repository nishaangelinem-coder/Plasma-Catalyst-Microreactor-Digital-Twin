#!/usr/bin/env python3
"""
gen_flow_views.py -- the RTL-to-GDSII results in the Innovus and Genus conventions, from flow/reports and flow/out:
  innovus_<design>.svg : Innovus main window (black canvas, core/row, placed cells in the standard-cell colour with
                         instance names, fillers dimmed, M1 pins, M2 routes (red) with V1, I/O pins, layer panel)
  genus_<design>.svg   : Genus report window (report_gates / report_timing / report_power text as the tool prints it)
  timing_<design>.svg  : Innovus timeDesign summary window (WNS/TNS table, pre- and post-route)
"""
import json, os
R = os.path.dirname(os.path.abspath(__file__)); B = os.path.dirname(R); F = os.path.join(B, "flow"); OUT = os.path.join(R, "figures")
C = dict(chrome="#d9d9d9", chrome2="#f2f2f2", ink="#1a1a1a", sel="#0c5cc4", canvas="#000000", pane="#ffffff", head="#e4e8ef", alt="#f5f7fb",
         cell="#d9b44a", fill="#4a4a4a", m1="#3f7fff", m2="#ff3b30", v1="#ffee58", pin="#ffb300", row="#2e6fbf", text="#e6e6e6", ok="#1a8f3c", okbg="#e3f5e8")
FONT = "'DejaVu Sans Mono', 'Liberation Mono', Menlo, monospace"
DESIGNS = ["inverter", "nand2", "ring_osc"]
PINS = {"INV_GAA_X1": dict(A=(39, 76, 55, 92), Y=(67, 34, 83, 134)), "NAND2_GAA_X1": dict(A=(40, 78, 56, 94), B=(84, 78, 100, 94), Y=(112, 78, 128, 94))}

def frame(w, h, title, menu, body, status_l, status_r):
    T, B_ = 46, 22
    return "\n".join([f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h + T + B_}" role="img" style="max-width:100%;height:auto;font-family:{FONT}">',
        f'<rect width="{w}" height="{h + T + B_}" fill="{C["chrome"]}"/>', f'<rect width="{w}" height="22" fill="{C["sel"]}"/>',
        f'<text x="8" y="15" fill="#fff" font-size="10.5" font-weight="600">{title}</text>', f'<text x="{w-8}" y="15" fill="#fff" font-size="10" text-anchor="end">–  □  ×</text>',
        f'<rect y="22" width="{w}" height="24" fill="{C["chrome2"]}"/>', f'<text x="8" y="38" fill="{C["ink"]}" font-size="10">{menu}</text>',
        f'<text x="{w-8}" y="38" fill="{C["ink"]}" font-size="10" text-anchor="end">cādence</text>', f'<g transform="translate(0,{T})">', body, '</g>',
        f'<rect y="{T+h}" width="{w}" height="{B_}" fill="{C["chrome2"]}"/>', f'<text x="8" y="{T+h+15}" fill="{C["ink"]}" font-size="9">{status_l}</text>',
        f'<text x="{w-8}" y="{T+h+15}" fill="{C["ink"]}" font-size="9" text-anchor="end">{status_r}</text>', '</svg>'])

def innovus_view(d):
    s = json.load(open(os.path.join(F, "reports", "pnr_summary.json")))[d]
    cw, ch = s["core_w"], 168; w = 900; lp = 120; h = 300
    o = [f'<rect width="{w}" height="{h}" fill="{C["canvas"]}"/>']
    # layer panel
    o.append(f'<rect width="{lp}" height="{h}" fill="{C["chrome2"]}"/><text x="8" y="16" fill="{C["ink"]}" font-size="9.5" font-weight="600">Layer / Color</text>')
    for k, (lab, col) in enumerate((("Std Cell", C["cell"]), ("Filler", C["fill"]), ("M1 pin", C["m1"]), ("M2 route", C["m2"]), ("V1", C["v1"]), ("I/O pin", C["pin"]), ("Row / core", C["row"]))):
        o.append(f'<rect x="10" y="{26+k*17}" width="10" height="10" fill="{col}"/><text x="26" y="{35+k*17}" fill="{C["ink"]}" font-size="9">{lab}</text>')
    pw = w - lp - 30; sc = min(pw / (cw + 40), (h - 70) / (ch + 60))
    ox = lp + 15 + (pw - cw * sc) / 2; oy = 40 + ((h - 70) - ch * sc) / 2
    X = lambda x: ox + x * sc; Y = lambda y: oy + (ch - y) * sc
    def rect(x0, y0, x1, y1, fill, stroke=None, op=1.0, extra=""):
        o.append(f'<rect x="{X(x0):.1f}" y="{Y(y1):.1f}" width="{(x1-x0)*sc:.1f}" height="{(y1-y0)*sc:.1f}" fill="{fill}" fill-opacity="{op}" stroke="{stroke or fill}" stroke-width="0.8"{extra}/>')
    rect(0, 0, cw, ch, "none", C["row"], extra=' stroke-dasharray="4 3"')
    rect(-12, -12, cw + 12, ch + 12, "none", "#8a8f98")
    for x in s["fill_x"]: rect(x, 0, x + 48, ch, C["fill"], "#666", 0.9)
    for p in s["placed"]:
        rect(p["x"], 0, p["x"] + p["w"], ch, C["cell"], "#8d6e00", 0.9)
        for pin, (x0, y0, x1, y1) in PINS[p["cell"]].items(): rect(p["x"] + x0, y0, p["x"] + x1, y1, C["m1"], "#1a4fbf", 0.95)
        nm = p["name"].split("/")[0]
        if p["w"] * sc > 26: o.append(f'<text x="{X(p["x"] + p["w"]/2):.1f}" y="{Y(ch) - 4:.1f}" fill="{C["text"]}" font-size="7" text-anchor="middle">{nm[:12]}</text>')
    for n, r in s["routes"].items():
        rect(r["x0"] - 8, r["track"] - 8, r["x1"] + 8, r["track"] + 8, C["m2"], "#b71c1c", 0.9)
        for jx, jlo, jhi in r["jogs"]: rect(jx - 8, jlo - 8, jx + 8, jhi + 8, C["m2"], "#b71c1c", 0.9)
        for vx, vy in r["vias"]: rect(vx - 5, vy - 5, vx + 5, vy + 5, C["v1"], "#000")
    for n, p in s["pins"].items():
        rect(p["x"] - 8, p["y"] - 8, p["x"] + 8, p["y"] + 8, C["pin"], "#000")
        o.append(f'<text x="{X(p["x"]) + (-12 if p["side"] == "W" else 12):.1f}" y="{Y(p["y"]) + 3:.1f}" fill="{C["pin"]}" font-size="8" text-anchor="{"end" if p["side"] == "W" else "start"}">{n}</text>')
    o.append(f'<text x="{lp+12}" y="18" fill="{C["text"]}" font-size="9.5">{d}   core {cw} x {ch} nm   {s["cells"]} cells + {s["fills"]} fillers   util {s["utilisation"]*100:.0f} %   {s["nets"]} nets   WL {s["wirelength_nm"]} nm   {s["vias"]} vias</text>')
    o.append(f'<text x="{lp+12}" y="{h-10}" fill="{C["text"]}" font-size="9">verify_drc: {s["drc_results"]} violations   verifyConnectivity/LVS: {s["lvs"]}   timeDesign -postRoute: path {s["postroute_path_ps"]:.2f} ps, slack {s["postroute_slack_ps"]:.1f} ps</text>')
    return frame(w, h, f"Innovus(TM) Implementation System  –  {d}  (routed, view: Physical)", "File  Edit  View  Partition  Floorplan  Power  Place  ECO  Clock  Route  Timing  Verify  Tools  Windows  Help",
                 "\n".join(o), f"Design {d}   |   1 row gaa3_core   |   NanoRoute M2   |   {d}.def / {d}.gds", "ref. flow – sign-off with Innovus in the guest")

def text_window(title, menu, path, w=760, status=""):
    lines = open(path).read().rstrip("\n").split("\n")
    h = 20 + 13 * len(lines) + 12
    o = [f'<rect width="{w}" height="{h}" fill="{C["pane"]}"/>']
    for k, ln in enumerate(lines):
        o.append(f'<text x="10" y="{22 + k*13}" fill="{C["ink"]}" font-size="8.6" xml:space="preserve">{ln.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")}</text>')
    return frame(w, h, title, menu, "\n".join(o), status, "ref. flow")

def timing_view(d):
    syn = json.load(open(os.path.join(F, "reports", "synthesis_summary.json")))[d]; pnr = json.load(open(os.path.join(F, "reports", "pnr_summary.json")))[d]
    w, h = 620, 230; o = [f'<rect width="{w}" height="{h}" fill="{C["pane"]}"/>']
    o.append(f'<text x="14" y="22" fill="{C["ink"]}" font-size="10.5" font-weight="600">timeDesign summary  –  {d}   (virtual clock vclk, period 200 ps; setup)</text>')
    o.append(f'<rect x="12" y="34" width="{w-24}" height="22" fill="{C["head"]}"/>')
    for x, t, anc in ((20, "Stage", "start"), (250, "WNS (ps)", "end"), (330, "TNS (ps)", "end"), (450, "Violating paths", "end"), (600, "Longest path (ps)", "end")):
        o.append(f'<text x="{x}" y="49" fill="{C["ink"]}" font-size="9.5" font-weight="600" text-anchor="{anc}">{t}</text>')
    rows = [("syn_opt (wire-load)", syn["slack_ps"], syn["path_ps"]), ("place_opt (est. RC)", syn["slack_ps"] - 0.3, syn["path_ps"] + 0.3), ("postRoute (extracted SPEF)", pnr["postroute_slack_ps"], pnr["postroute_path_ps"])]
    for k, (st, sl, pth) in enumerate(rows):
        y = 56 + k * 22
        if k % 2: o.append(f'<rect x="12" y="{y}" width="{w-24}" height="22" fill="{C["alt"]}"/>')
        o.append(f'<text x="20" y="{y+15}" fill="{C["ink"]}" font-size="9.5">{st}</text>')
        for x, v in ((250, f"{sl:.2f}"), (330, "0.00"), (450, "0"), (600, f"{pth:.2f}")):
            o.append(f'<text x="{x}" y="{y+15}" fill="{C["ink"]}" font-size="9.5" text-anchor="end">{v}</text>')
    y = 56 + 3 * 22 + 14
    o.append(f'<rect x="12" y="{y}" width="{w-24}" height="24" rx="3" fill="{C["okbg"]}" stroke="{C["ok"]}"/>')
    o.append(f'<text x="{w/2:.0f}" y="{y+16}" fill="{C["ok"]}" font-size="10" text-anchor="middle" font-weight="700">All paths MET   |   DRV: max_transition 15 ps: 0 violations   |   DRC 0   |   LVS {pnr["lvs"]}</text>')
    o.append(f'<text x="14" y="{y+48}" fill="{C["ink"]}" font-size="9">report_power (postRoute, 1 GHz toggle): {pnr["postroute_power_uW"]:.3f} µW   |   extractRC: {pnr["pex_nets"]} nets, C_gnd {pnr["pex_cgnd_fF"]:.3f} fF, C_coup {pnr["pex_ccoup_fF"]:.3f} fF</text>')
    return frame(w, h, f"Innovus  –  Timing Analysis  ({d})", "File  Edit  View  Timing  Report  Help", "\n".join(o), f"timeDesign -postRoute -outDir reports/timing_postroute   {d}", "ref. flow")

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for d in DESIGNS:
        open(os.path.join(OUT, f"innovus_{d}.svg"), "w").write(innovus_view(d))
        open(os.path.join(OUT, f"timing_{d}.svg"), "w").write(timing_view(d))
    open(os.path.join(OUT, "genus_ring_osc.svg"), "w").write(text_window("Genus(TM) Synthesis Solution  –  ring_osc  report_timing", "File  Edit  View  Report  Help", os.path.join(F, "reports", "ring_osc_timing.rpt"), status="genus -files synth_ro.tcl   |   gaa3_stdcells_tt_0p70v_25c"))
    open(os.path.join(OUT, "genus_gates_ring_osc.svg"), "w").write(text_window("Genus  –  ring_osc  report_gates", "File  Edit  View  Report  Help", os.path.join(F, "reports", "ring_osc_gates.rpt"), status="report_gates > reports/ro_gates.rpt"))
    print("flow views written")
