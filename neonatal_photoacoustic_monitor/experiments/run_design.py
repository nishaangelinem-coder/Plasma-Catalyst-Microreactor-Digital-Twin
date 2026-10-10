"""Design-space exploration: E1 optical, E2 acoustic, E6 thermal safety / power budget."""
import sys, os, json, itertools, time, argparse
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, pandas as pd
import common
from p2pneo import tissue, mc, acoustic as ac, thermal, estimators as est
from p2pneo.fluence import FluenceModel, LAYERS_CANON, BONE_GRID, BEAM_RADII
from p2pneo.forward import ForwardModel, HeadParams, CI

ap = argparse.ArgumentParser(); ap.add_argument("--quick", action="store_true")
ap.add_argument("--only", default="E1a,E1b,E1c,E1d,E2,E6"); args = ap.parse_args()
ONLY = set(args.only.split(","))
sources = common.make_sources(common.DEFAULT_LAMS)
src = sources["Compact laser"]


def noise_env_std(td, n_avg, H, n=20):
    v = []
    for _ in range(n):
        p = ac.add_noise(np.zeros(ac.NT), td, n_avg, H, rng)
        sel = (ac.T_AX > 3.0 / 154500) & (ac.T_AX < 3.6 / 154500)
        v.append(ac.envelope(p)[sel].std())
    return float(np.mean(v))

RES, FIG = common.RES, common.FIG
fl = FluenceModel(common.TABLE)
LAMS_ALL = fl.lams
rng = np.random.default_rng(0)
summary = {}

# =============================================================== E1a fluence vs depth
if "E1a" in ONLY:
    rows = []
    for lam in LAMS_ALL:
        for bone in BONE_GRID:
            for a in BEAM_RADII:
                phi = fl.fluence(lam, bone, 1.0, a, np.zeros(len(LAYERS_CANON)), so2v=0.65)
                top = HeadParams(bone=bone).sinus_top
                iz = lambda z: int(z / mc.DZ)
                rows.append(dict(wavelength_nm=lam, bone_cm=bone, beam_radius_cm=a,
                                 phi_sinus_top=phi[iz(top)], phi_0p5cm=phi[iz(0.5)], phi_1cm=phi[iz(1.0)],
                                 phi_1p5cm=phi[iz(1.5)], phi_2cm=phi[iz(2.0)]))
    E1a = pd.DataFrame(rows); E1a.to_csv(os.path.join(RES, "E1a_fluence_vs_depth.csv"), index=False)
    np.savez(os.path.join(RES, "E1a_fluence_profiles.npz"), z=fl.z,
             **{f"phi_{lam}_b{b}": fl.fluence(lam, b, 1.0, 0.5, np.zeros(6), 0.65) for lam in LAMS_ALL for b in BONE_GRID})


# =============================================================== E1b sources, MPE, SNR
if "E1b" in ONLY:

    rows = []
    for sname, src in sources.items():
        for tname, td in common.TRANSDUCERS.items():
            dev = ac.DeviceConfig("x", src, td, 10.0)
            fm = ForwardModel(fl, HeadParams(), dev, second_order=True)
            fa = est.FastAcoustics(fm, dict(scalp=dev.scalp_gate, brain=dev.brain_gate))
            for lam in src.wavelengths:
                prf_total = src.prf_per_wl * len(src.wavelengths)
                mpe_single = ac.mpe_single_pulse_mJcm2(lam); mpe_avg = ac.mpe_average_Wcm2(lam)
                allowed = ac.allowed_fluence(lam, prf_total, derate=0.5)
                F0 = min(src.fluence_mJcm2, allowed)
                p0, phi = fm.p0(lam, 0.65, 37.0, 34.0, 1.0, F0=F0)
                A = fa.gate_amps(p0)
                for frame_s in (2.0, 10.0, 30.0):
                    n_avg = max(1, int(src.prf_per_wl * frame_s))
                    sig = noise_env_std(td, n_avg, fm.H)
                    rows.append(dict(source=sname, transducer=tname, wavelength_nm=lam, prf_total_Hz=prf_total,
                                     F0_mJcm2=F0, allowed_mJcm2=allowed, mpe_single_mJcm2=mpe_single, mpe_avg_Wcm2=mpe_avg,
                                     I_avg_Wcm2=F0 * prf_total * 1e-3, p0_sinus_edge_Pa=float(p0[fm.is_sinus][0]),
                                     A_scalp_Pa=A["scalp"], A_sinus_Pa=A["brain"], frame_s=frame_s, n_avg=n_avg,
                                     noise_Pa=sig, SNR_sinus=A["brain"] / sig, SNR_scalp=A["scalp"] / sig))
    E1b = pd.DataFrame(rows); E1b.to_csv(os.path.join(RES, "E1b_source_snr.csv"), index=False)


# =============================================================== E1c wavelength selection (CRLB)
if "E1c" in ONLY:
    def crlb_so2(lams, src_name="Compact laser", frame_s=10.0, so2=0.65, bone=0.0):
        src = common.make_sources(tuple(lams))[src_name]
        td = common.TRANSDUCERS["single-element PZT 8 mm"]
        dev = ac.DeviceConfig("x", src, td, frame_s)
        fm = ForwardModel(fl, HeadParams(bone=bone), dev, second_order=False)
        fa = est.FastAcoustics(fm, dict(scalp=dev.scalp_gate, brain=dev.brain_gate))
        sig = noise_env_std(td, dev.n_avg, fm.H, n=10)
        def lnA(x):
            out = []
            for lam in lams:
                F0 = min(src.fluence_mJcm2, ac.allowed_fluence(lam, src.prf_per_wl * len(lams)))
                p0, _ = fm.p0(lam, x[0], 37.0, 34.0, np.exp(x[1]), F0=F0)
                out.append(np.log(fa.gate_amps(p0)["brain"]))
            return np.array(out)
        x0 = np.array([so2, 0.0]); f0 = lnA(x0)
        J = np.zeros((len(lams), 2)); eps = [0.01, 0.02]
        for i in range(2):
            xp = x0.copy(); xp[i] += eps[i]; J[:, i] = (lnA(xp) - f0) / eps[i]
        A = np.exp(f0)
        R = np.diag((sig / A) ** 2 + 0.02 ** 2)
        F = J.T @ np.linalg.solve(R, J)
        C = np.linalg.inv(F)
        return float(np.sqrt(C[0, 0])), float(np.linalg.cond(J)), float(A.min() / sig)

    rows = []
    cands = [l for l in LAMS_ALL]
    for K in (2, 3, 4):
        for sub in itertools.combinations(cands, K):
            if 800 not in sub:
                continue
            s, cond, snr = crlb_so2(sub)
            rows.append(dict(K=K, wavelengths="/".join(map(str, sub)), crlb_so2=s, cond=cond, min_snr=snr))
    E1c = pd.DataFrame(rows).sort_values(["K", "crlb_so2"]); E1c.to_csv(os.path.join(RES, "E1c_wavelength_selection.csv"), index=False)
    best4 = E1c[E1c.K == 4].iloc[0]
    summary["best_wavelengths_4"] = best4.wavelengths; summary["crlb_so2_best4"] = float(best4.crlb_so2)
    # sO2 sensitivity across saturations and bone
    rows = []
    for so2 in (0.45, 0.55, 0.65, 0.75, 0.85):
        for bone in (0.0, 0.1, 0.2, 0.3):
            s, cond, snr = crlb_so2(common.DEFAULT_LAMS, so2=so2, bone=bone)
            rows.append(dict(so2=so2, bone_cm=bone, crlb_so2=s, min_snr=snr))
    pd.DataFrame(rows).to_csv(os.path.join(RES, "E1c_crlb_vs_so2_bone.csv"), index=False)


# =============================================================== E1d perturbation validation (direct MC)
if "E1d" in ONLY:
    rows = []
    nphot = 20_000 if args.quick else 100_000
    for lam in (750, 850):
        for so2v in (0.55, 0.75):
            names, th = tissue.head_geometry(0.0)
            props = [tissue.layer_props(n, lam, so2=(so2v if n == "sinus" else None)) for n in names]
            mua = np.array([p[0] for p in props]); mus = np.array([p[1] for p in props]); g = np.array([p[2] for p in props])
            Phi, Lz, Rr, Lr, raw = mc.fluence_and_paths(nphot, th, mua, mus, g, seed=7)
            wgt = (np.arange(mc.NR) + 0.5) * mc.DR < 0.5
            A = (raw["A"] * wgt[:, None]).sum(0); phi_mc = A / mc.DZ / raw["mua_z"]
            phi_model = fl.fluence(lam, 0.0, 1.0, 0.5, np.zeros(6), so2v=so2v)
            # second check: perturbation from the 0.65 node with no sO2 interpolation (first-order only)
            fm = ForwardModel(fl, HeadParams(), ac.DeviceConfig("x", sources["Compact laser"], common.TRANSDUCERS["single-element PZT 8 mm"]), second_order=False)
            nom65 = fl.nominal_mua(lam, 0.65); dm = fl.nominal_mua(lam, so2v) - nom65
            phi_pert = fl.fluence(lam, 0.0, 1.0, 0.5, dm, so2v=0.65, second_order=False)
            for zz in (0.1, 0.3, 0.42, 0.5, 0.7, 1.0, 1.5, 2.0):
                i = int(zz / mc.DZ)
                rows.append(dict(wavelength_nm=lam, so2v=so2v, z_cm=zz, phi_mc=phi_mc[i], phi_model=phi_model[i],
                                 phi_pert_from_0p65=phi_pert[i], err_model_pct=100 * (phi_model[i] / phi_mc[i] - 1),
                                 err_pert_pct=100 * (phi_pert[i] / phi_mc[i] - 1)))
    E1d = pd.DataFrame(rows); E1d.to_csv(os.path.join(RES, "E1d_perturbation_validation.csv"), index=False)
    summary["E1d_max_abs_err_model_pct_z<=1cm"] = float(E1d[E1d.z_cm <= 1.0].err_model_pct.abs().max())
    summary["E1d_max_abs_err_pert_pct_z<=1cm"] = float(E1d[E1d.z_cm <= 1.0].err_pert_pct.abs().max())


# =============================================================== E2 acoustic design
if "E2" in ONLY:
    rows = []
    for fc in (1.0, 1.5, 2.0, 3.0, 5.0, 7.5):
        for pulse in (8.0, 80.0, 150.0, 300.0):
            for bone in (0.0, 0.1, 0.2, 0.3):
                td = ac.Transducer("t", fc * 1e6, 0.7, 3.0, 0.8)
                s2 = ac.Source("s", src.wavelengths, src.fluence_mJcm2, pulse, src.prf_per_wl, src.beam_radius)
                dev = ac.DeviceConfig("x", s2, td, 10.0)
                head = HeadParams(bone=bone)
                fm = ForwardModel(fl, head, dev, second_order=True)
                top = head.sinus_top
                gates = dict(scalp=dev.scalp_gate, brain=(top - 0.03, top + 0.12))
                fa = est.FastAcoustics(fm, gates)
                p0, _ = fm.p0(800, 0.65, 37.0, 34.0, 1.0)
                A = fa.gate_amps(p0)
                A_scalp_only = fa.gate_amps(np.where(fm.deep_mask, 0.0, p0))
                A_sinus_only = fa.gate_amps(np.where(fm.is_sinus, p0, 0.0))
                sig = noise_env_std(td, dev.n_avg, fm.H, n=8)
                rows.append(dict(fc_MHz=fc, pulse_ns=pulse, bone_cm=bone, A_scalp=A["scalp"], A_sinus=A["brain"],
                                 crosstalk_scalp_into_sinus=A_scalp_only["brain"] / max(A_sinus_only["brain"], 1e-12),
                                 noise_Pa=sig, SNR_sinus=A["brain"] / sig,
                                 axial_res_mm=1545.0 / (2 * 0.7 * fc * 1e6) * 1e3))
    E2 = pd.DataFrame(rows); E2.to_csv(os.path.join(RES, "E2_acoustic_design.csv"), index=False)
    # echo-shift sensitivity
    fm = ForwardModel(fl, HeadParams(), ac.DeviceConfig("x", src, common.TRANSDUCERS["single-element PZT 8 mm"]))
    t0 = fm.echo_times(37.0, 34.0); t1 = fm.echo_times(38.0, 34.0); t2 = fm.echo_times(37.0, 35.0)
    summary["echo_sens_deep_ns_per_C"] = ((t1[1] - t1[0]) - (t0[1] - t0[0])) * 1e9
    summary["echo_sens_sup_ns_per_C"] = (t2[0] - t0[0]) * 1e9
    # TOF precision by simulation
    rows = []
    for snr_db in (20, 24, 30):
        for n_avg in (10, 100, 400):
            td = ac.Transducer("t", 3e6, 0.7, 3.0, 0.8, snr_db)
            tp = est.T_PAD
            ref = ac.echo_trace(td, [tp, tp + t0[0], tp + t0[1]], [0.6, 1.0, 0.5], rng, n_avg)
            dsp = est.DeviceDSP(ac.DeviceConfig("x", src, td), t0[0], t0[1]); dsp.echo_ref = ref
            sh = [dsp.echo_shifts(ac.echo_trace(td, [tp, tp + t0[0], tp + t0[1]], [0.6, 1.0, 0.5], rng, n_avg)) for _ in range(40)]
            sh = np.array(sh)
            rows.append(dict(echo_snr_db=snr_db, n_avg=n_avg, std_sup_ns=sh[:, 0].std() * 1e9, std_deep_ns=sh[:, 1].std() * 1e9,
                             std_T_deep_C=sh[:, 1].std() * 1e9 / abs(summary["echo_sens_deep_ns_per_C"])))
    pd.DataFrame(rows).to_csv(os.path.join(RES, "E2_echo_shift_precision.csv"), index=False)


# =============================================================== E6 thermal safety and power budget
if "E6" in ONLY:
    rows = []
    names, th = tissue.head_geometry(0.0)
    phi = fl.fluence(800, 0.0, 1.0, 0.5, np.zeros(6), 0.65)
    fm = ForwardModel(fl, HeadParams(), ac.DeviceConfig("x", src, common.TRANSDUCERS["single-element PZT 8 mm"]))
    dm, nom = fm.dmua(800, 0.65); mua_z = fm.mua_z(nom, dm)
    th_sim = th.copy(); th_sim[-1] = 5.0
    for I in (0.0, 0.02, 0.05, 0.10, 0.15, 0.20, 0.32):
        for q_el in (0.0, 0.02, 0.05):
            for h_top, label in ((5.0, "insulated patch"), (15.0, "open probe")):
                for T_core in (37.0, 33.5):
                    z, T, T0, ts, Tskin, Tcx = thermal.simulate(names, th_sim, mua_z, phi, fl.z, I, q_el, h_top=h_top,
                                                                T_amb=33.0, T_core=T_core, t_end_s=1200.0)
                    rows.append(dict(I_avg_Wcm2=I, q_elec_Wcm2=q_el, contact=label, T_core=T_core,
                                     dT_skin_20min=Tskin[-1] - Tskin[0], dT_cortex_20min=Tcx[-1] - Tcx[0],
                                     dT_skin_5min=float(np.interp(300, ts, Tskin)) - Tskin[0],
                                     T_skin_abs=Tskin[-1], dT_max_profile=float((T - T0).max())))
    E6 = pd.DataFrame(rows); E6.to_csv(os.path.join(RES, "E6_thermal_safety.csv"), index=False)
    # power budget (wearable, 4 wavelengths, beam area pi*0.5^2)
    area = np.pi * 0.5 ** 2
    rows = []
    for sname, src_ in sources.items():
        wpe = {"LED array": 0.15, "Laser-diode stack": 0.30, "Compact laser": 0.02}[sname]
        e_opt = src_.fluence_mJcm2 * area                      # mJ per pulse
        e_el = e_opt / wpe
        p_src = e_el * 1e-3 * src_.prf_per_wl * len(src_.wavelengths)   # W
        for duty in (1.0, 0.25):
            p_tot = p_src * duty + 0.25                                   # AFE+ADC+MCU+BLE
            rows.append(dict(source=sname, wpe=wpe, E_opt_mJ=e_opt, E_elec_mJ=e_el, P_source_W=p_src, duty=duty,
                             P_total_W=p_tot, battery_h_7p4Wh=7.4 / p_tot, I_avg_Wcm2=src_.fluence_mJcm2 * src_.prf_per_wl * len(src_.wavelengths) * 1e-3 * duty))
    pd.DataFrame(rows).to_csv(os.path.join(RES, "E6_power_budget.csv"), index=False)

_p = os.path.join(RES, "design_summary.json")
_old = json.load(open(_p)) if os.path.exists(_p) else {}
_old.update(summary); json.dump(_old, open(_p, "w"), indent=2)
print(json.dumps(_old, indent=2))
