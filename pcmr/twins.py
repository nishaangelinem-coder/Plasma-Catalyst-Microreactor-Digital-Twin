"""Digital-twin estimators.

Every twin implements
    forecast(u) -> (mean[3], std[3])  one-step-ahead prediction of the next
                   measurement z = [ln y_NH3, ln P, T] at a NEW operating point u
    update(u, z)  assimilate the measurement taken at u
and physics-based twins additionally expose ``activity()`` (catalyst activity
estimate) and ``ensemble()`` (parameter samples for the twin-in-the-loop optimiser).

Baselines (existing methods)
    StaticPhysicsTwin   nominal first-principles model, never updated
    BatchRecalTwin      physics model re-fitted by least squares every 24 h
    StaticMLTwin        RSM / ANN / GPR trained once on an initial DoE campaign
    SlidingGPRTwin      purely data-driven, GPR retrained on a moving window
Proposed
    PCHDT               Physics-Constrained Hybrid Digital Twin:
                        (i) EnKF joint parameter estimation with physics-informed
                            deactivation drift, (ii) innovation-triggered covariance
                            inflation for abrupt events, (iii) bias-free RLS residual
                            learner on a slower time scale, (iv) innovation-based
                            predictive-variance adaptation for calibrated UQ.
"""
from __future__ import annotations

import warnings

import numpy as np
from scipy.optimize import least_squares
from scipy.stats import chi2

from . import twin_model as tm

# sensor specification (known to all twins)
SIG_OBS = np.array([0.03, 0.02, 2.0])


def _uvec(u):
    return np.asarray(u, dtype=float).reshape(1, 4)


class StaticPhysicsTwin:
    name = "Static physics"

    def __init__(self, theta=None):
        self.theta = tm.THETA0.copy() if theta is None else np.asarray(theta, float)
        self.sig = SIG_OBS.copy()

    def _pred(self, u, theta):
        ly, lP, T = tm.predict(_uvec(u), theta)
        return np.array([ly.item(), lP.item(), T.item()])

    def forecast(self, u):
        return self._pred(u, self.theta), self.sig

    def update(self, u, z):
        pass

    def activity(self):
        return float(np.exp(self.theta[0]))

    def ensemble(self):
        return self.theta[None, :], np.zeros((tm.N_FEAT, tm.N_OUT)), self.sig


class BatchRecalTwin(StaticPhysicsTwin):
    """Periodic offline recalibration (the usual 'calibrated model' practice)."""
    name = "Batch recalibration"

    def __init__(self, period=48, window=48):
        super().__init__()
        self.period, self.window = period, window
        self.U, self.Z, self.k = [], [], 0
        self.sig = SIG_OBS * 1.5

    def update(self, u, z):
        self.U.append(np.asarray(u, float)); self.Z.append(np.asarray(z, float)); self.k += 1
        if self.k % self.period == 0:
            U = np.array(self.U[-self.window:]); Z = np.array(self.Z[-self.window:])

            def res(th):
                ly, lP, T = tm.predict(U, th)
                return np.concatenate([(ly[0] - Z[:, 0]) / SIG_OBS[0], (lP[0] - Z[:, 1]) / SIG_OBS[1],
                                       (T[0] - Z[:, 2]) / SIG_OBS[2]])
            sol = least_squares(res, self.theta, bounds=([np.log(0.05), -1.0, 0.0], [0.3, 1.0, 2.5]))
            self.theta = sol.x
            r = sol.fun.reshape(3, -1)
            self.sig = np.maximum(r.std(axis=1) * SIG_OBS, SIG_OBS)


def _xfeat(U):
    U = np.atleast_2d(U)
    return np.column_stack([U[:, 0], U[:, 1], np.log(U[:, 2]), U[:, 3]])


class StaticMLTwin:
    """Data-driven surrogate trained once on the first n_train samples."""

    def __init__(self, kind="gpr", n_train=96, seed=0):
        self.kind, self.n_train, self.seed = kind, n_train, seed
        self.name = {"rsm": "RSM (static)", "ann": "ANN (static)", "gpr": "GPR (static)"}[kind]
        self.U, self.Z, self.models, self.sig = [], [], None, None

    def _make(self):
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler, PolynomialFeatures
        from sklearn.linear_model import Ridge
        from sklearn.neural_network import MLPRegressor
        from sklearn.gaussian_process import GaussianProcessRegressor
        from sklearn.gaussian_process.kernels import RBF, WhiteKernel, ConstantKernel as C
        if self.kind == "rsm":
            return make_pipeline(StandardScaler(), PolynomialFeatures(2), Ridge(alpha=1e-3))
        if self.kind == "ann":
            return make_pipeline(StandardScaler(), MLPRegressor(hidden_layer_sizes=(32, 32), alpha=1e-3, max_iter=5000,
                                                                random_state=self.seed))
        k = C(1.0) * RBF(np.ones(4), (1e-2, 1e2)) + WhiteKernel(1e-2, (1e-6, 1.0))
        return make_pipeline(StandardScaler(), GaussianProcessRegressor(k, normalize_y=True,
                                                                        n_restarts_optimizer=2,
                                                                        random_state=self.seed))

    def _fit(self, U, Z):
        X = _xfeat(U)
        self.models, sig = [], []
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            for j in range(3):
                m = self._make().fit(X, Z[:, j])
                self.models.append(m)
                sig.append(np.std(Z[:, j] - m.predict(X)))
        self.sig = np.maximum(np.array(sig), SIG_OBS)

    def forecast(self, u):
        if self.models is None:
            return np.full(3, np.nan), np.full(3, np.nan)
        X = _xfeat(u)
        mu, sd = np.zeros(3), self.sig.copy()
        for j, m in enumerate(self.models):
            if self.kind == "gpr":
                gp = m[-1]
                mu_j, sd_j = gp.predict(m[0].transform(X), return_std=True)
                mu[j], sd[j] = mu_j.item(), sd_j.item()
            else:
                mu[j] = m.predict(X).item()
        return mu, sd

    def update(self, u, z):
        if self.models is None:
            self.U.append(np.asarray(u, float)); self.Z.append(np.asarray(z, float))
            if len(self.U) >= self.n_train:
                self._fit(np.array(self.U), np.array(self.Z))


class SlidingGPRTwin(StaticMLTwin):
    """Adaptive purely data-driven twin: GPR re-trained on a moving window."""

    def __init__(self, window=96, refit_every=12, seed=0):
        super().__init__("gpr", window, seed)
        self.name = "GPR (sliding window)"
        self.window, self.refit_every, self.k = window, refit_every, 0

    def update(self, u, z):
        self.U.append(np.asarray(u, float)); self.Z.append(np.asarray(z, float)); self.k += 1
        if len(self.U) < self.window:
            return
        U = np.array(self.U[-self.window:]); Z = np.array(self.Z[-self.window:])
        X = _xfeat(U)
        if self.models is None or self.k % self.refit_every == 0:
            self._fit(U, Z)
        else:  # cheap update: keep hyper-parameters, refit on new window
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                for j, m in enumerate(self.models):
                    gp = m[-1]
                    gp.set_params(kernel=gp.kernel_, optimizer=None)
                    m.fit(X, Z[:, j])


class PCHDT:
    """Proposed Physics-Constrained Hybrid Digital Twin (see module docstring)."""

    def __init__(self, n_ens=64, seed=0, residual=True, adaptive=True, deact_drift=True,
                 dt_h=0.5, lam=0.995, name=None):
        self.rng = np.random.default_rng(1000 + seed)
        self.N, self.residual, self.adaptive, self.deact_drift = n_ens, residual, adaptive, deact_drift
        self.dt_h, self.lam = dt_h, lam
        self.name = name or "PC-HDT (proposed)"
        self.theta = tm.THETA0 + self.rng.standard_normal((n_ens, 3)) * np.array([0.05, 0.05, 0.05])
        self.q_rw = np.array([0.01, 0.004, 0.003])           # random-walk process noise
        self.R_eff = SIG_OBS ** 2 + np.array([0.03, 0.01, 2.0]) ** 2   # sensor + representation
        self.W = np.zeros((tm.N_FEAT, tm.N_OUT))
        self.Prls = np.eye(tm.N_FEAT) * 1.0
        self.s_add = np.zeros(3)                              # adaptive extra variance
        self.lo = np.array([np.log(0.05), -1.0, 0.0]); self.hi = np.array([0.3, 1.0, 2.5])
        self.nis_thr = chi2.ppf(0.99, 3)
        self.n_inflations = 0

    # ---------------------------------------------------------------- helpers
    def _phys(self, u, theta):
        ly, lP, T = tm.predict(_uvec(u), theta)
        return np.column_stack([ly[:, 0], lP[:, 0], T[:, 0]])     # (N, 3)

    def _res(self, u):
        return (tm.features(_uvec(u)) @ self.W)[0] if self.residual else np.zeros(3)

    # ---------------------------------------------------------------- interface
    def forecast(self, u):
        Y = self._phys(u, self.theta) + self._res(u)
        var = Y.var(axis=0, ddof=1) + self.R_eff + self.s_add
        return Y.mean(axis=0), np.sqrt(var)

    def update(self, u, z):
        z = np.asarray(z, float)
        res = self._res(u)
        Y = self._phys(u, self.theta) + res
        Rv = self.R_eff + self.s_add
        d = z - Y.mean(axis=0)
        Cyy = np.cov(Y.T)
        S = Cyy + np.diag(Rv)
        nis = float(d @ np.linalg.solve(S, d))
        if self.adaptive and nis > self.nis_thr:          # abrupt event -> inflate
            infl = np.sqrt(min(nis / 3.0, 16.0))
            m = self.theta.mean(axis=0)
            self.theta = m + infl * (self.theta - m)
            self.theta = np.clip(self.theta, self.lo, self.hi)
            Y = self._phys(u, self.theta) + res
            Cyy = np.cov(Y.T)
            self.n_inflations += 1
        # stochastic EnKF analysis
        Th, Ya = self.theta - self.theta.mean(0), Y - Y.mean(0)
        Cty = Th.T @ Ya / (self.N - 1)
        K = Cty @ np.linalg.inv(Cyy + np.diag(Rv))
        Zp = z + self.rng.standard_normal((self.N, 3)) * np.sqrt(Rv)
        self.theta = np.clip(self.theta + (Zp - Y) @ K.T, self.lo, self.hi)
        # innovation-based predictive variance adaptation (Mehra-type)
        excess = np.maximum(d ** 2 - np.diag(Cyy) - self.R_eff, 0.0)
        self.s_add = 0.97 * self.s_add + 0.03 * excess
        # slow time-scale: bias-free residual learner (RLS with forgetting)
        if self.residual:
            e = z - self._phys(u, self.theta.mean(0, keepdims=True))[0]
            phi = tm.features(_uvec(u))[0]
            Pphi = self.Prls @ phi
            g = Pphi / (self.lam + phi @ Pphi)
            self.W += np.outer(g, e - phi @ self.W)
            self.Prls = (self.Prls - np.outer(g, Pphi)) / self.lam
        # time update to next step: physics-informed drift + random walk
        if self.deact_drift:
            out = tm.predict(_uvec(u), self.theta, return_all=True)
            a = np.exp(self.theta[:, 0])
            da = tm.deact_rate(out["T"][:, 0], a) * self.dt_h
            self.theta[:, 0] = np.log(np.maximum(a - da, 0.05))
        self.theta += self.rng.standard_normal((self.N, 3)) * self.q_rw
        self.theta = np.clip(self.theta, self.lo, self.hi)

    def activity(self):
        return float(np.exp(self.theta[:, 0]).mean())

    def ensemble(self):
        # model-error sigma (sensor noise excluded: constraints act on TRUE states)
        return self.theta.copy(), (self.W.copy() if self.residual else np.zeros_like(self.W)), \
            np.sqrt(self.R_eff - SIG_OBS ** 2 + self.s_add)
