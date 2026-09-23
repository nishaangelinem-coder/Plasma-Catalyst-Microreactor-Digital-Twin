import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from pcmr.plant import Plant, Inputs, manley_power, manley_voltage_for_power  # noqa: E402
from pcmr import twin_model as tm, twins as TW, control as C  # noqa: E402
from pcmr.scenario import random_doe_inputs  # noqa: E402


def test_manley_inverse():
    P = manley_power(9.0, 20.0, 2.5, 40e-12, 10e-12)
    assert abs(P - 47.0) < 1e-6
    assert abs(manley_voltage_for_power(P, 20.0, 2.5, 40e-12, 10e-12) - 9.0) < 1e-9


def test_plant_limiter_and_ranges():
    pl = Plant()
    s = pl.steady_state(Inputs(11.0, 25.0, 100.0, 0.75), P_cap=30.0)
    assert s["limited"] and abs(s["P"] - 30.0) < 1e-9
    s = pl.steady_state(Inputs(9.0, 20.0, 100.0, 0.75))
    assert 0.1 < 100 * s["y"] < 3.0 and 0.1 < s["EY"] < 3.0     # DBD literature range


def test_deactivation_monotone():
    pl = Plant(seed=1)
    a = [pl.step(Inputs(10, 20, 100, 0.75), 0.5)["a_true"] for _ in range(50)]
    assert np.all(np.diff(a) <= 0)


def test_twin_vectorised_shapes():
    ly, lP, T = tm.predict(np.ones((7, 4)) * [9, 20, 100, 0.75], np.zeros((5, 3)))
    assert ly.shape == lP.shape == T.shape == (5, 7)
    assert tm.features(np.ones((3, 4)) * [9, 20, 100, 0.75]).shape == (3, tm.N_FEAT)


def test_pchdt_beats_static_physics():
    U = random_doe_inputs(160, 3); pl = Plant(seed=3)
    tw = [TW.StaticPhysicsTwin(), TW.PCHDT(seed=3)]
    err = np.zeros((2, 160))
    for k in range(160):
        f = [t.forecast(U[k])[0][0] for t in tw]
        o = pl.step(Inputs(*U[k]), 0.5)
        z = np.array([np.log(o["y_meas"]), np.log(o["P_meas"]), o["T_meas"]])
        err[:, k] = np.abs(np.array(f) - z[0])
        for t in tw:
            t.update(U[k], z)
    assert err[1, 60:].mean() < 0.5 * err[0, 60:].mean()


def test_optimiser_respects_temperature_constraint_nominal():
    u = C.nominal_optimum(460.0, P_cap=80.0)
    _, _, T = tm.predict(u, tm.THETA0)
    assert T.item() <= 460.0
