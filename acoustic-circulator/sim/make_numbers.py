"""Generate paper/numbers.tex (LaTeX macros) from the result JSON files so the manuscript stays consistent."""
import os, json, glob, math, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, 'results'); PAPER = os.path.join(ROOT, 'paper')
sys.path.insert(0, ROOT)


def J(name, default=None):
    p = os.path.join(RES, name)
    return json.load(open(p)) if os.path.exists(p) else default


def main():
    from sim.load_design import load_design
    des, d = load_design()
    ltp = J('ltp_summary.json', {}); ng = J('ngspice_summary.json', {}); cmt = J('cmt_design_rules.json', {})
    proj = J('projection_table.json', []); pw = J('power_handling.json', {}); stress = J('ngspice_stress.json', {})
    lay = json.load(open(os.path.join(ROOT, 'layout', 'layout_stats.json'))) if os.path.exists(os.path.join(ROOT, 'layout', 'layout_stats.json')) else {}
    r, sw = des.res, des.sw
    missing = []
    def f(x, n=2, _m=missing):
        if x == x:
            return ('%.' + str(n) + 'f') % x
        _m.append(1); return '0.00'
    M = {}
    M['fop'] = f(d.get('f0', 1.0e9) / 1e9, 3)
    M['fs'] = f(r.fs / 1e6, 1); M['Cnought'] = f(r.C0 * 1e12, 2); M['Cm'] = f(r.Cm * 1e12, 2); M['Cratio'] = f(r.Cm / r.C0, 2)
    M['kt'] = f(r.kt2 * 100, 1); M['Qm'] = str(int(r.Qm)); M['Lm'] = f(r.Lm * 1e9, 1); M['Rm'] = f(r.Rm, 2)
    M['fp'] = f(r.fp / 1e6, 1)
    M['Csh'] = f(des.Cp * 1e12, 2); M['Csw'] = f(sw.Csw * 1e12, 2); M['Cpar'] = f(sw.Cpar * 1e12, 2); M['Wsw'] = f(sw.W, 0)
    M['Ron'] = f(sw.Ron, 2); M['Coff'] = f(sw.Coff * 1e15, 0); M['Qsw'] = f(sw.Qon, 0)
    M['xratio'] = f(r.Cm / sw.Csw, 2)
    M['fm'] = f(des.fm / 1e6, 1); M['fclk'] = f(6 * des.fm / 1e6, 0); M['clockratio'] = f(d.get('f0', 1e9) / (6 * des.fm), 1)
    # ngspice
    M['ILdB'] = f(ng.get('IL_dB', float('nan'))); M['ISOdB'] = f(ng.get('ISO_dB', float('nan')), 1); M['RLdB'] = f(ng.get('RL_dB', float('nan')), 1)
    M['IMup'] = f(ng.get('IM_up_S21_dB', float('nan')), 1); M['IMdn'] = f(ng.get('IM_dn_S21_dB', float('nan')), 1)
    M['Pmod'] = f(ng.get('P_vddm_mW', float('nan')), 3); M['Pcore'] = f(ng.get('P_vdd_mW', float('nan')), 3)
    M['Pmodtot'] = f(ng.get('P_vddm_mW', 0) + ng.get('P_vdd_mW', 0), 2)
    pg = ng.get('phasegen', {})
    M['phasetwo'] = f(pg.get('phase_ch2_deg', float('nan')), 1); M['phasethree'] = f(pg.get('phase_ch3_deg', float('nan')), 1)
    M['phaseerr'] = f(max(abs(pg.get('phase_ch2_deg', 120) - 120), abs(pg.get('phase_ch3_deg', 240) - 240)) + 0.05, 1)
    M['trise'] = f(pg.get('trise_ns', float('nan')), 2); M['trisepct'] = f(100 * pg.get('trise_ns', 0) * 1e-9 * des.fm, 1)
    M['agreeIL'] = f(abs(ng.get('IL_dB', 0) - ng.get('LTP_IL_dB', 0)) + 0.005, 2); M['agreeISO'] = f(abs(ng.get('ISO_dB', 0) - ng.get('LTP_ISO_dB', 0)) + 0.05, 1)
    M['idealIL'] = f(ng.get('ideal_IL_dB', float('nan'))); M['idealISO'] = f(ng.get('ideal_ISO_dB', float('nan')), 1)
    # best isolation point of the transistor-level sweep (CMOS drivers)
    import csv
    best = None
    pcsv = os.path.join(RES, 'sparams_ngspice.csv')
    if os.path.exists(pcsv):
        for row in csv.DictReader(open(pcsv)):
            if row['driver'] != 'cmos': continue
            rev = max(float(row['S12_dB']), float(row['S23_dB']), float(row['S31_dB'])); fwd = max(float(row['S21_dB']), float(row['S32_dB']), float(row['S13_dB']))
            if -fwd > 8.0: continue      # in-band points only (worst-path IL < 8 dB)
            if best is None or -rev > best[1]: best = (float(row['f_Hz']), -rev, -fwd)
    M['ngbestf'] = f(best[0] / 1e6, 0) if best else '0'; M['ngbestiso'] = f(best[1], 1) if best else '0'; M['ngbestil'] = f(best[2], 2) if best else '0'
    M['BWisong'] = f(ng.get('BW_iso20_MHz_ngspice', float('nan')), 0)
    # ltp
    M['ILltp'] = f(ltp.get('IL_dB', float('nan'))); M['ISOltp'] = f(ltp.get('ISO_dB', float('nan')), 1); M['RLltp'] = f(ltp.get('RL_dB', float('nan')), 1)
    M['BWiso'] = f(ltp.get('BW_iso20_MHz', float('nan')), 2); M['BWisofifteen'] = f(ltp.get('BW_iso15_MHz', float('nan')), 2)
    M['BWil'] = f(ltp.get('BW_il1dB_MHz', float('nan')), 2); M['BWrl'] = f(ltp.get('BW_rl10_MHz', float('nan')), 2)
    M['revIL'] = f(ltp.get('reverse_ISO_dB', float('nan'))); M['revISO'] = f(ltp.get('reverse_IL_dB', float('nan')), 1)   # with the phase order swapped, the former isolated path carries the signal
    u = ltp.get('unmod', {})
    M['fdeg'] = f(u.get('f_deg_MHz', float('nan')), 1); M['Qload'] = f(u.get('Qloaded', float('nan')), 0); M['bwdeg'] = f(u.get('bw3dB_MHz', float('nan')), 1)
    M['Sunmod'] = f(u.get('S21_peak_dB', float('nan')), 1); M['Sunmodrl'] = f(-u.get('S11_peak_dB', float('nan')), 1)
    c = ltp.get('cmt', {})
    M['Qe'] = f(c.get('Qe', float('nan')), 0); M['Qi'] = f(c.get('Qi', float('nan')), 0); M['kappaMHz'] = f(c.get('kappa_Hz', 0) / 1e6, 1)
    M['dfMHz'] = f(c.get('dw_Hz', 0) / 1e6, 1); M['dfused'] = f(c.get('dw_used_Hz', 0) / 1e6, 1); M['slope'] = f(abs(c.get('slope_MHz_per_pF', float('nan'))), 1)
    ge = c.get('ge_Hz', 1.0); gi = c.get('gi_Hz', 0.0)
    M['geMHz'] = f(ge / 1e6, 2); M['wmratio'] = f(des.fm / ge, 1); M['dwratio'] = f(c.get('dw_used_Hz', 0) / ge, 1); M['kratio'] = f(abs(c.get('kappa_Hz', 0)) / ge, 1)
    M['lossratio'] = f(gi / ge, 2); M['fomval'] = f(c.get('Qi', 0) * c.get('dw_used_Hz', 0) / c.get('f0_Hz', 1e9), 1)
    jm = ltp.get('cmt', {})
    on = jm.get('on', {}); off = jm.get('off', {})
    M['gzerophase'] = f(on.get('G0_phase_deg', float('nan')), 0); M['fonres'] = f(on.get('f_res_MHz', float('nan')), 1)
    M['geon'] = f(on.get('ge_MHz', float('nan')), 1); M['gion'] = f(on.get('gi_MHz', float('nan')), 1)
    M['Qeon'] = f(on.get('Qe', float('nan')), 0); M['Qion'] = f(on.get('Qi', float('nan')), 0)
    M['geoff'] = f(off.get('ge_MHz', float('nan')), 1); M['detoff'] = f(jm.get('detuning_off_MHz', float('nan')), 0)
    M['foffres'] = f(off.get('f_res_MHz', float('nan')), 1); M['goffmin'] = f(-off.get('Gmin_dB', float('nan')), 1)
    M['detoffhalf'] = f(jm.get('detuning_off_MHz', float('nan')) / 2, 0); M['lossratioon'] = f(on.get('loss_ratio', float('nan')), 2)
    M['cmtilpred'] = f(jm.get('cmt_IL_pred_dB', float('nan')), 1)
    M['tolfloor'] = f(ltp.get('tol_iso_floor_dB', 15.0), 0)
    M['phasetol'] = f(ltp.get('phase_tol_deg', float('nan')), 0); M['cswtol'] = f(ltp.get('csw_tol_pct', float('nan')), 0)
    M['Pmaxone'] = f(pw.get('Pmax_single_dBm', float('nan')), 1); M['Pmaxtwo'] = f(pw.get('Pmax_stack2_dBm', float('nan')), 1)
    M['vdspk'] = f(stress.get('vds_pk', float('nan')), 2); M['Pinng'] = f(stress.get('P_in_dBm', float('nan')), 1)
    pq = [e for e in proj if e['Qm'] == 1000 and e['ron_w'] == 269]; pb = [e for e in proj if e['Qm'] == 2000 and e['ron_w'] == 120]
    M['projILq'] = f(pq[0]['IL']) if pq else 'n/a'; M['projILbest'] = f(pb[0]['IL']) if pb else 'n/a'
    M['vdspkpervolt'] = f(pw.get('vpk_per_volt', float('nan')), 1)
    M['chanw'] = f(lay.get('core_channel_um', [0, 0])[0], 0); M['chanh'] = f(lay.get('core_channel_um', [0, 0])[1], 0)
    rows = []
    for wm, e in sorted(cmt.get('scan', {}).items(), key=lambda kv: float(kv[0])):
        rows.append(f"{float(wm):.0f} & {abs(e['kappa']):.1f} & {e['dw']:.2f} & {e['IL']:.2f} & {e['RL']:.1f} \\\\")
    M['cmtrows'] = '\n'.join(rows)
    prow = []
    for e in proj:
        prow.append(f"{e['Qm']} & {e['ron_w']} & {e['IL']:.2f} & {e['ISO']:.1f} & {e['RL']:.1f} & {e.get('BW_iso15_MHz', e.get('BW_iso20_MHz', 0)):.1f} \\\\")
    M['projrows'] = '\n'.join(prow)
    # topology / modulator comparison rows (same resonator Qm = 500)
    trows = []
    pv = J('polishC_varactor_Q500.json'); pa = J('search_A_varactor_Q500.json')
    if pa: trows.append(f"A: parallel loop & A-MOS varactor & {pa['IL']:.2f} & {pa['ISO']:.1f} & {pa['RL']:.1f} & {pa['x'][3]/1e6:.1f} \\\\")
    if pv: trows.append(f"C: junction & A-MOS varactor & {pv['IL']:.2f} & {pv['ISO']:.1f} & {pv['RL']:.1f} & {pv['y'][2]/1e6:.1f} \\\\")
    if ltp: trows.append(f"C: junction (this design) & switched MIM & {ltp['IL_dB']:.2f} & {ltp['ISO_dB']:.1f} & {ltp['RL_dB']:.1f} & {des.fm/1e6:.1f} \\\\")
    pq1 = [e for e in proj if e['Qm'] == 1000 and e['ron_w'] == 269]
    if pq1: trows.append(f"C: junction, $Q_m$=1000 & switched MIM & {pq1[0]['IL']:.2f} & {pq1[0]['ISO']:.1f} & {pq1[0]['RL']:.1f} & {des.fm/1e6:.1f} \\\\")
    M['toporows'] = '\n'.join(trows) if trows else '\\multicolumn{6}{c}{(search not run)}\\\\'
    M['varIL'] = f(pv['IL']) if pv else 'n/a'; M['varISO'] = f(pv['ISO'], 1) if pv else 'n/a'
    M['loopIL'] = f(pa['IL']) if pa else 'n/a'; M['loopISO'] = f(pa['ISO'], 1) if pa else 'n/a'
    M['swgain'] = f((pv['IL'] - ltp.get('IL_dB', float('nan'))) if pv else float('nan'), 1)
    with open(os.path.join(PAPER, 'numbers.tex'), 'w') as fh:
        for k, val in M.items():
            fh.write(f"\\newcommand{{\\{k}}}{{{val}}}\n")
    print('numbers.tex written with', len(M), 'macros;', len(missing), 'placeholders (0.00) for missing results')


if __name__ == '__main__':
    main()
