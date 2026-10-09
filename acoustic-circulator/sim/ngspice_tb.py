"""
Transistor-level co-simulation of the complete circulator in ngspice:
  reference clock -> Johnson phase generator -> tapered drivers -> modulators
  -> three-resonator (mBVD) wye network (topology 'C') -> 50-ohm ports.

Modulator 'switch': MIM C_sw in series with a wide nMOS switch (BSIM4) whose gate is driven by the
CMOS driver; 'varactor': behavioural A-MOS varactor whose tuning node is the driver output.

S-parameters of the (time-varying) network are extracted exactly as Spectre's PSS+PSP would report
them: a single tone at f_RF is applied to one port, the steady-state port voltages are Fourier-analysed
over an integer number of common periods, and S_mn = b_m / a_n at f_RF (plus the +/- k f_m sidebands).
"""
from __future__ import annotations
import os, subprocess, json, math
import numpy as np
from .circulator import Design, SwitchCap

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SPICE = os.path.join(ROOT, 'spice')


def netlist(des: Design, f_rf: float, port: int, t_settle: float, t_win: float, dt: float,
            ideal_driver: bool = False, vdd: float = 1.2, out_file: str = 'out.txt', vsrc: float = 0.2,
            cdec: float = 10e-12, nfinger_w: float = 5.0) -> str:
    r = des.res
    fm = des.fm
    tclk = 1 / (6 * fm)
    direction = des.direction
    is_sw = des.element == 'switch'
    sw = des.sw or SwitchCap()
    vddm = vdd if is_sw else 2 * des.Vm
    L = []
    a = L.append
    a('* STM acoustic circulator (series-mode wye, %s modulator) - transistor-level testbench (auto-generated)' % des.element)
    a(f'.include {SPICE}/cmos_blocks.lib')
    a(f'.param vdd={vdd} vddm={vddm:.4f} fm={fm:.6e} frf={f_rf:.6e} tclk={tclk:.6e}')
    a('Vdd vdd 0 dc {vdd}')
    a('Vddm vddm 0 dc {vddm}')
    # phase order: cell n lags by n*120 deg for direction +1
    ph = ['ph0', 'ph120', 'ph240'] if direction > 0 else ['ph0', 'ph240', 'ph120']
    if ideal_driver:
        for n in range(3):
            lag = (n if direction > 0 else (3 - n) % 3) * (1 / fm) / 3
            # gate high (switch ON) when cos(wm t - phi) > 0  -> high from -T/4 to +T/4 relative to the lag
            a(f'Vt{n} vt{n} 0 dc 0 pulse(0 {vddm:.4f} {lag + 0.75 / fm:.6e} 60p 60p {0.5 / fm - 60e-12:.6e} {1 / fm:.6e})')
    else:
        a('Vclk clk 0 dc 0 pulse(0 {vdd} 0 40p 40p {tclk/2-40p} {tclk})')
        a('Vrst rstn 0 dc 0 pulse(0 {vdd} {3.5*tclk} 50p 50p 1 2)')
        a('Xpg clk rstn ph0 ph120 ph240 vdd 0 phasegen')
        for n in range(3):
            a(f'Xd{n} {ph[n]} vt{n} vdd vddm 0 vdrv')
            if not is_sw:
                a(f'Cdec{n} vt{n} 0 {cdec:.3e}')
    if not is_sw:
        v = des.var
        a(f'.param cmax={v.cmax:.4e} cmin={v.cmin:.4e} v0={v.V0} vs={v.Vs}')
        a(f'Vb vbias 0 dc {des.Vdc + vddm / 2:.4f}')
    a('Rstar star 0 10k')
    for n in range(3):
        p = n + 1
        amp = vsrc if p == port else 0.0
        a(f'Vp{p} ps{p} 0 dc 0 sin(0 {amp} {{frf}})')
        a(f'Rp{p} ps{p} p{p} {des.z0}')
        if des.Cp > 0:
            a(f'Csh{p} p{p} 0 {des.Cp:.4e}')
        # mBVD resonator between p and m
        a(f'Rs{p} p{p} ri{p} {r.Rs}')
        a(f'R0_{p} ri{p} c0{p} {r.R0}')
        a(f'C0_{p} c0{p} m{p} {r.C0:.4e}')
        a(f'Rm{p} ri{p} m1{p} {r.Rm:.4f}')
        a(f'Lm{p} m1{p} m2{p} {r.Lm:.6e}')
        a(f'Cm{p} m2{p} m{p} {r.Cm:.4e}')
        a(f'Rb{p} m{p} 0 50k')
        if is_sw:
            # MIM in series with the nMOS switch to the star; optional fixed Cpar; gate = driver output
            a(f'Csw{p} m{p} d{p} {sw.Csw:.4e}')
            nf = max(1, int(round(sw.W / nfinger_w)))
            # BSIM4: w is the TOTAL width, nf the number of fingers (per-finger width = w/nf)
            # RF-switch configuration: gate through Rg (floating at RF), triple-well body tied to source via Rb, DNW cap
            a(f'Rg{p} vt{n} g{p} {sw.Rg:.1f}')
            a(f'Rbody{p} b{p} star {sw.Rb:.1f}')
            a(f'Cdnw{p} b{p} 0 {sw.Cdnw:.3e}')
            a(f'Msw{p} d{p} g{p} star b{p} nmos65 w={sw.W:.1f}u l=65n nf={nf} m=1')
            a(f'Rd{p} d{p} 0 50k')
            if sw.Cpar > 0:
                a(f'Cpar{p} m{p} star {sw.Cpar:.4e}')
        else:
            # varactor: gate side at the resonator node (biased through Rb to vbias), well/tune side at the star
            a(f'Rv{p} m{p} vg{p} {v.rv:.4f}')
            a(f'Cv{p} vg{p} star C={{cmin + (cmax-cmin)*0.5*(1+tanh((v(vg{p},star)-v0)/vs))}}')
    a('.option reltol=1e-4 abstol=1e-12 vntol=1e-7 chgtol=1e-16 method=trap')   # trap: no numerical damping of the high-Q resonators
    a(f'.tran {dt:.3e} {t_settle + t_win:.6e} {t_settle:.6e} {dt:.3e}')
    a('.control')
    a('run')
    a(f'wrdata {out_file} v(ps{port}) v(p1) v(p2) v(p3) v(vt0) v(vt1) v(vt2) i(Vddm) i(Vdd) v(d{port},star) v(m{port})')
    a('.endc')
    a('.end')
    return '\n'.join(L) + '\n'


def read_wrdata(path, ncols):
    d = np.loadtxt(path)
    t = d[:, 0]
    cols = [d[:, 2 * i + 1] for i in range(ncols)]
    return t, cols


def dft(t, x, f):
    """Single-bin DFT (complex amplitude of exp(j2pi f t)) on a uniform resampled grid over [t0, t_end]."""
    tu = np.linspace(t[0], t[-1], 1 << int(math.ceil(math.log2(len(t)))))
    xu = np.interp(tu, t, x)
    w = np.exp(-2j * np.pi * f * tu)
    return 2 * np.trapezoid(xu * w, tu) / (tu[-1] - tu[0])


def run_point(des: Design, f_rf: float, port: int, workdir: str, tag: str, K: int = 2, **kw):
    """Run one transient and return dict with S[(k, m)] at fundamental and sidebands, plus supply power."""
    workdir = os.path.abspath(workdir)
    os.makedirs(workdir, exist_ok=True)
    fm = des.fm
    g = math.gcd(int(round(f_rf)), int(round(fm)))
    T = 1.0 / g
    nper = max(1, int(round(200e-9 / T)))
    t_win = nper * T
    t_settle = kw.pop('t_settle', 400e-9)
    dt = kw.pop('dt', 20e-12)
    out = os.path.join(workdir, f'{tag}.txt')
    cir = os.path.join(workdir, f'{tag}.cir')
    with open(cir, 'w') as fh:
        fh.write(netlist(des, f_rf, port, t_settle, t_win, dt, out_file=out, **kw))
    res = subprocess.run(['ngspice', '-b', cir], capture_output=True, text=True, cwd=workdir)
    if not os.path.exists(out):
        raise RuntimeError(res.stdout[-2000:] + res.stderr[-2000:])
    t, (vs, p1, p2, p3, vt0, vt1, vt2, iddm, idd, vds, vm) = read_wrdata(out, 11)
    m = t >= t_settle
    t = t[m]; V = [p1[m], p2[m], p3[m]]; vs = vs[m]
    z0 = des.z0
    S = {}
    Vs = dft(t, vs, f_rf)
    a_in = Vs / (2 * np.sqrt(z0))
    for k in range(-K, K + 1):
        f = f_rf + k * fm
        for mm in range(3):
            Vm = dft(t, V[mm], f)
            if mm + 1 == port and k == 0:
                b = (2 * Vm - Vs) / (2 * np.sqrt(z0))
            else:
                b = Vm / np.sqrt(z0)
            S[(k, mm + 1)] = b / a_in
    vddm_val = 1.2 if des.element == 'switch' else 2 * des.Vm
    pdm = -np.mean(iddm[m]) * vddm_val
    pdd = -np.mean(idd[m]) * 1.2
    return dict(S=S, P_vddm=pdm, P_vdd=pdd, t=t, vt=(vt0[m], vt1[m], vt2[m]), vp=V, vs=vs,
                vds_pk=float(np.max(np.abs(vds[m]))), vm_pk=float(np.max(np.abs(vm[m]))), a_in=abs(a_in))
