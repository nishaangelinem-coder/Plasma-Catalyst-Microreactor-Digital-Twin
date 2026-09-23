"""Operating scenarios: DoE excitation and intermittent renewable power."""
import numpy as np

BOUNDS = dict(V=(6.5, 11.0), f=(10.0, 25.0), Q=(40.0, 200.0), xH2=(0.5, 0.85))


def random_doe_inputs(n, seed):
    """Space-filling random excitation (log-uniform flow) used for twin identification."""
    rng = np.random.default_rng(seed)
    V = rng.uniform(*BOUNDS["V"], n)
    f = rng.uniform(*BOUNDS["f"], n)
    Q = np.exp(rng.uniform(np.log(BOUNDS["Q"][0]), np.log(BOUNDS["Q"][1]), n))
    x = rng.uniform(*BOUNDS["xH2"], n)
    return np.column_stack([V, f, Q, x])


def renewable_power(n, dt_h, seed, base=18.0, solar=50.0, wind_sd=8.0):
    """Available electric power (W): PV diurnal profile + AR(1) wind + base load."""
    rng = np.random.default_rng(5000 + seed)
    t = np.arange(n) * dt_h
    pv = solar * np.clip(np.sin(2 * np.pi * (t - 6.0) / 24.0), 0.0, None)
    cloud = np.clip(1.0 - 0.5 * rng.beta(2, 5, n), 0.3, 1.0)
    w = np.zeros(n)
    for k in range(1, n):
        w[k] = 0.9 * w[k - 1] + rng.normal(0.0, wind_sd * np.sqrt(1 - 0.81))
    return np.clip(base + pv * cloud + w + 10.0, 10.0, 85.0)
