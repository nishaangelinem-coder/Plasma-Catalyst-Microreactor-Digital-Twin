#!/usr/bin/env python3
"""
ref_model.py -- dependency-free reference simulation of the GAA nanosheet inverter.

A unified EKV-style compact model (weak->strong inversion continuous, velocity-
saturation exponent alpha, DIBL-like output conductance) is calibrated to
IRDS-2023 3-nm-class nanosheet targets. It reproduces the metrics that the
Spectre/BSIM-CMG testbench `gaa_inv_tb.scs` extracts, so results can be checked
before/after running Cadence in the VMware guest.  Writes results.json and SVG plots.
"""
import json, math

PHI_T = 0.02585                 # kT/q at 300 K
VDD = 0.70
TECH = dict(NS_N=3, NS_T=5e-9, NS_W_N=30e-9, NS_W_P=45e-9, LG=14e-9, EOT=0.9e-9)

def w_eff(w):                    # gate-all-around perimeter * sheet count
    return TECH["NS_N"] * 2 * (w + TECH["NS_T"])

DEV = {
    "n": dict(vth=0.24, ss=0.068, alpha=1.25, lam=0.12, jon=1.00e-3, weff=w_eff(TECH["NS_W_N"]), sgn=+1),
    "p": dict(vth=0.26, ss=0.070, alpha=1.25, lam=0.14, jon=0.75e-3, weff=w_eff(TECH["NS_W_P"]), sgn=-1),
}
for d in DEV.values():
    d["n_ss"] = d["ss"] / (PHI_T * math.log(10.0))
    d["ion"] = d["jon"] * d["weff"] * 1e6        # A  (jon in A/um, weff in m)

def _vov(d, vgs):
    s = d["alpha"] * d["n_ss"] * PHI_T
    x = (vgs - d["vth"]) / s
    return s * (math.log1p(math.exp(x)) if x < 40 else x)

def _g(d, vov, vds):
    vdsat = math.sqrt((0.55 * vov) ** 2 + (3 * PHI_T) ** 2)
    r = vds / vdsat
    return r / (1.0 + r ** 2) ** 0.5 * (1.0 + d["lam"] * vds)

def ids(dev, vgs, vds):
    """Drain current magnitude (A). vgs, vds given as |values| for PMOS."""
    d = DEV[dev]
    if "k" not in d:
        d["k"] = 1.0
        d["k"] = d["ion"] / ids(dev, VDD, VDD)
    vov = _vov(d, vgs)
    return d["k"] * vov ** d["alpha"] * _g(d, vov, vds)

def i_n(vin, vout): return ids("n", vin, vout)
def i_p(vin, vout): return ids("p", VDD - vin, VDD - vout)

def vtc(npts=141):
    pts = []
    for i in range(npts):
        vin = VDD * i / (npts - 1)
        lo, hi = 0.0, VDD
        for _ in range(60):                       # bisection on I_n(vout) = I_p(vout)
            mid = 0.5 * (lo + hi)
            if i_n(vin, mid) > i_p(vin, mid): hi = mid
            else: lo = mid
        pts.append((vin, 0.5 * (lo + hi)))
    return pts

def metrics_static(curve):
    vin = [p[0] for p in curve]; vout = [p[1] for p in curve]
    gain = [0.0] * len(curve)
    for i in range(1, len(curve) - 1):
        gain[i] = (vout[i + 1] - vout[i - 1]) / (vin[i + 1] - vin[i - 1])
    imax = min(range(len(gain)), key=lambda i: gain[i])
    # switching threshold: vout = vin
    vm = next(vin[i] for i in range(len(curve)) if vout[i] <= vin[i])
    # unity-gain points -> VIL, VIH, VOL, VOH
    il = max(i for i in range(imax) if gain[i] > -1.0)
    ih = min(i for i in range(imax, len(curve)) if gain[i] > -1.0)
    VIL, VIH, VOH, VOL = vin[il], vin[ih], vout[il], vout[ih]
    return dict(VM=vm, gain_max=gain[imax], VIL=VIL, VIH=VIH, VOH=VOH, VOL=VOL,
                NMH=VOH - VIH, NML=VIL - VOL, gain=gain)

def transient(cl, tr=12e-12, tstop=80e-12, dt=2e-15, cpar=0.35e-15):
    """Input: 0->VDD ramp at t0 then VDD->0 at t1 (10-90 % slew = tr). Euler on C dV/dt."""
    C = cl + cpar
    t0, t1 = 10e-12, 45e-12
    ramp = tr / 0.8
    def vin_t(t):
        if t < t0: return 0.0
        if t < t0 + ramp: return VDD * (t - t0) / ramp
        if t < t1: return VDD
        if t < t1 + ramp: return VDD * (1 - (t - t1) / ramp)
        return 0.0
    t, vout = 0.0, VDD
    ts, vins, vouts, idds = [], [], [], []
    e_supply = 0.0
    while t <= tstop:
        vi = vin_t(t)
        ip, in_ = i_p(vi, vout), i_n(vi, vout)
        vout += dt * (ip - in_) / C
        vout = min(max(vout, -0.05), VDD + 0.05)
        e_supply += ip * VDD * dt
        if int(t / dt) % 25 == 0:
            ts.append(t); vins.append(vi); vouts.append(vout); idds.append(ip)
        t += dt
    def cross(sig, level, rising, tstart):
        for i in range(1, len(ts)):
            if ts[i] < tstart: continue
            a, b = sig[i - 1], sig[i]
            if (rising and a < level <= b) or (not rising and a > level >= b):
                return ts[i - 1] + (level - a) / (b - a) * (ts[i] - ts[i - 1])
        return float("nan")
    half = VDD / 2
    tphl = cross(vouts, half, False, t0) - cross(vins, half, True, t0)
    tplh = cross(vouts, half, True, t1) - cross(vins, half, False, t1)
    tf = cross(vouts, 0.1 * VDD, False, t0) - cross(vouts, 0.9 * VDD, False, t0)
    trr = cross(vouts, 0.9 * VDD, True, t1) - cross(vouts, 0.1 * VDD, True, t1)
    e_leak = 0.5 * (i_n(0, VDD) + i_p(VDD, 0)) * VDD * tstop
    return dict(tpHL=tphl, tpLH=tplh, tpd=0.5 * (tphl + tplh), tfall=tf, trise=trr,
                E_cycle=e_supply - e_leak, wave=dict(t=ts, vin=vins, vout=vouts, idd=idds))

def idvg(dev):
    rows = []
    for i in range(0, 71):
        vgs = VDD * i / 70
        rows.append((vgs, ids(dev, vgs, VDD), ids(dev, vgs, 0.05)))
    return rows

# ------------------------------------------------------------------ SVG helpers
def svg_chart(w, h, series, xlab, ylab, xlim, ylim, log=False, extra=""):
    ml, mr, mt, mb = 52, 16, 12, 40
    pw, ph = w - ml - mr, h - mt - mb
    def X(x): return ml + (x - xlim[0]) / (xlim[1] - xlim[0]) * pw
    def Y(y):
        if log: y = math.log10(max(y, 1e-30)); a, b = math.log10(ylim[0]), math.log10(ylim[1])
        else: a, b = ylim
        return mt + ph - (y - a) / (b - a) * ph
    meta = json.dumps(dict(ml=ml, mt=mt, pw=pw, ph=ph, xlim=xlim, ylim=ylim, log=log, xlab=xlab, ylab=ylab))
    data = json.dumps([dict(name=s["name"], xy=[[round(x, 5), float(f"{y:.4g}")] for x, y in s["xy"]], color=s["color"]) for s in series if not s.get("nohover")])
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" class="chart" '
           f"data-plot='{meta}' data-series='{data}' "
           f'style="max-width:100%;height:auto;font-family:var(--font-ui);font-size:11px">']
    # grid
    nx = 7
    for i in range(nx + 1):
        xv = xlim[0] + (xlim[1] - xlim[0]) * i / nx
        out.append(f'<line x1="{X(xv):.1f}" y1="{mt}" x2="{X(xv):.1f}" y2="{mt+ph}" stroke="var(--grid)" stroke-width="1"/>')
        out.append(f'<text x="{X(xv):.1f}" y="{mt+ph+16}" text-anchor="middle" fill="var(--ink-2)">{xv:.1f}</text>')
    if log:
        e0, e1 = int(math.log10(ylim[0])), int(math.log10(ylim[1]))
        for e in range(e0, e1 + 1):
            yv = 10.0 ** e
            out.append(f'<line x1="{ml}" y1="{Y(yv):.1f}" x2="{ml+pw}" y2="{Y(yv):.1f}" stroke="var(--grid)"/>')
            out.append(f'<text x="{ml-6}" y="{Y(yv)+4:.1f}" text-anchor="end" fill="var(--ink-2)">10<tspan font-size="8" dy="-5">{e}</tspan></text>')
    else:
        ny = 7
        for i in range(ny + 1):
            yv = ylim[0] + (ylim[1] - ylim[0]) * i / ny
            out.append(f'<line x1="{ml}" y1="{Y(yv):.1f}" x2="{ml+pw}" y2="{Y(yv):.1f}" stroke="var(--grid)"/>')
            out.append(f'<text x="{ml-6}" y="{Y(yv)+4:.1f}" text-anchor="end" fill="var(--ink-2)">{yv:.2g}</text>')
    out.append(f'<rect x="{ml}" y="{mt}" width="{pw}" height="{ph}" fill="none" stroke="var(--ink-3)"/>')
    for s in series:
        d = " ".join(f"{X(x):.1f},{Y(y):.1f}" for x, y in s["xy"] if xlim[0] <= x <= xlim[1])
        dash = f' stroke-dasharray="{s["dash"]}"' if s.get("dash") else ""
        out.append(f'<polyline points="{d}" fill="none" stroke="{s["color"]}" stroke-width="{s.get("w",2)}"{dash}><title>{s["name"]}</title></polyline>')
    out.append(f'<text x="{ml+pw/2:.0f}" y="{h-6}" text-anchor="middle" fill="var(--ink)">{xlab}</text>')
    out.append(f'<text transform="translate(14,{mt+ph/2:.0f}) rotate(-90)" text-anchor="middle" fill="var(--ink)">{ylab}</text>')
    # legend
    lx, ly = ml + 10, mt + 14
    for k, s in enumerate(series):
        out.append(f'<line x1="{lx}" y1="{ly+k*15}" x2="{lx+18}" y2="{ly+k*15}" stroke="{s["color"]}" stroke-width="2"'
                   + (f' stroke-dasharray="{s["dash"]}"' if s.get("dash") else "") + '/>')
        out.append(f'<text x="{lx+24}" y="{ly+k*15+4}" fill="var(--ink)">{s["name"]}</text>')
    out.append(extra.replace("__X__", "").replace("__Y__", ""))
    out.append("</svg>")
    return "\n".join(out), X, Y

if __name__ == "__main__":
    curve = vtc()
    st = metrics_static(curve)
    fo1 = transient(cl=0.32e-15)
    fo4 = transient(cl=4 * 0.32e-15)
    ioff_n, ioff_p = i_n(0.0, VDD), i_p(VDD, 0.0)
    res = dict(
        VDD=VDD, tech=TECH,
        device={k: dict(vth=d["vth"], SS_mV_dec=d["ss"]*1e3, Weff_nm=d["weff"]*1e9, Ion_uA=d["ion"]*1e6,
                        Ioff_nA=(ioff_n if k == "n" else ioff_p)*1e9,
                        Ion_Ioff=d["ion"]/(ioff_n if k == "n" else ioff_p),
                        DIBL_like_lambda=d["lam"]) for k, d in DEV.items()},
        static={k: v for k, v in st.items() if k != "gain"},
        fo1={k: v for k, v in fo1.items() if k != "wave"},
        fo4={k: v for k, v in fo4.items() if k != "wave"},
        P_static_pW=0.5 * (ioff_n + ioff_p) * VDD * 1e12,
        P_dyn_uW_at_1GHz=fo4["E_cycle"] * 1e9 * 1e6,
        area_um2=0.096 * 0.168,
    )
    json.dump(res, open("results.json", "w"), indent=1)
    for k, v in res.items():
        if k not in ("tech",): print(k, "=", json.dumps(v, default=lambda o: round(o, 6)) if isinstance(v, dict) else v)

    # ---- figures
    g = st["gain"]
    gain_xy = [(curve[i][0], -g[i]) for i in range(1, len(curve) - 1)]
    s1, X, Y = svg_chart(560, 330,
        [dict(name="V_OUT", xy=curve, color="var(--c1)"),
         dict(name="V_OUT = V_IN", xy=[(0, 0), (VDD, VDD)], color="var(--ink-3)", w=1, dash="2 4", nohover=True)],
        "V_IN (V)", "V_OUT (V)", (0, VDD), (0, VDD))
    marks = (f'<circle cx="{X(st["VM"]):.1f}" cy="{Y(st["VM"]):.1f}" r="4" fill="var(--c1)" stroke="var(--bg)" stroke-width="2"/>'
             f'<text x="{X(st["VM"])+8:.1f}" y="{Y(st["VM"])-8:.1f}" fill="var(--ink)">V_M = {st["VM"]*1e3:.0f} mV</text>')
    for (vx, vy, lab, dx, dy) in ((st["VIL"], st["VOH"], "V_IL", -6, -8), (st["VIH"], st["VOL"], "V_IH", 6, 14)):
        marks += (f'<circle cx="{X(vx):.1f}" cy="{Y(vy):.1f}" r="4" fill="var(--c2)" stroke="var(--bg)" stroke-width="2"/>'
                  f'<text x="{X(vx)+dx:.1f}" y="{Y(vy)+dy:.1f}" text-anchor="{"end" if dx<0 else "start"}" fill="var(--ink)">{lab} = {vx*1e3:.0f} mV</text>')
    open("fig_vtc.svg", "w").write(s1.replace("</svg>", marks + "</svg>"))

    gmax = -st["gain_max"]
    s1b, X, Y = svg_chart(560, 240,
        [dict(name="|A_v| = |dV_OUT/dV_IN|", xy=gain_xy, color="var(--c2)"),
         dict(name="unity gain", xy=[(0, 1), (VDD, 1)], color="var(--ink-3)", w=1, dash="2 4", nohover=True)],
        "V_IN (V)", "|A_v|", (0, VDD), (0, 30))
    open("fig_gain.svg", "w").write(s1b)

    w = fo4["wave"]
    s2, X, Y = svg_chart(560, 300,
        [dict(name="V_IN", xy=list(zip([t*1e12 for t in w["t"]], w["vin"])), color="var(--ink-3)", w=1.5),
         dict(name="V_OUT (FO4)", xy=list(zip([t*1e12 for t in w["t"]], w["vout"])), color="var(--c1)"),
         dict(name="V_OUT (FO1)", xy=list(zip([t*1e12 for t in fo1["wave"]["t"]], fo1["wave"]["vout"])), color="var(--c2)", dash="5 4")],
        "time (ps)", "voltage (V)", (0, 80), (0, VDD))
    open("fig_tran.svg", "w").write(s2)

    n_rows, p_rows = idvg("n"), idvg("p")
    s3, X, Y = svg_chart(560, 330,
        [dict(name="NMOS  V_DS = 0.7 V", xy=[(v, i) for v, i, _ in n_rows], color="var(--c1)"),
         dict(name="NMOS  V_DS = 50 mV", xy=[(v, i) for v, _, i in n_rows], color="var(--c1)", dash="5 4"),
         dict(name="PMOS  |V_DS| = 0.7 V", xy=[(v, i) for v, i, _ in p_rows], color="var(--c2)"),
         dict(name="PMOS  |V_DS| = 50 mV", xy=[(v, _, i)[2] and (v, i) for v, _, i in p_rows], color="var(--c2)", dash="5 4")],
        "|V_GS| (V)", "|I_D| (A)", (0, VDD), (1e-10, 1e-3), log=True)
    open("fig_idvg.svg", "w").write(s3)
    print("figures written")
