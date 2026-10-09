"""
Transistor-level verification in ngspice.
  1. Waveforms at the design point (clock, 3-phase outputs, varactor tuning nodes, port voltages).
  2. S-parameter sweep by single-tone transient + DFT for ports 1, 2, 3 (all nine S_mn at the fundamental
     plus the +/- f_m sidebands), with the real CMOS phase generator + drivers.
  3. Power consumption.
Results: results/sparams_ngspice.csv, results/ngspice_summary.json, figures/fig_waveforms*.png, fig_sparams_ngspice.png
"""
import os, sys, json, csv, time
import numpy as np
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim.circulator import Design, Resonator, Varactor, sparams
from sim.ltp import db
from sim.ngspice_tb import run_point
from sim.load_design import load_design
from sim.plotstyle import plt, PAL, COL1, COL2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(ROOT, 'figures'); RES = os.path.join(ROOT, 'results')
WORK = os.path.join(ROOT, 'spice', 'runs')
F0 = 1.0e9


def load():
    return load_design()


def one(args):
    des, f, port, ideal = args
    tag = f"{'ideal' if ideal else 'cmos'}_p{port}_{int(round(f/1e6))}MHz"
    r = run_point(des, f, port, WORK, tag, K=1, ideal_driver=ideal)
    return (f, port, ideal, {str(k): [v.real, v.imag] for k, v in r['S'].items()}, r['P_vddm'], r['P_vdd'])


def waveforms(des):
    r = run_point(des, F0, 1, WORK, 'wave_cmos', K=1, ideal_driver=False)
    t = r['t']; t0 = t[0]
    json.dump(dict(vds_pk=r['vds_pk'], vm_pk=r['vm_pk'], a_in=r['a_in'], P_in_dBm=10*np.log10(r['a_in']**2/1e-3)), open(os.path.join(RES, 'ngspice_stress.json'), 'w'), indent=1)
    fig, ax = plt.subplots(3, 1, figsize=(COL1, 4.8))
    for i in range(3):
        ax[0].plot((t - t0) * 1e9, r['vt'][i] + 1.6 * (2 - i), color=PAL[i], label=f'V$_{{G{i+1}}}$ (+{1.6*(2-i):.1f} V)')
    ax[0].set(ylabel='Gate drives, offset (V)', title='(a) Three-phase CMOS gate drives'); ax[0].legend(ncol=3, loc='upper right', fontsize=6)
    Tm = 1 / des.fm
    ax[0].set_xlim(0, 2.2 * Tm * 1e9)
    for i in range(3):
        ax[1].plot((t - t0) * 1e9, r['vp'][i], color=PAL[i], label=f'v$_{{P{i+1}}}$', lw=0.8)
    ax[1].set(ylabel='Port voltage (V)', title='(b) Port voltages, 1-GHz tone injected at port 1'); ax[1].legend(ncol=3, loc='upper right')
    ax[1].set_xlim(0, 2.2 * Tm * 1e9)
    # zoom
    for i in range(3):
        ax[2].plot((t - t0) * 1e9, r['vp'][i], color=PAL[i], lw=0.9)
    ax[2].set(xlabel='Time (ns)', ylabel='Port voltage (V)', title='(c) Zoom: port 2 carries the signal, port 3 is isolated')
    ax[2].set_xlim(0.5 * Tm * 1e9, 0.5 * Tm * 1e9 + 6)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, 'fig_waveforms.png')); fig.savefig(os.path.join(FIG, 'fig_waveforms.pdf')); plt.close(fig)
    # clock/phase generator waveforms from the standalone bench
    return r


def phasegen_fig():
    """Plot phase generator waveforms from spice/tb_phasegen_out.txt (re-run with design fm)."""
    import subprocess
    des, p = load()
    cir = open(os.path.join(ROOT, 'spice', 'tb_phasegen.cir')).read()
    vddm = 1.2 if des.element == 'switch' else 2 * des.Vm
    cir = cir.replace('fm=25meg', f'fm={des.fm:.6e}').replace('vddm=1.0', f'vddm={vddm:.4f}')
    if des.element == 'switch':
        cir = cir.replace('11.4p', '1.6p')   # gate load of the switch instead of Cdec + varactor
    cir = cir.replace('.tran 20p 400n', '.tran 20p 450n')
    path = os.path.join(WORK, 'tb_phasegen_design.cir'); os.makedirs(WORK, exist_ok=True)
    open(path, 'w').write(cir.replace('wrdata tb_phasegen_out.txt', f'wrdata {WORK}/tb_phasegen_out.txt').replace('.include cmos_blocks.lib', f'.include {ROOT}/spice/cmos_blocks.lib'))
    out = subprocess.run(['ngspice', '-b', path], capture_output=True, text=True, cwd=WORK)
    meas = {}
    for line in out.stdout.splitlines():
        for k in ('pvdd', 'pvddm', 't0', 't1', 't2', 'tr0'):
            if line.startswith(k + ' '):
                meas[k] = float(line.split('=')[1].split()[0])
    d = np.loadtxt(os.path.join(WORK, 'tb_phasegen_out.txt'))
    t = d[:, 0]; cols = [d[:, 2 * i + 1] for i in range(9)]
    clk, ph0, ph120, ph240, vt0, vt1, vt2 = cols[:7]
    Tm = 1 / des.fm
    m = (t > 300e-9) & (t < 300e-9 + 2.3 * Tm)
    fig, ax = plt.subplots(3, 1, figsize=(COL1, 4.2), sharex=True)
    ax[0].plot((t[m] - 300e-9) * 1e9, clk[m], color=PAL[6], lw=0.8); ax[0].set(ylabel='CLK (V)', title=f'(a) Reference clock, {6*des.fm/1e6:.0f} MHz')
    for k, (s, c, l) in enumerate(zip((ph0, ph120, ph240), PAL[:3], ('PH0', 'PH120', 'PH240'))):
        ax[1].plot((t[m] - 300e-9) * 1e9, s[m] + 1.6 * (2 - k), color=c, label=l)
    ax[1].set(ylabel='Phase gen., offset (V)', title='(b) Johnson-counter outputs (0/120/240°)'); ax[1].legend(ncol=3, loc='upper right', fontsize=6)
    for k, (s, c, l) in enumerate(zip((vt0, vt1, vt2), PAL[:3], ('V$_{G1}$', 'V$_{G2}$', 'V$_{G3}$'))):
        ax[2].plot((t[m] - 300e-9) * 1e9, s[m] + 1.6 * (2 - k), color=c, label=l)
    ax[2].set(xlabel='Time (ns)', ylabel='Driver out, offset (V)', title='(c) Driver outputs at the switch gates'); ax[2].legend(ncol=3, loc='upper right', fontsize=6)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, 'fig_phasegen_waveforms.png')); fig.savefig(os.path.join(FIG, 'fig_phasegen_waveforms.pdf')); plt.close(fig)
    ph = {}
    if all(k in meas for k in ('t0', 't1', 't2')):
        ph['phase_ch2_deg'] = ((meas['t1'] - meas['t0']) / Tm * 360) % 360
        ph['phase_ch3_deg'] = ((meas['t2'] - meas['t0']) / Tm * 360) % 360
    vddm = 1.2 if des.element == 'switch' else 2 * des.Vm
    ph['P_vdd_mW'] = -meas.get('pvdd', 0) * 1.2e3; ph['P_vddm_mW'] = -meas.get('pvddm', 0) * vddm * 1e3
    ph['trise_ns'] = meas.get('tr0', float('nan')) * 1e9
    return ph


def main(nfreq=41, ideal_too=True, workers=4):
    des, p = load()
    os.makedirs(WORK, exist_ok=True)
    t0 = time.time()
    ph = phasegen_fig()
    print('phasegen:', ph)
    wr = waveforms(des)
    print('waveform run done', time.time() - t0)
    step = 5e6
    freqs = F0 + step * np.arange(-(nfreq // 2), nfreq // 2 + 1)
    jobs = [(des, f, port, False) for f in freqs for port in (1, 2, 3)]
    freqs_ideal = freqs[::3]
    if ideal_too:
        jobs += [(des, f, port, True) for f in freqs_ideal for port in (1, 2, 3)]
    with ProcessPoolExecutor(workers) as ex:
        results = list(ex.map(one, jobs))
    print('sweep done', time.time() - t0)
    # assemble
    out = {}
    for f, port, ideal, S, pm, pd in results:
        key = 'ideal' if ideal else 'cmos'
        out.setdefault(key, {}).setdefault(f, {})
        for k, v in S.items():
            kk = eval(k); out[key][f][(kk[0], kk[1], port)] = complex(v[0], v[1])
        out[key][f]['P_vddm'] = pm; out[key][f]['P_vdd'] = pd
    # CSV + figure
    S_ltp = sparams(des, freqs, 40)
    fig, ax = plt.subplots(1, 2, figsize=(COL2, 2.6))
    rows = []
    for key, mk in (('cmos', 'o'), ('ideal', 's')):
        if key not in out: continue
        fk = freqs if key == 'cmos' else freqs_ideal
        for (m, n), c, lab in (((2, 1), PAL[0], 'S21'), ((1, 2), PAL[1], 'S12'), ((1, 1), PAL[2], 'S11'), ((3, 1), PAL[3], 'S31')):
            y = [db(out[key][f][(0, m, n)]) for f in fk]
            ax[0].plot(np.array(fk) / 1e9, y, marker=mk, ms=3, ls='none', color=c, mfc='none' if key == 'ideal' else c,
                       label=f'{lab} ngspice ({"CMOS drivers" if key=="cmos" else "ideal pump"})')
    for (m, n), c, lab in (((1, 0), PAL[0], 'S21'), ((0, 1), PAL[1], 'S12'), ((0, 0), PAL[2], 'S11'), ((2, 0), PAL[3], 'S31')):
        fx = np.linspace(freqs[0], freqs[-1], 121)
        ax[0].plot(fx / 1e9, db(sparams(des, fx, 40)[:, 40, m, n]), color=c, lw=1.0, label=f'{lab} LTP' if m == 1 and n == 0 else None)
    ax[0].set(xlabel='Frequency (GHz)', ylabel='|S| (dB)', ylim=(-45, 1), title='(a) Transistor-level transient vs LTP/PSP'); ax[0].legend(fontsize=5, ncol=2, loc='lower left')
    # sidebands
    for key, mk in (('cmos', 'o'),):
        for k, c, lab in ((1, PAL[0], 'port 2 @ f+f$_m$'), (-1, PAL[1], 'port 2 @ f-f$_m$')):
            ax[1].plot(freqs / 1e9, [db(out[key][f][(k, 2, 1)]) for f in freqs], marker=mk, ms=3, ls='none', color=c, label=lab + ' (ngspice)')
            ax[1].plot(freqs / 1e9, db(S_ltp[:, 40 + k, 1, 0]), color=c, lw=1.0, label=lab + ' (LTP)')
    ax[1].set(xlabel='Frequency (GHz)', ylabel='Conversion gain (dB)', ylim=(-70, 0), title='(b) Sideband conversion'); ax[1].legend(fontsize=6)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, 'fig_sparams_ngspice.png')); fig.savefig(os.path.join(FIG, 'fig_sparams_ngspice.pdf')); plt.close(fig)
    with open(os.path.join(RES, 'sparams_ngspice.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['driver', 'f_Hz'] + [f'S{m}{n}_dB' for n in (1, 2, 3) for m in (1, 2, 3)] + ['S21_up_dB', 'S21_dn_dB', 'P_vddm_W', 'P_vdd_W'])
        for key in out:
            for f in (freqs if key == 'cmos' else freqs_ideal):
                d = out[key][f]
                w.writerow([key, f'{f:.4e}'] + [f'{db(d[(0, m, n)]):.3f}' for n in (1, 2, 3) for m in (1, 2, 3)] +
                           [f'{db(d[(1, 2, 1)]):.3f}', f'{db(d[(-1, 2, 1)]):.3f}', f'{d["P_vddm"]:.4e}', f'{d["P_vdd"]:.4e}'])
    i0 = int(np.argmin(np.abs(freqs - F0)))
    d = out['cmos'][freqs[i0]]
    fwd = [db(d[(0, 2, 1)]), db(d[(0, 3, 2)]), db(d[(0, 1, 3)])]; rev = [db(d[(0, 1, 2)]), db(d[(0, 2, 3)]), db(d[(0, 3, 1)])]
    summ = dict(IL_dB=-max(fwd), ISO_dB=-max(rev), RL_dB=-max(db(d[(0, 1, 1)]), db(d[(0, 2, 2)]), db(d[(0, 3, 3)])),
                IL_paths_dB=[-x for x in fwd], ISO_paths_dB=[-x for x in rev],
                IM_up_S21_dB=db(d[(1, 2, 1)]), IM_dn_S21_dB=db(d[(-1, 2, 1)]),
                P_vddm_mW=d['P_vddm'] * 1e3, P_vdd_mW=d['P_vdd'] * 1e3, phasegen=ph)
    # LTP at same point for the comparison table
    SL = S_ltp[i0, 40]
    summ['LTP_IL_dB'] = -max(db(SL[1, 0]), db(SL[2, 1]), db(SL[0, 2])); summ['LTP_ISO_dB'] = -max(db(SL[0, 1]), db(SL[1, 2]), db(SL[2, 0]))
    # 20 dB isolation bandwidth from ngspice points (worst reverse path)
    iso = np.array([-max(db(out['cmos'][f][(0, 1, 2)]), db(out['cmos'][f][(0, 2, 3)]), db(out['cmos'][f][(0, 3, 1)])) for f in freqs])
    il = np.array([-max(db(out['cmos'][f][(0, 2, 1)]), db(out['cmos'][f][(0, 3, 2)]), db(out['cmos'][f][(0, 1, 3)])) for f in freqs])
    summ['BW_iso20_MHz_ngspice'] = float(step / 1e6 * np.sum(iso >= 20)); summ['IL_max_in_iso20_bw_dB'] = float(il[iso >= 20].max()) if np.any(iso >= 20) else None
    if 'ideal' in out and freqs[i0] in out['ideal']:
        d2 = out['ideal'][freqs[i0]]
        summ['ideal_IL_dB'] = -max(db(d2[(0, 2, 1)]), db(d2[(0, 3, 2)]), db(d2[(0, 1, 3)])); summ['ideal_ISO_dB'] = -max(db(d2[(0, 1, 2)]), db(d2[(0, 2, 3)]), db(d2[(0, 3, 1)]))
    json.dump(summ, open(os.path.join(RES, 'ngspice_summary.json'), 'w'), indent=1)
    print(json.dumps(summ, indent=1)); print('total time', time.time() - t0)


if __name__ == '__main__':
    nf = int(sys.argv[1]) if len(sys.argv) > 1 else 41
    main(nfreq=nf)
