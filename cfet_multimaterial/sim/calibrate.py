"""Step 13 of the flow: calibrate every device model against its reference I-V data.

Fits VTH0, MU0 (or TTR for CNT), VSAT (or ALPHA for CNT), RSW=RDW, LAMBDA, ETA and N0 by
non-linear least squares on log10(ID) of the Id-Vg curves (linear + saturation) and on the
relative error of the Id-Vd family, then reports MAPE per device and writes
data/calibrated_params.json (consumed by the Verilog-A and ngspice emitters).

Run: python3 -m sim.calibrate
"""
from __future__ import annotations
import os, csv, json
import numpy as np
from scipy.optimize import least_squares
from .platforms import DEVICES, eff_width, TRANSPORT_LANDAUER
from .ucm import id_terminal, mape, fom
from .make_reference_data import ANCHORS, VDS_LIN

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLOOR = 1e-13  # [A] ignore reference points below this in MAPE/fit (noise floor of real data)


def load_ref(name):
    a = np.genfromtxt(os.path.join(HERE, "data", f"{name}_idvg_ref.csv"), delimiter=",", skip_header=1)
    b = np.genfromtxt(os.path.join(HERE, "data", f"{name}_idvd_ref.csv"), delimiter=",", skip_header=1)
    with open(os.path.join(HERE, "data", f"{name}_idvd_ref.csv")) as f:
        hdr = next(csv.reader(f))
    vgl = [float(h.split("=")[1].rstrip(")")) for h in hdr[1:]]
    return a[:, 0], a[:, 1], a[:, 2], b[:, 0], b[:, 1:], vgl


def fit_vector(name):
    """Free parameters and bounds. Contact resistance of the 2D and CNT devices is a
    *measured* quantity in practice (TLM) and is the subject of the sensitivity study, so it
    is held at its physical nominal value (RSW = RDW = RC) instead of being fitted."""
    dev = DEVICES[name]; p = dev["params"]
    if dev["transport"] == TRANSPORT_LANDAUER:
        keys = ["VTH0", "TTR", "ALPHA", "LAMBDA", "ETA", "N0"]
        lo = [0.0, 0.05, 0.5, 0.0, 0.0, 1.0]; hi = [0.8, 1.0, 1.0, 0.3, 0.2, 1.8]
    elif dev["platform_tag"] == "TMD":
        keys = ["VTH0", "MU0", "VSAT", "LAMBDA", "ETA", "N0"]
        lo = [0.0, p["MU0"] * 0.2, p["VSAT"] * 0.3, 0.0, 0.0, 1.0]
        hi = [0.9, p["MU0"] * 3.0, p["VSAT"] * 3.0, 0.3, 0.2, 1.8]
    else:
        keys = ["VTH0", "MU0", "VSAT", "RSW", "LAMBDA", "ETA", "N0"]
        lo = [0.0, p["MU0"] * 0.2, p["VSAT"] * 0.3, p["RSW"] * 0.6, 0.0, 0.0, 1.0]
        hi = [0.9, p["MU0"] * 5.0, p["VSAT"] * 2.5, p["RSW"] * 1.6, 0.3, 0.2, 1.8]
    x0 = [p[k] for k in keys]
    # start N0 from the reference subthreshold slope to avoid a local minimum
    from .make_reference_data import ANCHORS as _A
    x0[-1] = min(1.75, max(1.0, _A[name]["ss"] / 59.6 / (1.0 + 1.602176634e-19 * p["DIT"] / p["COX"])))
    scale = np.array([abs(v) if v else 1.0 for v in x0])
    return keys, np.array(x0) / scale, np.array(lo) / scale, np.array(hi) / scale, scale


def calibrate(name, verbose=True):
    dev = DEVICES[name]; s = 1 if dev["polarity"] == "n" else -1
    vg, il_ref, is_ref, vd, idvd_ref, vgl = load_ref(name)
    vdd = ANCHORS[name]["vdd"]
    keys, x0, lo, hi, scale = fit_vector(name)
    if name.startswith("cnt"):
        base = {"FMET": 1e-6}   # 99.9999 % semiconducting purity (nominal)
    else:
        base = {}
    sel_l = il_ref > FLOOR; sel_s = is_ref > FLOOR

    def model(x):
        o = dict(base); o.update({k: float(v) for k, v in zip(keys, x * scale)})
        if "RSW" in o: o["RDW"] = o["RSW"]
        il = s * id_terminal(s * vg, s * VDS_LIN, 0.0, name, params=o)
        isat = s * id_terminal(s * vg, s * vdd, 0.0, name, params=o)
        fam = np.column_stack([s * id_terminal(s * v, s * vd, 0.0, name, params=o) for v in vgl])
        return o, il, isat, fam

    def resid(x):
        o, il, isat, fam = model(x)
        r1 = np.log10(np.maximum(il[sel_l], 1e-30) / il_ref[sel_l])
        r2 = np.log10(np.maximum(isat[sel_s], 1e-30) / is_ref[sel_s])
        m = idvd_ref > FLOOR
        r3 = ((fam - idvd_ref) / np.maximum(idvd_ref, FLOOR))[m]
        return np.concatenate([2.0 * r1, 2.0 * r2, 0.5 * r3])

    res = least_squares(resid, x0, bounds=(lo, hi), xtol=1e-10, ftol=1e-10, max_nfev=400)
    o, il, isat, fam = model(res.x)
    m = idvd_ref > FLOOR
    out = dict(params=o,
               mape_idvg_lin=mape(il[sel_l], il_ref[sel_l]), mape_idvg_sat=mape(isat[sel_s], is_ref[sel_s]),
               mape_idvd=100 * np.mean(np.abs((fam - idvd_ref)[m] / idvd_ref[m])),
               rmse_log_idvg=float(np.sqrt(np.mean(np.log10(np.maximum(isat[sel_s], 1e-30) / is_ref[sel_s]) ** 2))))
    out["fom"] = fom(vg, il, isat, vdd, VDS_LIN, vdd, eff_width(dev["params"]))
    out["fom_ref"] = fom(vg, il_ref, is_ref, vdd, VDS_LIN, vdd, eff_width(dev["params"]))
    if verbose:
        f = out["fom"]
        print(f"{name:7s} MAPE lin={out['mape_idvg_lin']:5.2f}% sat={out['mape_idvg_sat']:5.2f}% IdVd={out['mape_idvd']:5.2f}% | "
              f"Ion={f['Ion_A_per_um']*1e3:.3f} mA/um Ioff={f['Ioff_A_per_um']*1e9:.3f} nA/um SS={f['SS_mV_dec']:.1f} DIBL={f['DIBL_mV_V']:.1f} | "
              + " ".join(f"{k}={o[k]:.4g}" for k in keys))
    return out


def main():
    cal, rows = {}, []
    for name in DEVICES:
        r = calibrate(name)
        cal[name] = r["params"]
        rows.append(dict(device=name, **{k: r[k] for k in ["mape_idvg_lin", "mape_idvg_sat", "mape_idvd", "rmse_log_idvg"]},
                         **{"model_" + k: v for k, v in r["fom"].items()}, **{"ref_" + k: v for k, v in r["fom_ref"].items()}))
    json.dump(cal, open(os.path.join(HERE, "data", "calibrated_params.json"), "w"), indent=1)
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    with open(os.path.join(HERE, "results", "calibration_mape.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print("wrote data/calibrated_params.json and results/calibration_mape.csv")


if __name__ == "__main__":
    main()
