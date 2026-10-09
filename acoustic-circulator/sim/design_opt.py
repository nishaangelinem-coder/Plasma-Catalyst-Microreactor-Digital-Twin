"""Design-space optimisation of the STM acoustic circulator with the LTP solver."""
import sys, json, time
import numpy as np
from scipy.optimize import differential_evolution, minimize
sys.path.insert(0, '.')
from sim.circulator import Design, Resonator, Varactor, sparams
from sim.ltp import db

F0 = 1.0e9


def make(x, waveform='square'):
    Cp, Cc, Vm, fm, fs, Vdc, mult = x
    return Design(Resonator(fs=fs), Varactor(mult=mult), Cp=Cp, Cc=Cc, Vm=Vm, fm=fm, Vdc=Vdc, waveform=waveform)


def evaluate(des, f0=F0, half_bw=0.5e6, npts=3, K=4):
    f = np.linspace(f0 - half_bw, f0 + half_bw, npts)
    S = sparams(des, f, K)[:, K]
    fwd1 = np.array([S[:, 1, 0], S[:, 2, 1], S[:, 0, 2]])   # 1->2->3->1
    fwd2 = np.array([S[:, 0, 1], S[:, 1, 2], S[:, 2, 0]])   # 1->3->2->1
    il1 = -db(fwd1).max(axis=0).mean(); il2 = -db(fwd2).max(axis=0).mean()
    if il1 <= il2:
        IL, ISO = -db(fwd1).max(axis=0), -db(fwd2).min(axis=0)
    else:
        IL, ISO = -db(fwd2).max(axis=0), -db(fwd1).min(axis=0)
    RL = -db(np.array([S[:, 0, 0], S[:, 1, 1], S[:, 2, 2]])).min(axis=0)
    return IL, ISO, RL


def cost(x, waveform='square'):
    des = make(x, waveform)
    IL, ISO, RL = evaluate(des)
    return IL.mean() + 0.3 * np.maximum(0, 30 - ISO).mean() + 0.2 * np.maximum(0, 15 - RL).mean()


if __name__ == '__main__':
    waveform = sys.argv[1] if len(sys.argv) > 1 else 'square'
    bounds = [(0.2e-12, 6.0e-12), (0.05e-12, 4.0e-12), (0.10, 0.60), (5e6, 80e6), (0.85e9, 1.0e9), (0.0, 0.5), (0.3, 3.0)]
    t = time.time()
    res = differential_evolution(cost, bounds, args=(waveform,), seed=1, maxiter=120, popsize=24, tol=1e-6,
                                 polish=False, workers=4, updating='deferred')
    x = res.x
    res2 = minimize(cost, x, args=(waveform,), method='Nelder-Mead', bounds=bounds, options=dict(xatol=1e-15, fatol=1e-4, maxiter=800))
    x = res2.x
    IL, ISO, RL = evaluate(make(x, waveform), npts=3, K=6)
    out = dict(waveform=waveform, Cp=x[0], Cc=x[1], Vm=x[2], fm=x[3], fs=x[4], Vdc=x[5], mult=x[6], cost=float(res2.fun),
               IL_mean=float(IL.mean()), ISO_min=float(ISO.min()), RL_min=float(RL.min()), time_s=time.time() - t)
    print(json.dumps(out, indent=1))
    json.dump(out, open(f'results/design_opt_{waveform}.json', 'w'), indent=1)
