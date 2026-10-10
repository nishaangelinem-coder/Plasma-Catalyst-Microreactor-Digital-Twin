"""Chromophore spectra and the layered neonatal head model.

All lengths in cm, absorption/scattering coefficients in 1/cm, concentrations in mol/L.

Molar extinction coefficients of oxy-/deoxy-haemoglobin are the widely used
compilation of S. Prahl (OMLC, after W. B. Gratzer and N. Kollias), tabulated at the
candidate source wavelengths of the monitor. Water absorption after Hale & Querry /
Kou et al. Neonatal layer thicknesses and reduced scattering follow the ranges used by
Fukui, Ajihara & Okada (2003) and Dehaes et al. (2011).  All numbers should be
re-checked against the cited tables before any hardware calibration.
"""
from __future__ import annotations
import numpy as np

# ---------------------------------------------------------------- chromophores
# wavelength (nm): (eps_HbO2, eps_Hb) in 1/(cm M)
_EPS = {
    690: (276.0, 2051.96),
    750: (518.0, 1405.24),
    760: (586.0, 1548.52),
    780: (710.0, 1075.44),
    800: (816.0, 761.72),
    850: (1058.0, 691.32),
    900: (1198.0, 761.84),
    940: (1214.0, 693.44),
}
# water absorption (1/cm)
_MUA_WATER = {690: 0.0048, 750: 0.0260, 760: 0.0270, 780: 0.0240, 800: 0.0200,
              850: 0.0430, 900: 0.0680, 940: 0.2700}
CANDIDATE_WAVELENGTHS = tuple(sorted(_EPS))
LN10 = np.log(10.0)


def extinction(lam: int) -> tuple[float, float]:
    """(eps_HbO2, eps_Hb) in 1/(cm M) at wavelength lam (nm)."""
    return _EPS[int(lam)]


def mua_water(lam: int) -> float:
    return _MUA_WATER[int(lam)]


def mua_blood_tissue(lam: int, so2: float, hbt_uM: float) -> float:
    """Haemoglobin absorption of a tissue with total haemoglobin hbt (micromolar)."""
    e_o, e_d = extinction(lam)
    return LN10 * (so2 * e_o + (1.0 - so2) * e_d) * hbt_uM * 1e-6


# ---------------------------------------------------------------- head model
# Layer order from the probe inwards. Thickness in cm (None = semi-infinite).
# mus' = a * (lam/800)^-b   (1/cm);  water fraction;  background absorption (1/cm)
LAYER_DEFAULTS = {
    "scalp":      dict(thick=0.20, a=19.0, b=1.2, water=0.55, bg=0.05, hbt=40.0, so2=0.70, g=0.90, n=1.40),
    "fontanelle": dict(thick=0.10, a=12.0, b=1.0, water=0.60, bg=0.08, hbt=10.0, so2=0.70, g=0.90, n=1.40),
    "bone":       dict(thick=0.00, a=16.0, b=0.6, water=0.30, bg=0.10, hbt=15.0, so2=0.70, g=0.90, n=1.40),
    "csf":        dict(thick=0.10, a=2.4,  b=0.5, water=0.99, bg=0.00, hbt=0.0,  so2=0.70, g=0.90, n=1.40),
    "sinus":      dict(thick=0.30, a=7.0,  b=0.8, water=0.80, bg=0.02, hbt=2300.0, so2=0.65, g=0.90, n=1.40),
    "brain":      dict(thick=None, a=6.5,  b=1.0, water=0.80, bg=0.04, hbt=50.0, so2=0.70, g=0.90, n=1.40),
}
LAYER_NAMES = tuple(LAYER_DEFAULTS)  # scalp, fontanelle, bone, csf, sinus, brain


def layer_props(name: str, lam: int, so2: float | None = None, hbt: float | None = None,
                mus_scale: float = 1.0) -> tuple[float, float, float]:
    """(mua, mus, g) of a layer at wavelength lam."""
    d = LAYER_DEFAULTS[name]
    so2 = d["so2"] if so2 is None else so2
    hbt = d["hbt"] if hbt is None else hbt
    mua = mua_blood_tissue(lam, so2, hbt) + d["water"] * mua_water(lam) + d["bg"]
    musp = mus_scale * d["a"] * (lam / 800.0) ** (-d["b"])
    mus = musp / (1.0 - d["g"])
    return mua, mus, d["g"]


def head_geometry(bone_thick_cm: float = 0.0, scalp_thick_cm: float = 0.20,
                  csf_thick_cm: float = 0.10, fontanelle_thick_cm: float = 0.10, sinus_thick_cm: float = 0.30):
    """Return (names, thicknesses) of the active layers.

    bone_thick_cm = 0 means the probe sits over the anterior fontanelle (membrane only);
    bone_thick_cm > 0 models a partly ossified/closing fontanelle or an off-fontanelle
    position. Thickness of the semi-infinite brain layer is encoded as a large number.
    """
    names, th = ["scalp"], [scalp_thick_cm]
    if bone_thick_cm > 0:
        names.append("bone"); th.append(bone_thick_cm)
    else:
        names.append("fontanelle"); th.append(fontanelle_thick_cm)
    names += ["csf", "sinus", "brain"]; th += [csf_thick_cm, sinus_thick_cm, 10.0]
    return names, np.array(th)


def layer_boundaries(thick):
    z = np.concatenate([[0.0], np.cumsum(thick)])
    return z


def depth_layer_index(z, thick):
    """Layer index for each depth z (cm)."""
    zb = layer_boundaries(thick)
    return np.clip(np.searchsorted(zb, z, side="right") - 1, 0, len(thick) - 1)
