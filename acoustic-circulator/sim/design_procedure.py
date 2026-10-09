"""CMT-guided design procedure for topology A (parallel-mode loop with shunt varactors).
For a given (varactor multiplicity, Cp) the unmodulated network gives gamma_e (loaded bandwidth of the
degenerate pair) and the l=0 offset (-> kappa); Cc is adjusted so 3|kappa| = 36 gamma_e, fm = wm_ratio*gamma_e,
and the modulated response is evaluated at the degenerate-pair frequency with the operating frequency refined."""
import os, sys, json
import numpy as np
from dataclasses import replace
from scipy.optimize import brentq, minimize_scalar
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim.circulator import Design, Resonator, Varactor, sparams
from sim.ltp import db
from sim.topologies import figures_of_merit, point_cost


def unmod_modes(des, fwin=(0.85e9, 1.15e9)):
    """Return (f_deg, bw3dB of the degenerate pair, f_l0) from the unmodulated response."""
    d0 = replace(des, Vm=0.0)
    f = np.linspace(*fwin, 3001)
    S = sparams(d0, f, 0)[:, 0]
    t = np.abs(S[:, 1, 0])
    # degenerate pair: the transmission peak; l=0: the S11 phase-only resonance (no transmission) -> find S11 min of dip of |S21|? use |S11| local minima
    i = int(np.argmax(t)); f_deg = f[i]
    half = t >= t[i] / np.sqrt(2)
    # contiguous region around i
    lo = i
    while lo > 0 and half[lo - 1]: lo -= 1
    hi = i
    while hi < len(f) - 1 and half[hi + 1]: hi += 1
    bw = f[hi] - f[lo]
    # l=0 mode: a symmetric excitation; compute response to in-phase excitation of all ports: sum_n S_mn
    sym = np.abs(S[:, 0, 0] + S[:, 0, 1] + S[:, 0, 2])      # reflection of symmetric mode (|.|=1 if lossless); its phase flips at l=0
    ph = np.unwrap(np.angle(S[:, 0, 0] + S[:, 0, 1] + S[:, 0, 2]))
    j = int(np.argmax(np.abs(np.gradient(ph)))); f_l0 = f[j]
    return f_deg, bw, f_l0


def design(mult=1.0, Cp=1.0e-12, Vm=0.5, wm_ratio=15.0, kappa_ratio=12.0, Qm=500.0, fs=0.96e9, verbose=False):
    des = Design(Resonator(fs=fs, Qm=Qm), Varactor(mult=mult), Cp=Cp, Cc=0.3e-12, Vm=Vm, fm=20e6, Vdc=0.25, waveform='square')
    # loaded gamma_e from the degenerate pair bandwidth (total gamma = pi*bw; gamma_e = gamma - gamma_i; approximate gamma_e ~ gamma)
    f_deg, bw, f_l0 = unmod_modes(des)
    gamma = np.pi * bw                                   # total amplitude decay rate (rad/s)
    # adjust Cc so that |f_l0 - f_deg| = 3*kappa_ratio*gamma/(2pi)
    target = 3 * kappa_ratio * gamma / (2 * np.pi)
    def g(logCc):
        d = replace(des, Cc=10 ** logCc)
        fd, b, fl0 = unmod_modes(d)
        return abs(fl0 - fd) - target
    try:
        lc = brentq(g, np.log10(0.02e-12), np.log10(5e-12), xtol=1e-3)
    except ValueError:
        lc = np.log10(5e-12)
    des = replace(des, Cc=10 ** lc)
    f_deg, bw, f_l0 = unmod_modes(des); gamma = np.pi * bw
    fm = wm_ratio * gamma / (2 * np.pi)
    des = replace(des, fm=fm)
    # evaluate: scan around f_deg for best cost
    f = np.linspace(f_deg - 6 * gamma / 2 / np.pi, f_deg + 6 * gamma / 2 / np.pi, 241)
    S = sparams(des, f, 5)[:, 5]
    IL, ISO, RL, sense = figures_of_merit(S)
    c = point_cost(IL, ISO, RL); i = int(np.argmin(c))
    out = dict(mult=mult, Cp=Cp, Cc=des.Cc, Vm=Vm, fm=fm, f_deg=f_deg, bw=bw, f_l0=f_l0, gamma_MHz=gamma / 2 / np.pi / 1e6,
               Qload=f_deg / bw, f_op=f[i], IL=IL[i], ISO=ISO[i], RL=RL[i], cost=c[i], sense=sense)
    if verbose: print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in out.items()})
    return out, des


if __name__ == '__main__':
    best = None
    for mult in (0.5, 1.0, 2.0):
        for Cp in (0.3e-12, 0.6e-12, 1.0e-12, 1.5e-12, 2.5e-12):
            for wm in (5.0, 10.0, 15.0):
                o, d = design(mult, Cp, 0.5, wm)
                print(f"mult={mult} Cp={Cp*1e12:.1f}pF wm/ge={wm}: Cc={o['Cc']*1e12:.2f}pF gamma={o['gamma_MHz']:.2f}MHz Qload={o['Qload']:.0f} fm={o['fm']/1e6:.1f}MHz f_op={o['f_op']/1e6:.1f} IL={o['IL']:.2f} ISO={o['ISO']:.1f} RL={o['RL']:.1f} cost={o['cost']:.2f}")
                if best is None or o['cost'] < best['cost']: best = o
    print('BEST', best)
    json.dump(best, open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results', 'design_procedure_scan.json'), 'w'), indent=1, default=float)
