"""Single source of truth for all nine device models and the five CFET platforms.

Every number here is a *nominal compact-model parameter* in SI units. Parameter names are
identical in the Verilog-A modules (veriloga/*.va), the ngspice behavioural library
(netlists/ngspice/ucm_cfet.lib) and the NumPy reference implementation (sim/ucm.py).

Nominal values are anchored to published figures of merit (see doc/calibration_targets.md
and paper/refs.bib); they are *not* fitted to any proprietary PDK.
"""
from __future__ import annotations
import math

Q = 1.602176634e-19
KB = 1.380649e-23
H = 6.62607015e-34
G0 = 4 * Q * Q / H          # Landauer conductance of one CNT (2 spins x 2 valleys) ~155 uS
EPS0 = 8.8541878128e-12
INF = 1e9                   # "infinite" quantum capacitance / off-switch value

TRANSPORT_DD = "dd"         # drift-diffusion + velocity saturation (Si, SiGe, GaN, TMD)
TRANSPORT_LANDAUER = "landauer"  # quasi-ballistic (CNT)

# --- parameter order used by every emitter -------------------------------------------
PARAM_ORDER = ["W", "L", "NNS", "WNS", "TNS", "VTH0", "N0", "ETA", "MU0", "COX", "VSAT",
               "LAMBDA", "RSW", "RDW", "CGSO", "CGDO", "TNOM", "MUEXP", "KVTH", "CQ", "DIT",
               "RC", "RTH", "CTH", "DCNT", "FMET", "TTR", "ALPHA"]

PARAM_DOC = {
    "W": "effective channel width [m] (ignored for nanosheet devices: W = NNS*2*(WNS+TNS))",
    "L": "gate length [m]", "NNS": "number of stacked nanosheets (0 = planar/2D/CNT/GaN)",
    "WNS": "nanosheet width [m]", "TNS": "nanosheet thickness [m]",
    "VTH0": "threshold voltage at TNOM, VDS->0 [V]", "N0": "subthreshold ideality factor",
    "ETA": "DIBL coefficient [V/V]", "MU0": "low-field mobility at TNOM [m^2/Vs]",
    "COX": "gate dielectric capacitance per area [F/m^2]", "VSAT": "saturation velocity [m/s]",
    "LAMBDA": "channel-length-modulation / output-conductance factor [1/V]",
    "RSW": "source series resistance x width [Ohm*m]", "RDW": "drain series resistance x width [Ohm*m]",
    "CGSO": "gate-source overlap/fringe capacitance per width [F/m]",
    "CGDO": "gate-drain overlap/fringe capacitance per width [F/m]",
    "TNOM": "nominal temperature [K]", "MUEXP": "mobility temperature exponent",
    "KVTH": "threshold temperature coefficient [V/K]",
    "CQ": "quantum capacitance per area [F/m^2] (2D/CNT), large = off",
    "DIT": "interface trap density [1/(m^2 eV)]", "RC": "contact resistance x width [Ohm*m] (2D/CNT)",
    "RTH": "thermal resistance [K/W] (GaN self-heating, 0 = off)", "CTH": "thermal capacitance [J/K]",
    "DCNT": "CNT density [tubes/m]", "FMET": "metallic CNT fraction",
    "TTR": "quasi-ballistic transmission probability", "ALPHA": "gate coupling efficiency (CNT)",
}

_BASE = dict(W=100e-9, L=16e-9, NNS=0, WNS=20e-9, TNS=5e-9, VTH0=0.25, N0=1.1, ETA=0.04,
             MU0=0.02, COX=0.043, VSAT=1e5, LAMBDA=0.1, RSW=60e-6, RDW=60e-6, CGSO=0.3e-9,
             CGDO=0.3e-9, TNOM=300.0, MUEXP=1.3, KVTH=-0.8e-3, CQ=INF, DIT=0.0, RC=0.0,
             RTH=0.0, CTH=1e-12, DCNT=0.0, FMET=0.0, TTR=0.0, ALPHA=1.0)


def _p(**kw):
    d = dict(_BASE)
    d.update(kw)
    return d


# --- the nine device models ----------------------------------------------------------
# Si gate-all-around nanosheet: EOT 0.8 nm (COX = 3.9*eps0/0.8 nm = 43 fF/um^2), Lg 16 nm,
# 3 sheets 20 nm x 5 nm -> Weff = 150 nm.  Targets: SS ~68 mV/dec, DIBL ~40 mV/V,
# Ion ~1 mA/um @ VDD 0.7 V, Ioff ~1 nA/um (IRDS 2023 "2 nm" class logic).
DEVICES = {
    "gaa_n": dict(polarity="n", transport=TRANSPORT_DD, material="Si nanosheet", platform_tag="Si",
                  params=_p(NNS=3, WNS=20e-9, TNS=5e-9, L=16e-9, VTH0=0.25, N0=1.12, ETA=0.040,
                            MU0=0.025, COX=0.043, VSAT=1.0e5, LAMBDA=0.10, RSW=60e-6, RDW=60e-6,
                            CGSO=0.30e-9, CGDO=0.30e-9, MUEXP=1.3, KVTH=-0.8e-3)),
    "gaa_p": dict(polarity="p", transport=TRANSPORT_DD, material="Si nanosheet", platform_tag="Si",
                  params=_p(NNS=3, WNS=20e-9, TNS=5e-9, L=16e-9, VTH0=0.25, N0=1.14, ETA=0.045,
                            MU0=0.012, COX=0.043, VSAT=0.8e5, LAMBDA=0.10, RSW=80e-6, RDW=80e-6,
                            CGSO=0.30e-9, CGDO=0.30e-9, MUEXP=1.1, KVTH=-0.9e-3)),
    # Strained SiGe (x~0.3) p-channel nanosheet: ~1.8x hole mobility, slightly lower VTH.
    "sige_p": dict(polarity="p", transport=TRANSPORT_DD, material="SiGe nanosheet", platform_tag="SiGe",
                   params=_p(NNS=3, WNS=20e-9, TNS=5e-9, L=16e-9, VTH0=0.24, N0=1.15, ETA=0.050,
                             MU0=0.022, COX=0.043, VSAT=0.9e5, LAMBDA=0.11, RSW=70e-6, RDW=70e-6,
                             CGSO=0.32e-9, CGDO=0.32e-9, MUEXP=1.2, KVTH=-1.0e-3)),
    # Monolayer MoS2 n-FET: mu ~40 cm^2/Vs, EOT 1 nm (COX 34.5 fF/um^2), Cq ~1.2 F/m^2,
    # Dit 5e11 cm^-2 eV^-1, contact resistance 500 Ohm*um dominates (RSW = RDW = RC).
    "mos2_n": dict(polarity="n", transport=TRANSPORT_DD, material="MoS2 monolayer", platform_tag="TMD",
                   params=_p(W=100e-9, L=20e-9, VTH0=0.20, N0=1.15, ETA=0.050, MU0=0.006,
                             COX=0.0345, VSAT=0.5e5, LAMBDA=0.12, CQ=1.2, DIT=5e15, RC=500e-6,
                             RSW=500e-6, RDW=500e-6, CGSO=0.20e-9, CGDO=0.20e-9, MUEXP=1.0,
                             KVTH=-1.0e-3)),
    "wse2_p": dict(polarity="p", transport=TRANSPORT_DD, material="WSe2 monolayer", platform_tag="TMD",
                   params=_p(W=100e-9, L=20e-9, VTH0=0.22, N0=1.20, ETA=0.055, MU0=0.005,
                             COX=0.0345, VSAT=0.4e5, LAMBDA=0.12, CQ=1.1, DIT=1e16, RC=800e-6,
                             RSW=800e-6, RDW=800e-6, CGSO=0.20e-9, CGDO=0.20e-9, MUEXP=1.0,
                             KVTH=-1.1e-3)),
    # Aligned CNT array: 250 tubes/um, 99.99 % semiconducting purity (FMET = 1e-4), quasi-ballistic transmission 0.3,
    # gate efficiency 0.8, contact 50 Ohm*um per side.
    "cnt_n": dict(polarity="n", transport=TRANSPORT_LANDAUER, material="CNT array", platform_tag="CNT",
                  params=_p(W=100e-9, L=20e-9, VTH0=0.20, N0=1.05, ETA=0.040, COX=0.020, CQ=0.05,
                            LAMBDA=0.05, DCNT=250e6, FMET=1e-4, TTR=0.30, ALPHA=0.80,
                            RC=50e-6, RSW=50e-6, RDW=50e-6, CGSO=0.15e-9, CGDO=0.15e-9,
                            MUEXP=0.0, KVTH=-0.6e-3, MU0=0.0, VSAT=0.0)),
    "cnt_p": dict(polarity="p", transport=TRANSPORT_LANDAUER, material="CNT array", platform_tag="CNT",
                  params=_p(W=100e-9, L=20e-9, VTH0=0.20, N0=1.05, ETA=0.040, COX=0.020, CQ=0.05,
                            LAMBDA=0.05, DCNT=250e6, FMET=1e-4, TTR=0.28, ALPHA=0.80,
                            RC=60e-6, RSW=60e-6, RDW=60e-6, CGSO=0.15e-9, CGDO=0.15e-9,
                            MUEXP=0.0, KVTH=-0.6e-3, MU0=0.0, VSAT=0.0)),
    # GaN: E-mode n-channel HEMT-like device, mu 1500 cm^2/Vs, 10 nm AlGaN barrier
    # (COX ~8 fF/um^2), Rsd 0.3 Ohm*mm, Rth 1.5e5 K/W for W = 1 um, Cth ~3e-14 J/K (active
# volume ~1e-20 m^3 x 3 MJ/m^3K, thermal time constant ~4.5 ns); p-GaN is projected
    # (mu_h ~20 cm^2/Vs, Rsd 1.5 Ohm*mm, upsized 3x).
    "gan_n": dict(polarity="n", transport=TRANSPORT_DD, material="GaN 2DEG", platform_tag="GaN",
                  params=_p(W=1e-6, L=100e-9, VTH0=0.40, N0=1.30, ETA=0.030, MU0=0.15, COX=0.008,
                            VSAT=1.5e5, LAMBDA=0.05, RSW=300e-6, RDW=300e-6, CGSO=0.5e-9,
                            CGDO=0.5e-9, MUEXP=1.5, KVTH=-1.5e-3, RTH=1.5e5, CTH=3e-14)),
    "gan_p": dict(polarity="p", transport=TRANSPORT_DD, material="p-GaN (projected)", platform_tag="GaN",
                  params=_p(W=3e-6, L=100e-9, VTH0=0.40, N0=1.40, ETA=0.030, MU0=0.002, COX=0.008,
                            VSAT=0.5e5, LAMBDA=0.05, RSW=1500e-6, RDW=1500e-6, CGSO=0.5e-9,
                            CGDO=0.5e-9, MUEXP=1.0, KVTH=-2.0e-3, RTH=1.0e5, CTH=9e-14)),
}

# --- the five CFET platforms -----------------------------------------------------------
PLATFORMS = {
    "si":   dict(name="CFET-Si",   n="gaa_n",  p="gaa_p",  vdd=0.7, vdd_sweep=(0.4, 0.8, 0.05),
                 cstack=0.05e-15, cout=0.3e-15, rlocal=10.0, cload=0.3e-15,
                 tstop=20e-9, maxstep=1e-12, maturity="advanced-node, roadmap-relevant",
                 temps=[-40, 27, 85, 125]),
    "sige": dict(name="CFET-SiGe", n="gaa_n",  p="sige_p", vdd=0.7, vdd_sweep=(0.4, 0.8, 0.05),
                 cstack=0.05e-15, cout=0.3e-15, rlocal=10.0, cload=0.3e-15,
                 tstop=20e-9, maxstep=1e-12, maturity="advanced-node, roadmap-relevant",
                 temps=[-40, 27, 85, 125]),
    "tmd":  dict(name="CFET-TMD",  n="mos2_n", p="wse2_p", vdd=0.5, vdd_sweep=(0.3, 0.6, 0.05),
                 cstack=0.03e-15, cout=0.3e-15, rlocal=50.0, cload=0.3e-15,
                 tstop=200e-9, maxstep=10e-12, maturity="emerging post-Si",
                 temps=[-40, 27, 85, 125]),
    "cnt":  dict(name="CFET-CNT",  n="cnt_n",  p="cnt_p",  vdd=0.6, vdd_sweep=(0.4, 0.8, 0.05),
                 cstack=0.03e-15, cout=0.3e-15, rlocal=50.0, cload=0.3e-15,
                 tstop=20e-9, maxstep=1e-12, maturity="emerging post-Si",
                 temps=[-40, 27, 85, 125]),
    "gan":  dict(name="CFET-GaN",  n="gan_n",  p="gan_p",  vdd=1.2, vdd_sweep=(0.8, 1.5, 0.1),
                 cstack=0.10e-15, cout=1.0e-15, rlocal=20.0, cload=1.0e-15,
                 tstop=50e-9, maxstep=2e-12, maturity="exploratory / projected",
                 temps=[-40, 27, 85, 125, 150, 200]),
}
PLATFORM_ORDER = ["si", "sige", "tmd", "cnt", "gan"]
PLATFORM_COLORS = {"si": "#0072B2", "sige": "#009E73", "tmd": "#D55E00", "cnt": "#CC79A7", "gan": "#E69F00"}  # Okabe-Ito, CVD-validated
PLATFORM_MARKERS = {"si": "o", "sige": "s", "tmd": "^", "cnt": "D", "gan": "v"}
PLATFORM_LS = {"si": "-", "sige": "--", "tmd": "-.", "cnt": ":", "gan": (0, (5, 1, 1, 1))}


def eff_width(p: dict) -> float:
    """Effective electrical width: nanosheet perimeter sum, or W."""
    if p["NNS"] and p["NNS"] > 0:
        return p["NNS"] * 2.0 * (p["WNS"] + p["TNS"])
    return p["W"]


def device_params(name: str, **overrides) -> dict:
    d = dict(DEVICES[name]["params"])
    d.update(overrides)
    return d
