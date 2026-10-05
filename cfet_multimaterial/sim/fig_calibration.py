"""Figures 2-4: Id-Vg calibration (log+lin), Id-Vd families, MAPE/FoM comparison."""
import os, json, csv
import numpy as np
import matplotlib.pyplot as plt
from .plotstyle import save, panel_label, DEVICE_LABEL, COL2, COL1
from .platforms import DEVICES, eff_width
from .ucm import id_terminal
from .calibrate import load_ref
from .make_reference_data import ANCHORS, VDS_LIN

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cal = json.load(open(os.path.join(HERE, "data", "calibrated_params.json")))
ORDER = ["gaa_n", "gaa_p", "sige_p", "mos2_n", "wse2_p", "cnt_n", "cnt_p", "gan_n", "gan_p"]
REF_C, MOD_C = "#898781", "#0072B2"


def fig_idvg():
    fig, axes = plt.subplots(3, 3, figsize=(COL2, 6.2))
    for ax, name, lab in zip(axes.flat, ORDER, "abcdefghi"):
        dev = DEVICES[name]; s = 1 if dev["polarity"] == "n" else -1; vdd = ANCHORS[name]["vdd"]
        vg, il, isat, *_ = load_ref(name); wum = eff_width(dev["params"]) * 1e6
        ml = s * id_terminal(s * vg, s * VDS_LIN, 0, name, params=cal[name]) / wum
        ms = s * id_terminal(s * vg, s * vdd, 0, name, params=cal[name]) / wum
        ax.semilogy(vg[::6], isat[::6] / wum, "o", mfc="none", color=REF_C, ms=3, label="reference (sat.)")
        ax.semilogy(vg[::6], il[::6] / wum, "s", mfc="none", color=REF_C, ms=3, label="reference (lin.)")
        ax.semilogy(vg, ms, "-", color=MOD_C, label=f"UCM, $V_{{DS}}$={vdd} V")
        ax.semilogy(vg, ml, "--", color=MOD_C, label=f"UCM, $V_{{DS}}$={VDS_LIN} V")
        ax2 = ax.twinx(); ax2.grid(False)
        ax2.plot(vg, ms * 1e3, "-", color="#D55E00", lw=1.0); ax2.plot(vg[::6], isat[::6] / wum * 1e3, "o", mfc="none", color="#D55E00", ms=2.5)
        ax2.set_ylabel("$|I_D|$ (mA/µm), linear", color="#D55E00", fontsize=7); ax2.tick_params(axis="y", colors="#D55E00", labelsize=6.5)
        ax2.set_ylim(0, None)
        ax.set_ylim(1e-11, 1e-2); ax.set_xlim(0, vdd)
        ax.set_xlabel("$|V_{GS}|$ (V)"); ax.set_ylabel("$|I_D|$ (A/µm), log")
        panel_label(ax, f"({lab}) {DEVICE_LABEL[name]}", 0.04, 0.96)
        if name == "gaa_n":
            ax.legend(loc="lower right", fontsize=5.5)
    fig.tight_layout(h_pad=0.6, w_pad=0.8)
    save(fig, "fig02_calibration_idvg")


def fig_idvd():
    fig, axes = plt.subplots(3, 3, figsize=(COL2, 5.8))
    for ax, name, lab in zip(axes.flat, ORDER, "abcdefghi"):
        dev = DEVICES[name]; s = 1 if dev["polarity"] == "n" else -1
        vg, il, isat, vd, fam, vgl = load_ref(name); wum = eff_width(dev["params"]) * 1e6
        for j, v in enumerate(vgl):
            m = s * id_terminal(s * v, s * vd, 0, name, params=cal[name]) / wum * 1e3
            ax.plot(vd[::5], fam[::5, j] / wum * 1e3, "o", mfc="none", color=REF_C, ms=2.5)
            ax.plot(vd, m, "-", color=plt.cm.viridis(j / 5.5), lw=1.1, label=f"{v:.2f} V")
        ax.set_xlabel("$|V_{DS}|$ (V)"); ax.set_ylabel("$|I_D|$ (mA/µm)"); ax.set_xlim(0, vd[-1]); ax.set_ylim(0, None)
        panel_label(ax, f"({lab}) {DEVICE_LABEL[name]}", 0.04, 0.96)
        ax.legend(title="$|V_{GS}|$", fontsize=5.5, title_fontsize=6, loc="center right", ncol=1)
    fig.tight_layout(h_pad=0.6, w_pad=0.8)
    save(fig, "fig03_calibration_idvd")


def fig_mape():
    rows = list(csv.DictReader(open(os.path.join(HERE, "results", "calibration_mape.csv"))))
    rows = {r["device"]: r for r in rows}
    x = np.arange(len(ORDER)); w = 0.26
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(COL2, 2.4), gridspec_kw=dict(width_ratios=[1.1, 1]))
    for k, (key, lab, c) in enumerate([("mape_idvg_lin", "$I_D$–$V_G$ linear", "#0072B2"),
                                        ("mape_idvg_sat", "$I_D$–$V_G$ saturation", "#56B4E9"),
                                        ("mape_idvd", "$I_D$–$V_D$ family", "#D55E00")]):
        v = [float(rows[d][key]) for d in ORDER]
        ax.bar(x + (k - 1) * w, v, w * 0.92, color=c, label=lab)
    ax.set_xticks(x); ax.set_xticklabels([DEVICE_LABEL[d] for d in ORDER], rotation=40, ha="right", fontsize=6.5)
    ax.set_ylabel("MAPE (%)"); ax.legend(fontsize=6, loc="upper left"); ax.set_ylim(0, 20); ax.grid(axis="x", visible=False)
    panel_label(ax, "(a)", 0.9, 0.96)
    # FoM parity: model vs reference for Ion, Ioff, SS, DIBL
    for key, lab, mk in [("Ion_A_per_um", "$I_{ON}$ (A/µm)", "o"), ("Ioff_A_per_um", "$I_{OFF}$ (A/µm)", "s"),
                         ("SS_mV_dec", "SS (mV/dec)", "^"), ("DIBL_mV_V", "DIBL (mV/V)", "D")]:
        r = np.array([float(rows[d]["ref_" + key]) for d in ORDER]); m = np.array([float(rows[d]["model_" + key]) for d in ORDER])
        bx.loglog(r, m, mk, mfc="none", ms=4, label=lab)
    lim = [1e-10, 1e3]; bx.plot(lim, lim, "-", color="#c3c2b7", lw=0.8); bx.plot(lim, [l * 1.2 for l in lim], ":", color="#c3c2b7", lw=0.7); bx.plot(lim, [l / 1.2 for l in lim], ":", color="#c3c2b7", lw=0.7)
    bx.set_xlim(lim); bx.set_ylim(lim); bx.set_xlabel("reference FoM"); bx.set_ylabel("calibrated model FoM"); bx.legend(fontsize=6, loc="upper left")
    panel_label(bx, "(b)", 0.9, 0.12)
    fig.tight_layout(w_pad=1.0)
    save(fig, "fig04_calibration_mape")


if __name__ == "__main__":
    fig_idvg(); fig_idvd(); fig_mape()
