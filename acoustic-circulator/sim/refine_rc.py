"""Local refinement of the design point at exactly 1 GHz with the physical RC-gate switch model (K=24)."""
import os, sys, json
import numpy as np
from dataclasses import replace
from scipy.optimize import minimize
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim.load_design import load_design
from sim.circulator import sparams, SwitchCap
from sim.topologies import figures_of_merit
from sim.ltp import db
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); RES = os.path.join(ROOT, 'results'); F0 = 1.0e9
des, p = load_design()
def cost(z):
    Csh, Csw, W, Cpar, fs = z
    d = replace(des, Cp=Csh, sw=replace(des.sw, Csw=Csw, W=W, Cpar=Cpar), res=replace(des.res, fs=fs))
    try:
        S = sparams(d, np.array([F0 - 0.5e6, F0, F0 + 0.5e6]), 24)[:, 24]
    except np.linalg.LinAlgError:
        return 50.0
    IL, ISO, RL, _ = figures_of_merit(S)
    return (IL + 0.5 * np.maximum(0, 30 - ISO) + 0.3 * np.maximum(0, 15 - RL)).mean()
z0 = [des.Cp, des.sw.Csw, des.sw.W, des.sw.Cpar, des.res.fs]
print('start cost', cost(z0), flush=True)
r = minimize(cost, z0, method='Nelder-Mead', bounds=[(0.3e-12, 15e-12), (0.3e-12, 10e-12), (100, 3000), (0, 3e-12), (0.85e9, 1.0e9)],
             options=dict(xatol=1e-15, fatol=1e-4, maxiter=250, initial_simplex=np.array([z0] + [[z0[0] * (1.15 if i == 0 else 1), z0[1] * (1.15 if i == 1 else 1), z0[2] * (1.3 if i == 2 else 1), z0[3] + (0.2e-12 if i == 3 else 0), z0[4] * (1.003 if i == 4 else 1)] for i in range(5)])))
Csh, Csw, W, Cpar, fs = r.x
d = replace(des, Cp=Csh, sw=replace(des.sw, Csw=Csw, W=W, Cpar=Cpar), res=replace(des.res, fs=fs))
S = sparams(d, np.array([F0]), 40)[0, 40]
IL, ISO, RL, sense = figures_of_merit(S[None])
d = replace(d, direction=d.direction * sense) if sense < 0 else d
S = sparams(d, np.array([F0]), 40)[0, 40]; IL, ISO, RL, _ = figures_of_merit(S[None])
p.update(dict(Cp=float(Csh), Csw=float(Csw), W_um=float(W), Cpar=float(Cpar), fs=float(fs), direction=int(d.direction),
              Ron_ohm=float(d.sw.Ron), Coff=float(d.sw.Coff), Qsw_1GHz=float(d.sw.Qon), IL_dB=float(IL[0]), ISO_dB=float(ISO[0]), RL_dB=float(RL[0]), cost=float(r.fun),
              model='rc-gate switched conductance, K=40'))
json.dump(p, open(os.path.join(RES, 'design_final.json'), 'w'), indent=1)
print(json.dumps({k: p[k] for k in ('Cp', 'Csw', 'W_um', 'Cpar', 'fs', 'fm', 'direction', 'IL_dB', 'ISO_dB', 'RL_dB', 'cost')}, indent=1))
