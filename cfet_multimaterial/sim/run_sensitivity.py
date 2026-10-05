"""Brief steps 30-33: material-specific sensitivity studies (all at the platform VDD, 27 C
unless stated). Each point runs the VTC, the inverter transient and the 5-stage RO.
  si/sige : NNSn, NNSp in {2,3,4,5}; SiGe hole-mobility ratio MUP_SiGe/MUP_Si = 1.0 .. 2.0
  tmd     : RCN, RCP in {0.1,0.2,0.5,1,2} kOhm*um grid; DIT 1e11 .. 1e13 cm^-2 eV^-1;
            Si RO extended to VDD 0.3-0.5 V for the iso-frequency energy crossover
  cnt     : DCNT {100,250,400}/um; FMET 0 .. 2 %; RC 50 .. 1000 Ohm*um
  gan     : T = 300 .. 500 K; RTH x{0,0.5,1,2,4}; VTHN/VTHP +-5/10/15 %; Si at the same T
Writes results/sens_<study>.csv.  Run: python3 -m sim.run_sensitivity
"""
import os, csv, json
import numpy as np
from multiprocessing import Pool
from .platforms import PLATFORMS, DEVICES
from .spice import tb_vtc, tb_inv_tran, tb_ro

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(HERE, "results")
CAL = json.load(open(os.path.join(HERE, "data", "calibrated_params.json")))
KEYS = ["study", "platform", "vdd", "temp_c", "x1name", "x1", "x2name", "x2", "VM", "gain", "NML", "NMH", "Pstat",
        "tpHL", "tpLH", "tpd_inv", "E_period", "osc", "fRO", "tpd", "Pavg", "Ecycle", "PDP"]


def point(job):
    study, pl, vdd, temp, x1n, x1, x2n, x2, ov_n, ov_p, cstack = job
    kw = dict(ov_n=ov_n, ov_p=ov_p)
    if cstack is not None:
        kw["cstack"] = cstack
    v = tb_vtc(pl, vdd=vdd, temp_c=temp, **kw)
    d = tb_inv_tran(pl, vdd=vdd, temp_c=temp, **kw)
    T_est = 2 * 5 * d["tpd"] * 1.2 if d["ok"] and np.isfinite(d["tpd"]) and d["tpd"] > 0 else None
    o = tb_ro(pl, N=5, vdd=vdd, temp_c=temp, T_est=T_est, **kw)
    r = dict(study=study, platform=pl, vdd=vdd, temp_c=temp, x1name=x1n, x1=x1, x2name=x2n, x2=x2,
             VM=v.get("VM"), gain=v.get("gain"), NML=v.get("NML"), NMH=v.get("NMH"), Pstat=v.get("Pstat"),
             tpHL=d.get("tpHL"), tpLH=d.get("tpLH"), tpd_inv=d.get("tpd"), E_period=d.get("E_period"),
             osc=o.get("osc"), fRO=o.get("fRO"), tpd=o.get("tpd"), Pavg=o.get("Pavg"), Ecycle=o.get("Ecycle"), PDP=o.get("PDP"))
    print(study, pl, x1n, x1, x2n, x2, "fRO=%.4g" % (o.get("fRO") or 0), flush=True)
    return r


def jobs_si_sige():
    J = []
    for pl in ("si", "sige"):
        vdd = PLATFORMS[pl]["vdd"]
        for nn in (2, 3, 4, 5):
            for np_ in (2, 3, 4, 5):
                J.append(("nns", pl, vdd, 27.0, "NNSn", nn, "NNSp", np_, {"NNS": nn}, {"NNS": np_}, None))
    mu_si_p = CAL["gaa_p"]["MU0"]
    for ratio in (1.0, 1.25, 1.5, 1.75, 2.0):
        J.append(("mup_ratio", "sige", PLATFORMS["sige"]["vdd"], 27.0, "MUP_ratio", ratio, "", 0, {}, {"MU0": mu_si_p * ratio}, None))
    return J


def jobs_tmd():
    J = []
    vdd = PLATFORMS["tmd"]["vdd"]
    for rcn in (0.1, 0.2, 0.5, 1.0, 2.0):
        for rcp in (0.1, 0.2, 0.5, 1.0, 2.0):
            J.append(("tmd_rc", "tmd", vdd, 27.0, "RCN_kohm_um", rcn, "RCP_kohm_um", rcp,
                      {"RSW": rcn * 1e-3, "RDW": rcn * 1e-3, "RC": rcn * 1e-3}, {"RSW": rcp * 1e-3, "RDW": rcp * 1e-3, "RC": rcp * 1e-3}, None))
    for dit in (1e11, 3e11, 1e12, 3e12, 1e13):   # cm^-2 eV^-1 -> m^-2 eV^-1 (x1e4)
        J.append(("tmd_dit", "tmd", vdd, 27.0, "DIT_cm2eV", dit, "", 0, {"DIT": dit * 1e4}, {"DIT": dit * 1e4}, None))
    for v in (0.3, 0.35, 0.4, 0.45, 0.5):        # Si at low VDD for the iso-frequency crossover
        J.append(("si_lowvdd", "si", v, 27.0, "VDD", v, "", 0, {}, {}, None))
    return J


def jobs_cnt():
    J = []
    vdd = PLATFORMS["cnt"]["vdd"]
    for dc in (100e6, 250e6, 400e6):
        J.append(("cnt_density", "cnt", vdd, 27.0, "DCNT_per_um", dc * 1e-6, "", 0, {"DCNT": dc}, {"DCNT": dc}, None))
    for fm in (0.0, 1e-4, 1e-3, 5e-3, 1e-2, 2e-2):
        J.append(("cnt_fmet", "cnt", vdd, 27.0, "FMET", fm, "", 0, {"FMET": fm}, {"FMET": fm}, None))
    for rc in (50, 100, 200, 500, 1000):
        J.append(("cnt_rc", "cnt", vdd, 27.0, "RC_ohm_um", rc, "", 0, {"RSW": rc * 1e-6, "RDW": rc * 1e-6}, {"RSW": rc * 1e-6, "RDW": rc * 1e-6}, None))
    return J


def jobs_gan():
    J = []
    vdd = PLATFORMS["gan"]["vdd"]
    for T in (300, 350, 400, 450, 500):
        J.append(("gan_temp", "gan", vdd, T - 273.15, "T_K", T, "", 0, {}, {}, None))
        J.append(("si_temp", "si", PLATFORMS["si"]["vdd"], T - 273.15, "T_K", T, "", 0, {}, {}, None))
    rn, rp = DEVICES["gan_n"]["params"]["RTH"], DEVICES["gan_p"]["params"]["RTH"]
    for k in (0.0, 0.5, 1.0, 2.0, 4.0):
        for T in (300, 400, 500):
            J.append(("gan_rth", "gan", vdd, T - 273.15, "RTH_scale", k, "T_K", T, {"RTH": rn * k}, {"RTH": rp * k}, None))
    vn, vp = CAL["gan_n"]["VTH0"], CAL["gan_p"]["VTH0"]
    for s in (-0.15, -0.10, -0.05, 0.0, 0.05, 0.10, 0.15):
        J.append(("gan_vth", "gan", vdd, 27.0, "dVTH_frac_n", s, "dVTH_frac_p", s, {"VTH0": vn * (1 + s)}, {"VTH0": vp * (1 + s)}, None))
        J.append(("gan_vth_skew", "gan", vdd, 27.0, "dVTH_frac_n", s, "dVTH_frac_p", -s, {"VTH0": vn * (1 + s)}, {"VTH0": vp * (1 - s)}, None))
    return J


def main(studies=None):
    allj = dict(si_sige=jobs_si_sige, tmd=jobs_tmd, cnt=jobs_cnt, gan=jobs_gan)
    for name, fn in allj.items():
        if studies and name not in studies:
            continue
        J = fn()
        with Pool(os.cpu_count()) as p:
            rows = p.map(point, J, chunksize=1)
        with open(os.path.join(RES, f"sens_{name}.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=KEYS); w.writeheader(); w.writerows(rows)
        print("wrote results/sens_%s.csv (%d points)" % (name, len(rows)), flush=True)


if __name__ == "__main__":
    import sys
    main(sys.argv[1:] or None)
