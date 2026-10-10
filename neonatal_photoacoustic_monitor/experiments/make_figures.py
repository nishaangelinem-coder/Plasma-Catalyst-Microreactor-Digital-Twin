"""Publication figures (300 dpi PNG) from results/*.csv|npz."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch, FancyArrowPatch
import common

RES, FIG = common.RES, common.FIG
plt.rcParams.update({"font.size": 8, "axes.titlesize": 9, "axes.labelsize": 8, "legend.fontsize": 7,
                     "figure.dpi": 110, "savefig.dpi": 300, "axes.spines.top": False, "axes.spines.right": False})
C = {"Proposed EKF": "#c0392b", "NIRS rScO2": "#2980b9", "PA linear unmixing": "#7f8c8d", "PA fluence-compensated": "#27ae60",
     "EKF -echo": "#e67e22", "EKF -reference": "#8e44ad", "EKF -fluence corr.": "#16a085", "EKF -depth gating": "#d35400",
     "Rectal proxy": "#2980b9", "Scalp thermistor": "#95a5a6", "PA amplitude (800 nm)": "#7f8c8d", "Echo shift only": "#27ae60"}
LAYER_COL = {"scalp": "#f5cba7", "fontanelle": "#d7bde2", "bone": "#d5d8dc", "csf": "#aed6f1", "sinus": "#f1948a", "brain": "#fadbd8"}


def save(fig, name):
    try:
        fig.tight_layout()
    except Exception:
        pass
    fig.savefig(os.path.join(FIG, name), bbox_inches="tight"); plt.close(fig); print("wrote", name)


# ------------------------------------------------------------------ Fig 0 schematic
def fig0():
    fig, ax = plt.subplots(1, 2, figsize=(8.4, 3.4), gridspec_kw=dict(width_ratios=[1.0, 1.25]))
    a = ax[0]; a.set_xlim(0, 10); a.set_ylim(-5, 3.4); a.axis("off"); a.set_title("(a) Probe over the anterior fontanelle")
    layers = [("scalp", 0.0, -0.8), ("fontanelle", -0.8, -1.2), ("csf", -1.2, -1.6), ("sinus", -1.6, -2.8), ("brain", -2.8, -5.0)]
    for n, y1, y2 in layers:
        a.add_patch(Rectangle((0.5, y2), 9, y1 - y2, color=LAYER_COL[n], ec="none"))
        a.text(9.4, (y1 + y2) / 2, {"sinus": "sup. sagittal sinus", "csf": "CSF"}.get(n, n), va="center", ha="right", fontsize=7)
    a.add_patch(Rectangle((2.6, 0.0), 4.8, 0.5, color="#5d6d7e")); a.text(5.0, 0.25, "stand-off pad + reference absorber", ha="center", va="center", fontsize=6, color="w")
    a.add_patch(Rectangle((3.3, 0.5), 3.4, 0.9, color="#2c3e50")); a.text(5.0, 0.95, "3-MHz transducer", ha="center", va="center", fontsize=7, color="w")
    for x in (1.7, 8.3):
        a.add_patch(Rectangle((x - 0.6, 0.5), 1.2, 0.9, color="#c0392b")); a.text(x, 0.95, "NIR", ha="center", va="center", fontsize=7, color="w")
        a.annotate("", xy=(x + (1.4 if x < 5 else -1.4), -1.7), xytext=(x, 0.5), arrowprops=dict(arrowstyle="->", color="#c0392b", lw=1.2))
    a.annotate("", xy=(4.4, 0.5), xytext=(4.4, -1.6), arrowprops=dict(arrowstyle="->", color="#1f618d", lw=1.5))
    a.text(4.6, -0.75, "PA wave (phonons)", fontsize=6.5, color="#1f618d")
    a.annotate("", xy=(5.6, -4.6), xytext=(5.6, 0.5), arrowprops=dict(arrowstyle="<->", color="#117a65", lw=1.0, ls="--"))
    a.text(5.8, -3.9, "pulse-echo\n(speed of sound)", fontsize=6.5, color="#117a65")
    a.text(0.5, 3.0, "photons in: 4 wavelengths, time-multiplexed", fontsize=7, color="#c0392b")
    a.text(0.5, 2.3, "phonons out: depth-gated PA + echo shift", fontsize=7, color="#1f618d")
    a.text(0.5, 1.7, "thermistor at the pad-skin interface", fontsize=7, color="#5d6d7e")
    b = ax[1]; b.set_xlim(0, 10); b.set_ylim(0, 6.2); b.axis("off"); b.set_title("(b) Joint estimation chain")
    inputs = [(4.7, "depth-gated PA amplitudes\nscalp gate + sinus gate, 4 λ", "#fadbd8"),
              (3.1, "differential echo shifts\nsuperficial / deep segment", "#d4efdf"),
              (1.5, "reference absorber (gain g)\nthermistor (scalp T)", "#d6eaf6")]
    for y, t, c in inputs:
        b.add_patch(FancyBboxPatch((0.2, y), 4.0, 1.25, boxstyle="round,pad=0.05", fc=c, ec="#555"))
        b.text(2.2, y + 0.62, t, ha="center", va="center", fontsize=6.5)
        b.annotate("", xy=(5.0, 4.0), xytext=(4.2, y + 0.62), arrowprops=dict(arrowstyle="->", color="#555"))
    b.add_patch(FancyBboxPatch((5.0, 2.6), 4.8, 3.0, boxstyle="round,pad=0.05", fc="#fcf3cf", ec="#555"))
    b.text(7.4, 4.1, "joint EKF\nx = [sO2v, f_v, T_b, sO2s, HbT_s, T_s, g]\nnominal Monte-Carlo fluence model\nGrüneisen + speed-of-sound thermometry\nχ² innovation test, coefficient uncertainty", ha="center", va="center", fontsize=6.3)
    b.add_patch(FancyBboxPatch((5.0, 0.3), 4.8, 1.7, boxstyle="round,pad=0.05", fc="#eaeded", ec="#555"))
    b.text(7.4, 1.15, "outputs every frame\ncerebral venous sO2, brain T, brain-scalp ΔT,\ncoupling quality, 95 % intervals, alarms", ha="center", va="center", fontsize=6.3)
    b.annotate("", xy=(7.4, 2.0), xytext=(7.4, 2.6), arrowprops=dict(arrowstyle="->", color="#555"))
    fig.tight_layout(); save(fig, "fig0_system_schematic.png")


# ------------------------------------------------------------------ Fig 1 optical design
def fig1():
    E1a = pd.read_csv(os.path.join(RES, "E1a_fluence_vs_depth.csv")); prof = np.load(os.path.join(RES, "E1a_fluence_profiles.npz"))
    E1b = pd.read_csv(os.path.join(RES, "E1b_source_snr.csv")); E1c = pd.read_csv(os.path.join(RES, "E1c_wavelength_selection.csv"))
    E1cb = pd.read_csv(os.path.join(RES, "E1c_crlb_vs_so2_bone.csv"))
    fig, ax = plt.subplots(2, 2, figsize=(7.2, 5.4))
    a = ax[0, 0]; z = prof["z"]
    for n, z1, z2 in (("scalp", 0, 0.2), ("fontanelle", 0.2, 0.3), ("csf", 0.3, 0.4), ("sinus", 0.4, 0.7), ("brain", 0.7, 2.5)):
        a.axvspan(z1 * 10, z2 * 10, color=LAYER_COL[n], alpha=0.5, lw=0)
    for lam in (690, 750, 800, 850, 900, 940):
        a.semilogy(z * 10, prof[f"phi_{lam}_b0.0"], label=f"{lam} nm")
    a.set_xlim(0, 25); a.set_ylim(1e-4, 10); a.set_xlabel("depth (mm)"); a.set_ylabel("fluence per incident fluence (cm$^{-2}$)")
    a.set_title("(a) Fluence vs depth, fontanelle, beam radius 5 mm"); a.legend(ncol=2)
    a = ax[0, 1]
    for arad in (0.3, 0.5, 0.75):
        d = E1a[(E1a.wavelength_nm == 800) & (E1a.beam_radius_cm == arad)]
        a.plot(d.bone_cm * 10, d.phi_sinus_top, "o-", label=f"beam radius {arad*10:.1f} mm")
    a.set_xlabel("bone thickness under the probe (mm)"); a.set_ylabel("fluence at the sinus surface (cm$^{-2}$)")
    a.set_title("(b) Sinus fluence vs ossification, 800 nm"); a.legend(); a.set_yscale("log")
    a = ax[1, 0]
    d = E1b[(E1b.frame_s == 10) & (E1b.wavelength_nm == 800)]
    srcs = ["LED array", "Laser-diode stack", "Compact laser"]; tds = list(common.TRANSDUCERS)
    w = 0.25
    for i, t in enumerate(tds):
        v = [d[(d.source == s) & (d.transducer == t)].SNR_sinus.values[0] for s in srcs]
        a.bar(np.arange(3) + (i - 1) * w, v, w, label=t)
    a.set_xticks(range(3)); a.set_xticklabels(srcs); a.set_yscale("log"); a.axhline(10, color="k", ls="--", lw=0.8)
    a.set_ylabel("sinus-gate SNR, 10-s frame"); a.set_title("(c) Source/transducer SNR at 0.1 W/cm² thermal cap"); a.legend()
    a = ax[1, 1]
    chosen = "/".join(map(str, common.DEFAULT_LAMS))
    best = pd.concat([E1c[E1c.K == k].head(3) for k in (2, 3, 4)] + [E1c[E1c.wavelengths == chosen]])
    a.barh(range(len(best)), best.crlb_so2 * 100, color=["#95a5a6"] * 3 + ["#5dade2"] * 3 + ["#c0392b"] * 3 + ["#922b21"])
    a.set_yticks(range(len(best))); a.set_yticklabels(list(best.wavelengths[:-1]) + [chosen + " (used)"]); a.invert_yaxis()
    a.set_xlabel("CRLB of sO2 (% abs.), bedside, 10-s frame"); a.set_title("(d) Wavelength-set selection (best 3 per K)")
    save(fig, "fig1_optical_design.png")
    # supplementary: CRLB vs sO2 and bone
    fig, a = plt.subplots(figsize=(3.5, 2.6))
    for bone in sorted(E1cb.bone_cm.unique()):
        d = E1cb[E1cb.bone_cm == bone]; a.plot(d.so2 * 100, d.crlb_so2 * 100, "o-", label=f"bone {bone*10:.0f} mm")
    a.set_xlabel("venous sO2 (%)"); a.set_ylabel("CRLB sO2 (% abs.)"); a.legend(); a.set_title("Fisher bound vs saturation and ossification")
    save(fig, "figS1_crlb_vs_so2_bone.png")


# ------------------------------------------------------------------ Fig 2 acoustic design
def fig2():
    E2 = pd.read_csv(os.path.join(RES, "E2_acoustic_design.csv")); E2e = pd.read_csv(os.path.join(RES, "E2_echo_shift_precision.csv"))
    fig, ax = plt.subplots(2, 2, figsize=(7.2, 5.2))
    a = ax[0, 0]
    for bone in (0.0, 0.1, 0.2, 0.3):
        d = E2[(E2.pulse_ns == 8) & (E2.bone_cm == bone)]; a.plot(d.fc_MHz, d.SNR_sinus, "o-", label=f"bone {bone*10:.0f} mm")
    a.set_xlabel("transducer centre frequency (MHz)"); a.set_ylabel("sinus-gate SNR (10-s frame, laser)"); a.set_yscale("log"); a.legend()
    a.set_title("(a) SNR vs centre frequency and ossification")
    a = ax[0, 1]
    d = E2[(E2.pulse_ns == 8) & (E2.bone_cm == 0.0)]
    a.plot(d.fc_MHz, d.crosstalk_scalp_into_sinus * 100, "s-", color="#c0392b"); a.set_xlabel("centre frequency (MHz)")
    a.set_ylabel("scalp leakage into sinus gate (%)"); a.set_title("(b) Depth selectivity"); a.set_ylim(0, 12)
    a2 = a.twinx(); a2.plot(d.fc_MHz, 1545.0 / (2 * 0.7 * d.fc_MHz * 1e6) * 1e3, "^--", color="#2980b9"); a2.set_ylabel("axial resolution (mm)", color="#2980b9"); a2.set_ylim(0, 1.3)
    a = ax[1, 0]
    for pulse in (8, 80, 150, 300):
        d = E2[(E2.pulse_ns == pulse) & (E2.bone_cm == 0.0)]; a.plot(d.fc_MHz, d.A_sinus, "o-", label=f"{pulse} ns pulse")
    a.set_xlabel("centre frequency (MHz)"); a.set_ylabel("sinus-gate amplitude (Pa, 10 mJ/cm²)"); a.legend(); a.set_title("(c) Optical pulse width (LED/LD stretch) vs bandwidth")
    a = ax[1, 1]
    for snr in sorted(E2e.echo_snr_db.unique()):
        d = E2e[E2e.echo_snr_db == snr]; a.plot(d.n_avg, d.std_T_deep_C * 1000, "o-", label=f"echo SNR {snr:.0f} dB")
    a.set_xscale("log"); a.set_yscale("log"); a.set_xlabel("pulse-echo lines averaged per frame"); a.set_ylabel("echo-shift temperature noise (mK)")
    a.legend(); a.set_title("(d) Speed-of-sound thermometry precision")
    save(fig, "fig2_acoustic_design.png")


# ------------------------------------------------------------------ Fig 3 static accuracy
def fig3():
    E3 = pd.read_csv(os.path.join(RES, "E3_static_accuracy_per_state.csv"))
    fig, ax = plt.subplots(2, 2, figsize=(7.2, 5.6))
    a = ax[0, 0]
    for m in ("NIRS rScO2", "PA linear unmixing", "PA fluence-compensated", "Proposed EKF"):
        d = E3[(E3.quantity == "sO2") & (E3.method == m)]; a.scatter(d.truth, d.est, s=12, alpha=0.7, label=m, color=C[m])
    a.plot([35, 95], [35, 95], "k--", lw=0.8); a.set_xlabel("true venous sO2 (%)"); a.set_ylabel("estimated (%)"); a.legend(); a.set_title("(a) Oxygenation, 16 subjects × 4 states")
    a = ax[0, 1]
    for m in ("NIRS rScO2", "PA fluence-compensated", "Proposed EKF"):
        d = E3[(E3.quantity == "sO2") & (E3.method == m)]; diff = d.est - d.truth
        a.scatter((d.est + d.truth) / 2, diff, s=12, alpha=0.7, color=C[m], label=f"{m}: {diff.mean():+.1f} ± {1.96*diff.std():.1f}")
        a.axhline(diff.mean(), color=C[m], lw=0.8); a.axhline(diff.mean() + 1.96 * diff.std(), color=C[m], lw=0.6, ls=":"); a.axhline(diff.mean() - 1.96 * diff.std(), color=C[m], lw=0.6, ls=":")
    a.set_xlabel("mean of estimate and truth (%)"); a.set_ylabel("estimate − truth (% abs.)"); a.legend(); a.set_title("(b) Bland–Altman, sO2")
    a = ax[1, 0]
    for m in ("Rectal proxy", "Echo shift only", "PA amplitude (800 nm)", "Proposed EKF"):
        d = E3[(E3.quantity == "T") & (E3.method == m)]; a.scatter(d.truth, d.est, s=12, alpha=0.7, label=m, color=C[m])
    a.plot([32, 39], [32, 39], "k--", lw=0.8); a.set_xlabel("true brain (sinus blood) temperature (°C)"); a.set_ylabel("estimated (°C)"); a.set_ylim(28, 42); a.legend(); a.set_title("(c) Temperature")
    a = ax[1, 1]
    for m in ("Rectal proxy", "Echo shift only", "Proposed EKF"):
        d = E3[(E3.quantity == "T") & (E3.method == m)]; diff = d.est - d.truth
        a.scatter((d.est + d.truth) / 2, diff, s=12, alpha=0.7, color=C[m], label=f"{m}: {diff.mean():+.2f} ± {1.96*diff.std():.2f} °C")
        a.axhline(diff.mean(), color=C[m], lw=0.8)
    a.set_xlabel("mean of estimate and truth (°C)"); a.set_ylabel("estimate − truth (°C)"); a.legend(); a.set_title("(d) Bland–Altman, temperature")
    save(fig, "fig3_static_accuracy.png")


# ------------------------------------------------------------------ Fig 4 traces
def fig4():
    s1 = np.load(os.path.join(RES, "E4_trace_S1_bedside_seed10.npz"), allow_pickle=True)
    s2 = np.load(os.path.join(RES, "E4_trace_S2_bedside_seed10.npz"), allow_pickle=True)
    fig, ax = plt.subplots(4, 1, figsize=(7.2, 8.0), sharex=False)
    t = s1["t"] / 3600
    a = ax[0]
    a.plot(t, s1["truth_so2"] * 100, "k", lw=1.2, label="truth (venous sO2)")
    a.fill_between(t, (s1["so2_Proposed EKF"] - 1.96 * s1["sd_so2"]) * 100, (s1["so2_Proposed EKF"] + 1.96 * s1["sd_so2"]) * 100, color=C["Proposed EKF"], alpha=0.25, lw=0)
    a.plot(t, s1["so2_Proposed EKF"] * 100, color=C["Proposed EKF"], lw=1, label="proposed EKF (95 % band)")
    a.plot(t, s1["so2_NIRS rScO2"] * 100, color=C["NIRS rScO2"], lw=0.6, alpha=0.8, label="NIRS rScO2")
    a.plot(t, s1["so2_PA linear unmixing"] * 100, color=C["PA linear unmixing"], lw=0.6, alpha=0.8, label="PA linear unmixing")
    for ev in s1["events"]:
        a.axvspan(ev[0] / 3600, ev[1] / 3600, color="#f9e79f", alpha=0.6, lw=0)
    a.set_ylabel("sO2 (%)"); a.legend(ncol=4, loc="lower left"); a.set_title("(a) S1 therapeutic hypothermia, bedside device: oxygenation")
    a = ax[1]
    a.plot(t, s1["truth_Tb"], "k", lw=1.2, label="true brain T")
    a.fill_between(t, s1["T_Proposed EKF"] - 1.96 * s1["sd_T"], s1["T_Proposed EKF"] + 1.96 * s1["sd_T"], color=C["Proposed EKF"], alpha=0.25, lw=0)
    a.plot(t, s1["T_Proposed EKF"], color=C["Proposed EKF"], lw=1, label="proposed EKF")
    a.plot(t, s1["T_Rectal proxy"], color=C["Rectal proxy"], lw=0.6, label="rectal probe")
    a.plot(t, s1["T_Echo shift only"], color=C["Echo shift only"], lw=0.6, label="echo shift only")
    a.plot(t, s1["T_PA amplitude (800 nm)"], color=C["PA amplitude (800 nm)"], lw=0.6, label="PA amplitude only")
    a.set_ylim(31, 40); a.set_ylabel("temperature (°C)"); a.legend(ncol=5, loc="lower right"); a.set_title("(b) S1: brain temperature (cooling, maintenance, rewarming, seizure-like episode at 6.5 h)")
    a = ax[2]
    a.plot(t, s1["truth_Tb"] - s1["truth_Ts"], "k", lw=1.2, label="true brain − scalp ΔT")
    a.plot(t, s1["T_Proposed EKF"] - s1["Ts_est"], color=C["Proposed EKF"], lw=1, label="estimated ΔT")
    a2 = a.twinx(); a2.plot(t, s1["truth_g"], color="#7f8c8d", lw=0.8, label="true coupling g"); a2.plot(t, s1["g_est"], color="#8e44ad", lw=0.8, ls="--", label="estimated g"); a2.set_ylabel("coupling gain")
    a.set_ylabel("ΔT brain−scalp (°C)"); a.set_xlabel("time (h)"); a.legend(loc="upper left"); a2.legend(loc="upper right"); a.set_title("(c) S1: brain–scalp gradient and probe coupling (motion events)")
    a = ax[3]; t2 = s2["t"] / 60
    a.plot(t2, s2["truth_so2"] * 100, "k", lw=1.2, label="truth")
    a.plot(t2, s2["so2_Proposed EKF"] * 100, color=C["Proposed EKF"], lw=1, label="proposed EKF (2-s frames)")
    a.plot(t2, s2["so2_NIRS rScO2"] * 100, color=C["NIRS rScO2"], lw=0.6, alpha=0.8, label="NIRS rScO2")
    for ev in s2["events"]:
        a.axvspan(ev[0] / 60, ev[1] / 60, color="#f9e79f", alpha=0.6, lw=0)
    a.set_xlabel("time (min)"); a.set_ylabel("sO2 (%)"); a.legend(ncol=3, loc="lower left"); a.set_title("(d) S2 intermittent hypoxaemia (preterm pattern), bedside device")
    fig.tight_layout(); save(fig, "fig4_closed_traces.png")


# ------------------------------------------------------------------ Fig 5 benchmark
def fig5():
    E4 = pd.read_csv(os.path.join(RES, "E4_dynamic_per_seed.csv"))
    fig, ax = plt.subplots(2, 2, figsize=(7.2, 5.6))
    panels = [("S1-bedside", "sO2", "(a) S1 bedside: sO2 RMSE (% abs.)"), ("S1-bedside", "T", "(b) S1 bedside: brain-T RMSE (°C)"),
              ("S2-bedside", "sO2", "(c) S2 bedside: sO2 RMSE (% abs.)"), ("S1-wearable", "T", "(d) S1 wearable (LD + CMUT patch): brain-T RMSE (°C)")]
    for a, (sc, q, title) in zip(ax.ravel(), panels):
        d = E4[(E4.scenario == sc) & (E4.quantity == q)]
        g = d.groupby("method").rmse.agg(["mean", "std"]).reindex([m for m in (common.METHODS_SO2 if q == "sO2" else common.METHODS_T) if m in d.method.unique()])
        a.barh(range(len(g)), g["mean"], xerr=g["std"], color=[C.get(m, "#999") for m in g.index], capsize=2)
        a.set_yticks(range(len(g))); a.set_yticklabels(g.index); a.invert_yaxis(); a.set_title(title)
        if q == "T":
            a.set_xscale("log")
    fig.tight_layout(); save(fig, "fig5_benchmark.png")


# ------------------------------------------------------------------ Fig 6 sensitivity
def fig6():
    E5 = pd.read_csv(os.path.join(RES, "E5_sensitivity_per_seed.csv"))
    settings = [("bone", "bone thickness (mm)", 10.0), ("noise_scale", "noise power ×", 1.0), ("kg_bias", "true/assumed Grüneisen slope", 1.0),
                ("kc_bias", "true/assumed dc/dT", 1.0), ("fill", "sinus fill factor", 1.0)]
    fig, ax = plt.subplots(2, 5, figsize=(9.5, 4.2))
    for j, (st, lab, sc) in enumerate(settings):
        for i, q in enumerate(("sO2", "T")):
            a = ax[i, j]
            d = E5[(E5.setting == st) & (E5.quantity == q)]
            meths = ["Proposed EKF", "PA fluence-compensated", "NIRS rScO2"] if q == "sO2" else ["Proposed EKF", "Echo shift only", "Rectal proxy"]
            for m in meths:
                g = d[d.method == m].groupby("value").rmse.agg(["mean", "std"])
                if len(g):
                    a.errorbar(g.index * sc, g["mean"], g["std"], fmt="o-", ms=3, capsize=2, label=m, color=C[m])
            if st == "noise_scale":
                a.set_xscale("log")
            a.set_xlabel(lab); a.set_ylabel("RMSE " + ("sO2 (% abs.)" if q == "sO2" else "T (°C)"))
            if j == 0:
                a.legend(fontsize=6)
    fig.tight_layout(); save(fig, "fig6_sensitivity.png")


# ------------------------------------------------------------------ Fig 7 thermal safety
def fig7():
    E6 = pd.read_csv(os.path.join(RES, "E6_thermal_safety.csv"))
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.8))
    a = ax[0]
    for contact in ("insulated patch", "open probe"):
        for q in (0.0, 0.02):
            d = E6[(E6.contact == contact) & (E6.q_elec_Wcm2 == q) & (E6.T_core == 37.0)]
            a.plot(d.I_avg_Wcm2, d.dT_skin_20min, "o-" if q == 0 else "s--", label=f"{contact}, electronics {q*1e3:.0f} mW/cm²")
    a.axhline(1.0, color="k", ls=":", lw=0.8); a.axvline(0.1, color="#c0392b", ls=":", lw=0.8)
    a.set_xlabel("average NIR irradiance (W/cm²)"); a.set_ylabel("skin ΔT after 20 min (°C)"); a.legend(fontsize=6); a.set_title("(a) Scalp heating (Pennes model)")
    a = ax[1]
    for contact in ("insulated patch", "open probe"):
        d = E6[(E6.contact == contact) & (E6.q_elec_Wcm2 == 0.0) & (E6.T_core == 33.5)]
        a.plot(d.I_avg_Wcm2, d.dT_cortex_20min, "o-", label=f"{contact}, cooled infant")
    a.set_xlabel("average NIR irradiance (W/cm²)"); a.set_ylabel("cortex ΔT after 20 min (°C)"); a.legend(fontsize=6); a.set_title("(b) Cortical heating")
    fig.tight_layout(); save(fig, "fig7_thermal_safety.png")


if __name__ == "__main__":
    which = sys.argv[1:] or ["0", "1", "2", "3", "4", "5", "6", "7"]
    for w in which:
        try:
            globals()[f"fig{w}"]()
        except FileNotFoundError as e:
            print("skip fig", w, e)
