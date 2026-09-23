"""Run all in-silico experiments and write readings/measurements to results/.

E1  Reactor characterisation (plant readings: parametric sweeps, fresh catalyst)
E2  Digital-twin fidelity benchmark (one-step-ahead forecasting under DoE excitation,
    240 h campaign with sintering, nitridation, U_b ageing and a poisoning event)
E3  Closed-loop renewable-powered operation benchmark (twin-in-the-loop control)
E4  Sensitivity: sensor-noise level (E2 setting) and deactivation severity (E3 setting)

Pilot/design seeds 0-9 were used during method development; all reported
numbers use held-out seeds 10-29.

Usage:  python experiments/run_experiments.py [--quick]
"""
from __future__ import annotations

import os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")  # one BLAS thread per worker process

import argparse  # noqa: E402
import json  # noqa: E402
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from pcmr.plant import Plant, Inputs  # noqa: E402
from pcmr.scenario import random_doe_inputs, renewable_power  # noqa: E402
from pcmr import twins as TW, control as C  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
RES = os.path.join(ROOT, "results")
DT, N_STEPS, T_MAX, N_TRAIN = 0.5, 480, 460.0, 96
HORIZON = DT * N_STEPS
SEEDS = list(range(10, 30))


def zvec(o):
    return np.array([np.log(o["y_meas"]), np.log(o["P_meas"]), o["T_meas"]])


# ============================================================== E1
def e1_characterisation():
    pl = Plant(seed=0)
    base = dict(V=9.0, f=20.0, Q=100.0, xH2=0.75)
    sweeps = dict(V=np.arange(6.0, 11.51, 0.5), f=np.arange(10.0, 30.1, 2.5),
                  Q=np.array([30, 40, 60, 80, 100, 130, 160, 200, 250.0]),
                  xH2=np.arange(0.25, 0.901, 0.05))
    rows = []
    for var, vals in sweeps.items():
        for v in vals:
            u = dict(base); u[var] = float(v)
            s = pl.steady_state(Inputs(**u))
            rows.append(dict(sweep=var, V_kV=u["V"], f_kHz=u["f"], Q_sccm=u["Q"], xH2=u["xH2"],
                             P_W=s["P"], SEI_kJ_per_L=s["SEI"], T_bed_K=s["T_mean"], T_hot_K=s["T_hot"],
                             y_NH3_pct=100 * s["y"], X_N2_pct=100 * s["X_N2"], NH3_g_per_h=s["mdot_gph"],
                             EY_g_per_kWh=s["EY"], tau_s=s["tau"]))
    return pd.DataFrame(rows)


# ============================================================== E2
def make_twins(seed):
    return [TW.StaticPhysicsTwin(), TW.BatchRecalTwin(),
            TW.StaticMLTwin("rsm", N_TRAIN, seed), TW.StaticMLTwin("ann", N_TRAIN, seed),
            TW.StaticMLTwin("gpr", N_TRAIN, seed), TW.SlidingGPRTwin(N_TRAIN, 12, seed),
            TW.PCHDT(seed=seed),
            TW.PCHDT(seed=seed, residual=False, name="Ablation: no residual"),
            TW.PCHDT(seed=seed, adaptive=False, name="Ablation: no adaptive inflation"),
            TW.PCHDT(seed=seed, deact_drift=False, name="Ablation: no deactivation drift")]


def e2_run(args):
    seed, noise, which = args
    U = random_doe_inputs(N_STEPS, seed)
    plant = Plant(seed=seed, noise_scale=noise)
    twins = make_twins(seed)
    if which is not None:
        twins = [t for t in twins if t.name in which]
    nT = len(twins)
    F = np.zeros((nT, N_STEPS, 3)); S = np.zeros_like(F); Ah = np.full((nT, N_STEPS), np.nan)
    Z = np.zeros((N_STEPS, 3)); Ztrue = np.zeros((N_STEPS, 3)); A = np.zeros(N_STEPS)
    tcomp = np.zeros(nT)
    for k in range(N_STEPS):
        for i, t in enumerate(twins):
            F[i, k], S[i, k] = t.forecast(U[k])
        o = plant.step(Inputs(*U[k]), DT)
        Z[k] = zvec(o); Ztrue[k] = [np.log(o["y"]), np.log(o["P"]), o["T_mean"]]; A[k] = o["a_true"]
        for i, t in enumerate(twins):
            t0 = time.perf_counter(); t.update(U[k], Z[k]); tcomp[i] += time.perf_counter() - t0
            if hasattr(t, "activity"):
                Ah[i, k] = t.activity()
    m = slice(N_TRAIN, None)
    rows = []
    ref = N_TRAIN  # relative-activity reference: end of commissioning window (48 h)
    for i, t in enumerate(twins):
        yp, ym = np.exp(F[i, m, 0]), np.exp(Z[m, 0])
        rows.append(dict(
            seed=seed, noise=noise, method=t.name,
            MAPE_NH3_pct=100 * np.mean(np.abs(yp - ym) / ym),
            RMSE_NH3_ppm=1e6 * np.sqrt(np.mean((yp - ym) ** 2)),
            R2_NH3=1 - np.sum((yp - ym) ** 2) / np.sum((ym - ym.mean()) ** 2),
            MAPE_NH3_post_event_pct=100 * np.mean((np.abs(yp - ym) / ym)[(np.arange(N_STEPS)[m] * DT) >= 140]),
            PICP95_NH3=np.mean(np.abs(F[i, m, 0] - Z[m, 0]) <= 1.96 * S[i, m, 0]),
            MPIW95_NH3_rel=np.mean(2 * 1.96 * S[i, m, 0]),
            RMSE_P_W=np.sqrt(np.mean((np.exp(F[i, m, 1]) - np.exp(Z[m, 1])) ** 2)),
            RMSE_T_K=np.sqrt(np.mean((F[i, m, 2] - Z[m, 2]) ** 2)),
            RMSE_rel_activity=(np.sqrt(np.mean((Ah[i, m] / Ah[i, ref] - A[m] / A[ref]) ** 2))
                               if not np.isnan(Ah[i, ref]) and t.name != "Static physics" else np.nan),
            update_ms=1e3 * tcomp[i] / N_STEPS))
    trace = None
    if seed == SEEDS[0] and noise == 1.0 and which is None:
        trace = dict(t_h=np.arange(N_STEPS) * DT, U=U, Z=Z, Ztrue=Ztrue, A=A,
                     names=[t.name for t in twins], F=F, S=S, Ah=Ah)
    return rows, trace


# ============================================================== E3
def make_controllers(seed):
    u_star = C.nominal_optimum(T_MAX)
    return [C.FixedSetpoint(u_star),
            C.ThermalPI(u_star, T_MAX - 10.0),
            C.ModelOptimizer(TW.StaticPhysicsTwin(), T_MAX, HORIZON, False, False, "Static-model optimiser"),
            C.ModelOptimizer(TW.BatchRecalTwin(), T_MAX, HORIZON, False, False, "Recalibrated-model optimiser"),
            C.ModelOptimizer(TW.PCHDT(seed=seed), T_MAX, HORIZON, True, True, "PC-HDT optimiser (proposed)"),
            C.ModelOptimizer(TW.PCHDT(seed=seed), T_MAX, HORIZON, False, False, "Ablation: deterministic PC-HDT"),
            C.ModelOptimizer(TW.PCHDT(seed=seed), T_MAX, HORIZON, True, False, "Ablation: no degradation cost"),
            C.ModelOptimizer(TW.PCHDT(seed=seed), T_MAX, HORIZON, False, True, "Ablation: no chance constraint")]


def e3_run(args):
    seed, deact, which = args
    Pcap = renewable_power(N_STEPS, DT, seed)
    rows, traces = [], {}
    for c in make_controllers(seed):
        if which is not None and c.name not in which:
            continue
        plant = Plant(seed=seed, deact_scale=deact)
        last, log, tc = None, [], 0.0
        for k in range(N_STEPS):
            t0 = time.perf_counter()
            u = c.act(k * DT, Pcap[k], last)
            tc += time.perf_counter() - t0
            o = plant.step(Inputs(*u), DT, P_cap=Pcap[k])
            ua = np.array(u, float); ua[0] = o["V_applied"]
            t0 = time.perf_counter(); c.observe(ua, zvec(o)); tc += time.perf_counter() - t0
            last = o
            log.append((k * DT, Pcap[k], *ua, o["P"], o["T_mean"], o["T_hot"], 100 * o["y"],
                        o["mdot_gph"], o["EY"], o["a_true"], int(o["limited"])))
        L = np.array(log)
        g = float(np.sum(L[:, 10]) * DT); E = float(np.sum(L[:, 6]) * DT / 1000.0)
        rows.append(dict(seed=seed, deact_scale=deact, controller=c.name, NH3_total_g=g,
                         energy_kWh=E, EY_g_per_kWh=g / E, renewable_util_pct=100 * E / (Pcap.sum() * DT / 1000),
                         T_violation_h=float(np.sum(L[:, 7] > T_MAX) * DT),
                         T_max_K=float(L[:, 7].max()), final_activity=float(plant.state.a),
                         limiter_events=int(L[:, 13].sum()), decision_ms=1e3 * tc / N_STEPS))
        if seed == SEEDS[0] and deact == 1.0 and which is None:
            traces[c.name] = L
    return rows, traces


# ============================================================== stats
def paired_stats(df, key, group, proposed, metrics, better):
    out = []
    P = df[df[group] == proposed].set_index("seed")
    for name in df[group].unique():
        if name == proposed:
            continue
        B = df[df[group] == name].set_index("seed")
        for mtr in metrics:
            a, b = P[mtr].dropna(), B[mtr].dropna()
            idx = a.index.intersection(b.index)
            if len(idx) < 5 or np.allclose(a[idx], b[idx]):
                p = np.nan
            else:
                p = wilcoxon(a[idx], b[idx]).pvalue
            d = a[idx].mean() - b[idx].mean()
            out.append(dict(comparison=f"{proposed} vs {name}", metric=mtr, mean_diff=d,
                            proposed_better=bool((d < 0) if better[mtr] == "low" else (d > 0)),
                            wilcoxon_p=p, n=len(idx)))
    return pd.DataFrame(out)


def summarise(df, group, metrics):
    g = df.groupby(group, sort=False)[metrics]
    m, s = g.mean(), g.std()
    out = m.copy()
    for c in metrics:
        out[c] = [f"{a:.4g} ± {b:.2g}" for a, b in zip(m[c], s[c])]
    return out.reset_index()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="3 seeds, for smoke testing")
    ap.add_argument("--procs", type=int, default=os.cpu_count())
    a = ap.parse_args()
    seeds = SEEDS[:3] if a.quick else SEEDS
    os.makedirs(RES, exist_ok=True)
    t_start = time.time()

    print("E1 characterisation ...")
    e1 = e1_characterisation(); e1.to_csv(os.path.join(RES, "E1_characterisation_readings.csv"), index=False)

    with Pool(a.procs) as pool:
        print("E2 twin fidelity ...")
        out = pool.map(e2_run, [(s, 1.0, None) for s in seeds])
        e2 = pd.DataFrame([r for rows, _ in out for r in rows])
        tr = [t for _, t in out if t is not None][0]
        e2.to_csv(os.path.join(RES, "E2_twin_fidelity_per_seed.csv"), index=False)
        np.savez_compressed(os.path.join(RES, "E2_trace_seed10.npz"), **{k: np.asarray(v) for k, v in tr.items()})
        m2 = ["MAPE_NH3_pct", "RMSE_NH3_ppm", "R2_NH3", "MAPE_NH3_post_event_pct", "PICP95_NH3",
              "MPIW95_NH3_rel", "RMSE_P_W", "RMSE_T_K", "RMSE_rel_activity", "update_ms"]
        summarise(e2, "method", m2).to_csv(os.path.join(RES, "E2_twin_fidelity_summary.csv"), index=False)
        better2 = {k: "low" for k in m2}; better2["R2_NH3"] = "high"; better2["PICP95_NH3"] = "high"
        paired_stats(e2, "seed", "method", "PC-HDT (proposed)",
                     ["MAPE_NH3_pct", "RMSE_T_K", "RMSE_P_W", "PICP95_NH3"], better2
                     ).to_csv(os.path.join(RES, "E2_wilcoxon.csv"), index=False)

        print("E3 closed-loop control ...")
        out = pool.map(e3_run, [(s, 1.0, None) for s in seeds])
        e3 = pd.DataFrame([r for rows, _ in out for r in rows])
        traces = [t for _, t in out if t][0]
        e3.to_csv(os.path.join(RES, "E3_control_per_seed.csv"), index=False)
        np.savez_compressed(os.path.join(RES, "E3_trace_seed10.npz"),
                            **{k.replace(" ", "_").replace(":", ""): v for k, v in traces.items()})
        m3 = ["NH3_total_g", "energy_kWh", "EY_g_per_kWh", "renewable_util_pct", "T_violation_h",
              "T_max_K", "final_activity", "limiter_events", "decision_ms"]
        summarise(e3, "controller", m3).to_csv(os.path.join(RES, "E3_control_summary.csv"), index=False)
        better3 = dict(NH3_total_g="high", EY_g_per_kWh="high", T_violation_h="low", final_activity="high")
        paired_stats(e3, "seed", "controller", "PC-HDT optimiser (proposed)", list(better3), better3
                     ).to_csv(os.path.join(RES, "E3_wilcoxon.csv"), index=False)

        print("E4 sensitivity ...")
        s4 = seeds[:10]
        sel2 = ["Batch recalibration", "GPR (sliding window)", "PC-HDT (proposed)"]
        out = pool.map(e2_run, [(s, nz, sel2) for nz in [0.5, 1.0, 2.0, 3.0] for s in s4])
        e4a = pd.DataFrame([r for rows, _ in out for r in rows])
        e4a.to_csv(os.path.join(RES, "E4a_noise_sensitivity.csv"), index=False)
        sel3 = ["Thermal PI (max-load)", "Static-model optimiser", "Recalibrated-model optimiser",
                "PC-HDT optimiser (proposed)"]
        out = pool.map(e3_run, [(s, d, sel3) for d in [0.5, 1.0, 2.0] for s in s4])
        e4b = pd.DataFrame([r for rows, _ in out for r in rows])
        e4b.to_csv(os.path.join(RES, "E4b_deactivation_sensitivity.csv"), index=False)

    meta = dict(seeds=seeds, dt_h=DT, n_steps=N_STEPS, T_max_K=T_MAX, n_train=N_TRAIN,
                runtime_s=round(time.time() - t_start, 1), numpy=np.__version__, pandas=pd.__version__)
    json.dump(meta, open(os.path.join(RES, "run_metadata.json"), "w"), indent=2)
    print("done in", meta["runtime_s"], "s")


if __name__ == "__main__":
    main()
