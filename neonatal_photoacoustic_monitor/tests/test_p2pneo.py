import os, sys, numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from p2pneo import tissue, mc, acoustic as ac, thermal, estimators as est
from p2pneo.fluence import FluenceModel, LAYERS_CANON
from p2pneo.forward import ForwardModel, HeadParams

TABLE = os.path.join(os.path.dirname(__file__), "..", "results", "fluence_table.npz")


def test_extinction_isosbestic():
    eo, ed = tissue.extinction(800)
    assert abs(eo - ed) / eo < 0.1          # 800 nm is close to the isosbestic point


def test_mua_blood_order_of_magnitude():
    mua = tissue.mua_blood_tissue(800, 0.65, 2300.0)
    assert 3.0 < mua < 6.0                  # whole blood ~4 /cm at 800 nm


def test_mc_energy_conservation_small():
    names, th = tissue.head_geometry(0.0)
    props = [tissue.layer_props(n, 800) for n in names]
    mua = np.array([p[0] for p in props]); mus = np.array([p[1] for p in props]); g = np.array([p[2] for p in props])
    Phi, Lz, Rr, Lr, raw = mc.fluence_and_paths(3000, th, mua, mus, g, seed=1)
    r = (np.arange(mc.NR) + 0.5) * mc.DR
    R_tot = (Rr * 2 * np.pi * r * mc.DR).sum()
    A_tot = raw["A"].sum()
    assert 0.2 < R_tot < 0.9 and 0.0 < A_tot < 1.0
    assert R_tot + A_tot < 1.05


def test_mpe():
    assert abs(ac.mpe_single_pulse_mJcm2(800) - 31.7) < 0.2
    assert ac.allowed_fluence(800, 10.0) <= 0.5 * ac.mpe_single_pulse_mJcm2(800)


def test_transducer_response_peak():
    H = ac.transducer_response(ac.Transducer("t"), 8.0)
    assert 0.95 < H.max() <= 1.0


def test_echo_shift_recovers_known_delay():
    rng = np.random.default_rng(0)
    td = ac.Transducer("t", echo_snr_db=40.0)
    t0 = [5e-6, 20e-6]
    ref = ac.echo_trace(td, t0, [1.0, 0.5], rng, 100)
    tr = ac.echo_trace(td, [5e-6 + 3e-9, 20e-6 + 10e-9], [1.0, 0.5], rng, 100)
    d1 = ac.echo_shift(tr, ref, (4.5e-6, 5.5e-6)); d2 = ac.echo_shift(tr, ref, (19e-6, 21e-6))
    assert abs(d1 - 3e-9) < 1e-9 and abs(d2 - 10e-9) < 1e-9


@pytest.mark.skipif(not os.path.exists(TABLE), reason="fluence table not built")
def test_fluence_table_monotone_and_perturbation():
    fl = FluenceModel(TABLE)
    phi = fl.fluence(800, 0.0, 1.0, 0.5, np.zeros(6), 0.65)
    assert phi[2] > phi[20] > phi[60]
    dm = np.zeros(6); dm[LAYERS_CANON.index("brain")] = 0.05
    phi2 = fl.fluence(800, 0.0, 1.0, 0.5, dm, 0.65)
    assert np.all(phi2[40:] <= phi[40:] + 1e-12)


@pytest.mark.skipif(not os.path.exists(TABLE), reason="fluence table not built")
def test_forward_signal_scales_with_fluence_and_gain():
    fl = FluenceModel(TABLE)
    src = ac.Source("s", (750, 800, 850, 900), 10.0, 8.0, 2.5, 0.5)
    dev = ac.DeviceConfig("d", src, ac.Transducer("t"))
    fm = ForwardModel(fl, HeadParams(), dev)
    p1, _ = fm.pa_trace(800, 0.65, 37.0, 34.0, 1.0)
    p2, _ = fm.pa_trace(800, 0.65, 37.0, 34.0, 2.0)
    assert np.allclose(p2, 2 * p1)
    a1 = ac.gate_amplitude(p1, dev.brain_gate); a2 = ac.gate_amplitude(p2, dev.brain_gate)
    assert abs(a2 / a1 - 2.0) < 1e-6
    # Grueneisen temperature dependence: warmer sinus -> larger signal
    p3, _ = fm.pa_trace(800, 0.65, 40.0, 34.0, 1.0)
    assert ac.gate_amplitude(p3, dev.brain_gate) > a1


@pytest.mark.skipif(not os.path.exists(TABLE), reason="fluence table not built")
def test_ekf_converges_on_static_truth():
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "experiments"))
    import common
    from p2pneo.subject import scenario_static, sample_head
    fl = FluenceModel(TABLE); rng = np.random.default_rng(5)
    head = sample_head(rng); dev = common.make_devices()["bedside"]
    scen = scenario_static(rng, 0.55, 35.0, dt=10.0, minutes=5.0, head=head)
    res = common.run_sequence(fl, head, dev, scen, rng, ablations=False)
    assert abs(np.nanmean(res["so2"]["Proposed EKF"][-5:]) - 0.55) < 0.10
    assert abs(np.nanmean(res["T"]["Proposed EKF"][-5:]) - 35.0) < 0.8


def test_thermal_model_runs_and_heats():
    names, th = tissue.head_geometry(0.0); th = th.copy(); th[-1] = 5.0
    z = (np.arange(mc.NZ) + 0.5) * mc.DZ
    phi = 4.0 * np.exp(-z / 0.3); mua = 0.15 * np.ones_like(z)
    out0 = thermal.simulate(names, th, mua, phi, z, 0.0, t_end_s=300.0)
    out1 = thermal.simulate(names, th, mua, phi, z, 0.2, t_end_s=300.0)
    assert out1[4][-1] > out0[4][-1]
