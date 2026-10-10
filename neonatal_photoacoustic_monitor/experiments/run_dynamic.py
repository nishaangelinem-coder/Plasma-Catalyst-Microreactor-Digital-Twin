"""E3 static accuracy, E4 dynamic clinical scenarios, E5 sensitivity (multiprocessing)."""
import sys, os, json, time, argparse, copy
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, pandas as pd
from multiprocessing import Pool
import common
from p2pneo import acoustic as ac, metrics as M
from p2pneo.fluence import FluenceModel
from p2pneo.forward import HeadParams
from p2pneo.subject import sample_head, scenario_hypothermia, scenario_intermittent_hypoxaemia, scenario_static

ap = argparse.ArgumentParser()
ap.add_argument("--quick", action="store_true"); ap.add_argument("--nproc", type=int, default=4)
ap.add_argument("--only", default="E3,E4,E5")
args = ap.parse_args()
RES = common.RES
SEEDS = list(range(10, 14)) if args.quick else list(range(10, 26))      # held-out seeds (0-9 used for development)
SEEDS_E5 = list(range(10, 12)) if args.quick else list(range(10, 18))
HOURS_S1 = 0.3 if args.quick else 10.0
MIN_S2 = 4.0 if args.quick else 45.0
HOURS_E5 = 0.2 if args.quick else 6.0
_FL = None


def get_fl():
    global _FL
    if _FL is None:
        _FL = FluenceModel(common.TABLE)
    return _FL


def summarise(res, scen_name):
    """Per-run metrics for every method."""
    tr = res["truth"]; rows = []
    for m, e in res["so2"].items():
        ok = ~np.isnan(e)
        if ok.sum() < 5:
            continue
        d = dict(scenario=scen_name, method=m, quantity="sO2", rmse=M.rmse(e[ok], tr["so2"][ok]) * 100,
                 bias=M.bias(e[ok], tr["so2"][ok]) * 100, mae=M.mae(e[ok], tr["so2"][ok]) * 100,
                 maxerr=M.maxerr(e[ok], tr["so2"][ok]) * 100)
        d["loa_lo"], d["loa_hi"] = [100 * v for v in M.loa(e[ok], tr["so2"][ok])]
        if res["events"]:
            ev = M.event_detection(res["t"], e, res["events"], res["t"][1] - res["t"][0])
            d.update(sensitivity=ev["sensitivity"], false_alarms_per_h=ev["false_alarms_per_h"], latency_s=ev["median_latency_s"])
        if m == "Proposed EKF":
            d["coverage95"] = M.coverage(e[ok], res["sd"]["so2"][ok], tr["so2"][ok])
        rows.append(d)
    T0 = tr["T_b"][0]
    for m, e in res["T"].items():
        ok = ~np.isnan(e)
        if ok.sum() < 5:
            continue
        d = dict(scenario=scen_name, method=m, quantity="T", rmse=M.rmse(e[ok], tr["T_b"][ok]), bias=M.bias(e[ok], tr["T_b"][ok]),
                 mae=M.mae(e[ok], tr["T_b"][ok]), maxerr=M.maxerr(e[ok], tr["T_b"][ok]),
                 rmse_rel=M.rmse(e[ok] - e[ok][0], tr["T_b"][ok] - T0))
        d["loa_lo"], d["loa_hi"] = M.loa(e[ok], tr["T_b"][ok])
        if m == "Proposed EKF":
            d["coverage95"] = M.coverage(e[ok], res["sd"]["T"][ok], tr["T_b"][ok])
            d["grad_rmse"] = M.rmse(e[ok] - res["Ts_est"][ok], tr["T_b"][ok] - tr["T_s"][ok])
            d["g_rmse"] = M.rmse(res["g_est"][ok], tr["g"][ok])
        rows.append(d)
    return rows


def job_E3(seed):
    fl = get_fl(); rng = np.random.default_rng(seed)
    head = sample_head(rng, bone_range=(0.0, 0.08)); dev = common.make_devices()["bedside"]
    rows = []
    for j in range(4):
        so2 = rng.uniform(0.40, 0.90); Tb = rng.uniform(32.5, 38.5)
        scen = scenario_static(rng, so2, Tb, dt=10.0, minutes=3.0 if args.quick else 12.0, head=head)
        res = common.run_sequence(fl, head, dev, scen, rng, ablations=False)
        last = slice(-20, None)
        for m, e in res["so2"].items():
            rows.append(dict(seed=seed, state=j, quantity="sO2", method=m, truth=so2 * 100, est=np.nanmean(e[last]) * 100))
        for m, e in res["T"].items():
            rows.append(dict(seed=seed, state=j, quantity="T", method=m, truth=Tb, est=np.nanmean(e[last]),
                             truth_rel=Tb - scen.T_core[0] - 0.4, est_rel=np.nanmean(e[last]) - (scen.T_core[0] + 0.4)))
        rows.append(dict(seed=seed, state=j, quantity="Tgrad", method="Proposed EKF", truth=Tb - scen.T_s[-1],
                         est=np.nanmean(res["T"]["Proposed EKF"][last] - res["Ts_est"][last])))
    return rows


def job_E4(arg):
    seed, scen_name, dev_name = arg
    fl = get_fl(); rng = np.random.default_rng(seed + 1000)
    head = sample_head(rng, bone_range=(0.0, 0.08))
    frame = 10.0 if scen_name == "S1" else 2.0
    dev = common.make_devices(frame_s=frame)[dev_name]
    if scen_name == "S1":
        dev.frame_s = 20.0; scen = scenario_hypothermia(rng, dt=20.0, hours=HOURS_S1, head=head)
    else:
        scen = scenario_intermittent_hypoxaemia(rng, dt=2.0, minutes=MIN_S2, head=head)
    t = time.time()
    res = common.run_sequence(fl, head, dev, scen, rng, ablations=(dev_name == "bedside"))
    rows = summarise(res, f"{scen_name}-{dev_name}")
    for r in rows:
        r.update(seed=seed, device=dev_name, snr=res["snr"], runtime_s=time.time() - t, bone=head.bone)
    trace = None
    if seed == SEEDS[0]:
        trace = dict(t=res["t"], truth_so2=res["truth"]["so2"], truth_Tb=res["truth"]["T_b"], truth_Ts=res["truth"]["T_s"],
                     truth_Tcore=res["truth"]["T_core"], truth_g=res["truth"]["g"], sd_so2=res["sd"]["so2"], sd_T=res["sd"]["T"],
                     Ts_est=res["Ts_est"], g_est=res["g_est"], events=np.array(res["events"]),
                     **{f"so2_{m}": v for m, v in res["so2"].items()}, **{f"T_{m}": v for m, v in res["T"].items()})
    return rows, trace


E5_SETTINGS = [("bone", b) for b in (0.0, 0.05, 0.1, 0.15, 0.2, 0.3)] + [("noise_scale", s) for s in (0.25, 4.0, 16.0)] + \
              [("kg_bias", s) for s in (0.7, 1.3)] + [("kc_bias", s) for s in (0.7, 1.3)] + [("fill", f) for f in (0.3, 0.7)]


def job_E5(arg):
    seed, (name, val) = arg
    fl = get_fl(); rng = np.random.default_rng(seed + 2000)
    head = sample_head(rng, bone_range=(0.0, 0.05))
    dev = common.make_devices(frame_s=20.0)["bedside"]
    if name == "bone":
        head.bone = val
    elif name == "noise_scale":
        dev.n_avg_scale = 1.0 / val                   # noise std x sqrt(val)
    elif name == "kg_bias":
        head.kg = head.kg / (head.kg / np.array([ac.KG_DEFAULT[n] for n in ac.LAYER_ORDER])) * val   # true kG = nominal x val
    elif name == "kc_bias":
        head.kc = np.array([ac.ACOUSTIC_DEFAULTS[n][1] for n in ac.LAYER_ORDER]) * val
    elif name == "fill":
        head.fill = val
    scen = scenario_hypothermia(rng, dt=20.0, hours=HOURS_E5, head=head)
    res = common.run_sequence(fl, head, dev, scen, rng, ablations=False)
    rows = summarise(res, "S1-E5")
    for r in rows:
        r.update(seed=seed, setting=name, value=val, snr=res["snr"])
    return rows


if __name__ == "__main__":
    only = args.only.split(",")
    t0 = time.time()
    with Pool(args.nproc) as pool:
        if "E3" in only:
            rows = sum(pool.map(job_E3, SEEDS), [])
            E3 = pd.DataFrame(rows); E3.to_csv(os.path.join(RES, "E3_static_accuracy_per_state.csv"), index=False)
            summ = []
            for (q, m), gdf in E3.groupby(["quantity", "method"]):
                d = gdf.est - gdf.truth
                summ.append(dict(quantity=q, method=m, n=len(gdf), bias=d.mean(), sd=d.std(), rmse=np.sqrt((d ** 2).mean()),
                                 loa_lo=d.mean() - 1.96 * d.std(), loa_hi=d.mean() + 1.96 * d.std(),
                                 r2=np.corrcoef(gdf.est, gdf.truth)[0, 1] ** 2 if gdf.truth.std() > 0 else np.nan))
                if q == "T" and "est_rel" in gdf:
                    dr = gdf.est_rel - gdf.truth_rel
                    summ[-1].update(rmse_rel=np.sqrt((dr ** 2).mean()))
            pd.DataFrame(summ).to_csv(os.path.join(RES, "E3_static_accuracy_summary.csv"), index=False)
            print("E3 done", time.time() - t0)
        if "E4" in only:
            jobs = [(s, sc, d) for s in SEEDS for sc in ("S1", "S2") for d in ("bedside", "wearable")]
            out = pool.map(job_E4, jobs)
            rows = sum([o[0] for o in out], [])
            E4 = pd.DataFrame(rows); E4.to_csv(os.path.join(RES, "E4_dynamic_per_seed.csv"), index=False)
            for (job, o) in zip(jobs, out):
                if o[1] is not None:
                    np.savez_compressed(os.path.join(RES, f"E4_trace_{job[1]}_{job[2]}_seed{job[0]}.npz"), **o[1])
            # summary and Wilcoxon vs proposed
            num = [c for c in E4.columns if E4[c].dtype.kind == "f" and c not in ("seed", "snr", "runtime_s", "bone")]
            summ = E4.groupby(["scenario", "quantity", "method"])[num].agg(["mean", "std"])
            summ.columns = [f"{a}_{b}" for a, b in summ.columns]
            summ.reset_index().to_csv(os.path.join(RES, "E4_dynamic_summary.csv"), index=False)
            wil = []
            for (sc, q), gdf in E4.groupby(["scenario", "quantity"]):
                prop = gdf[gdf.method == "Proposed EKF"].sort_values("seed")
                for m in gdf.method.unique():
                    if m == "Proposed EKF":
                        continue
                    other = gdf[gdf.method == m].sort_values("seed")
                    if len(other) == len(prop):
                        wil.append(dict(scenario=sc, quantity=q, baseline=m, metric="rmse",
                                        p=M.wilcoxon(prop.rmse.values, other.rmse.values),
                                        proposed_mean=prop.rmse.mean(), baseline_mean=other.rmse.mean()))
            pd.DataFrame(wil).to_csv(os.path.join(RES, "E4_wilcoxon.csv"), index=False)
            print("E4 done", time.time() - t0)
        if "E5" in only:
            jobs = [(s, st) for st in E5_SETTINGS for s in SEEDS_E5]
            rows = sum(pool.map(job_E5, jobs), [])
            E5 = pd.DataFrame(rows); E5.to_csv(os.path.join(RES, "E5_sensitivity_per_seed.csv"), index=False)
            summ = E5.groupby(["setting", "value", "quantity", "method"])[["rmse", "bias", "rmse_rel"] if "rmse_rel" in E5 else ["rmse", "bias"]].agg(["mean", "std"])
            summ.columns = [f"{a}_{b}" for a, b in summ.columns]
            summ.reset_index().to_csv(os.path.join(RES, "E5_sensitivity_summary.csv"), index=False)
            print("E5 done", time.time() - t0)
    json.dump(dict(seeds=SEEDS, seeds_E5=SEEDS_E5, hours_S1=HOURS_S1, minutes_S2=MIN_S2, hours_E5=HOURS_E5,
                   runtime_s=time.time() - t0, quick=args.quick), open(os.path.join(RES, "run_metadata_dynamic.json"), "w"), indent=2)
