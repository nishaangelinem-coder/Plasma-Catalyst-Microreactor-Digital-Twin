"""
phase_noise.py -- Phase-noise model of the phononic-ring oscillator.

Leeson-Cutler form with every term taken from the circuit:
    F    : loop noise factor from oscillator_design.loop_noise_factor
    Q_e  : electrically loaded Q (resonator Q_L further loaded by the amplifier ports)
    P_s  : signal power dissipated in the motional resistance (acoustic power)
    f_c  : effective 1/f-noise corner of the sustaining amplifier after
           up-conversion (Hajimiri-Lee: f_c,eff = f_c,dev * (Gamma_dc/Gamma_rms)^2).
           It is a parameter here and is swept, because it is set by waveform
           symmetry and the PDK flicker model; the Spectre Pnoise run resolves it.

Also: FoM, Allan deviation from L(f), and the literature comparison table.
"""
from __future__ import annotations
import numpy as np
from ring_model import kB
from oscillator_design import loop_noise_factor, loop_gain_summary, signal_power_in_resonator

T_K = 300.0


def leeson(fm, f0, Qe, F, P_s, fc=0.0):
    fm = np.asarray(fm, float)
    L = (F * kB * T_K / (2 * P_s)) * (1 + (f0 / (2 * Qe * fm)) ** 2) * (1 + fc / fm)
    return 10 * np.log10(L)


def leeson_terms(fm, f0, Qe, F, P_s, fc):
    """Return the three contributions (dBc/Hz): floor, 1/f^2 (thermal, Q-limited), 1/f^3 (flicker)."""
    fm = np.asarray(fm, float)
    floor = F * kB * T_K / (2 * P_s)
    t2 = floor * (f0 / (2 * Qe * fm)) ** 2
    t3 = t2 * fc / fm
    t1 = floor * (1 + fc / fm)
    return 10 * np.log10(floor * np.ones_like(fm)), 10 * np.log10(t2), 10 * np.log10(t3)


def oscillator_phase_noise(p, amp, fm, fc_eff=30e3, extra_F_dB=0.0, P_override=None):
    s = loop_gain_summary(p, amp)
    nf = loop_noise_factor(p, amp)
    ps = signal_power_in_resonator(p, amp)
    F = nf["F"] * 10 ** (extra_F_dB / 10)
    P = ps["P_W"] if P_override is None else P_override
    return leeson(fm, p.f0, s["Qe"], F, P, fc_eff), dict(Qe=s["Qe"], F_dB=10 * np.log10(F), P_s_dBm=10 * np.log10(P / 1e-3), fc_eff=fc_eff)


def fom(L_dB, fm, f0, P_dc_W):
    return -L_dB + 20 * np.log10(f0 / fm) - 10 * np.log10(P_dc_W / 1e-3)


def allan_deviation_from_L(fm, L_dB, f0, taus):
    """sigma_y(tau) from S_phi(f) = 2*10^(L/10) (IEEE Std 1139 relation)."""
    fm = np.asarray(fm, float)
    S_phi = 2 * 10 ** (np.asarray(L_dB) / 10)
    S_y = (fm / f0) ** 2 * S_phi
    out = []
    for tau in taus:
        H = 2 * np.sin(np.pi * fm * tau) ** 4 / (np.pi * fm * tau) ** 2
        out.append(np.sqrt(max(np.trapezoid(S_y * H, fm), 0)))
    return np.array(out)


# --------------------------------------------------------------------------
#  Literature comparison (values as published; see paper/refs.bib)
# --------------------------------------------------------------------------
REFERENCES = [
    dict(key="ji2026",      name="Ji et al. 2026 [SiN-LN ring, bench amp.]", f0=1001.15e6, tech="SiN-LN phononic ring", pn={100e3: -159.0}, pdc=None, kind="PnIC"),
    dict(key="shin2025",    name="Shin et al. 2025 [SAW PnC edge mode]",      f0=1.0e9,     tech="128Y-LN SAW",          pn={10e3: -132.5}, pdc=None, kind="SAW"),
    dict(key="otis2003",    name="Otis & Rabaey 2003 [FBAR, 0.13-um CMOS]",   f0=1.9e9,     tech="AlN FBAR + CMOS",      pn={100e3: -120.0}, pdc=300e-6, kind="FBAR"),
    dict(key="ostman2006",  name="Östman et al. 2006 [FBAR, SiGe]",           f0=2.1e9,     tech="above-IC AlN FBAR",    pn={1e6: -144.1}, pdc=None, kind="FBAR"),
    dict(key="norling2008", name="Norling et al. 2008 [TFBAR, SiGe]",         f0=2.0e9,     tech="monolithic AlN TFBAR", pn={100e3: -125.0}, pdc=None, kind="FBAR"),
    dict(key="quartz",      name="100-MHz SC-cut OCXO, x10 multiplied",       f0=1.0e9,     tech="quartz (scaled +20 dB)", pn={1e3: -145.0, 10e3: -155.0, 100e3: -160.0}, pdc=None, kind="quartz"),
]


def scaled_pn(ref, f_target):
    """Scale a reference's phase noise to f_target with 20log10(f_target/f0)."""
    return {k: v + 20 * np.log10(f_target / ref["f0"]) for k, v in ref["pn"].items()}


if __name__ == "__main__":
    from oscillator_design import default_design
    p, amp = default_design()
    fm = np.logspace(2, 7, 11)
    L, info = oscillator_phase_noise(p, amp, fm)
    print(info)
    for a, b in zip(fm, L):
        print(f"  {a:9.0f} Hz : {b:7.1f} dBc/Hz")
    print("FoM@100k:", fom(np.interp(100e3, fm, L), 100e3, p.f0, amp.P_dc))
    taus = np.logspace(-5, 0, 11)
    fm2 = np.logspace(0, 7, 2000)
    L2, _ = oscillator_phase_noise(p, amp, fm2)
    print("ADEV:", dict(zip(taus, allan_deviation_from_L(fm2, L2, p.f0, taus))))
