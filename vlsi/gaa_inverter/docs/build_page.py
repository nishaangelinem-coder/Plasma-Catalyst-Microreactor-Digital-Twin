#!/usr/bin/env python3
"""build_page.py -- assemble gaa_inverter_paper.html from template.html, figures, listings and results."""
import html, json, os
R = os.path.dirname(os.path.abspath(__file__)); B = os.path.dirname(R)
def rd(p): return open(os.path.join(B, p), encoding="utf-8").read()
res = json.load(open(os.path.join(B, "spectre/results.json")))
fin = json.load(open(os.path.join(B, "spectre/results_finfet.json")))
ro_g = json.load(open(os.path.join(B, "spectre/results_ro.json")))
ro_f = json.load(open(os.path.join(B, "spectre/results_ro_finfet.json")))
tpl = rd("docs/template.html")

# ---------------- Fig. 1: device cross-sections (hand-drawn SVG, theme tokens) ----------------
def device_svg():
    o = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 300" role="img" style="max-width:100%;height:auto;font-family:var(--font-ui);font-size:11.5px">']
    o.append('<defs><pattern id="sp" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="5" stroke="var(--ink-3)" stroke-width="1"/></pattern></defs>')
    # ---- left: cut along the gate (across sheets): sheets wrapped by gate metal
    x0, y0, w, h = 40, 40, 300, 210
    o.append(f'<rect x="{x0}" y="{y0+150}" width="{w}" height="60" fill="var(--bg-3)" stroke="var(--ink-3)"/>')
    o.append(f'<text x="{x0+w/2}" y="{y0+185}" text-anchor="middle" fill="var(--ink-2)">Si substrate / bottom dielectric isolation</text>')
    # gate metal body
    gx, gy, gw, gh = x0+60, y0+8, 180, 142
    o.append(f'<rect x="{gx}" y="{gy}" width="{gw}" height="{gh}" fill="var(--c2)" fill-opacity="0.25" stroke="var(--c2)"/>')
    # sheets: 3 stacked, width 120 (=30nm scaled 4x), thickness 20 (=5nm), spacing 36 (=9nm)
    sw, st, sp = 120, 20, 36
    sx = gx + (gw - sw)/2
    for i in range(3):
        sy = gy + 18 + i*(st+sp)
        # high-k liner
        o.append(f'<rect x="{sx-5}" y="{sy-5}" width="{sw+10}" height="{st+10}" fill="var(--accent)" fill-opacity="0.35" stroke="none"/>')
        o.append(f'<rect x="{sx}" y="{sy}" width="{sw}" height="{st}" fill="var(--c1)" stroke="var(--ink)" stroke-width="0.8"/>')
        o.append(f'<text x="{sx+sw/2}" y="{sy+14}" text-anchor="middle" fill="#fff" font-size="10">Si nanosheet {3-i}</text>')
    # dimension labels
    top = gy + 18
    o.append(f'<line x1="{sx}" y1="{top-12}" x2="{sx+sw}" y2="{top-12}" stroke="var(--ink)" marker-start="url(#a)"/>')
    o.append(f'<text x="{sx+sw/2}" y="{top-16}" text-anchor="middle" fill="var(--ink)">W_NS = 30 nm (N) / 45 nm (P)</text>')
    o.append(f'<line x1="{sx+sw+22}" y1="{top}" x2="{sx+sw+22}" y2="{top+st}" stroke="var(--ink)"/>')
    o.append(f'<text x="{sx+sw+28}" y="{top+st/2+4}" fill="var(--ink)">T_NS = 5 nm</text>')
    o.append(f'<line x1="{sx+sw+22}" y1="{top+st}" x2="{sx+sw+22}" y2="{top+st+sp}" stroke="var(--ink)" stroke-dasharray="2 2"/>')
    o.append(f'<text x="{sx+sw+28}" y="{top+st+sp/2+4}" fill="var(--ink)">T_SP = 9 nm</text>')
    o.append(f'<text x="{gx+8}" y="{gy+gh-8}" fill="var(--c2)" font-weight="600">HK/MG gate (wraps 4 sides)</text>')
    o.append(f'<text x="{x0+w/2}" y="{y0+h+30}" text-anchor="middle" fill="var(--ink-2)">(a) cut along the gate: 3 sheets, W_eff = N·2(W_NS + T_NS)</text>')
    # ---- right: cut along the channel: S - gate - D with inner spacers
    X0 = 400; Y0 = 40
    o.append(f'<rect x="{X0}" y="{Y0+150}" width="320" height="60" fill="var(--bg-3)" stroke="var(--ink-3)"/>')
    o.append(f'<text x="{X0+160}" y="{Y0+185}" text-anchor="middle" fill="var(--ink-2)">bottom dielectric isolation</text>')
    # S/D epi
    for (ex, lab) in ((X0+10, "S"), (X0+220, "D")):
        o.append(f'<rect x="{ex}" y="{Y0+10}" width="90" height="140" fill="var(--bg-3)" stroke="var(--ink-2)" rx="2"/>')
        o.append(f'<rect x="{ex}" y="{Y0+10}" width="90" height="140" fill="url(#sp)"/>')
        o.append(f'<text x="{ex+45}" y="{Y0+32}" text-anchor="middle" fill="var(--ink)" font-weight="600">{lab} epi</text>')
    # gate column with sheets crossing
    gx2, gw2 = X0+120, 80
    o.append(f'<rect x="{gx2}" y="{Y0}" width="{gw2}" height="150" fill="var(--c2)" fill-opacity="0.25" stroke="var(--c2)"/>')
    for i in range(3):
        sy = Y0 + 25 + i*(20+22)
        o.append(f'<rect x="{X0+100}" y="{sy}" width="120" height="20" fill="var(--c1)" stroke="var(--ink)" stroke-width="0.8"/>')
        # inner spacers between sheets on both sides
        if i < 2:
            for spx in (X0+100, X0+200):
                o.append(f'<rect x="{spx}" y="{sy+20}" width="20" height="22" fill="var(--ink-3)" fill-opacity="0.5"/>')
    o.append(f'<line x1="{gx2}" y1="{Y0-8}" x2="{gx2+gw2}" y2="{Y0-8}" stroke="var(--ink)"/>')
    o.append(f'<text x="{gx2+gw2/2}" y="{Y0-12}" text-anchor="middle" fill="var(--ink)">L_g = 14 nm</text>')
    o.append(f'<text x="{gx2+gw2/2}" y="{Y0+142}" text-anchor="middle" fill="var(--c2)" font-weight="600">gate</text>')
    o.append(f'<text x="{X0+110}" y="{Y0+165+40}" fill="var(--ink-2)" font-size="10">inner spacer</text>')
    o.append(f'<text x="{X0+160}" y="{Y0+210+30}" text-anchor="middle" fill="var(--ink-2)">(b) cut along the channel: source / wrapped gate / drain</text>')
    # legend
    o.append('<g transform="translate(40,282)">'
             '<rect width="12" height="12" fill="var(--c1)"/><text x="16" y="10" fill="var(--ink-2)">Si channel</text>'
             '<rect x="90" width="12" height="12" fill="var(--c2)" fill-opacity="0.25" stroke="var(--c2)"/><text x="106" y="10" fill="var(--ink-2)">work-function metal gate</text>'
             '<rect x="260" width="12" height="12" fill="var(--accent)" fill-opacity="0.35"/><text x="276" y="10" fill="var(--ink-2)">high-k (EOT 0.9 nm)</text>'
             '<rect x="400" width="12" height="12" fill="var(--ink-3)" fill-opacity="0.5"/><text x="416" y="10" fill="var(--ink-2)">inner spacer</text></g>')
    o.append('</svg>')
    return "\n".join(o)

# ---------------- listings ----------------
LISTINGS = [
    ("1", "rtl/inverter.v", "RTL of the inverter (Verilog-2005)", False),
    ("2", "genus/constraints.sdc", "Timing constraints", False),
    ("3", "spectre/gaa_inv_tb.scs", "Spectre testbench with BSIM-CMG nanosheet model cards", False),
    ("4", "genus/synth.tcl", "Genus synthesis script", False),
    ("5", "innovus/pnr.tcl", "Innovus place-and-route and GDSII stream-out script", False),
    ("5b", "innovus/mmmc.tcl", "Multi-mode multi-corner setup", True),
    ("6", "layout/gen_gaa_inverter_gds.py", "Dependency-free GDSII writer and INV_GAA_X1 layout generator", True),
    ("7", "layout/streamout_virtuoso.il", "Virtuoso SKILL stream-out", False),
    ("7b", "layout/gaa3.layermap", "Layer map", True),
    ("8", "README.md", "VMware Workstation guest set-up and run commands", True),
    ("9", "rtl/inverter_tb.v", "Self-checking testbench (RTL and gate level)", True),
    ("10", "spectre/ref_model.py", "Reference compact model and figure generator", True),
    ("11", "spectre/gaa_ro11_tb.scs", "Spectre testbench: 11-stage FO3 ring oscillator with supply sweep", False),
    ("12", "rtl/ring_osc.v", "Ring-oscillator RTL with preserved stages", False),
    ("12b", "genus/synth_ro.tcl", "Genus script preserving the oscillator loop", True),
    ("13", "layout/gen_gaa_ro_gds.py", "Hierarchical RO11 GDSII generator (SREF placement and M2 wiring)", True),
    ("14", "spectre/ro.py", "Ring-oscillator reference simulation and figures", True),
]
def listing(num, path, title, collapsed):
    code = html.escape(rd(path))
    bar = f'<div class="bar"><span>Listing {num}. {html.escape(title)} · <code>{path}</code></span><button type="button" data-copy>Copy</button></div>'
    if collapsed:
        return (f'<details class="listing" id="lst{num}"><summary><span>Listing {num}. {html.escape(title)} · <code>{path}</code></span></summary>'
                f'<div class="bar"><span>{len(code.splitlines())} lines</span><button type="button" data-copy>Copy</button></div><pre>{code}</pre></details>')
    return f'<div class="listing" id="lst{num}">{bar}<pre>{code}</pre></div>'

# ---------------- FinFET comparison numbers ----------------
def finfet_sub():
    fd, fs, ff4 = fin["device"], fin["static"], fin["fo4"]
    g4 = res["fo4"]
    skew_f = abs(ff4["tpHL"] - ff4["tpLH"]) * 1e12
    skew_g = abs(g4["tpHL"] - g4["tpLH"]) * 1e12
    edp_f = ff4["E_cycle"] * 1e15 * ff4["tpd"] * 1e12
    edp_g = g4["E_cycle"] * 1e15 * g4["tpd"] * 1e12
    de = (g4["E_cycle"] - ff4["E_cycle"]) / ff4["E_cycle"] * 100
    return {
        "F_IONN": f"{fd['n']['Ion_uA']:.0f}", "F_IONP": f"{fd['p']['Ion_uA']:.0f}",
        "F_IOFFN": f"{fd['n']['Ioff_nA']:.1f}", "F_IOFFP": f"{fd['p']['Ioff_nA']:.1f}",
        "F_PN": f"{fd['p']['Ion_uA']/fd['n']['Ion_uA']:.2f}", "G_PN": f"{res['device']['p']['Ion_uA']/res['device']['n']['Ion_uA']:.2f}",
        "F_VM": f"{fs['VM']*1e3:.0f}", "F_GAIN": f"{-fs['gain_max']:.0f}",
        "F_NML": f"{fs['NML']*1e3:.0f}", "F_NMH": f"{fs['NMH']*1e3:.0f}",
        "F_TPHL4": f"{ff4['tpHL']*1e12:.2f}", "F_TPLH4": f"{ff4['tpLH']*1e12:.2f}", "F_TPD4": f"{ff4['tpd']*1e12:.2f}",
        "F_ECYC4": f"{ff4['E_cycle']*1e15:.2f}", "F_PSTAT": f"{fin['P_static_pW']/1e3:.2f}",
        "F_SKEW": f"{skew_f:.2f}", "G_SKEW": f"{skew_g:.2f}",
        "F_EDP": f"{edp_f:.2f}", "G_EDP": f"{edp_g:.2f}",
        "TPD_GAIN": f"{(1 - g4['tpd']/ff4['tpd'])*100:.0f}", "AREA_GAIN": f"{(1 - res['area_um2']/fin['area_um2'])*100:.0f}",
        "EDP_GAIN": f"{(1 - edp_g/edp_f)*100:.0f}",
        "E_DELTA": (f"+{de:.0f} %" if de >= 0 else f"−{-de:.0f} %"),
    }

# ---------------- ring-oscillator numbers ----------------
def ro_sub():
    gn, fn = ro_g["nominal"], ro_f["nominal"]
    g_lo = ro_g["sweep"][0]; f_lo = ro_f["sweep"][0]
    edp_g = gn["E_stage_J"] * gn["t_stage_s"]; edp_f = fn["E_stage_J"] * fn["t_stage_s"]
    rows = []
    for a, b in zip(ro_g["sweep"], ro_f["sweep"]):
        rows.append(f'            <tr><td>{a["VDD"]:.2f} V</td><td class="n">{a["f_Hz"]/1e9:.1f} GHz</td><td class="n">{a["t_stage_s"]*1e12:.2f} ps</td>'
                    f'<td class="n">{a["P_W"]*1e6:.1f} µW</td><td class="n">{a["E_stage_J"]*1e18:.0f} aJ</td>'
                    f'<td class="n">{b["f_Hz"]/1e9:.1f} GHz</td><td class="n">{b["t_stage_s"]*1e12:.2f} ps</td><td class="n">{b["P_W"]*1e6:.1f} µW</td>'
                    f'<td class="n">+{(a["f_Hz"]/b["f_Hz"]-1)*100:.0f} %</td></tr>')
    return {
        "RO_CNODE": f"{ro_g['C_node_fF']:.2f}",
        "RO_F": f"{gn['f_Hz']/1e9:.1f}", "RO_TS": f"{gn['t_stage_s']*1e12:.2f}", "RO_P": f"{gn['P_W']*1e6:.0f}", "RO_E": f"{gn['E_stage_J']*1e18:.0f}",
        "RO_FF": f"{fn['f_Hz']/1e9:.1f}", "RO_TSF": f"{fn['t_stage_s']*1e12:.2f}",
        "RO_FGAIN": f"{(gn['f_Hz']/fn['f_Hz']-1)*100:.0f}", "RO_FGAIN_LO": f"{(g_lo['f_Hz']/f_lo['f_Hz']-1)*100:.0f}",
        "RO_EDPGAIN": f"{(1-edp_g/edp_f)*100:.0f}",
        "RO_ROWS": "\n".join(rows),
        "FIG_RO_WAVE": rd("spectre/fig_ro_wave.svg"), "FIG_RO_FVDD": rd("spectre/fig_ro_fvdd.svg"),
        "FIG_RO_PVDD": rd("spectre/fig_ro_pvdd.svg"), "FIG_RO_LAYOUT": rd("layout/gaa_ro11.svg"),
    }

# ---------------- numbers ----------------
d, st, f1, f4 = res["device"], res["static"], res["fo1"], res["fo4"]
mv = lambda v: f"{v*1e3:.0f}"
ps = lambda v: f"{v*1e12:.2f}"
fj = lambda v: f"{v*1e15:.2f}"
sub = {
    "VM": mv(st["VM"]), "GAIN": f"{-st['gain_max']:.0f}", "VIL": mv(st["VIL"]), "VIH": mv(st["VIH"]),
    "VOH": mv(st["VOH"]), "VOL": mv(st["VOL"]), "NML": mv(st["NML"]), "NMH": mv(st["NMH"]),
    "VMPCT": f"{st['VM']/res['VDD']*100:.0f}",
    "VTHN": f"{d['n']['vth']:.2f}", "VTHP": f"{d['p']['vth']:.2f}", "SSN": f"{d['n']['SS_mV_dec']:.0f}", "SSP": f"{d['p']['SS_mV_dec']:.0f}",
    "IONN": f"{d['n']['Ion_uA']:.0f}", "IONP": f"{d['p']['Ion_uA']:.0f}", "IOFFN": f"{d['n']['Ioff_nA']:.1f}", "IOFFP": f"{d['p']['Ioff_nA']:.1f}",
    "RATN": f"{d['n']['Ion_Ioff']/1e3:.0f}", "RATP": f"{d['p']['Ion_Ioff']/1e3:.0f}",
    "TPHL1": ps(f1["tpHL"]), "TPLH1": ps(f1["tpLH"]), "TPD1": ps(f1["tpd"]), "TF1": ps(f1["tfall"]), "TR1": ps(f1["trise"]), "ECYC1": fj(f1["E_cycle"]),
    "TPHL4": ps(f4["tpHL"]), "TPLH4": ps(f4["tpLH"]), "TPD4": ps(f4["tpd"]), "TF4": ps(f4["tfall"]), "TR4": ps(f4["trise"]), "ECYC4": fj(f4["E_cycle"]),
    "PDYN1": f"{f1['E_cycle']*1e9*1e6:.2f}", "PDYN4": f"{f4['E_cycle']*1e9*1e6:.2f}",
    "PSTAT": f"{res['P_static_pW']/1e3:.2f}", "DYNSTAT": f"{f4['E_cycle']*1e9/(res['P_static_pW']*1e-12):.0f}",
    **finfet_sub(),
    **ro_sub(),
    "FIG_DEVICE": device_svg(), "FIG_LAYOUT": rd("layout/gaa_inverter.svg"),
    "FIG_IDVG": rd("spectre/fig_idvg.svg"), "FIG_VTC": rd("spectre/fig_vtc.svg"),
    "FIG_GAIN": rd("spectre/fig_gain.svg"), "FIG_TRAN": rd("spectre/fig_tran.svg"),
    "LISTINGS": "\n".join(listing(*l) for l in LISTINGS),
}
out = tpl
for k, v in sub.items():
    out = out.replace("{{" + k + "}}", v)
import re
left = re.findall(r"\{\{[A-Z0-9_]+\}\}", out)
assert not left, left
open(os.path.join(R, "gaa_inverter_paper.html"), "w", encoding="utf-8").write(out)
print("built gaa_inverter_paper.html", len(out), "bytes")
for k in ("VM","GAIN","NML","NMH","TPD4","ECYC4","PSTAT","DYNSTAT","IOFFN","RATN"): print(k, sub[k])
