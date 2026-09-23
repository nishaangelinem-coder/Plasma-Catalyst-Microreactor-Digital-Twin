"""Reduced-order (0-D, lumped) physics model used inside the digital twins.

Deliberately simpler than the plant (typical of a real-time twin):
uniform power/temperature, analytic CSTR-in-series-free solution
y = G/D (1 - exp(-D tau)), first-order H2 dependence, no frequency effect,
composition-independent burning voltage and thermal resistance.

Uncertain / time-varying parameters theta (estimated online):
    theta[0] = ln a      catalyst activity
    theta[1] = dUb       burning-voltage shift, kV
    theta[2] = ln Rth    effective thermal resistance, K/W
Everything is vectorised: ``u`` has shape (M, 4) = [V, f, Q, xH2] and
``theta`` shape (N, 3); outputs broadcast to (N, M).
"""
from __future__ import annotations

import numpy as np

from .plant import R_GAS, M_NH3, molar_flow

NOMINAL = dict(Cd=40e-12, Cg=10e-12, Ub0=2.5, V_reactor=1.0, void=0.40, T_wall=300.0,
               Q_cool=400.0, k_pc0=9.0, E_pc=20e3, gamma=0.8, k_g=1.0e-3, k_d=0.20,
               k_r0=3.1e9, E_r=80e3,
               # nominal deactivation model (from literature-type accelerated tests)
               ks0=5.5e-3, E_s=60e3, T_ref_s=430.0, a_inf=0.35)
THETA0 = np.array([0.0, 0.0, np.log(3.0)])   # nominal: fresh catalyst, no ageing, Rth=3.0
N_OUT = 3                                     # [ln y, ln P, T]


def _as2d(x, n):
    x = np.asarray(x, dtype=float)
    return x.reshape(-1, n) if x.ndim == 1 else x


def predict(u, theta, prm=NOMINAL, return_all=False):
    u = _as2d(u, 4)
    theta = _as2d(theta, 3)
    V, f, Q, xH2 = (u[None, :, i] for i in range(4))
    lna, dUb, lnR = (theta[:, None, i] for i in range(3))
    a = np.exp(lna)
    Ub = prm["Ub0"] + dUb
    k = (prm["Cd"] + prm["Cg"]) / prm["Cd"]
    P = np.maximum(4.0 * f * 1e3 * prm["Cd"] * Ub * 1e3 * (V - k * Ub) * 1e3, 1e-3)
    T = prm["T_wall"] + np.exp(lnR) * P / (1.0 + Q / prm["Q_cool"])
    Pd = P / prm["V_reactor"]
    tau = prm["void"] * prm["V_reactor"] / (Q / 60.0 * T / 273.15)
    xN2 = 1.0 - xH2
    G = (a * prm["k_pc0"] * np.exp(-prm["E_pc"] / (R_GAS * T)) * Pd ** prm["gamma"] * xN2 * xH2
         + prm["k_g"] * Pd * xN2 * xH2)
    D = prm["k_d"] * Pd + a * prm["k_r0"] * np.exp(-prm["E_r"] / (R_GAS * T))
    y = np.maximum(G / D * (1.0 - np.exp(-D * tau)), 1e-9)
    if not return_all:
        return np.log(y), np.log(P), T
    mdot = y * molar_flow(Q) * M_NH3 * 3600.0
    return dict(y=y, P=P, T=T, mdot=mdot, a=a * np.ones_like(P))


def deact_rate(T, a, prm=NOMINAL):
    """Nominal twin deactivation rate da/dt (1/h) at bed-mean temperature T."""
    ex = np.maximum(a - prm["a_inf"], 0.0)
    return prm["ks0"] * np.exp(-prm["E_s"] / R_GAS * (1.0 / T - 1.0 / prm["T_ref_s"])) * ex ** 2


# ------------------------------------------------------------ residual features
# Centred, bias-free polynomial features of normalised inputs. No constant term,
# so the residual cannot absorb a uniform offset: level shifts are left to the
# physical parameter (activity), keeping the physics identifiable.
def features(u):
    u = _as2d(u, 4)
    v = (u[:, 0] - 9.0) / 2.5
    fq = (u[:, 1] - 17.5) / 7.5
    q = (np.log(u[:, 2]) - np.log(90.0)) / 0.8
    r = (u[:, 3] - 0.675) / 0.175
    c = 1.0 / 3.0
    return np.stack([v, fq, q, r, v * v - c, fq * fq - c, q * q - c, r * r - c,
                     v * q, v * r, q * r, fq * v, fq * r], axis=1)


N_FEAT = 13
