"""NumPy reference implementation of the UCM-CFET compact model (see doc/model_spec.md).

The equations here are, line by line, the same as in the generated Verilog-A modules and the
ngspice behavioural library. This module is used for DC calibration (MAPE), figure-of-merit
extraction and fast parameter sweeps; the circuit-level results come from ngspice/Spectre.
"""
from __future__ import annotations
import numpy as np
from .platforms import Q, KB, G0, DEVICES, TRANSPORT_LANDAUER, eff_width

DELTA = 1e-3      # [V] smoothing of |Vds|
EPS = 1e-9        # [V] guard for divisions


def softplus(x):
    x = np.asarray(x, dtype=float)
    return np.where(x > 40.0, x, np.log1p(np.exp(np.minimum(x, 40.0))))


def smooth_abs(x):
    return np.sqrt(x * x + DELTA * DELTA)


def derived(p: dict, tdev):
    """Temperature-dependent and effective quantities shared by all branches."""
    W = eff_width(p)
    vt = KB * tdev / Q
    cox_eff = p["COX"] * p["CQ"] / (p["COX"] + p["CQ"])
    n = p["N0"] * (1.0 + Q * p["DIT"] / p["COX"])
    vth_t = p["VTH0"] + p["KVTH"] * (tdev - p["TNOM"])
    mu_t = p["MU0"] * (tdev / p["TNOM"]) ** (-p["MUEXP"]) if p["MU0"] > 0 else 0.0
    return W, vt, cox_eff, n, vth_t, mu_t


def id_intrinsic(vgs, vds, p: dict, transport: str, tdev):
    """Intrinsic channel current for the n-type convention (vgs, vds referenced to the
    *internal* source node). Odd in vds, smooth everywhere."""
    vgs = np.asarray(vgs, float); vds = np.asarray(vds, float)
    W, vt, cox_eff, n, vth_t, mu_t = derived(p, tdev)
    vds_abs = smooth_abs(vds)
    vth_eff = vth_t - p["ETA"] * vds_abs
    if transport == TRANSPORT_LANDAUER:
        # Landauer quasi-ballistic transport, N_tube semiconducting tubes in parallel
        eta_s = p["ALPHA"] * (vgs - vth_eff) / (n * vt)
        eta_d = eta_s - vds / (n * vt)
        itube = G0 * p["TTR"] * n * vt * (softplus(eta_s) - softplus(eta_d))
        ntube = p["DCNT"] * W * (1.0 - p["FMET"])
        gmet = p["FMET"] * p["DCNT"] * W * G0 * p["TTR"]           # metallic-tube shunt
        ids = ntube * itube * (1.0 + p["LAMBDA"] * vds_abs) + gmet * vds
        return ids
    # drift-diffusion with velocity saturation
    # EKV-type interpolation: Vov^2 ~ exp((Vgs-Vth)/(n Vt)) in weak inversion (SS = n Vt ln10)
    # and Vov -> Vgs - Vth in strong inversion.
    vov = 2.0 * n * vt * softplus((vgs - vth_eff) / (2.0 * n * vt))
    vsatv = p["VSAT"] * p["L"] / mu_t
    vdsat = vov / (1.0 + vov / vsatv)
    beta = mu_t * cox_eff * W / p["L"]
    isat = beta * vov * vov / (2.0 * (1.0 + vov / vsatv))
    ids = isat * np.tanh(2.0 * vds / (vdsat + EPS)) * (1.0 + p["LAMBDA"] * vds_abs)
    return ids


def charges(vgs, vgd, p: dict, tdev):
    """Terminal charges Q_gs(V_gs), Q_gd(V_gd) (n-type convention). Q_g = Q_gs + Q_gd and
    Q_s = -Q_gs, Q_d = -Q_gd so that Q_g + Q_d + Q_s = 0 by construction."""
    W, vt, cox_eff, n, vth_t, mu_t = derived(p, tdev)
    qch = 0.5 * W * p["L"] * cox_eff
    qgs = qch * 2.0 * n * vt * softplus((np.asarray(vgs, float) - vth_t) / (2.0 * n * vt)) + p["CGSO"] * W * vgs
    qgd = qch * 2.0 * n * vt * softplus((np.asarray(vgd, float) - vth_t) / (2.0 * n * vt)) + p["CGDO"] * W * vgd
    return qgs, qgd


def solve_series(icore, vgs, vds, rs, rd, iters=60):
    """Solve I = Icore(Vgs - I*Rs, Vds - I*(Rs+Rd)) by bracketed bisection (vectorised).
    f(I) = I - Icore(...) is monotonically increasing in I because dIcore/dVds >= 0 and
    dIcore/dVgs >= 0, and the root is bracketed by 0 and the short-circuit current
    Vds/(Rs+Rd); 60 halvings give ~1e-18 relative accuracy without any stability issue."""
    vgs = np.asarray(vgs, float); vds = np.asarray(vds, float)
    shape = np.broadcast(vgs, vds).shape
    rtot = rs + rd
    if rtot <= 0:
        return icore(vgs, vds)
    lo = np.minimum(np.zeros(shape), vds / rtot) * 1.0
    hi = np.maximum(np.zeros(shape), vds / rtot) * 1.0
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        f = mid - icore(vgs - mid * rs, vds - mid * rtot)
        pos = f > 0
        hi = np.where(pos, mid, hi); lo = np.where(pos, lo, mid)
    return 0.5 * (lo + hi)


def id_terminal(vg, vd, vs, name_or_dev, tamb_c=27.0, params: dict | None = None):
    """Extrinsic drain current I(d->s) of a complete device (series resistances and, for
    GaN, quasi-static self-heating T_dev = T_amb + RTH*I*Vds_int) for arbitrary terminal
    voltages (arrays broadcast). The Verilog-A/ngspice versions let the circuit solver do this."""
    dev = DEVICES[name_or_dev] if isinstance(name_or_dev, str) else name_or_dev
    p = dict(dev["params"]); p.update(params or {})
    sign = 1.0 if dev["polarity"] == "n" else -1.0
    vg = np.asarray(vg, float); vd = np.asarray(vd, float); vs = np.asarray(vs, float)
    vgs = sign * (vg - vs); vds = sign * (vd - vs)
    W = eff_width(p)
    rs, rd = p["RSW"] / W, p["RDW"] / W
    tamb = tamb_c + 273.15

    def icore(vgsi, vdsi):
        if p["RTH"] > 0:   # quasi-static self-heating: inner fixed point on temperature
            tdev = np.full(np.broadcast(vgsi, vdsi).shape, tamb)
            for _ in range(25):
                i = id_intrinsic(vgsi, vdsi, p, dev["transport"], tdev)
                tdev = 0.5 * tdev + 0.5 * (tamb + p["RTH"] * np.abs(i * vdsi))
            return id_intrinsic(vgsi, vdsi, p, dev["transport"], tdev)
        return id_intrinsic(vgsi, vdsi, p, dev["transport"], tamb)

    return sign * solve_series(icore, vgs, vds, rs, rd)


# ---------------------------------------------------------------- figures of merit -----
def fom(vg, id_lin, id_sat, vdd, vds_lin, vds_sat, width):
    """Ion/Ioff/SS/DIBL/gm from Id-Vg data (currents in A, width in m). Returns dict in
    engineering units (A/um, mV/dec, mV/V, uS/um)."""
    vg = np.asarray(vg); idl = np.abs(np.asarray(id_lin)); ids = np.abs(np.asarray(id_sat))
    wum = width * 1e6
    ion = np.interp(vdd, vg, ids) / wum
    ioff = np.interp(0.0, vg, ids) / wum
    logi = np.log10(np.maximum(ids, 1e-30))
    # SS: minimum slope in the decade range 10^-9 .. 10^-6 A/um
    sel = (ids / wum > 1e-10) & (ids / wum < 1e-7)
    if sel.sum() > 3:
        ss = 1e3 / np.max(np.gradient(logi[sel], vg[sel]))
    else:
        ss = float("nan")
    # constant-current Vth at 100 nA x Weff/L-ish -> use 1e-7 A/um
    def vth_cc(curve):
        thr = 1e-7 * wum
        idx = np.where(curve >= thr)[0]
        if len(idx) == 0 or idx[0] == 0:
            return float("nan")
        k = idx[0]
        return vg[k - 1] + (thr - curve[k - 1]) * (vg[k] - vg[k - 1]) / (curve[k] - curve[k - 1])
    vth_l, vth_s = vth_cc(idl), vth_cc(ids)
    dibl = (vth_l - vth_s) / (vds_sat - vds_lin) * 1e3
    gm = np.max(np.gradient(ids, vg)) / wum * 1e6
    return dict(Ion_A_per_um=ion, Ioff_A_per_um=ioff, SS_mV_dec=ss, DIBL_mV_V=dibl,
                Vth_lin_V=vth_l, Vth_sat_V=vth_s, gm_max_uS_um=gm, Ion_Ioff=ion / max(ioff, 1e-30))


def mape(model, ref, floor=None):
    model = np.asarray(model, float); ref = np.asarray(ref, float)
    if floor is not None:
        sel = np.abs(ref) > floor
        model, ref = model[sel], ref[sel]
    return 100.0 * np.mean(np.abs((model - ref) / ref))
