"""Generate LaTeX tables and number macros for the manuscript from the result CSVs.
Run: python3 -m sim.make_tables   -> paper/tables/*.tex, paper/numbers.tex
"""
import os, csv, json
import numpy as np
from .platforms import DEVICES, PLATFORMS, PLATFORM_ORDER, eff_width

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(HERE, "results"); TAB = os.path.join(HERE, "paper", "tables")
NAME = {"si": "CFET-Si", "sige": "CFET-SiGe", "tmd": "CFET-TMD", "cnt": "CFET-CNT", "gan": "CFET-GaN"}
DEVN = {"gaa_n": "Si GAA n", "gaa_p": "Si GAA p", "sige_p": "SiGe GAA p", "mos2_n": "MoS$_2$ n", "wse2_p": "WSe$_2$ p",
        "cnt_n": "CNT n", "cnt_p": "CNT p", "gan_n": "GaN n", "gan_p": "p-GaN (proj.)"}


def rd(name):
    return list(csv.DictReader(open(os.path.join(RES, name))))


def F(r, k):
    try:
        return float(r[k])
    except Exception:
        return float("nan")


def si(x, unit="", nd=2):
    return f"{x:.{nd}f}{unit}"


def macro(name, value):
    return f"\\newcommand{{\\{name}}}{{{value}}}\n"


def tab_devparams(cal):
    keys = [("L", 1e9, "$L_g$ (nm)", 0), ("VTH0", 1e3, "$V_{TH0}$ (mV)", 0), ("N0", 1, "$n_0$", 2), ("ETA", 1e3, "$\\eta$ (mV/V)", 0),
            ("MU0", 1e4, "$\\mu_0$ (cm$^2$/Vs)", 0), ("VSAT", 1e-5, "$v_{sat}$ ($10^7$ cm/s)", 2), ("LAMBDA", 1, "$\\lambda$ (V$^{-1}$)", 2),
            ("RSW", 1e6, "$R_{S}W$ ($\\Omega\\cdot\\mu$m)", 0), ("COX", 1e3, "$C_{ox}$ (fF/$\\mu$m$^2$)", 1), ("CGSO", 1e9, "$C_{gso}$ (fF/$\\mu$m)", 2)]
    L = ["\\begin{tabular}{l" + "r" * 9 + "}", "\\hline", "Parameter & " + " & ".join(DEVN[d] for d in DEVICES) + " \\\\", "\\hline"]
    for k, sc, lab, nd in keys:
        row = []
        for d in DEVICES:
            p = dict(DEVICES[d]["params"]); p.update(cal[d])
            v = p[k] * sc
            row.append("--" if (k in ("MU0", "VSAT") and p["MU0"] == 0) else f"{v:.{nd}f}")
        L.append(lab + " & " + " & ".join(row) + " \\\\")
    row = []
    for d in DEVICES:
        p = dict(DEVICES[d]["params"]); p.update(cal[d]); row.append(f"{eff_width(p)*1e9:.0f}")
    L.append("$W_{eff}$ (nm) & " + " & ".join(row) + " \\\\")
    extra = {"cnt_n": lambda p: f"$T$={p['TTR']:.2f}, $\\alpha$={p['ALPHA']:.2f}", "cnt_p": lambda p: f"$T$={p['TTR']:.2f}, $\\alpha$={p['ALPHA']:.2f}",
             "mos2_n": lambda p: f"$C_q$={p['CQ']:.1f}, $D_{{it}}$={p['DIT']*1e-4:.0e}", "wse2_p": lambda p: f"$C_q$={p['CQ']:.1f}, $D_{{it}}$={p['DIT']*1e-4:.0e}",
             "gan_n": lambda p: f"$R_{{th}}$={p['RTH']*1e-5:.1f}e5", "gan_p": lambda p: f"$R_{{th}}$={p['RTH']*1e-5:.1f}e5"}
    row = []
    for d in DEVICES:
        p = dict(DEVICES[d]["params"]); p.update(cal[d]); row.append(extra[d](p) if d in extra else "--")
    L.append("material block & " + " & ".join(row) + " \\\\")
    L += ["\\hline", "\\end{tabular}"]
    open(os.path.join(TAB, "tab_devparams.tex"), "w").write("\n".join(L) + "\n")


def tab_calibration():
    rows = rd("calibration_mape.csv")
    L = ["\\begin{tabular}{lrrrrrrrrr}", "\\hline",
         "Device & MAPE$_{lin}$ & MAPE$_{sat}$ & MAPE$_{I_D\\text{-}V_D}$ & $I_{ON}$ & $I_{ON}^{ref}$ & $I_{OFF}$ & SS & SS$^{ref}$ & DIBL \\\\",
         " & (\\%) & (\\%) & (\\%) & (mA/$\\mu$m) & (mA/$\\mu$m) & (nA/$\\mu$m) & (mV/dec) & (mV/dec) & (mV/V) \\\\", "\\hline"]
    for r in rows:
        L.append(f"{DEVN[r['device']]} & {F(r,'mape_idvg_lin'):.1f} & {F(r,'mape_idvg_sat'):.1f} & {F(r,'mape_idvd'):.1f} & "
                 f"{F(r,'model_Ion_A_per_um')*1e3:.2f} & {F(r,'ref_Ion_A_per_um')*1e3:.2f} & {F(r,'model_Ioff_A_per_um')*1e9:.2f} & "
                 f"{F(r,'model_SS_mV_dec'):.0f} & {F(r,'ref_SS_mV_dec'):.0f} & {F(r,'model_DIBL_mV_V'):.0f} \\\\")
    L += ["\\hline", "\\end{tabular}"]
    open(os.path.join(TAB, "tab_calibration.tex"), "w").write("\n".join(L) + "\n")
    return rows


def tab_nominal():
    inv = {r["platform"]: r for r in rd("nominal_inverter.csv")}
    ro = {(r["platform"], r["N"]): r for r in rd("nominal_ro.csv")}
    L = ["\\begin{tabular}{lrrrrrrrrrr}", "\\hline",
         "Platform & $V_{DD}$ & $V_M/V_{DD}$ & $A_V$ & $NM_L/V_{DD}$ & $NM_H/V_{DD}$ & $t_{pd}^{inv}$ & $f_{RO5}$ & $t_{pd}^{RO}$ & $P_{avg}$ & $E_{cycle}$ \\\\",
         " & (V) & & & & & (ps) & (GHz) & (ps) & ($\\mu$W) & (fJ) \\\\", "\\hline"]
    for pl in PLATFORM_ORDER:
        i, r = inv[pl], ro[(pl, "5")]; vdd = PLATFORMS[pl]["vdd"]
        L.append(f"{NAME[pl]} & {vdd:.1f} & {F(i,'VM')/vdd:.3f} & {F(i,'gain'):.1f} & {F(i,'NML')/vdd:.2f} & {F(i,'NMH')/vdd:.2f} & "
                 f"{F(i,'tpd')*1e12:.2f} & {F(r,'fRO')*1e-9:.2f} & {F(r,'tpd')*1e12:.2f} & {F(r,'Pavg')*1e6:.2f} & {F(r,'Ecycle')*1e15:.2f} \\\\")
    L += ["\\hline", "\\end{tabular}"]
    open(os.path.join(TAB, "tab_nominal.tex"), "w").write("\n".join(L) + "\n")
    return inv, ro


def tab_mc():
    s = {r["platform"]: r for r in rd("mc_yield_summary.csv")}
    L = ["\\begin{tabular}{lrrrrrrr}", "\\hline",
         "Platform & $N_{RO}$ & $\\bar f_{RO}$ (GHz) & $\\sigma_f/\\bar f$ (\\%) & $Y_f$ (\\%) & $\\bar E_{cycle}$ (fJ) & $N_{inv}$ & $Y_{func}$ (\\%) \\\\", "\\hline"]
    for pl in PLATFORM_ORDER:
        r = s[pl]
        L.append(f"{NAME[pl]} & {int(F(r,'N_ro'))} & {F(r,'f_mean_GHz'):.2f} & {F(r,'f_sigma_over_mu_pct'):.1f} & {F(r,'Y_f_pct'):.1f} & "
                 f"{F(r,'E_mean_fJ'):.2f} & {int(F(r,'N_inv'))} & {F(r,'Y_func_pct'):.1f} \\\\")
    L += ["\\hline", "\\end{tabular}"]
    open(os.path.join(TAB, "tab_mc.tex"), "w").write("\n".join(L) + "\n")
    return s


def main():
    os.makedirs(TAB, exist_ok=True)
    cal = json.load(open(os.path.join(HERE, "data", "calibrated_params.json")))
    tab_devparams(cal); crows = tab_calibration(); inv, ro = tab_nominal(); mc = tab_mc()
    M = ""
    mapes = [F(r, k) for r in crows for k in ("mape_idvg_lin", "mape_idvg_sat")]
    M += macro("mapeIdVgMin", f"{min(mapes):.1f}") + macro("mapeIdVgMax", f"{max(mapes):.1f}")
    mv = [F(r, "mape_idvd") for r in crows]; M += macro("mapeIdVdMin", f"{min(mv):.1f}") + macro("mapeIdVdMax", f"{max(mv):.1f}")
    for pl in PLATFORM_ORDER:
        r = ro[(pl, "5")]; i = inv[pl]; vdd = PLATFORMS[pl]["vdd"]
        M += macro(f"fro{pl}", f"{F(r,'fRO')*1e-9:.2f}") + macro(f"tpd{pl}", f"{F(r,'tpd')*1e12:.1f}") + macro(f"ecyc{pl}", f"{F(r,'Ecycle')*1e15:.2f}")
        M += macro(f"pavg{pl}", f"{F(r,'Pavg')*1e6:.1f}") + macro(f"vm{pl}", f"{F(i,'VM')/vdd:.2f}") + macro(f"gain{pl}", f"{F(i,'gain'):.0f}")
        M += macro(f"nml{pl}", f"{F(i,'NML')/vdd:.2f}") + macro(f"nmh{pl}", f"{F(i,'NMH')/vdd:.2f}") + macro(f"pdp{pl}", f"{F(r,'PDP')*1e15:.3f}")
        M += macro(f"yf{pl}", f"{F(mc[pl],'Y_f_pct'):.0f}") + macro(f"yfunc{pl}", f"{F(mc[pl],'Y_func_pct'):.0f}") + macro(f"sigf{pl}", f"{F(mc[pl],'f_sigma_over_mu_pct'):.1f}")
    # temperature
    for r in rd("temp_sweep.csv"):
        if r["osc"] == "True":
            M += macro(f"fT{r['platform']}{str(int(F(r,'temp_c'))).replace('-', 'm')}", f"{F(r,'fRO')*1e-9:.2f}")
    # tmd crossover and gan tcf
    for r in csv.reader(open(os.path.join(RES, "tmd_crossover.csv"))):
        if r[0] == "RC_critical_kohm_um": M += macro("rcCritical", f"{float(r[1]):.2f}")
        elif r[0] not in ("RC_kohm_um",): M += macro("tmdRatio" + r[0].replace(".", "p"), f"{float(r[1]):.2f}")
    for r in rd("gan_tcf.csv"):
        M += macro(f"tcf{r['platform']}", f"{F(r,'TCF_ppm_per_K_300_500K'):.0f}") + macro(f"fFiveHundred{r['platform']}", f"{F(r,'f500_GHz'):.2f}")
    # areas
    for r in rd(os.path.join(HERE, "layout", "area_report.csv")) if False else csv.DictReader(open(os.path.join(HERE, "layout", "area_report.csv"))):
        M += macro("area" + r["cell"].replace("_", ""), f"{float(r['area_um2'])*1e6:.0f}")  # in 1e-3 um^2 -> nm^2/1000
    open(os.path.join(HERE, "paper", "numbers.tex"), "w").write(M)
    print("wrote paper/tables/*.tex and paper/numbers.tex")


if __name__ == "__main__":
    main()
