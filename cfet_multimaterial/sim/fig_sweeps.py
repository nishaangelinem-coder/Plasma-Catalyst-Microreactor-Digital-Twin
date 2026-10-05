"""Figures 8-12: fRO-VDD, power-frequency, energy/cycle-frequency, PDP-VDD, temperature."""
import os, csv
import numpy as np
import matplotlib.pyplot as plt
from .plotstyle import save, panel_label, LABEL, COLOR, MARKER, LS, COL1, COL2
from .platforms import PLATFORMS, PLATFORM_ORDER

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(HERE, "results")


def load(name):
    rows = list(csv.DictReader(open(os.path.join(RES, name))))
    out = {}
    for pl in PLATFORM_ORDER:
        rr = [r for r in rows if r["platform"] == pl and r["osc"] == "True"]
        out[pl] = {k: np.array([float(r[k]) if r[k] not in ("", "None") else np.nan for r in rr])
                   for k in ["vdd", "temp_c", "fRO", "tpd", "Pavg", "Ecycle", "PDP", "VM", "gain", "NML", "NMH", "Pstat", "E_period"]}
    return out


def fig_vdd():
    d = load("vdd_sweep.csv")
    fig, axes = plt.subplots(2, 2, figsize=(COL2, 4.6))
    (a, b), (c, e) = axes
    for pl in PLATFORM_ORDER:
        x = d[pl]
        a.semilogy(x["vdd"], x["fRO"] * 1e-9, ls=LS[pl], marker=MARKER[pl], color=COLOR[pl], label=LABEL[pl])
        b.loglog(x["fRO"] * 1e-9, x["Pavg"] * 1e6, ls=LS[pl], marker=MARKER[pl], color=COLOR[pl], label=LABEL[pl])
        c.semilogx(x["fRO"] * 1e-9, x["Ecycle"] * 1e15, ls=LS[pl], marker=MARKER[pl], color=COLOR[pl], label=LABEL[pl])
        e.semilogy(x["vdd"], x["PDP"] * 1e15, ls=LS[pl], marker=MARKER[pl], color=COLOR[pl], label=LABEL[pl])
    a.set_xlabel("$V_{DD}$ (V)"); a.set_ylabel("5-stage $f_{RO}$ (GHz)"); a.legend(fontsize=6)
    b.set_xlabel("$f_{RO}$ (GHz)"); b.set_ylabel("$P_{avg}$ (µW)")
    c.set_xlabel("$f_{RO}$ (GHz)"); c.set_ylabel("$E_{cycle}$ (fJ)"); c.set_yscale("log")
    e.set_xlabel("$V_{DD}$ (V)"); e.set_ylabel("PDP = $P_{avg}\\,t_{pd}$ (fJ)")
    for ax, l in zip((a, b, c, e), "abcd"):
        panel_label(ax, f"({l})", 0.03, 0.96)
    fig.tight_layout(h_pad=0.8, w_pad=1.0); save(fig, "fig08_vdd_sweep")


def fig_temp():
    d = load("temp_sweep.csv")
    fig, axes = plt.subplots(1, 3, figsize=(COL2, 2.3))
    for pl in PLATFORM_ORDER:
        x = d[pl]; o = np.argsort(x["temp_c"]); T = x["temp_c"][o]
        f = x["fRO"][o]; f27 = np.interp(27, T, f)
        axes[0].plot(T, f / f27, ls=LS[pl], marker=MARKER[pl], color=COLOR[pl], label=LABEL[pl])
        axes[1].semilogy(T, x["Ecycle"][o] * 1e15, ls=LS[pl], marker=MARKER[pl], color=COLOR[pl])
        axes[2].semilogy(T, x["Pstat"][o] * 1e9, ls=LS[pl], marker=MARKER[pl], color=COLOR[pl])
    axes[0].set_xlabel("T (°C)"); axes[0].set_ylabel("$f_{RO}(T)/f_{RO}(27°C)$"); axes[0].legend(fontsize=6)
    axes[1].set_xlabel("T (°C)"); axes[1].set_ylabel("$E_{cycle}$ (fJ)")
    axes[2].set_xlabel("T (°C)"); axes[2].set_ylabel("inverter static power (nW)")
    for ax, l in zip(axes, "abc"):
        panel_label(ax, f"({l})", 0.03, 0.96)
    fig.tight_layout(w_pad=1.0); save(fig, "fig09_temperature")


if __name__ == "__main__":
    fig_vdd(); fig_temp()
