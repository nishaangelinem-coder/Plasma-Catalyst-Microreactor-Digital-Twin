#!/usr/bin/env python3
"""
gen_viva.py -- simulation results drawn in the Virtuoso Visualization & Analysis XL (ViVA) convention:
black plot area with dotted grid, traces and their legend names in the trace colours, 'Transient
Response' / 'DC Response' titles, point markers (M0, M1 ...) with value boxes and delta readouts,
and the viewer's window frame.  Data come from the reference-model scripts in ../spectre, so the
panels show the same curves as Figs. 7-8, 12 and 14; the Spectre run in the VMware guest produces
the real ViVA plots that replace these for the camera-ready manuscript.

    python3 gen_viva.py   -> figures/viva_{inv_dc,inv_tran,nand2_tran,ro11_tran,sram_butterfly}.svg
"""
import json, math, os, sys
R = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(R, "figures")
sys.path.insert(0, os.path.join(R, "..", "spectre"))
os.chdir(os.path.join(R, "..", "spectre"))
import ref_model as rm, nand2 as nd, sram6t as sr

C = dict(bg="#000000", grid="#555555", axis="#c8c8c8", text="#e6e6e6", title="#ffffff",
         chrome="#d9d9d9", chrome2="#f2f2f2", ink="#1a1a1a", sel="#0c5cc4")
TRACE = ["#ffff33", "#33ff66", "#ff66ff", "#33e6ff", "#ff9933", "#ff4d4d"]
FONT = "'DejaVu Sans Mono', 'Liberation Mono', Menlo, monospace"

def ticks(lo, hi, n=6):
    span = hi - lo; raw = span / n; mag = 10 ** math.floor(math.log10(raw)); r = raw / mag
    step = (1 if r < 1.5 else 2 if r < 3.5 else 5 if r < 7.5 else 10) * mag
    t = math.ceil(lo / step) * step; out = []
    while t <= hi + 1e-12: out.append(round(t, 10)); t += step
    return out

def fmt(v, unit):
    a = abs(v)
    if unit == "V": return (f"{v*1e3:.1f}mV" if a < 1 else f"{v:.3f}V")
    if unit == "ps": return f"{v:.2f}ps"
    return f"{v:g}"

def panel(name, title, traces, xlabel, ylabel, xlim, ylim, markers=(), deltas=(), w=560, h=330, annot=()):
    T, B = 46, 22; ml, mr, mt, mb = 62, 16, 40, 40; pw, ph = w - ml - mr, h - mt - mb
    X = lambda x: ml + (x - xlim[0]) / (xlim[1] - xlim[0]) * pw
    Y = lambda y: mt + ph - (y - ylim[0]) / (ylim[1] - ylim[0]) * ph
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h + T + B}" role="img" style="max-width:100%;height:auto;font-family:{FONT}" stroke-linecap="round" stroke-linejoin="round">',
         f'<rect width="{w}" height="{h + T + B}" fill="{C["chrome"]}"/>',
         f'<rect width="{w}" height="22" fill="{C["sel"]}"/>',
         f'<text x="8" y="15" fill="#fff" font-size="10.5" font-weight="600">Virtuoso (R) Visualization &amp; Analysis XL  –  {name}</text>',
         f'<text x="{w-8}" y="15" fill="#fff" font-size="10" text-anchor="end">–  □  ×</text>',
         f'<rect y="22" width="{w}" height="24" fill="{C["chrome2"]}"/>',
         f'<text x="8" y="38" fill="{C["ink"]}" font-size="10">File  Edit  Frame  Graph  Axis  Trace  Marker  Measurements  Tools  Browser  Help</text>',
         f'<g transform="translate(0,{T})">', f'<rect width="{w}" height="{h}" fill="{C["bg"]}"/>',
         f'<text x="{ml + pw/2:.0f}" y="16" fill="{C["title"]}" font-size="12" text-anchor="middle" font-weight="600">{title}</text>']
    for i, tr in enumerate(traces):                                     # legend strip
        col = TRACE[i % len(TRACE)]; lx = ml + i * 118
        o.append(f'<rect x="{lx}" y="{mt-18}" width="9" height="9" fill="{col}"/><text x="{lx+13}" y="{mt-10}" fill="{col}" font-size="9.5">{tr["name"]}</text>')
    for xv in ticks(*xlim):
        o.append(f'<line x1="{X(xv):.1f}" y1="{mt}" x2="{X(xv):.1f}" y2="{mt+ph}" stroke="{C["grid"]}" stroke-width="0.8" stroke-dasharray="1 3"/>')
        o.append(f'<text x="{X(xv):.1f}" y="{mt+ph+14}" fill="{C["text"]}" font-size="9" text-anchor="middle">{xv:g}</text>')
    for yv in ticks(*ylim):
        o.append(f'<line x1="{ml}" y1="{Y(yv):.1f}" x2="{ml+pw}" y2="{Y(yv):.1f}" stroke="{C["grid"]}" stroke-width="0.8" stroke-dasharray="1 3"/>')
        o.append(f'<text x="{ml-6}" y="{Y(yv)+3:.1f}" fill="{C["text"]}" font-size="9" text-anchor="end">{yv:g}</text>')
    o.append(f'<rect x="{ml}" y="{mt}" width="{pw}" height="{ph}" fill="none" stroke="{C["axis"]}" stroke-width="1"/>')
    o.append(f'<text x="{ml+pw/2:.0f}" y="{h-8}" fill="{C["text"]}" font-size="10" text-anchor="middle">{xlabel}</text>')
    o.append(f'<text transform="translate(14,{mt+ph/2:.0f}) rotate(-90)" fill="{C["text"]}" font-size="10" text-anchor="middle">{ylabel}</text>')
    for i, tr in enumerate(traces):
        col = TRACE[i % len(TRACE)]
        pts = " ".join(f"{X(x):.1f},{Y(y):.1f}" for x, y in tr["xy"] if xlim[0] <= x <= xlim[1])
        dash = ' stroke-dasharray="6 4"' if tr.get("dash") else ""
        o.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="1.6"{dash}/>')
    for k, m in enumerate(markers):                                     # point markers M0, M1 ...
        col = TRACE[m.get("trace", 0) % len(TRACE)]; x, y = X(m["x"]), Y(m["y"])
        o.append(f'<line x1="{x:.1f}" y1="{mt}" x2="{x:.1f}" y2="{mt+ph}" stroke="{col}" stroke-width="0.8" stroke-dasharray="3 3"/>')
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{col}" stroke="#000"/>')
        lab = f"M{k}: {fmt(m['x'], m['xu'])}, {fmt(m['y'], 'V')}"; tw = 6.2 * len(lab) + 8
        bx = (x - tw - 8) if m.get("left") else min(max(x + 8, ml), ml + pw - tw); by = y - 24 - m.get("dy", 0)
        o.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{tw:.0f}" height="15" rx="2" fill="#000" stroke="{col}" stroke-width="0.8"/>')
        o.append(f'<text x="{bx+4:.1f}" y="{by+11:.1f}" fill="{col}" font-size="9">{lab}</text>')
    for d in deltas:                                                    # delta readouts (ViVA 'delta marker')
        o.append(f'<rect x="{d["x"]:.0f}" y="{d["y"]:.0f}" width="{6.2*len(d["text"])+8:.0f}" height="15" rx="2" fill="#000" stroke="{C["axis"]}" stroke-width="0.8"/>')
        o.append(f'<text x="{d["x"]+4:.0f}" y="{d["y"]+11:.0f}" fill="{C["text"]}" font-size="9">{d["text"]}</text>')
    for a in annot:
        o.append(a(X, Y))
    o += ['</g>', f'<rect y="{T+h}" width="{w}" height="{B}" fill="{C["chrome2"]}"/>',
          f'<text x="8" y="{T+h+15}" fill="{C["ink"]}" font-size="9">{name}   |   {title}</text>',
          f'<text x="{w-8}" y="{T+h+15}" fill="{C["ink"]}" font-size="9" text-anchor="end">reference model – replace with ViVA capture</text>', '</svg>']
    return "\n".join(o)

def cross(ts, sig, level, rising, tstart):
    for i in range(1, len(ts)):
        if ts[i] < tstart: continue
        a, b = sig[i-1], sig[i]
        if (rising and a < level <= b) or (not rising and a > level >= b):
            return ts[i-1] + (level - a) / (b - a) * (ts[i] - ts[i-1])
    return float("nan")

def main():
    V = rm.VDD; out = {}
    # (a) inverter DC response
    curve = rm.vtc(); st = rm.metrics_static(curve)
    out["viva_inv_dc"] = panel("ADE L (1) INV_GAA_X1", "DC Response",
        [dict(name="/out", xy=curve), dict(name="/in", xy=[(0, 0), (V, V)], dash=True)],
        "dc (V)", "V (V)", (0, V), (0, V),
        markers=[dict(x=st["VM"], y=st["VM"], xu="V"), dict(x=st["VIL"], y=st["VOH"], xu="V", dy=-30, left=True), dict(x=st["VIH"], y=st["VOL"], xu="V", dy=-30)],
        deltas=[dict(x=330, y=60, text=f"gain(max) = {-st['gain_max']:.1f}"), dict(x=330, y=80, text=f"NM_L = {st['NML']*1e3:.0f}mV  NM_H = {st['NMH']*1e3:.0f}mV")])
    # (b) inverter transient (FO4)
    tr = rm.transient(cl=4 * 0.32e-15); w = tr["wave"]; ts = [t * 1e12 for t in w["t"]]
    t_in_r = cross(ts, w["vin"], V/2, True, 5); t_out_f = cross(ts, w["vout"], V/2, False, 5)
    t_in_f = cross(ts, w["vin"], V/2, False, 40); t_out_r = cross(ts, w["vout"], V/2, True, 40)
    out["viva_inv_tran"] = panel("ADE L (1) INV_GAA_X1", "Transient Response",
        [dict(name="/in", xy=list(zip(ts, w["vin"]))), dict(name="/out", xy=list(zip(ts, w["vout"])))],
        "time (ps)", "V (V)", (0, 80), (0, 0.8),
        markers=[dict(x=t_in_r, y=V/2, xu="ps", trace=0), dict(x=t_out_f, y=V/2, xu="ps", trace=1, dy=20),
                 dict(x=t_in_f, y=V/2, xu="ps", trace=0), dict(x=t_out_r, y=V/2, xu="ps", trace=1, dy=20)],
        deltas=[dict(x=330, y=60, text=f"tpHL = M1 - M0 = {tr['tpHL']*1e12:.2f}ps"), dict(x=330, y=80, text=f"tpLH = M3 - M2 = {tr['tpLH']*1e12:.2f}ps"),
                dict(x=330, y=100, text="load: 1.28f (FO4), slew 12p")])
    # (c) NAND2 transient, A arc (B = 1) and B arc
    ta = nd.transient("A", 4 * nd.CIN); tb = nd.transient("B", 4 * nd.CIN); wa, wb = ta["wave"], tb["wave"]; ts = [t * 1e12 for t in wa["t"]]
    out["viva_nand2_tran"] = panel("ADE L (2) NAND2_GAA_X1", "Transient Response",
        [dict(name="/a (b=vdd)", xy=list(zip(ts, wa["vin"]))), dict(name="/y : A arc", xy=list(zip(ts, wa["vout"]))), dict(name="/y : B arc", xy=list(zip(ts, wb["vout"])), dash=True)],
        "time (ps)", "V (V)", (0, 80), (0, 0.8),
        markers=[dict(x=cross(ts, wa["vout"], V/2, False, 5), y=V/2, xu="ps", trace=1), dict(x=cross(ts, wb["vout"], V/2, False, 5), y=V/2, xu="ps", trace=2, dy=20)],
        deltas=[dict(x=300, y=60, text=f"A: tpHL {ta['tpHL']*1e12:.2f}ps  tpLH {ta['tpLH']*1e12:.2f}ps"), dict(x=300, y=80, text=f"B: tpHL {tb['tpHL']*1e12:.2f}ps  tpLH {tb['tpLH']*1e12:.2f}ps")])
    # (d) RO11 transient with period delta
    ro = json.load(open("results_ro.json")); wv = ro["nominal"]["wave"]
    sel = [k for k in range(len(wv["t"])) if 300 <= wv["t"][k] <= 500]
    t0 = [wv["t"][k] - 300 for k in sel]; n1 = [wv["v0"][k] for k in sel]; n2 = [wv["v1"][k] for k in sel]
    c1 = cross(t0, n1, V/2, True, 5); c2 = cross(t0, n1, V/2, True, c1 + 5)
    out["viva_ro11_tran"] = panel("ADE L (3) RO11_GAA", "Transient Response",
        [dict(name="/n1", xy=list(zip(t0, n1))), dict(name="/n2", xy=list(zip(t0, n2)))],
        "time (ps)  [window 300-500 ps]", "V (V)", (0, 200), (0, 0.8),
        markers=[dict(x=c1, y=V/2, xu="ps"), dict(x=c2, y=V/2, xu="ps", dy=20)],
        deltas=[dict(x=290, y=60, text=f"T = M1 - M0 = {c2-c1:.2f}ps  f = {1e3/(c2-c1):.2f}GHz"), dict(x=290, y=80, text=f"t_stage = T/22 = {(c2-c1)/22:.2f}ps (FO3, 0.7V)")])
    # (e) SRAM butterfly (read and hold), SNM square in the read lobe
    hold = sr.butterfly("hold", V); read = sr.butterfly("read", V)
    snm_r = sr.snm(read, V); snm_h = sr.snm(hold, V)
    mirror = lambda cv: sorted((y, x) for x, y in cv)
    def square(X, Y):
        # locate the largest square in the upper-left lobe of the read curves (same search as sram6t.snm)
        xs = [p[0] for p in read]; ys = [p[1] for p in read]
        def f(x):
            k = min(max(int((len(xs)-1) * x / V), 0), len(xs)-2); return ys[k] + (ys[k+1]-ys[k]) * (x - xs[k]) / (xs[k+1]-xs[k])
        best = (0, 0, 0)
        for x0 in xs[:-1]:
            lo, hi = 0.0, V - x0
            for _ in range(40):
                mid = 0.5*(lo+hi); y0 = f(x0+mid) - mid
                if y0 >= 0 and x0 >= f(y0): lo = mid
                else: hi = mid
            if lo > best[0]: best = (lo, x0, f(x0+lo) - lo)
        s, x0, y0 = best
        return (f'<rect x="{X(x0):.1f}" y="{Y(y0+s):.1f}" width="{X(x0+s)-X(x0):.1f}" height="{Y(y0)-Y(y0+s):.1f}" fill="none" stroke="#ffffff" stroke-width="1" stroke-dasharray="4 3"/>'
                f'<text x="{X(x0):.1f}" y="{Y(y0+s)-5:.1f}" fill="#ffffff" font-size="9">SNM_read = {snm_r*1e3:.0f}mV (largest square)</text>')
    out["viva_sram_butterfly"] = panel("ADE L (4) SRAM6T_GAA_HD", "DC Response",
        [dict(name="/q (read)", xy=read), dict(name="/qb (read)", xy=mirror(read)), dict(name="/q (hold)", xy=hold, dash=True), dict(name="/qb (hold)", xy=mirror(hold), dash=True)],
        "dc (V)", "V (V)", (0, V), (0, V),
        deltas=[dict(x=330, y=60, text=f"SNM_hold = {snm_h*1e3:.0f}mV"), dict(x=330, y=80, text="WL = BL = BLB = vdd! (read)")], annot=[square])
    # (f) pre- vs post-layout overlays (Innovus/Quantus SPEF back-annotated run)
    pl = json.load(open("results_postlayout.json"))
    wp, wq = pl["inverter"]["wave_pre"], pl["inverter"]["wave_post"]
    tp, tq = pl["inverter"]["pre"], pl["inverter"]["post"]
    m0 = cross(wp["t"], wp["vout"], V/2, False, 5); m1 = cross(wq["t"], wq["vout"], V/2, False, 5)
    out["viva_inv_postlayout"] = panel("ADE L (1) INV_GAA_X1 : schematic vs av_extracted", "Transient Response",
        [dict(name="/in", xy=list(zip(wp["t"], wp["vin"]))), dict(name="/out pre-layout", xy=list(zip(wp["t"], wp["vout"]))),
         dict(name="/out post-layout (SPEF)", xy=list(zip(wq["t"], wq["vout"])))],
        "time (ps)", "V (V)", (0, 80), (0, 0.8),
        markers=[dict(x=m0, y=V/2, xu="ps", trace=1), dict(x=m1, y=V/2, xu="ps", trace=2, dy=20)],
        deltas=[dict(x=300, y=60, text=f"tpd pre {tp['tpd']*1e12:.2f}ps  post {tq['tpd']*1e12:.2f}ps  (+{(tq['tpd']/tp['tpd']-1)*100:.0f}%)"),
                dict(x=300, y=80, text=f"load {pl['inverter']['load_pre_fF']:.2f}f -> {pl['inverter']['load_post_fF']:.2f}f  Rout {pl['inverter']['Rout_ohm']:.0f}ohm")])
    rp, rq = pl["ro11"]["wave_pre"], pl["ro11"]["wave_post"]
    selp = [k for k in range(len(rp["t"])) if 300 <= rp["t"][k] <= 500]; selq = [k for k in range(len(rq["t"])) if 300 <= rq["t"][k] <= 500]
    out["viva_ro11_postlayout"] = panel("ADE L (3) RO11_GAA : schematic vs av_extracted", "Transient Response",
        [dict(name="/n1 pre-layout", xy=[(rp["t"][k] - 300, rp["v0"][k]) for k in selp]),
         dict(name="/n1 post-layout (SPEF)", xy=[(rq["t"][k] - 300, rq["v0"][k]) for k in selq])],
        "time (ps)  [window 300-500 ps]", "V (V)", (0, 200), (0, 0.8),
        deltas=[dict(x=300, y=60, text=f"f_osc pre {pl['ro11']['pre']['f_Hz']/1e9:.2f}GHz  post {pl['ro11']['post']['f_Hz']/1e9:.2f}GHz"),
                dict(x=300, y=80, text=f"t_stage pre {pl['ro11']['pre']['t_stage_s']*1e12:.2f}ps  post {pl['ro11']['post']['t_stage_s']*1e12:.2f}ps")])
    os.makedirs(OUT, exist_ok=True)
    for name, svg in out.items():
        open(os.path.join(OUT, name + ".svg"), "w").write(svg)
    print("ViVA-style panels written:", ", ".join(out))

if __name__ == "__main__":
    main()
