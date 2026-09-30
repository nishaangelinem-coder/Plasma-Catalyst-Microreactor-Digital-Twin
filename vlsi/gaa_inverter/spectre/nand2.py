#!/usr/bin/env python3
"""
nand2.py -- NAND2_GAA_X1 reference simulation (static, transient, leakage by input state).

    python3 nand2.py                  -> results_nand2.json, fig_nand2_vtc.svg, fig_nand2_tran.svg
    GAA_TECH=finfet python3 nand2.py  -> results_nand2_finfet.json

Topology: PMOS A || PMOS B (VDD -> Y); NMOS A (VSS -> X) in series with NMOS B (X -> Y).
GAA sizing: NMOS 45-nm sheets (W_eff 300 nm), PMOS 30-nm sheets (W_eff 210 nm): the bands
of the inverter swapped.  FinFET baseline keeps 2 fins per device (no rebalancing possible).
"""
import json, math
import ref_model as rm

if rm.FINFET:
    WN, WP = 1.0, 1.0                      # 2 fins each, quantised
else:
    WN = rm.w_eff(45e-9) / rm.w_eff(30e-9)  # 300/210
    WP = rm.w_eff(30e-9) / rm.w_eff(45e-9)  # 210/300
CIN  = 0.30e-15 if rm.FINFET else 0.32e-15
CPAR = 0.45e-15 if rm.FINFET else 0.40e-15  # two drains on the output node
CX   = 0.15e-15                             # internal stack node

def i_n(vg, vs, vd): return WN * rm.ids("n", vg - vs, vd - vs) if vd > vs else -WN * rm.ids("n", vg - vd, vs - vd)
def i_p(vg, vd): return WP * rm.i_p(vg, vd)

def stack_x(va, vb, vy):
    """Internal node X for which I(MNA) = I(MNB) at DC; bisection."""
    lo, hi = 0.0, max(vy, 0.0)
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if i_n(va, 0.0, mid) > i_n(vb, mid, vy): hi = mid   # bottom device discharges X faster than top charges it
        else: lo = mid
    return 0.5 * (lo + hi)

def i_pd(va, vb, vy):
    return i_n(va, 0.0, stack_x(va, vb, vy))

def vout_dc(va, vb):
    lo, hi = 0.0, rm.VDD
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if i_pd(va, vb, mid) > i_p(va, mid) + i_p(vb, mid): hi = mid
        else: lo = mid
    return 0.5 * (lo + hi)

def vtc(mode, npts=141):
    pts = []
    for i in range(npts):
        v = rm.VDD * i / (npts - 1)
        va, vb = {"AB": (v, v), "A": (v, rm.VDD), "B": (rm.VDD, v)}[mode]
        pts.append((v, vout_dc(va, vb)))
    return pts

def vm(curve):
    return next(x for x, y in curve if y <= x)

def transient(mode, cl, tr=12e-12, tstop=80e-12, dt=2e-15):
    """Input 'mode' ('A', 'B' or 'AB') gets 0->VDD->0; the other input is held at VDD."""
    C = cl + CPAR; V = rm.VDD; t0, t1 = 10e-12, 45e-12; ramp = tr / 0.8
    def stim(t):
        if t < t0: return 0.0
        if t < t0 + ramp: return V * (t - t0) / ramp
        if t < t1: return V
        if t < t1 + ramp: return V * (1 - (t - t1) / ramp)
        return 0.0
    vy, vx = V, V - 0.05
    t = 0.0; ts, vin, vout, e = [], [], [], 0.0
    k = 0
    while t <= tstop:
        s = stim(t)
        va = s if mode in ("A", "AB") else V
        vb = s if mode in ("B", "AB") else V
        ip = i_p(va, vy) + i_p(vb, vy)
        ia = i_n(va, 0.0, vx); ib = i_n(vb, vx, vy)
        vy += dt * (ip - ib) / C
        vx += dt * (ib - ia) / CX          # MNB charges X from Y, MNA discharges it to VSS
        vy = min(max(vy, -0.05), V + 0.05); vx = min(max(vx, -0.05), V + 0.05)
        e += ip * V * dt
        if k % 25 == 0: ts.append(t); vin.append(s); vout.append(vy)
        t += dt; k += 1
    def cross(sig, level, rising, tstart):
        for i in range(1, len(ts)):
            if ts[i] < tstart: continue
            a, b = sig[i - 1], sig[i]
            if (rising and a < level <= b) or (not rising and a > level >= b):
                return ts[i - 1] + (level - a) / (b - a) * (ts[i] - ts[i - 1])
        return float("nan")
    h = V / 2
    tphl = cross(vout, h, False, t0) - cross(vin, h, True, t0)
    tplh = cross(vout, h, True, t1) - cross(vin, h, False, t1)
    return dict(tpHL=tphl, tpLH=tplh, tpd=0.5 * (tphl + tplh), E_cycle=e, wave=dict(t=ts, vin=vin, vout=vout))

def leakage():
    V = rm.VDD; out = {}
    for a, b in ((0, 0), (0, 1), (1, 0), (1, 1)):
        va, vb = a * V, b * V
        vy = vout_dc(va, vb)
        if a and b:      # output low: PMOS leak, both off
            i = i_p(va, vy) + i_p(vb, vy)
        else:            # output high: NMOS path leaks (stack effect when both off)
            i = i_pd(va, vb, vy)
        out[f"{a}{b}"] = dict(I_nA=i * 1e9, P_pW=i * V * 1e12, Vout=vy)
    return out

if __name__ == "__main__":
    curves = {m: vtc(m) for m in ("AB", "A", "B")}
    fo4 = 4 * CIN
    tr = {m: transient(m, fo4) for m in ("A", "B", "AB")}
    lk = leakage()
    vy_low = vout_dc(rm.VDD, rm.VDD)
    res = dict(
        tech="finfet" if rm.FINFET else "gaa", WN=WN, WP=WP,
        Ion_pd_uA=i_pd(rm.VDD, rm.VDD, rm.VDD) * 1e6,            # series stack, output at VDD
        Ion_pu_uA=i_p(0.0, 0.0) * 1e6,                            # single PMOS, output at 0
        VM={m: vm(curves[m]) for m in curves},
        VOL=vy_low,
        fo4={m: {k: v for k, v in tr[m].items() if k != "wave"} for m in tr},
        leak=lk, P_static_avg_pW=sum(v["P_pW"] for v in lk.values()) / 4,
        area_um2=(0.162 * 0.180) if rm.FINFET else (0.144 * 0.168),
    )
    json.dump(res, open("results_nand2_finfet.json" if rm.FINFET else "results_nand2.json", "w"), indent=1)
    print(json.dumps({k: v for k, v in res.items()}, default=lambda o: round(o, 5))[:900])
    if not rm.FINFET:
        s, X, Y = rm.svg_chart(560, 330,
            [dict(name="A = B switching", xy=curves["AB"], color="var(--c1)"),
             dict(name="A switching, B = V_DD", xy=curves["A"], color="var(--c2)"),
             dict(name="B switching, A = V_DD", xy=curves["B"], color="var(--c2)", dash="5 4"),
             dict(name="V_OUT = V_IN", xy=[(0, 0), (rm.VDD, rm.VDD)], color="var(--ink-3)", w=1, dash="2 4", nohover=True)],
            "V_IN (V)", "V_OUT (V)", (0, rm.VDD), (0, rm.VDD))
        open("fig_nand2_vtc.svg", "w").write(s)
        w = tr["A"]["wave"]; wb = tr["B"]["wave"]
        s, X, Y = rm.svg_chart(560, 300,
            [dict(name="V_IN (switching input)", xy=list(zip([t * 1e12 for t in w["t"]], w["vin"])), color="var(--ink-3)", w=1.5),
             dict(name="V_OUT, A switches (B = 1)", xy=list(zip([t * 1e12 for t in w["t"]], w["vout"])), color="var(--c1)"),
             dict(name="V_OUT, B switches (A = 1)", xy=list(zip([t * 1e12 for t in wb["t"]], wb["vout"])), color="var(--c2)", dash="5 4")],
            "time (ps)", "voltage (V)", (0, 80), (0, rm.VDD))
        open("fig_nand2_tran.svg", "w").write(s)
        print("NAND2 figures written")
