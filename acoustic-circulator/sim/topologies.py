"""
Candidate circuit topologies for the STM acoustic circulator, all built on the LTP solver.

  'A'  parallel-mode loop   : port -Cp- tank node ; mBVD to gnd ; shunt modulated cap to gnd ; ring Cc  (Estep-type)
  'B'  series-mode delta    : port n -[mBVD + modulated cap]- port n+1 ; shunt Csh at each port        (bandpass delta)
  'C'  series-mode wye      : port n -[mBVD + modulated cap]- floating star node ; shunt Csh at ports  (resonant junction)

Modulating element:
  'varactor' : A-MOS varactor, smooth C-V (Varactor class), square-wave gate drive
  'switch'   : switched MIM capacitor (C_sw in series with an nMOS switch); C(t) toggles between
               C_on = C_sw*Cgs/(C_sw+Cgs) ~ C_sw and C_off = C_sw*Coff/(C_sw+Coff); loss R_on when on.
"""
from __future__ import annotations
import numpy as np
from dataclasses import dataclass, replace
from .ltp import Network, fourier_coeffs, db
from .circulator import Resonator, Varactor, Design, varactor_drive


@dataclass
class SwitchCap:
    """Switched MIM capacitor: C_sw [F] in series with an nMOS switch of width W [um]."""
    Csw: float = 1.0e-12
    W: float = 300.0                 # um
    Cpar: float = 0.0                # fixed MIM in parallel with the switched branch
    ron_w: float = 350.0             # ohm*um  (65 nm nMOS, VGS=1.2 V, thick-oxide-free)
    coff_w: float = 0.6e-15          # F/um    (drain-bulk + overlap)
    @property
    def Ron(self): return self.ron_w / self.W
    @property
    def Coff(self): return self.coff_w * self.W
    def C(self, on):
        return self.Cpar + np.where(on > 0.5, self.Csw, self.Csw * self.Coff / (self.Csw + self.Coff))


@dataclass
class Candidate:
    topo: str = 'A'
    element: str = 'varactor'
    res: Resonator = None
    var: Varactor = None
    sw: SwitchCap = None
    Cp: float = 1.0e-12      # 'A': port coupling cap ; 'B','C': shunt matching cap at the port
    Cc: float = 0.3e-12      # 'A' only: ring coupling cap
    fm: float = 25e6
    Vm: float = 0.5          # varactor drive half-swing (VDDM = 2 Vm)
    Vdc: float = 0.25
    direction: int = +1
    z0: float = 50.0

    def design(self):
        return Design(self.res, self.var, Cp=self.Cp, Cc=self.Cc, fm=self.fm, Vdc=self.Vdc, Vm=self.Vm, waveform='square', direction=self.direction)


def mod_coeffs(c: Candidate, K: int):
    """Fourier coefficients of the modulated capacitance for the 3 cells + series loss resistance."""
    out = []
    for n in range(3):
        phi = c.direction * 2 * np.pi * n / 3
        if c.element == 'varactor':
            d = c.design()
            ck = fourier_coeffs(lambda th: c.var.C(varactor_drive(d, th - phi)), K)
            r = c.var.rv
        else:
            ck = fourier_coeffs(lambda th: c.sw.C((np.cos(th - phi) > 0).astype(float)), K)
            r = c.sw.Ron            # (approximation: loss applies in both states; conservative)
        out.append((ck, r))
    return out


def build(c: Candidate, K: int) -> Network:
    from .circulator import build_network, SwitchCap as SC
    sw = None
    if c.element == 'switch':
        sw = SC(Csw=c.sw.Csw, W=c.sw.W, Cpar=c.sw.Cpar, ron_w=c.sw.ron_w, coff_w=c.sw.coff_w)
    d = Design(c.res, c.var, Cp=c.Cp, Cc=c.Cc, fm=c.fm, Vdc=c.Vdc, Vm=c.Vm, waveform='square', direction=c.direction,
               topo=c.topo, element=c.element, sw=sw, z0=c.z0)
    return build_network(d, K)


def sweep(c: Candidate, freqs, K=4):
    net = build(c, K)
    return np.array([net.solve(f, c.fm, K) for f in freqs])


def figures_of_merit(S0):
    """S0: (..., 3, 3) fundamental S. Returns IL, ISO, RL (dB, positive) choosing the better circulation sense."""
    fwd = np.stack([S0[..., 1, 0], S0[..., 2, 1], S0[..., 0, 2]]); rev = np.stack([S0[..., 0, 1], S0[..., 1, 2], S0[..., 2, 0]])
    il1 = -db(fwd).max(axis=0); il2 = -db(rev).max(axis=0)
    iso1 = -db(rev).min(axis=0); iso2 = -db(fwd).min(axis=0)
    use1 = il1.mean() <= il2.mean()
    IL = il1 if use1 else il2; ISO = iso1 if use1 else iso2
    RL = -db(np.stack([S0[..., 0, 0], S0[..., 1, 1], S0[..., 2, 2]])).min(axis=0)
    return IL, ISO, RL, (+1 if use1 else -1)


def point_cost(IL, ISO, RL, iso_target=30.0, rl_target=15.0):
    return IL + 0.3 * np.maximum(0, iso_target - ISO) + 0.2 * np.maximum(0, rl_target - RL)


def best_operating_point(c: Candidate, fwin=(0.85e9, 1.10e9), coarse=1.0e6, fine=0.1e6, K=4):
    """Coarse sweep, pick best cost, refine locally. Returns (f_best, IL, ISO, RL, cost)."""
    f = np.arange(fwin[0], fwin[1] + coarse / 2, coarse)
    S = sweep(c, f, K)[:, K]
    IL, ISO, RL, _ = figures_of_merit(S)
    cst = point_cost(IL, ISO, RL)
    i = int(np.argmin(cst))
    f2 = np.arange(f[i] - coarse, f[i] + coarse + fine / 2, fine)
    S2 = sweep(c, f2, K)[:, K]
    IL2, ISO2, RL2, _ = figures_of_merit(S2)
    c2 = point_cost(IL2, ISO2, RL2)
    j = int(np.argmin(c2))
    return f2[j], IL2[j], ISO2[j], RL2[j], c2[j]
