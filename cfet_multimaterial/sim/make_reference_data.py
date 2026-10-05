"""Generate literature-anchored *reference* I-V curves for compact-model calibration.

IMPORTANT (stated verbatim in the manuscript): no measured or TCAD data were available for
this study, so the calibration targets are *synthetic reference curves* reconstructed from
published figures of merit (Ion, Ioff, SS, DIBL at the platform VDD; see
doc/calibration_targets.md and paper/refs.bib). The reference curves are produced by an
INDEPENDENT device formulation (EKV-style charge-based interpolation with a power-law
(m = 4) Vds_eff smoothing and explicit series resistance) so that fitting the UCM-CFET model to them
is a non-trivial test of the model's functional form. The flow accepts measured/TCAD CSVs with
the same column layout (VGS, ID_lin, ID_sat) as drop-in replacements.
"""
from __future__ import annotations
import os, csv, json
import numpy as np
from scipy.optimize import fsolve
from .platforms import DEVICES, PLATFORMS, eff_width, Q, KB
from .ucm import softplus, smooth_abs, solve_series

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VDS_LIN = 0.05

# anchors: platform VDD, Ion [mA/um], Ioff [nA/um], SS [mV/dec], DIBL [mV/V], source key
ANCHORS = {
    "gaa_n":  dict(vdd=0.7, ion=1.00, ioff=1.0,  ss=68, dibl=40, src="IRDS2023;Loubet2017;Mertens2017"),
    "gaa_p":  dict(vdd=0.7, ion=0.75, ioff=1.0,  ss=70, dibl=45, src="IRDS2023;Loubet2017"),
    "sige_p": dict(vdd=0.7, ion=0.95, ioff=1.5,  ss=72, dibl=50, src="Mertens2016;Mochizuki2020"),
    "mos2_n": dict(vdd=0.5, ion=0.10, ioff=1.0,  ss=72, dibl=55, src="Li2023Nature;Intel2024;OBrien2023"),
    "wse2_p": dict(vdd=0.5, ion=0.07, ioff=1.0,  ss=78, dibl=60, src="Chou2021;OBrien2023"),
    "cnt_n":  dict(vdd=0.6, ion=1.50, ioff=10.0, ss=75, dibl=45, src="Liu2020Science;Hills2019"),
    "cnt_p":  dict(vdd=0.6, ion=1.40, ioff=10.0, ss=75, dibl=45, src="Liu2020Science;Hills2019"),
    "gan_n":  dict(vdd=1.2, ion=0.50, ioff=1.0,  ss=80, dibl=30, src="Amano2018;Chowdhury2020"),
    "gan_p":  dict(vdd=1.2, ion=0.05, ioff=0.1,  ss=85, dibl=30, src="Chowdhury2020;Bader2020"),
}


def ref_current(vgs, vds, k, dev):
    """Independent reference formulation (EKV-type charge interpolation)."""
    p = dev["params"]; W = eff_width(p); vt = KB * 300.15 / Q
    n = k["ss"] * 1e-3 / (vt * np.log(10.0))
    vds = np.asarray(vds, float); vgs = np.asarray(vgs, float)
    vth = k["vth"] - k["dibl"] * 1e-3 * smooth_abs(vds)
    # EKV: Id ~ Ispec [F(eta_s)^2 - F(eta_d)^2], F = softplus, eta = (Vgs-Vth-V)/(2 n vt)
    fs = softplus((vgs - vth) / (2 * n * vt))
    # velocity-saturation limited drain-end potential via power-law smoothing (m = 2)
    vov = 2 * n * vt * fs
    vdsat_r = k["vdsat_frac"] * vov + 3.0 * vt          # saturation voltage floors at ~3 Vt in weak inversion
    vds_eff = vds / np.power(1.0 + np.power(np.abs(vds) / vdsat_r, 4.0), 0.25)
    fd = softplus((vgs - vth - vds_eff) / (2 * n * vt))
    ispec = k["ispec"] * W
    ids = ispec * (fs * fs - fd * fd) * (1.0 + k["lam"] * smooth_abs(vds))
    return ids


def ref_terminal(vg, vd, k, dev):
    p = dev["params"]; W = eff_width(p); rs, rd = p["RSW"] / W, p["RDW"] / W
    return solve_series(lambda a, b: ref_current(a, b, k, dev), vg, vd, rs, rd)


def fit_anchor(name):
    dev = DEVICES[name]; a = ANCHORS[name]; W = eff_width(dev["params"]); wum = W * 1e6
    k = dict(ss=a["ss"], dibl=a["dibl"], vdsat_frac=0.6 if dev["transport"] == "dd" else 1.0,
             lam=dev["params"]["LAMBDA"] * 0.8, vth=0.3, ispec=1e-3)

    def resid(x):
        k["vth"], k["ispec"] = x[0], 10 ** x[1]
        ion = ref_terminal(a["vdd"], a["vdd"], k, dev) / wum
        ioff = ref_terminal(0.0, a["vdd"], k, dev) / wum
        return [np.log10(ion / (a["ion"] * 1e-3)), np.log10(ioff / (a["ioff"] * 1e-9))]
    x = fsolve(resid, [0.3, -3.0], xtol=1e-10)
    k["vth"], k["ispec"] = x[0], 10 ** x[1]
    return k


def main():
    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    meta = {}
    for name, dev in DEVICES.items():
        a = ANCHORS[name]; k = fit_anchor(name)
        vg = np.round(np.arange(0.0, a["vdd"] + 1e-9, 0.005), 4)
        il = ref_terminal(vg, VDS_LIN, k, dev); isat = ref_terminal(vg, a["vdd"], k, dev)
        with open(os.path.join(HERE, "data", f"{name}_idvg_ref.csv"), "w", newline="") as f:
            w = csv.writer(f); w.writerow(["VGS_V", f"ID_lin_A(VDS={VDS_LIN})", f"ID_sat_A(VDS={a['vdd']})"])
            for r in zip(vg, il, isat): w.writerow([f"{r[0]:.4f}", f"{r[1]:.6e}", f"{r[2]:.6e}"])
        vd = np.round(np.arange(0.0, a["vdd"] + 1e-9, 0.01), 4)
        vgl = [round(x, 3) for x in np.linspace(0.3, 1.0, 6) * a["vdd"]]
        with open(os.path.join(HERE, "data", f"{name}_idvd_ref.csv"), "w", newline="") as f:
            w = csv.writer(f); w.writerow(["VDS_V"] + [f"ID_A(VGS={v})" for v in vgl])
            cols = [ref_terminal(v, vd, k, dev) for v in vgl]
            for i_, x in enumerate(vd): w.writerow([f"{x:.4f}"] + [f"{c[i_]:.6e}" for c in cols])
        meta[name] = dict(anchors=a, reference_formulation_params={kk: float(v) for kk, v in k.items()},
                          polarity_note="magnitudes; p-type devices: |VGS|, |VDS|, |ID|")
        print(f"{name}: ref vth={k['vth']:.3f} ispec={k['ispec']:.3e}  Ion={isat[-1]/ (eff_width(dev['params'])*1e6)*1e3:.3f} mA/um Ioff={isat[0]/(eff_width(dev['params'])*1e6)*1e9:.3f} nA/um")
    json.dump(meta, open(os.path.join(HERE, "data", "reference_metadata.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
