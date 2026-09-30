#!/usr/bin/env python3
"""
gaa3_pex.py -- parasitic RC extraction of the GAA3 GDSII cells (reference extractor; sign-off: Quantus QRC).

Uses the net/device recognition of gaa3_lvs.extract() and the GAA3 PEX technology table below:
  device level : parasitic gate-to-source and gate-to-drain coupling of a 3-sheet stack, 0.25 aF per nm
                 of effective width per side (inner-spacer / epi capacitance, [1], [3])
  contacts     : SDC-to-isolation area capacitance; contact resistance rho_c / A(SDC on diffusion)
  metals       : area to ground (eps_ild / h), fringe per edge length, lateral coupling eps_ild * t / gap
                 between facing edges on the same layer (< 60 nm apart), overlap capacitance between
                 vertically adjacent layers, sheet resistance per square; vias as fixed resistances
Outputs per cell: <name>.pex.json (per-net C_gnd, coupling matrix, R), <name>.spef (IEEE 1481 SPEF),
                  <name>.pex.sum (Quantus-style summary).

    python3 gaa3_pex.py <cell.gds> [<cell.gds> ...]
"""
import json, math, os, sys
import gaa3_lvs as lvs

EPS0 = 8.854e-12
TECH = {  # layer: thickness t (nm), height h of its bottom above ground reference (nm), k of surrounding dielectric, Rs (ohm/sq)
    (3, 0):  dict(name="GATE", t=45, h=0,  k=3.9, rs=60),
    (4, 0):  dict(name="SDC",  t=60, h=0,  k=4.5, rs=40),
    (5, 0):  dict(name="CB",   t=30, h=45, k=4.5, rs=40),
    (7, 0):  dict(name="M1",   t=30, h=85, k=2.9, rs=22),
    (9, 0):  dict(name="M2",   t=32, h=145, k=2.9, rs=18),
    (11, 0): dict(name="M3",   t=36, h=211, k=2.9, rs=15),
}
VIA_R = {(6, 0): ("V0", 45.0), (8, 0): ("V1", 35.0), (10, 0): ("V2", 30.0)}
STACK = [((3, 0), (7, 0)), ((4, 0), (7, 0)), ((7, 0), (9, 0)), ((9, 0), (11, 0))]   # vertically adjacent pairs for overlap C
C_GSD_PER_WEFF = 0.25          # aF per nm of W_eff, per side (gate-to-S/D parasitic of the sheet stack)
C_SDC_ISO = 2.5e-3             # aF per nm^2, contact/epi to the bottom dielectric isolation
RHO_C = 1.0e5                  # ohm nm^2 (1e-9 ohm cm^2) contact resistivity SDC-to-epi
CB_R = 80.0                    # ohm, gate contact
FRINGE = 0.03                  # aF per nm of edge length (metal fringe to ground)
LATERAL_MAX_GAP = 60.0

def aF_per_nm2(k, h): return k * EPS0 / (h * 1e-9) * 1e-18 * 1e18 / 1e18 * 1e18  # F/m^2 -> aF/nm^2 == F/m^2 * 1e-18/1e-18 ... (=k*eps0/h [F/m^2])
def area_cap(k, h_nm): return k * EPS0 / (h_nm * 1e-9)          # F/m^2 == aF/nm^2
def lateral_cap(k, t_nm, gap_nm): return k * EPS0 * (t_nm * 1e-9) / (gap_nm * 1e-9) * 1e9   # F/m -> aF/nm (1 F/m = 1e9 aF/nm)

def facing(a, b):
    """facing length and gap between two axis-aligned rects (x0,y0,x1,y1); (0, None) if not facing."""
    ax0, ay0, ax1, ay1 = a; bx0, by0, bx1, by1 = b
    ox = min(ax1, bx1) - max(ax0, bx0); oy = min(ay1, by1) - max(ay0, by0)
    if ox > 0 and oy <= 0: return ox, max(by0 - ay1, ay0 - by1)
    if oy > 0 and ox <= 0: return oy, max(bx0 - ax1, ax0 - bx1)
    return 0, None

def overlap(a, b):
    ax0, ay0, ax1, ay1 = a; bx0, by0, bx1, by1 = b
    return max(0, min(ax1, bx1) - max(ax0, bx0)) * max(0, min(ay1, by1) - max(ay0, by0))

def extract(path):
    lay = lvs.extract(path)
    names = lay["names"]; devices = lay["devices"]; geom = lay["geom"]; chans = lay["channels"]
    nets = {}
    dev_nets = {n for d in devices if not d.get("bad") for n in [d["g"]] + d["sd"]}
    counters = {"int": 0, "float": 0}
    def net(n):
        if n not in nets:
            if names.get(n): nm = names[n]
            else:
                kind = "int" if n in dev_nets else "float"
                nm = f"{kind}{counters[kind]}"; counters[kind] += 1
            nets[n] = dict(name=nm, cgnd=0.0, coup={}, r=0.0, elems=[], floating=(n not in dev_nets and not names.get(n)))
        return nets[n]
    def couple(n1, n2, c, tag):
        if n1 is None or n2 is None or c <= 0: return
        if n1 == n2: return
        g1, g2 = names.get(n1) in lvs.GLOBALS, names.get(n2) in lvs.GLOBALS
        if g1 and g2: return
        if g2: net(n1)["cgnd"] += c; return
        if g1: net(n2)["cgnd"] += c; return
        net(n1)["coup"][n2] = net(n1)["coup"].get(n2, 0.0) + c
        net(n2)["coup"][n1] = net(n2)["coup"].get(n1, 0.0) + c
    # ---- device-level gate-to-S/D parasitics
    for d in devices:
        if d.get("bad"): continue
        weff = 3 * 2 * (d["W"] + 5)
        for sd in d["sd"]:
            couple(d["g"], sd, C_GSD_PER_WEFF * weff, "gsd")
    # ---- geometry: area / fringe / lateral / overlap / resistance
    rects = [(g["layer"], g["bbox"], g["net"]) for g in geom if g["net"] is not None]
    chan_area_by_gate = {}
    for lay_, bb, n in rects:
        x0, y0, x1, y1 = bb; w, h = x1 - x0, y1 - y0; A = w * h; P = 2 * (w + h)
        if lay_ in TECH:
            tk = TECH[lay_]
            if lay_ == (3, 0):                       # gate over isolation only (channel area is in the device model)
                ch = sum(overlap(bb, [c[0][0], c[0][1], c[1][0], c[1][1]]) for c in chans)
                net(n)["cgnd"] += area_cap(tk["k"], 30) * max(A - ch, 0)
                net(n)["r"] += tk["rs"] * (max(w, h) / max(min(w, h), 1)) * 0.5     # distributed gate line: half
            elif lay_ == (4, 0):
                net(n)["cgnd"] += C_SDC_ISO * A
                diff = sum(overlap(bb, r[1]) for r in rects if r[0] == "DIFF")
                if diff > 0:
                    net(n)["r"] += RHO_C / diff; net(n)["elems"].append(("Rc", RHO_C / diff))
            elif lay_ == (5, 0):
                net(n)["r"] += CB_R; net(n)["elems"].append(("CB", CB_R))
            else:
                net(n)["cgnd"] += area_cap(tk["k"], tk["h"]) * A + FRINGE * P
                sq = max(w, h) / max(min(w, h), 1)
                net(n)["r"] += tk["rs"] * sq; net(n)["elems"].append((tk["name"], tk["rs"] * sq))
        elif lay_ in VIA_R:
            net(n)["r"] += VIA_R[lay_][1]; net(n)["elems"].append(VIA_R[lay_])
    # lateral coupling on the same layer, overlap between adjacent layers
    for i in range(len(rects)):
        li, bi, ni = rects[i]
        for j in range(i + 1, len(rects)):
            lj, bj, nj = rects[j]
            if ni == nj or ni is None or nj is None: continue
            if li == lj and li in TECH and li not in ((5, 0),):
                L, gap = facing(bi, bj)
                if L > 0 and gap is not None and 0 < gap <= LATERAL_MAX_GAP:
                    tk = TECH[li]; couple(ni, nj, lateral_cap(tk["k"], tk["t"], gap) * L, "lat")
            elif (li, lj) in STACK or (lj, li) in STACK:
                lo, hi = (li, lj) if (li, lj) in STACK else (lj, li)
                A = overlap(bi, bj)
                if A > 0:
                    hsep = TECH[hi]["h"] - (TECH[lo]["h"] + TECH[lo]["t"])
                    couple(ni, nj, area_cap(TECH[hi]["k"], max(hsep, 10)) * A, "ovl")
    out = dict(cell=lay["cell"], nets={}, devices=len([d for d in devices if not d.get("bad")]))
    for n, v in nets.items():
        out["nets"][v["name"]] = dict(cgnd_aF=round(v["cgnd"], 2), coup_aF={nets[m]["name"]: round(c, 2) for m, c in v["coup"].items()},
                                     ctotal_aF=round(v["cgnd"] + sum(v["coup"].values()), 2), r_ohm=round(v["r"], 1),
                                     n_res=len(v["elems"]), floating=v["floating"],
                                     elems=[(e[0], round(e[1], 1)) for e in v["elems"]])
    out["totals"] = dict(nets=len(nets), cgnd_aF=round(sum(v["cgnd"] for v in nets.values()), 2),
                         ccoup_aF=round(sum(sum(v["coup"].values()) for v in nets.values()) / 2, 2),
                         resistors=sum(len(v["elems"]) for v in nets.values()),
                         capacitors=sum(1 for v in nets.values() if v["cgnd"] > 0) + sum(len(v["coup"]) for v in nets.values()) // 2)
    return out

def spef(o, path):
    L = ['*SPEF "IEEE 1481-1998"', f'*DESIGN "{o["cell"]}"', '*DATE "2026"', '*VENDOR "GAA3 reference extractor (gaa3_pex.py)"',
         '*PROGRAM "gaa3_pex"', '*VERSION "1.0"', '*DESIGN_FLOW "PIN_CAP NONE" "NAME_SCOPE LOCAL"', '*DIVIDER /', '*DELIMITER :',
         '*BUS_DELIMITER [ ]', '*T_UNIT 1 PS', '*C_UNIT 1 FF', '*R_UNIT 1 OHM', '*L_UNIT 1 HENRY', '', '*NAME_MAP']
    ids = {}
    for i, n in enumerate(o["nets"], 1): ids[n] = i; L.append(f"*{i} {n}")
    L.append("")
    for n, v in o["nets"].items():
        L += [f"*D_NET *{ids[n]} {v['ctotal_aF']/1e3:.5f}", "*CONN", f"*P *{ids[n]} B", "*CAP"]
        k = 1
        if v["cgnd_aF"] > 0: L.append(f"{k} *{ids[n]}:1 {v['cgnd_aF']/1e3:.5f}"); k += 1
        for m, c in v["coup_aF"].items():
            if ids[m] > ids[n]: L.append(f"{k} *{ids[n]}:1 *{ids[m]}:1 {c/1e3:.5f}"); k += 1
        L += ["*RES", f"1 *{ids[n]}:1 *{ids[n]}:2 {v['r_ohm']:.2f}", "*END", ""]
    open(path, "w").write("\n".join(L))

def summary(o):
    t = o["totals"]
    L = ["=" * 78, "  Quantus QRC  -  Extraction Summary  (reference extractor: gaa3_pex.py; sign-off: Quantus QRC)", "=" * 78,
         f"  Cell            : {o['cell']}", f"  Extraction type : rc_coupled, decoupled ground for VDD/VSS, coupling threshold 0 aF",
         f"  Technology      : GAA3 PEX (ILD k=2.9, spacer k=4.5, Rs M1/M2/M3 = 22/18/15 ohm/sq, rho_c = 1e-9 ohm cm^2)",
         f"  Nets            : {t['nets']:5d}      Devices : {o['devices']:4d}", f"  Capacitors      : {t['capacitors']:5d}      Resistors : {t['resistors']:4d}",
         f"  Total C to gnd  : {t['cgnd_aF']/1e3:8.3f} fF     Total coupling C : {t['ccoup_aF']/1e3:8.3f} fF", "-" * 78,
         f"  {'NET':<10}{'C_gnd(aF)':>12}{'C_coup(aF)':>12}{'C_tot(aF)':>12}{'R(ohm)':>10}{'#R':>5}   coupled to", "-" * 78]
    for n, v in sorted(o["nets"].items()):
        cc = sum(v["coup_aF"].values())
        tag = "  (floating dummy gate)" if v.get("floating") else ""
        L.append(f"  {n:<10}{v['cgnd_aF']:12.1f}{cc:12.1f}{v['ctotal_aF']:12.1f}{v['r_ohm']:10.1f}{v['n_res']:5d}   " + ", ".join(f"{m}:{c:.1f}" for m, c in v["coup_aF"].items()) + tag)
    L += ["-" * 78, f"  SPEF written    : {o['cell'].lower()}.spef", "=" * 78]
    return "\n".join(L) + "\n"

if __name__ == "__main__":
    for p in sys.argv[1:]:
        o = extract(p); base = os.path.splitext(os.path.basename(p))[0]
        json.dump(o, open(f"{base}.pex.json", "w"), indent=1); spef(o, f"{base}.spef"); open(f"{base}.pex.sum", "w").write(summary(o))
        print(summary(o))
