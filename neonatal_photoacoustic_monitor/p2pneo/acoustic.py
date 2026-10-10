"""Photoacoustic generation, 1-D acoustic propagation, transducer, noise and DSP.

Photon-to-phonon conversion: p0(z) = Gamma(T(z)) * mua(z) * Phi(z) * F0, with the
Grueneisen parameter Gamma(T) = Gamma37 * (1 + kG (T - 37 C)). For a laterally wide
source (beam radius >= transducer half-aperture, depths inside the near field) the
pressure at the probe is the plane-wave solution p(t) = p0(c t)/2 filtered by
frequency-dependent attenuation of the layers, the optical pulse spectrum and the
transducer band-pass. Pulse-echo (active ultrasound) time-of-flight through the same
layers gives the echo-shift thermometry channel: c_j(T) = c_j0 + kc_j (T - 37 C).
"""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np

FS = 40e6          # sampling rate (Hz)
NT = 1024          # samples per A-line (25.6 us ~ 3.9 cm)
T_STANDOFF = 0.1 / 150000.0   # one-way delay through the 1-mm coupling pad (s)
T_AX = np.arange(NT) / FS
F_AX = np.fft.rfftfreq(NT, 1 / FS)

# canonical layer order: scalp, fontanelle, bone, csf, brain
ACOUSTIC_DEFAULTS = {
    #            c0 (m/s) @37C, kc (m/s/C), alpha0 (dB/cm/MHz^y), y
    "scalp":      (1540.0, 1.3, 0.70, 1.1),
    "fontanelle": (1560.0, 1.3, 1.50, 1.0),
    "bone":       (2800.0, 0.0, 12.0, 1.0),
    "csf":        (1509.0, 2.4, 0.002, 2.0),
    "sinus":      (1584.0, 1.5, 0.20, 1.2),
    "brain":      (1546.0, 1.6, 0.60, 1.1),
}
LAYER_ORDER = tuple(ACOUSTIC_DEFAULTS)
GAMMA37 = 0.20                 # Grueneisen parameter of water-rich soft tissue at 37 C
KG_DEFAULT = {"scalp": 0.025, "fontanelle": 0.02, "bone": 0.005, "csf": 0.036, "sinus": 0.032, "brain": 0.030}  # 1/C


@dataclass
class Source:
    name: str
    wavelengths: tuple
    fluence_mJcm2: float        # per pulse on the skin (same for all wavelengths unless MPE-limited)
    pulse_ns: float
    prf_per_wl: float           # Hz per wavelength (time multiplexed)
    beam_radius: float          # cm
    duty: float = 1.0           # fraction of the frame in which the source runs (wearable thermal budget)
    cost_class: str = ""


@dataclass
class Transducer:
    name: str
    fc: float = 3.0e6           # centre frequency (Hz)
    bw: float = 0.70            # -6 dB fractional bandwidth
    nep_pa: float = 3.0         # single-shot in-band rms noise referred to the face (Pa) for a 3 MHz/70 % band
    aperture_cm: float = 0.8
    echo_snr_db: float = 30.0   # single-shot pulse-echo SNR of the deep speckle window


@dataclass
class DeviceConfig:
    name: str
    source: Source
    transducer: Transducer
    frame_s: float = 10.0
    scalp_gate: tuple = (0.03, 0.15)     # cm, in assumed-nominal depth coordinates
    brain_gate: tuple = (0.37, 0.52)     # cm (leading edge of the sinus, nominal geometry)
    echo_pulses: int = 100
    n_avg_scale: float = 1.0

    @property
    def n_avg(self):
        """Pulses averaged per wavelength and frame."""
        return max(1, int(self.source.prf_per_wl * self.frame_s * self.source.duty * self.n_avg_scale))


def mpe_single_pulse_mJcm2(lam):
    """ANSI Z136.1 skin MPE for 1 ns-100 us pulses, 700-1050 nm: 20*C_A mJ/cm^2."""
    ca = 10 ** (0.002 * (lam - 700.0))
    return 20.0 * ca


def mpe_average_Wcm2(lam):
    """ANSI Z136.1 skin MPE for exposures > 10 s: 0.2*C_A W/cm^2."""
    return 0.2 * 10 ** (0.002 * (lam - 700.0))


def allowed_fluence(lam, prf_total_hz, derate=0.5):
    """Allowed per-pulse fluence (mJ/cm^2) given the single-pulse and the average-power
    limits (neonatal derating factor applied to both)."""
    return derate * min(mpe_single_pulse_mJcm2(lam), 1e3 * mpe_average_Wcm2(lam) / prf_total_hz)


def gamma_of_T(T, layer_idx, kg=None):
    kg = np.array([KG_DEFAULT[n] for n in LAYER_ORDER]) if kg is None else np.asarray(kg)
    return GAMMA37 * (1.0 + kg[layer_idx] * (np.asarray(T) - 37.0))


def transducer_response(td: Transducer, pulse_ns: float):
    sig = td.bw * td.fc / (2 * np.sqrt(2 * np.log(2)))
    H = np.exp(-(F_AX - td.fc) ** 2 / (2 * sig ** 2))
    tp = pulse_ns * 1e-9
    S = np.sinc(F_AX * tp)
    return H * np.abs(S)


def _layer_lengths(z, thick_canon):
    """Path length inside each canonical layer for a path from the surface to depth z."""
    zb = np.concatenate([[0.0], np.cumsum(thick_canon)])
    seg = np.clip(z[:, None] - zb[None, :-1], 0.0, thick_canon[None, :])
    return seg                                     # [nz, L]


def propagate(p0_z, z, thick_canon, c_layer, alpha0, y, H):
    """Plane-wave propagation of the initial pressure profile p0(z) (Pa) to the probe.
    thick_canon: thickness of the 5 canonical layers (0 for absent ones), c_layer (m/s),
    alpha0 (dB/cm/MHz^y), y: per canonical layer. Returns pressure trace (Pa) vs T_AX."""
    seg = _layer_lengths(z, thick_canon)                                   # cm
    t_arr = (seg / (c_layer[None, :] * 100.0)).sum(1) + T_STANDOFF          # s
    fMHz = F_AX / 1e6
    att_db = (seg[:, :, None] * alpha0[None, :, None] * fMHz[None, None, :] ** y[None, :, None]).sum(1)  # [nz, nf]
    amp = 10 ** (-att_db / 20.0)
    dz = z[1] - z[0]
    lay = np.argmax(z[:, None] < np.cumsum(thick_canon)[None, :], axis=1)
    c_z = c_layer[lay] * 100.0                                              # cm/s
    P = ((p0_z * dz / (2.0 * c_z))[:, None] * amp * np.exp(-2j * np.pi * F_AX[None, :] * t_arr[:, None])).sum(0)
    P *= H
    p = np.fft.irfft(P, n=NT) * FS
    return p


ENBW_REF = (0.70 * 3.0e6 / (2 * np.sqrt(2 * np.log(2)))) * np.sqrt(np.pi)   # noise bandwidth of the reference 3 MHz / 70 % element


def enbw(td: Transducer):
    """Equivalent noise bandwidth of the Gaussian |H|^2 (Hz)."""
    return (td.bw * td.fc / (2 * np.sqrt(2 * np.log(2)))) * np.sqrt(np.pi)


def add_noise(p, td: Transducer, n_avg, H, rng):
    """Band-limited white noise. td.nep_pa is the single-shot in-band rms of a reference
    3 MHz / 70 % element; it scales with sqrt(noise bandwidth) for other bandwidths and
    averages down with sqrt(n_avg)."""
    w = rng.standard_normal(NT)
    W = np.fft.rfft(w) * H
    n = np.fft.irfft(W, n=NT)
    n *= (td.nep_pa * np.sqrt(enbw(td) / ENBW_REF) / np.sqrt(n_avg)) / max(np.std(n), 1e-30)
    return p + n


def envelope(p):
    P = np.fft.fft(p)
    h = np.zeros(NT); h[0] = 1; h[1:NT // 2] = 2; h[NT // 2] = 1
    return np.abs(np.fft.ifft(P * h))


def gate_amplitude(p, gate_cm, c_assumed=1545.0):
    """Mean envelope inside a depth gate (depth coordinates mapped with an assumed c)."""
    env = envelope(p)
    t1, t2 = gate_cm[0] / (c_assumed * 100.0) + T_STANDOFF, gate_cm[1] / (c_assumed * 100.0) + T_STANDOFF
    sel = (T_AX >= t1) & (T_AX < t2)
    return env[sel].mean()


# ---------------------------------------------------------------- pulse-echo
def echo_trace(td: Transducer, tof_s, amps, rng, n_avg, jitter_s=0.0):
    """Synthesise an RF pulse-echo A-line with echoes at tof_s (s), relative amplitudes amps."""
    sig = td.bw * td.fc / (2 * np.sqrt(2 * np.log(2)))
    H = np.exp(-(F_AX - td.fc) ** 2 / (2 * sig ** 2))
    P = np.zeros(len(F_AX), complex)
    for tof, a in zip(tof_s, amps):
        P += a * H * np.exp(-2j * np.pi * F_AX * (tof + jitter_s))
    p = np.fft.irfft(P, n=NT) * FS
    p /= max(np.abs(p).max(), 1e-30)
    snr = 10 ** (td.echo_snr_db / 20.0) * np.sqrt(n_avg)
    w = np.fft.irfft(np.fft.rfft(rng.standard_normal(NT)) * H, n=NT)
    w /= max(np.std(w), 1e-30)
    return p + w / snr


def echo_shift(trace, ref, window_s, fs=FS):
    """Cross-correlation delay of `trace` relative to `ref` in a time window (s), with
    parabolic sub-sample interpolation. Returns the shift in seconds."""
    i1, i2 = int(window_s[0] * fs), int(window_s[1] * fs)
    a = trace[i1:i2] - trace[i1:i2].mean(); b = ref[i1:i2] - ref[i1:i2].mean()
    maxlag = 20
    lags = np.arange(-maxlag, maxlag + 1)
    cc = np.array([np.dot(a[max(0, l):len(a) + min(0, l)], b[max(0, -l):len(b) + min(0, -l)]) for l in lags])
    k = int(np.argmax(cc))
    if 0 < k < len(cc) - 1:
        y0, y1, y2 = cc[k - 1], cc[k], cc[k + 1]
        den = (y0 - 2 * y1 + y2)
        frac = 0.5 * (y0 - y2) / den if abs(den) > 1e-30 else 0.0
    else:
        frac = 0.0
    return (lags[k] + frac) / fs
