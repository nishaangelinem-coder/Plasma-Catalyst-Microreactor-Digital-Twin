"""Print the key numbers used in the paper from results/."""
import os, sys, json
import numpy as np, pandas as pd
R = os.path.join(os.path.dirname(__file__), "..", "results")
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
def rd(n): return pd.read_csv(os.path.join(R, n))

def design():
    print(json.dumps(json.load(open(os.path.join(R, "design_summary.json"))), indent=1))
    a = rd("E1a_fluence_vs_depth.csv")
    print("\n== E1a fluence at sinus top / 1 cm / 2 cm (bone 0, a=0.5)")
    print(a[(a.bone_cm == 0) & (a.beam_radius_cm == 0.5)][["wavelength_nm", "phi_sinus_top", "phi_1cm", "phi_2cm"]].round(4).to_string())
    print(a[(a.wavelength_nm == 800) & (a.beam_radius_cm == 0.5)][["bone_cm", "phi_sinus_top"]].round(4).to_string())
    print(a[(a.wavelength_nm == 800) & (a.bone_cm == 0)][["beam_radius_cm", "phi_sinus_top"]].round(4).to_string())
    b = rd("E1b_source_snr.csv")
    print("\n== E1b SNR at 800 nm")
    print(b[(b.wavelength_nm == 800)].pivot_table(index=["source", "transducer"], columns="frame_s", values="SNR_sinus").round(1).to_string())
    print(b[(b.wavelength_nm == 800) & (b.frame_s == 10)][["source", "transducer", "F0_mJcm2", "allowed_mJcm2", "I_avg_Wcm2", "p0_sinus_edge_Pa", "A_sinus_Pa", "noise_Pa"]].round(3).to_string())
    print(b[(b.source == "Compact laser") & (b.transducer.str.startswith("single")) & (b.frame_s == 10)][["wavelength_nm", "mpe_single_mJcm2", "allowed_mJcm2", "A_sinus_Pa", "SNR_sinus"]].round(2).to_string())
    c = rd("E1c_wavelength_selection.csv")
    print("\n== E1c best sets"); print(pd.concat([c[c.K == k].head(3) for k in (2, 3, 4)]).round(4).to_string()); print(c[c.wavelengths == "750/800/850/900"].round(4).to_string())
    print(rd("E1c_crlb_vs_so2_bone.csv").pivot(index="so2", columns="bone_cm", values="crlb_so2").round(4).to_string())
    d = rd("E1d_perturbation_validation.csv"); print("\n== E1d"); print(d.groupby("z_cm")[["err_model_pct", "err_pert_pct"]].agg(lambda x: np.abs(x).max()).round(2).to_string())
    e = rd("E2_acoustic_design.csv"); print("\n== E2 (8 ns)")
    print(e[e.pulse_ns == 8].pivot(index="fc_MHz", columns="bone_cm", values="SNR_sinus").round(0).to_string())
    print(e[(e.pulse_ns == 8) & (e.bone_cm == 0)][["fc_MHz", "crosstalk_scalp_into_sinus", "A_sinus"]].round(4).to_string())
    print(e[e.bone_cm == 0].pivot(index="fc_MHz", columns="pulse_ns", values="A_sinus").round(1).to_string())
    print(rd("E2_echo_shift_precision.csv").round(3).to_string())
    t = rd("E6_thermal_safety.csv"); print("\n== E6 thermal (20 min)")
    print(t[(t.T_core == 37)].pivot_table(index="I_avg_Wcm2", columns=["contact", "q_elec_Wcm2"], values="dT_skin_20min").round(2).to_string())
    print(t[(t.T_core == 33.5) & (t.q_elec_Wcm2 == 0)].pivot_table(index="I_avg_Wcm2", columns="contact", values=["dT_skin_20min", "dT_cortex_20min"]).round(2).to_string())
    print(rd("E6_power_budget.csv").round(3).to_string())

def dynamic():
    if os.path.exists(os.path.join(R, "E3_static_accuracy_summary.csv")):
        print("\n== E3"); s = rd("E3_static_accuracy_summary.csv"); print(s.dropna(subset=["rmse"]).round(3).to_string())
    if os.path.exists(os.path.join(R, "E4_dynamic_summary.csv")):
        s = rd("E4_dynamic_summary.csv")
        cols = [c for c in ["scenario", "quantity", "method", "rmse_mean", "rmse_std", "bias_mean", "maxerr_mean", "rmse_rel_mean", "coverage95_mean", "grad_rmse_mean", "g_rmse_mean", "sensitivity_mean", "false_alarms_per_h_mean", "latency_s_mean"] if c in s]
        for sc in s.scenario.unique():
            print("\n== E4", sc); print(s[s.scenario == sc][cols].round(3).to_string())
        print("\n== E4 Wilcoxon"); print(rd("E4_wilcoxon.csv").round(5).to_string())
        p = rd("E4_dynamic_per_seed.csv"); print("SNR per device:", p.groupby("device").snr.agg(["mean", "min", "max"]).round(0).to_string())
    if os.path.exists(os.path.join(R, "E5_sensitivity_summary.csv")):
        s = rd("E5_sensitivity_summary.csv")
        for q in ("sO2", "T"):
            print("\n== E5", q)
            keep = ["Proposed EKF", "PA fluence-compensated", "NIRS rScO2"] if q == "sO2" else ["Proposed EKF", "Echo shift only", "Rectal proxy"]
            d = s[(s.quantity == q) & (s.method.isin(keep))]
            print(d.pivot_table(index=["setting", "value"], columns="method", values="rmse_mean").round(2).to_string())

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "design"): design()
    if which in ("all", "dynamic"): dynamic()
