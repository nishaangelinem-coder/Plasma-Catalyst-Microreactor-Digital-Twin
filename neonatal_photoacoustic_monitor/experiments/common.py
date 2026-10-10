"""Device configurations and the per-frame simulation loop shared by the experiments."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import numpy as np
from p2pneo import acoustic as ac, tissue
from p2pneo.fluence import FluenceModel
from p2pneo.forward import ForwardModel, HeadParams
from p2pneo.subject import VirtualNeonate, sample_head, scenario_hypothermia, scenario_intermittent_hypoxaemia, scenario_static
from p2pneo import estimators as est

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "results"); FIG = os.path.join(HERE, "..", "figures")
TABLE = os.environ.get("P2P_TABLE", os.path.join(RES, "fluence_table.npz"))
DEFAULT_LAMS = (690, 800, 850, 900)      # CRLB-optimal set without the 940-nm water band (E1c)
I_THERMAL_CAP = 0.10        # W/cm^2 average irradiance budget on neonatal scalp (E6)
NOMINAL_TOP = 0.40
GATE_ERR = None             # test hook: force the echo gate-localisation error (cm)


def make_sources(lams=DEFAULT_LAMS, i_cap=I_THERMAL_CAP):
    K = len(lams)
    return {
        "LED array":        ac.Source("LED array", lams, 0.05, 100.0, 1e3 * i_cap / 0.05 / K, 0.5, cost_class="low"),
        "Laser-diode stack": ac.Source("Laser-diode stack", lams, 0.5, 80.0, 1e3 * i_cap / 0.5 / K, 0.5, cost_class="mid"),
        "Compact laser":    ac.Source("Compact laser", lams, 10.0, 8.0, 1e3 * i_cap / 10.0 / K, 0.5, cost_class="high"),
    }


TRANSDUCERS = {
    "single-element PZT 8 mm": ac.Transducer("single-element PZT 8 mm", 3.0e6, 0.70, 3.0, 0.8, 30.0),
    "flexible PVDF patch":     ac.Transducer("flexible PVDF patch", 3.0e6, 0.80, 8.0, 0.6, 24.0),
    "CMUT patch":              ac.Transducer("CMUT patch", 3.0e6, 1.0, 1.5, 0.6, 30.0),
}


def make_devices(lams=DEFAULT_LAMS, frame_s=10.0):
    S = make_sources(lams)
    return {
        "bedside":  ac.DeviceConfig("bedside", S["Compact laser"], TRANSDUCERS["single-element PZT 8 mm"], frame_s),
        "wearable": ac.DeviceConfig("wearable", S["Laser-diode stack"], TRANSDUCERS["CMUT patch"], frame_s),
        "wearable-LED": ac.DeviceConfig("wearable-LED", S["LED array"], TRANSDUCERS["CMUT patch"], frame_s),
    }


METHODS_SO2 = ["NIRS rScO2", "PA linear unmixing", "PA fluence-compensated", "Proposed EKF",
               "EKF -echo", "EKF -reference", "EKF -fluence corr.", "EKF -depth gating"]
METHODS_T = ["Rectal proxy", "Scalp thermistor", "PA amplitude (800 nm)", "Echo shift only", "Proposed EKF",
             "EKF -echo", "EKF -reference", "EKF -fluence corr.", "EKF -depth gating"]


def run_sequence(fl, head, dev, scen, rng, ablations=True, baselines=True, ekf_kwargs=None):
    """Simulate a scenario; return dict of per-frame estimates and truth."""
    neo = VirtualNeonate(fl, head, dev, scen, rng)
    gates = dict(scalp=dev.scalp_gate, brain=dev.brain_gate)           # nominal geometry (estimator)
    gates_nogate = dict(scalp=dev.scalp_gate, brain=(0.03, 1.0))
    # The co-registered pulse-echo line locates the sinus surface (+-0.3 mm). The device
    # places its deep gate there and the model-based estimators adapt their nominal
    # geometry (superficial thickness) to the measured depth ("ultrasound-guided").
    shift = head.sinus_top - HeadParams().sinus_top + (GATE_ERR if GATE_ERR is not None else rng.normal(0, 0.03))
    gates_dev = dict(scalp=dev.scalp_gate, brain=(dev.brain_gate[0] + shift, dev.brain_gate[1] + shift))
    nominal = HeadParams(scalp_thick=0.20 + max(shift, -0.1))      # sinus surface at the echo-measured depth
    dsp = est.DeviceDSP(dev, neo.t_sup0, neo.t_deep0, gates_dev)
    dsp_ng = est.DeviceDSP(dev, neo.t_sup0, neo.t_deep0, gates_nogate, peak_lock=False)
    T_b0 = scen.T_core[0] + 0.4                 # anchor: rectal temperature + nominal gradient
    T_s0 = scen.T_probe[0] - 0.65
    n = len(scen.t)
    kw = dict(nominal_head=nominal, **(ekf_kwargs or {}))
    ekfs = {"Proposed EKF": est.JointEKF(fl, dev, gates_dev, T_b0, T_s0, **kw)}
    if ablations:
        ekfs["EKF -echo"] = est.JointEKF(fl, dev, gates_dev, T_b0, T_s0, use_echo=False, **kw)
        ekfs["EKF -reference"] = est.JointEKF(fl, dev, gates_dev, T_b0, T_s0, use_ref=False, **kw)
        ekfs["EKF -fluence corr."] = est.JointEKF(fl, dev, gates_dev, T_b0, T_s0, fluence_correction=False, **kw)
        ekfs["EKF -depth gating"] = est.JointEKF(fl, dev, gates_nogate, T_b0, T_s0, peak_lock=False, **kw)
    fcu = est.FluenceCompensatedUnmixing(fl, dev, gates_dev, nominal_head=nominal)
    amp_th = est.AmplitudeThermometry(T0=T_b0)
    echo_th = est.EchoShiftThermometry(ekfs["Proposed EKF"].fm, T_b0)
    out = {m: np.full(n, np.nan) for m in METHODS_SO2}
    outT = {m: np.full(n, np.nan) for m in METHODS_T}
    sd = {"so2": np.full(n, np.nan), "T": np.full(n, np.nan), "Ts": np.full(n, np.nan)}
    Ts_est = np.full(n, np.nan); g_est = np.full(n, np.nan); hbt_est = np.full(n, np.nan)
    sig_hist = np.full(n, np.nan); amp_hist = np.full(n, np.nan)
    for k in range(n):
        fr = neo.frame(k)
        A = dsp.amplitudes(fr["traces"])
        sig = dsp.noise_floor(fr["traces"])
        dtau = dsp.echo_shifts(fr["echo"])
        meas = dict(A=A, sigma_amp=sig, dtau=dtau, a_ref=fr["a_ref"])
        sig_hist[k] = sig; amp_hist[k] = A[dev.source.wavelengths[0]]["brain"]
        for name, f in ekfs.items():
            if name == "EKF -depth gating":
                m2 = dict(meas); m2["A"] = dsp_ng.amplitudes(fr["traces"])
                x, s = f.step(m2, fr["T_probe"])
            else:
                x, s = f.step(meas, fr["T_probe"])
            out[name][k] = x[0]; outT[name][k] = x[2]
            if name == "Proposed EKF":
                # reported temperature interval includes the +-0.25 C uncertainty of the rectal/thermistor anchor
                sd["so2"][k], sd["T"][k], sd["Ts"][k] = s[0], np.sqrt(s[2] ** 2 + 0.25 ** 2), np.sqrt(s[5] ** 2 + 0.25 ** 2)
                Ts_est[k] = x[5]; g_est[k] = np.exp(x[6]); hbt_est[k] = np.exp(x[1])
        if baselines:
            Ab = {l: A[l]["brain"] for l in dev.source.wavelengths}
            out["PA linear unmixing"][k] = est.linear_unmixing(Ab, dev.source.wavelengths)
            out["PA fluence-compensated"][k] = fcu.estimate(Ab)
            out["NIRS rScO2"][k] = fr["nirs"]
            outT["PA amplitude (800 nm)"][k] = amp_th.estimate(Ab) if 800 in Ab else np.nan
            outT["Echo shift only"][k] = echo_th.estimate(dtau[1])
            outT["Rectal proxy"][k] = scen.T_core[k] + 0.1 * rng.standard_normal()
            outT["Scalp thermistor"][k] = fr["T_probe"] - 0.65
    return dict(t=scen.t, so2=out, T=outT, sd=sd, Ts_est=Ts_est, g_est=g_est, hbt_est=hbt_est,
                snr=float(np.nanmean(amp_hist) / np.nanmean(sig_hist)),
                truth=dict(so2=scen.so2_b, T_b=scen.T_b, T_s=scen.T_s, T_core=scen.T_core, g=scen.g,
                           hbt=scen.hbt_b, motion=scen.motion), events=scen.events, head=head)
