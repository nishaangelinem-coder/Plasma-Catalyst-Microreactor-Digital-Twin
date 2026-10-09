"""
oscillator_design.py -- Sustaining-amplifier co-design for the two-port SiN-LN
phononic ring resonator (180-nm bulk CMOS, VDD = 1.8 V).

Topologies evaluated with the SAME resonator model:

  (A) Pierce (parallel-resonance; the IDT C0's act as C1/C2).  Shown to be
      infeasible: k_eff^2 ~ 5e-6 gives an inductive window of only ~2 Hz.
  (B) Transmission-mode (series-resonance) differential sustaining amplifier:

        port-2 IDT --[L_in || C0]--> common-gate pair --[LC tank]--> gain stage
        --> source-follower drivers --[L_out || C0]--> port-1 IDT

      * L_in / L_out resonate the IDT static capacitance at each port so the
        motional current is not shunted by C0 and the driver does not have to
        supply the reactive current of C0 (this is the co-design lever that
        turns the 28-dB "50-ohm insertion loss" into a ~0.5-dB loop loss).
      * the stage-1 tank gives a large transimpedance at 1 GHz (noise) and a
        varactor on it serves as the loop phase trim (mode selection).

Every number is re-derived from the resonator mBVD values and from the
transistor gm/ID operating points, so the design is transparent and can be
ported to any PDK (see cadence/).
"""
from __future__ import annotations
import numpy as np
from dataclasses import dataclass, asdict, replace
from ring_model import (RingParams, calibrate_to_measurement, two_port_Y, shunt_inductor_Y,
                        insertion_gain_general, Z0, kB)

T_K = 300.0
GAMMA = 1.3          # short-channel excess-noise factor (180 nm)


@dataclass
class AmpDesign:
    vdd: float = 1.8
    # ---- port inductors (0 -> none) ----
    L_in: float = 29.8e-9;   Q_Lin: float = 8.0      # across port 2 (TIA input)
    L_out: float = 29.8e-9;  Q_Lout: float = 8.0     # across port 1 (driver output)
    # ---- stage 1: common-gate differential pair with LC-tank load ----
    I1: float = 3.0e-3;  gm_id1: float = 10.0
    L_t: float = 60e-9;  Q_t: float = 8.0;  tank_detune: float = 0.0   # differential tank L, Q, (f_t-f0)/f0
    C_t_par: float = 0.35e-12                        # parasitic + varactor capacitance (differential)
    # ---- stage 2: differential pair with a second LC tank (zero phase at resonance) ----
    I2: float = 3.0e-3;  gm_id2: float = 10.0
    L_t2: float = 40e-9;  Q_t2: float = 8.0;  tank2_detune: float = 0.0
    k_impl: float = 1.0                                   # implementation factor on Z_T (calibrated from transistor-level sim)
    # ---- stage 4: source-follower drivers ----
    I4: float = 2.0e-3;  gm_id4: float = 10.0;  fp4: float = 5.0e9
    # ---- misc ----
    Cpar_in: float = 60e-15            # pad/ESD parasitic per side at the TIA input
    phase_trim_deg: float = 0.0        # extra trim (varactor phase interpolator)
    polarity: int = +1                 # +1 / -1 : wiring of the differential loop
    v_lim: float = 0.70                # differential peak swing limit at port 1 (stage-2 limiting x SF gain)

    @property
    def gm1(self): return self.gm_id1 * self.I1
    @property
    def gm2(self): return self.gm_id2 * self.I2
    @property
    def gm4(self): return self.gm_id4 * self.I4
    @property
    def Zin_diff(self): return 2.0 / self.gm1
    @property
    def Zout_diff(self): return 2.0 / self.gm4
    @property
    def Rp_tank2(self): return self.Q_t2 * 2 * np.pi * 1.00115e9 * self.L_t2
    @property
    def A2(self): return self.gm2 * self.Rp_tank2
    @property
    def A4(self): return 0.85
    @property
    def P_dc(self): return self.vdd * 2 * (self.I1 + self.I2 + self.I4)
    @property
    def Rp_tank(self): return self.Q_t * 2 * np.pi * 1.00115e9 * self.L_t

    def Z_tank(self, f, f0, which=1):
        """Differential parallel-RLC tank tuned to f0*(1+detune)."""
        f = np.asarray(f, float)
        w = 2 * np.pi * f
        L, Q, det = (self.L_t, self.Q_t, self.tank_detune) if which == 1 else (self.L_t2, self.Q_t2, self.tank2_detune)
        ft = f0 * (1 + det)
        Ct = 1 / ((2 * np.pi * ft) ** 2 * L)
        Rp = Q * 2 * np.pi * ft * L
        Y = 1 / Rp + 1j * w * Ct + 1 / (1j * w * L)
        return 1 / Y

    def ZT(self, f, f0):
        """Differential transimpedance V_out,diff / I_in,diff of the chain."""
        f = np.asarray(f, float)
        H = self.k_impl * self.Z_tank(f, f0) * self.gm2 * self.Z_tank(f, f0, 2) * self.A4 / (1 + 1j * f / self.fp4)
        return self.polarity * H * np.exp(1j * np.deg2rad(self.phase_trim_deg))


# --------------------------------------------------------------------------
#  (A) Pierce feasibility
# --------------------------------------------------------------------------
def pierce_analysis(p: RingParams):
    m = p.mbvd()
    gm_crit = p.w0 ** 2 * p.C0 * p.C0 * m["Rm"]
    fp = p.f0 * np.sqrt(1 + m["Cm"] / p.C0)
    return dict(gm_crit_mS=gm_crit * 1e3, gm_3x_mS=3e3 * gm_crit, I_3x_mA=3e3 * gm_crit / 12.5,
                P_3x_mW=1.8 * 3e3 * gm_crit / 12.5, fs_Hz=p.f0, fp_Hz=fp,
                inductive_window_Hz=fp - p.f0, keff2=m["keff2"], Cm_C0_ratio=m["Cm"] / p.C0)


# --------------------------------------------------------------------------
#  (B) Transmission-mode loop
# --------------------------------------------------------------------------
def _res_kw(amp: AmpDesign):
    return dict(Lres1=amp.L_out or None, Lres2=amp.L_in or None, QL=amp.Q_Lin)


def resonator_transfer_admittance(p: RingParams, f, Zs, Zl, **kw):
    """I2/Vs for a Thevenin source (Vs, Zs) at port 1 and a load Zl at port 2
    (I2 flows into the load)."""
    Y = two_port_Y(p, f, **kw)
    Z = np.linalg.inv(Y)
    Z11, Z12, Z21, Z22 = Z[:, 0, 0], Z[:, 0, 1], Z[:, 1, 0], Z[:, 1, 1]
    return -Z21 / ((Z11 + Zs) * (Z22 + Zl) - Z12 * Z21)


def port2_source_admittance(p: RingParams, f, Zs, **kw):
    """Admittance looking back into port 2 with port 1 terminated by Zs."""
    Y = two_port_Y(p, f, **kw)
    Z = np.linalg.inv(Y)
    Z11, Z12, Z21, Z22 = Z[:, 0, 0], Z[:, 0, 1], Z[:, 1, 0], Z[:, 1, 1]
    return 1 / (Z22 - Z12 * Z21 / (Z11 + Zs))


def loop_gain(p: RingParams, amp: AmpDesign, f, comb=False, spurs=True, envelope=True):
    f = np.asarray(f, float)
    w = 2 * np.pi * f
    Zs = amp.Zout_diff + 0j
    Ycg = 1 / amp.Zin_diff
    Ypar = 1j * w * amp.Cpar_in / 2
    Zl = 1 / (Ycg + Ypar)
    Yt = resonator_transfer_admittance(p, f, Zs, Zl, comb=comb, spurs=spurs, envelope=envelope, **_res_kw(amp))
    div = Ycg / (Ycg + Ypar)             # share of the port-2 current entering the CG devices
    return amp.ZT(f, p.f0) * Yt * div


def auto_phase_trim(p: RingParams, amp: AmpDesign):
    """Choose loop polarity and the residual trim so that the loop phase is 0 at f0.
    Returns a new AmpDesign and the trim required (deg)."""
    a = replace(amp, polarity=+1, phase_trim_deg=0.0)
    ph = np.degrees(np.angle(loop_gain(p, a, np.array([p.f0]))[0]))
    if abs(ph) > 90:
        a = replace(a, polarity=-1)
        ph = np.degrees(np.angle(loop_gain(p, a, np.array([p.f0]))[0]))
    a = replace(a, phase_trim_deg=-ph)
    return a, -ph


def loop_gain_summary(p: RingParams, amp: AmpDesign):
    T0 = loop_gain(p, amp, np.array([p.f0]))[0]
    m = p.mbvd()
    Rext = amp.Zout_diff + amp.Zin_diff + 2 * p.Rs
    Qe = p.QL * m["Rm"] / (m["Rm"] + Rext)
    return dict(T0_mag=abs(T0), T0_dB=20 * np.log10(abs(T0)), T0_phase_deg=np.degrees(np.angle(T0)),
                Rext=Rext, Qe=Qe, ZT0=abs(amp.ZT(np.array([p.f0]), p.f0)[0]), Rp_tank=amp.Rp_tank,
                P_dc_mW=amp.P_dc * 1e3, I_dc_mA=amp.P_dc / amp.vdd * 1e3,
                gm1_mS=amp.gm1 * 1e3, gm2_mS=amp.gm2 * 1e3, gm4_mS=amp.gm4 * 1e3,
                polarity=amp.polarity, phase_trim_deg=amp.phase_trim_deg)


def find_oscillation_point(p: RingParams, amp: AmpDesign, span=200e3, n=40001, **kw):
    """Barkhausen point: zero loop-phase crossing nearest f0."""
    f = np.linspace(p.f0 - span, p.f0 + span, n)
    T = loop_gain(p, amp, f, **kw)
    ph = np.angle(T)
    idx = np.where((np.diff(np.sign(ph)) != 0) & (abs(np.diff(ph)) < np.pi))[0]
    if len(idx) == 0:
        return None
    best = idx[np.argmin(abs(f[idx] - p.f0))]
    fo = f[best] - ph[best] * (f[best + 1] - f[best]) / (ph[best + 1] - ph[best])
    To = np.interp(fo, f, abs(T))
    return dict(f_osc=fo, df_osc=fo - p.f0, T_mag=To, T_dB=20 * np.log10(To))


def mode_selection(p: RingParams, amp: AmpDesign, span=60e6, n=1200001):
    """Loop gain across the ring comb: every comb mode, its gain relative to the
    design mode and whether the Barkhausen phase condition can be met."""
    f = np.linspace(p.f0 - span, p.f0 + span, n)
    T = loop_gain(p, amp, f, comb=True, spurs=False, envelope=True)
    mag, ph = abs(T), np.angle(T)
    pk = np.where((mag[1:-1] > mag[:-2]) & (mag[1:-1] > mag[2:]))[0] + 1
    rows = []
    for k in pk:
        kk = int(round((f[k] - p.f0) / p.fsr))
        if abs(f[k] - (p.f0 + kk * p.fsr)) > 0.2 * p.fsr:
            continue
        rows.append(dict(k=kk, f=f[k], T_dB=20 * np.log10(mag[k]), phase_deg=np.degrees(ph[k])))
    rows.sort(key=lambda r: r["f"])
    main = [r for r in rows if r["k"] == 0][0]
    for r in rows:
        r["margin_dB"] = main["T_dB"] - r["T_dB"]
        r["phase_ok"] = abs(r["phase_deg"]) < 60 and r["T_dB"] > 0
    return f, T, rows


def startup_time(p: RingParams, amp: AmpDesign, v0=1e-5):
    s = loop_gain_summary(p, amp)
    tau = 2 * s["Qe"] / (p.w0 * (s["T0_mag"] - 1))
    return dict(tau_s=tau, t_startup_s=tau * np.log(amp.v_lim / v0))


# --------------------------------------------------------------------------
#  Loop noise factor (Norton sources referred to the TIA input node)
# --------------------------------------------------------------------------
def loop_noise_factor(p: RingParams, amp: AmpDesign, f=None):
    f = np.array([p.f0 if f is None else f])
    w = 2 * np.pi * f
    m = p.mbvd()
    Zs = amp.Zout_diff + 0j
    kw = _res_kw(amp)
    # passive resonator network seen from port 2 (includes C0, R0, Rs, L_out, Zs)
    Ysrc_res = port2_source_admittance(p, f, Zs, **kw)[0]
    Y_Lin = shunt_inductor_Y(f, amp.L_in, amp.Q_Lin)[0] if amp.L_in else 0.0
    Ypar = 1j * w[0] * amp.Cpar_in / 2
    Ysrc = Ysrc_res + Y_Lin + Ypar                    # total source admittance at the CG input
    gm_d = amp.gm1 / 2
    div = abs(gm_d / (gm_d + Ysrc)) ** 2              # current share into the CG devices
    # reference: thermal noise of Rm alone -> approximately the fraction Rm/Re(Zloop)
    Rloop = m["Rm"] + 2 * p.Rs + Zs.real
    S_res = 4 * kB * T_K * Ysrc_res.real              # whole passive network (Rm, Rs, R0, L_out loss, Rout)
    S_ref = S_res * m["Rm"] / Rloop
    S_lin = 4 * kB * T_K * Y_Lin.real if amp.L_in else 0.0
    S_drv_x = 4 * kB * T_K * (GAMMA - 1) * Zs.real / Rloop ** 2       # driver excess noise
    S_cg = 4 * kB * T_K * GAMMA * abs(Ysrc + 0.0) ** 2 / gm_d        # CG channel noise referred to input
    ZT1 = abs(amp.Z_tank(f, p.f0)[0])
    S_tank = 4 * kB * T_K / ZT1 / div                                 # tank loss, input-referred
    v_n2 = 2 * 4 * kB * T_K * (GAMMA / amp.gm2 + 1 / (amp.gm2 ** 2 * amp.Rp_tank2))
    S_st2 = v_n2 / ZT1 ** 2 / div
    parts = dict(Rm=S_ref, res_other=S_res - S_ref, L_in=S_lin, driver=S_drv_x, CG=S_cg, tank=S_tank, stage2=S_st2)
    tot = sum(parts.values())
    F = tot / S_ref
    return dict(F=F, F_dB=10 * np.log10(F), parts_rel={k: v / S_ref for k, v in parts.items()},
                Ysrc_mS=Ysrc * 1e3, div=div)


def signal_power_in_resonator(p: RingParams, amp: AmpDesign):
    """Power dissipated in Rm when the driver swings v_lim (diff. peak) at port 1."""
    m = p.mbvd()
    Rext = amp.Zout_diff + amp.Zin_diff + 2 * p.Rs
    Im = amp.v_lim / (m["Rm"] + Rext)
    P = 0.5 * Im ** 2 * m["Rm"]
    return dict(Im_peak=Im, P_W=P, P_dBm=10 * np.log10(P / 1e-3), V_port1=amp.v_lim)


def loss_vs_interface(p: RingParams, R_list, Lres=None, QL=8.0):
    """Transducer gain at f0 for symmetric real terminations R (dB)."""
    f = np.array([p.f0])
    return np.array([10 * np.log10(insertion_gain_general(p, f, np.array([R + 0j]), np.array([R + 0j]),
                                                          comb=False, spurs=False, Lres=Lres, QL=QL)[0]) for R in R_list])


def loop_loss_budget(p: RingParams, amp: AmpDesign):
    m = p.mbvd()
    f = np.array([p.f0])
    Yt = resonator_transfer_admittance(p, f, np.array([amp.Zout_diff + 0j]), np.array([amp.Zin_diff + 0j]), **_res_kw(amp))[0]
    Yt_noL = resonator_transfer_admittance(p, f, np.array([amp.Zout_diff + 0j]), np.array([amp.Zin_diff + 0j]))[0]
    ideal = 1 / m["Rm"]
    return dict(Yt_mS=abs(Yt) * 1e3, Yt_noL_mS=abs(Yt_noL) * 1e3, ideal_mS=ideal * 1e3,
                loop_loss_dB=-20 * np.log10(abs(Yt) / ideal), loop_loss_noL_dB=-20 * np.log10(abs(Yt_noL) / ideal))


def default_design():
    p = calibrate_to_measurement(RingParams(), verbose=False)
    amp, trim = auto_phase_trim(p, AmpDesign())
    return p, amp


if __name__ == "__main__":
    p, amp = default_design()
    print("Pierce:", {k: f"{v:.4g}" for k, v in pierce_analysis(p).items()})
    print("Loop:", {k: f"{v:.4g}" for k, v in loop_gain_summary(p, amp).items()})
    print("Osc point:", find_oscillation_point(p, amp))
    print("Startup:", startup_time(p, amp))
    nf = loop_noise_factor(p, amp)
    print("Noise factor:", f"{nf['F_dB']:.2f} dB", {k: f"{v:.2f}" for k, v in nf["parts_rel"].items()}, nf["Ysrc_mS"], nf["div"])
    print("Signal power:", signal_power_in_resonator(p, amp))
    print("Loss budget:", loop_loss_budget(p, amp))
    R = [50, 100, 200, 500, 1000, 2000, 5000]
    print("IL vs R (no L):", dict(zip(R, loss_vs_interface(p, R).round(2))))
    print("IL vs R (L, Q=8):", dict(zip(R, loss_vs_interface(p, R, Lres=29.8e-9).round(2))))
    f, T, rows = mode_selection(p, amp)
    for r in rows:
        print(f"  mode k={r['k']:+d}  f={r['f']/1e6:.3f} MHz  T={r['T_dB']:.2f} dB  phase={r['phase_deg']:.1f}  margin={r['margin_dB']:.2f}  phase_ok={r['phase_ok']}")
