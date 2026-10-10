"""Shared forward model: physiological/thermal state -> photoacoustic traces, pulse-echo
times, reference-absorber amplitude and NIRS reflectances.

The same class is instantiated twice: once with the *true* subject parameters (the
virtual neonate, second-order fluence perturbation, true acoustic/thermal coefficients)
and once with *nominal population* parameters inside the estimator (first-order
perturbation, nominal coefficients). The difference between the two is the structural
model error the estimator has to live with.

Target absorber of the deep gate: the superior sagittal sinus (SSS), which lies on the
midline directly beneath the anterior fontanelle. Its photoacoustic spectrum gives the
cerebral venous oxygen saturation and, through the Grueneisen parameter of blood, the
brain (venous blood) temperature.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
from . import tissue, acoustic as ac
from .fluence import FluenceModel, LAYERS_CANON

CI = {n: i for i, n in enumerate(LAYERS_CANON)}
HBT_BLOOD = tissue.LAYER_DEFAULTS["sinus"]["hbt"]      # uM


@dataclass
class HeadParams:
    bone: float = 0.0                # cm of bone (0 = fontanelle membrane)
    mus_scale: float = 1.0
    hbt_scalp: float = 40.0          # uM
    hbt_brain: float = 50.0          # uM parenchyma
    so2_scalp: float = 0.70
    hct_scale: float = 1.0           # haematocrit scaling of the blood absorption
    fill: float = 0.5                # lateral fill factor of the sinus within the aperture
    par_offset: float = 0.05         # parenchyma sO2 - sinus sO2
    bg_scale: float = 1.0            # scaling of background absorption (all layers)
    kg: np.ndarray = field(default_factory=lambda: np.array([ac.KG_DEFAULT[n] for n in LAYERS_CANON]))
    gamma37: float = ac.GAMMA37
    c0: np.ndarray = field(default_factory=lambda: np.array([ac.ACOUSTIC_DEFAULTS[n][0] for n in LAYERS_CANON]))
    kc: np.ndarray = field(default_factory=lambda: np.array([ac.ACOUSTIC_DEFAULTS[n][1] for n in LAYERS_CANON]))
    alpha0: np.ndarray = field(default_factory=lambda: np.array([ac.ACOUSTIC_DEFAULTS[n][2] for n in LAYERS_CANON]))
    y: np.ndarray = field(default_factory=lambda: np.array([ac.ACOUSTIC_DEFAULTS[n][3] for n in LAYERS_CANON]))
    scalp_thick: float = 0.20
    deep_echo_depth: float = 1.5     # cm, speckle window used for brain echo-shift
    ref_gain: float = 1.0            # reference absorber relative efficiency

    @property
    def sinus_top(self):
        return self.scalp_thick + (self.bone if self.bone > 0 else 0.10) + 0.10


class ForwardModel:
    def __init__(self, fl: FluenceModel, head: HeadParams, dev: ac.DeviceConfig, second_order=True):
        self.fl, self.head, self.dev, self.so = fl, head, dev, second_order
        self.z = fl.z
        self.names, th = tissue.head_geometry(head.bone, scalp_thick_cm=head.scalp_thick)
        self.thick = np.zeros(len(LAYERS_CANON))
        for n, t in zip(self.names, th):
            self.thick[CI[n]] = t if n != "brain" else 10.0
        self.lay = tissue.depth_layer_index(self.z, th)              # index into self.names
        self.lay_c = np.array([CI[n] for n in self.names])[self.lay]  # canonical index per depth bin
        self.H = ac.transducer_response(dev.transducer, dev.source.pulse_ns)
        self.is_sinus = self.lay_c == CI["sinus"]
        self.deep_mask = self.lay_c >= CI["csf"]

    # ---- optics
    def dmua(self, lam, so2_v, so2_s=None, hbt_s=None):
        """Absorption change of the canonical layers relative to the table's nominal
        (table interpolated at sinus saturation so2_v)."""
        h = self.head
        so2_s = h.so2_scalp if so2_s is None else so2_s
        hbt_s = h.hbt_scalp if hbt_s is None else hbt_s
        nom = self.fl.nominal_mua(lam, so2_v)
        d = np.zeros(len(LAYERS_CANON))
        spec = {"scalp": (so2_s, hbt_s), "sinus": (so2_v, HBT_BLOOD * h.hct_scale),
                "brain": (min(so2_v + h.par_offset, 0.98), h.hbt_brain)}
        for name, (so2, hbt) in spec.items():
            i = CI[name]; dft = tissue.LAYER_DEFAULTS[name]
            mua_new = (tissue.mua_blood_tissue(lam, so2, hbt) + dft["water"] * tissue.mua_water(lam)
                       + h.bg_scale * dft["bg"])
            d[i] = mua_new - nom[i]
        for name in ("fontanelle", "bone", "csf"):
            i = CI[name]; dft = tissue.LAYER_DEFAULTS[name]
            d[i] = (h.bg_scale - 1.0) * dft["bg"]
        return d, nom

    def fluence(self, lam, dm, so2_v):
        return self.fl.fluence(lam, self.head.bone, self.head.mus_scale, self.dev.source.beam_radius, dm,
                               so2v=so2_v, second_order=self.so)

    def mua_z(self, nom, dm):
        return (nom + dm)[self.lay_c]

    # ---- temperature field (superficial layers at T_s, csf/sinus/brain at T_b)
    def T_z(self, T_b, T_s):
        return np.where(self.deep_mask, T_b, T_s)

    def c_layers(self, T_b, T_s):
        T = np.array([T_s, T_s, T_s, T_b, T_b, T_b])
        return self.head.c0 + self.head.kc * (T - 37.0)

    def p0(self, lam, so2_v, T_b, T_s, g, fill=None, so2_s=None, hbt_s=None, F0=None):
        dm, nom = self.dmua(lam, so2_v, so2_s, hbt_s)
        phi = self.fluence(lam, dm, so2_v)
        mua = self.mua_z(nom, dm)
        T = self.T_z(T_b, T_s)
        gam = self.head.gamma37 * (1.0 + self.head.kg[self.lay_c] * (T - 37.0))
        F0 = self.dev.source.fluence_mJcm2 if F0 is None else F0
        fill = self.head.fill if fill is None else fill
        p0 = g * gam * (mua * 100.0) * (phi * F0 * 10.0)          # Pa : 1/m * J/m^2
        return np.where(self.is_sinus, fill * p0, p0), phi

    # ---- photoacoustic trace at one wavelength (noise-free, Pa at the probe)
    def pa_trace(self, lam, so2_v, T_b, T_s, g, **kw):
        p0, phi = self.p0(lam, so2_v, T_b, T_s, g, **kw)
        c = self.c_layers(T_b, T_s)
        return ac.propagate(p0, self.z, self.thick, c, self.head.alpha0, self.head.y, self.H), p0

    # ---- pulse-echo times (two-way) of the superficial and deep windows
    def echo_times(self, T_b, T_s):
        c = self.c_layers(T_b, T_s)
        d_sup = self.thick[:CI["csf"]]                        # scalp + membrane/bone
        t_sup = 2 * (d_sup / (c[:CI["csf"]] * 100.0)).sum()
        d_csf, d_sin = self.thick[CI["csf"]], self.thick[CI["sinus"]]
        d_brain = max(self.head.deep_echo_depth - d_sup.sum() - d_csf - d_sin, 0.2)
        t_deep = t_sup + 2 * (d_csf / (c[CI["csf"]] * 100.0) + d_sin / (c[CI["sinus"]] * 100.0)
                              + d_brain / (c[CI["brain"]] * 100.0))
        return t_sup, t_deep

    # ---- NIRS reflectances (pencil source) at the table's rho values
    def nirs(self, lam, so2_v, so2_s=None, hbt_s=None):
        dm, _ = self.dmua(lam, so2_v, so2_s, hbt_s)
        return self.fl.reflectance_nirs(lam, self.head.bone, self.head.mus_scale, dm, so2v=so2_v)
