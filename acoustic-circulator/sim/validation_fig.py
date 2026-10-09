"""Solver validation figure: (a) single modulated capacitor sideband vs analytic; (b) weakly coupled lumped loop: LTP vs CMT."""
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim.ltp import Network, db
from sim.cmt import cmt_sparams
from sim.plotstyle import plt, PAL, COL2
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); FIG = os.path.join(ROOT, 'figures')
fig, ax = plt.subplots(1, 2, figsize=(COL2, 2.4))
# (a) sideband ratio vs modulation index for a series modulated capacitor
K = 4; C0 = 0.1e-12; fm = 37.5e6; f = 1e9
ms = np.linspace(0.02, 0.6, 15); num = []; ana = []
for mi in ms:
    net = Network(nnodes=2); net.port(1, 50); net.port(2, 50)
    ck = np.zeros(2 * K + 1, complex); ck[K] = C0; ck[K + 1] = mi * C0 / 2; ck[K - 1] = mi * C0 / 2
    net.TVC(1, 2, ck); S = net.solve(f, fm, K)
    num.append(db(S[K + 1, 1, 0]) - db(S[K, 1, 0])); ana.append(20 * np.log10(mi / 2 * (f + fm) / f))
ax[0].plot(ms, ana, color=PAL[1], label='analytic $(m/2)(f+f_m)/f$')
ax[0].plot(ms, num, 'o', ms=3, color=PAL[0], label='LTP solver')
ax[0].set(xlabel='Modulation index $m=\\Delta C/C_0$', ylabel='Upper sideband / carrier (dB)', title='(a) Modulated-capacitor sideband check'); ax[0].legend()
# (b) weak loop
w0 = 2 * np.pi * 1e9; Ct = 3e-12; Lt = 1 / (w0 ** 2 * Ct); Cc = 0.02e-12; Cp = 0.08e-12; K = 8
Ctot = Ct + Cp + 2 * Cc; w0c = 1 / np.sqrt(Lt * Ctot); ge = (w0c * Cp) ** 2 * 50 / (2 * Ctot)
fmw = 15 * ge / 2 / np.pi; dC1 = 5.6 * ge * 2 * Ctot / w0c
w00 = 1 / np.sqrt(Lt * (Ct + Cp)); w1 = 1 / np.sqrt(Lt * (Ct + Cp + 3 * Cc)); kappa = (w00 - w1) / 3; w0cmt = w00 - 2 * kappa
net = Network(nnodes=6)
for n in range(3):
    P, T = 1 + n, 4 + n; net.port(P, 50); net.C(P, T, Cp); net.L(T, 0, Lt)
    ck = np.zeros(2 * K + 1, complex); ck[K] = Ct; phi = 2 * np.pi * n / 3
    ck[K + 1] = dC1 / 2 * np.exp(-1j * phi); ck[K - 1] = dC1 / 2 * np.exp(1j * phi)
    net.TVC(T, 0, ck); net.C(T, 4 + (n + 1) % 3, Cc)
fs = np.linspace(w1 / 2 / np.pi - 2.5e6, w1 / 2 / np.pi + 2.5e6, 501)
Sl = np.array([net.solve(ff, fmw, K)[K] for ff in fs]); Sc = np.array([cmt_sparams(ff, w0cmt, 0.0, ge, kappa, w0c * dC1 / (2 * Ctot), fmw, K=K)[K] for ff in fs])
ax[1].plot(fs / 1e6, db(Sl[:, 2, 0]), color=PAL[0], label='S31 circuit (LTP)')
ax[1].plot(fs / 1e6, db(Sc[:, 2, 0]), color=PAL[0], ls='--', label='S31 CMT')
ax[1].plot(fs / 1e6, db(Sl[:, 1, 0]), color=PAL[1], label='S21 circuit (LTP)')
ax[1].plot(fs / 1e6, db(Sc[:, 1, 0]), color=PAL[1], ls='--', label='S21 CMT')
ax[1].plot(fs / 1e6, db(Sl[:, 0, 0]), color=PAL[6], label='S11 circuit')
ax[1].set(xlabel='Frequency (MHz)', ylabel='|S| (dB)', ylim=(-50, 1), title='(b) Lumped loop at the CMT optimum: LTP vs CMT'); ax[1].legend(fontsize=6)
fig.tight_layout(); fig.savefig(os.path.join(FIG, 'fig_validation.png')); fig.savefig(os.path.join(FIG, 'fig_validation.pdf'))
print('validation figure written; weak loop: LTP S31 min %.1f dB, CMT %.1f dB' % (db(Sl[:, 2, 0]).min(), db(Sc[:, 2, 0]).min()))
