#!/usr/bin/env python3
"""
sram6t.py -- 6T SRAM bitcell reference analysis with the compact model.

    python3 sram6t.py                  -> results_sram6t.json + fig_sram_butterfly.svg, fig_sram_snm_vdd.svg
    GAA_TECH=finfet python3 sram6t.py  -> results_sram6t_finfet.json

Metrics: hold SNM, read SNM (butterfly, 45-degree method), write trip voltage (BL sweep),
read current and read-disturb voltage, cell leakage.  GAA HD cell: PD 36-nm / PG 24-nm /
PU 20-nm sheets (beta 1.41, gamma 1.55).  FinFET HD cell: 1-1-1 fins (beta 1.0).
"""
import json, math
import ref_model as rm

if rm.FINFET:
    W_PD = W_PG = 1.0 / 2.0            # 1 fin each (ref calibration is 2 fins)
    W_PU = 1.0 / 2.0
else:
    base_n, base_p = rm.w_eff(30e-9), rm.w_eff(45e-9)
    W_PD, W_PG, W_PU = rm.w_eff(36e-9) / base_n, rm.w_eff(24e-9) / base_n, rm.w_eff(20e-9) / base_p
BETA = W_PD / W_PG

def i_n(w, vg, vs, vd):
    if vd >= vs: return w * rm.ids("n", vg - vs, vd - vs)
    return -w * rm.ids("n", vg - vd, vs - vd)
def i_pu(vg, vd):   return W_PU * rm.i_p(vg, vd)          # PMOS source at VDD

def node(v_other, bl, wl, vdd):
    """DC voltage of a storage node driven by the other node (gate) with its access transistor
    to bit line 'bl' under word line 'wl'. Bisection on the node voltage."""
    lo, hi = 0.0, vdd
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        # access transistor current into the node (positive when BL > node)
        i_pg = i_n(W_PG, wl, mid, bl) if bl >= mid else -i_n(W_PG, wl, bl, mid)
        i_in = i_pu(v_other, mid) + i_pg
        i_out = i_n(W_PD, v_other, 0.0, mid)
        if i_in > i_out: lo = mid
        else: hi = mid
    return 0.5 * (lo + hi)

def butterfly(mode, vdd, npts=121):
    wl = vdd if mode == "read" else 0.0
    xs = [vdd * i / (npts - 1) for i in range(npts)]
    return [(x, node(x, vdd, wl, vdd)) for x in xs]

def snm(curve, vdd):
    """Side of the largest square that fits in one lobe between y = f(x) and its mirror x = f(y).
    For a square [x0, x0+s] x [y0, y0+s] under curve 1 and right of curve 2 the binding corners are
    top-right (y0 + s <= f(x0 + s)) and bottom-left (x0 >= f(y0)); with y0 = f(x0+s) - s the
    condition is x0 >= f(f(x0+s) - s).  Both inverters are identical, so one lobe suffices."""
    xs = [p[0] for p in curve]; ys = [p[1] for p in curve]
    def f(x):
        if x <= xs[0]: return ys[0]
        if x >= xs[-1]: return ys[-1]
        k = int((len(xs) - 1) * (x - xs[0]) / (xs[-1] - xs[0]))
        k = min(max(k, 0), len(xs) - 2)
        return ys[k] + (ys[k + 1] - ys[k]) * (x - xs[k]) / (xs[k + 1] - xs[k])
    best = 0.0
    for i in range(0, len(xs) - 1):
        x0 = xs[i]
        lo, hi = 0.0, vdd - x0
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            y0 = f(x0 + mid) - mid
            if y0 >= 0 and x0 >= f(y0): lo = mid
            else: hi = mid
        best = max(best, lo)
    return best

def dc_state(bl, blb, wl, vdd, q=None, qb=None, iters=400):
    q = vdd if q is None else q; qb = 0.0 if qb is None else qb
    for _ in range(iters):
        q_new = node(qb, bl, wl, vdd)
        qb_new = node(q_new, blb, wl, vdd)
        if abs(q_new - q) < 1e-6 and abs(qb_new - qb) < 1e-6:
            q, qb = q_new, qb_new; break
        q, qb = 0.5 * (q + q_new), 0.5 * (qb + qb_new)
    return q, qb

def write_trip(vdd):
    """Cell holds Q=1: sweep BL down (BLB=VDD, WL=VDD) until the cell flips (Q < QB)."""
    lo, hi = 0.0, vdd
    for _ in range(24):
        mid = 0.5 * (lo + hi)
        q, qb = dc_state(mid, vdd, vdd, vdd)
        if q < qb: lo = mid
        else: hi = mid
    return 0.5 * (lo + hi)

def read_metrics(vdd):
    q0 = node(vdd, vdd, vdd, vdd)                   # '0' node with QB=VDD, BL=WL=VDD (read disturb)
    i_read = i_n(W_PG, vdd, q0, vdd)
    return q0, i_read

def leakage(vdd):
    # hold: Q=VDD, QB=0, BL=BLB=VDD, WL=0
    i = (i_n(W_PD, 0.0, 0.0, vdd)            # PD1 off, Vds = VDD (node Q=1)
         + W_PU * rm.i_p(vdd, 0.0)            # PU2 off, Vds = -VDD (node QB=0)
         + i_n(W_PG, 0.0, 0.0, vdd))          # PG2 off, BLB=VDD, QB=0
    return i

if __name__ == "__main__":
    V = rm.VDD
    hold = butterfly("hold", V); read = butterfly("read", V)
    res = dict(tech="finfet" if rm.FINFET else "gaa", W_PD=W_PD, W_PG=W_PG, W_PU=W_PU, beta=BETA,
               gamma=(W_PG * rm.DEV["n"]["ion"]) / (W_PU * rm.DEV["p"]["ion"]),
               SNM_hold_mV=snm(hold, V) * 1e3, SNM_read_mV=snm(read, V) * 1e3,
               V_trip_mV=write_trip(V) * 1e3,
               area_um2=0.0210 if rm.FINFET else 0.216 * 0.096, sweep=[])
    q0, ir = read_metrics(V)
    res.update(V_read_disturb_mV=q0 * 1e3, I_read_uA=ir * 1e6, I_leak_pA=leakage(V) * 1e12,
               P_leak_pW=leakage(V) * V * 1e12)
    for vdd in (0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80):
        rm.VDD = vdd
        res["sweep"].append(dict(VDD=vdd, SNM_hold_mV=snm(butterfly("hold", vdd), vdd) * 1e3,
                                 SNM_read_mV=snm(butterfly("read", vdd), vdd) * 1e3,
                                 V_trip_mV=write_trip(vdd) * 1e3))
    rm.VDD = V
    json.dump(res, open("results_sram6t_finfet.json" if rm.FINFET else "results_sram6t.json", "w"), indent=1)
    print(res["tech"], {k: (round(v, 3) if isinstance(v, float) else v) for k, v in res.items() if k != "sweep"})
    for s in res["sweep"]: print("  ", s)
    if not rm.FINFET:
        mirror = lambda cv: [(y, x) for x, y in cv]
        s, X, Y = rm.svg_chart(560, 420,
            [dict(name="read: Q = f(QB)", xy=read, color="var(--c1)"),
             dict(name="read: QB = f(Q)", xy=sorted(mirror(read)), color="var(--c1)", dash="5 4"),
             dict(name="hold: Q = f(QB)", xy=hold, color="var(--c2)"),
             dict(name="hold: QB = f(Q)", xy=sorted(mirror(hold)), color="var(--c2)", dash="5 4")],
            "V_QB (V)", "V_Q (V)", (0, V), (0, V))
        open("fig_sram_butterfly.svg", "w").write(s)
        f = json.load(open("results_sram6t_finfet.json")) if __import__("os").path.exists("results_sram6t_finfet.json") else None
        series = [dict(name="GAA read SNM", xy=[(r["VDD"], r["SNM_read_mV"]) for r in res["sweep"]], color="var(--c1)"),
                  dict(name="GAA hold SNM", xy=[(r["VDD"], r["SNM_hold_mV"]) for r in res["sweep"]], color="var(--c1)", dash="5 4")]
        if f:
            series += [dict(name="FinFET read SNM", xy=[(r["VDD"], r["SNM_read_mV"]) for r in f["sweep"]], color="var(--c2)"),
                       dict(name="FinFET hold SNM", xy=[(r["VDD"], r["SNM_hold_mV"]) for r in f["sweep"]], color="var(--c2)", dash="5 4")]
        top = max(max(y for _, y in s_["xy"]) for s_ in series)
        s, X, Y = rm.svg_chart(560, 320, series, "V_DD (V)", "SNM (mV)", (0.4, 0.8), (0, math.ceil(top * 1.1 / 50) * 50))
        open("fig_sram_snm_vdd.svg", "w").write(s)
        print("SRAM figures written")
