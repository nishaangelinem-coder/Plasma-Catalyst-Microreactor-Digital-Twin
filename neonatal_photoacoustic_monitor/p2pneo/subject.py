"""Virtual neonate: hidden physiological truth, clinical scenarios and the raw data the
device would record each frame."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from . import acoustic as ac
from .forward import ForwardModel, HeadParams, CI


def sample_head(rng, bone_range=(0.0, 0.1)):
    """Random subject-specific head: the estimator never sees these numbers."""
    kg = np.array([ac.KG_DEFAULT[n] for n in ac.LAYER_ORDER]) * rng.uniform(0.75, 1.25)
    kc = np.array([ac.ACOUSTIC_DEFAULTS[n][1] for n in ac.LAYER_ORDER]) * rng.uniform(0.75, 1.25)
    a0 = np.array([ac.ACOUSTIC_DEFAULTS[n][2] for n in ac.LAYER_ORDER]) * rng.uniform(0.7, 1.4)
    return HeadParams(
        bone=float(rng.uniform(*bone_range)), mus_scale=float(rng.uniform(0.8, 1.2)),
        hbt_scalp=float(rng.uniform(28.0, 52.0)), hbt_brain=float(rng.uniform(38.0, 65.0)),
        so2_scalp=float(rng.uniform(0.60, 0.80)), bg_scale=float(rng.uniform(0.7, 1.3)),
        hct_scale=float(rng.uniform(0.85, 1.15)), fill=float(rng.uniform(0.35, 0.65)),
        par_offset=float(rng.uniform(0.0, 0.10)),
        kg=kg, gamma37=ac.GAMMA37 * float(rng.uniform(0.9, 1.1)), kc=kc, alpha0=a0,
        scalp_thick=float(rng.uniform(0.16, 0.24)), deep_echo_depth=float(rng.uniform(1.3, 1.7)),
        ref_gain=float(rng.uniform(0.9, 1.1)))


@dataclass
class Scenario:
    name: str
    dt: float
    t: np.ndarray
    so2_b: np.ndarray
    hbt_b: np.ndarray        # parenchymal HbT; also modulates the sinus blood content (fill) relative to baseline
    T_core: np.ndarray
    T_b: np.ndarray
    T_s: np.ndarray
    T_probe: np.ndarray
    g: np.ndarray            # coupling gain
    motion: np.ndarray       # bool per frame
    events: list             # (t_start, t_end, depth) desaturation events


def _ou(rng, n, dt, tau, sigma):
    x = np.zeros(n); a = np.exp(-dt / tau); s = sigma * np.sqrt(1 - a * a)
    for i in range(1, n):
        x[i] = a * x[i - 1] + s * rng.standard_normal()
    return x


def _coupling(rng, n, motion):
    g = np.ones(n); drift = _ou(rng, n, 1.0, 400.0, 0.03)
    level = 1.0
    for i in range(1, n):
        if motion[i] and not motion[i - 1]:
            level *= rng.uniform(0.6, 0.95)        # gel/contact loss after a movement
        level += (1.0 - level) * 0.01              # slow partial recovery
        g[i] = level * (1 + drift[i])
    return g


def scenario_hypothermia(rng, dt=10.0, hours=10.0, head=None):
    """Therapeutic hypothermia for HIE: induction 37 -> 33.5 C (60 min), maintenance,
    rewarming 0.5 C/h from t = 4 h, two desaturation events and one seizure-like
    hyperaemic/hyperthermic episode."""
    n = int(hours * 3600 / dt); t = np.arange(n) * dt
    T_core = np.where(t < 3600, 33.5 + 3.5 * np.exp(-t / 1500.0), 33.5)
    rew = (t > 4 * 3600)
    T_core = np.where(rew, np.minimum(33.5 + 0.5 * (t - 4 * 3600) / 3600.0, 36.8), T_core)
    T_core += _ou(rng, n, dt, 1800.0, 0.08)
    grad_bc = rng.uniform(0.2, 0.8)                      # brain warmer than core
    grad_bc_t = grad_bc + 0.3 * (37 - T_core) / 3.5 * rng.uniform(0.3, 1.0)  # gradient grows with cooling
    T_b = T_core + grad_bc_t + _ou(rng, n, dt, 900.0, 0.05)
    cap = rng.uniform(1.0, 3.0)                          # scalp below core (cooling cap / ambient)
    T_s = T_core - cap + _ou(rng, n, dt, 600.0, 0.15)
    # seizure-like episode: +0.4 C brain, +8 % HbT, sO2 +5 % for 15 min at ~6.5 h
    s0 = int(6.5 * 3600 / dt); s1 = min(s0 + int(900 / dt), n)
    seiz = np.zeros(n)
    if s1 > s0:
        seiz[s0:s1] = np.sin(np.linspace(0, np.pi, s1 - s0))
    T_b += 0.4 * seiz
    so2 = 0.68 + _ou(rng, n, dt, 1200.0, 0.02) + 0.05 * seiz
    hbt = (head.hbt_brain if head else 50.0) * (1 + 0.08 * seiz + _ou(rng, n, dt, 1800.0, 0.02))
    events = []
    for te in (2.2 * 3600, 8.1 * 3600):
        i0 = int(te / dt); dur = int(rng.uniform(90, 240) / dt); depth = rng.uniform(0.12, 0.22)
        if i0 + dur >= n:
            continue
        prof = np.sin(np.linspace(0, np.pi, dur)) ** 0.7
        so2[i0:i0 + dur] -= depth * prof
        events.append((t[i0], t[min(i0 + dur, n - 1)], depth))
    so2 = np.clip(so2, 0.3, 0.95)
    motion = rng.random(n) < (dt / 1800.0)              # ~ one movement per 30 min
    g = _coupling(rng, n, motion)
    T_probe = T_s + rng.uniform(0.3, 1.0) + _ou(rng, n, dt, 300.0, 0.05)
    return Scenario("hypothermia", dt, t, so2, hbt, T_core, T_b, T_s, T_probe, g, motion, events)


def scenario_intermittent_hypoxaemia(rng, dt=2.0, minutes=60.0, head=None):
    """Preterm intermittent hypoxaemia: ~12 desaturations of 20-90 s, depth 8-25 %."""
    n = int(minutes * 60 / dt); t = np.arange(n) * dt
    T_core = 36.8 + _ou(rng, n, dt, 1800.0, 0.05)
    T_b = T_core + rng.uniform(0.2, 0.6) + _ou(rng, n, dt, 600.0, 0.03)
    T_s = T_core - rng.uniform(0.5, 1.5) + _ou(rng, n, dt, 300.0, 0.1)
    so2 = 0.72 + _ou(rng, n, dt, 600.0, 0.015)
    events = []
    starts = np.sort(rng.uniform(60, max(minutes * 60 - 100, 90), 12))
    for ts in starts:
        i0 = int(ts / dt); dur = int(rng.uniform(20, 90) / dt); depth = rng.uniform(0.08, 0.25)
        if i0 + dur >= n:
            continue
        prof = np.sin(np.linspace(0, np.pi, dur)) ** 0.6
        so2[i0:i0 + dur] -= depth * prof
        events.append((t[i0], t[min(i0 + dur, n - 1)], depth))
    so2 = np.clip(so2, 0.3, 0.95)
    hbt = (head.hbt_brain if head else 50.0) * (1 + _ou(rng, n, dt, 600.0, 0.02))
    motion = rng.random(n) < (dt / 400.0)
    g = _coupling(rng, n, motion)
    T_probe = T_s + rng.uniform(0.3, 1.0) + _ou(rng, n, dt, 300.0, 0.05)
    return Scenario("intermittent_hypoxaemia", dt, t, so2, hbt, T_core, T_b, T_s, T_probe, g, motion, events)


def scenario_static(rng, so2, T_b, dt=10.0, minutes=12.0, head=None):
    """Stationary state for calibration-type accuracy experiments (E3)."""
    n = int(minutes * 60 / dt); t = np.arange(n) * dt
    T_core = np.full(n, T_b - rng.uniform(0.2, 0.8))
    T_s = T_core - rng.uniform(0.5, 2.5) + _ou(rng, n, dt, 300.0, 0.05)
    so2a = np.full(n, so2) + _ou(rng, n, dt, 600.0, 0.005)
    hbt = (head.hbt_brain if head else 50.0) * np.ones(n)
    motion = np.zeros(n, bool); g = _coupling(rng, n, motion)
    T_probe = T_s + rng.uniform(0.3, 1.0)
    return Scenario("static", dt, t, np.clip(so2a, 0.3, 0.95), hbt, T_core, np.full(n, T_b), T_s, T_probe, g, motion, [])


class VirtualNeonate:
    """Generates the raw device data for every frame of a scenario."""

    def __init__(self, fl, head: HeadParams, dev: ac.DeviceConfig, scen: Scenario, rng, nirs_lams=(760, 850)):
        self.fm = ForwardModel(fl, head, dev, second_order=True)
        self.head, self.dev, self.scen, self.rng = head, dev, scen, rng
        self.nirs_lams = nirs_lams
        self.nirs_w = rng.uniform(0.15, 0.35); self.nirs_bias = rng.uniform(-0.06, 0.06)
        td = dev.transducer
        self.echo_ref = None
        self.t_sup0, self.t_deep0 = self.fm.echo_times(scen.T_b[0], scen.T_s[0])

    def frame(self, k):
        s, d, rng = self.scen, self.dev, self.rng
        n_avg = d.n_avg
        traces = {}
        for lam in d.source.wavelengths:
            p, _ = self.fm.pa_trace(lam, s.so2_b[k], s.T_b[k], s.T_s[k], s.g[k], fill=self.head.fill * s.hbt_b[k] / self.head.hbt_brain)
            traces[lam] = ac.add_noise(p, d.transducer, n_avg, self.fm.H, rng)
        # reference absorber: strong, SNR 200 single shot, gain g, weak known T-dependence
        a_ref = s.g[k] * self.head.ref_gain * (1 - 0.001 * (s.T_probe[k] - 37.0)) * (1 + rng.standard_normal() / (200 * np.sqrt(n_avg)))
        # pulse-echo
        t_sup, t_deep = self.fm.echo_times(s.T_b[k], s.T_s[k])
        jit = (rng.standard_normal() * 0.3e-9) + (rng.uniform(-15e-9, 15e-9) if s.motion[k] else 0.0)
        t_pad = 2 * 0.1 / 150000.0
        echo = ac.echo_trace(d.transducer, [t_pad, t_pad + t_sup, t_pad + t_deep], [0.6, 1.0, 0.5], rng, d.echo_pulses, jitter_s=0.0)
        # motion/probe shift affects the whole line; thermal shift of each segment is in t_sup/t_deep
        echo = np.interp(ac.T_AX - jit, ac.T_AX, echo)
        T_probe_meas = s.T_probe[k] + 0.1 * rng.standard_normal()
        # Empirical comparator: a commercial NIRS cerebral oximeter (rScO2). It reads a
        # mixed arterial/venous compartment (~25/75 %), is contaminated by extracerebral
        # tissue (w), carries a sensor/device-specific offset and has ~2.6 % precision
        # (Dix 2013; Kleiser 2018). It is NOT a physics simulation of a NIRS device.
        sao2 = min(0.98, s.so2_b[k] + 0.27)
        nirs = ((1 - self.nirs_w) * (0.75 * s.so2_b[k] + 0.25 * sao2) + self.nirs_w * self.head.so2_scalp
                + self.nirs_bias + 0.026 * rng.standard_normal() * np.sqrt(10.0 / self.dev.frame_s))
        return dict(traces=traces, a_ref=a_ref, echo=echo, T_probe=T_probe_meas, nirs=float(np.clip(nirs, 0.15, 0.95)),
                    t_sup=t_sup, t_deep=t_deep)
