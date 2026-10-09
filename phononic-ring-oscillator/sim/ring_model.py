"""
ring_model.py  --  Physics-to-circuit model of the two-port SiN-on-LN phononic ring
resonator (identical equations to veriloga/phononic_ring_resonator.va).

Model chain
-----------
    (Qi, Qc, FSR, f0)  ->  ring round-trip (a, t, kappa^2, tau_rt)
                       ->  drop-port transfer T_ring(f) (recirculating delay loop)
    (C0, R0, Rs, Ga0, eta_t) -> IDT parasitics and transduction
                       ->  2-port Y-parameters -> S-parameters in 50 ohm
                       ->  extended mBVD (Rm, Lm, Cm) for the dominant mode

Everything here is dimensionally consistent with the Verilog-A so that numbers
produced by the open-source pipeline carry over 1:1 to Spectre.
"""
from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field, asdict

Z0 = 50.0
kB = 1.380649e-23


@dataclass
class RingParams:
    # measured (Ji et al., arXiv:2603.27711, 2026)
    f0: float = 1001.15e6
    Qi: float = 22393.0
    Qc: float = 179680.0
    IL_meas_dB: float = 28.2          # |S21| at f0 in a 50-ohm system
    # assumed geometry (not reported in the preprint -> parameterised)
    v_ac: float = 3600.0              # guided-mode group velocity [m/s]
    m_az: int = 175                   # azimuthal mode number of the 1001.15-MHz mode
                                      # (radius follows: L = m_az * v_ac / f0 -> R ~ 100 um)
    # IDT / transduction
    C0: float = 0.85e-12              # static capacitance [F]
    R0: float = 20.0e3                # dielectric-loss resistance [ohm] (Q_diel ~ 100)
    Rs: float = 4.0                   # electrode series resistance [ohm]
    Ga0: float = 0.32e-3              # radiation conductance at f0 [S]
    eta_t: float = 0.40               # IDT->ring power efficiency (bidirectional
                                      # IDT = 0.5, taper ~0.8  -> 0.40)
    tcf: float = -70e-6               # temperature coefficient of frequency [1/K]
    N_idt: int = 20                   # IDT finger pairs (sets the sinc^2 transduction envelope)
    # spurious modes (frequency offset [Hz], Q, relative coupling)
    spurs: list = field(default_factory=lambda: [(+4.1e6, 6000.0, 0.08), (-7.6e6, 4500.0, 0.05)])

    # ---------------- derived ----------------
    @property
    def L(self):
        return self.m_az * self.v_ac / self.f0

    @property
    def radius(self):
        return self.L / (2 * np.pi)

    @property
    def fsr(self):
        return self.v_ac / self.L

    @property
    def tau_rt(self):
        return 1.0 / self.fsr

    @property
    def QL(self):
        return 1.0 / (1.0 / self.Qi + 2.0 / self.Qc)

    @property
    def w0(self):
        return 2 * np.pi * self.f0

    def round_trip(self):
        """(a, t, kappa2): field attenuation per round trip, coupler through-field
        transmission and coupler power cross-coupling."""
        a = np.exp(-np.pi * self.f0 / (self.Qi * self.fsr))
        kappa2 = self.w0 * self.tau_rt / self.Qc
        t = np.sqrt(1 - kappa2)
        return a, t, kappa2

    def T_drop_f0(self):
        a, t, k2 = self.round_trip()
        return k2 ** 2 * a / (1 - t ** 2 * a) ** 2

    # ------------- extended-mBVD derivation (same as Verilog-A) -------------
    def mbvd(self):
        Td = self.T_drop_f0()
        Gm = self.Ga0 * self.eta_t * np.sqrt(Td)
        Rm = 1.0 / Gm
        Lm = self.QL * Rm / self.w0
        Cm = 1.0 / (self.w0 ** 2 * Lm)
        return dict(Rm=Rm, Lm=Lm, Cm=Cm, C0=self.C0, R0=self.R0, Rs=self.Rs,
                    keff2=Cm / self.C0, Tdrop_dB=10 * np.log10(Td))

    def spur_branches(self):
        Rm = self.mbvd()["Rm"]
        out = []
        for df, Qs, ks in self.spurs:
            fs = self.f0 + df
            Rs_ = Rm / ks
            Ls_ = Qs * Rs_ / (2 * np.pi * fs)
            Cs_ = 1 / ((2 * np.pi * fs) ** 2 * Ls_)
            out.append(dict(f=fs, R=Rs_, L=Ls_, C=Cs_))
        return out


# --------------------------------------------------------------------------
#  Frequency-domain network
# --------------------------------------------------------------------------
def ring_drop_transfer(p: RingParams, f, comb=True):
    """Field transfer from the input bus to the drop bus of an add-drop ring.
    comb=True uses the exact recirculating-delay form (full FSR comb);
    comb=False uses the single-Lorentzian (mBVD) approximation around f0."""
    a, t, k2 = p.round_trip()
    w = 2 * np.pi * np.asarray(f, float)
    if comb:
        phi = w * p.tau_rt
        return k2 * np.sqrt(a) * np.exp(-1j * phi / 2) / (1 - t ** 2 * a * np.exp(-1j * phi))
    # Lorentzian: same peak, loaded linewidth f0/QL
    return np.sqrt(p.T_drop_f0()) / (1 + 2j * p.QL * (w / p.w0 - 1))


def idt_envelope(p: RingParams, f):
    """Normalised IDT transduction envelope |H_idt|^2 = sinc^2(N (f-f0)/f0)."""
    x = p.N_idt * (np.asarray(f, float) - p.f0) / p.f0
    return np.sinc(x) ** 2


def series_branch_Y(p: RingParams, f, comb=True, spurs=True, envelope=True):
    """Admittance of the port-to-port motional path (A-parameter style, the
    'series element' between the internal nodes i1 and i2)."""
    w = 2 * np.pi * np.asarray(f, float)
    m = p.mbvd()
    if comb:
        # scale the comb so that it equals 1/Rm with ZERO phase at f0 (the same
        # reference as the mBVD branch; the physical propagation phase of the
        # half round trip is absorbed in the amplifier polarity choice)
        H = ring_drop_transfer(p, f, comb=True)
        H0 = ring_drop_transfer(p, np.array([p.f0]), comb=True)[0]
        Y = (1.0 / m["Rm"]) * (H / H0)
    else:
        Z = m["Rm"] + 1j * w * m["Lm"] + 1 / (1j * w * m["Cm"])
        Y = 1 / Z
    if spurs:
        for b in p.spur_branches():
            Y = Y + 1 / (b["R"] + 1j * w * b["L"] + 1 / (1j * w * b["C"]))
    if envelope:
        Y = Y * idt_envelope(p, f)     # two IDTs: sqrt(env)^2
    return Y


def shunt_inductor_Y(f, L, QL):
    """Admittance of a lossy inductor (series r = wL/Q) placed across a port."""
    w = 2 * np.pi * np.asarray(f, float)
    if not L:
        return np.zeros_like(w, dtype=complex)
    return 1 / (1j * w * L + w * L / QL)


def two_port_Y(p: RingParams, f, comb=False, spurs=True, Lres=None, envelope=True,
               Lres1=None, Lres2=None, QL=8.0):
    """Full 2-port Y-matrix at external terminals (including Rs, C0, R0 and
    optional lossy shunt inductors across port 1 / port 2 that resonate C0).
    Lres (legacy) applies the same inductor to both ports."""
    w = 2 * np.pi * np.asarray(f, float)
    Ym = series_branch_Y(p, f, comb, spurs, envelope)     # between i1 and i2
    Ysh = 1j * w * p.C0 + 1 / p.R0                        # shunt at i1 and i2
    L1 = Lres1 if Lres1 is not None else Lres
    L2 = Lres2 if Lres2 is not None else Lres
    Ysh1 = Ysh + shunt_inductor_Y(f, L1, QL)
    Ysh2 = Ysh + shunt_inductor_Y(f, L2, QL)
    # internal 2-port (nodes i1,i2): pi-network
    Y11i = Ysh1 + Ym
    Y22i = Ysh2 + Ym
    Y12i = -Ym
    Yint = np.array([[Y11i, Y12i], [Y12i, Y22i]]).transpose(2, 0, 1)
    # add series Rs at each port: convert to Z, add, convert back
    Zint = np.linalg.inv(Yint)
    Zint[:, 0, 0] += p.Rs
    Zint[:, 1, 1] += p.Rs
    return np.linalg.inv(Zint)


def Y_to_S(Y, Z0=Z0):
    n = Y.shape[-1]
    I = np.eye(n)
    S = np.empty_like(Y)
    for k in range(Y.shape[0]):
        S[k] = np.linalg.solve(I + Z0 * Y[k], I - Z0 * Y[k])
    return S


def s_params(p: RingParams, f, comb=False, spurs=True, Z0=Z0, Lres=None, envelope=True, **kw):
    return Y_to_S(two_port_Y(p, f, comb, spurs, Lres, envelope, **kw), Z0)


def insertion_gain_general(p: RingParams, f, Zs, Zl, comb=False, spurs=True, Lres=None, envelope=True, **kw):
    """Transducer power gain |G_T| (linear) of the resonator between a source of
    impedance Zs and a load Zl (both may be complex); used to evaluate the loop
    loss seen by the CMOS amplifier interfaces instead of 50 ohm."""
    Y = two_port_Y(p, f, comb, spurs, Lres, envelope, **kw)
    Z = np.linalg.inv(Y)
    Z11, Z12, Z21, Z22 = Z[:, 0, 0], Z[:, 0, 1], Z[:, 1, 0], Z[:, 1, 1]
    num = 4 * Zs.real * Zl.real * np.abs(Z21) ** 2
    den = np.abs((Z11 + Zs) * (Z22 + Zl) - Z12 * Z21) ** 2
    return num / den


def calibrate_to_measurement(p: RingParams, target_dB=None, verbose=True):
    """Scale (Ga0*eta_t) so that |S21(f0)| in 50 ohm equals the measured IL."""
    target_dB = -(target_dB or p.IL_meas_dB)
    f = np.array([p.f0])
    for _ in range(60):                      # fixed-point on a 1-D monotone map
        S = s_params(p, f, comb=False, spurs=False)
        cur = 20 * np.log10(abs(S[0, 1, 0]))
        err = target_dB - cur
        if abs(err) < 1e-4:
            break
        p.Ga0 *= 10 ** (err / 20)
    if verbose:
        print(f"calibrated Ga0 = {p.Ga0*1e3:.4f} mS  ->  |S21(f0)| = {cur:.2f} dB")
    return p


def loaded_Q_electrical(p: RingParams, Rext):
    """Electrical loading of the motional branch by the amplifier interface
    (sum of real source + load impedances seen in series with Rm)."""
    m = p.mbvd()
    return p.QL * m["Rm"] / (m["Rm"] + Rext)


if __name__ == "__main__":
    p = calibrate_to_measurement(RingParams())
    a, t, k2 = p.round_trip()
    print(f"R = {p.radius*1e6:.1f} um, FSR = {p.fsr/1e6:.3f} MHz, tau_rt = {p.tau_rt*1e9:.1f} ns, a = {a:.5f}, t = {t:.5f}, kappa2 = {k2:.5f}")
    print(f"QL = {p.QL:.0f}, T_drop(f0) = {10*np.log10(p.T_drop_f0()):.2f} dB")
    print("mBVD:", {k: f"{v:.4g}" for k, v in p.mbvd().items()})
