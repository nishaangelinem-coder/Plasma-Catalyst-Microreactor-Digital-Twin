#!/usr/bin/env python3
"""build_page.py -- assemble gaa_inverter_paper.html from template.html, figures, listings and results."""
import html, json, os
R = os.path.dirname(os.path.abspath(__file__)); B = os.path.dirname(R)
def rd(p): return open(os.path.join(B, p), encoding="utf-8").read()
res = json.load(open(os.path.join(B, "spectre/results.json")))
fin = json.load(open(os.path.join(B, "spectre/results_finfet.json")))
ro_g = json.load(open(os.path.join(B, "spectre/results_ro.json")))
ro_f = json.load(open(os.path.join(B, "spectre/results_ro_finfet.json")))
nd_g = json.load(open(os.path.join(B, "spectre/results_nand2.json")))
nd_f = json.load(open(os.path.join(B, "spectre/results_nand2_finfet.json")))
sr_g = json.load(open(os.path.join(B, "spectre/results_sram6t.json")))
sr_f = json.load(open(os.path.join(B, "spectre/results_sram6t_finfet.json")))
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
    ("15", "spectre/gaa_nand2_tb.scs", "Spectre testbench: NAND2 with width-swapped BSIM-CMG cards", False),
    ("16", "rtl/nand2.v", "NAND2 RTL", False),
    ("16b", "rtl/nand2_tb.v", "NAND2 truth-table testbench", True),
    ("17", "layout/gen_gaa_nand2_gds.py", "NAND2_GAA_X1 GDSII generator", True),
    ("18", "spectre/nand2.py", "NAND2 reference simulation (stack node, leakage by state)", True),
    ("19", "spectre/gaa_sram6t_tb.scs", "Spectre testbench: 6T bitcell butterfly, write, read, leakage, supply sweep", False),
    ("20", "layout/gen_gaa_sram6t_gds.py", "SRAM6T_GAA_HD thin-cell GDSII generator", True),
    ("21", "spectre/sram6t.py", "6T bitcell reference analysis (SNM, write trip, read current)", True),
    ("22", "docs/gen_schematics.py", "Schematic symbol library and the four schematics of Fig. 2", True),
    ("23", "docs/gen_schematics_virtuoso.py", "Virtuoso-convention schematic renderings of Fig. 3", True),
    ("24", "docs/render_pngs.py", "PNG rendering of all schematics, waveforms and layouts (headless Chromium)", True),
    ("25", "docs/gen_viva.py", "ViVA-convention waveform panels of Fig. 9", True),
    ("26", "verify/gaa3_drc.py", "GAA3 design-rule deck and reference DRC checker (gdstk booleans)", True),
    ("27", "verify/gaa3_lvs.py", "Reference LVS: device extraction from GDSII and comparison with the Spectre subcircuit", True),
    ("28", "verify/ro11_sch.scs", "Schematic netlist of the ring for LVS", True),
    ("29", "verify/gaa3_drc_all.sum", "DRC summary reports of the four cells (final pass)", True),
    ("30", "verify/gaa3_lvs_all.rpt", "LVS comparison reports of the four cells", True),
    ("31", "verify/run_all.sh", "One-command regeneration of the GDSII cells, DRC and LVS", True),
    ("32", "docs/gen_verif_views.py", "Pegasus-convention DRC/LVS/QRC results-viewer renderings of Figs. 16-18", True),
    ("33", "verify/gaa3_qrc.ccl", "Quantus QRC command file for the sign-off extraction", False),
    ("34", "verify/gaa3_pex.py", "Reference parasitic extractor (GAA3 PEX technology table, SPEF writer)", True),
    ("35", "verify/gaa_inverter.spef", "Extracted SPEF of INV_GAA_X1", True),
    ("35b", "verify/gaa3_pex_all.sum", "Extraction summaries of the four cells", True),
    ("36", "spectre/postlayout.py", "Post-layout simulation with the extracted RC", True),
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

# ---------------- NAND2 numbers ----------------
def nand_sub():
    def one(r, p):
        ps = lambda v: f"{v*1e12:.2f}"
        worst = max(r["fo4"][m][k] for m in ("A", "B") for k in ("tpHL", "tpLH"))
        return {
            p + "IPD": f"{r['Ion_pd_uA']:.0f}", p + "IPU": f"{r['Ion_pu_uA']:.0f}", p + "RATIO": f"{r['Ion_pd_uA']/r['Ion_pu_uA']:.2f}",
            p + "VMAB": f"{r['VM']['AB']*1e3:.0f}", p + "VMA": f"{r['VM']['A']*1e3:.0f}", p + "VMB": f"{r['VM']['B']*1e3:.0f}",
            p + "TPHLA": ps(r["fo4"]["A"]["tpHL"]), p + "TPLHA": ps(r["fo4"]["A"]["tpLH"]),
            p + "TPHLB": ps(r["fo4"]["B"]["tpHL"]), p + "TPLHB": ps(r["fo4"]["B"]["tpLH"]),
            p + "TPDW": ps(worst), p + "E": f"{r['fo4']['A']['E_cycle']*1e15:.2f}",
            p + "L00": f"{r['leak']['00']['I_nA']:.2f}", p + "L01": f"{r['leak']['01']['I_nA']:.2f}",
            p + "L10": f"{r['leak']['10']['I_nA']:.2f}", p + "L11": f"{r['leak']['11']['I_nA']:.2f}",
            p + "STACK": f"{r['leak']['10']['I_nA']/r['leak']['00']['I_nA']:.1f}", p + "PST": f"{r['P_static_avg_pW']/1e3:.2f}",
        }
    d = one(nd_g, "N_"); d.update(one(nd_f, "NF_"))
    arcs = [nd_g["fo4"][m]["tpd"] for m in ("A", "B")]
    d["N_ARCDIFF"] = f"{abs(arcs[0]-arcs[1])*1e12:.2f}"
    d["NF_AREAPCT"] = f"{(nd_f['area_um2']/nd_g['area_um2']-1)*100:.0f}"
    d["FIG_NAND_LAYOUT"] = rd("layout/gaa_nand2.svg")
    d["FIG_NAND_VTC"] = rd("spectre/fig_nand2_vtc.svg"); d["FIG_NAND_TRAN"] = rd("spectre/fig_nand2_tran.svg")
    return d

# ---------------- SRAM numbers ----------------
def sram_sub():
    def one(r, p):
        sw = {round(s["VDD"], 2): s for s in r["sweep"]}
        return {p + "BETA": f"{r['beta']:.2f}", p + "GAMMA": f"{r['gamma']:.2f}",
                p + "HSNM": f"{r['SNM_hold_mV']:.0f}", p + "RSNM": f"{r['SNM_read_mV']:.0f}",
                p + "DIST": f"{r['V_read_disturb_mV']:.0f}", p + "TRIP": f"{r['V_trip_mV']:.0f}",
                p + "IREAD": f"{r['I_read_uA']:.1f}", p + "LEAK": f"{r['I_leak_pA']/1e3:.2f}",
                p + "RSNM50": f"{sw[0.5]['SNM_read_mV']:.0f}", p + "RSNM40": f"{sw[0.4]['SNM_read_mV']:.0f}"}
    d = one(sr_g, "S_"); d.update(one(sr_f, "SF_"))
    d["S_TRIPDIFF"] = f"{sr_g['V_trip_mV'] - sr_f['V_trip_mV']:.0f}"
    d["S_HSNMDIFF"] = f"{abs(sr_g['SNM_hold_mV']/sr_f['SNM_hold_mV']-1)*100:.0f}"
    d["S_RSNMGAIN"] = f"{(sr_g['SNM_read_mV']/sr_f['SNM_read_mV']-1)*100:.0f}"
    d["FIG_SRAM_LAYOUT"] = rd("layout/gaa_sram6t.svg")
    d["FIG_SRAM_BUTTERFLY"] = rd("spectre/fig_sram_butterfly.svg"); d["FIG_SRAM_SNM"] = rd("spectre/fig_sram_snm_vdd.svg")
    return d

# ---------------- physical verification ----------------
FIRST_PASS = {  # first DRC run on the layouts as originally drawn (per cell), before correction
    "INV": {"M1.S.1": 2}, "NAND2": {"V0.E.LOW": 1}, "RO11": {"NS.S.1": 11, "M1.S.1": 22, "M2.S.1": 2},
    "SRAM": {"NS.E.NW": 2, "SDC.S.GATE": 2, "V0.E.M1": 14, "V0.E.LOW": 8, "M1.W.1": 4, "M1.S.1": 1, "V1.E.M1": 6, "V1.E.M2": 2, "M2.S.1": 2},
}
def verif_sub():
    V = os.path.join(B, "verify")
    drc = {k: json.load(open(os.path.join(V, f + ".drc.json"))) for k, f in (("INV", "gaa_inverter"), ("NAND2", "gaa_nand2"), ("RO11", "gaa_ro11"), ("SRAM", "gaa_sram6t"))}
    lvs = {k: json.load(open(os.path.join(V, f + ".lvs.json"))) for k, f in (("INV", "gaa_inverter"), ("NAND2", "gaa_nand2"), ("RO11", "gaa_ro11"), ("SRAM", "gaa_sram6t"))}
    rows = []
    for r in drc["INV"]["rules"]:
        cells = [FIRST_PASS[k].get(r["rule"], 0) for k in ("INV", "NAND2", "RO11", "SRAM")]
        final = sum(next(x["count"] for x in drc[k]["rules"] if x["rule"] == r["rule"]) for k in drc)
        cell_td = "".join(f'<td class="n">{("<b>%d</b>" % c) if c else "0"}</td>' for c in cells)
        rows.append(f'            <tr><td>{r["rule"]}</td><td>{r["kind"]}</td><td class="n">{r["value"]}</td><td>{html.escape(r["desc"])}</td>{cell_td}<td class="n">{final}</td></tr>')
    tot = [sum(FIRST_PASS[k].values()) for k in ("INV", "NAND2", "RO11", "SRAM")]
    rows.append(f'            <tr><td><b>Total</b></td><td></td><td></td><td>26 rules</td>' + "".join(f'<td class="n"><b>{x}</b></td>' for x in tot) + f'<td class="n"><b>{sum(d["total"] for d in drc.values())}</b></td></tr>')
    lrows = []
    for k, r in lvs.items():
        L, S = r["layout"], r["schematic"]
        lrows.append(f'            <tr><td>{r["layout_cell"]}</td><td class="n">{L["ports"]} / {S["ports"]}</td><td class="n">{L["nets"]} / {S["nets"]}</td>'
                     f'<td class="n">{L["instances"]} / {S["instances"]}</td><td class="n">{L["n"]} / {S["n"]}</td><td class="n">{L["p"]} / {S["p"]}</td>'
                     f'<td>{", ".join(L["port_names"])}</td><td><b>{r["result"]}</b></td></tr>')
    return {"DRC_ROWS": "\n".join(rows), "LVS_ROWS": "\n".join(lrows), "DRC_FIRST_TOTAL": str(sum(tot)),
            "DRCV_INV": rd("docs/figures/drc_inv.svg"), "DRCV_NAND2": rd("docs/figures/drc_nand2.svg"), "DRCV_RO11": rd("docs/figures/drc_ro11.svg"), "DRCV_SRAM": rd("docs/figures/drc_sram6t.svg"),
            "LVSV_INV": rd("docs/figures/lvs_inv.svg"), "LVSV_NAND2": rd("docs/figures/lvs_nand2.svg"), "LVSV_RO11": rd("docs/figures/lvs_ro11.svg"), "LVSV_SRAM": rd("docs/figures/lvs_sram6t.svg")}

# ---------------- parasitic extraction / post-layout ----------------
def pex_sub():
    V = os.path.join(B, "verify"); S = os.path.join(B, "spectre")
    pex = {k: json.load(open(os.path.join(V, f + ".pex.json"))) for k, f in (("INV_GAA_X1", "gaa_inverter"), ("NAND2_GAA_X1", "gaa_nand2"), ("RO11_GAA", "gaa_ro11"), ("SRAM6T_GAA_HD", "gaa_sram6t"))}
    pl = json.load(open(os.path.join(S, "results_postlayout.json")))
    rows = []
    for cell, p in pex.items():
        nets = [(n, x) for n, x in p["nets"].items() if not x.get("floating")]
        if cell == "RO11_GAA":
            sig = [x for n, x in nets if n.startswith("int") or n == "OUT"]
            cg = sum(x["cgnd_aF"] for x in sig) / len(sig); cc = sum(sum(x["coup_aF"].values()) for x in sig) / len(sig); r = sum(x["r_ohm"] for x in sig) / len(sig)
            rows.append(f'            <tr><td>{cell}</td><td>stage net n<sub>i</sub> (avg. of 11)</td><td class="n">{cg:.1f}</td><td class="n">{cc:.1f}</td><td class="n">{cg+cc:.1f}</td><td class="n">{r:.0f}</td><td>next stage (gate-drain), feedback line</td></tr>')
            continue
        for n, x in nets:
            if n in ("VDD", "VSS"): continue
            cc = sum(x["coup_aF"].values()); partners = ", ".join(f"{m} ({c:.0f})" for m, c in x["coup_aF"].items() if not m.startswith("float"))
            label = "X (stack node)" if n.startswith("int") else n
            rows.append(f'            <tr><td>{cell}</td><td>{label}</td><td class="n">{x["cgnd_aF"]:.1f}</td><td class="n">{cc:.1f}</td><td class="n">{x["ctotal_aF"]:.1f}</td><td class="n">{x["r_ohm"]:.0f}</td><td>{partners}</td></tr>')
    inv, nd, ro, sr = pl["inverter"], pl["nand2"], pl["ro11"], pl["sram"]
    ps = lambda v: f"{v*1e12:.2f}"
    def pct(a, b): return f"+{(b/a-1)*100:.0f} %" if b >= a else f"−{(1-b/a)*100:.0f} %"
    nw_pre = max(nd["pre"]["A"]["tpHL"], nd["pre"]["A"]["tpLH"], nd["pre"]["B"]["tpHL"], nd["pre"]["B"]["tpLH"])
    nw_post = max(nd["post"]["A"]["tpHL"], nd["post"]["A"]["tpLH"], nd["post"]["B"]["tpHL"], nd["post"]["B"]["tpLH"])
    plrows = [
        ("INV_GAA_X1", "Input capacitance", f"{inv['Cin_pre_fF']:.2f} fF", f"{inv['Cin_post_fF']:.2f} fF", pct(inv['Cin_pre_fF'], inv['Cin_post_fF'])),
        ("INV_GAA_X1", "Output-net parasitic capacitance", f"{inv['Cout_pre_fF']:.2f} fF", f"{inv['Cout_post_fF']:.2f} fF", pct(inv['Cout_pre_fF'], inv['Cout_post_fF'])),
        ("INV_GAA_X1", "Output-net resistance (half, driver to load)", "0 Ω", f"{inv['Rout_ohm']:.0f} Ω", ""),
        ("INV_GAA_X1", "t<sub>pHL</sub> / t<sub>pLH</sub> (FO4)", f"{ps(inv['pre']['tpHL'])} / {ps(inv['pre']['tpLH'])} ps", f"{ps(inv['post']['tpHL'])} / {ps(inv['post']['tpLH'])} ps", ""),
        ("INV_GAA_X1", "Propagation delay t<sub>pd</sub> (FO4)", f"{ps(inv['pre']['tpd'])} ps", f"{ps(inv['post']['tpd'])} ps", pct(inv['pre']['tpd'], inv['post']['tpd'])),
        ("INV_GAA_X1", "Energy per cycle (FO4)", f"{inv['pre']['E_cycle']*1e15:.2f} fJ", f"{inv['post']['E_cycle']*1e15:.2f} fJ", pct(inv['pre']['E_cycle'], inv['post']['E_cycle'])),
        ("NAND2_GAA_X1", "Input capacitance / stack-node capacitance", "0.32 / 0.15 fF", f"{nd['Cin_post_fF']:.2f} / {nd['CX_post_fF']:.2f} fF", ""),
        ("NAND2_GAA_X1", "Worst-case arc t<sub>pd</sub> (FO4)", f"{ps(nw_pre)} ps", f"{ps(nw_post)} ps", pct(nw_pre, nw_post)),
        ("RO11_GAA", "Node capacitance per stage (FO3)", f"{ro['Cnode_pre_fF']:.2f} fF", f"{ro['Cnode_post_fF']:.2f} fF", pct(ro['Cnode_pre_fF'], ro['Cnode_post_fF'])),
        ("RO11_GAA", "Oscillation frequency", f"{ro['pre']['f_Hz']/1e9:.2f} GHz", f"{ro['post']['f_Hz']/1e9:.2f} GHz", pct(ro['pre']['f_Hz'], ro['post']['f_Hz'])),
        ("RO11_GAA", "Stage delay", f"{ps(ro['pre']['t_stage_s'])} ps", f"{ps(ro['post']['t_stage_s'])} ps", pct(ro['pre']['t_stage_s'], ro['post']['t_stage_s'])),
        ("RO11_GAA", "Average power", f"{ro['pre']['P_W']*1e6:.0f} µW", f"{ro['post']['P_W']*1e6:.0f} µW", pct(ro['pre']['P_W'], ro['post']['P_W'])),
        ("SRAM6T_GAA_HD", "Bit-line / word-line capacitance per cell", "–", f"{sr['C_BL_cell_fF']*1e3:.0f} / {sr['C_WL_cell_fF']*1e3:.0f} aF", ""),
        ("SRAM6T_GAA_HD", "100-mV bit-line development, 256 cells", "–", f"{sr['t_BL_100mV_ps']:.1f} ps", ""),
        ("SRAM6T_GAA_HD", "Word-line Elmore delay, 64-cell segment", "–", f"{sr['t_WL_elmore_ps']:.1f} ps", ""),
    ]
    plr = "\n".join(f'            <tr><td>{a}</td><td>{b_}</td><td class="n">{c}</td><td class="n">{d}</td><td class="n">{e}</td></tr>' for a, b_, c, d, e in plrows)
    A = pex["INV_GAA_X1"]["nets"]["A"]
    return {"PEX_ROWS": "\n".join(rows), "PL_ROWS": plr,
            "PL_CINA": f"{A['cgnd_aF']:.0f}", "PL_CCAY": f"{A['coup_aF'].get('Y', 0):.0f}", "PL_CIN_POST": f"{inv['Cin_post_fF']:.2f}", "PL_CIN_PRE": f"{inv['Cin_pre_fF']:.2f}",
            "PL_COUT_POST": f"{pex['INV_GAA_X1']['nets']['Y']['cgnd_aF']/1e3:.3f}", "PL_ROUT": f"{inv['Rout_ohm']:.0f}",
            "PL_TPD_PRE": ps(inv["pre"]["tpd"]), "PL_TPD_POST": ps(inv["post"]["tpd"]), "PL_TPD_PCT": f"{(inv['post']['tpd']/inv['pre']['tpd']-1)*100:.0f}",
            "PL_E_PRE": f"{inv['pre']['E_cycle']*1e15:.2f}", "PL_E_POST": f"{inv['post']['E_cycle']*1e15:.2f}",
            "PL_LOAD_POST": f"{inv['load_post_fF']:.2f}", "PL_LOAD_PRE": f"{inv['load_pre_fF']:.2f}",
            "PL_RO_F_PRE": f"{ro['pre']['f_Hz']/1e9:.1f}", "PL_RO_F_POST": f"{ro['post']['f_Hz']/1e9:.1f}", "PL_RO_TS_POST": ps(ro["post"]["t_stage_s"]),
            "PL_N_PRE": ps(nw_pre), "PL_N_POST": ps(nw_post),
            "PL_CBL": f"{sr['C_BL_cell_fF']*1e3:.0f}", "PL_CWL": f"{sr['C_WL_cell_fF']*1e3:.0f}", "PL_RWL": f"{sr['R_WL_cell_ohm']:.0f}",
            "PL_TBL": f"{sr['t_BL_100mV_ps']:.1f}", "PL_TWL": f"{sr['t_WL_elmore_ps']:.1f}",
            "PL_CIN_RATIO": f"{inv['Cin_post_fF']/inv['Cin_pre_fF']:.1f}", "PL_R_PCT": f"{max(inv['R_delay_pct'], 0.5):.0f}",
            "PEXV_INV": rd("docs/figures/pex_inv.svg"), "PEXV_NAND2": rd("docs/figures/pex_nand2.svg"), "PEXV_SRAM": rd("docs/figures/pex_sram6t.svg"),
            "VV_INV_PL": rd("docs/figures/viva_inv_postlayout.svg"), "VV_RO_PL": rd("docs/figures/viva_ro11_postlayout.svg")}

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
    **nand_sub(),
    **sram_sub(),
    **verif_sub(),
    **pex_sub(),
    "FIG_DEVICE": device_svg(),
    "SCH_INV": rd("docs/figures/schematic_inv_page.svg"), "SCH_NAND2": rd("docs/figures/schematic_nand2_page.svg"),
    "SCH_RO11": rd("docs/figures/schematic_ro11_page.svg"), "SCH_SRAM": rd("docs/figures/schematic_sram6t_page.svg"),
    "VS_INV": rd("docs/figures/virtuoso_inv.svg"), "VS_NAND2": rd("docs/figures/virtuoso_nand2.svg"),
    "VS_RO11": rd("docs/figures/virtuoso_ro11.svg"), "VS_SRAM": rd("docs/figures/virtuoso_sram6t.svg"),
    "VV_INV_DC": rd("docs/figures/viva_inv_dc.svg"), "VV_INV_TRAN": rd("docs/figures/viva_inv_tran.svg"),
    "VV_NAND2_TRAN": rd("docs/figures/viva_nand2_tran.svg"), "VV_RO11_TRAN": rd("docs/figures/viva_ro11_tran.svg"),
    "VV_SRAM": rd("docs/figures/viva_sram_butterfly.svg"), "FIG_LAYOUT": rd("layout/gaa_inverter.svg"),
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
