#!/usr/bin/env python3
"""
postlayout.py -- post-layout simulation of the GAA3 cells with the extracted parasitics (verify/*.pex.json).

Pre-layout runs used lumped placeholders (C_in = 0.32 fF, C_par = 0.35 fF, C_X = 0.15 fF, no wire R).
Post-layout: the intrinsic gate capacitance C_ox W_eff L_g stays in the device, and every parasitic comes
from the extraction: gate-to-source coupling of the driven cells (to ground), gate-to-drain coupling
applied exactly through d(V_in - V_out)/dt on the driver and with a Miller factor of 2 on the loads,
contact/metal capacitance of the output net, and half the extracted net resistance between the driver
and its load (two-node RC).  Writes results_postlayout.json and the pre/post waveforms.
"""
import json, math, os, sys
import ref_model as rm, nand2 as nd, ro as rosc
V = rm.VDD
HERE = os.path.dirname(os.path.abspath(__file__)); PEX = os.path.join(HERE, "..", "verify")
EOT = 0.9e-9; COX = 3.9 * 8.854e-12 / EOT                     # F/m^2
LG = 14e-9
def cg_int(weff_nm_list): return sum(COX * LG * w * 1e-9 for w in weff_nm_list)   # intrinsic gate cap
CG_INV = cg_int([210, 300]); CG_NAND = cg_int([300, 210])       # per input, F

def pex(name): return json.load(open(os.path.join(PEX, name + ".pex.json")))
aF = 1e-18

def load_cap_inv(p):
    """input capacitance of one INV_GAA_X1 as a load, post-layout: intrinsic + gate-source (gnd) + 2 x gate-drain (Miller)"""
    A = p["nets"]["A"]; return CG_INV + A["cgnd_aF"] * aF + 2 * A["coup_aF"].get("Y", 0) * aF

def tran_inv(cl, cout, ccoup, rout, tr=12e-12, tstop=80e-12, dt=2e-15):
    """Driver output node (C_out, coupling C_c to the input) -> R_out -> load node (C_L)."""
    t0, t1 = 10e-12, 45e-12; ramp = tr / 0.8
    def vin_t(t):
        if t < t0: return 0.0
        if t < t0 + ramp: return V * (t - t0) / ramp
        if t < t1: return V
        if t < t1 + ramp: return V * (1 - (t - t1) / ramp)
        return 0.0
    t, vo, vl = 0.0, V, V; ts, vins, vouts, vloads = [], [], [], []; e = 0.0; k = 0; vin_prev = 0.0
    while t <= tstop:
        vi = vin_t(t); dvin = (vi - vin_prev) / dt; vin_prev = vi
        ip, inn = rm.i_p(vi, vo), rm.i_n(vi, vo)
        ir = (vo - vl) / rout if rout > 0 else 0.0
        if rout > 0:
            vo += dt * (ip - inn - ir + ccoup * dvin) / (cout + ccoup)
            vl += dt * ir / cl
        else:
            vo += dt * (ip - inn + ccoup * dvin) / (cout + ccoup + cl); vl = vo
        vo = min(max(vo, -0.05), V + 0.05); vl = min(max(vl, -0.05), V + 0.05)
        e += ip * V * dt
        if k % 25 == 0: ts.append(t); vins.append(vi); vouts.append(vo); vloads.append(vl)
        t += dt; k += 1
    def cross(sig, level, rising, tstart):
        for i in range(1, len(ts)):
            if ts[i] < tstart: continue
            a, b = sig[i - 1], sig[i]
            if (rising and a < level <= b) or (not rising and a > level >= b):
                return ts[i - 1] + (level - a) / (b - a) * (ts[i] - ts[i - 1])
        return float("nan")
    h = V / 2
    tphl = cross(vloads, h, False, t0) - cross(vins, h, True, t0); tplh = cross(vloads, h, True, t1) - cross(vins, h, False, t1)
    return dict(tpHL=tphl, tpLH=tplh, tpd=0.5 * (tphl + tplh), E_cycle=e - 0.5 * (rm.i_n(0, V) + rm.i_p(V, 0)) * V * tstop,
                wave=dict(t=ts, vin=vins, vout=vloads))

def tran_nand(mode, cl, cout, cc_a, cc_b, cx, rout, tr=12e-12, tstop=80e-12, dt=2e-15):
    t0, t1 = 10e-12, 45e-12; ramp = tr / 0.8
    def stim(t):
        if t < t0: return 0.0
        if t < t0 + ramp: return V * (t - t0) / ramp
        if t < t1: return V
        if t < t1 + ramp: return V * (1 - (t - t1) / ramp)
        return 0.0
    vy, vx, vl = V, V - 0.05, V; t = 0.0; k = 0; ts, vin, vout = [], [], []; e = 0.0; sprev = 0.0
    while t <= tstop:
        s = stim(t); ds = (s - sprev) / dt; sprev = s
        va = s if mode == "A" else V; vb = s if mode == "B" else V
        cc = cc_a if mode == "A" else cc_b; cgnd_extra = cc_b if mode == "A" else cc_a       # static input's coupling -> ground
        ip = nd.i_p(va, vy) + nd.i_p(vb, vy); ia = nd.i_n(va, 0.0, vx); ib = nd.i_n(vb, vx, vy)
        ir = (vy - vl) / rout
        vy += dt * (ip - ib - ir + cc * ds) / (cout + cc + cgnd_extra)
        vl += dt * ir / cl
        vx += dt * (ib - ia) / cx
        vy = min(max(vy, -0.05), V + 0.05); vx = min(max(vx, -0.05), V + 0.05); vl = min(max(vl, -0.05), V + 0.05)
        e += ip * V * dt
        if k % 25 == 0: ts.append(t); vin.append(s); vout.append(vl)
        t += dt; k += 1
    def cross(sig, level, rising, tstart):
        for i in range(1, len(ts)):
            if ts[i] < tstart: continue
            a, b = sig[i - 1], sig[i]
            if (rising and a < level <= b) or (not rising and a > level >= b):
                return ts[i - 1] + (level - a) / (b - a) * (ts[i] - ts[i - 1])
        return float("nan")
    h = V / 2
    tphl = cross(vout, h, False, t0) - cross(vin, h, True, t0); tplh = cross(vout, h, True, t1) - cross(vin, h, False, t1)
    return dict(tpHL=tphl, tpLH=tplh, tpd=0.5 * (tphl + tplh), E_cycle=e, wave=dict(t=ts, vin=vin, vout=vout))

def ro_post(cnode, ccoup, rnet, cdrv_frac=0.3, n=11, vdd=V, tstop=600e-12, dt=8e-15):
    """Ring with two nodes per net: driver side (fraction cdrv_frac of C, contacts/M1) -> R -> receiver side (rest, + loads).
    Adjacent-node coupling ccoup (gate-drain of the next stage) applied explicitly with the previous step's slopes."""
    rm.VDD = vdd
    cd = cdrv_frac * cnode; cr = (1 - cdrv_frac) * cnode
    vd = [vdd if i % 2 else 0.0 for i in range(n)]; vr = vd[:]; vd[0] = vdd * 0.45; vr[0] = vd[0]
    slope = [0.0] * n; t = 0.0; step = 0; ts, v0, idd = [], [], []
    while t <= tstop:
        nvd, nvr, nslope = vd[:], vr[:], slope[:]; ipsum = 0.0
        for i in range(n):
            vin = vr[i - 1]
            ip = rm.i_p(vin, vd[i]); inn = rm.i_n(vin, vd[i]); ipsum += ip
            ir = (vd[i] - vr[i]) / rnet
            dvd = (ip - inn - ir) / cd
            # receiver node i is coupled to the driver node of stage i+1 (its gate-drain capacitance)
            dvr = (ir + ccoup * slope[(i + 1) % n]) / (cr + ccoup)
            nvd[i] = min(max(vd[i] + dt * dvd, -0.05), vdd + 0.05); nvr[i] = min(max(vr[i] + dt * dvr, -0.05), vdd + 0.05)
            nslope[i] = dvd
        vd, vr, slope = nvd, nvr, nslope
        if step % 10 == 0: ts.append(t); v0.append(vr[0]); idd.append(ipsum)
        t += dt; step += 1
    half = vdd / 2; cr_ = []
    for k in range(1, len(ts)):
        if ts[k] > tstop / 2 and v0[k - 1] < half <= v0[k]:
            cr_.append(ts[k - 1] + (half - v0[k - 1]) / (v0[k] - v0[k - 1]) * (ts[k] - ts[k - 1]))
    T = (cr_[-1] - cr_[0]) / (len(cr_) - 1)
    sel = [k for k in range(len(ts)) if cr_[0] <= ts[k] <= cr_[-1]]
    p = sum(idd[k] for k in sel) / len(sel) * vdd
    rm.VDD = V
    return dict(f_Hz=1 / T, T_s=T, t_stage_s=T / (2 * n), P_W=p, wave=dict(t=[round(x * 1e12, 3) for x in ts], v0=[round(x, 4) for x in v0]))

if __name__ == "__main__":
    pi, pn, pr, ps = pex("gaa_inverter"), pex("gaa_nand2"), pex("gaa_ro11"), pex("gaa_sram6t")
    # ---- inverter
    cin_post = load_cap_inv(pi)
    Y = pi["nets"]["Y"]; cout = Y["cgnd_aF"] * aF; cc = Y["coup_aF"].get("A", 0) * aF; rout = 0.5 * Y["r_ohm"]
    pre = rm.transient(cl=4 * 0.32e-15)
    post = tran_inv(4 * cin_post, cout, cc, rout)
    post_noR = tran_inv(4 * cin_post, cout, cc, 0.0)                     # same capacitances, no wire resistance
    inv = dict(Cin_pre_fF=0.32, Cin_post_fF=cin_post * 1e15, Cg_int_fF=CG_INV * 1e15, Cout_pre_fF=0.35, Cout_post_fF=(cout + cc) * 1e15,
               Ccoup_AY_fF=cc * 1e15, Rout_ohm=rout, load_pre_fF=4 * 0.32, load_post_fF=4 * cin_post * 1e15,
               R_delay_pct=(post["tpd"] / post_noR["tpd"] - 1) * 100,
               pre={k: pre[k] for k in ("tpHL", "tpLH", "tpd", "E_cycle")}, post={k: post[k] for k in ("tpHL", "tpLH", "tpd", "E_cycle")},
               wave_pre=dict(t=[x * 1e12 for x in pre["wave"]["t"]], vin=pre["wave"]["vin"], vout=pre["wave"]["vout"]),
               wave_post=dict(t=[x * 1e12 for x in post["wave"]["t"]], vin=post["wave"]["vin"], vout=post["wave"]["vout"]))
    # ---- NAND2 (loads: four NAND2 inputs, Miller x2 on their gate-drain coupling)
    A, Bn, Yn = pn["nets"]["A"], pn["nets"]["B"], pn["nets"]["Y"]
    X = next(v for k, v in pn["nets"].items() if k.startswith("int"))
    cin_nand = CG_NAND + A["cgnd_aF"] * aF + 2 * A["coup_aF"].get("Y", 0) * aF
    cout_n = Yn["cgnd_aF"] * aF + Yn["coup_aF"].get(next(k for k in pn["nets"] if k.startswith("int")), 0) * aF
    cx = X["cgnd_aF"] * aF + (X["coup_aF"].get("A", 0) + X["coup_aF"].get("B", 0)) * aF
    ta_pre, tb_pre = nd.transient("A", 4 * nd.CIN), nd.transient("B", 4 * nd.CIN)
    ta = tran_nand("A", 4 * cin_nand, cout_n, Yn["coup_aF"].get("A", 0) * aF, Yn["coup_aF"].get("B", 0) * aF, cx, 0.5 * Yn["r_ohm"])
    tb = tran_nand("B", 4 * cin_nand, cout_n, Yn["coup_aF"].get("A", 0) * aF, Yn["coup_aF"].get("B", 0) * aF, cx, 0.5 * Yn["r_ohm"])
    nand = dict(Cin_post_fF=cin_nand * 1e15, Cout_post_fF=cout_n * 1e15, CX_post_fF=cx * 1e15, Rout_ohm=0.5 * Yn["r_ohm"],
                pre=dict(A={k: ta_pre[k] for k in ("tpHL", "tpLH", "tpd", "E_cycle")}, B={k: tb_pre[k] for k in ("tpHL", "tpLH", "tpd", "E_cycle")}),
                post=dict(A={k: ta[k] for k in ("tpHL", "tpLH", "tpd", "E_cycle")}, B={k: tb[k] for k in ("tpHL", "tpLH", "tpd", "E_cycle")}))
    # ---- RO11 (stage-averaged extracted net: driver contacts + M2 stub + next stage's gate parasitics; FO3 with two dummy loads)
    sig = [v for k, v in pr["nets"].items() if k.startswith("int") or k == "OUT"]
    cg_avg = sum(v["cgnd_aF"] for v in sig) / len(sig) * aF
    cc_avg = sum(sum(v["coup_aF"].values()) for v in sig) / len(sig) / 2 * aF     # coupling to the adjacent node (counted once)
    r_avg = sum(v["r_ohm"] for v in sig) / len(sig)
    cnode = cg_avg + CG_INV + 2 * cin_post                                        # + real load intrinsic + 2 dummy loads
    ro_pre = json.load(open(os.path.join(HERE, "results_ro.json")))["nominal"]
    ro_po = ro_post(cnode, cc_avg, 0.5 * r_avg)
    ro = dict(Cnode_pre_fF=rosc.C_NODE * 1e15, Cnode_post_fF=(cnode + cc_avg) * 1e15, Cnet_extracted_fF=cg_avg * 1e15, Ccoup_fF=cc_avg * 1e15, Rnet_ohm=r_avg,
              pre=dict(f_Hz=ro_pre["f_Hz"], t_stage_s=ro_pre["t_stage_s"], P_W=ro_pre["P_W"]),
              post={k: ro_po[k] for k in ("f_Hz", "t_stage_s", "P_W")}, wave_post=ro_po["wave"], wave_pre=ro_pre["wave"])
    # ---- SRAM: bit-line and word-line loading from the extracted cell
    sr = json.load(open(os.path.join(HERE, "results_sram6t.json")))
    BL, WL, Q = ps["nets"]["BL"], ps["nets"]["WL"], ps["nets"]["Q"]
    c_bl_cell = BL["ctotal_aF"] * aF; c_wl_cell = WL["ctotal_aF"] * aF
    r_wl_cell = sum(r for n, r in WL["elems"] if n == "M3")            # only the M3 line segment is in series along the row
    r_bl_cell = sum(r for n, r in BL["elems"] if n == "M2")
    i_read = sr["I_read_uA"] * 1e-6
    sram = dict(C_BL_cell_fF=c_bl_cell * 1e15, C_WL_cell_fF=c_wl_cell * 1e15, R_WL_cell_ohm=r_wl_cell, R_BL_cell_ohm=r_bl_cell, C_Q_fF=Q["ctotal_aF"] * 1e-3,
                cells_per_BL=256, cells_per_WL_segment=64, dV_sense_V=0.1,
                t_BL_100mV_ps=0.1 * 256 * c_bl_cell / i_read * 1e12,
                t_WL_elmore_ps=0.5 * 64 ** 2 * r_wl_cell * c_wl_cell * 1e12)
    out = dict(inverter=inv, nand2=nand, ro11=ro, sram=sram)
    json.dump(out, open(os.path.join(HERE, "results_postlayout.json"), "w"), indent=1)
    print("INV   Cin %.3f -> %.3f fF   Cout %.3f -> %.3f fF   R_out %.0f ohm   tpd %.2f -> %.2f ps   E %.2f -> %.2f fJ" % (
        inv["Cin_pre_fF"], inv["Cin_post_fF"], inv["Cout_pre_fF"], inv["Cout_post_fF"], rout, pre["tpd"] * 1e12, post["tpd"] * 1e12, pre["E_cycle"] * 1e15, post["E_cycle"] * 1e15))
    print("NAND2 worst tpd A/B pre %.2f/%.2f -> post %.2f/%.2f ps" % (max(ta_pre["tpHL"], ta_pre["tpLH"]) * 1e12, max(tb_pre["tpHL"], tb_pre["tpLH"]) * 1e12,
                                                                      max(ta["tpHL"], ta["tpLH"]) * 1e12, max(tb["tpHL"], tb["tpLH"]) * 1e12))
    print("RO11  Cnode %.3f -> %.3f fF   f %.2f -> %.2f GHz   t_stage %.2f -> %.2f ps   P %.1f -> %.1f uW" % (
        ro["Cnode_pre_fF"], ro["Cnode_post_fF"], ro["pre"]["f_Hz"] / 1e9, ro["post"]["f_Hz"] / 1e9, ro["pre"]["t_stage_s"] * 1e12, ro["post"]["t_stage_s"] * 1e12, ro["pre"]["P_W"] * 1e6, ro["post"]["P_W"] * 1e6))
    print("SRAM  C_BL %.1f aF/cell  t_BL(100mV,256) %.1f ps   WL %.1f aF, %.0f ohm per cell  Elmore(64) %.1f ps" % (
        c_bl_cell * 1e18, sram["t_BL_100mV_ps"], c_wl_cell * 1e18, r_wl_cell, sram["t_WL_elmore_ps"]))
