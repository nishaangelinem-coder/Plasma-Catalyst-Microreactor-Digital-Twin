"""Pick the best series-mode wye / switched-MIM design (results/polishC_switch_Q500.json), re-weight the return-loss
target, re-centre the operating frequency at exactly 1.000 GHz by adjusting fs, snap fm to a 5-MHz grid (commensurate
transient analysis) and write results/design_final.json."""
import os, sys, json
import numpy as np
from dataclasses import replace
from scipy.optimize import minimize
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim.circulator import Design, Resonator, Varactor, SwitchCap, sparams
from sim.topologies import figures_of_merit
from sim.ltp import db
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, 'results')
F0 = 1.0e9
QM = 500.0


def design_from(y, fs, fm=None):
    Csh, Csw, W, Cpar, fm0 = y
    return Design(Resonator(fs=fs, Qm=QM), Varactor(), Cp=Csh, Cc=0.0, fm=fm if fm else fm0, topo='C', element='switch',
                  sw=SwitchCap(Csw=Csw, W=W, Cpar=Cpar), waveform='trap', trise=0.10)


def fom_at(des, f, K=16):
    S = sparams(des, f, K)[:, K]
    return figures_of_merit(S)


def cost_window(des, f0=F0, half=0.5e6, K=16):
    f = np.array([f0 - half, f0, f0 + half])
    IL, ISO, RL, _ = fom_at(des, f, K)
    return (IL + 0.5 * np.maximum(0, 30 - ISO) + 0.25 * np.maximum(0, 15 - RL)).mean()


def recentre(des, f_target=F0):
    """Adjust fs so that the best operating point sits at f_target."""
    for _ in range(5):
        f = np.linspace(f_target - 30e6, f_target + 30e6, 301)
        IL, ISO, RL, _ = fom_at(des, f)
        c = IL + 0.5 * np.maximum(0, 30 - ISO) + 0.25 * np.maximum(0, 15 - RL)
        fb = f[int(np.argmin(c))]
        des = replace(des, res=replace(des.res, fs=des.res.fs * f_target / fb))
    return des


def main():
    s = json.load(open(os.path.join(RES, 'polishC_switch_Q500.json')))
    y = s['y']
    des = design_from(y, 0.90e9)
    des = recentre(des)
    fm = 5e6 * round(des.fm / 5e6)
    des = replace(des, fm=fm)
    des = recentre(des)
    # local refinement at exactly F0 with fm fixed on the grid: variables Csh, Csw, W, Cpar, fs
    def cost(z):
        Csh, Csw, W, Cpar, fs = z
        d = replace(des, Cp=Csh, sw=SwitchCap(Csw=Csw, W=W, Cpar=Cpar), res=replace(des.res, fs=fs))
        try:
            return cost_window(d)
        except np.linalg.LinAlgError:
            return 50.0
    z0 = [des.Cp, des.sw.Csw, des.sw.W, des.sw.Cpar, des.res.fs]
    bnd = [(0.3e-12, 15e-12), (0.3e-12, 8e-12), (100, 3000), (0.0, 3e-12), (0.85e9, 1.0e9)]
    r = minimize(cost, z0, method='Nelder-Mead', bounds=bnd, options=dict(xatol=1e-15, fatol=1e-4, maxiter=400))
    Csh, Csw, W, Cpar, fs = r.x
    des = replace(des, Cp=Csh, sw=SwitchCap(Csw=Csw, W=W, Cpar=Cpar), res=replace(des.res, fs=fs))
    IL, ISO, RL, sense = fom_at(des, np.array([F0]), K=24)
    des = replace(des, direction=sense)      # make 1->2->3->1 the forward sense with phase order 0/120/240
    IL, ISO, RL, sense2 = fom_at(des, np.array([F0]), K=24)
    out = dict(topo='C', element='switch', f0=F0, Cp=float(des.Cp), Cc=0.0, fm=float(des.fm), fs=float(des.res.fs), Qm=QM,
               Csw=float(des.sw.Csw), W_um=float(des.sw.W), Cpar=float(des.sw.Cpar), Ron_ohm=float(des.sw.Ron), Coff=float(des.sw.Coff), Gsh_S=float(des.sw.Gsh), Csh_par=float(des.sw.Csh), Rg=float(des.sw.Rg), Rb=float(des.sw.Rb),
               Qsw_1GHz=float(des.sw.Qon), direction=int(des.direction), Vm=0.6, Vdc=0.0, mult=1.0,
               IL_dB=float(IL[0]), ISO_dB=float(ISO[0]), RL_dB=float(RL[0]), cost=float(r.fun), from_polish=s)
    json.dump(out, open(os.path.join(RES, 'design_final.json'), 'w'), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != 'from_polish'}, indent=1))


if __name__ == '__main__':
    main()
