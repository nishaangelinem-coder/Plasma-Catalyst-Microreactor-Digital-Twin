"""Brief steps 27-29: unified VDD sweeps and temperature sweeps for the five platforms
(RO5 fRO/tpd/Pavg/Ecycle/PDP and inverter VM/gain/NM at each point).
Writes results/vdd_sweep.csv and results/temp_sweep.csv.  Run: python3 -m sim.run_sweeps
"""
import os, csv
import numpy as np
from multiprocessing import Pool
from .platforms import PLATFORMS, PLATFORM_ORDER
from .spice import tb_vtc, tb_inv_tran, tb_ro

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(HERE, "results")
KEYS = ["platform", "vdd", "temp_c", "VM", "gain", "NML", "NMH", "Pstat", "tpd_inv", "E_period", "osc", "fRO", "tpd", "Pavg",
        "Ecycle", "PDP", "Vswing"]


def point(args):
    pl, vdd, temp = args
    v = tb_vtc(pl, vdd=vdd, temp_c=temp)
    d = tb_inv_tran(pl, vdd=vdd, temp_c=temp)
    o = tb_ro(pl, N=5, vdd=vdd, temp_c=temp, T_est=(2 * 5 * d["tpd"] * 1.2 if d["ok"] and np.isfinite(d["tpd"]) else None))
    r = dict(platform=pl, vdd=vdd, temp_c=temp, VM=v.get("VM"), gain=v.get("gain"), NML=v.get("NML"), NMH=v.get("NMH"),
             Pstat=v.get("Pstat"), tpd_inv=d.get("tpd"), E_period=d.get("E_period"), osc=o.get("osc"), fRO=o.get("fRO"),
             tpd=o.get("tpd"), Pavg=o.get("Pavg"), Ecycle=o.get("Ecycle"), PDP=o.get("PDP"), Vswing=o.get("Vswing"))
    print(pl, vdd, temp, "fRO=%.4g" % (o.get("fRO") or 0), flush=True)
    return r


def merge_write(rows, name, pls):
    """Write rows; when a platform subset is re-run, merge into the existing table."""
    path = os.path.join(RES, name)
    if pls and os.path.exists(path):
        old = [r for r in csv.DictReader(open(path)) if r["platform"] not in pls]
        rows = sorted(old + rows, key=lambda r: (PLATFORM_ORDER.index(r["platform"]), float(r["vdd"]), float(r["temp_c"])))
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=KEYS); w.writeheader(); w.writerows(rows)


def main(pls=None):
    jobs = []
    for pl in (pls or PLATFORM_ORDER):
        a, b, s = PLATFORMS[pl]["vdd_sweep"]
        for vdd in np.round(np.arange(a, b + 1e-9, s), 3):
            jobs.append((pl, float(vdd), 27.0))
    with Pool(os.cpu_count()) as p:
        rows = p.map(point, jobs, chunksize=1)
    merge_write(rows, "vdd_sweep.csv", pls)
    jobs = [(pl, PLATFORMS[pl]["vdd"], float(t)) for pl in (pls or PLATFORM_ORDER) for t in PLATFORMS[pl]["temps"]]
    with Pool(os.cpu_count()) as p:
        rows = p.map(point, jobs, chunksize=1)
    merge_write(rows, "temp_sweep.csv", pls)
    print("wrote results/vdd_sweep.csv and results/temp_sweep.csv")


if __name__ == "__main__":
    import sys
    main(sys.argv[1:] or None)
