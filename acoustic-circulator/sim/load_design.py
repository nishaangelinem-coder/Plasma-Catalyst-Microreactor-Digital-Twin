"""Common loader: results/design_final.json -> Design."""
import os, json, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim.circulator import Design, Resonator, Varactor, SwitchCap
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_design():
    p = json.load(open(os.path.join(ROOT, 'results', 'design_final.json')))
    sw = SwitchCap(Csw=p['Csw'], W=p['W_um'], Cpar=p.get('Cpar', 0.0)) if p.get('element', 'switch') == 'switch' else None
    des = Design(Resonator(fs=p['fs'], Qm=p.get('Qm', 500.0)), Varactor(mult=p.get('mult', 1.0)), Cp=p['Cp'], Cc=p.get('Cc', 0.0),
                 fm=p['fm'], Vdc=p.get('Vdc', 0.25), Vm=p.get('Vm', 0.5), waveform='square', direction=p.get('direction', 1),
                 topo=p.get('topo', 'C'), element=p.get('element', 'switch'), sw=sw)
    return des, p
