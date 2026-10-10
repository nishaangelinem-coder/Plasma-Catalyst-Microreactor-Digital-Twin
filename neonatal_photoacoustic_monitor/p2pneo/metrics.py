import numpy as np
from scipy import stats


def rmse(a, b): return float(np.sqrt(np.mean((np.asarray(a) - np.asarray(b)) ** 2)))
def bias(a, b): return float(np.mean(np.asarray(a) - np.asarray(b)))
def mae(a, b): return float(np.mean(np.abs(np.asarray(a) - np.asarray(b))))
def maxerr(a, b): return float(np.max(np.abs(np.asarray(a) - np.asarray(b))))


def loa(a, b):
    d = np.asarray(a) - np.asarray(b)
    return float(d.mean() - 1.96 * d.std()), float(d.mean() + 1.96 * d.std())


def coverage(est, sd, truth, k=1.96):
    return float(np.mean(np.abs(np.asarray(est) - np.asarray(truth)) <= k * np.asarray(sd)))


def event_detection(t, est, events, dt, thresh=0.06, win_s=300.0, max_latency_s=120.0):
    """Alarm when the estimate drops more than `thresh` below its running median over
    the previous `win_s`. Returns sensitivity, false alarms per hour, median latency (s)."""
    est = np.asarray(est); n = len(est); w = max(1, int(win_s / dt))
    alarm = np.zeros(n, bool)
    for i in range(w, n):
        base = np.median(est[i - w:i])
        alarm[i] = est[i] < base - thresh
    detected, latencies = 0, []
    for (t0, t1, depth) in events:
        i0, i1 = int(t0 / dt), int(min(t1 + max_latency_s, t[-1]) / dt)
        idx = np.where(alarm[i0:i1])[0]
        if len(idx):
            detected += 1; latencies.append(idx[0] * dt)
    # false alarms: alarm onsets outside event windows (+ latency tolerance)
    in_ev = np.zeros(n, bool)
    for (t0, t1, depth) in events:
        in_ev[int(t0 / dt):int(min(t1 + max_latency_s, t[-1]) / dt)] = True
    onsets = np.where(alarm[1:] & ~alarm[:-1])[0] + 1
    fa = int(np.sum(~in_ev[onsets]))
    hours = t[-1] / 3600.0
    return dict(sensitivity=detected / max(len(events), 1), false_alarms_per_h=fa / max(hours, 1e-9),
                median_latency_s=float(np.median(latencies)) if latencies else np.nan)


def wilcoxon(a, b):
    a, b = np.asarray(a), np.asarray(b)
    if np.allclose(a, b):
        return 1.0
    try:
        return float(stats.wilcoxon(a, b).pvalue)
    except ValueError:
        return np.nan
