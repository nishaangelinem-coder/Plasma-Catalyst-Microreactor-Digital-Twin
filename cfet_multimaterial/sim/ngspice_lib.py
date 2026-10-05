"""Emit the ngspice behavioural library implementing the UCM-CFET equations.

Run: python3 -m sim.ngspice_lib   (writes netlists/ngspice/ucm_cfet.lib)
Each device is a .subckt with the same parameter names as the Verilog-A module; the
equations are evaluated with B-sources, .func macros and charge-based (Q=) capacitors, which
is the ngspice equivalent of the Verilog-A ddt() contributions. TEMPK is the ambient
temperature in kelvin passed from the testbench.
"""
from __future__ import annotations
import json, os, datetime
from .platforms import DEVICES, PARAM_ORDER, TRANSPORT_LANDAUER, INF, G0

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def fmt(v):
    return "1.0e9" if v == INF else repr(float(v))


def load_calibrated():
    f = os.path.join(HERE, "data", "calibrated_params.json")
    return json.load(open(f)) if os.path.exists(f) else {}


def subckt(name, dev, params):
    sign = 1 if dev["polarity"] == "n" else -1
    plist = " ".join(f"{k}={fmt(params[k])}" for k in PARAM_ORDER)
    td = "(TEMPK + V(tj))"
    vgs, vds = "(TYPE*V(g,si))", "(TYPE*V(di,si))"
    if dev["transport"] == TRANSPORT_LANDAUER:
        core = (f"* Landauer quasi-ballistic current (CNT array), n-type convention; eta_s on an auxiliary node\n"
                f"Betas etas 0 V = ALPHA*({vgs} - vtheff({vds},{td}))/(nid()*vt({td}))\n"
                f"Bids di dx I = TYPE*(DCNT*weff()*(1-FMET)*G0*TTR*nid()*vt({td})*(sp(V(etas)) - sp(V(etas) - {vds}/(nid()*vt({td}))))*(1 + LAMBDA*sabs({vds}))\n"
                f"+ + FMET*DCNT*weff()*G0*TTR*{vds})\n")
    else:
        core = (f"* drift-diffusion + velocity saturation, n-type convention; Vov and Vdsat on auxiliary nodes\n"
                f"Bvov vov 0 V = 2*nid()*vt({td})*sp(({vgs} - vtheff({vds},{td}))/(2*nid()*vt({td})))\n"
                f"Bvdsat vdsat 0 V = V(vov)/(1 + V(vov)/(VSAT*L/mut({td})))\n"
                f"Bids di dx I = TYPE*mut({td})*coxeff()*weff()/L*V(vov)*V(vov)/(2*(1 + V(vov)/(VSAT*L/mut({td}))))*tanh(2*{vds}/(V(vdsat) + 1e-9))*(1 + LAMBDA*sabs({vds}))\n")
    mut = ".func mut(td) {MU0 > 0 ? MU0*pow(td/TNOM, -MUEXP) : 1}"
    return f"""
* -------------------------------------------------------------------------------------
* {name}: UCM-CFET {dev['material']} {dev['polarity']}-FET  (platform {dev['platform_tag']}, {dev['transport']})
* terminals d g s b ; TYPE = {sign}
* -------------------------------------------------------------------------------------
.subckt {name} d g s b {plist} TEMPK=300.15
.param TYPE={sign}
.param G0={G0!r}
.param QE=1.602176634e-19 KBOLTZ=1.380649e-23
.func sp(x) {{x > 40 ? x : ln(1 + exp(x))}}
.func sabs(x) {{sqrt(x*x + 1e-6)}}
.func weff() {{NNS > 0 ? NNS*2*(WNS + TNS) : W}}
.func vt(td) {{KBOLTZ*td/QE}}
.func coxeff() {{COX*CQ/(COX + CQ)}}
.func nid() {{N0*(1 + QE*DIT/COX)}}
.func vtht(td) {{VTH0 + KVTH*(td - TNOM)}}
.func vtheff(vds,td) {{vtht(td) - ETA*sabs(vds)}}
{mut}
* charge function (own-branch voltage only)
.func qg(v,td) {{0.5*weff()*L*coxeff()*2*nid()*vt(td)*sp((v - vtht(td))/(2*nid()*vt(td)))}}
* series resistances (floored at 1 mOhm for the solver)
Rd d di R={{(RDW/weff()) > 1e-3 ? RDW/weff() : 1e-3}}
Rs s si R={{(RSW/weff()) > 1e-3 ? RSW/weff() : 1e-3}}
{core}Vsns dx si 0
* terminal charges  Qg = Qgs + Qgd ; Qs = -Qgs ; Qd = -Qgd
Cgs g si Q = TYPE*(qg({vgs}, {td}) + CGSO*weff()*{vgs})
Cgd g di Q = TYPE*(qg(TYPE*V(g,di), {td}) + CGDO*weff()*TYPE*V(g,di))
* self-heating thermal node (temperature rise in volts == kelvin); RTH=0 -> node held at 0
Bpd tj 0 I = -(RTH > 0 ? 1 : 0)*TYPE*i(Vsns)*{vds}
Rth tj 0 R={{RTH > 0 ? RTH : 1e-3}}
Cth tj 0 {{CTH}}
* body: reference only
Rb b si 1e12
.ends {name}
"""


def main():
    cal = load_calibrated()
    out = [f"* ucm_cfet.lib -- ngspice behavioural implementation of the UCM-CFET models\n"
           f"* generated {datetime.date.today()} by sim/ngspice_lib.py from sim/platforms.py "
           f"(+ data/calibrated_params.json if present)\n"
           f"* Equations identical to veriloga/*.va ; see doc/model_spec.md\n"]
    for name, dev in DEVICES.items():
        params = dict(dev["params"]); params.update(cal.get(name, {}))
        out.append(subckt(name, dev, params))
    os.makedirs(os.path.join(HERE, "netlists", "ngspice"), exist_ok=True)
    path = os.path.join(HERE, "netlists", "ngspice", "ucm_cfet.lib")
    open(path, "w").write("".join(out))
    print("wrote", path)


if __name__ == "__main__":
    main()
