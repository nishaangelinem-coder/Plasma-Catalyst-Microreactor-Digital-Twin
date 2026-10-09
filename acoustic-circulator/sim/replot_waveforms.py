"""Re-generate the two waveform figures from saved ngspice outputs (no re-simulation)."""
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim.plotstyle import plt, PAL, COL1
from sim.load_design import load_design
from sim.ngspice_tb import read_wrdata
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); FIG = os.path.join(ROOT, 'figures'); WORK = os.path.join(ROOT, 'spice', 'runs')
des, p = load_design(); Tm = 1 / des.fm
# phase generator bench
d = np.loadtxt(os.path.join(WORK, 'tb_phasegen_out.txt')); t = d[:, 0]; cols = [d[:, 2 * i + 1] for i in range(9)]
clk, ph0, ph120, ph240, vt0, vt1, vt2 = cols[:7]
m = (t > 300e-9) & (t < 300e-9 + 2.3 * Tm)
fig, ax = plt.subplots(3, 1, figsize=(COL1, 4.2), sharex=True)
ax[0].plot((t[m] - 300e-9) * 1e9, clk[m], color=PAL[6], lw=0.8); ax[0].set(ylabel='CLK (V)', title=f'(a) Reference clock, {6*des.fm/1e6:.0f} MHz')
for k, (s, c, l) in enumerate(zip((ph0, ph120, ph240), PAL[:3], ('PH0', 'PH120', 'PH240'))):
    ax[1].plot((t[m] - 300e-9) * 1e9, s[m] + 1.6 * (2 - k), color=c, label=l)
ax[1].set(ylabel='Phase gen., offset (V)', title='(b) Johnson-counter outputs (0/120/240°)'); ax[1].legend(ncol=3, loc='upper right', fontsize=6)
for k, (s, c, l) in enumerate(zip((vt0, vt1, vt2), PAL[:3], ('V$_{G1}$', 'V$_{G2}$', 'V$_{G3}$'))):
    ax[2].plot((t[m] - 300e-9) * 1e9, s[m] + 1.6 * (2 - k), color=c, label=l)
ax[2].set(xlabel='Time (ns)', ylabel='Driver out, offset (V)', title='(c) Driver outputs at the switch gates'); ax[2].legend(ncol=3, loc='upper right', fontsize=6)
fig.tight_layout(); fig.savefig(os.path.join(FIG, 'fig_phasegen_waveforms.png')); fig.savefig(os.path.join(FIG, 'fig_phasegen_waveforms.pdf')); plt.close(fig)
# co-simulation waveforms
t, (vs, p1, p2, p3, g0, g1, g2, iddm, idd, vds, vm) = read_wrdata(os.path.join(WORK, 'wave_cmos.txt'), 11)
t0 = t[0]
fig, ax = plt.subplots(3, 1, figsize=(COL1, 4.8))
for i, g in enumerate((g0, g1, g2)):
    ax[0].plot((t - t0) * 1e9, g + 1.6 * (2 - i), color=PAL[i], label=f'V$_{{G{i+1}}}$')
ax[0].set(ylabel='Gate drives, offset (V)', title='(a) Three-phase CMOS gate drives'); ax[0].legend(ncol=3, loc='upper right', fontsize=6)
ax[0].set_xlim(0, 2.2 * Tm * 1e9)
for i, v in enumerate((p1, p2, p3)):
    ax[1].plot((t - t0) * 1e9, v, color=PAL[i], label=f'v$_{{P{i+1}}}$', lw=0.8)
ax[1].set(ylabel='Port voltage (V)', title='(b) Port voltages, 1-GHz tone injected at port 1'); ax[1].legend(ncol=3, loc='upper right', fontsize=6)
ax[1].set_xlim(0, 2.2 * Tm * 1e9)
for i, v in enumerate((p1, p2, p3)):
    ax[2].plot((t - t0) * 1e9, v, color=PAL[i], lw=0.9)
ax[0].set(xlabel='Time (ns)'); ax[1].set(xlabel='Time (ns)')
ax[2].set(xlabel='Time (ns)', ylabel='Port voltage (V)', title='(c) Zoom: transmitted port carries the signal, isolated port does not')
ax[2].set_xlim(0.5 * Tm * 1e9, 0.5 * Tm * 1e9 + 6)
fig.tight_layout(); fig.savefig(os.path.join(FIG, 'fig_waveforms.png')); fig.savefig(os.path.join(FIG, 'fig_waveforms.pdf')); plt.close(fig)
print('waveform figures regenerated')
