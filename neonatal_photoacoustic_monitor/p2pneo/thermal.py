"""1-D Pennes bioheat model of the scalp/skull/brain under the probe.

rho c dT/dt = k d2T/dz2 + w_b rho_b c_b (T_art - T) + Q(z)
Q(z) = I_avg * mua(z) * Phi(z)/F0   (optical heating, W/cm^3)
Top boundary: probe contact; heat exchange with the probe/ambient through an effective
conductance h_top (W/m^2/K) plus electronic self-heating flux q_elec (W/cm^2).
Bottom boundary (3 cm): T = T_core.
"""
from __future__ import annotations
import numpy as np

# rho (kg/m3), c (J/kg/K), k (W/m/K), perfusion w (1/s)
THERMAL = {
    "scalp":      (1100.0, 3400.0, 0.40, 0.0010),
    "fontanelle": (1100.0, 3300.0, 0.45, 0.0005),
    "bone":       (1800.0, 1300.0, 0.40, 0.0002),
    "csf":        (1000.0, 4000.0, 0.60, 0.0000),
    "sinus":      (1050.0, 3800.0, 0.52, 0.0200),   # flowing venous blood: strong advective clearance
    "brain":      (1040.0, 3650.0, 0.50, 0.0040),
}
RHO_B, C_B = 1050.0, 3800.0


def simulate(layer_names, thick_cm, mua_z, phi_z, z_cm, I_avg_Wcm2, q_elec_Wcm2=0.0,
             h_top=8.0, T_amb=33.0, T_core=37.0, t_end_s=1200.0, dt=0.05, perf_scale=1.0):
    """Return (z, T(z) at t_end, T_skin(t), T_cortex(t), t)."""
    zmax = 3.0
    nz = 301
    z = np.linspace(0, zmax, nz) ; dz = (z[1] - z[0]) / 100.0           # m
    zb = np.concatenate([[0.0], np.cumsum(thick_cm)])
    lay = np.clip(np.searchsorted(zb, z, side="right") - 1, 0, len(thick_cm) - 1)
    names = [layer_names[i] for i in lay]
    rho = np.array([THERMAL[n][0] for n in names]); cp = np.array([THERMAL[n][1] for n in names])
    k = np.array([THERMAL[n][2] for n in names]); w = perf_scale * np.array([THERMAL[n][3] for n in names])
    Q = I_avg_Wcm2 * np.interp(z, z_cm, mua_z * phi_z, right=0.0) * 1e6       # W/m^3
    # baseline temperature profile (no source): solve steady state first
    T = np.full(nz, T_core)
    def step(T, dt):
        Tn = T.copy()
        flux = k[:-1] * 0.5 + k[1:] * 0.5
        d2 = np.zeros(nz)
        d2[1:-1] = (flux[1:] * (T[2:] - T[1:-1]) - flux[:-1] * (T[1:-1] - T[:-2])) / dz ** 2
        # top boundary: -k dT/dz = h (T_amb - T) + q_elec  (ghost node)
        qtop = h_top * (T_amb - T[0]) + q_elec_Wcm2 * 1e4
        d2[0] = (flux[0] * (T[1] - T[0]) / dz + qtop) / dz
        Tn = T + dt * (d2 + w * RHO_B * C_B * (T_core - T) + Q) / (rho * cp)
        Tn[-1] = T_core
        return Tn
    # stability
    dt = min(dt, 0.4 * dz ** 2 * (rho * cp / k).min())
    # equilibrate without the source
    Qs = Q.copy(); Q = np.zeros(nz)
    for _ in range(int(3600 / dt)):
        T = step(T, dt)
    Q = Qs
    nsteps = int(t_end_s / dt)
    rec = max(1, nsteps // 400)
    ts, Tskin, Tcx = [], [], []
    icx = int(np.searchsorted(z, zb[-2] + 0.1))
    T0 = T.copy()
    for i in range(nsteps):
        T = step(T, dt)
        if i % rec == 0:
            ts.append(i * dt); Tskin.append(T[0]); Tcx.append(T[icx])
    return z, T, T0, np.array(ts), np.array(Tskin), np.array(Tcx)
