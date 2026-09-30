#!/usr/bin/env python3
"""
ro.py -- N-stage ring-oscillator simulation with the reference compact model.

    python3 ro.py                 # GAA nanosheet RO11: results_ro.json
    GAA_TECH=finfet python3 ro.py # FinFET baseline:    results_ro_finfet.json
    python3 ro.py --figs          # fig_ro_wave.svg, fig_ro_fvdd.svg, fig_ro_pvdd.svg from both JSONs

Each node is loaded by the next stage's gate capacitance (C_in) and its own drain
parasitics (C_par); node voltages are integrated with forward Euler (dt = 8 fs).
"""
import json, math, os, sys
import ref_model as rm

N_STAGES = 11
CIN  = 0.30e-15 if rm.FINFET else 0.32e-15
CPAR = 0.40e-15 if rm.FINFET else 0.35e-15
FANOUT = 3                      # FO3-loaded RO: library-characterisation convention
C_NODE = FANOUT * CIN + CPAR

def simulate(vdd, n=N_STAGES, tstop=600e-12, dt=8e-15):
    rm.VDD = vdd                                   # model closes over module VDD
    v = [vdd if i % 2 else 0.0 for i in range(n)]
    v[0] = vdd * 0.45                              # kick
    t = 0.0; ts, v0, v1, idd = [], [], [], []
    step = 0
    while t <= tstop:
        ip_sum = 0.0; nv = v[:]
        for i in range(n):
            vin = v[i - 1]
            ip = rm.i_p(vin, v[i]); inn = rm.i_n(vin, v[i])
            ip_sum += ip
            nv[i] = min(max(v[i] + dt * (ip - inn) / C_NODE, -0.05), vdd + 0.05)
        v = nv
        if step % 10 == 0:
            ts.append(t); v0.append(v[0]); v1.append(v[1]); idd.append(ip_sum)
        t += dt; step += 1
    # period from rising half-VDD crossings of node 0 in the second half of the run
    half = vdd / 2; cr = []
    for k in range(1, len(ts)):
        if ts[k] > tstop / 2 and v0[k - 1] < half <= v0[k]:
            cr.append(ts[k - 1] + (half - v0[k - 1]) / (v0[k] - v0[k - 1]) * (ts[k] - ts[k - 1]))
    if len(cr) < 3:
        return None
    T = (cr[-1] - cr[0]) / (len(cr) - 1)
    sel = [k for k in range(len(ts)) if cr[0] <= ts[k] <= cr[-1]]
    p_avg = sum(idd[k] for k in sel) / len(sel) * vdd
    p_leak = 0.5 * (rm.i_n(0.0, vdd) + rm.i_p(vdd, 0.0)) * vdd * n
    return dict(VDD=vdd, N=n, f_Hz=1.0 / T, T_s=T, t_stage_s=T / (2 * n), P_W=p_avg, P_leak_W=p_leak,
                E_stage_J=(p_avg - p_leak) * T / n,        # dynamic energy per stage per cycle
                wave=dict(t=[round(x * 1e12, 3) for x in ts], v0=[round(x, 4) for x in v0],
                          v1=[round(x, 4) for x in v1]))

def main():
    out = {"tech": "finfet" if rm.FINFET else "gaa", "N": N_STAGES, "fanout": FANOUT, "C_node_fF": C_NODE * 1e15, "sweep": []}
    for vdd in (0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80):
        r = simulate(vdd)
        if r is None: continue
        if abs(vdd - 0.70) < 1e-9:
            out["nominal"] = r
        out["sweep"].append({k: r[k] for k in r if k != "wave"})
        print(f"{out['tech']:6s} VDD={vdd:.2f}  f={r['f_Hz']/1e9:6.2f} GHz  t_stage={r['t_stage_s']*1e12:5.2f} ps  "
              f"P={r['P_W']*1e6:6.2f} uW  E/stage={r['E_stage_J']*1e18:6.1f} aJ")
    json.dump(out, open("results_ro_finfet.json" if rm.FINFET else "results_ro.json", "w"), indent=1)

def ylim(v):
    step = 10 ** math.floor(math.log10(v)) / 2
    return math.ceil(v * 1.08 / step) * step

def figs():
    g = json.load(open("results_ro.json")); f = json.load(open("results_ro_finfet.json"))
    w = g["nominal"]["wave"]
    sel = [k for k in range(len(w["t"])) if 300 <= w["t"][k] <= 500]
    s, X, Y = rm.svg_chart(560, 280,
        [dict(name="node 1 (GAA RO11, FO3)", xy=[(w["t"][k] - 300, w["v0"][k]) for k in sel], color="var(--c1)"),
         dict(name="node 2", xy=[(w["t"][k] - 300, w["v1"][k]) for k in sel], color="var(--c2)", dash="5 4")],
        "time (ps)", "node voltage (V)", (0, 200), (0, 0.7))
    open("fig_ro_wave.svg", "w").write(s)
    s, X, Y = rm.svg_chart(560, 300,
        [dict(name="GAA nanosheet", xy=[(r["VDD"], r["f_Hz"] / 1e9) for r in g["sweep"]], color="var(--c1)"),
         dict(name="FinFET", xy=[(r["VDD"], r["f_Hz"] / 1e9) for r in f["sweep"]], color="var(--c2)")],
        "V_DD (V)", "f_osc (GHz)", (0.5, 0.8), (0, ylim(max(r["f_Hz"] for r in g["sweep"]) / 1e9)))
    open("fig_ro_fvdd.svg", "w").write(s)
    s, X, Y = rm.svg_chart(560, 300,
        [dict(name="GAA nanosheet", xy=[(r["VDD"], r["P_W"] * 1e6) for r in g["sweep"]], color="var(--c1)"),
         dict(name="FinFET", xy=[(r["VDD"], r["P_W"] * 1e6) for r in f["sweep"]], color="var(--c2)")],
        "V_DD (V)", "P_avg (µW)", (0.5, 0.8), (0, ylim(max(r["P_W"] for r in g["sweep"]) * 1e6)))
    open("fig_ro_pvdd.svg", "w").write(s)
    print("RO figures written")

if __name__ == "__main__":
    figs() if "--figs" in sys.argv else main()
