"""Design analysis with the LTP solver + CMT comparison for the series-mode wye / switched-MIM circulator.
Produces figures and CSV/JSON for the paper."""
import os, sys, json, csv
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim.circulator import Design, Resonator, Varactor, SwitchCap, sparams, build_network, cap_coeffs
from sim.ltp import db
from sim.cmt import cmt_sweep
from sim.topologies import figures_of_merit
from sim.load_design import load_design
from sim.plotstyle import plt, PAL, COL1, COL2
from scipy.optimize import least_squares
from dataclasses import replace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(ROOT, 'figures'); RES = os.path.join(ROOT, 'results')
F0 = 1.0e9


def fom(des, f0=F0, bw=60e6, npts=121, K=40):
    f = np.linspace(f0 - bw / 2, f0 + bw / 2, npts)
    S = sparams(des, f, K)[:, K]
    fwd = np.array([S[:, 1, 0], S[:, 2, 1], S[:, 0, 2]]); rev = np.array([S[:, 0, 1], S[:, 1, 2], S[:, 2, 0]])
    IL = -db(fwd).max(axis=0); ISO = -db(rev).min(axis=0)
    RL = -db(np.array([S[:, 0, 0], S[:, 1, 1], S[:, 2, 2]])).min(axis=0)
    i0 = np.argmin(np.abs(f - f0))
    def bw_of(mask):
        if not mask[i0]: return 0.0
        lo = i0
        while lo - 1 >= 0 and mask[lo - 1]: lo -= 1
        hi = i0
        while hi + 1 < len(f) and mask[hi + 1]: hi += 1
        return f[hi] - f[lo]
    return dict(f=f, IL=IL, ISO=ISO, RL=RL, IL0=IL[i0], ISO0=ISO[i0], RL0=RL[i0],
                BW_iso20=bw_of(ISO >= 20), BW_iso15=bw_of(ISO >= 15), BW_il1=bw_of(IL <= IL[i0] + 1.0), BW_rl10=bw_of(RL >= 10), S=S)


def fig_sparams(des):
    K = 40
    f = np.linspace(0.90e9, 1.10e9, 201)
    S = sparams(des, f, K)
    S0 = S[:, K]
    fig, ax = plt.subplots(1, 2, figsize=(COL2, 2.5))
    for (lab, m, n), c in zip([('S21', 1, 0), ('S32', 2, 1), ('S13', 0, 2)], PAL[:3]):
        ax[0].plot(f / 1e9, db(S0[:, m, n]), color=c, label=lab + ' (fwd)')
    for (lab, m, n), c in zip([('S12', 0, 1), ('S23', 1, 2), ('S31', 2, 0)], PAL[:3]):
        ax[0].plot(f / 1e9, db(S0[:, m, n]), color=c, ls='--', label=lab + ' (rev)')
    ax[0].plot(f / 1e9, db(S0[:, 0, 0]), color=PAL[6], ls=':', label='S11')
    ax[0].set(xlabel='Frequency (GHz)', ylabel='|S| (dB)', ylim=(-50, 2), title='(a) Fundamental-tone S-parameters (LTP/PSP)')
    ax[0].legend(ncol=2, loc='lower left')
    for k, ls in [(1, '-'), (-1, '--'), (2, ':'), (-2, '-.')]:
        ax[1].plot(f / 1e9, db(S[:, K + k, 1, 0]), color=PAL[0], ls=ls, label=f'port 2 @ f{k:+d}f$_m$')
        ax[1].plot(f / 1e9, db(S[:, K + k, 0, 0]), color=PAL[1], ls=ls, label=f'port 1 @ f{k:+d}f$_m$')
    ax[1].set(xlabel='Frequency (GHz)', ylabel='Conversion gain (dB)', ylim=(-80, 0), title='(b) Intermodulation sidebands (input at port 1)')
    ax[1].legend(ncol=2, fontsize=6, loc='lower left')
    fig.savefig(os.path.join(FIG, 'fig_sparams_ltp.png')); fig.savefig(os.path.join(FIG, 'fig_sparams_ltp.pdf')); plt.close(fig)
    with open(os.path.join(RES, 'sparams_ltp.csv'), 'w', newline='') as fh:
        w = csv.writer(fh); w.writerow(['f_Hz', 'S11_dB', 'S21_dB', 'S31_dB', 'S12_dB', 'S22_dB', 'S32_dB', 'S13_dB', 'S23_dB', 'S33_dB', 'S21_up_dB', 'S21_dn_dB'])
        for i, ff in enumerate(f):
            w.writerow([f'{ff:.6e}'] + [f'{db(S0[i, m, n]):.3f}' for n in range(3) for m in range(3)] + [f'{db(S[i, K + 1, 1, 0]):.3f}', f'{db(S[i, K - 1, 1, 0]):.3f}'])
    return f, S


def fig_unmodulated(des):
    """Unmodulated response: switches held ON (resonant junction) and held OFF."""
    f = np.linspace(0.90e9, 1.10e9, 801)
    fig, ax = plt.subplots(figsize=(COL1, 2.3))
    out = {}
    for state, ls, lab in (('on', '-', 'switches ON'), ('off', '--', 'switches OFF')):
        d0 = replace(des, waveform='dc_' + state)
        S = sparams(d0, f, 1)[:, 1]
        ax.plot(f / 1e9, db(S[:, 0, 0]), color=PAL[0], ls=ls, label='S11 ' + lab)
        ax.plot(f / 1e9, db(S[:, 1, 0]), color=PAL[1], ls=ls, label='S21 = S31 ' + lab)
        out[state] = S
    S = out['on']; i = int(np.argmax(np.abs(S[:, 1, 0])))
    t = np.abs(S[:, 1, 0]); half = t >= t[i] / np.sqrt(2)
    lo = i
    while lo > 0 and half[lo - 1]: lo -= 1
    hi = i
    while hi < len(f) - 1 and half[hi + 1]: hi += 1
    ax.set(xlabel='Frequency (GHz)', ylabel='|S| (dB)', ylim=(-40, 1), title='Unmodulated (reciprocal) junction')
    ax.legend(fontsize=6)
    fig.savefig(os.path.join(FIG, 'fig_unmodulated.png')); fig.savefig(os.path.join(FIG, 'fig_unmodulated.pdf')); plt.close(fig)
    return dict(f_deg_MHz=f[i] / 1e6, S21_peak_dB=float(db(S[i, 1, 0])), S11_peak_dB=float(db(S[i, 0, 0])), bw3dB_MHz=(f[hi] - f[lo]) / 1e6,
                Qloaded=f[i] / (f[hi] - f[lo]))


def junction_modes(des):
    """Eigenmode picture of the junction: reflection coefficients of the l=0 and l=+-1 excitations in the two switch
    states, single-pole CMT fit of the l=+-1 mode (gamma_e, gamma_i) in each state, and the loss ratio gamma_i/gamma_e."""
    f = np.linspace(0.92e9, 1.08e9, 641)
    S = {'on': sparams(replace(des, waveform='dc_on'), f, 1)[:, 1], 'off': sparams(replace(des, waveform='dc_off'), f, 1)[:, 1]}
    w = np.exp(1j * 2 * np.pi / 3)
    def eig(Sx, l):
        return Sx[:, 0, 0] + Sx[:, 0, 1] * w ** l + Sx[:, 0, 2] * w ** (-l)
    fit = {}
    fig, ax = plt.subplots(1, 2, figsize=(COL2, 2.5))
    for state, ls in (('on', '-'), ('off', '--')):
        G1 = eig(S[state], 1); G0 = eig(S[state], 0)
        def model(x):
            w0, gi, ge = x
            return -1 + 2 * ge / (1j * (2 * np.pi * f - w0) + gi + ge)
        def resid(x):
            m = model(x); return np.concatenate([(m - G1).real, (m - G1).imag])
        i = int(np.argmin(np.abs(G1)))
        sol = least_squares(resid, [2 * np.pi * f[i], 2 * np.pi * 2e6, 2 * np.pi * 10e6], x_scale=[1e8, 1e7, 1e7])
        w0, gi, ge = sol.x
        fit[state] = dict(f_res_MHz=w0 / 2 / np.pi / 1e6, ge_MHz=ge / 2 / np.pi / 1e6, gi_MHz=gi / 2 / np.pi / 1e6,
                          Qe=w0 / (2 * ge), Qi=w0 / (2 * gi), loss_ratio=gi / ge, G0_mag_at_f0=float(np.abs(G0[np.argmin(np.abs(f - F0))])),
                          G0_phase_deg=float(np.degrees(np.angle(G0[np.argmin(np.abs(f - F0))]))))
        ax[0].plot(f / 1e9, db(G1), color=PAL[0], ls=ls, label=f'|$\\Gamma_{{\\pm1}}$| switches {state}')
        ax[0].plot(f / 1e9, db(G0), color=PAL[1], ls=ls, label=f'|$\\Gamma_0$| switches {state}')
        ax[1].plot(f / 1e9, np.degrees(np.unwrap(np.angle(G1))), color=PAL[0], ls=ls, label=f'arg $\\Gamma_{{\\pm1}}$ {state}')
        ax[1].plot(f / 1e9, np.degrees(np.unwrap(np.angle(G0))), color=PAL[1], ls=ls, label=f'arg $\\Gamma_0$ {state}')
    ax[0].set(xlabel='Frequency (GHz)', ylabel='|$\\Gamma_l$| (dB)', ylim=(-25, 1), title='(a) Eigenmode reflection magnitude'); ax[0].legend(fontsize=6)
    ax[1].set(xlabel='Frequency (GHz)', ylabel='Phase (deg)', title='(b) Eigenmode reflection phase'); ax[1].legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, 'fig_junction_modes.png')); fig.savefig(os.path.join(FIG, 'fig_junction_modes.pdf')); plt.close(fig)
    # CMT loss-curve prediction for the on-state loss ratio (lossless IL subtracted): interpolate the CMT loss table
    rules = json.load(open(os.path.join(RES, 'cmt_design_rules.json'))) if os.path.exists(os.path.join(RES, 'cmt_design_rules.json')) else None
    if rules:
        xs = sorted(float(k) for k in rules['loss']); ys = [rules['loss'][str(k) if str(k) in rules['loss'] else repr(k)]['IL'] for k in xs] if False else None
        keys = sorted(rules['loss'].keys(), key=float); xs = [float(k) for k in keys]; ys = [rules['loss'][k]['IL'] for k in keys]
        fit['cmt_IL_pred_dB'] = float(np.interp(fit['on']['loss_ratio'], xs, ys))
    fit['detuning_off_MHz'] = fit['off']['f_res_MHz'] - fit['on']['f_res_MHz']
    json.dump(fit, open(os.path.join(RES, 'junction_modes.json'), 'w'), indent=1)
    return fit


def fig_design_space(des):
    """Sweeps around the design point: switch width, switched capacitance, pump frequency, resonator Q, switch Ron*W."""
    fig, ax = plt.subplots(2, 2, figsize=(COL2, 4.4))
    sw = des.sw
    def plot3(a, x, r, xlabel, title, xv, log=False):
        fn = a.semilogx if log else a.plot
        fn(x, [v['IL0'] for v in r], label='IL @ f$_0$')
        fn(x, [v['ISO0'] for v in r], label='ISO @ f$_0$')
        fn(x, [v['RL0'] for v in r], label='RL @ f$_0$', color=PAL[6])
        fn(x, [v['BW_iso20'] / 1e6 for v in r], label='20-dB ISO BW (MHz)', color=PAL[3])
        a.axvline(xv, color='k', lw=0.6, ls=':')
        a.set(xlabel=xlabel, ylabel='dB / MHz', title=title, ylim=(0, 45)); a.legend(fontsize=6)
    Ws = np.array([200, 300, 450, 650, 900, 1300, 1800, 2500])
    r = [fom(replace(des, sw=replace(sw, W=w)), K=16, npts=61) for w in Ws]
    plot3(ax[0, 0], Ws, r, 'Switch width W (µm)', '(a) Switch width (R$_{on}$, C$_{off}$)', sw.W, log=True)
    Cs = np.linspace(0.5, 2.0, 13) * sw.Csw
    r = [fom(replace(des, sw=replace(sw, Csw=c)), K=16, npts=61) for c in Cs]
    plot3(ax[0, 1], Cs * 1e12, r, 'Switched capacitance C$_{sw}$ (pF)', '(b) Switched capacitance', sw.Csw * 1e12)
    fms = np.array([5, 10, 15, 20, 25, 30, 35, 40, 50, 60, 80]) * 1e6
    r = [fom(replace(des, fm=v), K=16, npts=61) for v in fms]
    plot3(ax[1, 0], fms / 1e6, r, 'Pump frequency f$_m$ (MHz)', '(c) Pump frequency', des.fm / 1e6)
    Qs = np.array([150, 250, 350, 500, 700, 1000, 1500, 2500])
    r = [fom(replace(des, res=replace(des.res, Qm=q)), K=16, npts=61) for q in Qs]
    plot3(ax[1, 1], Qs, r, 'Resonator motional Q$_m$', '(d) Resonator quality factor', des.res.Qm, log=True)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, 'fig_design_space.png')); fig.savefig(os.path.join(FIG, 'fig_design_space.pdf')); plt.close(fig)
    # projection table: Qm x switch Ron*W
    proj = []
    for Qm in (500, 1000, 2000):
        for ronw in (277, 150, 75):
            rr = fom(replace(des, res=replace(des.res, Qm=Qm), sw=replace(sw, ron_w=ronw)), K=16, npts=61)
            proj.append(dict(Qm=Qm, ron_w=ronw, IL=rr['IL0'], ISO=rr['ISO0'], RL=rr['RL0'], BW_iso20_MHz=rr['BW_iso20'] / 1e6))
    json.dump(proj, open(os.path.join(RES, 'projection_table.json'), 'w'), indent=1)
    return proj


def fig_waveform_and_mismatch(des):
    fig, ax = plt.subplots(1, 2, figsize=(COL2, 2.5))
    f = np.linspace(0.96e9, 1.04e9, 81)
    for rg, lab, c in ((1000.0, 'R$_g$ = 1 kΩ (fast gate)', PAL[0]), (3000.0, 'R$_g$ = 3 kΩ (design)', PAL[1]), (10000.0, 'R$_g$ = 10 kΩ (slow gate)', PAL[2])):
        d = replace(des, waveform='rc', sw=replace(des.sw, Rg=rg))
        S = sparams(d, f, 32)[:, 32]
        ax[0].plot(f / 1e9, db(S[:, 1, 0]), color=c, label='S21 ' + lab)
        ax[0].plot(f / 1e9, db(S[:, 0, 1]), color=c, ls='--')
    ax[0].set(xlabel='Frequency (GHz)', ylabel='|S| (dB)', ylim=(-50, 1), title='(a) Gate-edge (R$_g$C$_g$) sensitivity (solid S21, dashed S12)'); ax[0].legend(fontsize=6)
    def with_err(dphi_deg, dcsw):
        d = replace(des, phase_err_deg=(0.0, dphi_deg, 0.0), csw_scale=(1.0, 1.0 + dcsw, 1.0))
        S = sparams(d, np.array([F0]), 32)[0, 32]
        IL, ISO, RL, _ = figures_of_merit(S[None])
        return IL[0], ISO[0]
    dphis = np.linspace(-10, 10, 11)
    r = [with_err(p_, 0.0) for p_ in dphis]
    ax[1].plot(dphis, [x[1] for x in r], color=PAL[0], label='worst ISO vs phase error of ch. 2')
    ax[1].plot(dphis, [x[0] for x in r], color=PAL[0], ls='--', label='worst IL vs phase error')
    dcs = np.linspace(-0.1, 0.1, 11)
    r2 = [with_err(0.0, a) for a in dcs]
    ax2 = ax[1].twiny()
    ax2.plot(dcs * 100, [x[1] for x in r2], color=PAL[1], label='worst ISO vs C$_{sw}$ error of ch. 2')
    ax2.plot(dcs * 100, [x[0] for x in r2], color=PAL[1], ls='--', label='worst IL vs C$_{sw}$ error')
    ax2.set_xlabel('C$_{sw}$ mismatch of channel 2 (%)', color=PAL[1]); ax2.grid(False)
    ax[1].set(xlabel='Phase error of channel 2 (deg)', ylabel='dB', title='(b) Pump / element mismatch at f$_0$', ylim=(0, 45))
    h1, l1 = ax[1].get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax[1].legend(h1 + h2, l1 + l2, fontsize=6, loc='upper right')
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, 'fig_waveform_mismatch.png')); fig.savefig(os.path.join(FIG, 'fig_waveform_mismatch.pdf')); plt.close(fig)
    iso_ph = np.array([x[1] for x in r]); iso_c = np.array([x[1] for x in r2])
    tol_ph = float(np.max(np.abs(dphis[iso_ph >= 20]))) if np.any(iso_ph >= 20) else 0.0
    tol_c = float(np.max(np.abs(dcs[iso_c >= 20]))) * 100 if np.any(iso_c >= 20) else 0.0
    return tol_ph, tol_c


def power_handling(des):
    """Voltage across the OFF switch per unit incident wave; limits for |Vds| < 1.2 V (single) and 2.4 V (stacked x2)."""
    K = 40
    net = build_network(des, K)
    S, V = net.solve(F0, des.fm, K, return_voltages=True)
    # node 10 (V1, after Ron) to star (13): voltage across the modulated element of branch 1 for a 1-V source at port 1
    v_el = V[0][9] - V[0][12]
    # time-domain peak over the pump period (sum of harmonics; conservative: sum of magnitudes)
    vpk_per_volt = np.sum(np.abs(v_el))              # peak voltage per 1 V source amplitude
    a_per_volt = 1.0 / (2 * np.sqrt(des.z0))         # incident wave per 1 V source
    pin_per_volt = a_per_volt ** 2                    # W per V^2 (peak amplitude -> available power = |a|^2/2 for sinusoid amplitude)
    pin_per_volt = (1.0 ** 2) / (8 * des.z0)           # available power for 1 V amplitude source: V^2/(8 R0)
    vmax1 = 1.2; vmax2 = 2.4
    p1 = pin_per_volt * (vmax1 / vpk_per_volt) ** 2; p2 = pin_per_volt * (vmax2 / vpk_per_volt) ** 2
    out = dict(vpk_per_volt=float(vpk_per_volt), Pmax_single_dBm=float(10 * np.log10(p1 / 1e-3)), Pmax_stack2_dBm=float(10 * np.log10(p2 / 1e-3)))
    json.dump(out, open(os.path.join(RES, 'power_handling.json'), 'w'), indent=1)
    return out


def main():
    des, p = load_design()
    r = fom(des)
    summary = dict(IL_dB=r['IL0'], ISO_dB=r['ISO0'], RL_dB=r['RL0'], BW_iso20_MHz=r['BW_iso20'] / 1e6, BW_iso15_MHz=r['BW_iso15'] / 1e6,
                   BW_il1dB_MHz=r['BW_il1'] / 1e6, BW_rl10_MHz=r['BW_rl10'] / 1e6)
    f, S = fig_sparams(des)
    K = 24; i0 = np.argmin(np.abs(f - F0))
    summary['IM_up_S21_dB'] = float(db(S[i0, K + 1, 1, 0])); summary['IM_dn_S21_dB'] = float(db(S[i0, K - 1, 1, 0]))
    summary['IM_up_S11_dB'] = float(db(S[i0, K + 1, 0, 0])); summary['IM_dn_S11_dB'] = float(db(S[i0, K - 1, 0, 0]))
    rr = fom(replace(des, direction=-des.direction))
    summary['reverse_IL_dB'] = rr['IL0']; summary['reverse_ISO_dB'] = rr['ISO0']
    summary['unmod'] = fig_unmodulated(des)
    summary['cmt'] = junction_modes(des)
    summary['projection'] = fig_design_space(des)
    tol_ph, tol_c = fig_waveform_and_mismatch(des)
    summary['phase_tol_deg'] = tol_ph; summary['csw_tol_pct'] = tol_c
    summary['power'] = power_handling(des)
    json.dump(summary, open(os.path.join(RES, 'ltp_summary.json'), 'w'), indent=1)
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
