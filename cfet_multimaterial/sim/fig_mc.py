"""Figures 14-15: Monte Carlo histograms + yield, and the material-selection chart."""
import os, csv
import numpy as np
import matplotlib.pyplot as plt
from .plotstyle import save, panel_label, LABEL, COLOR, MARKER, LS, COL1, COL2
from .platforms import PLATFORMS, PLATFORM_ORDER

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(HERE, "results")


def f(r, k):
    return float(r[k]) if r[k] not in ("", "None") else np.nan


def fig_mc():
    ro = list(csv.DictReader(open(os.path.join(RES, "mc_ro.csv"))))
    inv = list(csv.DictReader(open(os.path.join(RES, "mc_inverter.csv"))))
    summ = {r["platform"]: r for r in csv.DictReader(open(os.path.join(RES, "mc_yield_summary.csv")))}
    fig, axes = plt.subplots(2, 3, figsize=(COL2, 4.4))
    a, b, c = axes[0]; d, e, g = axes[1]
    for pl in PLATFORM_ORDER:
        rr = [r for r in ro if r["platform"] == pl]; fr = np.array([f(r, "fRO") for r in rr]); fr = fr[fr > 0]
        f0 = f(summ[pl], "f_nom_GHz") * 1e9
        a.hist(fr / f0, bins=25, histtype="step", color=COLOR[pl], lw=1.2, label=LABEL[pl], density=True)
        ec = np.array([f(r, "Ecycle") for r in rr]) * 1e15
        b.hist(ec / np.nanmedian(ec), bins=25, histtype="step", color=COLOR[pl], lw=1.2, density=True)
        ii = [r for r in inv if r["platform"] == pl]
        vm = np.array([f(r, "VM") for r in ii]) / PLATFORMS[pl]["vdd"]
        c.hist(vm, bins=25, histtype="step", color=COLOR[pl], lw=1.2, density=True)
        nml = np.array([f(r, "NML") for r in ii]) / PLATFORMS[pl]["vdd"]; nmh = np.array([f(r, "NMH") for r in ii]) / PLATFORMS[pl]["vdd"]
        d.scatter(nml, nmh, s=4, color=COLOR[pl], alpha=0.5, marker=MARKER[pl], label=LABEL[pl])
    a.axvline(0.9, ls=":", color="k", lw=0.8); a.text(0.9, a.get_ylim()[1] * 0.95, " $f_{target}$=0.9$f_{nom}$", fontsize=6, va="top")
    a.set_xlabel("$f_{RO}/f_{RO,nom}$"); a.set_ylabel("density"); a.legend(fontsize=5.5)
    b.set_xlabel("$E_{cycle}$/median"); b.set_ylabel("density (log)"); b.set_yscale("log")
    c.set_xlabel("$V_M/V_{DD}$"); c.set_ylabel("density (log)"); c.set_yscale("log")
    d.axvline(0.1, ls=":", color="k", lw=0.8); d.axhline(0.1, ls=":", color="k", lw=0.8)
    d.set_xlabel("$NM_L/V_{DD}$"); d.set_ylabel("$NM_H/V_{DD}$"); d.legend(fontsize=5.5, markerscale=2)
    x = np.arange(5); names = [LABEL[p].replace("CFET-", "") for p in PLATFORM_ORDER]
    e.bar(x - 0.18, [f(summ[p], "Y_f_pct") for p in PLATFORM_ORDER], 0.36, color=[COLOR[p] for p in PLATFORM_ORDER], label="$Y_f$ ($f_{RO}\\geq0.9f_{nom}$)")
    e.bar(x + 0.18, [f(summ[p], "Y_func_pct") for p in PLATFORM_ORDER], 0.36, color=[COLOR[p] for p in PLATFORM_ORDER], alpha=0.5, hatch="///", label="functional yield")
    e.set_xticks(x); e.set_xticklabels(names, fontsize=6.5); e.set_ylabel("yield (%)"); e.set_ylim(0, 125); e.legend(fontsize=5.5, loc="upper center", ncol=2); e.grid(axis="x", visible=False)
    for xi, p in zip(x, PLATFORM_ORDER):
        e.text(xi - 0.18, f(summ[p], "Y_f_pct") + 1, f"{f(summ[p], 'Y_f_pct'):.0f}", ha="center", fontsize=5.5)
        e.text(xi + 0.18, f(summ[p], "Y_func_pct") + 1, f"{f(summ[p], 'Y_func_pct'):.0f}", ha="center", fontsize=5.5)
    g.bar(x, [f(summ[p], "f_sigma_over_mu_pct") for p in PLATFORM_ORDER], 0.6, color=[COLOR[p] for p in PLATFORM_ORDER])
    for xi, p in zip(x, PLATFORM_ORDER):
        g.text(xi, f(summ[p], "f_sigma_over_mu_pct"), f"{f(summ[p], 'f_sigma_over_mu_pct'):.1f}", ha="center", va="bottom", fontsize=6)
    g.set_xticks(x); g.set_xticklabels(names, fontsize=6.5); g.set_ylabel("$\\sigma_f/\\mu_f$ (%)"); g.grid(axis="x", visible=False)
    for ax, l in zip((a, b, c, d, e, g), "abcdef"):
        panel_label(ax, f"({l})", 0.03, 0.96)
    fig.tight_layout(h_pad=0.8, w_pad=1.0); save(fig, "fig14_montecarlo")


def fig_selection():
    """Radar-style material-selection chart on five normalised axes (higher = better)."""
    nom = {r["platform"]: r for r in csv.DictReader(open(os.path.join(RES, "nominal_ro.csv"))) if r["N"] == "5"}
    inv = {r["platform"]: r for r in csv.DictReader(open(os.path.join(RES, "nominal_inverter.csv")))}
    summ = {r["platform"]: r for r in csv.DictReader(open(os.path.join(RES, "mc_yield_summary.csv")))}
    temp = list(csv.DictReader(open(os.path.join(RES, "temp_sweep.csv"))))
    axes_names = ["speed\n($f_{RO}$)", "energy eff.\n(1/$E_{cycle}$)", "low $V_{DD}$\n(1/$V_{DD}$)", "temp. stability\n(1/|$\\Delta f/f$|, 27→125 °C)", "variability\n(1/$\\sigma_f$)"]
    vals = {}
    for pl in PLATFORM_ORDER:
        tt = [r for r in temp if r["platform"] == pl]
        f27 = [f(r, "fRO") for r in tt if f(r, "temp_c") == 27][0]; f125 = [f(r, "fRO") for r in tt if f(r, "temp_c") == 125][0]
        vals[pl] = np.array([f(nom[pl], "fRO"), 1 / f(nom[pl], "Ecycle"), 1 / PLATFORMS[pl]["vdd"], 1 / abs(f125 / f27 - 1), 1 / f(summ[pl], "f_sigma_over_mu_pct")])
    M = np.array([vals[p] for p in PLATFORM_ORDER]); M = M / M.max(axis=0)
    ang = np.linspace(0, 2 * np.pi, 5, endpoint=False).tolist(); ang += ang[:1]
    fig = plt.figure(figsize=(COL1, 3.2)); ax = fig.add_subplot(111, polar=True)
    for k, pl in enumerate(PLATFORM_ORDER):
        v = M[k].tolist() + [M[k][0]]
        ax.plot(ang, v, ls=LS[pl], marker=MARKER[pl], color=COLOR[pl], label=LABEL[pl], lw=1.2); ax.fill(ang, v, color=COLOR[pl], alpha=0.06)
    ax.set_xticks(ang[:-1]); ax.set_xticklabels(axes_names, fontsize=6.5); ax.set_yticks([0.25, 0.5, 0.75, 1.0]); ax.set_yticklabels(["", "0.5", "", "1"], fontsize=6)
    ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.12), fontsize=6)
    save(fig, "fig15_selection_chart")
    with open(os.path.join(RES, "selection_metrics.csv"), "w") as fh:
        fh.write("platform,fRO_GHz,inv_Ecycle_fJ,vdd,temp_stability_1_over_dfdf,sigma_f_pct\n")
        for k, pl in enumerate(PLATFORM_ORDER):
            v = vals[pl]; fh.write(f"{pl},{v[0]*1e-9:.4f},{1/v[1]*1e15:.4f},{PLATFORMS[pl]['vdd']},{v[3]:.4f},{1/v[4]:.3f}\n")


if __name__ == "__main__":
    fig_mc(); fig_selection()
