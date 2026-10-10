"""Layered Monte Carlo photon transport (MCML-type) with partial path-length recording.

A pencil beam enters at the origin normal to the surface. Absorbed weight is binned in
(r, z); for every layer j the product weight x (path length already travelled in layer j)
is binned as well, so that the mean partial path length <L_j>(r, z) of the photons that
contribute to the fluence at (r, z) is available. The same is done for diffusely
reflected photons versus exit radius. These "Hiraoka" partial path lengths give a fast
and accurate first-order (Beer-Lambert) correction of the fluence and reflectance for
changes in layer absorption (haemoglobin concentration / oxygenation), which the
virtual neonate uses to update the optical forward model every frame without a new
Monte Carlo run.

Units: cm. Outputs are per unit incident energy (fluence in 1/cm^2 per J injected).
"""
from __future__ import annotations
import numpy as np
from numba import njit

NR, DR = 80, 0.05      # radial bins to 4 cm
NZ, DZ = 160, 0.025    # depth bins to 4 cm
WCRIT, CHANCE = 1e-4, 0.1


@njit(cache=True)
def _fresnel(n1, n2, ca1):
    """Fresnel reflectance for unpolarised light, incident cosine ca1 in medium n1."""
    if n1 == n2:
        return 0.0, ca1
    if ca1 > 1.0 - 1e-12:
        r = ((n2 - n1) / (n2 + n1)) ** 2
        return r, 1.0
    if ca1 < 1e-6:
        return 1.0, 0.0
    sa1 = np.sqrt(1.0 - ca1 * ca1)
    sa2 = n1 * sa1 / n2
    if sa2 >= 1.0:
        return 1.0, 0.0
    ca2 = np.sqrt(1.0 - sa2 * sa2)
    cap = ca1 * ca2 - sa1 * sa2
    cam = ca1 * ca2 + sa1 * sa2
    sap = sa1 * ca2 + ca1 * sa2
    sam = sa1 * ca2 - ca1 * sa2
    r = 0.5 * sam * sam * (cam * cam + cap * cap) / (sap * sap * cam * cam)
    return r, ca2


@njit(cache=True)
def run_mc(nphot, thick, mua, mus, g, n_tissue, seed):
    """Run nphot photon packets. Returns (A, PL, PL2, R, RL)
    A  : absorbed weight [NR, NZ]
    PL : absorbed weight x partial path length [L, NR, NZ]
    PL2: absorbed weight x partial path length squared [L, NR, NZ]
    R  : diffuse reflectance weight [NR]
    RL : reflectance weight x partial path length [L, NR]
    """
    np.random.seed(seed)
    L = thick.shape[0]
    zb = np.zeros(L + 1)
    for j in range(L):
        zb[j + 1] = zb[j] + thick[j]
    A = np.zeros((NR, NZ))
    PL = np.zeros((L, NR, NZ))
    PL2 = np.zeros((L, NR, NZ))
    R = np.zeros(NR)
    RL = np.zeros((L, NR))
    rsp = ((n_tissue - 1.0) / (n_tissue + 1.0)) ** 2  # specular at entry
    pl = np.zeros(L)
    for ip in range(nphot):
        x = 0.0; y = 0.0; z = 0.0
        ux = 0.0; uy = 0.0; uz = 1.0
        w = 1.0 - rsp
        lay = 0
        for j in range(L):
            pl[j] = 0.0
        sleft = 0.0
        alive = True
        nstep = 0
        while alive and nstep < 20000:
            nstep += 1
            mut = mua[lay] + mus[lay]
            if sleft <= 0.0:
                sleft = -np.log(np.random.random() + 1e-300)
            s = sleft / mut
            # distance to layer boundary
            if uz > 0.0:
                db = (zb[lay + 1] - z) / uz
            elif uz < 0.0:
                db = (zb[lay] - z) / uz
            else:
                db = 1e30
            if db < s:
                # move to boundary
                x += ux * db; y += uy * db; z += uz * db
                pl[lay] += db
                sleft -= db * mut
                # cross or reflect
                if uz < 0.0 and lay == 0:
                    # exit to air?
                    rf, ca2 = _fresnel(n_tissue, 1.0, -uz)
                    if np.random.random() > rf:
                        # exits: record reflectance
                        r = np.sqrt(x * x + y * y)
                        ir = int(r / DR)
                        if ir < NR:
                            R[ir] += w
                            for j in range(L):
                                RL[j, ir] += w * pl[j]
                        alive = False
                        continue
                    uz = -uz
                elif uz < 0.0:
                    lay -= 1
                    z = zb[lay + 1]
                else:
                    if lay == L - 1:
                        alive = False  # left the bottom of the (deep) brain layer
                        continue
                    lay += 1
                    z = zb[lay]
                continue
            # full step
            x += ux * s; y += uy * s; z += uz * s
            pl[lay] += s
            sleft = 0.0
            # absorb
            dw = w * mua[lay] / mut
            w -= dw
            r = np.sqrt(x * x + y * y)
            ir = int(r / DR); iz = int(z / DZ)
            if ir < NR and iz < NZ and iz >= 0:
                A[ir, iz] += dw
                for j in range(L):
                    PL[j, ir, iz] += dw * pl[j]
                    PL2[j, ir, iz] += dw * pl[j] * pl[j]
            # scatter (Henyey-Greenstein)
            gg = g[lay]
            if gg == 0.0:
                ct = 2.0 * np.random.random() - 1.0
            else:
                tmp = (1.0 - gg * gg) / (1.0 - gg + 2.0 * gg * np.random.random())
                ct = (1.0 + gg * gg - tmp * tmp) / (2.0 * gg)
                if ct < -1.0: ct = -1.0
                if ct > 1.0: ct = 1.0
            st = np.sqrt(1.0 - ct * ct)
            psi = 2.0 * np.pi * np.random.random()
            cp = np.cos(psi); sp = np.sin(psi)
            if abs(uz) > 0.99999:
                nx = st * cp; ny = st * sp; nz = ct * (1.0 if uz >= 0 else -1.0)
            else:
                den = np.sqrt(1.0 - uz * uz)
                nx = st * (ux * uz * cp - uy * sp) / den + ux * ct
                ny = st * (uy * uz * cp + ux * sp) / den + uy * ct
                nz = -st * cp * den + uz * ct
            ux = nx; uy = ny; uz = nz
            # roulette
            if w < WCRIT:
                if np.random.random() < CHANCE:
                    w /= CHANCE
                else:
                    alive = False
            if z > 8.0 or r > 8.0:
                alive = False
    return A, PL, PL2, R, RL


def fluence_and_paths(nphot, thick, mua, mus, g, n_tissue=1.4, seed=0):
    """Normalised pencil-beam fluence Phi[NR,NZ] (1/cm^2 per J), mean partial paths
    Lz[L,NR,NZ] (cm), reflectance per area Rr[NR] (1/cm^2 per J), reflectance partial
    paths Lr[L,NR] (cm)."""
    A, PL, PL2, R, RL = run_mc(int(nphot), np.asarray(thick, float), np.asarray(mua, float),
                               np.asarray(mus, float), np.asarray(g, float), float(n_tissue), int(seed))
    ir = np.arange(NR)
    vol = 2.0 * np.pi * (ir + 0.5) * DR * DR * DZ        # annulus volume per z-bin
    area = 2.0 * np.pi * (ir + 0.5) * DR * DR
    iz = np.arange(NZ)
    # layer of each depth bin
    zb = np.concatenate([[0.0], np.cumsum(thick)])
    zc = (iz + 0.5) * DZ
    lay = np.clip(np.searchsorted(zb, zc, side="right") - 1, 0, len(thick) - 1)
    mua_z = np.asarray(mua)[lay]
    Phi = A / nphot / vol[:, None] / mua_z[None, :]
    with np.errstate(invalid="ignore", divide="ignore"):
        Lz = np.where(A[None] > 0, PL / np.maximum(A[None], 1e-300), 0.0)
        Lr = np.where(R[None] > 0, RL / np.maximum(R[None], 1e-300), 0.0)
    Rr = R / nphot / area
    raw = dict(A=A / nphot, PL=PL / nphot, PL2=PL2 / nphot, R=R / nphot, RL=RL / nphot, mua_z=mua_z)
    return Phi, Lz, Rr, Lr, raw
