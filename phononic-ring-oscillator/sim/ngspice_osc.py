"""
ngspice_osc.py -- Transistor-level verification of the transmission-mode
phononic-ring oscillator with ngspice (generic 180-nm BSIM3v3 cards).

What it produces (results/ngspice_*.json, paper/data/*.csv):
  1. open-loop AC gain/phase  (loop broken at port 1, replica terminations)
  2. loop noise factor at f0 from .noise per-device contributions
  3. closed-loop transient start-up, steady-state frequency, swing, THD,
     resonator motional current and the power dissipated in Rm

The Spectre equivalents (cadence/netlists/*.scs) use the same element values
(written by this script to cadence/netlists/design_values.scs).
"""
from __future__ import annotations
import os, re, json, subprocess, pathlib, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from ring_model import RingParams, calibrate_to_measurement
from oscillator_design import AmpDesign, default_design
from dataclasses import replace

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
WORK = ROOT / "results" / "ngspice"
WORK.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------
_CHAR = {}


def characterize_model(L=0.18e-6, vds=0.9, model="nch"):
    """DC-sweep a 100-um test device: returns (vgs, id_per_um, gm_id) arrays (cached)."""
    key = (L, vds, model)
    if key in _CHAR:
        return _CHAR[key]
    if model == "nch":
        dev = f"M1 d g 0 0 nch W=100u L={L}"
    else:   # PMOS: source at 1.8 V, sweep |Vgs| via Vg = 1.8 - vsg
        dev = f"M1 d g vdd vdd pch W=100u L={L}\nVdd vdd 0 1.8"
        vds = 1.8 - vds
    cir = f"""* model characterisation
.include {HERE/'models_180nm.lib'}
Vg g 0 0.5
Vd d 0 {vds}
{dev}
.control
set filetype=ascii
dc Vg 0.3 1.2 0.005
wrdata {WORK/'char.txt'} i(Vd)
quit
.endc
.end
"""
    f = WORK / "char.cir"; f.write_text(cir)
    subprocess.run(["ngspice", "-b", str(f)], capture_output=True)
    d = np.loadtxt(WORK / "char.txt")
    vgs, idd = d[:, 0], -d[:, 1]
    if model != "nch":
        vgs, idd = (1.8 - vgs)[::-1], (-idd)[::-1]
    gm = np.gradient(idd, vgs)
    _CHAR[key] = (vgs, idd / 100.0, gm / idd)
    return _CHAR[key]


def size_for(I, gm_id, L=0.18e-6):
    """Width [m] giving current I at the requested gm/ID (bias Vgs is set by the tail)."""
    vgs, jd, gmid = characterize_model(L)
    k = np.argmin(abs(gmid - gm_id))
    return 1e-6 * I / jd[k], vgs[k]


def tail_width(I, vgs=0.9, L=0.36e-6, model="nch"):
    vg, jd, _ = characterize_model(L, model=model)
    return 1e-6 * I / np.interp(vgs, vg, jd)


VBN = 0.9     # tail-bias gate voltage


def device_sizes(amp: AmpDesign):
    """W/L from the gm/ID targets using the actual model characteristics."""
    W1, vg1 = size_for(amp.I1, amp.gm_id1)
    W2, vg2 = size_for(amp.I2, amp.gm_id2)
    W4, vg4 = size_for(amp.I4, amp.gm_id4)
    W3, vg3 = size_for(amp.I3, amp.gm_id3)
    return dict(W1=W1, W2=W2, W3=W3, W4=W4, L=0.18e-6, vgs1=vg1, vgs2=vg2, vgs4=vg4,
                Wt1=tail_width(amp.I1), Wt2=tail_width(2 * amp.I2), Wt3=tail_width(2 * amp.I3), Wt4=tail_width(amp.I4),
                Wp2=tail_width(amp.I2p, vgs=0.9, model="pch"))


def resonator_subckt(p: RingParams):
    m = p.mbvd()
    sp = p.spur_branches()
    lines = [".subckt ring p1 n1 p2 n2",
             f"Rs1 p1 i1 {p.Rs}", f"C01 i1 n1 {p.C0}", f"R01 i1 n1 {p.R0}",
             f"Rs2 p2 i2 {p.Rs}", f"C02 i2 n2 {p.C0}", f"R02 i2 n2 {p.R0}",
             "* main motional chain, floating 4-terminal implementation",
             "E1 ma mx i1 n1 1", "E2 mx 0 i2 n2 -1",
             f"Lm ma mc {m['Lm']}", f"Cm mc md {m['Cm']}", f"Rm md ms {m['Rm']}", "Vsm ms 0 0",
             "F1 i1 n1 Vsm 1", "F2 n2 i2 Vsm 1"]
    for k, b in enumerate(sp, 1):
        lines += [f"Es{k} sa{k} sx{k} i1 n1 1", f"Es{k}b sx{k} 0 i2 n2 -1",
                  f"Ls{k} sa{k} sc{k} {b['L']}", f"Cs{k} sc{k} sd{k} {b['C']}", f"Rsp{k} sd{k} se{k} {b['R']}", f"Vss{k} se{k} 0 0",
                  f"Fs{k}a i1 n1 Vss{k} 1", f"Fs{k}b n2 i2 Vss{k} 1"]
    lines.append(".ends ring")
    return "\n".join(lines)


def amplifier_core(p: RingParams, amp: AmpDesign, Ct, polarity):
    """Sustaining amplifier.  Inputs: port-2 nodes p2/n2.  Outputs: oa/ob."""
    d = device_sizes(amp)
    w0 = 2 * np.pi * p.f0
    rLin = w0 * amp.L_in / amp.Q_Lin
    rLout = w0 * amp.L_out / amp.Q_Lout
    rLt = w0 * (amp.L_t / 2) / amp.Q_t
    # polarity: which drain feeds which stage-2 gate
    ga, gb = ("d1a", "d1b") if polarity > 0 else ("d1b", "d1a")
    return f"""
* ---- bias ----
Vdd vdd 0 {amp.vdd}
Vb1 vb1 0 {0.45 + d['vgs1']:.3f}
Vb2 vb2 0 {0.40 + d['vgs2']:.3f}
Vbn vbn 0 {VBN}
Vbc vbc 0 1.30
Vbp vbp 0 0.90
* ---- port-2 resonating inductor (Q={amp.Q_Lin}), CENTRE-TAPPED: its tap feeds the
* ---- CG bias current, so the tail-current-source noise is common-mode ----
Lina p2 lina {amp.L_in/2}
RLina lina ct {rLin/2}
Linb n2 linb {amp.L_in/2}
RLinb linb ct {rLin/2}
Cct ct 0 10p
Cpa p2 0 {amp.Cpar_in}
Cpb n2 0 {amp.Cpar_in}
* ---- stage 1: common-gate pair, LC tank load ----
M1a d1ai vb1 p2 0 nch W={d['W1']:.3e} L={d['L']:.2e}
M1b d1bi vb1 n2 0 nch W={d['W1']:.3e} L={d['L']:.2e}
* cascode devices: isolate the tank from gds of the CG pair
M1ca d1a vbc d1ai 0 nch W={d['W1']:.3e} L={d['L']:.2e}
M1cb d1b vbc d1bi 0 nch W={d['W1']:.3e} L={d['L']:.2e}
Mt1 ct vbn 0 0 nch W={2*d['Wt1']:.3e} L=0.36e-6
Lta vdd lta {amp.L_t/2}
Rta lta d1a {rLt}
Ltb vdd ltb {amp.L_t/2}
Rtb ltb d1b {rLt}
Ct d1a d1b {Ct}
* ---- stage 2: resistor-loaded differential pair (AC coupled) ----
Cc2a {ga} g2a 2p
Cc2b {gb} g2b 2p
Rb2a g2a vb2 5k
Rb2b g2b vb2 5k
M2a d2a g2a s2 0 nch W={d['W2']:.3e} L={d['L']:.2e}
M2b d2b g2b s2 0 nch W={d['W2']:.3e} L={d['L']:.2e}
Mt2 s2 vbn 0 0 nch W={d['Wt2']:.3e} L=0.36e-6
RL2a vdd d2a {amp.RL2}
RL2b vdd d2b {amp.RL2}
* PMOS current-source assist: carries I2p of the stage-2 bias so RL2 can be larger
M5a d2a vbp vdd vdd pch W={d['Wp2']:.3e} L=0.36e-6
M5b d2b vbp vdd vdd pch W={d['Wp2']:.3e} L=0.36e-6
* ---- stage 3: second resistor-loaded differential pair ----
Cc3a d2a g3a 2p
Cc3b d2b g3b 2p
Rb3a g3a vb2 5k
Rb3b g3b vb2 5k
M3a d3a g3a s3 0 nch W={d['W3']:.3e} L={d['L']:.2e}
M3b d3b g3b s3 0 nch W={d['W3']:.3e} L={d['L']:.2e}
Mt3 s3 vbn 0 0 nch W={d['Wt3']:.3e} L=0.36e-6
RL3a vdd d3a {amp.RL3}
RL3b vdd d3b {amp.RL3}
* ---- stage 4: source-follower drivers ----
M4a vdd d3a oa 0 nch W={d['W4']:.3e} L={d['L']:.2e}
M4b vdd d3b ob 0 nch W={d['W4']:.3e} L={d['L']:.2e}
Mt4a oa vbn 0 0 nch W={d['Wt4']:.3e} L=0.36e-6
Mt4b ob vbn 0 0 nch W={d['Wt4']:.3e} L=0.36e-6
"""


def port1_network(amp: AmpDesign, p: RingParams, prefix=""):
    w0 = 2 * np.pi * p.f0
    rLout = w0 * amp.L_out / amp.Q_Lout
    return f"""
* ---- port-1 resonating inductor and DC definition ----
Lout{prefix} p1{prefix} lo1{prefix} {amp.L_out}
RLout{prefix} lo1{prefix} n1{prefix} {rLout}
Rdc{prefix} p1{prefix} 0 10k
"""


def tank_cap(amp: AmpDesign, p: RingParams, Cdev=0.25e-12):
    """Tank capacitor so that the tank resonates at f0 (Cdev = estimated device/parasitic C)."""
    return max(1 / ((2 * np.pi * p.f0 * (1 + amp.tank_detune)) ** 2 * amp.L_t) - Cdev, 50e-15)


# --------------------------------------------------------------------------
def netlist_openloop(p, amp, Ct, polarity):
    """Loop broken at port 1: drive the resonator with a differential source
    through replica driver impedances; load the real drivers with a replica of
    port 1 (C0 || L_out || R0).  Loop gain = V(oa,ob)/V(src)."""
    r_out = 1 / amp.gm4
    return f"""* open-loop AC / noise of the phononic ring oscillator
.include {HERE/'models_180nm.lib'}
{resonator_subckt(p)}
Xr p1 n1 p2 n2 ring
{port1_network(amp, p)}
Vsrc src 0 dc 0 ac 1
Esa sa 0 src 0 0.5
Esb sb 0 src 0 -0.5
Roa sa p1 {r_out}
Rob sb n1 {r_out}
{amplifier_core(p, amp, Ct, polarity)}
* replica of port 1 as the driver load
Cr1 oa orx {p.C0}
Rr1 orx ob 1m
Rr0 oa ob {p.R0}
Lr oa lr1 {amp.L_out}
Rlr lr1 ob {2*np.pi*p.f0*amp.L_out/amp.Q_Lout}
Rdco oa 0 10k
Rdcb ob 0 10k
.control
set filetype=ascii
op
print v(d1a) v(d1b) v(p2) v(n2) v(d2a) v(d2b) v(oa) v(ob) i(Vdd)
ac lin 4001 {p.f0-400e3:.6e} {p.f0+400e3:.6e}
let gain = v(oa,ob)
wrdata {WORK/'openloop_ac.txt'} mag(gain) ph(gain)
* wide-band for the tank / mode envelope
ac lin 2001 {p.f0-80e6:.6e} {p.f0+80e6:.6e}
let gainw = v(oa,ob)
wrdata {WORK/'openloop_ac_wide.txt'} mag(gainw) ph(gainw)
noise v(oa,ob) Vsrc lin 3 {p.f0-1e3:.6e} {p.f0+1e3:.6e} 1
setplot noise1
print all > {WORK/'noise_contrib.txt'}
setplot noise2
print all >> {WORK/'noise_contrib.txt'}
quit
.endc
.end
"""


def netlist_closedloop(p, amp, Ct, polarity, tstop=40e-6, tstep=25e-12):
    return f"""* closed-loop transient start-up of the phononic ring oscillator
.include {HERE/'models_180nm.lib'}
{resonator_subckt(p)}
Xr p1 n1 p2 n2 ring
{port1_network(amp, p)}
{amplifier_core(p, amp, Ct, polarity)}
* drivers -> port 1 (AC coupled)
Cca oa p1 10p
Ccb ob n1 10p
* motional-current sense (series with chain inside Xr: use Vsm)
* start-up kick: 1-ns current pulse into port 1
Ikick 0 p1 pulse(0 50u 1n 10p 10p 1n 1)
.option reltol=1e-4 abstol=1e-12 vntol=1e-7 method=gear maxord=2
.control
set filetype=ascii
tran {tstep} {tstop} 0 {tstep}
let vdiff = v(p1)-v(n1)
let vout = v(oa)-v(ob)
let im = i(v.xr.vsm)
wrdata {WORK/'tran_ss.txt'} vdiff vout im
quit
.endc
.end
"""


def run(netlist_text, name):
    f = WORK / f"{name}.cir"
    f.write_text(netlist_text)
    log = WORK / f"{name}.log"
    with open(log, "w") as lf:
        r = subprocess.run(["ngspice", "-b", str(f)], stdout=lf, stderr=subprocess.STDOUT, timeout=3600)
    return r.returncode, log


def read_wrdata(path, ncols):
    d = np.loadtxt(path)
    # wrdata writes x y x y ... pairs per column
    cols = [d[:, 2 * k + 1] for k in range(ncols)]
    return d[:, 0], cols


def analyse_openloop(p):
    f, (mag, ph) = read_wrdata(WORK / "openloop_ac.txt", 2)
    i0 = np.argmin(abs(f - p.f0))
    ph_u = np.unwrap(np.deg2rad(ph))
    # zero-phase crossing nearest f0
    z = np.where(np.diff(np.sign(ph_u)) != 0)[0]
    fosc = None
    if len(z):
        k = z[np.argmin(abs(f[z] - p.f0))]
        fosc = f[k] - ph_u[k] * (f[k + 1] - f[k]) / (ph_u[k + 1] - ph_u[k])
    return dict(T0_dB=float(20 * np.log10(mag[i0])), T0_phase_deg=float(ph[i0]),
                f_barkhausen=None if fosc is None else float(fosc),
                T_dB_at_barkhausen=None if fosc is None else float(20 * np.log10(np.interp(fosc, f, mag))))


def analyse_noise():
    """ngspice prints output-noise spectral densities in V/sqrt(Hz) per generator.
    Loop noise factor F = (total)^2 / (contribution of the motional resistance Rm)^2."""
    txt = (WORK / "noise_contrib.txt").read_text()
    vals = {}
    for b in re.split(r"\n\s*\n", txt):
        lines = [l for l in b.splitlines() if l.strip()]
        hdr = [l for l in lines if l.startswith("Index")]
        rows = [l.split() for l in lines if re.match(r"^\d+\s", l)]
        if not hdr or len(rows) < 2:
            continue
        cols = hdr[0].split()[2:]
        for c, v in zip(cols, rows[1][2:]):
            vals[c] = float(v)
    tot = vals.get("onoise_spectrum")
    rm_keys = [k for k in vals if k.startswith("onoise") and "xr.rm" in k.lower() and not k.endswith("_")]
    if tot is None or not rm_keys:
        return dict(raw={k: v for k, v in vals.items() if v > 0})
    rm = vals[rm_keys[0]]
    parts = {k.replace("onoise", "").strip("._"): (v / rm) ** 2 for k, v in vals.items()
             if k.startswith("onoise") and k not in ("onoise_spectrum",) and v > 0.03 * rm}
    F = (tot / rm) ** 2
    return dict(F=F, F_dB=10 * np.log10(F), parts_rel=dict(sorted(parts.items(), key=lambda kv: -kv[1])[:12]))


def analyse_transient(p, amp):
    ts, (vds, vos, im) = read_wrdata(WORK / "tran_ss.txt", 3)
    t, vd, vo = ts, vds, vos
    # envelope: block maxima over 100-ns windows
    nb = 100e-9 / (t[1] - t[0])
    n = int(len(t) // nb)
    env_t = t[: n * int(nb)].reshape(n, int(nb)).mean(1)
    env = abs(vd[: n * int(nb)]).reshape(n, int(nb)).max(1)
    vfinal = env[-10:].mean()
    i90 = np.argmax(env > 0.9 * vfinal)
    out = dict(v_port1_peak=float(vfinal), t_startup_90=float(env_t[i90]), env_t=env_t, env=env)
    # steady state: last 1.5 us
    sel = ts > ts[-1] - 1.5e-6
    ts, vds, vos, im = ts[sel], vds[sel], vos[sel], im[sel]
    # zero crossings -> frequency
    s = np.sign(vds - vds.mean())
    zc = np.where((s[:-1] < 0) & (s[1:] > 0))[0]
    tz = ts[zc] - vds[zc] * (ts[zc + 1] - ts[zc]) / (vds[zc + 1] - vds[zc])
    per = np.diff(tz)
    f_osc = 1 / per.mean()
    # FFT for harmonics (window an integer number of periods)
    N = int(len(tz) - 2)
    i_a, i_b = np.searchsorted(ts, tz[1]), np.searchsorted(ts, tz[N + 1])
    x = vds[i_a:i_b]
    X = abs(np.fft.rfft(x - x.mean()))
    fr = np.fft.rfftfreq(len(x), ts[1] - ts[0])
    def harm(k):
        j = np.argmin(abs(fr - k * f_osc)); return X[max(j - 2, 0): j + 3].max()
    h = np.array([harm(k) for k in range(1, 6)])
    thd = np.sqrt((h[1:] ** 2).sum()) / h[0]
    Im_pk = (im.max() - im.min()) / 2
    P_rm = 0.5 * Im_pk ** 2 * p.mbvd()["Rm"]
    out.update(f_osc=float(f_osc), f_jitter_period_ps=float(per.std() * 1e12), thd_pct=float(100 * thd),
               hd2_dBc=float(20 * np.log10(h[1] / h[0])), hd3_dBc=float(20 * np.log10(h[2] / h[0])),
               v_port1_peak_ss=float((vds.max() - vds.min()) / 2), v_out_peak=float((vos.max() - vos.min()) / 2),
               Im_peak=float(Im_pk), P_Rm_W=float(P_rm), P_Rm_dBm=float(10 * np.log10(P_rm / 1e3)),
               ss_t=ts, ss_v=vds, ss_im=im)
    return out


def main(quick=False):
    p, amp = default_design()
    Ct = tank_cap(amp, p)
    res = {}
    # ---- choose polarity from the open-loop phase and tune the tank to zero phase ----
    best = None
    for pol in (+1, -1):
        rc, log = run(netlist_openloop(p, amp, Ct, pol), f"openloop_pol{pol:+d}")
        if rc != 0:
            print(log.read_text()[-2000:]); raise SystemExit("ngspice failed")
        a = analyse_openloop(p)
        a["polarity"] = pol
        print("open loop", pol, a)
        if best is None or abs(a["T0_phase_deg"]) < abs(best["T0_phase_deg"]):
            best = a
    pol = best["polarity"]
    # ---- tune L_in to the actual port-2 capacitance (C0 + pads + CG/tail parasitics) ----
    bestL, bestT = amp.L_in, -99
    for Lin in np.linspace(0.70, 1.05, 8) * amp.L_in:
        rc, log = run(netlist_openloop(replace(amp, L_in=Lin), p, Ct, pol) if False else netlist_openloop(p, replace(amp, L_in=Lin), Ct, pol), "openloop_lin")
        a = analyse_openloop(p)
        print(f"  L_in = {Lin*1e9:.1f} nH -> T0 = {a['T0_dB']:.2f} dB")
        if a["T0_dB"] > bestT:
            bestT, bestL = a["T0_dB"], Lin
    amp = replace(amp, L_in=bestL)
    rc, log = run(netlist_openloop(p, amp, Ct, pol), "openloop_lin")
    best = analyse_openloop(p); best["polarity"] = pol; best["L_in"] = bestL
    # phase trim with the tank varactor: detune so that phase(f0) -> 0 (2 iterations)
    Ct_trim = Ct
    for it in range(3):
        ph = best["T0_phase_deg"]
        # dphi/dCt ~ -2 Q_t * (dC/2C) ... use numeric secant on detune
        dC = -np.tan(np.deg2rad(ph)) / amp.Q_t * Ct_trim / 2
        Ct_trim = Ct_trim + dC
        rc, log = run(netlist_openloop(p, amp, Ct_trim, pol), "openloop_trim")
        best = analyse_openloop(p); best["polarity"] = pol; best["Ct"] = Ct_trim
        print("trim", it, best)
        if abs(best["T0_phase_deg"]) < 2:
            break
    res["openloop"] = best
    res["noise"] = analyse_noise()
    print("noise:", res["noise"])
    # ---- closed loop ----
    tstop = 12e-6 if quick else 40e-6
    rc, log = run(netlist_closedloop(p, amp, Ct_trim, pol, tstop=tstop), "closedloop")
    if rc != 0:
        print(log.read_text()[-2000:]); raise SystemExit("ngspice closed-loop failed")
    tr = analyse_transient(p, amp)
    res["transient"] = {k: v for k, v in tr.items() if not isinstance(v, np.ndarray)}
    print("transient:", res["transient"])
    np.savetxt(ROOT / "paper" / "data" / "ngspice_startup_envelope.csv", np.c_[tr["env_t"], tr["env"]], delimiter=",", header="t_s,v_port1_env_V", comments="")
    np.savetxt(ROOT / "paper" / "data" / "ngspice_steady_state.csv", np.c_[tr["ss_t"], tr["ss_v"], tr["ss_im"]], delimiter=",", header="t_s,v_port1_V,i_motional_A", comments="")
    res["design"] = dict(Ct=Ct_trim, polarity=pol, L_in=amp.L_in, **device_sizes(amp))
    (ROOT / "results" / "ngspice_results.json").write_text(json.dumps(res, indent=2, default=float))
    # element values for the Spectre netlists
    d = device_sizes(amp); m = p.mbvd()
    (ROOT / "cadence" / "netlists" / "design_values.scs").write_text(f"""// design_values.scs -- generated by sim/ngspice_osc.py  (do not edit by hand)
parameters f0={p.f0:.6e} Rm={m['Rm']:.6e} Lm={m['Lm']:.6e} Cm={m['Cm']:.6e} C0={p.C0:.3e} R0={p.R0:.3e} Rs={p.Rs:.3e}
parameters Lin={amp.L_in:.4e} Lout={amp.L_out:.4e} Lt={amp.L_t:.4e} Ct={Ct_trim:.4e} QL={amp.Q_Lin}
parameters W1={d['W1']:.3e} W2={d['W2']:.3e} W3={d['W3']:.3e} W4={d['W4']:.3e} Wp2={d['Wp2']:.3e} Wt1={d['Wt1']:.3e} Wt2={d['Wt2']:.3e} Wt3={d['Wt3']:.3e} Wt4={d['Wt4']:.3e} Lg={d['L']:.2e} RL2={amp.RL2} RL3={amp.RL3} vb1={0.45 + d['vgs1']:.3f} vb2={0.40 + d['vgs2']:.3f} vbn={VBN}
parameters I1={amp.I1:.3e} I2={amp.I2:.3e} I2p={amp.I2p:.3e} I3={amp.I3:.3e} I4={amp.I4:.3e} vdd={amp.vdd} polarity={pol}
""")
    return res


if __name__ == "__main__":
    main(quick="--quick" in sys.argv)
