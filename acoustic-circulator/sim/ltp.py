"""
Linear time-periodic (LTP) harmonic-balance solver for lumped networks that
contain periodically time-varying capacitors (conversion-matrix method).

This is the same analysis that Cadence Spectre performs with PSS followed by
PSP (periodic S-parameter) analysis: the network is linear in the RF signal,
but the capacitors are modulated at a pump frequency f_m, so an input at
frequency f is converted to f + k f_m (k = ..., -1, 0, 1, ...).

A modulated capacitor  q(t) = C(t) v(t),  C(t) = sum_k c_k exp(j k w_m t)
gives, for v(t) = sum_l V_l exp(j (w + l w_m) t),

    I_m = j (w + m w_m) * sum_l c_{m-l} V_l

i.e. a Toeplitz conversion matrix.  Everything else is LTI and block-diagonal
across the sidebands.  Modified nodal analysis with admittance stamps only
(all elements are 2-terminal admittances, ports are Norton sources).
"""
from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import Callable, List, Tuple


@dataclass
class Element:
    kind: str                 # 'R', 'L', 'C', 'TVC' (time varying capacitor), 'SER' (series RLC branch)
    n1: int
    n2: int
    value: float = 0.0        # R [ohm], L [H], C [F]
    ck: np.ndarray | None = None   # Fourier coefficients c_k, k=-K..K for 'TVC'
    rlc: Tuple[float, float, float] | None = None   # (R, L, C) for a series branch (C=inf allowed)


@dataclass
class Port:
    node: int
    z0: float = 50.0


@dataclass
class Network:
    nnodes: int                      # number of non-ground nodes (ground = 0, nodes 1..nnodes)
    elements: List[Element] = field(default_factory=list)
    ports: List[Port] = field(default_factory=list)

    # ---- builders -------------------------------------------------------
    def R(self, n1, n2, r):  self.elements.append(Element('R', n1, n2, r))
    def L(self, n1, n2, l):  self.elements.append(Element('L', n1, n2, l))
    def C(self, n1, n2, c):  self.elements.append(Element('C', n1, n2, c))
    def SER(self, n1, n2, r, l, c): self.elements.append(Element('SER', n1, n2, rlc=(r, l, c)))
    def TVC(self, n1, n2, ck): self.elements.append(Element('TVC', n1, n2, ck=np.asarray(ck, complex)))
    def port(self, node, z0=50.0): self.ports.append(Port(node, z0))

    # ---- analysis -------------------------------------------------------
    def solve(self, f: float, fm: float, K: int, return_voltages: bool = False):
        """Return S[k][m, n]: scattering from port n (fundamental, k=0) to port m at sideband k.
        Returned as array of shape (2K+1, P, P); index k+K is sideband k.
        With return_voltages=True also returns V[n][node, k] (node voltages for a 1-V source at port n)."""
        Nh = 2 * K + 1
        ks = np.arange(-K, K + 1)
        w = 2 * np.pi * (f + ks * fm)                # sideband angular frequencies
        N = self.nnodes
        Y = np.zeros((N * Nh, N * Nh), complex)

        def stamp(n1, n2, Yb):
            # Yb: (Nh, Nh) admittance block between n1 and n2 (0 = ground)
            if n1:
                i = (n1 - 1) * Nh
                Y[i:i + Nh, i:i + Nh] += Yb
            if n2:
                j = (n2 - 1) * Nh
                Y[j:j + Nh, j:j + Nh] += Yb
            if n1 and n2:
                Y[i:i + Nh, j:j + Nh] -= Yb
                Y[j:j + Nh, i:i + Nh] -= Yb

        for e in self.elements:
            if e.kind == 'R':
                stamp(e.n1, e.n2, np.diag(np.full(Nh, 1.0 / e.value, complex)))
            elif e.kind == 'L':
                stamp(e.n1, e.n2, np.diag(1.0 / (1j * w * e.value)))
            elif e.kind == 'C':
                stamp(e.n1, e.n2, np.diag(1j * w * e.value))
            elif e.kind == 'SER':
                r, l, c = e.rlc
                z = r + 1j * w * l + (0 if np.isinf(c) else 1.0 / (1j * w * c))
                stamp(e.n1, e.n2, np.diag(1.0 / z))
            elif e.kind == 'TVC':
                ck = e.ck
                Kc = (len(ck) - 1) // 2
                T = np.zeros((Nh, Nh), complex)
                for m in range(Nh):
                    for l in range(Nh):
                        d = (m - l)
                        if abs(d) <= Kc:
                            T[m, l] = ck[d + Kc]
                stamp(e.n1, e.n2, (1j * w)[:, None] * T)
            else:
                raise ValueError(e.kind)

        # ports: z0 to ground
        for p in self.ports:
            stamp(p.node, 0, np.diag(np.full(Nh, 1.0 / p.z0, complex)))

        P = len(self.ports)
        S = np.zeros((Nh, P, P), complex)
        Vall = np.zeros((P, N, Nh), complex)
        lu = np.linalg.inv(Y)  # small systems; direct inverse is fine
        for n, pn in enumerate(self.ports):
            # Norton source: Vs = 1 V at fundamental into port n
            vs = 1.0
            I = np.zeros(N * Nh, complex)
            I[(pn.node - 1) * Nh + K] = vs / pn.z0
            V = lu @ I
            Vall[n] = V.reshape(N, Nh)
            a_n = vs / (2 * np.sqrt(pn.z0))
            for m, pm in enumerate(self.ports):
                Vm = V[(pm.node - 1) * Nh:(pm.node) * Nh]
                b = Vm / np.sqrt(pm.z0)                      # passive port: I_in = -V/z0
                if m == n:
                    b = b.copy(); b[K] = (2 * Vm[K] - vs) / (2 * np.sqrt(pm.z0))
                S[:, m, n] = b / a_n
        if return_voltages:
            return S, Vall
        return S


def fourier_coeffs(c_of_t: Callable[[np.ndarray], np.ndarray], K: int, nsamp: int = 4096) -> np.ndarray:
    """Fourier coefficients c_k, k=-K..K of a 1-periodic function c(theta/2pi) sampled on theta in [0,2pi)."""
    th = np.arange(nsamp) * 2 * np.pi / nsamp
    c = c_of_t(th)
    Ck = np.fft.fft(c) / nsamp
    out = np.zeros(2 * K + 1, complex)
    for k in range(-K, K + 1):
        out[k + K] = Ck[k % nsamp]
    return out


def db(x):
    return 20 * np.log10(np.maximum(np.abs(x), 1e-30))
