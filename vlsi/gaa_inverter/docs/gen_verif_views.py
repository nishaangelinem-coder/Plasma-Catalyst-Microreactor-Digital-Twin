#!/usr/bin/env python3
"""
gen_verif_views.py -- DRC and LVS results drawn in the Pegasus / PVS results-viewer convention from the
JSON written by verify/gaa3_drc.py and verify/gaa3_lvs.py: a DRC Results Viewer window (rule tree with
per-rule violation counts and the layout marker pane) and an LVS Results window (object counts,
port map and the MATCH banner).  Renderings in the tool's style of the reference checker's results;
the sign-off run in the VMware guest produces the viewer's own captures.

    python3 gen_verif_views.py  -> figures/drc_{inv,nand2,ro11,sram6t}.svg, figures/lvs_{...}.svg, figures/drc_summary.svg
"""
import json, os
R = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(R, "figures"); VER = os.path.join(R, "..", "verify")
C = dict(chrome="#d9d9d9", chrome2="#f2f2f2", ink="#1a1a1a", sel="#0c5cc4", pane="#ffffff", alt="#f5f7fb", line="#c9ced6",
         ok="#1a8f3c", okbg="#e3f5e8", bad="#c62828", badbg="#fde8e8", head="#e4e8ef", canvas="#000000")
FONT = "'DejaVu Sans Mono', 'Liberation Mono', Menlo, monospace"
CELLS = [("inv", "gaa_inverter"), ("nand2", "gaa_nand2"), ("ro11", "gaa_ro11"), ("sram6t", "gaa_sram6t")]

def frame(w, h, title, menu, body, status_l, status_r):
    T, B = 46, 22
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h + T + B}" role="img" style="max-width:100%;height:auto;font-family:{FONT}">',
        f'<rect width="{w}" height="{h + T + B}" fill="{C["chrome"]}"/>', f'<rect width="{w}" height="22" fill="{C["sel"]}"/>',
        f'<text x="8" y="15" fill="#fff" font-size="10.5" font-weight="600">{title}</text>',
        f'<text x="{w-8}" y="15" fill="#fff" font-size="10" text-anchor="end">–  □  ×</text>',
        f'<rect y="22" width="{w}" height="24" fill="{C["chrome2"]}"/>', f'<text x="8" y="38" fill="{C["ink"]}" font-size="10">{menu}</text>',
        f'<text x="{w-8}" y="38" fill="{C["ink"]}" font-size="10" text-anchor="end">cādence</text>',
        f'<g transform="translate(0,{T})">', body, '</g>',
        f'<rect y="{T+h}" width="{w}" height="{B}" fill="{C["chrome2"]}"/>',
        f'<text x="8" y="{T+h+15}" fill="{C["ink"]}" font-size="9">{status_l}</text>',
        f'<text x="{w-8}" y="{T+h+15}" fill="{C["ink"]}" font-size="9" text-anchor="end">{status_r}</text>', '</svg>'])

def drc_view(key, base):
    d = json.load(open(os.path.join(VER, base + ".drc.json")))
    w, h = 760, 440; lw = 470
    o = [f'<rect width="{w}" height="{h}" fill="{C["pane"]}"/>']
    # left: rule tree
    o.append(f'<rect width="{lw}" height="{h}" fill="{C["pane"]}"/><rect width="{lw}" height="22" fill="{C["head"]}"/>')
    for x, t in ((8, "Rule"), (118, "Type"), (190, "Value"), (250, "Results"), (318, "Description")):
        o.append(f'<text x="{x}" y="15" fill="{C["ink"]}" font-size="9.5" font-weight="600">{t}</text>')
    o.append(f'<text x="8" y="36" fill="{C["ink"]}" font-size="9.5" font-weight="600">▾ {d["cell"]}   ({d["checked"]} checks, {d["total"]} results)</text>')
    rh = 14.2
    for i, r in enumerate(d["rules"]):
        y = 42 + i * rh
        if i % 2: o.append(f'<rect x="0" y="{y:.1f}" width="{lw}" height="{rh}" fill="{C["alt"]}"/>')
        col = C["ok"] if r["count"] == 0 else C["bad"]
        o.append(f'<rect x="20" y="{y+3:.1f}" width="8" height="8" fill="{col}"/>')
        o.append(f'<text x="34" y="{y+10.5:.1f}" fill="{C["ink"]}" font-size="8.8">{r["rule"]}</text>')
        o.append(f'<text x="118" y="{y+10.5:.1f}" fill="{C["ink"]}" font-size="8.8">{r["kind"]}</text>')
        o.append(f'<text x="212" y="{y+10.5:.1f}" fill="{C["ink"]}" font-size="8.8" text-anchor="end">{r["value"]}</text>')
        o.append(f'<text x="290" y="{y+10.5:.1f}" fill="{col}" font-size="8.8" text-anchor="end" font-weight="600">{r["count"]}</text>')
        o.append(f'<text x="318" y="{y+10.5:.1f}" fill="{C["ink"]}" font-size="8" >{r["desc"][:30]}</text>')
    o.append(f'<line x1="{lw}" y1="0" x2="{lw}" y2="{h}" stroke="{C["line"]}"/>')
    # right: layout marker pane (black canvas with the cell outline and any violation boxes)
    px, pw, ph = lw + 1, w - lw - 1, h
    o.append(f'<rect x="{px}" y="0" width="{pw}" height="{ph}" fill="{C["canvas"]}"/>')
    x0, y0, x1, y1 = d["bbox_nm"]; sc = min((pw - 30) / (x1 - x0), (ph - 60) / (y1 - y0))
    ox = px + 15 + ((pw - 30) - (x1 - x0) * sc) / 2; oy = 30 + ((ph - 60) - (y1 - y0) * sc) / 2
    X = lambda x: ox + (x - x0) * sc; Y = lambda y: oy + (y1 - y) * sc
    o.append(f'<rect x="{X(x0):.1f}" y="{Y(y1):.1f}" width="{(x1-x0)*sc:.1f}" height="{(y1-y0)*sc:.1f}" fill="none" stroke="#8a8f98" stroke-dasharray="4 3"/>')
    nb = 0
    for r in d["rules"]:
        for bx0, by0, bx1, by1 in r["boxes"]:
            nb += 1
            o.append(f'<rect x="{X(bx0):.1f}" y="{Y(by1):.1f}" width="{max((bx1-bx0)*sc,2):.1f}" height="{max((by1-by0)*sc,2):.1f}" fill="none" stroke="#ff3b30" stroke-width="1.5"/>')
    o.append(f'<text x="{px+8}" y="16" fill="#e6e6e6" font-size="9.5">{d["cell"]}  -  {d["gds"]}  ({(x1-x0):.0f} x {(y1-y0):.0f} nm)</text>')
    verdict = "DRC CLEAN" if d["total"] == 0 else f"{d['total']} VIOLATIONS"
    vc = C["ok"] if d["total"] == 0 else C["bad"]
    o.append(f'<rect x="{px+8}" y="{ph-28}" width="{pw-16}" height="20" rx="3" fill="{vc}"/>')
    o.append(f'<text x="{px+pw/2:.0f}" y="{ph-14}" fill="#fff" font-size="10.5" text-anchor="middle" font-weight="700">{verdict}: {d["total"]} results in {d["checked"]} rulechecks</text>')
    body = "\n".join(o)
    return frame(w, h, f"Pegasus DRC Results Viewer  –  {base}.drc.db  ({d['cell']})",
                 "File  View  Setup  Rules  Results  Highlight  Window  Help", body,
                 f"Rule deck {d['deck']}   |   {d['polygons']} polygons (flat)   |   errors highlighted on the layout pane",
                 "ref. checker – sign-off with Pegasus in the guest")

def lvs_view(key, base):
    r = json.load(open(os.path.join(VER, base + ".lvs.json")))
    w, h = 560, 330; o = [f'<rect width="{w}" height="{h}" fill="{C["pane"]}"/>']
    ok = r["result"] == "MATCH"
    o.append(f'<rect x="12" y="12" width="{w-24}" height="52" rx="4" fill="{C["okbg"] if ok else C["badbg"]}" stroke="{C["ok"] if ok else C["bad"]}" stroke-width="1.5"/>')
    o.append(f'<text x="{w/2:.0f}" y="36" fill="{C["ok"] if ok else C["bad"]}" font-size="18" text-anchor="middle" font-weight="700">{"LVS " + r["result"]}</text>')
    o.append(f'<text x="{w/2:.0f}" y="54" fill="{C["ink"]}" font-size="9.5" text-anchor="middle">Layout cell {r["layout_cell"]}  vs  schematic cell {r["schematic_cell"]}</text>')
    o.append(f'<rect x="12" y="78" width="{w-24}" height="22" fill="{C["head"]}"/>')
    for x, t, anc in ((20, "Object", "start"), (260, "Layout", "end"), (360, "Schematic", "end"), (400, "Status", "start")):
        o.append(f'<text x="{x}" y="93" fill="{C["ink"]}" font-size="9.5" font-weight="600" text-anchor="{anc}">{t}</text>')
    rows = [("Ports", "ports"), ("Nets", "nets"), ("Instances", "instances"), ("   NMOS  nsheet_n", "n"), ("   PMOS  nsheet_p", "p")]
    for i, (lab, k) in enumerate(rows):
        y = 100 + i * 20; a, b = r["layout"][k], r["schematic"][k]
        if i % 2: o.append(f'<rect x="12" y="{y}" width="{w-24}" height="20" fill="{C["alt"]}"/>')
        o.append(f'<text x="20" y="{y+14}" fill="{C["ink"]}" font-size="9.5">{lab}</text>')
        o.append(f'<text x="260" y="{y+14}" fill="{C["ink"]}" font-size="9.5" text-anchor="end">{a}</text>')
        o.append(f'<text x="360" y="{y+14}" fill="{C["ink"]}" font-size="9.5" text-anchor="end">{b}</text>')
        good = a == b
        o.append(f'<text x="400" y="{y+14}" fill="{C["ok"] if good else C["bad"]}" font-size="9.5" font-weight="600">{"✓ matched" if good else "✗ different"}</text>')
    y = 100 + len(rows) * 20 + 12
    o.append(f'<text x="20" y="{y}" fill="{C["ink"]}" font-size="9.5" font-weight="600">Port map</text>')
    o.append(f'<text x="20" y="{y+16}" fill="{C["ink"]}" font-size="9">layout    : {", ".join(r["layout"]["port_names"])}</text>')
    o.append(f'<text x="20" y="{y+30}" fill="{C["ink"]}" font-size="9">schematic : {", ".join(r["schematic"]["port_names"])}</text>')
    o.append(f'<text x="20" y="{y+50}" fill="{C["ink"]}" font-size="9">device classes: {"match" if r["device_classes_match"] else "MISMATCH"}   net classes: {"match" if r["net_classes_match"] else "MISMATCH"}   unrecognised devices: {r["layout"]["unrecognised"]}</text>')
    body = "\n".join(o)
    return frame(w, h, f"Pegasus LVS  –  Comparison Results  ({r['layout_cell']})",
                 "File  View  Setup  Extraction  Comparison  Reports  Window  Help", body,
                 f"{base}.lvs.rpt   |   virtual connect: VDD VSS", "ref. extractor – sign-off with Pegasus in the guest")

def pex_view(key, base):
    p = json.load(open(os.path.join(VER, base + ".pex.json")))
    nets = [(n, x) for n, x in sorted(p["nets"].items()) if not x.get("floating")]
    w, h = 760, 96 + 20 * len(nets) + 60; o = [f'<rect width="{w}" height="{h}" fill="{C["pane"]}"/>']
    t = p["totals"]
    o.append(f'<rect x="12" y="10" width="{w-24}" height="44" rx="3" fill="{C["head"]}"/>')
    o.append(f'<text x="20" y="27" fill="{C["ink"]}" font-size="10" font-weight="600">Cell {p["cell"]}   extraction: rc_coupled   technology: GAA3 PEX (ILD k = 2.9, spacer k = 4.5)</text>')
    o.append(f'<text x="20" y="45" fill="{C["ink"]}" font-size="9.5">nets {t["nets"]}   devices {p["devices"]}   capacitors {t["capacitors"]}   resistors {t["resistors"]}   '
             f'C_gnd {t["cgnd_aF"]/1e3:.3f} fF   C_coupling {t["ccoup_aF"]/1e3:.3f} fF</text>')
    o.append(f'<rect x="12" y="64" width="{w-24}" height="22" fill="{C["head"]}"/>')
    for x, tt, anc in ((20, "Net", "start"), (200, "C_gnd (aF)", "end"), (300, "C_coup (aF)", "end"), (400, "C_total (aF)", "end"), (480, "R (Ω)", "end"), (500, "coupled to", "start")):
        o.append(f'<text x="{x}" y="79" fill="{C["ink"]}" font-size="9.5" font-weight="600" text-anchor="{anc}">{tt}</text>')
    for i, (n, x) in enumerate(nets):
        y = 86 + i * 20
        if i % 2: o.append(f'<rect x="12" y="{y}" width="{w-24}" height="20" fill="{C["alt"]}"/>')
        cc = sum(x["coup_aF"].values())
        o.append(f'<text x="20" y="{y+14}" fill="{C["ink"]}" font-size="9.5">{n}</text>')
        for xx, val in ((200, f"{x['cgnd_aF']:.1f}"), (300, f"{cc:.1f}"), (400, f"{x['ctotal_aF']:.1f}"), (480, f"{x['r_ohm']:.0f}")):
            o.append(f'<text x="{xx}" y="{y+14}" fill="{C["ink"]}" font-size="9.5" text-anchor="end">{val}</text>')
        cp = ", ".join(f"{m}: {c:.1f}" for m, c in x["coup_aF"].items() if not m.startswith("float"))[:44]
        o.append(f'<text x="500" y="{y+14}" fill="{C["ink"]}" font-size="8.5">{cp}</text>')
    y = 86 + len(nets) * 20 + 16
    o.append(f'<rect x="12" y="{y}" width="{w-24}" height="26" rx="3" fill="{C["okbg"]}" stroke="{C["ok"]}"/>')
    o.append(f'<text x="{w/2:.0f}" y="{y+17}" fill="{C["ok"]}" font-size="10.5" text-anchor="middle" font-weight="700">Extraction complete: {base}.spef written  (IEEE 1481 SPEF, C_UNIT 1 FF, R_UNIT 1 OHM)</text>')
    return frame(w, h, f"Quantus QRC  –  Extraction Summary  ({p['cell']})", "File  View  Setup  Extraction  Reports  Tools  Window  Help",
                 "\n".join(o), f"{base}.pex.sum   |   qrc -cmd gaa3_qrc.ccl   |   decoupled ground: VDD VSS", "ref. extractor – sign-off with Quantus QRC in the guest")

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for key, base in CELLS:
        open(os.path.join(OUT, f"pex_{key}.svg"), "w").write(pex_view(key, base))
    for key, base in CELLS:
        open(os.path.join(OUT, f"drc_{key}.svg"), "w").write(drc_view(key, base))
        open(os.path.join(OUT, f"lvs_{key}.svg"), "w").write(lvs_view(key, base))
    print("verification views written")
