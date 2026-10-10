"""Fluence / reflectance tables and fast perturbation model.

The table is built once by Monte Carlo (p2pneo.mc) on a grid of
  wavelength x bone thickness x scattering scale
for the pencil-beam Green's functions. For a flat-top disc beam of radius a the on-axis
fluence is the radial integral of the pencil response. Changes in layer absorption
(haemoglobin, oxygenation) are applied with the partial-path-length (Beer-Lambert)
perturbation, including a second-order (path-length variance) term for the truth
model. The estimator's reduced model uses the first-order term only (see estimators).
"""
from __future__ import annotations
import os, itertools
import numpy as np
from multiprocessing import Pool
from . import tissue, mc

BONE_GRID = (0.0, 0.1, 0.2, 0.3)          # cm  (0 = over the fontanelle)
MUS_GRID = (0.8, 1.0, 1.2)                 # scaling of reduced scattering of all layers
SO2V_GRID = (0.45, 0.65, 0.85)             # venous (sinus) oxygen saturation
BEAM_RADII = (0.3, 0.5, 0.75)              # cm
RHO_NIRS = (1.5, 2.0, 2.5, 3.0)            # cm  source-detector separations (NIRS baseline)
LAYERS_CANON = ("scalp", "fontanelle", "bone", "csf", "sinus", "brain")   # canonical layer slots
Z = (np.arange(mc.NZ) + 0.5) * mc.DZ
R_PENCIL = (np.arange(mc.NR) + 0.5) * mc.DR


def _canon_index(names):
    return [LAYERS_CANON.index(n) for n in names]


def _one(args):
    lam, bone, mscale, so2v, nphot, seed = args
    names, th = tissue.head_geometry(bone)
    props = [tissue.layer_props(n, lam, mus_scale=mscale, so2=(so2v if n == "sinus" else None)) for n in names]
    mua = np.array([p[0] for p in props]); mus = np.array([p[1] for p in props]); g = np.array([p[2] for p in props])
    Phi, Lz, Rr, Lr, raw = mc.fluence_and_paths(nphot, th, mua, mus, g, seed=seed)
    ci = _canon_index(names)
    out = {}
    for a in BEAM_RADII:
        # Absorbed weight per bin is already a volume integral of the pencil response, so the
        # on-axis fluence of a flat-top disc beam (per unit incident fluence) is the plain sum
        # of the bins inside the beam radius divided by (mua dz).
        wgt = (R_PENCIL < a).astype(float)
        A = (raw["A"] * wgt[:, None]).sum(0)                        # absorbed weight per z (per J/cm^2)
        PL = (raw["PL"] * wgt[None, :, None]).sum(1)                  # [L, NZ]
        PL2 = (raw["PL2"] * wgt[None, :, None]).sum(1)
        with np.errstate(invalid="ignore", divide="ignore"):
            L1 = np.where(A > 0, PL / np.maximum(A, 1e-300), 0.0)
            L2 = np.where(A > 0, PL2 / np.maximum(A, 1e-300), 0.0)
        phi = A / mc.DZ / raw["mua_z"]
        L1c = np.zeros((len(LAYERS_CANON), mc.NZ)); L2c = np.zeros_like(L1c)
        L1c[ci] = L1; L2c[ci] = L2
        out[f"phi_a{a}"] = phi; out[f"L1_a{a}"] = L1c; out[f"L2_a{a}"] = L2c
    # NIRS reflectance (pencil source) at rho in RHO_NIRS: average over +-0.1 cm ring
    Rn = []; Ln = []
    for rho in RHO_NIRS:
        sel = np.abs(R_PENCIL - rho) <= 0.1
        Rn.append(Rr[sel].mean())
        Lc = np.zeros(len(LAYERS_CANON))
        Lc[ci] = (Lr[:, sel] * Rr[sel][None]).sum(1) / max(Rr[sel].sum(), 1e-300)
        Ln.append(Lc)
    out["R_nirs"] = np.array(Rn); out["L_nirs"] = np.array(Ln)   # [nrho], [nrho, L]
    out["mua"] = np.zeros(len(LAYERS_CANON)); out["mua"][ci] = mua
    out["mua_z"] = raw["mua_z"]
    return (lam, bone, mscale, so2v), out


def build_table(path, nphot=100_000, lams=tissue.CANDIDATE_WAVELENGTHS, nproc=4, seed0=100):
    jobs = [(lam, b, m, s, nphot, seed0 + i) for i, (lam, b, m, s) in
            enumerate(itertools.product(lams, BONE_GRID, MUS_GRID, SO2V_GRID))]
    with Pool(nproc) as p:
        res = p.map(_one, jobs)
    store = {"lams": np.array(lams), "bone": np.array(BONE_GRID), "mus": np.array(MUS_GRID),
             "so2v": np.array(SO2V_GRID),
             "radii": np.array(BEAM_RADII), "rho": np.array(RHO_NIRS), "z": Z, "nphot": nphot}
    for (lam, b, m, s), out in res:
        for k, v in out.items():
            store[f"{k}|{lam}|{b}|{m}|{s}"] = v
    np.savez_compressed(path, **store)
    return path


class FluenceModel:
    """Interpolating fluence/reflectance model on top of the MC table."""

    def __init__(self, path):
        d = np.load(path)
        self.d = {k: d[k] for k in d.files}
        self.lams = tuple(int(x) for x in self.d["lams"]); self.bone = tuple(self.d["bone"])
        self.mus = tuple(self.d["mus"]); self.so2v = tuple(self.d["so2v"]); self.z = self.d["z"]

    @staticmethod
    def _bracket(grid, v):
        g = np.array(grid); v = float(np.clip(v, g[0], g[-1]))
        i = int(np.clip(np.searchsorted(g, v, side="right") - 1, 0, len(g) - 2))
        return i, (v - g[i]) / (g[i + 1] - g[i]), g

    def _get(self, key, lam, bone, mscale, so2v, log=None):
        """Trilinear interpolation in (bone, mus_scale, sinus sO2); log for fluence-like keys."""
        ib, fb, bg = self._bracket(self.bone, bone)
        im, fm, mg = self._bracket(self.mus, mscale)
        iv, fv, vg = self._bracket(self.so2v, so2v)
        logkey = (key.startswith("phi") or key.startswith("R_nirs")) if log is None else log
        acc = 0.0
        for db, wb in ((0, 1 - fb), (1, fb)):
            for dm, wm in ((0, 1 - fm), (1, fm)):
                for dv, wv in ((0, 1 - fv), (1, fv)):
                    w = wb * wm * wv
                    if w == 0.0:
                        continue
                    v = self.d[f"{key}|{lam}|{bg[ib + db]}|{mg[im + dm]}|{vg[iv + dv]}"]
                    acc = acc + w * (np.log(np.maximum(v, 1e-300)) if logkey else v)
        return np.exp(acc) if logkey else acc

    def nominal_mua(self, lam, so2v=0.65):
        """Layer absorption the table node (interpolated linearly in sinus sO2) was built with."""
        return self._get("mua", lam, self.bone[0], 1.0, so2v, log=False)

    def fluence(self, lam, bone, mscale, a, dmua, so2v=0.65, second_order=True):
        """On-axis fluence vs depth (1/cm^2 per J/cm^2 incident) for layer absorption
        changes dmua[6] (1/cm) relative to the table's (interpolated) nominal absorption."""
        phi0 = self._get(f"phi_a{a}", lam, bone, mscale, so2v)
        L1 = self._get(f"L1_a{a}", lam, bone, mscale, so2v)
        expo = -(dmua[:, None] * L1).sum(0)
        if second_order:
            L2 = self._get(f"L2_a{a}", lam, bone, mscale, so2v)
            var = np.maximum(L2 - L1 ** 2, 0.0)
            expo = expo + 0.5 * (dmua[:, None] ** 2 * var).sum(0)
        return phi0 * np.exp(expo)

    def reflectance_nirs(self, lam, bone, mscale, dmua, so2v=0.65):
        R0 = self._get("R_nirs", lam, bone, mscale, so2v)
        L = self._get("L_nirs", lam, bone, mscale, so2v)        # [nrho, L]
        return R0 * np.exp(-(L * dmua[None, :]).sum(1))
