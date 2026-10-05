"""Figures 5-7: VTCs, inverter/RO FoM comparison, RO waveforms."""
import os, csv
import numpy as np
import matplotlib.pyplot as plt
from .plotstyle import save, panel_label, LABEL, COLOR, MARKER, LS, COL1, COL2
from .platforms import PLATFORMS, PLATFORM_ORDER

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(HERE, "results")


def rows(name):
    return list(csv.DictReader(open(os.path.join(RES, name))))


def fig_vtc():
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(COL2, 2.5))
    for pl in PLATFORM_ORDER:
        w = np.load(os.path.join(RES, f"waveforms_{pl}.npz")); vdd = PLATFORMS[pl]["vdd"]
        ax.plot(w["vin"] / vdd, w["vout"] / vdd, ls=LS[pl], color=COLOR[pl], label=f"{LABEL[pl]} ({vdd} V)")
        g = np.abs(np.gradient(w["vout"], w["vin"]))
        bx.plot(w["vin"] / vdd, g, ls=LS[pl], color=COLOR[pl], label=LABEL[pl])
    ax.plot([0, 1], [0, 1], ":", color="#c3c2b7", lw=0.7)
    ax.set_xlabel("$V_{in}/V_{DD}$"); ax.set_ylabel("$V_{out}/V_{DD}$"); ax.legend(fontsize=6, loc="upper right")
    bx.set_xlabel("$V_{in}/V_{DD}$"); bx.set_ylabel("$|dV_{out}/dV_{in}|$"); bx.set_xlim(0.2, 0.8)
    panel_label(ax, "(a)"); panel_label(bx, "(b)")
    fig.tight_layout(w_pad=1.2); save(fig, "fig05_inverter_vtc")


def fig_fom():
    inv = {r["platform"]: r for r in rows("nominal_inverter.csv")}
    ro = {(r["platform"], r["N"]): r for r in rows("nominal_ro.csv")}
    fig, axes = plt.subplots(2, 3, figsize=(COL2, 3.9))
    x = np.arange(5); names = [LABEL[p].replace("CFET-", "") for p in PLATFORM_ORDER]; cols = [COLOR[p] for p in PLATFORM_ORDER]

    def bars(ax, vals, ylab, lab, fmt="{:.2f}", log=False):
        ax.bar(x, vals, 0.62, color=cols)
        for xi, v in zip(x, vals):
            ax.text(xi, v, fmt.format(v), ha="center", va="bottom", fontsize=6)
        ax.set_xticks(x); ax.set_xticklabels(names, fontsize=6.5); ax.set_ylabel(ylab); ax.grid(axis="x", visible=False)
        if log: ax.set_yscale("log")
        panel_label(ax, lab, 0.03, 0.97)
    bars(axes[0, 0], [float(inv[p]["VM"]) / PLATFORMS[p]["vdd"] for p in PLATFORM_ORDER], "$V_M/V_{DD}$", "(a)")
    axes[0, 0].axhline(0.5, ls=":", color="#898781", lw=0.7); axes[0, 0].set_ylim(0, 0.7)
    w = 0.3
    axes[0, 1].bar(x - w / 2, [float(inv[p]["NML"]) / PLATFORMS[p]["vdd"] for p in PLATFORM_ORDER], w, color=cols, label="$NM_L$")
    axes[0, 1].bar(x + w / 2, [float(inv[p]["NMH"]) / PLATFORMS[p]["vdd"] for p in PLATFORM_ORDER], w, color=cols, alpha=0.55, hatch="///", label="$NM_H$")
    axes[0, 1].set_xticks(x); axes[0, 1].set_xticklabels(names, fontsize=6.5); axes[0, 1].set_ylabel("$NM/V_{DD}$"); axes[0, 1].legend(fontsize=6); axes[0, 1].grid(axis="x", visible=False)
    panel_label(axes[0, 1], "(b)", 0.03, 0.97)
    bars(axes[0, 2], [float(inv[p]["gain"]) for p in PLATFORM_ORDER], "max. gain $A_V$", "(c)", "{:.1f}")
    bars(axes[1, 0], [float(inv[p]["tpd"]) * 1e12 for p in PLATFORM_ORDER], "inverter $t_{pd}$ (ps)", "(d)", "{:.1f}", log=True)
    bars(axes[1, 1], [float(ro[(p, "5")]["fRO"]) * 1e-9 for p in PLATFORM_ORDER], "5-stage $f_{RO}$ (GHz)", "(e)", "{:.2f}", log=True)
    bars(axes[1, 2], [float(ro[(p, "5")]["Ecycle"]) * 1e15 for p in PLATFORM_ORDER], "RO $E_{cycle}$ (fJ)", "(f)", "{:.2f}", log=True)
    fig.tight_layout(h_pad=0.8, w_pad=1.0); save(fig, "fig06_inverter_ro_fom")


def fig_ro_waves():
    fig, axes = plt.subplots(5, 1, figsize=(COL1, 5.4), sharex=False)
    for ax, pl in zip(axes, PLATFORM_ORDER):
        w = np.load(os.path.join(RES, f"waveforms_{pl}.npz")); vdd = PLATFORMS[pl]["vdd"]
        if "t_ro5" not in w:
            ax.text(0.5, 0.5, "no oscillation", transform=ax.transAxes, ha="center"); continue
        t, v, i, tc = w["t_ro5"], w["v_ro5"], w["idd_ro5"], w["tcross_ro5"]
        t0, t1 = tc[10], tc[14]
        m = (t >= t0 - 0.2 * (t1 - t0) / 4) & (t <= t1)
        ax.plot((t[m] - t0) * 1e12, v[m], "-", color=COLOR[pl], lw=1.1, label=f"V(n3), {LABEL[pl]}")
        ax.set_ylabel("V (V)"); ax.set_ylim(-0.15, vdd + 0.25)
        ax.text(0.98, 0.9, f"{LABEL[pl]}: $f_{{RO}}$ = {1e-9/np.mean(np.diff(tc[10:30])):.2f} GHz", transform=ax.transAxes, ha="right", va="top", fontsize=7)
        ax.text(0.02, 0.9, "(" + "abcde"[PLATFORM_ORDER.index(pl)] + ")", transform=ax.transAxes, fontsize=8, fontweight="bold", va="top")
        ax.set_xlabel("time after cycle 10 (ps)") if pl == "gan" else None
    fig.tight_layout(h_pad=0.5); save(fig, "fig07_ro_waveforms")


if __name__ == "__main__":
    fig_vtc(); fig_fom(); fig_ro_waves()
