"""ngspice circuit-validation flow for the five CFET platforms (open-source stand-in for the
Spectre/ADE testbenches in cadence/ and netlists/spectre/).

Testbenches (same topology, stimuli and measurement definitions as the Cadence flow):
  * inverter_subckt   – CFET inverter cell with Cstack, Cout, Rlocal_n/p (design variables)
  * tb_vtc            – DC VTC: VM, max gain, NML/NMH (unity-gain method), static IDD
  * tb_inv_tran       – vpulse (0->VDD, 100 ps delay, 5 ps edges, 500 ps width, 1 ns period):
                        tpHL/tpLH at 50 % crossings, switching energy from VDD*IDD
  * tb_ro             – N-stage RO with IC V(n1)=0 and a 1 % p-FET width mismatch in stage 1;
                        two-pass transient (coarse pass finds the period, fine pass uses
                        maxstep = T/300 and stops after 40 cycles); fRO from rising VDD/2
                        crossings of V(n3) (cycles 10..30), Pavg over the same window,
                        tpd = 1/(2 N fRO), Ecycle = Pavg/fRO, PDP = Pavg*tpd
"""
from __future__ import annotations
import os, subprocess, tempfile, shutil, uuid
import numpy as np
from .platforms import PLATFORMS, DEVICES, PARAM_ORDER

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(HERE, "netlists", "ngspice", "ucm_cfet.lib")
SCRATCH = os.environ.get("CFET_SCRATCH", os.path.join(tempfile.gettempdir(), "cfet_ng"))
OPTIONS = ".options reltol=1e-4 abstol=1e-14 vntol=1e-7 chgtol=1e-18 gmin=1e-15 method=gear maxord=2\n"


def _ovr(d: dict | None) -> str:
    return " ".join(f"{k}={float(v)!r}" for k, v in (d or {}).items() if k in PARAM_ORDER)


def run_ngspice(netlist: str, tag: str = "run", keep: bool = False) -> dict:
    """Run a netlist in batch mode; returns {vector_name: array} from every wrdata file."""
    wd = os.path.join(SCRATCH, f"{tag}_{uuid.uuid4().hex[:8]}")
    os.makedirs(wd, exist_ok=True)
    cir = os.path.join(wd, "tb.cir")
    open(cir, "w").write(netlist)
    r = subprocess.run(["ngspice", "-b", cir], cwd=wd, capture_output=True, text=True, timeout=1800)
    out = {"_log": r.stdout + r.stderr, "_wd": wd}
    for f in sorted(os.listdir(wd)):
        if f.endswith(".dat"):
            try:
                with open(os.path.join(wd, f)) as fh:
                    hdr = fh.readline().split()
                a = np.loadtxt(os.path.join(wd, f), skiprows=1, ndmin=2)
                for k, name in enumerate(hdr):
                    out[name] = a[:, k]
            except Exception as e:  # pragma: no cover
                out["_err_" + f] = str(e)
    if not keep:
        shutil.rmtree(wd, ignore_errors=True)
    return out


def inverter_subckt(pl: str, name: str, vdd: float, temp_c: float, cstack=None, cout=None, rlocal=None,
                    ov_n=None, ov_p=None, p_width_scale=1.0) -> str:
    """CFET inverter cell. p_width_scale implements the stated 1 % start-up mismatch."""
    P = PLATFORMS[pl]
    cstack = P["cstack"] if cstack is None else cstack
    cout = P["cout"] if cout is None else cout
    rlocal = P["rlocal"] if rlocal is None else rlocal
    ov_p = dict(ov_p or {})
    if p_width_scale != 1.0:
        pp = DEVICES[P["p"]]["params"]
        if pp["NNS"] > 0:
            ov_p["WNS"] = ov_p.get("WNS", pp["WNS"]) * p_width_scale
        else:
            ov_p["W"] = ov_p.get("W", pp["W"]) * p_width_scale
    tk = temp_c + 273.15
    return f"""
.subckt {name} in out vdd vss
Xn dn in vss vss {P['n']} TEMPK={tk!r} {_ovr(ov_n)}
Xp dp in vdd vdd {P['p']} TEMPK={tk!r} {_ovr(ov_p)}
Rlocn dn out {rlocal!r}
Rlocp dp out {rlocal!r}
Cstack dn dp {cstack!r}
Cout out vss {cout!r}
.ends {name}
"""


# ------------------------------------------------------------------ VTC -----------------
def tb_vtc(pl, vdd=None, temp_c=27.0, npts=401, **kw):
    P = PLATFORMS[pl]; vdd = P["vdd"] if vdd is None else vdd
    net = f"""* VTC {pl}
.include {LIB}
{OPTIONS}{inverter_subckt(pl, 'inv', vdd, temp_c, **kw)}
Vdd vdd 0 dc {vdd!r}
Vin in 0 dc 0
X1 in out vdd 0 inv
.control
set wr_singlescale
set wr_vecnames
dc Vin 0 {vdd!r} {vdd / (npts - 1)!r}
wrdata vtc.dat v(out) i(vdd)
quit
.endc
.end
"""
    r = run_ngspice(net, f"vtc_{pl}")
    vin, vout, idd = r.get("v-sweep"), r.get("v(out)"), r.get("i(vdd)")
    if vout is None:
        return dict(ok=False, log=r["_log"])
    g = np.gradient(vout, vin)
    k = np.argmin(np.abs(vout - vin)); vm = vin[k]
    gain = float(np.max(np.abs(g)))
    # unity-gain points
    idx = np.where(np.abs(g) >= 1.0)[0]
    if len(idx):
        vil, vih = vin[idx[0]], vin[idx[-1]]
        voh, vol = vout[idx[0]], vout[idx[-1]]
        nml, nmh = vil - vol, voh - vih
    else:
        vil = vih = voh = vol = nml = nmh = float("nan")
    return dict(ok=True, vdd=vdd, VM=float(vm), gain=gain, VIL=float(vil), VIH=float(vih), VOL=float(vol),
                VOH=float(voh), NML=float(nml), NMH=float(nmh), Istat_low=float(-idd[0]), Istat_high=float(-idd[-1]),
                Pstat=float(vdd * 0.5 * (-idd[0] - idd[-1])), vin=vin, vout=vout, idd=-idd)


# ------------------------------------------------------------------ inverter transient --
def tb_inv_tran(pl, vdd=None, temp_c=27.0, cload=None, **kw):
    P = PLATFORMS[pl]; vdd = P["vdd"] if vdd is None else vdd
    cload = P["cload"] if cload is None else cload
    net = f"""* inverter transient {pl}
.include {LIB}
{OPTIONS}{inverter_subckt(pl, 'inv', vdd, temp_c, **kw)}
Vdd vdd 0 dc {vdd!r}
Vin in 0 dc 0 pulse(0 {vdd!r} 100p 5p 5p 500p 1n)
X1 in out vdd 0 inv
Cl out 0 {cload!r}
.control
set wr_singlescale
set wr_vecnames
tran 0.05p 2.1n 0 0.2p
wrdata tr.dat v(in) v(out) i(vdd)
quit
.endc
.end
"""
    r = run_ngspice(net, f"invtr_{pl}")
    t, vin, vout, idd = r.get("time"), r.get("v(in)"), r.get("v(out)"), r.get("i(vdd)")
    if vout is None:
        return dict(ok=False, log=r["_log"])
    half = vdd / 2

    def cross(x, y, level, rising, tmin):
        s = np.where((t[:-1] >= tmin) & (((y[:-1] < level) & (y[1:] >= level)) if rising else ((y[:-1] > level) & (y[1:] <= level))))[0]
        if len(s) == 0:
            return np.nan
        i = s[0]
        return t[i] + (level - y[i]) * (t[i + 1] - t[i]) / (y[i + 1] - y[i])
    # period 2 (1 ns..2 ns): rising input at ~1.1 ns, falling at ~1.6 ns
    tin_r = cross(t, vin, half, True, 1.0e-9); tout_f = cross(t, vout, half, False, 1.0e-9)
    tin_f = cross(t, vin, half, False, 1.5e-9); tout_r = cross(t, vout, half, True, 1.5e-9)
    tphl, tplh = tout_f - tin_r, tout_r - tin_f
    p = vdd * (-idd)
    m = (t >= 1.0e-9) & (t <= 2.0e-9)
    e_period = np.trapezoid(p[m], t[m])
    m1 = (t >= 1.0e-9) & (t <= 1.5e-9); m2 = (t >= 1.5e-9) & (t <= 2.0e-9)
    return dict(ok=True, vdd=vdd, tpHL=float(tphl), tpLH=float(tplh), tpd=float(0.5 * (tphl + tplh)),
                E_period=float(e_period), E_HL=float(np.trapezoid(p[m1], t[m1])), E_LH=float(np.trapezoid(p[m2], t[m2])),
                Pavg=float(e_period / 1e-9), t=t, vin=vin, vout=vout, idd=-idd)


# ------------------------------------------------------------------ ring oscillator -------
def _ro_netlist(pl, N, vdd, temp_c, tstop, maxstep, inv_kw, probe="n3"):
    stages = []
    for i in range(1, N + 1):
        a = f"n{i}"; b = f"n{i + 1}" if i < N else "n1"
        stages.append(f"X{i} {a} {b} vdd 0 {'inv_s1' if i == 1 else 'inv'}")
    return f"""* {N}-stage RO {pl}
.include {LIB}
{OPTIONS}{inverter_subckt(pl, 'inv', vdd, temp_c, **inv_kw)}{inverter_subckt(pl, 'inv_s1', vdd, temp_c, p_width_scale=1.01, **inv_kw)}
Vdd vdd 0 dc {vdd!r}
{chr(10).join(stages)}
.ic v(n1)=0
.control
set wr_singlescale
set wr_vecnames
tran {maxstep!r} {tstop!r} 0 {maxstep!r}
wrdata ro.dat v({probe}) i(vdd)
quit
.endc
.end
"""


def _rising_crossings(t, v, level):
    i = np.where((v[:-1] < level) & (v[1:] >= level))[0]
    return t[i] + (level - v[i]) * (t[i + 1] - t[i]) / (v[i + 1] - v[i])


def thermal_settle(pl, inv_kw):
    """5 thermal time constants (RTH*CTH) of the slower device, 0 for platforms without
    self-heating: the RO measurement window starts only after the device temperature has
    settled, so fRO/Pavg include the steady-state self-heating."""
    tau = 0.0
    for dn, key in ((PLATFORMS[pl]["n"], "ov_n"), (PLATFORMS[pl]["p"], "ov_p")):
        pp = dict(DEVICES[dn]["params"]); pp.update(inv_kw.get(key) or {})
        tau = max(tau, pp["RTH"] * pp["CTH"])
    return 5.0 * tau


def tb_ro(pl, N=5, vdd=None, temp_c=27.0, cycles=(10, 30), T_est=None, **inv_kw):
    """Two-pass RO measurement. The period estimate for the coarse pass comes from the
    inverter-delay testbench (T ~ 2 N tpd) unless given; the fine pass then uses a uniform
    window of `cycles` (counted after the thermal settling time) with maxstep = T/300,
    identical for every material platform."""
    P = PLATFORMS[pl]; vdd = P["vdd"] if vdd is None else vdd
    settle = thermal_settle(pl, inv_kw)
    if T_est is None:
        d = tb_inv_tran(pl, vdd=vdd, temp_c=temp_c, **{k: v for k, v in inv_kw.items() if k != "cload"})
        if not d["ok"] or not np.isfinite(d["tpd"]) or d["tpd"] <= 0:
            return dict(ok=False, osc=False, log=d.get("log", "inverter delay failed"))
        T_est = 2.0 * N * d["tpd"] * 1.2
    # pass 1: coarse (15 estimated periods) to pin the period down
    r = run_ngspice(_ro_netlist(pl, N, vdd, temp_c, 15 * T_est, T_est / 100.0, inv_kw), f"ro_{pl}")
    t, v = r.get("time"), r.get("v(n3)")
    if v is None:
        return dict(ok=False, log=r["_log"], osc=False)
    tc = _rising_crossings(t, v, vdd / 2)
    if len(tc) < 4:   # not oscillating within the estimate: widen once (x8)
        r = run_ngspice(_ro_netlist(pl, N, vdd, temp_c, 120 * T_est, T_est / 100.0, inv_kw), f"ro_{pl}")
        t, v = r.get("time"), r.get("v(n3)")
        tc = _rising_crossings(t, v, vdd / 2)
        if len(tc) < 4:
            return dict(ok=True, osc=False, fRO=0.0, log=r["_log"][-2000:], t=t, v=v)
    T0 = float(np.median(np.diff(tc[len(tc) // 2:])))
    # pass 2: fine, uniform measurement window in cycles (after thermal settling, if any)
    tstop = settle + T0 * (cycles[1] + 12); maxstep = T0 / 300.0
    r = run_ngspice(_ro_netlist(pl, N, vdd, temp_c, tstop, maxstep, inv_kw), f"ro_{pl}")
    t, v, idd = r.get("time"), r.get("v(n3)"), r.get("i(vdd)")
    tc = _rising_crossings(t, v, vdd / 2)
    tc = tc[tc >= settle]
    if len(tc) <= cycles[1]:
        return dict(ok=True, osc=False, fRO=0.0, t=t, v=v)
    T = (tc[cycles[1]] - tc[cycles[0]]) / (cycles[1] - cycles[0])
    T_1011 = tc[cycles[0] + 1] - tc[cycles[0]]
    f = 1.0 / T
    m = (t >= tc[cycles[0]]) & (t <= tc[cycles[1]])
    pavg = np.trapezoid(vdd * (-idd[m]), t[m]) / (tc[cycles[1]] - tc[cycles[0]])
    tpd = 1.0 / (2 * N * f)
    return dict(ok=True, osc=True, vdd=vdd, N=N, fRO=float(f), fRO_cycle10_11=float(1 / T_1011), period=float(T), tpd=float(tpd),
                Pavg=float(pavg), Ecycle=float(pavg / f), PDP=float(pavg * tpd), Vswing=float(v[m].max() - v[m].min()),
                t=t, v=v, idd=-idd, tcross=tc)


if __name__ == "__main__":
    import sys
    pl = sys.argv[1] if len(sys.argv) > 1 else "si"
    v = tb_vtc(pl); print({k: v[k] for k in ["VM", "gain", "NML", "NMH", "Istat_low", "Istat_high"]} if v["ok"] else v["log"][-1500:])
    d = tb_inv_tran(pl); print({k: d[k] for k in ["tpHL", "tpLH", "tpd", "E_period"]} if d["ok"] else d["log"][-1500:])
    o = tb_ro(pl); print({k: o[k] for k in ["osc", "fRO", "tpd", "Pavg", "Ecycle", "PDP", "Vswing"] if k in o} if o["ok"] else o["log"][-1500:])
