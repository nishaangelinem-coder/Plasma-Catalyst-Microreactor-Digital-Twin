"""Supervisory controllers for renewable-powered plasma-catalytic NH3 production.

Task: every dt_h choose u = [V, f, Q, xH2] to maximise NH3 output under the
currently available renewable power P_cap(t) and a bed-temperature limit T_max
(catalyst protection). The power supply has a hardware limiter (P <= P_cap).

Baselines
    FixedSetpoint     offline DoE/model optimum, held constant (limiter curtails)
    ThermalPI         'run as hard as the thermal limit allows': PI on bed T via V
    ModelOptimizer    twin-in-the-loop optimiser with a deterministic twin
                      (static nominal model, or batch-recalibrated model)
Proposed
    ModelOptimizer(PCHDT, chance=True, degradation=True): risk-aware,
    degradation-aware economic optimisation over the twin ensemble.
"""
from __future__ import annotations

import itertools

import numpy as np

from . import twin_model as tm
from .plant import molar_flow, M_NH3

GRID = np.array(list(itertools.product(np.arange(6.0, 11.51, 0.25), [10.0, 15.0, 20.0, 25.0],
                                       [40.0, 60.0, 80.0, 100.0, 130.0, 160.0, 200.0],
                                       [0.5, 0.6, 0.7, 0.75, 0.8])))
PHI = tm.features(GRID)
MU_ENERGY = 0.2      # g-NH3 per kWh: marginal energy value (discourages useless power)
Z95 = 1.645


def evaluate_grid(theta, W, sig, grid=GRID, phi=PHI):
    out = tm.predict(grid, theta, return_all=True)
    corr = phi @ W                                   # (M, 3)
    y = out["y"] * np.exp(corr[:, 0])
    P = out["P"] * np.exp(corr[:, 1])
    T = out["T"] + corr[:, 2]
    mdot = y * molar_flow(grid[:, 2]) * M_NH3 * 3600.0
    return dict(y=y, P=P, T=T, mdot=mdot, a=np.exp(theta[:, 0])[:, None] * np.ones_like(P))


def optimise(theta, W, sig, P_cap, T_max, t_h, horizon_h, chance=True, degradation=True):
    ev = evaluate_grid(theta, W, sig)
    # Power is hard-limited by the supply (over-prediction only curtails, which is
    # safe), so it uses the expected value. Bed temperature is the safety state and
    # gets a chance constraint: P(T <= T_max) >= 95 % over parameter + model error.
    P_hi = ev["P"].mean(0)
    if chance and theta.shape[0] > 1:
        T_hi = np.quantile(ev["T"], 0.95, axis=0) + Z95 * sig[2]
    else:
        T_hi = ev["T"].mean(0)
    J = ev["mdot"].mean(0) - MU_ENERGY * ev["P"].mean(0) / 1000.0
    if degradation:
        rate = tm.deact_rate(ev["T"], ev["a"]) / np.maximum(ev["a"], 1e-3)   # 1/h relative
        J = J - (ev["mdot"] * rate).mean(0) * max(horizon_h - t_h, 0.0)
    feas = (P_hi <= P_cap) & (T_hi <= T_max)
    if not feas.any():
        return GRID[np.argmin(T_hi + 1e3 * np.maximum(P_hi - P_cap, 0))].copy()
    J = np.where(feas, J, -np.inf)
    return GRID[int(np.argmax(J))].copy()


class ModelOptimizer:
    def __init__(self, twin, T_max, horizon_h, chance=True, degradation=True, name=None):
        self.twin, self.T_max, self.H = twin, T_max, horizon_h
        self.chance, self.degr = chance, degradation
        self.name = name or f"Optimiser[{twin.name}]"

    def act(self, t_h, P_cap, last):
        th, W, sig = self.twin.ensemble()
        return optimise(th, W, sig, P_cap, self.T_max, t_h, self.H, self.chance, self.degr)

    def observe(self, u, z):
        self.twin.update(u, z)


class FixedSetpoint:
    def __init__(self, u_star, name="Fixed set-point (DoE optimum)"):
        self.u, self.name = np.asarray(u_star, float), name

    def act(self, t_h, P_cap, last):
        return self.u.copy()

    def observe(self, u, z):
        pass


class ThermalPI:
    def __init__(self, u_star, T_set, kp=0.02, ki=0.01, name="Thermal PI (max-load)"):
        self.u = np.asarray(u_star, float).copy()
        self.T_set, self.kp, self.ki, self.name = T_set, kp, ki, name
        self.e_prev = 0.0

    def act(self, t_h, P_cap, last):
        if last is not None:
            e = self.T_set - last["T_meas"]
            V_new = self.u[0] + self.kp * (e - self.e_prev) + self.ki * e
            # anti-windup: do not push V beyond what the limiter allows
            self.u[0] = float(np.clip(V_new, 6.0, min(11.5, last["V_applied"] + 0.5)))
            self.e_prev = e
        return self.u.copy()

    def observe(self, u, z):
        pass


def nominal_optimum(T_max, P_cap=50.0):
    """Offline optimum of the nominal model (what a DoE/model study would recommend)."""
    return optimise(tm.THETA0[None, :], np.zeros((tm.N_FEAT, tm.N_OUT)), np.zeros(3),
                    P_cap, T_max, 0.0, 0.0, chance=False, degradation=False)
