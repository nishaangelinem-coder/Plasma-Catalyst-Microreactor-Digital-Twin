"""
Circuit description of the CMOS-driven spatiotemporally modulated (STM)
acoustic circulator used throughout the project.

Two topologies are supported (see sim/topologies.py for the netlists):

  'A' parallel-mode loop (Estep-type): port -Cp- tank; mBVD + shunt modulated cap to ground; ring Cc
  'C' series-mode resonant junction (wye): port (shunt Csh) - mBVD - modulated cap - floating star node
      The three series-resonant branches meet at the star; for the counter-rotating (l=+-1)
      modes the star is a virtual ground, for the in-phase (l=0) mode the star is open, so the
      l=0 mode is non-resonant and the junction behaves as an ideal cyclic-symmetric circulator
      core once the l=+-1 pair is split by the angular-momentum-biased modulation.

Modulating element: 'varactor' (A-MOS, analogue C-V, square-wave gate drive) or 'switch'
(MIM capacitor in series with a wide nMOS switch: two-state 'digital varactor').
"""
from __future__ import annotations

import numpy as np
from dataclasses import dataclass, asdict
from .ltp import Network, fourier_coeffs, db


@dataclass
class Resonator:
    """Modified Butterworth-Van Dyke (mBVD) parameters (Larson et al., 2000)."""
    fs: float = 0.9600e9      # series resonance [Hz]
    C0: float = 1.20e-12      # static capacitance [F]
    Cm: float = 0.30e-12      # motional capacitance [F]  (Cm/C0 = 0.25, k_t^2 ~ 24 %, X-cut LiNbO3 SH0 LVR)
    Qm: float = 500.0         # motional quality factor
    Rs: float = 0.50          # electrode/routing series resistance [ohm]
    R0: float = 0.30          # dielectric loss in series with C0 [ohm]

    @property
    def Lm(self):
        return 1.0 / ((2 * np.pi * self.fs) ** 2 * self.Cm)

    @property
    def Rm(self):
        return 2 * np.pi * self.fs * self.Lm / self.Qm

    @property
    def fp(self):
        return self.fs * np.sqrt(1 + self.Cm / self.C0)

    @property
    def kt2(self):
        # k_t^2 = (pi^2/8) * (fp^2 - fs^2) / fp^2   (common definition for LVRs)
        return (np.pi ** 2 / 8) * (self.fp ** 2 - self.fs ** 2) / self.fp ** 2


@dataclass
class Varactor:
    """Smooth accumulation-mode MOS varactor C-V model, C(V) = Cmin + (Cmax-Cmin)*(1+tanh((V-V0)/Vs))/2.
    V is the gate-to-well voltage.  Values representative of a 65 nm CMOS n-well A-MOS varactor."""
    Cmax: float = 2.00e-12     # per unit cell (scale with 'mult')
    Cmin: float = 0.80e-12
    V0: float = 0.25
    Vs: float = 0.22
    Rv: float = 1.5            # series resistance per unit cell [ohm] (Q ~ 75 at 1 GHz, 1.4 pF, min-L fingers)
    mult: float = 1.0          # number of unit cells in parallel (Cmax, Cmin scale up; Rv scales down)

    @property
    def cmax(self): return self.Cmax * self.mult
    @property
    def cmin(self): return self.Cmin * self.mult
    @property
    def rv(self): return self.Rv / self.mult

    def C(self, v):
        return self.cmin + (self.cmax - self.cmin) * 0.5 * (1 + np.tanh((v - self.V0) / self.Vs))


@dataclass
class SwitchCap:
    """Switched MIM capacitor: C_sw [F] in series with an nMOS switch of width W [um], plus fixed Cpar."""
    Csw: float = 2.0e-12
    W: float = 1000.0                # um
    Cpar: float = 0.0
    ron_w: float = 350.0             # ohm*um  (65 nm nMOS, VGS = 1.2 V)
    coff_w: float = 0.6e-15          # F/um    (drain junction + overlap)
    @property
    def Ron(self): return self.ron_w / self.W
    @property
    def Coff(self): return self.coff_w * self.W
    @property
    def Qon(self): return 1.0 / (2 * np.pi * 1e9 * self.Csw * self.Ron)
    def C(self, on):
        return self.Cpar + np.where(on > 0.5, self.Csw, self.Csw * self.Coff / (self.Csw + self.Coff))


@dataclass
class Design:
    res: Resonator
    var: Varactor
    Cp: float = 0.45e-12      # 'A': port coupling capacitor; 'C': shunt matching capacitor Csh at the port [F]
    Cc: float = 0.12e-12      # 'A' only: inter-resonator coupling capacitor [F]
    topo: str = 'C'           # 'A' | 'C'
    element: str = 'switch'   # 'varactor' | 'switch'
    sw: SwitchCap | None = None
    fm: float = 25e6          # modulation (pump) frequency [Hz]
    Vdc: float = 0.25         # varactor bias midpoint [V]
    Vm: float = 0.50          # modulation amplitude [V] (square wave swings Vdc +/- Vm)
    waveform: str = 'square'  # 'square' | 'sine' | 'trap'
    trise: float = 0.08       # rise time as a fraction of the period for 'trap'
    direction: int = +1       # +1: phases 0,-120,-240 (1->2->3), -1 reversed
    z0: float = 50.0

    def to_dict(self):
        d = asdict(self)
        return d


def varactor_drive(des: Design, theta):
    """Tuning voltage waveform v(theta), theta = 2*pi*fm*t, for phase 0."""
    if des.waveform == 'sine':
        return des.Vdc + des.Vm * np.cos(theta)
    if des.waveform == 'square':
        return des.Vdc + des.Vm * np.sign(np.cos(theta))
    if des.waveform == 'trap':
        # trapezoid with finite rise/fall of trise*T, same fundamental phase as cos
        x = ((theta / (2 * np.pi)) + 0.25) % 1.0   # 0..1, high for first half
        tr = des.trise
        y = np.where(x < tr, x / tr,
            np.where(x < 0.5, 1.0,
            np.where(x < 0.5 + tr, 1 - (x - 0.5) / tr, 0.0)))
        return des.Vdc + des.Vm * (2 * y - 1)
    raise ValueError(des.waveform)


def cap_coeffs(des: Design, K: int):
    """Fourier coefficients of the modulated capacitance C_n(t) for n = 0, 1, 2 (phase-shifted by n*120 deg)."""
    return [ck for ck, _ in mod_coeffs(des, K)]


def mod_coeffs(des: Design, K: int):
    """Fourier coefficients of the modulated capacitance of the three cells and the series loss resistance."""
    out = []
    for n in range(3):
        phi = des.direction * 2 * np.pi * n / 3
        if des.element == 'varactor':
            ck = fourier_coeffs(lambda th: des.var.C(varactor_drive(des, th - phi)), K)
            r = des.var.rv
        else:
            sw = des.sw or SwitchCap()
            if des.waveform == 'trap':
                tr = des.trise
                def on(th):
                    x = ((th / (2 * np.pi)) + 0.25) % 1.0
                    return np.where(x < tr, x / tr, np.where(x < 0.5, 1.0, np.where(x < 0.5 + tr, 1 - (x - 0.5) / tr, 0.0)))
                coff_eff = sw.Csw * sw.Coff / (sw.Csw + sw.Coff)
                ck = fourier_coeffs(lambda th: sw.Cpar + coff_eff + on(th - phi) * (sw.Csw - coff_eff), K)
            else:
                ck = fourier_coeffs(lambda th: sw.C((np.cos(th - phi) > 0).astype(float)), K)
            r = sw.Ron
        out.append((ck, r))
    return out


def build_network(des: Design, K: int) -> Network:
    """Topology 'A': nodes 1-3 ports, 4-6 tank, 7-9 modulator internal, 10-12 resonator internal.
       Topology 'C': nodes 1-3 ports, 4-6 resonator internal (after Rs), 7-9 node between resonator and modulator,
                     10-12 modulator internal (after its loss R), 13 star."""
    r = des.res
    mods = mod_coeffs(des, K)
    if des.topo == 'A':
        net = Network(nnodes=12)
        for n in range(3):
            P, T, V, Ri = 1 + n, 4 + n, 7 + n, 10 + n
            ck, rv = mods[n]
            net.port(P, des.z0); net.C(P, T, des.Cp)
            net.R(T, Ri, r.Rs); net.SER(Ri, 0, r.R0, 0.0, r.C0); net.SER(Ri, 0, r.Rm, r.Lm, r.Cm)
            net.R(T, V, rv); net.TVC(V, 0, ck)
            net.C(T, 4 + (n + 1) % 3, des.Cc)
        return net
    if des.topo == 'C':
        net = Network(nnodes=13); star = 13
        for n in range(3):
            P, Ri, M, V = 1 + n, 4 + n, 7 + n, 10 + n
            ck, rv = mods[n]
            net.port(P, des.z0)
            if des.Cp > 0: net.C(P, 0, des.Cp)
            net.R(P, Ri, r.Rs); net.SER(Ri, M, r.R0, 0.0, r.C0); net.SER(Ri, M, r.Rm, r.Lm, r.Cm)
            net.R(M, V, rv); net.TVC(V, star, ck)
        return net
    raise ValueError(des.topo)


def sparams(des: Design, freqs, K: int = 6):
    """S[f, k, m, n] over frequency list; k index = sideband + K."""
    net = build_network(des, K)
    out = np.zeros((len(freqs), 2 * K + 1, 3, 3), complex)
    for i, f in enumerate(freqs):
        out[i] = net.solve(f, des.fm, K)
    return out


def metrics(des: Design, f0: float, bw: float = 20e6, npts: int = 41, K: int = 6):
    """Insertion loss / isolation / return loss figures at f0 and over +/- bw/2."""
    f = np.linspace(f0 - bw / 2, f0 + bw / 2, npts)
    S = sparams(des, f, K)
    S0 = S[:, K]            # fundamental
    il_fwd = -db(np.array([S0[:, 1, 0], S0[:, 2, 1], S0[:, 0, 2]])).max(axis=0)   # worst of the three forward paths
    iso = -db(np.array([S0[:, 0, 1], S0[:, 1, 2], S0[:, 2, 0]])).min(axis=0)      # worst isolation
    rl = -db(np.array([S0[:, 0, 0], S0[:, 1, 1], S0[:, 2, 2]])).min(axis=0)
    return dict(f=f, IL=il_fwd, ISO=iso, RL=rl, S=S)
