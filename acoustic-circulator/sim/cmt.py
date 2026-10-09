"""
Temporal coupled-mode theory (CMT) of a three-resonator loop with
angular-momentum biasing (Estep et al., Nat. Phys. 2014), solved exactly in
the Floquet/harmonic-balance sense.

  da_n/dt = [ j w_n(t) - g_i - g_e ] a_n + j k (a_{n+1} + a_{n-1}) + sqrt(2 g_e) s_in,n
  s_out,n = - s_in,n + sqrt(2 g_e) a_n
  w_n(t)  = w_0 + dw * cos( w_m t - 2 pi n / 3 )

All rates in rad/s.  Returns scattering matrix at the fundamental and at the
sidebands exactly like sim.ltp.Network.solve().
"""
from __future__ import annotations
import numpy as np


def cmt_sparams(f, w0, gi, ge, kappa, dw, fm, direction=+1, K=6, mod='sine', duty=0.5):
    """S[k+K, m, n] for an excitation at frequency f (Hz)."""
    Nh = 2 * K + 1
    ks = np.arange(-K, K + 1)
    w = 2 * np.pi * (f + ks * fm)
    N = 3
    A = np.zeros((N * Nh, N * Nh), complex)
    # modulation Fourier coefficients of  m(t) = cos(theta)  (sine)  or  sign(cos theta) (square)
    if mod == 'sine':
        mk = {1: 0.5, -1: 0.5}
    else:  # square wave of amplitude 1, same fundamental phase as cos
        mk = {}
        for q in range(-K, K + 1):
            if q == 0 or q % 2 == 0:
                continue
            mk[q] = (2 / (np.pi * q)) * np.sin(np.pi * q / 2)   # coefficient of exp(j q theta)
    for n in range(N):
        phi = direction * 2 * np.pi * n / 3
        for i in range(Nh):
            row = n * Nh + i
            # j w_i a - (j w0 - g) a   ... written as  (j (w_i - w0) + g) a_i - j dw sum_q m_q e^{-j q phi} a_{i-q} - j k (a_{n+1,i} + a_{n-1,i}) = sqrt(2ge) s_in
            A[row, row] += 1j * (w[i] - w0) + gi + ge
            for q, c in mk.items():
                j = i - q
                if 0 <= j < Nh:
                    A[row, n * Nh + j] += -1j * dw * c * np.exp(-1j * q * phi)
            for nb in ((n + 1) % 3, (n - 1) % 3):
                A[row, nb * Nh + i] += -1j * kappa
    Ainv = np.linalg.inv(A)
    S = np.zeros((Nh, N, N), complex)
    for n in range(N):
        b = np.zeros(N * Nh, complex)
        b[n * Nh + K] = np.sqrt(2 * ge)
        a = Ainv @ b
        for m in range(N):
            s_out = np.sqrt(2 * ge) * a[m * Nh:(m + 1) * Nh]
            if m == n:
                s_out = s_out.copy(); s_out[K] -= 1.0
            S[:, m, n] = s_out
    return S


def cmt_sweep(freqs, **kw):
    K = kw.get('K', 6)
    out = np.zeros((len(freqs), 2 * K + 1, 3, 3), complex)
    for i, f in enumerate(freqs):
        out[i] = cmt_sparams(f, **kw)
    return out
