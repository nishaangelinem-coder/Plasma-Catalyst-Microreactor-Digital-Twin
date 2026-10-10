"""Device DSP, the proposed joint estimator and the baselines.

Proposed (PA+echo joint EKF): state x = [sO2_v, ln f_v, T_b, sO2_s, ln HbT_s, T_s, ln g]
(f_v: effective blood fill of the sinus gate)
measurements z = [ln A_s(lam_k), ln A_b(lam_k) (k = 1..K), dtau_s, dtau_b, ln A_ref, T_skin]
 - depth-gated multi-wavelength photoacoustic amplitudes (scalp gate, brain gate),
 - differential pulse-echo shifts of the superficial and deep segments,
 - the on-probe reference absorber (observes the coupling gain g),
 - the probe thermistor (anchors the scalp temperature).
The measurement model is the nominal (population) forward model with a first-order
fluence perturbation; Jacobians are numerical. Innovation gating (chi-square, 99 %)
inflates the covariance of outlying channels (motion, coupling loss).
"""
from __future__ import annotations
import numpy as np
from . import tissue, acoustic as ac
from .forward import ForwardModel, HeadParams, CI

C_ASSUMED = 1545.0
T_PAD = 2 * 0.1 / 150000.0     # two-way time through a 1-mm stand-off pad (s)


class DeviceDSP:
    """Turns raw A-lines into gate amplitudes and echo shifts."""

    def __init__(self, dev: ac.DeviceConfig, t_sup0, t_deep0, gates=None, peak_lock=True):
        self.dev = dev
        self.gates = gates or dict(scalp=dev.scalp_gate, brain=dev.brain_gate)
        self.win_pad = (T_PAD - 0.3e-6, T_PAD + 0.4e-6)
        self.win_sup = (T_PAD + t_sup0 - 0.4e-6, T_PAD + t_sup0 + 0.4e-6)
        self.win_deep = (T_PAD + t_deep0 - 0.8e-6, T_PAD + t_deep0 + 0.8e-6)
        self.echo_ref = None
        self.peak_lock = peak_lock

    def amplitudes(self, traces):
        """Gate envelopes. The sinus ('brain') gate is locked to the leading-edge peak of
        the summed envelope found within +-0.7 mm of the echo-located depth."""
        gates = dict(self.gates)
        if self.peak_lock:
            gates["brain"] = peak_locked_gate(sum(ac.envelope(p) for p in traces.values()), self.gates["brain"])
        A = {}
        for lam, p in traces.items():
            A[lam] = {gname: ac.gate_amplitude(p, g, C_ASSUMED) for gname, g in gates.items()}
        return A

    def noise_floor(self, traces):
        """rms envelope in a deep window (3.0-3.6 cm, no signal) -> amplitude noise std estimate."""
        sel = (ac.T_AX > 3.0 / (C_ASSUMED * 100)) & (ac.T_AX < 3.6 / (C_ASSUMED * 100))
        return float(np.mean([ac.envelope(p)[sel].std() for p in traces.values()]))

    def echo_shifts(self, echo):
        if self.echo_ref is None:
            self.echo_ref = echo.copy()
            return 0.0, 0.0
        d_pad = ac.echo_shift(echo, self.echo_ref, self.win_pad)
        d_sup = ac.echo_shift(echo, self.echo_ref, self.win_sup)
        d_deep = ac.echo_shift(echo, self.echo_ref, self.win_deep)
        return d_sup - d_pad, d_deep - d_sup          # superficial segment, deep segment


def peak_locked_gate(env, gate, search=0.07, pre=0.05, post=0.10):
    """Centre a (pre+post)-wide gate on the envelope peak found within +-search cm (0.7 mm,
    about twice the echo-localisation error) of the
    nominal gate (depth coordinates with the assumed sound speed)."""
    z = (ac.T_AX - ac.T_STANDOFF) * C_ASSUMED * 100.0
    sel = (z >= gate[0] - search) & (z <= gate[1] + search)
    idx = np.where(sel)[0]
    zp = z[idx[np.argmax(env[idx])]]
    return (zp - pre, zp + post)


# ------------------------------------------------------------------ fast linear acoustics
class FastAcoustics:
    """Precomputed linear map p0(z) -> gate amplitudes (temperature-independent delays)."""

    def __init__(self, fm: ForwardModel, gates, peak_lock=True):
        self.peak_lock = peak_lock
        z, th = fm.z, fm.thick
        c = fm.c_layers(37.0, 37.0)
        seg = ac._layer_lengths(z, th)
        t_arr = (seg / (c[None, :] * 100.0)).sum(1) + ac.T_STANDOFF
        fMHz = ac.F_AX / 1e6
        att_db = (seg[:, :, None] * fm.head.alpha0[None, :, None] * fMHz[None, None, :] ** fm.head.y[None, :, None]).sum(1)
        amp = 10 ** (-att_db / 20.0)
        dz = z[1] - z[0]
        lay = np.argmax(z[:, None] < np.cumsum(th)[None, :], axis=1)
        c_z = c[lay] * 100.0
        M = ((dz / (2.0 * c_z))[:, None] * amp * np.exp(-2j * np.pi * ac.F_AX[None, :] * t_arr[:, None])) * fm.H[None, :]
        self.nf = M.shape[1]
        self.M = np.ascontiguousarray(np.hstack([M.real, M.imag]))     # real matmul is much faster
        self.gates = gates
        self.sel = {g: (ac.T_AX >= v[0] / (C_ASSUMED * 100) + ac.T_STANDOFF) & (ac.T_AX < v[1] / (C_ASSUMED * 100) + ac.T_STANDOFF)
                    for g, v in gates.items()}
        h = np.zeros(ac.NT); h[0] = 1; h[1:ac.NT // 2] = 2; h[ac.NT // 2] = 1
        self.h = h

    def gate_amps(self, p0):
        PM = p0 @ self.M
        P = PM[:self.nf] + 1j * PM[self.nf:]
        p = np.fft.irfft(P, n=ac.NT) * ac.FS
        env = np.abs(np.fft.ifft(np.fft.fft(p) * self.h))
        out = {g: env[s].mean() for g, s in self.sel.items()}
        if self.peak_lock and "brain" in self.gates:
            g1, g2 = peak_locked_gate(env, self.gates["brain"])
            sel = (ac.T_AX >= g1 / (C_ASSUMED * 100) + ac.T_STANDOFF) & (ac.T_AX < g2 / (C_ASSUMED * 100) + ac.T_STANDOFF)
            out["brain"] = env[sel].mean()
        return out


# ------------------------------------------------------------------ proposed EKF
class JointEKF:
    def __init__(self, fl, dev: ac.DeviceConfig, gates, T_b0, T_s0, use_echo=True, use_ref=True,
                 fluence_correction=True, nominal_head: HeadParams | None = None, sigma_amp=None,
                 model_floor=0.02, scalp_free=True, peak_lock=True):
        self.head = nominal_head or HeadParams()
        self.fm = ForwardModel(fl, self.head, dev, second_order=False)
        self.fa = FastAcoustics(self.fm, gates, peak_lock=peak_lock)
        self.dev, self.lams = dev, dev.source.wavelengths
        self.use_echo, self.use_ref, self.fc = use_echo, use_ref, fluence_correction
        self.T_b0, self.T_s0 = T_b0, T_s0
        self.x = np.array([0.65, np.log(0.5), T_b0, 0.70, np.log(40.0), T_s0, 0.0])
        self.P = np.diag([0.08, 0.3, 0.5, 0.08, 0.3, 0.5, 0.2]) ** 2
        dt = dev.frame_s
        self.Q = np.diag([0.015, 0.006, 0.012, 0.006, 0.004, 0.02, 0.006]) ** 2 * (dt / 10.0)
        self.coef_unc = 0.25        # relative uncertainty of k_Gamma and dc/dT (enters R)
        self.model_floor = model_floor
        if not scalp_free:        # scalp optical states held at the population prior
            self.P[3, 3] = 0.02 ** 2; self.P[4, 4] = 0.05 ** 2; self.Q[3, 3] = 1e-8; self.Q[4, 4] = 1e-8
        self.sigma_amp = sigma_amp
        self.frozen_fluence = None
        # dtau/dT of the two segments (nominal), linearised sensitivities
        self.t0 = self.fm.echo_times(T_b0, T_s0)
        self.nis_hist = []

    # measurement model
    def h(self, x, T_probe):
        so2_v, lfv, T_b, so2_s, lhs, T_s, lg = x
        fill, hbt_s, g = np.exp(lfv), np.exp(lhs), np.exp(lg)
        out = []
        for lam in self.lams:
            dm, nom = self.fm.dmua(lam, so2_v, so2_s, hbt_s)
            if self.fc:
                phi = self.fm.fluence(lam, dm, so2_v)
            else:
                if self.frozen_fluence is None:
                    self.frozen_fluence = {}
                if lam not in self.frozen_fluence:
                    dm0, _ = self.fm.dmua(lam, 0.65, 0.70, 40.0)
                    self.frozen_fluence[lam] = self.fm.fluence(lam, dm0, 0.65)
                phi = self.frozen_fluence[lam]
            mua = self.fm.mua_z(nom, dm)
            T = self.fm.T_z(T_b, T_s)
            gam = self.head.gamma37 * (1.0 + self.head.kg[self.fm.lay_c] * (T - 37.0))
            p0 = g * gam * (mua * 100.0) * (phi * self.dev.source.fluence_mJcm2 * 10.0)
            p0 = np.where(self.fm.is_sinus, fill * p0, p0)
            A = self.fa.gate_amps(p0)
            out += [np.log(max(A["scalp"], 1e-12)), np.log(max(A["brain"], 1e-12))]
        if self.use_echo:
            ts, td = self.fm.echo_times(T_b, T_s)
            out += [ts - self.t0[0], (td - ts) - (self.t0[1] - self.t0[0])]
        if self.use_ref:
            out += [lg + np.log(1 - 0.001 * (T_probe - 37.0))]
        out += [T_s]
        return np.array(out)

    def step(self, meas, T_probe):
        """meas: dict with A (gate amplitudes per lam), dtau (sup, deep), a_ref, sigma_amp."""
        z = []
        R = []
        for lam in self.lams:
            for gname in ("scalp", "brain"):
                a = meas["A"][lam][gname]
                z.append(np.log(max(a, 1e-12)))
                R.append((meas["sigma_amp"] / max(a, 1e-12)) ** 2 + self.model_floor ** 2)   # noise + model floor
        if self.use_echo:
            z += list(meas["dtau"]); R += [(3e-9) ** 2, (4e-9) ** 2]
        if self.use_ref:
            z.append(np.log(max(meas["a_ref"], 1e-12))); R.append(0.01 ** 2)
        z.append(T_probe - 0.65); R.append(0.35 ** 2)
        z, R = np.array(z), np.diag(R)
        # predict
        P = self.P + self.Q
        x = self.x.copy()
        # jacobian (forward differences)
        h0 = self.h(x, T_probe)
        eps = np.array([0.01, 0.02, 0.1, 0.01, 0.02, 0.1, 0.02])
        Hj = np.zeros((len(h0), len(x)))
        for i in range(len(x)):
            xp = x.copy(); xp[i] += eps[i]
            Hj[:, i] = (self.h(xp, T_probe) - h0) / eps[i]
        # coefficient uncertainty (k_Gamma, dc/dT) -> state-dependent measurement variance
        K = len(self.lams); idx = np.arange(len(h0))
        R = R.copy()
        kg = self.head.kg[CI["sinus"]]
        for i in range(K):
            R[2 * i + 1, 2 * i + 1] += (self.coef_unc * kg * (x[2] - self.T_b0)) ** 2
        if self.use_echo:
            for j in (2 * K, 2 * K + 1):
                R[j, j] += (self.coef_unc * h0[j]) ** 2
        v = z - h0
        S = Hj @ P @ Hj.T + R
        # (a) per-channel gating of the motion-prone echo channels only
        if self.use_echo:
            for j in (2 * K, 2 * K + 1):
                nis_j = v[j] ** 2 / S[j, j]
                if nis_j > 6.63:
                    R[j, j] *= min(nis_j, 100.0)
            S = Hj @ P @ Hj.T + R
        # (b) global innovation test -> inflate the state covariance so the state can jump
        nis = float(v @ np.linalg.solve(S, v))
        m = len(z)
        thr = m + 2.33 * np.sqrt(2 * m)          # ~ chi2_m 99 % quantile
        if nis > thr:
            P = P * min(nis / m, 25.0)
            S = Hj @ P @ Hj.T + R
        Kg = P @ Hj.T @ np.linalg.solve(S, np.eye(len(z)))
        self.x = x + Kg @ v
        self.x[0] = np.clip(self.x[0], 0.2, 0.99); self.x[3] = np.clip(self.x[3], 0.2, 0.99)
        I = np.eye(len(x))
        self.P = (I - Kg @ Hj) @ P @ (I - Kg @ Hj).T + Kg @ R @ Kg.T
        self.nis_hist.append(float(v @ np.linalg.solve(S, v)))
        return self.x.copy(), np.sqrt(np.diag(self.P))


# ------------------------------------------------------------------ baselines: oxygenation
def _eps_matrix(lams):
    return np.array([tissue.extinction(l) for l in lams])      # [K, 2] (HbO2, Hb)


def linear_unmixing(A_brain, lams, phi_corr=None):
    """Classical linear spectral unmixing (optionally fluence-compensated). Returns sO2."""
    a = np.array([A_brain[l] for l in lams])
    if phi_corr is not None:
        a = a / np.array([phi_corr[l] for l in lams])
    E = _eps_matrix(lams)
    c, *_ = np.linalg.lstsq(E, a, rcond=None)
    c = np.maximum(c, 0.0)
    return float(c[0] / max(c.sum(), 1e-12))


class FluenceCompensatedUnmixing:
    """Iterative model-based fluence compensation with the nominal head (no scalp
    estimation, no temporal filtering, no echo channel)."""

    def __init__(self, fl, dev, gates, n_iter=4, nominal_head=None):
        self.fm = ForwardModel(fl, nominal_head or HeadParams(), dev, second_order=False)
        self.fa = FastAcoustics(self.fm, gates); self.lams = dev.source.wavelengths; self.n_iter = n_iter

    def estimate(self, A_brain):
        so2 = 0.65
        for _ in range(self.n_iter):
            corr = {}
            for lam in self.lams:
                dm, nom = self.fm.dmua(lam, so2)
                phi = self.fm.fluence(lam, dm, so2)
                # gate transfer per unit absorption: unit absorber in the sinus layer
                p0 = phi * 10.0 * self.fm.is_sinus
                corr[lam] = self.fa.gate_amps(p0)["brain"]
            so2 = linear_unmixing(A_brain, self.lams, corr)
        return so2


class NirsSRS:
    """Spatially resolved spectroscopy (NIRO-type tissue oxygenation index): the slope of
    ln(rho^2 R) versus rho gives mu_eff(lam); with mus'(lam) ~ (1 - h lam) assumed, the
    ratio of mu_eff^2 between two wavelengths gives the haemoglobin saturation without
    knowing the absolute scattering or the coupling."""

    def __init__(self, lams=(760, 850), rho=(2.0, 2.5, 3.0), rho_all=(1.5, 2.0, 2.5, 3.0), h=6.3e-4):
        self.lams, self.rho = lams, np.array(rho)
        self.idx = [rho_all.index(r) for r in rho]
        self.h = h

    def estimate(self, nirs):
        k = []
        for lam in self.lams:
            R = np.array(nirs[lam])[self.idx]
            slope = np.polyfit(self.rho, np.log(self.rho ** 2 * R), 1)[0]
            k.append(slope ** 2 / (1.0 - self.h * lam))          # proportional to mua(lam)
        (eo1, ed1), (eo2, ed2) = tissue.extinction(self.lams[0]), tissue.extinction(self.lams[1])
        r = k[0] / max(k[1], 1e-12)
        S = (r * ed2 - ed1) / ((eo1 - ed1) - r * (eo2 - ed2))
        return float(np.clip(S, 0.0, 1.0))


# ------------------------------------------------------------------ baselines: temperature
class AmplitudeThermometry:
    """Classical PA thermometry: dT = (A/A0 - 1)/kG at the isosbestic 800 nm, brain gate."""

    def __init__(self, kg=ac.KG_DEFAULT["brain"], T0=37.0, lam=800):
        self.kg, self.T0, self.lam, self.A0 = kg, T0, lam, None

    def estimate(self, A_brain):
        a = A_brain[self.lam]
        if self.A0 is None:
            self.A0 = a
        return self.T0 + (a / self.A0 - 1.0) / self.kg


class EchoShiftThermometry:
    """Deep-segment differential echo shift with nominal dtau/dT."""

    def __init__(self, fm_nom: ForwardModel, T0):
        t0 = fm_nom.echo_times(T0, T0); t1 = fm_nom.echo_times(T0 + 1.0, T0)
        self.sens = (t1[1] - t1[0]) - (t0[1] - t0[0])        # s per C of the deep segment
        self.T0 = T0

    def estimate(self, dtau_deep):
        return self.T0 + dtau_deep / self.sens
