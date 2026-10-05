"""Nominal circuit validation (brief steps 17-26): VTC, inverter transient and 5/7/9-stage
ROs for all five platforms. Writes results/nominal_inverter.csv, results/nominal_ro.csv,
results/waveforms_<pl>.npz and figures 5-7.  Run: python3 -m sim.run_nominal
"""
import os, csv, json
import numpy as np
from multiprocessing import Pool
from .platforms import PLATFORMS, PLATFORM_ORDER
from .spice import tb_vtc, tb_inv_tran, tb_ro

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(HERE, "results")
KEYS_INV = ["vdd", "VM", "gain", "VIL", "VIH", "VOL", "VOH", "NML", "NMH", "Istat_low", "Istat_high", "Pstat",
            "tpHL", "tpLH", "tpd", "E_period", "E_HL", "E_LH", "Pavg"]
KEYS_RO = ["N", "vdd", "osc", "fRO", "fRO_cycle10_11", "period", "tpd", "Pavg", "Ecycle", "PDP", "Vswing"]


def one(pl):
    v = tb_vtc(pl); d = tb_inv_tran(pl)
    inv = dict(platform=pl)
    for src in (v, d):
        inv.update({k: src[k] for k in KEYS_INV if k in src})
    ros, wave = [], dict(vin=v["vin"], vout=v["vout"], idd_dc=v["idd"], t_inv=d["t"], vin_inv=d["vin"], vout_inv=d["vout"], idd_inv=d["idd"])
    T_est = 2 * 5 * d["tpd"] * 1.2
    for N in (5, 7, 9):
        o = tb_ro(pl, N=N, T_est=T_est * N / 5)
        ros.append(dict(platform=pl, **{k: o.get(k, np.nan) for k in KEYS_RO}))
        if o.get("osc"):
            wave[f"t_ro{N}"] = o["t"]; wave[f"v_ro{N}"] = o["v"]; wave[f"idd_ro{N}"] = o["idd"]; wave[f"tcross_ro{N}"] = o["tcross"]
        print(pl, N, {k: o.get(k) for k in ["osc", "fRO", "tpd", "Pavg", "Ecycle"]}, flush=True)
    np.savez_compressed(os.path.join(RES, f"waveforms_{pl}.npz"), **wave)
    return inv, ros


def main(platforms=None):
    os.makedirs(RES, exist_ok=True)
    pls = platforms or PLATFORM_ORDER
    with Pool(min(5, os.cpu_count())) as p:
        out = p.map(one, pls)
    invs = [o[0] for o in out]; ros = [r for o in out for r in o[1]]
    if platforms:   # merge into existing tables
        old_i = [r for r in csv.DictReader(open(os.path.join(RES, "nominal_inverter.csv"))) if r["platform"] not in pls]
        old_r = [r for r in csv.DictReader(open(os.path.join(RES, "nominal_ro.csv"))) if r["platform"] not in pls]
        invs = sorted(old_i + invs, key=lambda r: PLATFORM_ORDER.index(r["platform"]))
        ros = sorted(old_r + ros, key=lambda r: (PLATFORM_ORDER.index(r["platform"]), int(r["N"])))
    with open(os.path.join(RES, "nominal_inverter.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["platform"] + KEYS_INV); w.writeheader(); w.writerows(invs)
    with open(os.path.join(RES, "nominal_ro.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["platform"] + KEYS_RO); w.writeheader(); w.writerows(ros)
    print("wrote results/nominal_inverter.csv, results/nominal_ro.csv")


if __name__ == "__main__":
    import sys
    main(sys.argv[1:] or None)
