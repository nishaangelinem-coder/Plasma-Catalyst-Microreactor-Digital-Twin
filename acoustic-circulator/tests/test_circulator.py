import os, sys, subprocess, numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim.ltp import Network, db
from sim.cmt import cmt_sparams
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_tvc_sideband_matches_analytic():
    K = 3; C0 = 0.1e-12; dC = 0.02e-12; fm = 37.5e6; f = 1e9
    net = Network(nnodes=2); net.port(1, 50); net.port(2, 50)
    ck = np.zeros(2 * K + 1, complex); ck[K] = C0; ck[K + 1] = dC / 2; ck[K - 1] = dC / 2
    net.TVC(1, 2, ck)
    S = net.solve(f, fm, K)
    expected = db(S[K, 1, 0]) + 20 * np.log10((dC / 2) / C0 * (f + fm) / f)
    assert abs(db(S[K + 1, 1, 0]) - expected) < 0.05


def test_unmodulated_loop_is_reciprocal_and_lossless_split():
    w0 = 2 * np.pi * 1e9; Ct = 3e-12; Lt = 1 / (w0 ** 2 * Ct); Cp = 0.219e-12; Cc = 0.18e-12
    net = Network(nnodes=6)
    for n in range(3):
        P, T = 1 + n, 4 + n
        net.port(P, 50); net.C(P, T, Cp); net.L(T, 0, Lt); net.C(T, 0, Ct); net.C(T, 4 + (n + 1) % 3, Cc)
    f = np.linspace(0.9e9, 1.0e9, 2001)
    S = np.array([net.solve(ff, 1e6, 0)[0] for ff in f])
    i = np.argmax(abs(S[:, 1, 0]))
    assert abs(db(S[i, 1, 0]) - (-3.52)) < 0.1 and abs(db(S[i, 2, 0]) - db(S[i, 1, 0])) < 0.01
    assert np.allclose(S[i, 1, 0], S[i, 0, 1])


def test_cmt_matches_ltp_weak_coupling():
    w0 = 2 * np.pi * 1e9; Ct = 3e-12; Lt = 1 / (w0 ** 2 * Ct); Cc = 0.02e-12; Cp = 0.08e-12; K = 8
    Ctot = Ct + Cp + 2 * Cc; w0c = 1 / np.sqrt(Lt * Ctot); ge = (w0c * Cp) ** 2 * 50 / (2 * Ctot)
    fm = 15 * ge / 2 / np.pi; dC1 = 5.6 * ge * 2 * Ctot / w0c
    w00 = 1 / np.sqrt(Lt * (Ct + Cp)); w1 = 1 / np.sqrt(Lt * (Ct + Cp + 3 * Cc)); kappa = (w00 - w1) / 3; w0cmt = w00 - 2 * kappa
    net = Network(nnodes=6)
    for n in range(3):
        P, T = 1 + n, 4 + n; net.port(P, 50); net.C(P, T, Cp); net.L(T, 0, Lt)
        ck = np.zeros(2 * K + 1, complex); ck[K] = Ct; phi = 2 * np.pi * n / 3
        ck[K + 1] = dC1 / 2 * np.exp(-1j * phi); ck[K - 1] = dC1 / 2 * np.exp(1j * phi)
        net.TVC(T, 0, ck); net.C(T, 4 + (n + 1) % 3, Cc)
    fs = np.linspace(w1 / 2 / np.pi - 3e6, w1 / 2 / np.pi + 3e6, 601)
    Sl = np.array([net.solve(ff, fm, K)[K] for ff in fs]); Sc = np.array([cmt_sparams(ff, w0cmt, 0.0, ge, kappa, w0c * dC1 / (2 * Ctot), fm, K=K)[K] for ff in fs])
    # both must show strong circulation (one of S21/S31 below -25 dB with the other above -1.5 dB)
    for S in (Sl, Sc):
        iso = np.minimum(db(S[:, 1, 0]), db(S[:, 2, 0])); thr = np.maximum(db(S[:, 1, 0]), db(S[:, 2, 0]))
        i = np.argmin(iso)
        assert iso[i] < -25 and thr[i] > -1.5


def test_phase_generator_120_degrees():
    cir = os.path.join(ROOT, 'spice', 'tb_phasegen.cir')
    out = subprocess.run(['ngspice', '-b', cir], capture_output=True, text=True, cwd=os.path.join(ROOT, 'spice'))
    m = {}
    for line in out.stdout.splitlines():
        for k in ('t0', 't1', 't2'):
            if line.startswith(k + ' '):
                m[k] = float(line.split('=')[1].split()[0])
    T = 40e-9
    ph2 = ((m['t1'] - m['t0']) / T * 360) % 360; ph3 = ((m['t2'] - m['t0']) / T * 360) % 360
    assert abs(ph2 - 120) < 2 and abs(ph3 - 240) < 2


def test_final_design_circulates():
    import json
    from sim.load_design import load_design
    from sim.circulator import sparams
    des, p = load_design()
    S = sparams(des, np.array([1.0e9]), 6)[0, 6]
    fwd = [S[1, 0], S[2, 1], S[0, 2]]; rev = [S[0, 1], S[1, 2], S[2, 0]]
    IL = -db(np.array(fwd)).max(); ISO = -db(np.array(rev)).min()
    assert IL < 6.0 and ISO > 18.0
