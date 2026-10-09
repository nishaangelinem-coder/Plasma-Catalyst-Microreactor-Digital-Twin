"""
make_figures.py -- generate every figure, table and number used by the manuscript.

Inputs : the model modules, results/ngspice_results.json (if present),
         paper/data/cadence_*.csv (if present, produced by collect_cadence_results.py)
Outputs: paper/figures/*.pdf, paper/data/*.csv, paper/numbers.tex (LaTeX macros),
         results/summary.json
"""
from __future__ import annotations
import json, os, sys, pathlib
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from dataclasses import replace

sys.path.insert(0, os.path.dirname(__file__))
from ring_model import RingParams, calibrate_to_measurement, s_params, Z0
from oscillator_design import (AmpDesign, auto_phase_trim, loop_gain, loop_gain_summary, find_oscillation_point,
                               mode_selection, startup_time, loop_noise_factor, signal_power_in_resonator,
                               loss_vs_interface, loop_loss_budget, pierce_analysis, default_design)
from phase_noise import oscillator_phase_noise, leeson, leeson_terms, fom, allan_deviation_from_L, REFERENCES, scaled_pn
from monte_carlo import run_monte_carlo, temperature_sweep

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIG = ROOT / "paper" / "figures"; FIG.mkdir(parents=True, exist_ok=True)
DAT = ROOT / "paper" / "data"; DAT.mkdir(parents=True, exist_ok=True)
RES = ROOT / "results"; RES.mkdir(exist_ok=True)

# ---- validated categorical palette (dataviz validator: light surface, all checks pass) ----
C = dict(blue="#0072B2", verm="#D55E00", green="#009E73", purple="#CC79A7", orange="#E69F00", sky="#56B4E9", ink="#222222", mute="#777777")
plt.rcParams.update({
    "font.size": 8, "font.family": "serif", "axes.labelsize": 8, "axes.titlesize": 8, "legend.fontsize": 7,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "lines.linewidth": 1.2, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "grid.color": "#dddddd", "grid.linewidth": 0.5,
    "legend.frameon": False, "figure.dpi": 150, "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
    "pdf.fonttype": 42,
})
W1, W2 = 3.45, 7.1   # IEEE single / double column widths (in)


def savefig(fig, name):
    fig.savefig(FIG / f"{name}.pdf"); fig.savefig(FIG / f"{name}.png", dpi=200); plt.close(fig)
    print("  wrote", name)


def load_json(path):
    return json.loads(path.read_text()) if path.exists() else None


# ==========================================================================
def main():
    numbers = {}
    p, amp_ideal = default_design()
    ng = load_json(RES / "ngspice_results.json")
    cad = load_json(RES / "cadence_results.json")

    # ---- calibrate the implementation factor of the behavioural amplifier model to the transistor-level run ----
    s_ideal = loop_gain_summary(p, amp_ideal)
    k_impl = 1.0
    if ng and ng.get("openloop", {}).get("T0_dB") is not None:
        k_impl = 10 ** ((ng["openloop"]["T0_dB"] - s_ideal["T0_dB"]) / 20)
    amp, trim = auto_phase_trim(p, replace(amp_ideal, k_impl=k_impl))
    s = loop_gain_summary(p, amp)
    nf_model = loop_noise_factor(p, amp)
    F_used_dB = nf_model["F_dB"]
    if ng and ng.get("noise", {}).get("F_dB") is not None:
        F_used_dB = ng["noise"]["F_dB"]
    ps = signal_power_in_resonator(p, amp)
    if ng and ng.get("transient", {}).get("P_Rm_W"):
        ps = dict(P_W=ng["transient"]["P_Rm_W"], P_dBm=ng["transient"]["P_Rm_dBm"], V_port1=ng["transient"]["v_port1_peak_ss"])
    m = p.mbvd()
    a, t, k2 = p.round_trip()
    numbers.update(dict(
        f0MHz=p.f0 / 1e6, Qi=p.Qi, Qc=p.Qc, QL=p.QL, Qe=s["Qe"], ILmeas=p.IL_meas_dB, Tdrop=-m["Tdrop_dB"], ILidt=p.IL_meas_dB + m["Tdrop_dB"],
        Rm=m["Rm"], LmH=m["Lm"] * 1e3, CmaF=m["Cm"] * 1e18, C0pF=p.C0 * 1e12, R0k=p.R0 / 1e3, Rs=p.Rs, keff=m["keff2"] * 1e6,
        FSRMHz=p.fsr / 1e6, radiusum=p.radius * 1e6, taurtns=p.tau_rt * 1e9, art=a, tcp=t, kappa2=k2 * 100, Ga0mS=p.Ga0 * 1e3, Nidt=p.N_idt,
        Lin=amp.L_in * 1e9, Lt=amp.L_t * 1e9, QLind=amp.Q_Lin, I1=amp.I1 * 1e3, I2=amp.I2 * 1e3, I4=amp.I4 * 1e3,
        Lttwo=amp.L_t2 * 1e9, Rptanktwo=amp.Rp_tank2, Pdc=amp.P_dc * 1e3, Idc=amp.P_dc / amp.vdd * 1e3, vdd=amp.vdd, gm1=amp.gm1 * 1e3, gm2=amp.gm2 * 1e3, gm4=amp.gm4 * 1e3,
        ZTideal=s_ideal["ZT0"], ZTeff=s["ZT0"], T0ideal=s_ideal["T0_dB"], T0=s["T0_dB"], kimpl=20 * np.log10(k_impl), trim=amp.phase_trim_deg,
        Rext=s["Rext"], Fmodel=nf_model["F_dB"], Fused=F_used_dB, Ps=ps["P_dBm"], Vport1=ps["V_port1"],
    ))
    numbers["Rptank"] = amp.Rp_tank
    numbers["taug"] = 2 * p.QL / p.w0 * 1e6
    numbers["Zin"] = amp.Zin_diff
    numbers["maz"] = p.m_az
    for k, v in nf_model["parts_rel"].items():
        numbers[f"Fpart{k.replace('_', '')}"] = 10 * np.log10(v) if v > 0 else -99
    lb = loop_loss_budget(p, amp); numbers.update(loopLoss=lb["loop_loss_dB"], loopLossNoL=lb["loop_loss_noL_dB"])
    pz = pierce_analysis(p); numbers.update(gmcrit=pz["gm_crit_mS"], gm3x=pz["gm_3x_mS"], P3x=pz["P_3x_mW"], window=pz["inductive_window_Hz"])
    st = startup_time(p, amp); numbers.update(tauStart=st["tau_s"] * 1e6, tStart=st["t_startup_s"] * 1e6)

    # ======================= Fig: resonator response ==========================
    print("fig resonator")
    f_w = np.linspace(p.f0 - 30e6, p.f0 + 30e6, 240001)
    S_comb = s_params(p, f_w, comb=True, spurs=True)
    S_mbvd = s_params(p, f_w, comb=False, spurs=True)
    f_z = np.linspace(p.f0 - 300e3, p.f0 + 300e3, 6001)
    S_z = s_params(p, f_z, comb=False, spurs=False)
    fig, ax = plt.subplots(1, 2, figsize=(W2, 2.3))
    ax[0].plot((f_w - p.f0) / 1e6, 20 * np.log10(abs(S_comb[:, 1, 0])), color=C["blue"], label="mBVD + delay (comb)")
    ax[0].plot((f_w - p.f0) / 1e6, 20 * np.log10(abs(S_mbvd[:, 1, 0])), color=C["verm"], ls="--", label="single-branch mBVD + spurs")
    ax[0].plot([0], [-p.IL_meas_dB], "o", color=C["ink"], ms=4, label="measured, Ji et al. 2026")
    ax[0].set(xlabel="$f - f_0$ (MHz)", ylabel="$|S_{21}|$ (dB, 50 $\\Omega$)", ylim=(-75, -20)); ax[0].legend(loc="lower left")
    ax[0].text(0.02, 0.95, "(a)", transform=ax[0].transAxes, va="top")
    ax[1].plot((f_z - p.f0) / 1e3, 20 * np.log10(abs(S_z[:, 1, 0])), color=C["blue"])
    ax2 = ax[1].twinx(); ax2.plot((f_z - p.f0) / 1e3, np.degrees(np.angle(S_z[:, 1, 0])), color=C["green"], ls=":")
    ax2.set_ylabel("phase (deg)", color=C["green"]); ax2.grid(False); ax2.spines["top"].set_visible(False)
    ax[1].set(xlabel="$f - f_0$ (kHz)", ylabel="$|S_{21}|$ (dB)")
    ax[1].annotate(f"$Q_L$ = {p.QL:.0f}\nBW$_{{3dB}}$ = {p.f0/p.QL/1e3:.1f} kHz", xy=(0.03, 0.08), xycoords="axes fraction")
    ax[1].text(0.02, 0.95, "(b)", transform=ax[1].transAxes, va="top")
    savefig(fig, "fig_resonator")
    np.savetxt(DAT / "resonator_s21_comb.csv", np.c_[f_w, 20 * np.log10(abs(S_comb[:, 1, 0])), 20 * np.log10(abs(S_mbvd[:, 1, 0]))][::20],
               delimiter=",", header="f_Hz,S21_comb_dB,S21_mbvd_dB", comments="")

    # ======================= Fig: IL recovery by impedance co-design =================
    print("fig IL recovery")
    R = np.logspace(1, 4, 61)
    fig, ax = plt.subplots(figsize=(W1, 2.3))
    ax.plot(R, loss_vs_interface(p, R), color=C["verm"], label="no inductor")
    for Q, col, ls in [(5, C["sky"], ":"), (8, C["blue"], "-"), (15, C["green"], "--"), (30, C["purple"], "-.")]:
        ax.plot(R, loss_vs_interface(p, R, Lres=amp.L_in, QL=Q), color=col, ls=ls, label=f"$C_0$ resonated, $Q_L$ = {Q}")
    ax.axhline(-p.IL_meas_dB, color=C["mute"], lw=0.8); ax.text(12, -p.IL_meas_dB + 0.6, "50-$\\Omega$ measurement", color=C["mute"], fontsize=6.5)
    ax.axhline(m["Tdrop_dB"], color=C["ink"], lw=0.8, ls="--"); ax.text(12, m["Tdrop_dB"] + 0.6, "ring drop-port limit", fontsize=6.5)
    ax.set(xscale="log", xlabel="symmetric termination resistance $R$ ($\\Omega$)", ylabel="transducer gain at $f_0$ (dB)", ylim=(-46, -10))
    ax.legend(loc="lower left", ncol=1)
    savefig(fig, "fig_il_recovery")
    best = {Q: float(loss_vs_interface(p, R, Lres=amp.L_in, QL=Q).max()) for Q in (5, 8, 15, 30)}
    numbers.update(ILbestQ8=-best[8], ILbestQ30=-best[30], ILrecQ8=p.IL_meas_dB + best[8])

    # ======================= Fig: loop gain, narrow + comb ============================
    print("fig loop gain")
    f_n = np.linspace(p.f0 - 400e3, p.f0 + 400e3, 8001)
    T_n = loop_gain(p, amp, f_n)
    fig, ax = plt.subplots(1, 2, figsize=(W2, 2.4)); fig.subplots_adjust(wspace=0.55)
    ax[0].plot((f_n - p.f0) / 1e3, 20 * np.log10(abs(T_n)), color=C["blue"], label="model (calibrated)")
    axp = ax[0].twinx(); axp.plot((f_n - p.f0) / 1e3, np.degrees(np.angle(T_n)), color=C["green"], ls=":"); axp.set_ylim(-180, 180)
    axp.set_ylabel("loop phase (deg)", color=C["green"]); axp.grid(False); axp.spines["top"].set_visible(False)
    if ng:
        d = np.loadtxt(RES / "ngspice" / "openloop_ac.txt")
        ax[0].plot((d[:, 0] - p.f0) / 1e3, 20 * np.log10(d[:, 1]), color=C["verm"], ls="--", label="ngspice, 180-nm BSIM3")
        axp.plot((d[:, 0] - p.f0) / 1e3, d[:, 3], color=C["orange"], ls="--", lw=0.8)
    if cad and "stb_loopgain" in cad:
        dd = np.array(cad["stb_loopgain"]); ax[0].plot((dd[:, 0] - p.f0) / 1e3, dd[:, 1], color=C["purple"], ls="-.", label="Spectre stb")
    ymax = 20 * np.log10(abs(T_n)).max() + 5
    ax[0].axhline(0, color=C["mute"], lw=0.8); ax[0].set(xlabel="$f - f_0$ (kHz)", ylabel="$|T|$ (dB)", ylim=(-30, ymax)); ax[0].legend(loc="lower left")
    ax[0].text(0.02, 0.95, "(a)", transform=ax[0].transAxes, va="top")
    f_c, T_c, rows = mode_selection(p, amp)
    ax[1].plot((f_c - p.f0) / 1e6, 20 * np.log10(abs(T_c)), color=C["blue"], lw=0.8)
    ok = [r for r in rows if r["phase_ok"]]; bad = [r for r in rows if not r["phase_ok"] and r["T_dB"] > -20]
    ax[1].plot([(r["f"] - p.f0) / 1e6 for r in ok], [r["T_dB"] for r in ok], "o", color=C["verm"], ms=4, label="phase condition met")
    ax[1].plot([(r["f"] - p.f0) / 1e6 for r in bad], [r["T_dB"] for r in bad], "x", color=C["mute"], ms=4, label="phase condition fails ($\\pm 180^\\circ$)")
    ax[1].axhline(0, color=C["mute"], lw=0.8); ax[1].set(xlabel="$f - f_0$ (MHz)", ylabel="$|T|$ at comb modes (dB)", ylim=(-40, ymax), xlim=(-45, 45))
    ax[1].legend(loc="lower center"); ax[1].text(0.02, 0.95, "(b)", transform=ax[1].transAxes, va="top")
    savefig(fig, "fig_loopgain")
    comp = sorted([r for r in ok if r["k"] != 0], key=lambda r: r["margin_dB"])
    numbers.update(modeMargin=comp[0]["margin_dB"] if comp else 99, modeCompK=comp[0]["k"] if comp else 0,
                   modeCompMHz=(comp[0]["f"] - p.f0) / 1e6 if comp else 0)
    with open(DAT / "mode_table.csv", "w") as fh:
        fh.write("k,f_MHz,T_dB,phase_deg,margin_dB,phase_ok\n")
        for r in rows:
            if abs(r["k"]) <= 6:
                fh.write(f"{r['k']},{r['f']/1e6:.4f},{r['T_dB']:.2f},{r['phase_deg']:.1f},{r['margin_dB']:.2f},{int(r['phase_ok'])}\n")

    # ======================= Fig: mode-selection margin vs IDT pairs ==================
    print("fig mode margin vs N")
    Ns = np.arange(10, 121, 5); marg = []
    for N in Ns:
        pp = replace(p, N_idt=int(N))
        _, _, rr = mode_selection(pp, amp, span=40e6, n=400001)
        cc = [r for r in rr if r["phase_ok"] and r["k"] != 0]
        marg.append(min(r["margin_dB"] for r in cc) if cc else 40)
    marg = np.array(marg)
    fig, ax = plt.subplots(figsize=(W1, 2.1))
    ax.plot(Ns, marg, color=C["blue"], marker="o", ms=3)
    Nopt = p.f0 / (2 * p.fsr)
    ax.axvline(Nopt, color=C["verm"], ls="--", lw=0.8); ax.text(Nopt + 1, marg.max() * 0.9, f"$N = f_0/(2\\,\\mathrm{{FSR}})$ = {Nopt:.0f}", color=C["verm"], fontsize=6.5)
    ax.axvline(p.N_idt, color=C["mute"], ls=":", lw=0.8); ax.text(p.N_idt + 1, 1.0, "baseline", color=C["mute"], fontsize=6.5)
    ax.set(xlabel="IDT finger pairs $N$", ylabel="gain margin to nearest\nin-phase mode (dB)")
    savefig(fig, "fig_mode_margin")
    np.savetxt(DAT / "mode_margin_vs_N.csv", np.c_[Ns, marg], delimiter=",", header="N_idt,margin_dB", comments="")
    numbers.update(Nopt=Nopt, marginNopt=float(np.interp(Nopt, Ns, marg)), marginBase=float(np.interp(p.N_idt, Ns, marg)))

    # ======================= Fig: start-up (ngspice) ===================================
    if ng and (DAT / "ngspice_startup_envelope.csv").exists():
        print("fig startup")
        env = np.loadtxt(DAT / "ngspice_startup_envelope.csv", delimiter=",", skiprows=1)
        ss = np.loadtxt(DAT / "ngspice_steady_state.csv", delimiter=",", skiprows=1)
        fig, ax = plt.subplots(1, 2, figsize=(W2, 2.2))
        ax[0].plot(env[:, 0] * 1e6, env[:, 1], color=C["blue"])
        tr = ng["transient"]
        ax[0].axvline(tr["t_startup_90"] * 1e6, color=C["verm"], ls="--", lw=0.8)
        ax[0].text(tr["t_startup_90"] * 1e6 + 0.5, 0.05, f"90 % at {tr['t_startup_90']*1e6:.1f} $\\mu$s", color=C["verm"], fontsize=6.5)
        ax[0].set(xlabel="time ($\\mu$s)", ylabel="port-1 envelope (V, diff. peak)"); ax[0].text(0.02, 0.95, "(a)", transform=ax[0].transAxes, va="top")
        tt = ss[:, 0]; sel = tt > tt[-1] - 4e-9
        ax[1].plot((tt[sel] - tt[sel][0]) * 1e9, ss[sel, 1], color=C["blue"], label="$v_{p1}-v_{n1}$")
        axi = ax[1].twinx(); axi.plot((tt[sel] - tt[sel][0]) * 1e9, ss[sel, 2] * 1e3, color=C["green"], ls=":", label="$i_m$")
        axi.set_ylabel("motional current (mA)", color=C["green"]); axi.grid(False); axi.spines["top"].set_visible(False)
        ax[1].set(xlabel="time (ns)", ylabel="port-1 voltage (V)"); ax[1].text(0.02, 0.95, "(b)", transform=ax[1].transAxes, va="top")
        ax[1].annotate(f"$f$ = {tr['f_osc']/1e6:.3f} MHz\nHD2 = {tr['hd2_dBc']:.0f} dBc, HD3 = {tr['hd3_dBc']:.0f} dBc", xy=(0.35, 0.04), xycoords="axes fraction", fontsize=6.5)
        savefig(fig, "fig_startup")
        numbers.update(ngT0=ng["openloop"]["T0_dB"], ngPhase=ng["openloop"]["T0_phase_deg"], ngFosc=tr["f_osc"] / 1e6,
                       ngDf=(tr["f_osc"] - p.f0) / 1e3, ngVp1=tr["v_port1_peak_ss"], ngIm=tr["Im_peak"] * 1e3, ngPrm=tr["P_Rm_dBm"],
                       ngTstart=tr["t_startup_90"] * 1e6, ngHD2=tr["hd2_dBc"], ngHD3=tr["hd3_dBc"], ngTHD=tr["thd_pct"],
                       ngF=ng["noise"].get("F_dB", float("nan")), ngCt=ng["design"]["Ct"] * 1e15, ngCttwo=ng["design"]["Ct2"] * 1e15, ngLin=ng["design"]["L_in"] * 1e9)

    # ======================= Fig: phase noise ==========================================
    print("fig phase noise")
    fm = np.logspace(2, 7, 501)
    Qe, F_lin, P = s["Qe"], 10 ** (F_used_dB / 10), ps["P_W"]
    fig, ax = plt.subplots(figsize=(W1, 3.4))
    for fc, col, ls in [(10e3, C["sky"], ":"), (30e3, C["blue"], "-"), (100e3, C["purple"], "--")]:
        L = leeson(fm, p.f0, Qe, F_lin, P, fc)
        ax.plot(fm, L, color=col, ls=ls, label=f"this work, $f_c$ = {fc/1e3:.0f} kHz")
    L30 = leeson(fm, p.f0, Qe, F_lin, P, 30e3)
    mk = {"PnIC": ("o", C["verm"]), "SAW": ("s", C["green"]), "FBAR": ("^", C["orange"]), "quartz": ("D", C["ink"])}
    for r in REFERENCES:
        pn = scaled_pn(r, p.f0)
        mrk, col = mk[r["kind"]]
        ax.plot(list(pn.keys()), list(pn.values()), mrk, color=col, ms=4, mfc="none", label=r["name"].split(" [")[0] + (" (scaled)" if r["f0"] != p.f0 else ""))
    if cad and "pnoise_nominal" in cad:
        dd = np.array(cad["pnoise_nominal"]); ax.plot(dd[:, 0], dd[:, 1], "-", color=C["verm"], lw=1.6, label="Spectre Pnoise")
    ax.set(xscale="log", xlabel="offset frequency (Hz)", ylabel="$\\mathcal{L}(\\Delta f)$ (dBc/Hz)", ylim=(-175, -70), xlim=(1e2, 1e7))
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), fontsize=6, ncol=2)
    savefig(fig, "fig_phase_noise")
    for fc in (10e3, 30e3, 100e3):
        L = leeson(np.array([1e3, 10e3, 100e3, 1e6]), p.f0, Qe, F_lin, P, fc)
        tag = f"fc{int(fc/1e3)}k"
        numbers.update({f"PN1k{tag}": L[0], f"PN10k{tag}": L[1], f"PN100k{tag}": L[2], f"PN1M{tag}": L[3]})
    numbers.update(PN1k=numbers["PN1kfc30k"], PN10k=numbers["PN10kfc30k"], PN100k=numbers["PN100kfc30k"], PN1M=numbers["PN1Mfc30k"],
                   PNfloor=10 * np.log10(F_lin * 1.380649e-23 * 300 / (2 * P)), halfBW=p.f0 / (2 * Qe) / 1e3,
                   FoM100k=fom(numbers["PN100kfc30k"], 100e3, p.f0, amp.P_dc), FoM1k=fom(numbers["PN1kfc30k"], 1e3, p.f0, amp.P_dc),
                   FoM1M=fom(numbers["PN1Mfc30k"], 1e6, p.f0, amp.P_dc))
    np.savetxt(DAT / "phase_noise_model.csv", np.c_[fm, L30], delimiter=",", header="offset_Hz,L_dBcHz_fc30k", comments="")
    # Leeson term breakdown
    t1, t2, t3 = leeson_terms(fm, p.f0, Qe, F_lin, P, 30e3)
    fig, ax = plt.subplots(figsize=(W1, 2.2))
    ax.plot(fm, L30, color=C["ink"], label="total"); ax.plot(fm, t1, color=C["sky"], ls=":", label="floor $FkT/2P_s$ (+1/f)")
    ax.plot(fm, t2, color=C["blue"], ls="--", label="$1/f^2$: $Q_e$-limited"); ax.plot(fm, t3, color=C["purple"], ls="-.", label="$1/f^3$: flicker up-conversion")
    ax.set(xscale="log", xlabel="offset frequency (Hz)", ylabel="dBc/Hz", ylim=(-175, -70)); ax.legend(loc="upper right")
    savefig(fig, "fig_pn_terms")

    # ======================= Fig: PN sensitivity (inductor Q, drive power, F) ==========
    print("fig pn sensitivity")
    fig, ax = plt.subplots(1, 2, figsize=(W2, 2.2))
    Qs = np.array([3, 5, 8, 12, 20, 30, 50]); pn100 = []; pn1k = []; Fl = []
    for Q in Qs:
        a2 = replace(amp, Q_Lin=Q, Q_Lout=Q, Q_t=Q, Q_t2=Q)
        a2, _ = auto_phase_trim(p, a2)
        nf = loop_noise_factor(p, a2); Fl.append(nf["F_dB"])
        L, _ = oscillator_phase_noise(p, a2, np.array([1e3, 100e3]), fc_eff=30e3)
        pn1k.append(L[0]); pn100.append(L[1])
    ax[0].plot(Qs, pn100, "o-", color=C["blue"], ms=3, label="$\\mathcal{L}$(100 kHz)")
    ax[0].plot(Qs, np.array(pn1k) + 40, "s--", color=C["verm"], ms=3, label="$\\mathcal{L}$(1 kHz) $-$ 40 dB")
    ax0b = ax[0].twinx(); ax0b.plot(Qs, Fl, "^:", color=C["green"], ms=3); ax0b.set_ylabel("loop noise factor $F$ (dB)", color=C["green"]); ax0b.grid(False); ax0b.spines["top"].set_visible(False)
    ax[0].set(xscale="log", xlabel="inductor quality factor $Q_L$", ylabel="phase noise (dBc/Hz)"); ax[0].legend(loc="upper right"); ax[0].text(0.02, 0.95, "(a)", transform=ax[0].transAxes, va="top")
    Pd = np.linspace(-20, 0, 41); L100 = [leeson(100e3, p.f0, Qe, F_lin, 10 ** (x / 10) * 1e-3, 30e3) for x in Pd]
    L1 = [leeson(1e3, p.f0, Qe, F_lin, 10 ** (x / 10) * 1e-3, 30e3) for x in Pd]
    ax[1].plot(Pd, L100, color=C["blue"], label="100 kHz"); ax[1].plot(Pd, np.array(L1) + 40, color=C["verm"], ls="--", label="1 kHz $-$ 40 dB")
    ax[1].axvline(ps["P_dBm"], color=C["mute"], ls=":", lw=0.8); ax[1].text(ps["P_dBm"] + 0.3, -150, "design\npoint", fontsize=6.5, color=C["mute"])
    ax[1].set(xlabel="power dissipated in the ring $P_s$ (dBm)", ylabel="phase noise (dBc/Hz)"); ax[1].legend(loc="upper right"); ax[1].text(0.02, 0.95, "(b)", transform=ax[1].transAxes, va="top")
    savefig(fig, "fig_pn_sensitivity")
    np.savetxt(DAT / "pn_vs_inductorQ.csv", np.c_[Qs, Fl, pn1k, pn100], delimiter=",", header="Q_L,F_dB,PN1k,PN100k", comments="")
    numbers.update(PN100kQ30=pn100[list(Qs).index(30)], FQ30=Fl[list(Qs).index(30)], PN100kQ5=pn100[list(Qs).index(5)])

    # ======================= Fig: Monte Carlo + temperature ============================
    print("monte carlo")
    rows = run_monte_carlo(n=300, seed=7)
    # apply the implementation factor to the MC amplifier as well
    for r in rows:
        r["T0_dB"] += 20 * np.log10(k_impl)
    T0 = np.array([r["T0_dB"] for r in rows]); PN100 = np.array([r["PN100k"] for r in rows]); PN1 = np.array([r["PN1k"] for r in rows])
    Qe_mc = np.array([r["Qe"] for r in rows]); trim_mc = np.array([r["trim_deg"] for r in rows])
    yield_osc = 100 * np.mean(T0 > 0)
    fig, ax = plt.subplots(1, 3, figsize=(W2, 2.0))
    ax[0].hist(T0, bins=25, color=C["blue"], alpha=0.85); ax[0].axvline(0, color=C["verm"], ls="--", lw=0.8); ax[0].set(xlabel="loop gain $|T|$ (dB)", ylabel="trials")
    ax[0].text(0.02, 0.95, f"(a) yield {yield_osc:.1f} %", transform=ax[0].transAxes, va="top", fontsize=6.5)
    ax[1].hist(PN100, bins=25, color=C["green"], alpha=0.85); ax[1].set(xlabel="$\\mathcal{L}$(100 kHz) (dBc/Hz)"); ax[1].text(0.02, 0.95, f"(b) $\\sigma$ = {PN100.std():.1f} dB", transform=ax[1].transAxes, va="top", fontsize=6.5)
    ax[2].hist(trim_mc, bins=25, color=C["purple"], alpha=0.85); ax[2].set(xlabel="required phase trim (deg)"); ax[2].text(0.02, 0.95, f"(c) range {trim_mc.min():.0f}..{trim_mc.max():.0f}$^\\circ$", transform=ax[2].transAxes, va="top", fontsize=6.5)
    savefig(fig, "fig_montecarlo")
    with open(DAT / "montecarlo.csv", "w") as fh:
        fh.write(",".join(rows[0].keys()) + "\n")
        for r in rows:
            fh.write(",".join("" if v is None else f"{v:.6g}" for v in r.values()) + "\n")
    numbers.update(mcN=len(rows), mcT0mean=T0.mean(), mcT0std=T0.std(), mcT0min=T0.min(), mcYield=yield_osc, mcPN100mean=PN100.mean(), mcPN100std=PN100.std(),
                   mcPN1mean=PN1.mean(), mcPN1std=PN1.std(), mcQeMean=Qe_mc.mean(), mcQeStd=Qe_mc.std(), mcTrimMin=trim_mc.min(), mcTrimMax=trim_mc.max())
    print("temperature")
    ts = temperature_sweep()
    T = np.array([r["T"] for r in ts]); dfp = np.array([r["df_ppm"] for r in ts]); T0t = np.array([r["T0_dB"] for r in ts]) + 20 * np.log10(k_impl)
    pn100t = np.array([r["PN100k"] for r in ts])
    fig, ax = plt.subplots(1, 2, figsize=(W2, 2.0))
    ax[0].plot(T, dfp, color=C["blue"]); ax[0].set(xlabel="temperature ($^\\circ$C)", ylabel="$\\Delta f/f_0$ (ppm)"); ax[0].text(0.02, 0.95, "(a)", transform=ax[0].transAxes, va="top")
    ax[1].plot(T, T0t, color=C["blue"], label="$|T|$ (dB)"); ax1b = ax[1].twinx(); ax1b.plot(T, pn100t, color=C["green"], ls="--"); ax1b.set_ylabel("$\\mathcal{L}$(100 kHz) (dBc/Hz)", color=C["green"]); ax1b.grid(False); ax1b.spines["top"].set_visible(False)
    ax[1].set(xlabel="temperature ($^\\circ$C)", ylabel="loop gain (dB)"); ax[1].text(0.02, 0.95, "(b)", transform=ax[1].transAxes, va="top")
    savefig(fig, "fig_temperature")
    np.savetxt(DAT / "temperature.csv", np.c_[T, dfp, T0t, pn100t], delimiter=",", header="T_C,df_ppm,T0_dB,PN100k", comments="")
    numbers.update(tempDfRange=dfp.max() - dfp.min(), tempT0min=T0t.min(), tempT0max=T0t.max(), tempPNmin=pn100t.min(), tempPNmax=pn100t.max())

    # ======================= Fig: Allan deviation ======================================
    print("fig adev")
    fm2 = np.logspace(0, 7, 3000); L2 = leeson(fm2, p.f0, Qe, F_lin, P, 30e3)
    taus = np.logspace(-6, 0, 25); ad = allan_deviation_from_L(fm2, L2, p.f0, taus)
    fig, ax = plt.subplots(figsize=(W1, 2.0)); ax.loglog(taus, ad, color=C["blue"]); ax.set(xlabel="averaging time $\\tau$ (s)", ylabel="$\\sigma_y(\\tau)$")
    savefig(fig, "fig_adev")
    numbers.update(adev1ms=float(np.interp(1e-3, taus, ad)), adev1s=ad[-1], adev10us=float(np.interp(1e-5, taus, ad)))

    # ======================= comparison table ==========================================
    with open(DAT / "comparison.csv", "w") as fh:
        fh.write("work,f0_MHz,technology,PN_1k,PN_10k,PN_100k,PN_1M,Pdc_mW,FoM_100k\n")
        pn_this = {1e3: numbers["PN1k"], 10e3: numbers["PN10k"], 100e3: numbers["PN100k"], 1e6: numbers["PN1M"]}
        def row(name, f0, tech, pn, pdc):
            vals = [f"{pn[k]:.1f}" if k in pn else "" for k in (1e3, 10e3, 100e3, 1e6)]
            fomv = f"{fom(pn[100e3], 100e3, f0, pdc):.1f}" if (pdc and 100e3 in pn) else ""
            fh.write(f"{name},{f0/1e6:.2f},{tech},{','.join(vals)},{pdc*1e3 if pdc else ''},{fomv}\n")
        row("This work (model, pre-layout)", p.f0, "SiN-LN ring + 180-nm CMOS", pn_this, amp.P_dc)
        for r in REFERENCES:
            row(r["name"], r["f0"], r["tech"], r["pn"], r["pdc"])

    # ======================= numbers.tex ===============================================
    def fmt(v):
        if isinstance(v, (int, np.integer)): return str(v)
        if isinstance(v, (float, np.floating)):
            if abs(v) >= 1000: return f"{v:,.0f}"
            if abs(v) < 0.01 and v != 0:
                m, e = f"{v:.2e}".split("e"); return f"{m}\\times10^{{{int(e)}}}"
            return f"{v:.2f}"
        return str(v)
    with open(ROOT / "paper" / "numbers.tex", "w") as fh:
        fh.write("% auto-generated by sim/make_figures.py -- do not edit\n")
        D = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine"}
        seen = set()
        for k, v in numbers.items():
            key = "".join(D.get(ch, ch) for ch in k if ch.isalnum())
            assert key not in seen, key
            seen.add(key)
            fh.write(f"\\providecommand{{\\n{key}}}{{{fmt(v)}}}\n")
    (RES / "summary.json").write_text(json.dumps({k: (float(v) if isinstance(v, (np.floating, float, np.integer, int)) else v) for k, v in numbers.items()}, indent=1))
    print("done; numbers:", {k: numbers[k] for k in ("T0", "Qe", "Fused", "Ps", "PN1k", "PN100k", "FoM100k", "mcYield")})


if __name__ == "__main__":
    main()
