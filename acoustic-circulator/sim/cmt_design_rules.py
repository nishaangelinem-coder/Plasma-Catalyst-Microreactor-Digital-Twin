"""Normalised CMT design rules: optimise (kappa, dw, wm, f_op)/gamma_e for max isolation & min IL; sweep gi/ge."""
import sys, os, json, numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim.cmt import cmt_sparams
from sim.ltp import db
from scipy.optimize import differential_evolution
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
w0 = 2 * np.pi * 1e9; ge = 2 * np.pi * 10e6

def ev(x, gi_rel=0.0, mod='sine', K=8, dfs=(-0.1, 0, 0.1)):
    kap, dw, wm, fo = x[0] * ge, x[1] * ge, x[2] * ge, x[3] * ge
    out = []
    for d in dfs:
        f = (w0 + fo + d * ge) / 2 / np.pi
        S = cmt_sparams(f, w0, gi_rel * ge, ge, kap, dw, wm / 2 / np.pi, K=K, mod=mod)[K]
        fwd = [S[1, 0], S[2, 1], S[0, 2]]; rev = [S[0, 1], S[1, 2], S[2, 0]]
        il1 = -db(np.array(fwd)).max(); iso1 = -db(np.array(rev)).min()
        il2 = -db(np.array(rev)).max(); iso2 = -db(np.array(fwd)).min()
        out.append((il1, iso1, -db(S[0, 0])) if il1 < il2 else (il2, iso2, -db(S[0, 0])))
    return np.array(out).T

def cost(x, gi_rel=0.0, mod='sine'):
    IL, ISO, RL = ev(x, gi_rel, mod)
    return IL.mean() + 0.3 * np.maximum(0, 35 - ISO).mean() + 0.2 * np.maximum(0, 20 - RL).mean()

if __name__ == '__main__':
    res = {}
    for wm in (2, 3, 4, 5, 7, 10, 15):
        r = differential_evolution(lambda y: cost([y[0], y[1], wm, y[2]]), [(-12, 12), (0, 12), (-15, 15)], seed=1, maxiter=120, popsize=20, tol=1e-10, polish=True)
        IL, ISO, RL = ev([r.x[0], r.x[1], wm, r.x[2]])
        res[wm] = dict(kappa=r.x[0], dw=r.x[1], fop=r.x[2], IL=IL[1], ISO=ISO[1], RL=RL[1])
        print(f"wm/ge={wm:4.1f}: kappa/ge={r.x[0]:6.2f} dw/ge={r.x[1]:5.2f} f_op/ge={r.x[2]:6.2f}  IL={IL[1]:.2f} dB ISO={ISO[1]:.1f} dB RL={RL[1]:.1f} dB")
    best = min(res, key=lambda k: res[k]['IL'] + 0.3 * max(0, 35 - res[k]['ISO']))
    b = res[best]
    print('best wm/ge', best, b)
    # loss sweep at the best normalised point, sine and square (same fundamental)
    loss = {}
    for gi in (0, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5):
        IL, ISO, RL = ev([b['kappa'], b['dw'], best, b['fop']], gi)
        ILs, ISOs, RLs = ev([b['kappa'], b['dw'] * np.pi / 4, best, b['fop']], gi, mod='square')
        loss[gi] = dict(IL=IL[1], ISO=ISO[1], IL_square=ILs[1], ISO_square=ISOs[1])
        print(f"gi/ge={gi}: sine IL={IL[1]:.2f} ISO={ISO[1]:.1f} | square IL={ILs[1]:.2f} ISO={ISOs[1]:.1f}")
    json.dump(dict(scan={str(k): v for k, v in res.items()}, best_wm=best, loss={str(k): v for k, v in loss.items()}),
              open(os.path.join(ROOT, 'results', 'cmt_design_rules.json'), 'w'), indent=1)
