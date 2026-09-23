"""Generate publication figures (PNG, 300 dpi) from results/ into figures/."""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
RES, FIG = os.path.join(ROOT, "results"), os.path.join(ROOT, "figures")
os.makedirs(FIG, exist_ok=True)

# validated categorical palette (fixed order) + neutral for baselines
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = (
    "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948")
GREY, INK, INK2 = "#9b9a94", "#0b0b0b", "#52514e"
PROPOSED_T, PROPOSED_C = "PC-HDT (proposed)", "PC-HDT optimiser (proposed)"

plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.grid": True, "grid.color": "#e6e5e0",
                     "grid.linewidth": 0.6, "lines.linewidth": 2.0, "legend.frameon": False,
                     "savefig.dpi": 300, "savefig.bbox": "tight"})


def save(fig, name):
    fig.savefig(os.path.join(FIG, name)); plt.close(fig)


def mean_std(df, group, col):
    g = df.groupby(group, sort=False)[col]
    return g.mean(), g.std()


def fig1():
    d = pd.read_csv(os.path.join(RES, "E1_characterisation_readings.csv"))
    fig, ax = plt.subplots(2, 2, figsize=(7.2, 5.4))
    for sw, col, lab in [("V", BLUE, "voltage sweep (6–11.5 kV)"), ("Q", ORANGE, "flow sweep (30–250 sccm)")]:
        s = d[d.sweep == sw].sort_values("SEI_kJ_per_L")
        ax[0, 0].plot(s.SEI_kJ_per_L, s.y_NH3_pct, "-o", color=col, ms=4, label=lab)
        ax[0, 1].plot(s.SEI_kJ_per_L, s.EY_g_per_kWh, "-o", color=col, ms=4, label=lab)
    ax[0, 0].set(xlabel="SEI (kJ/L)", ylabel="Outlet NH$_3$ (mol %)", title="(a) NH$_3$ concentration vs SEI")
    ax[0, 1].set(xlabel="SEI (kJ/L)", ylabel="Energy yield (g/kWh)", title="(b) Energy yield vs SEI")
    ax[0, 0].legend(fontsize=8)
    s = d[d.sweep == "xH2"]
    ax[1, 0].plot(s.xH2, s.EY_g_per_kWh, "-o", color=BLUE, ms=4)
    ax[1, 0].set(xlabel="H$_2$ inlet fraction", ylabel="Energy yield (g/kWh)", title="(c) Feed ratio")
    s = d[d.sweep == "f"]
    ax[1, 1].plot(s.f_kHz, s.EY_g_per_kWh, "-o", color=BLUE, ms=4)
    ax[1, 1].set(xlabel="Frequency (kHz)", ylabel="Energy yield (g/kWh)", title="(d) Frequency (P varies with f)")
    fig.tight_layout(); save(fig, "fig1_characterisation.png")


def fig2():
    t = np.load(os.path.join(RES, "E2_trace_seed10.npz"), allow_pickle=True)
    names = list(t["names"]); th = t["t_h"]
    ip, ib = names.index(PROPOSED_T), names.index("Batch recalibration")
    ig = names.index("GPR (sliding window)")
    fig, ax = plt.subplots(2, 1, figsize=(7.2, 6.2), gridspec_kw=dict(height_ratios=[1.1, 1]))
    w = slice(266, 306)  # 133-153 h: window around the unannounced poisoning event (140 h)
    tw = th[w]
    ym = 1e2 * np.exp(t["Z"][w, 0])
    fp, sp = t["F"][ip, w, 0], t["S"][ip, w, 0]
    yp = 1e2 * np.exp(fp)
    err = np.vstack([yp - 1e2 * np.exp(fp - 1.96 * sp), 1e2 * np.exp(fp + 1.96 * sp) - yp])
    ax[0].errorbar(tw + 0.08, yp, err, fmt="o", ms=4.5, color=BLUE, ecolor=BLUE, elinewidth=1,
                   capsize=0, alpha=0.9, label="PC-HDT forecast ± 95 % PI")
    ax[0].plot(tw - 0.08, 1e2 * np.exp(t["F"][ib, w, 0]), "s", ms=3.5, color=ORANGE, label="Batch recalibration")
    ax[0].plot(tw - 0.16, 1e2 * np.exp(t["F"][ig, w, 0]), "^", ms=3.5, color=GREY, label="GPR (sliding window)")
    ax[0].plot(tw, ym, "_", ms=11, mew=2.2, color=INK, label="Measured (plant)")
    ax[0].axvline(140, color=RED, lw=1, ls="--")
    ax[0].set(ylabel="NH$_3$ (mol %)", xlabel="Time on stream (h)",
              title="(a) One-step-ahead forecasts at new random operating points, 133–153 h (seed 10)")
    ax[0].legend(fontsize=7, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.2))
    ax[0].text(140.2, 0.02, "poisoning event", color=RED, fontsize=8, transform=ax[0].get_xaxis_transform())
    A = t["A"]; r = 96
    ax[1].plot(th, A / A[r], color=INK, label="True (hidden) relative activity")
    ax[1].plot(th, t["Ah"][ip] / t["Ah"][ip, r], color=BLUE, lw=1.4, label="PC-HDT estimate")
    ax[1].step(th, t["Ah"][ib] / t["Ah"][ib, r], color=ORANGE, lw=1.4, where="post", label="Batch recalibration (24 h)")
    ax[1].axvline(140, color=RED, lw=1, ls="--"); ax[1].set_xlim(0, th[-1])
    ax[1].axvspan(0, 48, color=GREY, alpha=0.12, lw=0)
    ax[1].text(1, 0.03, "commissioning", fontsize=7.5, color=INK2, transform=ax[1].get_xaxis_transform())
    ax[1].set(xlabel="Time on stream (h)", ylabel="a(t) / a(48 h)", title="(b) Catalyst-activity tracking")
    ax[1].legend(fontsize=7)
    fig.tight_layout(); save(fig, "fig2_twin_tracking.png")


def barh(ax, names, m, s, proposed, xlabel, title, fmt="{:.2f}", zero=False):
    """Dot plot (mean ± SD across seeds); bars only when the axis starts at zero."""
    y = np.arange(len(names))[::-1]
    cols = [BLUE if n == proposed else GREY for n in names]
    if zero:
        ax.barh(y, m, color=cols, height=0.6)
        ax.errorbar(m, y, xerr=s, fmt="none", ecolor=INK2, lw=0.8, capsize=2)
    else:
        for yi, mi, si, c in zip(y, m, s, cols):
            ax.errorbar(mi, yi, xerr=si, fmt="o", ms=7 if c == BLUE else 5.5, color=c, ecolor=c, lw=1.2, capsize=2)
    ax.set_yticks(y); ax.set_yticklabels(names, fontsize=7.5); ax.set(xlabel=xlabel, title=title)
    ax.grid(axis="y", visible=False)
    span = np.nanmax(m + s) - (0 if zero else np.nanmin(m - s))
    for yi, v, e in zip(y, m, s):
        ax.text(v + e + 0.03 * span, yi, fmt.format(v), va="center", fontsize=7, color=INK)
    lo = 0 if zero else np.nanmin(m - s) - 0.05 * span
    ax.set_xlim(lo, np.nanmax(m + s) + 0.28 * span)


def fig3():
    d = pd.read_csv(os.path.join(RES, "E2_twin_fidelity_per_seed.csv"))
    names = list(d.method.unique())
    fig, ax = plt.subplots(1, 3, figsize=(10, 3.6), sharey=True)
    for a, col, xl, tt, f in [(ax[0], "MAPE_NH3_pct", "MAPE (%)", "(a) NH$_3$ forecast error", "{:.1f}"),
                              (ax[1], "RMSE_T_K", "RMSE (K)", "(b) Bed-temperature error", "{:.1f}"),
                              (ax[2], "PICP95_NH3", "coverage of 95 % PI", "(c) Uncertainty calibration", "{:.2f}")]:
        m, s = mean_std(d, "method", col)
        barh(a, names, m[names].values, s[names].values, PROPOSED_T, xl, tt, f, zero=col != "PICP95_NH3")
    ax[2].axvline(0.95, color=INK2, ls="--", lw=1)
    fig.tight_layout(); save(fig, "fig3_twin_benchmark.png")


def fig4():
    t = np.load(os.path.join(RES, "E3_trace_seed10.npz"))
    key = lambda n: n.replace(" ", "_").replace(":", "")  # noqa: E731
    Lp, Lpi, Ls = t[key(PROPOSED_C)], t[key("Thermal PI (max-load)")], t[key("Static-model optimiser")]
    th = Lp[:, 0]
    fig, ax = plt.subplots(3, 1, figsize=(7.2, 6.8), sharex=True)
    ax[0].fill_between(th, 0, Lp[:, 1], color=GREY, alpha=0.25, lw=0, label="Available renewable power")
    ax[0].plot(th, Lp[:, 6], color=BLUE, lw=1.4, label="PC-HDT optimiser (proposed)")
    ax[0].plot(th, Ls[:, 6], color=ORANGE, lw=1.0, label="Static-model optimiser")
    ax[0].set(ylabel="Discharge power (W)", title="(a) Power tracking under intermittent supply (seed 10)")
    ax[0].legend(fontsize=7, ncol=3, loc="upper left")
    ax[1].plot(th, Ls[:, 7], color=ORANGE, lw=1.0, label="Static-model optimiser")
    ax[1].plot(th, Lpi[:, 7], color=GREY, lw=1.0, label="Thermal PI")
    ax[1].plot(th, Lp[:, 7], color=BLUE, lw=1.4, label="PC-HDT optimiser (proposed)")
    ax[1].axhline(460, color=RED, ls="--", lw=1); ax[1].text(1, 461, "T$_{max}$ = 460 K", color=RED, fontsize=8, va="bottom")
    ax[1].set(ylabel="Bed temperature (K)", title="(b) Thermal safety"); ax[1].set_ylim(290, 500)
    ax[1].legend(fontsize=7, ncol=3, loc="lower left")
    ax[2].plot(th, Ls[:, 12], color=ORANGE, lw=1.4, label="Static-model optimiser")
    ax[2].plot(th, Lpi[:, 12], color=GREY, lw=1.4, label="Thermal PI")
    ax[2].plot(th, Lp[:, 12], color=BLUE, lw=1.8, label="PC-HDT optimiser (proposed)")
    ax[2].set(xlabel="Time on stream (h)", ylabel="Catalyst activity a(t)", title="(c) Catalyst degradation")
    ax[2].legend(fontsize=7); ax[2].set_xlim(0, th[-1])
    fig.tight_layout(); save(fig, "fig4_closed_loop_trace.png")


def fig5():
    d = pd.read_csv(os.path.join(RES, "E3_control_per_seed.csv"))
    names = list(d.controller.unique())
    fig, ax = plt.subplots(1, 4, figsize=(12, 3.6), sharey=True)
    for a, col, xl, tt, f in [(ax[0], "NH3_total_g", "g over 240 h", "(a) NH$_3$ produced", "{:.2f}"),
                              (ax[1], "EY_g_per_kWh", "g/kWh", "(b) Energy yield", "{:.3f}"),
                              (ax[2], "T_violation_h", "hours", "(c) Time above T$_{max}$", "{:.1f}"),
                              (ax[3], "final_activity", "a(240 h)", "(d) Residual catalyst activity", "{:.3f}")]:
        m, s = mean_std(d, "controller", col)
        barh(a, names, m[names].values, s[names].values, PROPOSED_C, xl, tt, f, zero=col == "T_violation_h")
    fig.tight_layout(); save(fig, "fig5_control_benchmark.png")


def fig6():
    a = pd.read_csv(os.path.join(RES, "E4a_noise_sensitivity.csv"))
    b = pd.read_csv(os.path.join(RES, "E4b_deactivation_sensitivity.csv"))
    fig, ax = plt.subplots(1, 3, figsize=(10.5, 3.3))
    cols = {"PC-HDT (proposed)": BLUE, "Batch recalibration": ORANGE, "GPR (sliding window)": AQUA,
            "PC-HDT optimiser (proposed)": BLUE, "Recalibrated-model optimiser": ORANGE,
            "Static-model optimiser": VIOLET, "Thermal PI (max-load)": GREY}
    g = a.groupby(["method", "noise"]).MAPE_NH3_pct.agg(["mean", "std"]).reset_index()
    for n, s in g.groupby("method"):
        ax[0].errorbar(s.noise, s["mean"], s["std"], marker="o", ms=5, color=cols[n], label=n, capsize=2)
    ax[0].set(xlabel="Sensor-noise multiplier", ylabel="NH$_3$ MAPE (%)", title="(a) Robustness to sensor noise")
    ax[0].legend(fontsize=7)
    for j, (col, yl, tt) in enumerate([("NH3_total_g", "NH$_3$ over 240 h (g)", "(b) Production vs deactivation"),
                                       ("T_violation_h", "Hours above T$_{max}$", "(c) Safety vs deactivation")]):
        g = b.groupby(["controller", "deact_scale"])[col].agg(["mean", "std"]).reset_index()
        for n, s in g.groupby("controller"):
            top = n == PROPOSED_C   # draw proposed on top (it overlaps Thermal PI at 0 h in panel c)
            ax[j + 1].errorbar(s.deact_scale, s["mean"], s["std"], marker="o", ms=6 if top else 5, color=cols[n],
                               label=n, capsize=2, zorder=5 if top else 2)
        ax[j + 1].set(xlabel="Deactivation-rate multiplier", ylabel=yl, title=tt)
    ax[1].legend(fontsize=7)
    fig.tight_layout(); save(fig, "fig6_sensitivity.png")


if __name__ == "__main__":
    for f in (fig1, fig2, fig3, fig4, fig5, fig6):
        f(); print("wrote", f.__name__)
