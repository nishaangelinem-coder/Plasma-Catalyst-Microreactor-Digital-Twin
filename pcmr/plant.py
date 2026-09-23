"""High-fidelity in-silico plant: DBD packed-bed plasma-catalytic NH3 microreactor.

The plant plays the role of the physical reactor in all experiments. It contains
physics the digital twins do NOT know exactly (structural mismatch) plus hidden,
time-varying degradation:

* Manley power law with composition-dependent burning voltage U_b(x_H2, t)
  and slow dielectric/packing ageing (U_b drift).
* Axially non-uniform filamentary power deposition and temperature profile,
  integrated over ``n_cells`` plug-flow cells.
* Plasma-catalytic (Langmuir-Hinshelwood on vibrationally excited N2) plus
  gas-phase radical NH3 formation; electron-impact and thermal-catalytic
  NH3 decomposition (gives the characteristic optimum in SEI).
* Frequency-dependent vibrational efficiency (V-T relaxation between pulses).
* Catalyst deactivation: hot-spot Arrhenius sintering (second order towards a
  residual activity) + plasma-induced surface nitridation, and an unannounced
  poisoning event (feed impurity) at ``poison_time_h``.
* Sensor noise on NH3 mole fraction (FTIR/MS), discharge power (Lissajous)
  and bed temperature (fibre-optic probe).
* A power-supply limiter that clamps the applied voltage so the discharge
  never exceeds the currently available (renewable) power.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

R_GAS = 8.314  # J mol-1 K-1
M_NH3 = 17.031  # g mol-1
V_MOLAR_STP = 22414.0  # cm3 mol-1 (273.15 K, 1 atm)


@dataclass
class PlantParams:
    # --- electrical (Manley) ---
    Cd: float = 40e-12          # dielectric capacitance, F
    Cg: float = 10e-12          # gap capacitance, F
    Ub0: float = 2.5            # burning voltage at x_H2 = 0.75, kV
    ub_comp: float = 0.30       # dU_b/U_b per unit (0.75 - x_H2)
    ub_drift_per_h: float = 4e-4  # relative U_b ageing per hour
    # --- geometry / thermal ---
    V_reactor: float = 1.0      # packed discharge volume, cm3
    void: float = 0.40          # bed void fraction
    T_wall: float = 300.0       # K
    Rth0: float = 3.2           # K/W (effective bed thermal resistance)
    Q_cool: float = 400.0       # sccm, convective-cooling scale
    rth_comp: float = 0.30      # H2 improves heat removal
    n_cells: int = 40
    power_decay: float = 1.2    # axial filament density ~ exp(-power_decay z)
    # --- kinetics ---
    k_pc0: float = 9.0          # plasma-catalytic pre-factor
    E_pc: float = 20e3          # effective (plasma-lowered) barrier, J/mol
    gamma: float = 0.8          # power-density order
    h2_order: float = 1.5       # H2 order of the surface route
    f_ref: float = 20.0         # kHz
    f_order: float = -0.15      # vibrational efficiency ~ (f/f_ref)^f_order
    k_g: float = 1.0e-3         # gas-phase radical route
    k_d: float = 0.20           # electron-impact NH3 destruction, per (W cm-3 s)
    k_r0: float = 3.1e9         # thermal-catalytic NH3 decomposition, s-1
    E_r: float = 80e3           # J/mol
    # --- deactivation ---
    ks0: float = 5.5e-3         # sintering constant at T_ref_s, h-1
    E_s: float = 60e3           # J/mol
    T_ref_s: float = 450.0      # K (hot-spot reference)
    a_inf: float = 0.35         # residual activity after sintering
    kn: float = 2.0e-5          # plasma nitridation, per (W cm-3 h)
    poison_time_h: float = 140.0
    poison_factor: float = 0.85
    # --- sensors ---
    sig_y_rel: float = 0.03
    sig_P_rel: float = 0.02
    sig_T: float = 2.0


@dataclass
class Inputs:
    V: float      # applied voltage amplitude, kV
    f: float      # frequency, kHz
    Q: float      # total flow, sccm
    xH2: float    # H2 inlet mole fraction (balance N2)

    def as_array(self) -> np.ndarray:
        return np.array([self.V, self.f, self.Q, self.xH2], dtype=float)


def manley_power(V, f, Ub, Cd, Cg):
    """Manley discharge power (W). V, Ub in kV; f in kHz."""
    k = (Cd + Cg) / Cd
    A = 4.0 * (f * 1e3) * Cd * (Ub * 1e3)
    return np.maximum(A * (V * 1e3 - k * Ub * 1e3), 0.0)


def manley_voltage_for_power(P, f, Ub, Cd, Cg):
    """Inverse Manley: voltage amplitude (kV) that gives discharge power P (W)."""
    k = (Cd + Cg) / Cd
    A = 4.0 * (f * 1e3) * Cd * (Ub * 1e3)
    return (P / A) / 1e3 + k * Ub


def molar_flow(Q_sccm):
    """Total molar flow, mol/s."""
    return Q_sccm / V_MOLAR_STP / 60.0


@dataclass
class PlantState:
    t_h: float = 0.0
    a: float = 1.0          # catalyst activity (hidden)
    poisoned: bool = False


@dataclass
class Plant:
    p: PlantParams = field(default_factory=PlantParams)
    seed: int = 0
    deact_scale: float = 1.0
    noise_scale: float = 1.0

    def __post_init__(self):
        self.rng = np.random.default_rng(self.seed)
        self.state = PlantState()
        n = self.p.n_cells
        z = (np.arange(n) + 0.5) / n
        w = np.exp(-self.p.power_decay * z)
        self._pw = w / w.mean()                       # axial power shape (mean 1)
        s = 1.0 + 0.6 * np.sin(np.pi * z)
        self._ts = s / s.mean()                       # axial temperature shape (mean 1)

    # ---------------------------------------------------------------- physics
    def burning_voltage(self, xH2, t_h=None):
        t_h = self.state.t_h if t_h is None else t_h
        p = self.p
        return p.Ub0 * (1.0 + p.ub_comp * (0.75 - xH2)) * (1.0 + p.ub_drift_per_h * t_h)

    def steady_state(self, u: Inputs, a=None, t_h=None, P_cap=None):
        """Quasi-steady reactor solution (residence time << control interval)."""
        p = self.p
        a = self.state.a if a is None else a
        Ub = self.burning_voltage(u.xH2, t_h)
        V = u.V
        P = float(manley_power(V, u.f, Ub, p.Cd, p.Cg))
        limited = False
        if P_cap is not None and P > P_cap:
            V = float(manley_voltage_for_power(P_cap, u.f, Ub, p.Cd, p.Cg))
            P = float(P_cap)
            limited = True
        Rth = p.Rth0 / (1.0 + u.Q / p.Q_cool) * (1.0 - p.rth_comp * (u.xH2 - 0.75))
        dT = Rth * P
        T_prof = p.T_wall + dT * self._ts
        T_mean = float(T_prof.mean())
        Pd = P / p.V_reactor * self._pw               # local power density, W/cm3
        Qact = u.Q / 60.0 * T_mean / 273.15           # cm3/s at bed temperature
        tau = p.void * p.V_reactor / Qact             # s
        dtau = tau / p.n_cells
        eta_f = (u.f / p.f_ref) ** p.f_order
        y = 0.0
        xN2_0, xH2_0 = 1.0 - u.xH2, u.xH2
        for i in range(p.n_cells):
            xN2 = max(xN2_0 - 0.5 * y, 1e-9)
            xH2 = max(xH2_0 - 1.5 * y, 1e-9)
            G = (a * p.k_pc0 * eta_f * np.exp(-p.E_pc / (R_GAS * T_prof[i]))
                 * Pd[i] ** p.gamma * xN2 * xH2 ** p.h2_order
                 + p.k_g * Pd[i] * xN2 * xH2)
            D = p.k_d * Pd[i] + a * p.k_r0 * np.exp(-p.E_r / (R_GAS * T_prof[i]))
            yeq = G / D if D > 0 else 0.0
            y = yeq + (y - yeq) * np.exp(-D * dtau) if D > 0 else y
        n_tot = molar_flow(u.Q)
        mdot_gph = y * n_tot * M_NH3 * 3600.0                 # g/h
        EY = mdot_gph / (P / 1000.0) if P > 0 else 0.0        # g/kWh
        SEI = P / (u.Q / 60.0 / 1000.0) / 1000.0 if u.Q > 0 else 0.0  # kJ/L
        X_N2 = y / (2.0 * xN2_0) if xN2_0 > 0 else 0.0
        return dict(V_applied=V, P=P, T_mean=T_mean, T_hot=float(T_prof.max()), y=y,
                    mdot_gph=mdot_gph, EY=EY, SEI=SEI, X_N2=X_N2, tau=tau,
                    Ub=Ub, limited=limited, Pd_mean=P / p.V_reactor)

    def _deactivate(self, ss, dt_h):
        p = self.p
        n_sub = 10
        h = dt_h / n_sub
        a = self.state.a
        kT = p.ks0 * self.deact_scale * np.exp(-p.E_s / R_GAS * (1.0 / ss["T_hot"] - 1.0 / p.T_ref_s))
        for _ in range(n_sub):
            ex = max(a - p.a_inf, 0.0)
            a -= h * (kT * ex ** 2 + self.deact_scale * p.kn * ss["Pd_mean"] * ex)
        self.state.a = a

    # ---------------------------------------------------------------- stepping
    def step(self, u: Inputs, dt_h: float, P_cap=None):
        """Operate for dt_h hours at inputs u; return true + measured outputs."""
        p = self.p
        if (not self.state.poisoned) and self.state.t_h >= p.poison_time_h:
            self.state.a *= p.poison_factor
            self.state.poisoned = True
        ss = self.steady_state(u, P_cap=P_cap)
        ns = self.noise_scale
        ss["y_meas"] = ss["y"] * (1.0 + ns * p.sig_y_rel * self.rng.standard_normal())
        ss["P_meas"] = ss["P"] * (1.0 + ns * p.sig_P_rel * self.rng.standard_normal())
        ss["T_meas"] = ss["T_mean"] + ns * p.sig_T * self.rng.standard_normal()
        ss["a_true"] = self.state.a
        ss["t_h"] = self.state.t_h
        self._deactivate(ss, dt_h)
        self.state.t_h += dt_h
        return ss
