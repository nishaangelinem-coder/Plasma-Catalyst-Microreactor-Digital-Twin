"""
monte_carlo.py -- Process / resonator-variation / temperature study.

Sampled (per trial): Qi, Qc (fabrication), f0 (lithography), C0, Ga0 (IDT),
transistor gm (process), inductor L and Q, tank detune (varactor range),
supply voltage.  Reported: loop gain at the design mode, Q_e, oscillation
frequency offset (phase condition), phase noise at 1 kHz / 100 kHz, start-up
time, and the mode-selection margin.  Temperature: TCF on f0, kT scaling.
"""
from __future__ import annotations
import numpy as np
from dataclasses import replace
from ring_model import RingParams, calibrate_to_measurement
from oscillator_design import (AmpDesign, auto_phase_trim, loop_gain_summary, find_oscillation_point,
                               startup_time, mode_selection)
from phase_noise import oscillator_phase_noise


def sample_design(rng, base_p: RingParams, base_amp: AmpDesign):
    p = replace(base_p,
                Qi=base_p.Qi * rng.lognormal(0, 0.20),
                Qc=base_p.Qc * rng.lognormal(0, 0.30),
                f0=base_p.f0 * (1 + rng.normal(0, 500e-6)),
                C0=base_p.C0 * (1 + rng.normal(0, 0.10)),
                Ga0=base_p.Ga0 * (1 + rng.normal(0, 0.15)))
    kL = 1 + rng.normal(0, 0.08)
    amp = replace(base_amp,
                  gm_id1=base_amp.gm_id1 * (1 + rng.normal(0, 0.10)),
                  I1=base_amp.I1 * (1 + rng.normal(0, 0.08)),
                  I2=base_amp.I2 * (1 + rng.normal(0, 0.08)),
                  I4=base_amp.I4 * (1 + rng.normal(0, 0.08)),
                  L_in=base_amp.L_in * kL, L_out=base_amp.L_out * kL, L_t=base_amp.L_t * kL,
                  Q_Lin=base_amp.Q_Lin * (1 + rng.normal(0, 0.15)),
                  Q_t=base_amp.Q_t * (1 + rng.normal(0, 0.15)),
                  vdd=base_amp.vdd * (1 + rng.normal(0, 0.03)))
    return p, amp


def run_monte_carlo(n=300, seed=1, fc_eff=30e3, with_trim=True):
    rng = np.random.default_rng(seed)
    base_p = calibrate_to_measurement(RingParams(), verbose=False)
    base_amp, _ = auto_phase_trim(base_p, AmpDesign())
    rows = []
    for i in range(n):
        p, amp = sample_design(rng, base_p, base_amp)
        if with_trim:
            amp, trim = auto_phase_trim(p, amp)        # the on-chip phase-trim calibration
        else:
            trim = amp.phase_trim_deg
        s = loop_gain_summary(p, amp)
        osc = find_oscillation_point(p, amp)
        L, info = oscillator_phase_noise(p, amp, np.array([1e3, 100e3]), fc_eff=fc_eff)
        st = startup_time(p, amp)
        rows.append(dict(trial=i, Qi=p.Qi, Qc=p.Qc, QL=p.QL, Qe=s["Qe"], T0_dB=s["T0_dB"], trim_deg=trim,
                         f_osc=None if osc is None else osc["f_osc"],
                         df_ppm=None if osc is None else 1e6 * (osc["f_osc"] - p.f0) / p.f0,
                         f0=p.f0, PN1k=L[0], PN100k=L[1], F_dB=info["F_dB"], P_s_dBm=info["P_s_dBm"],
                         t_start_us=st["t_startup_s"] * 1e6, P_dc_mW=amp.P_dc * 1e3))
    return rows


def temperature_sweep(T_list=np.arange(-40, 86, 5)):
    base_p = calibrate_to_measurement(RingParams(), verbose=False)
    base_amp, _ = auto_phase_trim(base_p, AmpDesign())
    out = []
    for T in T_list:
        p = replace(base_p, f0=base_p.f0 * (1 + base_p.tcf * (T - 27.0)))
        # Qi degrades mildly with temperature (phonon-phonon), ~T^-0.5 around room temperature
        p = replace(p, Qi=base_p.Qi * ((273.15 + 27) / (273.15 + T)) ** 0.5)
        amp, trim = auto_phase_trim(p, base_amp)
        s = loop_gain_summary(p, amp)
        import phase_noise as pn
        pn.T_K = 273.15 + T
        L, info = oscillator_phase_noise(p, amp, np.array([1e3, 100e3]))
        pn.T_K = 300.0
        out.append(dict(T=T, f0=p.f0, df_ppm=1e6 * (p.f0 - base_p.f0) / base_p.f0, QL=p.QL, Qe=s["Qe"],
                        T0_dB=s["T0_dB"], PN1k=L[0], PN100k=L[1], trim_deg=trim))
    return out


if __name__ == "__main__":
    import json
    rows = run_monte_carlo(100)
    keys = ["T0_dB", "Qe", "df_ppm", "PN1k", "PN100k", "t_start_us", "trim_deg"]
    for k in keys:
        v = np.array([r[k] for r in rows if r[k] is not None], float)
        print(f"{k:10s} mean={v.mean():9.3f}  std={v.std():8.3f}  min={v.min():9.3f}  max={v.max():9.3f}")
    for r in temperature_sweep(np.array([-40, 27, 85])):
        print(r)
