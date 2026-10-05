"""Brief steps 34-37: Monte Carlo on the calibrated models.
  * N_RO samples per platform: 5-stage RO (fRO, Pavg, Ecycle, PDP) + inverter tpd
  * N_INV samples per platform: inverter VTC (VM, gain, NML, NMH) for functional yield
Random variables (per platform, n and p devices drawn independently unless stated):
  si   : VTH0 ~ N(0, 20 mV) [includes work-function shift], WNS ~ N(0, 1 nm), RSW=RDW ~ N(0, 10 %)
  sige : si + MU0 (SiGe p) ~ N(0, 10 %) [composition proxy]
  tmd  : RC(=RSW=RDW) ~ logN(0.3 dec eq. 30 %), VTH0 ~ N(0, 50 mV), MU0 ~ N(0, 20 %), DIT ~ logN(0.3 dec)
  cnt  : DCNT ~ N(0, 15 %), FMET ~ logN(median 1e-6, 0.5 dec), RSW=RDW ~ N(0, 30 %)
  gan  : VTH0 ~ N(0, 50 mV) [incl. trap shift], MU0 ~ N(0, 10 %), RTH ~ N(0, 20 %)
Yield: Y_f = N(fRO >= 0.9 fRO,nominal)/N ; functional yield = NML > 0.1 VDD & NMH > 0.1 VDD & Av > 10.
Run: python3 -m sim.run_montecarlo [N_RO N_INV]
"""
import os, csv, json, sys
import numpy as np
from multiprocessing import Pool
from .platforms import PLATFORMS, DEVICES, PLATFORM_ORDER
from .spice import tb_vtc, tb_inv_tran, tb_ro

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(HERE, "results")
CAL = json.load(open(os.path.join(HERE, "data", "calibrated_params.json")))


def sample(pl, rng):
    """One random draw of (ov_n, ov_p) for platform pl."""
    n, p = PLATFORMS[pl]["n"], PLATFORMS[pl]["p"]
    cn, cp = dict(DEVICES[n]["params"], **CAL[n]), dict(DEVICES[p]["params"], **CAL[p])
    on, op = {}, {}
    if pl in ("si", "sige"):
        for o, c in ((on, cn), (op, cp)):
            o["VTH0"] = c["VTH0"] + rng.normal(0, 0.020)
            o["WNS"] = c["WNS"] + rng.normal(0, 1e-9)
            r = c["RSW"] * (1 + rng.normal(0, 0.10)); o["RSW"] = o["RDW"] = max(r, 1e-6)
        if pl == "sige":
            op["MU0"] = cp["MU0"] * max(1 + rng.normal(0, 0.10), 0.3)
    elif pl == "tmd":
        for o, c in ((on, cn), (op, cp)):
            rc = c["RSW"] * 10 ** rng.normal(0, 0.3 * 0.434 * 1.0)   # ~30 % lognormal
            o["RSW"] = o["RDW"] = o["RC"] = rc
            o["VTH0"] = c["VTH0"] + rng.normal(0, 0.050)
            o["MU0"] = c["MU0"] * max(1 + rng.normal(0, 0.20), 0.3)
            o["DIT"] = c["DIT"] * 10 ** rng.normal(0, 0.3)
    elif pl == "cnt":
        for o, c in ((on, cn), (op, cp)):
            o["DCNT"] = c["DCNT"] * max(1 + rng.normal(0, 0.15), 0.3)
            o["FMET"] = 1e-6 * 10 ** rng.normal(0, 0.5)
            r = c["RSW"] * max(1 + rng.normal(0, 0.30), 0.2); o["RSW"] = o["RDW"] = r
    elif pl == "gan":
        for o, c in ((on, cn), (op, cp)):
            o["VTH0"] = c["VTH0"] + rng.normal(0, 0.050)
            o["MU0"] = c["MU0"] * max(1 + rng.normal(0, 0.10), 0.3)
            o["RTH"] = c["RTH"] * max(1 + rng.normal(0, 0.20), 0.2)
    return on, op


def ro_sample(job):
    pl, k, T_est, on, op = job
    d = tb_inv_tran(pl, ov_n=on, ov_p=op)
    o = tb_ro(pl, N=5, T_est=(2 * 5 * d["tpd"] * 1.2 if d["ok"] and np.isfinite(d["tpd"]) and d["tpd"] > 0 else T_est),
              cycles=(6, 16), ov_n=on, ov_p=op)
    r = dict(platform=pl, sample=k, tpd_inv=d.get("tpd"), E_period=d.get("E_period"), osc=o.get("osc"), fRO=o.get("fRO"),
             tpd=o.get("tpd"), Pavg=o.get("Pavg"), Ecycle=o.get("Ecycle"), PDP=o.get("PDP"))
    r.update({"n_" + a: b for a, b in on.items()}); r.update({"p_" + a: b for a, b in op.items()})
    if k % 20 == 0:
        print(pl, k, "fRO=%.4g" % (o.get("fRO") or 0), flush=True)
    return r


def inv_sample(job):
    pl, k, on, op = job
    v = tb_vtc(pl, npts=201, ov_n=on, ov_p=op)
    r = dict(platform=pl, sample=k, VM=v.get("VM"), gain=v.get("gain"), NML=v.get("NML"), NMH=v.get("NMH"), Pstat=v.get("Pstat"))
    r.update({"n_" + a: b for a, b in on.items()}); r.update({"p_" + a: b for a, b in op.items()})
    return r


def write(rows, name):
    keys = []
    for r in rows:
        for k in r:
            if k not in keys: keys.append(k)
    with open(os.path.join(RES, name), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)


def main(n_ro=200, n_inv=1000, seed=2026):
    nom = {r["platform"]: r for r in csv.DictReader(open(os.path.join(RES, "nominal_ro.csv"))) if r["N"] == "5"}
    rng = np.random.default_rng(seed)
    jobs_ro, jobs_inv = [], []
    for pl in PLATFORM_ORDER:
        T_est = float(nom[pl]["period"])
        for k in range(n_ro):
            on, op = sample(pl, rng); jobs_ro.append((pl, k, T_est, on, op))
        for k in range(n_inv):
            on, op = sample(pl, rng); jobs_inv.append((pl, k, on, op))
    with Pool(os.cpu_count()) as p:
        rows = p.map(inv_sample, jobs_inv, chunksize=4)
    write(rows, "mc_inverter.csv"); print("wrote results/mc_inverter.csv", flush=True)
    with Pool(os.cpu_count()) as p:
        rows = p.map(ro_sample, jobs_ro, chunksize=1)
    write(rows, "mc_ro.csv"); print("wrote results/mc_ro.csv", flush=True)
    # yield summary
    summ = []
    inv = [r for r in csv.DictReader(open(os.path.join(RES, "mc_inverter.csv")))]
    for pl in PLATFORM_ORDER:
        vdd = PLATFORMS[pl]["vdd"]; f0 = float(nom[pl]["fRO"])
        rr = [r for r in rows if r["platform"] == pl]
        f = np.array([float(r["fRO"] or 0) for r in rr]); e = np.array([float(r["Ecycle"] or np.nan) for r in rr])
        ii = [r for r in inv if r["platform"] == pl]
        nml = np.array([float(r["NML"] or np.nan) for r in ii]); nmh = np.array([float(r["NMH"] or np.nan) for r in ii]); g = np.array([float(r["gain"] or np.nan) for r in ii])
        summ.append(dict(platform=pl, N_ro=len(rr), f_nom_GHz=f0 * 1e-9, f_mean_GHz=f[f > 0].mean() * 1e-9, f_std_GHz=f[f > 0].std() * 1e-9,
                         f_sigma_over_mu_pct=100 * f[f > 0].std() / f[f > 0].mean(), osc_fraction=(f > 0).mean(),
                         Y_f_pct=100 * (f >= 0.9 * f0).mean(), E_mean_fJ=np.nanmean(e) * 1e15, E_std_fJ=np.nanstd(e) * 1e15,
                         N_inv=len(ii), Y_func_pct=100 * np.mean((nml > 0.1 * vdd) & (nmh > 0.1 * vdd) & (g > 10)),
                         NML_min_over_VDD=np.nanmin(nml) / vdd, NMH_min_over_VDD=np.nanmin(nmh) / vdd, gain_min=np.nanmin(g)))
    write(summ, "mc_yield_summary.csv"); print("wrote results/mc_yield_summary.csv")


if __name__ == "__main__":
    a = [int(x) for x in sys.argv[1:]]
    main(*a)
