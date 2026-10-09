"""Global search over (coupling, modulation, pump frequency) for each topology/element with adaptive operating frequency."""
import os, sys, json, time
import numpy as np
from dataclasses import replace
from scipy.optimize import differential_evolution, minimize
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim.topologies import Candidate, SwitchCap, best_operating_point, sweep, figures_of_merit, point_cost
from sim.circulator import Resonator, Varactor
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F0 = 1.0e9


def make(topo, element, x, Qm=500.0):
    if element == 'varactor':
        Cp, Cc, Vm, fm, mult = x
        return Candidate(topo=topo, element=element, res=Resonator(fs=0.96e9, Qm=Qm), var=Varactor(mult=mult), Cp=Cp, Cc=Cc, Vm=Vm, fm=fm, Vdc=0.25)
    else:
        Cp, Cc, Csw, fm, W = x
        return Candidate(topo=topo, element=element, res=Resonator(fs=0.96e9, Qm=Qm), var=Varactor(), sw=SwitchCap(Csw=Csw, W=W), Cp=Cp, Cc=Cc, fm=fm)


def cost(x, topo, element, Qm=500.0):
    c = make(topo, element, x, Qm)
    try:
        fb, IL, ISO, RL, cst = best_operating_point(c, coarse=1.0e6, fine=0.2e6, K=3)
    except np.linalg.LinAlgError:
        return 50.0
    return cst


def bounds_for(topo, element):
    if element == 'varactor':
        b = [(0.1e-12, 6e-12), (0.02e-12, 3e-12), (0.15, 0.6), (3e6, 80e6), (0.3, 3.0)]
    else:
        b = [(0.1e-12, 6e-12), (0.02e-12, 3e-12), (0.1e-12, 3e-12), (3e6, 80e6), (50, 1000)]
    if topo != 'A':
        b[0] = (0.0, 4e-12)           # shunt matching cap at ports
        b[1] = (0.05e-12, 0.06e-12)   # Cc unused
    return b


if __name__ == '__main__':
    topo, element = sys.argv[1], sys.argv[2]
    Qm = float(sys.argv[3]) if len(sys.argv) > 3 else 500.0
    t = time.time()
    b = bounds_for(topo, element)
    r = differential_evolution(cost, b, args=(topo, element, Qm), seed=7, maxiter=35, popsize=12, tol=1e-9, polish=False, workers=4, updating='deferred')
    r2 = minimize(cost, r.x, args=(topo, element, Qm), method='Nelder-Mead', bounds=b, options=dict(xatol=1e-14, fatol=1e-4, maxiter=400))
    c = make(topo, element, r2.x, Qm)
    fb, IL, ISO, RL, cst = best_operating_point(c, coarse=0.5e6, fine=0.05e6, K=6)
    out = dict(topo=topo, element=element, Qm=Qm, x=list(map(float, r2.x)), f_op=float(fb), IL=float(IL), ISO=float(ISO), RL=float(RL), cost=float(cst), time_s=time.time() - t)
    print(json.dumps(out, indent=1))
    json.dump(out, open(os.path.join(ROOT, 'results', f'search_{topo}_{element}_Q{int(Qm)}.json'), 'w'), indent=1)
