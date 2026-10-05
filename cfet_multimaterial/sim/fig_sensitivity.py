"""Figures 10-13: Si/SiGe nanosheet & mobility study, TMD contact-resistance crossover map,
CNT density/purity/contact study, GaN temperature/self-heating map."""
import os, csv
import numpy as np
import matplotlib.pyplot as plt
from .plotstyle import save, panel_label, LABEL, COLOR, MARKER, LS, COL1, COL2
from .platforms import PLATFORMS, PLATFORM_ORDER

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(HERE, "results")


def rows(name, study=None, platform=None):
    rr = list(csv.DictReader(open(os.path.join(RES, name))))
    return [r for r in rr if (study is None or r["study"] == study) and (platform is None or r["platform"] == platform)]


def f(r, k):
    return float(r[k]) if r[k] not in ("", "None") else np.nan


def fig_si_sige():
    fig, axes = plt.subplots(1, 3, figsize=(COL2, 2.3))
    rr = rows("sens_si_sige.csv", "nns", "si")
    M = np.full((4, 4), np.nan); V = np.full((4, 4), np.nan)
    for r in rr:
        i, j = int(f(r, "x1")) - 2, int(f(r, "x2")) - 2
        M[i, j] = f(r, "fRO") * 1e-9; V[i, j] = f(r, "VM") / PLATFORMS["si"]["vdd"]
    ax = axes[0]
    ax.imshow(M, origin="lower", cmap="Blues", extent=[1.5, 5.5, 1.5, 5.5])
    for i in range(4):
        for j in range(4):
            ax.text(j + 2, i + 2, f"{M[i, j]:.1f}\n$V_M$={V[i, j]:.2f}", ha="center", va="center", fontsize=5.5,
                    color="white" if M[i, j] > np.nanmean(M) else "black")
    ax.set_xlabel("$N_{NS,p}$"); ax.set_ylabel("$N_{NS,n}$"); ax.set_xticks([2, 3, 4, 5]); ax.set_yticks([2, 3, 4, 5]); ax.grid(False)
    ax.set_title("CFET-Si: $f_{RO}$ (GHz)", fontsize=8)
    ax = axes[1]
    for pl in ("si", "sige"):
        q = [r for r in rows("sens_si_sige.csv", "nns", pl) if f(r, "x1") == f(r, "x2")]
        n = [f(r, "x1") for r in q]
        ax.plot(n, [f(r, "fRO") * 1e-9 for r in q], ls=LS[pl], marker=MARKER[pl], color=COLOR[pl], label=f"{LABEL[pl]} $f_{{RO}}$")
        ax.plot(n, [f(r, "Ecycle") * 1e15 * 10 for r in q], ls=LS[pl], marker=MARKER[pl], mfc="none", color=COLOR[pl], alpha=0.6, label=f"{LABEL[pl]} $E_{{cycle}}$ (×10 fJ)")
    ax.set_xlabel("$N_{NS,n} = N_{NS,p}$"); ax.set_ylabel("GHz / 10 fJ"); ax.set_xticks([2, 3, 4, 5]); ax.legend(fontsize=5.5)
    rr = rows("sens_si_sige.csv", "mup_ratio")
    x = [f(r, "x1") for r in rr]
    ax = axes[2]
    ax.plot(x, [f(r, "tpLH") / f(r, "tpHL") for r in rr], "o-", color=COLOR["sige"], label="$t_{pLH}/t_{pHL}$")
    ax.plot(x, [f(r, "VM") / PLATFORMS["sige"]["vdd"] for r in rr], "s--", color=COLOR["si"], label="$V_M/V_{DD}$")
    ax.plot(x, [f(r, "fRO") / f(rr[0], "fRO") for r in rr], "^:", color=COLOR["tmd"], label="$f_{RO}$ (norm.)")
    ax.set_xlabel("$\\mu_{p,SiGe}/\\mu_{p,Si}$"); ax.legend(fontsize=6); ax.set_ylabel("ratio")
    for ax, l in zip(axes, "abc"):
        panel_label(ax, f"({l})", 0.03, 0.96)
    fig.tight_layout(w_pad=1.2); save(fig, "fig10_si_sige_sensitivity")


def fig_tmd():
    rr = rows("sens_tmd.csv", "tmd_rc"); rc = [0.1, 0.2, 0.5, 1.0, 2.0]
    E = np.full((5, 5), np.nan); F = np.full((5, 5), np.nan)
    for r in rr:
        i, j = rc.index(f(r, "x1")), rc.index(f(r, "x2"))
        E[i, j] = f(r, "Ecycle") * 1e15; F[i, j] = f(r, "fRO") * 1e-9
    # Si iso-frequency energy: interpolate Si E_cycle(f) from the low-VDD + VDD sweep points
    si = rows("sens_tmd.csv", "si_lowvdd") + [r for r in csv.DictReader(open(os.path.join(RES, "vdd_sweep.csv"))) if r["platform"] == "si"]
    fs = np.array([f(r, "fRO") * 1e-9 for r in si]); es = np.array([f(r, "Ecycle") for r in si]); o = np.argsort(fs)   # GHz, fJ
    fs, es = fs[o], es[o] * 1e15
    Esi = np.interp(np.log(F), np.log(fs), es)     # Si energy/cycle at the TMD frequency
    ratio = E / Esi
    fig, axes = plt.subplots(1, 3, figsize=(COL2, 2.4))
    ax = axes[0]
    im = ax.imshow(np.log10(ratio), origin="lower", cmap="RdBu_r", vmin=-0.25, vmax=0.25)
    cs = ax.contour(ratio, levels=[1.0], colors="k", linewidths=1.0)
    ax.clabel(cs, fmt={1.0: "$E_{TMD}=E_{Si}$"}, fontsize=6)
    for i in range(5):
        for j in range(5):
            ax.text(j, i, f"{ratio[i, j]:.2f}", ha="center", va="center", fontsize=6)
    ax.set_xticks(range(5)); ax.set_xticklabels(rc); ax.set_yticks(range(5)); ax.set_yticklabels(rc); ax.grid(False)
    ax.set_xlabel("$R_{C,p}$ (kΩ·µm)"); ax.set_ylabel("$R_{C,n}$ (kΩ·µm)")
    cb = fig.colorbar(im, ax=ax, fraction=0.046); cb.set_label("log$_{10}$($E_{cycle,TMD}/E_{cycle,Si}$ @ same $f$)", fontsize=6.5)
    ax = axes[1]
    for j in range(5):
        ax.semilogx(rc, F[:, j], "o-", color=plt.cm.Oranges(0.35 + 0.15 * j), label=f"$R_{{C,p}}$={rc[j]}")
    ax.set_xlabel("$R_{C,n}$ (kΩ·µm)"); ax.set_ylabel("5-stage $f_{RO}$ (GHz)"); ax.legend(fontsize=5.5, ncol=1)
    rr = rows("sens_tmd.csv", "tmd_dit"); ax = axes[2]
    x = [f(r, "x1") for r in rr]
    ax.loglog(x, [f(r, "Pstat") / f(rr[0], "Pstat") for r in rr], "v-", color=COLOR["gan"], label="static power")
    ax.loglog(x, [f(r, "fRO") / f(rr[0], "fRO") for r in rr], "o-", color=COLOR["tmd"], label="$f_{RO}$")
    ax.loglog(x, [f(r, "gain") / f(rr[0], "gain") for r in rr], "^:", color=COLOR["cnt"], label="gain $A_V$")
    ax.loglog(x, [f(r, "NML") / f(rr[0], "NML") for r in rr], "s--", color=COLOR["si"], label="$NM_L$")
    ax.set_xlabel("$D_{it}$ (cm$^{-2}$ eV$^{-1}$)"); ax.set_ylabel("normalised to $D_{it}=10^{11}$"); ax.legend(fontsize=6)
    for ax, l in zip(axes, "abc"):
        panel_label(ax, f"({l})", 0.03, 0.96) if l != "a" else ax.set_title("(a)", loc="left", fontsize=8.5, fontweight="bold")
    fig.tight_layout(w_pad=1.0); save(fig, "fig11_tmd_contact_crossover")
    # report critical RC along the diagonal
    diag = np.array([ratio[i, i] for i in range(5)])
    with open(os.path.join(RES, "tmd_crossover.csv"), "w") as fh:
        fh.write("RC_kohm_um,E_ratio_TMD_over_Si_isofreq,fRO_GHz\n")
        for i in range(5): fh.write(f"{rc[i]},{diag[i]:.4f},{F[i, i]:.4f}\n")
        if np.any(diag < 1) and np.any(diag > 1):
            rcc = np.exp(np.interp(0.0, np.log(diag), np.log(rc)))
            fh.write(f"RC_critical_kohm_um,{rcc:.4f},\n")


def fig_cnt():
    nom = dict(cnt_density=250.0, cnt_fmet=1e-4, cnt_rc=50.0)
    fig, axes = plt.subplots(1, 3, figsize=(COL2, 2.4))
    for ax, study, xl, lab in zip(axes, ("cnt_density", "cnt_fmet", "cnt_rc"),
                                  ("CNT density (µm$^{-1}$)", "metallic fraction $F_{met}$", "$R_C$ per side (Ω·µm)"), "abc"):
        rr = rows("sens_cnt.csv", study); x = np.array([f(r, "x1") for r in rr])
        k0 = int(np.argmin(np.abs(x - nom[study])))
        if study == "cnt_fmet":
            x = np.where(x == 0, 3e-5, x)
        for key, lab2, mk, c in (("fRO", "$f_{RO}$", "o-", COLOR["cnt"]), ("Ecycle", "$E_{cycle}$", "s--", COLOR["si"]),
                                 ("gain", "gain $A_V$", "^:", COLOR["sige"]), ("Pstat", "static power", "v-.", COLOR["gan"])):
            v = np.array([f(r, key) for r in rr])
            ax.plot(x, v / v[k0], mk, color=c, label=lab2, ms=3.5)
        if study == "cnt_fmet":
            g0 = f(rr[k0], "gain")
            ax.axhline(10 / g0, ls=":", color="k", lw=0.8); ax.text(x.min(), 10 / g0 * 1.1, "$A_V$ = 10", fontsize=6)
        ax.set_yscale("log")
        if study != "cnt_density":
            ax.set_xscale("log")
        if study == "cnt_fmet":
            ax.set_xticks([3e-5, 1e-4, 1e-3, 1e-2]); ax.set_xticklabels(["0", "$10^{-4}$", "$10^{-3}$", "$10^{-2}$"])
        ax.set_xlabel(xl); ax.set_ylabel("normalised to nominal")
        if lab == "a": ax.legend(fontsize=6, loc="upper left")
        panel_label(ax, f"({lab})", 0.03, 0.96) if lab != "a" else ax.set_title("(a)", loc="left", fontsize=8.5, fontweight="bold")
    fig.tight_layout(w_pad=1.0); save(fig, "fig12_cnt_sensitivity")


def fig_gan():
    fig, axes = plt.subplots(1, 3, figsize=(COL2, 2.4))
    g = rows("sens_gan.csv", "gan_temp"); s = rows("sens_gan.csv", "si_temp")
    T = np.array([f(r, "x1") for r in g]); fg = np.array([f(r, "fRO") for r in g]); fs_ = np.array([f(r, "fRO") for r in s])
    ax = axes[0]
    ax.plot(T, fg / fg[0], "v-", color=COLOR["gan"], label="CFET-GaN $f_{RO}$"); ax.plot(T, fs_ / fs_[0], "o--", color=COLOR["si"], label="CFET-Si $f_{RO}$")
    ax.plot(T, [f(r, "Pstat") / f(g[0], "Pstat") for r in g], "v:", color=COLOR["gan"], alpha=0.6, label="GaN static P")
    ax.plot(T, [f(r, "Pstat") / f(s[0], "Pstat") for r in s], "o:", color=COLOR["si"], alpha=0.6, label="Si static P")
    ax.set_yscale("log"); ax.set_xlabel("T (K)"); ax.set_ylabel("normalised to 300 K"); ax.legend(fontsize=5.5, loc="upper left", bbox_to_anchor=(0.0, 0.98))
    tcf_g = (fg[-1] - fg[0]) / fg[0] / (T[-1] - T[0]) * 1e6; tcf_s = (fs_[-1] - fs_[0]) / fs_[0] / (T[-1] - T[0]) * 1e6
    ax.text(0.03, 0.62, f"TCF (300–500 K):\nGaN {tcf_g:.0f} ppm/K\nSi {tcf_s:.0f} ppm/K", transform=ax.transAxes, ha="left", va="top", fontsize=6)
    ax = axes[1]
    rr = rows("sens_gan.csv", "gan_rth")
    for Tk, c in zip((300, 500), (0.45, 0.9)):
        q = [r for r in rr if f(r, "x2") == Tk]; xs = [f(r, "x1") for r in q]
        ax.plot(xs, [f(r, "NML") / 1.2 for r in q], "v-", color=plt.cm.Oranges(c), label=f"$NM_L/V_{{DD}}$, {Tk} K")
        ax.plot(xs, [f(r, "gain") / 100 for r in q], "^--", color=plt.cm.Oranges(c), mfc="none", label=f"$A_V/100$, {Tk} K")
    ax.axhline(0.1, ls=":", color="k", lw=0.8); ax.text(4.0, 0.105, "$NM_L$=0.1$V_{DD}$ / $A_V$=10 limit", ha="right", fontsize=6)
    ax.set_xlabel("$R_{th}/R_{th,nom}$"); ax.set_ylabel("inverter margin"); ax.legend(fontsize=5.5, loc="center right"); ax.set_ylim(-0.02, 0.36)
    ax = axes[2]
    rr = rows("sens_gan.csv", "gan_vth"); rs = rows("sens_gan.csv", "gan_vth_skew")
    ax.plot([100 * f(r, "x1") for r in rr], [f(r, "fRO") * 1e-9 for r in rr], "v-", color=COLOR["gan"], label="common $\\Delta V_{TH}$")
    ax.plot([100 * f(r, "x1") for r in rs], [f(r, "fRO") * 1e-9 for r in rs], "^--", color=COLOR["si"], label="skewed ($+n$, $-p$)")
    ax.set_xlabel("$\\Delta V_{TH}$ (%)"); ax.set_ylabel("$f_{RO}$ (GHz)"); ax.legend(fontsize=6)
    for ax, l in zip(axes, "abc"):
        panel_label(ax, f"({l})", 0.03, 0.96)
    fig.tight_layout(w_pad=1.0); save(fig, "fig13_gan_thermal")
    with open(os.path.join(RES, "gan_tcf.csv"), "w") as fh:
        fh.write("platform,TCF_ppm_per_K_300_500K,f300_GHz,f500_GHz\n")
        fh.write(f"gan,{tcf_g:.1f},{fg[0]*1e-9:.4f},{fg[-1]*1e-9:.4f}\nsi,{tcf_s:.1f},{fs_[0]*1e-9:.4f},{fs_[-1]*1e-9:.4f}\n")


if __name__ == "__main__":
    fig_si_sige(); fig_tmd(); fig_cnt(); fig_gan()
