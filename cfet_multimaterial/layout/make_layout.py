#!/usr/bin/env python3
"""
make_layout.py — conceptual, DRC-clean CFET layouts for the UCM-CFET paper.

Generates (gdstk, GDSII unit 1e-6 m, precision 1e-9 m):
  * inv_cfet_{si,sige,tmd,cnt,gan}     single-gate CFET inverters (2 CPP wide, 4 tracks tall)
  * ro5_cfet_{si,sige,tmd,cnt,gan}     5-stage ring oscillators (abutted inverters + M1 feedback)
  * CFET_MULTIMATERIAL_TOP             the five RO blocks in a row with platform labels
Outputs:
  layout/gds/<cell>.gds, layout/gds/cfet_multimaterial_top.gds
  layout/drc_report.txt, layout/area_report.csv
  layout/png/<cell>.png, figures/fig_layout_inverters.png, figures/fig_layout_ro5.png

All layouts are *conceptual* (generic 3-nm-class rule set, see design_rules.md). GDSII is
2-D, so the two CFET tiers are drawn as separate layers in plan view. Run:
    python3 layout/make_layout.py
"""
from __future__ import annotations

import csv
import os
import sys
from dataclasses import dataclass

import gdstk
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Polygon as MplPolygon, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GDS_DIR = os.path.join(HERE, "gds")
PNG_DIR = os.path.join(HERE, "png")
FIG_DIR = os.path.join(ROOT, "figures")
for d in (GDS_DIR, PNG_DIR, FIG_DIR):
    os.makedirs(d, exist_ok=True)

NM = 1e-3  # 1 nm in library user units (um)

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "Liberation Sans", "Nimbus Sans", "DejaVu Sans"],
    "font.size": 8,
    "axes.labelsize": 8,
    "axes.titlesize": 9,
    "legend.fontsize": 7,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "pdf.fonttype": 42,
    "svg.fonttype": "none",
})

# ----------------------------------------------------------------------------- layer map
def read_layermap(path=os.path.join(HERE, "layermap.txt")):
    lm = {}
    order = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 4)
            layer, dtype, name, colour = int(parts[0]), int(parts[1]), parts[2], parts[3]
            desc = parts[4] if len(parts) > 4 else ""
            lm[name] = dict(layer=layer, datatype=dtype, colour=colour, desc=desc)
            order.append(name)
    return lm, order


LM, LAYER_ORDER = read_layermap()
L = {k: (v["layer"], v["datatype"]) for k, v in LM.items()}  # name -> (layer, datatype)
MARKERS = ("SIGE_TOP", "TMD_BOT", "TMD_TOP", "CNT_BOT", "CNT_TOP", "GAN_BOT", "GAN_TOP")
# draw order (bottom -> top) for rendering
DRAW_ORDER = ["PR_BOUNDARY", "NS_BOT", "NS_TOP", "GATE", "CT_BOT", "CT_TOP", "CT_GATE",
              "M0", "M1", "VIA_TIER", "VIA0"] + list(MARKERS)
ALPHA = {"NS_BOT": 0.95, "NS_TOP": 0.75, "GATE": 0.80, "CT_BOT": 0.85, "CT_TOP": 0.75,
         "CT_GATE": 0.9, "VIA_TIER": 1.0, "M0": 0.70, "VIA0": 1.0, "M1": 0.65}


# ----------------------------------------------------------------------------- geometry
@dataclass
class Geom:
    """Per-platform cell geometry (nm)."""
    platform: str
    label: str
    cpp: float          # contacted gate pitch
    lg: float           # gate length
    mp: float           # metal pitch (M0 and M1)
    wns: float          # nanosheet / channel width (plan-view y extent)
    lct: float          # S/D contact length (x)
    sgc: float          # gate-to-contact space
    ct_end: float       # contact to active end
    act_bd: float       # active to cell boundary (half diffusion break)
    height: float       # cell height (4 tracks)
    mw: float           # metal width (M0, M1, vias)
    gate_margin: float  # gate cut distance from cell top/bottom edge
    markers: tuple      # marker layers (bot, top)
    rules: str          # rule set key

    @property
    def width(self):
        return 2 * self.cpp

    def check(self):
        half = self.lg / 2 + self.sgc + self.lct + self.ct_end + self.act_bd
        assert abs(half - self.cpp) < 1e-9, f"{self.platform}: half-cell {half} != CPP {self.cpp}"


GEOMS = {
    "si":   Geom("si", "Si", 45, 16, 24, 20, 16, 8, 5, 8, 96, 12, 20, (None, None), "A"),
    "sige": Geom("sige", "SiGe", 45, 16, 24, 20, 16, 8, 5, 8, 96, 12, 20, (None, "SIGE_TOP"), "A"),
    "tmd":  Geom("tmd", "MoS$_2$/WSe$_2$", 54, 20, 24, 20, 24, 8, 4, 8, 96, 12, 20, ("TMD_BOT", "TMD_TOP"), "A"),
    "cnt":  Geom("cnt", "CNT", 54, 20, 24, 20, 24, 8, 4, 8, 96, 12, 20, ("CNT_BOT", "CNT_TOP"), "A"),
    "gan":  Geom("gan", "GaN", 200, 100, 100, 80, 80, 30, 20, 20, 400, 50, 80, ("GAN_BOT", "GAN_TOP"), "B"),
}
for g in GEOMS.values():
    g.check()

# DRC rule sets (nm): layer -> (min width, min space)
RULES = {
    "A": {
        "NS_BOT": (20, 16), "NS_TOP": (20, 16), "GATE": (16, 29), "CT_GATE": (12, 24),
        "CT_BOT": (16, 24), "CT_TOP": (16, 24), "VIA_TIER": (12, 24), "M0": (12, 12),
        "VIA0": (12, 12), "M1": (12, 12),
        "_gate_ct_space": 8, "_via_tier_enc": 2, "_ct_gate_enc": 2, "_via0_enc": 0,
    },
    "B": {
        "NS_BOT": (80, 40), "NS_TOP": (80, 40), "GATE": (100, 100), "CT_GATE": (50, 100),
        "CT_BOT": (80, 80), "CT_TOP": (80, 80), "VIA_TIER": (50, 100), "M0": (50, 50),
        "VIA0": (50, 50), "M1": (50, 50),
        "_gate_ct_space": 30, "_via_tier_enc": 15, "_ct_gate_enc": 25, "_via0_enc": 0,
    },
}


def rect(x0, y0, x1, y1, name):
    """Rectangle in nm on a named layer."""
    layer, dtype = L[name]
    return gdstk.rectangle((x0 * NM, y0 * NM), (x1 * NM, y1 * NM), layer=layer, datatype=dtype)


def label(text, x, y, name):
    layer, dtype = L[name]
    return gdstk.Label(text, (x * NM, y * NM), anchor="o", layer=layer, texttype=dtype)


class InvPins:
    """Key coordinates of an inverter cell (nm), used for RO routing."""

    def __init__(self, g: Geom):
        self.g = g
        self.W, self.H = g.width, g.height
        self.tracks = [g.mp / 2 + k * g.mp for k in range(4)]  # VSS, in, out, VDD
        self.gate_c = g.cpp
        self.src_c = g.cpp - g.lg / 2 - g.sgc - g.lct / 2
        self.drn_c = g.cpp + g.lg / 2 + g.sgc + g.lct / 2
        self.ns_c = self.H / 2
        self.pin_y0 = self.tracks[1] - g.mw
        self.pin_y1 = self.tracks[2] + g.mw


def build_inverter(lib: gdstk.Library, g: Geom) -> tuple[gdstk.Cell, InvPins]:
    p = InvPins(g)
    W, H, mw, hw = p.W, p.H, g.mw, g.mw / 2
    cell = gdstk.Cell(f"inv_cfet_{g.platform}")
    t = p.tracks

    # PR boundary
    cell.add(rect(0, 0, W, H, "PR_BOUNDARY"))

    # active (both tiers overlap in plan view: n below p)
    ns0, ns1 = p.ns_c - g.wns / 2, p.ns_c + g.wns / 2
    ax0, ax1 = g.act_bd, W - g.act_bd
    cell.add(rect(ax0, ns0, ax1, ns1, "NS_BOT"))
    cell.add(rect(ax0, ns0, ax1, ns1, "NS_TOP"))

    # common vertical gate
    gx0, gx1 = p.gate_c - g.lg / 2, p.gate_c + g.lg / 2
    cell.add(rect(gx0, g.gate_margin, gx1, H - g.gate_margin, "GATE"))

    # source contacts: n (tier 1) straps down to VSS rail, p (tier 2) straps up to VDD rail
    sx0, sx1 = p.src_c - g.lct / 2, p.src_c + g.lct / 2
    cell.add(rect(sx0, t[0] - hw, sx1, ns1, "CT_BOT"))
    cell.add(rect(sx0, ns0, sx1, t[3] + hw, "CT_TOP"))

    # drain contacts (both tiers), inter-tier via, M0 out pad
    dx0, dx1 = p.drn_c - g.lct / 2, p.drn_c + g.lct / 2
    cell.add(rect(dx0, t[1] - hw, dx1, t[2] + hw, "CT_BOT"))
    cell.add(rect(dx0, t[1] - hw, dx1, t[2] + hw, "CT_TOP"))
    cell.add(rect(p.drn_c - hw, p.ns_c - hw, p.drn_c + hw, p.ns_c + hw, "VIA_TIER"))
    cell.add(rect(p.drn_c - mw, t[2] - hw, p.drn_c + mw, t[2] + hw, "M0"))       # out pad
    cell.add(rect(p.drn_c - hw, t[2] - hw, p.drn_c + hw, t[2] + hw, "VIA0"))
    cell.add(rect(p.drn_c - hw, p.pin_y0, p.drn_c + hw, p.pin_y1, "M1"))        # out pin

    # gate contact, M0 in pad, VIA0, M1 in pin
    cell.add(rect(p.gate_c - hw, t[1] - hw, p.gate_c + hw, t[1] + hw, "CT_GATE"))
    cell.add(rect(p.gate_c - mw, t[1] - hw, p.gate_c + mw, t[1] + hw, "M0"))     # in pad
    cell.add(rect(p.gate_c - hw, t[1] - hw, p.gate_c + hw, t[1] + hw, "VIA0"))
    cell.add(rect(p.gate_c - hw, p.pin_y0, p.gate_c + hw, p.pin_y1, "M1"))      # in pin

    # power rails (M0) — VSS bottom track, VDD top track
    cell.add(rect(0, t[0] - hw, W, t[0] + hw, "M0"))
    cell.add(rect(0, t[3] - hw, W, t[3] + hw, "M0"))

    # material marker layers over the tiers
    mb, mt = g.markers
    pad = 2 if g.rules == "A" else 8
    if mb:
        cell.add(rect(ax0 - pad, ns0 - pad, ax1 + pad, ns1 + pad, mb))
    if mt:
        cell.add(rect(ax0 - pad, ns0 - pad, ax1 + pad, ns1 + pad, mt))

    # pin labels
    cell.add(label("in", p.gate_c, p.ns_c, "M1_PIN"))
    cell.add(label("out", p.drn_c, p.ns_c, "M1_PIN"))
    cell.add(label("vdd", p.gate_c, t[3], "M0_PIN"))
    cell.add(label("vss", p.gate_c, t[0], "M0_PIN"))
    lib.add(cell)
    return cell, p


def build_ro5(lib: gdstk.Library, inv: gdstk.Cell, p: InvPins, g: Geom, n=5) -> gdstk.Cell:
    W, H, mw, hw, mp = p.W, p.H, g.mw, g.mw / 2, g.mp
    t = p.tracks
    cell = gdstk.Cell(f"ro5_cfet_{g.platform}")
    fb_y = H + mp / 2                       # M1 feedback track above the row
    cell.add(rect(0, 0, n * W, H + mp, "PR_BOUNDARY"))
    for k in range(n):
        cell.add(gdstk.Reference(inv, (k * W * NM, 0)))
    # inter-stage M0 routing: out pad of stage k (track 3) -> in pad of stage k+1 (track 2)
    for k in range(n - 1):
        x_out = k * W + p.drn_c + mw               # right edge of out pad
        x_in = (k + 1) * W + p.gate_c - mw         # left edge of next in pad
        jog0, jog1 = x_in - mw, x_in + hw
        cell.add(rect(x_out, t[2] - hw, jog1, t[2] + hw, "M0"))
        cell.add(rect(jog0, t[1] - hw, jog1, t[2] + hw, "M0"))
    # M1 feedback: stage n out pin -> stage 1 in pin
    x5 = (n - 1) * W + p.drn_c
    x1 = p.gate_c
    cell.add(rect(x5 - hw, p.pin_y1, x5 + hw, fb_y + hw, "M1"))
    cell.add(rect(x1 - hw, p.pin_y1, x1 + hw, fb_y + hw, "M1"))
    cell.add(rect(x1 - hw, fb_y - hw, x5 + hw, fb_y + hw, "M1"))
    # labels: probe at n3 (output of stage 3), power
    cell.add(label("n3", 2 * W + p.drn_c, p.pin_y0 + hw, "M1_PIN"))   # probe node n3 = out of stage 3
    cell.add(label("n5_fb", x5, fb_y, "M1_PIN"))
    cell.add(label("vdd", n * W / 2, t[3], "M0_PIN"))
    cell.add(label("vss", n * W / 2, t[0], "M0_PIN"))
    lib.add(cell)
    return cell


def build_top(lib: gdstk.Library, ros: dict, geoms: dict) -> gdstk.Cell:
    top = gdstk.Cell("CFET_MULTIMATERIAL_TOP")
    x = 0.0
    gap = 100.0
    for key in ("si", "sige", "tmd", "cnt", "gan"):
        ro, g = ros[key], geoms[key]
        top.add(gdstk.Reference(ro, (x * NM, 0)))
        bb = ro.bounding_box()
        w = (bb[1][0] - bb[0][0]) / NM
        h = (bb[1][1] - bb[0][1]) / NM
        top.add(label(f"ro5_cfet_{key}", x + w / 2, h + 40, "TEXT"))
        x += w + gap
    lib.add(top)
    return top


# ----------------------------------------------------------------------------- DRC
PREC = 1e-5   # boolean precision (um) = 0.01 nm
TOL = 0.2     # nm tolerance on min-width / min-space checks
MIN_AREA = 1e-8  # um^2, ignore numerical slivers


def _polys(cell, name):
    layer, dtype = L[name]
    return cell.get_polygons(depth=None, layer=layer, datatype=dtype)


def _merge(polys):
    if not polys:
        return []
    return gdstk.boolean(polys, polys, "or", precision=PREC)


def _nonempty(polys):
    return [q for q in polys if abs(q.area()) > MIN_AREA]


def check_min_width(polys, w_nm):
    merged = _merge(polys)
    if not merged:
        return []
    d = (w_nm / 2 - TOL) * NM
    eroded = gdstk.offset(merged, -d, join="miter", precision=PREC)
    regrown = gdstk.offset(eroded, d + TOL * NM, join="miter", precision=PREC, use_union=True) if eroded else []
    return _nonempty(gdstk.boolean(merged, regrown, "not", precision=PREC)) if regrown else _nonempty(merged)


def check_min_space(polys, s_nm):
    merged = _merge(polys)
    if len(merged) < 2:
        return []
    d = (s_nm / 2 - TOL) * NM
    dil = gdstk.offset(merged, d, join="miter", precision=PREC, use_union=True)
    shr = gdstk.offset(dil, -(d + TOL * NM), join="miter", precision=PREC)
    return _nonempty(gdstk.boolean(shr, merged, "not", precision=PREC))


def check_space_between(a, b, s_nm):
    """Inter-layer spacing: dilate a by (s - tol) and intersect with b."""
    if not a or not b:
        return []
    dil = gdstk.offset(_merge(a), (s_nm - TOL) * NM, join="miter", precision=PREC, use_union=True)
    return _nonempty(gdstk.boolean(dil, b, "and", precision=PREC))


def check_enclosure(inner, outer, enc_nm):
    """inner must lie inside outer shrunk by enc."""
    if not inner:
        return []
    if not outer:
        return _nonempty(inner)
    shr = gdstk.offset(_merge(outer), -(enc_nm - TOL) * NM, join="miter", precision=PREC) if enc_nm > 0 else _merge(outer)
    return _nonempty(gdstk.boolean(inner, shr, "not", precision=PREC))


def run_drc(cell: gdstk.Cell, rules: dict, report: list) -> int:
    nviol = 0
    report.append(f"== {cell.name} (rule set) ==")
    for name, val in rules.items():
        if name.startswith("_"):
            continue
        w, s = val
        polys = _polys(cell, name)
        if not polys:
            continue
        vw = check_min_width(polys, w)
        vs = check_min_space(polys, s)
        nviol += len(vw) + len(vs)
        report.append(f"  {name:9s} n={len(polys):3d}  min_width({w:g} nm): {len(vw)} viol   min_space({s:g} nm): {len(vs)} viol")
        for q in vw[:5]:
            report.append(f"      WIDTH  @ {_bbox_nm(q)}")
        for q in vs[:5]:
            report.append(f"      SPACE  @ {_bbox_nm(q)}")
    gate = _polys(cell, "GATE")
    ct = _polys(cell, "CT_BOT") + _polys(cell, "CT_TOP")
    v = check_space_between(gate, ct, rules["_gate_ct_space"])
    nviol += len(v)
    report.append(f"  GATE-to-CT space ({rules['_gate_ct_space']:g} nm): {len(v)} viol")
    for inner, outers, enc, tag in (
        ("VIA_TIER", ("CT_BOT", "CT_TOP"), rules["_via_tier_enc"], "VIA_TIER enclosure"),
        ("CT_GATE", ("GATE",), rules["_ct_gate_enc"], "CT_GATE in GATE"),
        ("VIA0", ("M0", "M1"), rules["_via0_enc"], "VIA0 in M0 & M1"),
    ):
        inner_p = _polys(cell, inner)
        for o in outers:
            v = check_enclosure(inner_p, _polys(cell, o), enc)
            nviol += len(v)
            report.append(f"  {tag} [{o}] ({enc:g} nm): {len(v)} viol")
            for q in v[:5]:
                report.append(f"      ENC    @ {_bbox_nm(q)}")
    report.append(f"  -> {cell.name}: {nviol} violation(s)")
    report.append("")
    return nviol


def _bbox_nm(poly):
    bb = poly.bounding_box()
    return "(%.1f,%.1f)-(%.1f,%.1f) nm" % (bb[0][0] / NM, bb[0][1] / NM, bb[1][0] / NM, bb[1][1] / NM)


# ----------------------------------------------------------------------------- rendering
NAME_BY_LD = {(v["layer"], v["datatype"]): k for k, v in LM.items()}


def draw_cell(ax, cell: gdstk.Cell, title=None, scalebar=None, show_labels=True, legend=False,
              label_fs=6.5, title_fs=None):
    present = []
    polys = cell.get_polygons(depth=None)
    by_layer = {}
    for q in polys:
        name = NAME_BY_LD.get((q.layer, q.datatype), f"L{q.layer}/{q.datatype}")
        by_layer.setdefault(name, []).append(q)
    for z, name in enumerate(DRAW_ORDER):
        if name not in by_layer:
            continue
        present.append(name)
        col = LM[name]["colour"] if name in LM else "#999999"
        for q in by_layer[name]:
            pts = q.points / NM
            if name == "PR_BOUNDARY":
                ax.add_patch(MplPolygon(pts, closed=True, fill=False, ec=col, lw=0.8, ls="--", zorder=z))
            elif name in MARKERS:
                ax.add_patch(MplPolygon(pts, closed=True, fill=False, ec=col, lw=0.7, ls=":",
                                        hatch="////" if name.endswith("TOP") else "\\\\\\\\", zorder=z + 20))
            elif name in ("VIA0", "VIA_TIER"):
                ax.add_patch(MplPolygon(pts, closed=True, fc=col, ec="black", lw=0.5,
                                        hatch="xx" if name == "VIA0" else None, alpha=0.9, zorder=z))
            else:
                ax.add_patch(MplPolygon(pts, closed=True, fc=col, ec="black", lw=0.3,
                                        alpha=ALPHA.get(name, 0.8), zorder=z))
    if show_labels:
        for lb in cell.get_labels(depth=None):
            x, y = lb.origin[0] / NM, lb.origin[1] / NM
            ax.text(x, y, lb.text, ha="center", va="center", fontsize=label_fs, fontweight="bold",
                    color="black", zorder=60,
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.75))
    bb = cell.bounding_box()
    x0, y0, x1, y1 = bb[0][0] / NM, bb[0][1] / NM, bb[1][0] / NM, bb[1][1] / NM
    w, h = x1 - x0, y1 - y0
    mx, my = 0.04 * w, 0.08 * h
    if scalebar is None:
        scalebar = _nice(w / 4)
    bar_h = 0.04 * h
    bar_y = y0 - my - bar_h
    ax.add_patch(Rectangle((x0, bar_y), scalebar, bar_h, fc="black", ec="none", zorder=70))
    ax.text(x0 + scalebar + 0.02 * w, bar_y + bar_h / 2, f"{scalebar:g} nm", ha="left", va="center",
            fontsize=label_fs + 0.5, zorder=70)
    ax.set_xlim(x0 - mx, x1 + mx)
    ax.set_ylim(bar_y - my, y1 + my)
    ax.set_aspect("equal")
    ax.set_xlabel("x (nm)")
    ax.set_ylabel("y (nm)")
    if title:
        ax.set_title(title, fontsize=title_fs)
    if legend:
        ax.legend(handles=legend_handles(present), loc="upper left", bbox_to_anchor=(1.01, 1.0),
                  frameon=False, borderaxespad=0.0)
    return present


def _nice(v):
    import math
    e = 10 ** math.floor(math.log10(v))
    for k in (1, 2, 5, 10):
        if k * e >= v:
            return k * e
    return 10 * e


def legend_handles(names):
    hs = []
    for name in DRAW_ORDER:
        if name not in names:
            continue
        col = LM[name]["colour"]
        if name == "PR_BOUNDARY":
            hs.append(Patch(fc="none", ec=col, ls="--", label=name))
        elif name in MARKERS:
            hs.append(Patch(fc="none", ec=col, ls=":", hatch="////", label=name))
        elif name in ("VIA0", "VIA_TIER"):
            hs.append(Patch(fc=col, ec="black", lw=0.5, hatch="xx" if name == "VIA0" else None, label=name))
        else:
            hs.append(Patch(fc=col, ec="black", lw=0.3, alpha=ALPHA.get(name, 0.8), label=name))
    return hs


def render_cell_png(cell, path, title):
    bb = cell.bounding_box()
    w = (bb[1][0] - bb[0][0]) / NM
    h = (bb[1][1] - bb[0][1]) / NM
    aspect = max(0.25, min(4.0, h / w))
    fw = 6.5 if aspect < 1 else 4.5
    fig, ax = plt.subplots(figsize=(fw + 1.6, max(2.6, fw * aspect + 1.0)))
    draw_cell(ax, cell, title=title, legend=True)
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)


# ----------------------------------------------------------------------------- main
def write_cell_gds(cell: gdstk.Cell, path: str):
    lib = gdstk.Library(name=cell.name, unit=1e-6, precision=1e-9)
    lib.add(cell, *cell.dependencies(True))
    lib.write_gds(path)


def main():
    lib = gdstk.Library(name="CFET_MULTIMATERIAL", unit=1e-6, precision=1e-9)
    invs, pins, ros = {}, {}, {}
    for key, g in GEOMS.items():
        invs[key], pins[key] = build_inverter(lib, g)
        ros[key] = build_ro5(lib, invs[key], pins[key], g)
    top = build_top(lib, ros, GEOMS)

    # --- GDS output
    produced = []
    for key in GEOMS:
        for c in (invs[key], ros[key]):
            path = os.path.join(GDS_DIR, f"{c.name}.gds")
            write_cell_gds(c, path)
            produced.append(path)
    top_path = os.path.join(GDS_DIR, "cfet_multimaterial_top.gds")
    lib.write_gds(top_path)
    produced.append(top_path)

    # --- re-load verification
    for path in produced:
        rl = gdstk.read_gds(path)
        names = [c.name for c in rl.cells]
        want = os.path.basename(path)[:-4]
        if want == "cfet_multimaterial_top":
            want = "CFET_MULTIMATERIAL_TOP"
        assert want in names, f"{path}: cell {want} missing after reload ({names})"
        npoly = sum(len(c.polygons) for c in rl.cells)
        print(f"reload OK  {os.path.relpath(path, ROOT):45s} cells={len(names):2d} polygons={npoly}")

    # --- DRC
    report = ["CFET multi-material conceptual layout — DRC report",
              "Rule sets: A = 3-nm-class (Si, SiGe, TMD, CNT), B = GaN projected (see design_rules.md)",
              f"Boolean precision {PREC*1e3:g} nm, tolerance {TOL} nm; checks run on flattened cells.", ""]
    total = 0
    for key, g in GEOMS.items():
        for c in (invs[key], ros[key]):
            total += run_drc(c, RULES[g.rules], report)
    # top cell: flattened, checked against rule set A (every GaN dimension exceeds rule A
    # minima, so a flat check with the tighter rule set is a valid superset check), plus an
    # explicit block-to-block gap check (>= 100 nm).
    total += run_drc(top, RULES["A"], report)
    boxes = sorted((r.bounding_box() for r in top.references), key=lambda b: b[0][0])
    gaps = [(boxes[i + 1][0][0] - boxes[i][1][0]) / NM for i in range(len(boxes) - 1)]
    v_top = sum(1 for gp in gaps if gp < 100 - TOL)
    report.append("== CFET_MULTIMATERIAL_TOP block placement ==")
    report.append("  RO block gaps (nm): " + ", ".join(f"{gp:g}" for gp in gaps) + f"  (>= 100 nm): {v_top} viol")
    report.append("")
    total += v_top
    report.append(f"TOTAL VIOLATIONS: {total}  -> {'DRC CLEAN' if total == 0 else 'DRC ERRORS'}")
    with open(os.path.join(HERE, "drc_report.txt"), "w") as f:
        f.write("\n".join(report) + "\n")
    print("\n".join(report[-1:]))

    # --- area report
    with open(os.path.join(HERE, "area_report.csv"), "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["cell", "platform", "cell_width_nm", "cell_height_nm", "area_um2"])
        for key, g in GEOMS.items():
            for c in (invs[key], ros[key]):
                pr = _polys(c, "PR_BOUNDARY")
                bb = gdstk.boolean(pr, pr, "or")[0].bounding_box()
                w = (bb[1][0] - bb[0][0]) / NM
                h = (bb[1][1] - bb[0][1]) / NM
                wr.writerow([c.name, g.platform, f"{w:g}", f"{h:g}", f"{w*h*1e-6:.6f}"])

    # --- PNG renders
    titles = {}
    for key, g in GEOMS.items():
        titles[invs[key].name] = f"inv_cfet_{key}  ({g.label}, Lg={g.lg:g} nm, CPP={g.cpp:g} nm)"
        titles[ros[key].name] = f"ro5_cfet_{key}  ({g.label})"
    for key in GEOMS:
        for c in (invs[key], ros[key]):
            render_cell_png(c, os.path.join(PNG_DIR, f"{c.name}.png"), titles[c.name])
    render_cell_png(top, os.path.join(PNG_DIR, "cfet_multimaterial_top.png"), "CFET_MULTIMATERIAL_TOP")

    # --- composite: five inverters side by side
    fig, axes = plt.subplots(1, 5, figsize=(7.16, 2.75))
    present = set()
    for i, (ax, (key, g)) in enumerate(zip(axes, GEOMS.items())):
        present |= set(draw_cell(ax, invs[key], label_fs=5.5, title_fs=7.5,
                                 title=f"({'abcde'[i]}) {g.label}\n$L_g$={g.lg:g} nm, CPP={g.cpp:g} nm"))
        if ax is not axes[0]:
            ax.set_ylabel("")
        ax.tick_params(labelsize=6)
        ax.xaxis.label.set_size(7)
        ax.yaxis.label.set_size(7)
    fig.legend(handles=legend_handles(present), loc="lower center", ncol=7, frameon=False,
               bbox_to_anchor=(0.5, 0.0), handlelength=1.2, columnspacing=0.9, fontsize=6.5)
    fig.tight_layout(rect=(0, 0.17, 1, 1), w_pad=0.6)
    fig.savefig(os.path.join(FIG_DIR, "fig_layout_inverters.png"), dpi=300)
    plt.close(fig)

    # --- composite: five ROs stacked
    fig, axes = plt.subplots(5, 1, figsize=(7.16, 9.2))
    present = set()
    for i, (ax, (key, g)) in enumerate(zip(axes, GEOMS.items())):
        present |= set(draw_cell(ax, ros[key], label_fs=5.5, title_fs=8,
                                 title=f"({'abcde'[i]}) ro5_cfet_{key} ({g.label}): 5 abutted CFET inverters, M1 feedback, probe n3"))
        ax.tick_params(labelsize=6.5)
    fig.legend(handles=legend_handles(present), loc="lower center", ncol=7, frameon=False,
               bbox_to_anchor=(0.5, 0.0), handlelength=1.2, columnspacing=0.9, fontsize=6.5)
    fig.tight_layout(rect=(0, 0.045, 1, 1), h_pad=0.8)
    fig.savefig(os.path.join(FIG_DIR, "fig_layout_ro5.png"), dpi=300)
    plt.close(fig)

    print("done.")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
