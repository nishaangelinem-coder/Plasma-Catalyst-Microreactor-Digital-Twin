"""Figure: gate-capacitance comparison of the nine calibrated models (C_gg = dQ_g/dV_GS at
V_DS = 0 and V_DS = V_DD, per unit effective width) from the charge model."""
import os, json
import numpy as np
import matplotlib.pyplot as plt
from .plotstyle import save, panel_label, DEVICE_LABEL, DEVICE_COLOR, COL2
from .platforms import DEVICES, eff_width
from .ucm import charges
from .make_reference_data import ANCHORS

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cal = json.load(open(os.path.join(HERE, "data", "calibrated_params.json")))
ORDER = ["gaa_n", "gaa_p", "sige_p", "mos2_n", "wse2_p", "cnt_n", "cnt_p", "gan_n", "gan_p"]
LSTY = {"gaa_n": "-", "gaa_p": "--", "sige_p": "-.", "mos2_n": "-", "wse2_p": "--", "cnt_n": "-", "cnt_p": "--", "gan_n": "-", "gan_p": "--"}


def main():
    fig, axes = plt.subplots(1, 3, figsize=(COL2, 2.4))
    groups = [("gaa_n", "gaa_p", "sige_p"), ("mos2_n", "wse2_p", "cnt_n", "cnt_p"), ("gan_n", "gan_p")]
    titles = ["Si / SiGe nanosheets", "MoS$_2$ / WSe$_2$ / CNT", "GaN"]
    for ax, grp, ttl, lab in zip(axes, groups, titles, "abc"):
        for name in grp:
            p = dict(DEVICES[name]["params"]); p.update(cal[name]); W = eff_width(p); vdd = ANCHORS[name]["vdd"]
            vg = np.linspace(-0.2, vdd, 400)
            for vds, alpha in ((0.0, 1.0), (vdd, 0.45)):
                qgs, qgd = charges(vg, vg - vds, p, 300.15)
                cgg = np.gradient(qgs + qgd, vg) / (W * 1e6) * 1e15     # fF/um
                ax.plot(vg, cgg, ls=LSTY[name], color=DEVICE_COLOR[name], alpha=alpha, lw=1.2 if vds == 0 else 1.0,
                        label=f"{DEVICE_LABEL[name]}" + ("" if vds == 0 else f" ($V_{{DS}}$={vdd} V)"))
        ax.set_xlabel("$|V_{GS}|$ (V)"); ax.set_ylabel("$C_{gg}/W_{eff}$ (fF/µm)"); ax.set_title(ttl, fontsize=8)
        ax.legend(fontsize=5, ncol=1, loc="lower right"); panel_label(ax, f"({lab})", 0.03, 0.96)
    fig.tight_layout(w_pad=1.0); save(fig, "fig03b_capacitance")


if __name__ == "__main__":
    main()
